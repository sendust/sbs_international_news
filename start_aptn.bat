title APTN news processor.. by sendust
timeout /t 1
:begin
rem python.exe  watchfolder.py --watchfolder D:\agent_APTN --target E:\output_aptn --port 50021 --script aptn   --transfer "10.40.24.121" --username "wire" --password "ndsnds00!"
python.exe  watchfolder.py --watchfolder D:\agent_APTN --target E:\output_aptn --port 50021 --script aptn   --transfer "10.40.28.101" --username "wire" --password "ndsnds00!"
goto begin
pause
 