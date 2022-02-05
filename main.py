# -*- coding: utf-8 -*-
import re
import os
from time import time, sleep, strftime, localtime
from psutil import net_io_counters


project_path = re.sub(r'\\', "/", os.path.abspath('.'))
pattern_url = r'http[a-zA-Z0-9\:\/\.\-]+'
pattern_ts_key = r'[a-zA-z0-9]+\.(key|ts)'
pattern_ts_key_only = r'^[a-zA-z0-9]+\.(key|ts)$'


class NetIOMonitor:
    def __init__(self):
        self.counter = net_io_counters().bytes_recv
        self.stamp = time()

    def GetSpeed(self):
        speed = round((net_io_counters().bytes_recv - self.counter) / (time() - self.stamp))
        self.counter = net_io_counters().bytes_recv
        self.stamp = time()
        return str(speed/1000) + "KB/s"


def DownloadM3U8(url):
    file_name = "index.m3u8"
    result = os.system("wget -U NoBrowser -O " + project_path + "/temp/m3u8/" + file_name + " -q " + url)
    stamp = int(time())
    while 1:
        if result == 0:
            print("[INFO] Original .m3u8 file downloaded successfully.")
            url_header = url[0:0 - len(url.split("/")[-1])]
            file_path = FormatM3U8(project_path + "/temp/m3u8/" + file_name, url_header, "formatted.m3u8")
            return file_path
        if int(time()) - stamp > 60:
            print("[ERROR] Failed to download original .m3u8 file.")
            break
        sleep(1)
    return None


def FormatM3U8(m3u8_file, url_header, new_name):
    file_path = project_path + "/temp/m3u8/" + new_name
    fo = open(file_path, "w")
    with open(m3u8_file, 'r') as f:
        while True:
            line = f.readline()
            if not line:
                break
            target = re.search(pattern_ts_key, line, flags=0)
            if target is not None:
                if re.search(pattern_url, line, flags=0) is not None:  # complete .key/.ts url
                    var = None
                elif re.search(pattern_ts_key_only, line, flags=0) is not None:  # incomplete .ts url
                    line = url_header + line
                elif "#EXT-X-KEY" in line:  # incomplete .key url
                    temp = line.split(target.group())
                    temp.insert(1, url_header + target.group())
                    line = "".join(temp)
                else:  # unexpected situation
                    print("[ERROR] Unexpected situation happened in function \'FormatM3U8\'")
            fo.write(line)
    return file_path


def LocalizeM3U8(m3u8_file, ts_path, new_name):
    file_path = project_path + "/temp/m3u8/" + new_name
    fo = open(file_path, "w")
    with open(m3u8_file, 'r') as f:
        while True:
            line = f.readline()
            if not line:
                break
            target = re.search(pattern_ts_key, line, flags=0)
            if target is not None:
                line = re.sub(pattern_url, ts_path + target.group(), line)
            fo.write(line)
    return file_path


def GetDownloadList(m3u8_file):
    url_list = []
    with open(m3u8_file, 'r') as f:
        while True:
            line = f.readline()
            if not line:
                break
            url = re.search(pattern_url, line, flags=0)
            if url is not None:
                url_list.append(url.group())
    return url_list


def DownloadVideos(download_list):
    path = project_path + "/temp/ts/"
    monitor = NetIOMonitor()
    print("[INFO] Downloading...")
    for item in download_list:
        result = os.system("wget -U NoBrowser -q -P " + path + " " + item)
        stamp = int(time())
        while 1:
            if result == 0:
                process_bar(len(os.listdir(path)) / len(download_list), start_str='', end_str=monitor.GetSpeed(),
                            total_length=15)
                break
            if int(time()) - stamp > 300:
                break
    print("[INFO] Video has been downloaded successfully.")
    return path


def AES128_Decode(m3u8_file, ts_path):
    local_file = LocalizeM3U8(m3u8_file, ts_path, "local.m3u8")
    video_name = strftime("%Y_%m_%d_%H_%M_%S", localtime()) + ".mp4"
    os.popen("ffmpeg -allowed_extensions ALL -i " + local_file + " -c copy " + project_path + "/video/" + video_name)
    stamp = int(time())
    while 1:
        file_list = os.listdir(project_path + "/video/")
        if video_name in file_list:
            print("[SUCCESS] Video has been generated, path: " + project_path + "/video/" + video_name)
            return 0
        if int(time()) - stamp > 60:
            break
    print("[ERROR] Failed to generate video.")
    return -1


def ResetTempFile():
    folder_path = [project_path + "/temp/", project_path + "/temp/ts/", project_path + "/temp/m3u8/",
                   project_path + "/video/"]
    for path in folder_path:
        if not os.path.exists(path):
            os.mkdir(path)
    file_list = os.listdir(project_path + "/temp/ts/")
    for item in file_list:
        os.remove(project_path + "/temp/ts/" + item)


def process_bar(percent, start_str='', end_str='', total_length=0):
    bar = ''.join(["\033[31m%s\033[0m" % '   '] * int(percent * total_length)) + ''
    bar = '\r' + start_str + bar.ljust(total_length) + ' {:0>4.1f}%|'.format(percent * 100) + end_str
    print(bar, end='', flush=True)


if __name__ == '__main__':
    ResetTempFile()
    url = input("Please input link of .m3u8 file: ")
    file_path = DownloadM3U8(url)
    if file_path is not None:
        download_list = GetDownloadList(file_path)
        ts_path = DownloadVideos(download_list)
        result = AES128_Decode(file_path, ts_path)
    else:
        print("[ERROR] Failed to download m3u8 file")
    var = input("Press [ENTER] to exit.")
