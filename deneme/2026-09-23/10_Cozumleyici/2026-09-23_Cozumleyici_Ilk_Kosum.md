# Bayi planı çözümleyici: ilk koşum (23 Eylül 2026)

**Amaç:** Bayinin gönderdiği planı okuyup kurallı DXF, PDF ve BOM üretmek. Hat şöyle: plan → Ölçülü Kroki → İş Emri → Motor → DXF / PDF / BOM. Yarı otomatik çalışır; en sonda insan onayı var.

**Test girdisi:** Tatar Grup'un 16.09 tarihli 80 m² planı (`.80m2-Model.pdf`, AutoCAD 2026 çıktısı). Bu plan satışa dönmüştü (12 Ekim sevk).

**Durum:** Deneme sürümü. Masaüstündeki depoya ve canlı sisteme dokunulmadı. Motor değişikliği ayrı bir yama dosyasında duruyor.

## 1. Sonuç özeti

| Ölçüt | Sonuç |
|---|---|
| PDF'ten okuma | Katmanlar: 0 (duvar), Pencere, Kapı, YAZI, tefriş. LLM kullanılmadı. |
| Ölçek | İki bağımsız kanıt birbirini tutuyor: pano modülü 1,63924 cm/pt, ölçü yazıları 1,64014 cm/pt. Fark %0,05. |
| Dış ölçü | 800 × 969 cm. Bayinin yazdığı ölçü birebir alındı. |
| Motor doğrulaması | **Geçti.** Hata 0, uyarı 0. Ayak izi farkı 0 cm². |
| Pencere / kapı | 8 pencerenin 8'i, 8 kapının 8'i yerleşti. Hiçbiri düşmedi. |
| Dış duvar metrajı | Bayi 34,68 m, Motor 34,68 m (fark %0,0). Tam dış pano: 23 = 23. |
| İç duvar metrajı | Bayi 31,51 m, Motor 31,35 m (fark −%0,5). Adet 28 = 28. |
| Toplam pano alanı (2,5 m) | Bayi 165,5 m², Motor 165,1 m² (fark −%0,2). |

Bayinin çizimi zaten pano birimli. Sol ve sağ duvarlarda 7 ve 6 tam panonun yanında **80,5'lik özel pano** var. Arka duvarda 89,7 özel pano ve 3 yarım pano var. Motor aynı dış ölçüyü ve aynı 80,5 özel panoyu kendisi buldu.

### Mahal net alanları (m²)
| Mahal | Bayinin etiketi | Bayinin çizimi | Motor | Fark (çizime göre) |
|---|---|---|---|---|
| Salon | 15,35 | 15,35 | 15,35 | %0,0 |
| Yatak odası 1 | 10,0 | 10,06 | 10,05 | −%0,1 |
| Yatak odası 2 | 9,6 | 9,65 | 9,61 | −%0,4 |
| Yatak odası 3 | 8,26 | 8,28 | 8,20 | −%1,0 |
| Mutfak | 8,1 | 8,12 | 8,17 | +%0,6 |
| Banyo | 3,6 | 3,61 | 3,61 | %0,0 |
| Hol | **7,4** | 8,95 | 9,09 | +%1,6 |
| WC | **4,0** | 2,50 | 2,50 | %0,0 |
| Veranda | 8,3 | — | **5,55** | Taşma yok (aşağıda) |

- **Hol ve WC:** Bayinin kendi etiketleri kendi çizimiyle uyuşmuyor. İkisinin toplamı tutuyor (11,4 ve 11,45), ama dağılım farklı. Sistem bunu bayiye bildirmeli.
- **Veranda:** Bayinin verandası bina kutusunun 60 cm dışına taşıyor (449 × 60 ≈ 2,7 m²). Motor v1 taşan kısmı çizmiyor. Bu, P9401 ve P7401'deki bulguyla aynı.

