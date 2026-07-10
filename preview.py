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

def preview(file_path,quality=100,max_width=960,max_height=540):
    if pathlib.Path(file_path).suffix in "." + ".".join(["jpeg","jpg","jpe","jfif","png","webp","tiff","tif","jp2","jpx","avif","gif","bmp","mp4","mov","avi","mkv","webm","flv","ts","mpg"]):
        try:
            return add_background(preview_media(file_path,max_width=960,max_height=540),width=960,height=540)
        except:
            return add_background(PIL.Image.open("./icons/video_file.png").convert("RGB"))
    elif pathlib.Path(file_path).suffix in ".pdf":
        try:
            return add_background(preview_pdf(file_path,max_width=960,max_height=540),width=960,height=540)
        except:
            return add_background(PIL.Image.open("./icons/image_file.png").convert("RGB"))
    elif pathlib.Path(file_path).suffix in "." + ".".join(["md","a","a51","ada","adb","ads","ahk","aj","ampl","apib","apl","applescript","arc","as","asc","ascx","ash","ashx","asm","asmx","asp","aspx","au3","aug","awk","b","bas","bash","bb","befunge","bf","bib","bmx","boo","bro","brs","bsv","bzl","c","c++","capnp","cbl","cc","ccm","ceylon","cgi","chpl","chs","cjs","clj","cljc","cljs","clp","cls","cmake","cmakein","cob","coffee","coffeescript","cpp","cppm","cpy","cr","cs","csh","cshtml","csx","cxx","d","dart","dats","db2","ddl","decls","dml","dpk","dpr","dyalog","e","ecl","el","elm","em","erl","ex","exs","f","f03","f08","f77","f90","f95","for","frm","fs","fsi","fsx","fun","g4","gawk","go","groovy","gsh","gvy","gy","h","hats","hh","hpp","hqf","hrl","hs","htm","html","hxx","i","inc","ino","jav","java","jl","js","json","jsp","jspx","jsx","ksh","kt","kts","l","lhs","lisp","lsl","lsp","lss","lua","m","mawk","mjs","ml","mli","mm","mod","mss","n","nasm","nim","nims","nix","o","obj","odin","opal","p","pas","php","php3","php4","php5","phps","phtml","pkl","pl","plx","pm","pp","prc","pro","ps1","psd1","psm1","purs","pxd","pxi","py","pyw","pyx","r","rake","rb","re","rei","rhtml","rkt","rktd","rktl","rpy","rq","rs","rsin","ru","s","sage","sagews","sass","sats","sbt","sc","scala","scaml","scd","sce","sci","scm","scpt","scss","self","sh","shen","sl","sld","sls","sma","smali","sml","smt","smt2","sp","sparql","sqf","sql","sqlpl","ss","st","stan","ston","sty","styl","sv","svelte","svh","swift","t","tcl","tcsh","tex","tm","toml","trg","ts","tsx","txt","v","vala","vapi","vb","vba","vbe","vbs","vh","vpr","vue","wast","wat","wsc","wsf","xhtml","xml","xsd","xslt","yaml","yml","zig","zsh"]):
        try:
            return add_background(preview_text(file_path,max_width=960,max_height=540),width=960,height=540)
        except:
            traceback.print_exc()
            return add_background(PIL.Image.open("./icons/document_file.png").convert("RGB"))
    elif pathlib.Path(file_path).suffix in "." + ".".join(["mp3","wav","aac","m4a","flac","ogg","wma"]):
        print("audio")
        return add_background(PIL.Image.open("./icons/audio_file.png").convert("RGB"))
    elif pathlib.Path(file_path).suffix in "." + ".".join(["7z","apk","dll","dmg","doc","exe","otf","ppt","ps","rar","tar","woff","zip","pptx","docx"]):
        return add_background(PIL.Image.open(f"./icons/{pathlib.Path(file_path).suffix[1:]}.png").convert("RGB"))
    else:
        return add_background(PIL.Image.open("./icons/file.png").convert("RGB"))


def preview_media(video_path,max_width=960,max_height=540):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Failed to open video.")

    ret,frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Failed to read the first ")

    # BGR -> RGB
    frame_rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

    # numpy -> PIL Image
    pil_img = PIL.Image.fromarray(frame_rgb)

    # ---------- 新增：等比例缩放 ----------
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
    img = images[0]
    buf = io.BytesIO()
    img.save(buf,format="JPEG",quality=95)
    pil_img = PIL.Image.open(io.BytesIO(buf.getvalue()))
    pil_img.load()
    return pil_img
    
def preview_text(text_path,max_width=960,max_height=540):
    handler = open(text_path,"rb")
    content_b = handler.read()
    content = content_b.decode(chardet.detect(content_b)["encoding"],errors='ignore')

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,max_width,max_height)
    ctx = cairo.Context(surface)

    markup = pygments.highlight(
        content,
        pygments.lexers.get_lexer_for_filename(text_path),
        pygments.formatters.PangoMarkupFormatter(style="monokai")
    )

    # 2. Pango layout
    layout = gi.repository.PangoCairo.create_layout(ctx)
    font_desc = gi.repository.Pango.FontDescription("Consolas 18")
    layout.set_font_description(font_desc)
    layout.set_markup(markup,-1)
    layout.set_width(max_width * gi.repository.Pango.SCALE)
    layout.set_wrap(gi.repository.Pango.WrapMode.WORD_CHAR)

    # 3. 绘制文字
    ctx.set_source_rgba(0,0,0,1)
    gi.repository.PangoCairo.show_layout(ctx,layout)

    # 4. 转成 Pillow Image
    data = surface.get_data()
    pil_img = PIL.Image.frombuffer(
        "RGBA",(max_width,max_height),data,"raw","BGRA",0,1
    )
    pil_img = pil_img.convert("RGB")
    return pil_img

def add_background(img,width=960,height=540,quality=100,background=(0,0,0)):
    pil_img = PIL.ImageOps.pad(
        img,
        (width,height),
        method=PIL.Image.Resampling.LANCZOS, # 不缩放，仅用于插值策略
        color=background,
        centering=(0.5,0.5)  # 居中
    )
    # --------------------------------------
    

    # 保存到内存
    buffer = io.BytesIO()
    pil_img.save(buffer,format="JPEG",quality=quality,optimize=True)

    return buffer.getvalue()

def preview_to_file(path,file="temp.jpg"):
    with open(file,"wb") as f:
        f.write(preview(path))
