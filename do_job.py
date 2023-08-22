import time, sys, os, subprocess



if (len(sys.argv) >= 2):
    filename = sys.argv[1]
else:
    print("Usage..... \r\n python do_job.py file_fullpath")
    sys.exit(0)




print(f"input file name is {filename}")

if os.path.isfile(filename):
    print("input is file.. continue processing..")
else:
    print("input is not file or exist.. terminate script")
    sys.exit(1)


for i in range(5):
    subprocess.Popen("ffmpeg.exe -f lavfi -i testsrc2=d=300 -f sdl out")
    subprocess.Popen("ffmpeg.exe -f lavfi -i testsrc=d=300 -f sdl out")

print(f"Finish transcoding ....")

