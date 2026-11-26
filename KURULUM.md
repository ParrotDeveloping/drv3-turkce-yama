# Kurulum Rehberi

Danganronpa V3: Killing Harmony (Steam, Windows) için Türkçe yama.
Python ya da başka bir program kurman **gerekmez**.

## Kurulum (2 dakika)

1. **Oyunu kapat.**
2. `DRV3_Turkce_Yama.zip` dosyasını indir ve bir klasöre çıkar (sağ tık → *Tümünü ayıkla*).
3. `DRV3_Turkce_Yama.exe` dosyasına çift tıkla.
   - Windows *"Bilgisayarınız korundu"* derse: **Ek bilgi** → **Yine de çalıştır**.
     (Program imzasız olduğu için bu uyarı çıkar, normaldir.)
4. Açılan pencerede `1` yazıp **Enter**'a bas.
5. Yaklaşık 1 dakika bekle. **"KURULUM TAMAMLANDI!"** yazısını görünce Enter'a basıp kapat.
6. Oyunu Steam'den aç. Oyun artık Türkçe!

> Program oyunu kendisi bulur. Bulamazsa senden oyun klasörünü ister:
> Steam → oyuna sağ tık → **Yönet** → **Yerel dosyalara göz at** → üstteki adres çubuğundan yolu kopyalayıp pencereye yapıştır.

## Kaldırma

`DRV3_Turkce_Yama.exe`'yi aç, `2` yaz, Enter'a bas. Oyun orijinal (İngilizce) haline döner.

Program açılmazsa: Steam → oyuna sağ tık → **Özellikler** → **Yüklü Dosyalar** → **Oyun dosyalarının bütünlüğünü doğrula**.

## Sorun çözme

| Sorun | Çözüm |
|---|---|
| "Oyun şu an açık" | Oyunu tamamen kapat, programı tekrar aç. |
| "Oyun dosyalarına yazılamadı" | Programa sağ tık → **Yönetici olarak çalıştır**. |
| "Zaten değiştirilmiş ama yedek bulunamadı" | Steam'den **Oyun dosyalarının bütünlüğünü doğrula**, sonra tekrar kur. |
| Antivirüs programı siliyor | Yanlış alarm; dosyayı antivirüste istisnalara ekle. |
| Steam oyunu güncelledi, yazılar İngilizce oldu | Programı açıp tekrar `1` ile kur. |

## Notlar

- Paketin içinde oyun dosyası **yoktur**. Program, senin bilgisayarındaki oyunun dosyalarını okuyup Türkçe çeviriyi üstüne işler.
- Orijinal dosyalar oyun klasöründe `data\win\TurkceYama_yedek` içine yedeklenir. Bu klasörü silme; kaldırma için gerekir.
- Kayıt dosyaların (save) etkilenmez.

---

### Geliştiriciler için

```
py -I tools/build_patch.py apply     # yamayı uygula
py -I tools/build_patch.py restore   # kaldır
py -I tools/build_patch.py build     # sadece mod/ klasörüne üret
```

Gerekenler: Python 3.10+, `numpy`, `Pillow`. Kurulum paketi `tools/kurulum.py`'den PyInstaller ile üretilir:

```
py -m PyInstaller --onefile --console --name DRV3_Turkce_Yama --paths tools --add-data "tr;tr" --hidden-import gen_font --hidden-import gen_trial_font --hidden-import cpk_patch tools/kurulum.py
```
