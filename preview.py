#!/usr/bin/python3
import cv2
import PIL.Image
import PIL.ImageOps
import io
import pathlib
import traceback
import pdf2image

def preview(file_path,quality=100,max_width=960,max_height=540):
    if pathlib.Path(file_path).suffix in ".".join(["jpeg","jpg","jpe","jfif","png","webp","tiff","tif","jp2","jpx","avif","gif","bmp","mp4","mov","avi","mkv","webm","flv","ts","mpg"]):
        try:
            return add_background(preview_media(file_path,max_width=960,max_height=540),width=960,height=540)
        except:
            traceback.print_exc()
            return
    elif pathlib.Path(file_path).suffix in ".pdf":
        try:
            return add_background(preview_pdf(file_path,max_width=960,max_height=540),width=960,height=540)
        except:
            traceback.print_exc()
            return
    else:
        return


def preview_media(video_path,max_width=960,max_height=540):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Failed to open video.")

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Failed to read the first ")

    # BGR -> RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # numpy -> PIL Image
    pil_img = PIL.Image.fromarray(frame_rgb)

    # ---------- 新增：等比例缩放 ----------
    orig_width, orig_height = pil_img.size
    scale = min(max_width / orig_width, max_height / orig_height, 1.0)

    if scale < 1.0:
        new_size = (
            int(orig_width * scale),
            int(orig_height * scale)
        )
        pil_img = pil_img.resize(new_size, PIL.Image.LANCZOS)
    return pil_img

def preview_pdf(pdf_path,max_width=960,max_height=540,dpi=200):
    images = pdf2image.convert_from_path(pdf_path,dpi=dpi,first_page=1,last_page=1,fmt="jpeg")
    if not images:
        raise RuntimeError("Pdf empty or corrupt.")
    img = images[0]
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    pil_img = PIL.Image.open(io.BytesIO(buf.getvalue()))
    pil_img.load()
    return pil_img

def add_background(img,width=960,height=540,quality=100):
    pil_img = PIL.ImageOps.pad(
        img,
        (width,height),
        method=PIL.Image.Resampling.LANCZOS,  # 不缩放，仅用于插值策略
        color=(0,0,0),
        centering=(0.5, 0.5)  # 居中
    )
    # --------------------------------------
    

    # 保存到内存
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG", quality=quality, optimize=True)

    return buffer.getvalue()
