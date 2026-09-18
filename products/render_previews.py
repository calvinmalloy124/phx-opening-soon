"""Recalculate workbooks with LibreOffice, render the Dashboard page to PNG (2000px), crop whitespace."""
import glob, os, subprocess, sys
from PIL import Image, ImageChops
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, sys.argv[1] if len(sys.argv) > 1 else "store_b", "out")
prev = os.path.join(os.path.dirname(out), "previews"); os.makedirs(prev, exist_ok=True)
for f in sorted(glob.glob(os.path.join(out, "*.xlsx"))):
    # recalc: convert xlsx -> xlsx in a temp dir, then replace
    tmp = os.path.join(here, "_tmp"); os.makedirs(tmp, exist_ok=True)
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", tmp, f], check=True, capture_output=True)
    os.replace(os.path.join(tmp, os.path.basename(f)), f)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", prev, f], check=True, capture_output=True)
    pdf = os.path.join(prev, os.path.basename(f).replace(".xlsx", ".pdf"))
    pages = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout.split("\f")
    idx = next((i for i, p in enumerate(pages) if i > 0 and ("Dashboard" in p or "Countdown" in p)), 1)
    base = pdf[:-4]
    subprocess.run(["pdftoppm", "-png", "-r", "120", "-f", str(idx + 1), "-l", str(idx + 1), "-singlefile", pdf, base], check=True)
    im = Image.open(base + ".png").convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if bbox:
        l, t, r, b = bbox; pad = 50; im = im.crop((max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad)))
    W = 2000; H = int(W * im.height / im.width); canvas = Image.new("RGB", (W, max(H, 1500)), (255, 255, 255)); canvas.paste(im.resize((W, H)), (0, (canvas.height - H) // 2))
    canvas.save(base + ".jpg", quality=88); os.remove(base + ".png"); os.remove(pdf)
    print("rendered", os.path.basename(base))
