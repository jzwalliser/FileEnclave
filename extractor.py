import os
import argparse
import sevenzipwrapper
import json
import passwordutil

parser = argparse.ArgumentParser(description="Archive Extractor")
parser.add_argument("archive",help="The archive file that you wish to extract")
parser.add_argument("password",help="Password to the archive")
parser.add_argument("directory",help="Output directory")
parser.add_argument("-f","--filename",default=None,help="Renames the file if specified")

args = parser.parse_args()

user_password = args.password
archive = args.archive
output_dir = args.directory
output_name = args.filename

meta = json.loads(sevenzipwrapper.read_file(archive,"metadata"))
salt = meta["salt"]
chunk_num = meta["chunks"]
user_pwd = passwordutil.hash(user_password,salt)
file_pwd = sevenzipwrapper.read_file(archive,"password",password=user_pwd).decode("utf-8")
original_meta = json.loads(sevenzipwrapper.read_file(archive,"original_metadata",user_pwd).decode("utf-8"))
filename = original_meta["filename"]

if not output_name:
    output_name = filename

fileobj = open(os.path.join(output_dir,output_name),"wb")
for i in range(chunk_num):
    fileobj.write(sevenzipwrapper.read_file(archive,str(i),file_pwd))

fileobj.close()
