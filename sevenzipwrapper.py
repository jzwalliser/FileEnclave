#!/usr/bin/python3
import subprocess

def read_file(archive,filename,password=None):
    cmd = ["7z","e",archive,"-so",filename] #命令模板
    if password: #存在密码
        cmd.insert(2,"-p" + password) #则在命令中加入密码

    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE) #执行命令
    data = proc.stdout.read() #读取结果
    proc.wait() #等待执行完毕
    if proc.returncode != 0: #非正常退出
        raise RuntimeError(f"Error opening {archive}, perhaps you provided a wrong password?") #抛错
    return data #返回读取到的内容

def write_file(archive,filename,data,password=None):
    cmd = ["7z","a","-t7z",archive,"-si" + filename,"-mhe=off"]
    if password:
        cmd.insert(3,"-p" + password)
    subprocess.run(cmd,input=data,check=True) #加入秘钥，用用户派生秘钥加密

