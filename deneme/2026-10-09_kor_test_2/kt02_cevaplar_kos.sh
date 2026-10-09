#!/usr/bin/env bash
# KT-02, Lokman'ın 9 Ekim 2026 22:22 cevaplarından sonra: güncel kural setiyle (kurallar.json; 0.16 ve sonrası) düzeltilmiş tanımdan iki liste ve
# gerçek listeyle tablo (`sonuc/KT02_cevaplar_*`). Cevaplar: 1,5 mm profil 2,07 kg/m (kural seti 0.16); açık sundurma bina alanına girer (hesap zaten
# öyleydi); veranda korkuluğunun iç yüzü de kaplanır (malzemesi soruldu; kural değişmedi); tanım ve çizimler depoda (`tanim/`, `cizimler/`).
# Satır notları: `kt02_farklar.json` + `kt02_cevaplar_notlari.json` (üstüne yazar; kör listenin sınıfları değişmez).
# 22:05 kıyasının kendisi kt02_kiyas_kos.sh ile (kural seti 0.15). Geçici dosya yazmaz, hiçbir dosyayı silmez.
# Kullanım: bash kt02_cevaplar_kos.sh tanim/KT02_duzeltilmis.json [python]   Çıkış kodu: denetim sorunu varsa 1.
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt02_cevaplar_kos.sh tanim/KT02_duzeltilmis.json [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR      # güncel kural seti (kurallar.json): ortamda başka bir set seçili kalmış olmasın
"$PY" -c 'import json, sys; t = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if t.get("duzeltmeler") else "Bu tanımda `duzeltmeler` alanı yok: düzeltilmiş tanımla koşulur.")' "$T"
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (ikinci kör test projesi; montaj paftası ve üretim dosyasından; kıyastan sonra düzeltildi; Lokman'ın 9 Ekim 22:22 cevaplarından sonra)"
"$PY" "$G" "$T" --dosya sonuc/KT02_cevaplar_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" "$G" "$T" --yontem panel --dosya sonuc/KT02_cevaplar_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in B A; do
  "$PY" "$Y" "sonuc/KT02_cevaplar_${X}_girdi.json" --elektrik-sayimi sonuc/KT02_pafta_sayimi.json \
      --cikti "sonuc/KT02_cevaplar_${X}_yukleme.json" --md "sonuc/KT02_cevaplar_${X}_yukleme.md" > /dev/null
done
"$PY" kt02_kiyas.py --kor-b sonuc/KT02_B_yukleme.json --kor-a sonuc/KT02_A_yukleme.json \
    --duz-b sonuc/KT02_cevaplar_B_yukleme.json --duz-a sonuc/KT02_cevaplar_A_yukleme.json --ek-notlar kt02_cevaplar_notlari.json \
    --md sonuc/KT02_cevaplar_kiyas.md --json sonuc/KT02_cevaplar_kiyas.json
