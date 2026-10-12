# A2 ve A3 · Prefabrik duvar

Kaynak: Lokman'ın anlattıkları (1–2 ve 6 Ekim 2026). Çalışma şimdilik çelik üzerine; burası yalnız kayıttır.
Astra dönemindeki prefabrik çizim kuralları (v1.4.3) buraya henüz taşınmadı.

## Panel (A2)

- Türkiye'deki prefabrik uygulaması dünyadakinden farklı: 8 mm betopan ya da fibercement iki levha arasında 80 mm, 16 dansite strafor (EPS). (1 Ekim)
- Panel ölçüsü 125 × 250, 280 ya da 300 cm. (1 Ekim)
- Aksların 125,5 olmasının nedeni: birleşim elemanı olarak H profil kullanılıyor. (1 Ekim)
- Astra'nın prefabrik aks mantığı doğru. (1 Ekim)

## Ölçüye kesim (özel pano)

- Her pano 1255 mm. Dizilim yapının bitiş noktasına geldiğinde son parça kesilir; özel ölçülü pano olur. (6 Ekim 18:50)
- Dış ölçü verildiyse yapı o ölçüde çizilir; tam panoya yuvarlanmaz. Örnek: 11,50 × 10,50 m, verandasız. (6 Ekim 18:50)
- Çıkarım: dizilim soldan ve önden başlar; kesilen parça sağ ve arka uçta kalır.
- Çıkarım: iç duvarlar aks üstünde kalır; her iç duvar koşusu da kendi başından 125,5 cm ilerler ve son parçası kesilir.
- Örnek (dış 160 mm): 1150 cm → 8 tam pano + 114 cm; 1050 cm → 8 tam pano + 30 cm.
- Canlı Motor'da yok. Deneme: `deneme/2026-10-06_kalinlik_160_100/`.

## Duvar kalınlığı seçeneği

- Dış duvar 160 mm, iç duvar 100 mm, yükseklik 2800 mm istendi. (6 Ekim 18:28)
- Çıkarım: akslar kalınlıkla birlikte kayar. Düşey akslar dış duvarın iç yüzünden, yatay akslar duvar ekseninden başlar; tam modülde dış ölçü = pano × 125,5 + iki dış duvar (x) ve + bir dış duvar (y).
- Çıkarım: dış köşe parçası 160 × 80, iç köşe 100 × 50, üçlü H 100.

## Köşe dikmeleri

- Tek kat prefabrikte köşe kolonu 50 × 100. (2 Ekim 20:15)
- Çift kat prefabrikte köşe kolonu 100 × 100, 532 cm profil dikme. (2 Ekim 20:15)
- Bu değişiklik aksı bozmaz, dizilimi bozar. (2 Ekim 20:15)

## Çift kat prefabrik alt kat (A3)

- Alt kat karkaslı. (2 Ekim 20:15)

## Açık sorular

- 100 × 100 köşe dikmesiyle köşedeki panel dizilimi nasıl değişiyor?
- Alt kat karkasının profilleri ve aralıkları.
- İç duvar (6 cm) neyden oluşuyor?
- Ölçüye kesimde son parça çok dar çıkarsa (örnek: 30 cm; iç duvarda 22 cm) ne yapılır? En az pano boyu var mı?
- Ölçüye kesimde dizilim hangi uçtan başlar?
- 160 mm dış ve 100 mm iç duvarda köşe ve H bağlantı profilleri hangileri?
- 160 mm ve 100 mm panonun katmanları (levha ve dolgu kalınlığı).
