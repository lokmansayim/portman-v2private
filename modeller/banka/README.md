# Model bankası · atölye kısmı (İE-09, D-20)

Çekirdek banka `beyin/veri/adaylar.json` ve `modeller/*.json`'dur (yedi model; referans girdi, değişmez). Atölyede üretilen modeller burada, her biri kendi klasöründe durur. Klasör adı ASCII'dir (Ç → C): `C8801D/`. Referans girdi kalıpları (`modeller/*.json`) bu alt klasöre inmez; yeni model referansı değiştirmez.

Araç: `python3 araclar/atolye.py …` (tarif `.claude/skills/atolye/SKILL.md`). Okuyan: `beyin/banka.py` (yalnız `kabul` kartlar) → Katalog, `araclar/aday_kabul.py`, `araclar/kabul_paketi.py`. İE-14 uyarlaması (`plan_uretici._banka`) atölye bankasını okumaz (İE-09 PR-1).

| Dosya | İçerik |
|---|---|
| `tanim.json` | Yapı Tanımı 0.5 (cm). Kabulden sonra donar (D-07): değişirse yeni kod ya da sürüm. |
| `kart.json` | Model kartı, `portman.model_karti/0.1` (aşağıda). |
| `kontrol.json` | Kabulde yazılır, `portman.banka_kontrol/0.1`: `tanim_sha256`, `kural_seti` ve özeti (pim: kartın pimi varsa metraj kapısının ölçüldüğü set, yoksa kabuldeki en yeni dondurulmuş set), `karkas_kurali` ve özeti (pimliyse), `hizli` (dış ölçü, brüt oturum, veranda, odalar, oda programı, pencere, kapı, açıklıklar, çatı tipi, düzlem sayısı, yüzey, kenar boyları, yükleme listesinin satır sayısı, çelik kg, grupları ve kanonik özeti), `tam` (çizim setinin içerik izleri: PNG bayt, PDF içerik, JSON kanonik, IFC ve DXF içerik; sabit üretim zamanı, perspektifsiz). Yeniden dondurma yalnız ayrı, onaylı PR'da (`dondur`, `dondurma` alanı). |
| `kart.png` | Aday kartı görseli (kabul edilen çizimin `<kod>_bayi_gorsel.png`'si). |

## Kart (`portman.model_karti/0.1`)

| Alan | Anlamı |
|---|---|
| `kod`, `gosterim`, `ad`, `aile`, `yapi_turu`, `kat` | Kimlik. Kod çekirdek bankayla çakışmaz. |
| `taban_model`, `varyant_turu` | Çatı varyantıysa taban modelin kodu ve `cati`. Çatı varyantı bayiye ayrı model olarak sunulmaz. |
| `musteri_projesi` | Müşteri projesi bayiye adsızdır. |
| `kaynak` | `tur` (istek, proje, varyant), `metin` (Lokman'ın sözü, tarihle), `proje` (AP-NN ya da ÇP-NN; `ac --proje` ya da `kaynak --proje`), `dosyalar` (etiket, uzantı, boyut, SHA-256; dosyanın kendisi ve adı depoya girmez), varyantta taban tanım ve özeti. |
| `kaynak_degerleri` | Kaynakta yazan değerler ve nereden geldikleri (kod, DXF, görsel okuma, Lokman): odalar, brüt m², oda programı, pencere, kapı, dış ölçü, çatı tipi. Kontrol sayfasında çizimle yan yana. |
| `durum` | `taslak` → `kontrolde` → `kabul` ya da `ret`; metraj kapısı geçmezse `beklemede` (kabul edilemez). |
| `metraj_testi` | `yok` (çelik hakemi ölçümü yok, koşulmadı), `gecti` ya da `beklemede`. Kaynağı her zaman çelik hakemidir (İE-16, `testler/celik/`; `metraj --celik ÇP-NN`): proje, hakemin sonucu, bizim ve gerçek liste kg, fark %, eşik ±%3, kapı dışı türler, tür tür tablo (açık projede hakemin işlevleriyle yeniden hesaplanır), mühür, listenin özeti ve commit'leri, yöntem. Atölye listeyi kendisi okumaz (D-28 madde 1, Z-03). |
| `pim` | Metraj kapısının ölçüldüğü kural seti ve karkas kuralı kopyaları (`testler/celik/projeler/setler/<sha16>.json`) ve özetleri. Model bu pimle çizilir, kontrol dosyası bu pimle yazılır; pim çizimden sonra değişirse kart `taslak`'a döner. |
| `olcum`, `son_cizim` | Son çizimin ölçümü, çizim numarası, tanım özeti, denetimler, çıktı klasörü ve kontrol sayfası. |
| `duzeltmeler` | Lokman'ın düzeltmeleri, türüyle: `okuma`, `tercih`, `kural`, `motor` (motor kusuru defterine de). |
| `gecmis` | Olaylar (ac, varyant, kaynak, ciz, duzelt, metraj, kabul, kabul_durdu, ret, dondur), Türkiye saatiyle. Gün sonu sayımı buradan. |
| `kabul`, `aday` | Kabul kaydı (kim, tarih, D-11, çizim, kural seti, metraj kapısı) ve aday kaydı (`aday_kaydet.genel` ile aynı alanlar; `tanim` depo köküne, `gorsel` `is_emri/`e göre). |

Bayiye sunulma K-A10 kabul kaydına bağlıdır: atölye modeli yalnız kabul kümesinde açıkça varsa görünür (haftalık sürümden sonra `vps/ie08_adaylar.sh`).
