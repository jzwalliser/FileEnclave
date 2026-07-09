#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import json
import subprocess
import os
from tkinterdnd2 import DND_FILES, TkinterDnD

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
root = TkinterDnD.Tk()
root.title("Creator GUI Tool")
root.geometry("1180x960")

file_path = None

# ========================
# 左右分栏 PanedWindow
# ========================
main_pane = tk.PanedWindow(root, orient="horizontal", sashrelief="raised")
main_pane.pack(fill="both", expand=True, padx=10, pady=10)

# ---- 左侧面板 ----
left_frame = tk.Frame(main_pane, padx=10, pady=10)
main_pane.add(left_frame, minsize=420)

# ---- 右侧面板 ----
right_frame = tk.Frame(main_pane, padx=10, pady=10)
main_pane.add(right_frame, minsize=420)

# ========================
# 左侧：拖拽区域
# ========================
drop_frame = tk.LabelFrame(left_frame, text="拖拽文件到此处", width=400, height=150)
drop_frame.pack(ipady=30, pady=(0, 10), fill="x")
drop_frame.pack_propagate(False)

drop_label = tk.Label(drop_frame, text="📂 拖拽一个文件进来", fg="gray")
drop_label.pack(expand=True)

def on_drop(event):
    global file_path
    file_path = event.data.strip().strip("{}")
    drop_label.config(text=f"✅ 已选择文件:\n{file_path}", fg="green")

try:
    drop_frame.drop_target_register(DND_FILES)
    drop_frame.dnd_bind("<<Drop>>", on_drop)
except ImportError:
    drop_label.config(text="⚠️ 不支持拖拽（请安装 tkinterdnd2）")

# ========================
# 左侧：密码
# ========================
frame_pwd = tk.Frame(left_frame)
frame_pwd.pack(fill="x", pady=5)

tk.Label(frame_pwd, text="密码：").pack(side="left")
user_password_var = tk.StringVar(value=password)
tk.Entry(frame_pwd, textvariable=user_password_var, show="*", width=30).pack(side="left", padx=5)

# ========================
# 左侧：rec 滑块
# ========================
frame_rec = tk.Frame(left_frame)
frame_rec.pack(fill="x", pady=5)

tk.Label(frame_rec, text="rec（0–100）：").pack(side="left")
rec_var = tk.IntVar(value=rec_percentage)
tk.Scale(
    frame_rec, from_=0, to=100, orient="horizontal", variable=rec_var
).pack(side="left", fill="x", expand=True)

# ========================
# 左侧：chunk_size
# ========================
frame_chunk = tk.Frame(left_frame)
frame_chunk.pack(fill="x", pady=5)

tk.Label(frame_chunk, text="chunk_size：").pack(side="left")
chunk_size_var = tk.IntVar(value=chunk_size)
tk.Spinbox(
    frame_chunk, from_=1, to=100000000, textvariable=chunk_size_var, width=15
).pack(side="left", padx=5)

# ========================
# 左侧：执行按钮
# ========================
def sha1_md5(file_path: str) -> str:
    with open(file_path, "rb") as f:
        sha1 = hashlib.sha1(f.read()).hexdigest()
    return hashlib.md5(sha1.encode("utf-8")).hexdigest()

def run_creator():
    global file_path

    if not file_path or not os.path.exists(file_path):
        messagebox.showerror("错误", "请先拖拽一个文件")
        return

    if not user_password_var.get():
        messagebox.showerror("错误", "请输入密码")
        return

    try:
        output_hash = sha1_md5(file_path)
    except Exception as e:
        messagebox.showerror("Hash 错误", str(e))
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

    try:
        subprocess.run(cmd, check=True)
        messagebox.showinfo("成功", "creator.py 执行完成 ✅")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("执行失败", str(e))

tk.Button(
    left_frame, text="🚀 执行 creator.py",
    bg="#4CAF50", fg="white", height=2,
    command=run_creator
).pack(fill="x", pady=15)

# ============================================================
# 右侧：Tags 区域（全部移到这里）
# ============================================================
right_container = tk.LabelFrame(right_frame, text="标签设置")
right_container.pack(fill="both", expand=True)

# Tags 输入框
frame_tags = tk.Frame(right_container)
frame_tags.pack(fill="x", padx=10, pady=10)

tk.Label(frame_tags, text="标签（空格分隔）：").pack(anchor="w")
tags_var = tk.StringVar()
tk.Entry(frame_tags, textvariable=tags_var, width=30).pack(fill="x", pady=(5, 10))

# 快捷标签按钮
frame_buttons = tk.Frame(right_container)
frame_buttons.pack(fill="both", expand=True, padx=10, pady=(0, 10))

def add_tag(tag):
    current = tags_var.get().strip()
    if current and not current.endswith(" "):
        tags_var.set(current + " " + tag)
    else:
        tags_var.set(current + tag)

for i, tag in enumerate(tags):
    tk.Button(
        frame_buttons, text=tag, width=8,
        command=lambda t=tag: add_tag(t)
    ).grid(row=i // 3, column=i % 3, padx=5, pady=5, sticky="w")

# ========================
# 启动
# ========================
root.mainloop()
