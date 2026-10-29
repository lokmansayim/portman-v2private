---
name: atolye
description: Model atölyesi (İE-09, D-20) — Lokman'ın isteğinden bankaya bir model; kart, Yapı Tanımı, çizim, kontrol sayfası, düzeltme, kabul ve gün sonu. Kullanım /atolye <KOD> <istek> (ör. /atolye Ç8801D Ç8801'in tam kırma çatılısı).
argument-hint: <KOD> <istek>
---

# Atölye: $ARGUMENTS

Sen Portman'ın model atölyesindesin (İE-09, `docs/is_emirleri/IE-09.md`; karar D-20). Lokman ne yapılacağını yazar, sen tanımı yazar ve düzeltirsin, kontrolü ve kabulü o yapar. Araç `araclar/atolye.py`; motoru yalnız çağırır, LLM yok. Her adımı Lokman'a iki cümleyle Türkçe söyle.

## Değişmezler

- **Hakem değişmez.** Model PR'ında yalnız yeni modelin kendi dosyaları eklenir (`modeller/banka/<DOSYA>/`). Referans (`testler/referans/`), başka modelin kontrol dosyası ve var olan test değişmez. Bunlar ayrı PR'da, gerekçe ve `KARARLAR/` altındaki bir kararla, Patron'un açık onayıyla değişir (`atolye.py dondur`; D-02).
- **Kör test seti açılmaz.** AIPrefabrik'te 20 projenin yükleme listesi kapalıdır (listesi açık olanlar: AP-01…05, 07, 08, 19); bu listeler kaynak ya da kıyas olarak alınmaz. Araç reddeder; elle de açma, okuma. Montaj paftası kaynak olabilir; liste yalnız kör test protokolüyle açılır.
- **Kaynak dosyalar depoya girmez.** Karta etiket (kişi ya da bayi adı taşımayan, senin yazdığın), uzantı, boyut ve SHA-256 girer. Müşteri projesi bayiye adsızdır (AP/KT kodu).
- **LLM anlar, kod karar verir.** DWG varsa LibreDWG ile DXF'e çevir, ölçüleri ezdxf ile koddan oku; PDF'te vektör ve metin koddan. Görselden okuduğun her ölçüyü ve kapı/pencere sayısını `kaynak --kaynagi "görsel okuma: …"` ile kaynağıyla yaz; kontrol sayfasında yan yana durur.
- **Motor kusuru o an düzeltilmez.** `duzelt --tur motor` kusur defterine (`docs/notlar/IE-09_motor_kusurlari.md`) yazar; düzeltmesi ayrı PR. Tanımla atlatılabiliyorsa (ör. kısa ad) atlat ve defterde söyle.
- Canlı, sunucu, ücretli deneme ve silme yok. Mac'teki arşiv yalnız okunur, izinle (cihaz klasör araçları).

## Adımlar

1. **Dal.** Atölye günü kendi dalında: `ie-09-atolye-<tarih>` (ya da oturumun verdiği dal). `main`'e birleştirme yalnız Lokman'ın onayıyla.
2. **Kart.** Yeni proje: `python3 araclar/atolye.py ac <KOD> --ad "…" --kaynak-metni "<Lokman'ın sözü, tarihle>" [--proje AP-NN] [--kaynak-dosya <yol>=<etiket> …] [--musteri-projesi]`. Var olan modelin çatı varyantı: `varyant <KOD> --taban <taban kod> --cati <çatı.json> --ad "…" --kaynak-metni "…"` (taban tanım değişmez; kaynak değerleri taban kaydından gelir). Kod çakışırsa ya da aynı çatı bankada varsa araç durur.
3. **Tanım.** `modeller/banka/<DOSYA>/tanim.json` (Yapı Tanımı 0.5, cm). Dikdörtgen planda plan şeması ve `plan_derle`; L, cumba, kanatlı çatıda üreteç betiği ya da elle (Ç8801, KT-01…03 örnekleri). Kaynakta yazan değerleri gir: `kaynak <KOD> --kaynagi "<nereden>" --oda "Salon=21,3" … --brut-m2 … --oda-programi … --pencere … --kapi …`.
4. **Çiz.** `ciz <KOD> --cikti /mnt/project-files/Portman_Proje_Dosyalari/IE-09_atolye/<tarih>` (paylaşılan klasör yoksa varsayılan `cikti/atolye/`). Kontrol sayfası `<DOSYA>_kontrol_cNN.pdf`: kart, oda tablosu (çizim ↔ kaynak), denetimler (motor, IFC, yazı çakışması, 15 cm parçalar, kart–çizim tutarlılığı, bankada aynı model), metraj kapısı, liste özeti, çizim seti, bayi paftası, bayi görseli. "kaldı" varsa göndermeden düzelt; "uyarı"yı mesajda tek satırla söyle.
5. **Metraj kapısı.** Gerçek Excel varsa: `metraj <KOD> --excel <yol> --hucre "Sayfa!F12"` (toplam hücresi koddan) ya da `--kg N` (elle, kaynağıyla). Çelik kg farkı ±%3'ü aşarsa model `beklemede`, kabul edilemez. Excel yoksa sayfa "referans yok, koşulmadı" der; kabul metraj doğrulaması sayılmaz.
6. **Lokman'a gönder.** Kontrol PDF'ini thread'e dosya olarak ekle; mesaj kısa: ne çizildi, uyarılar, metraj kapısının sonucu. "Uygunsa **kabul** yazın, değilse düzeltmeyi düz cümleyle yazın."
7. **Düzeltme.** Lokman'ın cümlesini tanıma işle, `duzelt <KOD> --tur okuma|tercih|kural|motor --metin "…"`, sonra yeniden `ciz` (yeni cNN) ve yeni sayfayı gönder.
8. **Kabul.** Lokman "kabul" deyince `kabul <KOD> [--not "…"]`. Kapı: son çizimle aynı tanım, kalan denetim yok, metraj kapısı geçti ya da referans yok, kontrol dosyası (hızlı + tam izler, kural seti pimi) yazılır, sonra harness 22/22 ve `pytest testler` model bankadayken koşar (birkaç dakika; Postgres için `PORTMAN_TEST_PG`). Bir test değişirse kabul durur, kart `kontrolde` kalır: testi kendin değiştirme, ayrı PR için Lokman'a sor.
9. **Gün sonu.** `gunluk` sayımı (açılan, çizilen, kabul, ret, beklemede, düzeltme türleri, motor kusurları). `kontrol --tam` "banka kontrol dosyalarıyla aynı" demeli. Günün dosyaları tek PR: kart, tanım, kontrol, `kart.png`, kusur defteri; DURUM.md ve `IE-09.md › Kanıt`. Dönüş satırı Notion'a (≤ 8 satır).
10. **Canlıya alma haftalıktır** ve ayrı onayla: sürüm etiketi + `guncelle.sh`, sonra haftanın kabul kodlarıyla `vps/ie08_adaylar.sh` (K-A10). Atölye modeli bayiye yalnız bu kayıtla görünür; çatı varyantı bugünkü çatı setine girmez.
