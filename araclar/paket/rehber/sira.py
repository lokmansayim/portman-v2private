"""Montaj sırası hakemi: montaj rehberinde sonra gelen ve öncekini örten parça, örttüğü parçaların üstünde mi (Lokman, 10 Kasım 2026 20:16:
"önce trapez sac ve mahya gelir sonra alın sacı üzerini örter"; 20:17: "en küçük adımlarla gidelim çizgi çizgi gidelim").

Kurallar `kurallar/rehber/montaj_sirasi.json`'da, her biri tek ilişki (MS-01: alın sacı trapez sacı ve mahyayı örter). Denetim `sira.js`
(Playwright): üst parçanın içinden noktalar, her noktadan çatı yüzüne dik doğrultuda yukarı ışın; ışın bir alt parçaya çarparsa bulgu.
Geometriyi değiştirmez, yalnız okur. Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister (`iz.hazir`).

    THREE_DIR=<three@0.160.0> python -m araclar.paket.rehber.sira <veri.json> [--html <rehber.html>] [--json <sonuç.json>]

Çıkış 0: bulgu yok; 1: bulgu var (anahtarlar yazılır).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

D = Path(__file__).resolve().parent
KOK = D.parents[2]
JS = D / "sira.js"
KURAL = KOK / "kurallar" / "rehber" / "montaj_sirasi.json"


def kurallar() -> list[dict]:
    return json.loads(KURAL.read_text(encoding="utf-8"))["kurallar"]


def coz(d: dict, ks: list[dict] | None = None) -> list[dict]:
    """Kuralların adımlarını rehber verisinin adım yerlerinden (`d["S"]`) çözer; verisinde o adım olmayan kural atlanmaz, hata verir."""
    S = d["S"]
    out = []
    for k in ks or kurallar():
        eksik = [k[y]["adim"] for y in ("ust", "alt") if k[y]["adim"] not in S]
        if eksik:
            raise KeyError(f"{k['no']}: rehber verisinde adım yok: {', '.join(eksik)}")
        out.append({"no": k["no"], "ust": {**k["ust"], "adim": S[k["ust"]["adim"]]}, "alt": {**k["alt"], "adim": S[k["alt"]["adim"]]}})
    return out


def denetle(d: dict, html: Path, ks: list[dict] | None = None) -> dict:
    """Sayfayı (`html`, `d`'den yazılmış) kurallarla denetler: {"kurallar": [{no, ust_parca, alt_parca, nokta, bulgular}], "hatalar"}."""
    with tempfile.TemporaryDirectory() as t:
        kj, cj = Path(t) / "k.json", Path(t) / "c.json"
        kj.write_text(json.dumps(coz(d, ks), ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["node", str(JS), str(Path(html).resolve()), str(kj), str(cj)], capture_output=True, text=True, timeout=900,
                           env={**os.environ})
        if r.returncode:
            raise RuntimeError(r.stderr[-2500:])
        return json.loads(cj.read_text(encoding="utf-8"))


def anahtar(no: str, b: dict) -> str:
    """Bulgunun kısa adı: kural · üst parçanın yeri (kalkan ve yüz) · üstüne binen parçanın türü (mahya ya da kaplama)."""
    yer = b["ust_bu"].split(" · alın")[0]
    tur = "mahya" if "mahya" in b["alt_ad"].lower() else "kaplama"
    return f"{no} · {yer} · {tur} üstünde"


def anahtarlar(sonuc: dict) -> dict[str, int]:
    """Bulgu anahtarı → nokta sayısı (aynı anahtarlı bulgular toplanır)."""
    out: dict[str, int] = {}
    for k in sonuc["kurallar"]:
        for b in k["bulgular"]:
            a = anahtar(k["no"], b)
            out[a] = out.get(a, 0) + b["nokta"]
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    from araclar.paket.rehber import iz, sayfa
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("veri", type=Path, help="rehber verisi (veri.py'nin çıktısı ya da testler/paket/rehber62/veri.json)")
    ap.add_argument("--html", type=Path, default=None, help="yazılacak sayfa (verilmezse geçici)")
    ap.add_argument("--json", type=Path, default=None, help="sonucun tamamı (işaret noktalarıyla)")
    a = ap.parse_args(argv)
    neden = iz.hazir()
    if neden:
        sys.exit(f"hakem koşamaz: {neden}")
    d = json.loads(a.veri.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        html = sayfa.yaz(d, a.html or Path(t) / "rehber.html")
        s = denetle(d, html)
    if a.json:
        a.json.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in s["kurallar"]:
        print(f"{k['no']}: üst parça {k['ust_parca']}, alt parça {k['alt_parca']}, nokta {k['nokta']}, bulgu {len(k['bulgular'])}")
    for a_, n in anahtarlar(s).items():
        print(f"  BULGU {a_} ({n} nokta)")
    if s["hatalar"]:
        print("sayfa hatası:", s["hatalar"][:3])
    return 1 if (anahtarlar(s) or s["hatalar"]) else 0


if __name__ == "__main__":
    sys.exit(main())
