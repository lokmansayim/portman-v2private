"""K2'nin beş yerleşim planı, K3'ün elektrik planı ve K3b'nin alt çerçeve ve çatı kenarları planı, kart modelinin IFC'sinden çizilir: tavan
omega, makas ve dere, baş makas betopanı, aşık, çatı kaplaması; sayımda elektrik varsa (komut her zaman kurar) altıncı sayfa elektrik
yerleşim planı, kenar varsa (komut her zaman kurar) yedinci sayfa alt çerçeve (zemin) ve çatı kenarlarıdır (çatı planı); yedinci sayfanın
lejantında her kartın sayısı liste üretecinin aynı satırıyla yan yanadır.

Her şekil modeldeki parçanın kendi geometrisinden (dünya koordinatı) ve özellik setinden okunur; planlar yerleşim kurallarının çıktısından
değil modelden gelir. Sayılar (adet, metre, kesim) sayımdandır (`<kod>_kart_sayim.json`). Antet bizimdir; paftanın anteti ve adları
çıktıya girmez. Paftayla kıyas hakemin işidir (`testler/kimlik/hakem/kiyas.py`). Sayımda "kural yok" varsa her sayfanın başında EKSİK
yazar; sayfanın katmanı kurulmadıysa nedeni, yerleşimin uyarıları da ilgili sayfada yazar.

Beşik dışı çatıda (İE-15 K5) çatı katmanları kurulmaz: kart modelinin IFC'si bugünkü IFC'nin kopyasıdır ve çatıyı hep beşik çizer; o
makaslar sayılmadığı (kural yok) için çizilmez, çatı sayfalarında yerine çatının adı ve nedeni yazar. Yedinci sayfanın lejantında
kurulmayan kart "kurulmadı", liste üretecinin yazmadığı liste "liste yazılmaz" (nedeniyle) yazar.

Taşan verandanın çatısı (K5b) aynı sayfalarda: yavru makas makas ve dere planında, veranda kalkanının betopanı baş makasların altında,
aşık, kaplama ve çatı kenarları ana çatınınkilerle birlikte. Dikey betopanda levhanın kenarı ve uçtaki artan betopan ayrı çizilir.

Tavan katmanı (K5b-2) tavan omega planında: asma dizme tavanın gözleri (beyaz ve yeşil alçıpan) ve H'ları omegaların altında, açık
mahale bakan dış duvarın omegası ayrı renkte; çatı izolasyonunun şeritleri makas ve dere planında makasların altında.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import numpy as np
from shapely.geometry import MultiPoint

PARCA_SETI = "PortatifEv_Parca"
RENK = {"duvar": "#c9c9c9", "duvar_kenar": "#8a8a8a",
        "omega": {"duvar_ekseni": "#c0392b", "duvar_yuzu": "#8e44ad", "ara": "#e67e22", "dis_duvar": "#1a5276"},
        "makas": "#2c3e50", "yavru_makas": "#7e5109", "dere": "#2e86c1", "inis": "#1b4f72", "asik": "#2471a3", "kaplama": ("#f4d03f", "#f9e79f"), "levha": "#e67e22",
        "goz": {"AL-01": "#f4f6f6", "AL-02": "#abebc6"}, "goz_kenar": "#aab7b8", "tavan_h": "#566573", "izolasyon": ("#f9e79f", "#fcf3cf")}
OMEGA_YER = {"duvar_ekseni": "iç duvar ekseninde", "duvar_yuzu": "duvar yüzünde", "ara": "arada", "dis_duvar": "açık mahale bakan dış duvarda"}
YUZ = {"sol": "sol", "sag": "sağ", "iki": "iki"}
# sayfanın katmanları: kural yokta katmanın adı (`motor.yerlesim`), parça adının öneki ve uyarının katmanı
SAYFA = {1: (("tavan omegası", "tavan H'ı ve gözler"), ("OMEGA_", "DIS_DUVAR_OMEGA_", "TAVAN_H_", "ALCIPAN_")),
         2: (("dere ve iniş", "iniş", "çatı izolasyonu"), ("DERE_", "INIS_", "VERANDA_DERE_", "VERANDA_INIS_", "VERANDA_YAVRU_MAKAS_", "iniş (", "veranda çatısı",
                                                          "IZOLASYON_")),
         3: (("baş makas betopanı",), ("BETOPAN_", "VERANDA_BETOPAN_", "baş makas betopanı (")),
         4: (("aşık",), ("ASIK_", "VERANDA_ASIK_")), 5: (("çatı kaplaması",), ("KAPLAMA_", "VERANDA_KAPLAMA_")),
         6: (("elektrik", "elektrik noktaları", "kablo_priz", "kablo_aydinlatma"),
             ("DUY_", "GLOP_", "ANAHTAR_", "PRIZ_", "UYDU_", "ZIL_", "SIGORTA_", "KABLO_")),
         7: (("alt çerçeve", "saçak omegası", "saçak sacı", "alın sacı", "baş makas Z'si", "C kapama", "mahya", "alt çerçeve ve çatı kenarları"),
             ("ALT_CERCEVE_", "SACAK_OMEGASI_", "SACAK_SACI_", "ALIN_SACI_", "BAS_MAKAS_Z_", "C_KAPAMA_", "MAHYA_", "VERANDA_SACAK_",
              "VERANDA_ALIN_SACI_", "VERANDA_MAHYA_"))}
ELEKTRIK_RENK = {"EL-01": "#c0392b", "EL-02": "#c0392b", "EL-03": "#1e8449", "EL-04": "#1e8449", "EL-05": "#1f4e9c", "EL-06": "#1f4e9c",
                 "EL-07": "#7d3c98", "EL-08": "#ca6f1e", "EL-09": "#111111", "EL-10": "#1f4e9c", "EL-11": "#e67e22"}
KENAR_RENK = {"AC-01": "#1f4e9c", "AC-02": "#e67e22", "CK-01": "#c0392b", "CK-02": "#85c1e9", "CK-03": "#ca6f1e", "CK-04": "#7d3c98",
              "CK-05": "#111111", "CK-06": "#1e8449"}


def _sayi(x: float, n: int = 2) -> str:
    return f"{x:,.{n}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _sekiller(f) -> dict[str, np.ndarray]:
    """GlobalId → köşeler (cm, dünya koordinatı)."""
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    out = {}
    it = ifcopenshell.geom.iterator(s, f)
    if it.initialize():
        while True:
            sh = it.get()
            out[sh.guid] = np.array(sh.geometry.verts, dtype=float).reshape(-1, 3) * 100
            if not it.next():
                break
    return out


def _iz(v: np.ndarray, eksenler=(0, 1)):
    return MultiPoint([tuple(p) for p in v[:, eksenler]]).convex_hull


def _model(yol: Path) -> dict:
    f = ifcopenshell.open(str(yol))
    sek = _sekiller(f)
    m = {"duvar": [], "makas": {}, "k2": {}}
    for e in f.by_type("IfcWall"):
        if e.GlobalId in sek:
            m["duvar"].append(_iz(sek[e.GlobalId]))
    for a in f.by_type("IfcElementAssembly"):
        if ue.get_predefined_type(a) == "TRUSS":
            uye = [sek[u.GlobalId] for r in a.IsDecomposedBy for u in r.RelatedObjects if u.GlobalId in sek]
            if not uye:                                         # kart modelinin yavru makası (MA-03, K5b) tek gövdedir; `k2`'de okunur
                continue
            kalem = str(ue.get_psets(a).get("PortatifEv_Kapsam", {}).get("BOMKalem", ""))
            m["makas"][a.Name] = {"uyeler": uye, "bas": "(baş)" in kalem}
    for e in f.by_type("IfcProduct"):
        p = ue.get_psets(e).get(PARCA_SETI, {})
        if e.GlobalId in sek and p.get("KartKodu") and p.get("Kural"):
            m["k2"].setdefault(p["KartKodu"], []).append({"ad": e.Name, "v": sek[e.GlobalId], "p": p})
    return m


def _cerceve(ax, baslik: str, alt: str):
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(baslik, fontsize=15, fontweight="bold", loc="left")
    ax.text(0, -0.04, alt, transform=ax.transAxes, fontsize=9, va="top", color="#444")


def _duvarlar(ax, m, dolgu=True):
    for p in m["duvar"]:
        x, y = p.exterior.xy
        if dolgu:
            ax.fill(x, y, color=RENK["duvar"], lw=0)
        ax.plot(x, y, color=RENK["duvar_kenar"], lw=0.4)


def _lejant(fig, satirlar: list[str]):
    fig.text(0.76, 0.90, "\n".join(satirlar), fontsize=10, va="top", ha="left", family="DejaVu Sans",
             bbox={"boxstyle": "round,pad=0.6", "fc": "white", "ec": "#999"})


def _kart(say: dict, kod: str) -> dict:
    return next((k for k in say["kartlar"] if k["kod"] == kod), {"adet": 0})


def _tavan_lejanti(say: dict, kesim: dict) -> list[str]:
    """K5b-2: asma dizme tavanın H'ı ve gözleri (lejantın tavan omega satırlarının altında); ters tavanda boş."""
    th, ab, ay = _kart(say, "H-11"), _kart(say, "AL-01"), _kart(say, "AL-02")
    if not (th["adet"] or ab["adet"] or ay["adet"]):
        return []
    lev = lambda kk: f" → {kesim[kk]['stok']} levha" if kk in kesim else ""                    # noqa: E731
    return (["", f"H-11 Tavan H'ı L 1185: {th['adet']} (▬)", f"AL-01 beyaz alçıpan: {ab['adet']} göz{lev('AL-01')}",
             f"AL-02 yeşil alçıpan: {ay['adet']} göz{lev('AL-02')}", "(levha 120 × 250, raflarla; yedek yok)"])


