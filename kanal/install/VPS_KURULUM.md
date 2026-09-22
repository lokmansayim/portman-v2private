# Portman — VPS işçisi kurulumu (kanal v1.1)

Mimari: **hosting = kontrol düzlemi** (Meta webhook, kuyruk `state.json`, gönderim, WhatsApp anahtarı, görüşme durumu),
**VPS = üretici** (Beyin + Motor). VPS ajanı hostinge yalnız dışarıdan bağlanır (`developer/kanal_api.php`), hosting VPS'e hiç bağlanmaz.
Ana anahtar: `kanal/settings.json → "worker": "hosting" | "vps" | "off"` (tek düzenlemeyle geri dönüş).

## A. VPS (Lokman, Mac Terminal — bir kez)
1. Natro panelinde sunucunun **IP adresi** ve root parolası (Claude'a verilmez).
2. Terminal: `ssh root@IP 'bash -s' < ~/Desktop/"Claude Portman Çalışması"/08_VPS/bootstrap_vps.sh`
   (parolayı ssh sorar). ~3–5 dk: sistem paketleri, Python venv (ezdxf 1.4.4, PyMuPDF 1.26, shapely, pydantic), `portman` kullanıcısı,
   `portman-agent` systemd servisi, ufw (yalnız SSH), fail2ban, saat dilimi.
3. Betiğin sonunda yazan **EŞLEŞME ANAHTARI**'nı kopyala (bir kez gösterilir; sohbete yazma).
4. Kontrol: `systemctl status portman-agent` → active; `journalctl -u portman-agent -n 20` → "paket yok; … bekleniyor" (normal, eşleşme öncesi).

## B. Hosting (DirectAdmin dosya yöneticisi)
1. `portman_app/kanal/` içine **yeni sürüm paketi** aç (api.php, worker.py v1.1; mevcut settings/state/durum korunur).
2. `portman_app/kanal/package/` oluştur → `current.zip` + `current.sha256` + `SURUM.txt` yükle (vps/build/ içinden).
3. `portman_app/kanal/api_token.txt` oluştur → içine adım A.3'teki anahtarı tek satır yapıştır (Lokman yapıştırır).
4. `public_html/developer/kanal_api.php` ← `install/kanal_api.candidate.php` (yeni dosya; webhook.php'ye dokunulmaz).
5. Doğrulama (tarayıcıdan): `https://portatifev.com/developer/kanal_api.php?op=settings` → **401** (anahtarsız) — doğru davranış.
   Ajan bağlanınca `kanal/vps-health.json` oluşur (60 s içinde) ve `kanal/vps.log` akar.

## C. Geçiş (kill switch)
- `settings.json → "worker": "vps"` → ajan iş almaya başlar; hosting cron'daki worker.py üretmez (yalnız sağlık yazar).
- Geri: `"worker": "hosting"`. Tamamen durdurmak: `"enabled": false`.
- Aynı anda iki üretici asla çalışmaz (claim yalnız `worker == vps` iken iş verir; hosting worker.py `worker == hosting` iken).

## D. İşleyiş
- Ajan 4 s'de bir `claim`; iş varsa LLM (OpenAI anahtarı hostingten HTTPS ile alınır, VPS diskine yazılmaz) + Motor; sonuç `result` ile
  hostinge (metin satırları + PDF dosyası projects/… altına + görüşme durumu). Gönderimi yine hosting cron tick'i yapar.
- Paket güncelleme: `kanal/package/current.zip` değişince ajan sha'yı görür, indirir, doğrular, kendini yeniden başlatır, öz-testi koşar
  (sonuç `vps-health.json → self_test`).
- Günlük: `kanal/vps.log` (hosting), `/opt/portman/logs/agent.log` ve `journalctl -u portman-agent` (VPS).

## E. Geri alma
`worker: hosting` (tek düzenleme) → VPS devre dışı. VPS'i kapatmak: `systemctl disable --now portman-agent`.
`developer/kanal_api.php` silinirse API kapanır; webhook/gönderim etkilenmez.
