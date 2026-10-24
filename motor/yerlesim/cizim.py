"""K2'nin beş yerleşim planı, kart modelinin IFC'sinden çizilir: tavan omega, makas ve dere, baş makas betopanı, aşık, çatı kaplaması.

Her şekil modeldeki parçanın kendi geometrisinden (dünya koordinatı) ve özellik setinden okunur; planlar yerleşim kurallarının çıktısından
değil modelden gelir. Sayılar (adet, metre, kesim) sayımdandır (`<kod>_kart_sayim.json`). Antet bizimdir; paftanın anteti ve adları
çıktıya girmez. Paftayla kıyas hakemin işidir (`testler/kimlik/hakem/kiyas.py`). Sayımda "kural yok" varsa her sayfanın başında EKSİK
yazar; sayfanın katmanı kurulmadıysa nedeni, yerleşimin uyarıları da ilgili sayfada yazar.
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
RENK = {"duvar": "#c9c9c9", "duvar_kenar": "#8a8a8a", "omega": {"duvar_ekseni": "#c0392b", "duvar_yuzu": "#8e44ad", "ara": "#e67e22"},
        "makas": "#2c3e50", "dere": "#2e86c1", "inis": "#1b4f72", "asik": "#2471a3", "kaplama": ("#f4d03f", "#f9e79f"), "levha": "#e67e22"}
OMEGA_YER = {"duvar_ekseni": "iç duvar ekseninde", "duvar_yuzu": "duvar yüzünde", "ara": "arada"}
YUZ = {"sol": "sol", "sag": "sağ"}
# sayfanın katmanları: kural yokta katmanın adı (`motor.yerlesim`), parça adının öneki ve uyarının katmanı
SAYFA = {1: (("tavan omegası",), ("OMEGA_",)), 2: (("dere ve iniş", "iniş"), ("DERE_", "INIS_")), 3: (("baş makas betopanı",), ("BETOPAN_",)),
         4: (("aşık",), ("ASIK_",)), 5: (("çatı kaplaması",), ("KAPLAMA_",))}


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


def _notlar(fig, say: dict, sayfa: int):
    """Sayımda kural yok varsa sayfanın başında EKSİK; bu sayfanın katmanında kural yok ve uyarı varsa lejantın altında."""
    adlar, onekler = SAYFA[sayfa]
    if say["kural_yok"]:
        fig.text(0.02, 0.975, f"EKSİK · sayımda {len(say['kural_yok'])} parça \"kural yok\" (ayrıntı `_kart_sayim.json`); bu planlar tam değildir",
                 fontsize=11, color="#b03a2e", fontweight="bold", va="top")
    satir = [f"Kurulmadı: {x['parca']}: {x['neden']}" for x in say["kural_yok"]
             if x["parca"] in adlar or str(x["parca"]).startswith(onekler)]
    satir += [f"Uyarı: {u['metin']}" for u in say.get("yerlesim", {}).get("uyarilar", []) if u["katman"] in adlar]
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
    alt = (f"{kod} · kart modeli (İE-15 K2) · {Path(model_yolu).name} · kartlar sürüm {say['kartlar_surumu']}, yerleşim kuralları sürüm "
           f"{say['yerlesim_surumu']} · ölçüler cm · şekiller modeldeki parçalardan")
    kesim = say.get("kesim_plani", {})
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(str(yol), metadata={"Creator": "motor.kart_model (İE-15 K2)", "CreationDate": None, "ModDate": None}) as pdf:
        # 1 · tavan omega
        fig, ax = plt.subplots(figsize=(16.54, 11.69))
        _duvarlar(ax, m)
        for p in m["k2"].get("OM-01", []):
            v, yer = p["v"], p["p"].get("Yer", "ara")
            x0, y0 = v[:, :2].min(0); x1, y1 = v[:, :2].max(0)
            dik = (y1 - y0) > (x1 - x0)
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=RENK["omega"][yer], lw=0))
            ax.plot([(x0 + x1) / 2] * 2 if dik else [x0, x1], [y0, y1] if dik else [(y0 + y1) / 2] * 2, color=RENK["omega"][yer], lw=2.2)
            ax.text((x0 + x1) / 2 + (6 if dik else 0), (y0 + y1) / 2 + (0 if dik else 6), _sayi(p["p"]["Boy_cm"], 2).rstrip("0").rstrip(","),
                    rotation=90 if dik else 0, fontsize=7.5, ha="left" if dik else "center", va="center" if dik else "bottom", color="#222")
        k = _kart(say, "OM-01")
        sayac = {}
        for p in m["k2"].get("OM-01", []):
            sayac[p["p"].get("Yer")] = sayac.get(p["p"].get("Yer"), 0) + 1
        _lejant(fig, [f"OM-01 60'lık tavan omegası L 3750", f"{k['adet']} parça, {_sayi(k.get('metre', 0))} m", f"tavan: {y['tavan']}", ""]
                + [f"■ {OMEGA_YER[a]}: {n}" for a, n in sorted(sayac.items())]
                + ([f"", f"kesim: {kesim['OM-01']['stok']} boy L {kesim['OM-01']['parca_boyu_cm']:g}", f"(tam parça {kesim['OM-01']['kullanilir_cm']:g}; yedek yok, karar D)"]
                   if "OM-01" in kesim else []))
        _cerceve(ax, f"{kod} · TAVAN OMEGA YERLEŞİM PLANI", alt)
        _notlar(fig, say, 1)
        pdf.savefig(fig); plt.close(fig)

        # 2 · makas ve dere
        fig, ax = plt.subplots(figsize=(16.54, 11.69))
        _duvarlar(ax, m, dolgu=False)
        for ad, mk in sorted(m["makas"].items()):
            iz = _iz(np.vstack(mk["uyeler"]))
            x, yy = iz.exterior.xy
            ax.fill(x, yy, color=RENK["makas"], alpha=0.85 if mk["bas"] else 0.55, lw=0)
            x0, y0, x1, y1 = iz.bounds
            yatay = (x1 - x0) > (y1 - y0)
            ax.text(x1 + 40 if yatay else (x0 + x1) / 2, (y0 + y1) / 2 if yatay else y1 + 40, f"{ad} ({'baş' if mk['bas'] else 'orta'})",
                    fontsize=8, va="center", ha="left" if yatay else "center", rotation=0 if yatay else 90, color=RENK["makas"])
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
        _lejant(fig, [f"MA-01 Makas (baş): {_kart(say, 'MA-01')['adet']}", f"MA-02 Makas (orta): {_kart(say, 'MA-02')['adet']}", "",
                     f"DR-01 Metal dere: {kd['adet']} hat, {_sayi(kd.get('metre', 0))} m"]
                + ([f"   kesim: {kesim['DR-01']['stok']} boy L {kesim['DR-01']['parca_boyu_cm']:g}", f"   ({kesim['DR-01']['bindirme_cm']:g} cm bindirme)"]
                   if "DR-01" in kesim else [])
                + [f"DR-02 Dere inişi: {ki['adet']} (◎)"])
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
            if ad in m["makas"]:
                for u in m["makas"][ad]["uyeler"]:
                    x, z = _iz(u, (yatay, 2)).exterior.xy
                    ax.fill(x, z, color=RENK["makas"], alpha=0.35, lw=0)
            for p in ps:
                iz = _iz(p["v"], (yatay, 2)); x, z = iz.exterior.xy
                ax.fill(x, z, fc=RENK["levha"], alpha=0.75, ec="#7b3f00", lw=1.2)
                c = iz.centroid
                ax.text(c.x, c.y, f"{p['p']['Levha']}\n{p['p']['Levha_cm']}", ha="center", va="center", fontsize=8)
            ax.set_aspect("equal"); ax.axis("off")
            ax.set_title(f"{ad} (baş makas), dış yüzden görünüş" if ad else "baş makas yok", fontsize=11)
        kb = _kart(say, "BT-01")
        _lejant(fig, [f"BT-01 Baş makas betopanı 1250 × 2500", f"{kb['adet']} levha (makas başına {levhalar[0]['p']['LevhaAdedi'] if levhalar else 0})",
                             "levha yerinde kesilir; sayı tam levha", "", f"SR-01 PVC plastik betopan H'ı: {say.get('sabit', {}).get('SR-01', {}).get('adet', '—')}",
                             "(sabit paket, liste kuralı; modelde yok)"])
        fig.suptitle(f"{kod} · BAŞ MAKAS BETOPAN YERLEŞİMİ", fontsize=15, fontweight="bold", x=0.02, ha="left")
        fig.text(0.02, 0.03, alt, fontsize=9, color="#444")
        _notlar(fig, say, 3)
        pdf.savefig(fig); plt.close(fig)

        # 4 · aşık ve 5 · çatı kaplaması
        for sayfa, kart, baslik in ((4, "AS-01", "AŞIK YERLEŞİM PLANI"), (5, "KP-01", "ÇATI KAPLAMASI YERLEŞİM PLANI")):
            fig, ax = plt.subplots(figsize=(16.54, 11.69))
            _duvarlar(ax, m, dolgu=False)
            parcalar = m["k2"].get(kart, [])
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
                yuzler = sorted({p["p"]["Yuz"] for p in parcalar})
                siralar = {yz: len({p["p"]["Sira"] for p in parcalar if p["p"]["Yuz"] == yz}) for yz in yuzler}
                _lejant(fig, [f"AS-01 Aşık L 4200", f"{ka['adet']} parça, {_sayi(ka.get('metre', 0))} m",
                             "sıralar: " + ", ".join(f"{YUZ[yz]} yüz {n}" for yz, n in siralar.items()), "mahyadan 60 cm, saçakta bir sıra (karar C)"]
                        + ([f"kesim: {kesim['AS-01']['stok']} boy L {kesim['AS-01']['parca_boyu_cm']:g}", f"(tam parça {kesim['AS-01']['kullanilir_cm']:g}; yedek yok, karar D)"]
                           if "AS-01" in kesim else []))
            else:
                boy = sorted({p["p"]["PanelBoyu_cm"] for p in parcalar})
                yuz = {}
                for p in parcalar:
                    yuz[p["p"]["Yuz"]] = yuz.get(p["p"]["Yuz"], 0) + 1
                tasma = sorted({p["p"].get("Tasma_cm", 0) for p in parcalar} - {0})
                _lejant(fig, [f"KP-01 Sandviç panel (100 cm kapatır)",
                             f"{ka['adet']} panel" + (f" ({', '.join(f'{YUZ[a]} yüz {n}' for a, n in sorted(yuz.items()))})" if yuz else ""),
                             *([f"boy {', '.join(f'{b:g}' for b in boy)} cm (eğik boy + 5, 10 mm'ye yukarı)"] if boy else []),
                             "son şerit yüzün ucundan taşar" + (f" ({', '.join(f'{x:g}' for x in tasma)} cm)" if tasma else "")])
            _cerceve(ax, f"{kod} · {baslik}", alt)
            _notlar(fig, say, sayfa)
            pdf.savefig(fig); plt.close(fig)
    return yol
