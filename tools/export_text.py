"""Export STX strings from game SPCs to translation/<spc>/<stx>.json  ([{"id":..,"en":..,"tr":""}])
Existing "tr" values are preserved on re-export."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from cpk import CPK
from spc import SPC, stx_read

GAME = r'C:/Program Files (x86)/Steam/steamapps/common/Danganronpa V3 Killing Harmony/data/win/'
TARGETS = {
    'resident': ('partition_resident_win.cpk', ['game_resident/game_resident_US.spc']),
    'data_us': ('partition_data_win_us.cpk', ['wrd_script/007/%s_text_US.SPC' % n for n in
                ['chap0', 'chap1', 'chap2', 'chap3', 'chap4', 'chap5', 'chap6', 'chap7', 'ainori', 'gallery', 'sub_routine']]
                + ['wrd_data/map_obj_name_text_US.SPC']),
}

def export(out_root, which):
    for key in which:
        cpkname, paths = TARGETS[key]
        c = CPK(GAME + cpkname)
        for p in paths:
            e = next(x for x in c.files if x['path'] == p)
            s = SPC(c.read(e))
            d = os.path.join(out_root, os.path.basename(p).split('.')[0])
            os.makedirs(d, exist_ok=True)
            for en in s.entries:
                if not en['name'].endswith('.stx'): continue
                data = s.get(en)
                if data[:4] != b'STXT': continue
                _, strs = stx_read(data)
                fn = os.path.join(d, en['name'][:-4] + '.json')
                old = {}
                if os.path.exists(fn):
                    old = {x['id']: x['tr'] for x in json.load(open(fn, encoding='utf-8'))}
                rows = [{'id': i, 'en': t, 'tr': old.get(i, '')} for i, t in strs]
                json.dump(rows, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('exported', p)

if __name__ == '__main__':
    export(sys.argv[1], sys.argv[2:] or list(TARGETS))
