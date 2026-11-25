"""Print untranslated lines: dump.py <spc_name> <stx_glob>..."""
import sys, os, json, glob
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spc = sys.argv[1]
for pat in sys.argv[2:]:
    for fn in sorted(glob.glob(os.path.join(ROOT, 'translation', spc, pat + '.json'))):
        name = os.path.basename(fn)[:-5]
        tsv = os.path.join(ROOT, 'tr', spc, name + '.tsv')
        done = set()
        if os.path.exists(tsv):
            done = {int(l.split('\t')[0]) for l in open(tsv, encoding='utf-8') if '\t' in l}
        rows = [x for x in json.load(open(fn, encoding='utf-8')) if x['id'] not in done and x['en'].strip()]
        if not rows: continue
        print('##', name)
        for x in rows:
            print('%d\t%s' % (x['id'], x['en'].replace('\r', '\\r').replace('\n', '\\n')))
