import ftplib

ftp = ftplib.FTP("10.40.254.51")
ftp.login("wire", "ndsnds00!")

#data = ftp.nlst()
data = []
ftp.dir(data.append)    
ftp.quit()
print(len(data))

for i in range(0, 10):
    print(data[i])


#for each in data:
    #print(each)