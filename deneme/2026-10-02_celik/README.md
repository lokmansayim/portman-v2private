# 2 Ekim 2026 · çelik deneme çizicisi (Ç8201)

Deneme kodu; canlıda değil, Motor'un yerine geçmez. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) ilk denemesi.

Amaç: tek kat çelik bir modeli, pano ızgarası olmadan, bir tanım dosyasından ve duvar tiplerinden kurmak; alanları ve Boardex metrajını hesaplamak; planı çizmek.

| Dosya | İçerik |
|---|---|
| `duvar_tipleri.json` | Baz paket duvar tipleri (katman listesi). Duvar kalınlığı katmanların toplamıdır |
| `C8201.json` | Ç8201'in tanımı: dış kutu, iç duvar aksları, mahaller, açıklıklar (arşivdeki çizimden) |
| `ciz.py` | Hesap ve plan çizimi |
| `gorunus.py` | Çatı hesabı, çatı planı, dört görünüş ve tek pafta |
| `cikti/` | Koşu çıktıları (depoya girmez) |
| `sonuc/` | 2 Ekim koşusunun kanıtları: plan, pafta, raporlar |

## Çalıştırma

```
python ciz.py C8201.json                    # baz paketin katmanlarıyla (10,5 cm duvar)
python ciz.py C8201.json --cizim-kalinligi  # arşiv çiziminin kalınlıklarıyla (12 / 11 cm); etiketlerle karşılaştırır
python gorunus.py C8201.json                # çatı + görünüşler + pafta
```

## Sonuç (2 Ekim 2026)

- `--cizim-kalinligi`: beş mahalin alanı çizimdeki etiketlerle aynı (11,8 · 11,8 · 4,3 · 6,7 · 23,3). Çıkış kodu 0.
- Katmanlardan: 11,9 · 11,9 · 4,3 · 6,7 · 23,5; kapalı net 58,4 m². Dış ölçü 850 × 750 (veranda dahil 1094 × 750).
- Dış Boardex: 32,0 m × 2,70 m − 19,6 m² = 66,8 m²; fire hariç 24 levha. Yükleme listesiyle karşılaştırılmadı.
- Çatı (kırma, %33, saçak 30): plan 1154 × 810, mahya 344 cm, saçak ucu 280, mahya kotu 414 cm, yüzey 98,4 m². 21:50 düzeltmesi: topuk saçak ucunda (SKP ölçümü); önceki mahya kotu 404'tü.
- Açıklık üst kotu 200 cm (lento 70).

## Sınırlar

- Yalnız dikdörtgen kapalı kutu ve eksenlere paralel iç duvarlar.
- Yalnız kırma çatı; 3B ve yükleme listesinin öteki kalemleri yok.
- Varsayım: veranda kolonu 20 cm. Topuk 10 cm modellerden ölçüldü (`docs/sartname/skp_olcumleri.md`). Subasman, merdiven ve cephe kaplaması çizilmiyor.
- Açık çelişki: lento 70 cm kuralı üst kotu 200 yapıyor; yükleme listelerinde ve üç SKP modelinde kapı başlıkları 214 (iç) ve 210 (dış). Çizimde kapılar 200; Lokman'ın cevabı bekleniyor.
- Kaynak çizim (DWG) depoda değil; tanım dosyası elle, çizimden okunarak yazıldı.
