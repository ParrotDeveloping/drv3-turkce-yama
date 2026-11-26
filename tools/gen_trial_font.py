"""Add missing characters (Turkish letters + any Latin letters/punctuation the subset lacks)
to the class-trial fonts (trial_font/game_fontXX_US.spc).

Trial fonts are per-phrase subsets: each holds only the glyphs its English line used.
Turkish letters are composed from the font's own base letters (c->ç, o->ö ...). A base
letter the font lacks is copied from a sibling font of the same typeface, else drawn
with a Windows system font of a similar style.
"""
import os, re, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from font import Font

TR_BASE = {'ç': 'c', 'Ç': 'C', 'ş': 's', 'Ş': 'S', 'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
           'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'İ': 'I'}
FONTS_DIR = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
SERIF = ('Tsuku', 'Matisse', 'Manyo')
BRUSH = ('Samurai', 'Shunpu', 'ComicMystery')


def font_name(srd):
    i = srd.index(b'font_table')
    m = re.findall(rb'((?:[\x20-\x7e]\x00){4,})', srd[max(0, i - 160):i])
    return m[-1].decode('utf-16le') if m else ''


def fallback_ttf(name):
    files = ['georgiab.ttf'] if any(s in name for s in SERIF) else \
            ['comicbd.ttf'] if any(s in name for s in BRUSH) else ['arialbd.ttf']
    for fn in files + ['arialbd.ttf', 'arial.ttf', 'segoeuib.ttf', 'tahomabd.ttf']:
        p = os.path.join(FONTS_DIR, fn)
        if os.path.exists(p): return p
    return None


class G:
    """glyph: img float32 (h,w), top = y offset in cell, a/b = side bearings"""
    def __init__(self, img, top, a, b):
        self.img, self.top, self.a, self.b = img.astype(np.float32), int(top), int(a), int(b)
    @property
    def bottom(self): return self.top + self.img.shape[0]
    @property
    def w(self): return self.img.shape[1]


def get_glyph(f, ch):
    if ord(ch) not in f.glyphs: return None
    x, y, w, h, a, b, yo = f.glyphs[ord(ch)]
    sb = lambda v: v - 256 if v > 127 else v
    return G(f.img[y:y + h, x:x + w], yo, sb(a), sb(b))


def trim(g):
    rows = np.where(g.img.max(1) > 8)[0]; cols = np.where(g.img.max(0) > 8)[0]
    if not len(rows): return g
    return G(g.img[rows.min():rows.max() + 1, cols.min():cols.max() + 1], g.top + rows.min(), g.a + cols.min(), g.b + (g.w - 1 - cols.max()))


def ss_draw(w, h, fn, s=8):
    im = Image.new('L', (max(1, int(w)) * s, max(1, int(h)) * s), 0)
    fn(ImageDraw.Draw(im), s)
    return np.asarray(im.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS), np.float32)


def compose(parts, a, b):
    """parts: list of (img, top, left). Returns G spanning all parts."""
    top = min(t for _, t, _ in parts); bottom = max(t + im.shape[0] for im, t, _ in parts)
    left = min(l for _, _, l in parts); right = max(l + im.shape[1] for im, _, l in parts)
    cv = np.zeros((bottom - top, right - left), np.float32)
    for im, t, l in parts:
        reg = cv[t - top:t - top + im.shape[0], l - left:l - left + im.shape[1]]
        np.maximum(reg, im, out=reg)
    return G(cv, top, a + min(0, left), b)


def squash(img, newh):
    return np.asarray(Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize((img.shape[1], max(1, newh)), Image.LANCZOS), np.float32)


