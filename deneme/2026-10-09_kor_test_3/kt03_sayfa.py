#!/usr/bin/env python3
"""KT-03 kıyasını okunur tek bir sayfaya (kendi başına HTML dosyası) çevirir.

Sayılar, sınıflar ve açıklamalar `sonuc/KT03_kiyas.json`'dan (`kt03_kiyas.py` çıktısı) okunur; elle yazılmaz. Sorular bu dosyadadır (`SORULAR`) ve
kıyastaki "kural" satırlarıyla denetlenir. Sayfada kişi, bayi ve firma adı, telefon ve fiyat yoktur. Çıktı depoya yazılmaz; Lokman'a dosya olarak verilir.

Kullanım: python kt03_sayfa.py --cikti KT03_kiyas.html --zaman "10 Ekim 2026 01:30"
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA.parent / "2026-10-06_kor_test"))
from kararlar_sayfa import dil          # noqa: E402  (sayfa dili: kişi adı yerine hitap)

SINIF = {"girdi": ("girdi hatamız", "eksik", "projenin belgesinde vardı, yanlış okuduk; düzeltildi"),
         "kural": ("kural eksiği", "bekle", "kuralımız yoktu ya da varsayımımız tutmadı; sizden karar bekliyor"),
         "karar": ("kararınız farklı", "ok", "bugünkü kural (sizin ya da Excel motorunun) o listeden farklı"),
         "elle": ("elle (liste)", "kaynak", "listenin elle hesabı ya da yuvarlaması"),
         "pafta": ("paftadan", "kaynak", "listede paftadan sayılmış; kör testte paftadaki adetler girdi değildi")}
DERE = ["Metal dere", "Dere kapağı", "Dere iniş aparatı", "Dere iniş borusu", "Açık dirsek", "Kapalı dirsek", "İniş kelepçesi", "Dere kelepçesi"]
KISI_OZETLERI = {"8b577ea24803ba5adf679534a5465626f66066c8f3b8f89a48e4657dba209381"}     # mühendisin adı (küçük harf, SHA-256)
BACA = ["Baca borusu", "Baca T'si", "Baca kör tapa", "Baca maşonu", "Baca şapkası"]
# Kural eksiği satırlarının hangi soruya bağlı olduğu (denetlenir: her kural satırı bir soruya bağlı olmalı)
SORULAR = [
    ("Veranda ve sundurmanın tek eğimli panel çatısının kenarları.",
     "Bu listede iki çatının saçağında dere ve iniş var (veranda 2, sundurma 1 iniş; 4 dere kapağı), saçakta özel büküm saçak sacı (3), eğik kenarlarda "
     "sıfır alın sacı (3); kenarlarda Boardex şeridi yok ve veranda ile sundurmanın tavanı çatının saçağıyla birlikte Boardex (7 levha). Kuralımız KT-01'in "
     "müştemilatından: çatı panelli çatıda dere, saçak sacı ve alın sacı yok, kenarlar 10 + 15 cm Boardex. Müştemilat öyle kalsın, veranda ve sundurma bu "
     "listedeki gibi mi olsun? Bir de iniş: paftada ana çatının sundurmanın üstüne düşen iç köşesinde iniş yok (su sundurmaya akıyor), sundurmanın kısa "
     "deresinde tek iniş var. \"Alçak bir çatının üstüne düşen köşeye iniş konmaz\" kural olsun mu?",
     ["Alın sacı (veranda ve sundurma)", "Özel büküm saçak sacı", "Dış cephe Boardex", "Veranda ve sundurma tavanı (Boardex)"] + DERE),
    ("Üretim dosyası yokken kırma uçlarının çatı panelleri.",
     "Üretim dosyası olmayınca çelik ağırlığı motorun ortalamasından çıkıyor ve kırma uçlarının çatı panelleri ayrı satır olmuyor (ağırlıkları makas "
     "satırında). Bu listede çatı panelleri 17: kırma uçlarında 13, veranda ve sundurmada 4 (paftada Ç01–Ç18, Ç10 yok); 5'i 1,2 mm, 312 kg. Paftadaki panel "
     "numaralarından adet sayayım mı?",
     ["Çatı panelleri (1,2 ve 0,8)"]),
    ("Çatı çıkış kapağı.",
     "Planda holde \"çatı çıkış kapağı 90 × 60\" çizili; listede çatı kaplamaları grubunda \"çatı çıkış kapağı (çatı kaplamasıyla uyumlu, özel ölçü)\" 1, "
     "ayrıca acil müdahale kapağı 1 (bizde de 1). \"Planda çatı çıkış kapağı varsa listeye 1 adet\" kural olsun mu?",
     ["Çatı çıkış kapağı"]),
    ("Bacanın içi.",
     "Açıklama 4: \"Baca olacak (karkas ve içi de olacak)\". Listede iki bacaya birer takım: baca borusu (4,3 m), T, kör tapa, maşon, şapka (40 × 40). "
     "\"Bacanın içi de bizdeyse baca başına bu beş kalem\" kural olsun mu? Borunun boyu sabit mi (4,3 m), bacanın boyundan mı?",
     BACA),
    ("Taharet musluğu.",
     "Listenin mekanik tesisat grubunda taharet musluğu 4 (KT-01 ve KT-02 listelerinde yoktu; bu projede bir banyo var). Kaç tane ve neye göre?",
     ["Taharet musluğu 20 mm"]),
    ("140'lık duvarda saçak omegası.",
     "Listede \"180'lik geniş saçak omegası (140'lık duvarlar için)\". Kural: dış duvar 140 ise saçak omegası 180'lik olsun mu? (Adet farkı ayrı: formül kararı.)",
     []),
    ("KT-03'ün tanımı ve çizimleri depoya eklensin mi?",
     "KT-01 ve KT-02'deki gibi: projenin geometrisi (kör ve düzeltilmiş tanım, onları üreten betikler) ve iki yöntemle çizim seti. Ad, telefon ve fiyat içermez.",
     []),
]


def kisi_adi_kaldi(sayfa: str) -> bool:
    """Sayfa Lokman'a "siz" diye hitap eder, mühendis "mühendis" diye geçer. Mühendisin adı bu dosyaya yazılmasın diye özetiyle aranır
    (küçük harfle SHA-256; KT-01 ve KT-02 sayfalarındaki denetimle aynı ad)."""
    kucuk = lambda w: w.replace("I", "ı").replace("İ", "i").lower()
    sozcukler = set(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû]+", sayfa))
    return "Lokman" in sozcukler or any(hashlib.sha256(kucuk(w).encode("utf-8")).hexdigest() in KISI_OZETLERI for w in sozcukler)


def e(s) -> str:
    return html.escape(str(s), quote=True)


def md(s: str) -> str:
    s = re.sub(r"(^|\. )Lokman, ", lambda m: m.group(1) + "Siz, ", s.replace("Lokman'a", "size"))
    s = e(dil(s))
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def n(v) -> str:
    return "—" if v is None else (f"{v:,}".replace(",", " ") if isinstance(v, int) else f"{v:g}".replace(".", ","))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cikti", type=Path, required=True)
    ap.add_argument("--zaman", required=True, help="künyede görünecek tarih ve saat")
    ap.add_argument("--kiyas", type=Path, default=BURADA / "sonuc" / "KT03_kiyas.json")
    a = ap.parse_args()
    k = json.loads(a.kiyas.read_text(encoding="utf-8"))
    if k["denetim_sorunlari"]:
        raise SystemExit("Kıyasta denetim sorunu var; sayfa üretilmez: " + "; ".join(k["denetim_sorunlari"][:3]))
    B, oz, sf, ks = k["birimler"], k["ozet"], k["siniflar"], k["kalan_siniflar"]
    if not ks or "duz_b" not in oz or "ne_olur_b" not in oz:
        raise SystemExit("Kıyasta düzeltilmiş ya da ne olur listesi yok: kt03_kiyas_kos.sh ile üretilmeli.")
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    toplam = oz["kor_b"]["gercek_satir"]
    kural_birim = {b["ad"] for b in B if b["sinif"] == "kural"}
    bagli = {x for _, _, bb in SORULAR for x in bb}
    if kural_birim != bagli:
        raise SystemExit(f"Sorular kıyastaki kural satırlarıyla uyuşmuyor: kıyasta {sorted(kural_birim)}, sorularda {sorted(bagli)}")
    c = k["celik"]
    ne = oz["ne_olur_b"]["ayni"]
    s1 = satir([b for b in B if b["ad"] in SORULAR[0][2]])
    bina = satir([b for b in B if b["sinif"] == "karar" and "bina alanı" in (b["neden"] or "").lower()])     # alana bağlı karar satırları (RYSB, uçlar, inox taş)
    if not 0 < bina < sf["karar"]:
        raise SystemExit(f"Bina alanından karar farkı {bina}: sayfadaki cümle tutmuyor")
    girdi_birim = [b for b in B if b["sinif"] == "girdi"]
    if [b["ad"] for b in girdi_birim] != ["Çatı makas panelleri (1,2 ve 0,8)"] or not all(b["duz_b_ayni"] for b in girdi_birim):
        raise SystemExit("Girdi hataları sayfadaki cümleyle tutmuyor")
    panel = [b for b in B if b["grup"] == B[0]["grup"]]
    panel_ayni, panel_duz = [b for b in panel if b["kor_b_ayni"]], [b for b in panel if b["duz_b_ayni"]]
    ozet = (f'<div><b>{oz["kor_b"]["ayni"]}<small> / {toplam}</small></b><span>Kör liste (dondurulduğu gibi), projenin yapıldığı yöntemle</span></div>'
            f'<div><b>{oz["duz_b"]["ayni"]}<small> / {toplam}</small></b><span>Girdi hatalarım düzeltilince (makas adedi; kurallar aynı)</span></div>'
            f'<div><b>{ne}<small> / {toplam}</small></b><span>Soru 1 ve 2 listedeki gibi cevaplanırsa (denendi; bilgi)</span></div>'
            f'<div><b>{n(round(c["kor_b"]["kg"]))}<small> / {n(round(c["gercek"]["kg"]))} kg</small></b>'
            f'<span>Çelik: bizim (üretim dosyası yok, motorun ortalaması) / gerçek liste</span></div>')
    lejant = "".join(f'<li><span class="rozet {SINIF[t][1]}">{e(SINIF[t][0])}</span> {sf[t]} satır: {e(SINIF[t][2])}</li>' for t in SINIF if sf[t])
    sorular = "".join(f"<li><b>{e(bas)}</b> {md(metin)}</li>" for bas, metin, _ in SORULAR)
    govde, grup = [], None
    for b in B:
        if b["grup"] != grup:
            grup = b["grup"]
            govde.append(f'<tr class="grup"><th colspan="5">{e(grup)}</th></tr>')
        etiket = [f'<span class="rozet {SINIF[b["sinif"]][1]}">{e(SINIF[b["sinif"]][0])}</span>'] if b["sinif"] else ['<span class="rozet cizgili">tuttu</span>']
        if len(b["gercek_satirlar"]) > 1:
            etiket.append(f'<span class="cok">gerçek listede {len(b["gercek_satirlar"])} satır</span>')
        aciklama = "".join(f'<p class="alt"><b>{bas}</b> {md(b[alan])}</p>' for bas, alan in (("Neden:", "neden"), ("Payı:", "pay"), ("Düzeltilmişte kalan:", "kalan")) if b.get(alan))
        hucre = "".join(f'<td class="say{"" if b[x + "_ayni"] or (b[x] is None and x == "kor_a") else " fark"}">{n(b[x])}</td>' for x in ("kor_b", "duz_b", "kor_a"))
        veri = f'data-kor="{int(not b["kor_b_ayni"])}" data-duz="{int(not b["duz_b_ayni"])}" data-tutan="{int(b["kor_b_ayni"])}"'
        govde.append(f'<tr {veri}><td class="kalem"><span class="ad">{e(b["ad"])}</span> {" ".join(etiket)}{aciklama}</td>'
                     f'<td class="say gercek">{n(b["gercek"])}</td>{hucre}</tr>')
    say = {"hepsi": satir(B), "kor": satir([b for b in B if not b["kor_b_ayni"]]), "duz": satir([b for b in B if not b["duz_b_ayni"]]), "tutan": satir([b for b in B if b["kor_b_ayni"]])}
    if say["hepsi"] != toplam or say["kor"] != toplam - oz["kor_b"]["ayni"] or say["duz"] != toplam - oz["duz_b"]["ayni"] or sum(sf.values()) != say["kor"] or sum(ks.values()) != say["duz"]:
        raise SystemExit(f"Sayfadaki sayım kıyasın özetiyle tutmuyor: {say} / {oz}")
    suzgec = "".join(f'<button type="button" data-suz="{x}" aria-pressed="{"true" if x == "hepsi" else "false"}">{e(ad)} <span>{say[x]}</span></button>'
                     for x, ad in (("hepsi", "Hepsi"), ("kor", "Kör listede farklı"), ("duz", "Düzeltilmişte de farklı"), ("tutan", "Tuttu")))
    fazla = "".join(f'<tr><td>{e(z["kalem"])}</td><td class="boyut">{e(z["boyut"])}</td><td class="say">{n(z["adet"])}</td><td>{md(z["neden"])}</td></tr>' for z in k["fazla"]["kor_b"])
    adet_disi = "".join(f"<li>{md(x)}</li>" for x in k["adet_disi"])
    sayfa = SABLON.format(**{"zaman": e(a.zaman), "toplam": toplam, "ozet": ozet, "kor": say["kor"], "lejant": lejant, "hata": k["bizim_hatamiz"],
                             "kural": sf["kural"], "karar": sf["karar"], "s1": s1, "panel": len(panel), "panel_ayni": len(panel_ayni), "panel_duz": len(panel_duz),
                             "sorular": sorular, "fazla": fazla, "suzgec": suzgec, "govde": "".join(govde), "birim": len(B), "adet_disi": adet_disi,
                             "fazla_n": len(k["fazla"]["kor_b"]), "girdi": sf["girdi"], "bina": bina})
    if kisi_adi_kaldi(sayfa):
        raise SystemExit("Sayfada kişi adı kaldı (Lokman ya da mühendisin adı)")
    a.cikti.write_text(sayfa, encoding="utf-8")
    print("yazıldı:", a.cikti, "·", len(sayfa) // 1024, "KB ·", len(B), "birim")
    return 0


SABLON = '''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KT-03 Kör Test</title>
<style>
/* Düzen: tek sütun; üstte özet ve sorular, altında satır satır kıyas. Sayılar eş aralıklı yazıyla sağa hizalı. */
:root {{
  --zemin: #f3f5f6; --kagit: #ffffff; --yazi: #17212b; --soluk: #5b6875; --cizgi: #d5dbe0; --vurgu: #1f5f7a;
  --ok-z: #dff1e6; --ok-y: #1c6b3c; --kay-z: #e3ebf2; --kay-y: #2f4a63; --bek-z: #fdebc8; --bek-y: #7a4d00; --eks-z: #f8d9d6; --eks-y: #8a2118;
  --sans: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--zemin); color: var(--yazi); font-family: var(--sans); font-size: 15px; line-height: 1.5; }}
.sayfa {{ max-width: 1040px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: flex; flex-direction: column; gap: 28px; }}
header {{ display: flex; flex-direction: column; gap: 10px; }}
.kunye {{ font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
h1 {{ font-size: clamp(24px, 4.6vw, 34px); line-height: 1.15; margin: 0; font-weight: 600; text-wrap: balance; }}
.aciklama {{ color: var(--soluk); max-width: 76ch; margin: 0; }}
.ozet {{ display: flex; flex-wrap: wrap; gap: 1px; background: var(--cizgi); border: 1px solid var(--cizgi); }}
.ozet div {{ flex: 1 1 200px; background: var(--kagit); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.ozet b {{ font-family: var(--mono); font-size: 24px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.ozet b small {{ font-size: 13px; color: var(--soluk); font-weight: 400; white-space: nowrap; }}
.ozet span {{ font-size: 12.5px; color: var(--soluk); }}
h2 {{ font-size: 15px; margin: 0 0 10px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }}
section > p {{ margin: 0 0 10px; max-width: 80ch; }}
.kaydir {{ overflow-x: auto; background: var(--kagit); border: 1px solid var(--cizgi); }}
table {{ border-collapse: collapse; width: 100%; min-width: 680px; }}
th, td {{ padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--cizgi); font-size: 13.5px; }}
tbody tr:last-child td {{ border-bottom: 0; }}
thead th {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); font-weight: 500; position: sticky; top: 0; background: var(--kagit); }}
tr.grup th {{ font-size: 12px; letter-spacing: .06em; text-transform: uppercase; background: var(--zemin); color: var(--soluk); }}
.say {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.say {{ font-size: 15px; font-weight: 500; }}
td.say.fark {{ color: var(--eks-y); }}
td.say.gercek {{ background: var(--kay-z); color: var(--kay-y); }}
.boyut {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); white-space: nowrap; }}
.kalem {{ min-width: 300px; }}
.ad {{ font-weight: 600; margin-right: 6px; }}
.alt {{ font-size: 12.5px; color: var(--soluk); max-width: 72ch; margin: 4px 0 0; }}
.alt b {{ color: var(--yazi); font-weight: 500; }}
.rozet {{ display: inline-block; font-size: 11.5px; padding: 1px 8px; border-radius: 10px; white-space: nowrap; font-weight: 500; }}
.rozet.ok {{ background: var(--ok-z); color: var(--ok-y); }}
.rozet.kaynak {{ background: var(--kay-z); color: var(--kay-y); }}
.rozet.bekle {{ background: var(--bek-z); color: var(--bek-y); }}
.rozet.eksik {{ background: var(--eks-z); color: var(--eks-y); }}
.rozet.cizgili {{ border: 1px solid var(--cizgi); color: var(--soluk); }}
.cok {{ font-size: 11.5px; color: var(--soluk); white-space: nowrap; }}
.suzgec {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }}
.suzgec button {{ font: inherit; font-size: 13.5px; padding: 6px 12px; border: 1px solid var(--cizgi); background: var(--kagit); color: var(--yazi); border-radius: 4px; cursor: pointer; }}
.suzgec button span {{ font-family: var(--mono); font-size: 12px; color: var(--soluk); }}
.suzgec button[aria-pressed="true"] {{ background: var(--vurgu); border-color: var(--vurgu); color: var(--kagit); }}
.suzgec button[aria-pressed="true"] span {{ color: inherit; }}
.suzgec button:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
ol.sorular {{ margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 10px; max-width: 86ch; }}
ul.notlar {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; max-width: 86ch; font-size: 14px; }}
.lejant {{ list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; color: var(--soluk); }}
code {{ font-family: var(--mono); font-size: .92em; }}
table.dar {{ min-width: 520px; }}
footer {{ font-size: 12.5px; color: var(--soluk); max-width: 86ch; }}
@media print {{ .suzgec {{ display: none; }} .kaydir {{ overflow: visible; border: 0; }} thead th {{ position: static; }} }}
</style>
</head>
<body>
<div class="sayfa">
<header>
  <div class="kunye">KT-03 · üçüncü kör test · {zaman} · deneme, canlıda değil</div>
  <h1>Üçüncü kör test: kendi listemiz ile gerçek liste</h1>
  <p class="aciklama">80 m² tek kat çelik proje (dış duvar 140 mm, kırma çatı ve kanat, verandanın ve sundurmanın tek eğimli panel çatıları, iki baca; liste 23 Eylül 2026, yeni şablon). Model yalnız montaj paftasından kuruldu (üretim dosyası yoktu: çelik ağırlığı motorun ortalaması, panel adetleri paftadan); liste bugünkü kurallarla (0.17) çıkarıldı ve gerçek liste açılmadan depoya kaydedildi (9 Ekim 23:55; liste 23:56'da açıldı). Gerçek listenin adedi yazılı {toplam} satırı tek tek kıyaslandı. "Aynı" yalnız adedin aynı olmasıdır. Kişi, bayi ve firma adı, fiyat yoktur.</p>
</header>
<div class="ozet">{ozet}</div>
<section>
  <h2>Kör listede farklı {kor} satır</h2>
  <ul class="lejant">{lejant}</ul>
  <p>Bizim hatamız {hata} satır. Girdi hatası {girdi} satır: paftada makas numaraları MK01 ve MK14'ü atlıyor, numaraları kesintisiz sayıp 36 yazdım (34). Kural eksiği {kural} satır: aşağıdaki sorular; bunların {s1}'i tek soruda (veranda ve sundurmanın panel çatısının kenarları). Karar farkı {karar} satır: bugünkü kurallarınız o listeden farklı. Bunların {bina} satırı bina alanından (liste 80 m², kuralımız veranda ve sundurmayla 94); ötekiler vida ve formül kararlarınız ve yöntem B kalemleri. Çelik panel grubunun {panel} biriminin {panel_ayni}'sında adet aynı, makas düzeltilince {panel_duz}; kg motorun ortalaması (bilgi).</p>
</section>
<section>
  <h2>Sizden beklenenler</h2>
  <ol class="sorular">{sorular}</ol>
</section>
<section>
  <h2>Kör listede olup gerçek listede olmayan {fazla_n} satır</h2>
  <div class="kaydir"><table class="dar"><thead><tr><th>Kalem</th><th>Boyut</th><th class="say">Adet</th><th>Neden</th></tr></thead><tbody>{fazla}</tbody></table></div>
</section>
<section>
  <h2>Satır satır</h2>
  <div class="suzgec" role="group" aria-label="Satırları süz">{suzgec}</div>
  <div class="kaydir"><table class="kiyas"><thead><tr><th>Kalem (gerçek listedeki satır)</th><th class="say">Gerçek</th><th class="say">Kör liste</th><th class="say">Düzeltilmiş</th><th class="say">Çelik standardı</th></tr></thead><tbody>{govde}</tbody></table></div>
  <p class="alt">Kör liste ve düzeltilmiş liste projenin yapıldığı yöntemle (tavan omegası ve aşık); çelik standardı (çatı ve tavan paneli) bilgi içindir. Kırmızı sayı: gerçek listeden farklı. "—": o listede kalem yok. Düğmelerdeki sayılar gerçek listenin satırıdır ({birim} tablo satırı, {toplam} gerçek satır).</p>
</section>
<section>
  <h2>Adet dışı farklar</h2>
  <ul class="notlar">{adet_disi}</ul>
</section>
<footer>Kaynak: <code>deneme/2026-10-09_kor_test_3/sonuc/KT03_kiyas.json</code>; sayfa <code>kt03_sayfa.py</code> ile üretilir, elle düzeltilmez. Sınıflar ve nedenler elle yazılmıştır ve hesap çıktısıyla denetlenir (<code>kt03_kiyas.py</code>). Sınır: tek proje; aynı satır sayısı kuralların o listeye benzerliğini gösterir, doğruluğunu değil.</footer>
</div>
<script>
(function () {{
  var dugmeler = document.querySelectorAll(".suzgec button"), satirlar = document.querySelectorAll("table.kiyas tbody tr");
  function suz(anahtar) {{
    var gorunen = null;
    satirlar.forEach(function (tr) {{
      if (tr.classList.contains("grup")) {{ if (gorunen) gorunen.hidden = !gorunen._var; gorunen = tr; tr._var = false; return; }}
      var goster = anahtar === "hepsi" || tr.dataset[anahtar] === "1";
      tr.hidden = !goster;
      if (goster && gorunen) gorunen._var = true;
    }});
    if (gorunen) gorunen.hidden = !gorunen._var;
  }}
  dugmeler.forEach(function (d) {{
    d.addEventListener("click", function () {{
      dugmeler.forEach(function (x) {{ x.setAttribute("aria-pressed", x === d ? "true" : "false"); }});
      suz(d.dataset.suz);
    }});
  }});
}})();
</script>
</body>
</html>
'''


if __name__ == "__main__":
    raise SystemExit(main())
