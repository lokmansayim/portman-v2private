"""İE-18 · Montaj rehberi sayfası: kabuk.html (62 m² rehberinin arayüzü) + sahne.js (tek şablon) + veri → tek dosya HTML.

    python -m araclar.paket.rehber.sayfa <veri.json> <çıktı.html>

Veri `veri.py`'den (motorun planı ve kimlik kartlı modeli) ya da hedef örnekten (`testler/paket/rehber62/veri.json`) gelir.
Başlık, rozet, özellik satırı ve kaynak notu verinin `kabuk` alanından; yerleştirme sırası 62 m²'nin `uret.py`'siyle aynı
(önce sahne ve veri, sonra başlık ve proje adı; proje adı verinin içindeki `__PROJE__` yerlerini de doldurur).
three.js 0.160.0 jsDelivr'den yüklenir; GLB'yi `glb.js` yazar (Playwright); galerinin görsellerini `galeri.py` (Blender) sayfaya gömer.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent


def metin(d: dict, gorseller: list | None = None) -> str:
    """`gorseller`: galerinin [[src, başlık], …]'ı (`galeri.uret`; boşsa "Render görselleri" düğmesi görünmez)."""
    k = d["kabuk"]
    s = (D / "kabuk.html").read_text(encoding="utf-8").replace("__SCRIPT__", (D / "sahne.js").read_text(encoding="utf-8"))
    s = s.replace("__DATA__", json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    gal = json.dumps(gorseller or [], ensure_ascii=False).replace("</", "<\\/")
    s = (s.replace("__GORSELLER__", gal).replace("__CHIP__", html.escape(k["chip"], quote=False))
          .replace("__SPEC__", "".join(f"<span>{html.escape(x, quote=False)}</span>" for x in k["spec"]))
          .replace("__NOTE__", html.escape(k["note"], quote=False))
          .replace("__KISA__", k.get("kisa") or k["proje"]).replace("__PROJE__", k["proje"]))
    return s


def yaz(d: dict, cikti: Path, gorseller: list | None = None) -> Path:
    cikti = Path(cikti)
    cikti.write_text(metin(d, gorseller), encoding="utf-8")
    return cikti


if __name__ == "__main__":
    veri, cikti = sys.argv[1:3]
    print(yaz(json.loads(Path(veri).read_text(encoding="utf-8")), Path(cikti)))
