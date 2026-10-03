# 3 Ekim 2026 · çelik yükleme listesi denemesi

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) B3 adımı için ilk deneme.

Amaç: bir modelin metrajından yükleme listesinin kalemlerini kuralla çıkarmak; kuralları gerçek listelerle karşılaştırmak. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir.

Yöntem ve bulgular: `docs/sartname/yukleme_listesi_yontemi.md`.

| Dosya | İçerik |
|---|---|
| `kurallar.json` | Katsayılar (zayiat, levha ve parça ölçüleri, aralıklar). Her birinin kaynağı ve durumu yanında |
| `yukleme.py` | Hesap: metraj girdisinden kalemler; `--karsilastir` ile gerçek listeyle karşılaştırma |
| `girdi_uret.py` | Yapı Tanımı taslağından (`../2026-10-02_celik/`) metraj girdisi üretir; seçenek dosyası alır |
| `ornek_90m2_*.json`, `ornek_62m2_*.json` | İki gerçek listenin girdileri ve kalemleri. Kişi, bayi ve firma adı içermez |
| `sonuc/` | Karşılaştırma sonuçları ve Ç8201'in ilk taslakları (baz ve dış 140 mm) |

## Çalıştırma

```
python yukleme.py ornek_90m2_girdi.json --karsilastir ornek_90m2_gercek_liste.json
python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
python girdi_uret.py ../2026-10-02_celik/C8201.json
python yukleme.py sonuc/C8201_girdi.json --cikti sonuc/C8201_yukleme_taslak.json --md sonuc/C8201_yukleme_taslak.md
```

## Sonuç (3 Ekim 2026)

- 90 m² liste (beşik çatı): karşılaştırılan 27 kalemin 20'sinde adet aynı.
- 62 m² liste (kırma çatı, dış 140 mm): 29 kalemin 26'sında aynı.
- Farkların biri dışında hepsi 1–3 adet; köşebent kuralı bilinmiyor.
- Ç8201 için ilk taslak üretildi. Çelik panel grubu (panel adedi, kg) yok: karkas çizimi gerekir.

## Sınırlar

- `uydurma` durumundaki katsayılar bu iki listeye bakılarak seçildi; aynı listelerle tutması kanıt değildir. Üçüncü bir listeyle yalnız kısmi sınama yapıldı.
- Örnek girdilerde çatı uzunlukları, tavan alanları ve iniş sayısı listelerde yazan değerlerdir.
- Çatı örtüsünde yalnız iki tip var: OSB üstü metal kiremit ve sandviç panel. Tek kat panel, shingle, dekoratif sıva, betopan, yalıpan yok.
- Çift kat, döşeme, merdiven yok.
- Gerçek listelerin çalışma kitapları depoda değil; Lokman'ın Mac'inde.
