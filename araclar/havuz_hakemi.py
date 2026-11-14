"""İE-38 (D-87) · Aday havuzu hakemi: prefabrik evin İş Emri'si gerçek projesinin proje kartıyla aynı mı.

Lokman, 13 Kasım 2026 21:41 UTC: AIPrefabrik ve AICelik'teki bütün tek katlı projeler bayiye giden aday havuzuna. Bayinin göreceği yanlış
ölçü gerçek hatadır: bir ev havuza ancak Motor'un kurduğu plan, montaj paftasından okunan proje kartıyla (`testler/havuz/proje_kartlari.json`)
aşağıdaki kalemlerde aynıysa girer. Hakem yalnız okur ve bulgu yazar; düzeltme yapmaz (öneren değişir, hakem değişmez).

Kalemler (her biri paftanın 1. sayfasındaki değerle):
- dış ölçü: gövde (W × H) ya da açık mahallerle birlikte (taşan teras ve veranda) en çok 5 cm fark (pafta okuması ve 125,5 köşe kuralı);
- brüt oturum: Motor'un brüt alanı (D-49, `prefabrik_liste.bina_brut_cm2`) + kubbelerin dış yüzden çıkıntısı, en çok 0,5 m² fark;
- oda programı: kartın oda sayısı (yoksa kartın yatak odası sayısı + 1) Motor'un yatak odası sayısıyla; paftada oda adı yoksa
  Lokman'ın karar kartıyla verdiği program (`oda_sayisi_lokman`, sözü ve saatiyle; AP-14, 14 Kasım 2026);
- pencereler: ölçü ölçü aynı adet (kubbenin pencereleri kubbe panolarından);
- dış kapı, iç kapı ve açık mahal sayısı aynı (kartın verandaları + sundurması; AP-07'nin sundurması, 14 Kasım 2026); kat 1.

    python3 araclar/havuz_hakemi.py testler/kor/projeler/AP14/is_emri.json --kart AP-14

Standart hâl (D-91, İE-40): dış duvarındaki özel ölçülü panolar standart panoya (125,5 / 62,75) çekilmiş ev. Lokman, 14 Kasım 2026
10:10:11 UTC karar kartı "Kural denetime girsin": oda, pencere, kapı kaynak evle aynı; dış duvarda özel pano yok (köşedeki 120,5 ve
57,75 özel sayılmaz); ölçü her yönde en çok 62,75 cm değişir. Kalemler:
- kaynak evin İş Emri'si proje kartıyla aynı (normal kip); oda programı, pencereler, kapılar, açık mahal ve kat kartla da aynı;
- odalar kaynak evle aynı: mahaller aynı sırada, adı, türü ve parça sayısı aynı; verandalar aynen (veranda bir oda gibi, D-87);
- pencere ve kapı kaynak evle aynı: açıklıklar aynen (tür, ölçü, oda, duvar, pano); dizilim aynen (kapının ve pencerenin yerini o verir;
  yalnız son pano kuralı değişebilir: kısalt hâli, Lokman 10:01:43); Motor'un yerleştirdiği kapının duvar boyunca aralığı kaynak evdekiyle
  aynı (10:12:22 düzeltmesi 62,75 cm'lik kapı kaymasıydı), pencere duvarıyla en çok 62,75 cm kayar (İş Emri'nin çerçevesinde);
- ölçü her yönde en çok 62,75 cm: "her yönde" iki türlü okunur, ikisi de denetlenir: Motor'un dış ölçüsü x ve y'de ayrı ayrı, ve her
  mahalin ve girintinin her köşesi İş Emri'nin kendi çerçevesinde (dizilimin başlangıç köşesinden) en çok 62,75 cm kayar (mahaller
  `konum_cm` ister);
- dış duvarda özel pano yok: Motor'un planında dış duvarda 125,5 / 62,75 tam ve yarım pano, köşede 5 cm düşülmüş 120,5 / 57,75 ve
  251'lik pencereli pano (iki tam pano; kaynak evde de var) dışında pano yok.
Brüt oturum kıyaslanmaz (ölçüyle değişir; kayıt Motor'un brütünü yazar). Çelikte standart hâl kipi yok (DUR).

    python3 araclar/havuz_hakemi.py testler/havuz/is_emirleri/AP07_STD45.json --kart AP-07 --standart-hal testler/havuz/is_emirleri/AP07.json

Çelik (AICelik): proje kartı yok. Hedef değerler İE-16'da müşteri onay paftasından okunan tanımın adından (`testler/havuz/
celik_kartlari.json`: antet m², oda programı, veranda): genel motor çizer ve doğrular, brüt oturum antet m²'sinden en çok 0,5 m² sapar,
oda programı antette yazılı ve aynı, antet verandalıysa Motor'da da veranda var, tek kat; aynı proje havuzda başka kodla varsa
(ÇP-14 = KT-04) girmez. Veranda bir oda gibi sayılır; verandasız proje de girer (Lokman, 14 Kasım 2026 07:34 UTC; D-87 › Veranda).
Antetteki sayı brüt oturum değilse kart `plan_m2` taşır ve brüt planın ölçtüğü m²'yle kıyaslanır; yalnız Lokman'ın sözüyle
(`plan_m2_kaynagi`; 14 Kasım 2026 12:33:58 UTC kartı "Planın m²'siyle girsin": ÇP-22, ÇP-24, ÇP-25).

    python3 araclar/havuz_hakemi.py testler/celik/projeler/CP18/CP18.json --kart ÇP-18
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
KARTLAR = KOK / "testler" / "havuz" / "proje_kartlari.json"
CELIK_KARTLARI = KOK / "testler" / "havuz" / "celik_kartlari.json"
TOL_OLCU_CM = 5.0
TOL_BRUT_M2 = 0.5
# D-91 (Lokman kartı 14 Kasım 2026 10:10:11 UTC): standart hâlde ölçü her yönde en çok yarım pano değişir; dış duvarda özel pano yok
TOL_STANDART_CM = 62.75
STANDART_PANO_CM = (125.5, 62.75, 251.0)                 # tam pano, yarım pano, 251'lik pencereli pano (iki tam pano)
KOSE_PAYI_CM = (120.5, 57.75)                            # köşede 5 cm düşülmüş tam ve yarım pano: özel sayılmaz (kart)
KAPI_TURLERI = ("dis_kapi", "ic_kapi")
# Standart hâlde dizilim kaynak evle aynı; yalnız son pano kuralı değişebilir (kısalt hâli: yarım pano duvarın sonunda, Lokman 10:01:43)
DIZILIM_SERBEST = ("son_pano",)


def kartlar() -> dict:
    return json.loads(KARTLAR.read_text(encoding="utf-8"))["evler"]


def _olcu(s) -> str:
    n = re.findall(r"\d+(?:[.,]\d+)?", str(s))
    return f"{int(float(n[0].replace(',', '.')))}x{int(float(n[1].replace(',', '.')))}" if len(n) >= 2 else str(s)


def _alan(poly) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def olcum(ie: dict) -> dict:
    """İş Emri → Motor'un planından hakemin okuduğu sayılar (LLM yok; Motor `geometry.kur`)."""
    from motor import geometry as G, prefabrik_liste as PL
    from shapely.geometry import box
    from shapely.ops import unary_union
    plan = G.kur(json.loads(json.dumps(ie)))
    kubbe = sum(_alan(list(k["dis"])) for k in plan.kubbeler) / 1e4
    acik = [m.poly for m in plan.mahaller.values() if m.acik]
    u = unary_union([box(0, 0, plan.W, plan.H)] + acik)
    x0, y0, x1, y1 = u.bounds
    pen = Counter(_olcu(a["olcu"]) for a in ie.get("acikliklar") or [] if a.get("tur") == "pencere")
    for k in plan.kubbeler:
        pen.update(_olcu(p["pencere"]) for p in k.get("panolar") or [] if p.get("pencere"))
    return {"dis_olcu_cm": [round(plan.W, 2), round(plan.H, 2)], "acikla_olcu_cm": [round(x1 - x0, 2), round(y1 - y0, 2)],
            "brut_m2": round(PL.bina_brut_cm2(plan) / 1e4, 2), "kubbe_m2": round(kubbe, 2),
            "yatak_odasi": sum(1 for m in ie.get("mahaller") or [] if m.get("tur") == "yatak_odasi"),
            "pencereler": dict(sorted(pen.items())),
            "dis_kapi": sum(1 for a in ie.get("acikliklar") or [] if a.get("tur") == "dis_kapi"),
            "ic_kapi": sum(1 for a in ie.get("acikliklar") or [] if a.get("tur") == "ic_kapi"),
            "veranda": len(acik), "kat": int((ie.get("yapi") or {}).get("kat_sayisi") or 1)}