## 2. Aynı plan eski yoldan geçseydi (K16-a, modüle uyarlama)
Katalog çıkarıcısında (`motor/cikarici.py`) aynı plan şu sonucu verdi (`tatar80_cikarici_uyarlama/cikarim_raporu.md`):
- Plan 90° döndürüldü, uzun kenar x'e geçti.
- Duvarlar aksa taşındı: yaklaşık 13 ve 31 cm.
- 3 açıklık düştü: WC penceresi, Yatak 1 kapısı, dış kapı.

Bayi temele veya ruhsata göre ölçü veriyor (Varna'da beton önce atıldı). Bu yüzden modüle uyarlama bayi planları için uygun değil.

**K16 önerisi:** Bayi planlarında (b) seçilmeli, yani serbest aks + özel pano. Katalog şablonlarında (a) sürebilir.

## 3. Motor'a yapılan değişiklik (deneme)
Dosya: `kod/motor_serbest_aks.patch`
- **geometry.py:** İş Emri'ne yeni bir alan eklendi: `yapi.aks_cm = {"x": [...], "y": [...]}`. Bu alanla akslar cm cinsinden listeden okunur, pano ayrıştırmayı Motor yapar: koşu başından 125,5, kalan özel pano sonda. Alan yoksa Motor v1.1 ile **birebir** aynı çalışır. Doğrulama kuralları: x[0] = 10, y[0] = 5, iki aks arası en az 20 cm.
- **cikarici.py:** Çıkarıcı başlarken önceki işten kalan serbest akslar sıfırlanır.
- **Regresyon:** `python3 denetim/kos.py` **8/8 geçti.** Altın 6×8 geçti. Astra'nın Yan Verandalı BOM'u 26 kalem birebir çıktı (`bom_fark` boş). P6001 çıkarıcı altın testi de geçti.
- **Bilinen görsel kusur:** Paftada "2,5 x 3 PANO" ve "3,52 x 1 aks modülü" etiketleri hâlâ düzenli modülü varsayıyor. Serbest aksta bu etiketler kaldırılmalı.

## 4. Astra'nın BOM'u ile kontrol
Astra 7 Eylül'de `yeni-2plus1-yan-verandali.dwg` üzerindeki blokları saydı (`ref_yan/BOM_SAYIM_KAYDI.json`). Bu sayım Motor'un altın BOM testi. Yamalı Motor aynı İş Emri'nden aynı 26 kalemi aynı adetlerle üretti. Blok sayımı yaklaşımı, Astra ile doğrulanan ve Lokman'ın elle saydığı yaklaşımın aynısı.

21 Eylül tarihli yükleme listesi analizi hâlâ geçerli. Blok olarak sayılabilen kalemler (pano, doğrama, köşe, üçlü H) Motor'dan çıkıyor. Geri kalan kalemler kural ister: ek sayımı (H), metraj (alt çerçeve, omega, U) ve çatı/tavan geometrisi.

## 5. %5 kabul kapısı (Lokman, 23.09 20:17)
Önerilen uygulama. Tolerans her ölçüte aynı uygulanmaz:

| Ölçüt | Tolerans | Gerekçe |
|---|---|---|
| Dış ölçü | 0 | Temel ve ruhsat ölçüsü sözleşmedir. |
| Pencere, kapı ve oda adedi | 0 | Sayı yanlışsa sipariş yanlış olur. |
| Pano metrajı / pano alanı | ±%5 → otomatik geçer | Fiyatı taşıyan büyüklük. Bu koşum %0,2. |
| Mahal net alanı | ±%5 → otomatik geçer | Bu koşumda 7/9 geçti. Hol ve WC bayi etiketinden, veranda taşmadan kaldı. |
| Açıklık konumu | Ubeydullah belirler (öneri ±30 cm) | Fiyatı değiştirmez ama bayi farkı görür. |

Bir ölçüt eşiği aşarsa iş insana düşer. Aşmazsa ön onay taslağı hazırlanır.

## 6. Kural soruları (Ubeydullah)
1. **Özel pano nerede duruyor?** Bayi özel panoyu koşu başına ya da köşeye koyuyor (sol arka 89,7). Motor koşu sonuna koyuyor. Bir iç L köşede bu fark 2,95 cm'lik kıymık pano üretti. Aks 2,95 cm kaydırılarak çözüldü. Üretimdeki kural hangisi?
2. **Yarım pano mu, tek özel pano mu?** Bayi 62,75'lik yarım pano kullanıyor ve 60/40 vasistası yarım panoya koyuyor. Motor tek bir özel pano çıkarıyor. Yükleme listesindeki 625 + 525 sorusuyla aynı konu: "625 + 625 mi, 1205 mi?"
3. **Açıklık konumu:** Bayi pencereyi odada istediği yere koyuyor, Motor pano ortasına. Farklar: banyo vasistası 118 cm, yatak 3 penceresi 63 cm, mutfak penceresi 46 cm. Kapılarda fark 4–13 cm. Pencere yeri bayinin isteği mi olmalı, yoksa panoya mı bağlı kalmalı?
4. **Bina içindeki dış duvar (mutfak–veranda):** Bayi duvar gövdesini aksın içine, mutfak tarafına çiziyor. Motor dışına, veranda tarafına koyuyor. Sonuç: bu duvar verandaya doğru yaklaşık 7 cm kaydı, hol sol duvarı 3 cm kaydı.
5. **Kapı eni:** Bayi 80 ve 100 cm çiziyor. İş Emri 82 ve 90 kullanıyor (21.09 kararı).
6. **Veranda taşması:** Bina kutusu dışına taşan veranda Motor v1.2 iş listesine eklenmeli.

## 7. Sınırlar ve sıradaki adım
- **Vektör PDF yolu dar bir girdi için çalışıyor:** Duvarları dörtgen parça olarak çizilmiş, katmanlı CAD çıktıları. Şu girdiler bu yoldan henüz geçmiyor:
  - 27.08 tarihli Tatar PDF'i (her şey katman 0'da)
  - ArchiCAD planı (duvarlar dolgulu)
  - El çizimleri

  Bunlar "görsel / LLM" yoluna düşer.
