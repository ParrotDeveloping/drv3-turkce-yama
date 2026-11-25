"""Translate a dump file via an exact-match dictionary (TSV: en<TAB>tr).
usage: mapfill.py <spc> <dump_file> <dict_file> <out_batch>  -- unmatched lines are printed."""
import sys
spc, dump, dic, out = sys.argv[1:5]
m = {}
for l in open(dic, encoding='utf-8'):
    l = l.rstrip('\n')
    if '\t' in l:
        a, b = l.split('\t', 1); m[a] = b
lines = ['@ ' + spc]; miss = 0
for l in open(dump, encoding='utf-8'):
    l = l.rstrip('\n')
    if l.startswith('## '): lines.append(l); continue
    if '\t' not in l: continue
    i, t = l.split('\t', 1)
    if t in m: lines.append(i + '|' + m[t])
    elif t.strip() in ('-', '―'): lines.append(i + '|' + t)
    else: print('MISS', i, t); miss += 1
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('written', len(lines), 'missing', miss)
