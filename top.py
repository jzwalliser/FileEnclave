from tkinter import Button
import tkinter
root = tkinter.Tk()

btn = Button(
    root,
    text="很长的文字",
    wraplength=120   # ✅ 支持
)

btn.pack()
