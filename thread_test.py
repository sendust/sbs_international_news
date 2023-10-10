import threading, time, os, subprocess


class threadtest:
    def start(self):
            
        newenv = os.environ.copy()
        newenv["FFREPORT"] = f'file=FFMPEG_AUDIO_{self.nameonly}.LOG:level=32'
        self.tm_start = time.time()
        
        
        
        self.t = threading.Thread(target=self.do_something, daemon=False, name="AUDIOENC")
        self.t.start()

        
    def do_something(self):
        time.sleep(1)
        print("Finish threading..")
        
        
t = threadtest()
t.start()