def _cati_notu(say: dict) -> str | None:
    """Beşik dışı çatıda (K5) çatı katmanlarının yerine yazılan not; çatı tipinden kural yok yoksa None."""
    if not any("cati" in x for x in say["kural_yok"]):
        return None
    from motor.yerlesim import girdi
    t = say["cati_tipi"]
    return "\n".join([f"Çatı: {girdi.cati_adi(t)} (İş Emri'nde \"{t}\")", "Çatı parçaları kurulmadı (kural yok):",
                      *textwrap.wrap(girdi.cati_sonra(t) + ".", 52), "Bugünkü IFC çatıyı beşik çizer;", "o makaslar sayılmaz, çizilmez."])


def _cati_yazisi(ax, not_: str) -> None:
    ax.text(0.5, 0.5, not_, transform=ax.transAxes, ha="center", va="center", fontsize=12, color="#b03a2e", linespacing=1.5,
            bbox={"boxstyle": "round,pad=0.8", "fc": "white", "ec": "#b03a2e", "alpha": 0.95})


def _notlar(fig, say: dict, sayfa: int):
    """Sayımda kural yok varsa sayfanın başında EKSİK; bu sayfanın katmanında kural yok ve uyarı varsa lejantın altında. Çatı tipinden
    kural yokta (K5) satır kısadır: nedeni sayfanın çatı notunda ve sayımdadır."""
    from motor.yerlesim import girdi
    adlar, onekler = SAYFA[sayfa]
    if say["kural_yok"]:
        fig.text(0.02, 0.975, f"EKSİK · sayımda {len(say['kural_yok'])} parça \"kural yok\" (ayrıntı `_kart_sayim.json`); bu planlar tam değildir",
                 fontsize=11, color="#b03a2e", fontweight="bold", va="top")
    satir = list(dict.fromkeys(f"Kurulmadı: {x['parca']}: " + (f"{girdi.cati_adi(x['cati'])} çatı" if "cati" in x else x["neden"])
                               for x in say["kural_yok"] if x["parca"] in adlar or str(x["parca"]).startswith(onekler)))
    satir += [f"Uyarı: {u['metin']}" for u in say.get("yerlesim", {}).get("uyarilar", []) + say.get("elektrik", {}).get("uyarilar", [])
              + say.get("kenar", {}).get("uyarilar", []) if u["katman"] in adlar]
    if satir:
        fig.text(0.76, 0.30, "\n".join(textwrap.fill(s, 46) for s in satir[:8]) + ("\n…" if len(satir) > 8 else ""), fontsize=8.5,
                 va="top", ha="left", color="#b03a2e")


