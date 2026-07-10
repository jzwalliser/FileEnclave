#!/usr/bin/python3
import subprocess
import io
import math
import json
import os
import argparse
import preview
import passwordutil
import sys
import sevenzipwrapper

parser = argparse.ArgumentParser(description="Archive Creator")
parser.add_argument("input",help="Input file that needs to be sliced and archived")
parser.add_argument("output",help="Output filename")
parser.add_argument("password",help="Password")
parser.add_argument("-c","--chunk_size",type=int,default=2 * 1024 * 1024,help="Chunk size (bytes),default 2 * 1024 * 1024")
parser.add_argument("-y","--yes",action="store_true",help="Skip all questions with yes")
parser.add_argument("-r","--recovery",type=int,default=0,help="Generate recovery data using par, choose a number between 0~100")
parser.add_argument("-m","--metadata",help="Additional metadatas to append in json format")
args = parser.parse_args()

salt = passwordutil.rand() #盐
src = args.input #输入文件
output = args.output #输出文件
user_password = passwordutil.hash(args.password,salt) #用户密码的派生
chunk_size = args.chunk_size #分块大小
file_password = passwordutil.rand(64) #获取随机秘钥
skip_questions = args.yes
recovery = args.recovery
additional_meta = args.metadata
print(args.metadata)

stats = os.stat(src) #信息
size = stats.st_size
chunks = math.ceil(size / chunk_size) #总切块个数

if os.path.exists(output): #检测覆写
    answer = "y"
    if not args.yes:
        answer = input(f"File \"{output}\" already exists. Overwrite? [y/n]")
    if answer.lower() in ["y","yes"]:
        os.remove(output)
    else:
        sys.exit() #用户拒绝覆写，退出

sevenzipwrapper.write_file(output,"password",file_password.encode("utf-8"),user_password) #加入秘钥，用用户派生秘钥加密
sevenzipwrapper.write_file(output,"preview",preview.preview(src),file_password) #加入预览，用随机秘钥加密
metadata = {"chunks": chunks,"chunk_size": chunk_size,"salt":salt} #元数据
sevenzipwrapper.write_file(output,"metadata",json.dumps(metadata).encode("utf-8")) #加入元数据，不加密

original_metadata = {"size": size,"filename":src.split("/")[-1],"atime":stats.st_atime,"ctime":stats.st_ctime,"mtime":stats.st_mtime} #加密元数据
if additional_meta:
    original_metadata = original_metadata | json.loads(additional_meta)
sevenzipwrapper.write_file(output,"original_metadata",json.dumps(original_metadata).encode("utf-8"),user_password) #加密元数据


with open(src,"rb") as f: #打开文件
    for i in range(chunks): #分块
        chunk = f.read(chunk_size) #分块读取
        if not chunk: #读到尾了
            break #结束循环
        print(i)
        sevenzipwrapper.write_file(output,f"{i}",chunk,file_password) #加入切块，用随机秘钥加密


print(f"Done creating encrypted archive: {output}")
#print(file_password)
if recovery:
    os.system(f"par2 create -n1 -r{recovery} {output}")
