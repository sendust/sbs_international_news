
import socket, threading, datetime, os, sys, time
from psutil import process_iter



def updatelog(txt, consoleout = False):
    tm_stamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f   ")
    txt = str(txt)
    pid = os.getpid()
    with open(f'temp_[{pid}].log', "a", encoding='UTF-8') as f:
        f.write(tm_stamp + txt + "\n")
    if consoleout:
        col = os.get_terminal_size().columns
        print(" " * (int(col) - 1), end='\r')     # clear single line
        print(tm_stamp + txt)





class tcp_svr_thread():
    thread_svr = ""
    loop_accept = True
    running = True
    
    def __init__(self, address="0.0.0.0", port=5250):
        updatelog(f'Create tcp class with port {port}', True)
        #threading.Thread.__init__(self)
        self.runnig = True
        try:      # Check another Engine instance
            updatelog("Check another engine is running..........", True)
            for proc in process_iter():
                for conns in proc.connections(kind = 'inet'):
                    if conns.laddr.port == port:
                        updatelog("Another engine instance found  {0}... exit script.".format(proc), True)
                        sys.exit()


            # create an INET, STREAMing socket
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # bind the socket to a public host, and a well-known port
            result1 = self.serversocket.bind((address, port))
            updatelog("tcp server bind result is {0}".format(result1), True) 
            # become a server socket
            result2 = self.serversocket.listen(1)   # 5 ?
            updatelog("tcp server listen result is {0}".format(result2), True)

        except Exception as err:
            updatelog(err)
            updatelog("Error creating socket... /// {0}".format(err))
            sys.exit()
        
        self.thread_svr = threading.Thread(target=self.run_server, daemon=False)
        
    def start(self):
        self.thread_svr.start()
        
    def stop(self):
        updatelog("tcp server stop....  Try to join..", True)
        self.loop_accept = False
        self.serversocket.close()
        self.thread_svr.join()
        
    def run_server(self):
        updatelog("<<<<Begin TCP acception>>>>>", True)
        
        while self.running:
            try:
                clientsocket, address = self.serversocket.accept()
                self.reply_client(clientsocket)
            except self.serversocket.timeout:
                pass
               
        
    def reply_client(self, clientsocket):
        try:
            data = clientsocket.recv(1024).decode()
            updatelog("Message from client: {}   ".format(data), True)
            clientsocket.send(("tcp MSG // " + data + " ").encode())
            #do_tcp_command(data)
        except:
            updatelog("Error while TCP receive or send", True)



svr = tcp_svr_thread("127.0.0.1", 5555)
svr.start()

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    svr.stop()
