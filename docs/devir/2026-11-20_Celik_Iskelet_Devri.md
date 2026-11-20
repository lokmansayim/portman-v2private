# Devir · 90 m² çelik projenin iskeleti (GLB) · 20 Kasım 2026

Dal: `claude/celik-iskelet-90m2`. Lokman'ın isteğiyle `main`'den ayrı tutulur; PR açılmaz, `main`'e birleşmez.
Dosyalar: `deneme/2026-11-20_celik_iskelet/`.

## Amaç

Kampanya binası için tanıtım animasyonu:
- Çelik karkas 3B yazıcıda basılıyor gibi alttan üste oluşur.
- Yazıcı görünmez.

Bu oturum yalnız iskeleti çıkardı. Animasyonu Lokman'ın Mac'indeki yerel oturum yapar; o oturumda Blender ve Higgsfield bağlantısı var.

## Elimizdekiler

- **Kaynak.** Lokman'ın 20 Kasım'da gönderdiği proje klasöründeki çelik modelin SKP'si (SketchUp 2023). Depoya girmedi.
- **İskelet:** `celik_iskelet_90m2.glb` (1,37 MB).
  - 824 parça, 4 grup: Duvar 508, Lento 32, Makas 237, Cati_paneli 47.
  - 8418 üçgen. Ölçü 9,82 × 10,13 × 4,42 m.
  - Birim metre. Taban ortası (0, 0, 0). Blender içe aktarınca Z yukarı olur.
  - Tek malzeme: `Galvaniz` (açık gri, metalik 0,9, pürüzlülük 0,35, iki yüzlü).
  - Her parçanın özel özellikleri: `katman`, `z_alt`, `z_ust` (m), `sira` (alttan üste sıra numarası).
- **Üreten komut:** `python iskelet_glb.py <çelik model>.skp celik_iskelet_90m2.glb --ozet ozet.json`. Gereken: openskp 1.3.0, numpy; Blender gerekmez.
- **Önizleme:** `onizleme.png`, `python onizleme.py celik_iskelet_90m2.glb onizleme.png` ile çizildi (matplotlib). Dört kare: kesit yüksekliği %25, %50, %75, %100; turuncu bant yeni basılan 15 cm.

## Kanıt (20 Kasım 2026)

- **Khronos glTF doğrulayıcısı:** hata 0, uyarı 0, bilgi 0; 8418 üçgen, 25.254 köşe.
- **Toplam çelik boyu:** SKP'deki 8 cm'lik gövde yüzlerinden 1392 m. Projenin Alpha Mini üretim dosyalarında (7 dosya, 53 panel, 1390 çubuk) 1416 m. Fark %1,7; iskelet eksiksiz sayılır.
- **Önizleme:** duvarlar alttan uzuyor, %75'te makaslar başlıyor, %100'de çatı paneli tamam.

## Sınırlar

- **Parça ve çubuk farkı.** Parça sayısı (824), çubuk sayısından (1390) az: birbirine değen bazı çubuklar SKP'de ortak kenar paylaşıyor ve tek parça kalıyor. Kesit düzlemiyle yapılan "yazıcı" efektinde bu fark görünmez. Çubuk çubuk belirme istenirse parçalar `sira`'ya göre açılır; birleşik parçalar birlikte belirir.
- **Eksik parçalar.** Modelde temel plak, kaplama, pencere ve kapı yok; yalnız çelik.
- **Ön kolonlar.** Öndeki birkaç kolon duvar altından daha aşağı iniyor. Model böyle; bu oturum değiştirmedi.

## Aşık ve tavan omegası (20 Kasım, ikinci adım)

Lokman: "bu model istisna olarak prefabrik mantığıyla aşık ve omega olacak"; "60'lık tavan omegasını ters tavana göre ayarla". Lokman önizlemeyi onayladı ("ön izlemede sorun yok").

- **Dosya:** `celik_iskelet_90m2_asik_omega.glb` (1,91 MB). İskelet GLB'si değişmedi.
  - Yeni gruplar: `Asik` 74 parça, `Tavan_omegasi` 45 parça. Öteki dört grup aynen.
  - Komut: `python asik_omega.py celik_iskelet_90m2.glb celik_iskelet_90m2_asik_omega.glb --plan plan_asik_omega.png --ozet ozet_asik_omega.json`. Proje ortamı yeter (numpy, matplotlib); openskp gerekmez.
- **Kural değerleri** depodan okunur:
  - aşık `asik_sirasi`, karar C: mahyadan 60 cm, saçak sırası, saçak eşiği 30 cm, tam parça 410;
  - tavan omegası `tavan_omegasi_yerlesimi`, ters tavan, karar B: odanın x (ya da y) küçük yüzünden 60 cm, karşı yüze 10 cm'den yakın hat yok, tam parça 365.
- **Kesitler:** montaj rehberinden.
  - Aşık 87 × 30 mm, üst 35. Kanatlar makasın üst başlığında.
  - Tavan omegası 110 × 35 mm, üst 65. Kanatlar alt başlığın altında (2,70 m), şapka aşağı.
- **Çatı ölçüleri** iskeletten (`ozet_asik_omega.json › olcu`):
  - ana çatı eğimi %33, mahya 4,415 m, saçak ucu 2,80 m;
  - veranda çatısı 3,295 → 2,80 m;
  - mahya kenarı (3,37; −2,89) → (4,91; −5,07).
  - Sağ yüz ile veranda çatısı mahya kenarının iki ucunda aynı kotta.
- **Sonuç ve kıyas:**

