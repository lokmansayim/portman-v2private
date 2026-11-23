"""Pano 83 · Bayi çizimi okuma denemesi: gerçek bayi çizimleri okuyucudan (`beyin/gorsel_okuma`) geçer, okunan plan onaylı planla yan yana.

İki adım (Lokman 22 Kasım 2026 05:15:43 UTC kartta "Evet, 6 çizim + 1 tekrar"; ücretli okuma yalnız bu onayla):

1. `paketle`: çizimler ve okuma programı tek bir bash betiğine gömülür. Betik sunucuda canlı sürümün koduyla (`/opt/portman/guncel`)
   okur; Lokman Mac'inden koşar (AGENTS.md › Sunucu erişimi, kopyası olmayan geçici betik):
       ssh portman-vps 'timeout 1500 bash -s' < okuma_betigi.sh > okuma_cikti.txt 2>&1
   Anahtar sunucudaki `/etc/portman/agent.env` ya da `llm.env`'den okunur; çıktıya, dosyaya ya da günlüğe yazılmaz. Çizimler sunucuda
   `/root/portman_cizim_okuma_<tarih>/` altına yazılır ve silinmez (silme ayrı onay). Bayi çizimleri depoya girmez.
       python -m araclar.cizim_okuma_deneme paketle <liste.json> <okuma_betigi.sh>
   liste.json: [{"ad": "TK-01", "dosya": "<çizim yolu>"}, …]

2. `kiyas`: sunucunun çıktısındaki her okuma kodla denetlenir (`GO.denetle`) ve İş Emri'ne çevrilir; okunan plan ile onaylı planın
   İş Emri'si Pano Motor'unda kurulur (`motor.geometry.kur`) ve pano dizilimi yan yana çizilir (`motor/dizilim_kiyas.ciz`, çalışma
   kuralı 12). Bayinin çizimi solda. Okuma soru doğurursa (bayiye "emin olamadım") ya da çizilemezse sağda okunan yerleşim görseli
   (`GO.yerlesim_gorseli`) ve sorular durur. LLM çağrısı yok.
       python -m araclar.cizim_okuma_deneme kiyas <okuma_cikti.txt> <esleme.json> <çıktı klasörü>
   esleme.json: {"TK-01": {"dosya": "<çizim>", "onayli": "<onaylı İş Emri.json>", "baslik": "80 m² 3+1"}, …}

Görsel inceleme içindir; ön onay çizimi (M-02) değildir. Kabul Lokman'ın baktığı kıyastır, test sayısı değildir.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import tarfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".pdf": "application/pdf"}
ISARET = "@@OKUMA "

# Sunucuda koşan program (canlı sürümün venv'iyle). Yalnız standart kitaplık + canlı kod.
SUNUCU_PY = r'''
import json, os, sys, time
from pathlib import Path
klasor, kok = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, kok)
for env in ("/etc/portman/agent.env", "/etc/portman/llm.env"):
    try:
        for s in Path(env).read_text(encoding="utf-8").splitlines():
            if s.startswith("ANTHROPIC_API_KEY=") and not os.environ.get("ANTHROPIC_API_KEY"):
                os.environ["ANTHROPIC_API_KEY"] = s.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
print("anahtar:", "var" if os.environ.get("ANTHROPIC_API_KEY") else "YOK", flush=True)
import importlib.util
def _ustune(ad, dosya):                    # dalın kodu (BK-70 + BK-71) canlı sürümün üstüne, yalnız bu süreçte
    sp = importlib.util.spec_from_file_location(ad, dosya); m = importlib.util.module_from_spec(sp)
    sys.modules[ad] = m; sp.loader.exec_module(m); return m
if (klasor / "kod").is_dir():
    import motor, beyin
    motor.geometry = _ustune("motor.geometry", klasor / "kod" / "motor" / "geometry.py")
    beyin.gorsel_okuma = _ustune("beyin.gorsel_okuma", klasor / "kod" / "beyin" / "gorsel_okuma.py")
    print("kod: dal (", (klasor / "kod" / "surum.txt").read_text().strip(), ")", flush=True)
from beyin import gorsel_okuma as GO
IKINCI = @@IKINCI@@
liste = json.loads((klasor / "liste.json").read_text(encoding="utf-8"))
FIYAT = @@FIYAT@@
ayar = {"model": "@@MODEL@@", "effort": "medium", "timeout_s": @@SURE@@, "max_tokens": @@TOKEN@@}
print("ayar:", json.dumps(ayar), "· sürüm:", os.path.realpath(kok), flush=True)
gt = ct = 0
for i, x in enumerate(liste, 1):
    yol = klasor / x["dosya"]
    r = GO.oku(yol, x["mime"], "", ayar=ayar)
    gt += r.get("girdi_token") or 0; ct += r.get("cikti_token") or 0
    b = None
    if IKINCI and r["durum"] == "tamam" and (r["okuma"] or {}).get("tur") == "plan":
        den = GO.denetle(r["okuma"])
        print(f"   ilk okuma: {len(den['sorular'])} soru, çizilemez {len(den['cizilemez'])}", flush=True)
        if den["sorular"] and not den["cizilemez"]:
            b = GO.ikinci_bakis(r["okuma"], list(den["sorular"]), yol, x["mime"], ayar=ayar)
            gt += b.get("girdi_token") or 0; ct += b.get("cikti_token") or 0
            print(f"   ikinci bakış: {b['durum']} · girdi {b.get('girdi_token')} · çıktı {b.get('cikti_token')} token"
                  + (f" · hata {b.get('hata')}" if b["durum"] != "tamam" else ""), flush=True)
    print(f"== {i}/{len(liste)} {x['ad']}: {r['durum']} · girdi {r.get('girdi_token')} · çıktı {r.get('cikti_token')} token · "
          f"{(r.get('sure_ms') or 0) / 1000:.0f} sn" + (f" · hata {r.get('hata')}" if r["durum"] != "tamam" else ""), flush=True)
    print("@@OKUMA " + json.dumps({"ad": x["ad"], **{k: r.get(k) for k in ("durum", "okuma", "girdi_token", "cikti_token", "sure_ms",
          "model", "hata")}, "ikinci": b}, ensure_ascii=False), flush=True)
print(f"== toplam: girdi {gt} · çıktı {ct} token · tahmini {gt * FIYAT[0] / 1e6 + ct * FIYAT[1] / 1e6:.2f} USD")
print("== bitti")
'''


KOD_DOSYALARI = ("beyin/gorsel_okuma.py", "motor/geometry.py", "kurallar/pencere/pencereler.json", "kurallar/plan/oda_kurallari.json",
                 "kurallar/liste/prefabrik.json")
FIYAT = {"claude-opus-5-5": (4, 20), "claude-fable-5-2": (8, 40)}     # USD / milyon token (girdi, çıktı)
# Canlı ayar (kanal/ayarlar.py: 180 sn, 8000 token) Opus 5.5 içindir; Fable 5.2 her zaman düşünür, çıktı payı ve süre büyür
SINIR = {"claude-opus-5-5": (180, 8000), "claude-fable-5-2": (300, 16000)}


def paketle(liste_yolu: Path, cikti: Path, tarih: str = "2026-11-22", model: str = "claude-opus-5-5", ikinci: bool = False,
            onay: str = "22 Kasım 2026 05:15:43 UTC") -> Path:
    liste = json.loads(Path(liste_yolu).read_text(encoding="utf-8"))
    b = io.BytesIO()
    kayit = []
    with tarfile.open(fileobj=b, mode="w:gz") as tar:
        for i, x in enumerate(liste, 1):
            kaynak = Path(x["dosya"])
            mime = MIME[kaynak.suffix.lower()]
            ad = f"{i:02d}{kaynak.suffix.lower()}"
            tar.add(kaynak, arcname=ad)
            kayit.append({"ad": x["ad"], "dosya": ad, "mime": mime})
        if ikinci:                         # BK-71: dalın okuyucusu ve Motor'u (canlıda henüz yok); sürüm notu git'ten
            import subprocess
            for kd in KOD_DOSYALARI:            # dosyaya göre okunan kurallar da dalın hâliyle (kod/kurallar/…)
                tar.add(KOK / kd, arcname="kod/" + kd)
            sv = subprocess.run(["git", "-C", str(KOK), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip().encode()
            ti = tarfile.TarInfo("kod/surum.txt"); ti.size = len(sv); tar.addfile(ti, io.BytesIO(sv))
        veri = json.dumps(kayit, ensure_ascii=False).encode()
        ti = tarfile.TarInfo("liste.json"); ti.size = len(veri)
        tar.addfile(ti, io.BytesIO(veri))
    b64 = base64.b64encode(b.getvalue()).decode()
    satirlar = "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76))
    klasor = f"/root/portman_cizim_okuma_{tarih}"
    betik = f"""#!/bin/bash
