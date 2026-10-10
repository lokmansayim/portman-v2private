#!/usr/bin/env bash
# Ç8801 (katalog modeli): kural kitabının yeni bir modelde sınanması (Lokman, 10 Ekim 2026 11:39: "istersen testini bir sonraki model olan ç8801 de yap").
# Tanımdan (tanim/C8801.json; tanim/c8801_tanim_uret.py üretir) güncel kural setiyle (kurallar/liste/kurallar.json):
#   sonuc/C8801_girdi.json, sonuc/C8801_yukleme.{json,md}   yükleme listesi (çelik standardı: yöntem A, çatı ve tavan paneli)
#   sonuc/C8801_C8201_yan_yana.md                          aynı kurallarla Ç8201'in listesiyle yan yana (sağlama)
#   cizimler/C8801_A/                                       çizim seti (plan, çatı planı, dört görünüş, pafta, IFC, perspektifler)
# Gerçek bir Ç8801 listesi yok: liste Lokman'ın incelemesi içindir. Çatı biçimi ve eğimler varsayımdır (README).
# Geçici dosya yazmaz, hiçbir dosyayı silmez. Kullanım: bash c8801_kos.sh [python]
set -euo pipefail
PY=${1:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR      # güncel kural seti: ortamda başka bir set seçili kalmış olmasın
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
mkdir -p sonuc cizimler/C8801_A
"$PY" "$G" tanim/C8801.json --dosya sonuc/C8801_girdi.json --uzerine-yaz \
    --kaynak "Yapı Tanımı 0.5 (Ç8801 katalog modeli: plan arşivdeki DWG'den, çatı katalog görsellerinden; çatı varsayım)" > /dev/null
"$PY" "$Y" sonuc/C8801_girdi.json --cikti sonuc/C8801_yukleme.json --md sonuc/C8801_yukleme.md > /dev/null
"$PY" c8801_yan_yana.py ../2026-10-03_yukleme/sonuc/C8201_yukleme_taslak.json sonuc/C8801_yukleme.json --md sonuc/C8801_C8201_yan_yana.md > /dev/null
bash ../2026-10-06_kor_test/cizim_seti_kos.sh tanim/C8801.json cizimler/C8801_A "$PY" --yontem panel
echo "Ç8801: liste sonuc/C8801_yukleme.{json,md}, yan yana tablo sonuc/C8801_C8201_yan_yana.md, çizim seti cizimler/C8801_A/"
