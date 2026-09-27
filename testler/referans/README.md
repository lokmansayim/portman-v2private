# Referans testleri · 28 Eylül 2026

v1.1.1 çekirdeği (`ec4e9a3`) temiz ortamda üç ayrı koşuda aynı sonucu verdi. Bu klasör o sonucu dondurur; bundan sonra yazılan her parça `dogrula.py`'yi geçmek zorundadır.

## Nasıl doğrulanır

```
python3 testler/referans/dogrula.py            # ~4,5 dk: kos.py --planlar + karşılaştırma
python3 testler/referans/dogrula.py --hizli    # ~45 sn: 16 katalog planı hariç
```

Betik yalnız v1.1.1 ağacını geçici bir klasöre kopyalar (`deneme/`, `testler/`, `KARARLAR/` hariç) ve `denetim/kos.py`'yi orada koşar; depoya yazmaz. Ağ, LLM, WhatsApp ya da canlı sunucu kullanmaz. Çıkış kodu 0, referansla aynı demektir.

Kurallar:
- Referans girdiler değişmemeli: İş Emri şablonları, `ref_*` çizimleri, Beyin test mesajları ve kayıtlı LLM çıkarımları. Kod dosyalarının özeti yalnız bilgi olarak raporlanır; kod değişikliği tek başına fark sayılmaz.
- Beyin harness'inde tüm vakalar uyumlu olmalı. Vaka sayısı 22'den az olamaz, yeni vaka eklenebilir.
- Motor sayıları, BOM sayımları, çıkarıcı sonuçları ve içerik parmak izleri aynı kalmalı. Bilerek yapılan bir değişiklik bunları değiştirirse referans gerekçesiyle ve yeni tarihle yeniden dondurulur; eskisi silinmez.

**Dikkat:** `denetim/kos.py`'yi bu dalın kökünde doğrudan koşmayın. Sır taraması `deneme/` altındaki IFC dosyasındaki ondalık koordinatları telefon numarası sanıyor ve adım "failed" dönüyor (9 yanlış bulgu). `kos.py`'yi `main`'de ya da `dogrula.py` üzerinden koşun. Kalıbın düzeltilmesi İE-02'de.

Ortam (28.09, pip ile kurulan sürümler): Python 3.11.15, ezdxf 1.4.4, pymupdf 1.26.0, shapely 2.1.2, pydantic 2.13.5, numpy 2.4.6. `kos.py`'nin kaydı pymupdf için sürüm yerine "(64-bit)." yazıyor.

## Dondurulan sonuç

| Adım | Sonuç |
|---|---|
| Beyin kural katmanı (harness) | 22/22 beklenen eylemle uyumlu. LLM çıkarımı kayıtlı dosyalardan gelir, gerçek API çağrılmaz. |
| Motor altın testi 6×8 | 41 pano, dış ölçü 773 × 1014 cm, ayak izi farkı 0 cm² |
| Motor altın testi Yan Verandalı 6×8,5 | 52 pano, dış ölçü 773 × 1076,75 cm, BOM 26 kod referans sayımla birebir |
| Motor P6001 katalog testi | 36 pano, dış ölçü 773 × 763 cm. Altın beklenti yok; kural doğrulaması. |
| Çıkarıcı P6001 altın testi | Izgara eşit, mahal 5/5, açıklık 7/9. İki fark menteşe yorumu; insan kararı bekliyor. |
| Çıkarıcı, 16 katalog planı | 15/16 Motor doğrulamasından geçti. P9901 desteklenmiyor (artı biçimli taban). P1051'de kapılar düşüyor. |
| Sır taraması | 4 bulgu, hepsi beklenen: 3'ü PHP testlerindeki sahte sabit, 1'i `kos.py`'nin kendi arama kalıbı |
| DXF içerik parmak izi | 18 çıktı, üç ayrı temiz koşuda birebir aynı (`dxf_parmak_izleri.txt`) |
| PDF sayfa sayısı ve ölçüsü | 18 çıktı, aynı (`pdf_parmak_izleri.txt`) |

Dosyalar:
- `denetim_kosum_2026-09-28.json`: `kos.py --planlar` sonucu.
- `dxf_parmak_izleri.txt`: 18 DXF'in içerik parmak izi.
- `pdf_parmak_izleri.txt`: 18 PDF'in sayfa sayısı ve ölçüsü.
- `parmak_izi.py`: parmak izi aracı.
- `dogrula.py`: referansa karşı doğrulama.
- `paket_karsilastir.py`: canlıya giden paketleri depo koduyla karşılaştırır.

## 22 Eylül koşusuyla karşılaştırma

Girdi özetleri (20 dosya), adım sonuçları, BOM sayımları ve 16 planın plan plan sonucu 22 Eylüldeki koşuyla aynı.

DXF ve PDF dosyalarının özetleri ise her koşuda değişiyor. DXF'te değişenler: oluşturma ve güncelleme zamanı (`$TDCREATE`, `$TDUPDATE`), rastgele kimlikler (`$FINGERPRINTGUID`, `$VERSIONGUID`), ezdxf'in üst veri zamanları, OBJECTS bölümündeki nesne sırası (Python karma tohumuna bağlı; `PYTHONHASHSEED=0` ile sabitlenir) ve Motor'un PORTMAN_INFO katmanına yazdığı "Üretim: … UTC" metni. Bu yüzden referans, dosya özeti değil içerik parmak izidir. Parmak izi model alanı, kâğıt alanları ve blok tanımlarındaki her varlığın tüm özniteliklerini, köşe noktalarını ve eğimlerini kapsar; yalnız tutamaç, sahip ve metinlerdeki tarih-saat dışarıda kalır. Bir blok içi çizgiyi 0,1 cm kaydırmak, bir yazıyı döndürmek ya da bir ölçü noktasını oynatmak parmak izini değiştiriyor (28.09 deneme). PDF, DXF'ten basıldığı için yalnız sayfa sayısı ve ölçüsüyle izlenir.

## Canlı paketlerle karşılaştırma

`python3 testler/referans/paket_karsilastir.py <hosting_guncelleme_2011.zip>` ile yapıldı. Paketler depoda değil, Lokman'ın masaüstü klasöründe (`08_VPS/hosting_paket/`). Bunlar canlıya giden paketlerin kopyalarıdır; sunucudaki dosyalar 28.09'da okunmadı.

| Paket | sha256 | Sonuç |
|---|---|---|
| `hosting_guncelleme_2011.zip` | `bf22a83a…` | Karşılaştırılan 37 dosyanın hepsi depoyla aynı. Paketin kendi 3 dosyası (`current.zip`, `current.sha256`, `SURUM.txt`) ayrıca incelendi. |
| `kanal/package/current.zip` (VPS, `kanal-v1.1.1-20260922-2011`) | `bd1ca27c…` | 36 aynı. 6 farklı ve 5 yalnız pakette olan dosyanın hepsi Beyin test çıktısı. Kod farkı yok. |

## Açık not

`beyin/testler/mesajlar.json` dosyasının 1. vakasında gerçek olabilecek bir müşteri adı ve sevk yeri var. Gerçekse takma adla değiştirilmeli. v1.1.1 ağacı dondurulduğu için İE-01'de dokunulmadı; iş İE-02'ye bırakıldı.
