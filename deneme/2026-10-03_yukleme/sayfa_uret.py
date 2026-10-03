#!/usr/bin/env python3
"""Ç8201 yükleme listesi taslağını okunur bir sayfaya (tek HTML dosyası) çevirir.

Sayılar `sonuc/` altındaki hesap çıktılarından alınır; elle yazılmaz. Önce `hepsini_kos.sh` koşulmalı.
Sayfa Claude'un artefakt biçimindedir (doctype, html, head, body etiketleri yok). Depoya çıktı yazılmaz.
Şimdilik Ç8201'e özgüdür: dosya adları, "değişenler" ve "sizden beklenenler" metinleri bu modele göredir.
Sayfa Lokman'ın özel artefaktıdır ama paylaşılabilir; o yüzden kişi adı yazılmaz (mühendis "mühendis" diye geçer).

Kullanım:
    python sayfa_uret.py --cikti /tmp/C8201_yukleme_listesi.html --zaman "3 Ekim 2026 19:30"
"""
import argparse
import base64
import html
import json
from pathlib import Path

S = Path(__file__).resolve().parent / "sonuc"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--cikti", type=Path, required=True)
ap.add_argument("--zaman", required=True, help="künyede görünecek tarih ve saat")
A = ap.parse_args()
baz = json.loads((S / "C8201_yukleme_taslak.json").read_text(encoding="utf-8"))
d140 = json.loads((S / "C8201_dis_karkas_140_yukleme_taslak.json").read_text(encoding="utf-8"))
KAPLAMALAR = [("Sandviç panel", baz, None)] + [
    (ad, json.loads((S / f"C8201_kaplama_{kod}.json").read_text(encoding="utf-8")), notu) for ad, kod, notu in (
        ("Tek kat panel", "tek_kat_panel", None),
        ("OSB + nem bariyeri + kiremit desen sac", "osb_kiremit", "Motordaki adı: OSB + membran + metal kiremit"),
        ("OSB + nem bariyeri + trapez sac", "osb_trapez", "Gerçek listeyle karşılaştırılmadı"),
        ("Trapez sac", "trapez_sac", "Gerçek listeyle karşılaştırılmadı"),
        ("OSB + membran + shingle", "osb_shingle", "Yalnız motorun formülüyle; gerçek listeyle karşılaştırılmadı"))]

def tr(x, n=0):
    return f"{x:.{n}f}".replace(".", ",")

def e(s):
    return html.escape(str(s), quote=True)

DURUM = {
    "lokman": ("Sizin kuralınız", "ok", "Kuralı siz söylediniz"),
    "muhendis": ("Mühendisin kuralı", "ok", "Kuralı ya da değeri inşaat mühendisi verdi (3 Ekim)"),
    "excel": ("Liste formülü", "kaynak", "Gerçek yükleme listelerinin çalışma kitabındaki formül"),
    "motor": ("Excel motoru", "kaynak", "CTKBF V1.1'deki formül ya da proje ortalaması"),
    "model": ("Modelden", "kaynak", "Çizimdeki açıklıklardan sayıldı"),
    "uydurma": ("Listeye uyduruldu", "bekle", "Gerçek listelerdeki adedi tutturan kural; teyit bekliyor"),
    "varsayim": ("Varsayım", "bekle", "Benim varsayımım; teyit bekliyor"),
    "soru": ("Soru", "eksik", "Kural bilinmiyor; adet yok"),
    "bekliyor": ("Değer yok", "eksik", "Ölçü ya da sayım gelince hesaplanacak"),
}

def es(s):
    for x in d140["satirlar"]:
        if x["grup"] == s["grup"] and x["kalem"] == s["kalem"] and (x["boyut"] == s["boyut"] or s["grup"] == "Çelik panel"):
            if s["grup"] == "Çelik panel" and s["kalem"] == "Boy C profil" and x["boyut"] != s["boyut"]:
                continue
            return x
    return None

def olcu(s):
    return "" if s["olcu"] is None else f"{tr(s['olcu'], 1)} {s['birim']}"

gruplar = []
for s in baz["satirlar"]:
    if s["grup"] not in gruplar:
        gruplar.append(s["grup"])

