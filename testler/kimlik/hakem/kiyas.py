"""Yerleşim kapısının kıyas aracı (İE-15 · KH-1 ve KH-2; hakem aracı, D-24).

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
değişikliğidir).

KH-2 (hakem değişikliği; ayrı onayla):
- **Adım kapısı.** Proje ayarında `kiyas.adimlar.<ADIM>` adım başına satır ekler (`anahtarlar`, `kapi`, `metre`). `--adim K2` ile koşunca
  bu satırlar KH-1'in satırlarının arkasına eklenir ve kapıya girer; adımsız koşunun satırları ve Kapı 1'i KH-1'deki gibidir.
- **Metre kapısı (`metre_kiyasla`, yeni işlev).** Bir anahtarı sözleşmeyle taşıyan parçaların boyları (`Qto_…BaseQuantities.Length`,
  modelin uzunluk birimiyle metreye çevrilir) toplanır ve cevaptaki metreyle kıyaslanır; fark ±%3 içindeyse geçer. Boy taşımayan bir
  parça "modelde boy yok" yazar ve geçmez. Adımla koşulunca Kapı 1 adet ve metre birlikte geçerse geçer.
- **Bölümler.** Okuyucunun KH-2 bölümleri (omega, aşık, kaplama, betopan, dere) tanınır; birinin teyidi yalnız kendi satırlarını durdurur.
  Omega anahtarı, okuyucudaki gibi proje ayarından (`ayar.omega.anahtar`) da tanınır.
- **Adım ayarı denetlenir.** Adımın `kapi` listesi boşsa ya da satırlarda olmayan bir anahtar içeriyorsa, `metre` satırında `anahtar`
  ya da `cevap` yoksa araç koşmaz (hata); boş bir adım "geçer" yazmaz.
- **Rapor.** Adet tablosunda satırın sayım yolu (kart sözleşmesi ya da ad eşlemesi) görünür.

Koşma:
    python3 -I testler/kimlik/hakem/kiyas.py <model.ifc> <cevap.json> --proje testler/kimlik/hakem/projeler/PK01.json [--adim K2] [--md <rapor.md>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu

SOZLESME = ("PortatifEv_Parca", "PaftaAnahtari")
METRE_PAYI = 0.03                           # metre kapısı: plan.md §5, ±%3


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


BOLUMLER = ("montaj", "h_plani", "makas", "omega", "asik", "kaplama", "betopan", "dere")
EK_ANAHTAR = {"tavan_omegasi": "omega", "duvar_omegasi_asma": "omega", "asik": "asik", "sandvic_panel": "kaplama",
              "bas_makas_betopan": "betopan", "dere": "dere", "inis": "dere"}


def bolum(anahtar: str, omega_anahtari: str | None = None) -> str | None:
    """Anahtarın okuyucudaki bölümü; teyit bekleyen bölümün satırı kapıya girmez."""
    if omega_anahtari and anahtar == omega_anahtari:
        return "omega"
    if anahtar.startswith("ayrinti.montaj."):
        return "montaj"
    if anahtar.startswith(("h_plani.", "ayrinti.h_plani.")):
        return "h_plani"
    if anahtar.startswith(("makas_", "ayrinti.makas.")):
        return "makas"
    if anahtar in EK_ANAHTAR:
        return EK_ANAHTAR[anahtar]
    if anahtar.startswith("ayrinti.") and anahtar.split(".")[1] in BOLUMLER[3:]:
        return anahtar.split(".")[1]
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


def _boy_m(e, olcek: float) -> float | None:
    """Parçanın boyu (m): `Qto_…BaseQuantities` setindeki `Length`; yoksa None."""
    for ad, q in ue.get_psets(e, qtos_only=True).items():
        if ad.startswith("Qto_") and ad.endswith("BaseQuantities") and isinstance(q.get("Length"), (int, float)):
            return q["Length"] * olcek
    return None


def boylar(model: ifcopenshell.file, anahtarlar: list[str]) -> dict[str, dict]:
    """Her anahtarı sözleşmeyle taşıyan parçaların sayısı, boysuz olanların sayısı ve boy toplamı (m)."""
    olcek = uu.calculate_unit_scale(model)
    out = {a: {"parca": 0, "boysuz": 0, "toplam_m": 0.0} for a in anahtarlar}
    for e in model.by_type("IfcProduct"):
        k = ue.get_psets(e).get(SOZLESME[0], {}).get(SOZLESME[1])
        if not k:
            continue
        for a in dict.fromkeys(_sozlesme_anahtarlari(k)):
            if a in out:
                b = _boy_m(e, olcek)
                out[a]["parca"] += 1
                if b is None:
                    out[a]["boysuz"] += 1
                else:
                    out[a]["toplam_m"] += b
    for v in out.values():
        v["toplam_m"] = round(v["toplam_m"], 4)
    return out


def metre_kiyasla(model: ifcopenshell.file, cevap: dict, metre: list[dict], kapali: set[str] = frozenset(),
                  omega_anahtari: str | None = None) -> list[dict]:
    """Metre kapısı (KH-2): `metre` listesindeki her anahtar için modelin boy toplamı cevaptaki metreyle (`cevap` yolu) kıyaslanır."""
    B = boylar(model, [m["anahtar"] for m in metre])
    satirlar = []
    for m in metre:
        a, p, b = m["anahtar"], cevap_degeri(cevap, m["cevap"]), B[m["anahtar"]]
        md_ = b["toplam_m"] if b["parca"] and not b["boysuz"] else None
        if bolum(a, omega_anahtari) in kapali or kapali - set(BOLUMLER):
            sonuc = "teyit bekliyor"
        elif p is None:
            sonuc = "paftada yok"
        elif not b["parca"]:
            sonuc = "modelde yok"
        elif b["boysuz"]:
            sonuc = "modelde boy yok"
        else:
            sonuc = "geçer" if abs(md_ - p) <= METRE_PAYI * p + 1e-9 else "geçmez"
        satirlar.append({"anahtar": a, "paftadan_m": p, "modelden_m": md_, "parca": b["parca"], "boysuz": b["boysuz"],
                         "fark_yuzde": None if p in (None, 0) or md_ is None else round((md_ - p) / p * 100, 2), "sonuc": sonuc})
    return satirlar


def kiyasla(model_yolu: Path | str, cevap: dict, proje: dict, adim: str | None = None) -> dict:
    K = proje.get("kiyas", {})
    A = None
    if adim:
        A = K.get("adimlar", {}).get(adim)
        if A is None:
            raise ValueError(f"proje ayarında adım yok: {adim} (var olanlar: {sorted(K.get('adimlar', {}))})")
    anahtarlar = K.get("anahtarlar", []) + [a for a in (A or {}).get("anahtarlar", []) if a not in K.get("anahtarlar", [])]
    if A is not None:
        if not A.get("kapi"):
            raise ValueError(f"adım {adim}: kapı listesi boş")
        yok = [a for a in A["kapi"] if a not in anahtarlar]
        if yok:
            raise ValueError(f"adım {adim}: kapıdaki anahtar satırlarda yok: {yok}")
        eksik = [m for m in A.get("metre", []) if not (m.get("anahtar") and m.get("cevap"))]
        if eksik:
            raise ValueError(f"adım {adim}: metre satırında `anahtar` ya da `cevap` yok: {eksik}")
    omega_anahtari = proje.get("ayar", {}).get("omega", {}).get("anahtar")
    model = ifcopenshell.open(str(model_yolu))
    sayim, kartli = say(model, anahtarlar, K.get("eslemeler", []))
    teyit = cevap.get("teyit_bekliyor", [])
    kapali = {t["bolum"] for t in teyit}
    kapi_anahtarlari = set(K.get("kapi", [])) | (set(K.get("kart_kapisi", [])) if kartli else set()) | set((A or {}).get("kapi", []))
    satirlar = []
    for a in anahtarlar:
        p, m = cevap_degeri(cevap, a), sayim[a]["adet"]
        if bolum(a, omega_anahtari) in kapali or kapali - set(BOLUMLER):
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
    out = {"proje": proje.get("kod"), "pafta_sha256": cevap.get("pafta_sha256"), "satirlar": satirlar,
           "kapi_1": "geçer" if kapi and all(s["sonuc"] == "geçer" for s in kapi) else "geçmez",
           "kart_modeli": kartli, "teyit_bekliyor": teyit, "metraj_referansi": proje.get("metraj_referansi")}
    if A is not None:                                   # adımla: Kapı 1 adet ve metre birlikte
        metre = metre_kiyasla(model, cevap, A.get("metre", []), kapali, omega_anahtari)
        gecer = out["kapi_1"] == "geçer" and all(m["sonuc"] == "geçer" for m in metre)
        out |= {"adim": adim, "metre": metre, "kapi_1": "geçer" if gecer else "geçmez"}
    return out


def md(k: dict) -> str:
    bos = lambda v: "—" if v is None else f"{v:g}" if isinstance(v, float) else str(v)
    satir = ["| Anahtar | Paftadan | Modelden | Fark | Sonuç | Kapıda | Sayım yolu |", "|---|---|---|---|---|---|---|"]
    for s in k["satirlar"]:
        satir.append(f"| `{s['anahtar']}` | {bos(s['paftadan'])} | {bos(s['modelden'])} | {bos(s['fark'])} | {s['sonuc']} | "
                     f"{'evet' if s['kapida'] else 'bilgi'} | {s['sayim_yolu']} |")
    satir.append("")
    if "adim" in k:
        satir += [f"Metre (±%{METRE_PAYI * 100:g}, {k['adim']}):", "",
                  "| Anahtar | Paftadan (m) | Modelden (m) | Fark (%) | Parça | Sonuç |", "|---|---|---|---|---|---|"]
        for m in k["metre"]:
            parca = f"{m['parca']}" + (f" ({m['boysuz']} boysuz)" if m["boysuz"] else "")
            satir.append(f"| `{m['anahtar']}` | {bos(m['paftadan_m'])} | {bos(m['modelden_m'])} | {bos(m['fark_yuzde'])} | {parca} | {m['sonuc']} |")
        satir.append("")
        satir.append(f"Kapı 1 (adet ve metre, {k['proje']}, {k['adim']}): **{k['kapi_1']}**.")
    else:
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
    ap.add_argument("--adim", help="proje ayarındaki `kiyas.adimlar` adımı (ör. K2); satırları ve metre kapısı da kapıya girer")
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    k = kiyasla(a.model, json.loads(a.cevap.read_text(encoding="utf-8")), json.loads(a.proje.read_text(encoding="utf-8")), a.adim)
    metin = md(k)
    if a.md:
        a.md.write_text(metin, encoding="utf-8")
    print(metin)
    return 0 if k["kapi_1"] == "geçer" else 1


if __name__ == "__main__":
    sys.exit(main())
