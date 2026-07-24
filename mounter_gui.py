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
import webbrowser
import pyperclip

import tkinter
import tkinter.ttk
import tkinter.simpledialog
import tkinter.filedialog
import PIL.Image
import PIL.ImageTk
import ttkbootstrap
import tkinter.scrolledtext
import tkinterdnd2

import passwordutil
import sevenzipwrapper
import shared
import gettext

gettext.bindtextdomain("mounter_gui","./locale")
gettext.textdomain("mounter_gui")
_ = gettext.gettext

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
release_colors = {"Alpha":ttkbootstrap.constants.DANGER,"Beta":ttkbootstrap.constants.WARNING,"Stable":ttkbootstrap.constants.SUCCESS}
current_button_count = 0
folders = {"/"}
folder_buttons = []

current_dir = "/"

class Tk(ttkbootstrap.Window,tkinterdnd2.TkinterDnD.Tk): #混合ttkbootstrap和tkinterdnd
    pass

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
        ok_btn = tkinter.Button(self.top,text=_("Ok"),command=self.top.destroy)
        ok_btn.bind("<Return>",lambda event: self.top.destroy())
        if not customize_button:
            ok_btn.pack(pady=20)
        if focus:
            focus.focus_set()
        else:
            ok_btn.focus_set()
        
        root.wait_window(self.top)
    def body(self,master):
        pass

class LogWindow(Modal):
    def __init__(self,master,logs):
        self.logs = logs
        super().__init__(master,title="Logs",resizable=(True,True),customize_button=True)
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
        
        buttons_frame = tkinter.Frame(master)
        buttons_frame.pack()
        self.copy_button = ttkbootstrap.Button(buttons_frame,text=_("Copy to clipboard"),command=self.copy)
        self.copy_button.grid(row=0,column=0,ipadx=20,padx=20,pady=10)
        ok_button = ttkbootstrap.Button(buttons_frame,text=_("Ok"),command=self.top.destroy)
        ok_button.grid(row=0,column=1,ipadx=20,padx=20,pady=10)
        return ok_button
    def copy(self):
        pyperclip.copy(self.logs)
        self.copy_button.configure(text=_("Copied"),bootstyle=ttkbootstrap.constants.SUCCESS)

class InfoWindow(Modal):
    def __init__(self,master,info):
        self.info = info
        super().__init__(master,title=_("File Info"),resizable=(True,True))
    def body(self,master):
        textpad = tkinter.scrolledtext.ScrolledText(master,width=80,height=15,font=("Noto Sans Mono",13))
        textpad.insert(tkinter.INSERT,self.info)
        textpad.configure(state=tkinter.DISABLED)
        textpad.pack(fill=tkinter.BOTH,expand=True)

