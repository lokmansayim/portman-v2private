# Defter · "unutmama" klasörü

Lokman'ın isteği (28 Ekim 2026): "LLM devamlı unuttuğu için hep başa dönüyoruz; kullandığın ne varsa aynı klasörde yeni bir klasöre
kaydet, ne yaptığımızı atom seviyesinde bilmem gerekiyor." Bu klasör o kayıttır. Her oturumun kendi tarihli alt klasörü vardır.

## Bir alt klasörde ne var

| Dosya | Ne |
|---|---|
| `ADIMLAR.md` | **Atomik adım günlüğü.** Her adım numaralı (A001…), saatli; ne yapıldı, nerede, sonuç/kanıt, durum. Oturum boyunca her adımdan sonra yazılır. |
| `BAGLAM.md` | O oturumun kısa bağlamı: amaç, kurallar (3–5 satır), dosya yolları, karar verilmiş şeyler, açık sorular. Yeni oturum önce bunu okur. |
| `kaynak_kopyalari/` | Oturumda okunan her kaynağın **o günkü kopyası** (CLAUDE.md, AGENTS.md, `.claude/rules/*`, iş emri belgeleri, İş Emri JSON'ları). Asılları depoda kendi yerinde; burası donmuş fotoğraf. |
| `autocad_komutlari/` | AutoCAD'de çizilen her adımın komut dosyası (`.scr`). Aynı adım, aynı dosyayla yeniden çizilebilir. |
| `plan_*.jpg` | Lokman'ın gönderdiği plan görselleri. |

## Yeni oturum protokolü (asistan için)

1. `defter/<en yeni klasör>/BAGLAM.md` oku (2 dk).
2. `ADIMLAR.md`'nin **son 10 adımını** oku; "bekliyor" durumundakiler sıradaki iştir.
3. Ancak ondan sonra depo belgelerine (devir notu, iş emri, kural belgesi) geç.
4. Her adımdan sonra `ADIMLAR.md`'ye yaz; oturum sonunda `BAGLAM.md`'yi güncelle.

## Lokman için yeni oturum promptu (yapıştır)

> Portman'ın geliştiricisisin, ben Lokman'ım. Depo bu klasörde. Önce `defter/README.md`'yi, sonra `defter/` altındaki en yeni klasörün
> `BAGLAM.md` ve `ADIMLAR.md` dosyalarını oku; "bekliyor" adımdan devam et. Her adımı iki cümleyle Türkçe anlat, her adımdan sonra
> `ADIMLAR.md`'ye yaz. Onay gereken yerde tek soru sor. Silme, canlı, sunucu yok.
