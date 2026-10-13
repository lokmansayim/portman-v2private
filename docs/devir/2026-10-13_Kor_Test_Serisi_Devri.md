# Devir · 13 Ekim 2026 öğleden sonra · prefabrik kör test serisi

**Dal:** `ie-11-pr2-kor-test` (yalnız yerel; itilmedi). Lokman 10:24: GitHub'a itme, PR ve birleştirme yok; talimat öteki sohbetten gelecek.

## Nerede kalındı

- Kör test serisi PK-01…PK-08 bitti. Özet ve 10 açık soru: `deneme/2026-10-13_kor_test_seri/SERI_OZETI.md`.
- Liste üreteci sürüm 7.1: `deneme/2026-10-13_kor_test_seri/yukleme_listesi.py`. Başlığında H1…O19 kuralları ve sürüm geçmişi var.
- Proje klasörleri `deneme/2026-10-13_pk_0N/`. Her birinde:
  - `kaynak/` (paftalar);
  - `pafta_oku.py` (PK-03…08, vektör okuyucu);
  - `yapi_pafta.json` ve `pafta_katmani.json`;
  - `sonuc/` (kör listemiz ve kıyas);
  - `gercek/` (mühürlü liste, açılış sonrası).
- `docs/is_emirleri/IE-13.md`: Pano Motoru genişletme planı, taslak, Lokman'ın onayını bekliyor.

## Kurallar (bu iş için)

- Gerçek liste, kendi listemiz commit'lenmeden açılmaz. Açılışta Mac'te `shasum -a 256` ile mühürle karşılaştırılır; saatler `MUHUR.md`'ye yazılır.
- Kör listeler (`sonuc/PK0N_liste.json`) açılıştan sonra değiştirilmez. Sonraki sürümlerin geri testi scratchpad'e yazılır.
- Açılıştan sonra okuyucuya ya da pafta katmanına giren her düzeltme dosyada "kıyastan sonra" notuyla durur.
- Aynı klasördeki teklif ya da liste olabilecek dosyalar açılmaz; özetleri `MUHUR.md`'ye eklenir.

## Sıradaki

1. Lokman'ın İE-13 onayı → madde 1–3 (PK-02 tam eşleşme).
2. Soruların cevaplarıyla kural adaylarını `kurallar/liste/` altında ayrı katmana taşımak (D-02, yeni kural seti sürümü).
3. KT-03 Örnek Şablon'un prefabriğe uyarlanması (öteki sohbetin talimatından sonra).
4. `wt-ie10` ve `wt-ie11` çalışma ağaçlarının kaldırılması (Lokman'ın onayıyla).
