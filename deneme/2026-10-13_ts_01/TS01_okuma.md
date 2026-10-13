# TS-01 · Diamond 45 m² (Ramazan Batmaz) · pafta okuması (AIPrefabrik test seti, kör test adım 1–3, pafta kipi)

13 Ekim 2026. Lokman 14:42: "İE-13'ten önce test setinde kör test".
- **Kaynak:** Mac `~/Desktop/AIPrefabrik/Diamond 45/`.
- **Montaj paftası** `kaynak/TS01_MONTAJ_PAFTASI.pdf`: SHA `63197621…6b7`, mühürle aynı; 12 sayfa; çizen Ubeydullah Özer, kontrol Lokman Sayım.
- **Gerçek liste açılmadı:** `DIAMOND 45M2 YUKLEME LISTESI.pdf`, SHA `dcfd289b…0b4`, mühürle aynı (`deneme/2026-10-13_aiprefabrik/test_seti/MUHUR.md`).

## Okuma (`pafta_oku.py`; vektör + göz)

### Plan

- 750 × 690. Sol bölümde yatak odası 150 cm öne çıkıyor (cumba, 300 × 150). Brüt 44,94 m², dış çevre 28,88 m.
- Arkada dış kapının önünde sundurma 135,5 × 130, iki kolon (D, 10'luk kutu profil 3 mm, 250).

### Panolar: 37 (dış 26 / 10 cm, iç 11 / 6 cm)

- Boylar yazıya oturtuldu: 125,5, 122,5, 120,5, 112,5, 85,75, 82,25, 80,75, 77,25, 62,75, 23,75.
- 150/190'lar mavi özel panoda: D01 (sağ ön, 251) ve D02 (cumba önü, 290).

### Açıklıklar

- **Pencereler:** 150/190 × 2, 120/120, 60/40 (banyo). Pencereler alıcıya ait.
- **Kapılar** (kanat geometrisi):
  - dış kapı arka duvarda, SOL;
  - iç kapılar 3: banyo, salon, yatak; hepsi SOL.

### Köşeler ve H

- **Köşe:** 10'luk 5, L'nin iç köşesi B 1, iç 6'lık 1.
- **H** (makas ekseniyle kulaklı):
  - dış: kulaklı 8 + dübelli 8; 3'lü kulaklı 3 + dübelli 1. H planındaki renkli dairelerle **birebir**.
  - iç: pano eki 5 (paftada 3), T 2.

### Çatı

| Parça | Ölçüler | Makas | Not |
|---|---|---|---|
| Ana beşik | 540 + 2 × 30, 18,2°, eğik 315,8, mahya 810 | MK01–MK08 (8) | |
| Cumba | çapraz beşik, 300 + 2 × 30, eğik 189,48 | MK11, MK12, iç uçta MK13 | |
| Sundurma | çapraz beşik, 135,5 + 2 × 30 | MK09, MK10 | altı açık |

- Kaplama: OSB + nem bariyeri + metal kiremit (bordo, 105 kapatır): 320 × 16, 195 × 6, 108 × 4. OSB 27.
- **İniş daireleri 7:** ana çatıda 3, cumbada 2, sundurmada 2. **Orta iniş yok.**

### Tavan ve alçıpan

- **Tavan:** ters; omega 31 parça, 77,17 m.
- **Açıklama:** iç cephe alçıpan, metal yağmur inişi (antrasit), dış cephede mastik, çatı müdahale kapağı.

### Elektrik (göz; çift anahtar ve çift priz 400 dpi'da)

- duy 5, glop 2;
- anahtar tekli 1, çift 3;
- priz tekli 10, çift 3;
- uydu 1, sigorta kutusu 1, zil yok.

## Üreteç sürüm 7.3 (gerçek liste açılmadan; model anlamı ve ilk tahmin)

- "Metal kiremit" kaplaması 105 cm kapatır (kaplama paftası); kaplama vidası 5,5 × 60.
- OSB ve nem bariyeri ilk tahmin (çatı alanı × 1,10 ÷ 2,977; alan 10 m²'ye yukarı). E2 / E3 listelerinde bu kalemler vardı.
- PK-01…08 çıktıları 7.2 ile aynı; hiçbirinde metal kiremit + OSB yok.

## Liste (adım 3)

`sonuc/TS01_liste.json` / `.xlsx`, 125 satır.

    python3 -I deneme/2026-10-13_ts_01/pafta_oku.py
    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py --yapi deneme/2026-10-13_ts_01/yapi_pafta.json deneme/2026-10-13_ts_01/sonuc \
        --pafta deneme/2026-10-13_ts_01/pafta_katmani.json
