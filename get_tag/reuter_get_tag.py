import glob
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup





def get_tag_reuter(infile):
    tree = ET.parse(infile)
    root = tree.getroot() 
    tag = ''
    #print("subject.... ++++++++++++")
    for child in root.iter("{http://iptc.org/std/nar/2006-10-01/}subject"):
        for each in child.iter():
            if each.text:
                if (ord(each.text[0]) - 10):     # begin character is not '\n'
                    #print("#"  + each.text.strip())
                    tag += "#" + each.text.strip()

    #print("keyword.... ++++++++++++")
    for child in root.iter("{http://iptc.org/std/nar/2006-10-01/}keyword"):
        #print(child.tag)
        for each in child.iter():
            if each.text:
                #print("#" + each.text.strip())
                tag +=  "#" + each.text.strip()
    
    return tag


def get_tag_aptn(infile):
    tree = ET.parse(infile)
    root = tree.getroot()
    #for each in root.iter():
    #    print(each.tag)
    tag = ''
    for child in root.iter("{http://iptc.org/std/nar/2006-10-01/}subject"):
        for each in child.iter():
            if each.text:
                if (ord(each.text[0]) - 10):     # begin character is not '\n'
                    #print("#" + each.text.strip())
                    tag += "#" + each.text.strip()

    return tag





def get_tag_cnn(infile):
    return "#---------"



def get_script_data_aptn(infile = ''):   # in file is xml, get from *-item.xml file (2023/11/20)
    text_script = ''
    if not infile:
        self.text_script =  "Error finding script data.... xml file not given"
    try:
        with open(infile, encoding='utf-8') as fp:
            tree = ET.parse(infile)
            root = tree.getroot()
            for each in root.iter('{http://iptc.org/std/NITF/2006-10-18/}p'):
                if each.text:
                    text_script += each.text + "\n"
    except:
        text_script = "Error finding script data......"
    return text_script


def get_script_data_cnn(infile = ''):   # in file is xml, get from *-item.xml file (2023/11/20)
    text_script = ''
    if not infile:
        self.text_script =  "Error finding script data.... xml file not given"
    try:
        with open(infile, encoding='utf-8') as fp:
            tree = ET.parse(infile)
            root = tree.getroot()
            for each in root.iter('category'):
                if each.text:
                    text_script += each.text + "\n"
    except:
        text_script = "Error finding script data......"
    return text_script





infile = 'PO-09FR_IL_ MIGRANTS IN CHICA_CNNA-ST1-200000000005c342_900_0.xml'


tree = ET.parse(infile)
root = tree.getroot()
#for each in root.iter():
#    print(each.tag)
tag = ''
#print("subject.... ++++++++++++")

for each in root.iter():
    if each.text:
        print(each.tag, end = " -->  ")
        print(each.text)

print("---------------------------------------------")

print(get_script_data_cnn(infile))

