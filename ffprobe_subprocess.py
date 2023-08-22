import subprocess

inputfile = "E:/int_download/2023-04-21T053305Z_1_LWD677021042023RP1_RTRWNEV_D_6770-SUDAN-POLITICS-BURHAN.MP4"


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

