#!/usr/bin/env python3
"""Kör test kıyasını okunur tek bir sayfaya (kendi başına HTML dosyası) çevirir.

Sayılar ve satır açıklamaları `sonuc/KT01_kiyas.json`'dan (`kiyas.py` çıktısı), karar tablosu, hata tablosu ve sorular rapordan
(`docs/raporlar/2026-10-07_Kor_Test_KT01.md`) okunur; elle yazılmaz. Önce `kiyas_kos.sh` koşulmalı.
Sayfada kişi, bayi ve firma adı, telefon ve fiyat yoktur (kaynakları da içermez). Çıktı depoya yazılmaz; Lokman'a dosya olarak verilir.

Kullanım:
    python kiyas_sayfa.py --cikti /tmp/KT01_kiyas.html --zaman "7 Ekim 2026 03:30"
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

BURADA = Path(__file__).resolve().parent
RAPOR = BURADA.parents[1] / "docs" / "raporlar" / "2026-10-07_Kor_Test_KT01.md"
LISTELER = [("kor", "Kör"), ("duzeltilmis", "Düzeltilmiş"), ("sablon", "+ 2026"), ("pafta", "+ pafta")]
SINIF = {"girdi": ("girdi hatası", "eksik"), "kural": ("kural hatası", "eksik"), "karar": ("karar farkı", "bekle"), "elle": ("elle (liste)", "kaynak"),
         "pafta": ("paftadan", "kaynak")}
KALAN = {"elle": "kalan fark: listede elle", "ölçü": "kalan fark: ölçünün yeri", "soru": "kalan fark: soru"}


def e(s) -> str:
    return html.escape(str(s), quote=True)


def md(s: str) -> str:
    """Rapor hücresindeki satır içi biçim: **kalın** ve `kod`."""
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def n(v) -> str:
    return "—" if v is None else (f"{v:,}".replace(",", " ") if isinstance(v, int) else str(v).replace(".", ","))


def bolum(metin: str, baslik_no: int) -> str:
    """Raporun `## <no>. …` başlıklı bölümünün gövdesi."""
    m = re.search(rf"^## {baslik_no}\. .*$", metin, re.M)
    if not m:
        raise SystemExit(f"Raporda {baslik_no}. bölüm bulunamadı.")
    son = re.search(r"^## ", metin[m.end():], re.M)
    return metin[m.end():m.end() + son.start() if son else len(metin)].strip()


def tablo(govde: str) -> tuple[list[str], list[list[str]]]:
    satirlar = [x for x in govde.split("\n") if x.startswith("|")]
    hucre = lambda x: [h.strip() for h in x.strip().strip("|").split("|")]
    return hucre(satirlar[0]), [hucre(x) for x in satirlar[2:]]


def liste(govde: str) -> list[str]:
    return [re.sub(r"^\d+\.\s+", "", x) for x in govde.split("\n") if re.match(r"^\d+\.\s", x)]


def html_tablo(baslik: list[str], satirlar: list[list[str]], sinif: str = "") -> str:
    return (f'<div class="kaydir"><table class="{sinif}"><thead><tr>' + "".join(f"<th>{md(h)}</th>" for h in baslik) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{md(h)}</td>" for h in s) + "</tr>" for s in satirlar) + "</tbody></table></div>")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cikti", type=Path, required=True)
    ap.add_argument("--zaman", required=True, help="künyede görünecek tarih ve saat")
    ap.add_argument("--kiyas", type=Path, default=BURADA / "sonuc" / "KT01_kiyas.json")
    ap.add_argument("--rapor", type=Path, default=RAPOR)
    a = ap.parse_args()
    k = json.loads(a.kiyas.read_text(encoding="utf-8"))
    rapor = a.rapor.read_text(encoding="utf-8")
    B, oz, bz, ck = k["birimler"], k["ozet"], k["bizim_hatamiz"], k["celik_kg"]
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    toplam = oz["kor"]["gercek_satir"]

    ozet = "".join(f'<div><b>{oz[x]["ayni"]}<small> / {toplam}</small></b><span>{e(ad)}</span></div>' for x, ad in
                   (("kor", "Kör liste: gerçek liste açılmadan önce"), ("duzeltilmis", "Düzeltilmiş: yalnız bizim hatalarımız"),
                    ("sablon", "+ Eylül 2026 uygulaması (karar bekliyor)"), ("pafta", "+ elektrik ve iniş paftadan")))
    ozet += (f'<div><b>{n(round(ck["duzeltilmis"]))}<small> / {n(round(ck["gercek"]))} kg</small></b><span>Çelik: düzeltilmiş / gerçek '
             f'(kör listede {n(round(ck["kor"]))})</span></div>')

    # satır satır tablo
    govde, grup = [], None
    for b in B:
        if b["grup"] != grup:
            grup = b["grup"]
            govde.append(f'<tr class="grup"><th colspan="{len(LISTELER) + 3}">{e(grup)}</th></tr>')
        son_farkli = not b["pafta_ayni"]
        etiket = []
        if b["sinif"]:
            ad, renk = SINIF[b["sinif"]]
            etiket.append(f'<span class="rozet {renk}">{e(ad)}</span>')
        if b.get("pay"):
            etiket.append('<span class="rozet eksik">bizim payımız</span>')
        if b.get("not"):
            etiket.append('<span class="rozet bekle">tesadüf ya da eşik</span>')
        if not b["sinif"] and not b.get("not"):
            etiket.append('<span class="rozet ok">tutuyor</span>')
        if son_farkli:
            etiket.append(f'<span class="rozet cizgili">{e(KALAN[b["kalan_turu"]])}</span>')
        if len(b["gercek_satirlar"]) > 1:
            etiket.append(f'<span class="cok">gerçek listede {len(b["gercek_satirlar"])} satır</span>')
        aciklama = "".join(f'<p class="alt"><b>{e(bas)}</b> {e(b[alan])}</p>' for bas, alan in
                           (("Neden:", "neden"), ("Bizim payımız:", "pay"), ("Yapılan:", "yapilan"), ("Kalan fark:", "kalan"), ("Not:", "not"), ("Bilgi:", "bilgi")) if b.get(alan))
        hucre = "".join(f'<td class="say{"" if b[x + "_ayni"] else " fark"}">{n(b[x])}</td>' for x, _ in LISTELER)
        veri = (f'data-bizim="{int(b["sinif"] in ("girdi", "kural") or bool(b.get("pay")))}" data-karar="{int(b["sinif"] == "karar")}" '
                f'data-kalan="{int(son_farkli)}" data-tutan="{int(b["kor_ayni"])}"')
        govde.append(f'<tr {veri}><td class="kalem"><span class="ad">{e(b["ad"])}</span> {" ".join(etiket)}{aciklama}</td>'
                     f'<td class="say gercek">{n(b["gercek"])}</td>{hucre}</tr>')
    satir_tablo = ('<div class="kaydir"><table class="kiyas"><thead><tr><th>Kalem (gerçek listedeki satır)</th><th class="say">Gerçek</th>'
                   + "".join(f'<th class="say">{e(ad)}</th>' for _, ad in LISTELER) + "</tr></thead><tbody>" + "".join(govde) + "</tbody></table></div>")
    # düğmelerdeki sayılar gerçek listenin satırıdır (özetteki sayılarla aynı birim); bir tablo satırı birden çok gerçek satırı karşılayabilir
    say = {"hepsi": satir(B), "kalan": satir([b for b in B if not b["pafta_ayni"]]), "bizim": satir([b for b in B if b["sinif"] in ("girdi", "kural") or b.get("pay")]),
           "karar": satir([b for b in B if b["sinif"] == "karar"]), "tutan": satir([b for b in B if b["kor_ayni"]])}
    if say["hepsi"] != toplam or say["kalan"] != oz["pafta"]["farkli"] or say["tutan"] != oz["kor"]["ayni"] or say["bizim"] != bz["satir"] + bz["payimiz_olan"]:
        raise SystemExit(f"Sayfadaki sayım kıyasın özetiyle tutmuyor: {say} / {oz} / {bz}")
    suzgec = "".join(f'<button type="button" data-suz="{anahtar}" aria-pressed="{"true" if anahtar == "hepsi" else "false"}">{e(ad)} <span>{say[anahtar]}</span></button>'
                     for anahtar, ad in (("hepsi", "Hepsi"), ("kalan", "Hâlâ farklı"), ("bizim", "Bizim hatamız ya da payımız"), ("karar", "Karar farkı"), ("tutan", "Kör listede tutan")))

    # çelik ağırlığı (kiyas.py'deki tabloyla aynı hesap: fark % ve %0,5 içinde tutan satır)
    celik, TOL = [b for b in B if b["grup"] == "Çelik panel"], 0.5
    yuzde = lambda v: "—" if v is None else ("0,0" if abs(v) < 0.05 else f"{v:+.1f}".replace(".", ","))
    fark = lambda b, x: None if b[x + "_kg"] is None or not b["gercek_kg"] else (b[x + "_kg"] - b["gercek_kg"]) / b["gercek_kg"] * 100
    kg = lambda v: "—" if v is None else f"{v:,.2f}".replace(",", " ").replace(".", ",")
    celik_govde = "".join(
        f'<tr><td>{e(b["ad"])}</td><td class="say gercek">{kg(b["gercek_kg"])}</td>'
        + "".join(f'<td class="say">{kg(b[x + "_kg"])}</td><td class="say{"" if fark(b, x) is not None and abs(fark(b, x)) <= TOL else " fark"}">{yuzde(fark(b, x))}</td>'
                  for x in ("kor", "duzeltilmis")) + "</tr>" for b in celik)
    celik_govde += (f'<tr class="toplam"><td>Toplam</td><td class="say gercek">{kg(ck["gercek"])}</td>'
                    + "".join(f'<td class="say">{kg(ck[x])}</td><td class="say{"" if abs((ck[x] - ck["gercek"]) / ck["gercek"] * 100) <= TOL else " fark"}">'
                              f'{yuzde((ck[x] - ck["gercek"]) / ck["gercek"] * 100)}</td>' for x in ("kor", "duzeltilmis")) + "</tr>")
    celik_tutan = {x: sum(1 for b in celik if fark(b, x) is not None and abs(fark(b, x)) <= TOL) for x in ("kor", "duzeltilmis")}
    celik_tablo = ('<div class="kaydir"><table class="celik"><thead><tr><th>Kalem</th><th class="say">Gerçek kg</th><th class="say">Kör kg</th><th class="say">fark %</th>'
                   '<th class="say">Düzeltilmiş kg</th><th class="say">fark %</th></tr></thead><tbody>' + celik_govde + "</tbody></table></div>")

    karar_b, karar_s = tablo(bolum(rapor, 5))
    hata_b, hata_s = tablo(bolum(rapor, 4))
    sorular = liste(bolum(rapor, 12))
    okuma = next((x for x in bolum(rapor, 5).split("\n") if x.startswith("Okuma:")), "")
    adet_disi = html_tablo(["Konu", "Gerçek liste", "Bizim liste", "Yapılan"], [[x["konu"], x["gercek"], x["biz"], x["yapilan"]] for x in k.get("adet_disi", [])])
    ss = k["kor_farklarinin_sinifi"]

    sayfa = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KT-01 Kör Test Kıyası</title>
<style>
/* Düzen: tek sütun; üstte özet ve beklenen kararlar, altında karar tablosu ve satır satır kıyas. Sayılar eş aralıklı yazıyla sağa hizalı. */
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
.ozet div {{ flex: 1 1 170px; background: var(--kagit); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.ozet b {{ font-family: var(--mono); font-size: 24px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.ozet b small {{ font-size: 13px; color: var(--soluk); font-weight: 400; white-space: nowrap; }}
.ozet span {{ font-size: 12.5px; color: var(--soluk); }}
h2 {{ font-size: 15px; margin: 0 0 10px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }}
section > p {{ margin: 0 0 10px; max-width: 80ch; }}
.kaydir {{ overflow-x: auto; background: var(--kagit); border: 1px solid var(--cizgi); }}
table {{ border-collapse: collapse; width: 100%; min-width: 720px; }}
th, td {{ padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--cizgi); font-size: 13.5px; }}
tbody tr:last-child td {{ border-bottom: 0; }}
thead th {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); font-weight: 500; white-space: nowrap; position: sticky; top: 0; background: var(--kagit); }}
tr.grup th {{ font-size: 12px; letter-spacing: .06em; text-transform: uppercase; background: var(--zemin); color: var(--soluk); }}
.say {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.say {{ font-size: 15px; font-weight: 500; }}
td.say.fark {{ color: var(--eks-y); }}
td.say.gercek {{ background: var(--kay-z); color: var(--kay-y); }}
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
ol.sorular {{ margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 8px; max-width: 86ch; }}
.lejant {{ list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--soluk); }}
code {{ font-family: var(--mono); font-size: .92em; }}
table.karar td:nth-child(1) {{ font-family: var(--mono); color: var(--soluk); }}
table.karar td:nth-child(2) {{ font-weight: 600; min-width: 150px; }}
table.celik td.say {{ font-size: 13.5px; font-weight: 400; }}
table.celik tr.toplam td {{ font-weight: 600; border-top: 2px solid var(--cizgi); }}
footer {{ font-size: 12.5px; color: var(--soluk); max-width: 86ch; }}
@media print {{ .suzgec {{ display: none; }} .kaydir {{ overflow: visible; border: 0; }} thead th {{ position: static; }} }}
</style>
</head>
<body>
<div class="sayfa">
<header>
  <div class="kunye">KT-01 · kör test · {e(a.zaman)} · deneme, canlıda değil</div>
  <h1>Kendi yükleme listemiz ile gerçek liste</h1>
  <p class="aciklama">98,7 m² tek kat çelik proje (beşik + cumba çatı, müştemilat, sandviç panel; Eylül 2026 listesi). Listemiz gerçek liste açılmadan önce donduruldu, sonra gerçek listenin adedi yazılı {toplam} satırıyla tek tek kıyaslandı. "Aynı" yalnız adedin aynı olmasıdır. Kişi, bayi ve firma adı, fiyat yoktur.</p>
</header>
<div class="ozet">{ozet}</div>
<section>
  <h2>Kör listedeki {sum(ss.values())} farkın nedeni</h2>
  <ul class="lejant">
    <li><span class="rozet eksik">girdi hatası</span> {ss["girdi"]} satır: belgede vardı, yanlış okuduk</li>
    <li><span class="rozet eksik">kural hatası</span> {ss["kural"]} satır: kuralımız yoktu ya da varsayımımız tutmadı</li>
    <li><span class="rozet bekle">karar farkı</span> {ss["karar"]} satır: mevcut kural o listedeki uygulamadan farklı</li>
    <li><span class="rozet kaynak">elle (liste)</span> {ss["elle"]} satır: listenin elle yuvarlaması ya da kaba hesabı</li>
    <li><span class="rozet kaynak">paftadan</span> {ss["pafta"]} satır: paftadan sayılan kalem</li>
  </ul>
  <p>Bizim hatamız olan {bz["satir"]} satırın {bz["duzeltilmis"]}'si düzeltilmiş listede, {bz["sablon"]}'si Eylül 2026 uygulamasıyla, {bz["pafta"]}'ü pafta sayımıyla tutuyor; {bz["kalan"]} satırda hatamız düzeldi ama fark başka bir nedenle sürüyor; {bz["duzeltilemedi"]} satır düzeltilemedi (kuralı bilinmiyor). Asıl nedeni başka olan {bz["payimiz_olan"]} satırda da bizim hatamızın payı vardı. Kör listede tutan {oz["kor"]["ayni"]} satırın {k["kor_listede_tesadufen_tutan_satir"]}'si tesadüfen ya da eşikte tutuyordu.</p>
</section>
<section>
  <h2>Sizden beklenen kararlar</h2>
  <p class="alt">Metinlerdeki bölüm numaraları raporun bölümleridir; 5. bölüm bu sayfadaki "Eylül 2026 listesinin farklı yaptıkları" tablosudur.</p>
  <ol class="sorular">{"".join(f"<li>{md(x)}</li>" for x in sorular)}</ol>
</section>
<section>
  <h2>Eylül 2026 listesinin farklı yaptıkları (karar bekliyor)</h2>
  <p>Hiçbiri varsayılan hesapta değil; yalnız "+ 2026" sütununda uygulanıyor. Son sütun, aynı uygulama 2025 tarihli üç gerçek listede denenince ne olduğunu gösterir.</p>
  {html_tablo(karar_b, karar_s, "karar")}
  <p class="alt">{md(okuma)}</p>
</section>
<section>
  <h2>Bizim hatalarımız ve yapılan düzeltmeler</h2>
  {html_tablo(hata_b, hata_s)}
</section>
<section>
  <h2>Çelik ağırlığı</h2>
  <p>Ağırlığı %{str(TOL).replace(".", ",")} içinde tutan satır ({len(celik)} satırda): kör listede {celik_tutan["kor"]}, düzeltilmiş listede {celik_tutan["duzeltilmis"]}. Kör listede ağırlık motorun proje ortalamalarından (duvar boyu × kg/m) hesaplanmıştı; korkuluk ve baca da 1,2 mm varsayılmıştı. Düzeltilmiş listede modeldeki profil boyundan ve modelde okunan et kalınlığından: boy × profilin birim ağırlığı.</p>
  {celik_tablo}
</section>
<section>
  <h2>Satır satır kıyas</h2>
  <div class="suzgec" role="group" aria-label="Satırları süz">{suzgec}</div>
  {satir_tablo}
  <p class="alt">Düğmelerdeki sayılar gerçek listenin satırıdır; tablonun bir satırı gerçek listede birden çok satırı karşılayabilir ({len(B)} tablo satırı, {toplam} gerçek satır). Kırmızı sayı: gerçek listeden farklı. Kör: dondurulan liste. Düzeltilmiş: yalnız bizim hatalarımız düzeltildi, bugünkü kurallar. + 2026: Eylül 2026 listesinin uygulaması da kural olursa. + pafta: elektrik ve iniş sayısı da paftadan alınırsa.</p>
</section>
<section>
  <h2>Adet dışındaki farklar</h2>
  {adet_disi}
</section>
<footer>Kaynak: <code>deneme/2026-10-06_kor_test/sonuc/KT01_kiyas.json</code> ve <code>docs/raporlar/2026-10-07_Kor_Test_KT01.md</code>; sayfa <code>kiyas_sayfa.py</code> ile üretilir, elle düzeltilmez. Sınırlar raporun 11. bölümünde: tek proje; Eylül 2026 uygulaması tek listeden; çelik birim ağırlıkları yalnız bu projeyle doğrulandı.</footer>
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
"""
    a.cikti.write_text(sayfa, encoding="utf-8")
    print("yazıldı:", a.cikti, "·", len(sayfa) // 1024, "KB ·", len(B), "birim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
