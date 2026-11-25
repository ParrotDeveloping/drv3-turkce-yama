"""Fill untranslated lines whose English text was already translated anywhere (all SPCs)."""
import os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def tsv_read(fn):
    d = {}
    if os.path.exists(fn):
        for l in open(fn, encoding='utf-8'):
            a, _, b = l.rstrip('\r\n').partition('\t')
            if b: d[int(a)] = b
    return d
memo = {}
files = sorted(glob.glob(os.path.join(ROOT, 'translation', '*', '*.json')))
for fn in files:
    spc = os.path.basename(os.path.dirname(fn)); name = os.path.basename(fn)[:-5]
    tr = tsv_read(os.path.join(ROOT, 'tr', spc, name + '.tsv'))
    for x in json.load(open(fn, encoding='utf-8')):
        if x['id'] in tr: memo.setdefault(x['en'], tr[x['id']])
added = 0
for fn in files:
    spc = os.path.basename(os.path.dirname(fn)); name = os.path.basename(fn)[:-5]
    out = os.path.join(ROOT, 'tr', spc, name + '.tsv')
    tr = tsv_read(out); n0 = len(tr)
    for x in json.load(open(fn, encoding='utf-8')):
        if x['id'] not in tr and x['en'] in memo and x['en'].strip():
            tr[x['id']] = memo[x['en']]
    if len(tr) > n0:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            for k in sorted(tr): f.write('%d\t%s\n' % (k, tr[k]))
        added += len(tr) - n0
print('autofilled', added, 'lines')
