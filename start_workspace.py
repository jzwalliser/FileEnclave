#!/usr/bin/python3
import os
import sevenzipwrapper
import getpass
import shutil
import sys

if os.popen("whoami").read() != "root\n":
    os.system("sudo python3 start_workspace.py")
    sys.exit()
    
os.system("mkdir -p /media/jzwalliser/RAMDisk")
os.system("mount -t tmpfs -o size=1024M,uid=0,gid=0,mode=777,x-gvfs-show=RamDisk tmpfs /media/jzwalliser/RAMDisk")
print("Created virtual disk.")

password = getpass.getpass("Enter password to extract config: ")

try:
    config = sevenzipwrapper.read_file("config.7z","config.json",password)
except:
    print("Wrong password. Now umounted virtual disk.")
    os.system("sudo umount -l /media/jzwalliser/RAMDisk")
    sys.exit()
    
file = open("/media/jzwalliser/RAMDisk/config.json","wb")
file.write(config)
file.close()

password = os.urandom(128)
config = os.urandom(128)
del password
del config

copylist = ["repair.py","creator_gui.py","creator.py","mounter.py","mounter_gui.py","passwordutil.py","preview.py","sevenzipwrapper.py"]
os.system("mkdir -p /media/jzwalliser/RAMDisk/files")
os.system("mkdir -p /media/jzwalliser/RAMDisk/mnt")

for i in copylist:
    shutil.copy(f"./{i}",f"/media/jzwalliser/RAMDisk/{i}")

for i in os.listdir("/media/jzwalliser/RAMDisk/"):
    os.system(f"chmod 777 /media/jzwalliser/RAMDisk/{i}")

try:
    input("Temporary workspace successfully set up. Press enter to destroy.")
except:
    pass
finally:

    print("Terminating Everything...")
    for i in copylist:
        os.popen(f"pkill {i.split()[0]}")
    
    os.system("ls /media/jzwalliser/RAMDisk/")
    os.system("umount -l /media/jzwalliser/RAMDisk")
    print("Check (After): ")
    os.system("ls /media/jzwalliser/RAMDisk/")
    os.system("pkill python3")

