"""Bayiye giden plan görseli (İE-08 A3; İE-05 devir §3.1 kural 1): genel motorun planı, çevresinde ÖN (GİRİŞ) / ARKA / SOL / SAĞ
etiketleri, başlıkta kod · m² · oda. Yön kuralı `sahne.py`: +y kuzey, ön cephe güneyde (planda altta).

Çizim seti baytlarına dokunmaz: plan `ciz_genel.plan_eksen` ile **yeni** bir figüre çizilir. Çıktı `<kod>_plan_bayi.png` (≤ 5 MB;
WhatsApp görsel sınırı). Seçenek bileşik görseli (`motor/bayi_gorseli.bilesik_gorsel`) bu PNG'yi okur.

    python -m motor.genel.bayi_gorseli modeller/C8801.json <çıktı klasörü> [--yontem panel|omega_asik] [--set <kural seti>]
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)
import argparse
import json
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
ETIKET = {"on": "ÖN (GİRİŞ)", "arka": "ARKA", "sol": "SOL", "sag": "SAĞ"}


def oda_programi(t: dict) -> str:
    yatak = sum(1 for m in t.get("mahaller", []) if "yatak" in " ".join(m.get("islev", [])).lower() or "yatak" in m["ad"].lower())
    salon = 1 if any("salon" in " ".join(m.get("islev", [])).lower() or "yaşam" in m["ad"].lower() or "salon" in m["ad"].lower() for m in t.get("mahaller", [])) else 0
    return f"{yatak}+{salon}"


def musteri_projesi(t: dict) -> bool:
    """Müşteri projesi (kör test, KT-xx) mi: bayiye adsız sunulur (kod, m², oda programı; D-08). Katalog kodları `[PÇ]\\d{4}[A-Z]?`."""
    return bool(t.get("musteri_projesi")) or str(t.get("kod", "")).upper().startswith("KT")


def plan_bayi(t: dict, hedef: Path, kod: str, is_emri_no: str | None = None, revizyon: int = 1, set_yolu: Path | None = None,
              yontem: str | None = None, sunum: str | None = None) -> Path:
    from . import cati_genel, ciz_genel, girdi_genel, kural, yapi
    import matplotlib.pyplot as plt
    t = json.loads(json.dumps(t))
    if yontem:
        t["cati"]["yontem"] = yontem
    with kural.secili(set_yolu):
        kur = kural.oku()                            # set dosyası var mı (yoksa SystemExit)
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    oturum = girdi_genel.metraj(y, c, kur)["oturum_m2"]      # brüt oturum (dış duvar dış yüzleri; veranda ve sundurma dahil) = listedeki bina_m2 (D-08 K-A1)
    bx0, by0, bx1, by1 = y["kutle"].bounds
    W, H = bx1 - bx0, by1 - by0
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    baslik = sunum or f"{t['kod']} · {oturum:.0f} m² · {oda_programi(t)}"
    ad = "" if musteri_projesi(t) else t.get("ad", "")        # müşteri projeleri bayiye adsız (D-08)
    taslak = f"TASLAK · r{int(revizyon):02d}" + (f" · {is_emri_no}" if is_emri_no else "")
    yol = hedef / f"{kod}_plan_bayi.png"

    def ciz(dpi: int) -> None:                       # aynı çizim; 5 MB'ı aşarsa yalnız çözünürlük düşer, etiketler ve başlık korunur
        fig, ax = plt.subplots(figsize=(11.0, 9.0), dpi=dpi)
        ciz_genel.plan_eksen(ax, y, baslik="\n".join(s for s in (baslik, ad, taslak) if s), olcu_zinciri=True)
        pay = 0.09 * max(W, H)
        kutu = dict(boxstyle="round,pad=0.35", fc="#1f5f93", ec="none")
        ax.text((bx0 + bx1) / 2, by0 - pay, ETIKET["on"], ha="center", va="top", fontsize=12, weight="bold", color="white", bbox=kutu, zorder=20)
        ax.text((bx0 + bx1) / 2, by1 + pay, ETIKET["arka"], ha="center", va="bottom", fontsize=12, weight="bold", color="white", bbox=kutu, zorder=20)
        ax.text(bx0 - pay, (by0 + by1) / 2, ETIKET["sol"], ha="right", va="center", fontsize=12, weight="bold", color="white", bbox=kutu, rotation=90, zorder=20)
        ax.text(bx1 + pay, (by0 + by1) / 2, ETIKET["sag"], ha="left", va="center", fontsize=12, weight="bold", color="white", bbox=kutu, rotation=-90, zorder=20)
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        ax.set_xlim(min(x0, bx0 - 1.6 * pay), max(x1, bx1 + 1.6 * pay)); ax.set_ylim(min(y0, by0 - 1.6 * pay), max(y1, by1 + 1.6 * pay))
        fig.savefig(yol, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    ciz(130)
    if yol.stat().st_size > 5 * 1024 * 1024:            # WhatsApp görsel sınırı: 5 MB
        ciz(90)
    return yol


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path); ap.add_argument("cikti", type=Path)
    ap.add_argument("--yontem", choices=("panel", "omega_asik")); ap.add_argument("--set", type=Path, default=None)
    ap.add_argument("--is-emri-no", default=None); ap.add_argument("--revizyon", type=int, default=1)
    a = ap.parse_args()
    from .uret import matplotlib_sabitle, kod_govde
    matplotlib_sabitle()
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    yol = plan_bayi(t, a.cikti, kod_govde(t), is_emri_no=a.is_emri_no, revizyon=a.revizyon, set_yolu=a.set, yontem=a.yontem)
    print("yazıldı:", yol.name, f"({yol.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
