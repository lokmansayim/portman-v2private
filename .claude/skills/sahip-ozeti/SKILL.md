---
name: sahip-ozeti
description: Lokman için 10 satırlık durum özeti — canlıda ne var, hangi iş açık, onayını bekleyenler, açık riskler, tarihli son kanıt. Kod yazmayan sahibin diliyle; dosya değiştirmez.
disable-model-invocation: true
---

# Sahip özeti

Kaynaklar (sırayla oku, değiştirme): `docs/durum/`'daki en yeni ekler (`main` ve açık iş dalları; 28 Ekim 2026'dan önceki durum `DURUM.md`'de), `KARARLAR/README.md` › "Açık kararlar", `docs/is_emirleri/` altındaki açık iş emirleri (Kanıt bölümü boş olanlar), varsa en yeni `docs/devir/` notu.

Çıktı tam olarak şu başlıklarla, her madde tek cümle, Türkçe, teknik terim yerine sonuç:

1. **Canlıda ne var** — bayi/Patron hattında bugün ne çalışıyor, hangi modda.
2. **Açık iş** — kod, dal, kullanıcı adımlarının durumu (Çalışmıyor / Kısmen / Yerelde / Canlıda).
3. **Senin onayını bekleyenler** — merge, silme, ücretli deneme, canlı değişiklik; her biri için bir evet/hayır sorusu.
4. **Senin kararını bekleyenler** — açık kararlar (K16, K3/K4, Z-03/Z-06 vb.) ve her birinin neyi tıkadığı.
5. **Açık riskler** — tarihli (anahtar son kullanma, sunucu erişimi, imzasız paket).
6. **Son kanıt** — en son doğrulamanın tarihi ve sayıları (harness, referans, test).
7. **Ölçüm** — varsa gerçek veriyle ölçülmüş son sonuç (ör. yükleme listesi eşleşmesi); "kural görmemiş veriyle" olup olmadığını belirt.
8. **Sıradaki en küçük adım** — bir oturumda bitecek, kanıtı tanımlı tek iş.

Kural: "çalışıyor" yalnız durum eklerindeki (ya da `DURUM.md`'deki) tarihli kanıta dayanır; kanıtı olmayan şey "kâğıtta" diye yazılır. Kişi adı yazma.
