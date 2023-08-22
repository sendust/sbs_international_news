
import socket
import sys

HOST = "127.0.0.1"    # Symbolic name meaning all available interfaces
PORT = 34410    # Arbitrary non-privileged port

if sys.argv[1]:
    PORT = int(sys.argv[1])

print(f'listen port is {PORT}')

# Datagram (udp) socket
try :
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('Socket created')
except Exception as msg :
    print('Failed to create socket. Error Code : ' + str(msg))
    sys.exit()


# Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except Exception as msg:
    print('Bind failed. Error Code : ' + str(msg))
    sys.exit()
    
print('Socket bind complete')

#now keep talking with the client
while 1:
    # receive data from client (data, addr)
    d = s.recvfrom(1024)
    data = d[0]
    addr = d[1]
    
    #if not data: 
    #    break
    
    reply = data.decode('utf-8')
    
    #print('Message ---------------   [%d]' % (len(reply)))
    print(reply)
    
s.close()