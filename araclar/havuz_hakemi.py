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

Silme hâli (BK-31; D-92 › Havuza uygulama): tek özel pano kuralı (D-92, "dizilim_sonu") dizilimin sonunda 30 cm'den kısa parça bırakan
evde parça silinmiş, o cephenin dış duvarı parça kadar içeri kaymış ev. Lokman, 14 Kasım 2026 UTC: kart 19:39:46 "Kısa parça silinsin";
ev kartları "Doğru, yanına eklensin" (85 m² 20:05:33, seçenek metni "Kayıt denetimine silme kalemi eklenir."; 60 m² 20:09:12; 70 m²
20:14:50). Standart hâl kipi gevşemez; ayrı kalem. Kalemler (Motor'un planından; kaynak ev anahtarla kurulur):
- kaynak ev proje kartıyla aynı (normal kip); kartın oda, pencere, kapı, açık mahal ve kat kalemleri silinmiş hâlde de aynı;
- silinmiş hâlde `yapi.dizilim.tek_ozel_pano` "dizilim_sonu" (kısa parça bu kuralın kalanıdır); dizilim öteki anahtarlarıyla aynen;
- dış ölçü her eksende 0 ile 30 cm arası küçülür (en az birinde); kart ölçüsüyle fark silinen kadar (normal kipin 5 cm'si içinde);
- duvarlar yerinde, yalnız dizilim sonundaki cephenin bandındaki (dış yüzden bir dış duvar kalınlığı) uçlar silinen kadar kayar; küçülen her
  eksende en az bir duvarda yalnız dizilim sonundaki kısa açıklıksız pano düşer (son pano köşe ya da T payını alabilir); kısa parçası
  olmayan kısalan duvarı (veranda kenarı) Motor yeniden dizer, açıklıklı ve karkaslı panoları aynı kalır; küçülmeyen duvarların pano dizisi
  aynı; silinmiş hâlde 30 cm'den kısa açıklıksız pano kalmaz;
- kapı ve pencere yerinde (duvar boyunca aralığı aynı; kayan cephedeki açıklığın hattı duvarla kayar); açıklıklar aynen (oda ortasındaki
  açıklığa bugünkü panosu yazılabilir, yeri aynı kalır);
- oda ve girinti köşeleri yalnız o bantta silinen kadar kayar; veranda (açık mahal) ve dikmesi yalnız Lokman'ın o evin kartıyla kısalır
  (`--veranda-sozu`, söz ve saat kayda yazılır); öteki alanlar (çatı, açık sınırlar, ek akslar) aynen.
30 cm sınırı varsayımdır (yedi evde parça 9,5–27 cm; BK-31 › Varsayımlar). Brüt oturum kıyaslanmaz (kayıt Motor'un brütünü yazar).

    python3 araclar/havuz_hakemi.py testler/havuz/is_emirleri/PA12_SILME.json --kart AP-11 --silme-hali is_emri/adaylar/PA12.json

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
# BK-31 (silme hâli; Lokman kartları 14 Kasım 2026 19:39:46 "Kısa parça silinsin", 20:05:33 ve 20:09:12 "Doğru, yanına eklensin"):
# kısa parça = tek özel pano kuralının (D-92) dizilim sonunda bıraktığı 30 cm'den kısa parça (yedi evde 9,5–27 cm; 30 sınırı varsayım, BK-31)
TOL_SILME_CM = 30.0
TEK_OZEL_PANO = "dizilim_sonu"
YER_TOL_CM = 0.05
SILME_KIMLIK = ("is_emri_no", "revizyon", "talep", "varsayimlar", "eksikler")   # kimlik ve talep yazıları: aday kaydı yeniden yazar


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


def _sayi(x):
    """Kıyas için sayı biçimi: 5 ile 5.0 aynı (kayan yazımı İş Emri'ni değiştirmez)."""
    if isinstance(x, bool) or not isinstance(x, (int, float, list, dict)):
        return x
    if isinstance(x, (int, float)):
        return round(float(x), 3)
    return [_sayi(v) for v in x] if isinstance(x, list) else {k: _sayi(v) for k, v in x.items()}


def _anahtarli(ie: dict) -> dict:
    ie = json.loads(json.dumps(ie))
    ie.setdefault("yapi", {}).setdefault("dizilim", {})["tek_ozel_pano"] = TEK_OZEL_PANO
    return ie


def duvar_dizileri(ie: dict) -> dict:
    """Motor'un planı İş Emri'nin çerçevesinde (dizilimin başlangıç köşesinden; arka-solda y arkadan, dizilim sonu her eksende büyük uç):
    dış ölçü ve her duvarın türü, yönü, hattı, aralığı ve panoları duvar boyunca sırayla (boy ve açıklıklı ya da karkaslı mı). Yalnız okur."""
    from motor import geometry as G
    plan = G.kur(json.loads(json.dumps(ie)))
    ayna_y = ((ie.get("yapi") or {}).get("dizilim") or {}).get("baslangic", "on-sol") == "arka-sol"
    y = (lambda v: plan.H - v) if ayna_y else (lambda v: v)
    duvarlar = []
    for d in plan.duvarlar:                                   # Duvar.a0/a1 Motor'un son kurduğu ızgaradan: kurulumdan hemen sonra okunur
        aralik = (lambda u, v: (u, v)) if d.yon == "x" else (lambda u, v: tuple(sorted((y(u), y(v)))))
        a0, a1 = aralik(d.a0, d.a1)
        panolar = sorted((round(aralik(p.a0, p.a1)[0], 2), round(p.boy, 2), bool(p.aciklar or p.karkasli)) for p in d.panolar)
        duvarlar.append({"tur": d.tur, "yon": d.yon, "c": round(y(d.c) if d.yon == "x" else d.c, 2), "a0": round(a0, 2), "a1": round(a1, 2),
                         "panolar": [(b, sabit) for _, b, sabit in panolar]})
    return {"W": round(plan.W, 2), "H": round(plan.H, 2), "duvarlar": duvarlar}


def _duvar_adi(d: dict) -> str:
    return f"{d['tur']} {d['yon']} {d['c']:g} ({d['a0']:g}–{d['a1']:g})"


def _kisa_parca_dustu(dk: dict, ds: dict, kisalma: float) -> float | None:
    """Kısalan duvarda yalnız dizilim sonundaki kısa parça düştü mü (BK-31): öteki panolar aynı, son pano köşe ya da T payını alabilir
    (ör. 125,5 → 120,5); açıklıklı son pano boyunu korur. Düştüyse parçanın boyu, yoksa None."""
    pk, ps = dk["panolar"], ds["panolar"]
    if not (len(pk) >= 2 and pk[-1][0] < TOL_SILME_CM and not pk[-1][1] and len(ps) == len(pk) - 1):
        return None
    pay = round(pk[-2][0] + pk[-1][0] - kisalma - ps[-1][0], 2)
    if ps[:-1] == pk[:-2] and ps[-1][1] == pk[-2][1] and abs(pay) <= YER_TOL_CM and (not pk[-2][1] or abs(ps[-1][0] - pk[-2][0]) <= YER_TOL_CM):
        return pk[-1][0]
    return None


def denetle_silme(ie: dict, kart: dict, kaynak_ie: dict, veranda_sozu: str | None = None) -> tuple[list[str], dict]:
    """(bulgular, ölçüm) silme hâli için (BK-31; D-92 › Havuza uygulama). Kaynak ev tek özel pano anahtarıyla (D-92, "dizilim_sonu") kurulunca
    dizilimin sonunda kalan 30 cm'den kısa parça silinmiş: o cephenin dış duvarı parça kadar içeri kaymış. Kalemler (Motor'un planından):
    kaynak ev proje kartıyla aynı (normal kip); silinmiş hâlde anahtar "dizilim_sonu"; dış ölçü her eksende 0 ile 30 cm arası küçülür (en az
    birinde); kısalan her duvarda yalnız dizilim sonundaki kısa açıklıksız pano düşer, öteki duvarların pano dizisi aynı; kapı ve pencere
    yerinde (kayan cephedeki açıklığın hattı duvarla kayar); oda ve girinti köşeleri yalnız kayan cephenin bandında silinen kadar kayar;
    veranda (açık mahal) kısalmaz, Lokman'ın ev kartıyla kısalır (`veranda_sozu`); açıklıklar, verandalar, dikmeler, çatı ve dizilim aynen;
    kartın oda, pencere, kapı, açık mahal ve kat kalemleri aynı; dış ölçü kartla silinen kadar farklı (normal kipin 5 cm'si içinde);
    silinmiş hâlde 30 cm'den kısa açıklıksız pano kalmaz. Brüt oturum kıyaslanmaz (ölçüyle küçülür; kayıt Motor'un brütünü yazar)."""
    from motor import geometry as G
    kaynak_b, _ = denetle(kaynak_ie, kart)
    bulgular, o = denetle(ie, kart)
    b = [f"kaynak ev: proje kartı hakemi geçmedi ({'; '.join(kaynak_b)})"] if kaynak_b else []
    b += [x for x in bulgular if not x.startswith(("dış ölçü:", "brüt oturum:"))]
    diz = dict(((ie.get("yapi") or {}).get("dizilim") or {}))
    if diz.get("tek_ozel_pano") != TEK_OZEL_PANO:
        b.append(f"dizilim: silme hâli tek özel pano kuralıyla kurulur (yapi.dizilim.tek_ozel_pano \"{TEK_OZEL_PANO}\"); kısa parça bu kuralın "
                 f"dizilim sonunda bıraktığı parçadır (D-92)")
    kaynak = _anahtarli(kaynak_ie)
    k, s = duvar_dizileri(kaynak), duvar_dizileri(ie)
    dx, dy = round(k["W"] - s["W"], 2), round(k["H"] - s["H"], 2)
    olc = {**o, "kaynak_dis_olcu_cm": [k["W"], k["H"]], "silinen_cm": [dx, dy], "silinen": [], "yeniden_dizilen": [], "veranda_kisalan": []}
    silinen_eksen: set = set()
    if not (0 <= dx < TOL_SILME_CM and 0 <= dy < TOL_SILME_CM and (dx > 0 or dy > 0)):
        return b + [f"dış ölçü: kaynak {k['W']:g} × {k['H']:g} cm, silinmiş {s['W']:g} × {s['H']:g} cm; silinen {dx:g} / {dy:g} cm (her "
                    f"eksende 0 ile {TOL_SILME_CM:g} cm arası küçülür, en az birinde)"], olc
    t = float(((kaynak.get("yapi") or {}).get("duvar_kalinligi_cm") or {}).get("dis") or 10)
    sx = lambda v: round(v - dx, 2) if v >= k["W"] - t - 0.5 else v     # dizilim sonundaki cephenin bandı (dış yüzden bir dış duvar)
    sy = lambda v: round(v - dy, 2) if v >= k["H"] - t - 0.5 else v     # silinen kadar içeri; öteki değerler yerinde
    yakin = lambda u, v: abs(u - v) <= YER_TOL_CM

    # duvarlar ve pano dizileri
    serbest = list(s["duvarlar"])
    for dk in k["duvarlar"]:
        bek = (sy(dk["c"]), sx(dk["a0"]), sx(dk["a1"])) if dk["yon"] == "x" else (sx(dk["c"]), sy(dk["a0"]), sy(dk["a1"]))
        ds = next((d for d in serbest if (d["tur"], d["yon"]) == (dk["tur"], dk["yon"]) and all(map(yakin, (d["c"], d["a0"], d["a1"]), bek))), None)
        if ds is None:
            b.append(f"duvar: kaynak evin {_duvar_adi(dk)} duvarı silinmiş hâlde yerinde değil (yalnız kayan cephe silinen kadar kayar)")
            continue
        serbest.remove(ds)
        kisalma = round((dk["a1"] - dk["a0"]) - (ds["a1"] - ds["a0"]), 2)
        if abs(kisalma) <= YER_TOL_CM:
            if ds["panolar"] != dk["panolar"]:
                b.append(f"pano dizisi: duvar {_duvar_adi(dk)} değişti ({[x for x, _ in dk['panolar']]} → {[x for x, _ in ds['panolar']]})")
            continue
        boy = _kisa_parca_dustu(dk, ds, kisalma)
        if boy is not None:
            olc["silinen"].append({"duvar": f"{dk['tur']} {dk['yon']} {dk['c']:g}", "boy": boy})
            silinen_eksen.add(dk["yon"])
        elif [p for p in ds["panolar"] if p[1]] != [p for p in dk["panolar"] if p[1]]:
            b.append(f"pano dizisi: duvar {_duvar_adi(dk)} {kisalma:g} cm kısaldı, açıklıklı ya da karkaslı pano değişti "
                     f"({[x for x, _ in dk['panolar']]} → {[x for x, _ in ds['panolar']]})")
        else:                                                 # kısa parçası olmayan kısalan duvar (veranda kenarı): Motor anahtarla yeniden dizer
            olc["yeniden_dizilen"].append({"duvar": f"{dk['tur']} {dk['yon']} {dk['c']:g}", "once": [x for x, _ in dk["panolar"]],
                                           "sonra": [x for x, _ in ds["panolar"]]})
    b += [f"duvar: silinmiş hâlde kaynak evde olmayan duvar {_duvar_adi(d)}" for d in serbest]
    for yon, sil in (("x", dx), ("y", dy)):
        if sil > 0 and yon not in silinen_eksen:
            b.append(f"silinen: {sil:g} cm hiçbir {yon} duvarında dizilim sonundaki kısa parça değil (silinen yalnız kısa parça kadar)")
    kisa = [f"{_duvar_adi(d)} {x:g} cm" for d in s["duvarlar"] for x, sabit in d["panolar"] if x < TOL_SILME_CM and not sabit]
    if kisa:
        b.append("kısa parça kaldı: " + ", ".join(kisa) + " (Lokman, 19:39:46 kartı \"Kısa parça silinsin\")")

    # kapı ve pencere: duvar boyunca aralığı aynı; kayan cephedeki açıklığın hattı duvarla kayar
    yer_k, yer_s = acikliklarin_yeri(kaynak), acikliklarin_yeri(ie)
    bek_yer = sorted(({**d, "hat": sy(d["hat"]) if d["yon"] == "x" else sx(d["hat"]),
                       "a0": sx(d["a0"]) if d["yon"] == "x" else sy(d["a0"]), "a1": sx(d["a1"]) if d["yon"] == "x" else sy(d["a1"])}
                      for d in yer_k), key=lambda d: (d["tur"], d["olcu"], d["duvar_tur"], d["yon"], d["hat"], d["a0"]))
    if len(bek_yer) != len(yer_s) or any((d["tur"], d["olcu"], d["duvar_tur"], d["yon"]) != (e["tur"], e["olcu"], e["duvar_tur"], e["yon"])
                                         or not all(yakin(d[x], e[x]) for x in ("hat", "a0", "a1")) for d, e in zip(bek_yer, yer_s)):
        fark = [f"{d['tur']} {d['olcu']} ({d['duvar_tur']}, {d['yon']} duvarı) hat {d['hat']:g}, {d['a0']:g}–{d['a1']:g}"
                for d in bek_yer if not any(all(d[x] == e[x] for x in ("tur", "olcu", "duvar_tur", "yon"))
                                            and all(yakin(d[x], e[x]) for x in ("hat", "a0", "a1")) for e in yer_s)]
        b.append(f"açıklık yeri: kapı ve pencere kaynak evdeki yerinde değil (beklenen: {fark or 'sayı farkı'})")

    # odalar, verandalar ve girintiler: köşe yalnız kayan cephenin bandında silinen kadar kayar
    mk_, ms_ = kaynak_ie.get("mahaller") or [], ie.get("mahaller") or []
    if [(m.get("ad"), m.get("tur"), len(m.get("konum_cm") or [])) for m in mk_] != [(m.get("ad"), m.get("tur"), len(m.get("konum_cm") or []))
                                                                               for m in ms_]:
        b.append("odalar: kaynak evle aynı değil (ad, tür, parça sayısı)")
    else:
        for mk, ms in zip(mk_, ms_):
            if _sayi({x: v for x, v in mk.items() if x != "konum_cm"}) != _sayi({x: v for x, v in ms.items() if x != "konum_cm"}):
                b.append(f"odalar: {mk.get('ad')} kaynak evle aynı değil (konum dışında)")
            bek_k = [[sx(r[0]), sy(r[1]), sx(r[2]), sy(r[3])] for r in _sayi(mk.get("konum_cm") or [])]
            if any(not all(map(yakin, r, rb)) for r, rb in zip(_sayi(ms.get("konum_cm") or []), bek_k)):
                b.append(f"oda köşesi: {mk.get('ad')} {mk.get('konum_cm')} → {ms.get('konum_cm')} (yalnız kayan cephe silinen kadar kayar)")
            elif bek_k != _sayi(mk.get("konum_cm") or []) and mk.get("tur") in G.ACIK_MAHAL_TURLERI:
                if veranda_sozu and veranda_sozu.strip():
                    olc["veranda_kisalan"].append(mk.get("ad"))
                else:
                    b.append(f"veranda: {mk.get('ad')} silinen kadar kısalır; veranda kısalması yalnız Lokman'ın ev kartıyla (--veranda-sozu)")
    g, gk = _sayi(ie.get("girintiler") or []), _sayi(kaynak_ie.get("girintiler") or [])
    if len(g) != len(gk) or any(not all(map(yakin, r, [sx(rk[0]), sy(rk[1]), sx(rk[2]), sy(rk[3])])) for r, rk in zip(g, gk)):
        b.append(f"girinti: kaynak evle aynı değil ya da kayan cepheden başka yerde kaydı ({gk} → {g})")

    # açıklıklar aynen; kaynakta panosu yazılmamış (oda ortası) açıklığa bugünkü panosu yazılabilir: yerini yukarıdaki kalem denetler
    ak, as_ = kaynak_ie.get("acikliklar") or [], ie.get("acikliklar") or []
    if len(ak) != len(as_) or any(_sayi({x: v for x, v in a.items() if x in e or x != "pano"}) != _sayi(e) for a, e in zip(as_, ak)):
        b.append("açıklıklar: kaynak evle aynı değil (tür, ölçü, oda, duvar, pano)")

    # dikmeler (gerçek çerçevede, ön y = 0): verandanın kayan cephedeki dikmesi veranda ile silinen kadar kayar, öteki dikmeler yerinde
    ayna_y = diz.get("baslangic", "on-sol") == "arka-sol"
    def dikme_bek(p):
        if not (isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)):
            return p
        yf = k["H"] - p[1] if ayna_y else p[1]                # İş Emri'nin çerçevesi: kayan cephe büyük uçta
        return [sx(float(p[0])), round(s["H"] - sy(yf), 2) if ayna_y else sy(float(yf))]
    dk_, ds_ = _sayi(kaynak_ie.get("dikmeler") or []), _sayi(ie.get("dikmeler") or [])
    bek_d = [dikme_bek(p) for p in dk_]
    ayni_nokta = lambda p, q: (all(map(yakin, p, q)) if isinstance(p, list) and isinstance(q, list) and len(p) == len(q)
                               and all(isinstance(v, float) for v in p + q) else p == q)
    if len(dk_) != len(ds_) or not all(ayni_nokta(p, q) for p, q in zip(ds_, bek_d)):
        b.append(f"dikmeler: kaynak evle aynı değil ya da kayan cepheden başka yerde kaydı ({dk_} → {ds_})")
    elif bek_d != dk_ and not (veranda_sozu and veranda_sozu.strip()):
        b.append("veranda: verandanın dikmesi silinen kadar kayar; veranda kısalması yalnız Lokman'ın ev kartıyla (--veranda-sozu)")

    # İş Emri'nin geri kalanı aynen (kimlik ve talep yazıları dışında)
    for alan in sorted((set(ie) | set(kaynak_ie)) - set(SILME_KIMLIK) - {"yapi", "mahaller", "girintiler", "acikliklar", "dikmeler"}):
        if _sayi(ie.get(alan)) != _sayi(kaynak_ie.get(alan)):
            b.append(f"{alan}: kaynak evle aynı değil")
    yk, ys = dict(kaynak_ie.get("yapi") or {}), dict(ie.get("yapi") or {})
    for alan in sorted((set(yk) | set(ys)) - {"dis_olcu_cm", "grid", "referans_model", "dizilim"}):
        if _sayi(ys.get(alan)) != _sayi(yk.get(alan)):
            b.append(f"yapi.{alan}: kaynak evle aynı değil")
    diz_k = {x: v for x, v in (yk.get("dizilim") or {}).items() if x != "tek_ozel_pano"}
    if _sayi({x: v for x, v in diz.items() if x != "tek_ozel_pano"}) != _sayi(diz_k):
        b.append("dizilim: kaynak evle aynı değil (tek özel pano anahtarı dışında); kapının ve pencerenin yerini dizilim verir")

    # kartın dış ölçüsü: silinen geri eklenince normal kipin sınırı içinde
    ko = kart["dis_olcu_cm"]
    geri = [[o[a][0] + dx, o[a][1] + dy] for a in ("dis_olcu_cm", "acikla_olcu_cm")]
    fark = min(_yakin(geri[0], ko), _yakin(geri[1], ko))
    if fark > TOL_OLCU_CM:
        b.append(f"dış ölçü: silinmiş {o['dis_olcu_cm'][0]:g} × {o['dis_olcu_cm'][1]:g} cm + silinen {dx:g} / {dy:g} cm, pafta {ko[0]:g} × "
                 f"{ko[1]:g} cm; fark {fark:.2f} cm > {TOL_OLCU_CM:g}")
    return b, olc


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
    ap.add_argument("--silme-hali", metavar="KAYNAK", default=None,
                    help="prefabrik: tek özel pano kuralının dizilim sonunda bıraktığı kısa parçası silinmiş ev; KAYNAK kaynak evin İş Emri'si (BK-31)")
    ap.add_argument("--veranda-sozu", default=None,
                    help="--silme-hali ile: veranda da silinen kadar kısalırsa Lokman'ın o evin kartı, sözü ve saatiyle (BK-31)")
    a = ap.parse_args(argv)
    if a.standart_hal and a.silme_hali:
        print("DUR: --standart-hal ve --silme-hali ayrı kalemlerdir; birlikte verilmez"); return 2
    if a.veranda_sozu and not a.silme_hali:
        print("DUR: --veranda-sozu yalnız --silme-hali ile"); return 2
    if a.kart.upper().startswith(("ÇP", "CP")):
        if a.standart_hal or a.silme_hali:
            print("DUR: standart hâl ve silme hâli kipi yalnız prefabrikte (D-91, BK-31); çelikte yok"); return 2
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
    oku = lambda yol: json.loads(Path(yol).read_text(encoding="utf-8"))
    if a.silme_hali:
        bulgular, o = denetle_silme(ie, kart, oku(a.silme_hali), a.veranda_sozu)
        sil = " + ".join(f"{p['duvar']} {p['boy']:g}" for p in o["silinen"])
        gecti = (f"GEÇTİ: silme hâli (BK-31), kaynak evin proje kartıyla aynı; silinen {o['silinen_cm'][0]:g} / {o['silinen_cm'][1]:g} cm "
                 f"(kısa parçalar: {sil})" + (f"; veranda kısaldı ({', '.join(o['veranda_kisalan'])}): {a.veranda_sozu}" if o["veranda_kisalan"] else ""))
    else:
        bulgular, o = denetle_standart(ie, kart, oku(a.standart_hal)) if a.standart_hal else denetle(ie, kart)
        gecti = "GEÇTİ: standart hâl, kaynak evin proje kartıyla aynı (D-91)" if a.standart_hal else "GEÇTİ: proje kartıyla aynı"
    print(json.dumps(o, ensure_ascii=False))
    print(gecti if not bulgular else "KALDI:\n- " + "\n- ".join(bulgular))
    return 0 if not bulgular else 1


if __name__ == "__main__":
    sys.exit(main())
