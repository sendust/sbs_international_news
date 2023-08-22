import time, datetime, threading, psutil, os, argparse, textwrap, signal, random, ftplib
import subprocess, glob, socket, re, copy
import xml.etree.ElementTree as ET
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserverVFS
from watchdog.events import PatternMatchingEventHandler
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup
from psutil import process_iter

#
#   SBS international news processing engine.
#   Code managed by sendust (2023)
#
#   Job triggering event : 
#                  APTN = creation    /    REUTER, CNN = modification
#
#   2023/4/26   logging with utf-8 character. 
#               Encoder have 5 state (idle, setfile, ready, running, finish)
#               Check output file size
#               Regulate number of concurrent encoder
#               Max Encoder age is duration dependent
#               Report Encoding done as file list ("./done" folder)
#               shows encoding missing file lists at start up (gather done list)
#   2023/4/27   Improve exception while ffmpeg pipe reading
#               Close tqdm progressbar if encoder is terminated
#   2023/4/28   Engine status report with UDP message
#               Add scriptfinder class (reuter, aptn)
#               Improve updatelog for stdout logging message (erase line & write line)
#               Two kind of Watchfolder class (OS API, simple polling)
#               Script data is write in mxf_done file
#               TCP Server for user command acception
#   2023/5/3    Change client protocol (tcp req tcp answer -> tcp req, udp answer)
#               Change script finder result (return script full list)
#               Add send_largetext_udp_ahk function
#   2023/5/4    Improve client reply protocol (file list + time stamp)
#   2023/5/8    Add CNN capability in scriptfinder
#   2023/5/9    Improve gather_missing function (Check all brother files)
#   2023/5/10   Add CNN proxy mp4 exception
#               Add polling argument option as a watchdog method (usage : --polling True)
#               Improve media probing. (Skip encoding if duration is 0)
#   2023/5/11   Add full_path_set class, add tqdm bar during udp response            
#   2023/5/12   Add make_xml_job
#   2023/5/14   Change waiter class trigerring position (do encoding -> encoder startMXF)
#               Check infile existence in job queue before appending job queue
#   2023/5/18   Gracefully shutdown (clear queue, terminate subprocess, thread)
#   2023/5/22   do story update xml job if new xml scripts are appear.
#   2023/5/26   Add tcp shutdown, tcp manual encoding
#   2023/5/30   Improve function search_media_files_reuter
#               Improve delete old class
#               Improve script find function (reuters... numbered ID)
#   2023/6/13   Add transfer class (FTP transfer)
#   2023/6/19   implement transfer queue, add, start, finish, remove job
#   2023/6/28   Log FTP transfer speed.
#   2023/6/29   Add command - <get_ftplist>, change send large udp send sleep time (shorter)
#   2023/7/25   Improve catalog image time stamp numbering..
#


def updatelog(txt, consoleout = False):
    pid = os.getpid()
    path_log = os.path.join(os.getcwd(), 'log', f'history_[{pid}].log')
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


