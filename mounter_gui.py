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

class MetadataError(Exception): #自定义异常
    pass

class Modal(): #自定义对话框
    def __init__(self,master,title="Topmost Dialog",resizable=(False,False),customize_button=False,esc=True,transistent=True):
        self.top = tkinter.Toplevel(master)
        frame = tkinter.Frame(self.top)
        frame.pack()
        focus = self.body(frame)
        if focus:
            focus.focus_set()
        self.top.title(title)
        self.top.resizable(*resizable)
        self.top.attributes("-topmost", True)
        self.top.grab_set()
        if transistent:
            self.top.transient(master)
        self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)
        if not customize_button:
            ok_btn = tkinter.Button(self.top, text="确定",command=self.top.destroy)
            ok_btn.pack(pady=(0, 20))
        if esc:
            self.top.bind("<Escape>",lambda event: self.top.destroy())
        root.wait_window(self.top)
    def body(self,master):
        tkinter.Label(master,text="Dialog").pack()

class LogWindow(Modal):
    def __init__(self,master,logs):
        self.logs = logs
        super().__init__(master,title="Logs")
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
        textpad.pack()

class InfoWindow(Modal):
    def __init__(self,master,info):
        self.info = info
        super().__init__(master,title="文件信息",)
    def body(self,master):
        textpad = tkinter.scrolledtext.ScrolledText(master,width=80,height=10,font=("Noto Sans Mono",13))
        textpad.insert(tkinter.INSERT,self.info)
        textpad.configure(state=tkinter.DISABLED)
        textpad.pack()

class DeleteWindow(Modal):
    def __init__(self,master,info):
        self.info = info
        super().__init__(master,title="删除",customize_button=True)
    def body(self,master):
        textpad = tkinter.scrolledtext.ScrolledText(master,width=80,height=10,font=("Noto Sans Mono",13))
        textpad.insert(tkinter.INSERT,self.info)
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
        super().__init__(master,title="登录",customize_button=True,transistent=False)
    def choose_file(self):
        folder = tkinter.filedialog.askdirectory()
        self.dir.delete(0,tkinter.END)
        self.dir.insert(tkinter.INSERT,folder)
    def body(self,master):
        pathchooser = tkinter.Frame(master)
        pathchooser.grid(row=0,column=1)
        tkinter.Label(master, text="Path: ").grid(row=0)
        tkinter.Label(master, text="Password: ").grid(row=1)
        tkinter.Label(master, text="Cache: ").grid(row=2)
        self.dir = tkinter.Entry(pathchooser)
        self.dir_button = tkinter.Button(pathchooser,text="Path",command=self.choose_file)
        if self.default_path: self.dir.insert(0,self.default_path)
        self.password = tkinter.Entry(master)
        if self.default_password: self.password.insert(0,self.default_password)
        self.dir.grid(row=0, column=1,ipadx=230)
        self.dir_button.grid(row=0,column=2,padx=20)
        self.password.grid(row=1, column=1,ipadx=300)
        cache_frame = tkinter.Frame(master)
        cache_frame.grid(row=2, column=1)
        self.cache = tkinter.ttk.Combobox(cache_frame,values=["不启用","1 MB","2 MB","4 MB","8 MB","16 MB","32 MB","64 MB","128 MB","256 MB"])
        self.cache.grid(row=0,column=0,ipadx=150)
        self.cache_show = tkinter.Label(cache_frame,width=20)
        self.cache_show.grid(row=0,column=1)
        self.cache.bind("<<ComboboxSelected>>",self.update_size)
        self.cache.bind("<KeyRelease>",self.update_size)
        self.cache.insert(tkinter.INSERT,shared.format_bytes(self.default_cache))
        if self.default_cache == 0:
            self.cache.current(0)
        self.update_size()
        buttons = tkinter.Frame(self.top)
        buttons.pack()
        ok_button = tkinter.Button(buttons,text="确定",command=self.apply)
        ok_button.grid(row=0,column=0,ipadx=20,padx=20,pady=10)
        cancel_button = tkinter.Button(buttons,text="取消",command=self.top.destroy)
        cancel_button.grid(row=0,column=1,ipadx=20,padx=20,pady=10)
        self.dir.bind("<Return>",self.apply)
        self.password.bind("<Return>",self.apply)
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

def log(log_text): 
    global logs
    if log_text:
        logs += f'[{time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())}]' + log_text + "\n"

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
        output = repair.stdout.read().decode("utf-8").rstrip()
        log(output)
        tkinter.messagebox.showinfo("修复",output)
    thread = threading.Thread(target=newthread,args=[file])
    thread.start()

def delete_file(archive,filename,button):
    delete = DeleteWindow(root,f"你即将删除：{archive} ({filename})\n此操作无法恢复。是否继续？")
    if delete.answer:
        os.system(f"rm {archive}*")
        log(f"[+] Deleted: {archive}*")
        preview_buttons.remove(button)
        for idx,i in enumerate(preview_buttons):
            row = idx // columns
            col = idx % columns
            idx += 1
            i.grid(row=row, column=col, padx=5, pady=5)

def search_file(event=None):
    idx = 0
    search_results = 0
    for i in preview_buttons:
        i.grid_forget()
        if search_entry.get() in i["text"]:
            row = idx // columns
            col = idx % columns
            idx += 1
            i.grid(row=row, column=col, padx=5, pady=5)

def delete_search():
    search_entry.delete(0,tkinter.END)
    search_file()

def safe_ui_update(fn):
    """确保所有 UI 操作回到主线程"""
    root.after(0, fn)

state = tkinter.NORMAL
def disable_all():
    global state
    state = tkinter.DISABLED
    with lock:
        for btn in preview_buttons:
            btn.config(state="disabled")