def _yakin(a, b) -> float:
    return min(max(abs(a[0] - b[0]), abs(a[1] - b[1])), max(abs(a[0] - b[1]), abs(a[1] - b[0])))


def denetle(ie: dict, kart: dict) -> tuple[list[str], dict]:
    """(bulgular, ölçüm). Bulgu yoksa ev havuza girebilir."""
    o = olcum(ie)
    b: list[str] = []
    ko = kart["dis_olcu_cm"]
    fark = min(_yakin(o["dis_olcu_cm"], ko), _yakin(o["acikla_olcu_cm"], ko))
    if fark > TOL_OLCU_CM:
        b.append(f"dış ölçü: Motor {o['dis_olcu_cm'][0]:g} × {o['dis_olcu_cm'][1]:g} cm (açık mahallerle {o['acikla_olcu_cm'][0]:g} × "
                 f"{o['acikla_olcu_cm'][1]:g}), pafta {ko[0]:g} × {ko[1]:g} cm; fark {fark:.2f} cm > {TOL_OLCU_CM:g}")
    brut = o["brut_m2"] + o["kubbe_m2"]
    if kart.get("brut_oturum_m2") is not None and abs(brut - kart["brut_oturum_m2"]) > TOL_BRUT_M2:
        b.append(f"brüt oturum: Motor {brut:.2f} m² (kubbe {o['kubbe_m2']:.2f} dahil), pafta {kart['brut_oturum_m2']:g} m²; "
                 f"fark {brut - kart['brut_oturum_m2']:+.2f} > {TOL_BRUT_M2:g}")
    oda = str(kart.get("oda_sayisi") or (kart.get("oda_sayisi_lokman") or {}).get("deger") or "").strip()   # paftada yoksa Lokman'ın kartı
    m = re.fullmatch(r"(\d+)\+1", oda)
    beklenen_yatak = int(m.group(1)) if m else (kart.get("yatak_odasi") if not oda else None)
    if beklenen_yatak is None or beklenen_yatak != o["yatak_odasi"]:
        b.append(f"oda programı: Motor {o['yatak_odasi']}+1, pafta \"{oda or '?'}\" (yatak odası {kart.get('yatak_odasi')})")
    kp = Counter()
    for s, n in (kart.get("acikliklar") or {}).items():
        kp[_olcu(s)] += int(n)
    if Counter(o["pencereler"]) != kp:
        eksik, fazla = kp - Counter(o["pencereler"]), Counter(o["pencereler"]) - kp
        b.append(f"pencereler: Motor'da eksik {dict(eksik) or '-'}, fazla {dict(fazla) or '-'}")
    for alan, ka in (("dis_kapi", "dis_kapi_adedi"), ("ic_kapi", "ic_kapi_adedi")):
        if kart.get(ka) is not None and int(kart[ka]) != o[alan]:
            b.append(f"{alan.replace('_', ' ')}: Motor {o[alan]}, pafta {kart[ka]}")
    if kart.get("veranda_adedi") is not None:                                     # sundurma da açık mahal (Motor'da taşan veranda)
        acik = int(kart["veranda_adedi"]) + int(kart.get("sundurma_adedi") or 0)
        if acik != o["veranda"]:
            ek = f" + sundurma {kart['sundurma_adedi']}" if kart.get("sundurma_adedi") else ""
            b.append(f"veranda: Motor {o['veranda']}, pafta {kart['veranda_adedi']}{ek}")
    if int(kart.get("kat_adedi") or 1) != 1 or o["kat"] != 1:
        b.append("kat: havuz yalnız tek kat")
    return b, o


