"""Generate the app icon (PNG + multi-size ICO). Run: python packaging/make_icon.py"""

import io
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SIZE = 256

doc = pymupdf.open()
page = doc.new_page(width=SIZE, height=SIZE)
red = (180 / 255, 101 / 255, 12 / 255)  # Vantage amber #B4650C
shape = page.new_shape()
shape.draw_rect(pymupdf.Rect(8, 8, SIZE - 8, SIZE - 8), radius=0.22)
shape.finish(color=red, fill=red)
# white page with folded corner
shape.draw_polyline([(76, 52), (148, 52), (184, 88), (184, 204), (76, 204), (76, 52)])
shape.finish(color=(1, 1, 1), fill=(1, 1, 1), closePath=True)
shape.draw_polyline([(148, 52), (148, 88), (184, 88)])
shape.finish(color=(0.85, 0.85, 0.88), fill=(0.85, 0.85, 0.88), closePath=True)
# redaction bars
for y, w in ((112, 84), (136, 60), (160, 76)):
    shape.draw_rect(pymupdf.Rect(92, y, 92 + w, y + 12))
    shape.finish(color=(0.12, 0.13, 0.16), fill=(0.12, 0.13, 0.16))
shape.commit()
pix = page.get_pixmap(alpha=True, clip=page.rect)
img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
# make the area outside the rounded square transparent
px = img.load()
for x in range(SIZE):
    for y in range(SIZE):
        r, g, b, a = px[x, y]
        if r > 250 and g > 250 and b > 250 and (x < 10 or y < 10 or x > SIZE - 11 or y > SIZE - 11 or (min(x, SIZE - x) < 60 and min(y, SIZE - y) < 60 and not (76 <= x <= 184 and 52 <= y <= 204))):
            px[x, y] = (0, 0, 0, 0)

img.save(ROOT / "pdfscout" / "static" / "icon.png")
img.save(ROOT / "packaging" / "pdfscout.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
# Splash shown by PyInstaller while the app starts.
sd = pymupdf.open()
sp = sd.new_page(width=480, height=220)
sh = sp.new_shape()
sh.draw_rect(sp.rect)
sh.finish(color=(0.86, 0.87, 0.9), fill=(1, 1, 1), width=2)
sh.commit()
sp.insert_image(pymupdf.Rect(40, 60, 140, 160), filename=str(ROOT / "pdfscout" / "static" / "icon.png"))
sp.insert_text((165, 104), "Vantage", fontsize=30, fontname="hebo", color=(0.11, 0.13, 0.16))
sp.insert_text((165, 136), "PDF Editor", fontsize=24, fontname="helv", color=(0.11, 0.13, 0.16))
sp.insert_text((167, 160), "by DTR Networks, Inc.", fontsize=12, fontname="helv", color=(0.42, 0.45, 0.5))
sp.insert_text((167, 192), "Starting...", fontsize=12, fontname="helv", color=red)
sd[0].get_pixmap(dpi=96).save(str(ROOT / "packaging" / "splash.png"))
print("icons written")
