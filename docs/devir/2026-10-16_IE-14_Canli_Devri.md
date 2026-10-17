# Devir · İE-14 canlıda (16–17 Ekim 2026 gecesi)

**Nerede kalındı.** İE-14 `v2026.10.16` ile canlıda. Patron kartıyla T1–T5 Canlıda çalışıyor. Ayarlar Lokman'ın kararıyla: `plan_uretimi` açık, `llm_once_revizyon` kapalı. Kanıt `docs/is_emirleri/IE-14.md › Kanıt › 16 Ekim`.

**Sıradaki (sırayla):**
1. **Gölge okuma kaydı.** Son kontrol iş bitmeden koştu. Lokman Mac'ten `ie14_kontrol.sh deneme 240` koşar (komut `docs/notlar/2026-10-15_IE14_canliya_alma.md`). Beklenen: "dış duvarlar 140" işi `bitti · … · gölge 1`, `okuma_kiyaslari`'nda `Ç8801K · r1 · … · 1`, açık iş 0. Sonuç IE-14 Kanıt'a ve Notion Görev 6d Dönüş'üne eklenir.
2. **Birleştirmeler (Lokman):**
   - belge PR'ı (dal `ie-14-talepten-plana`; yalnız belge ve kural);
   - PR #25 (BK-11, `bk-11-postgres-bekleme`). Dal eski `main`'de; yalnız `DURUM.md` çakışıyor. Çözüm `main`'i dala birleştirmek (merge commit), ancak Lokman isterse; başka oturumun dalı.
3. **Bakım adayları (BK-12'den; Lokman'ın sırasıyla):**
   - düğmeli mesajda satır sonları siliniyor (`worker._kes`, İE-04'ten beri);
   - banka planının ilk çiziminde LLM özeti mesaja ve PDF başlığına giriyor ("netleştirmeniz gerekiyor" ile "planınız hazır");
   - dış kapı taşımanın üç düşük sınırı (`IE-14.md › K › Bilinen sınırlamalar`).

**Kurallar (yeni).** `kvkk-denetcisi` kapanışta yalnız sır taraması; KVKK maddeleri pilottan önce toplu (Lokman 16.10, `CLAUDE.md`). Asistan sunucuya bağlanmaz; komutlar Lokman'ın Mac'inden, depo klasöründe (`~/Desktop/"Claude Portman Çalışması"/30_IE06/depo`), çıktılar `IE14_canli/` klasörüne.
