"""İE-15 · K1 · Kimlik kartlı model (D-24): bugünkü IFC'nin parçaları kartlarına bağlanır, adetler modelden sayılır.

    python -m motor.kart_model <İş Emri.json> <çıktı klasörü> [--kod PK01]

Çıktılar: `<kod>.ifc` (bugünkü IFC, `motor.ifc_uret`; dokunulmaz), `<kod>_model.ifc` (kart modeli; Bonsai'de açılır),
`<kod>_kart_sayim.json` ve `<kod>_kart_katalogu.xlsx` (kartlar, sayım, H türleri, kartsız parçalar).

- **Kart** bir üründür; modelde IFC tür nesnesidir (`IfcWallType`, `IfcMemberType`…). Kartlar `kurallar/urun/kartlar.json`'da; alanları türde
  `PortatifEv_Kart` setinde durur. Parçaya özgü alanlar örnekte `PortatifEv_Parca` setindedir: kart kodu, paftadaki anahtarı
  (`PaftaAnahtari`, `;` ile; yerleşim kapısının hakemi bu sözleşmeyle sayar), bugünkü katalog kodu ve uygulanan kural.
- **Kart modeli bugünkü IFC'nin kopyasıdır** (plan §4): parça eklenmez, silinmez, yeri ve geometrisi değişmez; yalnız türleri kartlara geçer.
  Duvar kartı eski pano tipinin katmanlarını ve `PortatifEv_PanoTipi` setini taşır, eski pano tipi kalkar. Ortak parçada çelişki çıkarsa
  bugünkü IFC esastır (test). İkisinin tek dosyada birleşmesi K4'ün işidir.
- **H türü bir kuraldır** (`kurallar/yerlesim/prefabrik.json › h_turu`, PK-07 lejantı): dış duvarda makasa denk gelen H dübelli & kulaklı,
  öteki dış H dübelli. Girdiler bugünkü IFC'de: dış duvarların ve H'lerin yeri, makasların yeri (makas parçalarından). Denk gelme payı makas
  aralığının yarısıdır; aralık `kurallar/liste/prefabrik.json`'dan okunur.
- **Kartı olmayan parça sayılmaz:** hiçbir karta uymayan parça "kural yok" yazar; iki karta uyan parçada model üretilmez. Görünüm (üçlü H'nin
  yüz görünümü), bileşen (makasın çubukları) ve kartsız olduğu bildirilen parçalar (çatı yüzü, alın, zemin betonu, boşluk) ayrı listelenir.

LLM yok, ağ yok. Sayım kodda; Bonsai bakma yeridir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
import ifcopenshell.guid
import ifcopenshell.util.element as ue

KOK = Path(__file__).resolve().parents[1]
KARTLAR = KOK / "kurallar" / "urun" / "kartlar.json"
YERLESIM = KOK / "kurallar" / "yerlesim" / "prefabrik.json"
LISTE_KURALLARI = KOK / "kurallar" / "liste" / "prefabrik.json"
KART_SETI, PARCA_SETI = "PortatifEv_Kart", "PortatifEv_Parca"
TUR_AD_ALANI = uuid.UUID("5d1f6a52-6c2b-4b8e-9a51-0f1e2d3c4b5a")     # kart türünün GlobalId'si koddan türer (her üretimde aynı)


def _oku(yol: Path) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def _goreli(yol: Path) -> str:
    try:
        return Path(yol).resolve().relative_to(KOK).as_posix()
    except ValueError:
        return str(yol)


def _api(ad: str, *a, **k):
    modul, islev = ad.split(".")
    return getattr(getattr(ifcopenshell.api, modul), islev)(*a, **k)


# ----------------------------------------------------------------------------- geometri (dünya koordinatı, cm)
class _Kutular:
    def __init__(self):
        self.s = ifcopenshell.geom.settings()
        self.s.set("use-world-coords", True)
        self._bellek: dict[int, tuple[list[float], list[float]]] = {}

    def __call__(self, e) -> tuple[list[float], list[float]]:
        if e.id() not in self._bellek:
            parcalar = [p for r in e.IsDecomposedBy for p in r.RelatedObjects] if e.is_a("IfcElementAssembly") else [e]
            xs, ys, zs = [], [], []
            for p in parcalar:
                v = ifcopenshell.geom.create_shape(self.s, p).geometry.verts
                xs += v[0::3]; ys += v[1::3]; zs += v[2::3]
            self._bellek[e.id()] = ([min(xs) * 100, min(ys) * 100, min(zs) * 100], [max(xs) * 100, max(ys) * 100, max(zs) * 100])
        return self._bellek[e.id()]

    def merkez(self, e) -> tuple[float, float]:
        a, b = self(e)
        return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


# ----------------------------------------------------------------------------- eşleme
def _bosluk(e) -> str:
    """Duvarın boşluk türleri (`PortatifEv_Bosluk.Tur`), sıralı ve virgülle; boşluksuz duvarda boş."""
    return ",".join(sorted(str(ue.get_psets(r.RelatedOpeningElement).get("PortatifEv_Bosluk", {}).get("Tur", "?"))
                           for r in getattr(e, "HasOpenings", ()) or ()))


def _uyar(e, m: dict) -> bool:
    """Eşlemenin sınıf, ad, özellik ve boşluk koşulları (yerleşim kuralı ayrı)."""
    if not e.is_a(m["sinif"]):
        return False
    if m.get("ad") and not re.search(m["ad"], e.Name or ""):
        return False
    ps = ue.get_psets(e)
    for pset, oz, desen in m.get("kosul", []):
        deger = ps.get(pset, {}).get(oz)
        if deger is None or not re.search(desen, str(deger)):
            return False
    if "bosluk" in m and not re.search(m["bosluk"], _bosluk(e)):
        return False
    return True


# ----------------------------------------------------------------------------- H türü kuralı
def h_turleri(f: ifcopenshell.file, adaylar: list, kural: dict, makas_aralik_cm: float, kutu: _Kutular) -> dict[int, dict]:
    """Dış H adaylarının türü (PK-07 lejantı). Dönen: parça id → {tur, makas, uzaklik_cm}."""
    pay_cizgi = kural["duvar_cizgisi_payi_cm"]
    pay_denk = makas_aralik_cm * kural["denk_gelme_payi"]["carpan"]
    makaslar = []
    for e in sorted(f.by_type("IfcElementAssembly"), key=lambda e: e.Name or ""):
        if ue.get_predefined_type(e) != "TRUSS":
            continue
        a, b = kutu(e)
        eksen = 0 if b[0] - a[0] > b[1] - a[1] else 1                 # makasın uzandığı eksen
        makaslar.append({"ad": e.Name, "eksen": eksen, "konum": (a[1 - eksen] + b[1 - eksen]) / 2, "aralik": (a[eksen], b[eksen])})
    duvarlar = []                                                      # dış duvar parçaları: (uzandığı eksen, orta çizgi, uç, uç)
    for w in f.by_type("IfcWall"):
        if ue.get_psets(w).get("Pset_WallCommon", {}).get("IsExternal") is not True:
            continue
        a, b = kutu(w)
        yon = 0 if b[0] - a[0] > b[1] - a[1] else 1
        duvarlar.append((yon, (a[1 - yon] + b[1 - yon]) / 2, a[yon], b[yon]))
    H = [(e, kutu.merkez(e)) for e in adaylar]
    sonuc = {e.id(): {"tur": kural["turler"]["denk_degil"], "makas": None, "uzaklik_cm": None} for e, _ in H}
    for m in makaslar:
        yon = 1 - m["eksen"]                                           # oturduğu duvar makasın dizildiği eksende uzanır
        cizgiler = sorted({round(c, 1) for y, c, u0, u1 in duvarlar
                           if y == yon and m["aralik"][0] <= c <= m["aralik"][1] and u0 <= m["konum"] <= u1})
        for c in cizgiler:
            ustteki = [(e, xy) for e, xy in H if abs(xy[1 - yon] - c) <= pay_cizgi]
            if not ustteki:
                continue
            e, xy = min(ustteki, key=lambda t: (abs(t[1][yon] - m["konum"]), t[0].Name or ""))
            d = abs(xy[yon] - m["konum"])
            if d <= pay_denk:
                sonuc[e.id()] = {"tur": kural["turler"]["denk"], "makas": m["ad"], "uzaklik_cm": round(d, 2)}
    return sonuc


# ----------------------------------------------------------------------------- sınıflandırma
def siniflandir(f: ifcopenshell.file, kartlar: dict, yerlesim: dict, makas_aralik_cm: float) -> list[dict]:
    """Her `IfcElement` için rol: kart, görünüm, bileşen, kartsız ya da kural yok."""
    kutu = _Kutular()
    elemanlar = sorted(f.by_type("IfcElement"), key=lambda e: (e.is_a(), e.Name or "", e.GlobalId))
    h_adaylari = [e for e in elemanlar if any(_uyar(e, m) for k in kartlar["kartlar"] for m in k["bugunku_ifc"]
                                               if m.get("kural", {}).get("ad") == "h_turu")]
    hk = h_turleri(f, h_adaylari, yerlesim["kurallar"]["h_turu"], makas_aralik_cm, kutu) if h_adaylari else {}
    kural_sonucu = {"h_turu": lambda e: hk.get(e.id(), {}).get("tur")}
    out = []
    for e in elemanlar:
        ust = [r.RelatingObject for r in getattr(e, "Decomposes", ()) or () if r.is_a("IfcRelAggregates")]
        if any(u.is_a("IfcElementAssembly") for u in ust):
            out.append({"e": e, "rol": "bilesen", "asil": ust[0]})
            continue
        g = next((g for g in kartlar.get("gorunum", []) if _uyar(e, g)), None)
        if g:
            xy = kutu.merkez(e)
            asillar = [(a, kutu.merkez(a)) for a in elemanlar if _uyar(a, g["asil"])]
            a, axy = min(asillar, key=lambda t: (abs(t[1][0] - xy[0]) + abs(t[1][1] - xy[1]), t[0].Name or ""), default=(None, None))
            if a is not None and max(abs(axy[0] - xy[0]), abs(axy[1] - xy[1])) <= g["pay_cm"]:
                out.append({"e": e, "rol": "gorunum", "asil": a, "neden": g["neden"]})
                continue
            out.append({"e": e, "rol": "kural_yok", "neden": "görünümün sayılan parçası bulunamadı"})
            continue
        uyan = []
        for k in kartlar["kartlar"]:
            for m in k["bugunku_ifc"]:
                if _uyar(e, m) and (not m.get("kural") or kural_sonucu[m["kural"]["ad"]](e) == m["kural"]["deger"]):
                    uyan.append(k)
                    break
        if len(uyan) > 1:
            raise ValueError(f"{e.Name}: iki karta uyuyor ({', '.join(k['kod'] for k in uyan)}); kart dosyası düzeltilmeli")
        if uyan:
            kayit = {"e": e, "rol": "kart", "kart": uyan[0]}
            if e.id() in hk:
                kayit["h"] = hk[e.id()]
            out.append(kayit)
            continue
        ks = next((k for k in kartlar.get("kartsiz", []) if _uyar(e, k)), None)
        out.append({"e": e, "rol": "kartsiz", "neden": ks["neden"]} if ks else {"e": e, "rol": "kural_yok", "neden": "hiçbir karta uymuyor"})
    return out


def _katalog_kodu(e) -> str:
    ps = ue.get_psets(e)
    return next((str(ps[s]["BOMKod"]) for s in ("PortatifEv_Pano", "PortatifEv_Dograma", "PortatifEv_Kapsam") if ps.get(s, {}).get("BOMKod")), "")


def pafta_anahtarlari(e, kart: dict) -> list[str]:
    anahtarlar = list(kart.get("pafta", []))
    if kart.get("pafta_dis_ic"):
        dis = ue.get_psets(e).get("Pset_WallCommon", {}).get("IsExternal")
        anahtarlar.append(kart["pafta_dis_ic"]["dis" if dis else "ic"])
    return list(dict.fromkeys(anahtarlar))


H_TURU_AD = {"dubelli_kulakli": "dübelli & kulaklı", "dubelli": "dübelli"}


# ----------------------------------------------------------------------------- kart modeli
def _tur_olustur(f, kart: dict, surum: str):
    sinif, alt = kart["ifc"]["sinif"], kart["ifc"]["alt_tur"]
    t = _api("root.create_entity", f, ifc_class=sinif, name=f"{kart['kod']} {kart['ad']}", predefined_type=alt)
    t.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(TUR_AD_ALANI, kart["kod"]).hex)
    t.Tag = kart["kod"]
    if sinif == "IfcDoorType":
        t.OperationType = "NOTDEFINED"
    elif sinif == "IfcWindowType":
        t.PartitioningType = "NOTDEFINED"
    ps = _api("pset.add_pset", f, product=t, name=KART_SETI)
    _api("pset.edit_pset", f, pset=ps, properties={
        "Kod": kart["kod"], "Ad": kart["ad"], "ListeGrubu": kart["liste"]["grup"], "ListeSatirlari": "; ".join(kart["liste"]["satirlar"]),
        "Olcu": kart["olcu"], "Birim": kart["birim"], "Nerede": kart["nerede"], "Sayim": kart["sayim"],
        "KaynakDurum": kart["kaynak"]["durum"], "KaynakTarih": kart["kaynak"]["tarih"], "Dayanak": kart["kaynak"]["dayanak"],
        "KartSurumu": surum})
    return t


def _duvar_turu_tasi(f, t, duvarlar: list) -> None:
    """Duvar kartı eski pano tipinin katmanlarını ve `PortatifEv_PanoTipi` setini alır (parçanın özellikleri aynı kalır)."""
    eski = {ue.get_type(w) for w in duvarlar} - {None}
    if len(eski) != 1:
        raise ValueError(f"{t.Tag}: parçaları {len(eski)} ayrı pano tipinden geliyor; kart iki katman dizisini taşıyamaz")
    eski = eski.pop()
    malzeme = ue.get_material(eski)
    if malzeme is not None:
        _api("material.assign_material", f, products=[t], type=malzeme.is_a(), material=malzeme)
    pt = ue.get_psets(eski).get("PortatifEv_PanoTipi")
    if pt:
        ps = _api("pset.add_pset", f, product=t, name="PortatifEv_PanoTipi")
        _api("pset.edit_pset", f, pset=ps, properties={k: v for k, v in pt.items() if k != "id"})


def _eski_turu_kaldir(f, t) -> None:
    """Önce malzeme bağı elle çözülür: API'nin `unassign_material`'ı türün katman dizisini kullanan bütün parçaların katman kullanımını
    (`IfcMaterialLayerSetUsage`) da siler (ifcopenshell 0.9.0); kart modelinde duvarlar bugünkü IFC'deki kullanımı korur (test)."""
    for rel in list(t.HasAssociations):
        if rel.is_a("IfcRelAssociatesMaterial"):
            kalan = [o for o in rel.RelatedObjects if o != t]
            if kalan:
                rel.RelatedObjects = kalan
            else:
                f.remove(rel)
    _api("root.remove_product", f, product=t)


