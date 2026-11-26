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
        fh.seek(0); hdr = fh.read(0x800)
        from cpk import parse_utf
        align = parse_utf(hdr[0x10:])[0].get('Align') or 0x800
        changed = 0
        files = []
        for root, _, fns in os.walk(mod):
            for fn in fns:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, mod).replace(os.sep, '/')
                if rel not in index:
                    print('  ! not in CPK, skipped:', rel); continue
                files.append((rel, open(full, 'rb').read()))
        files.sort(key=lambda x: x[0])
        up = lambda v: (v + align - 1) // align * align
        inplace, moved = [], []
        for rel, data in files:
            r = index[rel]
            pos = toc + r['FileOffset'][0]; slot = r['FileSize'][0]
            (inplace if len(data) <= slot else moved).append((rel, data, r, pos, slot))
        # --- plan (nothing is written until everything has a place)
        free = []
        for rel, data, r, pos, slot in inplace:
            st = up(pos + len(data))
            if pos + slot > st: free.append([st, pos + slot])
        blocks, gaps = [], []
        for st, en in sorted((pos, pos + slot) for _, _, _, pos, slot in moved):
            if blocks and blocks[-1][1] <= st < blocks[-1][1] + align:
                if st > blocks[-1][1]: gaps.append((blocks[-1][1], st))
                blocks[-1][1] = en
            else:
                blocks.append([st, en])
        free += blocks
        plan = []
        for rel, data, r, pos, slot in sorted(moved, key=lambda x: -len(x[1])):
            free.sort(key=lambda x: x[1] - x[0])
            spot = next((fr for fr in free if fr[1] - fr[0] >= len(data)), None)
            if spot is None:
                raise SystemExit('  ! %s (%d bytes) does not fit anywhere in %s' % (rel, len(data), os.path.basename(cpk)))
            plan.append((rel, data, r, spot[0]))
            spot[0] = up(spot[0] + len(data))

        def backup(pos, size, rel):
            if pos not in saved:
                fh.seek(pos); orig = fh.read(size)
                bf = 'slot_%d.bin' % len(meta['slots'])
                open(os.path.join(bdir, bf), 'wb').write(orig)
                meta['slots'].append({'pos': pos, 'file': bf, 'path': rel}); saved.add(pos)

        def set_entry(r, pos, data):
            for col, val in (('FileSize', len(data)), ('ExtractSize', len(data))):
                _, ap, f = r[col]; fh.seek(ap); fh.write(struct.pack(f, val))
            _, ap, f = r['FileOffset']; fh.seek(ap); fh.write(struct.pack(f, pos - toc))

        # --- backups of every byte range that will change
        for rel, data, r, pos, slot in inplace + moved: backup(pos, slot, rel)
        for st, en in gaps: backup(st, en - st, '<gap>')
        json.dump(meta, open(meta_fn, 'w'), indent=1)
        # --- write
        changed = 0
        for rel, data, r, pos, slot in inplace:
            fh.seek(pos); fh.write(data + b'\0' * (slot - len(data)))
            set_entry(r, pos, data); changed += 1
            print('  + %s %d/%d' % (rel, len(data), slot))
        for rel, data, r, npos in plan:
            fh.seek(npos); fh.write(data)
            set_entry(r, npos, data); changed += 1
            print('  > %s %d (moved)' % (rel, len(data)))
    json.dump(meta, open(meta_fn, 'w'), indent=1)
    print(changed, 'files patched in', os.path.basename(cpk))

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if sys.argv[1] == 'apply': apply(*sys.argv[2:5])
    elif sys.argv[1] == 'restore': print('restored' if restore(*sys.argv[2:4]) else 'no backup')
