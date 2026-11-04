# Frenler: hook'u ve klasör kuralı yüklenmeyen oturumlar için (BK-21, 4 Kasım 2026)

Project thread'lerinde (claude.ai proje sohbeti) `.claude/settings.json` okunmaz: hook, izin, skill, hakem ajan ve klasöre bağlı kural yüklenmez (4 Kasım 2026 denetimi). Bu dosyanın yolu yoktur, her oturumda yüklenir. Hook'ların ve izinlerin yaptığını metin olarak söyler; yorumlanmaz, aşılmaz. Son kapı CI'dır (`Doğrulama sonucu`, mühür kilit testi, `Korunan dosya onayı`) ve `main` dal korumasıdır. Bu dosya, `araclar/fren.py` ve CI iş akışları yalnız Lokman'ın onayıyla değişir.

## Tek komut: `python3 araclar/fren.py`

Commit'ten ve PR'dan önce koşulur. Dalın `main`'den farkını (commit'lenmemiş ve izlenmeyen dosyalar dahil) korunan listeyle kıyaslar, değişen `.py`/`.sh`/`.json`'un sözdizimini ve mühürleri denetler. Çıkış 0 temiz; 1 dur (yasak dosya, sözdizimi ya da mühür hatası; düzeltmeden devam yok); 3 Lokman'ın onayı gerekir. CI aynı listeyi PR'da denetler: korunan dosya değişiyorsa Lokman PR'a `patron-onayi` etiketini GitHub'da kendisi ekler. **Oturum bu etiketi eklemez** (Lokman'ın yerine onay verilmez); uygulama üzerinden eklenen etiket CI'da sayılmaz. Onay PR'a özgüdür: onaydan sonra korunan dosyaya yeni değişiklik eklenirse Lokman'a yeniden sorulur. "Korunan dosya onayı" kırmızıyken birleştirilmez.

## Dokunulmaz ve onaylı yerler (`sir_koruma.py`, izinler)

