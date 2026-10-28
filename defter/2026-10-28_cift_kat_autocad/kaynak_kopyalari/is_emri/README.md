# Çift kat prefabrik · ilk taslak (İE-22, 28 Ekim 2026)

Lokman'ın 28 Ekim'de gönderdiği iki kat planı (zemin: ODA 9,38 · SALON 17,00 · MUTFAK 7,13 · BALKON 5,93; 1. kat: ODA 7,42 · ODA 15,66 ·
ODA 8,80 · BALKON 5,93; gövde 763 × 706, merdiven kutusu 220 × 260 iç, arkaya 125 çıkma, balkon 337 × 165) bugünkü **tek kat** pano
Motor'uyla, kat kat çizildi. Motor çift katı henüz tanımıyor (`kat_sayisi ≠ 1` hata); bu klasör İE-22'nin başlangıç kanıtı ve Lokman'la
"beraber çizme" turunun ilk adımıdır. Kurallar: `docs/sartname/cift_kat_prefabrik_kurallari.md`; iş emri: `docs/is_emirleri/IE-22.md`.

| Dosya | Ne |
|---|---|
| `zemin_kat.json` | Zemin kat İş Emri (tek kat biçiminde; `varsayimlar` ve `eksikler` içinde) |
| `birinci_kat.json` | 1. kat İş Emri (aynı gövde ve ızgara) |
| `sonuc/zemin_kat/` | Motor çıktısı: `Portman_IE22-CK01-ZEMIN_r01.dxf` (AutoCAD'de açılır, cm), `.pdf` (ön onay taslağı), `preview.png`, `validation.json` (geçti), `bom.json` |
| `sonuc/birinci_kat/` | Aynısı 1. kat için (`…KAT1_r01.dxf/.pdf`) |
| `sonuc/*_bayi/` | Bayi paftası (`motor.sunum`, perspektifsiz): `CK01_bayi.pdf`, `CK01_plan_bayi.png` |

Bu taslakta olmayanlar (Motor sınırı, İE-22 PR-1): merdiven çıkması (arkaya 125,5) ve merdivenin kendisi; balkonun 30 cm taşması; iki katın tek
dosyada çizilmesi ve iki katlı ön görünüş; ara kat. Giriş kapısı planda yok, eklenmedi. Beşik çatıda `makas_ekseni: y` yazılı olsa da ön görünüş
ve çatı profili eski yolla x'e (763) göre çizildi; bu da İE-22'de bulgu.

Yeniden koşmak için (depo kökünde, sanal ortam açıkken):

```
python -c "import json,pathlib; from motor import dxf_out; ie=json.load(open('deneme/2026-10-28_cift_kat/zemin_kat.json')); print(dxf_out.uret(ie, pathlib.Path('deneme/2026-10-28_cift_kat/sonuc/zemin_kat'), pdf_hatada=True)['validation_passed'])"
python -m motor.sunum deneme/2026-10-28_cift_kat/zemin_kat.json deneme/2026-10-28_cift_kat/sonuc/zemin_kat_bayi --perspektifsiz
```

Kişi ve bayi adı yok ("Bayi CK-01" yer tutucudur); telefon yok.
