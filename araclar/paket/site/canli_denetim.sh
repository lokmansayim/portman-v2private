#!/usr/bin/env bash
# İE-41 · yayındaki rehber sitesini kurulan paketle kıyaslar (Lokman'ın Mac'inden; sunucuya bağlanmaz, yalnız HTTPS ile okur).
#   bash canli_denetim.sh <paketin SHA256SUMS dosyası> [https://rehber.portatifev.com] > rehber_canli_denetim.txt 2>&1
# Paketteki her dosya sitedeki adresinden indirilir ve sha256'sı paketteki satırla kıyaslanır. Ayrıca: açılış ve her rehber 200,
# SHA256SUMS 404 (nginx gizler), bilinmeyen yol 404. Son satır "SONUÇ: site paketle aynı" ya da "SONUÇ: FARK VAR (n)".
set -uo pipefail
SUMS="${1:?kullanım: canli_denetim.sh <SHA256SUMS> [taban adres]}"
TABAN="${2:-https://rehber.portatifev.com}"
TABAN="${TABAN%/}"
[ -f "$SUMS" ] || { echo "SHA256SUMS yok: $SUMS"; exit 2; }
command -v curl >/dev/null || { echo "curl yok"; exit 2; }
if command -v sha256sum >/dev/null; then OZET() { sha256sum | cut -d' ' -f1; }; else OZET() { shasum -a 256 | cut -d' ' -f1; }; fi
echo "== rehber sitesi canlı denetimi · $(date -u '+%Y-%m-%d %H:%M:%S UTC') · $TABAN · paket listesi $(wc -l < "$SUMS" | tr -d ' ') dosya"
fark=0; tamam=0
while read -r beklenen yol; do
  [ -n "$yol" ] || continue
  gelen=$(curl -fsS -m 60 "$TABAN/$yol" | OZET) || gelen="indirilemedi"
  if [ "$gelen" = "$beklenen" ]; then tamam=$((tamam + 1)); else fark=$((fark + 1)); echo "   FARK: $yol (beklenen ${beklenen:0:16}…, gelen ${gelen:0:16}…)"; fi
done < "$SUMS"
echo "   dosyalar: $tamam aynı, $fark farklı"
kod() { curl -s -o /dev/null -m 30 -w '%{http_code}' "$1"; }
for yol in "" $(awk '{print $2}' "$SUMS" | grep '/index.html$' | sed 's#index.html$##'); do
  k=$(kod "$TABAN/$yol"); echo "   $TABAN/$yol → $k"; [ "$k" = 200 ] || fark=$((fark + 1))
done
for yol in SHA256SUMS yok-boyle-bir-yol/; do
  k=$(kod "$TABAN/$yol"); echo "   $TABAN/$yol → $k (404 beklenir)"; [ "$k" = 404 ] || fark=$((fark + 1))
done
if [ "$fark" = 0 ]; then echo "SONUÇ: site paketle aynı"; else echo "SONUÇ: FARK VAR ($fark)"; exit 1; fi