def enable_all():
    global state
    state = tkinter.NORMAL
    with lock:
        for btn in preview_buttons:
            btn.config(state="normal")

def on_close():
    global current_proc
    with lock:
        if current_proc is not None:
            current_proc.send_signal(signal.SIGINT)
            current_proc = None
    enable_all()
    os.system("umount -l mnt")
    log(f"[i] Attempted to umount mnt")

def on_destroy():
    on_close()
    root.destroy()
    executor.shutdown(wait=False,cancel_futures=True)
    sys.exit()

def load_preview(archive):
    try:
        meta = json.loads(sevenzipwrapper.read_file(archive, "metadata").decode("utf-8"))
    except:
        raise MetadataError(archive)
    salt = meta["salt"]

    user_pwd = passwordutil.hash(user_password, salt)
    file_pwd = sevenzipwrapper.read_file(archive, "password", password=user_pwd).decode("utf-8")
    #print("{" + archive + " " + file_pwd + "|" + user_pwd + "}")

    original_meta = json.loads(
        sevenzipwrapper.read_file(archive, "original_metadata", user_pwd).decode("utf-8"))

    preview_bytes = sevenzipwrapper.read_file(archive, "preview", password=file_pwd)

    img = PIL.Image.open(io.BytesIO(preview_bytes))
    img = img.resize((480,270))
    return archive, img, original_meta["filename"],original_meta["tags"],original_meta["size"],meta["chunks"],meta["chunk_size"]

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
        archive, img, filename,tags,size,chunks,chunk_size = future.result()
        log(f"[+] Loaded archive: {archive}")
    except Exception as e:
        if isinstance(e,RuntimeError):
            log(f"[!] {e}")
        elif isinstance(e,MetadataError):
            log(f"[!] {e} isn't designed to be loaded.")
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

            btn = tkinter.Button(frame,text=filename + parse(tags),image=tk_img,command=lambda a=archive,f=filename: on_preview_click(a,f),compound=tkinter.TOP,state=state,wraplength=450)
            def show_menu(event):
                global menu
                if menu:
                    menu.unpost()
                menu = tkinter.Menu(btn,tearoff=0)
                menu.add_command(label="修复",command=lambda: repair_file(archive))
                menu.add_command(label="删除",command=lambda: delete_file(archive,filename,btn))
                menu.add_command(label="文件信息",command=lambda: InfoWindow(root,f'路径：{pathlib.Path(archive).parent}\n加密：{pathlib.Path(archive).name}\n文件：{filename}\n标签：{" ".join(tags)}\n大小：{shared.format_bytes(size)} ({size} Bytes)\n切片数量：{chunks}\n切片规格：{shared.format_bytes(chunk_size)} ({chunk_size} Bytes)'))
                menu.post(event.x_root, event.y_root)
                
            btn.image = tk_img
            btn.bind("<Button-3>",show_menu)
            btn.grid(row=row, column=col, padx=5, pady=5)
            preview_buttons += [btn]
            load_indicator.configure(text=f"已加载：{len(preview_buttons)}/{total}")

    safe_ui_update(add_button)

def on_preview_click(archive,filename):
    global current_proc
    with lock:
        if current_proc is not None:
            return
        current_proc = subprocess.Popen(["python3", "mounter.py", archive, user_password, "mnt","-c",str(cache),"-o"])
        log(f"[+] Attempted to mount {archive}")
        
    disable_all()

def load_archives():
    global user_password
    global archive_dir
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
        log("[i] Loaded config.json")
    except:
        archive_dir = None
        log("[!] Failed to load config.json")
    root.withdraw()
    dialog = LoginWindow(root,default_path=archive_dir,default_password=user_password,cache=cache)
    try:
        archive_dir,user_password,cache = dialog.path,dialog.passwd,dialog.cache_size
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
        future = executor.submit(load_preview, archive)
        future.add_done_callback(on_loaded)
root = ttkbootstrap.Window()
root.title("Encrypted Archive Viewer")
root.geometry("2200x1200")
archives = []
top_banner = tkinter.ttk.Frame(root)
top_banner.pack(fill="x")
search_frame = tkinter.ttk.LabelFrame(top_banner,text="搜索")
search_frame.grid(row=0,column=0,padx=20)
search_entry = tkinter.Entry(search_frame)
search_entry.grid(row=0,column=0,padx=10,pady=10,ipadx=520)
search_entry.pack_propagate(False)
search_button = tkinter.Button(search_frame,text="搜索",command=search_file)
search_button.grid(row=0,column=1,padx=10)
search_entry.bind("<Return>",search_file)
search_delete = tkinter.Button(search_entry,text="x",command=delete_search,cursor="arrow")
search_delete.pack(side=tkinter.RIGHT)
repair_everything = ttkbootstrap.Button(top_banner,text="检查修复所有文件",command=repair_all)
repair_everything.grid(row=0,column=3,padx=20)

canvas = tkinter.Canvas(root)
scrollbar = tkinter.ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
frame = tkinter.ttk.Frame(canvas)

canvas.create_window((0, 0), window=frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

load_frame = tkinter.Frame(top_banner)
load_frame.grid(row=0,column=1)
umount = tkinter.ttk.Button(load_frame, text="卸载卷/修复", command=on_close)
umount.grid(row=0,column=0,pady=10)
load_indicator = tkinter.ttk.Label(load_frame,text="已加载：0/0")
load_indicator.grid(row=1,column=0)
log_button = ttkbootstrap.Button(top_banner,text="Logs",command=lambda: LogWindow(root,logs))
log_button.grid(row=0,column=2)
root.protocol("WM_DELETE_WINDOW",on_destroy)

root.bind("<Button-1>", hide_menu)
root.after(100, load_archives)
root.mainloop()
