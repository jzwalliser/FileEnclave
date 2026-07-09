#!/usr/bin/python3
import os
import json
import subprocess
import argparse

parser = argparse.ArgumentParser(description="File Repair")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-d","--directory",help="Repair the whole directory")
group.add_argument("-f","--file",help="Repair only a single file")
args = parser.parse_args()

def repair(file):
    message = {0:"[+] Repair Ok",2:"[!] Repair failed",3:"[~] No recovery files found"}
    proc = subprocess.Popen(f"par2 repair {file}",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) #执行命令
    proc.wait() #等待执行完毕
    #print(proc.stdout.read(),proc.returncode)
    return message[proc.returncode] + ": " + file

if args.directory:
    archive_dir = args.directory
    for i in os.listdir(archive_dir):
        if i.endswith(".7z"):
            print(repair(f"{archive_dir}/{i}"))
else:
    print(repair(args.file))
    
