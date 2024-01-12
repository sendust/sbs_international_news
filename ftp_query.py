import time, os, ftplib, datetime, threading, socketio, json

# update ftp list reply string. 2023/12/23


# host = "10.40.24.121"  # Old ftp (before 2023/12/230
host = "10.40.28.101"   # New 2023/23/23
username = "wire"
password = "ndsnds00!"



def updatelog(txt, consoleout = False):
    pid = os.getpid()
    path_log = os.path.join(os.getcwd(), 'log', f'ftp_[{pid}].log')
    tm_stamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f   ")
    
    try:
        if (os.stat(path_log).st_size > 3000000):
            path_archive = os.path.splitext(path_log)[0]
            path_archive += '_' + datetime.datetime.now().strftime("_%m%d%Y-%H%M%S.log")
            os.rename(path_log, path_archive)
    except:
        print("Log with file....")
        
    txt = str(txt)
    with open(path_log, "a", encoding='UTF-8') as f:
        f.write(tm_stamp + txt + "\n")
    if consoleout:
        col = os.get_terminal_size().columns
        print(" " * (int(col) - 1), end='\r')     # clear single line
        print(tm_stamp + txt)






class transfer:

    status = 'idle'
    tm_start = 0
    infile = ''

    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.status = 'idle'
        self.dict_callback = {"send" : self.send, "sendlist" : self.sendlist, "mkdir" : self.mkdir}

    def schedule(self, callback='', argument1='', argument2=''):   
        if not callback:
            return
        self.callback = callback
        self.arguments = [argument1, argument2]
        try:
            if type(argument1) == list:
                self.infile = argument1[0]
            else:
                self.infile = argument1
        except Exception as e:
            updatelog(f'Error while schedule transfer ... {e}', True)
            self.set_status("finish")
            return
        self.set_status("ready")
        #print(f'Schedule callback.. {callback}')
    
    def do_schedule(self):
        fn_cb = self.dict_callback[self.callback]
        #print(f'do schedulled callback.. {fn_cb}')
        self.tm_start = time.time()
        self.set_status("running")
        fn_cb(self.arguments[0], self.arguments[1])
        self.set_status("finish")
        
    def remote_list(self, rpath="."):
        result = []
        try:
            f = ftplib.FTP(host = self.host, user = self.username, passwd = self.password, timeout = 30, encoding = 'utf-8')
            result = f.nlst(rpath)
            f.quit()
        except Exception as e:
            updatelog(f'Error while retrieve remote path [{rpath}] list files...  [{e}]', True)
        return result
    
    
    def mkdir(self, pathname, *dummy_arg):
        updatelog(f'make ftp remote path {pathname}', True)
        try:
            f = ftplib.FTP(host = self.host, user = self.username, passwd = self.password, timeout = 4, encoding = 'utf-8')
            f.mkd('./' + pathname)
            f.quit()
        except Exception as e:
            updatelog(f'Error while create ftp object or make dir..   {pathname}  [{e}]', True)

    
    def send(self, filepath, path_remote = ''):
        tm_start = time.time()
        try:
            f = ftplib.FTP(host = self.host, user = self.username, passwd = self.password, timeout = 4, encoding = 'utf-8')
            #print("ftp object created..")
            f.set_pasv(True)
            updatelog(f'Start transfer... {filepath} / path is {path_remote}', True)
            with open(filepath, "rb") as fp:
                remotecmd = "STOR " + './' + path_remote + '/' + os.path.basename(filepath)
                f.storbinary(cmd=remotecmd, fp=fp, blocksize=1024*1024, callback=self.showtransfer)
            f.quit()
            tm_duration = time.time() - tm_start + 0.00000000001
            size_file_MB = os.stat(filepath).st_size / (1024*1024)  # Ger file size in MB
            updatelog(f'Finish transfer... {filepath}  \n transfer speed is {size_file_MB / tm_duration} MB/sec,  remote path is {path_remote}', True)
        except Exception as e:
            updatelog(f'Error while create ftp object.. or send single file {e}', True)

    
    def sendlist(self, list_filepath, path_remote = ''):
        try:
            f = ftplib.FTP(host = self.host, user = self.username, passwd = self.password, timeout = 4, encoding = 'utf-8')
        except Exception as e:
            print("Error while create ftp object..")
        updatelog(f'Start transfer (list mode) ', True)
        for each in list_filepath:
            try:
                with open(each, "rb") as fp:
                    f.storbinary(cmd="STOR " + './' + path_remote + '/' + os.path.basename(each), fp=fp, blocksize=1024*1024, callback=self.showtransfer)
                    updatelog(os.path.basename(each), True)
            except Exception as e:
                updatelog(f'Error while transfer file list..  {e}', True)
        try:
            f.quit()
        except Exception as e:
            updatelog(f'Error while close transfer (list mode)..  {e}', True)
        #print("Finish Transfer")
        updatelog(f'Finish transfer (list mode)', True)
                        
    def showtransfer(self, this):
        #print("!", end='', flush=True)
        increase_queue_cycle()
        pass


    def set_status(self, st):
        self.status = st
        print(f'status changed... {st}')



