#!/usr/bin/python3
import os
import json
import io
import subprocess
import threading
import concurrent.futures
import signal
import pathlib
import time
import sys
import traceback
import re

import tkinter
import tkinter.ttk
import tkinter.simpledialog
import tkinter.filedialog
import PIL.Image
import PIL.ImageTk
import ttkbootstrap
import tkinter.scrolledtext

import passwordutil
import sevenzipwrapper
import shared

logs = ""
archive_dir = "./archives"
columns = 4
user_password = None
preview_buttons = []
current_proc = None
lock = threading.Lock()
menu = None
total = 0
cache = 0
executor = None
state = tkinter.NORMAL #当前所有按钮的状态
archives = []
info_password = False

class MetadataError(Exception): #自定义异常
    pass

class Modal(): #自定义对话框
    def __init__(self,master,title="Topmost Dialog",resizable=(False,False),customize_button=False,esc=True,transient=True,geometry=None):
        self.top = tkinter.Toplevel(master)
        self.top.title(title)
        self.top.resizable(*resizable)
        self.top.attributes("-topmost",True)
        self.top.grab_set()
        if transient:
            self.top.transient(master)
        if esc:
            self.top.bind("<Escape>",lambda event: self.top.destroy())
        if geometry:
            self.top.geometry(geometry)
            
        frame = tkinter.Frame(self.top)
        frame.pack(fill=tkinter.BOTH,expand=True)
        focus = self.body(frame)
        if focus:
            focus.focus_set()
        if not customize_button:
            ok_btn = tkinter.Button(self.top,text="确定",command=self.top.destroy)
            ok_btn.pack(pady=20)
        
        root.wait_window(self.top)
    def body(self,master):
        pass

class LogWindow(Modal):
    def __init__(self,master,logs):
        self.logs = logs
        super().__init__(master,title="Logs",resizable=(True,True))
    def body(self,master):
        font = ["Noto Sans Mono",8]
        textpad = tkinter.scrolledtext.ScrolledText(master,width=160,font=font)
        textpad.tag_config("Info",foreground="blue",font=font)
        textpad.tag_config("Error",foreground="red",font=font + ["bold"])
        textpad.tag_config("Warning",foreground="orange",font=font + ["bold"])
        for i in self.logs.split("\n"):
            if "[!]" in i:
                textpad.insert(tkinter.INSERT,i + "\n","Error")
            elif "[~]" in i:
                textpad.insert(tkinter.INSERT,i + "\n","Warning")
            else:
                textpad.insert(tkinter.INSERT,i + "\n","Info")
        textpad.see(tkinter.END)
        textpad.configure(state=tkinter.DISABLED)
        textpad.pack(fill=tkinter.BOTH,expand=True)

class InfoWindow(Modal):
    def __init__(self,master,info):
        self.info = info
        super().__init__(master,title="文件信息",resizable=(True,True))
    def body(self,master):
        textpad = tkinter.scrolledtext.ScrolledText(master,width=80,height=15,font=("Noto Sans Mono",13))
        textpad.insert(tkinter.INSERT,self.info)
        textpad.configure(state=tkinter.DISABLED)
        textpad.pack(fill=tkinter.BOTH,expand=True)

class DeleteWindow(Modal):
    def __init__(self,master,archive,filename):
        self.archive = archive
        self.filename = filename
        super().__init__(master,title="删除",customize_button=True)
    def body(self,master):
        message = f"你即将删除：{self.archive} ({self.filename})\n此操作无法撤销，内部文件也无法恢复。是否继续？"
        textpad = tkinter.scrolledtext.ScrolledText(master,width=80,height=10,font=("Noto Sans Mono",13))
        textpad.insert(tkinter.INSERT,message)
        textpad.configure(state=tkinter.DISABLED)
        textpad.pack()
        buttons = tkinter.Frame(self.top)
        buttons.pack()
        ok_button = tkinter.Button(buttons,text="确定",command=self.apply)
        ok_button.grid(row=0,column=0,ipadx=20,padx=20,pady=10)
        cancel_button = tkinter.Button(buttons,text="取消",command=self.top.destroy)
        cancel_button.grid(row=0,column=1,ipadx=20,padx=20,pady=10)
        self.answer = False
        return ok_button
    def apply(self):
        self.answer = True
        self.top.destroy()

