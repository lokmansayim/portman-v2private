"""İE-18 · Rehberin "Render görselleri" galerisi (62 m² rehberindeki gibi): rehberin GLB'si (`glb.js`) → Blender Cycles (`render.py`,
bpy kurulu ayrı bir Python ile) → JPEG'ler, çatı katmanlarında etiketler, hepsi tek paftada → sayfaya gömülü galeri (`sayfa.yaz`).

Blender `BLENDER_PY` ortam değişkeninin gösterdiği Python'dan çağrılır (`pip install bpy==4.5.4`; depo ortamına girmez, CI'da yok).
Yoksa galeri yazılmaz ve neden `bilgi.md`'ye gider. Görseller bilgisayara bağlı değil ama piksel piksel belirlenimci de değil (Cycles);
kıyas testi yok, dayanak 62 m²'nin onaylı galerisi (dal `claude/montaj-rehberi-devir` `6b899b4`, `rehber/gorsel/`).
"""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess
from pathlib import Path

D = Path(__file__).resolve().parent
GORUNUMLER = ("on_sol", "on_sag", "arka_sol", "catisiz", "cati_katman")
VURGU, KOYU = (176, 62, 38), (28, 32, 38)


class Yok(Exception):
    """Galeri yazılamadı; `str(e)` nedendir."""


def sahne(d: dict) -> dict:
    """`render.py`'nin sahnesi rehberin verisinden: dış ölçü, temel plak, çatısız görünüşte gizlenen adımlar (çatıyı kuran adımlar:
    duvar ve baş makas omegasından alın sacına; 62 m²'de 8–19, Lokman'ın sırası)."""
    S = d["S"]
    return {"dis": d["dis"], "zemin": d["zemin"], "catisiz": list(range(S["omega"], S["alin"] + 1)), "gorunumler": list(GORUNUMLER)}


def _kaplama(d: dict) -> str:
    return ((d.get("kaplama") or {}).get("metin") or {}).get("say_onek") or "Çatı kaplaması"


def basliklar(d: dict) -> dict[str, str]:
    kap = _kaplama(d)
    tavan = {"asma": "asma tavanın", "ters": "ters tavanın"}.get((d.get("tavan") or {}).get("tip"), "tavanın")
    return {
        "on_sol": "Ön-soldan: montajı biten ev (ham malzeme; boya ve sıva yok)",
        "on_sag": "Ön-sağdan: veranda, saçak, dere ve inişler",
        "arka_sol": "Arka-soldan: kalkan, alın sacı ve inişler",
        "catisiz": "Çatısız: oda oda dizilim, iç kapılar, pencereler ve dış kapı",
        "cati_katman": f"Çatı katmanları: makas, omega aşık, {kap.lower()}; {tavan} üstünde 10 cm cam yünü",
        "pafta": "Hepsi tek paftada",
    }


def _font(boy: int):
    from matplotlib import font_manager
    from PIL import ImageFont
    return ImageFont.truetype(font_manager.findfont("DejaVu Sans"), boy)


