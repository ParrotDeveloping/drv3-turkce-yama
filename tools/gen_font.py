"""Add Turkish glyphs (çÇöÖüÜşŞğĞıİ) to v3_font00 by composing existing glyphs.
usage: gen_font.py <in_dir> <out_dir>   (expects v3_font00.stx / v3_font00.srdv)"""
import sys, os, struct
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from font import Font, bc4_encode

BASE = 43  # baseline (absolute row in 47px cell)

def glyph(f, ch):
    x, y, w, h, a, b, yo = f.glyphs[ord(ch)]
    return f.img[y:y + h, x:x + w].astype(np.float32), yo, a, b

def canvas(w, top, bottom):
    return np.zeros((bottom - top, w), np.float32), top

def paste(cv, top, g, gy, gx=0):
    h, w = g.shape
    ys = gy - top
    reg = cv[ys:ys + h, gx:gx + w]
    np.maximum(reg, g[:reg.shape[0], :reg.shape[1]], out=reg)

def supersample(draw_fn, w, h, s=8):
    im = Image.new('L', (w * s, h * s), 0)
    draw_fn(ImageDraw.Draw(im), s)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32)

def cedilla(s_):
    w, h = 10, 10
    def d(dr, s):
        st = 3.6 * s
        # stub down from top center, then hook to lower-left
        dr.line([(5 * s, 0), (5.2 * s, 3.2 * s)], fill=255, width=int(st))
        dr.arc([(1.0 * s, 1.6 * s), (8.6 * s, 9.2 * s)], start=-90, end=135, fill=255, width=int(st))
    return supersample(d, w, h)

def breve(w=14, h=7):
    def d(dr, s):
        dr.arc([(0.8 * s, -5.5 * s), ((w - 0.8) * s, (h - 0.6) * s)], start=15, end=165, fill=255, width=int(3.6 * s))
    return supersample(d, w, h)

def squash(g, newh):
    im = Image.fromarray(g.clip(0, 255).astype(np.uint8))
    return np.asarray(im.resize((g.shape[1], newh), Image.LANCZOS), np.float32)

def build_glyphs(f):
    out = {}
    gi, iyo, _, _ = glyph(f, 'i')
    dot = gi[0:7, :].copy()            # 7x7 dot
    dot_small = squash(dot[:, :], 6)    # 7 wide x 6 tall for capitals
    dot_small = np.asarray(Image.fromarray(dot_small.astype(np.uint8)).resize((6, 6), Image.LANCZOS), np.float32)
    ced = cedilla(None)

    def lower_dots(ch):
        g, yo, a, b = glyph(f, ch)
        w = g.shape[1]
        cv, top = canvas(w, 4, yo + g.shape[0])
        paste(cv, top, g, yo)
        cx = w / 2
        for dx in (-6.5, 6.5):
            paste(cv, top, dot, 4, int(round(cx + dx - 3.5)))
        return cv, top, a, b

    def upper_mark(ch, mark, mark_h):
        g, yo, a, b = glyph(f, ch)
        w = g.shape[1]
        bottom = yo + g.shape[0]
        newtop = mark_h + 2
        g2 = squash(g, bottom - newtop)
        cv, top = canvas(w, 0, bottom)
        paste(cv, top, g2, newtop)
        return cv, top, a, b, w

    def with_cedilla(ch):
        g, yo, a, b = glyph(f, ch)
        w = g.shape[1]
        bottom = yo + g.shape[0]
        cv, top = canvas(w, yo, BASE + 10)
        paste(cv, top, g, yo)
        paste(cv, top, ced, BASE - 1, int(round(w / 2 - 5)))
        return cv, top, a, b

    out['ö'] = lower_dots('o')
    out['ü'] = lower_dots('u')
    out['ç'] = with_cedilla('c')
    out['ş'] = with_cedilla('s')
    out['Ç'] = with_cedilla('C')
    out['Ş'] = with_cedilla('S')
    # dotless i
    gi_full, iyo, a, b = glyph(f, 'i')
    out['ı'] = (gi_full[12:, :].copy(), iyo + 12, a, b)
    # g breve
    g, yo, a, b = glyph(f, 'g'); w = g.shape[1]
    br = breve()
    cv, top = canvas(w, 4, yo + g.shape[0]); paste(cv, top, g, yo)
    paste(cv, top, br, 4, int(round(w / 2 - br.shape[1] / 2)))
    out['ğ'] = (cv, top, a, b)
    # capitals with marks above
    for ch, base in (('Ö', 'O'), ('Ü', 'U')):
        cv, top, a, b, w = upper_mark(base, None, 6)
        for dx in (-7.5, 7.5):
            paste(cv, top, dot_small, 0, int(round(w / 2 + dx - 3)))
        out[ch] = (cv, top, a, b)
    cv, top, a, b, w = upper_mark('I', None, 6)
    paste(cv, top, dot_small, 0, int(round(w / 2 - 3)))
    out['İ'] = (cv, top, a, b)
    cv, top, a, b, w = upper_mark('G', None, 6)
    brc = breve(14, 6)
    paste(cv, top, brc, 0, int(round(w / 2 - 7)))
    out['Ğ'] = (cv, top, a, b)
    return out

