import passwordutil
import sevenzipwrapper
import json
import argparse
import os

parser = argparse.ArgumentParser(description="Archive Data Editor")
parser.add_argument("archive",help="The archive file that you wish to edit")
parser.add_argument("password",help="Password to the archive")
parser.add_argument("data",help="The data you wish to edit")
parser.add_argument("new",help="New value")
parser.add_argument("-r","--recovery",type=int,default=0,help="Generate recovery data using par, choose a number between 0~100")

args = parser.parse_args()

archive = args.archive
password = args.password
new = args.new
data = args.data
rec = args.recovery

salt = json.loads(sevenzipwrapper.read_file(archive,"metadata"))["salt"]
user_password = passwordutil.hash(password,salt)
file_password = sevenzipwrapper.read_file(archive,"password",user_password)
original_metadata = sevenzipwrapper.read_file(archive,"original_metadata",user_password)

if data == "password" or data == "pass":
    password = new
else:
    meta = json.loads(original_metadata)
    if args.new != "":
        meta[args.data] = eval(args.new)
    else:
        meta.pop(args.data,None)
    original_metadata = json.dumps(meta).encode("utf-8")

sevenzipwrapper.write_file(archive,"password",file_password,passwordutil.hash(password,salt))
sevenzipwrapper.write_file(archive,"original_metadata",original_metadata,passwordutil.hash(password,salt))
os.system(f"rm {archive}.*")
if rec:
    os.system(f"par2 create -n1 -r{rec} {archive}")
