#!/usr/bin/python3
import tkinter
import tkinter.messagebox
import hashlib
import json
import subprocess
import os
import tkinterdnd2
import ttkbootstrap
import preview
import PIL
import io
import threading

#TODO：把chunk_size选择器美化掉
#TODO：设置最小窗口大小

class Tk(ttkbootstrap.Window,tkinterdnd2.TkinterDnD.Tk): #混合ttkbootstrap和tkinterdnd
    pass

#=====加载与配置=====
rec_percentage = 0 #恢复量（百分比）
chunk_size = 2079152 #单个
tags = [] #标签
path = "./" #当前路径
password = "" #密码
file_path = None #被加载的文件
tk_img = None #图片缓存
edit_mode = False #标签修改模式

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

#=====各种函数定义=====

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
        tkinter.messagebox.showerror("执行失败",str(e))
        root.after(3000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
    else:
        run.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
        tkinter.messagebox.showinfo("成功","文件加密完成")
        root.after(1000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))

def run_creator(): #创建加密压缩包
    global file_path
    if not file_path or not os.path.exists(file_path):
        run.configure(bootstyle=ttkbootstrap.constants.WARNING)
        tkinter.messagebox.showwarning("缺少文件","请先拖拽一个文件")
        root.after(1000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        return

    if not user_password_var.get():
        run.configure(bootstyle=ttkbootstrap.constants.WARNING)
        tkinter.messagebox.showwarning("缺少密码","请输入密码")
        root.after(1000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        return

    try:
        output_hash = sha1_md5(file_path)
    except Exception as e:
        run.configure(bootstyle=ttkbootstrap.constants.DANGER)
        tkinter.messagebox.showerror("Hash 错误",str(e))
        root.after(3000,lambda: run.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        return

    tags_raw = tags_var.get().strip()
    tags_list = [t.strip() for t in tags_raw.split() if t.strip()]
    tags_json = ",".join(f'"{t}"' for t in tags_list)

    cmd = ["python3","creator.py",file_path,f"{path}/{output_hash}.7z",user_password_var.get(),"-y","-m",f'{{"tags":[{tags_json}]}}',"-c",str(chunk_size)]
    
    if rec_percentage != 0:
        print("rec")
        cmd += ["-r",str(rec_percentage)]
    run.configure(state=tkinter.DISABLED)
    threading.Thread(target=run_cmd,args=[cmd],daemon=True).start()

def edit():
    global edit_mode
    if edit_mode:
        edit_mode = False
        edit_tags.configure(text="编辑标签",bootstyle=ttkbootstrap.constants.PRIMARY)
        tag_append.grid_forget()
    else:
        edit_mode = True
        edit_tags.configure(text="完成编辑（右键标签即可将其删除）",bootstyle=ttkbootstrap.constants.SUCCESS)
        tag_append.grid(row=len(tag_buttons) // 3,column=len(tag_buttons) % 3,padx=5,pady=5,sticky=tkinter.W)

def user_add(event):
    tag_name = tag_append.get()
    for i in tag_name.split():
        for j in tag_buttons:
            if j["text"] == i:
                j.configure(bootstyle=(ttkbootstrap.constants.INFO,ttkbootstrap.constants.OUTLINE))
                root.after(1000,lambda btn=j: j.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
                root.after(1500,tag_highlighter)
                return
        add_tag(i)
        tag_append.grid(row=len(tag_buttons) // 3,column=len(tag_buttons) % 3,padx=5,pady=5,sticky=tkinter.W)
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
        tag_buttons[i].grid(row=i // 3,column=i % 3,padx=5,pady=5,sticky=tkinter.W)
    tag_append.grid(row=len(tag_buttons) // 3,column=len(tag_buttons) % 3,padx=5,pady=5,sticky=tkinter.W)

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
    if tag == "":
        return
    tag_button = ttkbootstrap.Button(frame_buttons,text=tag,width=8,command=lambda t=tag: insert_tag(t))
    tag_button.grid(row=len(tag_buttons) // 3,column=len(tag_buttons) % 3,padx=5,pady=5,sticky=tkinter.W)
    tag_button.bind("<Button-3>",lambda event,t=tag: del_tag(event,t))
    tag_buttons.append(tag_button)

def tag_highlighter(arg1=None,arg2=None,arg3=None):
    current = tags_var.get().strip().split()
    for i in tag_buttons:
        if i["text"] in current:
            i.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
        else:
            i.configure(bootstyle=ttkbootstrap.constants.PRIMARY)
            
    
#=====窗口与界面=====
root = Tk()
root.title("Creator GUI Tool")
root.geometry("1180x960")
main_pane = tkinter.PanedWindow(root,orient=tkinter.HORIZONTAL)
main_pane.pack(fill=tkinter.BOTH,expand=True,padx=10,pady=10)

left_frame = tkinter.Frame(main_pane,padx=10,pady=10)
main_pane.add(left_frame,minsize=620)

right_frame = tkinter.Frame(main_pane,padx=10,pady=10)
main_pane.add(right_frame,minsize=420)

drop_frame = tkinter.LabelFrame(left_frame,text="拖拽文件到此处",width=400,height=150)
drop_frame.pack(ipady=30,pady=(0,10),fill=tkinter.X)
drop_frame.pack_propagate(False)

drop_label = tkinter.Label(drop_frame,text="📂 拖拽一个文件进来",fg="gray",wraplength=450)
drop_label.pack(expand=True)

preview_pic = tkinter.Label(left_frame,text="预览图")
preview_pic.pack(ipady=0,pady=(0,10),fill=tkinter.X)
                           
drop_frame.drop_target_register(tkinterdnd2.DND_FILES)
drop_frame.dnd_bind("<<Drop>>",on_drop)

frame_pwd = tkinter.Frame(left_frame)
frame_pwd.pack(fill=tkinter.X,pady=5)

password_label = tkinter.Label(frame_pwd,text="密码：")
password_label.pack(side=tkinter.LEFT)
user_password_var = tkinter.StringVar(value=password)
password_entry = tkinter.Entry(frame_pwd,textvariable=user_password_var,show="*",width=30)
password_entry.pack(side=tkinter.LEFT,padx=5)

frame_rec = tkinter.Frame(left_frame)
frame_rec.pack(fill=tkinter.X,pady=5)

rec_label = tkinter.Label(frame_rec,text="恢复（0–100）：")
rec_label.pack(side=tkinter.LEFT)
rec_var = tkinter.IntVar(value=rec_percentage)
rec_scale = tkinter.Scale(frame_rec,from_=0,to=100,orient=tkinter.HORIZONTAL,variable=rec_var)
rec_scale.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)

frame_chunk = tkinter.Frame(left_frame)
frame_chunk.pack(fill=tkinter.X,pady=5)

chunk_size_label = tkinter.Label(frame_chunk,text="切片大小：")
chunk_size_label.pack(side=tkinter.LEFT)
chunk_size_var = tkinter.IntVar(value=chunk_size)
chunk_size_entry = tkinter.Spinbox(frame_chunk,from_=1,to=100000000,textvariable=chunk_size_var,width=15)
chunk_size_entry.pack(side=tkinter.LEFT,padx=5)

run = ttkbootstrap.Button(left_frame,text="🚀 执行 creator.py",command=run_creator)
run.pack(fill=tkinter.X,pady=15,ipady=20)

right_container = tkinter.LabelFrame(right_frame,text="标签设置")
right_container.pack(fill=tkinter.BOTH,expand=True)

frame_tags = tkinter.Frame(right_container)
frame_tags.pack(fill=tkinter.X,padx=10,pady=10)

edit_tags = ttkbootstrap.Button(frame_tags,text="编辑标签",command=edit)
edit_tags.pack(fill=tkinter.X)

tags_label = tkinter.Label(frame_tags,text="标签（空格分隔）：")
tags_label.pack(anchor=tkinter.W)
tags_var = tkinter.StringVar()
tags_var.trace_add("write",tag_highlighter)
tag_entry = tkinter.Entry(frame_tags,textvariable=tags_var,width=30)
tag_entry.pack(fill=tkinter.X,pady=(5,10))

frame_buttons = tkinter.Frame(right_container)
frame_buttons.pack(fill=tkinter.BOTH,expand=True,padx=10,pady=(0,10))
tag_buttons = []

tag_append = tkinter.Entry(frame_buttons,width=9)
tag_append.bind("<Return>",user_add)

#=====启动=====
for i in tags:
    add_tag(i)
root.mainloop()
