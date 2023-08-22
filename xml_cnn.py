
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





xfile = "E:/cnn_download/NE-003SU_IN_ TORNADOES TOUCH D_CNNA-ST1-200000000004e78d_900_0.xml"


with open(xfile, encoding='utf-8') as fp:
    soup = BeautifulSoup(fp.read(), 'html.parser')
    data = soup.storynum.text + '\n' + re.sub('<.*?>', '', soup.description.text)
    print(data)
