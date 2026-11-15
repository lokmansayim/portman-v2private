"""BK-37 · Mühendis paftasının H profil montaj planından profil kartı: birleşim yerleri (cm, kaydın çerçevesinde) ve türleri.

`araclar/birlesim_hakemi.py`'nin hedef değerlerini (`testler/havuz/profil_kartlari.json` › `evler`) yazar. Pafta depoya girmez; araç
Drive'dan indirilmiş paftayla yerelde koşulur, dosyanın SHA-256'sı karta yazılır (mühür: `docs/notlar/2026-10-18_AIPrefabrik_muhur.md`).
LLM yok; okuma PyMuPDF'in çizim ve yazı listesinden (`testler/kimlik/hakem/pafta_oku.py`'nin yardımcıları).

Okuma:
1. Sayfa: başlığı "H PROFİL MONTAJ PLANI" (ya da "H YERLEŞİM PLANI") olan sayfa. Yoksa kart "okunamadi" yazar.
2. Lejant: "H (DÜBELLİ & KULAKLI)" gibi her yazının solundaki (ya da üstündeki) dairenin rengi o türdür; 3'LÜ ve 4'LÜ önekleri.
   Lejantın kendi daireleri plandan çıkarılır. Paftalar renk düzeninde ayrışır; renk paftadan okunur, sabit değildir.
3. Hizalama: dairelerin çerçevesi önce bir renk grubunun kutusundan (en-boy oranı kaydın ölçüsüne uyan), olmazsa ölçek taramasıyla
   (0,30–0,70 pt/cm) bulunur; sekiz yön ve öteleme kaydın pano ekleri ve birleşimleriyle oylanır (8 cm pay). En çok eşleşen seçilir;
   eşleşme oranı karta yazılır. Paftanın yönü kaydınkinden farklı olabilir (ayna, dönme).
4. Tür: daire 3'lü ya da 4'lü H ise "uclu_h" / "dortlu_h", öteki H'lar "h"; paftanın kendi adı `pafta_turu`'nda.

    python3 araclar/profil_karti.py --pafta-dizini <dizin> PA-08 PA-26      # dizinde AP01.pdf, AP08.pdf ...
    python3 araclar/profil_karti.py --pafta-dizini <dizin> hepsi --yaz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
for _y in (KOK, KOK / "testler" / "kimlik" / "hakem"):
    if str(_y) not in sys.path:
        sys.path.insert(0, str(_y))

import pafta_oku as PO  # noqa: E402
from araclar import birlesim_hakemi as BH  # noqa: E402

H_BASLIK = re.compile(r"H (PROFİL |PROFIL |DÜBEL )?(MONTAJ|YERLEŞİM) (PLANI|DETAYI)")
H_ETIKET = re.compile(r"(3'LÜ|4'LÜ)?H\(?(DÜBELLİ&KULAKLI|DÜBELLİ|STANDART)\)?")
ONEK = {None: "", "3'LÜ": "uclu_", "4'LÜ": "dortlu_"}
HIZA_TOL_CM = 8.0
TURETILMIS = ("D-91", "D-92")                  # standart hâl, silme ve büyüme hâli: pano dizisi bilerek paftadan ayrılır


def h_sayfasi(doc) -> int | None:
    for i, pg in enumerate(doc):
        if any(H_BASLIK.fullmatch(PO._norm(t)) for t, _ in PO._satirlar(pg)):
            return i
    return None


def lejant(pg, daire) -> tuple[dict, set]:
    """renk → paftanın tür adı (ör. "uclu_dubelli_kulakli"); lejantın kendi daireleri (plandan çıkarılır)."""
    renk_turu, lej = {}, set()
    satir = [(PO._norm(t), r) for t, r in PO._satirlar(pg)]
    for t, r in satir:                                       # satır lejantı: daire yazının solunda
        m = H_ETIKET.fullmatch(t.replace(" ", ""))
        if not m:
            continue
        tur = ONEK[m.group(1)] + PO.H_TURU[m.group(2)]
        cy = (r.y0 + r.y1) / 2
        aday = [c for c in daire if abs(c[2] - cy) <= 14 and c[1] < r.x0 and r.x0 - c[1] <= 160]
        if aday:
            c = min(aday, key=lambda c: r.x0 - c[1])
            if renk_turu.get(c[0], tur) == tur:
                renk_turu[c[0]] = tur; lej.add(c)
    for c in daire:                                          # başlık tablosu: daire üstte, ad altında birkaç satıra bölünmüş
        if c in lej:
            continue
        alt = sorted([(r.y0, t) for t, r in satir if abs((r.x0 + r.x1) / 2 - c[1]) <= 30 and 0 < r.y0 - c[2] <= 70], key=lambda a: a[0])
        m = H_ETIKET.match("".join(t for _, t in alt).replace(" ", ""))
        if m and (c[0] not in renk_turu or renk_turu[c[0]] == ONEK[m.group(1)] + PO.H_TURU[m.group(2)]):
            renk_turu.setdefault(c[0], ONEK[m.group(1)] + PO.H_TURU[m.group(2)]); lej.add(c)
    return renk_turu, lej


def _kutular(pg) -> dict:
    rm, k = pg.rotation_matrix, {}
    for d in pg.get_drawings():
        if any(it[0] == "c" for it in d["items"]):
            continue
        r = d["rect"] * rm
        if r.width < 0.5 and r.height < 0.5:
            continue
        k.setdefault(PO._renk(d.get("color") or d.get("fill")), []).append(r)
    return k


def _donustur(p, W, H, o):
    x, y = p
    if o & 4:
        x, y, W, H = y, x, H, W
    if o & 1:
        x = W - x
    if o & 2:
        y = H - y
    return x, y


def _hizala(pts, W, H, ref):
    en = (-1, 0, 0.0, 0.0)
    for o in range(8):
        tp = [_donustur(p, W, H, o) for p in pts]
        oy = Counter((round((b[0] - a[0]) / 2) * 2, round((b[1] - a[1]) / 2) * 2) for a in tp for b in ref)
        for (dx, dy), _ in oy.most_common(5):
            n = sum(1 for a in tp if any(abs(a[0] + dx - b[0]) <= HIZA_TOL_CM and abs(a[1] + dy - b[1]) <= HIZA_TOL_CM for b in ref))
            if n > en[0]:
                en = (n, o, float(dx), float(dy))
    return en


def oku(pdf: Path, ie: dict) -> dict:
    """Paftanın H planı → kart girdisi (kaydın çerçevesinde)."""
    import pymupdf as fitz
    doc = fitz.open(pdf)
    kart = {"pafta_sha256": hashlib.sha256(Path(pdf).read_bytes()).hexdigest()}
    i = h_sayfasi(doc)
    if i is None:
        return {**kart, "okunamadi": "paftada H profil montaj planı yok"}
    pg = doc[i]
    daire = PO._daireler(pg)
    rt, lej = lejant(pg, daire)
    td = [c for c in daire if c[0] in rt and c not in lej]
    k = BH.kayit_birlesimleri(ie)
    ref = [e["xy"] for e in k["ekler"]] + [c["xy"] for c in k["cektirme_u"]] + k["koseler"]
    adaylar = []
    # (a) çerçeve: oranı kaydın ölçüsüne uyan renk grubu kutusu
    for renk, rs in _kutular(pg).items():
        if renk in rt or len(rs) < 8:
            continue
        x0, y0, x1, y1 = min(r.x0 for r in rs), min(r.y0 for r in rs), max(r.x1 for r in rs), max(r.y1 for r in rs)
        if x1 - x0 < 100 or y1 - y0 < 100:
            continue
        for W, H in ((k["W"], k["H"]), (k["H"], k["W"])):
            sx, sy = (x1 - x0) / W, (y1 - y0) / H
            if abs(sx - sy) / sx < 0.025:
                pts = [((c[1] - x0) / sx, (y1 - c[2]) / sy) for c in td]
                n, o, dx, dy = _hizala(pts, W, H, ref)
                adaylar.append((n, "cerceve", round((sx + sy) / 2, 4), o, dx, dy, pts, W, H))
    # (b) ölçek taraması
    if td:
        x0, y1 = min(c[1] for c in td), max(c[2] for c in td)
        s = 0.30
        while s <= 0.70:
            pts = [((c[1] - x0) / s, (y1 - c[2]) / s) for c in td]
            W, H = max(p[0] for p in pts), max(p[1] for p in pts)
            n, o, dx, dy = _hizala(pts, W, H, ref)
            adaylar.append((n, "olcek", round(s, 3), o, dx, dy, pts, W, H))
            s += 0.004
    if not adaylar:
        return {**kart, "sayfa": i + 1, "okunamadi": "H planında birleşim dairesi okunamadı"}
    n, yontem, olcek, o, dx, dy, pts, W, H = max(adaylar, key=lambda a: (a[0], a[1] == "cerceve"))
    h = []
    for c, p in zip(td, pts):
        x, y = _donustur(p, W, H, o)
        x, y = x + dx, y + dy
        if not (-30 <= x <= k["W"] + 30 and -30 <= y <= k["H"] + 30):
            continue
        t = rt[c[0]]
        h.append({"xy": [round(x, 1), round(y, 1)], "tur": "uclu_h" if t.startswith("uclu_") else "dortlu_h" if t.startswith("dortlu_") else "h",
                  "pafta_turu": t})
    h.sort(key=lambda a: (a["xy"][1], a["xy"][0]))
    return {**kart, "sayfa": i + 1, "hiza": {"yontem": yontem, "olcek_pt_cm": olcek, "yon": o, "dx_cm": dx, "dy_cm": dy,
                                             "eslesen": n, "daire": len(td)}, "h": h}


def kaynak_kart(kod: str) -> str | None:
    """Havuz kodunun proje kartı (AP-NN): havuz kaydından ya da aday listesinin kaynak yazısından."""
    y = KOK / "beyin" / "veri" / "havuz" / f"{kod.replace('-', '')}.json"
    if y.exists():
        return json.loads(y.read_text(encoding="utf-8"))["kaynak"]["kart_kiyasi"]["kart"]
    for a in json.loads((KOK / "beyin" / "veri" / "adaylar_prefabrik.json").read_text(encoding="utf-8")):
        if a.get("kod", "").replace("-", "") == kod.replace("-", ""):
            m = re.search(r"(AP-\d\d) montaj paftasından", (a.get("kaynak") or {}).get("metin", ""))
            return m.group(1) if m else None
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kodlar", nargs="+", help="havuz kodları (PA-08) ya da hepsi (paftası olan ve kaynak evi olmayan kayıtlar)")
    ap.add_argument("--pafta-dizini", required=True, help="APnn.pdf dosyalarının dizini (montaj paftası)")
    ap.add_argument("--yaz", action="store_true", help="kartı testler/havuz/profil_kartlari.json › evler'e yaz")
    a = ap.parse_args(argv)
    if a.kodlar == ["hepsi"]:
        kodlar = sorted({f"PA-{p.stem[2:]}" for p in (KOK / "is_emri" / "adaylar").glob("PA[0-9][0-9].json")})
    else:
        kodlar = [BH.kod_yaz(k) for k in a.kodlar]
    K = BH.kartlar() if BH.KARTLAR.exists() else {"evler": {}, "farklar": {}}
    for kod in kodlar:
        ie_y = BH.is_emri_yolu(kod)
        ie = json.loads(ie_y.read_text(encoding="utf-8"))
        kk = kaynak_kart(kod)
        havuz = KOK / "beyin" / "veri" / "havuz" / f"{kod.replace('-', '')}.json"
        if havuz.exists() and (json.loads(havuz.read_text(encoding="utf-8")).get("kaynak") or {}).get("karar") in TURETILMIS:
            print(f"{kod}: atlandı (standart, silinmiş ya da büyümüş hâl; kaynak evi kıyaslanır)"); continue
        pdf = Path(a.pafta_dizini) / f"{(kk or '').replace('-', '')}.pdf"
        if not kk or not pdf.exists():
            print(f"{kod}: atlandı (paftası yok: {kk or 'proje kartı yok'})"); continue
        r = {"kart": kk, **oku(pdf, ie)}
        hz = r.get("hiza") or {}
        print(f"{kod} {kk}: " + (r["okunamadi"] if r.get("okunamadi") else
                                 f"{len(r['h'])} birleşim, eşleşen {hz['eslesen']}/{hz['daire']} ({hz['yontem']}, yön {hz['yon']})"))
        K["evler"][kod] = r
    if a.yaz:
        BH.kartlari_yaz(K)
        print(f"yazıldı: {BH.KARTLAR.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
