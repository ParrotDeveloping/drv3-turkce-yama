"""Write the next untranslated lines of an SPC (in file/id order) to batches/_next.txt, up to a char budget.
usage: next.py <spc> [budget=4200]   prints remaining count."""
import sys, os, json, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spc = sys.argv[1]; budget = int(sys.argv[2]) if len(sys.argv) > 2 else 4200
out = []; used = 0; remaining = 0; full = False
for fn in sorted(glob.glob(os.path.join(ROOT, 'translation', spc, '*.json'))):
    name = os.path.basename(fn)[:-5]
    t = os.path.join(ROOT, 'tr', spc, name + '.tsv')
    done = set()
    if os.path.exists(t):
        done = {int(l.split('\t')[0]) for l in open(t, encoding='utf-8') if '\t' in l}
    rows = [x for x in json.load(open(fn, encoding='utf-8')) if x['en'].strip() and x['id'] not in done]
    remaining += len(rows)
    header = False
    for x in rows:
        if full: break
        line = '%d\t%s' % (x['id'], x['en'].replace('\r', '\\r').replace('\n', '\\n'))
        if used + len(line) > budget and out:
            full = True; break
        if not header:
            out.append('## ' + name); header = True
        out.append(line); used += len(line) + 1
open(os.path.join(ROOT, 'batches', '_next.txt'), 'w', encoding='utf-8').write('@ ' + spc + '\n' + '\n'.join(out) + '\n')
print('remaining', remaining, 'in', spc, '| chunk lines', sum(1 for l in out if not l.startswith('## ')))