def kart_modeli(ifc_yolu: Path, cikti_yolu: Path, kartlar: dict | None = None, yerlesim: dict | None = None,
                liste_kurallari: dict | None = None) -> dict:
    """Bugünkü IFC → kart modeli. Bugünkü IFC'ye yazılmaz. Dönen: sayım (JSON'a yazılacak biçimde)."""
    kartlar = kartlar or _oku(KARTLAR)
    yerlesim = yerlesim or _oku(YERLESIM)
    liste_kurallari = liste_kurallari or _oku(LISTE_KURALLARI)
    okunan = yerlesim["kurallar"]["h_turu"]["denk_gelme_payi"]["okunan"]
    makas_aralik_cm = liste_kurallari["kurallar"][okunan.rsplit(".", 1)[1]]["deger"]
    f = ifcopenshell.open(str(ifc_yolu))
    sinif = siniflandir(f, kartlar, yerlesim, makas_aralik_cm)
    surum = kartlar["surum"]
    kaynak = f"{_goreli(KARTLAR)} sürüm {surum}"

    gruplar: dict[str, list] = {}
    for s in sinif:
        if s["rol"] == "kart":
            gruplar.setdefault(s["kart"]["kod"], []).append(s)
    turler, eski_turler = {}, set()
    for kart in kartlar["kartlar"]:
        parcalar = [s["e"] for s in gruplar.get(kart["kod"], [])]
        if not parcalar:
            continue
        t = turler[kart["kod"]] = _tur_olustur(f, kart, surum)
        if kart["ifc"]["sinif"] == "IfcWallType":
            _duvar_turu_tasi(f, t, parcalar)
        eski_turler |= {ue.get_type(p) for p in parcalar} - {None}
        _api("type.assign_type", f, related_objects=parcalar, relating_type=t, should_map_representations=False)
    for eski in sorted(eski_turler, key=lambda t: t.Name or ""):
        if not getattr(eski, "Types", None):                           # kullanılmayan eski pano tipi kalkar; katmanlar kart türünde
            _eski_turu_kaldir(f, eski)

    for s in sinif:
        e = s["e"]
        if s["rol"] == "kart":
            kural = ""
            if "h" in s:
                h = s["h"]
                kural = f"h_turu: {H_TURU_AD[h['tur']]}" + (f" ({h['makas']} {h['uzaklik_cm']:.2f} cm)" if h["makas"] else "")
            ps = _api("pset.add_pset", f, product=e, name=PARCA_SETI)
            _api("pset.edit_pset", f, pset=ps, properties={"KartKodu": s["kart"]["kod"], "PaftaAnahtari": ";".join(pafta_anahtarlari(e, s["kart"])),
                                                        "KatalogKodu": _katalog_kodu(e), "Kural": kural, "Kaynak": kaynak})
        elif s["rol"] == "gorunum":
            ps = _api("pset.add_pset", f, product=e, name=PARCA_SETI)
            _api("pset.edit_pset", f, pset=ps, properties={"Rol": "görünüm", "Asil": s["asil"].Name, "AsilGlobalId": s["asil"].GlobalId,
                                                        "Not": s["neden"], "Kaynak": kaynak})
    cikti_yolu = Path(cikti_yolu)
    cikti_yolu.parent.mkdir(parents=True, exist_ok=True)
    f.write(str(cikti_yolu))
    return sayim(sinif, kartlar, yerlesim, makas_aralik_cm, ifc_yolu, cikti_yolu)


