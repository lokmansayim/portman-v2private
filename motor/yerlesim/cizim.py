"""K2'nin beş yerleşim planı, K3'ün elektrik planı ve K3b'nin alt çerçeve ve çatı kenarları planı, kart modelinin IFC'sinden çizilir: tavan
omega, makas ve dere, baş makas betopanı, aşık, çatı kaplaması; sayımda elektrik varsa (komut her zaman kurar) altıncı sayfa elektrik
yerleşim planı, kenar varsa (komut her zaman kurar) yedinci sayfa alt çerçeve (zemin) ve çatı kenarlarıdır (çatı planı); yedinci sayfanın
lejantında her kartın sayısı liste üretecinin aynı satırıyla yan yanadır.

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
         4: (("aşık",), ("ASIK_",)), 5: (("çatı kaplaması",), ("KAPLAMA_",)),
         6: (("elektrik", "elektrik noktaları", "kablo_priz", "kablo_aydinlatma"),
             ("DUY_", "GLOP_", "ANAHTAR_", "PRIZ_", "UYDU_", "ZIL_", "SIGORTA_", "KABLO_")),
         7: (("alt çerçeve", "saçak omegası", "saçak sacı", "alın sacı", "baş makas Z'si", "C kapama", "mahya", "alt çerçeve ve çatı kenarları"),
             ("ALT_CERCEVE_", "SACAK_OMEGASI_", "SACAK_SACI_", "ALIN_SACI_", "BAS_MAKAS_Z_", "C_KAPAMA_", "MAHYA_"))}
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
    alt = (f"{kod} · kart modeli (İE-15 K2) · {Path(model_yolu).name} · kartlar sürüm {say['kartlar_surumu']}, yerleşim kuralları sürüm "
           f"{say['yerlesim_surumu']} · ölçüler cm · şekiller modeldeki parçalardan")
    kesim = say.get("kesim_plani", {})
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(str(yol), metadata={"Creator": "motor.kart_model (İE-15 K2)", "CreationDate": None, "ModDate": None}) as pdf:
        # 1 · tavan omega
        fig, ax = plt.subplots(figsize=(16.54, 11.69))
        _duvarlar(ax, m)
        OMK = [kk for kk in ("OM-01", "OM-02") if m["k2"].get(kk)] or ["OM-01"]   # OM-02: 100'lük iç duvarın üstü, 100'lük duvar omegası (D-32 ek)
        for kk in OMK:
            for p in m["k2"].get(kk, []):
                v, yer = p["v"], p["p"].get("Yer", "ara")
                x0, y0 = v[:, :2].min(0); x1, y1 = v[:, :2].max(0)
                dik = (y1 - y0) > (x1 - x0)
                ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=RENK["omega"][yer], lw=0))
                ax.plot([(x0 + x1) / 2] * 2 if dik else [x0, x1], [y0, y1] if dik else [(y0 + y1) / 2] * 2, color=RENK["omega"][yer], lw=2.2)
                ax.text((x0 + x1) / 2 + (6 if dik else 0), (y0 + y1) / 2 + (0 if dik else 6), _sayi(p["p"]["Boy_cm"], 2).rstrip("0").rstrip(","),
                        rotation=90 if dik else 0, fontsize=7.5, ha="left" if dik else "center", va="center" if dik else "bottom", color="#222")
        sayac = {}
        for kk in OMK:
            for p in m["k2"].get(kk, []):
                sayac[p["p"].get("Yer")] = sayac.get(p["p"].get("Yer"), 0) + 1
        lej = []
        for kk in OMK:
            k = _kart(say, kk)
            ad = k.get("ad") or "60'lık tavan omegası L 3750"
            lej += [f"{kk} {ad}", f"{k['adet']} parça, {_sayi(k.get('metre', 0))} m"]
        _lejant(fig, lej + [f"tavan: {y['tavan']}", ""]
                + [f"■ {OMEGA_YER[a]}: {n}" for a, n in sorted(sayac.items())]
                + [x for kk in OMK if kk in kesim for x in
                   (f"", f"kesim{'' if len(OMK) == 1 else ' ' + kk}: {kesim[kk]['stok']} boy L {kesim[kk]['parca_boyu_cm']:g}",
                    f"(tam parça {kesim[kk]['kullanilir_cm']:g}; yedek yok, karar D)")])
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
            fig.suptitle(f"{kod} · ALT ÇERÇEVE VE ÇATI KENARLARI YERLEŞİM PLANI", fontsize=15, fontweight="bold", x=0.02, ha="left")
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
    """Her kartın modeldeki sayısı (kesim planı: boy; C kapama metre) ve liste üretecinin aynı satırı yan yana."""
    from matplotlib.patches import Patch
    kesim, liste = say.get("kesim_plani", {}), say["kenar"]["liste"]
    tutamak, yazi = [], []
    for k in say["kartlar"]:
        if k["kod"] not in KENAR_RENK:
            continue
        kp = kesim.get(k["kod"])
        model = f"{kp['stok']} boy" if kp else f"{_sayi(k.get('metre', 0))} m"
        lst = liste.get(k["kod"])
        lst = "listede yok" if lst is None else f"liste {lst}" + ("" if kp and kp["stok"] == lst else "  ≠")
        tutamak.append(Patch(color=KENAR_RENK[k["kod"]]))
        yazi.append(f"{k['kod']} {k['ad']}\nmodel {model} · {lst}")
    fig.legend(tutamak, yazi, loc="upper left", bbox_to_anchor=(0.76, 0.90), fontsize=9, frameon=True, edgecolor="#999",
               title="model (kesim planı) · liste üreteci", title_fontsize=9, labelspacing=0.9)
    fig.text(0.76, 0.56, "\n".join(textwrap.fill(s, 48) for s in (
        "Sayı listenin yöntemiyle, boy modelden (kesim planı); C kapama metreyle sayılır.",
        "Yer montaj rehberinden; teyit bekleyen maddeler varsayım (Lokman, 25 Ekim).",
        "Saçak omegası rehberdeki gibi duvar boyunca; liste saçak boyunu sayar.")), fontsize=8.5, va="top", ha="left", color="#444")


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
