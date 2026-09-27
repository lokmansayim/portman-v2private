"""Canlıya giden paketleri depo koduyla dosya dosya karşılaştırır. Fark bulursa listeler, düzeltmez.

Paketler depoda değildir (Lokman'ın masaüstü klasörü: 08_VPS/hosting_paket/). Kullanım (depo kökünde):
    python3 testler/referans/paket_karsilastir.py <hosting_guncelleme_2011.zip>

Hosting paketi `kanal/` önekli dosyalar ve içinde VPS paketini (kanal/package/current.zip) taşır.
Eşleme: hosting `kanal/beyin|motor|is_emri/…` → depo `beyin|motor|is_emri/…`; hosting `kanal/worker.py` → `kanal/worker.py`.
VPS paketi (current.zip) kökü: `beyin|motor|is_emri/…` aynı yol; `agent.py` → `vps/agent.py`; `worker.py`,
`ref_*.json|dxf`, `self-test-request.json`, `DejaVuSans.ttf` → `kanal/…`.
"""
from __future__ import annotations
import hashlib, io, sys, zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def hosting_esle(ad: str) -> str | None:
    if ad.startswith("kanal/package/"):
        return None                      # paket kendisi; ayrıca karşılaştırılır
    for on in ("kanal/beyin/", "kanal/motor/", "kanal/is_emri/"):
        if ad.startswith(on):
            return ad[len("kanal/"):]
    return ad                            # kanal/worker.py → kanal/worker.py


def vps_esle(ad: str) -> str | None:
    if ad == "SURUM.txt":
        return None
    if ad.split("/")[0] in ("beyin", "motor", "is_emri"):
        return ad
    if ad == "agent.py":
        return "vps/agent.py"
    return "kanal/" + ad                 # worker.py, ref_*, self-test-request.json, DejaVuSans.ttf


def karsilastir(z: zipfile.ZipFile, esle) -> dict:
    sonuc = {"ayni": [], "farkli": [], "yalniz_pakette": [], "atlandi": []}
    for bilgi in z.infolist():
        if bilgi.is_dir():
            continue
        hedef = esle(bilgi.filename)
        if hedef is None:
            sonuc["atlandi"].append(bilgi.filename); continue
        yol = KOK / hedef
        if not yol.exists():
            sonuc["yalniz_pakette"].append(bilgi.filename); continue
        (sonuc["ayni"] if sha(z.read(bilgi)) == sha(yol.read_bytes()) else sonuc["farkli"]).append(bilgi.filename)
    return sonuc


def main(hosting_zip: str) -> int:
    ham = Path(hosting_zip).read_bytes()
    print(f"hosting paketi: {Path(hosting_zip).name}  sha256 {sha(ham)}")
    with zipfile.ZipFile(io.BytesIO(ham)) as hz:
        h = karsilastir(hz, hosting_esle)
        ic = hz.read("kanal/package/current.zip")
        surum = hz.read("kanal/package/SURUM.txt").decode().strip() if "kanal/package/SURUM.txt" in hz.namelist() else "?"
    print(f"  depoyla aynı {len(h['ayni'])}, farklı {len(h['farkli'])}, yalnız pakette {len(h['yalniz_pakette'])}")
    for k in ("farkli", "yalniz_pakette"):
        for a in h[k]:
            print(f"    {k}: {a}")
    print(f"VPS paketi: kanal/package/current.zip  sha256 {sha(ic)}  sürüm {surum}")
    with zipfile.ZipFile(io.BytesIO(ic)) as vz:
        v = karsilastir(vz, vps_esle)
    print(f"  depoyla aynı {len(v['ayni'])}, farklı {len(v['farkli'])}, yalnız pakette {len(v['yalniz_pakette'])}")
    for k in ("farkli", "yalniz_pakette"):
        for a in v[k]:
            print(f"    {k}: {a}")
    kod_farki = [a for a in h["farkli"] + v["farkli"] if not a.split("/")[-1].startswith(("is_emri_", "rapor"))]
    print("SONUÇ:", "kod dosyalarında fark yok" if not kod_farki else f"kod farkı: {kod_farki}")
    return 0 if not kod_farki else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1]))