def sayim(sinif: list[dict], kartlar: dict, yerlesim: dict, makas_aralik_cm: float, ifc_yolu: Path, model_yolu: Path) -> dict:
    adet = Counter(s["kart"]["kod"] for s in sinif if s["rol"] == "kart")
    katalog = {}
    for s in sinif:
        if s["rol"] == "kart":
            katalog.setdefault(s["kart"]["kod"], Counter())[_katalog_kodu(s["e"]) or "—"] += 1
    pafta = Counter(a for s in sinif if s["rol"] == "kart" for a in pafta_anahtarlari(s["e"], s["kart"]))
    h = [{"parca": s["e"].Name, "kart": s["kart"]["kod"], "tur": s["h"]["tur"], "makas": s["h"]["makas"], "uzaklik_cm": s["h"]["uzaklik_cm"]}
         for s in sinif if s["rol"] == "kart" and "h" in s]
    return {
        "aciklama": "İE-15 K1 kart sayımı: her parça kartına bağlı; kartsız parça sayılmaz. Paftayla kıyas hakemin işidir (`testler/kimlik/hakem/kiyas.py`).",
        "bugunku_ifc": Path(ifc_yolu).name, "bugunku_ifc_sha256": hashlib.sha256(Path(ifc_yolu).read_bytes()).hexdigest(),
        "kart_modeli": Path(model_yolu).name,
        "kartlar_surumu": kartlar["surum"], "yerlesim_surumu": yerlesim["surum"], "makas_aralik_cm": makas_aralik_cm,
        "kartlar": [{"kod": k["kod"], "ad": k["ad"], "adet": adet[k["kod"]], "katalog_kodlari": dict(sorted(katalog.get(k["kod"], {}).items()))}
                    for k in kartlar["kartlar"]],
        "pafta_anahtarlari": dict(sorted(pafta.items())),
        "h_turu": sorted(h, key=lambda x: x["parca"]),
        "gorunum": [{"parca": s["e"].Name, "asil": s["asil"].Name} for s in sinif if s["rol"] == "gorunum"],
        "bilesen": dict(sorted(Counter(s["asil"].Name for s in sinif if s["rol"] == "bilesen").items())),
        "kartsiz": [{"parca": s["e"].Name, "sinif": s["e"].is_a(), "neden": s["neden"]} for s in sinif if s["rol"] == "kartsiz"],
        "kural_yok": [{"parca": s["e"].Name, "sinif": s["e"].is_a(), "neden": s["neden"]} for s in sinif if s["rol"] == "kural_yok"],
    }


