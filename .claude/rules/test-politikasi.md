# Test politikası (her oturumda geçerli)

- Testler davranışın değişmediğini söyler, planın doğru olduğunu değil. "Çalışıyor" ancak tarihli kanıtla yazılır (komut + sonuç).
- Üç katman: Beyin harness (22 vaka, LLM çağrısı yok) · referans gerilemesi (`testler/referans/dogrula.py`; sonuç AYNI/FARKLI) · pytest (`testler/`; Postgres yoksa kalıcı akış atlanır).
- `motor/`, `beyin/` ya da `kanal/` değiştiyse kapanışta tam doğrulama (`bash araclar/ortam_kur.sh --dogrula`); yalnız belge/ayar değiştiyse `dogrula.py --hizli` yeter.
- Referans girdiler (`is_emri/`, `ref_katalog/`, `ref_yan/`, `beyin/veri/`; 23 dosya) ve 22 harness vakası değişmez; yeni vaka yalnız sona eklenir (aynı göndericinin vakaları durumu paylaşır).
- Referans yeniden dondurma (`dogrula.py --dondur --gerekce … --karar …`) `KARARLAR/` altında var olan bir karara dayanır; yalnız testi geçirmek için yapılmaz (D-02).
- `denetim/kos.py` depo kökünde doğrudan koşulmaz; `dogrula.py` üzerinden koşulur (`deneme/` ve `testler/` olmadan geçici kopyada).
- Bilinen fark yok (İE-08, 12.10.2026'dan beri): sır taramasının `vps/kapi_d_dogrula.sh:25` yanlış pozitifi `kos.py`'de beklenen bulgudur, telefon deseni ondalıkları numara sanmaz (`testler/test_sir_taramasi.py`). `dogrula.py` "fark yok" demeli; herhangi bir FARKLI varsa iş kapanmaz.
- Testi geçirmek için test gevşetilmez; bir vaka değişecekse gerekçesi iş emri belgesine yazılır ve incelemede ayrıca gösterilir.
