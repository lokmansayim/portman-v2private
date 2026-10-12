"""İE-08 Adım 8 · Mühendis kabul kaydı (K-A10): `beyin/veri/adaylar.json`'daki adaylardan yalnız komut satırında verilen kodlar Postgres
`adaylar` tablosuna `durum = gecerli` ve `muhendis_kabulu = {kim, tarih, not}` ile yazılır. Kalıcı akış (`kanal/kalici.py`) yalnız bu
kayıtları bayiye sunar (`depo.kabul_edilmis_adaylar`): kabul edilmeyen aday yazılmaz, sunulmaz.

    PORTMAN_PG_DSN="dbname=portman" python3 araclar/aday_kabul.py --kodlar Ç8801,Ç8801K,Ç8801L --kim "<mühendisin adı>" \
        --tarih 2026-10-13 [--not "<mühendisin notu>"] [--paket "<kabul paketi tarihi/klasörü>"] [--kuru]

Kurallar (Lokman, 12 Ekim 2026): mühendis yedi modeli tek oturumda kabul paketiyle görür (`araclar/kabul_paketi.py`); betik ondan sonra,
yalnız kabul edilen kodlarla koşar; ad yalnız komut satırından gelir, depoya (git) ve çıktıya girmez (çıktıda yalnız ilk harf);
yeniden koşulabilir (upsert, `depo.aday_yaz`). Sunucuda `vps/ie08_adaylar.sh` ile Lokman koşar (ayrı onay). `--kuru`: yazmaz, ne
yazacağını söyler."""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "kanal"))


def kod_normalize(s: str) -> str:
    """Tek kaynak: `beyin.katalog.Katalog.kod_normalize` (Ç8801-K → Ç8801K, C8801K → Ç8801K, KT-01 → KT01)."""
    from beyin.katalog import Katalog
    return Katalog.kod_normalize(s) or s.strip().upper()


def kabul_kayitlari(adaylar: list[dict], kodlar: list[str], kim: str, tarih: str, not_: str, paket: str) -> tuple[list[dict], list[str]]:
    """Yazılacak kayıtlar (kod sırasıyla) ve adaylar.json'da bulunmayan kodlar."""
    kayit = {str(a["kod"]).upper(): a for a in adaylar}
    out, yok = [], []
    for k in kodlar:
        a = kayit.get(k)
        if a is None:
            yok.append(k); continue
        out.append({"kod": k, "durum": "gecerli", "referans_model": a.get("referans_model"),
                    "kaynak": {"motor": a.get("motor"), "tanim": a.get("tanim"), "tanim_sha256": a.get("tanim_sha256"), **(a.get("kaynak") or {})},
                    "ozet": {"katalog_m2": a.get("katalog_m2"), "kapali_m2": a.get("kapali_m2"), "veranda_m2": a.get("veranda_m2"),
                             "oda_programi": a.get("oda_programi"), "kat": a.get("kat"), "varyantlar": a.get("varyantlar"), **(a.get("ozet") or {})},
                    "denetim": {"kabul_paketi": paket, "dogrulama": (a.get("kaynak") or {}).get("dogrulama")},
                    "muhendis_kabulu": {"kim": kim, "tarih": tarih, "not": not_}, "not_": a.get("not") or None})
    return out, yok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kodlar", required=True, help="mühendisin kabul ettiği kodlar, virgülle (Ç8801,Ç8801K,…)")
    ap.add_argument("--kim", required=True, help="mühendisin adı (yalnız Postgres'e yazılır)")
    ap.add_argument("--tarih", required=True, help="kabul tarihi (YYYY-AA-GG)")
    ap.add_argument("--not", dest="not_", default="", help="mühendisin notu")
    ap.add_argument("--paket", default="", help="kabul paketinin tarihi ya da klasörü (denetim alanına)")
    ap.add_argument("--adaylar", default=str(KOK / "beyin" / "veri" / "adaylar.json"))
    ap.add_argument("--kuru", action="store_true", help="yazma; ne yazılacağını söyle")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.tarih):
        print("DUR: tarih YYYY-AA-GG biçiminde olmalı"); return 2
    if not a.kim.strip():
        print("DUR: mühendisin adı boş"); return 2
    kodlar = [kod_normalize(k) for k in a.kodlar.split(",") if k.strip()]
    adaylar = json.loads(Path(a.adaylar).read_text(encoding="utf-8"))
    kayitlar, yok = kabul_kayitlari(adaylar, kodlar, a.kim.strip(), a.tarih, a.not_.strip(), a.paket.strip())
    if yok:
        print("DUR: adaylar.json'da olmayan kod:", ", ".join(yok)); return 2
    if not kayitlar:
        print("DUR: kod verilmedi"); return 2
    kim_izi = a.kim.strip()[0] + "…"                 # ad çıktıya girmez (K09; kişisel veri)
    if a.kuru:
        print(f"KURU: {len(kayitlar)} kayıt yazılacak ({', '.join(k['kod'] for k in kayitlar)}); kim {kim_izi}, tarih {a.tarih}")
        return 0
    if not os.environ.get("PORTMAN_PG_DSN"):
        print("DUR: PORTMAN_PG_DSN tanımlı değil"); return 2
    from depo import Depo
    d = Depo()
    for k in kayitlar:
        d.aday_yaz(k["kod"], k["durum"], referans_model=k["referans_model"], kaynak=k["kaynak"], ozet=k["ozet"], denetim=k["denetim"],
                   muhendis_kabulu=k["muhendis_kabulu"], not_=k["not_"])
    kabul = sorted(d.kabul_edilmis_adaylar())
    print(f"yazıldı: {len(kayitlar)} kayıt ({', '.join(k['kod'] for k in kayitlar)}); kim {kim_izi}, tarih {a.tarih}")
    print("kabul kaydı olan 'gecerli' adaylar:", ", ".join(kabul))
    return 0


if __name__ == "__main__":
    sys.exit(main())
