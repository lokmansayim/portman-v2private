"""Proje kartı veri seti: kartları birleştirir ve hakem karşılaştırmasıyla tek özet sayfası (HTML) yazar.

Kullanım:
    python3 araclar/proje_karti_ozet.py <çalışma klasörü> <çıktı klasörü>

Çalışma klasörü her proje için `AP-NN/` içerir: `pafta.pdf`, `kart_yapi.json` (yapı değerleri, okuyan ajan),
`script/kart.json` (yükleme listesi, depodaki liste okuyucusu `testler/kor/oku.py`), `dogrulama.json` (hakemin kaynakla
karşılaştırması). Çıktı: `<çıktı>/AP-NN/kart.json` (birleşik kart) ve `<çıktı>/ozet.html`.
Gerçek proje adı ve kişi adı dosyalara yazılmaz; plan görselinde ad olabilecek yazılar örtülür.
"""
from __future__ import annotations

import base64
import html
import io
import json
import sys
from pathlib import Path

import pdfplumber


def _h(x):
    if x is None:
        return "<span class='bos'>—</span>"
    if isinstance(x, float):
        x = f"{x:g}".replace(".", ",")
    if isinstance(x, (dict, list)):
        x = json.dumps(x, ensure_ascii=False)
    return html.escape(str(x))


_KATLA = str.maketrans("ÇĞİIÖŞÜçğıiöşü", "CGIIOSUcgiiosu")
# Kişi, firma ve proje adı olabilecek sözcükler (klasör ve antet adlarından); görselde beyazla örtülür.
GIZLI = {"UBEYDULLAH", "OZER", "LOKMAN", "SAYIM", "NADIRE", "HANIM", "ABDULSELAM", "ANDULSELAM", "AYKUT", "EREN", "KUBRA",
         "TOP", "AHMET", "DOGAN", "DIAMOND", "YASAMTAS", "YASAM", "TATAR", "NEHIR", "YILDIRIM", "SARAY", "CMS", "MODERN",
         "HUMA", "BEY", "PORTATIFEV", "LOFTEV", "RAMAZAN", "BATMAZ", "NIMET", "UBEYTULLAH", "GRUP", "KUBBELI", "KUBBESIZ", "AZIZ", "TURKER", "FILIZ", "SAFAK", "IPAK", "AREL"}
ETIKET = ("CIZEN", "KONTROL", "MUSTERI", "HAZIRLAYAN", "TASARLAYAN", "ONAYLAYAN", "PROJE", "FIRMA", "BAYI", "TEL")


def _katla(t: str) -> str:
    return t.translate(_KATLA).upper()


def plan_gorseli(pafta: Path) -> str:
    """Paftanın 1. sayfası, gri tonlu; ad olabilecek yazılar (GIZLI sözcükler ve antet etiketlerinin sağındaki yazı) örtülür."""
    from PIL import ImageDraw
    with pdfplumber.open(pafta) as pdf:
        s = pdf.pages[0]
        kel = s.extract_words()
        ortu = []
        for w in kel:
            t = _katla(w["text"]).strip(":,.;()")
            if t in GIZLI or any(g in t for g in GIZLI if len(g) > 4):
                ortu.append(w)
            if any(t.startswith(e) for e in ETIKET):
                ortu += [u for u in kel if abs(u["top"] - w["top"]) < 4 and 0 < u["x0"] - w["x1"] < 260]
        olcek = 80 / 72
        img = s.to_image(resolution=80).original.convert("L")
        ciz = ImageDraw.Draw(img)
        for w in ortu:
            ciz.rectangle([w["x0"] * olcek - 2, w["top"] * olcek - 2, w["x1"] * olcek + 2, w["bottom"] * olcek + 2], fill=255)
    b = io.BytesIO()
    img.save(b, format="PNG", optimize=True)
    return base64.b64encode(b.getvalue()).decode()


def kart_birlestir(d: Path) -> dict:
    yapi = json.loads((d / "kart_yapi.json").read_text(encoding="utf-8"))
    liste = json.loads((d / "script" / "kart.json").read_text(encoding="utf-8"))["yukleme_listesi"]
    kart = {k: v for k, v in yapi.items() if k not in ("kaynak_yerleri", "belirsiz")}
    kart["yukleme_listesi"] = liste
    kart["kaynak_yerleri"] = yapi.get("kaynak_yerleri", {})
    kart["belirsiz"] = yapi.get("belirsiz", [])
    return kart


