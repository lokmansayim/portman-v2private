"""İE-14 · plan denetçisi: LLM'in plan taslağını kurallara karşı denetler (LLM'siz, belirlenimci).

Sıra: şema → oda programı ve alan (K-A1) → derleme (`motor/genel/plan_derle.py`: döşeme, ızgara, kapı ve pencere yerleşimi) →
geometri (`yapi.kur` + `varyant.aciklik_denetimi`) → oda en küçükleri (`kurallar/plan/oda_kurallari.json`) → erişim (kapı grafiği)
→ zorunlu pencereler. İhlaller Türkçe ve somuttur: LLM'e gerekçe olarak geri gider (en çok 2 yeniden deneme; `plan_uretici`).
"""
from __future__ import annotations

import json
import math
import re
from collections import deque
from pathlib import Path

from pydantic import ValidationError

from beyin.plan_sema import PlanTaslagi

ROOT = Path(__file__).resolve().parent.parent
KURAL_YOLU = ROOT / "kurallar" / "plan" / "oda_kurallari.json"
ISLEV_ADI = {"yatak_odasi": "yatak odası", "salon": "salon", "mutfak": "mutfak", "banyo": "banyo", "hol": "hol", "depo": "depo",
             "veranda": "veranda"}


def kurallar(yol: Path = KURAL_YOLU) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def program_coz(s: str | None) -> tuple[int, int] | None:
    """'3+1' → (3, 1); '1+0' → (1, 0); tanınmazsa None."""
    m = re.fullmatch(r"\s*(\d)\s*\+\s*(\d)\s*", str(s or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _tr(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def kapi_yaylari(tanim: dict) -> list[tuple[str, object]]:
    """Her kapının açılım alanı (`plan_derle.kapi_yayi`). Ad: 'Mahal kapısı (K3)'."""
    from motor.genel.plan_derle import kapi_yayi
    duvar = {d["ad"]: d["kutu"] for d in tanim["duvarlar"]}
    return [(f"{a.get('not') or ''} kapısı ({a['ad']})".strip(), kapi_yayi(a, duvar[a["duvar"]]))
            for a in tanim["acikliklar"] if a["tur"] in ("dis_kapi", "ic_kapi") and a["duvar"] in duvar]


def denetle(plan: dict, talep: dict | None = None, kural: dict | None = None, kod: str = "YENI") -> dict:
    """Plan taslağını denetler. Dönüş: {gecerli, ihlaller[], tanim (geçerliyse), ozet}. Hiçbir zaman istisna fırlatmaz."""
    from motor.genel.plan_derle import PlanHatasi, derle
    from beyin.varyant import VaryantHatasi, _kur, aciklik_denetimi
    kural = kural or kurallar()
    talep = talep or {}
    ihlal: list[str] = []
    try:
        p = PlanTaslagi.model_validate(plan).model_dump()
    except ValidationError as e:
        return {"gecerli": False, "ihlaller": [f"şema: {'.'.join(str(x) for x in er['loc'])}: {er['msg']}" for er in e.errors()][:12],
                "tanim": None, "ozet": {}}
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    brut = W * H / 1e4
    odalar = [m for m in p["mahaller"] if m["islev"] != "veranda"]
    say = {i: sum(1 for m in odalar if m["islev"] == i) for i in ISLEV_ADI}
    ozet = {"dis_olcu_cm": [W, H], "brut_m2": round(brut, 2), "yatak": say["yatak_odasi"], "salon": say["salon"], "banyo": say["banyo"]}

    prog = program_coz(talep.get("oda_programi"))
    if prog:
        if say["yatak_odasi"] != prog[0]:
            ihlal.append(f"oda programı {prog[0]}+{prog[1]} isteniyor: yatak odası {prog[0]} olmalı, planda {say['yatak_odasi']}")
        if say["salon"] != prog[1]:
            ihlal.append(f"oda programı {prog[0]}+{prog[1]} isteniyor: salon {prog[1]} olmalı, planda {say['salon']} "
                         f"(açık mutfaklı salon tek mahal: işlev 'salon')")
    if say["banyo"] < 1:
        ihlal.append("en az bir banyo olmalı")
    tol = float(kural["alan_tolerans"]["deger"])
    if talep.get("alan_m2"):
        hedef = float(talep["alan_m2"])
        if abs(brut - hedef) > tol * hedef + 1e-9:
            ihlal.append(f"brüt alan {_tr(brut)} m² (dış ölçü {W} × {H} cm), istenen {hedef:g} m² ±%{tol * 100:g}: "
                         f"{_tr(hedef * (1 - tol))}–{_tr(hedef * (1 + tol))} m² arası olmalı")

    ct = p.get("cati") or {}
    uzun = "x" if W >= H else "y"
    if ct.get("tip") == "kirma" and ct.get("mahya_yonu") and ct["mahya_yonu"] != uzun and W != H:
        ihlal.append(f"kırma çatıda mahya uzun kenar boyunca olur ({'doğu–batı' if uzun == 'x' else 'kuzey–güney'}); mahya_yonu '{uzun}' "
                     "ya da boş bırakın")
    if any(m["islev"] == "veranda" and (m.get("ortu") or "cati") == "cati" for m in p["mahaller"]) and ct.get("tip") != "kirma":
        ihlal.append("çatı altındaki veranda yalnız kırma çatıyla (beşikte kalkan verandanın açık kenarına oturur); kırma seçin ya da şerit "
                     "verandayı pergola/açık yapın")
    try:
        tanim = derle(p, kod=kod)
    except PlanHatasi as e:
        return {"gecerli": False, "ihlaller": ihlal + e.ihlaller, "tanim": None, "ozet": ozet}
    try:
        if p.get("dis_karkas") == 140:                         # dış ölçü korunur, iç yüz içeri (İE-08 A4 işlemi; derleyici 80'lik kurar)
            from beyin.varyant import dis_karkas_140
            tanim = dis_karkas_140(tanim)
        g = _kur(tanim)
        aciklik_denetimi(tanim, g)
    except VaryantHatasi as e:
        return {"gecerli": False, "ihlaller": ihlal + [f"geometri: {e}"], "tanim": None, "ozet": ozet}

    from shapely.geometry import box
    # duvar (karkas) kutuları üst üste binmez (geometri hakemi 14.10: yakın paralel sınırlar çift duvar üretiyordu)
    kutular = [(d["ad"], box(*d["kutu"])) for d in tanim["duvarlar"]]
    for i in range(len(kutular)):
        for j in range(i + 1, len(kutular)):
            if kutular[i][1].intersection(kutular[j][1]).area > 1:
                ihlal.append(f"duvarlar üst üste biniyor ({kutular[i][0]}, {kutular[j][0]}): iki sınır birbirine çok yakın; mahal kenarlarını "
                             "en az 20 cm ayırın")
    # çatı motorun kendi kurucusundan geçer (geçersiz düzlem K23'te düşerdi; bayiye görselsiz seçenek gitmesin)
    try:
        from motor.genel import cati_genel
        cati_genel.cati_kur(tanim["cati"])
    except (SystemExit, Exception) as e:
        ihlal.append(f"çatı kurulamadı: {e}")
    # 15 cm ve daha kısa parça çıkmaz (D-10, "Çelikte 15 cm parça çıkmaz"): dış yüzler ve iç duvar eksenleri arası, her iki yönde
    for eks, ad in ((0, "doğu–batı"), (1, "kuzey–güney")):
        dis = {0, (W, H)[eks]}
        ic = {round((d["kutu"][eks] + d["kutu"][eks + 2]) / 2, 2) for d in tanim["duvarlar"]
              if d["sinif"] == "ic" and (d["kutu"][eks + 2] - d["kutu"][eks]) < (d["kutu"][3 - eks] - d["kutu"][1 - eks])}
        cizgiler = sorted(dis | ic | {r[eks] for m in p["mahaller"] for r in m["dikdortgenler"]} | {r[eks + 2] for m in p["mahaller"] for r in m["dikdortgenler"]})
        kisa = [(a, b) for a, b in zip(cizgiler, cizgiler[1:]) if 0 < b - a <= 15]
        if kisa:
            ihlal.append(f"{ad} yönünde 15 cm ve daha kısa parça var ({', '.join(f'{a:g}–{b:g}' for a, b in kisa[:3])}); çelikte 15 cm parça çıkmaz")
    # kapı açılım yayları birbirine binmez (çeyrek daire; menteşe ucunda, açılım yönünde)
    yaylar = kapi_yaylari(tanim)
    duvar_adi = {a["ad"]: a["duvar"] for a in tanim["acikliklar"]}
    for ad, yay in yaylar:                                      # yay kendi duvarı dışında bir duvara çarpmaz (geometri hakemi 14.10)
        kid = ad[ad.rfind("(") + 1:-1]
        carpan = [d for d, kb in kutular if d != duvar_adi.get(kid) and yay.intersection(kb).area > 1]
        if carpan:
            ihlal.append(f"{ad}: açılırken duvara çarpıyor ({', '.join(carpan[:2])}); oda bu kapı için dar")
    for i in range(len(yaylar)):
        for j in range(i + 1, len(yaylar)):
            if yaylar[i][1].intersection(yaylar[j][1]).area > 25:
                ihlal.append(f"kapı yayları çakışıyor: {yaylar[i][0]} ile {yaylar[j][0]} (kapılardan birini aynı duvarda kaydırın "
                             f"ya da başka duvara alın)")

    # oda en küçükleri (net alan, net bölgenin dar kenarı)
    alanlar = {}
    for m in odalar:
        b = g["bolgeler"][m["ad"]]
        x0, y0, x1, y1 = b["net"].bounds
        dar = min(x1 - x0, y1 - y0)
        alanlar[m["ad"]] = round(b["alan_m2"], 2)
        r = kural["odalar"].get(m["islev"]) or {}
        if b["alan_m2"] + 1e-6 < float(r.get("en_az_m2", 0)):
            ihlal.append(f"{m['ad']} net {_tr(b['alan_m2'])} m², {ISLEV_ADI[m['islev']]} için en az {r['en_az_m2']:g} m²")
        kol = float(kural.get("kol_en_az_cm", {}).get("deger", 0) or 0)
        if kol and m["islev"] != "veranda":
            acik = b["net"].buffer(-kol / 2, join_style=2).buffer(kol / 2, join_style=2)
            if b["net"].difference(acik).area > 500:            # 0,05 m²'den büyük dar kol (L odanın ince kolu, duvara gömülen şerit)
                ihlal.append(f"{m['ad']}: {kol:g} cm'den dar kolu var (net {b['net'].difference(acik).area / 1e4:.2f} m²); dar şeritleri komşu mahale katın")
        if dar + 1e-6 < float(r.get("dar_kenar_cm", 0)):
            ihlal.append(f"{m['ad']} dar kenarı net {dar:.0f} cm, {ISLEV_ADI[m['islev']]} için en az {r['dar_kenar_cm']} cm "
                         f"(eksenden eksene en az {math.ceil((r['dar_kenar_cm'] + 10.5) / 5) * 5} cm)")
    ozet["odalar_m2"] = alanlar

    # erişim: kapı grafiği; veranda dış sayılır
    ver = {m["ad"] for m in p["mahaller"] if m["islev"] == "veranda"}
    komsu: dict[str, set[str]] = {m["ad"]: set() for m in odalar}
    komsu["dis"] = set()
    for k in p["kapilar"]:
        a, b = ["dis" if x in ver else x for x in (k["arasinda"] + ["", ""])[:2]]
        if a in komsu and b in komsu:
            komsu[a].add(b)
            komsu[b].add(a)
    islev = {m["ad"]: m["islev"] for m in odalar}

    def ulasir(hedef: str, yasak: set[str]) -> bool:
        gor, q = {"dis"}, deque(["dis"])
        while q:
            u = q.popleft()
            if u == hedef:
                return True
            for v in komsu[u]:
                if v not in gor and (v == hedef or v not in yasak):
                    gor.add(v)
                    q.append(v)
        return False
    for m in odalar:
        if not ulasir(m["ad"], set()):
            ihlal.append(f"{m['ad']}: giriş kapısından kapılarla ulaşılamıyor")
            continue
        yataklar = {a for a, i in islev.items() if i == "yatak_odasi"} - {m["ad"]}
        if m["islev"] == "banyo" and kural["erisim"].get("banyo_yatak_odasindan_gecmez") and not ulasir(m["ad"], yataklar) and \
                sum(1 for o in odalar if o["islev"] == "banyo") == 1:
            ihlal.append(f"{m['ad']}: yatak odasından geçmeden ulaşılamıyor (tek banyo ortak alandan açılmalı)")
        if m["islev"] == "yatak_odasi" and kural["erisim"].get("yatak_odasi_baska_yatak_odasindan_gecmez") and not ulasir(m["ad"], yataklar):
            ihlal.append(f"{m['ad']}: başka bir yatak odasından geçmeden ulaşılamıyor")

    pencereli = {pc["mahal"] for pc in p["pencereler"]}
    for m in odalar:
        if m["islev"] in kural["pencere_zorunlu"]["deger"] and m["ad"] not in pencereli:
            ihlal.append(f"{m['ad']}: penceresi yok ({ISLEV_ADI[m['islev']]} için zorunlu; dış cepheye değmeli)")
    return {"gecerli": not ihlal, "ihlaller": ihlal, "tanim": tanim if not ihlal else None, "ozet": ozet,
            **({"_tanim_taslak": tanim} if ihlal else {})}
