import argparse #Purpose: Parse command-line flags like -l, -p, -t, -c, -e, -u.
import socket   # Purpose: Create TCP sockets, connect/listen, send/recv bytes.
import shlex    # Purpose: Split a command string safely into argv pieces (handles quoting).
import subprocess # Purpose: Run OS commands when you use -e or -c modes.
import sys      # Purpose: Read stdin for piped input; exit cleanly.
import textwrap # Purpose: Format the help text (epilog) nicely.
import threading  # Purpose: Handle multiple incoming clients concurrently in listen mode.


def execute(cmd):       # Purpose: Given a text command (like "whoami"), run it on the local OS and return its stdout as a string.
    cmd = cmd.strip()   # Purpose: Remove leading/trailing whitespace/newlines so blank/space-only commands don’t get executed.
    if not cmd:         # Purpose: If the command is empty after stripping, do nothing
        return
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)    # Purpose: Run the command and capture output. shlex.split(cmd) turns "cat /etc/passwd" into ["cat","/etc/passwd"]. stderr redirected into stdout so you get errors too.
    return output.decode() # Purpose: Convert bytes -> string for printing/sending.

class NetCat:
    def __init__(self, args, buffer=None):   # Purpose: Bundle all netcat behaviors (client, listener, upload, command shell) into one object.
        self.args = args                     # Purpose: Keep CLI options accessible everywhere.
        self.buffer = buffer                 # Purpose: Hold any initial bytes to send (usually from stdin pipe).
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Purpose: Create an IPv4 TCP socket. AF_INET = IPv4 addressing (e.g. 127.0.0.1). SOCK_STREAM = TCP (reliable stream), not UDP.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # Purpose: Allow re-binding to the same port quickly after restart. SOL_SOCKET = “socket-level options”. SO_REUSEADDR = “let me reuse the address/port”. 

    def run(self):                      # Purpose: Decide if we’re acting like a server (-l) or a client.
        if self.args.listen:            # Purpose: If -l specified, we wait for inbound connections.
            self.listen()
        else:                           # Purpose: Otherwise, we connect out to a target and talk.
            self.send()


    def send(self):                                                # Purpose: Client mode: connect to target, optionally send initial data, then loop receiving output + sending user input.
        self.socket.connect((self.args.target, self.args.port))    # Purpose: Establish a TCP connection to target:port.
        if self.buffer:                                            # Purpose: If we were given initial data (piped stdin), send it once.
            self.socket.send(self.buffer)
        try:                                                       # Purpose: Keep the client interactive loop running until Ctrl+C.
            while True:
                recv_len = 1                                       # Purpose: Seed value so inner "while recv_len" runs at least once.
                response = ''                                      # Purpose: Accumulate everything the remote side sends us.
                while recv_len:                                    # Purpose: Keep receiving until remote sends less than 4096 bytes.
                    data = self.socket.recv(4096)                  # Purpose: Read up to 4096 bytes from the socket.
                    recv_len = len(data)                           # Purpose: If 0, connection closed; if <4096, likely end of burst.?????If 0 close connection?
                    response += data.decode()                      # Purpose: Convert bytes->string and append to full response.
                    if recv_len < 4096:                            # Purpose: Heuristic: if we got a “short” read, stop reading for now.
                        break
                if response:
                    print(response)
                    buffer = input('> ')
                    buffer += '\n'
                    self.socket.send(buffer.encode())
        except KeyboardInterrupt:
            print("User terminated.")
            self.socket.close()
            sys.exit()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        while True:
            client_socket, _ = self.socket.accept()
            client_thread = threading.Thread(
                target=self.handle, args=(client_socket,)
            )
            client_thread.start()

    def handle(self, client_socket):
        if self.args.execute:
            output = execute(self.args.execute)
            client_socket.send(output.encode())

        elif self.args.upload:
            file_buffer = b''
            while True:
                data = client_socket.recv(4096)
                if data:
                    file_buffer += data
                else:
                    break

            with open(self.args.upload, 'wb') as f:
                f.write(file_buffer)
            message = f'Saved file {self.args.upload}'
            client_socket.send(message.encode())

        elif self.args.command:
            cmd_buffer = b''
            while True:
                try:
                    client_socket.send(b"<BHP:#> ")
                    while b'\n' not in cmd_buffer:
                        cmd_buffer += client_socket.recv(64)
                    response = execute(cmd_buffer.decode())
                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b''
                except Exception as e:
                    print(f"Server killed {e}")
                    self.socket.close()
                    sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Netcat-like tool for network communication and command execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Example usage:
            netcat.py -t 192.168.1.108 -p 5555 -l -c #Command shell
            netcat.py -t 192.168.1.108 -p 5555 -l -u=mytest.txt #Upload to file
            netcat.py -t 192.168.1.108 -p 5555 -l -e\"cat /etc/passwd\" #Execute command
            echo 'Hello' | ./netcat.py -t 192.168.1.108 -p 135 #echo text to server port 135
            netcat.py -t 192.168.1.108 -p 5555 #Connect to server
        '''
        ),
    )

    parser.add_argument('-c', '--command', action='store_true', help='Initialize a command shell')
    parser.add_argument('-e', '--execute', help='Execute specified command upon receiving a connection')
    parser.add_argument('-l', '--listen', action='store_true', help='Listen for incoming connections')
    parser.add_argument('-p', '--port', type=int, default=5555, help='Specify the port to listen on or connect to')
    parser.add_argument('-t', '--target', default='192.168.1.203', help='Specify the target host IP')
    parser.add_argument('-u', '--upload', help='Specify the file to upload')

    args = parser.parse_args()
    
    if args.listen:
        buffer = ''
    else:
        buffer = sys.stdin.read()

    nc = NetCat(args, buffer.encode())
    nc.run()