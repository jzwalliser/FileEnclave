#!/usr/bin/python3
import tkinter
import tkinter.messagebox
import tkinter.filedialog
import dataclasses
import hashlib
import json
import subprocess
import os
import tkinterdnd2
import ttkbootstrap
import preview
import PIL
import PIL.Image
import PIL.ImageTk
import io
import threading
import shared
import sys
import argparse
import gettext

gettext.bindtextdomain("creator_gui","./locale")
gettext.textdomain("creator_gui")
_ = gettext.gettext

class Tk(ttkbootstrap.Window,tkinterdnd2.TkinterDnD.Tk): #混合ttkbootstrap和tkinterdnd
    pass

rec_percentage = 0 #恢复量（百分比）
chunk_size = 2079152 #单个切片大小
tags = [] #标签
path = "./" #当前路径
password = "" #密码
file_path = None #被加载的文件
edit_mode = False #标签修改模式
column = 5 #每行标签数
tag_buttons = []

try:
    with open("config.json","rb") as conf:
        config = json.loads(conf.read().decode("utf-8")) #读取配置文件
except Exception:
    pass
else:
    rec_percentage = config.get("rec",rec_percentage)
    chunk_size = config.get("chunk_size",chunk_size)
    tags = config.get("tags",tags)
    path = config.get("creator_path",path)
    password = config.get("password",password)

def on_drop(event): #拖拽
    global file_path
    global tk_img
    file_path = event.data.strip().strip("{}")
    drop_label.config(text=f"{file_path}",fg="green")
    img = PIL.Image.open(io.BytesIO(preview.preview(file_path))) #加载预览图
    img = img.resize((480,270)) #调整预览图大小
    tk_img = PIL.ImageTk.PhotoImage(img) #加载成tkinter格式
    preview_pic.configure(image=tk_img) #贴到界面上

def sha1_md5(file_path): #计算文件名
    with open(file_path,"rb") as f:
        sha1 = hashlib.sha1(f.read()).hexdigest()
    return hashlib.md5(sha1.encode("utf-8")).hexdigest()

def run_cmd(cmd): #运行命令
    try:
        proc = subprocess.run(cmd,check=True)
    except subprocess.CalledProcessError as e:
        err = e
    else:
        err = None
    finally:
        root.after(0,on_finish,err)

def on_finish(err): #运行命令结束调用
    run.configure(state=tkinter.NORMAL)
    if err:
        run.configure(bootstyle=ttkbootstrap.constants.DANGER)
        tkinter.messagebox.showerror(_("Failed"),str(err))
        root.after(3000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
    else:
        run.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
        tkinter.messagebox.showinfo(_("Success"),_("File encrypted."))
        root.after(1000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))

