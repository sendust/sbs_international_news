import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import glob, os

def get_name(f):
    head, tail = os.path.split(f)
    return tail
    
    
list_xml = glob.glob(r'E:\aptn_download\*.xml')
list_mp4 = glob.glob(r'E:\aptn_download\*.mp4')


list_xml_parsed = []

def test2():
    for f in list_xml:
        parser = get_name(f).split('_')
        list_xml_parsed.append(parser)
        print(parser)

    print('-' * 80)

def test():
    for f in list_mp4:
        parser_mp4 = get_name(f).split('_')
        print(parser_mp4)
        key_mp4 = parser_mp4[5][5:-4] + '.XML'
        print(key_mp4)
        for x in list_xml_parsed:
            if key_mp4 in x:
                print(x)
        print('\r\n')


def find_script_reuter(infile):
    key = get_name(infile).split('_')[-1][5:-4] + '.XML'
    sclist = glob.glob(os.path.join(r'E:\int_download', '*' + key))
    sclist.sort()
    if sclist:
        return sclist[-1]   # Last last version of script
    else:
        return ''


infile = r'E:\int_download\2023-04-27T022304Z_1_LWD815527042023RP1_RTRWNEV_D_8155-USA-WEATHER-HAIL-UGC.MP4'

            
            

class scriptfinder:
    watchpath = ""
    tree = ""
    root = ""
    file_script = ""
    text_script = ""
    mode = "reuter"
    

    
    def __init__(self, watchpath, mode = "reuter"):      # init with watch folder
        self.watchpath = watchpath
        self.mode = mode

    def search_script_file(self, infile):      # in file is mp4 (video media)
        dict_search_script_file = {'reuter': self.search_script_file_reuter, 'aptn' : self.search_script_file_aptn}
        return dict_search_script_file[self.mode](infile)
        
    def get_script_data(self, infile = ''):   # in file is xml
        dict_get_script_date = {'reuter': self.get_script_data_reuter, 'aptn' : self.get_script_data_aptn}
        return dict_get_script_date[self.mode](infile)



    def search_script_file_reuter(self, infile):   # infile is mp4
        key = get_name(infile).split('_')[-1][5:-4] + '.XML'
        sclist = glob.glob(os.path.join(self.watchpath, '*' + key))
        sclist.sort()
        if sclist:
            self.file_script = sclist[-1]   # return last version of script
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
        xlist = glob.glob(os.path.join(self.watchpath, id + '*_script.xml'))
        xlist.sort()
        if xlist:
            self.file_script = xlist[-1]
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
        

sf = scriptfinder(r'E:\aptn_download', 'aptn')


for f in list_mp4:
    print('-' * 40)
    print(f)
    x = sf.search_script_file(f)
    print(x)
    print(sf.get_script_data(x))



def reuter_sc_good():
    for mp4 in list_mp4:
        xmlfile = sf.search_script_file(mp4)
        print('-' * 40)
        print(xmlfile)
        if xmlfile:
            print(sf.get_script_data())





def travel2():
    for child  in root:
        print(child.tag, child.attrib)




def travel():
    for el in root:
        print(el)
        print('-' * 20)
        for item in el:
            print('+' * 20)
            for val in item:
                print(val)

print('0' * 20)    
def findsome():
    for cset in root.iter('{http://iptc.org/std/nar/2006-10-01/}contentSet'):
        print(cset)
        for element in cset:
            print(element.tag)
            if element.tag == '{http://iptc.org/std/nar/2006-10-01/}inlineXML':
                print("Found script !!!")
                print(element.attrib)

    
