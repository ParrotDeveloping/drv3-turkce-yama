"""CRI CPK archive reader (TOC + CRILAYLA decompression)."""
import struct, sys, os

def _xor_utf(data):
    # Some CPKs XOR-encrypt @UTF tables
    out = bytearray(len(data)); m = 0x655f; t = 0x4115
    for i, b in enumerate(data):
        out[i] = b ^ (m & 0xff); m = (m * t) & 0xffffffff
    return bytes(out)

def parse_utf(buf):
    if buf[:4] != b'@UTF':
        buf = _xor_utf(buf)
        if buf[:4] != b'@UTF':
            raise ValueError('not @UTF')
    size = struct.unpack('>I', buf[4:8])[0]
    d = buf[8:8 + size]
    _, rows_off, str_off, data_off, name_off, ncol, rowlen, nrows = struct.unpack('>HHIIIHHI', d[:24])
    def s(o):
        e = d.index(b'\0', str_off + o)
        return d[str_off + o:e].decode('utf-8', 'replace')
    fmt = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f'}
    def read(t, p):
        if t in fmt:
            f = fmt[t]; n = struct.calcsize(f)
            return struct.unpack(f, d[p:p + n])[0], n
        if t == 0xA:
            return s(struct.unpack('>I', d[p:p + 4])[0]), 4
        if t == 0xB:
            o, l = struct.unpack('>II', d[p:p + 8])
            return d[data_off + o:data_off + o + l], 8
        raise ValueError('type %x' % t)
    cols = []; p = 24
    for _ in range(ncol):
        flags = d[p]; name = s(struct.unpack('>I', d[p + 1:p + 5])[0]); p += 5
        st = flags & 0xF0; t = flags & 0x0F; const = None
        if st == 0x30:
            const, n = read(t, p); p += n
        cols.append((name, st, t, const))
    rows = []
    for r in range(nrows):
        p = rows_off + r * rowlen; row = {}
        for name, st, t, const in cols:
            if st == 0x50:
                v, n = read(t, p); p += n; row[name] = v
            elif st == 0x30:
                row[name] = const
            else:
                row[name] = None
        rows.append(row)
    return rows

def decompress_layla(src):
    if src[:8] != b'CRILAYLA':
        return src
    usize, hsize = struct.unpack('<II', src[8:16])
    out = bytearray(usize + 0x100)
    out[:0x100] = src[16 + hsize:16 + hsize + 0x100]
    data = src[16:16 + hsize]
    pos = len(data) - 1; bitpool = 0; bits_left = 0
    def getbits(n):
        nonlocal pos, bitpool, bits_left
        v = 0
        while n:
            if bits_left == 0:
                bitpool = data[pos]; pos -= 1; bits_left = 8
            take = min(bits_left, n)
            v = (v << take) | ((bitpool >> (bits_left - take)) & ((1 << take) - 1))
            bits_left -= take; n -= take
        return v
    w = usize - 1 + 0x100; end = 0x100
    while w >= end:
        if getbits(1):
            back = w + getbits(13) + 3
            ln = 3; lv = [2, 3, 5, 8]; i = 0
            while True:
                b = getbits(lv[min(i, 3)])
                ln += b
                if b != (1 << lv[min(i, 3)]) - 1: break
                i += 1
            for _ in range(ln):
                if w < end: break
                out[w] = out[back]; w -= 1; back -= 1
        else:
            out[w] = getbits(8); w -= 1
    return bytes(out[:usize + 0x100])

class CPK:
    def __init__(self, path, toc_override=None):
        """toc_override: path to an original TOC dump (from cpk_patch backups) so reads
        return the unpatched files even after the CPK was patched."""
        self.f = open(path, 'rb')
        hdr = self.f.read(0x800)
        assert hdr[:4] == b'CPK ', 'not a CPK'
        self.header = parse_utf(hdr[0x10:])[0]
        toc_off = self.header['TocOffset']; content_off = self.header['ContentOffset']
        self.f.seek(toc_off); h = self.f.read(16); tsize = struct.unpack('<Q', h[8:16])[0]
        toc = self.f.read(tsize)
        if toc_override and os.path.exists(toc_override):
            toc = open(toc_override, 'rb').read()
        self.files = parse_utf(toc)
        base = min(toc_off, content_off) if content_off else toc_off
        for e in self.files:
            e['path'] = (e.get('DirName') or '') + '/' + e['FileName'] if e.get('DirName') else e['FileName']
            e['abs'] = base + e['FileOffset']

    def read(self, e):
        self.f.seek(e['abs']); raw = self.f.read(e['FileSize'])
        if e['ExtractSize'] and e['ExtractSize'] != e['FileSize']:
            raw = decompress_layla(raw)
        return raw

if __name__ == '__main__':
    c = CPK(sys.argv[1])
    print({k: v for k, v in c.header.items() if not isinstance(v, bytes)})
    print(len(c.files), 'files')
    for e in c.files[:int(sys.argv[2]) if len(sys.argv) > 2 else 20]:
        print(e['path'], e['FileSize'], e['ExtractSize'], hex(e['abs']))
