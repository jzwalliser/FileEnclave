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


class Tk(ttkbootstrap.Window,tkinterdnd2.TkinterDnD.Tk): pass

# ========================
# 配置加载
# ========================
rec_percentage = 0
chunk_size = 2079152
tags = ["娱乐", "电影", "科技", "生活", "感情"]
path = "./archive"
password = ""

try:
    with open("config.json", "rb") as conf:
        config = json.loads(conf.read().decode("utf-8"))
except Exception:
    pass
else:
    rec_percentage = config.get("rec", rec_percentage)
    chunk_size = config.get("chunk_size", chunk_size)
    tags = config.get("tags", tags)
    path = config.get("creator_path", path)
    password = config.get("password", password)

# ========================
# 主窗口
# ========================
root = Tk()
root.title("Creator GUI Tool")
root.geometry("1180x960")

file_path = None

# ========================
# 左右分栏 PanedWindow
# ========================
main_pane = tkinter.PanedWindow(root, orient="horizontal", sashrelief="raised")
main_pane.pack(fill="both", expand=True, padx=10, pady=10)

# ---- 左侧面板 ----
left_frame = tkinter.Frame(main_pane, padx=10, pady=10)
main_pane.add(left_frame, minsize=420)

# ---- 右侧面板 ----
right_frame = tkinter.Frame(main_pane, padx=10, pady=10)
main_pane.add(right_frame, minsize=420)

# ========================
# 左侧：拖拽区域
# ========================
drop_frame = tkinter.LabelFrame(left_frame, text="拖拽文件到此处", width=400, height=150)
drop_frame.pack(ipady=30, pady=(0, 10), fill="x")
drop_frame.pack_propagate(False)

drop_label = tkinter.Label(drop_frame, text="📂 拖拽一个文件进来", fg="gray",wraplength=450)
drop_label.pack(expand=True)

preview_pic = tkinter.Label(left_frame,text="预览图")
preview_pic.pack(ipady=0, pady=(0, 10), fill="x")
tk_img = None

def on_drop(event):
    global file_path
    global tk_img
    file_path = event.data.strip().strip("{}")
    drop_label.config(text=f"✅ 已选择文件:\n{file_path}", fg="green")
    preview_bytes = preview.preview(file_path)
    img = PIL.Image.open(io.BytesIO(preview_bytes))
    img = img.resize((480,270))
    tk_img = PIL.ImageTk.PhotoImage(img)
    preview_pic.configure(image=tk_img)

drop_frame.drop_target_register(tkinterdnd2.DND_FILES)
drop_frame.dnd_bind("<<Drop>>", on_drop)
    

# ========================
# 左侧：密码
# ========================
frame_pwd = tkinter.Frame(left_frame)
frame_pwd.pack(fill="x", pady=5)

tkinter.Label(frame_pwd, text="密码：").pack(side="left")
user_password_var = tkinter.StringVar(value=password)
tkinter.Entry(frame_pwd, textvariable=user_password_var, show="*", width=30).pack(side="left", padx=5)

# ========================
# 左侧：rec 滑块
# ========================
frame_rec = tkinter.Frame(left_frame)
frame_rec.pack(fill="x", pady=5)

tkinter.Label(frame_rec, text="rec（0–100）：").pack(side="left")
rec_var = tkinter.IntVar(value=rec_percentage)
tkinter.Scale(
    frame_rec, from_=0, to=100, orient="horizontal", variable=rec_var
).pack(side="left", fill="x", expand=True)

# ========================
# 左侧：chunk_size
# ========================
frame_chunk = tkinter.Frame(left_frame)
frame_chunk.pack(fill="x", pady=5)

tkinter.Label(frame_chunk, text="chunk_size：").pack(side="left")
chunk_size_var = tkinter.IntVar(value=chunk_size)
tkinter.Spinbox(
    frame_chunk, from_=1, to=100000000, textvariable=chunk_size_var, width=15
).pack(side="left", padx=5)

# ========================
# 左侧：执行按钮
# ========================
def sha1_md5(file_path):
    with open(file_path, "rb") as f:
        sha1 = hashlib.sha1(f.read()).hexdigest()
    return hashlib.md5(sha1.encode("utf-8")).hexdigest()

def run_cmd(cmd):
    try:
        proc = subprocess.run(cmd,check=True)
    except subprocess.CalledProcessError as e:
        err = e
    else:
        err = None
    finally:
        root.after(0, on_finish, err)

def on_finish(err):
    if err:
        tkinter.messagebox.showerror("执行失败", str(e))
    else:
        tkinter.messagebox.showinfo("成功", "creator.py 执行完成 ✅")