def trim_rows(cv, top):
    rows = np.where(cv.max(1) > 8)[0]
    return cv[rows.min():rows.max() + 1], top + rows.min()

def patch_srd(f, sp):
    """Rebuild v3_font00.stx (srd) with a new SpFt payload."""
    old = bytes(f.srd)
    rsi_hdr = 0x30; rsi = 0x40
    assert old[rsi_hdr:rsi_hdr + 4] == b'$RSI'
    rsi_len = struct.unpack('>I', old[rsi_hdr + 4:rsi_hdr + 8])[0]
    sp_rel = f.sp - rsi  # 0x30
    old_sp_len = f.name_end()
    new_sp, delta = sp
    head = bytearray(old[rsi:f.sp])
    # RSI header fields: +0x0C external name offset ; local resource @+0x20 (name, off, size)
    for off in (0x0C, 0x20, 0x28):
        v = struct.unpack_from('<I', head, off)[0]
        struct.pack_into('<I', head, off, v + delta)
    rest = old[f.sp + old_sp_len:rsi + rsi_len]
    rsi_data = bytes(head) + new_sp + rest
    assert len(rsi_data) == rsi_len + delta
    pad = (0x10 - len(rsi_data) % 0x10) % 0x10
    rsi_block = b'$RSI' + struct.pack('>I', len(rsi_data)) + old[rsi_hdr + 8:rsi_hdr + 16] + rsi_data + b'\0' * pad
    old_pad = (0x10 - rsi_len % 0x10) % 0x10
    after_rsi = old[rsi + rsi_len + old_pad:]  # $CT0 (end of TXR subdata) + final $CT0
    txr_sub_old = struct.unpack('>I', old[0x18:0x1C])[0]
    sub_ct0 = after_rsi[:16]
    final = after_rsi[16:]
    assert sub_ct0[:4] == b'$CT0' and final[:4] == b'$CT0', (sub_ct0, final)
    new_sub = rsi_block + sub_ct0
    txr_hdr = bytearray(old[0x10:0x20])
    struct.pack_into('>I', txr_hdr, 8, len(new_sub))
    return old[:0x10] + bytes(txr_hdr) + old[0x20:0x30] + new_sub + final

def main(src, dst):
    f = Font(open(os.path.join(src, 'v3_font00.stx'), 'rb').read(), open(os.path.join(src, 'v3_font00.srdv'), 'rb').read())
    gl = build_glyphs(f)
    x = 420; y0 = 52; prev = Image.new('L', (12 * 50, 60), 0); px = 0
    for ch in 'çÇöÖüÜşŞğĞıİ':
        cv, top, a, b = gl[ch]
        cv, top = trim_rows(cv, top)
        h, w = cv.shape
        assert y0 + h <= f.h, (ch, h)
        f.img[y0:y0 + h, x:x + w] = cv.clip(0, 255).astype(np.uint8)
        f.glyphs[ord(ch)] = [x, y0, w, h, a, b, top]
        prev.paste(Image.fromarray(cv.clip(0, 255).astype(np.uint8)), (px, top))
        px += w + 6; x += w + 4
    prev.save(os.path.join(dst, 'preview_glyphs.png'))
    sp = f.build()
    srd = patch_srd(f, sp)
    os.makedirs(dst, exist_ok=True)
    open(os.path.join(dst, 'v3_font00.stx'), 'wb').write(srd)
    tex = f.texture()
    open(os.path.join(dst, 'v3_font00.srdv'), 'wb').write(tex)
    # verify round trip
    f2 = Font(srd, tex)
    assert len(f2.chars) == len(f.glyphs)
    print('ok', len(f2.chars), 'glyphs; srd', len(srd), 'tex', len(tex))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
