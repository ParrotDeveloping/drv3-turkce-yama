"""Build the Turkish patch.

  build_patch.py build          -> writes mod/<cpk>/... files
  build_patch.py apply          -> build + patch game CPKs (backups in backup/)
  build_patch.py restore        -> restore original CPKs

Translations: tr/<spc_name>/<stx_name>.tsv  lines: "<id>\t<turkish text>"  (\\n = newline)
"""
import sys, os, re, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cpk import CPK
from spc import SPC, stx_read, stx_write
from font import Font
import cpk_patch

GAME = r'C:/Program Files (x86)/Steam/steamapps/common/Danganronpa V3 Killing Harmony/data/win/'
CPKS = {'resident': 'partition_resident_win.cpk', 'data_us': 'partition_data_win_us.cpk'}
# (cpk key, path inside cpk)  -- every wrd_script version folder gets the same translation
SCRIPT_VERSIONS = ['003', '004', '005', '006', '007']
TARGETS = [('resident', 'game_resident/game_resident_US.spc')]
SCRIPT_FILES = ['%s_text_US.SPC' % n for n in
                ['chap0', 'chap1', 'chap2', 'chap3', 'chap4', 'chap5', 'chap6', 'chap7', 'ainori', 'gallery', 'sub_routine']]
for name in SCRIPT_FILES:
    TARGETS += [('data_us', 'wrd_script/%s/%s' % (v, name)) for v in SCRIPT_VERSIONS]
TARGETS += [('data_us', 'wrd_data/map_obj_name_text_US.SPC')]

def has_translations(path):
    spc_name = os.path.basename(path).split('.')[0]
    d = os.path.join(ROOT, 'tr', spc_name)
    return path.startswith('game_resident') or (os.path.isdir(d) and os.listdir(d))

FONT_DIR = os.path.join(ROOT, 'font')
TAG = re.compile(r'<[^>]*>')
# characters missing from the game font -> nearest available
FIX = str.maketrans({'â': 'a', 'Â': 'A', 'î': 'i', 'Î': 'I', 'û': 'u', 'Û': 'U', '’': "'", '‘': "'", '“': '"', '”': '"'})

def load_tr(spc_name, stx_name):
    """Return {english_text_by_id: tr} as {id: tr} and {en: tr} maps."""
    base = os.path.join(ROOT, 'tr', spc_name, stx_name)
    ids = {}
    if os.path.exists(base + '.tsv'):
        for ln in open(base + '.tsv', encoding='utf-8'):
            ln = ln.rstrip('\r\n')
            if not ln or ln.startswith('#'): continue
            i, _, t = ln.partition('\t')
            if t: ids[int(i)] = t.replace('\\r', '\r').replace('\\n', '\n').translate(FIX)
    en = {}
    ref = os.path.join(ROOT, 'translation', spc_name, stx_name + '.json')
    if os.path.exists(ref):
        for x in json.load(open(ref, encoding='utf-8')):
            if x['id'] in ids: en[x['en']] = ids[x['id']]
    return ids, en

def build():
    font_chars = None
    fstx = open(os.path.join(FONT_DIR, 'v3_font00.stx'), 'rb').read()
    fsrdv = open(os.path.join(FONT_DIR, 'v3_font00.srdv'), 'rb').read()
    font_chars = set(Font(fstx, fsrdv).chars)
    out = os.path.join(ROOT, 'mod')
    shutil.rmtree(out, ignore_errors=True)
    cache = {}
    stats = {'done': 0, 'total': 0}; warns = []
    for key, path in TARGETS:
        if not has_translations(path): continue
        if key not in cache: cache[key] = CPK(GAME + CPKS[key], os.path.join(ROOT, 'backup', key, 'toc.bin'))
        c = cache[key]
        e = next(x for x in c.files if x['path'] == path)
        s = SPC(c.read(e))
        spc_name = os.path.basename(path).split('.')[0]
        count_stats = path.startswith('game_resident') or '/007/' in path
        for en_ in s.entries:
            nm = en_['name']
            if nm == 'v3_font00.stx': s.set(en_, fstx); continue
            if nm == 'v3_font00.srdv': s.set(en_, fsrdv); continue
            if not nm.endswith('.stx'): continue
            data = s.get(en_)
            if data[:4] != b'STXT': continue
            meta, strs = stx_read(data)
            ids, by_en = load_tr(spc_name, nm[:-4])
            if 'Ascii' in nm:  # ASCII-only lists: fold Turkish letters
                fold = str.maketrans('çğıİöşüÇĞÖŞÜ', 'cgiIosuCGOSU')
                ids = {k: v.translate(fold) for k, v in ids.items()}
                by_en = {k: v.translate(fold) for k, v in by_en.items()}
            new = []; changed = False
            for i, t in strs:
                tr = by_en.get(t) if '/007/' not in path else ids.get(i)
                if tr is None and '/007/' not in path: tr = None
                if count_stats and t.strip():
                    stats['total'] += 1
                    if tr: stats['done'] += 1
                if tr:
                    if TAG.findall(tr) != TAG.findall(t):
                        warns.append('%s/%s #%d tag mismatch' % (spc_name, nm, i))
                    bad = {ch for ch in tr if ord(ch) not in font_chars and ch not in '\r\n' and ch not in t}
                    if bad: warns.append('%s/%s #%d chars not in font: %s' % (spc_name, nm, i, ''.join(sorted(bad))))
                    new.append((i, tr)); changed = True
                else:
                    new.append((i, t))
            if changed: s.set(en_, stx_write(meta, new))
        dst = os.path.join(out, key, path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(s.build())
    warns = list(dict.fromkeys(warns))
    for w in warns[:50]: print('  !', w)
    if len(warns) > 50: print('  ! ... %d more warnings' % (len(warns) - 50))
    print('translated %d / %d lines' % (stats['done'], stats['total']))
    return out

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    if cmd in ('build', 'apply'):
        out = build()
        if cmd == 'apply':
            for key, name in CPKS.items():
                cpk_patch.apply(GAME + name, os.path.join(out, key), os.path.join(ROOT, 'backup', key))
    elif cmd == 'restore':
        for key, name in CPKS.items():
            print(key, cpk_patch.restore(GAME + name, os.path.join(ROOT, 'backup', key)))
