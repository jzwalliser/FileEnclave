#!/usr/bin/python3
import fuse
import subprocess
import os
import errno
import json
import collections
import argparse
import passwordutil
import sevenzipwrapper
import time

class SevenZipMemoryFuse(fuse.Operations):
    def __init__(self,mountpoint,archive,password,mount_filename=None,max_cache_size=20 * 1024 ** 2,open_file=False):
        start_time = time.time()
        self.archive = archive
        self.cache = collections.OrderedDict() #淘汰制缓存区
        self.password = None
        
        meta = self._load_json_from_7z("metadata") #元数据
        salt = meta["salt"]
        user_password = passwordutil.hash(password,salt)
        print(f"Maximum cache size: {max_cache_size}")
        print(f"Hashed user password: {user_password}")
        self.password = self._read_file("password",password=user_password).decode("utf-8")
        print(f"Loaded real password: {self.password}")
        self.chunks = meta["chunks"] #切块数量
        self.chunk_size = meta["chunk_size"] #切块大小
        original_meta = self._load_json_from_7z("original_metadata",password=user_password) #加密元数据
        self.size = original_meta["size"] #总大小
        self.mount_filename = original_meta["filename"] #原文件名
        self.max_cache = int(max_cache_size // self.chunk_size) #最多缓存切块数量
        self.time = [original_meta["atime"],original_meta["mtime"],original_meta["ctime"]]
        print(self.time)
        if mount_filename:
            self.mount_filename = mount_filename
        print("Done",time.time() - start_time)
        if open_file:
            subprocess.Popen(["open",mountpoint + "/" + self.mount_filename])
            print("Open",mountpoint + "/" + self.mount_filename)

    def _read_file(self,filename,password=None): #将文件解压到内存
        ret = sevenzipwrapper.read_file(self.archive,filename,password)
        if not ret:
            raise ValueError("Failed to read {filename}")
        return ret

    def _load_json_from_7z(self,name,password=None):
        content = self._read_file(name,password)
        return json.loads(content) #读取配置

    def _get_chunk(self,index): #获取切块
        if index in self.cache: #如果缓存了切块
            print(f"Read from Cache: {index}")
            chunk = self.cache.pop(index) #最近使用了该切块，把它移到末尾避免被淘汰
            self.cache[index] = chunk
            return chunk #返回切块内容

        if index >= self.chunks: #越界读取
            return b"" #啥都读不到

        print(f"Read from archive: {index}")
        print(f"Cache usage: {len(self.cache)}/{self.max_cache}")
        chunk = self._read_file(str(index),password=self.password) #未缓存切块，从压缩包中读取
        self.cache[index] = chunk #读取后，放入缓存

        if len(self.cache) > self.max_cache: #如果超过了缓存限制
            self.cache.popitem(last=False) #干掉最老的（即第一个）
            print(f"Cache full, deleted 1 chunk.")

        return chunk #返回读取到的切块

    # ---- FUSE ----

    def getattr(self,path,fh=None): #获取信息
        if path == '/':
            return dict(st_mode=0o40755,st_nlink=2)

        if path == '/' + self.mount_filename:
            return dict(st_mode=0o100644,st_nlink=1,st_size=self.size,st_atime=self.time[0],st_mtime=self.time[1],st_ctime=self.time[2])

        raise fuse.FuseOSError(errno.ENOENT)

    def readdir(self,path,fh):
        if path != '/':
            raise fuse.FuseOSError(errno.ENOENT)
        return ['.','..',self.mount_filename]

    def open(self,path,flags):
        if path != '/' + self.mount_filename:
            raise fuse.FuseOSError(errno.ENOENT)
        return 0

    def read(self,path,size,offset,fh): #读取文件
        if offset >= self.size: #越界读取
            return b"" #啥都读不到

        result = bytearray() #返回值的初始化
        while len(result) < size and offset < self.size: #返回值未到达指定大小且文件没有读完
            index = offset // self.chunk_size #定位到切块
            chunk_offset = offset % self.chunk_size #定位切块内部的偏移量

            chunk = self._get_chunk(index) #获取切块数据
            available = len(chunk) - chunk_offset #偏移量的后面还剩多少内容（假设文件完整）
            to_read = min(size - len(result),available) #实际可读的数据量（也可能是最后一个切块，大小不定，所以取小的）

            result.extend(chunk[chunk_offset:chunk_offset + to_read]) #把内容拼接起来
            offset += to_read #推进偏移量

        return bytes(result) #返回请求的数据

    def release(self,path,fh):
        return 0

    def statfs(self,path):
        stv = os.statvfs('.')
        return dict(f_bsize=stv.f_bsize,f_blocks=stv.f_blocks,f_bfree=stv.f_bfree,f_bavail=stv.f_bavail,f_files=stv.f_files,f_ffree=stv.f_ffree)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="File Decryptor")
    parser.add_argument("archive",help="The archive to decrypt")
    parser.add_argument("password",help="The password")
    parser.add_argument("mountpoint",help="The mountpoint")
    parser.add_argument("-f","--filename",help="The mount filename")
    parser.add_argument("-c","--cache_size",type=int,default=10 * 1024 * 1024,help="Cache size (bytes),default 10 * 1024 * 1024")
    parser.add_argument("-o","--open_file",action="store_true")

    args = parser.parse_args()
    try:
        fuse.FUSE(SevenZipMemoryFuse(args.mountpoint,args.archive,args.password,args.filename,args.cache_size,args.open_file),args.mountpoint,foreground=True,nothreads=True)
    except:
        sys.exit(1)
