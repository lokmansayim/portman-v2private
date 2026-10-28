"""İE-08 8a PR-2b (A4) · Bayiye giden iki görsel (çelik revizyon):

- `okumalar()`: pencere okuması belirsizken (iki aday) "1 / 2 / Hiçbiri" sorusunun başlık görseli: alt alta iki panelde plan, değişecek pencere
  daire içinde ve büyük numarayla. `<kod>_okuma.png`.
- `once_sonra()`: r0N (N ≥ 2) Onayla/Revize et mesajının başlık görseli: ÖNCE r0(N−1) ve altında SONRA r0N planları (telefonda okunsun diye alt alta) (değişen pencere daire
  içinde; dış 140'ta dış duvarlar vurgulu; yalnız çatı varyantı değiştiyse iki çatı planı), altta YENİ planın çatı planı ve iki perspektifi (VTK yoksa iki görünüş;
  `bayi_gorseli.alt_sira_ciz`, kartla aynı). Lokman (12.10.2026): perspektifler aynı görselin içinde, ayrı mesaj yok. `<kod>_once_sonra.png`.

Altın koşuda üretilmezler (çizim setine ve kartın baytlarına dokunmaz). ≤ 5 MB. Planlar ölçü zincirsizdir (ölçüler PDF'te ve
`plan_bayi.png`'de); pencere etiketleri (en/yük) plandadır.
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası (İE-08 GM2; toplam.py)
import json
from pathlib import Path

KIRMIZI = "#d0342c"
MAVI = "#1f5f93"


def _cm_pt(ax, fig, span_cm: float) -> float:
    return (span_cm + 300.0) / (ax.get_position().width * fig.get_figwidth() * 72)


def _yazilari_sigdir(fig, paneller) -> None:
    """Dar mahalde ad / m² yazısı küçülür (`bayi_gorseli.dar_mahal_yazisi`, bayi plan görseliyle aynı kural). `tight_layout`tan sonra,
    son ölçekle çağrılır. BK-15: "EBEVEYN BANYO" önce–sonra panelinde 2 m'lik odadan taşıyordu (plan_bayi.png'de küçülüyordu)."""
    from .bayi_gorseli import dar_mahal_yazisi
    fig.canvas.draw(); r = fig.canvas.get_renderer()
    for ax, y in paneller:
        dar_mahal_yazisi(ax, y, r)


def _plan(ax, fig, y: dict, baslik: str, daireler=(), vurgu_dis: bool = False, kesik: bool = False) -> None:
    """Plan + işaretler. daireler: [(açıklık adı, numara | None)]. Panel bayi plan görseliyle aynı ölçekte (11 × 9 inç; yazılar binmesin,
    `testler/genel/test_okuma_gorseli.py` mürekkep kutusuyla denetler). Numara rozeti dairenin çevresinde, yazılara binmeyen ilk yere
    (dışarı, dışarı-yanlar, yanlar, içeri-yanlar, içeri); yer ölçülerek seçilir."""
    import math
    from matplotlib.patches import Circle, Polygon as MplPolygon
    from shapely.geometry import Point, box as sbox
    from . import ciz_genel
    bx0, by0, bx1, by1 = y["kutle"].bounds
    cm_pt = _cm_pt(ax, fig, max(bx1 - bx0, by1 - by0))
    ciz_genel.plan_eksen(ax, y, baslik=baslik, olcu_zinciri=False, mahal_aralik=max(14.0, 8.5 * cm_pt), giris_yazi_dy=max(44.0, 16 * cm_pt))
    R = 19.0 * cm_pt                                                # rozet yarıçapı: 22 pt yazı, daire payı 0,35 em
    pay = 70.0 + 2.5 * R
    x0, x1 = ax.get_xlim(); y0_, y1_ = ax.get_ylim()              # işaretler eksen sınırını aşmasın (rozet planın dışına çıkabilir)
    ax.set_xlim(min(x0, bx0 - pay), max(x1, bx1 + pay)); ax.set_ylim(min(y0_, by0 - pay), max(y1_, by1 + pay))
    rozetler = []
    for ad, numara in daireler:
        ac = next((a for a in y["acikliklar"] if a["ad"] == ad), None)
        if ac is None:
            continue
        k = ciz_genel.aciklik_kutusu(y, ac)
        kx0, ky0, kx1, ky1 = k.bounds
        cx, cy = (kx0 + kx1) / 2, (ky0 + ky1) / 2
        r = max(60.0, 0.8 * max(kx1 - kx0, ky1 - ky0), 22 * cm_pt)
        ax.add_patch(Circle((cx, cy), r, fc="none", ec=KIRMIZI, lw=2.6 if not kesik else 1.6, ls="--" if kesik else "-", zorder=15))
        if numara is not None:
            d = y["adli"][ac["duvar"]]
            dis = next((f["kenar"] for f in y["yuzler"] if f["duvar"] == d["ad"] and f["uzun"] and f["bolge_sinifi"] in ("dis", "veranda")), None)
            rozetler.append((cx, cy, r, numara, {"alt": -90.0, "ust": 90.0, "sol": 180.0, "sag": 0.0}.get(dis or "", 90.0)))
    if vurgu_dis:
        for d in y["duvarlar"]:
            if d["sinif"] != "dis":
                continue
            ax.add_patch(MplPolygon(list(d["geo"].exterior.coords), closed=True, fc="none", ec=KIRMIZI, lw=2.2, zorder=14))
    if rozetler:
        fig.canvas.draw(); rr = fig.canvas.get_renderer(); inv = ax.transData.inverted()
        engel = []
        for t_ in ax.texts:
            bb = t_.get_window_extent(rr)
            (a, b), (c, d_) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
            engel.append(sbox(min(a, c), min(b, d_), max(a, c), max(b, d_)).buffer(3 * cm_pt))
        lx0, lx1 = ax.get_xlim(); ly0, ly1 = ax.get_ylim()
        for cx, cy, r, numara, aci in rozetler:
            yer = None
            for fark in (0, 45, -45, 90, -90, 135, -135, 180):
                a_ = math.radians(aci + fark)
                px, py = cx + math.cos(a_) * (r + R + 3 * cm_pt), cy + math.sin(a_) * (r + R + 3 * cm_pt)
                g = Point(px, py).buffer(R)
                if lx0 < px - R and px + R < lx1 and ly0 < py - R and py + R < ly1 and not any(e.intersects(g) for e in engel):
                    yer = (px, py); break
            if yer is None:
                a_ = math.radians(aci); yer = (cx + math.cos(a_) * (r + R + 3 * cm_pt), cy + math.sin(a_) * (r + R + 3 * cm_pt))
            engel.append(Point(*yer).buffer(R + 3 * cm_pt))
            ax.text(yer[0], yer[1], str(numara), ha="center", va="center", fontsize=22, weight="bold", color="white", zorder=16,
                    bbox=dict(boxstyle="circle,pad=0.35", fc=KIRMIZI, ec="none"))


def _kur(t: dict, set_yolu: Path | None, yontem: str | None):
    from . import kural, yapi
    t = json.loads(json.dumps(t))
    if yontem:
        t["cati"]["yontem"] = yontem
    with kural.secili(set_yolu):
        kural.oku()
    return t, yapi.kur(t)


def _cati(ax, t: dict, y: dict, baslik: str, set_yolu: Path | None) -> None:
    """Çatı planı (çatı varyantı değişince önce–sonra üst sırası; `ciz_genel.cati_plani_eksen`, yazılar ayrık)."""
    from . import cati_genel, ciz_genel, kural
    with kural.secili(set_yolu):
        kur = kural.oku()
    c = cati_genel.cati_kur(t["cati"], kur)
    inis, _ = ciz_genel.inis_kurali(c, kur, t["cati"].get("sacak", 30))
    ciz_genel.cati_plani_eksen(ax, y, c, inis, baslik=baslik, yazi_ayir=True)


def okumalar(t: dict, adaylar: list[dict], hedef: Path, kod: str, olcu=None, set_yolu: Path | None = None, yontem: str | None = None) -> Path:
    """`<kod>_okuma.png`: her aday için bir panel (en çok 2); değişecek pencere daire içinde, büyük numara; başlıkta aday anlatımı."""
    import matplotlib.pyplot as plt
    from .uret import matplotlib_sabitle
    matplotlib_sabitle()
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    yol = hedef / f"{kod}_okuma.png"
    adaylar = list(adaylar)[:2]
    t, y = _kur(t, set_yolu, yontem)
    en, yuk = (olcu or (None, None))
    olcu_s = f" → {en}/{yuk}" if en else ""

    def ciz(dpi: int) -> None:
        fig, axs = plt.subplots(len(adaylar), 1, figsize=(11.0, 9.0 * len(adaylar)), dpi=dpi, squeeze=False)     # alt alta: telefonda okunur
        for ax, (i, a) in zip(axs[:, 0], enumerate(adaylar, 1)):
            _plan(ax, fig, y, f"{i} · {a.get('aciklama', a['aciklik'])}{olcu_s}", daireler=[(a["aciklik"], i)])
        fig.suptitle("Hangi pencere? 1 ya da 2 (ya da Hiçbiri)", fontsize=15, weight="bold", color=MAVI, y=0.995)
        fig.tight_layout(rect=(0, 0, 1, 0.985))
        _yazilari_sigdir(fig, [(ax, y) for ax in axs[:, 0]])
        fig.savefig(yol, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    ciz(110)
    if yol.stat().st_size > 5 * 1024 * 1024:
        ciz(80)
    return yol


def once_sonra(t_once: dict, t_sonra: dict, hedef: Path, kod: str, degisen: list[dict], rev_once: int, rev_sonra: int, set_yolu: Path | None = None,
               yontem: str | None = None, perspektif: bool | None = None, baslik: str | None = None) -> Path:
    """`<kod>_once_sonra.png`: [ÖNCE r0(N−1) | SONRA r0N] + alt sıra (çatı planı, perspektifler; yeni plan)."""
    import matplotlib.pyplot as plt
    from . import bayi_gorseli as BG
    from .uret import matplotlib_sabitle
    matplotlib_sabitle()
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    yol = hedef / f"{kod}_once_sonra.png"; ust = hedef / f"{kod}_once_sonra_ust.png"; alt = hedef / f"{kod}_once_sonra_alt.png"
    _, y0 = _kur(t_once, set_yolu, yontem)
    t1, y1 = _kur(t_sonra, set_yolu, yontem)
    pencereler = [(d["aciklik"], None) for d in degisen if d.get("op") == "pencere_olcu" and d.get("aciklik")]
    dis140 = any(d.get("op") == "dis_karkas_140" for d in degisen)
    yalniz_cati = any(d.get("op") == "cati_varyanti" for d in degisen) and not pencereler and not dis140   # çatı değişti: üstte iki çatı planı
    anlatim = "; ".join(str(d.get("aciklama") or d.get("op")) for d in degisen)
    h = BG.alt_sira_hazirla(t1, hedef, kod, set_yolu=set_yolu, yontem=yontem, perspektif=perspektif)

    def ust_ciz(dpi: int) -> None:
        fig, axs = plt.subplots(2, 1, figsize=(11.0, 18.0), dpi=dpi)              # ÖNCE üstte, SONRA altta (telefonda okunur)
        if yalniz_cati:
            _cati(axs[0], t_once, y0, f"ÖNCE · r{int(rev_once):02d} · ÇATI PLANI", set_yolu)
            _cati(axs[1], t1, y1, f"SONRA · r{int(rev_sonra):02d} · ÇATI PLANI", set_yolu)
        else:
            _plan(axs[0], fig, y0, f"ÖNCE · r{int(rev_once):02d}", daireler=pencereler, kesik=True)
            _plan(axs[1], fig, y1, f"SONRA · r{int(rev_sonra):02d}", daireler=pencereler, vurgu_dis=dis140)
        fig.suptitle(baslik or (f"Değişiklik: {anlatim}" if anlatim else f"r{int(rev_sonra):02d}"), fontsize=15, weight="bold", color=MAVI, y=0.995)
        fig.tight_layout(rect=(0, 0, 1, 0.985))
        if not yalniz_cati:
            _yazilari_sigdir(fig, [(axs[0], y0), (axs[1], y1)])
        fig.savefig(ust, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    ust_ciz(110); BG.alt_sira_ciz(h, alt, 110); BG.ust_alt_birlestir(ust, alt, yol)
    if yol.stat().st_size > 5 * 1024 * 1024:
        ust_ciz(80); BG.alt_sira_ciz(h, alt, 80); BG.ust_alt_birlestir(ust, alt, yol)
    BG.bes_mb_sinirla(yol)
    ust.unlink(missing_ok=True); alt.unlink(missing_ok=True)
    return yol