def main(argv=None):
    argv = argv or sys.argv[1:]
    calisma, cikti = Path(argv[0]), Path(argv[1])
    satirlar, bolumler = [], []
    for d in sorted(p for p in calisma.iterdir() if p.is_dir() and p.name.startswith("AP-")):
        if not (d / "kart_yapi.json").exists():
            continue
        kart = kart_birlestir(d)
        (cikti / d.name).mkdir(parents=True, exist_ok=True)
        (cikti / d.name / "kart.json").write_text(json.dumps(kart, ensure_ascii=False, indent=1), encoding="utf-8")
        dog = json.loads((d / "dogrulama.json").read_text(encoding="utf-8")) if (d / "dogrulama.json").exists() else None
        yf = [r for r in (dog or {}).get("yapi", []) if not r.get("ayni")]
        yd = [r for r in (dog or {}).get("yapi", []) if r.get("duzeltildi")]
        ly = (dog or {}).get("liste", {})
        lf = ly.get("farklar", [])
        o = kart.get("dis_olcu_cm") or {}
        satirlar.append(
            f"<tr class='{'fark' if (yf or lf) else ''}'><td><a href='#{d.name}'>{d.name}</a></td>"
            f"<td>{_h(kart.get('yapi_tipi'))}</td><td class='d'>{_h(o.get('genislik'))} × {_h(o.get('derinlik'))}</td>"
            f"<td class='d'>{_h(kart.get('brut_oturum_m2'))}</td><td class='d'>{_h(kart.get('liste_bina_m2'))}</td>"
            f"<td class='d'>{_h(kart.get('oda_sayisi'))}</td><td class='d'>{kart['yukleme_listesi']['kalem_sayisi']}</td>"
            f"<td class='d'>{len(kart.get('belirsiz', []))}</td>"
            f"<td class='d'>{'—' if dog is None else len(yf)}</td><td class='d'>{len(yd)}</td><td class='d'>{'—' if dog is None else len(lf)}</td><td class='d'>{len(ly.get('cozulen', []))}</td></tr>")
        yt = "".join(
            f"<tr class='{'duz' if r.get('duzeltildi') else ('' if r.get('ayni') else 'fark')}'><td>{_h(r.get('alan'))}</td><td>{_h(r.get('kart'))}{' → düzeltildi' if r.get('duzeltildi') else ''}</td>"
            f"<td>{_h(r.get('kaynak'))}</td><td class='yer'>{_h(r.get('kaynak_yeri'))}</td><td class='yer'>{_h(r.get('not'))}</td></tr>"
            for r in (dog or {}).get("yapi", []))
        lt = "".join(
            f"<tr class='fark'><td>{_h(r.get('malzeme'))}</td><td>{_h(r.get('boyut_kart'))}</td><td>{_h(r.get('boyut_kaynak'))}</td>"
            f"<td class='d'>{_h(r.get('adet_kart'))}</td><td class='d'>{_h(r.get('adet_kaynak'))}</td><td class='yer'>{_h(r.get('tur'))} · {_h(r.get('kaynak_yeri'))}</td></tr>"
            for r in lf) + "".join(
            f"<tr class='duz'><td>{_h(r.get('malzeme'))}</td><td>{_h(r.get('boyut_kart'))}</td><td>{_h(r.get('boyut_kaynak'))}</td>"
            f"<td class='d'>{_h(r.get('adet_kart'))}</td><td class='d'>{_h(r.get('adet_kaynak'))}</td><td class='yer'>{_h(r.get('tur'))} · düzeltildi (okuyucu)</td></tr>"
            for r in ly.get("cozulen", []))
        bel = "".join(f"<li>{_h(b)}</li>" for b in kart.get("belirsiz", []))
        bolumler.append(f"""<details id="{d.name}"><summary><b>{d.name}</b> · {_h(o.get('genislik'))} × {_h(o.get('derinlik'))} cm · {_h(kart.get('brut_oturum_m2'))} m² · {_h(kart.get('oda_sayisi'))} · yapı farkı {len(yf)}, liste farkı {len(lf)}</summary>
<div class="ust"><div><img alt="Kat planı {d.name}" src="data:image/png;base64,{plan_gorseli(d / 'pafta.pdf')}">
<p class="ozet">Hakem: {_h((dog or {}).get('ozet', 'karşılaştırma yok'))}</p>{'<p><b>Okuyan ajanın emin olmadığı alanlar</b></p><ul>' + bel + '</ul>' if bel else ''}</div>
<div><div class="tw"><table><tr><th>Alan</th><th>Kart</th><th>Kaynak (hakem)</th><th>Nereden</th><th>Not</th></tr>{yt}</table></div>
<p class="ozet">Liste: kartta {_h(ly.get('satir_sayisi_kart'))} satır, kaynakla aynı {_h(ly.get('ayni'))}.</p>
{'<div class="tw"><table><tr><th>Kalem</th><th>Boyut (kart)</th><th>Boyut (kaynak)</th><th>Adet (kart)</th><th>Adet (kaynak)</th><th>Tür · yer</th></tr>' + lt + '</table></div>' if lt else ''}
</div></div></details>""")
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Proje kartları</title><style>
:root{{--bg:#fff;--fg:#1d1d1f;--ince:#6b6b70;--cizgi:#ddd;--kirmizi:#c62828;--kirmizi-bg:#fdecea;--yesil:#1b6e2a;--yesil-bg:#e8f5e9}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#17171a;--fg:#ececf0;--ince:#a0a0a8;--cizgi:#333;--kirmizi:#ff6b6b;--kirmizi-bg:#3a1d1d;--yesil:#7fd68a;--yesil-bg:#1d3a22}}}}
:root[data-theme="dark"]{{--bg:#17171a;--fg:#ececf0;--ince:#a0a0a8;--cizgi:#333;--kirmizi:#ff6b6b;--kirmizi-bg:#3a1d1d;--yesil:#7fd68a;--yesil-bg:#1d3a22}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;padding:16px;max-width:1300px;margin:auto}}
h1{{font-size:20px}} .tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid var(--cizgi);padding:4px 6px;text-align:left;vertical-align:top}} td.d{{text-align:right;white-space:nowrap}}
.yer,.ozet,.bos{{color:var(--ince);font-size:12px}} tr.fark td{{color:var(--kirmizi);background:var(--kirmizi-bg)}} tr.duz td{{color:var(--yesil);background:var(--yesil-bg)}}
details{{border:1px solid var(--cizgi);border-radius:6px;margin:10px 0;padding:8px}} summary{{cursor:pointer}}
.ust{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:16px;margin-top:8px}} @media(max-width:800px){{.ust{{grid-template-columns:1fr}}}}
img{{width:100%;height:auto;border:1px solid var(--cizgi);background:#fff}} a{{color:inherit}} td:first-child{{white-space:nowrap}}
</style></head><body><h1>Proje kartları · AIPrefabrik</h1>
<p class="ozet">Kırmızı: hakemin kaynakta okuduğu değer kartla farklı. Yeşil: 9 Kasım'da düzeltildi; yapı satırında kart hakemin okuduğu kaynak değerle, liste satırında liste okuyucusu (Kart sütunu eski değeri gösterir). Kart: yapı değerlerini okuyan ajan, listeyi depodaki liste okuyucusu çıkardı. Kaynak: hakemin montaj paftası ve yükleme listesinden kendi okuması.</p>
<div class="tw"><table><tr><th>Kod</th><th>Yapı</th><th>Dış ölçü (cm)</th><th>Brüt m²</th><th>Liste m²</th><th>Oda</th><th>Liste kalemi</th><th>Belirsiz</th><th>Yapı farkı</th><th>Düzeltilen</th><th>Liste farkı</th><th>Liste düzeltilen</th></tr>{''.join(satirlar)}</table></div>
{''.join(bolumler)}</body></html>"""
    (cikti / "ozet.html").write_text(sayfa, encoding="utf-8")
    print(f"{len(satirlar)} proje → {cikti / 'ozet.html'}")


if __name__ == "__main__":
    main()