# Portman · bayi çizimi okuma denemesi ({len(kayit)} çizim, {model}{', ikinci bakış' if ikinci else ''}). Lokman'ın onayı: {onay}.
set -u
KOK=/opt/portman/guncel
K={klasor}
mkdir -p "$K" && chmod 700 "$K"
base64 -d > "$K/girdi.tgz" <<'B64'
{satirlar}
B64
tar -xzf "$K/girdi.tgz" -C "$K" || {{ echo "== DUR: paket açılamadı"; exit 1; }}
cat > "$K/oku.py" <<'PY'
{SUNUCU_PY.strip().replace('@@MODEL@@', model).replace('@@IKINCI@@', repr(ikinci)).replace('@@FIYAT@@', repr(FIYAT[model])).replace('@@SURE@@', str(SINIR[model][0])).replace('@@TOKEN@@', str(SINIR[model][1]))}
PY
cd "$KOK" && "$KOK/venv/bin/python" "$K/oku.py" "$K" "$KOK"
echo "== çıkış $?"
"""
    Path(cikti).write_text(betik, encoding="utf-8")
    return Path(cikti)


def okumalar(txt: Path) -> dict[str, dict]:
    out = {}
    for s in Path(txt).read_text(encoding="utf-8").splitlines():
        if s.startswith(ISARET):
            r = json.loads(s[len(ISARET):])
            out[r["ad"]] = r
    return out


def _cizim_resmi(yol: Path):
    """Bayinin çizimi (PDF'in ilk sayfası ya da resim) → numpy dizisi."""
    from PIL import Image
    import numpy as np
    yol = Path(yol)
    if yol.suffix.lower() == ".pdf":
        import pymupdf
        sayfa = pymupdf.open(yol)[0]
        pm = sayfa.get_pixmap(dpi=110)
        im = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")
    else:
        im = Image.open(yol).convert("RGB")
    return np.asarray(im)


def _pano_anahtari(pn) -> tuple:
    x0, y0, x1, y1 = pn.rect()
    return (round(x0), round(y0), round(x1), round(y1))


def _oda_ozeti(plan) -> list[str]:
    return [f"{m.ad} {m.alan_m2:.2f}".replace(".", ",") for m in plan.mahaller.values() if m.poly is not None]


def _aciklik_sayisi(ie: dict) -> tuple[int, int]:
    a = ie.get("acikliklar") or []
    return sum(1 for x in a if x.get("tur") == "pencere"), sum(1 for x in a if "kapi" in str(x.get("tur")))


def kiyas_ev(ad: str, r: dict, es: dict, hedef: Path) -> dict:
    import copy
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from beyin import gorsel_okuma as GO
    from motor import geometry as G
    from motor import dizilim_kiyas as DK

    sonuc = {"ad": ad, "baslik": es.get("baslik", ""), "durum": r.get("durum"), "token": [r.get("girdi_token"), r.get("cikti_token")],
             "sorular": [], "kod_sorulari": [], "varsayim": None, "cizilemez": [], "notlar": [], "okunan": None, "onayli": None, "ayni_pano": None}
    ie0 = json.loads(Path(es["onayli"]).read_text(encoding="utf-8"))
    p0 = G.kur(copy.deepcopy(ie0))
    sonuc["onayli"] = {"W": p0.W, "H": p0.H, "pano": len(p0.panolar), "odalar": _oda_ozeti(p0), "pencere_kapi": _aciklik_sayisi(ie0)}
    p1 = den = None
    if r.get("durum") == "tamam" and r.get("okuma"):
        den = GO.denetle(r["okuma"])
        ik = r.get("ikinci") or {}
        if ik:                                 # BK-71: hangi okuma bayiye gider, kod seçer (canlıdaki gibi)
            sec, den_s, secildi = GO.ikinci_bakis_sec(r["okuma"], den, ik.get("okuma") if ik.get("durum") == "tamam" else None)
            sonuc["ikinci_bakis"] = {"durum": ik.get("durum"), "secildi": secildi, "soru_once": len(den["sorular"]),
                                     "soru_sonra": len(den_s["sorular"]), "degisenler": ik.get("degisenler") or []}
            r = {**r, "okuma": sec}
            den = den_s
        sonuc.update(sorular=den["sorular"], cizilemez=den["cizilemez"], notlar=den["notlar"])
        ie1 = ((den.get("cevrim") or {}).get("is_emri"))
        if not ie1 and den.get("plan_mi") and r["okuma"].get("emin_olunamayanlar"):
            # bayi okuyucunun kendi sorularına "doğru" derse: aynı okuma, modelin soruları boş; kodun soruları yine durur
            den2 = GO.denetle({**r["okuma"], "emin_olunamayanlar": []})
            sonuc["kod_sorulari"] = den2["sorular"]
            ie1 = ((den2.get("cevrim") or {}).get("is_emri"))
            if ie1:
                sonuc["varsayim"] = "bayi okuyucunun sorularına 'doğru' derse"
                den = {**den, "cevrim": den2["cevrim"]}
        if ie1:
            ie1 = json.loads(json.dumps(ie1))
            try:
                p1 = G.kur(copy.deepcopy(ie1))
                sonuc["okunan"] = {"W": p1.W, "H": p1.H, "pano": len(p1.panolar), "odalar": _oda_ozeti(p1),
                                   "pencere_kapi": _aciklik_sayisi(ie1)}
                (hedef / f"{ad}_okunan_is_emri.json").write_text(json.dumps(ie1, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as e:      # Motor kuramadı: kayda geçer, görselde yazar
                sonuc["cizilemez"].append(f"Motor kuramadı: {type(e).__name__}: {str(e)[:160]}")
    else:
        sonuc["cizilemez"].append(f"okuma hatası: {r.get('hata')}")

    s0 = s1 = None
    if p1 is not None:
        k0 = {_pano_anahtari(q) for q in p0.panolar}
        k1 = {_pano_anahtari(q) for q in p1.panolar}
        s0 = {id(q): ("ayni" if _pano_anahtari(q) in k1 else "degisti") for q in p0.panolar}
        s1 = {id(q): ("ayni" if _pano_anahtari(q) in k0 else "degisti") for q in p1.panolar}
        sonuc["ayni_pano"] = sum(v == "ayni" for v in s1.values())

    fig = plt.figure(figsize=(30, 12.5), dpi=90)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1])
    ax = fig.add_subplot(gs[0, 0]); ax.imshow(_cizim_resmi(es["dosya"])); ax.axis("off")
    ax.set_title("Bayinin çizimi", fontsize=15, loc="left", fontweight="bold")
    ax0 = fig.add_subplot(gs[0, 1])
    DK.ciz(ax0, p0, s0, f"Onaylı plan · {DK.tr(p0.W)} × {DK.tr(p0.H)} cm · {len(p0.panolar)} pano")
    ax1 = fig.add_subplot(gs[0, 2])
    Wm, Hm = p0.W, p0.H
    if p1 is not None:
        on = "Okuyucunun planı" + (f" ({sonuc['varsayim']})" if sonuc["varsayim"] else "")
        DK.ciz(ax1, p1, s1, f"{on} · {DK.tr(p1.W)} × {DK.tr(p1.H)} cm · {len(p1.panolar)} pano")
        Wm, Hm = max(p0.W, p1.W), max(p0.H, p1.H)
        ax1.set_xlim(-170, Wm + 90); ax1.set_ylim(-150, Hm + 60)
    elif den is not None and den.get("plan_mi"):
        yg = GO.yerlesim_gorseli(r["okuma"], den, hedef / f"{ad}_okunan_yerlesim.png")
        ax1.imshow(plt.imread(yg)); ax1.axis("off")
        ax1.set_title("Okuyucunun okuduğu yerleşim (plan çizilmedi)", fontsize=13, loc="left", fontweight="bold")
    else:
        ax1.axis("off"); ax1.set_title("Okuyucu plan çıkaramadı", fontsize=13, loc="left", fontweight="bold")
    ax0.set_xlim(-170, Wm + 90); ax0.set_ylim(-150, Hm + 60)
    alt = []
    if sonuc["ayni_pano"] is not None:
        alt.append(f"Gri: iki planda yeri ve boyu aynı pano ({sonuc['ayni_pano']} / {len(p1.panolar)}). Pembe: yalnız o planda olan pano "
                   f"(onaylıda {sum(v == 'degisti' for v in s0.values())}, okunanda {sum(v == 'degisti' for v in s1.values())}). "
                   "Kırmızı çerçeve pencere, yeşil çerçeve kapı.")
    for baslik, liste in (("Bayiye soracağı", sonuc["sorular"]), ("Çizemediği", sonuc["cizilemez"])):
        for x in liste[:4]:
            alt.append(f"{baslik}: {x}"[:190])
    for i, s in enumerate(alt[:7]):
        fig.text(0.01, 0.02 + 0.026 * (len(alt[:7]) - 1 - i), s, fontsize=12.5, color="#333333")
    fig.suptitle(f"{ad} · {es.get('baslik', '')}", fontsize=18, x=0.01, ha="left", fontweight="bold")
    plt.tight_layout(rect=(0, 0.03 + 0.026 * len(alt[:7]), 1, 0.96))
    yol = hedef / f"{ad}_kiyas.png"
    fig.savefig(yol, dpi=90)
    plt.close(fig)
    sonuc["gorsel"] = str(yol)
    return sonuc


def kiyas(txt: Path, esleme_yolu: Path, hedef: Path) -> list[dict]:
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    es = json.loads(Path(esleme_yolu).read_text(encoding="utf-8"))
    rr = okumalar(txt)
    out = [kiyas_ev(ad, rr[ad], es[ad], hedef) for ad in es if ad in rr]
    (hedef / "ozet.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bayi çizimi okuma denemesi (pano 83)")
    alt = ap.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("paketle"); a.add_argument("liste"); a.add_argument("cikti"); a.add_argument("--model", default="claude-opus-5-5", choices=sorted(FIYAT)); a.add_argument("--etiket", default="2026-11-22"); a.add_argument("--ikinci-bakis", action="store_true"); a.add_argument("--onay", default="22 Kasım 2026 05:15:43 UTC")
    k = alt.add_parser("kiyas"); k.add_argument("okuma_cikti"); k.add_argument("esleme"); k.add_argument("hedef")
    a = ap.parse_args(argv)
    if a.komut == "paketle":
        print(paketle(Path(a.liste), Path(a.cikti), tarih=a.etiket, model=a.model, ikinci=a.ikinci_bakis, onay=a.onay))
    else:
        for x in kiyas(Path(a.okuma_cikti), Path(a.esleme), Path(a.hedef)):
            print(json.dumps({k: x[k] for k in ("ad", "durum", "ayni_pano", "varsayim", "kod_sorulari", "cizilemez", "okunan", "onayli")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