def run_creator(): #创建加密压缩包
    global file_path
    if not file_path or not os.path.exists(file_path):
        run.configure(bootstyle=ttkbootstrap.constants.WARNING)
        tkinter.messagebox.showwarning(_("File"),_("Please add a file."))
        root.after(1000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        return

    if not user_password_var.get():
        run.configure(bootstyle=ttkbootstrap.constants.WARNING)
        tkinter.messagebox.showwarning(_("Password"),_("Please set a password."))
        root.after(1000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        return

    try:
        output_hash = sha1_md5(file_path)
    except Exception as e:
        run.configure(bootstyle=ttkbootstrap.constants.DANGER)
        tkinter.messagebox.showerror(_("Hash error"),str(e))
        root.after(3000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        return

    tags_raw = tags_var.get().strip()
    tags_list = [t.strip() for t in tags_raw.split() if t.strip()]
    tags_json = ",".join(f'"{t}"' for t in tags_list)

    cmd = ["python3","creator.py",file_path,f"{path}/{output_hash}.7z",user_password_var.get(),"-y","-m",f'{{"tags":[{tags_json}],"folder":"{virtual_directory_var.get()}"}}',"-c",str(calc_size(chunk_size_entry.current(),chunk_size_entry.get()))]
    print(cmd)
    
    if rec_percentage != 0:
        print("rec")
        cmd += ["-r",str(rec_percentage)]
    run.configure(state=tkinter.DISABLED)
    threading.Thread(target=run_cmd,args=[cmd],daemon=True).start()

def edit():
    global edit_mode
    if edit_mode:
        edit_mode = False
        edit_tags.configure(text=_("Edit tags"),bootstyle=ttkbootstrap.constants.PRIMARY)
        tag_append.grid_forget()
    else:
        edit_mode = True
        edit_tags.configure(text=_("Finish (Right click to delete tag)"),bootstyle=ttkbootstrap.constants.SUCCESS)
        tag_append.grid(row=len(tag_buttons) // column,column=len(tag_buttons) % column,padx=5,pady=5,sticky=tkinter.W)

def user_add(event):
    tag_name = tag_append.get()
    for i in tag_name.split():
        continue_flag = False
        for j in tag_buttons:
            if j["text"] == i:
                j.configure(bootstyle=(ttkbootstrap.constants.INFO,ttkbootstrap.constants.OUTLINE))
                root.after(1000,lambda btn=j: j.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
                root.after(1500,tag_highlighter)
                continue_flag = True
                break
        if continue_flag:
            continue
        add_tag(i)
        tag_append.grid(row=len(tag_buttons) // column,column=len(tag_buttons) % column,padx=5,pady=5,sticky=tkinter.W)
        tag_append.delete(0,tkinter.END)
        tag_highlighter()

def del_tag(event,tag):
    if not edit_mode:
        return
    for i in tag_buttons:
        print(i["text"],tag)
        if i["text"] == tag:
            tag_buttons.remove(i)
            i.grid_forget()
            break
    for i in range(len(tag_buttons)):
        tag_buttons[i].grid(row=i // column,column=i % column,padx=5,pady=5,sticky=tkinter.W)
    tag_append.grid(row=len(tag_buttons) // column,column=len(tag_buttons) % column,padx=5,pady=5,sticky=tkinter.W)

def insert_tag(tag):
    current = tags_var.get().strip()
    if tag in current.split():
        temp = current.split()
        temp.remove(tag)
        tags_var.set(" ".join(temp))
        return
    if current and not current.endswith(" "):
        tags_var.set(current + " " + tag)
    else:
        tags_var.set(current + tag)

def add_tag(tag):
    global tag_buttons
    if tag == "":
        return
    tag_button = ttkbootstrap.Button(frame_buttons,text=tag,width=8,command=lambda t=tag: insert_tag(t))
    tag_button.grid(row=len(tag_buttons) // column,column=len(tag_buttons) % column,padx=5,pady=5,sticky=tkinter.W)
    tag_button.bind("<Button-3>",lambda event,t=tag: del_tag(event,t))
    tag_buttons += [tag_button]

def tag_highlighter(arg1=None,arg2=None,arg3=None):
    current = tags_var.get().strip().split()
    for i in tag_buttons:
        if i["text"] in current:
            i.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
        else:
            i.configure(bootstyle=ttkbootstrap.constants.PRIMARY)

def choose_file(event):
    file = tkinter.filedialog.askopenfilename()
    @dataclasses.dataclass
    class Event:
        data = file
    if file:
        on_drop(Event())

def calc_size(index,size):
    sizes = [1,2,4,5,8,10,16,20,32]
    if index == -1:
        return shared.get_bytes(size)
    else:
        return sizes[index] * 1024 ** 2

def update_size(event):
    chunk_size_indicator.configure(text=str(calc_size(chunk_size_entry.current(),chunk_size_entry.get())) + " Bytes")

root = Tk()
root.title("FileEnclave")

if shared.current_build == "Alpha" or shared.current_build == "Beta":
    release_colors = {"Alpha":ttkbootstrap.constants.DANGER,"Beta":ttkbootstrap.constants.WARNING,"Stable":ttkbootstrap.constants.SUCCESS}
    release = ttkbootstrap.Label(root,text=f"{shared.current_build}: {shared.builds[shared.current_build]}",anchor="center",bootstyle=(ttkbootstrap.constants.INVERSE,release_colors[shared.current_build]))
    release.pack(fill=tkinter.X)
    
main_pane = tkinter.PanedWindow(root,orient=tkinter.HORIZONTAL)
main_pane.pack(fill=tkinter.BOTH,expand=True,padx=10,pady=10)

left_frame = tkinter.Frame(main_pane,padx=10,pady=10)
main_pane.add(left_frame)

right_frame = tkinter.Frame(main_pane,padx=10,pady=10)
main_pane.add(right_frame)

drop_frame = tkinter.LabelFrame(left_frame,text=_("DND a file or choose one"),width=400,height=150,cursor="hand2")
drop_frame.pack(ipady=30,fill=tkinter.X)
drop_frame.pack_propagate(False)
drop_label = tkinter.Label(drop_frame,text=_("Drag and drop a file\nor click and choose one"),fg="gray",wraplength=500)
drop_label.pack(expand=True)
drop_label.bind("<Button-1>",choose_file)

preview_frame = tkinter.LabelFrame(left_frame,text=_("Preview"),width=400,height=150)
preview_frame.pack(fill=tkinter.X)
tk_img = PIL.ImageTk.PhotoImage(PIL.Image.new(mode="RGB",size=(480,270),color=(255,255,255)))
preview_pic = tkinter.Label(preview_frame,image=tk_img)
preview_pic.pack(ipady=20,fill=tkinter.X)
                           
drop_frame.drop_target_register(tkinterdnd2.DND_FILES)
drop_frame.dnd_bind("<<Drop>>",on_drop)
drop_frame.bind("<Button-1>",choose_file)

frame_pwd = tkinter.Frame(left_frame)
frame_pwd.pack(fill=tkinter.X,pady=5)
password_label = tkinter.Label(frame_pwd,text=_("Password: "))
password_label.pack(side=tkinter.LEFT)
user_password_var = tkinter.StringVar(value=password)
password_entry = tkinter.Entry(frame_pwd,textvariable=user_password_var,show="●",width=30)
password_entry.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
password_reveal_button = tkinter.Button(frame_pwd,text="👁")
password_reveal_button.pack(side=tkinter.LEFT)
password_reveal_button.bind("<ButtonPress-1>",lambda event: password_entry.configure(show=""))
password_reveal_button.bind("<ButtonRelease-1>",lambda event: password_entry.configure(show="●"))

frame_rec = tkinter.Frame(left_frame)
frame_rec.pack(fill=tkinter.X,pady=5)
rec_size_label = tkinter.Label(frame_rec,text=_("Recovery (0~100)%: "))
rec_size_label.pack(side=tkinter.LEFT)
rec_size_tip = ttkbootstrap.widgets.tooltip.ToolTip(rec_size_label,text=_("If an encrypted ZIP file gets damaged (e.g., from faulty USB storage), it can be fixed. For instance, at a 15% recovery level, any damage under 15% is repairable. Note that this uses extra disk space—roughly the archive size times the recovery rate."),delay=0)
rec_size_var = tkinter.IntVar(value=rec_percentage)
rec_size_scale = ttkbootstrap.Spinbox(frame_rec,from_=1,to=100,textvariable=rec_size_var,width=15)
rec_size_scale.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True,ipadx=50)

frame_chunk = tkinter.Frame(left_frame)
frame_chunk.pack(fill=tkinter.X,pady=5)
chunk_size_label = tkinter.Label(frame_chunk,text=_("Chunk size: "))
chunk_size_tip = ttkbootstrap.widgets.tooltip.ToolTip(chunk_size_label,text=_("Files are split into chunks before encryption to boost performance. For example, a 51 MB file with a 10 MB chunk size will be divided into 6 pieces (5 × 10 MB + 1 × 1 MB = 51 MB)."),delay=0)
chunk_size_label.pack(side=tkinter.LEFT)       
chunk_size_entry = tkinter.ttk.Combobox(frame_chunk,values=["1 MB","2 MB","4 MB","5 MB","8 MB","10 MB","16 MB","20 MB","32 MB"])
chunk_size_entry.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
chunk_size_entry.insert(tkinter.INSERT,shared.format_bytes(chunk_size))
chunk_size_entry.bind("<<ComboboxSelected>>",update_size)
chunk_size_entry.bind("<KeyRelease>",update_size)
chunk_size_indicator = tkinter.Label(frame_chunk,text=str(calc_size(chunk_size_entry.current(),chunk_size_entry.get())) + " Bytes")
chunk_size_indicator.pack(side=tkinter.LEFT,padx=10)

frame_output = tkinter.Frame(left_frame)
frame_output.pack(fill=tkinter.X,pady=5)
output_label = tkinter.Label(frame_output,text=_("Output path: "))
output_label.pack(side=tkinter.LEFT)
output_entry = tkinter.Entry(frame_output,width=15)
output_entry.insert(tkinter.INSERT,path)
output_entry.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)

virtual_directory = tkinter.Frame(left_frame)
virtual_directory.pack(fill=tkinter.X,pady=5)
virtual_directory_label = tkinter.Label(virtual_directory,text=_("Virtual folder: "))
virtual_directory_label.pack(side=tkinter.LEFT)
virtual_directory_var = tkinter.StringVar()
virtual_directory_entry = tkinter.Entry(virtual_directory,textvariable=virtual_directory_var,width=15)
virtual_directory_entry.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)

run = ttkbootstrap.Button(left_frame,text=_("Start encryption: "),command=run_creator)
run.pack(fill=tkinter.X,pady=15,ipady=20)

right_container = tkinter.LabelFrame(right_frame,text=_("Tag settings"))
right_container.pack(fill=tkinter.BOTH,expand=True)

frame_tags = tkinter.Frame(right_container)
frame_tags.pack(fill=tkinter.X,padx=10,pady=10)

edit_tags = ttkbootstrap.Button(frame_tags,text=_("Edit tags"),command=edit)
edit_tags.pack(fill=tkinter.X)

tags_label = tkinter.Label(frame_tags,text=_("Tags: (Use space to seperate)"))
tags_label.pack(anchor=tkinter.W)
tags_var = tkinter.StringVar()
tags_var.trace_add("write",tag_highlighter)
tag_entry = tkinter.Entry(frame_tags,textvariable=tags_var,width=30)
tag_entry.pack(fill=tkinter.X,pady=(5,10))
tag_entry.pack_propagate(False)
tag_reset = ttkbootstrap.Button(tag_entry,text="×",command=lambda: tags_var.set(value=""),cursor="arrow",bootstyle=ttkbootstrap.constants.LINK)
tag_reset.pack(side=tkinter.RIGHT)

frame_buttons = tkinter.Frame(right_container)
frame_buttons.pack(fill=tkinter.BOTH,expand=True,padx=10)

tag_append = tkinter.Entry(frame_buttons,width=9)
tag_append.bind("<Return>",user_add)

for i in tags:
    add_tag(i)

parser = argparse.ArgumentParser(description="Creator GUI")
parser.add_argument("-f","--file",help="The file you wish to encrypt")
parser.add_argument("-p","--password",help="Password for the file, loads from config.json if not given")
parser.add_argument("-d","--directory",help="Virtual directory",default="/")
args = parser.parse_args()

if args.file:
    @dataclasses.dataclass
    class Event:
        data = args.file
    on_drop(Event())

if args.password:
    user_password_var.set(value=args.password)
virtual_directory_var.set(value=args.directory)

root.mainloop()
