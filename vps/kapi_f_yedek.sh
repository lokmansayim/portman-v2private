#!/usr/bin/env bash
# PORTMAN · Kapı F.4 (İE-02): VPS'in geçiş öncesi yedeği. Yalnız /var/backups/portman altına YENİ bir arşiv yazar; başka hiçbir
# şeyi değiştirmez, hiçbir şeyi silmez. Arşiv: /opt/portman'ın data/ (konuşma kopyaları, projeler, öz-test), app/ (kurulu paket)
# ve agent.py'si. /etc/portman (anahtarlar) arşive GİRMEZ.
#   ssh portman-vps 'bash -s' < kapi_f_yedek.sh > 4_vps_yedek.txt
# Sonra Mac'e:  scp portman-vps:/var/backups/portman/opt-portman-ie02-f-20260929.tgz yedek/
# Test için: PM_HOME, PM_YEDEK, PM_AD.
set -u
PM_HOME="${PM_HOME:-/opt/portman}"; YEDEK="${PM_YEDEK:-/var/backups/portman}"; AD="${PM_AD:-opt-portman-ie02-f-20260929.tgz}"
echo "== Kapı F.4 · VPS yedeği · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
[ -e "$YEDEK/$AD" ] && { echo "DUR: $YEDEK/$AD zaten var; üzerine yazılmaz. (Özeti: $(sha256sum "$YEDEK/$AD" | cut -d' ' -f1))"; exit 1; }
[ -d "$YEDEK" ] || install -d -m 700 "$YEDEK"         # D'de postgres:postgres 700 kuruldu; varsa dokunulmaz
echo "   kaynak boyutu: $(du -sh "$PM_HOME/data" "$PM_HOME/app" 2>/dev/null | awk '{print $2 " " $1}' | tr '\n' ' ')"
tar czf "$YEDEK/$AD.yarim" -C "$PM_HOME" data app agent.py || { echo "DUR: arşiv yazılamadı (yarım dosya silinmedi: $YEDEK/$AD.yarim)"; exit 1; }
chmod 600 "$YEDEK/$AD.yarim" && mv "$YEDEK/$AD.yarim" "$YEDEK/$AD"
echo "   arşiv: $YEDEK/$AD · $(stat -c '%s' "$YEDEK/$AD") B · $(stat -c '%U:%G %a' "$YEDEK/$AD")"
echo "   sha256: $(sha256sum "$YEDEK/$AD" | cut -d' ' -f1)"
echo "   içerik: $(tar tzf "$YEDEK/$AD" | wc -l) girdi · durum/ $(tar tzf "$YEDEK/$AD" | grep -c '^data/durum/.*\.json$') konuşma · projects/ $(tar tzf "$YEDEK/$AD" | grep -c '^data/projects/.*\.pdf$') PDF · agent.py $(tar tzf "$YEDEK/$AD" | grep -cx 'agent.py')"
echo "   arşivde anahtar dosyası (agent.env/pg.env): $(tar tzf "$YEDEK/$AD" | grep -cE '(agent|pg)\.env$')"
echo "== bitti"
