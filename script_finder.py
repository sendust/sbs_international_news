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


class scriptfinder:
    watchpath = ""
    tree = ""
    root = ""
    file_script = ['']
    text_script = ""
    mode = "reuter"
    
    
    def __init__(self, watchpath, mode = "reuter"):      # init with watch folder
        self.watchpath = watchpath
        self.mode = mode

    def search_script_file(self, infile):      # in file is mp4 (video media)
        self.file_script = ['']
        dict_search_script_file = {'reuter': self.search_script_file_reuter, 'aptn' : self.search_script_file_aptn, 'cnn' : self.search_script_file_cnn}
        updatelog(f'script finder mode is {self.mode}', True)
        scfiles = dict_search_script_file[self.mode](infile)
        for scfile in scfiles:
            updatelog(f'Script search result is {scfile}', True)
        return scfiles
        
    def get_script_data(self, infile = ''):   # in file is xml
        dict_get_script_data = {'reuter': self.get_script_data_reuter, 'aptn' : self.get_script_data_aptn, 'cnn' : self.get_script_data_cnn}
        try:
            updatelog(f'Script head ----\n{dict_get_script_data[self.mode](infile)[:100]}', True)
        except Exception as e:
            updatelog(f'Error acquiring script data {e}')
        return dict_get_script_data[self.mode](infile)



    def search_script_file_reuter(self, infile):   # infile is mp4
        #key = get_name(infile).split('_')[-1][5:-4] + '.XML'
        key = get_name(infile).split('_')[5][5:-4] + '.XML'
        sclist = glob.glob(os.path.join(self.watchpath, '*' + key))
        sclist.sort()
        if sclist:
            self.file_script = sclist   # return script list
            return self.file_script
        else:
            return self.file_script
    
    def get_script_data_reuter(self, infile = ''):   # in file is xml
        if not infile:
            infile = self.file_script
        try:
            with open(infile, encoding='utf-8') as fp:
                soup = BeautifulSoup(fp, 'html.parser', from_encoding='utf-8')
                self.text_script = soup.body.text
        except:
            self.text_script = "Error finding script data......"
        return self.text_script
        


    def search_script_file_aptn(self, infile):   # infile is mp4
        id = get_name(infile).split('_')[0]
        sclist = glob.glob(os.path.join(self.watchpath, id + '*_script.xml'))
        sclist.sort()
        if sclist:
            return sclist  # return script list
        else:
            return self.file_script


    def get_script_data_aptn(self, infile = ''):   # in file is xml
        if not infile:
            infile = self.file_script
        try:
            with open(infile, encoding='utf-8') as fp:
                soup = BeautifulSoup(fp.read(), 'html.parser')
                self.text_script = soup.body.text
        except:
            self.text_script = "Error finding script data......"
        return self.text_script


    def search_script_file_cnn(self, infile):   # infile is mp4
        id = get_name(infile).split('_')[1]     # Get news ID  // caution !! do not put cnn proxy mp4 
        sclist = glob.glob(os.path.join(self.watchpath, id + '*.xml'))
        sclist.sort()
        if sclist:
            return sclist  # return script list
        else:
            return self.file_script


    def get_script_data_cnn(self, infile = ''):   # in file is xml
        if not infile:
            infile = self.file_script
        try:
            with open(infile, encoding='utf-8') as fp:
                soup = BeautifulSoup(fp.read(), 'html.parser')
                self.text_script = soup.storynum.text + '\n' + re.sub('<.*?>', '', soup.description.text)
        except:
            self.text_script = "Error finding script data......"
        return self.text_script


mp4list = glob.glob('D:/agent_REUTERS/*.mp4')
#print(mp4list)
sf = scriptfinder('D:/agent_REUTERS', 'reuter')
for f in mp4list:
    l = sf.search_script_file(f)
    print(f)
    print(len(l))
    #print(sf.get_script_data(l[-1][:100]))
    print('*'*100)