class LoginWindow(Modal):
    def __init__(self,master,default_path=None,default_password=None,cache=0):
        self.default_path = default_path
        self.default_password = default_password
        self.warning = False
        self.default_cache = cache
        super().__init__(master,title="登录",customize_button=True,transient=False,geometry="1200x300")
    def choose_file(self):
        folder = tkinter.filedialog.askdirectory()
        self.dir.delete(0,tkinter.END)
        self.dir.insert(tkinter.INSERT,folder)
    def body(self,master):
        path_frame = tkinter.Frame(master)
        path_frame.pack(fill=tkinter.X)
        path_label = tkinter.Label(path_frame,text="路径：")
        path_label.pack(side=tkinter.LEFT)
        self.dir = tkinter.Entry(path_frame)
        self.dir.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
        self.dir.bind("<Return>",self.apply)
        if self.default_path:
            self.dir.insert(0,self.default_path)
        dir_button = tkinter.Button(path_frame,text="选择",command=self.choose_file)
        dir_button.pack(side=tkinter.LEFT,padx=10)

        password_frame = tkinter.Frame(master)
        password_frame.pack(fill=tkinter.X)
        password_label = tkinter.Label(password_frame,text="密码：")
        password_label.pack(side=tkinter.LEFT)
        self.password = tkinter.Entry(password_frame,show="●")
        self.password.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
        self.password.bind("<Return>",self.apply)
        if self.default_password:
            self.password.insert(0,self.default_password)
        password_show = tkinter.Button(password_frame,text="显示")
        password_show.pack(side=tkinter.LEFT,padx=10)
        password_show.bind("<ButtonPress-1>",lambda event: self.password.configure(show=""))
        password_show.bind("<ButtonRelease-1>",lambda event: self.password.configure(show="●"))

        cache_frame = tkinter.Frame(master)
        cache_frame.pack(fill=tkinter.X)
        cache_label = tkinter.Label(cache_frame,text="缓存：")
        cache_label.pack(side=tkinter.LEFT)
        self.cache = tkinter.ttk.Combobox(cache_frame,values=["不启用","1 MB","2 MB","4 MB","8 MB","16 MB","32 MB","64 MB","128 MB","256 MB"])
        self.cache.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
        self.cache_show = tkinter.Label(cache_frame)
        self.cache_show.pack(side=tkinter.LEFT,padx=10)
        self.cache.bind("<<ComboboxSelected>>",self.update_size)
        self.cache.bind("<KeyRelease>",self.update_size)
        self.cache.insert(tkinter.INSERT,shared.format_bytes(self.default_cache))
        if self.default_cache == 0:
            self.cache.current(0)
        self.update_size()

        self.info_show_password_var = tkinter.IntVar()
        info_show_passwords = ttkbootstrap.Checkbutton(master,text="展示盐和密码（仅调试用）",variable=self.info_show_password_var)
        info_show_passwords.pack(anchor=tkinter.W,padx=10)
        self.info_show_password_var.set(value=0)

        buttons_frame = tkinter.Frame(master)
        buttons_frame.pack()
        ok_button = tkinter.Button(buttons_frame,text="确定",command=self.apply)
        ok_button.grid(row=0,column=0,ipadx=20,padx=20,pady=10)
        cancel_button = tkinter.Button(buttons_frame,text="取消",command=self.top.destroy)
        cancel_button.grid(row=0,column=1,ipadx=20,padx=20,pady=10)
        return self.password # 初始焦点
    def apply(self,event=None):
        self.path = self.dir.get()
        self.passwd = self.password.get()
        self.cache_size = self.calc_size(self.cache.current(),self.cache.get())
        self.top.destroy()
    def calc_size(self,index,size):
        sizes = [0,1,2,4,8,16,32,64,128,256]
        if index == -1:
            return shared.get_bytes(size)
        else:
            return sizes[index] * 1024 ** 2
    def update_size(self,event=None):
        size = self.calc_size(self.cache.current(),self.cache.get())
        self.cache_show.configure(text=str(size) + " Bytes")
        if size > 512 * 1024 ** 2:
            self.cache_show.configure(fg="red")
            if not self.warning:
                tkinter.messagebox.showwarning("缓存大小",f"您设置的缓存大小（{shared.format_bytes(size)}）太大了，大于512 MB。这种情况下，若您打开了一个大文件，则有可能引发OOM（内存不足）。")
                self.warning = True
        else:
            self.cache_show.configure(fg="black")

