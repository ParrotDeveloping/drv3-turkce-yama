# Danganronpa V3: Killing Harmony — Türkçe Yama

Steam (Windows) sürümü için hayran yapımı, **tam** Türkçe çeviri.

**İndir:** [Releases](../../releases) sayfasından `DRV3_Turkce_Yama.zip` → kurulum için [KURULUM.md](KURULUM.md).

## Durum

| Bölüm | Durum |
|---|---|
| Menüler / arayüz | ✅ |
| Prolog (Bölüm 0) | ✅ |
| Bölüm 1 – 6 | ✅ |
| Epilog | ✅ |
| Ainori (bonus aşk modu) | ✅ |
| Galeri | ✅ |
| Harita / obje isimleri | ✅ |

Çevrilmeden bırakılanlar: oyuncunun görmediği geliştirici etiketleri, müzik parça isimleri ve PS4/Vita sistem mesajları.

## Klasörler

- `tr/` — yamaya giren çeviriler (`<id>\t<metin>` TSV)
- `translation/` — İngilizce + Türkçe referans JSON
- `batches/` — çeviri parti dosyaları
- `tools/` — CPK/SPC/STX okuma-yazma, font ve yama araçları (Python)
  - `kurulum.py` — son kullanıcı kurulum/kaldırma aracı (exe'ye bu derlenir)

Oyun dosyaları (CPK, font) telif nedeniyle repoda ve kurulum paketinde **yoktur**; kurulum aracı bunları kullanıcının kendi oyunundan okur.
