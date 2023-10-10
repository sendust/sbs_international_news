import subprocess

inputfile = r'E:\cnn_download\BHDP_MW-007SU_WI_ ST CROIX CO_ DEPU_CNNA-ST1-200000000004e77a_175_0.mp4'


def get_duration(inputfile):
    p = subprocess.run(f'ffprobe.exe -show_streams "{inputfile}"', stdout = subprocess.PIPE, stderr=subprocess.PIPE)

    result = p.stdout.decode()
    result = result.split("\n")
    print(result)
    duration = 9999999999999.9
    for line in result:
        pair = line.split("=")
        if (pair[0] == "duration"):
            duration_probe = float(pair[1])
            if (duration_probe < duration):
                duration = duration_probe
    print(f"Input file duration is {duration}  seconds")
    return duration

get_duration(inputfile)