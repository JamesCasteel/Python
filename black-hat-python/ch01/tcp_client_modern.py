"""Modern TCP client — cleaner, safer, and reusable."""

import socket

# creates the function
def tcp_client(host: str, port: int, message: str):
    """Connect to a TCP server, send a message, and return the response"""

    # create a TCP connection
    with socket.create_connection((host, port)) as sock:
    
        # send the message
        sock.sendall(message.encode())

        # receive data back
        response = sock.recv(4096)

        # decode the bytes
        response_text = response.decode(errors="replace")

        #return the text
        return response_text
    
# If I'm running this file directly (not importing it),
# run the following example:
if __name__ == "__main__":
    reply = tcp_client("www.google.com", 80, "GET / HTTP/1.1\r\nHost: google.com\r\n\r\n")
    print(reply)