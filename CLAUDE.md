@AGENTS.md

# Claude Code · oturum akışı

Ortak kurallar yukarıdaki `AGENTS.md`'den gelir; burada yalnız Claude'a özgü akış var.

## Oturum başında

1. **Devir notunu oku.** `docs/devir/` altındaki en yeni not, nerede kalındığını ve sırayı söyler.
2. **Güncel durumu ve aktif işi oku.** `DURUM.md`'nin başında aktif iş emri ve dalı yazar; o dala geç. `main`'deki DURUM geride olabilir; en yeni iş dalındaki DURUM esastır.
3. **Ortamı kur:** `bash araclar/ortam_kur.sh` (gerileme için `--dogrula`).
4. **Yeni işe Plan modunda başla.** Plan Lokman'ın onayından sonra uygulanır; iş emri belgesi `/is-emri` ile açılır. Diff'i tek cümleyle anlatılabilen küçük düzeltmelerde plan atlanabilir.
5. **Lokman'a anlatım.** Her adımda ne yapıldığı iki cümleyle Türkçe söylenir; onayı gereken yerde tek soru sorulur; beklemeye düşülmez, kendi başına devam edilir.

## Komutlar (skill)

| Komut | Ne yapar |
|---|---|
| `/is-emri <KOD> <başlık>` | Dal + iş emri belgesi + plan; onay için durur |
| `/kapanis` | Doğrulama → kanıt → DURUM → commit/push → `/code-review` → PR özeti |
| `/sahip-ozeti` | Lokman için 10 satırlık durum: canlıda ne var, bekleyen onaylar, açık riskler |

Hakemler (`.claude/agents/`): `geometri-hakemi` (Motor/İş Emri değişikliklerini kurallara karşı inceler), `kvkk-denetcisi` (diff'te sır ve kişisel veri arar). Kapanışta ikisi de koşturulur.

## Frenler (hook; `.claude/settings.json`)

- `sir_koruma.py` — sır ve canlı durum dosyaları ile dondurulmuş kayıtlar düzenlenemez; sır içeren yazım engellenir; telefon numarasına benzeyen içerik sorar.
- `komut_koruma.py` — `ssh/scp/sftp/rsync`, `vps_komut`, `main`'e push ve zorla push engellenir; `main`'deyken birleştirme engellenir; silme, ağ ve veritabanı komutları sorar.
- `hizli_kontrol.py` — her `.py/.sh/.json` düzenlemesinden sonra sözdizimi denetimi; hata varsa düzeltmeden devam edilmez.

Hook'lar talimat değil koddur: kuralı yorumlayarak aşılamaz. Bir hook'u değiştirmek ya da kapatmak Lokman'ın onayını gerektirir.

## Commit ve dal

- **Commit kimliği:** `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit`. Mesajın sonuna oturumun verdiği Co-Authored-By ve Claude-Session satırları eklenir.
- **Push.** Oturum sonunda izlenmeyen dosyalar da commit'lenip iş dalına push edilir.
- **Dallar.** Her iş emrinin kendi dalı olur. `main`'e birleştirme yalnız Lokman'ın açık onayıyla yapılır.
- **Oturum sonu.** Her oturumun son adımı `DURUM.md`'yi güncellemektir (`/kapanis` bunu yapar). Pencere değişecekse `docs/devir/`'e bir not yazılır.

## Yerler

- **Mac çalışma klasörü:** `~/Desktop/Claude Portman Çalışması/`, numaralı klasörler.
  - Kapı çıktıları, yedekler, aday paketleri ve Astra'nın çizimleri (`24_Astra_Cizimler/`) orada durur.
  - Kökteki `DURUM.md` 23.09 tarihlidir ve güncel değildir; güncel durum depodadır.
- **Zemin (Claude Docs):** belge `65844cef-e6c5-4a5d-b714-ee003c57fe5b`. "Güncel durum" sekmesi durumlarla birlikte güncellenir.
- **Hedef WhatsApp Akışı (Design kanvası):** https://claude.ai/artifact/478avu6uRTg3tP7q8A3qoL.