def ciz(model_yolu: Path, say: dict, yol: Path, kod: str) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    m = _model(Path(model_yolu))
    y = say["yerlesim"]
    cn = _cati_notu(say)
    if cn:
        m["makas"] = {}                                         # bugünkü IFC'nin beşik makasları sayılmadı (kural yok); çizilmez
    alt = (f"{kod} · kart modeli (İE-15 K2) · {Path(model_yolu).name} · kartlar sürüm {say['kartlar_surumu']}, yerleşim kuralları sürüm "
           f"{say['yerlesim_surumu']} · ölçüler cm · şekiller modeldeki parçalardan")
    kesim = say.get("kesim_plani", {})
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(str(yol), metadata={"Creator": "motor.kart_model (İE-15 K2)", "CreationDate": None, "ModDate": None}) as pdf:
        # 1 · tavan omega
        fig, ax = plt.subplots(figsize=(16.54, 11.69))
        _duvarlar(ax, m)
        for kk in ("AL-01", "AL-02"):                           # K5b-2: asma dizme tavanın gözleri ve H'ları, omegaların altında
            for p in m["k2"].get(kk, []):
                x0, y0 = p["v"][:, :2].min(0); x1, y1 = p["v"][:, :2].max(0)
                ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc=RENK["goz"][kk], ec=RENK["goz_kenar"], lw=0.3))
        for p in m["k2"].get("H-11", []):
            x0, y0 = p["v"][:, :2].min(0); x1, y1 = p["v"][:, :2].max(0)
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=RENK["tavan_h"], lw=0))
        OMK = [kk for kk in ("OM-01", "OM-02") if m["k2"].get(kk)] or ["OM-01"]   # OM-02: 100'lük iç duvarın üstü, 100'lük duvar omegası (D-32 ek)
        yer_ = lambda p: "dis_duvar" if p["p"].get("Duvar") == "dis" else p["p"].get("Yer", "ara")     # noqa: E731  (K5b-2: dış duvar)
        for kk in OMK:
            for p in m["k2"].get(kk, []):
                v, yer = p["v"], yer_(p)
                x0, y0 = v[:, :2].min(0); x1, y1 = v[:, :2].max(0)
                dik = (y1 - y0) > (x1 - x0)
                ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=RENK["omega"][yer], lw=0))
                ax.plot([(x0 + x1) / 2] * 2 if dik else [x0, x1], [y0, y1] if dik else [(y0 + y1) / 2] * 2, color=RENK["omega"][yer], lw=2.2)
                ax.text((x0 + x1) / 2 + (6 if dik else 0), (y0 + y1) / 2 + (0 if dik else 6), _sayi(p["p"]["Boy_cm"], 2).rstrip("0").rstrip(","),
                        rotation=90 if dik else 0, fontsize=7.5, ha="left" if dik else "center", va="center" if dik else "bottom", color="#222")
        sayac = {}
        for kk in OMK:
            for p in m["k2"].get(kk, []):
                sayac[yer_(p)] = sayac.get(yer_(p), 0) + 1
        lej = []
        for kk in OMK:
            k = _kart(say, kk)
            ad = k.get("ad") or "60'lık tavan omegası L 3750"
            lej += [f"{kk} {ad}", f"{k['adet']} parça, {_sayi(k.get('metre', 0))} m"]
        _lejant(fig, lej + [f"tavan: {y['tavan']}", ""]
                + [f"■ {OMEGA_YER[a]}: {n}" for a, n in sorted(sayac.items())]
                + [x for kk in OMK if kk in kesim for x in
                   (f"", f"kesim{'' if len(OMK) == 1 else ' ' + kk}: {kesim[kk]['stok']} boy L {kesim[kk]['parca_boyu_cm']:g}",
                    f"(tam parça {kesim[kk]['kullanilir_cm']:g}; yedek yok, karar D)")]
                + _tavan_lejanti(say, kesim))
        _cerceve(ax, f"{kod} · TAVAN OMEGA YERLEŞİM PLANI", alt)
        _notlar(fig, say, 1)
        pdf.savefig(fig); plt.close(fig)

        # 2 · makas ve dere
        fig, ax = plt.subplots(figsize=(16.54, 11.69))
        _duvarlar(ax, m, dolgu=False)
        for p in sorted(m["k2"].get("IZ-01", []), key=lambda p: p["p"]["Aralik"]):     # K5b-2: çatı izolasyonu, makas aralığı başına şerit
            x0, y0 = p["v"][:, :2].min(0); x1, y1 = p["v"][:, :2].max(0)
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc=RENK["izolasyon"][p["p"]["Aralik"] % 2], ec="#d4ac0d", lw=0.5))
            ax.text(x0 + 8, (y0 + y1) / 2, f"İ{p['p']['Aralik']}", fontsize=7.5, va="center", ha="left", color="#9a7d0a")
        for ad, mk in sorted(m["makas"].items()):
            iz = _iz(np.vstack(mk["uyeler"]))
            x, yy = iz.exterior.xy
            ax.fill(x, yy, color=RENK["makas"], alpha=0.85 if mk["bas"] else 0.55, lw=0)
            x0, y0, x1, y1 = iz.bounds
            yatay = (x1 - x0) > (y1 - y0)
            ax.text(x1 + 40 if yatay else (x0 + x1) / 2, (y0 + y1) / 2 if yatay else y1 + 40, f"{ad} ({'baş' if mk['bas'] else 'orta'})",
                    fontsize=8, va="center", ha="left" if yatay else "center", rotation=0 if yatay else 90, color=RENK["makas"])
        for p in m["k2"].get("MA-03", []):                     # yavru makas (K5b): taşan verandanın çatısı
            iz = _iz(p["v"]); x, yy = iz.exterior.xy
            ax.fill(x, yy, color=RENK["yavru_makas"], alpha=0.75, lw=0)
            x0, y0, x1, y1 = iz.bounds
            yatay = (x1 - x0) > (y1 - y0)
            ax.text(x1 + 25 if yatay else (x0 + x1) / 2, (y0 + y1) / 2 if yatay else y0 - 25, f"Y{p['p']['Sira']}", fontsize=7,
                    va="center" if yatay else "top", ha="left" if yatay else "center", color=RENK["yavru_makas"])
        for p in m["k2"].get("DR-01", []):
            iz = _iz(p["v"]); x, yy = iz.exterior.xy
            ax.fill(x, yy, color=RENK["dere"], alpha=0.7, lw=0)
            x0, y0, x1, y1 = iz.bounds
            dik = (y1 - y0) > (x1 - x0)
            ax.text((x0 + x1) / 2, (3 * y0 + y1) / 4 if dik else (y0 + y1) / 2, f"dere {_sayi(p['p']['Boy_cm'] / 100)} m",
                    rotation=90 if dik else 0, fontsize=8,
                    ha="center", va="center", color="white", fontweight="bold")
        for p in m["k2"].get("DR-02", []):
            cx, cy = p["v"][:, :2].mean(0)
            ax.add_patch(plt.Circle((cx, cy), 14, fc="white", ec=RENK["inis"], lw=1.6))
            ax.add_patch(plt.Circle((cx, cy), 5, color=RENK["inis"]))
        kd, ki = _kart(say, "DR-01"), _kart(say, "DR-02")
        ym = _kart(say, "MA-03")
        _lejant(fig, [f"MA-01 Makas (baş): {_kart(say, 'MA-01')['adet']}", f"MA-02 Makas (orta): {_kart(say, 'MA-02')['adet']}"]
                + ([f"MA-03 Yavru makas: {ym['adet']} (Y; veranda çatısı)"] if ym["adet"] else []) + ["",
                     f"DR-01 Metal dere: {kd['adet']} hat, {_sayi(kd.get('metre', 0))} m"]
                + ([f"   kesim: {kesim['DR-01']['stok']} boy L {kesim['DR-01']['parca_boyu_cm']:g}", f"   ({kesim['DR-01']['bindirme_cm']:g} cm bindirme)"]
                   if "DR-01" in kesim else [])
                + [f"DR-02 Dere inişi: {ki['adet']} (◎)"]
                + ([f"", f"IZ-01 Çatı izolasyonu: {iz['adet']} şerit (İ),", f"   {_sayi(kesim['IZ-01']['alan_m2'])} m² → {kesim['IZ-01']['stok']} paket "
                    f"({_sayi(kesim['IZ-01']['paket_m2'], 1)} m²)"] if (iz := _kart(say, "IZ-01"))["adet"] and "IZ-01" in kesim else []))
        if cn:
            _cati_yazisi(ax, cn)
        _cerceve(ax, f"{kod} · MAKAS VE DERE YERLEŞİM PLANI", alt)
        _notlar(fig, say, 2)
        pdf.savefig(fig); plt.close(fig)

        # 3 · baş makas betopanı (görünüş)
        levhalar = m["k2"].get("BT-01", [])
        baslar = sorted({p["p"]["Makas"] for p in levhalar})
        fig, axs = plt.subplots(max(1, len(baslar)), 1, figsize=(16.54, 11.69), squeeze=False)
        fig.subplots_adjust(left=0.04, right=0.74, top=0.88, bottom=0.10, hspace=0.25)
        for ax, ad in zip(axs[:, 0], baslar or [None]):
            ps = [p for p in levhalar if p["p"]["Makas"] == ad]
            v = np.vstack([p["v"] for p in ps]) if ps else np.zeros((1, 3))
            yatay = 0 if (v[:, 1].max() - v[:, 1].min()) < (v[:, 0].max() - v[:, 0].min()) else 1    # levhanın düzlemi x–z ya da y–z
            cati_ad = ps[0]["p"].get("Cati") if ps else None          # taşan verandanın kalkanı (K5b): altında dış kirişin yavru makası
            uyeler = (m["makas"][ad]["uyeler"] if ad in m["makas"] else
                      [p["v"] for p in m["k2"].get("MA-03", []) if cati_ad and p["p"].get("Cati") == cati_ad and p["p"].get("Yer") == "dış kiriş"])
            for u in uyeler:
                x, z = _iz(u, (yatay, 2)).exterior.xy
                ax.fill(x, z, color=RENK["yavru_makas" if cati_ad else "makas"], alpha=0.35, lw=0)
            for p in ps:
                iz = _iz(p["v"], (yatay, 2)); x, z = iz.exterior.xy
                ax.fill(x, z, fc=RENK["levha"], alpha=0.75, ec="#7b3f00", lw=1.2)
                u0, u1 = p["p"].get("LevhaU0_cm"), p["p"].get("LevhaU1_cm")
                lo, hi = iz.bounds[0], iz.bounds[2]
                if u0 is not None:                                      # dikey levha: uçtaki artan betopan taralı, levhanın kenarı kesik
                    from shapely.geometry import box
                    _x0, z0_, _x1, z1_ = iz.bounds
                    for uc in ([box(lo, z0_, u0, z1_)] if lo < u0 - 0.5 else []) + ([box(u1, z0_, hi, z1_)] if hi > u1 + 0.5 else []):
                        q = iz.intersection(uc)
                        if q.geom_type == "Polygon" and not q.is_empty:
                            x, z = q.exterior.xy
                            ax.fill(x, z, fc="#f5cba7", ec="#7b3f00", lw=0.8, ls="--", hatch="///")
                    c = ((u0 + u1) / 2, (z0_ + z1_) / 2)
                else:
                    c = (iz.centroid.x, iz.centroid.y)
                ax.text(*c, f"{p['p']['Levha']}\n{p['p']['Levha_cm']}", ha="center", va="center", fontsize=8)
            ax.set_aspect("equal"); ax.axis("off")
            ax.set_title((f"{ad}, dış yüzden görünüş" if cati_ad else f"{ad} (baş makas), dış yüzden görünüş") if ad else "" if cn else "baş makas yok",
                         fontsize=11)
            if cn:
                _cati_yazisi(ax, cn)
        kb = _kart(say, "BT-01")
        basina = {}
        for p in levhalar:
            basina.setdefault(p["p"]["Makas"], p["p"]["LevhaAdedi"])
        dikey = any(p["p"].get("Dizilim") == "dikey" for p in levhalar)
        _lejant(fig, [f"BT-01 Baş makas betopanı 1250 × 2500",
                      f"{kb['adet']} levha (makas başına {next(iter(basina.values()), 0)})" if len(set(basina.values())) <= 1
                      else f"{kb['adet']} levha", *([f"   {a}: {n}" for a, n in basina.items()] if len(set(basina.values())) > 1 else []),
                      "levha yerinde kesilir; sayı tam levha",
                      *(["dikey: uçlar artan betopanla (kesik çizginin dışı)"] if dikey else []), "", f"SR-01 PVC plastik betopan H'ı: {say.get('sabit', {}).get('SR-01', {}).get('adet', '—')}",
                             "(sabit paket, liste kuralı; modelde yok)"])
        fig.suptitle(f"{kod} · BAŞ MAKAS BETOPAN YERLEŞİMİ", fontsize=15, fontweight="bold", x=0.02, ha="left", y=0.95 if say["kural_yok"] else 0.98)
        fig.text(0.02, 0.03, alt, fontsize=9, color="#444")
        _notlar(fig, say, 3)
        pdf.savefig(fig); plt.close(fig)

        # 4 · aşık ve 5 · çatı kaplaması
        KP = [kk for kk in ("KP-01", "KP-02") if m["k2"].get(kk)] or ["KP-01"]   # sandviç ya da tek kat panel (K5b)
        for sayfa, kart, baslik in ((4, "AS-01", "AŞIK YERLEŞİM PLANI"), (5, KP[0], "ÇATI KAPLAMASI YERLEŞİM PLANI")):
            fig, ax = plt.subplots(figsize=(16.54, 11.69))
            _duvarlar(ax, m, dolgu=False)
            parcalar = [p for kk in ([kart] if kart == "AS-01" else KP) for p in m["k2"].get(kk, [])]
            for i, p in enumerate(sorted(parcalar, key=lambda p: (p["p"].get("Yuz", ""), p["p"].get("Sira", p["p"].get("Serit", 0)), p["ad"]))):
                iz = _iz(p["v"]); x0, y0, x1, y1 = iz.bounds
                dik = (y1 - y0) > (x1 - x0)
                if kart == "AS-01":
                    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=RENK["asik"], lw=0))
                    ax.plot([(x0 + x1) / 2] * 2 if dik else [x0, x1], [y0, y1] if dik else [(y0 + y1) / 2] * 2, color=RENK["asik"], lw=1.8)
                    sol = p["p"]["Yuz"] == "sol"
                    ax.text((x0 + x1) / 2 + ((-5 if sol else 5) if dik else 0), (y0 + y1) / 2 + (0 if dik else (-5 if sol else 5)),
                            _sayi(p["p"]["Boy_cm"], 2).rstrip("0").rstrip(","), rotation=90 if dik else 0, fontsize=7, color="#1b2631",
                            ha=("right" if sol else "left") if dik else "center", va="center" if dik else ("top" if sol else "bottom"))
                else:
                    renk = RENK["kaplama"][p["p"]["Serit"] % 2]
                    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc=renk, ec="#7d6608", lw=0.8))
                    ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{p['p']['Serit']}\n{p['p']['Genislik_cm']:g} × {p['p']['PanelBoyu_cm']:g}",
                            fontsize=7, ha="center", va="center")
            ka = _kart(say, kart)
            if kart == "AS-01":
                catilar = list(dict.fromkeys(p["p"].get("Cati", "") for p in sorted(parcalar, key=lambda p: p["p"].get("Cati", ""))))
                sira_ = []
                for c in catilar:
                    yz_ = sorted({p["p"]["Yuz"] for p in parcalar if p["p"].get("Cati", "") == c})
                    sira_.append(f"{c or 'ana çatı'}: " + ", ".join(
                        f"{YUZ[yz]} {len({p['p']['Sira'] for p in parcalar if p['p'].get('Cati', '') == c and p['p']['Yuz'] == yz})}" for yz in yz_))
                _lejant(fig, [f"AS-01 Aşık L 4200", f"{ka['adet']} parça, {_sayi(ka.get('metre', 0))} m",
                             "sıralar (yüz başına):", *[f"   {x}" for x in sira_], "mahyadan 60 cm, saçakta bir sıra (karar C)"]
                        + ([f"kesim: {kesim['AS-01']['stok']} boy L {kesim['AS-01']['parca_boyu_cm']:g}", f"(tam parça {kesim['AS-01']['kullanilir_cm']:g}; yedek yok, karar D)"]
                           if "AS-01" in kesim else []))
            else:
                boy = sorted({p["p"]["PanelBoyu_cm"] for p in parcalar})
                yuz = {}
                for p in parcalar:
                    yuz[p["p"]["Yuz"]] = yuz.get(p["p"]["Yuz"], 0) + 1
                tasma = sorted({p["p"].get("Tasma_cm", 0) for p in parcalar} - {0})
                genis = sorted({p["p"]["Genislik_cm"] for p in parcalar})
                ka = {"adet": sum(_kart(say, kk)["adet"] for kk in KP), "ad": " + ".join(_kart(say, kk).get("ad", kk) for kk in KP)}
                _lejant(fig, [f"{' + '.join(KP)} {ka['ad'] if ka['ad'] != 'KP-01' else 'Sandviç panel (100 cm kapatır)'}",
                             f"{ka['adet']} panel" + (f" ({', '.join(f'{YUZ[a]} yüz {n}' for a, n in sorted(yuz.items()))})" if yuz else ""),
                             *([f"kapatır {', '.join(f'{b:g}' for b in genis)} cm"] if genis else []),
                             *([f"boy {', '.join(f'{b:g}' for b in boy)} cm (eğik boy + 5, 10 mm'ye yukarı)"] if boy else []),
                             "son şerit yüzün ucundan taşar" + (f" ({', '.join(f'{x:g}' for x in tasma)} cm)" if tasma else ""),
                             *(["iki: verandada iki yüzün artan şeritleri bir panelden"] if "iki" in yuz else [])])
            if cn:
                _cati_yazisi(ax, cn)
            _cerceve(ax, f"{kod} · {baslik}", alt)
            _notlar(fig, say, sayfa)
            pdf.savefig(fig); plt.close(fig)

        # 6 · elektrik (K3)
        if "elektrik" in say:
            fig, ax = plt.subplots(figsize=(16.54, 11.69))
            _elektrik(ax, m, say, plt)
            _cerceve(ax, f"{kod} · ELEKTRİK YERLEŞİM PLANI", alt.replace("(İE-15 K2)", "(İE-15 K3)"))
            _lejant(fig, _elektrik_lejanti(say))
            _notlar(fig, say, 6)
            pdf.savefig(fig); plt.close(fig)

        # 7 · alt çerçeve ve çatı kenarları (K3b)
        if "kenar" in say:
            fig = plt.figure(figsize=(16.54, 11.69))
            zemin, cati_ = fig.add_axes([0.02, 0.08, 0.35, 0.80]), fig.add_axes([0.39, 0.08, 0.35, 0.80])
            _kenar(zemin, cati_, m, plt)
            if cn:
                _cati_yazisi(cati_, cn)
            fig.suptitle(f"{kod} · ALT ÇERÇEVE VE ÇATI KENARLARI YERLEŞİM PLANI", fontsize=15, fontweight="bold", x=0.02, ha="left",
                         y=0.95 if say["kural_yok"] else 0.98)
            fig.text(0.02, 0.03, alt.replace("(İE-15 K2)", "(İE-15 K3b)"), fontsize=9, color="#444")
            _kenar_lejanti(fig, say, plt)
            _notlar(fig, say, 7)
            pdf.savefig(fig); plt.close(fig)
    return yol


