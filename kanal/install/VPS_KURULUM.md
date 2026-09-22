# Portman — VPS işçisi kurulumu (kanal v1.1)

Mimari: **hosting = kontrol düzlemi** (Meta webhook, kuyruk `state.json`, gönderim, WhatsApp anahtarı, görüşme durumu),
**VPS = üretici** (Beyin + Motor). VPS ajanı hostinge yalnız dışarıdan bağlanır (`developer/kanal_api.php`), hosting VPS'e hiç bağlanmaz.
Ana anahtar: `kanal/settings.json → "worker": "hosting" | "vps" | "off"` (tek düzenlemeyle geri dönüş).

## A. VPS (Lokman, Mac Terminal — bir kez)
1. Natro panelinde sunucunun **IP adresi** ve root parolası: sunucu sayfasında **"Şifre"** satırı (göz simgesi ile görünür) — "Panel Şifresi" değil. Claude'a verilmez.
2. Terminal: `ssh root@IP 'bash -s' < ~/Desktop/"Claude Portman Çalışması"/08_VPS/bootstrap_vps.sh`
   (parolayı ssh sorar; yapıştırınca ekranda görünmez). ~3–5 dk: sistem paketleri, Python venv (ezdxf 1.4.4, PyMuPDF 1.26, shapely, pydantic), `portman` kullanıcısı,
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
- `settings.json → "worker": "vps"` → ajan iş almaya başlar; hosting cron'daki worker.py üretmez, pip/öz-test de çalıştırmaz (yalnız sağlık yazar; v1.1.1).
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

## F. Bilinen notlar
- Natro XCloud sanal CPU'su x86-64-v2 komut setini sunmuyor → NumPy 2.x çalışmaz (`RuntimeError: X86_V2`); betik NumPy 1.26'ya sabitler.
- Betik idempotent: yarıda kesilirse aynı komut yeniden çalıştırılır; eşleşme anahtarı ilk üretimde `/etc/portman/agent.env`'de saklanır ve tekrar gösterilmez.

## G. Güvenlik sınırları (bağımsız denetim 22.09, F01/F02)
- Eşleşme anahtarını bilen taraf: `settings` ile **OpenAI anahtarını** alır (`vps_llm_key_from_hosting` true iken), gerçek iş çekebilir (`claim`) ve o işin
  göndericisine (ya da Patron'a) `result` ile **metin/PDF gönderebilir** (gönderimi hosting tick'i yapar; alıcı = gelen mesajın göndericisi, 24 saat penceresi).
  WhatsApp erişim anahtarını alamaz, keyfi numaraya gönderemez. Anahtar sızarsa: `rm /etc/portman/agent.env` + bootstrap + `api_token.txt` yenile, OpenAI anahtarını da yenile.
- Paket kanalı imzasız: `kanal/package/` dosyalarını yazabilen, VPS'te `portman` kullanıcısıyla kod çalıştırır (sha aynı yerden gelir). İmzalı paket (ed25519) yol haritasında.
- `worker.py` hosting'de `worker != hosting` iken pip/öz-test/iş almaz (v1.1.1); ajan `log` yanıtını denetler, `openai_key` gelmezse süreçteki anahtarı siler.
