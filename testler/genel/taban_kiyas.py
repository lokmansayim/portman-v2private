#!/usr/bin/env python3
"""İE-08 Adım 2 · Taban kanıtı: ie-05'in deneme betikleri olduğu gibi koşturulur, her çıktı depodaki haliyle (çalışma ağacının HEAD'i)
ve kural seti tablosundaki commit'teki haliyle karşılaştırılır. Kod taşınmadan önce "bugünkü kod + hangi paket seti = hangi çıktı"
sorusunun cevabıdır; sonucu docs/is_emirleri/IE-08.md › Kanıt'a girer.

    python testler/genel/taban_kiyas.py --agac <ie-05 çalışma ağacı> --python <venv python> --etiket ie05 --rapor <klasör> [--atla ...]

Koşulanlar (hepsi ağacın içinde, dosyaları yerinde yeniden yazar; sonra `git status` farkı okunur):
  hepsini   deneme/2026-10-03_yukleme/hepsini_kos.sh            Ç8201 eski zincir (girdi_uret → yukleme), 3 örnek liste, çatı açılımı; güncel set
  kt01      kiyas_kos.sh (0.12), kararlar_kos.sh (güncel), saglama.py
  kt02      kt02_kos.sh (0.15, kör), kt02_kiyas_kos.sh (0.15), kt02_cevaplar_kos.sh (güncel)
  kt03      kt03_kos.sh (0.17, kör), kt03_kiyas_kos.sh (0.17), kt03_cevaplar_kos.sh (güncel)
  c8801     c8801_kos.sh'nin liste kısmı (3 çatı; güncel set) ve iki tablo
  cizim     çizim setleri perspektifsiz (ciz_genel + ifc_genel): C8801{,K,L}_A, KT01_{A,B}, KT02_{A,B}, KT03_{A,B}; Ç8201 0.5 seti rapor klasörüne (depoda yok)
  setler    0.12–0.18 setleriyle Ç8201 (eski zincir) ve o setin kör test modeli (düzeltilmiş tanım, A ve B) listeleri → set tablosundaki commit'teki dosyayla kıyas

Karşılaştırma: PNG/MD/TXT bayt bayt (sha256); JSON kanonik içerik (anahtar sırası ve boşluk bağımsız) + bayt; IFC kanonik iz
(motor/genel/iz.py: başlık ve GlobalId maskeli, ondalık 1e-4) + bayt. Perspektif PNG'leri ve geometri.json üretilmez (VTK gerekmez).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import iz as IZ  # noqa: E402

YUK = "deneme/2026-10-03_yukleme"
KOR = "deneme/2026-10-06_kor_test"
KT2 = "deneme/2026-10-09_kor_test_2"
KT3 = "deneme/2026-10-09_kor_test_3"
C88 = "deneme/2026-10-10_c8801"
CEL = "deneme/2026-10-02_celik"

# kurallar/README.md › Sürümler: o günkü çıktıları bayt bayt veren commit
SET_COMMIT = {"0.12": "eff6a74", "0.13": "021c277", "0.14": "4251345", "0.15": "b5ff4cf", "0.16": "6b265c8", "0.17": "c939fe2", "0.18": "8fca288"}
SET_MODEL = {"0.12": "KT01", "0.13": "KT01", "0.14": "KT01", "0.15": "KT02", "0.16": "KT02", "0.17": "KT03", "0.18": "KT03"}
KT_KLASOR = {"KT01": KOR, "KT02": KT2, "KT03": KT3}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Kos:
    def __init__(self, agac: Path, py: str, rapor: Path):
        self.agac, self.py, self.rapor = agac, py, rapor
        self.adimlar: list[dict] = []
        self.gunluk = (rapor / "kosum_gunlugu.txt").open("a", encoding="utf-8")

    def snapshot(self) -> dict[str, tuple[int, int]]:
        d = {}
        for p in (self.agac / "deneme").rglob("*"):
            if p.is_file() and "cikti" not in p.parts:
                st = p.stat(); d[str(p.relative_to(self.agac))] = (st.st_mtime_ns, st.st_size)
        return d

    def kos(self, ad: str, cmd: list[str], cwd: str, env_ek: dict | None = None, set_: str | None = None) -> dict:
        env = {k: v for k, v in os.environ.items() if k != "PORTMAN_KURALLAR"}
        if set_:
            env["PORTMAN_KURALLAR"] = str(self.agac / "kurallar" / "liste" / "setler" / f"{set_}.json")
        env.update(env_ek or {})
        once = self.snapshot(); t0 = time.time()
        r = subprocess.run(cmd, cwd=str(self.agac / cwd), env=env, capture_output=True, text=True)
        sonra = self.snapshot()
        dokunulan = sorted(k for k, v in sonra.items() if once.get(k) != v)
        kayit = {"ad": ad, "komut": " ".join(cmd), "cwd": cwd, "set": set_ or "güncel", "cikis": r.returncode, "sure_s": round(time.time() - t0, 1),
                 "dokunulan": dokunulan, "son_satir": (r.stdout.strip().splitlines() or [""])[-1][:200], "hata": r.stderr.strip()[-600:] if r.returncode else ""}
        self.adimlar.append(kayit)
        self.gunluk.write(f"\n## {ad} (çıkış {r.returncode}, {kayit['sure_s']} s)\n$ {kayit['komut']}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}\n"); self.gunluk.flush()
        print(f"[{r.returncode:>3}] {ad:<28} {kayit['sure_s']:>6} s · dokunulan {len(dokunulan)}" + (f" · {kayit['son_satir'][:90]}" if r.returncode == 0 else f" · HATA {kayit['hata'][-160:]}"))
        return kayit

    # --- git karşılaştırması -------------------------------------------------------------------------------------------
    def git(self, *a: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.agac), *a], capture_output=True, text=True)

    def blob(self, rev: str, yol: str) -> Path | None:
        r = subprocess.run(["git", "-C", str(self.agac), "cat-file", "-e", f"{rev}:{yol}"], capture_output=True)
        if r.returncode:
            return None
        hedef = self.rapor / "blob" / rev / yol; hedef.parent.mkdir(parents=True, exist_ok=True)
        with open(hedef, "wb") as f:
            subprocess.run(["git", "-C", str(self.agac), "show", f"{rev}:{yol}"], stdout=f, check=True)
        return hedef

    def kiyas(self, yol: str, rev: str = "HEAD", dosya: Path | None = None) -> dict:
        """Çalışma ağacındaki (ya da verilen) dosya ile rev'deki blob: bayt ve içerik."""
        dosya = dosya or (self.agac / yol)
        eski = self.blob(rev, yol)
        if eski is None:
            return {"yol": yol, "rev": rev, "durum": "revde yok"}
        if not dosya.exists():
            return {"yol": yol, "rev": rev, "durum": "üretilmedi"}
        bayt = sha(dosya) == sha(eski)
        u = dosya.suffix.lower()
        if u in (".json", ".ifc"):
            icerik = IZ.dosya_izi(dosya) == IZ.dosya_izi(eski)
        else:
            icerik = bayt
        durum = "AYNI" if bayt else ("İÇERİK AYNI" if icerik else "FARKLI")
        return {"yol": yol, "rev": rev, "durum": durum, "bayt": bayt, "icerik": icerik}


