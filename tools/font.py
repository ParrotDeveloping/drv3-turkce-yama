"""DRV3 SpFt font (v3_font00.stx/.srdv) reader/writer with BC4 texture codec."""
import struct
import numpy as np

# ---------------- BC4 ----------------
def bc4_palette(r0, r1):
    r0 = r0.astype(np.int32); r1 = r1.astype(np.int32)
    p = np.zeros(r0.shape + (8,), np.int32)
    p[..., 0] = r0; p[..., 1] = r1
    m = r0 > r1
    for i in range(1, 7):
        p[..., i + 1] = np.where(m, ((7 - i) * r0 + i * r1) // 7, 0)
    for i in range(1, 5):
        v = ((5 - i) * r0 + i * r1) // 5
        p[..., i + 1] = np.where(m, p[..., i + 1], v)
    p[..., 6] = np.where(m, p[..., 6], 0)
    p[..., 7] = np.where(m, p[..., 7], 255)
    return p

def bc4_decode(data, w, h):
    bw, bh = (w + 3) // 4, (h + 3) // 4
    a = np.frombuffer(data[:bw * bh * 8], np.uint8).reshape(bh, bw, 8)
    pal = bc4_palette(a[..., 0], a[..., 1])
    bits = np.zeros((bh, bw), np.uint64)
    for i in range(6):
        bits |= a[..., 2 + i].astype(np.uint64) << np.uint64(8 * i)
    idx = np.zeros((bh, bw, 16), np.int64)
    for i in range(16):
        idx[..., i] = ((bits >> np.uint64(3 * i)) & np.uint64(7)).astype(np.int64)
    px = np.take_along_axis(pal, idx, axis=2).reshape(bh, bw, 4, 4)
    img = px.transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)
    return img.astype(np.uint8)

def bc4_encode(img):
    h, w = img.shape
    bh, bw = h // 4, w // 4
    blk = img.reshape(bh, 4, bw, 4).transpose(0, 2, 1, 3).reshape(bh, bw, 16).astype(np.int32)
    mx = blk.max(2); mn = blk.min(2)
    r0 = mx.copy(); r1 = mn.copy()
    flat = r0 == r1
    r0 = np.where(flat & (r0 < 255), r0 + 1, r0)
    r1 = np.where(flat & (r0 == r1), r1 - 1, r1)  # r0>r1 always -> 8-value mode
    pal = bc4_palette(r0, r1)
    d = np.abs(blk[..., :, None] - pal[..., None, :])
    idx = d.argmin(3).astype(np.uint64)
    bits = np.zeros((bh, bw), np.uint64)
    for i in range(16):
        bits |= idx[..., i] << np.uint64(3 * i)
    out = np.zeros((bh, bw, 8), np.uint8)
    out[..., 0] = r0; out[..., 1] = r1
    for i in range(6):
        out[..., 2 + i] = ((bits >> np.uint64(8 * i)) & np.uint64(0xFF)).astype(np.uint8)
    return out.tobytes()

# ---------------- SpFt ----------------
class Font:
    """srd = v3_font00.stx bytes, srdv = texture bytes."""
    def __init__(self, srd, srdv):
        self.srd = bytearray(srd)
        assert srd[0x10:0x14] == b'$TXR'
        # TXR data at 0x20
        self.txr = 0x20
        _, sw, self.w, self.h, scan, fmt = struct.unpack('<IHHHHB', srd[0x20:0x2D])
        assert fmt == 0x16, hex(fmt)
        self.sp = srd.index(b'SpFt')
        b = self.srd[self.sp:]
        (self.ver, self.maxc, self.u0c, self.name_off, self.count, self.glyph_off,
         self.bm_off, self.rank_off) = struct.unpack('<8I', b[4:36])
        self.fs1, self.fs2, self.u28 = struct.unpack('<HHI', b[36:44])
        self.bm = bytearray(b[self.bm_off:self.rank_off])
        self.chars = [c for c in range(self.maxc + 1) if (self.bm[c >> 3] >> (c & 7)) & 1]
        assert len(self.chars) == self.count
        self.glyphs = {}
        for i, c in enumerate(self.chars):
            e = b[self.glyph_off + i * 8:self.glyph_off + i * 8 + 8]
            xy = e[0] | (e[1] << 8) | (e[2] << 16)
            self.glyphs[c] = [xy & 0xFFF, xy >> 12, e[3], e[4], e[5], e[6], e[7]]
        self.tail = bytes(b[self.u28:])  # name strings etc. (offset u28)
        self.after_sp = None
        self.img = bc4_decode(srdv, self.w, ((self.h + 3) // 4) * 4)

    def build(self):
        chars = sorted(self.glyphs)
        maxc = self.maxc
        bm = bytearray((maxc + 1 + 7) // 8)
        bm = bytearray(len(self.bm))
        for c in chars:
            bm[c >> 3] |= 1 << (c & 7)
        rank = bytearray(); n = 0
        for i in range(0, len(bm), 4):
            rank += struct.pack('<I', n)
            n += sum(bin(x).count('1') for x in bm[i:i + 4])
        gl = bytearray()
        for c in chars:
            x, y, w, h, a, b2, c2 = self.glyphs[c]
            xy = x | (y << 12)
            gl += bytes([xy & 0xFF, (xy >> 8) & 0xFF, xy >> 16, w, h, a, b2, c2])
        bm_off = 0x2C; rank_off = bm_off + len(bm); glyph_off = rank_off + len(rank)
        tail_off = glyph_off + len(gl)
        old = self.srd[self.sp:]
        # tail: original data from old u28 (contains name offsets relative to SpFt start)
        tail = bytearray(old[self.u28:self.name_end()])
        delta = tail_off - self.u28
        # first 4 u32 in tail are offsets (relative to SpFt) -> shift
        for i in range(4):
            v = struct.unpack_from('<I', tail, i * 4)[0]
            struct.pack_into('<I', tail, i * 4, v + delta)
        hdr = b'SpFt' + struct.pack('<8I', self.ver, maxc, self.u0c, self.name_off + delta,
                                    len(chars), glyph_off, bm_off, rank_off)
        hdr += struct.pack('<HHI', self.fs1, self.fs2, tail_off)
        sp = hdr + bm + rank + gl + tail
        return sp, delta

    def name_end(self):
        b = self.srd[self.sp:]
        # end of tail strings: find 'font_table\0'
        i = b.index(b'font_table\0') + len(b'font_table\0')
        return i

    def texture(self):
        img = self.img
        return bc4_encode(img)
