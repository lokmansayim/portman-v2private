"""İE-41 · rehber.portatifev.com sitesi main'deki koddan (D-28; Lokman, 14 Kasım 2026 20:37 UTC kartı "Siteyi main'den kur").

Girdi: main'in montaj rehberleri (`python -m araclar.paket <KOD> <çıktı> --is-emri <İş Emri>`; 62 m² hedef örneğin verisinden
`araclar.paket.rehber.sayfa.yaz`). Kayıt: `araclar/paket/site/rehberler.json` (hangi rehber, sitedeki klasörü ve adı).
Çıktı: herkese açık statik site (açılış sayfası + her rehber kendi klasöründe; three.js ve yazı tipleri yerel, dış istek yok),
belirlenimci `rehber_paket.tgz` ve `rehber_kur.sh` (`vps/rehber_yayin.sh` + gömülü paket; Lokman Mac'ten koşar).

Kurallar (Lokman, 4 Kasım 2026, kart 104; ilk paketleyici `claude/montaj-rehberi-devir` dalında, `deneme/2026-11-04_rehber_sitesi/`):
başlıkta kod yerine alan ve oda sayısı; iç notlar (Motor, kural, karar kodu, kişi adı, başka evin kodu) sayfaya girmez; ön onay
paftasının üst satırı ("PORTMAN | Bayi … | İş Emri …") örtülür; son kapı `ortak.YASAK` taraması.

    python -m araclar.paket.site <çıktı> --npm <npm pack klasörü> --esbuild <esbuild yolu>
"""