ACIK = ("tahmin", "teyit bekliyor", "geçici", "priz sayısı bilinmediği", "katalog görsellerinden", "iki katı")


def bekleyen(s):
    return DURUM[s["durum"]][1] in ("bekle", "eksik") or any(k in (s.get("not") or "") for k in ACIK)


def satir_html(s):
    o = es(s)
    ad, sinif, _ = DURUM[s["durum"]]
    celik = s["grup"] == "Çelik panel"
    adet_baz = "" if s["adet"] is None else str(s["adet"])
    if celik:
        kg_baz = "" if s["kg"] is None else tr(s["kg"])
        if o is None:
            oteki = "—"
        else:
            parca = []
            if o["boyut"] != s["boyut"]:
                parca.append(e(o["boyut"]))
            if o["kg"] is not None and (o["kg"] != s["kg"] or o["boyut"] != s["boyut"]):
                parca.append(f"{tr(o['kg'])} kg")
            elif o["kg"] is None and o["olcu"] != s["olcu"]:
                parca.append(e(olcu(o)))
            oteki = " · ".join(parca) if parca else "aynı"
        hucre = f'<td class="say">{adet_baz}</td><td class="say">{kg_baz}</td><td class="oteki">{oteki}</td>'
    else:
        if o is None:
            oteki = "—"
        elif o["adet"] == s["adet"]:
            oteki = "aynı"
        else:
            oteki = f'<b>{o["adet"]}</b>'
        hucre = f'<td class="say">{adet_baz}</td><td class="oteki">{oteki}</td>'
    alt = []
    if s["olcu"] is not None:
        alt.append(e(olcu(s)))
    if s["formul"]:
        alt.append(e(s["formul"]))
    notu = f'<div class="not">{e(s["not"])}</div>' if s.get("not") else ""
    return (f'<tr data-d="{"bekle" if bekleyen(s) else "tamam"}"><td class="kalem"><div class="ad">{e(s["kalem"])}</div><div class="alt">{" · ".join(alt)}</div>{notu}</td>'
            f'<td class="boyut">{e(s["boyut"])}</td>{hucre}<td><span class="rozet {sinif}" title="{e(DURUM[s["durum"]][2])}">{ad}</span></td></tr>')

bolumler = []
for g in gruplar:
    celik = g == "Çelik panel"
    bas = ("<tr><th>Kalem</th><th>Boyut</th><th class='say'>Adet</th><th class='say'>kg</th><th>Dış 140</th><th>Kaynak</th></tr>" if celik
           else "<tr><th>Kalem</th><th>Boyut</th><th class='say'>Baz</th><th>Dış 140</th><th>Kaynak</th></tr>")
    govde = "\n".join(satir_html(s) for s in baz["satirlar"] if s["grup"] == g)
    n = sum(1 for s in baz["satirlar"] if s["grup"] == g)
    bolumler.append(f'<section class="grup"><h2>{e(g)} <span class="sayac">{n} kalem</span></h2><div class="kaydir"><table class="{"celik" if celik else ""}"><thead>{bas}</thead><tbody>{govde}</tbody></table></div></section>')

def kap(v):
    return [s for s in v["satirlar"] if s["grup"] == "Çatı kaplamaları" or (s["grup"] == "Vida" and ("5,5 × 60" in s["kalem"] or "panel)" in s["kalem"] or "OSB ve yalıpan" in s["kalem"]))]

def kap_tablo(ad, v, notu):
    r = "".join(f'<tr><td>{e(s["kalem"])}</td><td class="boyut">{e(s["boyut"])}</td><td class="say">{s["adet"]}</td></tr>' for s in kap(v))
    alt = f'<p class="secenek-not">{e(notu)}</p>' if notu else ""
    return f'<div class="secenek"><h3>{e(ad)}</h3><table><tbody>{r}</tbody></table>{alt}</div>'

kaplama = "".join(kap_tablo(ad, v, notu) for ad, v, notu in KAPLAMALAR)

def kg(v, kalem):
    return next(s["kg"] for s in v["satirlar"] if s["kalem"] == kalem)
def adet(v, kalem):
    return next(s["adet"] for s in v["satirlar"] if s["kalem"] == kalem)