| | Kuralla (bu dosya) | Projenin paftası | Projenin yükleme listesi |
|---|---|---|---|
| Aşık sırası | sol 10, sağ 10, panelin sağ yüzü 4, veranda 5 | sol 11, sağ 11, panelin sağ yüzü 4, veranda 4 (paftanın görüntüsünden sayıldı) | — |
| Panelin sağ yüzü, sıra boyu | 216,0 · 216,0 · 185,5 · 103,1 cm | 216 · 216 · 184,4 · 102,3 cm | — |
| Veranda, sıra boyu | 492,5 – 496,4 cm | 495 cm | — |
| Aşık boyu | 215,5 m (74 parça) | — | 55 adet L 4200 (Excel'in ara değeri 51,2) |
| Tavan omegası hattı | 27: odalar 7 + 3 + 6, salon 8, ön sağ oda 3 | 24: 6 + 3 + 5, 8, 2 | — |
| Tavan omegası boyu | 104,8 m (45 parça) | — | 30 adet L 3750 |

- **Farkın nedeni:**
  - Kural ilk omega hattını duvar yüzüne koyar; pafta ilk hattı yüzden yaklaşık 56 cm içeride çizmiş.
  - Aşıkta pafta saçaktan başlıyor ve 20 cm'de bir mahya sırası koyuyor; karar C mahyadan başlar.
- **Düzeltme (Lokman, 20 Kasım: "şuan gördüğün yerde de aşık olması gerekiyor"):**
  - Çatı panelinin sağ yüzü ana çatının ön kalkanının (y = −2,88 m) önünde açıkta; buraya 4 sıra eklendi.
  - Bu yüz veranda çatısıyla bir derede buluşuyor. Dere (−0,12; −5,04) noktasından (−1,58; −2,87) noktasına gidiyor.
  - Veranda sıraları soldan bu dereye kadar uzar; paftadaki 495'lik paralelkenar budur.
  - Önce ve sonra görüntüsü: `once_sonra_asik.png` (`once_sonra.py`).
- **Çatı paneli:** sol ön köşedeki bölümde omega yok. Paftada da yok; kitapta "çatı panelli ek yapıda omega yok". Salonu bölen kiriş (x = −0,41 m) tavan gözünü böler.
- **Görseller:**
  - `plan_asik_omega.png`: üstten; mavi omega, turuncu aşık.
  - `kesit_asik_omega.png`: saçak, mahya, tavan ve veranda kesiti.
  - `onizleme_asik_omega.png`: yazdırma önizlemesi.
- **Kanıt:** Khronos glTF doğrulayıcısı hata 0, uyarı 0 (13.654 üçgen). Yeniden üretilen iskelet GLB'si bayt bayt aynı.
- **Onay (Lokman, 2026-11-20 21:00 UTC):** "onaylıyorum iç duvar omegalarını boş ver bu şekilde onaylıyorum".
  - Onay `celik_iskelet_90m2_asik_omega.glb` için (dal `claude/celik-iskelet-90m2`, commit `81489726`).
  - İç duvar ekseninde omega hattı (60'lık duvar omegası) konmaz; soru kapandı.
- **Küçük not:** sol yüzün saçağa yakın sıraları sol ön köşede çatı panelinin 2,5 cm üstünden geçer; panel çatı ana çatının düzleminin 2,5 cm altında.

## Mac'teki oturuma yapıştırılacak metin

Lokman öteki oturumu yerelde çalıştırıyor; git ve GitHub kullanılmaz. Dosyalar pakette elle verilir: `celik_iskelet_90m2_paket.zip` (onaylı GLB, bu not, üç kontrol görseli, aşağıdaki metin `OTURUMA_YAPISTIR.txt` olarak).

```
Ekteki dosyalar Raif Can 90 m² çelik iskeleti içindir. Lokman 20 Kasım 2026 21:00 UTC'de onayladı.
Dosyalar bu klasörde; git ya da GitHub kullanma, yerelde çalış.

Dosyalar:
- celik_iskelet_90m2_asik_omega.glb: 3B model (iskelet, aşık, tavan omegası).
  - Birim metre. Taban ortası (0, 0, 0). Blender'da içe aktarınca Z yukarı olur.
  - Gruplar: Duvar, Lento, Makas, Cati_paneli, Tavan_omegasi, Asik.
  - Her parçanın özel özellikleri: katman, z_alt, z_ust (m), sira (alttan üste sıra numarası).
  - Tek malzeme: Galvaniz.
- DEVIR_NOTU.md: ölçüler, kurallar, kanıt.
- onizleme_asik_omega.png: alttan üste yazdırma fikrinin dört karesi.
- plan_asik_omega.png ve kesit_asik_omega.png: aşık ve omeganın yeri; kontrol için.

İş: Blender'da bu GLB'den 10 saniyelik tanıtım animasyonu yap.
- Çelik karkas 3B yazıcıda basılıyormuş gibi alttan üste oluşsun.
- Yazıcı görünmesin.

Önerilen yöntem:
1. GLB'yi içe aktar: Dosya › İçe Aktar › glTF 2.0.
2. Malzemede dünya Z'sine göre kesit kur: kesit yüksekliğinin üstü saydam.
3. Kesitte 15 cm turuncu ışıklı bant koy.
4. Kesit yüksekliğine 0'dan 4,44 m'ye doğrusal anahtar kare ver (4,44 m aşığın tepesi).
5. Kamerayı yavaşça döndür.
6. 1920 × 1080, 30 kare/sn çıkar.

DİKKAT: Higgsfield ücretlidir. Kullanmadan önce Lokman'a tutarı söyle ve onay al.

Model değişmez. Değişiklik gerekirse Lokman'a sor.
```
