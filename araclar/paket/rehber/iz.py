"""Rehber sayfasının izi (`iz.js`, Playwright): her parçanın adımı, sırası, kartı, yazısı ve dünya koordinatındaki köşeleri; adımların
metni, satırları ve kamerası; sayfa hataları. Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister.

    THREE_DIR=<three@0.160.0> python -m araclar.paket.rehber.iz <rehber.html> <iz.json>
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

JS = Path(__file__).with_name("iz.js")


def hazir() -> str | None:
    """İz için gereken araçlar var mı; eksikse nedeni."""
    if not shutil.which("node"):
        return "node yok"
    t = os.environ.get("THREE_DIR")
    if not t or not (Path(t) / "build" / "three.module.js").exists():
        return "THREE_DIR (three.js 0.160.0) yok"
    if json.loads((Path(t) / "package.json").read_text(encoding="utf-8"))["version"] != "0.160.0":
        return "THREE_DIR'deki three.js 0.160.0 değil"
    if subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode:
        return "Playwright yok"
    return None


def al(html: Path, cikti: Path) -> dict:
    r = subprocess.run(["node", str(JS), str(Path(html).resolve()), str(Path(cikti).resolve())], capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return json.loads(Path(cikti).read_text(encoding="utf-8"))


if __name__ == "__main__":
    neden = hazir()
    if neden:
        sys.exit(f"iz alınamaz: {neden}")
    z = al(Path(sys.argv[1]), Path(sys.argv[2]))
    print(sys.argv[2], "parça", z["parca"], "adım", len(z["adimlar"]), "hata", len(z["hatalar"]))
