-- BK-10 · 011: mühendis kontrolünün iki yeni kapanışı ve onay bekleyen revizyonun zaman aşımı. (1) D-19 (24 saat kuralı; Lokman 14.10 23:56): mühendis kontrol açıldıktan 24 saat
-- sonra karar vermediyse hatırlatmalar durur, kontrol 'zaman_asimi' olur, Patron'a tek bildirim gider; Patron panelden yeniden açabilir.
-- (2) Rehber §4 "plan değişirse önceki onaylar düşer": bayi onaydan sonra yeni revizyon isterse açık kontrol 'plan_degisti' olur, mühendise
-- "plan değişti" yazılır (kanal/muhendis.py). (3) D-19 bayi tarafı: bayiden cevap beklenen açık iş bayinin son mesajından 24 saat sonra
-- kapanır; onay bekleyen revizyon 'zaman_asimi' olur (kanal/kalici.py › acik_is_kapanisi), kayıt silinmez.
-- YALNIZ EKLER (docs/is_emirleri/IE-06.md › Sürüm kuralı; .claude/rules/kanal-vps.md): önceki sürümün kodu bu şemada çalışır (yeni durumları
-- hiç yazmaz; okurken bilinmeyen durum karar bekleyen sayılmaz). CHECK genişletme serbest. Her ifade tekrar koşulabilir. Uygulandıktan sonra
-- bu dosya değiştirilmez; sonraki değişiklik 012_… olur.

ALTER TABLE muhendis_kontrolleri DROP CONSTRAINT IF EXISTS muhendis_kontrolleri_durum_check;
ALTER TABLE muhendis_kontrolleri ADD CONSTRAINT muhendis_kontrolleri_durum_check
    CHECK (durum IN ('bekliyor', 'patrona_gonderildi', 'duzeltme', 'kart_yok', 'zaman_asimi', 'plan_degisti'));

ALTER TABLE muhendis_kontrolleri ADD COLUMN IF NOT EXISTS zaman_asimi timestamptz;      -- 24 saat doldu (D-19); Patron'a bildirim bu anda
ALTER TABLE muhendis_kontrolleri ADD COLUMN IF NOT EXISTS yeniden_acildi timestamptz;   -- Patron panelden yeniden açtı: 24 saat buradan sayılır
ALTER TABLE muhendis_kontrolleri ADD COLUMN IF NOT EXISTS plan_degisti timestamptz;     -- bayi yeni revizyon istedi; bildirim bir kez (karar verilmişse durum aynen kalır)

ALTER TABLE revizyonlar DROP CONSTRAINT IF EXISTS revizyonlar_durum_check;
ALTER TABLE revizyonlar ADD CONSTRAINT revizyonlar_durum_check
    CHECK (durum IN ('onay_bekliyor', 'onaylandi', 'yerini_aldi', 'dogrulanmadi', 'zaman_asimi'));
