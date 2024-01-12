title CNN news processor. by sendust
timeout /t 2
:begin
rem python.exe  watchfolder.py --watchfolder D:\agent_CNN --target E:\output_cnn --port 50031 --script cnn  --transfer "10.40.24.121" --username "wire" --password "ndsnds00!"
python.exe  watchfolder.py --watchfolder D:\agent_CNN --target E:\output_cnn --port 50031 --script cnn  --transfer "10.40.28.101" --username "wire" --password "ndsnds00!"
goto begin
pause

 