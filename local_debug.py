import gi, threading, socket, sys, time, os, signal, datetime

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


def updatelog(txt, consoleout = False):
    pid = os.getpid()
    path_log = os.path.join(os.getcwd(), 'log', f'watchdog_[{pid}].log')
    tm_stamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f   ")
    txt = str(txt)
    with open(path_log, "a", encoding='UTF-8') as f:
        f.write(tm_stamp + txt + "\n")
    if consoleout:
        col = os.get_terminal_size().columns
        print(" " * (int(col) - 1), end='\r')     # clear single line
        print(tm_stamp + txt)
    if (os.stat(path_log).st_size > 3000000):
        path_archive = os.path.splitext(path_log)[0]
        path_archive += '_' + datetime.datetime.now().strftime("_%m%d%Y-%H%M%S.log")
        os.rename(path_log, path_archive)


   
def button1(this):
    global w1
    try:
        pid = int(w1.status_current["pid"])
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        print(f'Error... terminating pid {pid}  ... {e}')
        return




def button2(this):
    global w2
    try:
        pid = int(w2.status_current["pid"])
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        print(f'Error... terminating pid {pid}  ... {e}')
        return

    


def button3(this):
    global w3
    try:
        pid = int(w3.status_current["pid"])
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        print(f'Error... terminating pid {pid}  ... {e}')
        return




def update_gui_info():
    global u1, u2, u3, win, w1, w2, w3
    win.entry11.set_text(u1.data)
    win.entry12.set_text(u2.data)
    win.entry13.set_text(u3.data)

    w1.parser(u1.data)
    w2.parser(u2.data)
    w3.parser(u3.data)
    
    w1.run()
    w2.run()
    w3.run()
    
    win.update_status("dead score = " \
            + str(w1.score_heartbeat) + "_" + str(w2.score_heartbeat) + "_" + str(w3.score_heartbeat) \
            + " / " + str(w1.score_lastjob) + " _ " + str(w2.score_lastjob)  + " _ " + str(w3.score_lastjob))
    

class udp_recv:

    data = 'Initial data'
    
    def setup(self, nb_port):
        try :
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print('Socket created')
        except Exception as msg :
            print('Failed to create socket. Error Code : ' + str(msg))

        # Bind socket to local host and port
        try:
            self.s.bind(("127.0.0.1", nb_port))
        except Exception as msg:
            print('Bind failed. Error Code : ' + str(msg))
            sys.exit()
            
        print(f'Socket bind complete  {nb_port}')
        
        threading.Thread(target=self.run, daemon=True).start()
        
    def run(self):
        while True:
            d = self.s.recvfrom(8096)
            data = d[0]
            addr = d[1]
            reply = data.decode('utf-8')
            if len(reply):
                self.data = reply

    def get_data(self):
        return self.data


class watchdog:
    score_heartbeat = 0
    score_lastjob = 0
    
    
    def __init__(self, name):
        self.name = name
        self.score_heartbeat = 0
        self.status_current = {"age" : "0", "last_job" : "--", "pid" : -1, "len_enc-wai-upd-xfer" : "[0, 0, 0, 0]"}
        self.status_old =  {"age" : "0", "last_job" : "--", "pid" : -1, "len_enc-wai-upd-xfer" : "[0, 0, 0, 0]"}
        
    def parser(self, text):
        if not text.startswith("age**"):
            return
        eachline = text.split("\n")
        for each in eachline:
            array = each.split("**")
            if len(array) >= 2:
                self.status_current[array[0]] = array[1]


    def run(self):
        if self.status_current["age"] == self.status_old["age"]:
            self.score_heartbeat += 1
        else:
            self.score_heartbeat = 0

        if self.status_current["last_job"] == self.status_old["last_job"]:
            self.score_lastjob += 1
        else:
            updatelog(f'Found new score_lastjob = {self.score_lastjob} / {self.name}', True)
            self.score_lastjob = 0
            
            
        for each in self.status_current:
            self.status_old[each] = self.status_current[each]

class gui(Gtk.Window):
    def __init__(self):
        super().__init__(title="LOCAL DEBUG")
        #self.set_border_width(10)
        self.set_default_size(100, 50)
        self.set_hexpand(False)
        self.timeout_id = None
        button1 = Gtk.Button(label="Button 1")
        button2 = Gtk.Button(label="Button 2")
        button3 = Gtk.Button(label="Button 3")
        
        
        button1.connect("clicked", self.on_button1)
        button2.connect("clicked", self.on_button2)
        button3.connect("clicked", self.on_button3)
        
        
        self.entry1 = Gtk.Entry()
        self.entry1.set_text("4002")
        self.entry2 = Gtk.Entry()
        self.entry2.set_text("7892")
        self.entry3 = Gtk.Entry()
        self.entry3.set_text("21002")
        
        #self.entry11 = Gtk.TextView()
        #self.entry12 = Gtk.TextView()
        #self.entry13 = Gtk.TextView()
        
        self.entry11 = Gtk.Label()
        self.entry12 = Gtk.Label()
        self.entry13 = Gtk.Label()
        self.entry11.set_selectable(True)
        self.entry12.set_selectable(True)
        self.entry13.set_selectable(True)
        
        self.entry99 = Gtk.Label()
        self.entry99.set_selectable(True)
               
               
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        
        grid.attach(self.entry1, 0, 0, 1, 1)
        grid.attach(button1, 1, 0, 1, 1)
        grid.attach(self.entry2, 2, 0, 1, 1)
        grid.attach(button2, 3, 0, 1, 1)
        grid.attach(self.entry3, 4, 0, 1, 1)
        grid.attach(button3, 5, 0, 1, 1)
        
        grid.attach(self.entry11, 0, 2, 10, 5)
        grid.attach(self.entry12, 0, 7, 10, 5)
        grid.attach(self.entry13, 0, 13, 10, 5)
        grid.attach(self.entry99, 0, 18, 10, 3)
        
        self.add(grid)

        self.entry11.set_line_wrap(True)
        self.entry12.set_line_wrap(True)
        self.entry13.set_line_wrap(True)
        self.entry99.set_line_wrap(True)
        
        self.entry11.set_xalign(0.1)
        self.entry12.set_xalign(0.1)
        self.entry13.set_xalign(0.1)

        
        self.entry99.set_text("Status bar")
        
        #self.entry11.set_wrap_mode(True)
        #self.entry12.set_wrap_mode(True)
        #self.entry13.set_wrap_mode(True)

    def timerstart(self):
        GLib.timeout_add(200, self.showlabel)
        
    def showlabel(self):
        update_gui_info()
        return True
    
    def update_status(self, text):
        self.entry99.set_text(text)


    def on_button1(self, button):
        button1(self)
        
        
    def on_button2(self, button):
        button2(self)        

    def on_button3(self, button):
        button3(self)

updatelog("Application started....", True)

win = gui()
win.connect("destroy", Gtk.main_quit)
win.show_all()
win.timerstart()

u1 = udp_recv()
u2 = udp_recv()
u3 = udp_recv()

w1 = watchdog("reuter")
w2 = watchdog("aptn")
w3 = watchdog("cnn")

u1.setup(int(win.entry1.get_text()))
u2.setup(int(win.entry2.get_text()))
u3.setup(int(win.entry3.get_text()))
    
updatelog("Begin GUI loop ....", True)
Gtk.main()