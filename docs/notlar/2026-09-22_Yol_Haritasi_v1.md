# Portman yol haritası v1 — 22 Eylül 2026

Dayanak: 21 Eylül araştırma raporu + Astra eleştirisi değerlendirmesi (uzlaşılan mimari: **LLM anlar, kod karar verir, Motor çizer, insan onaylar**).
Bugünkü durum: canlı kanal Patron modunda açık (3 gerçek mesaj, 2'si PDF olarak read); şablonu kodlanmış tek model P6001.
Aşamalar takvimden çok **kabul ölçütüyle** ilerler; takvim tahmindir.

## Aşama 0 — Canlı hattı güvenceye al ve ölç (bu hafta)
| İş | Kim | Çıktı |
|---|---|---|
| 0.1 İş başına ölçüm: aşama zaman damgaları + token toplamı + günlük özet (`kanal/rapor.py`) | Claude | `06_Kanal/gunluk_ozet` + panelden okunabilir JSON |
| 0.2 Test seti: 30 mesaj (regresyon) + 6 senaryo (mükerrer mesaj, çift onay, üretim sırasında revizyon, eski PDF'in yeni diye gitmemesi, medya, kayıtsız numara) | Claude (mesajlar için Lokman'dan 10 gerçek bayi cümlesi) | `kanal/tests/senaryolar.json`, geçiş raporu |
| 0.3 Yönlendirme: WhatsApp liste/buton (oda programı listesi, 3 aday butonu, "Onayla / Değiştir / Yetkili"); buton cevabı → LLM çağrısı sıfır | Claude | kanal v1.1 |
| 0.4 Beyin: alan başına kaynak mesaj + "beyan/varsayım" etiketi; onaylı katalog çıktıları önbellekten | Claude | beyin v0.2 |
| 0.5 VPS: Python işçisi VPS'e (PHP webhook paylaşımlıda kalır); LVE bellek sorunu biter | **Lokman karar** (Hetzner CX23 €5,49 / TR sağlayıcı), kurulum Claude | çalışan işçi + geri alma |
| 0.6 Tek depo: özel Git (kod, kural sürümü, şema, testler, `KARARLAR.md`, çalışan sürüm kimliği) | **Lokman hesap**, düzen Claude | repo |
**Geçiş ölçütü:** aynı test talebi tekrarlanabilir sonuç veriyor; mükerrer iş ve yanlış sürüm teslimi testte engelleniyor; mesaj→PDF süresi ve iş başına token günlük raporda.

## Aşama 1 — İlk plan ailesi: 16 tek kat planı tek çıkarıcıyla (2–4. hafta)
Ham madde elimizde: `TEK_KAT_PREFABRIK_PLANLARI.dxf` içinde etiketli **16 plan** (P6001, P6501, P6701, P7001, P7401, P7601, P8201, P8501, P9201, P9401, P9501, P9901, P1051, P1081, P1121, P3701), temiz katmanlar (DUVAR, Kapı, Pencere, Veranda, icolcu). Katalogdaki 19 prefabrik tek kat modelin 3'ü (P1142, P1202 …) bu dosyada yok → ayrıca istenecek.
| İş | Kim | Çıktı |
|---|---|---|
| 1.1 Pilot 4 plan: **P6001** (elle kodlanmış şablonla birebir karşılaştırma = altın test), **P7001**, **P8501**, **P9201 (3+1)** — DXF → aks tanıma (k×125,5 / k×62,75; özel uçlar öznitelik) → İş Emri JSON → Motor → kaynakla karşılaştırma | Claude | çıkarıcı + 4 doğrulanmış şablon |
| 1.2 Kalan 12 plana yayma; uyuşmazlık raporu (çıkarıcı hatası / birim / bağlantı / istisna ayrımı) | Claude, Ubeydullah kontrol | 16 şablon + rapor |
| 1.3 Ön onay pafta formatı: akssız plan + görünüşler + BİNA ÖZELLİKLERİ tablosu + ÖZEL İSTEKLER + künye (AutoCAD örneğindeki gibi) | Claude, **Lokman örnek pafta** | Motor v1.2 |
| 1.4 Kural tablosu (ERROR/WARNING/INFO; asgari ölçüler, pano/köşe/H, makas yönü köşe payı) | Ubeydullah + Claude | `kurallar.csv` |
**Geçiş ölçütü:** 16 planın her biri çıkarılan İş Emri'nden yeniden üretilip tam kural setinden geçiyor; bayi "P8501 aynalı, pencere 120x180" deyince PDF geliyor; pafta formatı senin örneğinle uyuşuyor.

## Aşama 2 — Parametrik aile + yönlendirmeli diyalog + hafıza (2.–3. ay)
| İş | Çıktı |
|---|---|
| 2.1 Uyarlama merdiveni: yeniden boyutlandırma (±1 modül), aynalama, oda ekle/çıkar; "şu kısmı değiştir, kalanı koru" (oda kilitleme + fark) | "80 m² 2+1 verandalı" → 3 uyarlanmış aday → PDF |
| 2.2 Flow formu (4–6 slot), KPI paneli, utility şablonu (pencere dışı teslim) | diyalog v2 |
| 2.3 Hafıza DB (MySQL): onaylı bilgi / bayi-müşteri / proje-revizyon / karar-gerekçe / iyileştirme kayıtları; kaynaklı getirme (belge adı, sürüm, kapsam, onay) | veri modeli + panel |
| 2.4 `mode: kayitli` — 2–3 pilot bayi; Patron bildirimleri; KVKK: maskeleme + saklama süresi + hukuk görüşü | bayi pilotu |
**Geçiş ölçütü:** pilot bayiler 2 dakikada aday+PDF alıyor; eski/yeni kural, farklı proje ve bayi bilgileri karışmıyor; fiyat/model asla modelden çıkmıyor.

## Aşama 3 — Serbest yerleşim + BOM/fiyat/teklif (3.–6. ay)
CP-SAT yerleşim + puanlama (çeşitlilik, en-boy, panel sayısı) → Motor → mühendis kapısı; İş Emri'nden BOM (var) → tarihli malzeme fiyatı → işçilik kuralı → bayi koşulu → teklif sürümü. Araştırma hattı canlı hattan ayrı.
**Geçiş ölçütü:** üretilen adayların mühendis tarafından düzeltmesiz onay oranı ölçülüyor ve hedefin üstünde; teklif, yükleme listesi formatıyla uyumlu.

## Senin bu hafta vereceğin 4 karar
1. VPS: Hetzner (€5,49–8,49) mı, Türkiye'de sunucu mu (KVKK tercihi)?
2. Git deposu: senin GitHub hesabında özel repo (Claude ve Astra'ya erişim).
3. Pilot planlar: önerim P6001, P7001, P8501, P9201 — satış sıklığına göre değiştir.
4. Ön onay pafta örneği (AutoCAD'deki 69 m² teklif paftası) — DWG/PDF olarak klasöre.

## Bugün başlanan ilk iş
Aşama 0.1–0.2 (ölçüm + test seti) ve paralelde Aşama 1.1'in ilk adımı: P6001'i master DXF'ten çıkarıp elle kodlanmış şablonla karşılaştırmak (çıkarıcının doğruluğunun ilk kanıtı).
