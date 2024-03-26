import peer
import sys

_help = "Usage\n"
_help += "help\tprints this message\n"
_help += "connect [Port]\tConnects to `localhost:port`\n"
_help += "send [Message]\tsends message to all peers\n"
_help += "exit\tcloses the server\n"

def help(_ = None, __ = None):
    print(_help)

def _connect(peer: peer.Peer, args):
    peer.connect("localhost", int(args[0]))

def _send(peer: peer.Peer, args):
    msg = " ".join(args)
    msg = {
        "host": peer.hostname(),
        "message": msg
    }
    peer.send_all(msg)

def _exit(peer: peer.Peer, _ = None):
    peer.close()
    sys.exit(0)

COMMANDS = {
    "help": help,
    "connect": _connect,
    "send": _send,
    "exit": _exit
}

def exists(command):
    for i in COMMANDS.keys():
        if i == command:
            return True
    return False
