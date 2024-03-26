import logging
from peer import Peer
import sys
import commands

if len(sys.argv) == 1:
    print("No argument found. Enter a PORT as an argument")
    sys.exit(1)

LOG = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = int(sys.argv[1])

prompt = ">> "
peer = None

def dialog():
    global peer, prompt, help
    commands.help()
    while True and peer:
        inp = input(prompt)
        args = inp.split(' ')
        if (len(args[0]) != 0):
            if commands.exists(args[0]):
                commands.COMMANDS[args[0]](peer, args[1::])
            else:
                print("unknown command")

        peer.print_messages()
        peer.print_connections()

def main():
    global peer
    peer = Peer(HOST, PORT)
    dialog()

if __name__ == "__main__":
    main()
