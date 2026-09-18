"""Compose Etsy listing images from the rendered dashboard previews.
For each product: 1_cover (designed, 2000x1600), 2_dashboard (full render), 3_included (what's inside card).
"""
import glob, json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

here = os.path.dirname(os.path.abspath(__file__))
store = sys.argv[1] if len(sys.argv) > 1 else "store_b"
prev = os.path.join(here, store, "previews"); out = os.path.join(here, store, "listing_images"); os.makedirs(out, exist_ok=True)
META = json.load(open(os.path.join(here, store, "meta.json")))

BG = (244, 241, 236); INK = (31, 42, 44); ACC = (46, 111, 115); ACC2 = (199, 129, 63); WHITE = (255, 255, 255); MUTED = (107, 122, 124)
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
W, H = 2000, 1600


def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size)


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= max_w: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def rounded(size, radius, fill):
    im = Image.new("RGBA", size, (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius, fill=fill); return im


def window_frame(shot, width):
    """Put a screenshot inside a browser-window style frame with shadow."""
    ratio = width / shot.width; shot = shot.resize((width, int(shot.height * ratio)))
    bar = 44; frame = Image.new("RGBA", (width + 40, shot.height + bar + 40), (0, 0, 0, 0))
    shadow = rounded((width + 40, shot.height + bar + 40), 28, (0, 0, 0, 70)).filter(ImageFilter.GaussianBlur(18))
    frame.alpha_composite(shadow, (0, 12))
    body = rounded((width, shot.height + bar), 18, WHITE + (255,))
    d = ImageDraw.Draw(body)
    for i, c in enumerate([(255, 95, 87), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([18 + i * 26, 14, 34 + i * 26, 30], fill=c)
    body.paste(shot, (0, bar))
    frame.alpha_composite(body, (20, 8))
    return frame


def badge(draw, xy, text, f, fill=ACC, fg=WHITE, pad=22):
    tw = draw.textlength(text, font=f); x, y = xy; h = f.size + pad
    draw.rounded_rectangle([x, y, x + tw + pad * 2, y + h], h // 2, fill=fill)
    draw.text((x + pad, y + pad // 2 - 2), text, font=f, fill=fg)
    return x + tw + pad * 2 + 16


def cover(key, m, shot):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    x = 110; y = 150
    d.text((x, y), m["kicker"].upper(), font=font(34), fill=ACC2); y += 70
    for line in wrap(d, m["headline"], font(92), 900):
        d.text((x, y), line, font=font(96), fill=INK); y += 108
    y += 20
    for line in wrap(d, m["sub"], font(38, False), 760):
        d.text((x, y), line, font=font(38, False), fill=MUTED); y += 52
    y += 40
    bx = x
    for b in ["Excel", "Google Sheets", "Instant Download"]:
        bx = badge(d, (bx, y), b, font(30), fill=ACC if b != "Instant Download" else ACC2)
    y += 110
    for i, bullet in enumerate(m["bullets"][:3]):
        d.ellipse([x, y + 14, x + 16, y + 30], fill=ACC); d.text((x + 36, y), bullet, font=font(34, False), fill=INK); y += 58
    fr = window_frame(shot, 1060)
    fr = fr.rotate(-3, resample=Image.BICUBIC, expand=True)
    im.paste(fr, (W - fr.width + 40, H - fr.height - 60), fr)
    d.text((110, H - 90), "TidyMoneySheets", font=font(30), fill=MUTED)
    im.save(os.path.join(out, f"{key}_1_cover.jpg"), quality=90)


def dashboard_img(key, shot):
    im = Image.new("RGB", (W, H), BG)
    fr = window_frame(shot, 1800)
    im.paste(fr, ((W - fr.width) // 2, (H - fr.height) // 2), fr)
    im.save(os.path.join(out, f"{key}_2_dashboard.jpg"), quality=90)


def included(key, m):
    im = Image.new("RGB", (W, H), ACC); d = ImageDraw.Draw(im)
    d.text((120, 130), "WHAT'S INCLUDED", font=font(36), fill=(200, 226, 224))
    d.text((120, 190), m["headline"], font=font(72), fill=WHITE)
    y = 330
    card = rounded((W - 240, H - 330 - 120), 30, WHITE + (255,)); im.paste(card, (120, y), card)
    y += 50
    for tab in m["tabs"]:
        d.text((180, y), "✓", font=font(40), fill=ACC); d.text((240, y - 4), tab, font=font(40, False), fill=INK); y += 78
    y += 20
    d.text((180, y), "Works in Excel 2016+ and Google Sheets. No macros. Sample data pre-loaded.", font=font(30, False), fill=MUTED)
    im.save(os.path.join(out, f"{key}_3_included.jpg"), quality=90)


for jpg in sorted(glob.glob(os.path.join(prev, "*.jpg"))):
    key = os.path.basename(jpg)[:2]
    if key not in META: continue
    shot = Image.open(jpg).convert("RGB")
    from PIL import ImageChops
    bbox = ImageChops.difference(shot, Image.new("RGB", shot.size, (255, 255, 255))).getbbox()
    if bbox: shot = shot.crop(bbox)
    cover(key, META[key], shot); dashboard_img(key, shot); included(key, META[key])
    print("images:", key)
