"""Danganronpa V3 Türkçe Yama - kurulum / kaldırma aracı (son kullanıcı).

Oyun dosyaları pakette yoktur: font ve metinler kullanıcının kendi oyun
kurulumundan okunur, Türkçe çeviri üzerine işlenir ve oyuna yazılır.
Orijinal dosyalar oyun klasöründe 'TurkceYama_yedek' içine yedeklenir.
"""
import sys, os, re, json, shutil, subprocess, tempfile, traceback

FROZEN = getattr(sys, 'frozen', False)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = getattr(sys, '_MEIPASS', os.path.dirname(HERE))  # tr/ klasörünün bulunduğu yer
sys.path.insert(0, HERE)
from cpk import CPK, decompress_layla
from spc import SPC, stx_read, stx_write
from font import Font
import cpk_patch, gen_font

VERSION = '1.0'
CPKS = {'resident': 'partition_resident_win.cpk', 'data_us': 'partition_data_win_us.cpk'}
SCRIPT_VERSIONS = ['003', '004', '005', '006', '007']
SCRIPTS = ['chap0', 'chap1', 'chap2', 'chap3', 'chap4', 'chap5', 'chap6', 'chap7', 'ainori', 'gallery']
TARGETS = [('resident', 'game_resident/game_resident_US.spc')]
for n in SCRIPTS:
    TARGETS += [('data_us', 'wrd_script/%s/%s_text_US.SPC' % (v, n)) for v in SCRIPT_VERSIONS]
TARGETS += [('data_us', 'wrd_data/map_obj_name_text_US.SPC')]
TAG = re.compile(r'<[^>]*>')
FIX = str.maketrans({'â': 'a', 'Â': 'A', 'î': 'i', 'Î': 'I', 'û': 'u', 'Û': 'U', '’': "'", '‘': "'", '“': '"', '”': '"'})
FOLD = str.maketrans('çğıİöşüÇĞÖŞÜ', 'cgiIosuCGOSU')
DEFAULT_GAME = r'C:\Program Files (x86)\Steam\steamapps\common\Danganronpa V3 Killing Harmony'


def say(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- oyun bulma
def steam_libraries():
    libs = []
    for base in (os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), os.environ.get('ProgramFiles', r'C:\Program Files')):
        vdf = os.path.join(base, 'Steam', 'steamapps', 'libraryfolders.vdf')
        if os.path.exists(vdf):
            for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf-8', errors='ignore').read()):
                libs.append(m.group(1).replace('\\\\', '\\'))
    return libs


def is_game_dir(d):
    return d and os.path.exists(os.path.join(d, 'data', 'win', CPKS['data_us']))


def find_game():
    cands = [os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__)), DEFAULT_GAME]
    cands += [os.path.join(l, 'steamapps', 'common', 'Danganronpa V3 Killing Harmony') for l in steam_libraries()]
    for d in cands:
        if is_game_dir(d): return d
        if is_game_dir(os.path.dirname(d)): return os.path.dirname(d)
    return None


def game_running():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Dangan3Win.exe'], capture_output=True, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        return 'Dangan3Win.exe' in out
    except Exception:
        return False


# ---------------------------------------------------------------- orijinal okuma
class OrigCPK:
    """Yama uygulanmış olsa bile orijinal dosyaları döndürür (yedekteki TOC + slotlar)."""
    def __init__(self, path, bdir):
        toc = os.path.join(bdir, 'toc.bin')
        self.c = CPK(path, toc if os.path.exists(toc) else None)
        self.slots = {}
        meta = os.path.join(bdir, 'meta.json')
        if os.path.exists(meta):
            for s in json.load(open(meta)).get('slots', []):
                self.slots[s['path']] = os.path.join(bdir, s['file'])
        self.by_path = {e['path']: e for e in self.c.files}

    def read(self, path):
        e = self.by_path[path]
        if path in self.slots:
            raw = open(self.slots[path], 'rb').read()[:e['FileSize']]
            if e['ExtractSize'] and e['ExtractSize'] != e['FileSize']:
                raw = decompress_layla(raw)
            return raw
        return self.c.read(e)

    def close(self):
        self.c.f.close()


# ---------------------------------------------------------------- çeviri
def load_ids(spc_name, stx_name):
    fn = os.path.join(DATA, 'tr', spc_name, stx_name + '.tsv')
    ids = {}
    if os.path.exists(fn):
        for ln in open(fn, encoding='utf-8'):
            ln = ln.rstrip('\r\n')
            if not ln or ln.startswith('#'): continue
            i, _, t = ln.partition('\t')
            if t: ids[int(i)] = t.replace('\\r', '\r').replace('\\n', '\n').translate(FIX)
    return ids


def font_is_turkish(cpk):
    s = SPC(cpk.read('game_resident/game_resident_US.spc'))
    d = {e['name']: s.get(e) for e in s.entries if e['name'] in ('v3_font00.stx', 'v3_font00.srdv')}
    return ord('ş') in Font(d['v3_font00.stx'], d['v3_font00.srdv']).chars


def make_font(cpks, tmp):
    s = SPC(cpks['resident'].read('game_resident/game_resident_US.spc'))
    src = os.path.join(tmp, 'font_orig'); dst = os.path.join(tmp, 'font_tr')
    os.makedirs(src, exist_ok=True); os.makedirs(dst, exist_ok=True)
    for e in s.entries:
        if e['name'] in ('v3_font00.stx', 'v3_font00.srdv'):
            open(os.path.join(src, e['name']), 'wb').write(s.get(e))
    gen_font.main(src, dst)
    return open(os.path.join(dst, 'v3_font00.stx'), 'rb').read(), open(os.path.join(dst, 'v3_font00.srdv'), 'rb').read()