class remotelist:
    def __init__(self):
        self.lists = {}
        self.lists["incominglist"] = []
        self.lists["successlist"] = []
        self.lists["errorlist"] = []

    def update_list(self, key, value):
        if len(value):
            self.lists[key] = value
            print(f'list update success.. {key}')
        else:
            print(f'list update fail or list is empty.. {key}')
            
    def get_list(self, key):
        return self.lists[key]


class get_ftplist:
    def __init__(self):
        self.ftplist = remotelist()
        self.ftp = transfer(host, username, password)    
        self.keep_timer = True
    
    def run(self):          # Update 2023/12/23
        tm_start = time.time()
        #self.ftplist.update_list("incominglist", self.ftp.remote_list('/incoming'))
        #self.ftplist.update_list("successlist", self.ftp.remote_list('/success'))
        #self.ftplist.update_list("errorlist", self.ftp.remote_list('/fail'))
        
        self.ftplist.update_list("incominglist", [f"/incoming/{x}" for x in self.ftp.remote_list('/incoming')])
        self.ftplist.update_list("successlist", [f"/success/{x}" for x in self.ftp.remote_list('/success')])
        self.ftplist.update_list("errorlist", [f"/fail/{x}" for x in self.ftp.remote_list('/fail')])
        
        tm_cost = time.time() - tm_start

        updatelog(f'length = {len(self.ftplist.get_list("incominglist"))} / {len(self.ftplist.get_list("successlist"))} / {len(self.ftplist.get_list("errorlist"))}', True)
        updatelog(f'query takes {tm_cost} seconds...', True)
        if self.keep_timer:
            self.tmr = threading.Timer(120, self.run)
            self.tmr.start()
          
    def halt(self):
        self.keep_timer = False
        self.tmr.cancel()




class sioclient():
    def __init__(self):
        print('Create python socket.io object')
        self.sio = socketio.Client(reconnection = True, reconnection_delay=0.5, request_timeout = 0.5)
        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("msg_gui", self.on_msg_gui)
        
        
    def on_connect(self):
        print('connection established')
        
    def on_msg_gui(self, data):
        #print('gui message received with ', data)
        try:
            threading.Thread(target=decode_protocol_sio, daemon=True, name="sio_reply", args=(data,)).start()
            #decode_protocol_sio(data)
        except Exception as e:
            print(e)
       
        
    def on_disconnect(self):
        print('disconnected from server')
        
    def connect(self, address):
        self.address = address

        result = False
        try:
            self.sio.connect(address)
            result = True
        except Exception as e:
            print(e)
            result = False
        finally:
            return result

    def isconnected(self):
        return self.sio.connected

    def disconnect(self):
        try:
            self.sio.disconnect()
        except Exception as e:
            print(e)

    def send(self, name_event, data):
        try:
            self.sio.emit(name_event, data)
        except Exception as e:
            print(e)
    


class webgui:

    def start(self):
        self.sio = sioclient()
        if (not self.sio.connect('http://localhost:50080')):
            print("Cannot establish socketio... check server..")
        
    def send(self, msg):
        if self.sio.isconnected():
            self.sio.send('msg_engine', msg)

    def send_reply(self, msg):
        if self.sio.isconnected():
            self.sio.send('reply_engine', msg)
        


def send_reply_socketio(id_client, largedata, finishtag = ''):
    global gui
    text_tosend = '<start_transfer>' + largedata + '<finish_transfer>' + finishtag
    json_tosend = {"receiverId" : id_client, "protocol" : "reply", "engine" : "reuter", "data" : text_tosend}
    gui.send_reply(json_tosend)



def decode_protocol_sio(data):
    global job
    try:
        id_client = data["receiverId"]
    except:
        id_client = "aabbccddeeffgghhiijj"

    if ((data["protocol"] == "gui") and (data["engine"] == "reuter")):
        updatelog("reply sio request....")
        updatelog(data, True)
        req_data = data["data"]["cmd"]
 

        if (req_data.startswith("<get_incomelist>")):
            get_list = job.ftplist.get_list("incominglist")
            largedata = ""
            for each in get_list:
                largedata += each + "\n"
            updatelog(f'reply ftp get_incomelist\n ftp incomelist is (shows head part only)', True)
            updatelog(largedata[:160], True)
            send_reply_socketio(id_client, largedata, '<ftpincomelist>')       
        

        elif (req_data.startswith("<get_successlist>")):
            get_list = job.ftplist.get_list("successlist")
            largedata = ""
            for each in get_list:
                largedata += each + "\n"
            updatelog(f'reply ftp get_successlist\n ftp successlist is (shows head part only)', True)
            updatelog(largedata[:160], True)
            send_reply_socketio(id_client, largedata, '<ftpsuccesslist>')       
        
        elif (req_data.startswith("<get_errorlist>")):
            get_list = job.ftplist.get_list("errorlist")
            largedata = ""
            for each in get_list:
                largedata += each + "\n"
            updatelog(f'reply ftp get_errorlist\n ftp errorlist is (shows head part only)', True)
            updatelog(largedata[:160], True)
            send_reply_socketio(id_client, largedata, '<ftperrorlist>')       


            
tm_startup = time.time()            
job = get_ftplist()
job.run()
gui = webgui()
gui.start()


try:
    while True:
        print(f'age = {format("%.1f" % (time.time() - tm_startup))}', end="\r")
        time.sleep(0.5)
        
except KeyboardInterrupt:
    job.halt()
