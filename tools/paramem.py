"""Paragraph-level translation memory for long multi-section texts.
  paramem.py <spc> <stx> fill   -> fills pages whose every paragraph is known; writes unknown paragraphs to batches/_para.txt
  paramem.py <spc> <stx> add <file>  -> file lines 'EN<TAB>TR' (escaped \\n) added to memory, then fill
Paragraphs are split on blank lines (\\n\\n)."""
import sys, os, json, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spc, stx, cmd = sys.argv[1:4]
MEM = os.path.join(ROOT, 'batches', 'paramem_%s.json' % stx)
SEP = re.compile(r'(\n\n+)')
def tsv(fn):
    d = {}
    if os.path.exists(fn):
        for l in open(fn, encoding='utf-8'):
            a, _, b = l.rstrip('\r\n').partition('\t')
            if b: d[int(a)] = b.replace('\\r', '\r').replace('\\n', '\n')
    return d
mem = json.load(open(MEM, encoding='utf-8')) if os.path.exists(MEM) else {}
src = {x['id']: x['en'] for x in json.load(open(os.path.join(ROOT, 'translation', spc, stx + '.json'), encoding='utf-8'))}
trfn = os.path.join(ROOT, 'tr', spc, stx + '.tsv')
tr = tsv(trfn)
# learn from aligned translated pages
for i, t in tr.items():
    e = SEP.split(src.get(i, '')); k = SEP.split(t)
    if len(e) == len(k):
        for a, b in zip(e[::2], k[::2]):
            if a.strip(): mem.setdefault(a, b)
if cmd == 'add':
    for l in open(sys.argv[4], encoding='utf-8'):
        a, _, b = l.rstrip('\r\n').partition('\t')
        if b: mem[a.replace('\\n', '\n')] = b.replace('\\n', '\n')
unknown = []
for i, e in src.items():
    if i in tr or not e.strip(): continue
    parts = SEP.split(e)
    if all((not p.strip()) or p in mem for p in parts[::2]):
        out = ''.join(mem.get(p, p) if j % 2 == 0 else p for j, p in enumerate(parts))
        tr[i] = out
    else:
        for p in parts[::2]:
            if p.strip() and p not in mem and p not in unknown: unknown.append(p)
json.dump(mem, open(MEM, 'w', encoding='utf-8'), ensure_ascii=False)
with open(trfn, 'w', encoding='utf-8') as f:
    for k in sorted(tr): f.write('%d\t%s\n' % (k, tr[k].replace('\r', '\\r').replace('\n', '\\n')))
open(os.path.join(ROOT, 'batches', '_para.txt'), 'w', encoding='utf-8').write(
    '\n'.join(p.replace('\n', '\\n') for p in unknown) + '\n')
print('pages done', len(tr), '/', len([1 for e in src.values() if e.strip()]), ' unknown paragraphs', len(unknown))