class DeleteWindow(Modal):
    def __init__(self,master,archive,filename):
        self.archive = archive
        self.filename = filename
        super().__init__(master,title=_("Delete"),customize_button=True)
    def body(self,master):
        message = _("You are going to delete: {archive} ({filename})\nThis can't be undone, and the file can't be recovered. Proceed?").format(archive=self.archive,filename=self.filename)
        textpad = tkinter.scrolledtext.ScrolledText(master,width=80,height=10,font=("Noto Sans Mono",13))
        textpad.insert(tkinter.INSERT,message)
        textpad.configure(state=tkinter.DISABLED)
        textpad.pack()
        buttons = tkinter.Frame(self.top)
        buttons.pack()
        ok_button = tkinter.Button(buttons,text=_("Yes"),command=self.apply)
        ok_button.grid(row=0,column=0,ipadx=20,padx=20,pady=10)
        cancel_button = tkinter.Button(buttons,text=_("Cancel"),command=self.top.destroy)
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
        super().__init__(master,title=_("Login"),customize_button=True,transient=False)
    def choose_file(self):
        folder = tkinter.filedialog.askdirectory()
        self.dir.delete(0,tkinter.END)
        self.dir.insert(tkinter.INSERT,folder)
    def body(self,master):
        if shared.current_build == "Alpha" or shared.current_build == "Beta":
            release = ttkbootstrap.Label(master,text=f"{shared.current_build}: {shared.builds[shared.current_build]}",anchor="center",bootstyle=(ttkbootstrap.constants.INVERSE,release_colors[shared.current_build]))
            release.pack(fill=tkinter.X)

        path_frame = tkinter.Frame(master)
        path_frame.pack(fill=tkinter.X)
        path_label = tkinter.Label(path_frame,text=_("Path: "))
        path_label.pack(side=tkinter.LEFT)
        self.dir = tkinter.Entry(path_frame)
        self.dir.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
        self.dir.bind("<Return>",self.apply)
        if self.default_path:
            self.dir.insert(0,self.default_path)
        dir_button = tkinter.Button(path_frame,text="🗁",command=self.choose_file)
        dir_button.pack(side=tkinter.LEFT,padx=10)

        password_frame = tkinter.Frame(master)
        password_frame.pack(fill=tkinter.X)
        password_label = tkinter.Label(password_frame,text=_("Password: "))
        password_label.pack(side=tkinter.LEFT)
        self.password = tkinter.Entry(password_frame,show="●")
        self.password.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
        self.password.bind("<Return>",self.apply)
        if self.default_password:
            self.password.insert(0,self.default_password)
        password_show = tkinter.Button(password_frame,text="👁")
        password_show.pack(side=tkinter.LEFT,padx=10)
        password_show.bind("<ButtonPress-1>",lambda event: self.password.configure(show=""))
        password_show.bind("<ButtonRelease-1>",lambda event: self.password.configure(show="●"))

        cache_frame = tkinter.Frame(master)
        cache_frame.pack(fill=tkinter.X)
        cache_label = tkinter.Label(cache_frame,text=_("Cache: "))
        cache_label.pack(side=tkinter.LEFT)
        cache_tip = ttkbootstrap.widgets.tooltip.ToolTip(cache_label,text=_("The cache temporarily stores file chunks to improve loading performance. 16 MB is recommended; the maximum should not exceed 512 MB."),delay=0)
        self.cache = tkinter.ttk.Combobox(cache_frame,values=[_("Diasbled"),"1 MB","2 MB","4 MB","8 MB","16 MB","32 MB","64 MB","128 MB","256 MB"])
        self.cache.pack(side=tkinter.LEFT,fill=tkinter.X,expand=True)
        self.cache_show = tkinter.Label(cache_frame)
        self.cache_show.pack(side=tkinter.LEFT,padx=10)
        self.cache.bind("<<ComboboxSelected>>",self.update_size)
        self.cache.bind("<KeyRelease>",self.update_size)
        self.cache.insert(tkinter.INSERT,shared.format_bytes(self.default_cache))
        
        if self.default_cache == 0:
            self.cache.current(0)
        self.update_size()

        self.info_show_password_var = tkinter.IntVar(value=0)
        info_show_passwords = ttkbootstrap.Checkbutton(master,text=_("Show salt and passwords (For debugging only)"),variable=self.info_show_password_var)
        info_show_passwords.pack(anchor=tkinter.W,padx=10)
        info_show_tip = ttkbootstrap.widgets.tooltip.ToolTip(info_show_passwords,text=_("When enabled, right-clicking and selecting File Info will display the salt, primary password, and secondary password. This feature is intended for debugging purposes only."),delay=0)

        buttons_frame = tkinter.Frame(master)
        buttons_frame.pack()
        ok_button = tkinter.Button(buttons_frame,text=_("Enter"),command=self.apply)
        ok_button.grid(row=0,column=0,ipadx=20,padx=20,pady=10)
        cancel_button = tkinter.Button(buttons_frame,text=_("Cancel"),command=self.top.destroy)
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
                tkinter.messagebox.showwarning(_("Cache size"),_("Cache too large ({size}), exceeding 512 MB. Opening a large file might trigger an OOM (Out of Memory) error.").format(size=shared.format_bytes(size)))
                self.warning = True
        else:
            self.cache_show.configure(fg="black")

