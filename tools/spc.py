"""Danganronpa V3 SPC archive + STX text table reader/writer."""
import struct

def _rev(b):
    b = ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)
    b = ((b & 0xCC) >> 2) | ((b & 0x33) << 2)
    return ((b & 0xAA) >> 1) | ((b & 0x55) << 1)

def spc_decompress(data):
    out = bytearray(); p = 0; flag = 1; n = len(data)
    while p < n:
        if flag == 1:
            flag = 0x100 | _rev(data[p]); p += 1
            if p >= n: break
        if flag & 1:
            out.append(data[p]); p += 1
        else:
            b = data[p] | (data[p + 1] << 8); p += 2
            count = (b >> 10) + 2
            off = (b & 0x3FF) - 1024
            for _ in range(count):
                out.append(out[len(out) + off])
        flag >>= 1
    return bytes(out)

def spc_compress(data):
    """LZ compressor matching spc_decompress: 1024-byte window, match length 2..65."""
    n = len(data); out = bytearray(); p = 0
    heads = {}  # 3-byte key -> list of positions
    def match(p):
        best_len = 0; best_off = 0
        if p + 2 >= n:
            return 0, 0
        lst = heads.get(data[p:p + 3])
        if not lst: return 0, 0
        maxl = min(65, n - p)
        for q in reversed(lst):
            if p - q > 1024: break
            l = 3
            while l < maxl and data[q + l] == data[p + l]: l += 1
            if l > best_len:
                best_len, best_off = l, q - p
                if l == maxl: break
        return best_len, best_off
    def add(pos):
        if pos + 2 < n:
            k = data[pos:pos + 3]; lst = heads.setdefault(k, [])
            lst.append(pos)
            if len(lst) > 64: del lst[:32]
    while p < n:
        flags = 0; chunk = bytearray()
        for bit in range(8):
            if p >= n: break
            l, off = match(p)
            if l >= 3:
                b = ((l - 2) << 10) | (off + 1024)
                chunk += bytes([b & 0xFF, b >> 8])
                for k in range(l): add(p + k)
                p += l
            else:
                flags |= 1 << bit
                chunk.append(data[p]); add(p); p += 1
        out.append(_rev(flags)); out += chunk
    return bytes(out)

def pad16(n):
    return (0x10 - n % 0x10) % 0x10

class SPC:
    def __init__(self, raw):
        if raw[:4] == b'$CMP':
            raise ValueError('$CMP wrapped SPC not supported yet')
        assert raw[:4] == b'CPS.', raw[:4]
        self.head_unk = raw[4:0x28]
        count, self.unk2 = struct.unpack('<iI', raw[0x28:0x30])
        self.mid = raw[0x30:0x40]
        assert raw[0x40:0x44] == b'Root'
        self.root_pad = raw[0x44:0x50]
        p = 0x50; self.entries = []
        for _ in range(count):
            cf, uf, csize, size, nlen = struct.unpack('<hhiii', raw[p:p + 16]); p += 16
            skip = raw[p:p + 16]; p += 16
            name = raw[p:p + nlen].decode('ascii'); p += nlen + 1 + pad16(nlen + 1)
            data = raw[p:p + csize]; p += csize + pad16(csize)
            self.entries.append(dict(cf=cf, uf=uf, size=size, name=name, skip=skip, raw=data))

    def get(self, e):
        if e['cf'] == 2:
            return spc_decompress(e['raw'])
        return e['raw']

    def set(self, e, data):
        c = spc_compress(data)
        assert spc_decompress(c) == data, 'compressor round-trip failed: ' + e['name']
        e['cf'] = 2; e['raw'] = c; e['size'] = len(data)

    def build(self):
        o = bytearray(b'CPS.' + self.head_unk + struct.pack('<iI', len(self.entries), self.unk2) + self.mid + b'Root' + self.root_pad)
        for e in self.entries:
            nb = e['name'].encode('ascii')
            o += struct.pack('<hhiii', e['cf'], e['uf'], len(e['raw']), e['size'], len(nb)) + e['skip']
            o += nb + b'\0' * (1 + pad16(len(nb) + 1))
            o += e['raw'] + b'\0' * pad16(len(e['raw']))
        return bytes(o)

def stx_read(data):
    assert data[:4] == b'STXT', data[:4]
    lang, unk1, toff, unk2, count = struct.unpack('<4sIIII', data[4:24])
    out = []
    for i in range(count):
        sid, soff = struct.unpack('<II', data[toff + i * 8:toff + i * 8 + 8])
        e = soff
        while data[e:e + 2] != b'\0\0': e += 2
        out.append((sid, data[soff:e].decode('utf-16-le')))
    return dict(lang=lang, unk1=unk1, unk2=unk2), out

def stx_write(meta, strings):
    count = len(strings); toff = 0x20
    head = b'STXT' + struct.pack('<4sIIII', meta['lang'], meta['unk1'], toff, meta['unk2'], count)
    head += b'\0' * (toff - len(head))
    table = bytearray(); body = bytearray(); base = toff + count * 8; seen = {}
    for sid, s in strings:
        if s in seen:
            off = seen[s]
        else:
            off = base + len(body); seen[s] = off
            body += s.encode('utf-16-le') + b'\0\0'
        table += struct.pack('<II', sid, off)
    return head + bytes(table) + bytes(body)