def dis_ozel_panolar(ie: dict) -> list[dict]:
    """Motor'un planında dış duvardaki standart dışı panolar (D-91): duvar (yön ve eksen, cm) ve boy."""
    from motor import geometry as G
    plan = G.kur(json.loads(json.dumps(ie)))
    return [{"duvar": f"{p.duvar.yon} {p.duvar.c:g}", "boy": round(p.boy, 2)} for p in plan.panolar
            if p.duvar.tur == "dis" and not any(abs(p.boy - s) < 0.05 for s in STANDART_PANO_CM + KOSE_PAYI_CM)]


def _kaynakla_ayni(ie: dict, kaynak_ie: dict) -> list[str]:
    """Standart hâlin odaları, açıklıkları ve verandaları kaynak evinkiyle aynı; her köşe en çok 62,75 cm kayar (D-91)."""
    b: list[str] = []
    oda = [(m.get("ad"), m.get("tur"), len(m.get("konum_cm") or [])) for m in ie.get("mahaller") or []]
    oda_k = [(m.get("ad"), m.get("tur"), len(m.get("konum_cm") or [])) for m in kaynak_ie.get("mahaller") or []]
    if oda != oda_k:
        b.append(f"odalar: kaynak evle aynı değil ({oda_k} → {oda})")
    if (ie.get("acikliklar") or []) != (kaynak_ie.get("acikliklar") or []):
        fark = [a for a in ie.get("acikliklar") or [] if a not in (kaynak_ie.get("acikliklar") or [])]
        b.append(f"açıklıklar: kaynak evle aynı değil (farklı: {fark or 'sıra ya da eksik'})")
    if (ie.get("verandalar") or []) != (kaynak_ie.get("verandalar") or []):
        b.append("veranda: verandalar kaynak evle aynı değil")
    if any("konum_cm" not in m for m in (ie.get("mahaller") or []) + (kaynak_ie.get("mahaller") or [])):
        return b + ["hat: standart hâl kipi mahallerin konum_cm'ini ister (köşelerin kayması denetlenemedi)"]
    kayan = []
    if oda == oda_k:
        for m, mk in zip(ie["mahaller"], kaynak_ie["mahaller"]):
            for r, rk in zip(m["konum_cm"], mk["konum_cm"]):
                kayan += [(m["ad"], rk[i], r[i]) for i in range(4) if abs(float(r[i]) - float(rk[i])) > TOL_STANDART_CM]
    g, gk = ie.get("girintiler") or [], kaynak_ie.get("girintiler") or []
    if len(g) != len(gk):
        b.append(f"hat: girinti sayısı kaynak evle aynı değil ({len(gk)} → {len(g)})")
    for r, rk in zip(g, gk):
        kayan += [("girinti", rk[i], r[i]) for i in range(4) if abs(float(r[i]) - float(rk[i])) > TOL_STANDART_CM]
    if kayan:
        b.append("hat: köşe 62,75 cm'den çok kaydı: " + ", ".join(f"{ad} {e:g} → {y:g}" for ad, e, y in kayan))
    diz = {k: v for k, v in ((ie.get("yapi") or {}).get("dizilim") or {}).items() if k not in DIZILIM_SERBEST}
    diz_k = {k: v for k, v in ((kaynak_ie.get("yapi") or {}).get("dizilim") or {}).items() if k not in DIZILIM_SERBEST}
    if diz != diz_k:
        b.append("dizilim: kaynak evle aynı değil (" + ", ".join(sorted(k for k in set(diz) | set(diz_k) if diz.get(k) != diz_k.get(k)))
                 + "); kapının ve pencerenin yerini dizilim verir")
    b += _aciklik_yeri_ayni(ie, kaynak_ie)
    return b