def build(cpks, out, fstx, fsrdv):
    font_chars = set(Font(fstx, fsrdv).chars)
    en_maps = {}  # spc_name -> {stx: {english: turkish}}  (007 sürümünden)
    for key, path in TARGETS:
        spc_name = os.path.basename(path).split('.')[0]
        s = SPC(cpks[key].read(path))
        is_ref = '/007/' in path or not path.startswith('wrd_script')
        if is_ref: en_maps[spc_name] = {}
        for e in s.entries:
            nm = e['name']
            if nm == 'v3_font00.stx': s.set(e, fstx); continue
            if nm == 'v3_font00.srdv': s.set(e, fsrdv); continue
            if not nm.endswith('.stx'): continue
            data = s.get(e)
            if data[:4] != b'STXT': continue
            meta, strs = stx_read(data)
            if is_ref:
                ids = load_ids(spc_name, nm[:-4])
                en_maps[spc_name][nm] = {t: ids[i] for i, t in strs if i in ids}
                look = lambda i, t: ids.get(i)
            else:
                m = en_maps.get(spc_name, {}).get(nm, {})
                look = lambda i, t: m.get(t)
            new = []; changed = False
            for i, t in strs:
                tr = look(i, t)
                if tr and 'Ascii' in nm: tr = tr.translate(FOLD)
                if tr:
                    new.append((i, tr)); changed = True
                else:
                    new.append((i, t))
            if changed: s.set(e, stx_write(meta, new))
        dst = os.path.join(out, key, path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(s.build())


def ordered_targets():
    """007 sürümü (referans) önce işlenmeli; diğer sürümler İngilizce metinle eşleşir."""
    ref = [t for t in TARGETS if '/007/' in t[1] or not t[1].startswith('wrd_script')]
    rest = [t for t in TARGETS if t not in ref]
    return ref + rest


# ---------------------------------------------------------------- komutlar
def install(game):
    win = os.path.join(game, 'data', 'win')
    bak = os.path.join(win, 'TurkceYama_yedek')
    tmp = tempfile.mkdtemp(prefix='drv3tr_')
    try:
        say('\n[1/4] Oyun dosyaları okunuyor...')
        cpks = {k: OrigCPK(os.path.join(win, n), os.path.join(bak, k)) for k, n in CPKS.items()}
        if font_is_turkish(cpks['resident']):
            for c in cpks.values(): c.close()
            raise SystemExit('\n! Oyun dosyaları zaten değiştirilmiş ama yedek bulunamadı.\n'
                             '  Önce Steam > Kütüphane > oyuna sağ tık > Özellikler > Yüklü Dosyalar >\n'
                             '  "Oyun dosyalarının bütünlüğünü doğrula" yap, sonra kurulumu tekrar çalıştır.')
        say('[2/4] Türkçe karakterli font hazırlanıyor...')
        fstx, fsrdv = make_font(cpks, tmp)
        say('[3/4] Çeviri işleniyor (birkaç dakika sürebilir)...')
        global TARGETS
        TARGETS = ordered_targets()
        out = os.path.join(tmp, 'mod')
        build(cpks, out, fstx, fsrdv)
        for c in cpks.values(): c.close()
        say('[4/4] Oyuna yazılıyor...')
        for k, n in CPKS.items():
            cpk_patch.apply(os.path.join(win, n), os.path.join(out, k), os.path.join(bak, k))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    say('\nKURULUM TAMAMLANDI! Oyunu Steam\'den açabilirsin.')


def uninstall(game):
    win = os.path.join(game, 'data', 'win')
    bak = os.path.join(win, 'TurkceYama_yedek')
    ok = False
    for k, n in CPKS.items():
        if cpk_patch.restore(os.path.join(win, n), os.path.join(bak, k)): ok = True
    if ok:
        shutil.rmtree(bak, ignore_errors=True)
        say('\nYama kaldırıldı, oyun orijinal haline döndü.')
    else:
        say('\nYedek bulunamadı. Steam > Kütüphane > oyuna sağ tık > Özellikler > Yüklü Dosyalar >')
        say('"Oyun dosyalarının bütünlüğünü doğrula" ile orijinal dosyaları geri alabilirsin.')


def main():
    say('=' * 56)
    say('  Danganronpa V3: Killing Harmony - Türkçe Yama v%s' % VERSION)
    say('=' * 56)
    game = find_game()
    while not game:
        say('\nOyun klasörü bulunamadı.')
        say('Oyunun klasör yolunu yapıştır (Steam > oyuna sağ tık > Yönet > Yerel dosyalara göz at):')
        p = input('> ').strip().strip('"')
        if is_game_dir(p): game = p
    say('\nOyun klasörü: ' + game)
    if game_running():
        say('\n! Oyun şu an açık. Önce oyunu kapat, sonra bu programı tekrar çalıştır.')
        return
    say('\n  1) Türkçe yamayı KUR')
    say('  2) Yamayı KALDIR (orijinale dön)')
    say('  3) Çıkış')
    ch = input('\nSeçimin (1/2/3): ').strip()
    if ch == '1': install(game)
    elif ch == '2': uninstall(game)


if __name__ == '__main__':
    try:
        main()
    except PermissionError:
        say('\n! Oyun dosyalarına yazılamadı. Programa sağ tıklayıp "Yönetici olarak çalıştır" ile tekrar dene.')
    except SystemExit as e:
        say(str(e))
    except Exception:
        traceback.print_exc()
        say('\n! Bir hata oluştu. Yukarıdaki yazının ekran görüntüsünü alıp geliştiriciye gönder.')
    input('\nKapatmak için Enter\'a bas...')
