"""BK-42 · Kayıtlı prefabrik aday resmini (`is_emri/adaylar/<kod>.png`, bayinin seçenek kartı) bugünkü koddan yeniden çizer.

    python3 araclar/aday_gorseli_yenile.py PA09 PA36 … [--yazi-tipi sunucu|makine] [--kuru]

`aday_kaydet.py`'nin resim adımının aynısı (D-28 madde 1: tek kod): kayıtlı İş Emri (`is_emri/adaylar/<kod>.json`) → Motor doğrulaması
(`dxf_out.uret`, geçici klasörde; geçmezse durur, K23) → `bayi_gorseli.plan_gorseli`. İş Emri'ne, aday kaydına (`beyin/veri/…`) ve
öteki dosyalara dokunmaz. `is_emri/` korunan klasördür: değişen resim PR'da Lokman'ın `patron-onayi` etiketini ister (BK-21).

Yazı tipi: kayıtlı resimlerin çoğu bulut konteynerinde makinenin matplotlib ayarıyla (Inter) çizildi, bazıları sunucunun yazı tipiyle
(DejaVu Sans). Kodun değişikliğinden başka bir şey değişmesin diye her resim çizildiği yazı tipiyle yeniden çizilir: `sunucu` = DejaVu
Sans (sunucu ve CI; `testler/motor/test_bayi_gorseli_yazi.py` ile aynı ayar), `makine` = makinenin ayarı. `--kuru` dosya yazmaz.
Her resim için eski ve yeni SHA-256'nın ilk 12 hanesi ve değişen piksel sayısı yazılır. LLM, ağ ve sunucu yok.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, sys, tempfile
from contextlib import nullcontext
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

ADAY_DIR = KOK / "is_emri" / "adaylar"
SUNUCU_YAZI_TIPI = {"font.family": ["sans-serif"], "font.sans-serif": ["DejaVu Sans"], "text.hinting": "default"}


def yeniden_ciz(kod: str, hedef: Path, yazi_tipi: str = "sunucu") -> Path:
    """Kayıtlı İş Emri'nden aday resmini `hedef`e çizer (aday_kaydet.py'deki gibi: Motor doğrulamasının net alanlarıyla)."""
    import matplotlib
    from motor import dxf_out, bayi_gorseli as BG
    ie = json.loads((ADAY_DIR / f"{kod}.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        dxf_out.uret(copy.deepcopy(ie), Path(t))
        v = json.loads((Path(t) / "validation.json").read_text(encoding="utf-8"))
    if not v.get("passed"):
        raise SystemExit(f"DUR: {kod} Motor doğrulamasından geçmedi (K23): {v.get('errors')}")
    with matplotlib.rc_context(SUNUCU_YAZI_TIPI) if yazi_tipi == "sunucu" else nullcontext():
        return BG.plan_gorseli(copy.deepcopy(ie), hedef, v)


def _degisen_piksel(a: Path, b: Path) -> int:
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return -1
    fark = ImageChops.difference(ia, ib).convert("L").point(lambda p: 255 if p else 0)
    return fark.histogram()[255]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kodlar", nargs="+", help="kayıt kodu (PA09) ya da bayinin gördüğü kod (PA-09)")
    ap.add_argument("--yazi-tipi", choices=["sunucu", "makine"], default="sunucu")
    ap.add_argument("--kuru", action="store_true", help="dosya yazma; yalnız farkı söyle")
    a = ap.parse_args()
    for ham in a.kodlar:
        kod = ham.strip().upper().replace("-", "")
        eski = ADAY_DIR / f"{kod}.png"
        if not (ADAY_DIR / f"{kod}.json").exists():
            print(f"DUR: {kod}: is_emri/adaylar/{kod}.json yok"); return 2
        with tempfile.TemporaryDirectory() as t:
            yeni = yeniden_ciz(kod, Path(t) / f"{kod}.png", a.yazi_tipi)
            ozet = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else "yok"
            n = _degisen_piksel(eski, yeni) if eski.exists() else -1
            print(f"{kod}: eski {ozet(eski)} → yeni {ozet(yeni)} · değişen piksel {n}" + (" (aynı)" if n == 0 else ""))
            if not a.kuru and n != 0:
                eski.write_bytes(yeni.read_bytes())
    return 0


if __name__ == "__main__":
    sys.exit(main())
