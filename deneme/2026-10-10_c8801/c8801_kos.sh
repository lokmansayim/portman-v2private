#!/usr/bin/env bash
# Ç8801 (katalog modeli): kural kitabının yeni bir modelde sınanması (Lokman, 10 Ekim 2026 11:39: "istersen testini bir sonraki model olan ç8801 de yap").
# Çatı: Lokman, 10 Ekim 14:46: katalogdaki model "2. versiyon"; üç çatı da olur (README). Tanımlar tanim/c8801_tanim_uret.py ile üretilir:
#   tanim/C8801.json (katalog), tanim/C8801K.json (varyant K: doğu ucu kırma), tanim/C8801L.json (varyant L: kanadın mahyası boydan boya).
# Güncel kural setiyle (kurallar/liste/kurallar.json), her biri için:
#   sonuc/<KOD>_girdi.json, sonuc/<KOD>_yukleme.{json,md}   yükleme listesi (çelik standardı: yöntem A, çatı ve tavan paneli)
#   cizimler/<KOD>_A/                                       çizim seti (plan, çatı planı, dört görünüş, pafta, IFC, perspektifler)
# Ayrıca: sonuc/C8801_C8201_yan_yana.md (katalog ile Ç8201, aynı kurallarla; sağlama) ve sonuc/C8801_cati_varyantlari.md (üç çatının farklı satırları).
# Gerçek bir Ç8801 listesi yok: listeler Lokman'ın incelemesi içindir. Geçici dosya yazmaz, hiçbir dosyayı silmez. Kullanım: bash c8801_kos.sh [python]
set -euo pipefail
PY=${1:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR      # güncel kural seti: ortamda başka bir set seçili kalmış olmasın
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
mkdir -p sonuc
for KOD in C8801 C8801K C8801L; do
    case $KOD in
        C8801) KAYNAK="katalog çatısı (Lokman, 10 Ekim 2026: 2. versiyon)" ;;
        C8801K) KAYNAK="çatı varyantı K (doğu ucu kırma)" ;;
        C8801L) KAYNAK="çatı varyantı L (kanadın mahyası boydan boya)" ;;
    esac
    "$PY" "$G" tanim/$KOD.json --dosya sonuc/${KOD}_girdi.json --uzerine-yaz \
        --kaynak "Yapı Tanımı 0.5 (Ç8801 katalog modeli: plan arşivdeki DWG'den; $KAYNAK)" > /dev/null
    "$PY" "$Y" sonuc/${KOD}_girdi.json --cikti sonuc/${KOD}_yukleme.json --md sonuc/${KOD}_yukleme.md > /dev/null
    mkdir -p cizimler/${KOD}_A
    bash ../2026-10-06_kor_test/cizim_seti_kos.sh tanim/$KOD.json cizimler/${KOD}_A "$PY" --yontem panel
done
"$PY" c8801_yan_yana.py ../2026-10-03_yukleme/sonuc/C8201_yukleme_taslak.json sonuc/C8801_yukleme.json --md sonuc/C8801_C8201_yan_yana.md > /dev/null
"$PY" c8801_varyantlar.py sonuc/C8801_yukleme.json sonuc/C8801K_yukleme.json sonuc/C8801L_yukleme.json --md sonuc/C8801_cati_varyantlari.md
echo "Ç8801: listeler sonuc/<KOD>_yukleme.{json,md}, çizim setleri cizimler/<KOD>_A/ (KOD: C8801 katalog, C8801K, C8801L); tablolar sonuc/C8801_C8201_yan_yana.md, sonuc/C8801_cati_varyantlari.md"
