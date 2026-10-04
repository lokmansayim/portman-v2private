#!/usr/bin/env bash
# PORTMAN · BK-04 kapı 6 · SSH parolalı girişi kapatır (yalnız anahtarla giriş). DEĞİŞİKLİK YAPAR; Lokman'ın onayıyla.
# Mac'ten, İKİNCİ bir terminalde (ilk terminalde açık bir ssh oturumu dururken) Lokman çalıştırır:
#   ssh portman-vps 'PM_ONAY=evet bash -s' < vps/bk04_ssh_sertlestir.sh > bk04_6_ssh.txt 2>&1
# Yaptığı: /etc/ssh/sshd_config.d/00-portman-bk04.conf yazar (ad sırasında ilk; sshd ilk gördüğü değeri kullanır, bu yüzden
# 50-cloud-init.conf gibi dosyaların "PasswordAuthentication yes" satırı etkisiz kalır), sshd -t ile sözdizimini denetler,
# etkin değerleri sshd -T ile gösterir, servisi RELOAD eder (restart değil: açık oturumlar kopmaz).
# Ön koşullar tutmazsa hiçbir şey değişmez: PM_ONAY=evet verilmemişse; root'un yetkili anahtarı yoksa; sshd -t geçmezse.
# Geri alma (açık oturumdan): rm /etc/ssh/sshd_config.d/00-portman-bk04.conf && systemctl reload ssh
# Son çare: Natro panelindeki konsol (VNC) ile giriş.
# Test için: PM_SSHD_DIR, PM_AUTH_KEYS, PM_RELOAD (varsayılan "systemctl reload ssh"), PM_SSHD_T (varsayılan "sshd -T").
set -u
PM_SSHD_DIR="${PM_SSHD_DIR:-/etc/ssh/sshd_config.d}"
PM_AUTH_KEYS="${PM_AUTH_KEYS:-/root/.ssh/authorized_keys}"
PM_RELOAD="${PM_RELOAD:-systemctl reload ssh}"
PM_SSHD_T="${PM_SSHD_T:-sshd -T}"
DOSYA="$PM_SSHD_DIR/00-portman-bk04.conf"
echo "== BK-04 kapı 6 · SSH sertleştirme · $(date '+%Y-%m-%d %H:%M:%S %Z') · $(hostname 2>/dev/null)"

[[ "${PM_ONAY:-}" == "evet" ]] || { echo "DUR: PM_ONAY=evet verilmedi; hiçbir şey değişmedi. Komut: ssh portman-vps 'PM_ONAY=evet bash -s' < vps/bk04_ssh_sertlestir.sh"; exit 1; }
if ! grep -qE '^(ssh-|ecdsa-|sk-)' "$PM_AUTH_KEYS" 2>/dev/null; then
  echo "DUR: $PM_AUTH_KEYS içinde yetkili anahtar yok; parolalı giriş kapatılırsa root giremez. Önce Mac'in anahtarını ekle (ssh-copy-id)."; exit 1
fi
if [[ -e "$DOSYA" ]]; then
  echo "DUR: $DOSYA zaten var; önce içeriğine bak (cat), gerekiyorsa sil ve yeniden koş."; exit 1
fi
mkdir -p "$PM_SSHD_DIR" || { echo "DUR: $PM_SSHD_DIR açılamadı"; exit 1; }
echo "-- şu anki etkin değerler"
$PM_SSHD_T 2>/dev/null | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication) ' | sed 's/^/   /'

umask 022
cat > "$DOSYA" <<'CONF'
# PORTMAN BK-04: parolalı giriş kapalı, yalnız anahtarla giriş. Ad sırasında ilk dosya olduğu için sshd'nin ilk gördüğü değer budur.
# Geri alma: bu dosyayı sil ve "systemctl reload ssh".
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
CONF
chmod 644 "$DOSYA"
echo "-- yazıldı: $DOSYA"

if command -v sshd >/dev/null 2>&1 && ! sshd -t 2>/tmp/bk04_sshd_t.txt; then
  echo "DUR: sshd -t geçmedi; dosya geri alındı:"; sed 's/^/   /' /tmp/bk04_sshd_t.txt; rm -f "$DOSYA"; exit 1
fi
echo "-- yeni etkin değerler (uygulanmadan önce, sshd -T)"
$PM_SSHD_T 2>/dev/null | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication) ' | sed 's/^/   /'
if $PM_SSHD_T 2>/dev/null | grep -qE '^passwordauthentication yes'; then
  echo "DUR: parolalı giriş hâlâ 'yes' görünüyor (başka bir dosya önce okunuyor olabilir). Dosya geri alındı; drop-in listesini incele."
  rm -f "$DOSYA"; exit 1
fi

if $PM_RELOAD; then
  echo "-- ssh servisi yeniden yüklendi (reload); açık oturumlar korunur"
else
  echo "DUR: reload başarısız; dosya geri alındı"; rm -f "$DOSYA"; exit 1
fi
echo "-- ŞİMDİ: bu oturumu KAPATMADAN ikinci terminalde iki deneme yap:"
echo "     ssh -o PasswordAuthentication=no -o PreferredAuthentications=publickey portman-vps 'echo anahtar-ok'   → anahtar-ok yazmalı"
echo "     ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password portman-vps                     → Permission denied (publickey) demeli"
echo "   İkisi de böyleyse kapı 6 tamam. Değilse geri alma: rm $DOSYA && $PM_RELOAD"
echo "== bitti"
