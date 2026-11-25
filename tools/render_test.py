import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from font import Font
d = sys.argv[1]; out = sys.argv[2]
f = Font(open(os.path.join(d, 'v3_font00.stx'), 'rb').read(), open(os.path.join(d, 'v3_font00.srdv'), 'rb').read())
lines = sys.argv[3:]
H = 56
img = np.zeros((H * len(lines) + 8, 1300), np.uint8)
for li, t in enumerate(lines):
    pen = 6
    for ch in t:
        g = f.glyphs.get(ord(ch)) or f.glyphs[ord('?')]
        x, y, w, h, a, b, yo = g
        pen += a
        reg = img[li * H + yo + 2:li * H + yo + 2 + h, pen:pen + w]
        np.maximum(reg, f.img[y:y + h, x:x + w][:reg.shape[0], :reg.shape[1]], out=reg)
        pen += w + b
Image.fromarray(img).convert('L').quantize(16).save(out, optimize=True)