def acikliklarin_yeri(ie: dict) -> list[dict]:
    """Motor'un panoya yerleştirdiği açıklıklar İş Emri'nin çerçevesinde (dizilimin başlangıç köşesinden, cm): tür, ölçü, duvar türü,
    duvar yönü, duvarın hattı ve duvar boyunca pano aralığı. arka-sol başlangıçta y arkadan ölçülür (Motor'un `ayna_y`'si)."""
    from motor import geometry as G
    plan = G.kur(json.loads(json.dumps(ie)))
    ayna_y = ((ie.get("yapi") or {}).get("dizilim") or {}).get("baslangic", "on-sol") == "arka-sol"
    y = (lambda v: plan.H - v) if ayna_y else (lambda v: v)
    yer = []
    for p in plan.panolar:
        if p.acilim is None:
            continue
        a = p.acilim
        if p.duvar.yon == "x":                                 # yatay duvar: hattı y'de, aralığı x'te
            hat, a0, a1 = y(p.duvar.c), p.a0, p.a1
        else:                                                 # düşey duvar: hattı x'te, aralığı y'de
            hat, a0, a1 = p.duvar.c, min(y(p.a0), y(p.a1)), max(y(p.a0), y(p.a1))
        yer.append({"tur": a.tur, "olcu": str(getattr(a, "olcu", "")), "duvar_tur": p.duvar.tur, "yon": p.duvar.yon,
                    "hat": round(hat, 2), "a0": round(a0, 2), "a1": round(a1, 2)})
    return sorted(yer, key=lambda d: (d["tur"], d["olcu"], d["duvar_tur"], d["yon"], d["hat"], d["a0"]))


