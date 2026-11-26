"""Geliştirici komutları (son kullanıcı aracı kurulum.py ile aynı kodu kullanır).

  build_patch.py build      -> mod/<cpk>/... dosyalarını yazar (oyuna dokunmaz)
  build_patch.py apply      -> yamayı oyuna uygular (yedek: <oyun>/data/win/TurkceYama_yedek)
  build_patch.py restore    -> orijinal dosyaları geri yükler

Çeviriler: tr/<spc_adı>/<stx_adı>.tsv  satırlar: "<id>\t<türkçe metin>"  (\\n = yeni satır)
Ana kaynak 007 sürümüdür; 003-006 sürümleri İngilizce metin eşleşmesiyle doldurulur.
"""
import sys, os, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kurulum as K

GAME = K.find_game() or K.DEFAULT_GAME

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    if K.game_running(): raise SystemExit('Oyun açık, önce kapat.')
    if cmd == 'build':
        win = os.path.join(GAME, 'data', 'win'); bak = os.path.join(win, 'TurkceYama_yedek')
        cpks = {k: K.OrigCPK(os.path.join(win, n), os.path.join(bak, k)) for k, n in K.CPKS.items()}
        tmp = tempfile.mkdtemp()
        fstx, fsrdv = K.make_font(cpks, tmp)
        out = os.path.join(ROOT, 'mod'); shutil.rmtree(out, ignore_errors=True)
        K.TARGETS = K.ordered_targets()
        K.build(cpks, out, fstx, fsrdv)
        shutil.rmtree(tmp, ignore_errors=True)
        print('built ->', out)
    elif cmd == 'apply':
        K.install(GAME)
    elif cmd == 'restore':
        K.uninstall(GAME)
