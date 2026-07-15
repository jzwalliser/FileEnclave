#!/usr/bin/python3
import cv2
import PIL.Image
import PIL.ImageOps
import io
import pathlib
import traceback
import pdf2image
import chardet
import cairo
import pygments
import pygments.lexers
import pygments.formatters
import gi
gi.require_version("Pango","1.0")
gi.require_version("PangoCairo","1.0")
import gi.repository.Pango
import gi.repository.PangoCairo
import mimetypes

mimetypes.add_type("text/x-python",".pyw")
mimetypes.add_type("image/webp",".webp")
mimetypes.add_type("text/json",".json")

def preview(file_path,quality=100,max_width=960,max_height=540):
    ftype = mimetypes.guess_type(file_path)
    if ftype[0] == None:
        img = load_icon("file.png")
    else:
        main = ftype[0].split("/")[0]
        sub = ftype[0].split("/")[1]
        maindict = {"image":(preview_media,"image_file.png"),"video":(preview_media,"video_file.png"),"text":(preview_text,"document_file.png"),"audio":(preview_audio,"audio_file.png")}
        typedict = {"application/pdf":(preview_pdf,"pdf.png")}
        if main in maindict.keys():
            try:
                img = maindict[main][0](file_path)
            except:
                traceback.print_exc()
                img = load_icon(maindict[main][1])
        elif ftype[0] in typedict.keys():
            print("pdf")
            try:
                img = typedict[ftype[0]][0](file_path)
            except:
                img = load_icon(typedict[ftype[0]])
        elif pathlib.Path(file_path).suffix in "." + ".".join(["7z","apk","dll","dmg","doc","exe","otf","ppt","ps","rar","tar","woff","zip","pptx","docx"]):
            img = load_icon(f"{pathlib.Path(file_path).suffix[1:]}.png")
        else:
            img = load_icon("file.png")
    return add_background(img)

def preview_media(video_path,max_width=960,max_height=540):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Failed to open video.")

    ret,frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Failed to read the first ")

    frame_rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    pil_img = PIL.Image.fromarray(frame_rgb)
    orig_width,orig_height = pil_img.size
    scale = min(max_width / orig_width,max_height / orig_height,1.0)

    if scale < 1.0:
        new_size = (int(orig_width * scale),int(orig_height * scale))
        pil_img = pil_img.resize(new_size,PIL.Image.LANCZOS)
    return pil_img

def preview_pdf(pdf_path,max_width=960,max_height=540,dpi=200):
    images = pdf2image.convert_from_path(pdf_path,dpi=dpi,first_page=1,last_page=1,fmt="jpeg")
    if not images:
        raise RuntimeError("Pdf empty or corrupt.")
    pil_img = images[0]
    pil_img.convert("RGB")
    return pil_img
    
def preview_text(text_path,max_width=960,max_height=540):
    handler = open(text_path,"rb")
    content_b = handler.read()
    content = content_b.decode(chardet.detect(content_b)["encoding"],errors='ignore')

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,max_width,max_height)
    ctx = cairo.Context(surface)

    markup = pygments.highlight(content,pygments.lexers.get_lexer_for_filename(text_path),pygments.formatters.PangoMarkupFormatter(style="monokai"))
    layout = gi.repository.PangoCairo.create_layout(ctx)
    font_desc = gi.repository.Pango.FontDescription("Consolas 18")
    layout.set_font_description(font_desc)
    layout.set_markup(markup,-1)
    layout.set_width(max_width * gi.repository.Pango.SCALE)
    layout.set_wrap(gi.repository.Pango.WrapMode.WORD_CHAR)
    ctx.set_source_rgba(0,0,0,1)
    gi.repository.PangoCairo.show_layout(ctx,layout)
    data = surface.get_data()
    pil_img = PIL.Image.frombuffer("RGBA",(max_width,max_height),data,"raw","BGRA",0,1)
    pil_img = pil_img.convert("RGB")
    return pil_img

def preview_audio(audio_path,max_width=960,max_height=540):
    return load_icon("audio_file.png")

def add_background(img,width=960,height=540,quality=100,background=(0,0,0)):
    pil_img = PIL.ImageOps.pad(img,(width,height),method=PIL.Image.Resampling.LANCZOS,color=background,centering=(0.5,0.5)) #把图片贴在黑色背景正中央
    buffer = io.BytesIO() #保存到内存
    pil_img.save(buffer,format="JPEG",quality=quality,optimize=True)
    return buffer.getvalue()

def load_icon(icon):
    img = PIL.Image.open(f"./icons/{icon}")
    return img.convert("RGB")

def preview_to_file(path,file="temp.jpg"):
    with open(file,"wb") as f:
        f.write(preview(path))
