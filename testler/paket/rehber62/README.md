# Montaj rehberinin hedef örneği: 62 m² (D-28 madde 2, A1)

| | |
|---|---|
| Örnek | 62 m² bayi projesinin montaj rehberi; rehber.portatifev.com'da yayında olan sayfa |
| Kaynak | dal `claude/montaj-rehberi-devir` `6b899b4`, `deneme/2026-10-25_rehber_62m2/rehber/` (`data.json`, `sahne.js`, `kabuk.html`, `uret.py`) |
| Onay | Lokman, 28 Ekim 2026 06:39 UTC, D-28 ("Her çıktının onayınızdan geçmiş bir hedef örneği depoda durur (rehberde 62 m²)" önerisine "evet yaz"); 06:29'da TK-01 rehberini bu sayfayla kıyasladı ("tam olarak aynısı olmamış 62 ile") |
| Girdi | `kaynak.json` (62'nin `data.json`'u aynen) + `metin.json` ve `donustur.py`'deki sabitler (62'nin `sahne.js`'inde eve ait sayılar ve yazılar) |
| Şablonun verisi | `veri.json` = `python testler/paket/rehber62/donustur.py` |
| Beklenen çıktı | `iz.json`: onaylı sayfanın izi (`araclar/paket/rehber/iz.js`: her parçanın adımı, sırası, kartı, yazısı, dünya koordinatındaki köşelerinin izi; adımların metni, satırları, kamerası) |
| Bilinçli fark | Dübelin adı "Çelik dübel" (karar verilmiş kalem); iz aynı düzeltmeyle alındı |
| Kıyas | `testler/paket/test_rehber.py`: şablon (`araclar/paket/rehber/sahne.js` + `kabuk.html`) + `veri.json` → sayfa → iz = `iz.json`. CI'da "kalan" işinde koşar (`.github/workflows/dogrulama.yml`) |
| Değişme yolu | Yalnız gerekçeli bir kararla (D-02); testi geçirmek için iz yeniden alınmaz |
