"""Patch files inside a CRI CPK by rewriting them in place and updating TOC entries.

  cpk_patch.py apply   <cpk> <mod_dir> <backup_dir>
  cpk_patch.py restore <cpk> <backup_dir>

mod_dir mirrors the CPK's internal paths (e.g. mod_dir/wrd_script/007/chap0_text_US.SPC).
A new file must fit in the original file's slot (the game does not read data appended
after the CPK's content area). The original TOC, file size and every overwritten slot
are saved to backup_dir; every apply restores those first.
"""
import sys, os, struct, json

def utf_layout(buf, base_abs):
    """Return rows as {col: (value, abs_pos, fmt)} for per-row columns. buf must be plain @UTF."""
    assert buf[:4] == b'@UTF', 'encrypted TOC not supported'
    d = buf[8:]
    _, rows_off, str_off, data_off, name_off, ncol, rowlen, nrows = struct.unpack('>HHIIIHHI', d[:24])
    fmts = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f', 0xA: '>I', 0xB: '>II'}
    def s(o):
        e = d.index(b'\0', str_off + o); return d[str_off + o:e].decode()
    cols = []; p = 24
    for _ in range(ncol):
        fl = d[p]; nm = s(struct.unpack('>I', d[p + 1:p + 5])[0]); p += 5
        st, t = fl & 0xF0, fl & 0x0F
        if st == 0x30: p += struct.calcsize(fmts[t])
        cols.append((nm, st, t))
    rows = []
    for r in range(nrows):
        p = rows_off + r * rowlen; row = {}
        for nm, st, t in cols:
            if st != 0x50: continue
            f = fmts[t]; n = struct.calcsize(f)
            v = struct.unpack(f, d[p:p + n])
            v = s(v[0]) if t == 0xA else v[0]
            row[nm] = (v, base_abs + 8 + p, f); p += n
        rows.append(row)
    return rows

def load(fh):
    fh.seek(0); hdr = fh.read(0x800)
    assert hdr[:4] == b'CPK '
    from cpk import parse_utf
    h = parse_utf(hdr[0x10:])[0]
    toc = h['TocOffset']
    fh.seek(toc); th = fh.read(16); size = struct.unpack('<Q', th[8:16])[0]
    return toc, size, fh.read(size)

def index_rows(rows):
    idx = {}
    for r in rows:
        dn = r['DirName'][0] if 'DirName' in r else ''
        idx[(dn + '/' if dn else '') + r['FileName'][0]] = r
    return idx

def restore(cpk, bdir):
    meta = os.path.join(bdir, 'meta.json')
    if not os.path.exists(meta): return False
    m = json.load(open(meta))
    with open(cpk, 'r+b') as fh:
        for sl in m.get('slots', []):
            fh.seek(sl['pos']); fh.write(open(os.path.join(bdir, sl['file']), 'rb').read())
        fh.seek(m['toc_abs']); fh.write(open(os.path.join(bdir, 'toc.bin'), 'rb').read())
        fh.truncate(m['size'])
    return True

def apply(cpk, mod, bdir):
    os.makedirs(bdir, exist_ok=True)
    meta_fn = os.path.join(bdir, 'meta.json')
    if os.path.exists(meta_fn):
        restore(cpk, bdir)
        meta = json.load(open(meta_fn))
    else:
        with open(cpk, 'rb') as fh:
            toc, tsize, raw = load(fh)
        open(os.path.join(bdir, 'toc.bin'), 'wb').write(raw)
        meta = {'toc_abs': toc + 16, 'size': os.path.getsize(cpk), 'slots': []}
    meta.setdefault('slots', [])
    saved = {s['pos'] for s in meta['slots']}
    with open(cpk, 'r+b') as fh:
        toc, tsize, raw = load(fh)
        index = index_rows(utf_layout(raw, toc + 16))
        changed = 0
        for root, _, files in os.walk(mod):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, mod).replace('\\', '/')
                if rel not in index:
                    print('  ! not in CPK, skipped:', rel); continue
                data = open(full, 'rb').read()
                r = index[rel]
                pos = toc + r['FileOffset'][0]; slot = r['FileSize'][0]
                if len(data) > slot:
                    raise SystemExit('  ! %s is %d bytes, larger than its slot (%d) - cannot patch in place' % (rel, len(data), slot))
                if pos not in saved:
                    fh.seek(pos); orig = fh.read(slot)
                    bf = 'slot_%d.bin' % len(meta['slots'])
                    open(os.path.join(bdir, bf), 'wb').write(orig)
                    meta['slots'].append({'pos': pos, 'file': bf, 'path': rel}); saved.add(pos)
                fh.seek(pos); fh.write(data + b'\0' * (slot - len(data)))
                for col, val in (('FileSize', len(data)), ('ExtractSize', len(data))):
                    _, ap, f = r[col]; fh.seek(ap); fh.write(struct.pack(f, val))
                changed += 1
                print('  + %s %d/%d' % (rel, len(data), slot))
    json.dump(meta, open(meta_fn, 'w'), indent=1)
    print(changed, 'files patched in', os.path.basename(cpk))

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if sys.argv[1] == 'apply': apply(*sys.argv[2:5])
    elif sys.argv[1] == 'restore': print('restored' if restore(*sys.argv[2:4]) else 'no backup')