def _aciklik_yeri_ayni(ie: dict, kaynak_ie: dict) -> list[str]:
    """Motor'un yerleştirdiği kapı ve pencere kaynak evle aynı yerde (D-91): kapının duvar boyunca aralığı aynen (en çok 0,05 cm;
    "kapı kaynak evle aynı", Lokman'ın 10:12:22 düzeltmesi 62,75 cm'lik kapı kaymasıydı); pencerenin hattı ve aralığı en çok 62,75 cm kayar
    (oda ortasındaki pencere duvarla kayar; 11:18:03 onaylı çizimde salonun ön penceresi 62,75 cm kaydı)."""
    def grup(yer):
        g: dict = {}
        for d in yer:
            g.setdefault((d["tur"], d["olcu"], d["duvar_tur"], d["yon"]), []).append(d)
        return g
    g, gk = grup(acikliklarin_yeri(ie)), grup(acikliklarin_yeri(kaynak_ie))
    b = []
    for anahtar in sorted(set(g) | set(gk)):
        yeni, eski = g.get(anahtar, []), gk.get(anahtar, [])
        ad = f"{anahtar[0]} {anahtar[1]} ({anahtar[2]}, {anahtar[3]} duvarı)"
        if len(yeni) != len(eski):
            b.append(f"açıklık yeri: {ad} kaynak evde {len(eski)}, standart hâlde {len(yeni)}")
            continue
        for d, dk in zip(yeni, eski):
            if anahtar[0] in KAPI_TURLERI:
                if abs(d["a0"] - dk["a0"]) > 0.05 or abs(d["a1"] - dk["a1"]) > 0.05:
                    b.append(f"açıklık yeri: {ad} {dk['a0']:g}–{dk['a1']:g} → {d['a0']:g}–{d['a1']:g} (kapı kaynak evle aynı yerde kalır)")
            elif max(abs(d[k] - dk[k]) for k in ("hat", "a0", "a1")) > TOL_STANDART_CM:
                b.append(f"açıklık yeri: {ad} hat {dk['hat']:g} → {d['hat']:g}, {dk['a0']:g}–{dk['a1']:g} → {d['a0']:g}–{d['a1']:g} "
                         f"(62,75 cm'den çok)")
    return b


