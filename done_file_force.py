import time, threading, os, datetime, glob

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

def get_done_file_set(infile, path_done_report):
    dlist = {}
    dlist["mxf"] = os.path.join(path_done_report, os.path.basename(infile) + ".mxf__done")
    dlist["pxy"] = os.path.join(path_done_report, os.path.basename(infile) + ".prox_done")
    dlist["cat"] = os.path.join(path_done_report, os.path.basename(infile) + ".cata_done")
    return dlist
    
    
    
def gather_missing(path_done, path_watch):
    updatelog(f'.... collect mp4 file list.... from path {path_watch}')
    list_watch = glob.glob(path_watch + '/*.mp4')
    nameonly_done = []
    list_missing = []


    for f in list_watch:
        nameonly_watch = os.path.basename(f)
        if nameonly_watch.startswith("WH16x9"):     # CNN exception (skip proxy)
            continue
        done_mxf = os.path.join(path_done, nameonly_watch + '.mxf__done')
        done_pxy = os.path.join(path_done, nameonly_watch + '.prox_done')
        done_cat = os.path.join(path_done, nameonly_watch + '.cata_done')
        result = os.path.isfile(done_mxf) and os.path.isfile(done_pxy) and os.path.isfile(done_cat)
        if not result:
            list_missing.append(f)
    updatelog(f'---- Missing file list ----')
    for m in list_missing:
        updatelog(get_name(m))
    updatelog(f'Number of missing file = {len(list_missing)}')
    return list_missing

l = gather_missing('E:/sbsint/done', 'z:/')

for f in l:
    print(f)
    dlist = get_done_file_set(f, 'E:/sbsint/done')
    for key in dlist:
        with open(dlist[key], "w") as done:
            done.write("CNN dummy done file..")