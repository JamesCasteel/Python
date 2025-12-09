import socket
import threading

IP = "0.0.0.0"
PORT = 9998

def main():
    # create a socket object
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind the socket to a public host, and a port
    server.bind((IP, PORT))

    # become a server socket
    server.listen(20)
    print(f"[*] Listening on {IP}:{PORT}")

    while True:
        # establish a connection
        client_socket, addr = server.accept()
        print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")

        # handle client connection in a new thread
        client_handler = threading.Thread(
            target=handle_client,
            args=(client_socket,)
            )
        client_handler.start()
        
def handle_client(client_socket):
    with client_socket as sock:
        # receive data from the client
        request = sock.recv(4096)
        print(f"[*] Received: {request.decode("utf-8")}")
        # send back a response
        sock.send(b"ACK")

if __name__ == "__main__":
    main()