- **El çizimi ve fotoğraf yolu (sıradaki iş):** Görsel LLM, oda dikdörtgenlerini ve ölçü yazılarını aynı Ölçülü Kroki biçimine yazar. Kod bu dikdörtgenlerden duvar parçalarını üretir, gerisi aynı hattan geçer. LLM'in çıktısı kanıt sayılmaz, girdi sayılır. Kod şu tutarlılıkları kontrol eder:
  - Parça ölçülerin toplamı dış ölçüyü tutuyor mu?
  - Etiketteki m² ile ölçülerden çıkan alan uyuşuyor mu?

  Tutmayan her yerde bayiye tek bir soru sorulur.
- **Blender:** Aynı İş Emri'nden 3B görünüm üretebilir. Doğruluk kaynağı İş Emri, Motor ve blok sayımı olarak kalır.

## 8. Dosyalar
- `kod/cozumleyici/pdf_vektor.py`: Vektör PDF'i Ölçülü Kroki'ye (kroki.json) ve normalize DXF'e çevirir.
- `kod/cozumleyici/kroki_is_emri.py`: Kroki'den serbest akslı İş Emri üretir, kayma raporu yazar, Motor'u çalıştırır.
- `kod/motor_serbest_aks.patch`: geometry.py ve cikarici.py değişikliği.
- `tatar80/`: bayi PDF'i, `kroki.json`, `is_emri.json`, `donusum_raporu.json` ve `motor/` klasörü (DXF, PDF, `bom.csv`, `bom.json`, `validation.json`, `preview.png`).
- `tatar80_cikarici_uyarlama/cikarim_raporu.md`: K16-a karşılaştırması.
- `karsilastirma.png`: Bayi planı ve Motor çıktısı yan yana.

Çalıştırma (depo kökünde, yama uygulanmış olarak):
```
python3 -m cozumleyici.pdf_vektor <bayi.pdf> --cikti cikti/<kod>
python3 -m cozumleyici.kroki_is_emri cikti/<kod>/kroki.json --kod <KOD> --cikti cikti/<kod>/serbest --motor
```
