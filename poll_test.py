
import time, datetime, threading, psutil, os, argparse, textwrap
import subprocess, glob, socket, re
import xml.etree.ElementTree as ET
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserverVFS
from watchdog.events import PatternMatchingEventHandler
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup
from psutil import process_iter


def updatelog(txt, consoleout = False):
    pid = os.getpid()
    path_log = os.path.join(os.path.dirname(__file__), 'log', f'history_[{pid}].log')
    tm_stamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f   ")
    txt = str(txt)
    with open(path_log, "a", encoding='UTF-8') as f:
        f.write(tm_stamp + txt + "\n")
    if consoleout:
        col = os.get_terminal_size().columns
        print(" " * (int(col) - 1), end='\r')     # clear single line
        print(tm_stamp + txt)


def get_name(f):
    head, tail = os.path.split(f)
    return tail


def get_extension(f):           # return .mp4  .txt   .avi ...
    name, extension = os.path.splitext(f)
    return extension

class defaultobserver:
    def __init__(self):
        patterns = ["*"]
        ignore_patterns = None
        ignore_directories = True
        case_sensitive = True
        self.event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        self.event_handler.on_created = self.on_created
        self.event_handler.on_deleted = self.on_deleted
        self.event_handler.on_modified = self.on_modified
        self.event_handler.on_moved = self.on_moved

    def start(self, path):
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def on_created(self, event):
        updatelog(f"-- created!    {event.src_path}", True)
        #on_created(event)

    def on_deleted(self, event):
        updatelog(f"-- deleted!   {event.src_path}", True)
        #on_deleted(event)
        

    def on_modified(self, event):
        updatelog(f"-- modifed !  {event.src_path}", True)
        #on_modified(event)

    def on_moved(self, event):
        updatelog(f"-- moved !    {event.src_path} to {event.dest_path}", True)    
        #on_moved(event)
    

class pollobservervfs:

    def __init__(self):
        patterns = ["*"]
        ignore_patterns = None
        ignore_directories = True
        case_sensitive = True
        self.event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        self.event_handler.on_created = self.on_created
        self.event_handler.on_deleted = self.on_deleted
        self.event_handler.on_modified = self.on_modified
        self.event_handler.on_moved = self.on_moved

    def start(self, path):
        self.observer = PollingObserverVFS(stat=os.stat, listdir=os.listdir, polling_interval=2)
        self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def on_created(self, event):
        updatelog(f"-- created!    {event.src_path}", True)

    def on_deleted(self, event):
        updatelog(f"-- deleted!   {event.src_path}", True)

    def on_modified(self, event):
        updatelog(f"-- modifed !  {event.src_path}", True)
        do_analysis(event.src_path)
        
    def on_moved(self, event):
        updatelog(f"-- moved !    {event.src_path} to {event.dest_path}", True)
        do_analysis(event.dest_path)

class probe:
    binary = "ffprobe.exe"
    result = ""

    def analysis(self, infile):
        #p = subprocess.run(f'{self.binary} -show_streams "{infile}"', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p = subprocess.run(f'{self.binary} -show_format "{infile}"', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.result = p.stdout.decode()
        return self.result

    def get_duration(self):
        eachline = self.result.split("\n")
        duration = 0
        for line in eachline:
            if line.startswith("duration="):
                duration = line[9:]
        return float(duration)

def do_analysis(f):
    if not (get_extension(f).lower() == ".mp4"):    # skip non mp4 files.
        return
    if get_name(f).startswith("WH16x9"):        # skip mp4 for CNN agent
        return
    global pb
    tm_start = time.time()
    loop = True
    while loop:
        if ((time.time() - tm_start) > 1):
            updatelog("Error getting media duration...")
            break
        pb.analysis(f)
        d = pb.get_duration()
        if not d:
            time.sleep(0.1)
        else:
            loop = False
    updatelog(d, True)

updatelog("Start watch with poll vfs observer", True)
po = pollobservervfs()
po.start('z:/')

pb = probe()

while True:
    print(int(time.time()), end="  ")
    print(threading.enumerate())
    time.sleep(1)