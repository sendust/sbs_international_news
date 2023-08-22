title CNN news processor. by sendust
timeout /t 2
:begin
python watchfolder.py --watchfolder z:\ --target f:\int_mxf_cnn --port 21000 --script cnn --polling True  --transfer "10.40.254.51" --username "wire" --password "ndsnds00!"
goto begin
pause

 