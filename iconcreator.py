#!/usr/bin/python3
from PIL import Image, ImageDraw, ImageFont

# ---------- 参数 ----------
img_size = (800, 800)                # 正方形画布
bg_color = (0, 0, 0)                 # 黑色背景
icon_color = (255, 255, 255)         # 白色图标
emoji = "▶"                           # 播放按钮（几何符号，不是 emoji）

# ---------- 字体 ----------
# Linux（绝大多数系统都有）
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# macOS
# font_path = "/System/Library/Fonts/Helvetica.ttc"

# Windows
# font_path = "C:/Windows/Fonts/arialbd.ttf"

font_size = 109  # hardcode，避免 invalid pixel size

# ---------- 创建画布 ----------
img = Image.new("RGB", img_size, bg_color)
draw = ImageDraw.Draw(img)

# ---------- 加载字体 ----------
font = ImageFont.truetype(font_path, font_size)

# ---------- 计算居中 ----------
bbox = font.getmask(emoji).getbbox()
emoji_w = bbox[2] - bbox[0]
emoji_h = bbox[3] - bbox[1]

x = (img_size[0] - emoji_w) // 2
y = (img_size[1] - emoji_h) // 2

# ---------- 绘制 ----------
draw.text((x, y), emoji, font=font, fill=icon_color)

# ---------- 保存 ----------
img.save("video_icon.png")
