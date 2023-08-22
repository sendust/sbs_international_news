import time, threading, os, sys
from pathlib import Path
import xml.etree.ElementTree as ET



def do_all_exist(this):
    print("All done files are detected...")


def make_xml_job(fp):
    root = ET.Element("SBS_MAM_Job_List")
    job = ET.SubElement(root, "SBS_MAM_Job")
    
    ET.SubElement(job, "Job_Creation_Time").text = str(int(time.time()))
    ET.SubElement(job, "Job_Type").text = "74"
    ET.SubElement(job, "Job_Src_Path_HR").text = fp.outputfiles["mxf"]
    ET.SubElement(job, "Job_Src_Path_LR").text = fp.outputfiles["pxy"]
    ET.SubElement(job, "Job_Src_Path_CAT").text = fp.outputfiles["jpg1"]
    ET.SubElement(job, "Job_Dest_Path").text = '//nds/storage/international'
    ET.SubElement(job, "Job_Dest_Filename").text = '//nds/storage/international'
    
    try:
        with open(fp.donefiles["mxf"], "rt", encoding="utf-8") as s:
            line = s.readline()    # abandon firest line
            line = s.readlines()
    except Exception as e:
        print("Error while read script...   ", e)

    story = "\n"
    for l in line:
        story += l
        
    story += "\n"    


    appdata = ET.SubElement(job, "Job_Src_App_Data")
    ET.SubElement(appdata, "STORY").text = story

    tree = ET.ElementTree(root)
    ET.indent(tree, '  ')
    tree.write(fp.outputfiles['xml'], encoding='utf-8', xml_declaration=True)



class full_path_set:     # Accept file list and chkeck all files are exist
    outputfiles = {}
    donefiles = {}
    infile = ''
    th = ''
    timeout = 3600
    
    def __init__(self, path_target, path_done):
        self.path_target = path_target
        self.path_done = path_done

    def set_input(self, infile):
        self.infile = infile
        nameonly = Path(infile).stem
        self.outputfiles["mxf"] = os.path.join(self.path_target, nameonly + ".mxf")
        self.outputfiles["pxy"] = os.path.join(self.path_target, nameonly, nameonly + ".mp4")
        self.outputfiles["xml"] = os.path.join(self.path_target, nameonly + ".xml")
        self.outputfiles["jpg"] = os.path.join(self.path_target, nameonly, f'{nameonly}_%05d.jpg')
        self.outputfiles["jpg1"] = os.path.join(self.path_target, nameonly, f'{nameonly}_00001.jpg')
        self.outputfiles["proxy_folder"] = os.path.join(self.path_target, nameonly)
        self.donefiles["mxf"] = os.path.join(self.path_done, os.path.basename(infile) + ".mxf__done")
        self.donefiles["pxy"] = os.path.join(self.path_done, os.path.basename(infile) + ".prox_done")
        self.donefiles["cat"] = os.path.join(self.path_done, os.path.basename(infile) + ".cata_done")
        
    def start_done_waiter(self, timeout = 300):
        self.tm_start = time.time()
        self.timeout = timeout
        self.th = threading.Thread(target=self.run, daemon=True, name="done_waiter")
        self.th.start()
        
    def run(self):
        continue_run = True
        while continue_run:
            result = True
            for k in self.donefiles:
                result *= os.path.isfile(self.donefiles[k])

            if result:
                continue_run = False
                make_xml_job(self)
                print(f'Done file all exist... exit waiter daemon --> {self.infile}')
            else:
                time.sleep(2)

            
fs = full_path_set("F:\\int_mxf_aptn", os.path.join(os.path.dirname(__file__), 'done'))
fs.set_input("E:\\aptn_download/4433897_US TX Protest Shooting Court_0_1080i60ESSENCE--31d55.mp4")


print(fs.infile)
for key in fs.outputfiles:
    print(key, fs.outputfiles[key])


for key in fs.donefiles:
    print(key, fs.donefiles[key])


fs.start_done_waiter()


try:
    while True:
        print(time.time())
        print(threading.enumerate())
        time.sleep(1)


except Exception as e:
    print(e)