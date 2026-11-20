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

## Mac'teki oturuma yapıştırılacak metin

```
portman-v2private deposunda claude/celik-iskelet-90m2 dalını çek; dala geçme, main'e karıştırma:
  git fetch origin claude/celik-iskelet-90m2
  git show origin/claude/celik-iskelet-90m2:deneme/2026-11-20_celik_iskelet/celik_iskelet_90m2.glb > ~/Desktop/celik_iskelet_90m2.glb
Not: docs/devir/2026-11-20_Celik_Iskelet_Devri.md (aynı daldan git show ile oku).
İş: Blender'da bu GLB'den 10 saniyelik tanıtım animasyonu. Çelik karkas 3B yazıcıda basılıyormuş gibi alttan üste oluşsun; yazıcı görünmesin.
Önerilen yöntem: malzemede dünya Z'sine göre kesit (kesit yüksekliğinin üstü saydam), kesitte 15 cm turuncu ışıklı bant, kesit yüksekliği 0'dan 4,42 m'ye doğrusal anahtar kare; yavaş dönen kamera; 1920 × 1080, 30 kare/sn.
Higgsfield ücretlidir: kullanmadan önce Lokman'a tutarı söyle ve onay al.
```
