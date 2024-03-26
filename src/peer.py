import socket
import threading
import json
from collections import deque
import time

HEARTBEAT_DELAY = 10
RECV_SIZE = 256
RECV_DELAY = 1

TYPE_HEARTBEAT = "heartbeat"

class SSocket:
    def __init__(self, socket: socket.socket):
        self.socket = socket
        self.alive = True

    def __str__(self) -> str:
        try:
            return f"{self.socket.getpeername()},alive={self.alive}"
        except:
            return f"NOT CONNECTED, alive={self.alive}"

class Peer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_thread = threading.Thread(target=self.listen, daemon=True)
        self.recv_thread = threading.Thread(target=self.recv, daemon=True)
        self.heartbeat = threading.Thread(target=self._heartbeat, daemon=True)
        # self.heartbeat_handler = threading.Thread(target=self._heartbeat_q_handler, daemon=True)
        self.connections: dict[socket._RetAddress, SSocket] = {}
        self.is_close = False
        self.lock = threading.Lock()
        self.messages = deque()
        self._hb_q = deque()

        self.listen_thread.start()
        self.recv_thread.start()
        self.heartbeat.start()
        # self.heartbeat_handler.start()

    def hostname(self) -> str:
        return f"{self.host}:{self.port}"

    def _heartbeat_q_handler(self):
        with self.lock:
            while len(self._hb_q) != 0:
                data = self._hb_q.pop()
                try:
                    data_j = dict(json.loads(data[0]))
                    peername = data[1]
                    if self.connections[peername].alive:
                        continue

                    keys = data_j.keys()
                    self.messages.append(data)
                    self.connections[peername].alive = True
                    if "type" in keys and data_j["type"] == TYPE_HEARTBEAT:
                        if "ping" in keys:
                            datar = json.dumps({
                                "host": self.hostname(),
                                "type": TYPE_HEARTBEAT,
                                "ping-response": self.hostname()
                            })
                            self.connections[peername].socket.send(datar.encode())
                            self.messages.append(datar)
                except Exception as e:
                    self.messages.append(f"_heartbeat_q_handler {e}")

    def _heartbeat(self):
        while not self.is_close:
            with self.lock:
                self.messages.append("starting heartbeat")
                for address in self.connections:
                    try:
                        ssocket = self.connections[address]
                        ssocket.alive = False
                        sc = ssocket.socket

                        data = json.dumps({
                            "host": self.hostname(),
                            "type": TYPE_HEARTBEAT,
                            "ping": self.hostname()
                        });
                        sc.send(data.encode());
                        self.messages.append(data)
                    except Exception as e:
                        self.messages.append(f"_heartbeat {e}")

            time.sleep(HEARTBEAT_DELAY)

            self._heartbeat_q_handler()

            time.sleep(HEARTBEAT_DELAY)

            with self.lock:
                to_remove: list[socket._RetAddress] = []
                for address in self.connections:
                    try:
                        ssocket = self.connections[address]
                        if not ssocket.alive:
                            self.messages.append(f"removing {ssocket}")
                            to_remove.append(address)
                    except Exception as e:
                        self.messages.append(f"_heartbeat {e}")

                for i in range(len(to_remove)):
                    addr = to_remove[i]
                    try:
                        ssocket = self.connections.pop(addr)
                        ssocket.socket.shutdown(socket.SHUT_WR)
                        ssocket.socket.close()
                    except Exception as e:
                        self.messages.append(f"_heartbeat {e}")

            time.sleep(HEARTBEAT_DELAY)

        print("heartbeat thread close")

    def listen(self) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)

        print("starting listening thread")
        while not self.is_close:
            conn, address = self.socket.accept()
            conn.setblocking(False)
            with self.lock:
                self.connections[address] = SSocket(conn)
                self.messages.append(("receive connection", self.connections[address].socket.getpeername()))

            conn.send(json.dumps({
                "host": self.hostname()
            }).encode())

            time.sleep(3)
        print("listen thread close")


    def connect(self, ip: str, port: int) -> None:
        try:
            msocket = socket.create_connection((ip,port))
            msocket.setblocking(False)
            self.messages.append(("connecting to ", (ip, port)))
            with self.lock:
                self.connections[msocket.getpeername()] = SSocket(msocket)

        except socket.error as e:
            print(e)

    def recv(self):
        while not self.is_close:
            with self.lock:
                for address in self.connections:
                    try:
                        ssocket = self.connections[address]
                        socket = ssocket.socket
                        data = socket.recv(RECV_SIZE)
                        if not data or len( data ) == 0:
                            continue

                        ssocket.alive = True
                        try:
                            dataj = json.loads(data.decode())
                            keys = dataj.keys()
                            if "type" in keys and dataj["type"] == TYPE_HEARTBEAT:
                                self._hb_q.append(( data.decode(), socket.getpeername() ))
                                self.messages.append(( data.decode(), socket.getpeername() ))
                            else:
                                self.messages.append(( data.decode(), socket.getpeername() ))
                        except Exception as e:
                            self.messages.append(f"recv {e}")
                    except:
                        # ignore resource temp unavailable error
                        pass
            time.sleep(RECV_DELAY)
        print("recv thread close")

    def send_all(self, data):
        with self.lock:
            for address in self.connections:
                socket = self.connections[address].socket
                msg = json.dumps(data).encode()
                socket.send(json.dumps(data).encode())
                self.messages.append(msg)

    def close(self):
        self.is_close = True
        self.recv_thread.join()
        self.heartbeat.join()
        # self.heartbeat_handler.join()

        with self.lock:
            self.socket.shutdown(socket.SHUT_WR)
            self.socket.close()
            print("successfully closed the server")

    def print_messages(self):
        if len( self.messages ) == 0:
            return
        with self.lock:
            print("------------ MESSAGES ------------")
            for _ in range(len( self.messages )):
                print(self.messages.pop())
            print("----------------------------------")

    def print_connections(self):
        if len(self.connections) == 0:
            return
        with self.lock:
            print("---------- CONNECTIONS -----------")
            for addr in self.connections:
                print(self.connections[addr])
            print("----------------------------------")

