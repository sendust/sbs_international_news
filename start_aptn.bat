title APTN news processor.. by sendust
timeout /t 1
:begin
"C:\Users\develop\miniconda3\python.exe"  watchfolder.py --watchfolder e:\aptn_download --target f:\int_mxf_aptn --port 7890 --script aptn   --transfer "10.40.254.51" --username "wire" --password "ndsnds00!"
goto begin
pause
 