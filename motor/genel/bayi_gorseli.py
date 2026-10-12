"""Bayiye giden plan görseli (İE-08 A3; İE-05 devir §3.1 kural 1): genel motorun planı, çevresinde ÖN (GİRİŞ) / ARKA / SOL / SAĞ
etiketleri, başlıkta kod · m² · oda. Yön kuralı `sahne.py`: +y kuzey, ön cephe güneyde (planda altta).

Çizim seti baytlarına dokunmaz: plan `ciz_genel.plan_eksen` ile **yeni** bir figüre çizilir. Çıktı `<kod>_plan_bayi.png` (≤ 5 MB;
WhatsApp görsel sınırı). `bayi_gorsel()` bunun altına çatı planı ile ön-sağ ve arka-sağ perspektifi (VTK yoksa ön ve sağ görünüşü)
ekler: `<kod>_bayi_gorsel.png` — aday kartı ve Onayla/Revize et mesajının başlık görseli (Lokman, 12 Ekim 2026: perspektifler aynı
görselin içinde, ayrı mesaj yok; VTK düşerse görsel perspektifsiz gider). Seçenek bileşik görseli (`motor/bayi_gorseli.bilesik_gorsel`)
bu PNG'yi okur.

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


def plan_bayi(t: dict, hedef: Path, kod: str, is_emri_no: str | None = None, revizyon: int | None = 1, set_yolu: Path | None = None,
              yontem: str | None = None, sunum: str | None = None) -> Path:
    """`<kod>_plan_bayi.png`: ÖN/ARKA/SOL/SAĞ etiketli plan. Başlıkta "TASLAK · rNN [· İş Emri no]"; `revizyon=None` → yalnız "TASLAK"
    (aday kartı: seçimden önce revizyon yoktur — Lokman, 12.10.2026; r01/r02 başlık görselinde numara kalır)."""
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
    taslak = "TASLAK" + (f" · r{int(revizyon):02d}" if revizyon is not None else "") + (f" · {is_emri_no}" if is_emri_no else "")
    yol = hedef / f"{kod}_plan_bayi.png"

    # Bayi çizimi kuralları (Lokman, 12–13.10.2026): 15 cm ve daha kısa zincir parçaları komşusuna katılır (şablon paftasıyla aynı anahtar,
    # D-10); yön etiketleri en dıştaki ölçü çizgisinin ve sayısının dışına, çizim yapıldıktan sonra ölçülen yerlere konur (ÖN etiketi
    # 1024'ü, SOL etiketi 860'ı kapatıyordu); mahal adı ile m² yazısı ölçeğe göre açılır. `testler/genel/test_yazi_cakismasi.py` denetler.
    from .sablon_pafta import sablon_kurallari
    _d = (sablon_kurallari().get("zincir_en_kisa_parca_cm") or {}).get("deger")
    en_kisa = 15.0 if _d is None else float(_d)
    pts = [p for h in ciz_genel.dis_hat(y) for p in h]                       # plan_eksen'in zincirleriyle aynı sınır (dış yüz)
    ex0, ey0, ex1, ey1 = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else (bx0, by0, bx1, by1)
    cm_pt_tahmin = max((W + 440) / 614.0, (H + 440) / 499.0)               # 11×9 in figürde eksen ≈ 614 × 499 pt; kenar payları ≈ 220 cm
    mahal_aralik = max(14.0, 8.5 * cm_pt_tahmin)                           # ad ve m² kutuları (≈ 11 pt) üst üste binmesin

    def ciz(dpi: int) -> None:                       # aynı çizim; 5 MB'ı aşarsa yalnız çözünürlük düşer, etiketler ve başlık korunur
        from matplotlib.text import Annotation
        fig, ax = plt.subplots(figsize=(11.0, 9.0), dpi=dpi)
        ciz_genel.plan_eksen(ax, y, baslik="\n".join(s for s in (baslik, ad, taslak) if s), olcu_zinciri=True, en_kisa_parca=en_kisa,
                             mahal_aralik=mahal_aralik, giris_yazi_dy=38.0)       # GİRİŞ yazısı alt zincirin sayısına değmesin (Ç8201)
        # çizilen her şeyin (ölçü sayıları ve okları dahil) dış sınırı; etiket bunun dışına, 10 pt boşlukla
        fig.canvas.draw(); r = fig.canvas.get_renderer(); inv = ax.transData.inverted()
        kutular = []
        for t in ax.texts:
            bb = t.arrow_patch.get_window_extent(r) if isinstance(t, Annotation) and getattr(t, "arrow_patch", None) is not None else t.get_window_extent(r)
            (dx0, dy0), (dx1, dy1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
            kutular.append((min(dx0, dx1), min(dy0, dy1), max(dx0, dx1), max(dy0, dy1)))
        cm_pt = abs(inv.transform([[0, 0], [72, 0]])[1][0] - inv.transform([[0, 0], [72, 0]])[0][0]) / 72 * fig.dpi / 72   # cm / pt
        bosluk = 10 * cm_pt
        yatayda = [k for k in kutular if ex0 <= (k[0] + k[2]) / 2 <= ex1]       # alt/üst zincirler (planın genişliğinde)
        duseyde = [k for k in kutular if ey0 <= (k[1] + k[3]) / 2 <= ey1]       # sol/sağ zincirler
        etiket_yeri = {"on": min([k[1] for k in yatayda] + [ey0 - 102]) - bosluk, "arka": max([k[3] for k in yatayda] + [ey1 + 50]) + bosluk,
                       "sol": min([k[0] for k in duseyde] + [ex0 - 86]) - bosluk, "sag": max([k[2] for k in duseyde] + [ex1 + 50]) + bosluk}
        kutu = dict(boxstyle="round,pad=0.35", fc="#1f5f93", ec="none")
        ax.text((ex0 + ex1) / 2, etiket_yeri["on"], ETIKET["on"], ha="center", va="top", fontsize=12, weight="bold", color="white", bbox=kutu, zorder=20)
        ax.text((ex0 + ex1) / 2, etiket_yeri["arka"], ETIKET["arka"], ha="center", va="bottom", fontsize=12, weight="bold", color="white", bbox=kutu, zorder=20)
        ax.text(etiket_yeri["sol"], (ey0 + ey1) / 2, ETIKET["sol"], ha="right", va="center", fontsize=12, weight="bold", color="white", bbox=kutu, rotation=90, zorder=20)
        ax.text(etiket_yeri["sag"], (ey0 + ey1) / 2, ETIKET["sag"], ha="left", va="center", fontsize=12, weight="bold", color="white", bbox=kutu, rotation=-90, zorder=20)
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        pay = 30 * cm_pt
        ax.set_xlim(min(x0, etiket_yeri["sol"] - pay), max(x1, etiket_yeri["sag"] + pay))
        ax.set_ylim(min(y0, etiket_yeri["on"] - pay), max(y1, etiket_yeri["arka"] + pay))
        fig.savefig(yol, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    ciz(130)
    if yol.stat().st_size > 5 * 1024 * 1024:            # WhatsApp görsel sınırı: 5 MB
        ciz(90)
    return yol


PERSPEKTIF_PANEL = (("perspektif_on_sag", "ÖN-SAĞ PERSPEKTİF", "on"), ("perspektif_arka_sag", "ARKA-SAĞ PERSPEKTİF", "sag"))


def bayi_gorsel(t: dict, hedef: Path, kod: str, set_yolu: Path | None = None, yontem: str | None = None, perspektif: bool | None = None) -> Path:
    """`<kod>_bayi_gorsel.png`: üstte `<kod>_plan_bayi.png` (olduğu gibi), altta tek sırada çatı planı, ön-sağ ve arka-sağ perspektif
    (`<kod>_perspektif_on_sag.png`, `<kod>_perspektif_arka_sag.png`; yoksa ön ve sağ görünüş `ciz_genel.gorunus_eksen`). `perspektif`:
    False → dosya olsa da perspektif kullanılmaz (uret bu koşuda perspektif üretmediyse eski dosya karta girmesin; geometri hakemi 12.10);
    None → dosya varsa. Altın koşuda perspektif yoktur, görsel deterministiktir (matplotlib varsayılanları + PIL). ≤ 5 MB (aşarsa alt
    sıra düşük çözünürlükle)."""
    from . import cati_genel, ciz_genel, kural, sahne as sahne_m, yapi
    import matplotlib.pyplot as plt
    from PIL import Image
    hedef = Path(hedef)
    plan = hedef / f"{kod}_plan_bayi.png"
    if not plan.is_file():
        raise FileNotFoundError(plan.name)
    t = json.loads(json.dumps(t))
    if yontem:
        t["cati"]["yontem"] = yontem
    with kural.secili(set_yolu):
        kur = kural.oku()
    y = yapi.kur(t); c = cati_genel.cati_kur(t["cati"], kur)
    inis, _ = ciz_genel.inis_kurali(c, kur, t["cati"].get("sacak", 30))
    pers = {ad: hedef / f"{kod}_{ad}.png" for ad, _, _ in PERSPEKTIF_PANEL}
    perspektifli = perspektif is not False and all(p.is_file() and p.stat().st_size > 0 for p in pers.values())
    S = None if perspektifli else sahne_m.sahne_kur(y, c)      # sahne yalnız görünüş çizilecekse kurulur (kod incelemesi 12.10)
    alt = hedef / f"{kod}_bayi_gorsel_alt.png"
    yol = hedef / f"{kod}_bayi_gorsel.png"

    def alt_sira(dpi: int) -> None:
        fig, axs = plt.subplots(1, 3, figsize=(11.0, 3.9), dpi=dpi)
        # küçük panel (≈ 2,9 in): mahya/kırma/vadi boy yazıları yok, eğim yazıları ölçeğe göre büyütülmüş kutuyla sığdığı yere (13.10.2026)
        xs = [p[0] for dz in c["duzlemler"] for p in dz["plan"]]
        cm_pt = ((max(xs) - min(xs)) + 130) / (axs[0].get_position().width * 11.0 * 72)
        ciz_genel.cati_plani_eksen(axs[0], y, c, inis, baslik="ÇATI PLANI", yazi_ayir=True, yalin=True, yazi_kutusu=(13 * cm_pt, 5.5 * cm_pt))
        for ax, (ad, baslik, taraf) in zip(axs[1:], PERSPEKTIF_PANEL):
            if perspektifli:
                ax.imshow(Image.open(pers[ad]).convert("RGB")); ax.set_title(baslik, fontsize=9.5, weight="bold"); ax.axis("off")
            else:                                        # VTK yok ya da düştü: aynı yerde görünüş, ölçüsüz (iş durmaz; Lokman 12.10.2026)
                ciz_genel.gorunus_eksen(ax, S, taraf, t["kat_yuksekligi"], olculu=False)
        fig.savefig(alt, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    def birlestir() -> None:
        ust = Image.open(plan).convert("RGB"); alt_img = Image.open(alt).convert("RGB")
        if alt_img.width != ust.width:                   # alt sıra plan genişliğine ölçeklenir
            alt_img = alt_img.resize((ust.width, max(1, round(alt_img.height * ust.width / alt_img.width))), Image.LANCZOS)
        ara = 12
        img = Image.new("RGB", (ust.width, ust.height + ara + alt_img.height), "white")
        img.paste(ust, (0, 0)); img.paste(alt_img, (0, ust.height + ara))
        img.save(str(yol), "PNG", optimize=True)

    alt_sira(130); birlestir()
    if yol.stat().st_size > 5 * 1024 * 1024:            # WhatsApp görsel sınırı
        alt_sira(80); birlestir()
    for _ in range(4):                                   # hâlâ büyükse bütün görsel küçültülür (plan görseli de; kod incelemesi 12.10)
        if yol.stat().st_size <= 5 * 1024 * 1024:
            break
        with Image.open(yol) as img:
            kucuk = img.convert("RGB").resize((max(1, int(img.width * 0.75)), max(1, int(img.height * 0.75))), Image.LANCZOS)
        kucuk.save(str(yol), "PNG", optimize=True)
    alt.unlink(missing_ok=True)
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
