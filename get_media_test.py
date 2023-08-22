
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



def get_name(f):
    head, tail = os.path.split(f)
    return tail
    
    
def get_media_list_ext(path, filter = '*'):
    medialist = glob.glob(os.path.join(path, filter))
    medialist_new = [x for x in medialist if not get_name(x).startswith('WH16x9')]  # add cnn exception
    medialist_new.sort(key=os.path.getmtime, reverse=True)
    new_list = [each + "|" + time.strftime('%Y%m%d %H%M%S', time.localtime(os.path.getmtime(each))) for each in medialist_new]
    result = ""
    for line in new_list:
        result += line + '\n'
    return result


print(get_media_list_ext('z:/', '*.mp4'))