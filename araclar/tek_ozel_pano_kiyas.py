"""D-92 (BK-30): tek özel pano kuralının önce/sonra pano dizilimi (çalışma kuralı 12, D-68).

Aynı İş Emri iki kez kurulur: anahtarsız (bugün) ve `yapi.dizilim.tek_ozel_pano: "dizilim_sonu"` ile. İki plan da Motor'un `Plan`'ından çizilir
(`motor/dizilim_kiyas.ciz`); kalkan ve yeni panolar pembe, öteki panolar gri. Görsel inceleme içindir; ön onay çizimi (M-02) bu değildir.
İş Emri'ni değiştirmez, dosyaya yazmaz (yalnız görseli).

    python -m araclar.tek_ozel_pano_kiyas <İş Emri.json> <çıktı.png> [--baslik "85 m² 3+1"]
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402
from motor import dizilim_kiyas as DK  # noqa: E402


def anahtarli(ie: dict, deger: str = "dizilim_sonu") -> dict:
    """İş Emri'nin kopyası, `yapi.dizilim.tek_ozel_pano` yazılı (girdi değişmez)."""
    ie = copy.deepcopy(ie)
    ie["yapi"].setdefault("dizilim", {})["tek_ozel_pano"] = deger
    return ie


def kiyas(ie: dict) -> tuple:
    """(önceki plan, sonraki plan, önceki sınıflar, sonraki sınıflar). Sınıf: 'ayni' (yeri ve boyu aynı) | 'degisti'."""
    p0 = G.kur(copy.deepcopy(ie))
    p1 = G.kur(anahtarli(ie))
    an = lambda q: (q.duvar.id, round(q.a0, 4), round(q.a1, 4))
    k0, k1 = {an(q) for q in p0.panolar}, {an(q) for q in p1.panolar}
    s0 = {id(q): ("ayni" if an(q) in k1 else "degisti") for q in p0.panolar}
    s1 = {id(q): ("ayni" if an(q) in k0 else "degisti") for q in p1.panolar}
    return p0, p1, s0, s1


def gorsel(ie: dict, yol: Path, baslik: str = "") -> dict:
    """Önce/sonra görselini yazar. Dönüş: {dosya, pano_once, pano_sonra, degisiklik}."""
    import matplotlib.pyplot as plt
    p0, p1, s0, s1 = kiyas(ie)
    yol = Path(yol)
    Wm, Hm = max(p0.W, p1.W), max(p0.H, p1.H)
    fig, axs = plt.subplots(1, 2, figsize=(20, 9.5 * (Hm + 230) / (Wm + 260) + 1.6), dpi=120)
    on = f"{baslik} · " if baslik else ""
    DK.ciz(axs[0], p0, s0, f"Önce · {on}{DK.tr(p0.W)} × {DK.tr(p0.H)} cm · {len(p0.panolar)} pano")
    DK.ciz(axs[1], p1, s1, f"Sonra · tek özel pano kuralı · {len(p1.panolar)} pano")
    for ax in axs:
        ax.set_xlim(-170, Wm + 90)
        ax.set_ylim(-150, Hm + 60)
    n0 = sum(v == "degisti" for v in s0.values())
    n1 = sum(v == "degisti" for v in s1.values())
    fig.text(0.5, 0.035, f"Gri: yeri ve boyu değişmeyen pano.   Pembe: önce planında kalkan pano ({n0}), sonra planında yeni pano ({n1}).   "
             "Kırmızı çerçeve pencere, yeşil çerçeve kapı.", ha="center", fontsize=11.5, color="#333333")
    fig.text(0.5, 0.012, "Sayı: 125,5 cm dışındaki pano boyu. İki köşe ya da T arasında 125,5'ler çıkar, kalan tek özel pano olur (D-92); "
             "kalan pano montaj köşesinden uzak uçta.", ha="center", fontsize=11.5, color="#333333")
    plt.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(yol, dpi=120)
    plt.close(fig)
    return {"dosya": str(yol), "pano_once": len(p0.panolar), "pano_sonra": len(p1.panolar), "degisiklik": p1.tek_ozel_pano}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="D-92 tek özel pano kuralı: önce/sonra pano dizilimi")
    ap.add_argument("is_emri")
    ap.add_argument("cikti")
    ap.add_argument("--baslik", default="")
    a = ap.parse_args(argv)
    ie = json.loads(Path(a.is_emri).read_text(encoding="utf-8"))
    print(json.dumps(gorsel(ie, Path(a.cikti), a.baslik), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
