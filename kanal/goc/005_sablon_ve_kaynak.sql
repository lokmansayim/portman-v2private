-- İE-07 · 005: Meta şablon mesajı (giden kind 'template'), giden satırının kaynağı (ajan | panel) ve kuru koşu için 'test' rolü.
-- YALNIZ EKLER (docs/is_emirleri/IE-06.md › Sürüm kuralı; .claude/rules/kanal-vps.md): önceki sürümün kodu bu şemada çalışmaya
-- devam eder; DROP TABLE / DROP COLUMN, RENAME, tür daraltma ve varsayılansız NOT NULL yok; CHECK genişletme serbest. Her ifade
-- tekrar koşulabilir. Uygulandıktan sonra bu dosya değiştirilmez; sonraki değişiklik 006_… olur.

-- Giden satır türlerine Meta şablon mesajı eklenir (satır içeriği giden.satir jsonb: sablon_anahtari, sablon{dil, govde, dugmeler},
-- pencere_kapaliysa). Şablonun Meta adı satıra yazılmaz; gönderim anında settings.json'daki anahtardan çözülür.
ALTER TABLE giden DROP CONSTRAINT IF EXISTS giden_kind_check;
ALTER TABLE giden ADD CONSTRAINT giden_kind_check CHECK (kind IN ('text', 'document', 'image', 'interactive', 'template'));

-- Satırı kim yazdı: ajan (bugünkü bütün satırlar) ya da panel (Patron'un panelden gönderdiği metin, PDF ve şablon).
-- Panel satırı bayinin son gelen mesajına bağlanır; gönderici penceresini o mesajın değil bayinin son mesajının zamanıyla ölçer.
ALTER TABLE giden ADD COLUMN IF NOT EXISTS kaynak text NOT NULL DEFAULT 'ajan';

-- Kuru koşu göndericisi: panelden girilen, rol = 'test' sahte kart. Patron modunda da sahiplenilir; Patron konuşmasına iz bırakmaz.
ALTER TABLE bayiler DROP CONSTRAINT IF EXISTS bayiler_rol_check;
ALTER TABLE bayiler ADD CONSTRAINT bayiler_rol_check CHECK (rol IN ('bayi', 'patron', 'muhendis', 'test'));
