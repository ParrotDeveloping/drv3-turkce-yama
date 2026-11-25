"""Build a game_resident_US.spc variant for crash bisecting and apply only it.
variants: orig_recompress | tex_only | full | stx_only"""
import sys, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cpk import CPK
from spc import SPC
import cpk_patch
GAME = r'C:/Program Files (x86)/Steam/steamapps/common/Danganronpa V3 Killing Harmony/data/win/'
v = sys.argv[1]
c = CPK(GAME + 'partition_resident_win.cpk', os.path.join(ROOT, 'backup', 'resident', 'toc.bin'))
e = next(x for x in c.files if x['path'] == 'game_resident/game_resident_US.spc')
s = SPC(c.read(e))
fstx = open(os.path.join(ROOT, 'font', 'v3_font00.stx'), 'rb').read()
fsrdv = open(os.path.join(ROOT, 'font', 'v3_font00.srdv'), 'rb').read()
for en in s.entries[:2]:
    orig = s.get(en)
    if v == 'orig_recompress': s.set(en, orig)
    elif v == 'orig_raw': pass
    elif v == 'tex_only' and en['name'].endswith('.srdv'): s.set(en, fsrdv)
    elif v == 'stx_only' and en['name'].endswith('.stx'): s.set(en, fstx)
    elif v == 'full': s.set(en, fstx if en['name'].endswith('.stx') else fsrdv)
    elif v == 'full_raw':
        en['raw'] = fstx if en['name'].endswith('.stx') else fsrdv; en['size'] = len(en['raw']); en['cf'] = 1
mod = os.path.join(ROOT, 'mod_variant')
p = os.path.join(mod, 'game_resident', 'game_resident_US.spc')
os.makedirs(os.path.dirname(p), exist_ok=True)
open(p, 'wb').write(s.build())
cpk_patch.apply(GAME + 'partition_resident_win.cpk', mod, os.path.join(ROOT, 'backup', 'resident'))
