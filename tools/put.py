"""Merge a batch file into tr/<spc>/<stx>.tsv
batch format:  first line '@ <spc_name>', then '## <stx_name>' sections and 'id|text' lines.
'## a,b,c' writes the same lines into several stx files."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spc = None; names = []; buf = {}
for ln in open(sys.argv[1], encoding='utf-8'):
    ln = ln.rstrip('\r\n')
    if not ln.strip(): continue
    if ln.startswith('@ '): spc = ln[2:].strip(); continue
    if ln.startswith('## '): names = [n.strip() for n in ln[3:].split(',')]; continue
    i, sep, t = ln.partition('|')
    if not sep: i, sep, t = ln.partition('\t')
    i = int(i.strip())
    for n in names: buf.setdefault((spc, n), {})[i] = t.strip()
n_lines = 0
for (s, n), rows in buf.items():
    d = os.path.join(ROOT, 'tr', s); os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, n + '.tsv'); cur = {}
    if os.path.exists(fn):
        for l in open(fn, encoding='utf-8'):
            a, _, b = l.rstrip('\r\n').partition('\t')
            if b: cur[int(a)] = b
    cur.update(rows); n_lines += len(rows)
    with open(fn, 'w', encoding='utf-8') as f:
        for k in sorted(cur): f.write('%d\t%s\n' % (k, cur[k]))
print('wrote', n_lines, 'lines into', len(buf), 'files')
