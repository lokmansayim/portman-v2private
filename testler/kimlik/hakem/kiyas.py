"""Yerleşim kapısının kıyas aracı (İE-15 · KH-1; hakem aracı, D-24).

Modelin IFC'sini açar, doğru cevaptaki her anahtar için modelde sayar ve yan yana yazar. Doğru cevap pafta okuyucusunun çıktısıdır
(`veri/<KOD>_pafta_katmani.json`; PR #28 biçimi, anahtar → {adet, not}, ayrıntı `ayrinti` altında).

Sayım iki yoldan biriyle yapılır:
- **Kart modeli sözleşmesi (K1 ve sonrası):** bir parça `PortatifEv_Parca` Pset'inde `PaftaAnahtari` taşıyorsa o parça bu anahtara
  sayılır. Bir parça birden çok anahtara girebilir; anahtarlar `;` ile ayrılır (ör. bir dış pano
  `ayrinti.montaj.pano.adet;ayrinti.montaj.pano.dis`, bir H `h_plani.dis;ayrinti.h_plani.turler.dubelli_kulakli`). Modelde bu
  özelliği taşıyan bir parça varsa o anahtar yalnız bu yoldan sayılır. Kart modeli bu sözleşmeye uyar; hakem kart modeline göre değişmez.
- **Bugünkü IFC (`motor.ifc_uret`):** proje ayarındaki `kiyas` eşlemesi; IFC sınıfı, ad deseni ve isteğe bağlı Pset özelliği.

Kapı 1 (plan.md §5): adette fark 0 geçer. Kapıya `kapi` listesindeki anahtarlar girer; model sözleşmeyi taşıyan en az bir parça
içeriyorsa (kart modeli) `kart_kapisi` listesindeki anahtarlar da girer. Böylece bugünkü IFC'de "modelde yok" yazan ayrıntı
(H türleri) K1'de hakem değişmeden kapıya girer. Okuyucunun teyit beklettiği bölümün (montaj, h_plani, makas) satırları
"teyit bekliyor" yazar ve kapı geçmez; neden rapora yazılır. Bu araç bölümünü tanımadığı bir teyit görürse hangi satırı etkilediğini
bilemez: bütün satırlar "teyit bekliyor" yazar. Bir parçada aynı anahtar iki kez yazılmışsa bir kez sayılır (bu iki cümle K1'in hakem
değişikliğidir). Boyla alınan kartların metre kıyası (±%3) KH-2'nin işidir ve yeni bir işlev olarak eklenir; bu dosyadaki sayım ve Kapı 1
değişmez.

Koşma:
    python3 -I testler/kimlik/hakem/kiyas.py <model.ifc> <cevap.json> --proje testler/kimlik/hakem/projeler/PK01.json [--md <rapor.md>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue

SOZLESME = ("PortatifEv_Parca", "PaftaAnahtari")


def cevap_degeri(cevap: dict, anahtar: str):
    v = cevap
    for a in anahtar.split("."):
        if not isinstance(v, dict) or a not in v:
            return None
        v = v[a]
    return v.get("adet") if isinstance(v, dict) else v


def _uyar(e, kural: dict) -> bool:
    if kural.get("ad") and not re.search(kural["ad"], e.Name or ""):
        return False
    if kural.get("pset"):
        pset, oz, desen = kural["pset"]
        deger = ue.get_psets(e).get(pset, {}).get(oz)
        if deger is None or not re.search(desen, str(deger)):
            return False
    return True


BOLUMLER = ("montaj", "h_plani", "makas")


def bolum(anahtar: str) -> str | None:
    """Anahtarın okuyucudaki bölümü; teyit bekleyen bölümün satırı kapıya girmez."""
    if anahtar.startswith("ayrinti.montaj."):
        return "montaj"
    if anahtar.startswith(("h_plani.", "ayrinti.h_plani.")):
        return "h_plani"
    if anahtar.startswith(("makas_", "ayrinti.makas.")):
        return "makas"
    return None


def _sozlesme_anahtarlari(deger) -> list[str]:
    parcalar = deger if isinstance(deger, (list, tuple)) else str(deger).split(";")
    return [a.strip() for a in parcalar if a and str(a).strip()]


def say(model: ifcopenshell.file, anahtarlar: list[str], eslemeler: list[dict]) -> tuple[dict[str, dict], int]:
    """Her anahtarı sayar; ikinci değer sözleşmeyi taşıyan parça sayısıdır (0 değilse model kart modelidir)."""
    sozlesmeli: dict[str, int] = {}
    kartli = 0
    for e in model.by_type("IfcProduct"):
        k = ue.get_psets(e).get(SOZLESME[0], {}).get(SOZLESME[1])
        if k:
            kartli += 1
            for a in dict.fromkeys(_sozlesme_anahtarlari(k)):          # parça başına bir kez ("a;a" iki sayılmaz)
                sozlesmeli[a] = sozlesmeli.get(a, 0) + 1
    out = {}
    for anahtar in anahtarlar:
        if anahtar in sozlesmeli:
            out[anahtar] = {"adet": sozlesmeli[anahtar], "yol": f"{SOZLESME[0]}.{SOZLESME[1]}"}
            continue
        kurallar = [k for k in eslemeler if k["anahtar"] == anahtar]
        if not kurallar:
            out[anahtar] = {"adet": None, "yol": "modelde yok"}
            continue
        n = sum(1 for k in kurallar for e in model.by_type(k["sinif"]) if _uyar(e, k))
        out[anahtar] = {"adet": n, "yol": "; ".join(f"{k['sinif']} {k.get('ad', '')}".strip() for k in kurallar)}
    return out, kartli


def kiyasla(model_yolu: Path | str, cevap: dict, proje: dict) -> dict:
    K = proje.get("kiyas", {})
    anahtarlar = K.get("anahtarlar", [])
    sayim, kartli = say(ifcopenshell.open(str(model_yolu)), anahtarlar, K.get("eslemeler", []))
    teyit = cevap.get("teyit_bekliyor", [])
    kapali = {t["bolum"] for t in teyit}
    kapi_anahtarlari = set(K.get("kapi", [])) | (set(K.get("kart_kapisi", [])) if kartli else set())
    satirlar = []
    for a in anahtarlar:
        p, m = cevap_degeri(cevap, a), sayim[a]["adet"]
        if bolum(a) in kapali or kapali - set(BOLUMLER):
            sonuc = "teyit bekliyor"
        elif p is None:
            sonuc = "paftada yok"
        elif m is None:
            sonuc = "modelde yok"
        else:
            sonuc = "geçer" if m == p else "geçmez"
        satirlar.append({"anahtar": a, "paftadan": p, "modelden": m, "fark": None if p is None or m is None else m - p,
                         "sonuc": sonuc, "sayim_yolu": sayim[a]["yol"], "kapida": a in kapi_anahtarlari})
    kapi = [s for s in satirlar if s["kapida"]]
    return {"proje": proje.get("kod"), "pafta_sha256": cevap.get("pafta_sha256"), "satirlar": satirlar,
            "kapi_1": "geçer" if kapi and all(s["sonuc"] == "geçer" for s in kapi) else "geçmez",
            "kart_modeli": kartli, "teyit_bekliyor": teyit, "metraj_referansi": proje.get("metraj_referansi")}


def md(k: dict) -> str:
    satir = ["| Anahtar | Paftadan | Modelden | Fark | Sonuç | Kapıda |", "|---|---|---|---|---|---|"]
    for s in k["satirlar"]:
        bos = lambda v: "—" if v is None else str(v)
        satir.append(f"| `{s['anahtar']}` | {bos(s['paftadan'])} | {bos(s['modelden'])} | {bos(s['fark'])} | {s['sonuc']} | "
                     f"{'evet' if s['kapida'] else 'bilgi'} |")
    satir.append("")
    satir.append(f"Kapı 1 (adet, {k['proje']}): **{k['kapi_1']}**.")
    if k["kart_modeli"]:
        satir.append(f"Kart modeli: evet, {k['kart_modeli']} parça `{'.'.join(SOZLESME)}` taşıyor; `kart_kapisi` satırları da kapıda.")
    else:
        satir.append("Kart modeli: hayır (bugünkü IFC; ad ve Pset eşlemesiyle sayıldı).")
    if not k["metraj_referansi"]:
        satir.append("Metraj kapısı: referans yok, koşulmadı; Patron kabulü kapının yerine geçmez.")
    else:
        satir.append(f"Metraj kapısı: referans {k['metraj_referansi']}; bu araç koşmaz, sonucu metraj kapısının raporunda.")
    if k["teyit_bekliyor"]:
        satir.append("Teyit bekleyen (bu bölümlerin satırları kapıdan geçmez):")
        satir += [f"- {t['bolum']}: {t['neden']}" + ("" if t["bolum"] in BOLUMLER else " (bölüm tanınmıyor; bütün satırlar teyit bekliyor)")
                  for t in k["teyit_bekliyor"]]
    else:
        satir.append("Teyit bekleyen yok.")
    return "\n".join(satir) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model", type=Path)
    ap.add_argument("cevap", type=Path)
    ap.add_argument("--proje", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    k = kiyasla(a.model, json.loads(a.cevap.read_text(encoding="utf-8")), json.loads(a.proje.read_text(encoding="utf-8")))
    metin = md(k)
    if a.md:
        a.md.write_text(metin, encoding="utf-8")
    print(metin)
    return 0 if k["kapi_1"] == "geçer" else 1


if __name__ == "__main__":
    sys.exit(main())
