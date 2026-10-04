#!/usr/bin/env bash
# PORTMAN · BK-05 · VPS'teki geçici kopyaların (İE-02 §7 A7, A8) temizliği. Varsayılan KURU KOŞU: yalnız listeler, silmez.
# Mac'ten Lokman çalıştırır:
#   ssh portman-vps 'bash -s' < vps/bk05_gecici_temizle.sh > bk05_1_kuru.txt 2>&1          # kuru koşu: ne silinecek, yerine kalan var mı
#   ssh portman-vps 'PM_SIL=evet bash -s' < vps/bk05_gecici_temizle.sh > bk05_2_sil.txt 2>&1   # silme (Lokman'ın onayıyla)
# Silinecekler (yalnız bu ikisi; başka hiçbir yol):
#   A7  /var/tmp/portman-gecis/           F'de hosting'ten taşınan state.json ve durum/ (içe aktarma 29.09'da doğrulandı)
#   A8  /root/portman-migration-staging/  Codex'in Opus geçiş klasörü (canlı yedek kopyaları)
# Ön koşul: yerine kalan yedek VPS'te var ve boş değil: /var/backups/portman/opt-portman-ie02-f-20260929.tgz (A7 için).
# A8'in yedeği Mac'tedir (19_Devir_Opus/yedek/); betik bunu denetleyemez, kuru koşuda hatırlatır.
# Yazdırmaz: dosya içeriği, numara, anahtar. Yalnız yol, dosya sayısı, boyut ve özet (sha256) yazılır.
# Test için: PM_A7, PM_A8, PM_YEDEK.
set -u
A7="${PM_A7:-/var/tmp/portman-gecis}"
A8="${PM_A8:-/root/portman-migration-staging}"
YEDEK="${PM_YEDEK:-/var/backups/portman/opt-portman-ie02-f-20260929.tgz}"
echo "== BK-05 geçici kopya temizliği · $(date '+%Y-%m-%d %H:%M:%S %Z') · $(hostname 2>/dev/null) · kip: ${PM_SIL:-kuru koşu}"

ozet() { # yol → "dosya N · boyut" ya da "yok"
  if [[ -d "$1" ]]; then echo "dosya $(find "$1" -type f 2>/dev/null | wc -l) · $(du -sh "$1" 2>/dev/null | cut -f1)"; elif [[ -e "$1" ]]; then echo "dosya 1 · $(du -sh "$1" 2>/dev/null | cut -f1)"; else echo "yok"; fi; }

echo "-- yerine kalan yedek (A7 için): $YEDEK"
if [[ -s "$YEDEK" ]]; then
  echo "   var · $(du -sh "$YEDEK" | cut -f1) · sha256 $(sha256sum "$YEDEK" | cut -c1-12)…"
  YEDEK_OK=1
else
  echo "   YOK ya da boş — A7 silinmez"; YEDEK_OK=0
fi
echo "-- A7 $A7: $(ozet "$A7")"
echo "-- A8 $A8: $(ozet "$A8")"
echo "   hatırlatma: A8'in yedeği Mac'te 19_Devir_Opus/yedek/ altında olmalı (betik Mac'i göremez)."

if [[ "${PM_SIL:-}" != "evet" ]]; then
  echo "== kuru koşu bitti; hiçbir şey silinmedi. Silmek için: ssh portman-vps 'PM_SIL=evet bash -s' < vps/bk05_gecici_temizle.sh"
  exit 0
fi

for yol in "$A7" "$A8"; do
  case "$yol" in /var/tmp/portman-gecis|/root/portman-migration-staging|/tmp/*) ;;  # yalnız beklenen yollar (ya da test için /tmp)
    *) echo "DUR: beklenmeyen yol ($yol); hiçbir şey silinmedi"; exit 1 ;; esac
done
if [[ -e "$A7" && $YEDEK_OK -ne 1 ]]; then echo "DUR: A7 için yedek yok; silinmedi"; exit 1; fi
for yol in "$A7" "$A8"; do
  if [[ -e "$yol" ]]; then rm -rf -- "$yol" && echo "-- silindi: $yol" || echo "-- SİLİNEMEDİ: $yol"; else echo "-- zaten yok: $yol"; fi
done
echo "-- sonra: A7 $(ozet "$A7") · A8 $(ozet "$A8")"
echo "== bitti"