def _kenar(zemin, cati_, m: dict, plt) -> None:
    """Solda zemin: alt çerçeve parçaları (100'lük ve 60'lık ayrı renk; kesilen kapı boşlukları açık), her hattın numarası ve boyu.
    Sağda çatı planı: saçak omegası duvarın üstünde, saçak sacı saçakta, mahya mahyada, her baş makasın iki eğik kenarında Z (duvarın
    dış yüzünde), C kapama (aşık uçlarında) ve alın sacı (C'nin önünde). Şekiller modeldeki parçaların plan izidir."""
    _duvarlar(zemin, m, dolgu=True)
    hatlar = {}
    for kod in ("AC-01", "AC-02"):
        for p in m["k2"].get(kod, []):
            x0, y0 = p["v"][:, :2].min(0); x1, y1 = p["v"][:, :2].max(0)
            zemin.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=KENAR_RENK[kod], lw=0))
            h = hatlar.setdefault(p["p"]["Hat"], {"kod": kod, "boy": p["p"]["HatBoyu_cm"], "k": []})
            h["k"].append((x0, y0, x1, y1))
    for no, h in sorted(hatlar.items()):                    # hattın yazısı en uzun parçasının ortasında (kapı ve T'den uzak)
        x0, y0, x1, y1 = max(h["k"], key=lambda k: max(k[2] - k[0], k[3] - k[1]))
        dik = (y1 - y0) > (x1 - x0)
        zemin.text((x0 + x1) / 2 + (9 if dik else 0), (y0 + y1) / 2 + (0 if dik else 9),
                   f"{no} · {h['boy']:g}".replace(".", ","), rotation=90 if dik else 0,
                   fontsize=7, ha="left" if dik else "center", va="center" if dik else "bottom", color=KENAR_RENK[h["kod"]])
    zemin.set_aspect("equal"); zemin.axis("off"); zemin.set_anchor("N")
    zemin.set_title("Zemin · alt çerçeve (hat no · hat boyu cm; kapı boşlukları açık)", fontsize=11, loc="left")

    _duvarlar(cati_, m, dolgu=False)
    for ad, mk in sorted(m["makas"].items()):
        x, yy = _iz(np.vstack(mk["uyeler"])).exterior.xy
        cati_.fill(x, yy, color=RENK["makas"], alpha=0.12, lw=0)
    for kod, alfa in (("CK-02", 0.55), ("CK-06", 0.75), ("CK-01", 0.9)):
        for p in m["k2"].get(kod, []):
            iz = _iz(p["v"]); x, yy = iz.exterior.xy
            cati_.fill(x, yy, color=KENAR_RENK[kod], alpha=alfa, lw=0)
    for kod in ("CK-03", "CK-05", "CK-04"):
        for p in m["k2"].get(kod, []):
            iz = _iz(p["v"]); x, yy = iz.exterior.xy
            cati_.fill(x, yy, color=KENAR_RENK[kod], lw=0)
    from shapely.ops import unary_union
    orta = unary_union(m["duvar"]).centroid if m["duvar"] else None
    for p in m["k2"].get("CK-04", []):                      # her kalkan kenarının eğik boyu, Z'nin iç yanında
        x0, y0, x1, y1 = _iz(p["v"]).bounds
        dik = (y1 - y0) > (x1 - x0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ic = 1 if orta is None or ((orta.x > cx) if dik else (orta.y > cy)) else -1
        cati_.text(cx + (14 * ic if dik else 0), cy + (0 if dik else 14 * ic), f"{p['p']['Makas']} {YUZ[p['p']['Yuz']]}: {_sayi(p['p']['Boy_cm'], 1)}",
                   rotation=90 if dik else 0, fontsize=6.5, ha=("left" if ic > 0 else "right") if dik else "center",
                   va="center" if dik else ("bottom" if ic > 0 else "top"), color=KENAR_RENK["CK-04"])
    for kod, ad in (("CK-02", "saçak sacı"), ("CK-01", "saçak omegası"), ("CK-06", "mahya")):
        for p in m["k2"].get(kod, []):
            x0, y0, x1, y1 = _iz(p["v"]).bounds
            dik = (y1 - y0) > (x1 - x0)
            cati_.text((x0 + x1) / 2 if dik else (3 * x0 + x1) / 4, (3 * y0 + y1) / 4 if dik else (y0 + y1) / 2,
                       f"{ad} {p['p']['Boy_cm']:g}", rotation=90 if dik else 0, fontsize=6.5, ha="center", va="center", color="#1b2631",
                       bbox={"boxstyle": "round,pad=0.1", "fc": "white", "ec": "none", "alpha": 0.8})
    cati_.set_aspect("equal"); cati_.axis("off"); cati_.set_anchor("N")
    cati_.set_title("Çatı · saçak, mahya ve kalkan kenarları (boylar cm)", fontsize=11, loc="left")


def _kenar_lejanti(fig, say: dict, plt) -> None:
    """Her kartın modeldeki sayısı (kesim planı: boy; C kapama metre) ve liste üretecinin aynı satırı yan yana. Kuralı kurulmayan kart
    "kurulmadı", liste üretecinin yazmadığı liste "liste yazılmaz" (K5)."""
    from matplotlib.patches import Patch
    from motor.kart_model import LISTE_YAZILMAZ
    kesim, liste, kurulmadi = say.get("kesim_plani", {}), say["kenar"]["liste"], set(say["kenar"].get("kurulmadi", []))
    tutamak, yazi = [], []
    for k in say["kartlar"]:
        if k["kod"] not in KENAR_RENK:
            continue
        kp = kesim.get(k["kod"])
        model = "kurulmadı" if k["kod"] in kurulmadi else f"{kp['stok']} boy" if kp else f"{_sayi(k.get('metre', 0))} m"
        lst = liste.get(k["kod"])
        lst = ("listede yok" if lst is None else "liste yazılmaz" if lst == LISTE_YAZILMAZ
               else f"liste {lst}" + ("" if kp and kp["stok"] == lst else "  ≠"))
        tutamak.append(Patch(color=KENAR_RENK[k["kod"]]))
        yazi.append(f"{k['kod']} {k['ad']}\nmodel {model} · {lst}")
    fig.legend(tutamak, yazi, loc="upper left", bbox_to_anchor=(0.76, 0.90), fontsize=9, frameon=True, edgecolor="#999",
               title="model (kesim planı) · liste üreteci", title_fontsize=9, labelspacing=0.9)
    fig.text(0.76, 0.56, "\n".join(textwrap.fill(s, 48) for s in (
        *([f"Liste üreteci: {say['kenar']['liste_yazilmaz']}."] if "liste_yazilmaz" in say["kenar"] else []),
        "Sayı listenin yöntemiyle, boy modelden (kesim planı); C kapama metreyle sayılır.",
        "Yer montaj rehberinden; teyit bekleyen maddeler varsayım (Lokman, 25 Ekim).",
        "Saçak omegası rehberdeki gibi duvar boyunca (verandada kiriş boyunca); liste saçak boyunu sayar.",
        *(["Veranda kalkanında C kapama var (rehberdeki gibi dört kalkanda), Z yok (liste O7'yi yalnız ana çatıda sayar)."]
          if any(p.get("bilgi", {}).get("Cati") for p in say.get("yerlesim", {}).get("parcalar", [])) else []))), fontsize=8.5, va="top", ha="left", color="#444")


def _elektrik(ax, m: dict, say: dict, plt) -> None:
    """Noktalar modeldeki parçaların yerinden (kutunun plandaki ortası; duvardakiler okunsun diye odaya doğru 14 cm içeride çizilir, zil
    anahtarın üstüne düşebildiği için 32 cm); oda adları sayımın oda özetinden; kablo çizgisi modeldeki çubuktan."""
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import polylabel, unary_union
    _duvarlar(ax, m, dolgu=True)
    duvar = unary_union(m["duvar"])

    def ice(x0, y0, x1, y1, a=14):                               # duvardaki kutunun ince ekseninde duvardan uzak yan
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if (x1 - x0) <= (y1 - y0):
            return (cx + (a if duvar.distance(Point(x0, cy)) < duvar.distance(Point(x1, cy)) else -a), cy)
        return (cx, cy + (a if duvar.distance(Point(cx, y0)) < duvar.distance(Point(cx, y1)) else -a))
    for o in say["elektrik"]["odalar"]:
        if o["poligon"]:                                          # ad, odanın ortasıyla alt duvarının arasında (tavandaki noktanın altında)
            pg = Polygon(o["poligon"])
            c = polylabel(pg, tolerance=1)
            alt_ = min(y for x, y in LineString([(c.x, c.y), (c.x, pg.bounds[1] - 1)]).intersection(pg).coords)
            ek = f"{o['takim']} takım" if o["takim"] else o["kaynak"].split(" + ")[0]
            ax.text(c.x, (c.y + alt_) / 2, f"{o['ad']}\n{_sayi(o['alan_m2'])} m² · {ek}", fontsize=7.5, ha="center", va="center", color="#666")
    for kod in ("EL-10", "EL-11"):
        for p in m["k2"].get(kod, []):
            v = p["v"][:, :2]
            i, j = np.unravel_index(np.argmax(((v[:, None, :] - v[None, :, :]) ** 2).sum(-1)), (len(v), len(v)))
            ax.plot([v[i, 0], v[j, 0]], [v[i, 1], v[j, 1]], ls="--", lw=1.4, color=ELEKTRIK_RENK[kod], alpha=0.8)
    for kod, ps in sorted(m["k2"].items()):
        if not kod.startswith("EL-") or kod in ("EL-10", "EL-11"):
            continue
        r = ELEKTRIK_RENK[kod]
        for p in ps:
            x0, y0 = p["v"][:, :2].min(0); x1, y1 = p["v"][:, :2].max(0)
            cx, cy = ice(x0, y0, x1, y1, 32 if kod == "EL-08" else 14) if p["p"].get("Yer") != "tavan" else ((x0 + x1) / 2, (y0 + y1) / 2)
            if kod == "EL-01":
                ax.add_patch(plt.Rectangle((cx - 12, cy - 12), 24, 24, color=r))
            elif kod == "EL-02":
                ax.add_patch(plt.Circle((cx, cy), 11, fc="white", ec=r, lw=1.6))
                ax.plot([cx - 8, cx + 8], [cy - 8, cy + 8], color=r, lw=1.2); ax.plot([cx - 8, cx + 8], [cy + 8, cy - 8], color=r, lw=1.2)
            elif kod in ("EL-03", "EL-04"):
                ax.add_patch(plt.Circle((cx, cy), 6, color=r))
                for k in range(1 if kod == "EL-03" else 2):
                    ax.plot([cx + 4 + 5 * k, cx + 12 + 5 * k], [cy + 4, cy + 14], color=r, lw=1.4)
            elif kod == "EL-09":
                ax.add_patch(plt.Rectangle((x0, y0), max(x1 - x0, 6), max(y1 - y0, 6), color=r))
                ax.text(cx, cy + 14, "SİGORTA", fontsize=6.5, ha="center", va="bottom", color=r, fontweight="bold")
            else:
                yazi = {"EL-05": "U", "EL-06": "UU", "EL-07": "TV", "EL-08": "Z"}[kod]
                ax.text(cx, cy, yazi, fontsize=8, ha="center", va="center", color=r, fontweight="bold",
                        bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": r, "lw": 0.8})


def _elektrik_lejanti(say: dict) -> list[str]:
    E = say["elektrik"]
    satir = ["Sayılar kuraldan (Lokman, 18 Ekim;", f"oda ve veranda takımı, her {E['degerler']['oda_kurali']['takim_m2']:g} m²'ye".replace(".", ","),
             "bir takım; banyo, mutfak, hol kitaptan).",
             "Yerler varsayım (plan §6).", ""]
    isaret = {"EL-01": "■", "EL-02": "⊗", "EL-03": "●╱", "EL-04": "●╱╱", "EL-05": "U", "EL-06": "UU", "EL-07": "TV", "EL-08": "Z", "EL-09": "▬"}
    for k in say["kartlar"]:
        if k["kod"] in isaret:
            satir.append(f"{isaret[k['kod']]}  {k['ad']}: {k['adet']}")
    satir.append("")
    for x in E["kablo"]:
        kart = "EL-10" if x["parca"] == "kablo_priz" else "EL-11"
        ad = next(k["ad"] for k in say["kartlar"] if k["kod"] == kart)
        satir += [f"- - {ad}: {x['metre']} m", f"    {x['hat']} hattı: {x['w_otomat']} W otomat × {_sayi(x['en_uzak_m'])} m",
                  f"    + {x['noktalar']} nokta × {_sayi(x['nokta_basina_m'], 0)} m, yukarı"]
    return satir