def run_creator():
    global file_path
    if not file_path or not os.path.exists(file_path):
        tkinter.messagebox.showerror("错误", "请先拖拽一个文件")
        return

    if not user_password_var.get():
        tkinter.messagebox.showerror("错误", "请输入密码")
        return

    try:
        output_hash = sha1_md5(file_path)
    except Exception as e:
        tkinter.messagebox.showerror("Hash 错误", str(e))
        return

    tags_raw = tags_var.get().strip()
    tags_list = [t.strip() for t in tags_raw.split() if t.strip()]
    tags_json = ",".join(f'"{t}"' for t in tags_list)

    cmd = [
        "python3", "creator.py",
        file_path,
        f"{path}/{output_hash}.7z",
        user_password_var.get(),
        "-y",
        "-m", f'{{"tags":[{tags_json}]}}',
        "-c", str(chunk_size)
    ]
    
    if rec_percentage != 0:
        print("rec")
        cmd += ["-r",str(rec_percentage)]

    threading.Thread(target=run_cmd,args=[cmd],daemon=True).start()

tkinter.Button(
    left_frame, text="🚀 执行 creator.py",
    bg="#4CAF50", fg="white", height=2,
    command=run_creator
).pack(fill="x", pady=15)

# ============================================================
# 右侧：Tags 区域（全部移到这里）
# ============================================================
right_container = tkinter.LabelFrame(right_frame, text="标签设置")
right_container.pack(fill="both", expand=True)

edit_mode = False
def edit():
    global edit_mode
    if edit_mode:
        edit_mode = False
        edit_tags.configure(text="编辑标签",bootstyle=ttkbootstrap.constants.PRIMARY)
        tag_append.grid_forget()
    else:
        edit_mode = True
        edit_tags.configure(text="完成编辑（右键标签即可将其删除）",bootstyle=ttkbootstrap.constants.SUCCESS)
        tag_append.grid(row=len(tag_buttons) // 3, column=len(tag_buttons) % 3, padx=5, pady=5, sticky="w")

# Tags 输入框
frame_tags = tkinter.Frame(right_container)
frame_tags.pack(fill="x", padx=10, pady=10)

edit_tags = ttkbootstrap.Button(frame_tags,text="编辑标签",command=edit)
edit_tags.pack(fill="x")

tags_label = tkinter.Label(frame_tags, text="标签（空格分隔）：")
tags_label.pack(anchor="w")
tags_var = tkinter.StringVar()
tkinter.Entry(frame_tags, textvariable=tags_var, width=30).pack(fill="x", pady=(5, 10))


# 快捷标签按钮
frame_buttons = tkinter.Frame(right_container)
frame_buttons.pack(fill="both", expand=True, padx=10, pady=(0, 10))
tag_buttons = []

def user_add(event):
    tag_name = tag_append.get()
    for i in tag_buttons:
        if i["text"] == tag_name:
            i.configure(bootstyle=(ttkbootstrap.constants.INFO,ttkbootstrap.constants.OUTLINE))
            root.after(1000,lambda btn=i: i.configure(bootstyle=ttkbootstrap.constants.PRIMARY))
            return
    add_tag(tag_name)
    tag_append.grid(row=len(tag_buttons) // 3, column=len(tag_buttons) % 3, padx=5, pady=5, sticky="w")
    tag_append.delete(0,tkinter.END)
    
tag_append = tkinter.Entry(frame_buttons,width=9)
tag_append.bind("<Return>",user_add)

def del_tag(event,tag):
    if not edit_mode:
        return
    for i in tag_buttons:
        print(i["text"],tag)
        if i["text"] == tag:
            tag_buttons.remove(i)
            break
    for i in range(len(tag_buttons)):
        tag_buttons[i].grid(row=i // 3, column=i % 3, padx=5, pady=5, sticky="w")
    tag_append.grid(row=len(tag_buttons) // 3, column=len(tag_buttons) % 3, padx=5, pady=5, sticky="w")

def insert_tag(tag):
    current = tags_var.get().strip()
    if current and not current.endswith(" "):
        tags_var.set(current + " " + tag)
    else:
        tags_var.set(current + tag)

def add_tag(tag):
    for i in tag_buttons:
        if i["text"] == tag:
            return
    tag_button = ttkbootstrap.Button(
        frame_buttons, text=tag, width=8,
        command=lambda t=tag: insert_tag(t)
    )
    tag_button.grid(row=len(tag_buttons) // 3, column=len(tag_buttons) % 3, padx=5, pady=5, sticky="w")
    tag_button.bind("<Button-3>",lambda event,t=tag: del_tag(event,t))
    tag_buttons.append(tag_button)

for i in tags:
    add_tag(i)
    

# ========================
# 启动
# ========================
root.mainloop()