# ----------------------------------------------------------------------------- kart kataloğu (Excel)
def katalog_excel(kartlar: dict, say: dict | None, yol: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    kalin, dolgu = Font(bold=True), PatternFill("solid", fgColor="DDE6F0")

    def sayfa(ws, basliklar, satirlar, genislik):
        ws.append(basliklar)
        for c in ws[1]:
            c.font, c.fill = kalin, dolgu
        for s in satirlar:
            ws.append(s)
        for i, g in enumerate(genislik):
            ws.column_dimensions[chr(65 + i)].width = g
        for satir in ws.iter_rows(min_row=2):
            for c in satir:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2"

    yollar = kartlar["sayim_yollari"]
    sayfa(wb.active, ["Kod", "Ad", "Liste grubu", "Listedeki satırları", "Ölçü", "Birim", "Nerede durur", "Nasıl sayılır",
                      "IFC tür sınıfı (alt tür)", "Paftadaki anahtarı", "Kaynak", "Tarih", "Dayanak"],
          [[k["kod"], k["ad"], k["liste"]["grup"], "; ".join(k["liste"]["satirlar"]), k["olcu"], k["birim"], k["nerede"], yollar[k["sayim"]],
            f"{k['ifc']['sinif']} ({k['ifc']['alt_tur']})",
            "; ".join(k.get("pafta", []) + ([f"{k['pafta_dis_ic']['dis']} / {k['pafta_dis_ic']['ic']}"] if k.get("pafta_dis_ic") else [])) or "—",
            k["kaynak"]["durum"], k["kaynak"]["tarih"], k["kaynak"]["dayanak"]] for k in kartlar["kartlar"]],
          [8, 34, 10, 34, 34, 8, 40, 22, 26, 40, 11, 11, 50])
    wb.active.title = "Kartlar"
    if say:
        sayfa(wb.create_sheet("Sayım"), ["Kod", "Ad", "Adet", "Bugünkü katalog kodları"],
              [[k["kod"], k["ad"], k["adet"], ", ".join(f"{a} × {n}" for a, n in k["katalog_kodlari"].items()) or "—"] for k in say["kartlar"]],
              [8, 40, 8, 50])
        sayfa(wb.create_sheet("H türü"), ["Parça", "Kart", "Tür", "Denk geldiği makas", "Uzaklık (cm)"],
              [[x["parca"], x["kart"], H_TURU_AD[x["tur"]], x["makas"] or "—", x["uzaklik_cm"] if x["uzaklik_cm"] is not None else "—"]
               for x in say["h_turu"]], [24, 8, 18, 18, 12])
        sayfa(wb.create_sheet("Kartsız"), ["Parça", "IFC sınıfı", "Rol", "Neden"],
              [[x["parca"], x["sinif"], "kartsız", x["neden"]] for x in say["kartsiz"]]
              + [[x["parca"], x["sinif"], "kural yok", x["neden"]] for x in say["kural_yok"]]
              + [[x["parca"], "IfcMember", "görünüm", f"sayılan parça {x['asil']}"] for x in say["gorunum"]]
              + [[a, "IfcElementAssembly", "bileşen", f"{n} çubuk birleşimin kartında"] for a, n in say["bilesen"].items()],
              [26, 20, 12, 60])
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(yol))
    return yol


