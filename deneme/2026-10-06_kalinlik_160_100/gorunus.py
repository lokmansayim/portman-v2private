"""6 Ekim 2026 denemesi: İş Emri → dört görünüş paftası (pano pano).

    python deneme/2026-10-06_kalinlik_160_100/gorunus.py is_emri_3arti1_1150x1050.json

Geometri Motor'un deneme kopyasından gelir (`kos.py` ile aynı plan); burada yalnız cepheye izdüşüm alınır.
Her dış pano ayrı dikdörtgendir; standart dışı (kesilmiş) panolar mor, köşe parçaları koyu gösterilir.
Çatı: beşik. Makaslar kısa kenarı geçer (Lokman, 20–21 Eylül); mahya uzun kenara paraleldir.
Canlı Motor'a dokunmaz. Çıktı: `cikti/<iş emri no>/gorunus/`.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MplPolygon

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIKTI = BURASI / "cikti"
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(BURASI))
os.environ.setdefault("PORTMAN_REF_DIR", str(KOK / "kanal"))

PENCERE_ESIK = {"120x120": 80.0, "120x180": 20.0, "60x40": 160.0}   # üst kot 200 cm (motor/ifc_uret.py ile aynı)
KAPI_UST = 200.0
CATI_KALINLIK = 14.0   # makas üst başlığı 10 + örtü 4 (motor/ifc_uret.py'deki şematik ölçü)

R_PANO, R_OZEL, R_KOSE, R_CATI, R_ALIN = "#e4dfd2", "#e2c9ee", "#9a958a", "#4e5560", "#d3cdbf"
R_CAM, R_KASA, R_KAPI, R_CIZGI, R_OLCU, R_OZEL_YAZI = "#cfe6f7", "#1f6fb5", "#7a4a21", "#2b2b2b", "#444444", "#7b2fa0"


def tr(v: float, n: int = 2) -> str:
    return f"{v:.{n}f}".rstrip("0").rstrip(".").replace(".", ",")


def cephe_verisi(plan, G) -> dict:
    """Dört cephe: her biri soldan sağa (bakan kişiye göre) parça listesi. Parça: (u0, u1, tür, pano ya da None)."""
    W, H = plan.W, plan.H
    nx2, ny2 = int(round(plan.nx * 2)), int(round(plan.ny * 2))
    yuz = {"on": [], "arka": [], "sol": [], "sag": []}
    for d in plan.duvarlar:
        if d.tur != "dis":
            continue
        if d.yon == "x" and d.hat in (0, ny2):
            ad = "on" if d.hat == 0 else "arka"
        elif d.yon == "y" and d.hat in (0, nx2):
            ad = "sol" if d.hat == 0 else "sag"
        else:
            raise SystemExit(f"DUR: çevrede olmayan dış duvar (veranda girintisi?) bu denemede çizilmiyor: duvar {d.id}")
        for p in d.panolar:
            yuz[ad].append((p.a0, p.a1, "pano", p))
    # köşe şeritleri: ön/arka görünüşte yan duvarların kalınlığı, yan görünüşte ön/arka duvarın köşe parçası
    t = G.T_DIS
    for ad, boy, uc in (("on", W, t), ("arka", W, t), ("sol", H, t / 2), ("sag", H, t / 2)):
        yuz[ad] += [(0.0, uc, "kose", None), (boy - uc, boy, "kose", None)]
    cikti = {}
    for ad, parcalar in yuz.items():
        boy = W if ad in ("on", "arka") else H
        ayna = ad in ("arka", "sol")          # bakış yönüne göre soldan sağa: ön x, arka W−x, sol H−y, sağ y
        liste = [((boy - u1, boy - u0) if ayna else (u0, u1)) + (tur, p) for u0, u1, tur, p in parcalar]
        liste.sort(key=lambda r: r[0])
        for (a0, a1, *_), (b0, b1, *_) in zip(liste, liste[1:]):
            if abs(a1 - b0) > 1e-6:
                raise SystemExit(f"DUR: {ad} cephesinde parçalar bitişik değil: {a1} / {b0}")
        if abs(liste[0][0]) > 1e-6 or abs(liste[-1][1] - boy) > 1e-6:
            raise SystemExit(f"DUR: {ad} cephesi dış ölçüyü doldurmuyor")
        cikti[ad] = {"boy": boy, "ayna": ayna, "parcalar": liste}
    return cikti


def cati_olculeri(ie: dict, W: float, H: float) -> dict:
    c = ie.get("cati", {}); H0 = float(ie["yapi"].get("duvar_yuksekligi_cm", 250))
    eg, s, top = float(c.get("egim_yuzde", 33)) / 100.0, float(c.get("sacak_cm", 30)), float(c.get("topuk_cm", 10))
    aciklik_y = (c["makas_ekseni"] == "y") if c.get("makas_ekseni") else (H <= W)   # verilmezse makas kısa kenarı geçer
    aciklik = H if aciklik_y else W
    zs = H0 + top; zm = zs + (aciklik / 2 + s) * eg
    return {"H0": H0, "egim": eg, "sacak": s, "topuk": top, "makas_ekseni": "y" if aciklik_y else "x", "aciklik": aciklik,
            "mahya_boyu": (W if aciklik_y else H) + 2 * s, "zs": zs, "zm": zm, "ust": zm + CATI_KALINLIK}


class Pafta:
    def __init__(self, en: float, boy: float, genislik_in: float = 22.0):
        self.k = genislik_in / en                       # inç / cm
        self.fig = plt.figure(figsize=(genislik_in, genislik_in * boy / en), dpi=150)
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, en); self.ax.set_ylim(0, boy)
        self.ax.set_aspect("equal"); self.ax.axis("off")

    def fs(self, cm: float) -> float:
        return cm * self.k * 72.0

    def yazi(self, x, y, s, cm=13, **kw):
        kw.setdefault("ha", "center"); kw.setdefault("va", "center"); kw.setdefault("color", R_CIZGI)
        self.ax.text(x, y, s, fontsize=self.fs(cm), **kw)

    def kutu(self, x, y, w, h, fc, ec=R_CIZGI, lw=0.5, z=2):
        self.ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))

    def cokgen(self, pts, fc, ec=R_CIZGI, lw=0.6, z=2):
        self.ax.add_patch(MplPolygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))

    def olcu_y(self, x0, x1, y, s=None, cm=11, renk=R_OLCU):
        """Yatay ölçü çizgisi."""
        self.ax.plot([x0, x1], [y, y], color=renk, lw=0.5, zorder=5)
        for x in (x0, x1):
            self.ax.plot([x, x], [y - 6, y + 6], color=renk, lw=0.5, zorder=5)
        self.yazi((x0 + x1) / 2, y + 9, s if s is not None else tr(x1 - x0), cm, color=renk, va="bottom")

    def olcu_d(self, x, y0, y1, s=None, cm=11, renk=R_OLCU):
        """Düşey ölçü çizgisi."""
        self.ax.plot([x, x], [y0, y1], color=renk, lw=0.5, zorder=5)
        for y in (y0, y1):
            self.ax.plot([x - 6, x + 6], [y, y], color=renk, lw=0.5, zorder=5)
        self.yazi(x + 9, (y0 + y1) / 2, s if s is not None else tr(y1 - y0), cm, color=renk, rotation=90, ha="left")


def dograma(pf: Pafta, ox, oy, u0, u1, ac):
    if ac.tur == "pencere":
        en, yuk = (float(v) for v in ac.olcu.split("x")); z0 = PENCERE_ESIK[ac.olcu]
        pf.kutu(ox + u0, oy + z0, u1 - u0, yuk, R_CAM, R_KASA, 1.0, 4)
        if en >= 100:
            pf.ax.plot([ox + (u0 + u1) / 2] * 2, [oy + z0, oy + z0 + yuk], color=R_KASA, lw=0.8, zorder=5)
        pf.yazi(ox + (u0 + u1) / 2, oy + z0 + yuk + 13, f"{int(en)}/{int(yuk)}", 12.5, color=R_KASA)
    elif ac.tur == "dis_kapi":
        pf.kutu(ox + u0, oy, u1 - u0, KAPI_UST, R_KAPI, "#3d250f", 1.0, 4)
        pf.yazi(ox + (u0 + u1) / 2, oy + KAPI_UST + 13, f"{tr(u1 - u0)}/{tr(KAPI_UST)}", 12.5, color="#3d250f")


KISA = {"on": "Ö", "arka": "A", "sol": "SL", "sag": "SĞ"}   # pano numarası öneki (cephede soldan sağa)


def cephe_ciz(pf: Pafta, ox: float, oy: float, ad: str, baslik: str, c: dict, cati: dict, G) -> dict:
    boy, H0, s = c["boy"], cati["H0"], cati["sacak"]
    sayim = {"pano": 0, "ozel": 0, "pencere": 0, "kapi": 0}
    pf.ax.plot([ox - 90, ox + boy + 90], [oy, oy], color=R_CIZGI, lw=1.0, zorder=6)                     # zemin
    for u0, u1, tur, p in c["parcalar"]:
        if tur == "kose":
            pf.kutu(ox + u0, oy, u1 - u0, H0, R_KOSE, lw=0.5)
            continue
        sayim["pano"] += 1
        ozel = abs(p.boy - G.MOD) > 1e-6
        sayim["ozel"] += ozel
        pf.kutu(ox + u0, oy, u1 - u0, H0, R_OZEL if ozel else R_PANO, lw=0.7)
        if p.acilim is not None:
            g = p.gap(); a0, a1 = (g[0], g[2]) if p.duvar.yon == "x" else (g[1], g[3])
            if c["ayna"]:
                a0, a1 = boy - a1, boy - a0
            dograma(pf, ox, oy, a0, a1, p.acilim)
            sayim["pencere" if p.acilim.tur == "pencere" else "kapi"] += 1
        pf.yazi(ox + (u0 + u1) / 2, oy + H0 - 20, f"{KISA[ad]}{sayim['pano']}", 11 if p.boy > 60 else 8.5, color=R_OZEL_YAZI if ozel else "#6b665c")
        pf.olcu_y(ox + u0, ox + u1, oy - 36, tr(p.boy), 12.5, R_OZEL_YAZI if ozel else R_OLCU)
    # çatı
    zs, zm, ust = cati["zs"], cati["zm"], cati["ust"]
    kalkan = (ad in ("sol", "sag")) == (cati["makas_ekseni"] == "y")      # bu cephe kalkan (üçgen) mi?
    if kalkan:
        pf.cokgen([(ox, oy + H0), (ox + boy, oy + H0), (ox + boy, oy + zs + s * cati["egim"]), (ox + boy / 2, oy + zm),
                   (ox, oy + zs + s * cati["egim"])], R_ALIN, lw=0.6, z=2)                                  # alın (kalkan) dolgusu
        pf.cokgen([(ox - s, oy + zs), (ox + boy / 2, oy + zm), (ox + boy + s, oy + zs), (ox + boy + s, oy + zs + CATI_KALINLIK),
                   (ox + boy / 2, oy + ust), (ox - s, oy + zs + CATI_KALINLIK)], R_CATI, lw=0.6, z=3)
        pf.yazi(ox + boy * 0.27, oy + (zs + zm) / 2 + 46, "%" + tr(cati["egim"] * 100), 16)
        pf.yazi(ox + boy * 0.73, oy + (zs + zm) / 2 + 46, "%" + tr(cati["egim"] * 100), 16)
    else:
        pf.kutu(ox - s, oy + zs, boy + 2 * s, ust - zs, R_CATI, lw=0.6, z=3)                               # saçak tarafı: çatı yüzeyi
        pf.ax.plot([ox - s, ox + boy + s], [oy + zs + CATI_KALINLIK] * 2, color="#aab0b8", lw=0.5, zorder=4)
        pf.kutu(ox - s, oy + H0, boy + 2 * s, zs - H0, R_KOSE, lw=0.4, z=3)                                # topuk / saçak yüzü
    # ölçüler
    pf.olcu_y(ox, ox + boy, oy - 86, None, 16)
    pf.olcu_y(ox - s, ox + boy + s, oy - 134, None, 15)
    pf.olcu_d(ox + boy + s + 28, oy, oy + H0, None, 15)
    pf.olcu_d(ox + boy + s + 76, oy, oy + ust, None, 15)
    pf.yazi(ox + boy / 2, oy + ust + 62, baslik, 26, fontweight="bold")
    return sayim


def anahtar_plan(pf: Pafta, ox, oy, olcek, plan, G):
    W, H = plan.W, plan.H
    for d in plan.duvarlar:
        for p in d.panolar:
            ozel = abs(p.boy - G.MOD) > 1e-6
            for (x0, y0, x1, y1) in p.rects():
                pf.kutu(ox + x0 * olcek, oy + y0 * olcek, (x1 - x0) * olcek, (y1 - y0) * olcek,
                        (R_OZEL if ozel else R_PANO) if d.tur == "dis" else "#f1efe9", lw=0.4)
    for k in plan.koseler:
        x0, y0, x1, y1 = k.rect
        pf.kutu(ox + x0 * olcek, oy + y0 * olcek, (x1 - x0) * olcek, (y1 - y0) * olcek, R_KOSE, lw=0.3)
    for ad, m in plan.mahaller.items():
        c = m.poly.representative_point()
        pf.yazi(ox + c.x * olcek, oy + c.y * olcek, ad, 11.5)
    oklar = (("ÖN", W / 2, -55, 0, 1), ("ARKA", W / 2, H + 55, 0, -1), ("SOL", -75, H / 2, 1, 0), ("SAĞ", W + 75, H / 2, -1, 0))
    for ad, x, y, dx, dy in oklar:
        pf.ax.annotate("", xy=(ox + (x + dx * 34) * olcek, oy + (y + dy * 34) * olcek), xytext=(ox + x * olcek, oy + y * olcek),
                       arrowprops=dict(arrowstyle="-|>", color="#b03030", lw=0.9))
        pf.yazi(ox + (x - dx * 60) * olcek, oy + (y - dy * 34) * olcek, ad, 15, color="#b03030", fontweight="bold")
    pf.yazi(ox + W * olcek / 2, oy + (H + 150) * olcek, "PLAN · bakış yönleri", 19, fontweight="bold")


def uret(is_emri_yolu: Path) -> dict:
    import yama
    yama.uret(CIKTI)
    sys.path.insert(0, str(CIKTI))
    from motor_k import geometry as G

    ie = json.loads(Path(is_emri_yolu).read_text(encoding="utf-8"))
    plan = G.kur(json.loads(json.dumps(ie)))
    W, H = plan.W, plan.H
    cepheler = cephe_verisi(plan, G)
    cati = cati_olculeri(ie, W, H)
    s = cati["sacak"]

    kol = max(W, H) + 2 * s + 260          # sütun adımı
    sat = cati["ust"] + 300                # satır adımı
    alt = 700.0                            # alt bant: anahtar plan + notlar
    en, boy = 2 * kol + 40, sat + alt + 170 + cati["ust"] + 210
    pf = Pafta(en, boy)
    x1, x2 = 110.0, 110.0 + kol
    y_ust, y_alt = alt + sat + 170, alt + 170
    yer = {"on": (x1, y_ust, "ÖN GÖRÜNÜŞ (giriş)"), "arka": (x2, y_ust, "ARKA GÖRÜNÜŞ"), "sol": (x1, y_alt, "SOL GÖRÜNÜŞ"), "sag": (x2, y_alt, "SAĞ GÖRÜNÜŞ")}
    sayim = {}
    for ad, (ox, oy, baslik) in yer.items():
        ox += (max(W, H) - cepheler[ad]["boy"]) / 2
        sayim[ad] = cephe_ciz(pf, ox, oy, ad, baslik, cepheler[ad], cati, G)

    olcek = 0.44
    anahtar_plan(pf, 190.0, 95.0, olcek, plan, G)
    t = ie.get("talep", {}); yapi = ie["yapi"]
    ozel = sorted({round(p.boy, 2) for d in plan.duvarlar if d.tur == "dis" for p in d.panolar if abs(p.boy - G.MOD) > 1e-6})
    toplam = {k: sum(v[k] for v in sayim.values()) for k in ("pano", "ozel", "pencere", "kapi")}
    satirlar = [
        f"Dış ölçü {tr(W)} × {tr(H)} cm · duvar yüksekliği {tr(cati['H0'])} cm · dış duvar {tr(G.T_DIS * 10)} mm, iç duvar {tr(G.T_IC * 10)} mm",
        f"Dış panolar: {toplam['pano']} adet; {toplam['ozel']} tanesi kesilmiş özel pano ({', '.join(tr(b) for b in ozel)} cm, mor). Standart pano 125,5 cm.",
        f"Cephe başına pano: ön {sayim['on']['pano']}, arka {sayim['arka']['pano']}, sol {sayim['sol']['pano']}, sağ {sayim['sag']['pano']}. "
        f"Pencere {toplam['pencere']}, dış kapı {toplam['kapi']}.",
        "Koyu şeritler köşe: ön ve arka görünüşte yan duvarın kalınlığı (16 cm), yan görünüşlerde köşe parçası (8 cm).",
        f"Pencere üst kotu {tr(KAPI_UST)} cm (lento {tr(cati['H0'] - KAPI_UST)} cm); eşikler: 120/180 → 20, 120/120 → 80, 60/40 → 160 cm. Dış kapı 90/200.",
        f"Çatı: beşik, %{tr(cati['egim'] * 100)}, saçak {tr(s)} cm, topuk {tr(cati['topuk'])} cm. Makaslar kısa kenarı ({tr(cati['aciklik'])} cm) geçer; "
        f"mahya uzun kenar boyunca {tr(cati['mahya_boyu'])} cm.",
        f"Mahya kotu {tr(cati['zm'], 1)} cm (makas üstü); çatı üstü {tr(cati['ust'], 1)} cm ({tr(CATI_KALINLIK)} cm şematik başlık + örtü).",
        "Ölçüler cm. Pano altındaki sayı o panonun boyudur; üstündeki kod cephedeki sırasıdır (soldan sağa). Subasman, basamak ve cephe kaplaması çizilmedi.",
    ]
    nx0 = 190.0 + W * olcek + 190
    pf.yazi(nx0, 95.0 + H * olcek + 60, "NOTLAR", 19, ha="left", fontweight="bold")
    for i, sx in enumerate(satirlar):
        pf.yazi(nx0, 95.0 + H * olcek + 8 - i * 54, sx, 17, ha="left")
    for i, u in enumerate(ie.get("pafta_uyarilari", [])):
        pf.yazi(nx0, 95.0 + H * olcek + 8 - (len(satirlar) + i) * 54 - 14, "UYARI: " + u, 15, ha="left", color="#a03a1a")
    pf.yazi(en / 2, boy - 55, f"{t.get('musteri_adi', '')} · GÖRÜNÜŞLER · İş Emri {ie.get('is_emri_no')} r{int(ie.get('revizyon', 1)):02d}"
            f"   —   TASLAK · çizim kurallarından kuruldu · üretim/statik projesi değildir", 22, fontweight="bold")

    hedef = CIKTI / ie["is_emri_no"] / "gorunus"; hedef.mkdir(parents=True, exist_ok=True)
    govde = f"Portman_{ie['is_emri_no']}_r{int(ie.get('revizyon', 1)):02d}_gorunusler"
    pf.fig.savefig(hedef / f"{govde}.pdf"); pf.fig.savefig(hedef / f"{govde}.png", dpi=150)
    plt.close(pf.fig)
    ozet = {"is_emri_no": ie["is_emri_no"], "dis_olcu_cm": [W, H], "cati": cati, "sayim": sayim, "toplam": toplam,
            "cephe_pano_boylari_cm": {ad: [round(p.boy, 3) for *_r, tur, p in c["parcalar"] if tur == "pano"] for ad, c in cepheler.items()},
            "dosyalar": [f"{govde}.pdf", f"{govde}.png"]}
    (hedef / "gorunus_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    return ozet | {"hedef": str(hedef)}


if __name__ == "__main__":
    yol = Path(sys.argv[1]) if len(sys.argv) > 1 else BURASI / "is_emri_3arti1_1150x1050.json"
    if not yol.is_absolute() and not yol.exists():
        yol = BURASI / yol
    o = uret(yol)
    print(json.dumps({k: o[k] for k in ("dis_olcu_cm", "toplam", "sayim", "cephe_pano_boylari_cm", "hedef")}, ensure_ascii=False, indent=1))
    c = o["cati"]
    print(f"çatı: makas ekseni {c['makas_ekseni']}, açıklık {c['aciklik']:g}, mahya kotu {c['zm']:.2f}, çatı üstü {c['ust']:.2f}")