class AboutWindow(Modal):
    def __init__(self,master):
        super().__init__(master,title=_("About FileEnclave"))
    def body(self,master):
        main = tkinter.Label(master,text="FileEnclave",font=(None,30))
        main.pack()
        ver = tkinter.Label(master,text=_("Version: {build_version} {current_build}").format(build_version=shared.build_version,current_build=shared.current_build))
        ver.pack()
        release = ttkbootstrap.Label(master,text=f"{shared.builds[shared.current_build]}",anchor="center",bootstyle=(release_colors[shared.current_build]))
        release.pack(fill=tkinter.X)
        slogan = tkinter.Label(master,text=_("May your digital assets find sanctuary here"),font=(None,10,"italic"),justify=tkinter.LEFT)
        slogan.pack()
        about_frame = tkinter.ttk.LabelFrame(master,text=_("About"))
        about_frame.pack(padx=10)
        desc_para1 = tkinter.Label(about_frame,text=_("Introduction"),font=(None,20),justify=tkinter.LEFT)
        desc_para1.pack(anchor=tkinter.W)
        desc_para2 = tkinter.Label(about_frame,text=_("A Linux-based file encryption tool for safeguarding sensitive data."),justify=tkinter.LEFT,wraplength=3000)
        desc_para2.pack(anchor=tkinter.W)
        desc_para3 = tkinter.Label(about_frame,text=_("Features"),font=(None,20),justify=tkinter.LEFT)
        desc_para3.pack(anchor=tkinter.W)
        desc_para4 = tkinter.Label(about_frame,text=_("Secure & Reliable:​ Utilizes the highly secure Argon2id algorithm for key derivation, combined with 7z encryption containers to effectively resist brute-force and plaintext attacks.\nEfficient & Flexible:​ Employs randomly generated internal keys for file encryption, eliminating the need to re-encrypt data when changing user passwords. Supports chunk-based storage and on-demand loading, enabling smooth handling of large files without excessive memory consumption.\nPrivacy-First:​ Leverages FUSE technology to mount files as a virtual filesystem during decryption. Data resides entirely in memory and vanishes instantly upon unmounting or unexpected power loss, mitigating the risk of disk residue.\nHigh Fault Tolerance:​ Supports the generation of recovery data (using PAR), allowing for partial repair of file corruption caused by storage media degradation.\nUser-Friendly:​ In addition to a fully-featured CLI tool, a graphical interface built with Tkinter (ttkbootstrap) is provided, ensuring an intuitive and streamlined user experience."),justify=tkinter.LEFT,wraplength=2000)
        desc_para4.pack(anchor=tkinter.W)
        desc_para5 = tkinter.Label(about_frame,text=_("Website"),font=(None,20),justify=tkinter.LEFT)
        desc_para5.pack(anchor=tkinter.W)
        desc_para6 = ttkbootstrap.Label(about_frame,text="Github：https://github.com/jzwalliser/FileEnclave",justify=tkinter.LEFT,foreground="#2222FF",cursor="hand2")
        desc_para6.pack(anchor=tkinter.W)
        desc_para6.bind("<ButtonRelease-1>",lambda event: webbrowser.open("https://github.com/jzwalliser/FileEnclave"))
        desc_para6.bind("<Enter>",lambda event: desc_para6.configure(foreground="#6666FF"))
        desc_para6.bind("<Leave>",lambda event: desc_para6.configure(foreground="#2222FF"))
        desc_para7 = tkinter.Label(about_frame,text=_("Credits"),font=(None,20),justify=tkinter.LEFT)
        desc_para7.pack(anchor=tkinter.W)
        desc_para8 = tkinter.Label(about_frame,text=_("Thanks to Yuanbao for providing some code for this project, Icons8 for the beautiful icons, and many other open-source library authors for providing easy-to-use libraries."),justify=tkinter.LEFT,wraplength=3000)
        desc_para8.pack(anchor=tkinter.W)
        