# ----------------------------------------------------------------------------- komut
def uret(ie: dict, klasor: Path, kod: str) -> dict:
    from motor import ifc_uret

    klasor = Path(klasor)
    bugunku = klasor / f"{kod}.ifc"
    ozet = ifc_uret.uret(ie, bugunku)
    say = kart_modeli(bugunku, klasor / f"{kod}_model.ifc")
    say["sema_hatasi"] = {"bugunku_ifc": ozet["sema_hatasi"], "kart_modeli": ifc_uret.ozet(klasor / f"{kod}_model.ifc")["sema_hatasi"]}
    (klasor / f"{kod}_kart_sayim.json").write_text(json.dumps(say, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    katalog_excel(_oku(KARTLAR), say, klasor / f"{kod}_kart_katalogu.xlsx")
    return say


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("is_emri", type=Path)
    ap.add_argument("klasor", type=Path)
    ap.add_argument("--kod", help="çıktı adlarının öneki (varsayılan: İş Emri dosyasının adı)")
    a = ap.parse_args(argv)
    say = uret(_oku(a.is_emri), a.klasor, a.kod or a.is_emri.stem)
    for k in say["kartlar"]:
        if k["adet"]:
            print(f"{k['kod']:6} {k['adet']:4}  {k['ad']}")
    print(f"görünüm {len(say['gorunum'])}, bileşen {sum(say['bilesen'].values())}, kartsız {len(say['kartsiz'])}, kural yok {len(say['kural_yok'])}; "
          f"şema hatası {say['sema_hatasi']}")
    return 1 if say["kural_yok"] or any(say["sema_hatasi"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