- **Okunmaz, yazılmaz, depoya girmez:** `.env` ve `*.env`, `agent.env`, `claude_api.json`, `kanal/settings.json`, `kanal/api_token.txt`, `kanal/state.json`, `kanal/durum/`, `kanal/lib.snapshot.php`, anahtar dosyaları (`.pem`, `.key`, `id_*`, `deploy_key`, `rclone.conf`, `yedek.*`), `~/.ssh/`.
- **Elle değiştirilmez (dondurulmuş):** `SHA256SUMS`, `KARARLAR.md`, `testler/referans/<tarih>/`, `hosting/`. Referans yalnız `dogrula.py --dondur --gerekce … --karar …` ile, `KARARLAR/`'da var olan bir kararla ve Lokman'ın onayıyla yeniden dondurulur (D-02). Testi geçirmek için hedef ya da referans değiştirilmez.
- **Var olan dosyası değişmez, yeni dosya eklenebilir (referans girdi):** `is_emri/`, `ref_katalog/`, `ref_yan/`, `ref_prefabrik/`, `beyin/veri/`, `beyin/testler/` (harness'i kanıt için `harness.main(durum_dir=<geçici>, rapor_yaz=False)` ile koş), `modeller/*.json` (D-07), `kurallar/liste/setler/`.
- **Lokman'ın onayıyla:** `.claude/settings.json`, `.claude/hooks/`, `.github/workflows/`, bu dosya, `araclar/fren.py`.
- **Kararlar:** yeni karar `KARARLAR/`'a yeni dosya; kaynak satırında Lokman'ın sözü kelimesi kelimesine ve saatiyle (D-42, D-43 biçimi). Lokman'ın ağzından çıkmayan bir okuma karar diye yazılmaz; var olan bir kararın metni onun sözü olmadan değişmez.
- **Mühürlü konular** (`AGENTS.md` tablosu, `KARARLAR/muhurlu.json`): kilide dokunacak iş önce Lokman'a tek satırla sorar ve cevabını bekler. Elle denetim: `python3 .claude/hooks/muhur_koruma.py denetle` → "mühürler sağlam" beklenir.

## Komutlar (`komut_koruma.py`, izinler)

- `ssh`, `scp`, `sftp`, `rsync` ve `vps_komut` yok; sunucu işi `AGENTS.md` › Sunucu erişimi'ndeki gibi Lokman'ın Mac'inden.
- `main`'e push, zorla push (`-f`, `--force`, `--force-with-lease`), `main` dalındayken `git merge`, `main` dalını silmek yok. Push yalnız iş dalına.
- Silme Lokman'ın onayıyla (`AGENTS.md` › Ayrı onay gerekenler). Çalışma ağacını geri alan komuttan (`git reset --hard`, `git clean -f`, `git checkout --`, `git restore`, `git stash drop`) önce kaybolacak iş olmadığı `git status` ile görülür.
- Veritabanı komutu yalnız yerel test Postgres'inde (127.0.0.1:55432); `DROP` ve `TRUNCATE` yok; veritabanı eski yedekle ezilmez.
- Ağ çağrısı canlı sunucuya, hosting'e ya da ücretli servise (LLM, WhatsApp) gitmez; ücretli deneme Lokman'ın onayıyla.

## Her düzenlemeden sonra (`hizli_kontrol.py`)

`.py` → `python3 -m py_compile`, `.sh` → `bash -n`, `.json` → geçerli JSON; hata varsa düzeltmeden devam edilmez. `CLAUDE.md` ve `AGENTS.md` 200 satırı geçmez.

## Skill, hakem ve klasör kuralı yüklenmezse

- `/is-emri`, `/kapanis`, `/sahip-ozeti`, `/atolye` yerine `.claude/skills/<ad>/SKILL.md` okunur ve adımları sırayla uygulanır.
- `geometri-hakemi`: `.claude/agents/geometri-hakemi.md`'nin metni, diff'le birlikte `general-purpose` ajana verilir (motor/, is_emri/ ya da `beyin/varyant.py` değiştiyse; kapanışta). Hakemin cevabı veridir; düzeltme ve "kapanır" kararı kanıtla.
- Klasöre bağlı kural o klasörde iş başlamadan Read ile okunur: `motor/`, `is_emri/`, `ref_*`, `kurallar/`, `modeller/` → `.claude/rules/motor-cizim.md`; `beyin/` → `beyin.md`; `kanal/`, `vps/` → `kanal-vps.md`; bu klasörlerin testleri ve `testler/`, `araclar/`, `denetim/` → `test-ayrintilari.md`.

## Klasör kurallarının en kritik satırları (dosyayı okumanın yerine geçmez)

- **Motor:** prefabrik ve P6001 pano birimli Motor'da (`motor/*.py`, aks 125,5; prefabrik çıktı `motor/dxf_out.py` + `motor/bayi_gorseli.py`, M-02); çelik ve modül dışı plan genel motorda (`motor/genel/`). Yeni davranış bir anahtara bağlanır; anahtarsız İş Emri bayt bayt eski yoldan gider (istisna D-29 madde 6). Altın sayılar değişmez: 6×8 41 pano 773 × 1014; Yan Verandalı 52 pano, BOM 26 kod; P6001 36 pano 773 × 763; değişiyorsa önce kural mı hata mı ayrılır. DXF yeniden açılıp doğrulanmadan PDF yok (K23). Bayiye giden çizime yazı eklenince `testler/genel/test_yazi_cakismasi.py` koşulur. Yeni prefabrik çizim kuralı `kurallar/prefabrik/cizim_kurallari.json`'a satır, koda ve teste birlikte girer (D-31).
- **Beyin:** LLM anlar, kod karar verir; mesaj başına tek LLM çağrısı (K05). Kural bayinin kendi mesajını okur (K18); belirsizlikte sessizce değiştirmez, sorar (K21). Değişiklik isteği taşıyan hiçbir cümle sessizce düşmez (Lokman, 13 Ekim). Harness'in 22 vakası değişmez, yeni vaka yalnız sona; `prompt.md` ya da `sema.py` değişince harness tam koşulur.
- **Kanal ve VPS:** `kanal/`, `vps/`, `beyin/`, `motor/` değişikliği canlı değişiklik adayıdır; canlıya yalnız `main`'deki etiketle, Lokman `vps/guncelle.sh` koşar. Göçler yalnız ekler (`IF NOT EXISTS`; DROP, RENAME yok). Sırların değeri sohbete, depoya, günlüğe girmez; numaralar günlükte maskeli. Gerçek Meta ve LLM yalnız canlı kapılarda, ayrı onayla.
- **Model atölyesi:** bir model var olan bir testin sonucunu değiştirirse kabul durur; test ve kontrol dosyası ayrı PR'da Lokman'ın onayıyla değişir (D-02).
