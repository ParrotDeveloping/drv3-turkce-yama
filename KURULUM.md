# Kurulum Rehberi

> ⚠️ **GELİŞTİRME AŞAMASINDA** — Bu rehber yama bittiğinde güncellenecek. Şu an hazır bir kurulum paketi yok; aşağıdaki adımlar geliştirici kurulumudur.

## Gereksinimler

- Danganronpa V3: Killing Harmony (Steam, Windows)
- Python 3.10+
- Oyun klasörü: `C:\Program Files (x86)\Steam\steamapps\common\Danganronpa V3 Killing Harmony`
  (başka yerdeyse `tools/build_patch.py` içindeki `GAME` satırını değiştir)

## Kurulum (geliştirici)

1. Oyunu kapat (Dangan3Win.exe çalışmıyor olmalı).
2. Bu repoyu indir ve klasörünün içinde komut satırı aç.
3. Font dosyalarını (`v3_font00.stx`, `v3_font00.srdv`) `font/` klasörüne koy.
4. Yamayı uygula:
   ```
   py -I tools/build_patch.py apply
   ```
   Orijinal dosyalar otomatik olarak `backup/` klasörüne yedeklenir.
5. Oyunu Steam'den aç.

## Kaldırma

```
py -I tools/build_patch.py restore
```

Ya da Steam → Oyun → Özellikler → Yüklü Dosyalar → **Oyun dosyalarının bütünlüğünü doğrula**.

## Bilinen notlar

- Steam oyunu güncellerse yamayı yeniden uygulaman gerekir.
- Oyun açıkken yama uygulanmaz.

## Son kullanıcı kurulumu

Yama bitince tek tıkla kurulum paketi ve adım adım Türkçe rehber buraya eklenecek.
