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


def gather_missing(path_done, path_watch):
    updatelog(f'.... collect mp4 file list.... from path {path_watch}', True)
    list_watch = glob.glob(path_watch + '/*.mp4')
    nameonly_done = []
    list_missing = []


    for f in list_watch:
        nameonly_watch = os.path.basename(f)
        done_mxf = os.path.join(path_done, nameonly_watch + '.mxf__done')
        done_pxy = os.path.join(path_done, nameonly_watch + '.prox_done')
        done_cat = os.path.join(path_done, nameonly_watch + '.cata_done')
        result = os.path.isfile(done_mxf) and os.path.isfile(done_pxy) and os.path.isfile(done_cat)
        if not result:
            list_missing.append(f)
    updatelog(f'---- Missing file list ----', True)
    for m in list_missing:
        updatelog(get_name(m), True)
    updatelog(f'Number of missing file = {len(list_missing)}', True)
    return list_missing



print(gather_missing('E:/sbsint/done', 'E:/aptn_download' ))