def log(message): 
    global logs
    if message:
        logs += f'[{time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())}]' + message + "\n"

def repair_all():
    def newthread():
        repair = subprocess.Popen(["python3","repair.py","-d",archive_dir],stdout=subprocess.PIPE)
        repair.wait()
        output = repair.stdout.read().decode("utf-8").split("\n")
        for i in output:
            log(i)
        repair_everything.configure(state=tkinter.NORMAL,bootstyle=ttkbootstrap.constants.SUCCESS)
        log_button.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
        repair_everything.configure(text="修复完成，可打开Logs查看")
        root.after(2000,lambda: repair_everything.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        root.after(2000,lambda: repair_everything.configure(text="修复检查所有文件"))
        root.after(4000,lambda: log_button.configure(bootstyle=ttkbootstrap.constants.PRIMARY))

    thread = threading.Thread(target=newthread)
    repair_everything.configure(state=tkinter.DISABLED)
    thread.start()

def repair_file(file):
    def newthread(file):
        repair = subprocess.Popen(["python3","repair.py","-f",file],stdout=subprocess.PIPE)
        repair.wait()
        log(repair.stdout.read().decode("utf-8").rstrip())
        tkinter.messagebox.showinfo("修复",output)
        
    thread = threading.Thread(target=newthread,args=[file])
    thread.start()

def delete_file(archive,filename,button):
    global total
    delete = DeleteWindow(root,archive,filename)
    if delete.answer:
        archives.remove(archive)
        total -= 1
        for i in range(json.loads(sevenzipwrapper.read_file(archive,"metadata").decode("utf-8"))["chunks"]):
            sevenzipwrapper.write_file(archive,str(i),b"0" * 1024,password=None)
        sevenzipwrapper.write_file(archive,"metadata",b"0" * 1024,password=None)
        sevenzipwrapper.write_file(archive,"password",b"0" * 1024,password=None)
        sevenzipwrapper.write_file(archive,"original_metadata",b"0" * 1024,password=None)
        sevenzipwrapper.write_file(archive,"preview",b"0" * 1024,password=None)
        os.system(f"rm {archive}*")
        log(f"[+] Deleted: {archive}*")
        preview_buttons.remove(button)
        for idx,i in enumerate(preview_buttons):
            row = idx // columns
            col = idx % columns
            idx += 1
            i.grid(row=row,column=col,padx=5,pady=5)

def search_file(event=None):
    idx = 0
    search_results = 0
    for i in preview_buttons:
        i.grid_forget()
        if search_entry.get() in i["text"]:
            row = idx // columns
            col = idx % columns
            idx += 1
            i.grid(row=row,column=col,padx=5,pady=5)

def reset_search():
    search_entry.delete(0,tkinter.END)
    search_file()

def set_state(status):
    global state
    state = status
    with lock:
        for btn in preview_buttons:
            btn.config(state=state)

def on_umount():
    global current_proc
    with lock:
        if current_proc is not None:
            current_proc.send_signal(signal.SIGINT)
            current_proc = None
    set_state(tkinter.NORMAL)
    os.system("umount -l mnt")
    log(f"[+] Attempted to umount mnt")

def on_close():
    on_umount()
    root.destroy()
    executor.shutdown(wait=False,cancel_futures=True)
    sys.exit()

def load_preview(archive):
    try:
        meta = json.loads(sevenzipwrapper.read_file(archive,"metadata").decode("utf-8"))
    except:
        raise MetadataError(archive)
    
    salt = meta["salt"]
    user_pwd = passwordutil.hash(user_password,salt)
    file_pwd = sevenzipwrapper.read_file(archive,"password",password=user_pwd).decode("utf-8")

    original_meta = json.loads(sevenzipwrapper.read_file(archive,"original_metadata",user_pwd).decode("utf-8"))
    filename = original_meta["filename"]
    tags = original_meta["tags"]
    size = original_meta["size"]
    chunk_num = meta["chunks"]
    chunk_size = meta["chunk_size"]
    
    img = PIL.Image.open(io.BytesIO(sevenzipwrapper.read_file(archive,"preview",password=file_pwd)))
    img = img.resize((480,270))
    return archive,img,filename,tags,size,chunk_num,chunk_size,salt,file_pwd,user_pwd

def hide_menu(event):
    global menu
    if menu:
        menu.unpost()
        menu = None

def parse(tags):
    ret = ""
    for i in tags:
        ret += " #" + i
    return ret

def on_loaded(future):
    global total
    try:
        archive,img,filename,tags,size,chunk_num,chunk_size,salt,file_pwd,user_pwd = future.result()
        log(f"[+] Loaded archive: {archive}")
    except Exception as e:
        if isinstance(e,RuntimeError):
            log(f"[!] {e}")
        elif isinstance(e,MetadataError):
            log(f"[!] {e} is invalid")
        else:
            traceback.print_exc()
            log(f"[!] Unknown error: {e}")
        total -= 1
        return

    tk_img = PIL.ImageTk.PhotoImage(img)

    def add_button():
        global preview_buttons
        with lock:
            row = len(preview_buttons) // columns
            col = len(preview_buttons) % columns
            btn = tkinter.Button(frame,text=filename + parse(tags),image=tk_img,command=lambda a=archive,f=filename: open_file(a,f),compound=tkinter.TOP,state=state,wraplength=450)

            def show_menu(event):
                global menu
                if menu:
                    menu.unpost()
                file_info = f"=====文件信息=====\n"
                file_info += f"路径：{pathlib.Path(archive).parent}\n"
                file_info += f"加密：{pathlib.Path(archive).name}\n"
                file_info += f"文件：{filename}\n"
                file_info += f"大小：{shared.format_bytes(size)} ({size} Bytes)\n"
                file_info += f"=====存储信息=====\n"
                file_info += f"切片数量：{chunk_num}\n"
                file_info += f"切片规格：{shared.format_bytes(chunk_size)} ({chunk_size} Bytes)\n"
                if info_password:
                    file_info += f"=====加密信息=====\n"
                    file_info += f"盐：{salt}\n"
                    file_info += f"一级密码：{user_pwd}\n"
                    file_info += f"二级密码：{file_pwd}\n"
                if tags:
                    file_info += f"=====其它信息=====\n"
                    file_info += f"标签：{parse(tags)}\n"
                
                menu = tkinter.Menu(btn,tearoff=0)
                menu.add_command(label="修复",command=lambda: repair_file(archive))
                menu.add_command(label="删除",command=lambda: delete_file(archive,filename,btn))
                menu.add_command(label="文件信息",command=lambda: InfoWindow(root,file_info))
                menu.post(event.x_root,event.y_root)
                
            btn.image = tk_img
            btn.bind("<Button-3>",show_menu)
            btn.grid(row=row,column=col,padx=5,pady=5)
            preview_buttons += [btn]
            load_indicator.configure(text=f"已加载：{len(preview_buttons)}/{total}",value=int(len(preview_buttons) / total * 100))
            if len(preview_buttons) == total:
                load_indicator.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
                root.after(1000,lambda: load_indicator.configure(text="已全部加载完毕"))
                root.after(3000,lambda: load_indicator.pack_forget())
            
    root.after(0,add_button)

def open_file(archive,filename):
    global current_proc
    with lock:
        if current_proc is not None:
            return
        current_proc = subprocess.Popen(["python3","mounter.py",archive,user_password,"mnt","-c",str(cache),"-o"])
        log(f"[+] Attempted to mount {archive}")
        
    set_state(tkinter.DISABLED)

def load_archives():
    global user_password
    global archive_dir
    global info_password
    global archives
    global total
    global cache
    global executor
    try:
        with open("config.json") as conf:
            config = json.loads(conf.read())
        archive_dir = config.get("mounter_path",archive_dir)
        user_password = config.get("password",user_password)
        cache = config.get("default_chunk_size",0)
        log("[+] Loaded config.json")
    except:
        archive_dir = None
        log("[!] Failed to load config.json")
    
    dialog = LoginWindow(root,default_path=archive_dir,default_password=user_password,cache=cache)
    try:
        archive_dir,user_password,cache,info_password = dialog.path,dialog.passwd,dialog.cache_size,dialog.info_show_password_var.get()
    except:
        root.destroy()
        sys.exit()
    
    root.deiconify()
    try:
        for i in os.listdir(archive_dir):
            if i.endswith(".7z"):
                archives += [os.path.join(archive_dir,i)]
    except:
        log(f"[!] No such directory: \"{archive_dir}\"")

    log(f"[+] Cache set to {shared.format_bytes(cache)} ({cache} Bytes)")
    if cache > 512 * 1024 ** 2:
        log(f"[~] Cache too large, this may trigger OOM when opening large files.")
    log(f"[+] Working directory: {archive_dir}")
    log(f"[+] Found {len(archives)} archive(s)")
    total = len(archives)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    for archive in archives:
        future = executor.submit(load_preview,archive)
        future.add_done_callback(on_loaded)

root = ttkbootstrap.Window()
root.title("Encrypted Archive Viewer")
root.geometry("2200x1200")
root.withdraw()

top_banner = tkinter.ttk.Frame(root)
top_banner.pack(fill=tkinter.X)

search_frame = tkinter.ttk.LabelFrame(top_banner,text="搜索")
search_frame.grid(row=0,column=0,padx=20)

search_entry = tkinter.Entry(search_frame)
search_entry.grid(row=0,column=0,padx=10,pady=10,ipadx=520)
search_entry.pack_propagate(False)
search_entry.bind("<Return>",search_file)

search_button = tkinter.Button(search_frame,text="搜索",command=search_file)
search_button.grid(row=0,column=1,padx=10)
search_reset = tkinter.Button(search_entry,text="x",command=reset_search,cursor="arrow")
search_reset.pack(side=tkinter.RIGHT)

log_button = ttkbootstrap.Button(top_banner,text="Logs",command=lambda: LogWindow(root,logs))
log_button.grid(row=0,column=1,padx=10)

umount_button = tkinter.ttk.Button(top_banner,text="卸载卷",command=on_umount)
umount_button.grid(row=0,column=2,padx=10)

repair_everything = ttkbootstrap.Button(top_banner,text="检查修复所有文件",command=repair_all)
repair_everything.grid(row=0,column=3,padx=10)

preview_frame = tkinter.Frame()
preview_frame.pack(fill=tkinter.BOTH,expand=True)
canvas = tkinter.Canvas(preview_frame)
scrollbar = tkinter.ttk.Scrollbar(preview_frame,orient="vertical",command=canvas.yview)
frame = tkinter.ttk.Frame(canvas)
frame.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox(tkinter.ALL)))
canvas.create_window((0,0),window=frame,anchor=tkinter.NW)
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side=tkinter.LEFT,fill=tkinter.BOTH,expand=True)
scrollbar.pack(side="right",fill=tkinter.Y)

load_indicator = ttkbootstrap.Floodgauge(root,text="已加载：0/0")
load_indicator.pack(fill=tkinter.X)
root.protocol("WM_DELETE_WINDOW",on_close)

root.bind("<Button-1>",hide_menu)
root.after(100,load_archives)
root.mainloop()
