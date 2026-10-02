# 2 Ekim 2026 · çelik deneme çizicisi (Ç8201)

Deneme kodu; canlıda değil, Motor'un yerine geçmez. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) ilk denemesi.

Amaç: tek kat çelik bir modeli, pano ızgarası olmadan, bir tanım dosyasından ve duvar tiplerinden kurmak; alanları ve Boardex metrajını hesaplamak; planı çizmek.

| Dosya | İçerik |
|---|---|
| `duvar_tipleri.json` | Baz paket duvar tipleri (katman listesi). Duvar kalınlığı katmanların toplamıdır |
| `C8201.json` | Ç8201'in tanımı: dış kutu, iç duvar aksları, mahaller, açıklıklar (arşivdeki çizimden) |
| `ciz.py` | Hesap ve plan çizimi |
| `cikti/` | Plan görselleri ve raporlar |

## Çalıştırma

```
python ciz.py C8201.json                    # baz paketin katmanlarıyla (10,5 cm duvar)
python ciz.py C8201.json --cizim-kalinligi  # arşiv çiziminin kalınlıklarıyla (12 / 11 cm); etiketlerle karşılaştırır
```

## Sonuç (2 Ekim 2026)

- `--cizim-kalinligi`: beş mahalin alanı çizimdeki etiketlerle aynı (11,8 · 11,8 · 4,3 · 6,7 · 23,3). Çıkış kodu 0.
- Katmanlardan: 11,9 · 11,9 · 4,3 · 6,7 · 23,5; kapalı net 58,4 m². Dış ölçü 850 × 750 (veranda dahil 1094 × 750).
- Dış Boardex: 32,0 m × 2,70 m − 19,7 m² = 66,7 m²; fire hariç 24 levha. Dış kapı yüksekliği 210 varsayıldı. Yükleme listesiyle karşılaştırılmadı.

## Sınırlar

- Yalnız dikdörtgen kapalı kutu ve eksenlere paralel iç duvarlar.
- Görünüş, çatı, 3B ve yükleme listesinin öteki kalemleri yok.
- Ölçü kuralı (dış yüz ve iç aks sabit) öneridir; Lokman'ın teyidini bekliyor.
- Kaynak çizim (DWG) depoda değil; tanım dosyası elle, çizimden okunarak yazıldı.
