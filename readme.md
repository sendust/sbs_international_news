SBS international news processor engine.

collect mp4 file from CNN, REUTER, APTN news agent


- transcoding to XDCAM MXF
- cataloging jpg sequence (with frame number)
- extract mp3 audio
- create proxy mp4 movie.



usage :

usage: watchfolder.py [-h] --watchfolder WATCHFOLDER --target TARGET [--done DONE] [--timeout TIMEOUT] [--maxenc MAXENC] --port PORT --script SCRIPT [--polling POLLING] [--transfer TRANSFER]
                      [--username USERNAME] [--password PASSWORD]

SBS Global News Processor by sendust  (2023, Media IT)

   Example)  python watchfolder.py --watchfolder "d:\download" --target "e:\done"

             For Full help ----
             python watchfolder.py --help

optional arguments:
  -h, --help            show this help message and exit
  --watchfolder WATCHFOLDER
                        path for watch folder
  --target TARGET       path for target folder
  --done DONE           path for done files
  --timeout TIMEOUT     Maxinum Encoder age
  --maxenc MAXENC       Maxinum Concurrent Encoder
  --port PORT           Engine status report port
  --script SCRIPT       Script type [reuter, aptn, cnn]
  --polling POLLING     set True if you want polling watch (CIFS)
  --transfer TRANSFER   FTP Transfer address.. ex) 10.10.108.2
  --username USERNAME   FTP username
  --password PASSWORD   FTP password
  
 
 
 example :
 
 python watchfolder.py --watchfolder e:\int_download --target f:\int_mxf_reuter --port 4000 --script reuter --transfer "10.40.254.51" --username "wire" --password "ndsnds00!"
  
 