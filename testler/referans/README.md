# Referans testleri · 28 Eylül 2026

v1.1.1 çekirdeği (`ec4e9a3`) temiz ortamda üç ayrı koşuda aynı sonucu verdi. Bu klasör o sonucu dondurur; bundan sonra yazılan her parça `dogrula.py`'yi geçmek zorundadır.

## Nasıl doğrulanır

```
python3 testler/referans/dogrula.py            # ~4,5 dk: kos.py --planlar + karşılaştırma
python3 testler/referans/dogrula.py --hizli    # ~45 sn: 16 katalog planı hariç
```

Betik depo ağacını geçici bir klasöre kopyalar ve `denetim/kos.py`'yi orada koşar; depoya yazmaz. Ağ, LLM, WhatsApp ya da canlı sunucu kullanmaz. Çıkış kodu 0, referansla aynı demektir.

Ortam (28.09): Python 3.11.15, ezdxf 1.4.4, pymupdf 1.26.0, shapely 2.1.2, pydantic 2.13.5, numpy 2.4.6.

## Dondurulan sonuç

| Adım | Sonuç |
|---|---|
| Beyin kural katmanı (harness) | 22/22 beklenen eylemle uyumlu. LLM çıkarımı kayıtlı dosyalardan gelir, gerçek API çağrılmaz. |
| Motor altın testi 6×8 | 41 pano, dış ölçü 773 × 1014 cm, ayak izi farkı 0 cm² |
| Motor altın testi Yan Verandalı 6×8,5 | 52 pano, dış ölçü 773 × 1076,75 cm, BOM 26 kod referans sayımla birebir |
| Motor P6001 katalog testi | 36 pano, dış ölçü 773 × 763 cm. Altın beklenti yok; kural doğrulaması. |
| Çıkarıcı P6001 altın testi | Izgara eşit, mahal 5/5, açıklık 7/9. İki fark menteşe yorumu; insan kararı bekliyor. |
| Çıkarıcı, 16 katalog planı | 15/16 Motor doğrulamasından geçti. P9901 desteklenmiyor (artı biçimli taban). P1051'de kapılar düşüyor. |
| Sır taraması | 4 bulgu; 4'ü de beklenen sahte test sabiti |
| DXF içerik parmak izi | 18 çıktı, iki bağımsız koşuda birebir aynı (`dxf_parmak_izleri.txt`) |

Dosyalar:
- `denetim_kosum_2026-09-28.json`: `kos.py --planlar` sonucu.
- `dxf_parmak_izleri.txt`: 18 DXF'in içerik parmak izi.
- `parmak_izi.py`: parmak izi aracı.
- `dogrula.py`: referansa karşı doğrulama.
- `paket_karsilastir.py`: canlıya giden paketleri depo koduyla karşılaştırır.

## 22 Eylül koşusuyla karşılaştırma

Girdi özetleri (20 dosya), adım sonuçları, BOM sayımları ve 16 planın plan plan sonucu 22 Eylüldeki koşuyla aynı.

DXF ve PDF dosyalarının özetleri ise her koşuda değişiyor. Motor her çizime üretim zamanını ve rastgele kimlik yazıyor: `$TDCREATE`, `$FINGERPRINTGUID` ve PORTMAN_INFO katmanındaki "Üretim: … UTC" yazısı. Bu 22 Eylülde de biliniyordu (karar K24). Bu yüzden referans, dosya özeti değil içerik parmak izidir. Parmak izi zaman ve kimlik alanlarını dışarıda bırakır; geri kalan içerik iki koşuda birebir aynı çıktı. PDF, DXF'ten basıldığı için yalnız sayfa sayısı ve ölçüsüyle izlenir.

## Canlı paketlerle karşılaştırma

`python3 testler/referans/paket_karsilastir.py <hosting_guncelleme_2011.zip>` ile yapıldı. Paketler depoda değil, Lokman'ın masaüstü klasöründe (`08_VPS/hosting_paket/`). Bunlar canlıya giden paketlerin kopyalarıdır; sunucudaki dosyalar 28.09'da okunmadı.

| Paket | sha256 | Sonuç |
|---|---|---|
| `hosting_guncelleme_2011.zip` | `bf22a83a…` | 37 dosyanın hepsi depoyla aynı |
| `kanal/package/current.zip` (VPS, `kanal-v1.1.1-20260922-2011`) | `bd1ca27c…` | 36 aynı. 6 farklı ve 5 yalnız pakette olan dosyanın hepsi Beyin test çıktısı. Kod farkı yok. |

## Açık not

`beyin/testler/mesajlar.json` dosyasının 1. vakasında gerçek olabilecek bir müşteri adı ve sevk yeri var. Gerçekse takma adla değiştirilmeli. v1.1.1 ağacı dondurulduğu için İE-01'de dokunulmadı; iş İE-02'ye bırakıldı.