def denetle_standart(ie: dict, kart: dict, kaynak_ie: dict) -> tuple[list[str], dict]:
    """(bulgular, ölçüm) standart hâl için (D-91). Kaynak ev (`kaynak_ie`, havuzdaki İş Emri'si) proje kartıyla aynı (normal kip);
    standart hâlin oda, pencere, kapı, açık mahal ve kat kalemleri kartla aynı; odalar, açıklıklar, verandalar ve dizilim (son pano hariç)
    kaynak evle aynı; Motor'un yerleştirdiği kapı aynı yerde, pencere en çok 62,75 cm kaymış; Motor'un
    dış ölçüsü x ve y'de ayrı ayrı ve her köşe kaynak evinkinden en çok 62,75 cm farklı; dış duvarda özel pano yok. Brüt kıyaslanmaz."""
    kaynak_b, ko = denetle(kaynak_ie, kart)
    bulgular, o = denetle(ie, kart)
    b = [f"kaynak ev: proje kartı hakemi geçmedi ({'; '.join(kaynak_b)})"] if kaynak_b else []
    fark = [round(abs(a - k), 2) for a, k in zip(o["dis_olcu_cm"], ko["dis_olcu_cm"])]
    if max(fark) > TOL_STANDART_CM:
        b.append(f"dış ölçü: Motor {o['dis_olcu_cm'][0]:g} × {o['dis_olcu_cm'][1]:g} cm, kaynak ev {ko['dis_olcu_cm'][0]:g} × "
                 f"{ko['dis_olcu_cm'][1]:g} cm; fark {fark[0]:g} / {fark[1]:g} cm > {TOL_STANDART_CM:g} (standart hâl)")
    b += _kaynakla_ayni(ie, kaynak_ie)
    b += [x for x in bulgular if not x.startswith(("dış ölçü:", "brüt oturum:"))]
    ozel = dis_ozel_panolar(ie)
    if ozel:
        b.append("dış duvarda özel pano: " + ", ".join(f"{p['duvar']} {p['boy']:g}" for p in ozel))
    return b, {**o, "dis_ozel_pano": len(ozel)}


def celik_kartlari() -> dict:
    return json.loads(CELIK_KARTLARI.read_text(encoding="utf-8"))["evler"]


