import time
import os
from watchdog.observers.polling import PollingObserverVFS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.events import PatternMatchingEventHandler


class defaultobserver:
    def __init__(self):
        patterns = ["*"]
        ignore_patterns = None
        ignore_directories = False
        case_sensitive = True
        self.event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        self.event_handler.on_created = self.on_created
        self.event_handler.on_deleted = self.on_deleted
        #self.event_handler.on_modified = self.on_modified
        self.event_handler.on_moved = self.on_moved

    def start(self, path):
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def on_created(self, event):
        print(f"-- created!    {event.src_path}")

    def on_deleted(self, event):
        print(f"-- deleted!   {event.src_path}")

    def on_modified(self, event):
        print(f"-- modifed !  {event.src_path}")

    def on_moved(self, event):
        print(f"-- moved !    {event.src_path} to {event.dest_path}")    
    


class pollobservervfs:

    def __init__(self):
        patterns = ["*"]
        ignore_patterns = None
        ignore_directories = False
        case_sensitive = True
        self.event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        self.event_handler.on_created = self.on_created
        self.event_handler.on_deleted = self.on_deleted
        #self.event_handler.on_modified = self.on_modified
        self.event_handler.on_moved = self.on_moved

    def start(self, path):
        self.observer = PollingObserverVFS(stat=os.stat, listdir=os.listdir, polling_interval=2)
        self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def on_created(self, event):
        print(f"-- created!    {event.src_path}")

    def on_deleted(self, event):
        print(f"-- deleted!   {event.src_path}")

    def on_modified(self, event):
        print(f"-- modifed !  {event.src_path}")

    def on_moved(self, event):
        print(f"-- moved !    {event.src_path} to {event.dest_path}")
        


        
        
poll = defaultobserver()
poll.start('c:\\temp')


try: 
    while True: 
        # Set the thread sleep time 
        time.sleep(60) 
except KeyboardInterrupt: 
    poll.stop()