class Maker:
    def __init__(self, f, name, donors):
        self.f, self.name, self.donors = f, name, donors
        self.k = f.fs1 / 47.0
        self.base_line = f.fs2
        self.ttf = fallback_ttf(name)
        self.cache = {}

    def base(self, ch):
        if ch in self.cache: return self.cache[ch]
        g = get_glyph(self.f, ch)
        if g is None:
            for d in self.donors:
                g = get_glyph(d, ch)
                if g is not None: break
        if g is None and ch in TR_BASE:
            g = self.make(ch)
        if g is None:
            g = self.render(ch)
        self.cache[ch] = g
        return g

    def cap_metrics(self):
        for c in 'HIETLDB':
            g = get_glyph(self.f, c)
            if g is not None: return trim(g).top, trim(g).bottom
        return int(round(self.base_line - 0.72 * self.f.fs1)), self.base_line

    def render(self, ch):
        if not self.ttf: return None
        cap_top, base = self.cap_metrics()
        cap_h = base - cap_top
        size = max(8, int(round(cap_h / 0.716)))
        ft = ImageFont.truetype(self.ttf, size)
        l, t, r, bt = ft.getbbox(ch, anchor='ls')
        if r <= l: return None
        im = Image.new('L', (r - l + 4, bt - t + 4), 0)
        ImageDraw.Draw(im).text((2 - l, 2 - t), ch, font=ft, fill=255, anchor='ls')
        g = G(np.asarray(im, np.float32), base + t - 2, 0, 0)
        g = trim(g)
        pad = max(1, int(round(2 * self.k)))
        g.a, g.b = pad, pad
        return g

    # ---- marks
    def dot(self):
        gi = self.base('i')
        if gi is not None:
            raw = gi.img.max(1) > 40
            for win in range(0, int(5 * self.k) + 1):
                ink = np.array([raw[max(0, r - win):r + win + 1].any() for r in range(len(raw))])
                r = 0
                while r < len(ink) and not ink[r]: r += 1
                s0 = r
                while r < len(ink) and ink[r]: r += 1
                e = r
                while r < len(ink) and not ink[r]: r += 1
                dh = e - s0 - 2 * win
                if r < len(ink) and r > e and 0.06 * self.f.fs1 <= dh <= 0.3 * self.f.fs1:
                    s1 = s0 + win; e1 = e - win
                    d = gi.img[s1:e1]
                    cols = np.where(d.max(0) > 8)[0]
                    if len(cols):
                        return d[:, cols.min():cols.max() + 1], gi.top + s1, gi.top + r - win, gi
        sz = max(3, int(round(7 * self.k)))
        d = ss_draw(sz, sz, lambda dr, s: dr.ellipse([0, 0, sz * s - 1, sz * s - 1], fill=255))
        xh_top = self.xheight_top()
        return d, xh_top - sz - max(2, int(3 * self.k)), xh_top, None

    def xheight_top(self):
        for c in 'xvwzosuc':
            g = get_glyph(self.f, c)
            if g is not None: return trim(g).top
        return int(self.base_line - 0.5 * self.f.fs1)

    def stem(self):
        g = get_glyph(self.f, 'l') or get_glyph(self.f, 'i') or get_glyph(self.f, 'I')
        if g is None: return max(2, int(round(4 * self.k)))
        row = g.img[g.img.shape[0] * 2 // 3]
        return max(2, int((row > 128).sum()))

    def cedilla(self, gw):
        st = self.stem()
        w = max(6, int(round(st * 1.9))); h = max(6, int(round(st * 2.0)))
        def d(dr, s):
            lw = max(1, int(st * 0.62 * s))
            dr.line([(w * 0.55 * s, 0), (w * 0.55 * s, h * 0.38 * s)], fill=255, width=lw)
            dr.arc([(w * 0.05 * s, h * 0.18 * s), (w * 0.95 * s, h * 0.98 * s - lw / 2)], start=-90, end=150, fill=255, width=lw)
        return ss_draw(w, h, d)

    def breve(self, w):
        st = self.stem()
        bw = max(6, int(round(w * 0.62))); bh = max(4, int(round(st * 1.15)))
        def d(dr, s):
            lw = max(1, int(st * 0.6 * s))
            dr.arc([(lw / 2, -bh * 1.4 * s), (bw * s - lw / 2, bh * s - lw / 2)], start=12, end=168, fill=255, width=lw)
        return ss_draw(bw, bh, d)

    def make(self, ch):
        b = self.base(TR_BASE[ch])
        if b is None: return None
        b = trim(b)
        dot, dtop, dbot, gi = self.dot()
        gap = max(1, dbot - (dtop + dot.shape[0]))
        if ch == 'ı':
            g = trim(b)
            cut = (dbot if gi is not None else self.xheight_top()) - g.top
            if 0 < cut < g.img.shape[0]:
                return trim(G(g.img[cut:], g.top + cut, g.a, g.b))
            return g
        if ch in 'çşÇŞ':
            c = self.cedilla(b.w)
            return compose([(b.img, b.top, 0), (c, b.bottom - max(1, int(self.k)), int(round(b.w / 2 - c.shape[1] / 2)))], b.a, b.b)
        if ch in 'öü':
            top = min(dtop, b.top - gap - dot.shape[0])
            sp = max(dot.shape[1] * 0.75 + 1, b.w * 0.2)
            parts = [(b.img, b.top, 0)]
            for dx in (-sp, sp):
                parts.append((dot, top, int(round(b.w / 2 + dx - dot.shape[1] / 2))))
            return compose(parts, b.a, b.b)
        if ch == 'ğ':
            br = self.breve(b.w)
            top = min(dtop, b.top - gap - br.shape[0])
            return compose([(b.img, b.top, 0), (br, top, int(round(b.w / 2 - br.shape[1] / 2)))], b.a, b.b)
        # capitals: squash to make room for the mark above
        mark = self.breve(b.w) if ch == 'Ğ' else dot
        mh = mark.shape[0] + gap
        cell_top = max(0, b.top - mh)
        newtop = cell_top + mh
        img = squash(b.img, b.bottom - newtop) if newtop > b.top else b.img
        top_img = max(newtop, b.top)
        parts = [(img, top_img, 0)]
        mt = top_img - gap - mark.shape[0]
        if ch == 'Ö' or ch == 'Ü':
            sp = max(mark.shape[1] * 0.75 + 1, b.w * 0.2)
            for dx in (-sp, sp):
                parts.append((mark, mt, int(round(b.w / 2 + dx - mark.shape[1] / 2))))
        else:
            parts.append((mark, mt, int(round(b.w / 2 - mark.shape[1] / 2))))
        return compose(parts, b.a, b.b)


def add_chars(f, srd_name, donors, needed):
    """Mutates f (glyphs + texture). Returns list of added chars."""
    mk = Maker(f, srd_name, donors)
    new = []
    order = [c for c in needed if c not in TR_BASE] + [c for c in needed if c in TR_BASE]
    for ch in order:
        if ord(ch) in f.glyphs: continue
        g = mk.make(ch) if ch in TR_BASE else mk.base(ch)
        if g is None: continue
        g = trim(g)
        g.top = max(0, g.top)
        new.append((ch, g))
        mk.cache[ch] = g
    if not new: return []
    W = f.w
    old_h = f.h
    x, y, rowh = 1, old_h + 1, 0
    places = []
    for ch, g in new:
        h, w = g.img.shape
        if x + w + 1 > W: x = 1; y += rowh + 2; rowh = 0
        places.append((ch, g, x, y)); x += w + 2; rowh = max(rowh, h)
    new_h = y + rowh + 1
    if new_h >= 4096: raise RuntimeError('texture too tall')
    hp = (new_h + 3) // 4 * 4
    img = np.zeros((hp, W), np.uint8)
    img[:f.img.shape[0]] = f.img[:min(f.img.shape[0], hp)]
    for ch, g, gx, gy in places:
        h, w = g.img.shape
        img[gy:gy + h, gx:gx + w] = np.maximum(img[gy:gy + h, gx:gx + w], g.img.clip(0, 255).astype(np.uint8))
        f.glyphs[ord(ch)] = [gx, gy, w, h, max(-128, min(127, g.a)) & 0xFF, max(-128, min(127, g.b)) & 0xFF, max(0, min(255, g.top))]
    f.img = img
    f.h = new_h
    need_max = max(f.glyphs) + 1
    if need_max > f.maxc:
        f.maxc = need_max
        n = ((need_max + 7) // 8 + 3) // 4 * 4
        f.bm = bytearray(n)
    return [c for c, _ in new]


def write_font(f):
    """Return (srd bytes, srdv bytes) with new height + SpFt payload."""
    from gen_font import patch_srd
    sp = f.build()
    srd = bytearray(patch_srd(f, sp))
    struct.pack_into('<H', srd, 0x28, f.h)
    tex = f.texture()
    # RSI local resource (texture offset|flags, size) right after the RSI header
    rsi = 0x40
    old_size = len(f._orig_tex)
    for off in range(rsi, min(len(srd), 0x80), 4):
        if struct.unpack_from('<I', srd, off)[0] == old_size:
            struct.pack_into('<I', srd, off, len(tex)); break
    return bytes(srd), tex


def load(srd, srdv):
    f = Font(srd, srdv)
    f._orig_tex = srdv
    return f