def celik_olcum(tanim_yolu: Path) -> dict:
    """Yapı Tanımı → genel motorun çizdiği ve doğruladığı plandan sayılar (perspektifsiz; LLM yok)."""
    import tempfile
    from motor.genel import uret as U
    from motor.genel.bayi_gorseli import oda_programi
    t = json.loads(Path(tanim_yolu).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        m = U.uret(Path(tanim_yolu), Path(tmp), is_emri_no=None, revizyon=None, set_yolu=None, yontem="panel", perspektif=False, bayi=True,
                   kaynak="havuz hakemi")
        v = json.loads((Path(tmp) / "validation.json").read_text(encoding="utf-8"))
        g = json.loads((Path(tmp) / f"{U.kod_govde(t)}_girdi.json").read_text(encoding="utf-8"))
    vm = g.get("veranda_m2") or 0
    veranda = float(vm.get("net") or vm.get("brut") or 0) if isinstance(vm, dict) else float(vm)
    return {"gecti": bool(m.get("passed")), "hatalar": v.get("errors") or [], "bayi_gorseli": bool(m.get("bayi_gorsel")),
            "oturum_m2": round(float(g.get("oturum_m2") or g["bina_m2"]), 2), "veranda_m2": round(veranda, 2), "oda_programi": oda_programi(t),
            "kat": 1 if str(t.get("kat", "zemin")) in ("zemin", "1") else 2}


def celik_denetle(tanim_yolu: Path, kart: dict) -> tuple[list[str], dict]:
    """(bulgular, ölçüm). Bulgu yoksa çelik proje havuza girebilir."""
    o = celik_olcum(tanim_yolu)
    b: list[str] = []
    if kart.get("havuzda"):
        b.append(f"havuzda: aynı proje {kart['havuzda']} koduyla havuzda")
    if not o["gecti"] or not o["bayi_gorseli"]:
        b.append(f"motor: genel motor doğrulaması geçmedi ya da bayi görseli yok ({o['hatalar']})")
    # Antetteki sayı brüt oturum değilse (net, planla çelişen, yuvarlanmış) kart `plan_m2` taşır: planın ölçtüğü m², yalnız Lokman'ın
    # sözüyle (`plan_m2_kaynagi`; 14 Kasım 2026 12:33:58 kartı "Planın m²'siyle girsin", D-87). Sınır aynı; `antet_m2` paftadaki sayı kalır.
    ad, hedef = ("plan", kart["plan_m2"]) if kart.get("plan_m2") is not None else ("antet", kart.get("antet_m2"))
    if ad == "plan" and not kart.get("plan_m2_kaynagi"):
        b.append("brüt oturum: plan m²'sinin kaynağı (Lokman'ın sözü) kartta yok")
    elif hedef is None or abs(o["oturum_m2"] - hedef) > TOL_BRUT_M2:
        b.append(f"brüt oturum: Motor {o['oturum_m2']:.2f} m², {ad} {hedef} m²; en çok {TOL_BRUT_M2:g}")
    if not kart.get("oda_programi"):
        b.append(f"oda programı: antette yok (Motor {o['oda_programi']}); doğrulanamadı")
    elif kart["oda_programi"] != o["oda_programi"]:
        b.append(f"oda programı: Motor {o['oda_programi']}, antet {kart['oda_programi']}")
    if kart.get("veranda") and o["veranda_m2"] <= 0:                           # veranda bir oda gibi: antette varsa Motor'da da olmalı;
        b.append("veranda: antet verandalı, Motor'da veranda yok")               # verandasız proje de girer (Lokman, 14 Kasım 2026; D-87)
    if int(kart.get("kat_adedi") or 1) != 1 or o["kat"] != 1:
        b.append("kat: havuz yalnız tek kat")
    return b, o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", help="prefabrik İş Emri ya da çelik Yapı Tanımı"); ap.add_argument("--kart", required=True, help="proje kodu (AP-14 ya da ÇP-18)")
    ap.add_argument("--standart-hal", metavar="KAYNAK", default=None,
                    help="prefabrik: dış duvardaki özel panoları standarda çekilmiş ev; KAYNAK kaynak evin İş Emri'si (D-91)")
    a = ap.parse_args(argv)
    if a.kart.upper().startswith(("ÇP", "CP")):
        if a.standart_hal:
            print("DUR: standart hâl kipi yalnız prefabrikte (D-91); çelikte yok"); return 2
        kod = "ÇP-" + re.sub(r"\D", "", a.kart)[-2:].zfill(2)
        kart = celik_kartlari().get(kod)
        if kart is None:
            print(f"DUR: {kod} için çelik hedef değeri yok ({CELIK_KARTLARI.relative_to(KOK)})"); return 2
        bulgular, o = celik_denetle(Path(a.is_emri), kart)
        print(json.dumps(o, ensure_ascii=False))
        gecti = "GEÇTİ: antetle aynı" + (" (brüt planın m²'siyle, Lokman'ın sözü)" if kart.get("plan_m2") is not None else "")
        print(gecti if not bulgular else "KALDI:\n- " + "\n- ".join(bulgular))
        return 0 if not bulgular else 1
    kart = kartlar().get(a.kart.upper())
    if kart is None:
        print(f"DUR: {a.kart} için proje kartı yok ({KARTLAR.relative_to(KOK)})"); return 2
    ie = json.loads(Path(a.is_emri).read_text(encoding="utf-8"))
    bulgular, o = (denetle_standart(ie, kart, json.loads(Path(a.standart_hal).read_text(encoding="utf-8"))) if a.standart_hal
                   else denetle(ie, kart))
    print(json.dumps(o, ensure_ascii=False))
    gecti = "GEÇTİ: standart hâl, kaynak evin proje kartıyla aynı (D-91)" if a.standart_hal else "GEÇTİ: proje kartıyla aynı"
    print(gecti if not bulgular else "KALDI:\n- " + "\n- ".join(bulgular))
    return 0 if not bulgular else 1


if __name__ == "__main__":
    sys.exit(main())
