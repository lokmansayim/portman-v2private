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

- **Dosya:** `celik_iskelet_90m2_asik_omega.glb` (1,88 MB). İskelet GLB'si değişmedi.
  - Yeni gruplar: `Asik` 68 parça, `Tavan_omegasi` 45 parça. Öteki dört grup aynen.
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
| Aşık sırası | sol 10, sağ 10, veranda 5 | sol 11, sağ 11, alt bölümde 4 + 4 (paftanın görüntüsünden sayıldı) | — |
| Aşık boyu | 204,8 m (68 parça) | — | 55 adet L 4200 (Excel'in ara değeri 51,2) |
| Tavan omegası hattı | 27: odalar 7 + 3 + 6, salon 8, ön sağ oda 3 | 24: 6 + 3 + 5, 8, 2 | — |
| Tavan omegası boyu | 104,8 m (45 parça) | — | 30 adet L 3750 |

- **Farkın nedeni:**
  - Kural ilk omega hattını duvar yüzüne koyar; pafta ilk hattı yüzden yaklaşık 56 cm içeride çizmiş.
  - Aşıkta pafta saçaktan başlıyor ve 20 cm'de bir mahya sırası koyuyor; karar C mahyadan başlar.
- **Çatı paneli:** sol ön köşedeki bölümde omega yok. Paftada da yok; kitapta "çatı panelli ek yapıda omega yok". Salonu bölen kiriş (x = −0,41 m) tavan gözünü böler.
- **Görseller:**
  - `plan_asik_omega.png`: üstten; mavi omega, turuncu aşık.
  - `kesit_asik_omega.png`: saçak, mahya, tavan ve veranda kesiti.
  - `onizleme_asik_omega.png`: yazdırma önizlemesi.
- **Kanıt:** Khronos glTF doğrulayıcısı hata 0, uyarı 0 (13.390 üçgen). Yeniden üretilen iskelet GLB'si bayt bayt aynı.
- **Açık soru:** iç duvar ekseninde omega hattı (60'lık duvar omegası).
  - Kural bunu 60'lık iç duvara koyar, 100'lüğe koymaz.
  - Bu evin iç duvarı 80 mm; Motor'un kodu 100 mm'den inceyi 60'lık sayar.
  - Pafta koymamış; bu dosyada da yok.
- **Küçük not:** sol yüzün saçağa yakın sıraları sol ön köşede çatı panelinin 2,5 cm üstünden geçer; panel çatı ana çatının düzleminin 2,5 cm altında.

## Mac'teki oturuma yapıştırılacak metin

```
portman-v2private deposunda claude/celik-iskelet-90m2 dalını çek; dala geçme, main'e karıştırma:
  git fetch origin claude/celik-iskelet-90m2
  git show origin/claude/celik-iskelet-90m2:deneme/2026-11-20_celik_iskelet/celik_iskelet_90m2_asik_omega.glb > ~/Desktop/celik_iskelet_90m2_asik_omega.glb
Not: docs/devir/2026-11-20_Celik_Iskelet_Devri.md (aynı daldan git show ile oku).
İş: Blender'da bu GLB'den (iskelet + aşık + tavan omegası; gruplar Duvar, Lento, Makas, Cati_paneli, Tavan_omegasi, Asik) 10 saniyelik tanıtım animasyonu. Çelik karkas 3B yazıcıda basılıyormuş gibi alttan üste oluşsun; yazıcı görünmesin.
Önerilen yöntem: malzemede dünya Z'sine göre kesit (kesit yüksekliğinin üstü saydam), kesitte 15 cm turuncu ışıklı bant, kesit yüksekliği 0'dan 4,44 m'ye (aşığın tepesi) doğrusal anahtar kare; yavaş dönen kamera; 1920 × 1080, 30 kare/sn.
Higgsfield ücretlidir: kullanmadan önce Lokman'a tutarı söyle ve onay al.
```