def etiketle(im, yerler: dict, d: dict):
    """Çatı katmanları görseline etiketler (62 m²'nin paftasındaki gibi: noktadan kutuya çizgi)."""
    from PIL import ImageDraw
    kap = _kaplama(d)
    metin = {"roof": f"{kap} (doğrudan aşıkta)", "asik": "Omega aşık", "izocam": "Cam yünü 10 cm (rulo)", "truss": "Makas"}
    dr = ImageDraw.Draw(im); f = _font(max(14, im.width // 70))
    W = im.width
    kutular = []
    for k, (x, y) in sorted(yerler.items(), key=lambda t: t[1][1]):
        if k not in metin:
            continue
        bb = dr.textbbox((0, 0), metin[k], font=f); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        sag = x > W * 0.55
        kx = min(W - tw - 40, x + W * 0.12) if sag else max(16, x - W * 0.12 - tw - 24)
        ky = max(16, y - im.height * 0.12)
        for _ in range(20):                                   # üst üste binmesin
            if all(abs(ky - y2) > th + 24 or abs(kx - x2) > tw + 40 for x2, y2 in kutular):
                break
            ky += th + 26
        kutular.append((kx, ky))
        kx1, ky1 = kx + tw + 24, ky + th + 16
        dr.line([(x, y), (kx if sag else kx1, (ky + ky1) / 2)], fill=VURGU, width=2)
        dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=VURGU)
        dr.rounded_rectangle([kx, ky, kx1, ky1], radius=6, fill=(255, 255, 255), outline=VURGU, width=2)
        dr.text((kx + 12, ky + 8 - bb[1]), metin[k], fill=KOYU, font=f)
    return im


def pafta(resimler: dict, basl: dict, baslik: str):
    """Beş görünüş tek paftada: iki sütun, çatı katmanları altta tam genişlikte; her görselin sol üstünde adı."""
    from PIL import Image, ImageDraw
    w = 1000; h = round(w * 0.625)
    sira = ["on_sol", "on_sag", "arka_sol", "catisiz"]
    ust = 90
    tam_h = round(2 * w * 0.625)
    P = Image.new("RGB", (2 * w, ust + 2 * h + tam_h), (246, 245, 242))
    dr = ImageDraw.Draw(P)
    dr.text((24, 26), baslik, fill=KOYU, font=_font(34))
    f = _font(18)

    def koy(ad, x, y, ww, hh):
        P.paste(resimler[ad].resize((ww, hh)), (x, y))
        t = basl[ad].split(":")[0]
        bb = dr.textbbox((0, 0), t, font=f)
        dr.rounded_rectangle([x + 14, y + 14, x + 38 + bb[2] - bb[0], y + 30 + bb[3] - bb[1]], radius=6, fill=(255, 255, 255))
        dr.text((x + 26, y + 22 - bb[1]), t, fill=KOYU, font=f)
    for i, ad in enumerate(sira):
        koy(ad, (i % 2) * w, ust + (i // 2) * h, w, h)
    koy("cati_katman", 0, ust + 2 * h, 2 * w, tam_h)
    return P


def _uri(im, kalite=84) -> str:
    b = io.BytesIO(); im.save(b, "JPEG", quality=kalite, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def uret(glb: Path, d: dict, gec: Path, ornek: int = 64, olcek: float = 1.0, zaman: int = 3600) -> list[list[str]]:
    """Galerinin görselleri: [[data URI, başlık], …] (62 m²'nin `GORSELLER` biçimi). Blender yoksa ya da hata verirse `Yok`."""
    from PIL import Image
    py = os.environ.get("BLENDER_PY")
    if not py:
        raise Yok("BLENDER_PY (bpy kurulu Python) bu ortamda yok")
    k = Path(gec) / "render"; k.mkdir(parents=True, exist_ok=True)
    (k / "sahne.json").write_text(json.dumps(sahne(d)), encoding="utf-8")
    try:
        r = subprocess.run([py, str(D / "render.py"), str(Path(glb).resolve()), str(k / "sahne.json"), str(k), str(ornek), str(olcek)],
                           capture_output=True, text=True, timeout=zaman)
    except subprocess.TimeoutExpired:
        raise Yok(f"Blender {zaman} sn'de bitmedi") from None
    eksik = [a for a in GORUNUMLER if not (k / f"{a}.png").exists()]
    if r.returncode != 0 or eksik:
        raise Yok(f"Blender hata verdi ({r.returncode}; eksik {', '.join(eksik) or '—'}): {(r.stderr or r.stdout).strip()[-200:]}")
    basl = basliklar(d)
    res = {a: Image.open(k / f"{a}.png").convert("RGB") for a in GORUNUMLER}
    yer = k / "cati_katman.json"
    if yer.exists():
        res["cati_katman"] = etiketle(res["cati_katman"], json.loads(yer.read_text(encoding="utf-8")), d)
    out = [[_uri(res[a]), basl[a]] for a in GORUNUMLER]
    out.append([_uri(pafta(res, basl, f"{d.get('kod', '')} · render görselleri"), 80), basl["pafta"]])
    return out
