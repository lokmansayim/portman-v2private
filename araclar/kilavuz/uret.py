"""BK-92 (D-169) · Portman WhatsApp kullanma kılavuzu (etkileşimli ekran): python -m araclar.kilavuz <çıktı.html>

`kilavuz.json` (açıklama, ipucu, bayinin yazdıkları) + `senaryo.uret` (Portman'ın mesajları, düğmeleri, PDF adları ve resimleri; main'deki
karar koduyla, D-28) + `sablon.html` → tek dosya HTML. Resimler JPEG olarak gömülür (Portman'ın /rehber/ CSP'si: img-src data:), yazı tipi
Google Fonts'tan. Yayın: Lokman `vps/rehber_yayinla.sh` ile (kanal/rehber_yayin.py kılavuzu da denetler). Hedef örnek
`testler/kilavuz/hedef.json`, kıyas `testler/test_kilavuz.py`: Portman'ın bir mesajı değişirse test kırmızı olur ve kılavuz yeniden bakılır.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import tempfile
from pathlib import Path

from . import senaryo

KLASOR = Path(__file__).resolve().parent
METIN = KLASOR / "kilavuz.json"
SABLON = KLASOR / "sablon.html"
GORSEL_ENI = {"set": 800, "plan": 700, "cati": 800, "r02": 700, "kaynak": 800, "yerlesim": 700, "plan3": 700}
NO_DESENI = re.compile(r"PM-[A-Z0-9]+-\d{8}-\d+")


def ogeleri_coz(metin: dict, m: dict) -> dict:
    """kilavuz.json'daki 'kaynak' anahtarlarını senaryonun mesajlarıyla doldurur. Dönen: şablonun okuduğu VERI."""
    def kay(o):
        a = o.get("kaynak") or o.get("dugme_metni")
        if a not in m:
            raise senaryo.KilavuzHatasi(f"kılavuzda bilinmeyen kaynak: {a}")
        return m[a]

    def sira(o, b):
        if "dugme" in o:
            ids = [x["id"] for x in b["butonlar"]]
            if o["dugme"] not in ids:
                raise senaryo.KilavuzHatasi(f"düğme yok: {o['dugme']} ({ids})")
            return ids.index(o["dugme"])
        if o["sira"] >= len(b["butonlar"]):
            raise senaryo.KilavuzHatasi(f"{o.get('kaynak') or o.get('dugme_metni')}: {o['sira'] + 1}. düğme yok")
        return o["sira"]

    bolumler = []
    for bl in metin["bolumler"]:
        adimlar = []
        for a in bl["adimlar"]:
            og = []
            for o in a["ogeler"]:
                t = o["tur"]
                if t == "yaziyor":
                    og.append({"tur": t})
                elif t == "sec":
                    og.append({"tur": t, "sira": sira(o, kay(o))})
                elif t == "btns":
                    b = kay(o)["butonlar"]
                    if not b:
                        raise senaryo.KilavuzHatasi(f"{o['kaynak']}: düğme beklenirdi")
                    og.append({"tur": t, "liste": [x["baslik"] for x in b]})
                elif t == "out" and "dugme_metni" in o:
                    b = kay(o)
                    og.append({"tur": "out", "metin": b["butonlar"][sira(o, b)]["baslik"], "saat": o["saat"]})
                elif t == "out":
                    og.append({k: o[k] for k in ("tur", "metin", "saat", "img") if k in o})
                elif t == "in":
                    og.append({"tur": "in", "metin": kay(o)["metin"], "saat": o["saat"], **({"img": o["img"]} if "img" in o else {})})
                elif t == "doc":
                    pdf = kay(o).get("pdf")
                    if not pdf:
                        raise senaryo.KilavuzHatasi(f"{o['kaynak']}: PDF beklenirdi")
                    og.append({"tur": "in", "doc": pdf, "metin": "", "saat": o["saat"]})
                else:
                    raise senaryo.KilavuzHatasi(f"bilinmeyen öge türü: {t}")
            adim = {"baslik": a["baslik"], "metin": a["metin"], "ogeler": og}
            if a.get("ipucu"):
                adim["ipucu"] = a["ipucu"]
            adimlar.append(adim)
        bolumler.append({"baslik": bl["baslik"], "adimlar": adimlar})
    return {"bolumler": bolumler}


def hedef_ozeti(m: dict) -> dict:
    """Kıyas için: Portman'ın mesajları ve düğme başlıkları; talep numarası '<NO>' (tarih ve sıra her koşuda değişir)."""
    return {a: {"metin": NO_DESENI.sub("<NO>", v["metin"]), "butonlar": [b["baslik"] for b in v["butonlar"]],
                **({"pdf": NO_DESENI.sub("<NO>", v["pdf"])} if v.get("pdf") else {})} for a, v in sorted(m.items())}


def _jpeg(yol: Path, en: int) -> str:
    from PIL import Image
    im = Image.open(yol).convert("RGB")
    if im.width > en:
        im = im.resize((en, round(im.height * en / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def sayfa(gorseller: Path | None = None) -> tuple[str, dict]:
    """Dönen: (index.html metni, senaryonun mesajları)."""
    with tempfile.TemporaryDirectory(prefix="kilavuz_gorsel_") as d:
        g = Path(gorseller or d)
        g.mkdir(parents=True, exist_ok=True)
        m = senaryo.uret(gorseller=g)
        veri = ogeleri_coz(json.loads(METIN.read_text(encoding="utf-8")), m)
        kullanilan = {o["img"] for b in veri["bolumler"] for a in b["adimlar"] for o in a["ogeler"] if "img" in o}
        yollar = {ad: g / f"{ad}.png" for ad in kullanilan}
        yollar["kaynak"] = senaryo.CIZIM
        eksik = sorted(ad for ad in kullanilan if not yollar[ad].exists())
        if eksik:
            raise senaryo.KilavuzHatasi(f"resim üretilmedi: {', '.join(eksik)}")
        img = {ad: _jpeg(yollar[ad], GORSEL_ENI.get(ad, 700)) for ad in sorted(kullanilan)}
    s = SABLON.read_text(encoding="utf-8")
    for yer, deger in (("__VERI__", veri), ("__GORSELLER__", img)):
        if s.count(yer) != 1:
            raise senaryo.KilavuzHatasi(f"şablonda {yer} bir kez olmalı")
        s = s.replace(yer, json.dumps(deger, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    return s, m


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m araclar.kilavuz", description=__doc__.split("\n")[0])
    ap.add_argument("cikti", type=Path, help="yazılacak HTML (ör. portman_whatsapp_kilavuzu.html)")
    ap.add_argument("--gorseller", type=Path, help="ara resimlerin (PNG) kalacağı klasör")
    a = ap.parse_args(argv)
    try:
        s, m = sayfa(a.gorseller)
    except senaryo.KilavuzHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    sys.path.insert(0, str(senaryo.DEPO / "kanal"))
    import rehber_yayin
    sorun, bilgi = rehber_yayin.denetle(s.encode("utf-8"))
    if sorun:
        print("HATA: yayın denetimi: " + "; ".join(sorun), file=sys.stderr)
        return 1
    a.cikti.write_text(s, encoding="utf-8")
    print(f"{a.cikti} · {bilgi['boyut'] / 1e3:.0f} KB · sha256 {bilgi['sha256'][:16]}… · {bilgi.get('baslik')} · {len(m)} Portman mesajı")
    return 0