class FolderWindow(Modal):
    def __init__(self,master,folders):
        self.folders = folders
        super().__init__(master,title=_("Folders"),customize_button=True)
    def body(self,master):
        buttons = ttkbootstrap.LabelFrame(master,text=_("Folders"))
        buttons.pack(ipadx=500,padx=10)
        for i in self.folders:
            folder = tkinter.Button(buttons,text=i,anchor=tkinter.W,command=lambda folder=i: self.apply(folder))
            folder.pack(fill=tkinter.X,padx=10)
        cancel_button = tkinter.Button(self.top,text=_("Cancel"),command=self.top.destroy)
        cancel_button.pack(ipadx=20,padx=20,pady=10)
        self.result = None
    def apply(self,folder):
        self.result = folder
        self.top.destroy()
        
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
        repair_everything.configure(text=_("Repair done, open logs for results."))
        root.after(2000,lambda: repair_everything.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
        root.after(2000,lambda: repair_everything.configure(text=_("Check & Repair all files.")))
        root.after(4000,lambda: log_button.configure(bootstyle=ttkbootstrap.constants.PRIMARY))

    thread = threading.Thread(target=newthread)
    repair_everything.configure(state=tkinter.DISABLED)
    thread.start()

def repair_file(file):
    def newthread(file):
        repair = subprocess.Popen(["python3","repair.py","-f",file],stdout=subprocess.PIPE)
        repair.wait()
        output = repair.stdout.read().decode("utf-8")
        log(repair.stdout.read().decode("utf-8").rstrip())
        tkinter.messagebox.showinfo(_("Repair"),output)
        
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
        button.destroy()
        search_file(refresh=True)

def search_file(event=None,refresh=False):
    idx = 0
    search_results = 0
    search_strs = search_entry.get().split()

    for i in preview_buttons:
        add = True
        i.grid_forget()
        if (search_scope_var.get() == _("Folder") or refresh) and i.folder != current_dir:
            add = False
        for j in search_strs:
            add = add and j in i["text"]
        if add:
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
    folder = original_meta.get("folder","/")
    chunk_num = meta["chunks"]
    chunk_size = meta["chunk_size"]
    
    img = PIL.Image.open(io.BytesIO(sevenzipwrapper.read_file(archive,"preview",password=file_pwd)))
    img = img.resize((480,270))
    return archive,img,filename,folder,tags,size,chunk_num,chunk_size,salt,file_pwd,user_pwd

def hide_menu(event=None):
    global menu
    if menu:
        try:
            menu.unpost()
        except:
            pass
        menu = None

def parse(tags):
    ret = ""
    for i in tags:
        ret += " #" + i
    return ret

def on_loaded(future):
    global total
    try:
        archive,img,filename,folder,tags,size,chunk_num,chunk_size,salt,file_pwd,user_pwd = future.result()
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
        global current_button_count
        global folders
        with lock:
            row = current_button_count // columns
            col = current_button_count % columns
            btn = tkinter.Button(frame,text=filename + parse(tags),image=tk_img,command=lambda a=archive,f=filename: open_file(a,f),compound=tkinter.TOP,state=state,wraplength=450)

            def show_menu(event):
                global menu
                if menu:
                    hide_menu()
                file_info = _("File info\n")
                file_info += _("Path: {path}\n").format(path=pathlib.Path(archive).parent)
                file_info += _("Encrypted: {crypt}\n").format(crypt=pathlib.Path(archive).name)
                file_info += _("Filename: {filename}\n").format(filename=filename)
                file_info += _("Size: {formatted} ({size} Bytes)\n").format(formatted=shared.format_bytes(size),size=size)
                file_info += _("Storage info\n")
                file_info += _("Chunks: {chunk_num}\n").format(chunk_num=chunk_num)
                file_info += _("Chunk size: {formatted} ({chunk_size} Bytes)\n").format(formatted=shared.format_bytes(chunk_size),chunk_size=chunk_size)
                if tags:
                    file_info += _("Other info\n")
                    file_info += _("Tags: {tags}\n").format(tags=parse(tags))
                if info_password:
                    file_info += _("Encryption info\n")
                    file_info += _("Salt: {salt}\n").format(salt=salt)
                    file_info += _("Primary Password: {user_pwd}\n").format(user_pwd=user_pwd)
                    file_info += _("Secondary Password: {file_pwd}\n").format(file_pwd=file_pwd)
                
                menu = tkinter.Menu(btn,tearoff=0)
                menu.add_command(label=_("Repair"),command=lambda: repair_file(archive))
                menu.add_command(label=_("Delete"),command=lambda: delete_file(archive,filename,btn))
                menu.add_command(label=_("File Info"),command=lambda: InfoWindow(root,file_info))
                menu.post(event.x_root,event.y_root)
                
            btn.image = tk_img
            btn.bind("<Button-3>",show_menu)
            btn.folder = folder
            folders |= {folder}
            if folder == current_dir:
                btn.grid(row=row,column=col,padx=5,pady=5)
                current_button_count += 1
            preview_buttons += [btn]
            load_indicator.configure(text=_("Loading: {loaded}/{total}").format(loaded=len(preview_buttons),total=total),value=int(len(preview_buttons) / total * 100))
            if len(preview_buttons) == total:
                load_indicator.configure(bootstyle=ttkbootstrap.constants.SUCCESS)
                root.after(1000,lambda: load_indicator.configure(text=_("Finished loading")))
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

def on_drop(event):
    print("DND")
    for i in root.tk.splitlist(event.data):
        subprocess.Popen(["python3","creator_gui.py","-f",i,"-p",user_password,"-d",current_dir],stdout=sys.stdout,stderr=sys.stderr)
    
def switch_folder():
    global current_dir
    window = FolderWindow(root,folders)
    result = window.result
    if result:
        current_dir = result
        search_file(refresh=True)
        folder_button.configure(text=_("Current folder: ") + result)

def scroll_up(event):
    canvas.yview_scroll(-1,tkinter.UNITS)

def scroll_down(event):
    canvas.yview_scroll(1,tkinter.UNITS)

root = Tk()
root.title("FileEnclave")
root.withdraw()

if shared.current_build == "Alpha" or shared.current_build == "Beta":
    release = ttkbootstrap.Label(root,text=f"{shared.current_build}: {shared.builds[shared.current_build]}",anchor="center",bootstyle=(ttkbootstrap.constants.INVERSE,release_colors[shared.current_build]))
    release.pack(fill=tkinter.X)
    
top_banner = tkinter.ttk.Frame(root)
top_banner.pack(fill=tkinter.X)

search_frame = tkinter.ttk.LabelFrame(top_banner,text=_("Search"))
search_frame.grid(row=0,column=0,padx=20)

search_entry = tkinter.Entry(search_frame)
search_entry.grid(row=0,column=0,padx=(5,0),pady=10,ipadx=520)
search_entry.bind("<KeyRelease>",search_file)

search_modes = [_("Global"),_("Folder")]
search_scope_var = tkinter.StringVar(value=search_modes[0])
search_scope = tkinter.OptionMenu(search_frame,search_scope_var,*search_modes)
search_scope.grid(row=0,column=2,pady=10)
search_scope_tip = ttkbootstrap.widgets.tooltip.ToolTip(search_scope,text=_("When you choose \"Global\", it searches everywhere; if you choose \"Folder\", it only searches within the current folder."),delay=0)

search_reset = ttkbootstrap.Button(search_frame,text="×",command=reset_search,cursor="arrow",bootstyle=ttkbootstrap.constants.LINK)
search_reset.grid(row=0,column=1,padx=(0,5),pady=10)

log_button = ttkbootstrap.Button(top_banner,text=_("Logs"),command=lambda: LogWindow(root,logs))
log_button.grid(row=0,column=1,padx=10)
log_tip = ttkbootstrap.widgets.tooltip.ToolTip(log_button,text=_("The log shows some debugging information while the software is running."),delay=0)

umount_button = tkinter.ttk.Button(top_banner,text=_("Unount"),command=on_umount)
umount_button.grid(row=0,column=2,padx=10)
umount_tip = ttkbootstrap.widgets.tooltip.ToolTip(umount_button,text=_("Unmount the currently mounted FUSE file system. After clicking, you can open other encrypted files. If issues occur, clicking the button might also fix them."),delay=0)

repair_everything = ttkbootstrap.Button(top_banner,text=_("Check & Repair all files"),command=repair_all)
repair_everything.grid(row=0,column=3,padx=10)
repair_tip = ttkbootstrap.widgets.tooltip.ToolTip(repair_everything,text=_("Scans files within the specified path for corruption and attempts to repair them."),delay=0)

add_button = ttkbootstrap.Button(top_banner,text=_("Add Files"),command=lambda: subprocess.Popen(["python3","creator_gui.py","-o",archive_dir]))
add_button.grid(row=0,column=4,padx=10)

about = ttkbootstrap.Button(top_banner,text=_("About"),command=lambda: AboutWindow(root))
about.grid(row=0,column=5,padx=10)

folder_button = tkinter.Button(root,text=_("Current folder: ") + "/",command=switch_folder)
folder_button.pack(fill=tkinter.X)

preview_frame = tkinter.Frame()
preview_frame.pack(fill=tkinter.BOTH,expand=True,ipady=350)
canvas = tkinter.Canvas(preview_frame)
scrollbar = tkinter.ttk.Scrollbar(preview_frame,orient=tkinter.VERTICAL,command=canvas.yview)
frame = tkinter.ttk.Frame(canvas)
frame.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox(tkinter.ALL)))
canvas.create_window((0,0),window=frame,anchor=tkinter.NW)
canvas.configure(yscrollcommand=scrollbar.set)
canvas.bind_all("<Button-4>",scroll_up)
canvas.bind_all("<Button-5>",scroll_down)
canvas.pack(side=tkinter.LEFT,fill=tkinter.BOTH,expand=True)
scrollbar.pack(side="right",fill=tkinter.Y)

root.drop_target_register(tkinterdnd2.DND_FILES)
root.dnd_bind("<<Drop>>",on_drop)

load_indicator = ttkbootstrap.Floodgauge(root,text=_("Loading: 0/0"))
load_indicator.pack(fill=tkinter.X)
root.protocol("WM_DELETE_WINDOW",on_close)

root.bind("<Button-1>",hide_menu)
root.after(100,load_archives)
root.mainloop()