class TqdmUpTo(tqdm):
    """Provides `update_to(n)` which uses `tqdm.update(delta_n)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tsize  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            self.total = tsize
        return self.update(b * bsize - self.n)  # also sets self.n = b * bsize


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




class queue:
    list_process = []
    list_xml = []
    list_update = []
    list_transfer = []
    tm_last_print = 0
    tm_last_gather = 0
    tm_startup = 0
    n_running = 0
    n_ready = 0
    list_cycle = ["[-     ]  ", "[ -    ]  ", "[  -   ]  ", "[   -  ]  ", "[    - ]  ", "[     -]  "]
    
    
    def __init__(self):
        self.tm_startup = time.time()
        self.count_cycle = 0
        self.progress_cycle = "[      ]  "

    def cycle_character(self):
        self.count_cycle += 1
        self.progress_cycle = self.list_cycle[self.count_cycle % len(self.list_cycle)]

    def run_transfer(self):                 # queue management for transfer job.

        if not len(self.list_transfer):
            return
            
        n_transfer = 0
        
        for each in self.list_transfer:     # delete finished job & count running job
            if each.status == "finish":
                self.list_transfer.remove(each)
                updatelog(f'Remove [finished] transfer job {each.infile}', True)
            elif each.status == "running":
                n_transfer += 1
        
        for each in self.list_transfer:     # Execute scheduled job.
            if (n_transfer < 1) and (each.status == "ready"):
                n_transfer += 1
                updatelog(f'Found [ready] transfer job and start new thread... {each.infile}', True)
                threading.Thread(target=each.do_schedule, daemon=True, name="transfer").start()

        

    def run(self):                          # queue management for run encoder, waiter ...
        if len(self.list_xml):
            for x in self.list_xml:
                if not x.continue_waiter:
                    self.list_xml.remove(x)
        
        if len(self.list_update):
            for u in self.list_update:
                if ((time.time() - u[0]) > 30):
                    do_story_update(u)
                    self.list_update.remove(u)
        
        
        if not self.list_process :  # There is no active encoder (list is null)
            show_tick_line(self)
            return
        n_running = 0    
        n_ready = 0
        for job in self.list_process:           # count running encoder, terminate aged encoder
            if (job.status == "running"):
                n_running += 1
                if (job.tm_elapsed > 1):        # Show progresbar with x second delay
                    job.progressbar.update_to(int(job.out_time_ms))
                if (job.tm_elapsed >= job.tm_maxage):
                    updatelog(f'Terminate encoder by timeout.. {job.tm_maxage} / pid = {job.pid}', True)
                    if job.pid:
                        try:
                            psutil.Process(job.pid).terminate()
                        except:
                            updatelog(f'Error terminating process.. pid = {job.pid}', True) 
            
            elif (job.status == "ready"):       # count ready encoder
                n_ready += 1


        for job in self.list_process:           # remove finished job
            if (job.status == "finish"):
                updatelog(f'Remove status [finish] job .......  {job.encodertype} / {job.file_in}  ', True)
                self.list_process.remove(job)


        for job in self.list_process:         # Start encoder if status is ready
            if ((job.status == "ready") and (n_running <= 2)):
                job.do_schedule()
                set_report_data("last_job", job.file_in + "   " + datetime.datetime.now().strftime("(%m/%d %H:%M.%S)"))
                n_running += 1
                n_ready -= 1
                updatelog(f'Start Encoder... number of Running / Ready is [{n_running}]/[{n_ready}]', True)
                break


        for job in self.list_process:           # remove source file not existing job.. (added 2023/8/4)
            if (not os.path.isfile(job.file_in)):
                updatelog(f'Remove [in file not exist] job ......  {job.encodertype} / {job.file_in}  ', True)
                self.list_process.remove(job)


        for job in self.list_process:           # remove over aged job.. (added 2023/8/4)
            if job.is_timeout():
                updatelog(f'Remove [over aged] job ......  {job.encodertype} / {job.file_in}  ', True)
                self.list_process.remove(job)


                
        self.n_running = n_running
        self.n_ready = n_ready
        set_report_data("running", n_running)
        set_report_data("ready", n_ready)

    def get_infiles(self):
        if len(self.list_process):
            return [encoder.file_in for encoder in self.list_process]
        else:
            return []

    def get_jobs(self):
        result = []
        for encoder in self.list_process:
            result.append(encoder.file_in + " , <" + encoder.encodertype + ">  , <" + encoder.status + ">")
        return result
            
    
    def get_waiters(self):
        if len(self.list_xml):
            return [xml.infile for xml in self.list_xml]
        else:
            return []
    
    def get_updaters(self):
        report = ''
        if len(self.list_update):
            for u in self.list_update:
                report += str(u[0]) + '|' + str(u[1]) + '\n'
        return report

        
            
    def force_quit(self):
        updatelog("Force subprocess terminate and clear queue list", True)
        for encoder in self.list_process:           # count running encoder, terminate aged encoder
            if (encoder.status == "running"):
                updatelog(f'Terminate encoder pid [{encoder.pid}]', True)
                encoder.enc.terminate()
                encoder.checkoutput = ''    # prevent from done file record...
        for waiter in self.list_xml:
            updatelog(f'Terminate waiter [{waiter.infile}]', True)
            waiter.continue_waiter = 0
            
            
class full_path_set:     # Accept file list and chkeck all files are exist

    infile = ''
    timeout = 3600
    continue_waiter = 10
    
    def __init__(self, path_target, path_done = '', path_watch = ''):
        self.path_target = path_target
        self.path_done = path_done
        self.path_watch = path_watch
        self.outputfiles = {}
        self.donefiles = {}

        self.th = ''
        self.continue_waiter = 10

    def set_input(self, infile):
        self.infile = infile
        nameonly = Path(infile).stem
        self.outputfiles["mxf"] = os.path.join(self.path_target, nameonly + ".mxf")
        self.outputfiles["pxy"] = os.path.join(self.path_target, nameonly, nameonly + ".mp4")
        self.outputfiles["aud"] = os.path.join(self.path_target, nameonly, nameonly + ".mp3")
        self.outputfiles["xml"] = os.path.join(self.path_target, nameonly + ".xml")
        self.outputfiles["jpg"] = os.path.join(self.path_target, nameonly, f'{nameonly}_%08d.jpg')
        self.outputfiles["jpg1"] = os.path.join(self.path_target, nameonly, f'{nameonly}_00000000.jpg')
        self.outputfiles["proxy_folder"] = os.path.join(self.path_target, nameonly)
        self.outputfiles["ftp_folder"] = nameonly
        self.donefiles["mxf"] = os.path.join(self.path_done, os.path.basename(infile) + ".mxf__done")
        self.donefiles["pxy"] = os.path.join(self.path_done, os.path.basename(infile) + ".prox_done")
        self.donefiles["cat"] = os.path.join(self.path_done, os.path.basename(infile) + ".cata_done")
        self.donefiles["aud"] = os.path.join(self.path_done, os.path.basename(infile) + ".aud__done")
    
    def get_story_update_xml(self, file_xml):
        nameonly = Path(file_xml).stem
        self.outputfiles["story_update_xml"] = os.path.join(self.path_target, nameonly + '_storyupdate.xml')
        return self.outputfiles["story_update_xml"]
    
    def check_donefiles(self):
        result = True
        for k in [self.donefiles["mxf"], self.donefiles["pxy"], self.donefiles["cat"]]:
            result *= os.path.isfile(k)
        return result

    def set_duration(self, duration = 0.0):
        self.duration = duration
    
    def start_done_waiter(self, timeout = 300):
        self.tm_start = time.time()
        self.timeout = timeout
        self.th = threading.Thread(target=self.run, daemon=True, name="done_waiter")
        self.th.start()
        
    def run(self):
        updatelog(f'Start done file waiter ... {self.infile}')
        while self.continue_waiter:

            if self.check_donefiles():
                self.continue_waiter = 0
                updatelog(f'Done file all exist... exit waiter daemon --> {self.infile}', True)
                updatelog(f'Create xml for job ..  {self.outputfiles["xml"]}', True)
                self.make_xml_job()
                
            else:
                chkeck_job_queue_len(self)
                time.sleep(2)


    def make_xml_job_old(self):
        write_xml_job(self)
        root = ET.Element("SBS_MAM_Job_List")
        job = ET.SubElement(root, "SBS_MAM_Job")
        
        ET.SubElement(job, "Job_Creation_Time").text = str(int(time.time()))
        ET.SubElement(job, "Job_Type").text = "74"
        
        ET.SubElement(job, "Job_Src_Path_HR_Abs").text = self.outputfiles["mxf"]
        ET.SubElement(job, "Job_Src_Path_LR_Abs").text = self.outputfiles["pxy"]
        ET.SubElement(job, "Job_Src_Path_CAT_Abs").text = self.outputfiles["jpg1"]
        
        len_target = len(self.path_target)
        ET.SubElement(job, "Job_Src_Path_HR").text = self.outputfiles["mxf"][len_target:]
        ET.SubElement(job, "Job_Src_Path_LR").text = self.outputfiles["pxy"][len_target:]
        ET.SubElement(job, "Job_Src_Path_CAT").text = self.outputfiles["jpg1"][len_target:]
        
        ET.SubElement(job, "Job_Dest_Path").text = '//nds/storage/international'
        ET.SubElement(job, "Job_Dest_Filename").text = '//nds/storage/international'
        
        try:
            with open(self.donefiles["mxf"], "r", encoding="utf-8") as s:
                line = s.readline()    # abandon first line
                line = s.readlines()
        except Exception as e:
            updatelog(f'Error while read script...   {e}', True)


        appdata = ET.SubElement(job, "Job_Src_App_Data")
        story = ET.SubElement(appdata, 'Story')
        story.tail = None

        for l in line:
            br = ET.SubElement(story, 'br')
            br.tail = l


        
        len_watch = len(self.path_watch)
        ET.SubElement(appdata, "Src_Origin_Abs").text = self.infile
        ET.SubElement(appdata, "Src_Origin").text = self.infile[len_watch:]
        ET.SubElement(appdata, "Src_Duration").text = str(self.duration)

        tree = ET.ElementTree(root)
        ET.indent(tree, '  ')
        tree.write(self.outputfiles['xml'], encoding='utf-8', xml_declaration=True)


    def make_xml_job(self):
        write_xml_job(self)



def chkeck_job_queue_len(this):     # Delete unused xml waiter
    global jobs
    if not len(jobs.list_process):
        if not this.infile in [encoder.file_in for encoder in jobs.list_process]:  # Check if there is xml related encoder..
            this.continue_waiter -= 1
            updatelog(f'Change continue_waiter -1 .. [{this.continue_waiter}] {this.infile}', True)
    

class encoder:
    binary = "ffmpeg.exe"
    result = ""
    pid = 0
    tm_start = 0
    tm_elapsed = 0
    tm_maxage = 3600
    oneline = ""
    file_in = ""
    file_out = ""
    duration = 0
    out_time_ms = 0
    progressbar = ""
    nameonly = ""
    debugpath = ""
    donepath = ""
    checkoutput = ""
    status = "idle"     # idle, setfile, ready, running, finish
    schedule_fn = ""
    done_file = ""
    done_message = ""
    script_data = ""
    encodertype = ""    # one of 'mxf' 'proxy' 'catalog' 'audio'

    
    def set_file(self, file_in, file_out, duration):
        self.file_in = file_in
        self.file_out = file_out
        self.duration = duration
        parser = Path(file_in)
        self.nameonly = parser.stem
        self.debugpath = os.path.join(os.getcwd(), 'debug')
        self.donepath = os.path.join(os.getcwd(), 'done')
        self.status = "setfile"
        self.tm_maxage = duration     # Suppose Encoder is faster than realtime !!
    
    def set_script(self, script_data):
        self.script_data = script_data

    def set_schedule(self, name_fn):
        schedule_dict = {"mxf" : self.startMXF, "proxy" : self.startPROXY, "catalog" : self.startCATALOG, "audio" : self.startAUDIO}
        self.schedule_fn = schedule_dict[name_fn]
        updatelog(f'Register schedule function as "{name_fn}"')
        self.status = "ready"
        self.encodertype = name_fn
    
    def do_schedule(self):
        if os.path.isfile(self.done_file):
            updatelog(f'Remove existing done file .... {self.done_file}')
            try:
                os.remove(self.done_file)    # remove done file before encoding start..
            except Exception as e:
                updatelog(e, True)
        self.schedule_fn()
    
    def get_age(self):
        age = 0
        if (self.status == "running"):
            age = time.time() - self.tm_start
            
        return age
    
    def is_timeout(self):
        if (self.get_age() > self.tm_maxage):
            return True
        else:
            return False
    
    
    def startMXF(self):
        newenv = os.environ.copy()
        newenv["FFREPORT"] = f'file=FFMPEG_MXF_{self.nameonly}.LOG:level=32'    
        self.tm_start = time.time()
        cmdline = f'{self.binary} -i "{self.file_in}" -r ntsc -c:v mpeg2video -profile:v 0 -level:v 2 -b:v 50000k -maxrate 50000k -minrate 50000k -bufsize 17825792 -mpv_flags strict_gop -flags +ildct+ilme+cgop -top 1 -g 15 -bf 2 -color_primaries 1 -color_trc 1 -colorspace 1 -sc_threshold 1000000000 -filter_complex "[0:v]format=pix_fmts=yuv422p[vformat];[vformat]scale=w=1920:h=1080:interl=1;[0:a]aresample=48000:async=10000[are];[are]pan=8c|c0=c0|c1=c1|c2=c0|c3=c1|c4=c0|c5=c1|c6=c0|c7=c1[a8ch];[a8ch]apad[apd];[apd]channelsplit=channel_layout=7.1" -acodec pcm_s24le -y  -max_delay 0 -shortest -max_interleave_delta 1000000000 -t {self.duration} "{self.file_out}" -nostats -progress pipe:2 '
        self.enc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=newenv, cwd=self.debugpath)
        self.pid = self.enc.pid
        updatelog(f'MXF Encoder started, pid = {self.enc.pid}', True)
        self.t = threading.Thread(target=self.get_pipe, daemon=False, name="MXFENC")
        self.t.start()
        description_bar = '0000' + str(self.pid)
        description_bar = description_bar[-5:]
        self.progressbar = TqdmUpTo(total=int(self.duration), desc=f'[{description_bar}-MXF]')
        self.checkoutput = self.file_out
        self.status = "running"
        start_waiter(self)
        #subprocess.Popen(f'ffmpeg -i "{filename}"  -r ntsc -c:v mpeg2video -profile:v 0 -level:v 2 -b:v 50000k -maxrate 50000k -minrate 50000k -bufsize 17825792 -mpv_flags strict_gop -flags +ildct+ilme+cgop -top 1 -g 15 -bf 2 -color_primaries 1 -color_trc 1 -colorspace 1 -sc_threshold 1000000000 -filter_complex "[0:v]format=pix_fmts=yuv422p[vformat];[vformat]scale=w=1920:h=1080:interl=1;[0:a]aresample=48000:async=10000[are];[are]pan=8c|c0=c0|c1=c1|c2=c0|c3=c1|c4=c0|c5=c1|c6=c0|c7=c1[a8ch];[a8ch]apad[apd];[apd]channelsplit=channel_layout=7.1" -acodec pcm_s24le -y  -max_delay 0 -shortest -max_interleave_delta 1000000000 -t {duration} "{out_fullpath}"')
    
    def startPROXY(self):
        newenv = os.environ.copy()
        newenv["FFREPORT"] = f'file=FFMPEG_PROXY_{self.nameonly}.LOG:level=32'
        self.tm_start = time.time()
        cmdline = f'{self.binary} -i "{self.file_in}" -r ntsc -vf scale=720:400 -c:v h264 -preset:v fast -g 15 -b:v 2000k -y -c:a aac -b:a 128k  -t {self.duration} "{self.file_out}" -nostats -progress pipe:2 '
        self.enc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=newenv, cwd=self.debugpath)
        self.pid = self.enc.pid
        updatelog(f'PROXY Encoder started, pid = {self.enc.pid}', True)
        self.t = threading.Thread(target=self.get_pipe, daemon=False, name="PROXYENC")
        self.t.start()
        description_bar = '0000' + str(self.pid)
        description_bar = description_bar[-5:]
        self.progressbar = TqdmUpTo(total=int(self.duration), desc=f'[{description_bar}-PXY]')
        self.checkoutput = self.file_out
        self.status = "running"

    
    def startAUDIO(self):
        newenv = os.environ.copy()
        newenv["FFREPORT"] = f'file=FFMPEG_AUDIO_{self.nameonly}.LOG:level=32'
        self.tm_start = time.time()
        cmdline = f'{self.binary} -i "{self.file_in}" -vn -y -c:a mp3 -b:a 128k  -t {self.duration} "{self.file_out}" -nostats -progress pipe:2 '
        self.enc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=newenv, cwd=self.debugpath)
        self.pid = self.enc.pid
        updatelog(f'AUDIO Encoder started, pid = {self.enc.pid}', True)
        self.t = threading.Thread(target=self.get_pipe, daemon=False, name="AUDIOENC")
        self.t.start()
        description_bar = '0000' + str(self.pid)
        description_bar = description_bar[-5:]
        self.progressbar = TqdmUpTo(total=int(self.duration), desc=f'[{description_bar}-AUD]')
        self.checkoutput = self.file_out
        self.status = "running"


    def startCATALOG(self):
        newenv = os.environ.copy()
        newenv["FFREPORT"] = f'file=FFMPEG_CATALOG_{self.nameonly}.LOG:level=32'
        self.tm_start = time.time()
        cmdline = f'{self.binary} -i "{self.file_in}" -vf yadif,select=\'isnan(prev_selected_t)+gte(t-prev_selected_t\,10)+gt(scene\,0.2)\',scale=720x400 -vsync 0  -frame_pts 1  -enc_time_base 1/29.97  -y "{self.file_out}" -nostats -progress pipe:2 '
        self.enc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=newenv, cwd=self.debugpath)
        self.pid = self.enc.pid
        updatelog(f'CATALOG Encoder started, pid = {self.enc.pid}', True)
        self.t = threading.Thread(target=self.get_pipe, daemon=False, name="CATAENC")
        self.t.start()
        description_bar = '0000' + str(self.pid)
        description_bar = description_bar[-5:]
        self.progressbar = TqdmUpTo(total=int(self.duration), desc=f'[{description_bar}-CAT]')
        self.checkoutput = self.file_out[:-8] + "00000000.jpg"
        self.status = "running"


    
    def get_pipe(self):
        while psutil.pid_exists(self.pid):
            self.tm_elapsed = time.time() - self.tm_start
            try:
                line = self.enc.stderr.read(1).decode(encoding='cp949')     # read single byte until meets new line
                self.oneline += line
                if ('\n' in self.oneline):
                    #print(f"\r encoder output =    {self.oneline}")
                    #print(f"\r   subprocess running time = {self.tm_elapsed}\n")
                    if self.oneline.startswith("out_time_ms="):     # Get ffmpeg progress in microseconds..
                        out_time_ms = int(self.oneline[12:])
                        self.out_time_ms = float(out_time_ms) / 1000000
                        #updatelog(self.out_time_ms, True)
                    self.oneline = ""
            except:
                time.sleep(0.1)
                self.oneline = ""
                continue
        if self.checkoutput:
            if os.path.isfile(self.checkoutput):
                size_outputfile = os.stat(self.checkoutput).st_size
                if size_outputfile:
                    updatelog(f'\nOutput file size is {size_outputfile / 1024 / 1024} MB \n  --->  {self.checkoutput}', True)
                    do_finishrecord(self)
                else:
                    updatelog(f'Error ! Output file has size 0...  check log  ---> {self.checkoutput}', True)
            else:
                updatelog(f'\nError ! Output file is not exist... check log  --->  {self.checkoutput}', True)
        updatelog(f'\nChange job status as FINISH...  --->  {self.file_out}', True)
        self.status = "finish"
        self.progressbar.update_to(int(self.duration))
        self.progressbar.close()
        updatelog(f"\nEncoder Terminated... pid = {self.pid}", True)
        self.pid = -1


def start_waiter(this):
    global jobs, args
    
    infile = this.file_in
    fp = full_path_set(args.target, args.done, args.watchfolder)
    fp.set_input(infile)
    fp.set_duration(this.duration)
    if os.path.isfile(fp.outputfiles['xml']):
        try:
            os.path.remove(fp.outputfiles['xml'])
        except Exception as e:
            updatelog(f'Error deleting xml file ... {fp.outputfiles["xml"]}')
      
    
    
    fp.start_done_waiter()
    jobs.list_xml.append(fp)


def do_encoding(filename):
    global ur, jobs, args, sc
    if filename in jobs.get_infiles():
        updatelog(filename, True)
        updatelog("source file already exist in job queue.... abort adding job scheduling..", True)
        return
    
    if not os.path.isfile(filename):
        updatelog(f'source file is not exist.. abort adding job scheduling.. {filename}', True)
        return


    mediainfo = probe()

    mediainfo.analysis(filename)
    duration= mediainfo.get_duration()

    if (duration < 5):
        updatelog(f'Media has very short duration or fail to get duration.. abort encoding {filename}', True)
        return

    fp = full_path_set(args.target, args.done)
    fp.set_input(filename)

    updatelog(f'Schedule transcoding ...  Number of running/ready is [{jobs.n_running}/{jobs.n_ready}]', True)

    updatelog(f'Input path is {filename}', True)
    updatelog(f'Output path is {fp.outputfiles["mxf"]}', True)
    updatelog(f"Input file duration is {duration} second", True)


    try:
        os.mkdir(fp.outputfiles["proxy_folder"])
    except:
        updatelog("Error proxy folder createion !!!")
        updatelog(f'proxy folder = {fp.outputfiles["proxy_folder"]}')


    mp3 = encoder()
    mp3.set_file(filename, fp.outputfiles["aud"], duration)
    mp3.set_schedule("audio")          # schedule STT audio encoding
    mp3.done_file = fp.donefiles["aud"]
    jobs.list_process.append(mp3)
    
    mxf = encoder()
    mxf.set_file(filename, fp.outputfiles["mxf"], duration)
    mxf.set_schedule("mxf")          # schedule MXF HiRes encoding
    mxf.done_file = fp.donefiles["mxf"]
    
    try:
        script_file = sc.search_script_file(filename)[-1]       # Select lastest version.
    except Exception as e:
        updatelog(f'Error while search script file.. {filename}', True)
        script_file = ''
        
    mxf.set_script(sc.get_script_data(script_file))
    jobs.list_process.append(mxf)
    ur.add_hourmeter(duration / 3600)
    updatelog(f'Encoder Hour meter changed ....  {ur.get_hourmeter()} h', True)


        

    proxy = encoder()
    proxy.set_file(filename, fp.outputfiles["pxy"], duration)
    proxy.set_schedule("proxy")       # schedule Prosy encoding
    proxy.done_file = fp.donefiles["pxy"]
    jobs.list_process.append(proxy)


    catalog = encoder()
    catalog.set_file(filename, fp.outputfiles["jpg"], duration)
    catalog.set_schedule("catalog")      # schedule catalogging
    catalog.done_file = fp.donefiles["cat"]
    jobs.list_process.append(catalog)
    

def do_add_updatelist(file_script):
    global jobs
    if len(jobs.list_update):
        if file_script in [data[1] for data in jobs.list_update]:
            updatelog(f'updated script already exist in queue... exit {file_script}', True)
            return
    jobs.list_update.append([time.time(), file_script])
        
    
    
def on_created(event):
    global args
    updatelog(f"-- created!    {get_name(event.src_path)}", True)
    set_report_data("last_event", f"-- created!    {get_name(event.src_path)}")
    if (get_extension(event.src_path).upper() == ".XML"):
        scf = scriptfinder(args.watchfolder, args.script)
        list_mp4 = scf.search_media_files(event.src_path)
        if len(list_mp4):
            do_add_updatelist(event.src_path)
    
def on_deleted(event):
    updatelog(f"-- deleted!   {get_name(event.src_path)}", True)
    set_report_data("last_event", f"-- deleted!    {get_name(event.src_path)}")


def on_modified(event):
    global args
    updatelog(f"-- modifed !  {get_name(event.src_path)}", True)
    set_report_data("last_event", f"-- modified!    {get_name(event.src_path)}")
    if (get_extension(event.src_path).upper() == ".XML"):
        scf = scriptfinder(args.watchfolder, args.script)
        list_mp4 = scf.search_media_files(event.src_path)
        if len(list_mp4):
            do_add_updatelist(event.src_path)

def on_moved(event):
    global args, jobs
    updatelog(f"-- moved !    {get_name(event.src_path)} to {get_name(event.dest_path)}", True)
    set_report_data("last_event", f"-- created!    {get_name(event.dest_path)}")
    if (get_extension(event.dest_path).upper() == ".XML"):
        scf = scriptfinder(args.watchfolder, args.script)
        list_mp4 = scf.search_media_files(event.dest_path)
        if len(list_mp4):
            do_add_updatelist(event.dest_path)    

def do_finishrecord(encoder):
    with open(encoder.done_file, "w", encoding="utf-8") as f:
        f.write(encoder.checkoutput + "\r\n" + encoder.script_data)

def argparser():
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
            SBS Global News Processor by sendust  (2023, Media IT)

               Example)  python watchfolder.py --watchfolder "d:\download" --target "e:\done"
                         
                         For Full help ----
                         python watchfolder.py --help
                '''))

    parser.add_argument("--watchfolder", required=True, type=str, default="E:/int_download", help="path for watch folder")
    parser.add_argument("--target", required=True, type=str, default="f:/int_mxf/", help="path for target folder")
    parser.add_argument("--done", required=False, type=str, default=os.path.join(os.getcwd(), 'done'), help="path for done files")
    parser.add_argument("--timeout", required=False, type=int, default=3600, help="Maxinum Encoder age")
    parser.add_argument("--maxenc", required=False, type=int, default=3, help="Maxinum Concurrent Encoder")
    parser.add_argument("--port", required=True, type=int, default=4020, help="Engine status report port")
    parser.add_argument("--script", required=True, type=str, default="reuter", help="Script type [reuter, aptn, cnn]")
    parser.add_argument("--polling", required=False, type=bool, default=False, help="set True if you want polling watch (CIFS)")
    parser.add_argument("--transfer", required=False, type=str, default="", help="FTP Transfer address.. ex) 10.10.108.2")
    parser.add_argument("--username", required=False, type=str, default="", help="FTP username")
    parser.add_argument("--password", required=False, type=str, default="", help="FTP password")

    return parser.parse_args()


def gather_missing_adv(path_done, path_watch):
    global args, jobs
    updatelog(">>>>> Start gather missing...", True)
    jobs.tm_last_gather = time.time()
    fps = full_path_set(args.target, path_done)
    updatelog(f'.... collect mp4 file list.... from path {path_watch}', True)
    
    if not os.path.exists(path_watch):
        updatelog(f'Error.. watch folder is not exist.. {path_watch}', True)
        return []
        
    try:
        list_watch = glob.glob(path_watch + '/*.mp4')
    except Exception as e:
        updatelog(f'Error while glob... {e}')
        list_watch = []
    list_missing = []


    for f in list_watch:
        fps.set_input(f)
        if os.path.basename(f).startswith("WH16x9"):     # CNN exception (skip proxy)
            continue
            
        try:
            mtime = os.path.getmtime(f)
        except Exception as e:
            mtime = time.time()
            updatelog(f'Error get modification time {f}\n{e}', True)
        if ((time.time() - mtime) < 120):  # skip some new files (under growing file)
            updatelog(f'Skip under aged file..  {f}')
            continue

        result = True            
        #done_mxf = fps.donefiles["mxf"]
        #done_pxy = fps.donefiles["pxy"]
        #done_cat = fps.donefiles["cat"]
        #result = os.path.isfile(done_mxf) and os.path.isfile(done_pxy) and os.path.isfile(done_cat)
        for each in ["mxf", "pxy", "cat"]:
            result = result and os.path.isfile(fps.donefiles[each])
        
        if not result:
            list_missing.append(f)
    updatelog(f'---- Missing file list ----', True)
    
    for m in list_missing:
        updatelog(get_name(m), True)
    updatelog(f'Number of missing file = {len(list_missing)}', True)
    updatelog(">>>>> Finish gather missing...", True)
    return list_missing    

    
def show_tick_line(q):
    global args, jobs
    if not tqdm.disable_tick:
        print(f'Watch = {args.watchfolder} <---> {format("%.1f" % (300 - (time.time() - jobs.tm_last_gather)))}/{format("%.1f" % (time.time() - jobs.tm_startup))}  Wait new media...  {jobs.progress_cycle}', end="\r")


def get_extension(f):           # return .mp4  .txt   .avi ...
    name, extension = os.path.splitext(f)
    return extension

def get_name(f):    # example)  head ==> c:/temp,   tail ==> test.txt
    head, tail = os.path.split(f)
    return tail


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
        try:
            self.observer.schedule(self.event_handler, path, recursive=True)
            self.observer.start()
        except Exception as e:
            updatelog(f'Error while start default observer... {e}', True)

    def stop(self):
        try:
            self.observer.stop()
            self.observer.join(1)
        except Exception as e:
            updatelog(f'Error while stop default observer.. {e}', True)
            
    def on_created(self, event):
        #print(f"-- created!    {event.src_path}")
        on_created(event)

    def on_deleted(self, event):
        #print(f"-- deleted!   {event.src_path}")
        on_deleted(event)
        

    def on_modified(self, event):
        #print(f"-- modifed !  {event.src_path}")
        on_modified(event)

    def on_moved(self, event):
        #print(f"-- moved !    {event.src_path} to {event.dest_path}")    
        on_moved(event)
    


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
        try:
            self.observer.schedule(self.event_handler, path, recursive=True)
            self.observer.start()
        except Exception as e:
            updatelog(f'Error while start poll observer vfs... {e}', True)

    def stop(self):
        try:
            self.observer.stop()
            self.observer.join(1)
        except Exception as e:
            updatelog(f'Error while stop poll observer vfs... {e}', True)

    def on_created(self, event):
        #print(f"-- created!    {event.src_path}")
        on_created(event)
        
    def on_deleted(self, event):
        #print(f"-- deleted!   {event.src_path}")
        on_deleted(event)
        
    def on_modified(self, event):
        #print(f"-- modifed !  {event.src_path}")
        on_modified(event)
        
    def on_moved(self, event):
        #print(f"-- moved !    {event.src_path} to {event.dest_path}")
        on_moved(event)



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
            updatelog(f'Script head ----\n{dict_get_script_data[self.mode](infile)[:100]}', True)   # Show few header lines..
        except Exception as e:
            updatelog(f'Error acquiring script data {e}')
        return dict_get_script_data[self.mode](infile)



    def search_script_file_reuter(self, infile):   # infile is mp4
        # 2023-05-15T130215Z_2_LWD254615052023RP1_RTRWNEV_D_2546-SLOVAKIA-GOVERNMENT.MP4
        try:
            key = get_name(infile).split('_')[-1][5:-4] + '.XML'
            key_number = get_name(infile).split('_')[-1][:4]        # probe 4 digit number part
        except Exception as e:
            updatelog(f'Error while parsing mp4 file name for script.. reuter  {infile} \n{e}', True)
            return []
            
        globkey = os.path.join(self.watchpath, '*' + key)
        updatelog(f'glob script files with key.. {globkey}', True)
        sclist = []
        sclist = glob.glob(globkey) 
        try:
            sclist.sort(key=os.path.getmtime)
        except Exception as e:
            updatelog(f'Error while sorting script list {e}', True)
        
        sclist2 = []
        
        for xmlfile in sclist:       # find if there is id matched file in xml list
            head, tail = os.path.split(xmlfile)
            if key_number in tail:
                sclist2.append(xmlfile)
        
        self.file_script = []
        
        if sclist:
            updatelog("Find matching script using basic algorithm", True)
            self.file_script = sclist   # return script list

        if sclist2:
            updatelog(f'Find better matching script using id number.. {key_number}', True)
            self.file_script = sclist2  # return improved script list

        return self.file_script
    
    def get_script_data_reuter(self, infile = ''):   # in file is xml
        print(infile)
        if not infile:
            self.text_script =  "Error finding script data.... xml file not given"
        try:
            with open(infile, encoding='utf-8') as fp:
                soup = BeautifulSoup(fp, 'html.parser', from_encoding='utf-8')
                self.text_script = soup.body.text
        except:
            self.text_script = "Error finding script data......"
        return self.text_script
        


    def search_script_file_aptn(self, infile):   # infile is mp4
        # 5362317_Games SEAG 17 Update 2_0_1080i60ESSENCE--3e371.mp4
        try:
            id = get_name(infile).split('_')[0]
        except:
            id = "Error parsing mp4 file name"
        globkey = os.path.join(self.watchpath, id + '*_script.xml')
        updatelog(f'glob script files with key.. {globkey}', True)
        sclist = glob.glob(globkey)
        try:
            sclist.sort(key=os.path.getmtime)
        except Exception as e:
            updatelog(f'Error while sorting script list {e}', True)
        if sclist:
            return sclist  # return script list
        else:
            return []


    def get_script_data_aptn(self, infile = ''):   # in file is xml
        if not infile:
            self.text_script =  "Error finding script data.... xml file not given"
        try:
            with open(infile, encoding='utf-8') as fp:
                soup = BeautifulSoup(fp.read(), 'html.parser')
                self.text_script = soup.body.text
        except:
            self.text_script = "Error finding script data......"
        return self.text_script


    def search_script_file_cnn(self, infile):   # infile is mp4
        # BHDP_BU-25TU_FILE_ HOME DEPOT SALE_CNNA-ST1-200000000004f132_175_0.mp4
        parser = get_name(infile).split('_')
        try:
            #key = parser[1] + '_' + parser[2]     # Get news ID  // caution !! do not put cnn proxy mp4 
            key = '_'.join(parser[1:-3])        # Improve 2023/5/31
        except Exception as e:
            updatelog(f'Error parsing mp4 file name for script searching.. {e}', True)
            return []
        if not len(key):
            key = "Error parsing key...."
        globkey = os.path.join(self.watchpath, key + '*.xml')
        updatelog(f'glob script files with key.. {globkey}', True)        
        sclist = glob.glob(globkey)
        try:
            sclist.sort(key=os.path.getmtime)
        except Exception as e:
            updatelog(f'Error while sorting script list {e}', True)     
        if sclist:
            return sclist  # return script list
        else:
            return []


    def get_script_data_cnn(self, infile = ''):   # in file is xml
        if not infile:
            self.text_script =  "Error finding script data.... xml file not given"
        try:
            with open(infile, encoding='utf-8') as fp:
                soup = BeautifulSoup(fp.read(), 'html.parser')
                self.text_script = soup.storynum.text + '\n' + re.sub('<.*?>', '', soup.description.text)
        except:
            self.text_script = "Error finding script data......"
        return self.text_script


    def search_media_files(self, file_xml): # Search mp4 media files from xml script
        tuple_search_media_file = {'reuter': self.search_media_files_reuter, 'aptn' : self.search_media_files_aptn, 'cnn' : self.search_media_files_cnn}
        updatelog(f'Search media files from xml script -> mode is {self.mode}', True)
        mediafiles = tuple_search_media_file[self.mode](file_xml)
        
        try:
            mediafiles.sort(key=os.path.getmtime)
        except Exception as e:
            updatelog(f'Error while sorting media file list {e}', True)  

        if mediafiles:
            for mp4 in mediafiles:
                updatelog(f'Search media files result is {mp4}', True)
            return mediafiles
        else:
            updatelog(f'Fail to search media files', True)
            return []
        
    def search_media_files_reuter(self, file_xml):
        name = Path(file_xml).stem
        key = ''                # 2023-05-15T122944Z_7_RW257215052023RP1_RTRMADC_0_G7-SUMMIT-EU.XML
        try:
            key = name.split('_')[-1]
        except Exception as e:
            updatelog(f'Error key sampling while search media..  {e}')
            return []
  
        #print(os.path.join(self.watchpath, '*' + key))
        globkey = os.path.join(self.watchpath, '*' + key + '.MP4')
        updatelog(f'Glob media files with key...  {globkey}', True)
         
        if not key:             # add condition 2023/5/30
            list_media = []
        else:
            list_media = glob.glob(globkey)
        return list_media
        
    def search_media_files_aptn(self, file_xml):
        # cctv057030_China-Central AsiaCivil AviationFlights_1_Script.xml--6f7e1_Script.xml
        parser = get_name(file_xml).split('_')
        if not 'Script.xml' in parser:
            return []
        if len(parser) > 1:
            key = parser[0] + '_' + parser[1]
        else:
            return []
        globkey = os.path.join(os.path.join(self.watchpath, key + '*.mp4'))
        updatelog(f'Glob media files with key...  {globkey}', True)            
        list_media = glob.glob(globkey)
        return list_media
        
    def search_media_files_cnn(self, file_xml):
        # RQ-504TU_REQUEST-REP NANCY MAC_CNNA-ST1-200000000004f124_900_0.xml
        # BHDP_RQ-504TU_REQUEST-REP NANCY MAC_CNNA-ST1-200000000004f124_175_0.mp4
        parser = get_name(file_xml).split('_')
        if (len(parser) < 3):
            updatelog(f'Error.. xml file is not standard cnn script. {file_xml}', True)
            return []
        try:
            #key = parser[0] + '_' + parser[1]
            key = '_'.join(parser[0:-3])        # Improve 2023/5/31
        except Exception as e:
            updatelog(f'Error while parsing script file name.. {file_xml}\n{e}', True)
            return []
        globkey = os.path.join(os.path.join(self.watchpath, 'BHDP_' + key + '*.mp4'))
        updatelog(f'Glob media files with key...  {globkey}', True)      
        list_media = glob.glob(globkey)
        return list_media


class udp_reporter:
    
    send_data = {"age" : 0,
                 "Hour" : 0.0,
                 "running" : 0,
                 "ready" : 0,
                 "last_job" : "",
                 "last_event" : ""}
                 

    def __init__(self, host= "127.0.0.1", port = 61234):
        self.port = port
        self.host = host
    
    def add_hourmeter(self, h):             # Hour meter increment
        self.send_data["Hour"] += h
    
    def get_hourmeter(self):
        return self.send_data["Hour"]
    
    def set_data(self, key, value):
        self.send_data[key] = value
    
    def send(self):
        data = ""
        for k in self.send_data:
            data += k + "**" + str(self.send_data[k]) + "\n"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(bytes(data, "utf-8"), (self.host, self.port))
    
    def get_status(self):
        data = ""
        for k in self.send_data:
            data += k + "**" + str(self.send_data[k]) + "\n"
        return data
    
def set_report_data(key, value):
    ur.set_data(key, value)



class tcp_svr_thread():
    running = True
    
    def __init__(self, address="0.0.0.0", port=5250):
        updatelog(f'Create tcp class with port {port}', True)
        self.runnig = True
        updatelog("Check another engine is running..........", True)
        # Check another Engine instance with port number
        for proc in process_iter():
            for conns in proc.connections(kind = 'inet'):
                if conns.laddr.port == port:
                    if proc.pid:   # pid is not zero
                        updatelog("Another engine instance found  {0}... exit script.".format(proc), True)
                        sys.exit()

        try: 
            # create an INET, STREAM socket
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # bind the socket to a public host, and a well-known port
            result1 = self.serversocket.bind((address, port))
            #updatelog("tcp server bind result is {0}".format(result1), True) 
            # become a server socket
            result2 = self.serversocket.listen(5)   # concurrent connection number
            #updatelog("tcp server listen result is {0}".format(result2), True)

        except Exception as err:
            updatelog(err)
            updatelog("Error creating socket... /// {0}".format(err), True)
            sys.exit()
        
        self.thread_svr = threading.Thread(target=self.run_server, daemon=True, name="TCPSVR")
        
    def start(self):
        self.running = True
        self.thread_svr.start()
        
    def stop(self):
        updatelog("tcp server stop....  Try to join..", True)
        self.running = False
        self.serversocket.close()
        self.thread_svr.join(1)
        updatelog("Finish tcp join", True)

        
    def run_server(self):
        updatelog("<<<<Begin TCP acception>>>>>", True)
        
        while self.running:
            try:
                updatelog("Start new acception..", True)
                clientsocket, address = self.serversocket.accept()
                threading.Thread(target=self.reply_client, daemon=True, args=[clientsocket, address], name="TCPCLIENT").start()
                updatelog(f'client address is {address}', True)
            except Exception as e:
                updatelog(e, True)
                
    def reply_client(self, clientsocket, address):
        updatelog("reply_client....", True)
        try:
            clientreq_msg = clientsocket.recv(1024).decode()
            updatelog("Message from client: {}   ".format(clientreq_msg), True)
            clientsocket.send(("tcp MSG // " + clientreq_msg + " ").encode('utf-8'))
            decode_command_new(address, clientreq_msg)
        except Exception as e:
            updatelog("exception while reply_client", True)
            updatelog(e, True)



# Delete old files... Created by sendust  2023/5/1
class delete_old():

    list_path=[]
    list_age=[]
    schedule = False
    period = 9999
    
    
    def add_path_age(self, path, hour):
        self.list_path.append(path)
        self.list_age.append(hour * 60 * 60)     # convert hour to second
        
    def start_schedule(self, hour):
        self.period = hour
        period_random = self.period * 60 * random.randint(40, 60)   # added 2023/6/7
        self.schedule = True
        self.tmr = threading.Timer(period_random, self.do_delete)  # timer accept second
        self.tmr.name = "DEL_OLD"
        self.tmr.start()
        updatelog(f'delete schedule Timer engaged.. from [start_schedule] function. remain sec.. {period_random}', True)

    def do_delete(self):
        if self.schedule:               # Move position here..  (beginning of function)   2023/5/30
            period_random = self.period * 60 * random.randint(40, 60)   # added 2023/6/7
            self.tmr = threading.Timer(period_random, self.do_delete)
            self.tmr.name = "DEL_OLD"
            self.tmr.start()
            updatelog(f'delete schedule Timer engaged.. from [do_delete] function. remain sec.. {period_random}', True)
                
        if not len(self.list_path):
            updatelog("Old path list is empty... There is  nothing to do..", True)
            return
            
        now = time.time()   # get current time in second
        for idx, path in enumerate(self.list_path):
            updatelog(f'Collect old file list from path = {path}', True)
            flist = glob.glob(os.path.join(path, "**"), recursive=True)    # Include subdir
            #flist = glob.glob(os.path.join(path, "*"), recursive=False)     # Exclude subdir
            updatelog(f'Number of files = {len(flist)}', True)
            count_file = 0
            count_folder = 0
            for f in flist:
                try:                                # file can be deleted by another engine !!!
                    tm_mod = os.path.getmtime(f)    # Modification time in second
                    tm_cre = os.path.getctime(f)    # Creation time in second, only Windows
                    diff = now - tm_cre             # unit is in second
                except Exception as e:
                    updatelog(f'Error while old collecting old files {f}\n{e}')
                    diff = 0
                    
                if (diff > self.list_age[idx]):
                    #print(f, "  ---- old !!! will delete")
                    #print(datetime.datetime.fromtimestamp(tm_mod))
                    if os.path.isfile(f):
                        try:
                            os.remove(f)
                            count_file += 1
                        except Exception as e:
                            updatelog(f'Error deleting ...   {f}', True)
                    else:
                        try:
                            os.rmdir(f)
                            count_folder += 1
                        except Exception as e:
                            updatelog(f'Error deleting ...   {f}', True)
                        
            updatelog(f'Number of deleted files = {count_file}', True)    
            updatelog(f'Number of deleted folders = {count_folder}', True)    


    def cancel_timer(self):
        self.schedule = False
        self.tmr.cancel()
        self.schedule = False

def shortsleep(duration, get_now=time.perf_counter):
    now = get_now()
    end = now + duration
    while now < end:
        now = get_now()



def send_largetext_udp_ahk(address, largedata, finishtag = ''):
    #UDP_IP = "10.10.108.43"
    UDP_PORT = args.port        # Get udp port from argument parser
    UDP_IP = address[0]

    n = 100     # chunk length
    chunks = [largedata[i:i+n] for i in range(0, len(largedata), n)]
    chunks.append('\n<finish_transfer>' + finishtag)
    byte_sent = 0
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto('<start_transfer>'.encode("utf-8"), (UDP_IP, UDP_PORT))

    tqdm.disable_tick = True        # Disable line tick count show
    for c in tqdm(chunks, ascii='-#'):
        shortsleep(0.00005)   # add 1ms delay for autohotkey's slow udp processing....
        byte_sent += sock.sendto(c.encode("utf-8"), (UDP_IP, UDP_PORT))
        #print(byte_sent, end=" ") # debugging !! check sent byte
        set_report_data("last_event", "byte_sent=" + str(byte_sent))  # Debugging !!
    tqdm.disable_tick = False
    updatelog(f'byte sent = {byte_sent} chunk lengh is {len(chunks)}', True)



def decode_command_new(address, client_req):
    global jobs, args, ur, tcpsvr, ob, periodic, deleteold, sc
    
    set_report_data("clientreq", client_req)
    if client_req.startswith("<get_income>"):
        largedata = get_media_list_ext(args.watchfolder, '*.mp4')
        send_largetext_udp_ahk(address, largedata, '<incomelist>')
    
    elif client_req.startswith("<get_script>"):
        req_data = client_req.split("><")[1][:-1]   # select second bracketted protocol
        dict_script = sc.search_script_file(req_data)
        updatelog(f'Number of searched script = {len(dict_script)}', True)
        dict_script_new = [each + "|" + time.strftime('%Y%m%d %H%M%S', time.localtime(os.path.getmtime(each))) for each in dict_script]
        largedata = ""
        for item in dict_script_new:                     # result is list !!
            largedata += item + '\n'
        send_largetext_udp_ahk(address, largedata, '<scriptlist>')
    
    elif client_req.startswith("<get_scdata>"):
        req_data = client_req.split("><")[1][:-1]   # select second bracketted protocol
        largedata = sc.get_script_data(req_data)    # result is text  !!
        send_largetext_udp_ahk(address, largedata, '<scriptdata>')

    elif client_req.startswith("<get_rawscript>"):  # send raw xml script data
        req_data = client_req.split("><")[1][:-1]   # select second bracketted protocol
        with open(req_data, "r", encoding="utf-8") as rawdata:
            ary_line = rawdata.readlines()
        largedata = ''.join(ary_line)
        send_largetext_udp_ahk(address, largedata, '<rawscript>')

        
    elif client_req.startswith("<get_waiters>"):
        updatelog(jobs.get_waiters(), True)
        largedata = ''
        for j in jobs.get_waiters():
            largedata += j + '\n'
        send_largetext_udp_ahk(address, largedata, '<waiters>')
        
    elif client_req.startswith("<get_jobs>"):
        updatelog("Response get_jobs request..", True)
        largedata = ''
        for j in jobs.get_jobs():
            largedata += j + '\n'
        send_largetext_udp_ahk(address, largedata, '<jobs>')
        updatelog(largedata, True)
    
    elif client_req.startswith("<get_status>"):
        updatelog(ur.get_status(), True)
        send_largetext_udp_ahk(address, ur.get_status(), '<status>')

    elif client_req.startswith("<get_updaters>"):
        report = jobs.get_updaters()
        updatelog("send updaters queue information", True)
        updatelog(report, True)
        send_largetext_udp_ahk(address, report, '<updaters>')

    elif client_req.startswith("<update_scdata>"):  # update new story
        req_data = client_req.split("><")[1][:-1]   # select second bracketted protocol
        updatelog(f'update story xml from tcp command {req_data}')
        do_story_update([time.time(), req_data])

    elif client_req.startswith("<do_encode>"):  # Manual encoding from tcp command
        req_data = client_req.split("><")[1][:-1]   # select second bracketted protocol
        updatelog(f'Queue up Manual encoding from tcp command {req_data}')
        do_encoding(req_data)

    elif client_req.startswith("<get_media>"):  # Search script related media
        req_data = client_req.split("><")[1][:-1]   # select second bracketted protocol
        updatelog(f'Search script related media from tcp command {req_data}', True)
        dict_media = sc.search_media_files(req_data)
        updatelog(f'Number of searched media = {len(dict_media)}', True)
        dict_media_new = [each + "|" + time.strftime('%Y%m%d %H%M%S', time.localtime(os.path.getmtime(each))) for each in dict_media]
        largedata = ""
        for item in dict_media_new:                     # result is list !!
            largedata += item + '\n'
        send_largetext_udp_ahk(address, largedata, '<medialist>')

    elif client_req.startswith("<get_ftplist>"):  # get ftp list
        connection = transfer(args.transfer, args.username, args.password)
        get_list = connection.remote_list()
        largedata = ""
        for each in get_list:
            largedata += each + "\n"
        send_largetext_udp_ahk(address, largedata, '<ftplist>')    


    elif client_req.startswith("<do_shutdown>"):
        updatelog("shutdown script by tcp command ..... ", True)
        updatelog("Stop tcp server", True)
        tcpsvr.stop()
        updatelog("Stop observer", True)
        ob.stop()
        updatelog("Stop gather timer", True)
        periodic.cancel_timer()
        updatelog("Stop delete old timer", True)
        deleteold.cancel_timer()
        updatelog("clear job queue..", True)
        jobs.force_quit()




def send_longtext_ahk_old(csocket, largedata):      # tcp reply for ahk.. depricated.....
    updatelog("replay to client", True)
    n = 400     # chunk length
    chunks = [largedata[i:i+n] for i in range(0, len(largedata), n)]
    byte_sent = 0
    csocket.send('<start_transfer>'.encode("utf-8"))
    for c in chunks:
        shortsleep(0.004)   # add 1ms delay for autohotkey's slow tcp processing....
        byte_sent += csocket.send(c.encode("utf-8"))
        #print(byte_sent, end=" ") # debugging !! check sent byte
    shortsleep(0.005)
    csocket.send('<finish_transfer>'.encode("utf-8"))
    print(f'byte sent = {byte_sent}')



def send_longtext_ahk(csocket, largedata):       # tcp reply for ahk.. depricated.....
    #print("replay to client")
    n = 100     # chunk length
    chunks = [largedata[i:i+n] for i in range(0, len(largedata), n)]
    chunks.append('\n<finish_transfer>')
    byte_sent = 0
    csocket.send('<start_transfer>'.encode("utf-8"))
    for c in chunks:
        #shortsleep(0.001)   # add 1ms delay for autohotkey's slow tcp processing....
        byte_sent += csocket.send(c.encode("utf-8"))
        #print(byte_sent, end=" ") # debugging !! check sent byte
        set_report_data("last_event", "byte_sent=" + str(byte_sent))  # Debugging !!
    updatelog(f'byte sent = {byte_sent}', True)


def get_media_list(path, filter = '*.mp4'):
    medialist = glob.glob(os.path.join(path, filter))
    medialist.sort(key=os.path.getmtime, reverse=True)
    result = ""
    for line in medialist:
        result += line + '\n'
    return result


def get_media_list_ext(path, filter = '*'):
    medialist = glob.glob(os.path.join(path, filter))
    medialist_new = [x for x in medialist if not get_name(x).startswith('WH16x9')]  # add cnn exception
    try:
        medialist_new.sort(key=os.path.getmtime, reverse=True)
    except Exception as e:
        updatelog(f'Error while sorting media list  {e}')
    new_list = [each + "|" + time.strftime('%Y%m%d %H%M%S', time.localtime(os.path.getmtime(each))) for each in medialist_new]
    result = ""
    for line in new_list:
        result += line + '\n'
    return result
    



class periodic_gather_encoding:
    def __init__(self, path_done, path_watch):
        self.done = path_done
        self.watch = path_watch
    
    def do_encoding(self):
        self.tmr = threading.Timer(300, self.do_encoding)
        self.tmr.name = "GATHER"
        self.tmr.start()
        set_report_data("last_gather", time.strftime("%m/%d %H:%M.%S"))
        
        list_missing = gather_missing_adv(self.done, self.watch)
        for media in list_missing:
            do_encoding(media)
        
        
        
    def cancel_timer(self):
        self.tmr.cancel()



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
        
    def remote_list(self):
        result = []
        try:
            f = ftplib.FTP(host = self.host, user = self.username, passwd = self.password, timeout = 4, encoding = 'utf-8')
            result = f.nlst()
            f.quit()
        except Exception as e:
            updatelog(f'Error while retrieve remote list files...  [{e}]', True)
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

def increase_queue_cycle():
    global jobs
    jobs.cycle_character()

def write_xml_job(this):
    global args
    root = ET.Element("SBS_MAM_Job_List")
    job = ET.SubElement(root, "SBS_MAM_Job")
    
    ET.SubElement(job, "Job_Creation_Time").text = str(int(time.time()))
    ET.SubElement(job, "Job_Type").text = "74"
    
    ET.SubElement(job, "Job_Src_Path_HR_Abs").text = this.outputfiles["mxf"]
    ET.SubElement(job, "Job_Src_Path_LR_Abs").text = this.outputfiles["pxy"]
    ET.SubElement(job, "Job_Src_Path_CAT_Abs").text = this.outputfiles["jpg1"]
    
    len_target = len(this.path_target)
    ET.SubElement(job, "Job_Src_Path_HR").text = this.outputfiles["mxf"][len_target:]
    ET.SubElement(job, "Job_Src_Path_LR").text = this.outputfiles["pxy"][len_target:]
    ET.SubElement(job, "Job_Src_Path_CAT").text = this.outputfiles["jpg1"][len_target:]
    ET.SubElement(job, "Job_Src_Path_AUDIO").text = this.outputfiles["aud"][len_target:]
    
    ET.SubElement(job, "Job_Dest_Path").text = '//nds/storage/international'
    ET.SubElement(job, "Job_Dest_Filename").text = '//nds/storage/international'
    ET.SubElement(job, "Job_OBJ_CATEGORY1").text = 'NDS'
    ET.SubElement(job, "Job_OBJ_CATEGORY2").text = 'INTERNATIONAL'
    ET.SubElement(job, "Job_OBJ_CATEGORY3").text = args.script
    
    try:
        with open(this.donefiles["mxf"], "r", encoding="utf-8") as s:
            line = s.readline()    # abandon first line
            line = s.readlines()
    except Exception as e:
        updatelog(f'Error while read script...   {e}', True)


    appdata = ET.SubElement(job, "Job_Src_App_Data")
    story = ET.SubElement(appdata, 'Story')
    story.tail = None

    for l in line:
        br = ET.SubElement(story, 'br')
        br.tail = l

    
    len_watch = len(this.path_watch)
    ET.SubElement(appdata, "OBJ_Origin_Abs").text = this.infile
    ET.SubElement(appdata, "OBJ_Origin").text = this.infile[len_watch:]
    ET.SubElement(appdata, "OBJ_Duration").text = str(this.duration)

    tree = ET.ElementTree(root)
    ET.indent(tree, '  ')
    tree.write(this.outputfiles['xml'], encoding='utf-8', xml_declaration=True)
    updatelog(f'Schedule File transfer {this.outputfiles["xml"]}', True)
    
    if args.transfer:
        do_transfer(this.infile)

def do_transfer(infile):
    global args, jobs
    for each in jobs.list_transfer:
        if infile in each.infile:
            updatelog(f'Requested file already exist in transfer queue... exit thread..   {infile}', True)
            return
    
    fps = full_path_set(args.target, args.done, args.watchfolder)
    fps.set_input(infile)
    
    job_mkdir = transfer(args.transfer, args.username, args.password)
    job_mkdir.schedule("mkdir", fps.outputfiles["ftp_folder"])
    jobs.list_transfer.append(job_mkdir)
    updatelog(f'Remote ftp mkdir scheduled.... {fps.outputfiles["ftp_folder"]}', True)
    
    job_transfer_mxf = transfer(args.transfer, args.username, args.password)
    job_transfer_mxf.schedule("send", fps.outputfiles["mxf"])
    jobs.list_transfer.append(job_transfer_mxf)
    updatelog(f'Transfer file scheduled.... {fps.outputfiles["mxf"]}', True)
    
    job_transfer_pxy = transfer(args.transfer, args.username, args.password)
    job_transfer_pxy.schedule("send", fps.outputfiles["pxy"], fps.outputfiles["ftp_folder"])
    jobs.list_transfer.append(job_transfer_pxy)
    updatelog(f'Transfer file scheduled.... {fps.outputfiles["pxy"]}, ftp path is {fps.outputfiles["ftp_folder"]}', True)
    
    job_transfer_cat = transfer(args.transfer, args.username, args.password)
    list_catalog = glob.glob(fps.outputfiles["proxy_folder"] + '/*.jpg')
    job_transfer_cat.schedule("sendlist", list_catalog, fps.outputfiles["ftp_folder"])
    jobs.list_transfer.append(job_transfer_cat)
    if len(list_catalog):
        updatelog(f'Transfer file list scheduled.... {list_catalog[0]}', True)
    
    job_transfer_audio = transfer(args.transfer, args.username, args.password)
    job_transfer_audio.schedule("send", fps.outputfiles["aud"], fps.outputfiles["ftp_folder"])
    jobs.list_transfer.append(job_transfer_audio)
    updatelog(f'Transfer file scheduled.... {fps.outputfiles["aud"]}', True)
    
    job_transfer_xml = transfer(args.transfer, args.username, args.password)
    job_transfer_xml.schedule("send", fps.outputfiles["xml"])
    jobs.list_transfer.append(job_transfer_xml)
    updatelog(f'Transfer file scheduled.... {fps.outputfiles["xml"]}', True)
    


def do_story_update(xml_story):     #  xml_story = [tm_stamp, path_xml]
    global args, jobs

    mediafile = ''
    scriptdata = ''

    try:
        path_xml = xml_story[1]
        sf = scriptfinder(args.watchfolder, args.script)
        mediafile = sf.search_media_files(path_xml)[-1]
        scriptdata = sf.get_script_data(path_xml).split('\n')
    except Exception as e:
        updatelog(f'Error while story processing.. {e} \n abort story update {path_xml}', True)
        return


    fs = full_path_set(args.target, args.done, args.watchfolder)
    fs.set_input(mediafile)

    if (mediafile and scriptdata and fs.check_donefiles() and os.path.isfile(path_xml)):
        root = ET.Element("SBS_MAM_Job_List")
        job = ET.SubElement(root, "SBS_MAM_Job")
        
        ET.SubElement(job, "Job_Creation_Time").text = str(int(time.time()))
        ET.SubElement(job, "Job_Type").text = "34"
        
        ET.SubElement(job, "Job_Src_Path_HR_Abs").text = fs.outputfiles["mxf"]
        len_target = len(fs.path_target)
        ET.SubElement(job, "Job_Src_Path_HR").text = fs.outputfiles["mxf"][len_target:]
        
        appdata = ET.SubElement(job, "Job_Src_App_Data")
        story = ET.SubElement(appdata, 'Story')
        story.tail = None

        for l in scriptdata:
            br = ET.SubElement(story, 'br')
            br.tail = l

        len_watch = len(args.watchfolder)
        ET.SubElement(appdata, "OBJ_Origin_Abs").text = mediafile
        ET.SubElement(appdata, "OBJ_Origin").text = mediafile[len_watch:]
        ET.SubElement(appdata, "Script_Origin").text = path_xml
        tree = ET.ElementTree(root)
        ET.indent(tree, '  ')
        new_xmlfile = fs.get_story_update_xml(path_xml)
        tree.write(new_xmlfile, encoding='utf-8', xml_declaration=True)
        updatelog(f'Successfully write story update xml.. {new_xmlfile}', True)
        if args.transfer:
            job_update_xml = transfer(args.transfer, args.username, args.password)
            job_update_xml.schedule("send", new_xmlfile)
            jobs.list_transfer.append(job_update_xml)
            updatelog(f'Transfer xml update scheduled.... {new_xmlfile}', True)

    else:
        updatelog(f'abort story update... {path_xml}  // file (media or done or xml) not exist.. or fail parsing story', True)


for folder in ['done', 'debug', 'log']:
    try:
        os.mkdir(folder)
    except Exception as e:
        updatelog(e, True)


tick_start = time.time()

updatelog("start watch folder....", True)
jobs = queue()


updatelog("Parse command line...", True)
args = argparser()

for k in args.__dict__:
    if args.__dict__[k] is not None:
        updatelog(f'args.{k}   -- > {args.__dict__[k]}', True)


timeout_encoder = args.timeout
ur = udp_reporter("127.0.0.1", args.port + 2)       # Setup status reporter for local debug
set_report_data("pid", os.getpid())                 # Send pid information with script startup
ur.send()

sc = scriptfinder(args.watchfolder, args.script)

tcpsvr = tcp_svr_thread("0.0.0.0", int(args.port + 1))
tcpsvr.start()
tqdm.disable_tick = False  # Disable STDOUT single line tick time ceremony during tqdm progress...


if args.polling:
    ob = pollobservervfs()
else:
    ob = defaultobserver()

updatelog(f'Start up observer service..... polling is {args.polling}')
ob.start(args.watchfolder)

#path_done_report = args.done

updatelog(f'Watch folder is "{args.watchfolder}" / target is "{args.target}" / Encoder limit is {timeout_encoder} second', True)

deleteold = delete_old()
deleteold.add_path_age(args.done, 480)
deleteold.add_path_age(args.target, 72)
deleteold.add_path_age(os.path.join(os.getcwd(), 'debug'), 480)
#deleteold.do_delete()
deleteold.start_schedule(2)

set_report_data("tcpsvr", int(args.port + 1))

set_report_data("watch", args.watchfolder)
set_report_data("target", args.target)
set_report_data("script", args.script)

periodic = periodic_gather_encoding(args.done, args.watchfolder)
periodic.do_encoding()


try:
    while tcpsvr.running:
        time.sleep(0.1)
        jobs.run()
        jobs.run_transfer()
        ur.set_data("age", time.time() - tick_start)
        ur.set_data("thread", threading.enumerate())
        ur.set_data("len_enc-wai-upd-xfer", [len(jobs.list_process), len(jobs.list_xml), len(jobs.list_update), len(jobs.list_transfer)])
        ur.send()
except KeyboardInterrupt:
    updatelog(f'Main thread halted... by keyboardinterrupt', True)
    tcpsvr.stop()
    ob.stop()
    periodic.cancel_timer()
    deleteold.cancel_timer()
    jobs.force_quit()
    
    
except Exception as e:
    updatelog(f'Main thread halted... {e}', True)
#    for encoder in jobs.list_process:           # count running encoder, terminate aged encoder
#        if (encoder.status == "running"):
#            updatelog(f'Terminate encoder pid [{encoder.pid}]', True)
#            encoder.enc.terminate()
#            encoder.checkoutput = ''    # prevent from done file record...
#    for waiter in jobs.list_xml:
#        updatelog(f'Terminate waiter [{waiter.infile}]', True)
#        waiter.continue_waiter = 0

print("Exit script....")
