import os, glob, time


def get_media_list_ext(path, filter = '*'):
    medialist = glob.glob(os.path.join(path, filter))
    medialist.sort(key=os.path.getmtime, reverse=True)
    new_list = [each + "|" + time.strftime('%Y%m%d %H%M%S', time.localtime(os.path.getmtime(each))) for each in medialist]
    result = ""
    for line in new_list:
        result += line + '\n'
    return result
    
    
l = get_media_list_ext("E:/int_download", "*.mp4")
print(l)




