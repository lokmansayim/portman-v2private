# Montaj rehberinin hedef örneği: Mehmet Kapaklı Tek 63 m² (D-160; D-28 madde 2)

| | |
|---|---|
| Örnek | Mehmet Kapaklı Tek 63 m² evin (TK-11) montaj rehberi: 20 adım ve bitmiş bina, 429 parça; çatı 14 üretim makasıyla (D-159) |
| Onay | Lokman, 27 Kasım 2026 21:42:26 UTC, kart "Soru 18: 63 m2 evin montaj rehberi bu çatıyla son hâli olsun mu?": "A: Onaylıyorum". Kartın açıklaması: "Rehber ana koddan üretildi. Veranda çatısı 1,24 cm saçağa kayık (saçak 31,24 cm). Dereler arasında 1,0 cm aralık var. Liste ve teklif aynı: 454.607,96 TL." Seçeneğin kartta yazan sonucu: "Rehberin hedef örneği dondurulur ve rehber, rehber sohbetine verilir." (kart `cmsg_01UAFvcnfVuTR1wfFux5fQPPAWLGGiCGrjtXa45Etor5tY`; seçimi koordinatör bildirdi). Onay rehber içindir; birleştirme, canlı ya da yayın onayı değildir |
| Önceki onaylar | Çatı: Soru 6, Soru 12, Soru 14, Soru 16 kartları (D-158, D-159; `testler/paket/veri/TK11_rehber_cati_beklenen.json`) |
| Onaylanan dosya | `TK-11_montaj_rehberi.html`, 27 Kasım 2026 16:12 UTC'de `main` `d350ebd5`'ten aşağıdaki komutla üretildi (sha256 `ad52e18c142c05d90050b260472e988d1f18704e0f7de344e9b9887311062b4d`). Proje dosyalarında: `Teklif_Calisma/TK-11/rehber_r02_main_d350ebd/`. Lokman'ın gördüğü görsel aynı klasörde: `TK11_rehber_cati_son_hali_20261127.png` |
| Girdi | `araclar/paket/girdi/TK11_r02_cati.json` (onaylı teklifin İş Emri r02 + iki çatı anahtarı), tavan seçeneği `ters` |
| Komut | `python -m araclar.paket TK-11 <çıktı> --is-emri araclar/paket/girdi/TK11_r02_cati.json --tavan ters` |
| Beklenen çıktı | `iz.json`: onaylanan sayfanın izi (`araclar/paket/rehber/iz.js`: her parçanın adımı, sırası, kartı, yazısı, dünya koordinatındaki köşelerinin izi; adımların metni, satırları, kamerası). `python -m araclar.paket.rehber.iz <rehber.html> <iz.json>` ile onaylanan dosyadan alındı |
| Kıyas | `testler/paket/test_rehber_tk11_63.py::test_rehberin_butunu_onayli_ornek`: komut → sayfa → iz = `iz.json`. CI'da pytest parçalarında koşar (`.github/workflows/dogrulama.yml`; three.js ya da Playwright yoksa iş kırmızıdır) |
| İzin kapsamadığı | Evin altındaki ön onay sayfası (M-13; kendi hedef örneği `testler/paket/rehber_kagit/`). Paketin öteki dosyaları (liste, çizim, montaj paftası, bilgi dosyası) |
| Değişme yolu | Yalnız Lokman'ın onayı ve gerekçeli kararla (D-02); testi geçirmek için iz yeniden alınmaz |
| Yeniden alınışlar | Yok |
