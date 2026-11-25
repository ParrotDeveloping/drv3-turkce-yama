import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from cpk import CPK
g = sys.argv[1]
for n in ['partition_data_win.cpk', 'partition_data_win_us.cpk', 'partition_resident_win.cpk']:
    c = CPK(os.path.join(g, n))
    dirs = collections.Counter(); sz = collections.Counter()
    for e in c.files:
        d = (e.get('DirName') or '')
        dirs[d] += 1; sz[d] += e['FileSize']
    print('==', n, len(c.files))
    for d, k in sorted(dirs.items()):
        print('  %-40s %5d %8.1f MB' % (d, k, sz[d] / 1e6))
    for e in c.files:
        p = e['path'].lower()
        if 'font' in p or 'text' in p or p.endswith('.stx'):
            print('   *', e['path'], e['FileSize'])
