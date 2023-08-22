import socket
import sys

if len(sys.argv)<2:
    print("Usage.... tcp_send.py  address port str_send_data")
    sys.exit(1)


HOST, PORT = str(sys.argv[1]), int(sys.argv[2])
data = sys.argv[3]

# Create a socket (SOCK_STREAM means a TCP socket)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    # Connect to server and send data
    sock.connect((HOST, PORT))
    sock.sendall(bytes(data + "\n", "utf-8"))

    # Receive data from the server and shut down
    received = str(sock.recv(1024), "utf-8")

print("Sent:     {}".format(data))
print("Received: {}".format(received))