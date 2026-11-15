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
  (`--veranda-sozu`, söz ve saat kayda yazılır); ek akslar duvarla kayar (BK-34); öteki alanlar (çatı, açık sınırlar) aynen.
30 cm sınırı varsayımdır (yedi evde parça 9,5–27 cm; BK-31 › Varsayımlar). Brüt oturum kıyaslanmaz (kayıt Motor'un brütünü yazar).

    python3 araclar/havuz_hakemi.py testler/havuz/is_emirleri/PA12_SILME.json --kart AP-11 --silme-hali is_emri/adaylar/PA12.json

Kesim hattı, üçlü H ve açıklık kayması (BK-34; silme hâlinin içinde, her biri yalnız Lokman'ın o evin kartı ya da sözüyle; tek ev sözleri,
genelleme varsayımdır). 71 m² 2+1: Lokman 14 Kasım 2026 20:46:54 sözü, kart 20:57:28 "Doğru, yanına eklensin" (eskiz 05c, 773 × 888,5 cm):
- kesim hattı (`--kesim-hatti <cephe>:<cm>:<hat>` + `--kesim-sozu`): kısa parça dizilim sonundaki cepheden içeride bir hatta kesilir; hattın
  ötesindeki duvar, oda köşesi, açıklık, dikme, ek aks ve dayanak cm kadar kayar, sonra dış yüzün bandı kalan kadar (silme ya da büyüme);
  kesilen bantta kaynak evin duvarı ya da oda köşesi olmaz; o eksende en az bir duvarda cm kadar kısa parça düşer;
- üçlü H (`--uclu-h-sozu`; D-96): silinmiş hâlde yalnız `t: "uclu_h"` birleşimi eklenebilir; nokta kaynak evde bir duvar köşesine eşlenir,
  kaynak ev o noktada üçlü H'la kurulur ve kıyas onunla yapılır (köşe direğinin kalkması pano dizisinde fark sayılmaz);
- açıklık kayması (`--aciklik-sozu`): Motor'un yeniden dizdiği duvarda (kısa parçasız kısalan ya da uzayan) kapı ya da pencere duvar boyunca
  kayabilir (oda ortasındaki pencere odanın ortasında kalır): hattı ve boyu aynı, duvarın içinde, kayma duvarın değişiminden çok değil.

    python3 araclar/havuz_hakemi.py testler/motor/veri/D96_71m2_uclu_h.json --kart AP-08 --silme-hali is_emri/adaylar/PA26.json \
        --kesim-hatti on:17:770 --kesim-sozu "<kart>" --buyume-sozu "<söz>" --veranda-sozu "<kart>" --uclu-h-sozu "<söz>" --aciklik-sozu "<kart>"

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
# BK-31 PR-2 (büyüme): kalan özel pano dış duvar dışarı kayarak tamamlanır, yalnız Lokman'ın ev sözüyle (`--buyume-sozu`). Hedef boylar
# Lokman'ın iki ev sözünden: 125,5 (140 m², 14 Kasım 2026 20:22:14 "sağ taraf doğru ön tarafta da salon kısmında 101,5'u 125,5 a
# tamamlayabilirsin") ve 62,75 (77 m², 20:35:43 "salon ve mutfaktaki 1000cm çizgisindeki 48,75'leride 62,75'e tamamla"). Tek ev sözleri;
# genelleme varsayımdır (CIO, 20:27).
TAMAMLAMA_BOYLARI_CM = (125.5, 62.75)
# BK-34 (kesim hattı ve üçlü H; yalnız Lokman'ın ev kartıyla): 71 m² 2+1, Lokman 14 Kasım 2026 20:46:54 sözü ve 20:57:28 kartı "Doğru,
# yanına eklensin" (eskiz 05c, 773 × 888,5 cm): kısa parça dış yüzde değil, dizilim sonundaki cepheden içeride bir hatta kesilir
# (`--kesim-hatti on:17:770`); hattın ötesindeki her şey parça kadar kayar. Üçlü H (D-96) silinmiş hâlde yazılır (`--uclu-h-sozu`).
KESIM_CEPHELERI = ("sag", "sol", "on", "arka")
KESIM_SECENEKLERI = (                                    # hakem ve aday kaydı aynı seçenekleri alır (BK-34)
    ("--kesim-hatti", "--silme-hali ile: kısa parça dış yüzde değil, dizilim sonundaki cepheden içeride bir hatta kesildiyse "
                      "<cephe>:<cm>:<hat> (ör. on:17:770; hat İş Emri'nin çerçevesinde); --kesim-sozu ile (BK-34)"),
    ("--kesim-sozu", "--kesim-hatti ile: Lokman'ın o evin kartı, sözü ve saatiyle (BK-34; tek ev sözü)"),
    ("--uclu-h-sozu", "--silme-hali ile: silinmiş hâlde köşe direği yerine üçlü H (yapi.birlesimler, D-96) yazıldıysa Lokman'ın o evdeki "
                      "sözü ve saati (BK-34)"),
    ("--aciklik-sozu", "--silme-hali ile: Motor'un yeniden dizdiği duvarda kapı ya da pencere kaydıysa Lokman'ın o evin kartı, sözü ve "
                       "saati (BK-34)"),
)
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


def _tamamlandi(dk: dict, ds: dict, uzama: float) -> tuple[float, float] | None:
    """Uzayan duvarda yalnız bir özel pano uzama kadar büyüyüp tam ya da yarım panoya tamamlandı mı (BK-31 PR-2): açıklıklı ve karkaslı
    panolar aynı, açıklıksız panoların kümesinde tek fark p → p + uzama ve p + uzama `TAMAMLAMA_BOYLARI_CM`'de. Motor tek özel pano
    kuralıyla aralığı yeniden dizdiği için tamamlanan pano yer değiştirebilir (77 m²); küme kıyaslanır. Tamamlandıysa (p, p + uzama)."""
    from collections import Counter
    if [p for p in ds["panolar"] if p[1]] != [p for p in dk["panolar"] if p[1]]:
        return None
    once, sonra = Counter(x for x, sabit in dk["panolar"] if not sabit), Counter(x for x, sabit in ds["panolar"] if not sabit)
    giden, gelen = list((once - sonra).elements()), list((sonra - once).elements())
    if len(giden) == 1 and len(gelen) == 1 and abs(giden[0] + uzama - gelen[0]) <= YER_TOL_CM \
            and any(abs(gelen[0] - t) <= YER_TOL_CM for t in TAMAMLAMA_BOYLARI_CM):
        return giden[0], gelen[0]
    return None


def _dizilim_bantta(diz: dict, sx, sy) -> dict:
    """Dizilimin Motor çerçevesindeki değerleri (dış pano dayanağı, köşe yönü, karkaslı pano) kayan cephenin bandında silinen ya da büyüyen
    kadar kayar; `beyin.yarim_pano.kaydir` gibi. Öteki anahtarlar aynen."""
    f = {"x": sx, "y": sy}
    ote = {"x": "y", "y": "x"}
    out = json.loads(json.dumps(diz))
    for dy in out.get("dis_pano_dayanagi") or []:
        e = "x" if "x" in dy else "y"
        dy[e] = f[e](dy[e]); dy["aralik_cm"] = [f[e](v) for v in dy.get("aralik_cm") or []]
        if "duvar_cm" in dy:
            dy["duvar_cm"] = f[ote[e]](dy["duvar_cm"])
    for kp in out.get("karkasli_panolar") or []:
        e = kp.get("yon")
        if e in f:
            kp["aralik_cm"] = [f[e](v) for v in kp.get("aralik_cm") or []]
            if kp.get("aciklik_ortasi_cm"):
                kp["aciklik_ortasi_cm"] = [None if v is None else f[e](v) for v in kp["aciklik_ortasi_cm"]]
            if "eksen_cm" in kp:
                kp["eksen_cm"] = f[ote[e]](kp["eksen_cm"])
    for k_ in out.get("kose_uzayan") or []:
        for e in ("x", "y"):
            if e in k_:
                k_[e] = f[e](k_[e])
    return out


def _kesim_oku(yazi: str, kaynak_ie: dict, k: dict, t: float) -> tuple[tuple[str, float, float] | None, str | None]:
    """BK-34: `<cephe>:<cm>:<hat>` (eskizin kayma yazımı, ör. "on:17:770"; hat İş Emri'nin çerçevesinde, dizilim sonundaki cepheden içeride)
    → ((eksen, hat, cm), None) ya da (None, bulgu). Cephe dizilim sonunda olmalı (Motor çerçevesinde büyük uç); parça 0 ile 30 cm arası; hat
    iki dış duvarın arasında ve kesilen bantta (hat − cm ile hat arası) kaynak evin duvar hattı, duvar ucu ya da oda köşesi yok."""
    from beyin import yarim_pano as Y
    m = re.fullmatch(r"\s*(sag|sol|on|arka):(\d+(?:[.,]\d+)?):(\d+(?:[.,]\d+)?)\s*", yazi or "")
    if not m:
        return None, f"kesim hattı: '{yazi}' okunmadı (<cephe>:<cm>:<hat>, cephe {' | '.join(KESIM_CEPHELERI)}; ör. on:17:770)"
    cephe, cm, hat = m.group(1), float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", "."))
    eksen, kenar, _ = Y.yan(cephe, kaynak_ie)
    L = k["W"] if eksen == "x" else k["H"]
    if kenar != "max":
        return None, f"kesim hattı: {cephe} cephesi dizilim sonunda değil (kısa parça yalnız dizilim sonunda kalır, D-92)"
    if not 0 < cm < TOL_SILME_CM:
        return None, f"kesim hattı: parça {cm:g} cm (0 ile {TOL_SILME_CM:g} cm arası kısa parça kesilir)"
    if not t < hat <= L - cm - t - 0.5:
        return None, f"kesim hattı: hat {hat:g} cm iki dış duvarın arasında değil ({t:g} ile {L - cm - t - 0.5:g} cm arası; dış yüzde kesim silme kalemidir)"
    bant = []
    for d in k["duvarlar"]:
        bant += [d["c"]] if d["yon"] != eksen else [d["a0"], d["a1"]]
    i0, i1 = (0, 2) if eksen == "x" else (1, 3)
    for m_ in kaynak_ie.get("mahaller") or []:
        for r in _sayi(m_.get("konum_cm") or []):
            bant += [r[i0], r[i1]]
    icinde = sorted({v for v in bant if hat - cm - YER_TOL_CM < v < hat - YER_TOL_CM})
    if icinde:
        return None, (f"kesim hattı: kesilen bantta ({hat - cm:g}–{hat:g} cm) kaynak evin duvarı ya da oda köşesi var "
                      f"({', '.join(f'{v:g}' for v in icinde)}); kesim yalnız boş bantta")
    return (eksen, hat, cm), None


def _eksen_esle(L: float, t: float, d: float, kesim: tuple[float, float] | None):
    """Bir eksende kaynak evin değeri → silinmiş hâldeki yeri (İş Emri'nin çerçevesi). Kesimsiz: dizilim sonundaki cephenin bandı (dış yüzden
    bir dış duvar) d kadar kayar (BK-31). Kesimli (BK-34; hat, cm): hattın ötesi cm kadar kayar, sonra bant kalan d − cm kadar (büyüme ya da
    silme)."""
    if kesim is None:
        return lambda v: round(v - d, 2) if v >= L - t - 0.5 else v
    hat, cm = kesim
    L1, kalan = L - cm, d - cm

    def esle(v):
        u = v - cm if v >= hat - YER_TOL_CM else v
        u = u - kalan if u >= L1 - t - 0.5 else u
        return round(u, 2) if u != v else v
    return esle


def denetle_silme(ie: dict, kart: dict, kaynak_ie: dict, veranda_sozu: str | None = None,
                  buyume_sozu: str | None = None, kesim_hatti: str | None = None, kesim_sozu: str | None = None,
                  uclu_h_sozu: str | None = None, aciklik_sozu: str | None = None) -> tuple[list[str], dict]:
    """(bulgular, ölçüm) silme hâli için (BK-31; D-92 › Havuza uygulama). Kaynak ev tek özel pano anahtarıyla (D-92, "dizilim_sonu") kurulunca
    dizilimin sonunda kalan 30 cm'den kısa parça silinmiş: o cephenin dış duvarı parça kadar içeri kaymış. Kalemler (Motor'un planından):
    kaynak ev proje kartıyla aynı (normal kip); silinmiş hâlde anahtar "dizilim_sonu"; dış ölçü her eksende 0 ile 30 cm arası küçülür (en az
    birinde); kısalan her duvarda yalnız dizilim sonundaki kısa açıklıksız pano düşer, öteki duvarların pano dizisi aynı; kapı ve pencere
    yerinde (kayan cephedeki açıklığın hattı duvarla kayar); oda ve girinti köşeleri yalnız kayan cephenin bandında silinen kadar kayar;
    veranda (açık mahal) kısalmaz, Lokman'ın ev kartıyla kısalır (`veranda_sozu`); açıklıklar, verandalar, dikmeler, çatı ve dizilim aynen;
    kartın oda, pencere, kapı, açık mahal ve kat kalemleri aynı; dış ölçü kartla silinen kadar farklı (normal kipin 5 cm'si içinde);
    silinmiş hâlde 30 cm'den kısa açıklıksız pano kalmaz. Brüt oturum kıyaslanmaz (ölçüyle küçülür; kayıt Motor'un brütünü yazar).
    Büyüme (BK-31 PR-2; yalnız Lokman'ın ev sözüyle, `buyume_sozu`): bir eksende dış ölçü büyüyebilir. O eksende en az bir duvarda kalan özel
    pano büyüme kadar uzayıp tam panoya (125,5) ya da yarım panoya (62,75) tamamlanır (`_tamamlandi`); uzayan öteki duvarları Motor anahtarla
    yeniden dizer (açıklıklı panolar aynı, özel pano sayısı artmaz). Kayan cephenin bandı büyüme kadar dışarı kayar; öteki kalemler aynen.
    Kesim hattı (`kesim_hatti`, `kesim_sozu`), üçlü H (`uclu_h_sozu`) ve yeniden dizilen duvarda açıklık kayması (`aciklik_sozu`): BK-34,
    modülün başındaki açıklama. Tek ev sözleri; genelleme varsayımdır."""
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
    olc = {**o, "kaynak_dis_olcu_cm": [k["W"], k["H"]], "silinen_cm": [max(0.0, dx), max(0.0, dy)], "buyuyen_cm": [max(0.0, -dx), max(0.0, -dy)],
           "silinen": [], "tamamlanan": [], "yeniden_dizilen": [], "veranda_kisalan": []}
    silinen_eksen, tamamlanan_eksen, silinen_boy, dizilen = set(), set(), [], []
    t = float(((kaynak.get("yapi") or {}).get("duvar_kalinligi_cm") or {}).get("dis") or 10)
    kesim = None                                              # BK-34: (eksen, hat, cm), yalnız Lokman'ın ev kartıyla
    if kesim_hatti:
        if not (kesim_sozu and kesim_sozu.strip()):
            return b + ["kesim hattı: içerideki hatta kesim yalnız Lokman'ın ev kartıyla (--kesim-sozu)"], olc
        kesim, hata = _kesim_oku(kesim_hatti, kaynak_ie, k, t)
        if hata:
            return b + [hata], olc
        olc["kesim_hatti"] = {"yazi": kesim_hatti.strip(), "eksen": kesim[0], "hat_cm": kesim[1], "cm": kesim[2]}
    kes = {e: ((kesim[1], kesim[2]) if kesim and kesim[0] == e else None) for e in ("x", "y")}
    kx, ky = (round(dx - (kes["x"] or (0, 0))[1], 2), round(dy - (kes["y"] or (0, 0))[1], 2))   # dış yüzde silinen (eksi: büyüyen)
    olc["silinen_cm"] = [round(max(0.0, kx) + (kes["x"] or (0, 0))[1], 2), round(max(0.0, ky) + (kes["y"] or (0, 0))[1], 2)]
    olc["buyuyen_cm"] = [max(0.0, -kx), max(0.0, -ky)]                # kesimli eksende silinen kesim dahil; dış ölçü farkı silinen − büyüyen
    buyume = bool(buyume_sozu and buyume_sozu.strip())
    alt = -max(TAMAMLAMA_BOYLARI_CM) if buyume else 0.0      # büyüme özel panoyu en çok tam panoya tamamlar
    if not (alt <= kx < TOL_SILME_CM and alt <= ky < TOL_SILME_CM and (dx != 0 or dy != 0)):
        return b + [f"dış ölçü: kaynak {k['W']:g} × {k['H']:g} cm, silinmiş {s['W']:g} × {s['H']:g} cm; silinen {dx:g} / {dy:g} cm"
                    + (f" (kesim hattında {kesim[2]:g} cm, dış yüzde {kx:g} / {ky:g} cm)" if kesim else "")
                    + f" (her eksende 0 ile {TOL_SILME_CM:g} cm arası küçülür, en az birinde; büyüme yalnız Lokman'ın ev sözüyle, --buyume-sozu)"], olc
    sx = _eksen_esle(k["W"], t, dx, kes["x"])                # dizilim sonundaki cephenin bandı (dış yüzden bir dış duvar) silinen kadar
    sy = _eksen_esle(k["H"], t, dy, kes["y"])                # içeri; kesim hattının ötesi kesilen kadar; öteki değerler yerinde
    yakin = lambda u, v: abs(u - v) <= YER_TOL_CM

    # BK-34: üçlü H (D-96) silinmiş hâlde yazılır; kaynak evde eşlendiği noktaya da yazılır, duvarlar ve açıklıklar onunla kıyaslanır
    bk_ = _sayi((kaynak_ie.get("yapi") or {}).get("birlesimler") or [])
    bs_ = _sayi((ie.get("yapi") or {}).get("birlesimler") or [])
    ayni_b = lambda p, q: ({a: v for a, v in p.items() if a != "nokta_cm"} == {a: v for a, v in q.items() if a != "nokta_cm"}
                           and all(map(yakin, p.get("nokta_cm") or [], q.get("nokta_cm") or [])))
    bek_b = [{**x, "nokta_cm": [sx(x["nokta_cm"][0]), sy(x["nokta_cm"][1])]} for x in bk_]
    eksik_b = [x for x in bek_b if not any(ayni_b(x, y) for y in bs_)]
    yeni_b = [y for y in bs_ if not any(ayni_b(x, y) for x in bek_b)]
    if eksik_b:
        b.append(f"birleşim: kaynak evin birleşimi silinmiş hâlde eşlendiği yerde değil ({eksik_b})")
    if yeni_b:
        uclar = [(d["a0"], d["c"]) for d in k["duvarlar"] if d["yon"] == "x"] + [(d["a1"], d["c"]) for d in k["duvarlar"] if d["yon"] == "x"] \
            + [(d["c"], d["a0"]) for d in k["duvarlar"] if d["yon"] == "y"] + [(d["c"], d["a1"]) for d in k["duvarlar"] if d["yon"] == "y"]
        diger_b, yeni_b = [y for y in yeni_b if y.get("t") != "uclu_h"], [y for y in yeni_b if y.get("t") == "uclu_h"]
        if diger_b:
            b.append(f"birleşim: silinmiş hâlde yalnız üçlü H eklenebilir (D-96); öteki birleşimler kaynak evle aynı ({diger_b})")
        if yeni_b and not (uclu_h_sozu and uclu_h_sozu.strip()):
            b.append("üçlü H: köşe direği yerine üçlü H yalnız Lokman'ın ev sözüyle (--uclu-h-sozu; D-96)")
        elif yeni_b:
            ek_b = []
            for y in yeni_b:
                (u, v), dxy = y["nokta_cm"], {"x": dx, "y": dy}
                aday = lambda w, e: {round(w + a, 2) for a in (0.0, (kes[e] or (0, 0))[1], dxy[e] - (kes[e] or (0, 0))[1], dxy[e])}
                nok = [(p, q) for p in aday(u, "x") for q in aday(v, "y")
                       if yakin(sx(p), u) and yakin(sy(q), v) and any(yakin(p, a) and yakin(q, c) for a, c in uclar)]
                if len(nok) != 1:
                    b.append(f"üçlü H: {y['nokta_cm']} kaynak evde bir duvar köşesine eşlenmiyor (eşlenen: {nok or 'yok'})")
                    continue
                ek_b.append({"nokta_cm": list(nok[0]), "t": "uclu_h"})
                olc.setdefault("uclu_h", []).append({"nokta_cm": y["nokta_cm"], "kaynakta_cm": list(nok[0])})
            if ek_b:
                kaynak = json.loads(json.dumps(kaynak))
                kaynak["yapi"]["birlesimler"] = list((kaynak["yapi"].get("birlesimler") or [])) + ek_b
                try:
                    k2 = duvar_dizileri(kaynak)
                except G.IsEmriHatasi as e:
                    return b + [f"üçlü H: kaynak evde o köşede kurulmuyor ({e})"], olc
                if (k2["W"], k2["H"]) != (k["W"], k["H"]):
                    return b + [f"üçlü H: kaynak evin dış ölçüsü değişti ({k['W']:g} × {k['H']:g} → {k2['W']:g} × {k2['H']:g} cm)"], olc
                k = k2

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
        if kisalma < 0:                                       # BK-31 PR-2: büyüyen eksende uzayan duvar
            tam = _tamamlandi(dk, ds, -kisalma)
            ozel = lambda d: sum(1 for x, sabit in d["panolar"] if not sabit and x < G.TEK_PANO_TAM_ESIGI_CM)
            if tam is not None:
                olc["tamamlanan"].append({"duvar": f"{dk['tur']} {dk['yon']} {dk['c']:g}", "once": tam[0], "sonra": tam[1]})
                tamamlanan_eksen.add(dk["yon"])
            elif [p for p in ds["panolar"] if p[1]] != [p for p in dk["panolar"] if p[1]]:
                b.append(f"pano dizisi: duvar {_duvar_adi(dk)} {-kisalma:g} cm uzadı, açıklıklı ya da karkaslı pano değişti "
                         f"({[x for x, _ in dk['panolar']]} → {[x for x, _ in ds['panolar']]})")
            elif ozel(ds) > ozel(dk):
                b.append(f"pano dizisi: duvar {_duvar_adi(dk)} {-kisalma:g} cm uzadı, özel pano sayısı arttı "
                         f"({[x for x, _ in dk['panolar']]} → {[x for x, _ in ds['panolar']]})")
            else:
                olc["yeniden_dizilen"].append({"duvar": f"{dk['tur']} {dk['yon']} {dk['c']:g}", "once": [x for x, _ in dk["panolar"]],
                                               "sonra": [x for x, _ in ds["panolar"]]})
                dizilen.append({**ds, "degisim": abs(kisalma)})
            continue
        boy = _kisa_parca_dustu(dk, ds, kisalma)
        if boy is not None:
            olc["silinen"].append({"duvar": f"{dk['tur']} {dk['yon']} {dk['c']:g}", "boy": boy})
            silinen_eksen.add(dk["yon"]); silinen_boy.append((dk["yon"], boy))
        elif [p for p in ds["panolar"] if p[1]] != [p for p in dk["panolar"] if p[1]]:
            b.append(f"pano dizisi: duvar {_duvar_adi(dk)} {kisalma:g} cm kısaldı, açıklıklı ya da karkaslı pano değişti "
                     f"({[x for x, _ in dk['panolar']]} → {[x for x, _ in ds['panolar']]})")
        else:                                                 # kısa parçası olmayan kısalan duvar (veranda kenarı): Motor anahtarla yeniden dizer
            olc["yeniden_dizilen"].append({"duvar": f"{dk['tur']} {dk['yon']} {dk['c']:g}", "once": [x for x, _ in dk["panolar"]],
                                           "sonra": [x for x, _ in ds["panolar"]]})
            dizilen.append({**ds, "degisim": abs(kisalma)})
    b += [f"duvar: silinmiş hâlde kaynak evde olmayan duvar {_duvar_adi(d)}" for d in serbest]
    for yon, sil in (("x", kx), ("y", ky)):
        if kes[yon] and not any(e == yon and yakin(boy, kes[yon][1]) for e, boy in silinen_boy):
            b.append(f"kesim hattı: {kes[yon][1]:g} cm hiçbir {yon} duvarında dizilim sonundaki kısa parça değil (kesim yalnız kısa parça kadar)")
        if sil > 0 and yon not in silinen_eksen:
            b.append(f"silinen: {sil:g} cm hiçbir {yon} duvarında dizilim sonundaki kısa parça değil (silinen yalnız kısa parça kadar)")
        if sil < 0 and yon not in tamamlanan_eksen:
            b.append(f"büyüme: {-sil:g} cm hiçbir {yon} duvarında özel panoyu tam panoya (125,5) ya da yarım panoya (62,75) tamamlamıyor "
                     f"(büyüme yalnız kalan özel pano kadar, Lokman'ın ev sözüyle)")
    kisa = [f"{_duvar_adi(d)} {x:g} cm" for d in s["duvarlar"] for x, sabit in d["panolar"] if x < TOL_SILME_CM and not sabit]
    if kisa:
        b.append("kısa parça kaldı: " + ", ".join(kisa) + " (Lokman, 19:39:46 kartı \"Kısa parça silinsin\")")

    # kapı ve pencere: duvar boyunca aralığı aynı; kayan cephedeki açıklığın hattı duvarla kayar
    yer_k, yer_s = acikliklarin_yeri(kaynak), acikliklarin_yeri(ie)
    bek_yer = sorted(({**d, "hat": sy(d["hat"]) if d["yon"] == "x" else sx(d["hat"]),
                       "a0": sx(d["a0"]) if d["yon"] == "x" else sy(d["a0"]), "a1": sx(d["a1"]) if d["yon"] == "x" else sy(d["a1"])}
                      for d in yer_k), key=lambda d: (d["tur"], d["olcu"], d["duvar_tur"], d["yon"], d["hat"], d["a0"]))
    ozellik = lambda d: (d["tur"], d["olcu"], d["duvar_tur"], d["yon"])
    kalan_s, kalan_b = list(yer_s), []
    for d in bek_yer:
        e = next((e for e in kalan_s if ozellik(e) == ozellik(d) and all(yakin(d[x], e[x]) for x in ("hat", "a0", "a1"))), None)
        if e is None:
            kalan_b.append(d)
        else:
            kalan_s.remove(e)
    # BK-34: Motor'un yeniden dizdiği duvarda (kısa parçasız kısalan ya da uzayan) açıklık duvar boyunca kayabilir (oda ortasındaki pencere
    # odanın ortasında kalır); hattı ve boyu aynı, duvarın içinde, kayma duvarın değişiminden çok değil; yalnız Lokman'ın ev kartıyla
    kayan = []
    for d in list(kalan_b):
        for e in kalan_s:
            w = next((w for w in dizilen if w["yon"] == e["yon"] and w["tur"] == e["duvar_tur"] and yakin(w["c"], e["hat"])
                      and w["a0"] - YER_TOL_CM <= e["a0"] and e["a1"] <= w["a1"] + YER_TOL_CM), None)
            if (w is not None and ozellik(e) == ozellik(d) and yakin(d["hat"], e["hat"]) and yakin(d["a1"] - d["a0"], e["a1"] - e["a0"])
                    and abs(e["a0"] - d["a0"]) <= w["degisim"] + YER_TOL_CM):
                kayan.append({"aciklik": f"{d['tur']} {d['olcu']}", "duvar": f"{w['tur']} {w['yon']} {w['c']:g}",
                              "once_cm": [d["a0"], d["a1"]], "sonra_cm": [e["a0"], e["a1"]]})
                kalan_b.remove(d); kalan_s.remove(e)
                break
    if kalan_b or kalan_s:
        fark = [f"{d['tur']} {d['olcu']} ({d['duvar_tur']}, {d['yon']} duvarı) hat {d['hat']:g}, {d['a0']:g}–{d['a1']:g}" for d in kalan_b]
        b.append(f"açıklık yeri: kapı ve pencere kaynak evdeki yerinde değil (beklenen: {fark or 'sayı farkı'})")
    if kayan:
        if aciklik_sozu and aciklik_sozu.strip():
            olc["kayan_aciklik"] = kayan
        else:
            b.append("açıklık yeri: " + ", ".join(f"{a['aciklik']} ({a['duvar']}) {a['once_cm'][0]:g}–{a['once_cm'][1]:g} → "
                                                  f"{a['sonra_cm'][0]:g}–{a['sonra_cm'][1]:g}" for a in kayan)
                     + " Motor'un yeniden dizdiği duvarda kaydı; açıklığın kayması yalnız Lokman'ın ev kartıyla (--aciklik-sozu)")

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
                    b.append(f"veranda: {mk.get('ad')} silinen ya da büyüyen kadar değişir; veranda değişikliği yalnız Lokman'ın ev kartıyla "
                             f"(--veranda-sozu)")
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
        b.append("veranda: verandanın dikmesi silinen ya da büyüyen kadar kayar; veranda değişikliği yalnız Lokman'ın ev kartıyla "
                 "(--veranda-sozu)")

    # İş Emri'nin geri kalanı aynen (kimlik ve talep yazıları dışında)
    for alan in sorted((set(ie) | set(kaynak_ie)) - set(SILME_KIMLIK) - {"yapi", "mahaller", "girintiler", "acikliklar", "dikmeler"}):
        if _sayi(ie.get(alan)) != _sayi(kaynak_ie.get(alan)):
            b.append(f"{alan}: kaynak evle aynı değil")
    yk, ys = dict(kaynak_ie.get("yapi") or {}), dict(ie.get("yapi") or {})
    for alan in sorted((set(yk) | set(ys)) - {"dis_olcu_cm", "grid", "referans_model", "dizilim", "birlesimler", "ek_akslar_cm"}):
        if _sayi(ys.get(alan)) != _sayi(yk.get(alan)):
            b.append(f"yapi.{alan}: kaynak evle aynı değil")
    f_ek = {"x": sx, "x_yardimci": sx, "y": sy, "y_yardimci": sy}    # ek akslar Motor çerçevesinde: bant ve kesim hattı gibi kayar
    ek_k = yk.get("ek_akslar_cm")
    bek_ek = ({a: ([f_ek[a](float(v)) for v in vs] if a in f_ek and isinstance(vs, list) else vs) for a, vs in ek_k.items()}
              if isinstance(ek_k, dict) else ek_k)
    if _sayi(ys.get("ek_akslar_cm")) != _sayi(bek_ek):
        b.append(f"yapi.ek_akslar_cm: kaynak evle aynı değil ya da kayan cepheden başka yerde kaydı ({ek_k} → {ys.get('ek_akslar_cm')})")
    diz_k = _dizilim_bantta(_sayi({x: v for x, v in (yk.get("dizilim") or {}).items() if x != "tek_ozel_pano"}), sx, sy)
    if _sayi({x: v for x, v in diz.items() if x != "tek_ozel_pano"}) != diz_k:
        b.append("dizilim: kaynak evle aynı değil (tek özel pano anahtarı dışında; paftanın dayanak akslarında yalnız kayan cephe kayar); "
                 "kapının ve pencerenin yerini dizilim verir")

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
    ap.add_argument("--buyume-sozu", default=None,
                    help="--silme-hali ile: dış duvar kalan özel panoyu tamamlamak için dışarı kayarsa Lokman'ın o evdeki sözü ve saati "
                         "(BK-31 PR-2; tek ev sözü)")
    for ad, yardim in KESIM_SECENEKLERI:
        ap.add_argument(ad, default=None, help=yardim)
    a = ap.parse_args(argv)
    if a.standart_hal and a.silme_hali:
        print("DUR: --standart-hal ve --silme-hali ayrı kalemlerdir; birlikte verilmez"); return 2
    if (a.veranda_sozu or a.buyume_sozu or a.kesim_hatti or a.kesim_sozu or a.uclu_h_sozu or a.aciklik_sozu) and not a.silme_hali:
        print("DUR: --veranda-sozu, --buyume-sozu, --kesim-hatti ve öteki söz seçenekleri yalnız --silme-hali ile"); return 2
    if bool(a.kesim_hatti) != bool(a.kesim_sozu and a.kesim_sozu.strip()):
        print("DUR: --kesim-hatti ve --kesim-sozu birlikte verilir (içerideki hatta kesim yalnız Lokman'ın ev kartıyla; BK-34)"); return 2
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
        bulgular, o = denetle_silme(ie, kart, oku(a.silme_hali), a.veranda_sozu, a.buyume_sozu, a.kesim_hatti, a.kesim_sozu,
                                    a.uclu_h_sozu, a.aciklik_sozu)
        sil = " + ".join(f"{p['duvar']} {p['boy']:g}" for p in o["silinen"])
        tam = " + ".join(f"{p['duvar']} {p['once']:g} → {p['sonra']:g}" for p in o.get("tamamlanan") or [])
        gecti = (f"GEÇTİ: silme hâli (BK-31), kaynak evin proje kartıyla aynı; silinen {o['silinen_cm'][0]:g} / {o['silinen_cm'][1]:g} cm "
                 f"(kısa parçalar: {sil or 'yok'})"
                 + (f"; büyüyen {o['buyuyen_cm'][0]:g} / {o['buyuyen_cm'][1]:g} cm (tamamlanan: {tam}); büyüme sözü: {a.buyume_sozu}" if tam else "")
                 + (f"; veranda {'değişti' if tam else 'kısaldı'} ({', '.join(o['veranda_kisalan'])}): {a.veranda_sozu}"
                    if o["veranda_kisalan"] else "")
                 + (f"; kesim hattı {o['kesim_hatti']['yazi']}: {a.kesim_sozu}" if o.get("kesim_hatti") else "")
                 + (f"; üçlü H {', '.join(str(u['nokta_cm']) for u in o['uclu_h'])}: {a.uclu_h_sozu}" if o.get("uclu_h") else "")
                 + (f"; açıklık kaydı ({', '.join(u['aciklik'] for u in o['kayan_aciklik'])}): {a.aciklik_sozu}"
                    if o.get("kayan_aciklik") else ""))
    else:
        bulgular, o = denetle_standart(ie, kart, oku(a.standart_hal)) if a.standart_hal else denetle(ie, kart)
        gecti = "GEÇTİ: standart hâl, kaynak evin proje kartıyla aynı (D-91)" if a.standart_hal else "GEÇTİ: proje kartıyla aynı"
    print(json.dumps(o, ensure_ascii=False))
    print(gecti if not bulgular else "KALDI:\n- " + "\n- ".join(bulgular))
    return 0 if not bulgular else 1


if __name__ == "__main__":
    sys.exit(main())