toplam_baz, toplam_140 = kg(baz, "Toplam (adedi ve kg'ı bilinenler)"), kg(d140, "Toplam (adedi ve kg'ı bilinenler)")
_kars = [json.loads((S / f"ornek_{n}m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma_ozeti"] for n in (90, 62, 105)]
kars_toplam, kars_ayni = sum(x["karsilastirilan"] for x in _kars), sum(x["ayni"] for x in _kars)
toplam_satir = len(baz["satirlar"])
bekleyen_sayisi = sum(1 for s in baz["satirlar"] if bekleyen(s))

def satir(v, kalem):
    return next(s for s in v["satirlar"] if s["kalem"] == kalem)

# Mühendisin 3 Ekim cevaplarıyla değişenler: "önce" değerleri 14:50 sürümünden (sabit), "sonra" değerleri hesap çıktısından.
osb_s, kose_s = satir(baz, "OSB (TV ve mutfak dolabı arkası takviyesi)"), satir(baz, "Köşebent")
degisenler = [
    ("Çelik", f"Tavan paneli {tr(kg(baz, 'Tavan paneli (makas arası)'))} kg ve çatı paneli {tr(kg(baz, 'Çatı paneli (makas üstü, sırt 80 mm)'))} kg eklendi "
              f"(100 m² bina için verilen değerler alana oranlandı). Toplam 1902 → {tr(toplam_baz)} kg."),
    ("Köşebent", f"33 → {kose_s['adet']}. Yeni formül: (odaların tavan çevresi + iç köşeler × 2,7 m) ÷ 2,5. m² ÷ 2,5 kuralınızın yerine geçti."),
    ("OSB takviyesi", f"15 → {osb_s['adet']} levha. Bütün oda değil, yalnız dolap ve TV ünitesi duvarları ({tr(osb_s['olcu'], 1)} m²)."),
    ("Elektrik", f"Sayılar artık oda başına kuraldan (doğruluk payı yaklaşık %75): duy {adet(baz, 'Tijli duy')}, glop {adet(baz, 'Yuvarlak glop')}, "
                 f"anahtar {adet(baz, 'Tekli anahtar')} + {adet(baz, 'Çiftli anahtar')}, priz {adet(baz, 'Tekli priz')} + {adet(baz, 'Çiftli priz')}, sigorta {adet(baz, 'W otomat (sigorta)')}; "
                 f"kablo {adet(baz, 'NYM kablo (3 × 2,5)')} ve {adet(baz, 'NYM kablo (2 × 1,5)')} m."),
    ("Saçak", "Saçak omegası gerekmiyor: satır kalktı. Saçak yüzünün Boardex olduğu teyit edildi."),
    ("Çatı kaplaması", "Üç yerine altı seçenek hesaplanıyor (Excel motorundaki liste)."),
    ("Dere inişi", f"Sayı aynı ({adet(baz, 'Dere iniş borusu')}). İniş plana bakarak yerleştirilir; elle yerleştirilirse o sayı kullanılır."),
]
degisen_html = "".join(f"<li><b>{e(b)}.</b> {e(m)}</li>" for b, m in degisenler)

_kgm = json.loads((S.parent / "kurallar.json").read_text(encoding="utf-8"))["celik"]["duvar_kg_m"]["deger"]
_g140 = json.loads((S / "C8201_dis_karkas_140_girdi.json").read_text(encoding="utf-8"))["celik"]
# dış 140'ta duvarlar 1,2 mm alınırsa toplam: dış 140 × 1,2 ve iç 80 × 1,2 birim ağırlıklarıyla
toplam_140_kalin = (toplam_140 + _g140["dis"]["boy_m"] * (_kgm["dis"]["140x45x1,2"] - _kgm["dis"]["140x45x0,8"])
                    + _g140["ic"]["boy_m"] * (_kgm["ic"]["80x45x1,2"] - _kgm["ic"]["80x45x0,8"]))
sorular = [
    ("Çatı kaplaması", "Baz pakette altı seçenekten hangisi var? Mühendis seçenekleri saydı, baz paketi yazmadı."),
    ("Dış 140'ta et kalınlığı", f"0,8 mm aldım: çelik toplamı {tr(toplam_140)} kg, baz paketten hafif. 1,2 mm olursa {tr(toplam_140_kalin)} kg. Excel motorundaki tek katlı 140'lık örnekte "
                                "duvarlar 1,2 mm; 0,8 mm örnekleri iki katlıların üst katı; 2025'teki iki tek katlı listede 0,8 mm. Tek katta hangisi?"),
    ("OSB takviyesi duvarları", "Katalog görselinden üç duvarı aldım: banyo ile mutfak arası, üst dış duvar (tezgâh ve eviye), hol ile yaşam alanı arası (TV). Planda turuncu çizgili. Doğru mu?"),
    ("Elektrik", "Yaşam Alanı'nda salon ve mutfak kurallarını birlikte uyguladım. Doğru mu?"),
    ("Makas ve kiriş", "Bir makas ölçüsünden verecektiniz; o zamana kadar çatı çeliği motorun ortalamasıyla (geçici). Tavan ve çatı panelinin adedi de alana oranlandı."),
    ("Kırma çatıda kaplama adedi", f"Yüzeyin %10 fazlasını alıyorum ({adet(baz, 'Sandviç panel')} panel); yerleşim hesabı {baz['ara']['kirma_kaplama_yerlesim_adedi']} veriyor. "
                                    "Mühendisin 10 × 10 m metrajında pay daha yüksek. Adedi yerleşimle mi bulalım?"),
    ("Motorda olup listede olmayanlar", "Çatı müdahale kapağı ve mahya bandı Excel motorunda var, okuduğum listelerde yok. Listeye girsin mi?"),
]
soru_html = "".join(f"<li><b>{e(b)}.</b> {e(m)}</li>" for b, m in sorular)

# Plan görseli (OSB takviyesi gelen duvarlar turuncu çizgili): çizim denemesinin son çıktısı, sayfanın içine gömülür.
_plan = S.parents[1] / "2026-10-02_celik" / "sonuc" / "C8201_plan.png"
plan_html = ""
if _plan.is_file():
    plan_html = ('<section><h2>Plan</h2><p class="aciklama" style="margin-bottom:10px">OSB takviyesi gelen duvarlar turuncu çizgiyle işaretli; '
                 'kesik çizgi veranda kirişi, siyah kutular dikmeler.</p><div class="plan"><img alt="Ç8201 planı: beş mahal ve veranda; OSB takviyesi gelen üç duvar turuncu çizgiyle işaretli" '
                 f'src="data:image/png;base64,{base64.b64encode(_plan.read_bytes()).decode("ascii")}"></div></section>')

kullanilan = {s["durum"] for s in baz["satirlar"]}
lejant = "".join(f'<li><span class="rozet {v[1]}">{v[0]}</span><span>{e(v[2])}</span></li>' for k, v in DURUM.items() if k in kullanilan)

sayfa = f"""<title>Ç8201 Yükleme Listesi</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Düzen: sevk listesi gibi tek sütun; üstte künye ve özet, altında grup grup tablolar. Sayılar eş aralıklı yazıyla sağa hizalı. */
:root {{
  --zemin: #f3f5f6; --kagit: #ffffff; --yazi: #17212b; --soluk: #5b6875; --cizgi: #d5dbe0; --vurgu: #1f5f7a;
  --ok-z: #dff1e6; --ok-y: #1c6b3c; --kay-z: #e3ebf2; --kay-y: #2f4a63; --bek-z: #fdebc8; --bek-y: #7a4d00; --eks-z: #f8d9d6; --eks-y: #8a2118;
  --cizim-z: #ffffff; /* çizimin kendi zemini beyaz: iki temada da beyaz kalır */
  --sans: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }}
body {{ background: var(--zemin); color: var(--yazi); font-family: var(--sans); font-size: 15px; line-height: 1.5; }}
.sayfa {{ max-width: 980px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: flex; flex-direction: column; gap: 26px; }}
header {{ display: flex; flex-direction: column; gap: 10px; }}
.kunye {{ font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
h1 {{ font-size: clamp(24px, 4.6vw, 34px); line-height: 1.15; margin: 0; font-weight: 600; text-wrap: balance; }}
.aciklama {{ color: var(--soluk); max-width: 68ch; margin: 0; }}
.taslak {{ display: inline-block; font-family: var(--mono); font-size: 12px; border: 1px solid var(--bek-y); color: var(--bek-y); padding: 2px 8px; border-radius: 3px; letter-spacing: .05em; }}
.ozet {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--cizgi); border: 1px solid var(--cizgi); }}
.ozet div {{ background: var(--kagit); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.ozet b {{ font-family: var(--mono); font-size: 20px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.ozet span {{ font-size: 12.5px; color: var(--soluk); }}
h2 {{ font-size: 15px; margin: 0 0 8px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; display: flex; align-items: baseline; gap: 10px; }}
h2 .sayac {{ font-family: var(--mono); font-size: 11.5px; font-weight: 400; color: var(--soluk); letter-spacing: 0; text-transform: none; }}
h3 {{ font-size: 14px; margin: 0 0 6px; font-weight: 600; }}
.kaydir {{ overflow-x: auto; background: var(--kagit); border: 1px solid var(--cizgi); }}
table {{ border-collapse: collapse; width: 100%; min-width: 620px; }}
th, td {{ padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--cizgi); }}
tbody tr:last-child td {{ border-bottom: 0; }}
th {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); font-weight: 500; white-space: nowrap; }}
.say {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.say {{ font-size: 15px; font-weight: 500; }}
.boyut {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); white-space: nowrap; }}
.oteki {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); }}
.oteki b {{ color: var(--yazi); font-weight: 500; font-size: 15px; }}
.kalem {{ min-width: 240px; }}
.ad {{ font-weight: 500; }}
.alt {{ font-size: 12.5px; color: var(--soluk); max-width: 62ch; }}
.not {{ font-size: 12.5px; color: var(--bek-y); max-width: 62ch; }}
.rozet {{ display: inline-block; font-size: 11.5px; padding: 2px 8px; border-radius: 10px; white-space: nowrap; font-weight: 500; }}
.rozet.ok {{ background: var(--ok-z); color: var(--ok-y); }}
.rozet.kaynak {{ background: var(--kay-z); color: var(--kay-y); }}
.rozet.bekle {{ background: var(--bek-z); color: var(--bek-y); }}
.rozet.eksik {{ background: var(--eks-z); color: var(--eks-y); }}
.suzgec {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
.suzgec button {{ font: inherit; font-size: 13.5px; padding: 6px 12px; border: 1px solid var(--cizgi); background: var(--kagit); color: var(--yazi); border-radius: 4px; cursor: pointer; }}
.suzgec button[aria-pressed="true"] {{ background: var(--vurgu); border-color: var(--vurgu); color: var(--kagit); }}
.suzgec button:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
.lejant {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 6px 18px; font-size: 13px; color: var(--soluk); }}
.lejant li {{ display: flex; gap: 8px; align-items: baseline; }}
.secenekler {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 14px; }}
.secenek {{ background: var(--kagit); border: 1px solid var(--cizgi); padding: 12px 14px; min-width: 0; }}
.secenek table {{ min-width: 0; }}
.secenek td {{ padding: 5px 0; font-size: 13.5px; }}
.secenek td.boyut {{ padding-inline: 8px; white-space: normal; }}
.secenek-not {{ margin: 8px 0 0; font-size: 12.5px; color: var(--bek-y); }}
.degisen {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; max-width: 76ch; }}
.plan {{ background: var(--cizim-z); border: 1px solid var(--cizgi); padding: 8px; }}
.plan img {{ display: block; width: 100%; height: auto; }}
.sorular {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; max-width: 76ch; }}
.dip {{ font-size: 12.5px; color: var(--soluk); max-width: 76ch; }}
[data-gizli] {{ display: none; }}
@media (max-width: 560px) {{ .ozet {{ grid-template-columns: 1fr 1fr; }} .ozet div:last-child {{ grid-column: 1 / -1; }} }}
</style>
<div class="sayfa" lang="tr">
<header>
  <div class="kunye">PortatifEv · Portman · İE-05 · {e(A.zaman)}</div>
  <h1>Ç8201 yükleme listesi</h1>
  <p class="aciklama">Tek kat çelik, 2+1, 82 m². Çatı: kırma, çatı ve tavan panelli yöntem; kaplama örnek olarak sandviç panel. Her sayının yanında nereden geldiği yazıyor.</p>
  <div><span class="taslak">TASLAK · ÜRETİM LİSTESİ DEĞİLDİR</span></div>
</header>

<div class="ozet">
  <div><b>{tr(toplam_baz)} kg</b><span>Çelik, baz paket (tavan ve çatı paneli dahil)</span></div>
  <div><b>{tr(toplam_140)} kg</b><span>Çelik, dış 140 (et kalınlığı varsayımıyla)</span></div>
  <div><b>{adet(baz, "Dış cephe Boardex")} + {adet(baz, "Saçaklar için Boardex")} + {adet(baz, "Saçak yüzü için Boardex")}</b><span>Boardex: cephe, saçak altı, saçak yüzü</span></div>
  <div><b>{adet(baz, "Duvar alçıpan beyaz") + adet(baz, "Tavan alçıpan beyaz")} + {adet(baz, "Duvar alçıpan yeşil") + adet(baz, "Tavan alçıpan yeşil")}</b><span>Alçıpan: beyaz + yeşil</span></div>
  <div><b>{bekleyen_sayisi} / {toplam_satir}</b><span>Teyit ya da değer bekleyen satır</span></div>
</div>

<section>
  <h2>Mühendisin cevaplarıyla değişenler</h2>
  <ul class="degisen">{degisen_html}</ul>
</section>

<section>
  <h2>Kaynak işaretleri</h2>
  <ul class="lejant">{lejant}</ul>
</section>

<div class="suzgec" role="group" aria-label="Satırları süz">
  <button type="button" id="s-hepsi" aria-pressed="true">Bütün satırlar</button>
  <button type="button" id="s-bekle" aria-pressed="false">Yalnız teyit ya da değer bekleyenler</button>
</div>

{chr(10).join(bolumler)}

<section>
  <h2>Çatı kaplaması seçenekleri</h2>
  <p class="aciklama" style="margin-bottom:10px">Baz paketin kaplaması henüz belli değil. Altı seçenek Excel motorundaki listeden; seçeneğe göre değişen kalemler:</p>
  <div class="secenekler">{kaplama}</div>
</section>

{plan_html}

<section>
  <h2>Sizden beklenenler</h2>
  <ol class="sorular">{soru_html}</ol>
</section>

<p class="dip">Kaynaklar: 3 Ekim 13:27 cevaplarınız; inşaat mühendisinin 3 Ekim cevapları (18:14'te ilettiniz); üç gerçek yükleme listesinin çalışma kitapları (62, 90 ve 105 m²); Excel hesaplama motoru (CTKBF V1.1). Bu modelin kendi gerçek listesi yok: sayılar yalnız kurallardan çıkıyor. Üç gerçek listeyle karşılaştırmada {kars_toplam} kalemin {kars_ayni} tanesinde adet aynı; bu bir sınama değil, çünkü katsayıların bir kısmı o listelere bakılarak seçildi. Ayrıntı depoda: docs/sartname/yukleme_listesi_yontemi.md.</p>
</div>
<script>
(function () {{
  var hepsi = document.getElementById('s-hepsi'), bekle = document.getElementById('s-bekle');
  function uygula(yalniz) {{
    document.querySelectorAll('tr[data-d]').forEach(function (tr) {{
      var d = tr.getAttribute('data-d');
      if (yalniz && d !== 'bekle') tr.setAttribute('data-gizli', ''); else tr.removeAttribute('data-gizli');
    }});
    document.querySelectorAll('section.grup').forEach(function (s) {{
      var gorunen = s.querySelectorAll('tbody tr:not([data-gizli])').length;
      if (gorunen === 0) s.setAttribute('data-gizli', ''); else s.removeAttribute('data-gizli');
    }});
    hepsi.setAttribute('aria-pressed', String(!yalniz));
    bekle.setAttribute('aria-pressed', String(yalniz));
  }}
  hepsi.addEventListener('click', function () {{ uygula(false); }});
  bekle.addEventListener('click', function () {{ uygula(true); }});
}})();
</script>
"""
A.cikti.write_text(sayfa, encoding="utf-8")
print("yazıldı:", A.cikti, "·", toplam_satir, "satır; teyit ya da değer bekleyen", bekleyen_sayisi)