def cizim_seti(k: Kos, tanim: str, cikti: str, yontem: str | None, ad: str, rapor_ici: bool = False) -> list[dict]:
    """ciz_genel + ifc_genel (perspektifsiz). rapor_ici: çıktı depoda yok, rapor klasörüne yazılır ve yalnız izleri kaydedilir."""
    kod = json.loads((k.agac / tanim).read_text(encoding="utf-8"))["kod"].replace("Ç", "C").replace("-", "")
    hedef = (k.rapor / "cizim" / cikti.split("/")[-1]) if rapor_ici else (k.agac / cikti)
    hedef.mkdir(parents=True, exist_ok=True)
    ek = ["--yontem", yontem] if yontem else []
    k.kos(f"{ad} ciz_genel", [k.py, "ciz_genel.py", str(k.agac / tanim), "--cikti", str(hedef)] + ek, KOR)
    k.kos(f"{ad} ifc_genel", [k.py, "ifc_genel.py", str(k.agac / tanim), str(hedef / f"{kod}.ifc")] + ek, KOR)
    sonuclar = []
    for d in (f"{kod}_plan.png", f"{kod}_gorunusler.png", f"{kod}_pafta.png", f"{kod}.ifc", f"{kod}.ozet.json"):
        if rapor_ici:
            p = hedef / d
            sonuclar.append({"yol": f"{cikti}/{d}", "rev": "-", "durum": "TABAN (depoda yok)", "iz": IZ.dosya_izi(p) if p.exists() else None, "bayt_sha": sha(p) if p.exists() else None})
        else:
            sonuclar.append(k.kiyas(f"{cikti}/{d}"))
    return sonuclar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agac", required=True); ap.add_argument("--python", required=True); ap.add_argument("--etiket", required=True)
    ap.add_argument("--rapor", required=True); ap.add_argument("--atla", nargs="*", default=[], help="hepsini kt01 kt02 kt03 c8801 cizim setler")
    a = ap.parse_args()
    agac = Path(a.agac).resolve(); rapor = Path(a.rapor).resolve() / a.etiket; rapor.mkdir(parents=True, exist_ok=True)
    py = str(Path(a.python).absolute())          # resolve() değil: venv'in bin/python bağı sistem Python'una çözülmesin
    if subprocess.run(["git", "-C", str(agac), "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        print("DUR: çalışma ağacı temiz değil; önce `git -C <ağaç> checkout -- .` (yalnız deneme ağacı) ya da yeni ağaç.", file=sys.stderr); return 2
    k = Kos(agac, py, rapor)
    surum = subprocess.run([py, "-c", "import sys, shapely, ifcopenshell, matplotlib, numpy, fitz; print(sys.version.split()[0], shapely.__version__, ifcopenshell.version, matplotlib.__version__, numpy.__version__, fitz.__doc__.split()[-1] if fitz.__doc__ else '?')"],
                           capture_output=True, text=True).stdout.strip()
    kiyaslar: dict[str, list[dict]] = {}
    at = set(a.atla)
    if "hepsini" not in at:
        k.kos("hepsini (Ç8201 eski zincir)", ["bash", "hepsini_kos.sh", py], YUK)
    if "kt01" not in at:
        k.kos("kt01 kiyas 0.12", ["bash", "kiyas_kos.sh", "tanim/KT01_duzeltilmis.json", py], KOR)
        k.kos("kt01 kararlar güncel", ["bash", "kararlar_kos.sh", "tanim/KT01_duzeltilmis.json", py], KOR)
        k.kos("kt01 saglama", [py, "saglama.py"], KOR)
    if "kt02" not in at:
        k.kos("kt02 kör 0.15", ["bash", "kt02_kos.sh", "tanim/KT02.json", py], KT2)
        k.kos("kt02 kiyas 0.15", ["bash", "kt02_kiyas_kos.sh", "tanim/KT02_duzeltilmis.json", py], KT2)
        k.kos("kt02 cevaplar güncel", ["bash", "kt02_cevaplar_kos.sh", "tanim/KT02_duzeltilmis.json", py], KT2)
    if "kt03" not in at:
        k.kos("kt03 kör 0.17", ["bash", "kt03_kos.sh", "tanim/KT03.json", py], KT3)
        k.kos("kt03 kiyas 0.17", ["bash", "kt03_kiyas_kos.sh", "tanim/KT03_duzeltilmis.json", py], KT3)
        k.kos("kt03 cevaplar güncel", ["bash", "kt03_cevaplar_kos.sh", "tanim/KT03_duzeltilmis.json", py], KT3)
    if "c8801" not in at:
        kaynak = {"C8801": "katalog çatısı (Lokman, 10 Ekim 2026: 2. versiyon)", "C8801K": "çatı varyantı K (doğu ucu kırma)", "C8801L": "çatı varyantı L (kanadın mahyası boydan boya)"}
        for kod, kk in kaynak.items():
            k.kos(f"c8801 {kod} girdi", [py, f"../2026-10-06_kor_test/girdi_genel.py", f"tanim/{kod}.json", "--dosya", f"sonuc/{kod}_girdi.json", "--uzerine-yaz",
                                         "--kaynak", f"Yapı Tanımı 0.5 (Ç8801 katalog modeli: plan arşivdeki DWG'den; {kk})"], C88)
            k.kos(f"c8801 {kod} yukleme", [py, f"../2026-10-03_yukleme/yukleme.py", f"sonuc/{kod}_girdi.json", "--cikti", f"sonuc/{kod}_yukleme.json", "--md", f"sonuc/{kod}_yukleme.md"], C88)
        k.kos("c8801 yan yana", [py, "c8801_yan_yana.py", "../2026-10-03_yukleme/sonuc/C8201_yukleme_taslak.json", "sonuc/C8801_yukleme.json", "--md", "sonuc/C8801_C8201_yan_yana.md"], C88)
        k.kos("c8801 varyantlar", [py, "c8801_varyantlar.py", "sonuc/C8801_yukleme.json", "sonuc/C8801K_yukleme.json", "sonuc/C8801L_yukleme.json", "--md", "sonuc/C8801_cati_varyantlari.md"], C88)
    if "cizim" not in at:
        cz = []
        for kod in ("C8801", "C8801K", "C8801L"):
            cz += cizim_seti(k, f"{C88}/tanim/{kod}.json", f"{C88}/cizimler/{kod}_A", "panel", f"cizim {kod}_A")
        cz += cizim_seti(k, f"{KOR}/tanim/KT01_duzeltilmis.json", f"{KOR}/cizimler/KT01_A", "panel", "cizim KT01_A")
        cz += cizim_seti(k, f"{KOR}/tanim/KT01_duzeltilmis.json", f"{KOR}/cizimler/KT01_B", None, "cizim KT01_B")
        cz += cizim_seti(k, f"{KT2}/tanim/KT02_duzeltilmis.json", f"{KT2}/cizimler/KT02_A", "panel", "cizim KT02_A")
        cz += cizim_seti(k, f"{KT2}/tanim/KT02_duzeltilmis.json", f"{KT2}/cizimler/KT02_B", None, "cizim KT02_B")
        cz += cizim_seti(k, f"{KT3}/tanim/KT03_duzeltilmis.json", f"{KT3}/cizimler/KT03_A", "panel", "cizim KT03_A")
        cz += cizim_seti(k, f"{KT3}/tanim/KT03_duzeltilmis.json", f"{KT3}/cizimler/KT03_B", "omega_asik", "cizim KT03_B")
        cz += cizim_seti(k, f"{KOR}/C8201_05.json", "C8201_05", "panel", "cizim C8201_05 (taban)", rapor_ici=True)
        kiyaslar["cizim"] = cz
    # HEAD ile kıyas: betiklerin dokunduğu her dosya
    dokunulan = sorted({d for ad in k.adimlar for d in ad["dokunulan"]})
    kiyaslar["head"] = [k.kiyas(d) for d in dokunulan]
    if "setler" not in at:
        st = []
        with tempfile.TemporaryDirectory() as t:
            for s, c in SET_COMMIT.items():
                tdir = Path(t) / s; tdir.mkdir()
                # Ç8201 eski zincir
                k.kos(f"set {s} Ç8201 girdi", [py, "girdi_uret.py", f"../2026-10-02_celik/C8201.json"], YUK, set_=s)
                k.kos(f"set {s} Ç8201 yukleme", [py, "yukleme.py", "sonuc/C8201_girdi.json", "--cikti", str(tdir / "C8201_yukleme_taslak.json"), "--md", str(tdir / "C8201_yukleme_taslak.md")], YUK, set_=s)
                st.append({"set": s, **k.kiyas(f"{YUK}/sonuc/C8201_yukleme_taslak.json", c, tdir / "C8201_yukleme_taslak.json")})
                # setin kör test modeli: o commit'teki düzeltilmiş tanım ve pafta sayımıyla (tanım sonradan düzeltilmiş olabilir), A ve B
                m = SET_MODEL[s]; kl = KT_KLASOR[m]
                tanim_c = k.blob(c, f"{kl}/tanim/{m}_duzeltilmis.json") or (k.agac / kl / "tanim" / f"{m}_duzeltilmis.json")
                sayim_c = k.blob(c, f"{kl}/sonuc/{m}_pafta_sayimi.json") or (k.agac / kl / "sonuc" / f"{m}_pafta_sayimi.json")
                for X, ek in (("A", ["--yontem", "panel"]), ("B", [])):
                    g = tdir / f"{m}_{X}_girdi.json"; y = tdir / f"{m}_{X}_yukleme.json"
                    k.kos(f"set {s} {m}_{X} girdi", [py, f"{'' if kl == KOR else '../2026-10-06_kor_test/'}girdi_genel.py", str(tanim_c), "--dosya", str(g), "--uzerine-yaz", "--kaynak", "taban"] + ek, kl, set_=s)
                    k.kos(f"set {s} {m}_{X} yukleme", [py, "../2026-10-03_yukleme/yukleme.py", str(g), "--elektrik-sayimi", str(sayim_c), "--cikti", str(y), "--md", str(y.with_suffix(".md"))], kl, set_=s)
                    for ad in (f"{m}_kararlar_{X}_yukleme.json", f"{m}_duzeltilmis_{X}_yukleme.json", f"{m}_cevaplar_{X}_yukleme.json", f"{m}_duzeltilmis_yukleme.json" if X == "B" else "-"):
                        r = k.kiyas(f"{kl}/sonuc/{ad}", c, y)
                        if r["durum"] != "revde yok":
                            st.append({"set": s, **r}); break
                    else:
                        st.append({"set": s, "yol": f"{kl}/sonuc/{m}_*_{X}_yukleme.json", "rev": c, "durum": "revde yok"})
        kiyaslar["setler"] = st
    # çalışma ağacı temizlenmez: farklar `git -C <ağaç> diff` ile incelenir; sonraki koşudan önce `git checkout -- deneme && git clean -fd deneme`
    durum = k.git("status", "--porcelain").stdout
    ozet = {"etiket": a.etiket, "python": py, "surumler": surum, "agac": str(agac), "head": k.git("rev-parse", "--short", "HEAD").stdout.strip(),
            "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "adimlar": k.adimlar, "kiyaslar": kiyaslar, "git_status_once": durum}
    (rapor / "taban.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    # kısa tablo
    sat = [f"# Taban kıyası · {a.etiket} · {surum} · ağaç {ozet['head']} · {ozet['zaman_utc']}", ""]
    for grup, liste in kiyaslar.items():
        say = {}
        for r in liste:
            say[r["durum"]] = say.get(r["durum"], 0) + 1
        sat.append(f"## {grup}: " + ", ".join(f"{d} {n}" for d, n in sorted(say.items())))
        for r in liste:
            if r["durum"] not in ("AYNI",):
                sat.append(f"- {r.get('set', '')} {r['yol']} @ {r['rev']}: **{r['durum']}**" + (f" iz {r['iz'][:12]}" if r.get("iz") else ""))
    hatali = [ad["ad"] for ad in k.adimlar if ad["cikis"]]
    sat.append(f"\nÇıkış kodu sıfır olmayan adımlar: {hatali or 'yok'}")
    (rapor / "taban.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    print("\n".join(sat))
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
