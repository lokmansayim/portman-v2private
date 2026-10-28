"""BK-12 PR-2 · Prefabrik pano evinin yükleme listesi (İE-11 M6): İş Emri ya da paftadan okunmuş geometri → liste JSON + Excel.

    python -m motor.prefabrik_liste <İş Emri.json> <çıktı klasörü> [--pafta <pafta_katmani.json>]
    python -m motor.prefabrik_liste --yapi <yapi_pafta.json> <çıktı klasörü> [--pafta <pafta_katmani.json>]

Kör test serisinin üreteci 7.3'ten gelir (13 Ekim 2026; `ie-11-pr2-kor-test` dalında `deneme/2026-10-13_kor_test_seri/yukleme_listesi.py`;
kural harfleri H1…R6 o dosyanın sürüm geçmişindedir ve satırların dayanak notlarında kalır). Kodun içindeki sabitler kural kitabına taşındı:
prefabriğe özgü ya da kitaptan farklı kurallar `kurallar/liste/prefabrik.json`'da (farklar orada `kitapla_farkli`'da beyanlı); kitapla aynı değerler
(parça boyları ve bindirmeler, levha alanları, kalınlıkları ve zayiatlar, aşık, şilte, kaplama, baş makas Z'si, dere kelepçesi, iniş, vida, elektrik,
boya ve tesisat değerleri) kural kitabının `prefabrik.json › kitap_seti`'nde sabitlenmiş setinden (`kurallar/liste/setler/`), iç duvar kalınlığı
`kurallar/model/duvar_tipleri.json`'dan okunur. Kitabın her kuralı üç yerden birindedir: okunur, `kitapla_farkli`'da ya da
`kitaptan_okunmayan`'dadır. Hiçbir adet elle yazılmaz; formül ve ölçü yazıları da kuraldan üretilir ki kural değişince adetle çelişmesin. Yalnız ürün adının ya da sabit sipariş boyunun parçası olan ölçüler (iç çektirme U'su 2440, pencere U'su 2500, kapı, kubbe
takımı, latalar, H'lar) yazıdır; levha ölçüsü kuraldaki levha alanıyla denetlenir (`levha`). LLM yok, ağ yok.

Geometri iki yoldan gelir; ikisi aynı ara yapıya (`N`) çevrilir:
  - **Motor kipi** (İş Emri): pano Motor'unun planı (`geometry.kur`).
  - **Pafta kipi** (`--yapi`): Motor'un çizemediği projelerde pano geometrisi montaj paftasından okunmuş hali (Lokman, 13 Ekim 11:45).
Üç sütun: **adet** (varsayılan), **pafta** (o projenin paftasından okunan adet; `--pafta`), **aday** (karar bekleyen ya da öteki uygulama).
Varsayılan uygulama Portatifev şablonu (Lokman, 13 Ekim 11:45 ve 14:42); ikinci şablonun (Şablon B, Kasım 2025, PK-02) farklı yaptığı
kalemler aday sütunundadır.

7.3'ten bilinen farklar (BK-12 PR-2; Lokman'ın 18 Ekim 19:22 kararları): orta iniş uzunluğa bağlı (Lokman, 13 Ekim 15:10), eşik kural kitabının
9 m'si (`prefabrik.json › inis_orta`); 7.3'ün "her saçak hattına bir orta iniş" kuralı (R3) aday sütununda. Kural kitabıyla farklı on yedi kalemde
kitap geçer: çatı kaplamasının kapatması ve panel boyu, sandviç ve tek kat panel kapaması, trapez sac mahyası, veranda tavanı, pencere alıcıya aitken
vida ve mastik, ters mahya kenar kutusu, müdahale kapağı, NYM kablo, buat kasa, alçıpan vidasının levhaları, silikonize mastik, dayson, çatı panelli
çatının kenarları ve duvar dibi (bu on yedi kalemde 7.3'ün değeri ya da yöntemi, kaldığı yerde aday sütununda).

PK-07 hedef örnekle düzeltmeler (BK-12 PR-2c; Lokman, 20 Ekim 15:27 ve 19:45–19:50): PVC betopan H'ı her evde 7 (baş makaslarda
betopanların birleşim yerlerine konur, tavanla bağı yok; Portatifev listelerindeki gibi Depo grubunda), profil vidalama aparatı yazılmaz. Kaynağı tek bir listeye dayanan kurallar `kurallar/liste/prefabrik_isaret.json`'da işaretli; satırlarının dayanağı
"Tek kaynak (zayıf)", Excel'de satır renkli. Metreyle sayılan satırların birimi m; formül yazılarında ondalık virgül.

T76 denemesinin cevapları (BK-12 PR-2d; Lokman, 20 Ekim 20:45 ve kart 20:59): 100'lük alt çerçeve dış duvarların altına (veranda sayılmaz; Motor
kipinde kapalı kısmın dış sınırı), 100'lük iç duvar varsa onların altına da; trapez çatıda panel kapaması yazılmaz; satır yazılarında "kalkan"
yerine "baş makas".

Elektrik oda kuralı (BK-12 PR-2f; Lokman, 18 Ekim 19:52, kartlar 19 Ekim 16:50 ve 22 Ekim 11:09–11:10): paftada elektrik sayımı yoksa noktalar
odalardan sayılır (`elektrik_oda`): oda başına 2 tekli priz, 1 tekli anahtar, 1 duy; açık mahale 2 glop, 1 çiftli anahtar; 15 m²'yi geçen her
15 m²'ye bir takım daha (yukarı); banyo, WC, mutfak ve hol kitabın sayılarıyla (ıslak hacimler banyo, koridor hol gibi); mutfağı ayrı mahal
olmayan evde salona yalnız tezgahın 4 tekli prizi (açık mutfak; Lokman, 23 Ekim 03:57); uydu prizi her evde 1. Sayım varsa sayım geçer, kuralın sonucu aday sütununda. Zil her
evde kitabın 1'i.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
KURAL_YOLU = KOK / "kurallar" / "liste" / "prefabrik.json"
DUVAR_TIPLERI = KOK / "kurallar" / "model" / "duvar_tipleri.json"
ISARET_YOLU = KOK / "kurallar" / "liste" / "prefabrik_isaret.json"
TEK_KAYNAK = "Tek kaynak (zayıf)"
ISARETLI = ("pencere_u_h_gecen", "omega_kapak")   # satırı `zayif(...)` ile yazılan kurallar (BK-12 PR-2c)

SURUM = "1.5 (22 Ekim 2026; kör test üreteci 7.3, kurallar kural kitabında; orta iniş 9 m, kitapla farklı on yedi kalemde kitap; PK-07 hedef örnek; T76 cevapları; 100'lük duvar omegası kirişlerin de üstünde; elektrik oda kuralı)"
GRUPLAR = {"1001": "Panel", "1002": "Metal aksam", "1003": "Kapı ve pencere", "1004": "Tavan", "1005": "Makas", "1006": "Çatı",
           "1007": "Elektrik", "1008": "Vida", "1009": "Depo", "1010": "Sıhhi tesisat", "1011": "Dere", "1012": "Boya"}
TAVAN = lambda x: int(math.ceil(x - 1e-9))
ASAGI = lambda x: int(math.floor(x + 1e-9))
MOD = 125.5                                                     # pano modülü (`geometry.MOD`); kural değil, sistemin ızgarası


def kurallari_oku(yol: Path | str | None = None) -> dict:
    """Prefabrik kuralları (`prefabrik.json`), kural kitabının o dosyada sabitlenmiş seti (`kitap_seti`, `kurallar/liste/setler/` altında;
    `PORTMAN_KURALLAR` bu listeyi etkilemez: kitapta çelik için yapılan bir değişiklik prefabrik listeyi sessizce değiştirmesin) ve duvar
    tipleri (`kurallar/model/duvar_tipleri.json`; iç duvarı olmayan planda iç duvar kalınlığı). Kaynağı tek listeye dayanan kuralların işaretleri
    `prefabrik_isaret.json › isaretler`'den (`prefabrik_isaret`; BK-12 PR-2c): her ad `prefabrik.json`'da bir kural ve adlar üretecin işaretli
    satırlarıyla (`ISARETLI`) aynı olmalı. İşaret eklemek ya da kaldırmak o satırın `zayif(...)` çağrısıyla birlikte yapılır; yalnız biri
    değişirse kurallar okunmaz (işaret sessizce yok sayılmasın, geometri hakemi PR-2c)."""
    p = json.loads(Path(yol or KURAL_YOLU).read_text(encoding="utf-8"))
    kitap = KOK / "kurallar" / "liste" / p["kitap_seti"]
    isaret = json.loads(ISARET_YOLU.read_text(encoding="utf-8"))["isaretler"]
    if set(isaret) - set(p["kurallar"]):
        raise ValueError(f"prefabrik_isaret.json: {sorted(set(isaret) - set(p['kurallar']))} prefabrik.json'da kural değil")
    if set(isaret) != set(ISARETLI):
        raise ValueError(f"prefabrik_isaret.json: işaretler {sorted(isaret)} üretecin işaretli satırlarıyla {sorted(ISARETLI)} aynı değil "
                         "(işaret, satırın `zayif(...)` çağrısıyla birlikte eklenir ya da kalkar)")
    return {"prefabrik": p, "ortak": json.loads(kitap.read_text(encoding="utf-8")), "duvar_tipleri": json.loads(DUVAR_TIPLERI.read_text(encoding="utf-8")),
            "prefabrik_isaret": isaret}


def _ortak(k: dict, *yol):
    v = k
    for a in yol:
        v = v[a]
        if isinstance(v, dict) and "deger" in v:
            v = v["deger"]
    return v


def _dt(k: dict, *yol):
    v = k
    for a in yol:
        v = v[a]
    return v


def _pr(k: dict, yol: str):
    a, *alt = yol.split(".")
    v = k["kurallar"][a]["deger"]
    for b in alt:
        v = v[b]
    return v


def _isaret(k: dict, kural: str) -> str:
    """Kaynağı zayıf kuralın işareti (`prefabrik_isaret.json`; CIO notu 5, BK-12 PR-2c). Yalnız `tek_kaynak` geçer; başka bir değer listeyi
    durdurur (işaret sessizce düşmesin). İşaret yalnız o kuralın satırı yazılırken okunur."""
    v = k[kural]
    if v != "tek_kaynak":
        raise ValueError(f"prefabrik_isaret.json: {kural} işareti {v!r} tanınmıyor (yalnız 'tek_kaynak')")
    return v


def siparis(cm: float, k: dict) -> int:
    """Pano sipariş boyu (PK-01 dersi 2, Portatifev): net boy − 2,5 mm, 5 mm'ye aşağı. PK-01'de 50 / 50; PK-02'de 39 → 390, 31 → 310.
    Modül katı (n × 125,5) panoda n × 1250 (J1; PK-03: 251 → 2500)."""
    s = _pr(k, "siparis_boyu")
    n = round(cm / MOD)
    if n >= 1 and abs(cm - n * MOD) < s["modul_tolerans_cm"]:
        return s["modul_siparis_mm"] * n
    return int(math.floor((cm * 10 - s["kesinti_mm"]) / s["yuvarlama_mm"] + 1e-6) * s["yuvarlama_mm"])


def mm(cm: float) -> str:
    v = round(cm * 10, 1)
    return f"{v:g}".replace(".", ",")


def sy(x: float) -> str:
    """Kuraldan gelen sayının formül ve ölçü yazısı (Türkçe ondalık): 2.3 → "2,3", 3.75 → "3,75". Yazılar kuraldan üretilir ki kural
    değişince adetle çelişmesin (geometri hakemi, BK-12 PR-2)."""
    return f"{round(x, 4):g}".replace(".", ",")


def od(x: float, b: int = 2) -> str:
    """Geometriden gelen sayının formül yazısı (Türkçe ondalık, sabit basamak): 112.917 → "112,92" (CIO notu 6, BK-12 PR-2c)."""
    return f"{x:.{b}f}".replace(".", ",")


def mm_m(m: float) -> str:
    """Metre → mm (parça boyu yazısı): 2.5 → "2500"."""
    return f"{round(m * 1000)}"


def ye(n: int) -> str:
    """Sayının yönelme hâli (yuvarlama yazısı): 100 → "100'e", 250 → "250'ye", 10 → "10'a"."""
    if n % 1000 == 0 or n % 100 == 0:
        ek = "e"                                                # bin, yüz
    elif n % 10 == 0:
        ek = {1: "a", 2: "ye", 3: "a", 4: "a", 5: "ye", 6: "a", 7: "e", 8: "e", 9: "a"}[(n // 10) % 10]
    else:
        ek = {1: "e", 2: "ye", 3: "e", 4: "e", 5: "e", 6: "ya", 7: "ye", 8: "e", 9: "a"}[n % 10]
    return f"{n}'{ek}"


def levha(olcu: str, alan_m2: float) -> str:
    """Levha ölçüsü yazısı (son iki sayı en × boy, mm). Alan kural kitabından gelir, ölçü ürünün adıdır; biri değişip öteki değişmezse
    adet ile ölçü çelişirdi, o yüzden çelişince liste üretilmez."""
    en, boy = (float(x) for x in olcu.split(" × ")[-2:])
    if abs(en * boy / 1e6 - alan_m2) > 1e-3:
        raise ValueError(f"levha ölçüsü {olcu} kuraldaki levha alanıyla ({alan_m2} m²) çelişiyor")
    return olcu


def pencere_olcusu(olcu: str) -> tuple[int, int]:
    en, boy = olcu.lower().replace("/", "x").split("x")
    return int(float(en)), int(float(boy))


# ── geometri: Motor kipi ────────────────────────────────────────────────────────
def model_motor(ie: dict) -> dict:
    from . import geometry as G
    from shapely.geometry import LineString, Point, box
    from shapely.ops import unary_union
    plan = G.kur(json.loads(json.dumps(ie)))
    y = ie["yapi"]; c = ie.get("cati") or {}
    mx = c.get("makas_ekseni", "x") == "x"                     # makaslar x'i geçiyorsa saçak duvarları y yönünde koşar
    eave_yon = "y" if mx else "x"
    panolar, ekler = [], []
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            panolar.append({"duvar": d.tur, "kal_mm": round(2 * d.h * 10), "boy": p.boy,
                            "aciklik": None if a is None else {"tur": a.tur, "olcu": a.olcu, "genislik": a.genislik, "mentese": a.mentese,
                                                                "dograma": a.dograma}})
        for a_, _b in zip(d.panolar, d.panolar[1:]):
            x, yy = (a_.a1, d.c) if d.yon == "x" else (d.c, a_.a1)
            uclu = any(abs(h.x - x) <= d.h + 3.5 and abs(h.y - yy) <= d.h + 3.5 for h in plan.h_baglantilar)
            ekler.append({"duvar": d.tur, "cins": "uclu" if uclu else "pano_eki", "sacak": d.yon == eave_yon})
            if any(abs(ax - x) <= d.h + 3.5 and abs(ay - yy) <= d.h + 3.5 for ax, ay in plan.arti_birlesimler):
                ekler[-1]["arti"] = True                        # BK-14: dört kollu birleşimdeki ek; profili kitapta yok, satır uyarır
    kapali = [m for m in plan.mahaller.values() if not (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    acik = [m for m in plan.mahaller.values() if (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    g = unary_union([plan.footprint()] + [m.poly for m in plan.mahaller.values() if m.poly is not None] + [box(*r) for r in plan.dikmeler])
    bx0, by0, bx1, by1 = g.bounds
    W, D = bx1 - bx0, by1 - by0
    fp = plan.footprint()
    # dış duvar boyu: kapalı kısmın dış sınırı; veranda ve dikmeler sayılmaz (Lokman, 20 Ekim 20:45; BK-12 PR-2d). Odalar çokgende delik, `.length` değil
    dis_duvar_m = sum(g_.exterior.length for g_ in getattr(fp, "geoms", [fp])) / 100
    # çatı kenarına gelmeyen dış duvarlar: kapalı kısmın açık mahallerle ortak sınırı. Motor'un çatısı dış dikdörtgeni örter; veranda dış çizgide,
    # ona bakan duvarlar çatının altında kalır ve 100'lük duvar omegası alır (Lokman, 21 Ekim 16:22; BK-12 PR-2e; PK-01 3,34 + 2,00)
    ic_kalan_m = sum(g_.exterior.intersection(m.poly).length for g_ in getattr(fp, "geoms", [fp]) for m in acik if m.poly is not None) / 100
    # duvarsız sınır (İş Emri `acik_sinirlar`, ör. salon–mutfak): üstüne kiriş gelir (Lokman, kart 22 Ekim "Evet, gelir"; E5, TS-01). Sınır
    # çizgileri ızgara gözü başına; aynı hattaki bitişik parçalar tek kiriş, boyu aks arası. Motor iki açık mahalin (ör. iki veranda) arasına da
    # çizgi koyar; o sınır iki oda arası değil, kiriş sayılmaz (geometri hakemi 3. tur)
    acik_g = [m.poly for m in acik if m.poly is not None]
    hatlar = {}
    for x0, y0, x1, y1 in plan.acik_sinir_cizgileri:
        orta = Point((x0 + x1) / 2, (y0 + y1) / 2)
        if any(g_.distance(orta) < 0.5 for g_ in acik_g):
            continue
        dik = abs(x1 - x0) < 1e-6
        hatlar.setdefault(("y" if dik else "x", round(x0 if dik else y0, 2)), []).append(tuple(sorted((y0, y1) if dik else (x0, x1))))
    ic_kirisler = []
    for _h, parcalar in sorted(hatlar.items()):
        parcalar.sort()
        u0, u1 = parcalar[0]
        for p0, p1 in parcalar[1:]:
            if p0 <= u1 + 0.5:
                u1 = max(u1, p1)
            else:
                ic_kirisler.append(round(u1 - u0, 2)); u0, u1 = p0, p1
        ic_kirisler.append(round(u1 - u0, 2))

    def oda(m):
        x0, y0, x1, y1 = m.poly.bounds
        en, derin = ((y1 - y0), (x1 - x0)) if mx else ((x1 - x0), (y1 - y0))
        return {"ad": m.ad, "tur": m.tur, "alan_m2": m.alan_m2, "en_cm": en, "derin_cm": derin}
    kirisler = []
    dis_ad = {v["ad"] for v in plan.dis_verandalar}
    if plan.dikmeler and acik:
        for v in acik:
            if v.ad in dis_ad:
                continue                                       # BK-14: taşan verandanın üç açık kenarı aşağıda, kenar kenar
            vx0, vy0, vx1, vy1 = v.poly.bounds
            yanlar = set()
            for (x0, y0, x1, y1, *_r) in plan.acik_kenarlar:
                if v.poly.buffer(1.0).contains(LineString([(x0, y0), (x1, y1)])):
                    yanlar.add("x" if abs(y1 - y0) < 1e-6 else "y")
            kirisler += [((vx1 - vx0) if e == "x" else (vy1 - vy0)) for e in sorted(yanlar)]
    for v in plan.dis_verandalar:                              # BK-14: dış kenar ve iki yan (TK-01 geçici yolu, PK-03/PK-06 paftası gibi)
        kirisler += [max(x1 - x0, y1 - y0) for (x0, y0, x1, y1) in v["kenarlar"]]
    t_dis = 2 * next(d.h for d in plan.duvarlar if d.tur == "dis")
    brut = W * D
    if plan.dis_verandalar:                                    # BK-14: ana çatı gövdeyi örter; brüt gövde + veranda, dış kutunun boş köşeleri sayılmaz
        gx0, gy0, gx1, gy1 = G.govde_kutusu(plan)
        GW, GD = gx1 - gx0, gy1 - gy0
        brut = GW * GD + sum((v["rect"][2] - v["rect"][0]) * (v["rect"][3] - v["rect"][1]) for v in plan.dis_verandalar)
    else:
        GW, GD = W, D
    aciklik, bina_boyu = (GW, GD) if mx else (GD, GW)
    # kitap `kablo_en_uzak_mesafe`: sigorta kutusu (yeri İş Emri'nde yok) giriş kapısında; kapının ortasından kapalı kısmın en uzak köşesine kuş uçuşu
    kose = [q for g_ in getattr(fp, "geoms", [fp]) for q in g_.exterior.coords]
    giris = next(((d, p) for d in plan.duvarlar if d.tur == "dis" for p in d.panolar if p.acilim and p.acilim.tur == "dis_kapi"), None)
    if giris:
        d, p = giris
        orta = (p.a0 + p.a1) / 2 + p.acilim.kayma
        kutu = (orta, d.c) if d.yon == "x" else (d.c, orta)
        en_uzak = {"m": max(math.hypot(qx - kutu[0], qy - kutu[1]) for qx, qy in kose) / 100, "nereden": "giriş kapısından kapalı kısmın en uzak köşesi"}
    else:
        fx0, fy0, fx1, fy1 = fp.bounds
        en_uzak = {"m": math.hypot(fx1 - fx0, fy1 - fy0) / 100, "nereden": "giriş kapısı yok: kapalı kısmın köşegeni"}
    return {"kaynak": "Motor", "H0": float(y.get("duvar_yuksekligi_cm", 250)), "W": W, "D": D, "brut_m2": round(brut / 1e4, 3),
            "dis_cevre_m": dis_duvar_m, "ic_kalan_dis_duvar_m": ic_kalan_m, "ic_kirisler_cm": ic_kirisler, "t_dis": t_dis, "panolar": panolar, "ekler": ekler,
            "koseler": dict(Counter("dis" if kk.tur == "dis" else "ic" for kk in plan.koseler)), "dikmeler": len(plan.dikmeler),
            "veranda_kenarlari_cm": kirisler, "kapali": [oda(m) for m in kapali], "acik": [{**oda(m), "tur": "veranda"} for m in acik],
            "sigorta_en_uzak": en_uzak,
            "cati": [{"ad": "ana çatı", "tip": c.get("tip", "besik"), "aciklik_cm": aciklik, "boy_cm": bina_boyu,
                      "egim_yuzde": float(c.get("egim_yuzde", 33)), "sacak_cm": float(c.get("sacak_cm", 30)), "kalkan": 2,
                      "makas_kosu_cm": bina_boyu - 2 * t_dis}] + _veranda_catilari(plan, ie),
            "ozellikler": ie.get("ozellikler") or {}, "alici_ait": ie.get("alici_ait") or {}, "is_emri_no": ie.get("is_emri_no"),
            "kod": y.get("referans_model")}


def _kucuk(x) -> str:
    """Türkçe küçük harf: "İ" → "i", "I" → "ı" (`motor/yerlesim/girdi.kucuk` ile aynı)."""
    return str(x).replace("İ", "i").replace("I", "ı").lower()


def _veranda_catilari(plan, ie: dict) -> list[dict]:
    """BK-14: taşan verandanın çatısı, açık çatı parçası olarak (pafta kipindeki PK-03, PK-06, TS-01 sundurması gibi). Beşiğin mahyası cepheye
    diktir (`veranda.cati`): açıklık cephe boyunca en, boy derinlik; kalkanı dış kenarda (1), altı açık. Mahyası ana çatının mahyasına paralelse
    (veranda ana çatının kalkan yüzünde, TK-01) dere içi yok, mahya ve iki saçak derinlik + saçak; ana çatının saçak yüzündeyse çapraz beşiktir,
    mahya ana çatının yüzüne kadar uzar (5.1'in dere hesabıyla aynı yatay), saçaklar ana çatının saçak hattına kadar (iki saçak farklıysa
    farkı kadar; geometri hakemi, 27 Ekim). Tek eğim dışarı iner:
    açıklık derinlik, boy en; tek saçak hattı dış kenarda, iki yan saçakla."""
    from . import veranda as VR
    if not plan.dis_verandalar:
        return []
    ana_eg = float((ie.get("cati") or {}).get("egim_yuzde", 33)) / 100
    ana_s = float((ie.get("cati") or {}).get("sacak_cm", 30))
    ana_mahya = VR.ana_mahya_yonu(ie)
    out = []
    for v in plan.dis_verandalar:
        c = v["cati"]; s = float(c["sacak_cm"]); en, derin = float(v["en"]), float(v["derinlik"])
        ad = f"{_kucuk(v['ad'])} çatısı"
        if c["tip"] == "besik":
            mahya = "y" if v["cephe"] in ("on", "arka") else "x"
            capraz = mahya != ana_mahya
            if capraz:                                     # saçak hattı dış kenardan ana çatının saçak hattına; mahya ana çatının yüzüne
                b = (en / 2 + s) * (c["egim_yuzde"] / 100) / max(ana_eg, 1e-6)
                out.append({"ad": ad, "tip": "besik", "aciklik_cm": en, "boy_cm": derin, "egim_yuzde": float(c["egim_yuzde"]), "sacak_cm": s,
                            "kalkan": 1, "capraz": True, "acik": True, "mahya_boy_cm": round(derin + s - ana_s + b, 2),
                            "sacak_hatlari_m": [round((derin + s - ana_s) / 100, 3)] * 2,
                            "not": "Motor (BK-14): ana çatının saçak yüzüne dik beşik; mahya ana çatının yüzüne kadar"})
            else:
                out.append({"ad": ad, "tip": "besik", "aciklik_cm": en, "boy_cm": derin, "egim_yuzde": float(c["egim_yuzde"]), "sacak_cm": s,
                            "kalkan": 1, "capraz": False, "acik": True, "mahya_boy_cm": derin + s,
                            "sacak_hatlari_m": [round((derin + s) / 100, 3)] * 2,
                            "not": "Motor (BK-14): ana çatının kalkan yüzünde, ana çatıya paralel küçük beşik; dış kenarda saçak"})
        else:
            out.append({"ad": ad, "tip": "tek_yon", "aciklik_cm": derin, "boy_cm": en, "egim_yuzde": float(c["egim_yuzde"]), "sacak_cm": s,
                        "kalkan": 0, "acik": True, "sacak_hatlari_m": [round((en + 2 * s) / 100, 3)],
                        "not": "Motor (BK-14): cepheden dışarı inen tek eğim; dış kenarda ve iki yanda saçak"})
    t_dis = 2 * next(d.h for d in plan.duvarlar if d.tur == "dis")
    for c in out:                                              # makas koşusu pafta kipinin varsayılanıyla aynı (`model_pafta`)
        c["makas_kosu_cm"] = c["boy_cm"] - 2 * t_dis
    return out


# ── geometri: pafta kipi ────────────────────────────────────────────────────────
def model_pafta(yp: dict) -> dict:
    """`yapi_pafta.json`: paftadan okunmuş geometri. Alanlar `model_motor` ile aynı; yalnız veranda kirişlerinin boyu
    `veranda_kirisleri_cm`'de paftadan okunmuş olarak gelir (Motor kipi açık kenarları verir, kiriş boyu kuraldan). Çatı kenarında olmayan kirişler
    (paftadaki yeşil kesikli profil: duvarsız açıklık, veranda ortası) isteğe bağlı `ic_kirisler_cm`'de; Motor kipinde iki oda arasındaki duvarsız sınırdan. L biçimli bir oda birden çok
    dikdörtgenle, aynı adla gelir. Sigortadan en uzak mesafe isteğe bağlı `sigorta_en_uzak`'ta, Motor kipindeki gibi `{"m": metre, "nereden": yazı}`
    (paftada sigorta kutusundan kapalı kısmın en uzak köşesine); okunmadıysa yoktur ve NYM dış ölçünün köşegenini alır (BK-12 PR-2f)."""
    N = dict(yp)
    N["kaynak"] = "pafta"
    N.setdefault("sigorta_en_uzak", None)
    se = N["sigorta_en_uzak"]
    if se is not None and not (isinstance(se, dict) and set(se) == {"m", "nereden"} and isinstance(se["m"], (int, float))
                               and not isinstance(se["m"], bool) and se["m"] > 0 and isinstance(se["nereden"], str) and se["nereden"].strip()):
        raise ValueError("pafta kipi: `sigorta_en_uzak` {\"m\": sıfırdan büyük metre, \"nereden\": ölçünün nereden alındığı} olmalı")
    N.setdefault("brut_m2", round(yp["W"] * yp["D"] / 1e4, 3))
    if "dis_cevre_m" not in N:
        if N.get("acik") or N.get("dikmeler"):
            raise ValueError("pafta kipi: verandalı yapıda dış duvar boyu (`dis_cevre_m`) paftadan okunmalı; dış dikdörtgen verandayı da sayar "
                             "(alt çerçeve yalnız dış duvarların altına: Lokman, 20 Ekim 20:45)")
        N["dis_cevre_m"] = 2 * (yp["W"] + yp["D"]) / 100       # verandasız: dikdörtgende ve köşesi çentikli L'de duvar boyu
    if "ic_kalan_dis_duvar_m" not in N:
        if N.get("acik") or N.get("dikmeler"):
            raise ValueError("pafta kipi: verandalı yapıda çatı kenarına gelmeyen dış duvar boyu (`ic_kalan_dis_duvar_m`) paftadan okunmalı; "
                             "verandaya bakan duvarlar 100'lük duvar omegası alır (Lokman, 21 Ekim 16:22)")
        N["ic_kalan_dis_duvar_m"] = 0.0                          # verandasız: bütün dış duvarlar çatı kenarında
    ik = N.get("ic_kirisler_cm")
    if ik is not None and not (isinstance(ik, list) and all(isinstance(x, (int, float)) and x > 0 for x in ik)):
        raise ValueError("pafta kipi: `ic_kirisler_cm` kiriş boylarının listesi olmalı (cm, sıfırdan büyük)")
    for c in N["cati"]:
        c.setdefault("kalkan", 2 if c["tip"] == "besik" else 0)
        c.setdefault("makas_kosu_cm", c["boy_cm"] - 2 * N["t_dis"])
    return N


def omega_hatlari(kapali, aralik_m: float, duvar_yuzu: bool = False) -> tuple[float, int]:
    """Tavan omega hatları: her kapalı odada mahyaya paralel, `aralik_m`'de bir; hat sayısı oda derinliği ÷ aralık en yakın tamsayı
    (en az 1), hat boyu oda net genişliği (PK-02 tavan planı: banyo 2, yatak 2, hol 1, mutfak 2, salon 3). Döner: (toplam m, hat).
    `duvar_yuzu` (O5; PK-07 ters tavan planı): her gözde iki duvar yüzünde de hat → ⌊derinlik ÷ aralık⌋ + 1."""
    L, n_top = 0.0, 0
    for m in kapali:
        n = (int(math.floor(m["derin_cm"] / 100 / aralik_m + 1e-9)) + 1) if duvar_yuzu else max(1, int(math.floor(m["derin_cm"] / 100 / aralik_m + 0.5)))
        L += n * m["en_cm"] / 100; n_top += n
    return L, n_top


def cati_olculeri(c: dict) -> dict:
    sac = c["sacak_cm"] / 100; eg = c["egim_yuzde"] / 100
    if c["tip"] == "besik":
        egik = (c["aciklik_cm"] / 200 + sac) * math.sqrt(1 + eg * eg); yuz = 2; sacak_hat = 2
    else:                                                       # tek yön: tek yüz, tek dere hattı; saçak yalnız alçak kenarda (L2)
        egik = (c["aciklik_cm"] / 100 + sac) * math.sqrt(1 + eg * eg); yuz = 1; sacak_hat = 1
    mahya_boy = c["mahya_boy_cm"] / 100 if c.get("mahya_boy_cm") else c["boy_cm"] / 100 + 2 * sac
    hatlar = list(c.get("sacak_hatlari_m") or [mahya_boy] * sacak_hat)      # pafta kipi: paftadaki gerçek saçak / dere hatları
    return {"sac": sac, "eg": eg, "egik": egik, "yuz": yuz, "sacak_hat": sacak_hat, "mahya_boy": mahya_boy, "hatlar": hatlar}


# kitabın oda kuralındaki nokta adı → pafta katmanındaki elektrik sayımının adı (`prefabrik.json › elektrik`)
ELEKTRIK_NOKTALARI = {"tijli_duy": "tavan_armaturu", "glop": "glop", "tekli_anahtar": "anahtar_tekli", "cift_anahtar": "anahtar_cift",
                      "tekli_priz": "priz_tekli", "cift_priz": "priz_cift", "uydu_prizi": "uydu_prizi"}


def elektrik_oda(N: dict, EO, odalar_k, AM) -> tuple[dict, dict]:
    """Elektrik noktalarının oda kuralı (`prefabrik.json › elektrik_oda`; BK-12 PR-2f). Odalar ve açık mahaller adla birleşir (L biçimli oda
    aynı adlı parçalarla gelir, buat kasadaki gibi tek oda; aynı adlı parçalar farklı türdeyse liste üretilmez). Banyo, WC, mutfak ve hol kitabın
    sayılarını alır (`kitaptan`; kitap `elektrik_oda.odalar`; ıslak hacim türleri banyo, koridor hol gibi); öteki her oda oda takımını, açık mahal
    veranda takımını alır. Takım sayısı alan ÷ `takim_m2`, yukarı, en az 1 (Lokman, 18 Ekim 19:52; kartlar 19 Ekim 16:50 ve 22 Ekim 11:10).
    Mutfak ayrı mahal değilse (açık mutfak, `elektrik_acik_mutfak`; planlayıcı açık mutfağı salona koyar) `AM["oda"]` türündeki ilk oda kendi
    takımını alır, ona yalnız tezgahın prizleri (`AM["ek"]`) eklenir (Lokman, 23 Ekim 03:57); o oda da yoksa satırın yazısı uyarıyla başlar,
    girdide hiç kapalı oda yoksa da (sessiz 0 değil). Uydu prizi her evde `uydu_prizi_ev_basina`
    (kart 22 Ekim 11:09). Döner: ({pafta katmanındaki ad: adet}, {pafta katmanındaki ad: oda oda döküm yazısı})."""
    say = dict.fromkeys(ELEKTRIK_NOKTALARI.values(), 0)
    dokum = {a: [] for a in say}
    tm = EO["takim_m2"]

    def takim(alan):
        return max(1, TAVAN(alan / tm))

    def alan_yazisi(alan, t):                                   # takım sayısı yazıdaki alandan da çıksın (15,04 m² "15,0" değil)
        b = 1
        while b < 6 and takim(round(alan, b)) != t:
            b += 1
        return od(alan, b)

    def topla(ad, sayilar, t=1, alan=None, ek=""):
        for kk in sayilar:
            if kk not in ELEKTRIK_NOKTALARI:
                raise ValueError(f"elektrik oda kuralı: {kk!r} tanınmıyor ({', '.join(ELEKTRIK_NOKTALARI)})")
            n = sayilar[kk]
            if n:
                a = ELEKTRIK_NOKTALARI[kk]
                say[a] += t * n
                dokum[a].append(f"{ad}: {n}{ek}" if t == 1 else f"{ad} ({alan_yazisi(alan, t)} m²): {t} takım × {n}")
    birlesik = {}
    for acik, mahaller in ((False, N["kapali"]), (True, N["acik"])):
        for m in mahaller:
            b = birlesik.setdefault((acik, m["ad"]), {"tur": m["tur"], "alan": 0.0})
            if b["tur"] != m["tur"]:
                raise ValueError(f"elektrik oda kuralı: {m['ad']!r} adlı parçalar farklı türde ({b['tur']}, {m['tur']}); aynı adlı parçalar tek oda sayılır")
            b["alan"] += m["alan_m2"]
    KT = EO["kitaptan"]

    def kitap_odasi(tur):
        if KT[tur] not in odalar_k:
            raise ValueError(f"elektrik oda kuralı: {tur} kitabın {KT[tur]!r} odasıyla sayılır, kitapta yok")
        return odalar_k[KT[tur]]
    odalar = [(ad, b) for (acik, ad), b in birlesik.items() if not acik]
    mutfak_var = any(b["tur"] == "mutfak" for _, b in odalar)
    acik_mutfak = None if mutfak_var else next((ad for ad, b in odalar if b["tur"] == AM["oda"]), None)
    for (acik, ad), b in birlesik.items():
        if acik:
            topla(ad, EO["acik_takimi"], takim(b["alan"]), b["alan"])
        elif b["tur"] in KT:
            topla(ad, kitap_odasi(b["tur"]), ek=" (kitap)")
        else:
            topla(ad, EO["oda_takimi"], takim(b["alan"]), b["alan"])
        if not acik and ad == acik_mutfak:
            topla(f"{ad} (açık mutfak)", AM["ek"], ek=" (tezgah)")
    if not odalar:                                              # odasız girdi: oda noktaları sayılmadı (0 kural sonucu değil)
        uyari = {a: "UYARI: girdide kapalı oda yok; oda noktaları sayılmadı." for a in say if a != "uydu_prizi"}
    elif not (mutfak_var or acik_mutfak):
        uyari = {ELEKTRIK_NOKTALARI[kk]: "UYARI: mutfak ayrı mahal değil, açık mutfağın odası da yok; tezgahın prizleri yazılmadı." for kk in AM["ek"]}
    else:
        uyari = {}
    u = EO["uydu_prizi_ev_basina"]
    say["uydu_prizi"] += u
    dokum["uydu_prizi"].append(f"her evde {u}")
    return say, {a: " ".join(x for x in (uyari.get(a), " + ".join(d)) if x) for a, d in dokum.items()}


def liste(N: dict, kurallar: dict | None = None, pafta: dict | None = None) -> dict:
    kurallar = kurallar or kurallari_oku()
    k, R = kurallar["ortak"], kurallar["prefabrik"]
    r = lambda yol: _pr(R, yol)
    zay = lambda a: 1 + _ortak(k, "zayiat", a)                  # kitabın zayiatı (fire çarpanı)
    lev = lambda a: _ortak(k, "levha_m2", a)
    pb = lambda a: _ortak(k, "parca_boyu_m", a)
    H0 = N["H0"]
    ISLAK = tuple(r("islak_hacim"))
    PENCERE_UST_KOTU_CM = r("pencere_ust_kotu_cm")
    ASMA_OMEGA_ARALIK_M, TERS_OMEGA_ARALIK_M = r("tavan_omegasi_aralik_m.asma"), _ortak(k, "tavan_omegasi_aralik_m")   # ters: kitabın 0,60
    TAVAN_H_ARALIK_M = r("tavan_h_aralik_m")
    ps_ = r("pencere_sinifi")
    kucuk = _kucuk
    oz = {kucuk(kk): kucuk(v) for kk, v in (N.get("ozellikler") or {}).items()}
    alici = [kucuk(x) for x in ((N.get("alici_ait") or {}).get("kalemler") or [])]
    pencere_alici = any("pencere" in x for x in alici) or "alıcı" in oz.get("pencere rengi", "")
    satirlar = []
    P = pafta or {}
    kaynak_ad = "Motor planından" if N["kaynak"] == "Motor" else "paftadan okunan geometriden"

    def pk(*yol):
        v = P
        for a in yol:
            v = (v or {}).get(a)
        return (v or {}).get("adet"), (v or {}).get("not", "")

    def ekle(grup, kalem, olcu, adet, dayanak, formul, kaynak="", birim="adet", pafta=None, aday=None, aday_notu=""):
        pa, pn = pk(*pafta) if pafta else (None, "")
        satirlar.append({"grup": grup, "grup_adi": GRUPLAR[grup], "kalem": kalem, "olcu": olcu, "adet": adet, "birim": birim, "dayanak": dayanak,
                         "formul": formul, "kaynak": kaynak, "pafta": pa, "pafta_notu": pn, "aday": aday, "aday_notu": aday_notu})

    def zayif(kural: str) -> str:
        """Kaynağı tek listeye dayanan kuralın satır dayanağı (`prefabrik_isaret.json`; CIO notu 5, BK-12 PR-2c)."""
        _isaret(kurallar["prefabrik_isaret"], kural)
        return TEK_KAYNAK

    def urun_adi(ad: str) -> str:
        """Listede üreticinin adı (kitap `urun_adlari`; Lokman, 8 Ekim 00:45: "üreticide ne yazıyorsa onu yaz")."""
        for eski, yeni in _ortak(k, "urun_adlari", "degistir"):
            if eski in ad:
                return ad.replace(eski, yeni)
        return ad

    bina_m2 = N["brut_m2"]
    tavan_kuru = sum(x["alan_m2"] for x in N["kapali"] if x["tur"] not in ISLAK)
    tavan_islak = sum(x["alan_m2"] for x in N["kapali"] if x["tur"] in ISLAK)
    tavan_net = tavan_kuru + tavan_islak
    kubbeler = [c for c in N["cati"] if c.get("kubbe")]          # R6: kubbe genel çatı satırlarına girmez, takımı ayrı
    C = [(c, cati_olculeri(c)) for c in N["cati"] if not c.get("kubbe")]
    ana, ao = C[0]

    def kubbe_takimi(grup):
        for g, kalem, olcu, n in r("kubbe_takimi"):
            if g == grup:
                ekle(g, kalem, olcu, n * len(kubbeler), "Kural (Lokman 13.10, R6)", f"kubbe başına {n} × {len(kubbeler)} kubbe",
                     "E2 − E3 (inceleme setinin kubbeli ve kubbesiz iki projesi); PK-08 aynı takım, makas ve membransız")
    acl = [p["aciklik"] for p in N["panolar"] if p["aciklik"]]
    pen = [a for a in acl if a["tur"] == "pencere"]
    vasistas = lambda a: pencere_olcusu(a["olcu"])[0] <= ps_["vasistas_en_cm"] and pencere_olcusu(a["olcu"])[1] <= ps_["vasistas_boy_cm"]   # 7.1
    standart = lambda a: pencere_olcusu(a["olcu"])[0] == ps_["standart_en_cm"]                  # 7.1: 120 genişlikte her pencere üst + alt panel (H7)
    cift = {id(a) for a in pen if not standart(a) and not vasistas(a)}                               # L1: karkaslı özel pencere panosu
    pen_k = [a for a in pen if not vasistas(a) and id(a) not in cift]   # ayrı karkaslı pencereler (vasistas ve iki modüllük hariç)

    # ── 1001 Panel ──────────────────────────────────────────────────────────
    fugali = "fugalı" in oz.get("açıklama", "") or "fugali" in oz.get("açıklama", "")
    ic_kal = Counter(p["kal_mm"] for p in N["panolar"] if p["duvar"] == "ic").most_common(1)[0][0] if any(p["duvar"] == "ic" for p in N["panolar"]) else _dt(kurallar["duvar_tipleri"], "tipler", "PE-IC-60", "anma_mm")
    sayac = Counter()
    for p in N["panolar"]:
        kal_mm = p["kal_mm"]
        kal = "100'lük" if kal_mm >= 100 else "60'lık"          # 6.1: iç duvar 100 mm olabilir (PK-07 özellik tablosu)
        fg = " (FUGALI)" if (fugali and p["duvar"] == "dis") else ""   # O1: fugalı dış cephede dış panolar ayrı satır (PK-07)
        L = siparis(p["boy"], R); a = p["aciklik"]
        if a is None:
            sayac[(f"{kal} yapıştırma dolu pano{fg}", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "sipariş boyu (PK-01 dersi 2)")] += 1
        elif a["tur"] == "pencere":
            en, boy = pencere_olcusu(a["olcu"])
            if vasistas(a):
                sayac[(f"{kal} yapıştırma dolu vasistaslı pano ({en}/{boy}){fg}", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "vasistaslı pano")] += 1
            elif id(a) in cift:
                sayac[(f"Karkaslı özel pencere panosu ({en}/{boy}){fg}", f"{kal_mm} × {L} × {mm(H0)}", "Kural (L1)", "standart dışı pencere panosu tek parça (PK-03 160/180, PK-05 80/120)")] += 1
            else:
                ust = H0 - PENCERE_UST_KOTU_CM
                sayac[(f"Pencere üst panel{fg}", f"{kal_mm} × {L} × {mm(ust)}", "Liste kuralı", "pencereli pano listede üst + alt panel")] += 1
                sayac[(f"Pencere alt panel ({en}/{boy}){fg}", f"{kal_mm} × {L} × {mm(PENCERE_UST_KOTU_CM - boy)}", "Liste kuralı",
                       f"alt panel = {sy(PENCERE_UST_KOTU_CM)} − pencere boyu (H7)")] += 1
        elif a["tur"] == "dis_kapi":
            sayac[(f"Karkaslı çelik kapı panosu{fg}", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "dış kapı boşluklu pano")] += 1
        elif a["tur"] == "ic_kapi":
            sayac[(f"{kal} karkaslı + kasalı pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "iç kapı boşluklu pano")] += 1
        else:
            sayac[(f"{kal} geçişli pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "kapısız geçiş")] += 1
    for (kalem, olcu, dayanak, kaynak), n in sorted(sayac.items(), key=lambda x: (x[0][0], -int(x[0][1].split(" × ")[1]))):
        ekle("1001", kalem, olcu, n, dayanak, f"{kaynak_ad} sayım", kaynak)

    if kubbeler:
        kubbe_takimi("1001")

    # ── 1002 Metal aksam ────────────────────────────────────────────────────
    kc = N["koseler"]
    if ic_kal >= 100:                                          # 6.1: iç duvar 100 → iç köşe de 10'luk (PK-07)
        ekle("1002", "10'luk köşe direği 100 × 100", f"100 × 100 × {mm(H0)}", kc.get("dis", 0) + kc.get("ic", 0), "Sayım",
             f"köşe parçası (dış {kc.get('dis', 0)} + iç {kc.get('ic', 0)}; iç duvar 100)", "PK-07 5 tuttu")
    else:
        ekle("1002", "10'luk köşe direği 100 × 100", f"100 × 100 × {mm(H0)}", kc.get("dis", 0), "Sayım", "köşe parçası", "özel köşe B, C, D'nin kuralı yok (soru 2)")
        ekle("1002", "6'lık köşe direği 60 × 60", f"60 × 60 × {mm(H0)}", kc.get("ic", 0), "Sayım", "iç köşe")
    if kc.get("ozel"):                                          # O2: L planın iç köşesi "özel köşe direği D" (PK-07)
        ekle("1002", "Özel köşe direği (D) 100 × 100", f"100 × 100 × {mm(H0)}", kc["ozel"], "Sayım", "dış çizginin iç köşesi (çektirme U'lu)", "PK-07 1 tuttu")
    ekle("1002", "Köşebent", f"L {mm_m(pb('kosebent'))}", r("kosebent"), "Kural (Portatifev)",
         f"sabit {r('kosebent')} (şablon notu \"tek kat 7\"; O3: PK-07 7, PK-06 7 tuttu; PK-01'de 0)", "",
         aday=r("kosebent_aday"), aday_notu=f"Şablon B sabit {r('kosebent_aday')} (PK-02 3, PK-03 ve PK-05 5)")
    if N["dikmeler"]:
        for L_k, n_k in sorted(Counter(N.get("kolon_boylari_cm") or [H0] * N["dikmeler"]).items(), reverse=True):   # O4: kolon boyu paftadan
            ekle("1002", "Özel kutu profil (kolon) 100 × 100", f"L {mm(L_k)}", n_k, "Sayım", "veranda dikmesi" + (" (boy paftadan, O4)" if N.get("kolon_boylari_cm") else ""))
        # profil vidalama aparatı yazılmaz: kolonlu beş Portatifev listesinde yok, yalnız PK-01'de 2 ("ekstradan ekledik"; BK-12 PR-2c)
    kirisler = N.get("veranda_kirisleri_cm")
    kiris_formul = "paftadan okunan kiriş boyu"
    if kirisler is None:                                        # Motor kipi açık kenarları verir; kiriş = açık kenar − 10
        kirisler = [x - r("veranda_kirisi_eksik_cm") for x in N.get("veranda_kenarlari_cm", [])]
        kiris_formul = f"açık kenar dış ölçüsü − {mm(r('veranda_kirisi_eksik_cm'))}"
    for L_ in kirisler:
        ekle("1002", "Kutu profil (kiriş) 100 × 100", f"L {mm(L_)}", 1, "Liste kuralı", kiris_formul, "PK-01'de tuttu")
    for L_ in N.get("ic_kirisler_cm") or []:                    # paftadaki yeşil kesikli profil (Lokman, 21 Ekim 16:22); Motor'da duvarsız sınır
        ekle("1002", "Kutu profil (kiriş) 100 × 100", f"L {mm(L_)}", 1, "Liste kuralı",
             "duvarsız sınırın boyu (İş Emri'nde açık sınır, aks arası)" if N["kaynak"] == "Motor" else "paftadan okunan kiriş boyu (çatı kenarında değil: duvarsız açıklık)",
             "E5 L 3255 ve TS-01 L 2800 gerçek listelerde var; duvarsız açıklığa kiriş gelir (Lokman, kart 22 Ekim)")
    ec = Counter((e["duvar"], e["cins"]) for e in N["ekler"])
    ek_s = Counter((e["duvar"], e["cins"]) for e in N["ekler"] if e["sacak"])
    ekle("1002", "H 100 (dış pano eki)", f"100 × 100 × {mm(H0)}", ec[("dis", "pano_eki")], "Sayım", "her dış ekte bir H", "kulaklı / dübelli ayrımı: aday",
         aday=f"kulaklı {ek_s[('dis', 'pano_eki')]} / dübelli {ec[('dis', 'pano_eki')] - ek_s[('dis', 'pano_eki')]}",
         aday_notu="makasın denk geldiği dış ek kulaklı; PK-01 12 / 7, PK-02 8 / 9, PK-06 13 / 6 tuttu", pafta=("h_plani", "dis"))
    arti = sum(1 for e in N["ekler"] if e.get("arti"))
    ekle("1002", f"H standart {ic_kal} (iç pano eki)", f"{ic_kal} × {ic_kal} × {mm(H0)}", ec[("ic", "pano_eki")], "Sayım", "her iç ekte bir H"
         + (f"; UYARI: {arti} dört kollu (+) birleşim burada pano eki sayıldı, birleşim profili kural kitabında yok" if arti else ""),
         pafta=("h_plani", "h_standart"))
    ekle("1002", f"3'lü H 100 × 100 × {ic_kal} (dış duvar T'si)", f"L {mm(H0)}", ec[("dis", "uclu")], "Sayım", "iç duvarın dış duvara geldiği T", "",
         aday=f"kulaklı {ek_s[('dis', 'uclu')]} / dübelli {ec[('dis', 'uclu')] - ek_s[('dis', 'uclu')]}", aday_notu="aynı kural; PK-01 2 / 3, PK-02 2 / 3",
         pafta=("h_plani", "uclu_dis"))
    ekle("1002", f"3'lü H standart {ic_kal} (iç T)", f"L {mm(H0)}", ec[("ic", "uclu")], "Sayım", "iç–iç T birleşimi", pafta=("h_plani", "uclu_standart"))
    dubelli = ec[("dis", "pano_eki")] + ec[("dis", "uclu")]
    for olcu, n in sorted(Counter(a["olcu"] for a in pen_k).items()):   # O12: pencere alıcıya ait olsa da karkas bizde (PK-07 C × 4)
        en, boy = pencere_olcusu(olcu)
        ekle("1002", f"Özel pencere karkası ({en}×{boy}) (100'lük çektirme U'su + 100'lük H geçen)", f"{en * 10} × {boy * 10}", n, "Kural (Portatifev)",
             "her karkaslı pencereye bir (PK-01 dersi 3; PK-07 alıcıya ait pencerede de 4)", "", aday=0, aday_notu="Şablon B (PK-02): hazır karkas yok, U'lar yerinde",
             pafta=("pencere_karkasi",))
    if not pencere_alici:
        ua = r("cektirme_u_100_aday")
        ekle("1002", "Çektirme U'su 100", f"100 × {ua['boy_cm'] * 10}", r("cektirme_u_100"), "Kural (Portatifev)",
             f"karkas hazır gidince {r('cektirme_u_100')} sabit (PK-01: \"pencere özel iletiliyor, 2 fix\")",
             aday=TAVAN(sum(2 * pencere_olcusu(a["olcu"])[0] for a in pen_k) / ua["boy_cm"] + ua["ek"]), aday_notu=f"Şablon B (PK-02 6 ✓): karkaslı pencerelerde (2 × en = {sum(2 * pencere_olcusu(a['olcu'])[0] for a in pen_k)} cm) ÷ {sy(ua['boy_cm'])} + {ua['ek']}")
        ekle("1002", "100'lük pencere U'su H geçen", "L 2500", r("pencere_u_h_gecen"), zayif("pencere_u_h_gecen"), f"sabit {r('pencere_u_h_gecen')} (yalnız PK-01)",
             aday=r("pencere_u_h_gecen_aday_pencere_basina") * len(pen_k), aday_notu=f"Şablon B (PK-02 8 ✓): karkaslı pencere {len(pen_k)} × {r('pencere_u_h_gecen_aday_pencere_basina')}")
    ekle("1002", f"Çektirme U'su {ic_kal}" + (" (iç duvar)" if ic_kal >= 100 else ""), f"{ic_kal} × 2440", r("cektirme_u_ic"), "Kural (Portatifev)",
         f"sabit {r('cektirme_u_ic')} (PK-01 ve PK-02'de 2; açık Portatifev listelerinde 2–5, ortak ölçü bulunamadı)")
    # tavan taşıyıcısı (H8)
    to = r("tavan_omegasi")
    to_b = round(pb("tavan_omegasi") - to["pay_m"], 4)              # şablonun 3,65'i: parça boyu − pay
    L_duvar = sum(p["boy"] for p in N["panolar"] if p["duvar"] == "ic") / 100
    tavan_tipi = oz.get("tavan", oz.get("tavan şekli", "asma"))
    ters = "ters" in tavan_tipi
    if ters and ic_kal >= 100:                                  # O5: iç duvar 100 → duvar üstleri 100'lük duvar omegasında; hatlar duvar yüzünden
        L_hat, n_hat = omega_hatlari(N["kapali"], TERS_OMEGA_ARALIK_M, duvar_yuzu=True)
        ekle("1002", "60'lık tavan omegası (ters tavan)", f"60 × {mm_m(pb('tavan_omegasi'))}", TAVAN(L_hat / to_b + to["ek"]), "Şablon formülü (Portatifev)",
             f"oda hatları {od(L_hat)} m [{n_hat} hat, her {sy(TERS_OMEGA_ARALIK_M * 100)} cm'de bir, iki duvar yüzünde de] ÷ {sy(to_b)} + {to['ek']} (iç duvar üstleri 100'lük omegada)",
             "PK-07 36 tuttu (O5)", pafta=("tavan_omegasi",), aday=TAVAN(L_hat / to_b), aday_notu=f"\"+{to['ek']}\" eklenmeden")
    elif ters:
        L_hat, n_hat = omega_hatlari(N["kapali"], TERS_OMEGA_ARALIK_M)
        ekle("1002", "60'lık tavan omegası (ters tavan)", f"60 × {mm_m(pb('tavan_omegasi'))}", TAVAN((L_hat + L_duvar) / to_b + to["ek"]), "Şablon formülü (Portatifev)",
             f"(oda içi hatlar {od(L_hat)} m [{n_hat} hat, her {sy(TERS_OMEGA_ARALIK_M * 100)} cm'de bir] + iç duvar üstleri {od(L_duvar)} m) ÷ {sy(to_b)} + {to['ek']}",
             "tavan: " + tavan_tipi + "; duvar üstleri PK-03 tavan planında da var", pafta=("tavan_omegasi",),
             aday=TAVAN((L_hat + L_duvar) / to_b), aday_notu=f"Şablon B (PK-02): \"+{to['ek']}\" eklenmeden")
    else:
        L_hat, n_hat = omega_hatlari(N["kapali"], ASMA_OMEGA_ARALIK_M)
        ekle("1002", "60'lık duvar omegası (asma dizme tavan)", f"60 × {mm_m(pb('tavan_omegasi'))}", TAVAN((L_hat + L_duvar) / to_b + to["ek"]), "Şablon formülü (Portatifev)",
             f"(oda içi hatlar {od(L_hat)} m [{n_hat} hat, her {sy(ASMA_OMEGA_ARALIK_M * 100)} cm'de bir] + iç duvar üstleri {od(L_duvar)} m) ÷ {sy(to_b)} + {to['ek']}",
             "PK-01'de formül 21, girilen 8 (soru 1)", pafta=("duvar_omegasi_asma",), aday=TAVAN((L_hat + L_duvar) / to_b),
             aday_notu=f"Şablon B (PK-02 16 ✓): \"+{to['ek']}\" eklenmeden")
    # N2 (sürüm 6): veranda tavanının omegası ayrı satır değil — PK-01, PK-03 ve PK-06 listelerinde tek omega satırı var (PK-03 dersi 10, PK-06)
    # Lokman, 21 Ekim 16:22: çatının altında kalıp kenarına gelmeyen her şeyin üstü (BK-12 PR-2e). Kenardakiler saçak ya da baş makas omegası alır
    ic_kalan = N.get("ic_kalan_dis_duvar_m", 0.0)
    kiris_ic = sum(N.get("ic_kirisler_cm") or []) / 100
    ust100 = L_duvar if ic_kal >= 100 else 0.0                  # O5: 100'lük iç duvarların üstü de 100'lük omega (PK-07 10)
    dob = r("duvar_omegasi_100_bolen_m")
    terim = " + ".join(t for t, v in ((f"çatı kenarına gelmeyen dış duvarlar {od(ic_kalan)} m", ic_kalan),
                                      (f"çatı kenarında olmayan kirişler {od(kiris_ic)} m", kiris_ic), (f"100'lük iç duvarlar {od(ust100)} m", ust100)) if v)
    uyari = ("UYARI: kenarda olmayan kiriş okunmadı (ic_kirisler_cm yok); paftada çatı kenarında olmayan yeşil kesikli profil varsa eksik. "
             if N["kaynak"] == "pafta" and N.get("ic_kirisler_cm") is None else "")
    ekle("1002", "100'lük duvar omegası", f"100 × {mm_m(dob)}", TAVAN((ic_kalan + kiris_ic + ust100) / dob), "Kural (J2, O5)",
         uyari + (f"{terim} ÷ {sy(dob)}" if terim else "çatı kenarına gelmeyen duvar ve kiriş yok (bütün dış duvarlar saçak ya da baş makas omegası alır)"),
         "Portatifev E2, E3, E5, PK-07 elle tuttu; TS-01 kuralla 2, girdide kiriş yok (üretilen 0); Şablon B bilgi: E1, E4, PK-06")
    sacak_m = sum(sum(o["hatlar"]) for _c, o in C)                # bütün saçaklar (sandviç kapaması da toplamdan; kitapta da)
    # Çatı panelli (makassız) parçanın kenarları kural kitabından (`panel_cati_kenarlari`; Lokman, 10 Ekim 10:18; prefabrikte 18 Ekim 19:22):
    # saçakta özel büküm saçak sacı, yanlarda sundurma kapama; o kenarlarda düz saçak sacı, saçak omegası ve alın sacı yok
    # (`ek_yapi_ve_korkuluk.cati_panelli_cati`). 7.3'te öteki kenarlar gibi sayılıyordu.
    pck, ep = _ortak(k, "panel_cati_kenarlari"), _ortak(k, "ek_yapi_ve_korkuluk", "cati_panelli_cati")
    panelli = lambda c: bool(c.get("makas_yok"))
    alin_boy = lambda c, o: (2 * c["kalkan"] if c["tip"] == "besik" else 2) * o["egik"]
    sacak_om = sum(sum(o["hatlar"]) for c, o in C if ep["sacak_omegasi"] or not panelli(c))
    sacak_sc = sum(sum(o["hatlar"]) for c, o in C if ep["sacak_saci"] or not panelli(c))
    alin = sum(alin_boy(c, o) for c, o in C if ep["alin_saci"] or not panelli(c))
    p_sacak = sum(sum(o["hatlar"]) for c, o in C if panelli(c))
    p_yan = sum(alin_boy(c, o) for c, o in C if panelli(c))
    haric = lambda kalan, hepsi: " (çatı panelli parçanın kenarı hariç)" if hepsi - kalan > 1e-9 else ""   # noqa: E731
    ob0 = N.get("ozel_bukum") or {}                             # O6: paftadaki özel büküm saçlar düz saçtan düşülür (PK-07 2 + 2)
    # Özel büküm çatı panelli çatının kenarındadır (Lokman, 10 Ekim 10:18: "yandan sandviç panel kötü görünmesin diye ... özel bükümlü kapama").
    # Çatı panelli parçası olan girdide paftanın özel büküm saçlarını kitabın kenar satırları sayar; paftanın sayısı o satırların notuna gider
    # (çıkarım: PK-07'de paftanın 2 + 2'si veranda saçağının kenarlarıdır, kitabın kenar kuralı da 2 + 2 verir)
    ob = {} if any(panelli(c) for c, _o in C) else ob0
    sob = r("sacak_omegasi_bolen_m")
    ekle("1002", "100'lük saçak omegası", f"100 × {mm_m(sob)}", TAVAN(sacak_om / sob), "Kural (PK-01)",
         f"saçak kenarları {od(sacak_om)} m{haric(sacak_om, sacak_m)} ÷ {sy(sob)}, bir kez yukarı", "PK-01 9, PK-02 7 tuttu")
    ps, bs = _ortak(k, "parca_boyu_m", "sacak_saci"), _ortak(k, "bindirme_m", "sacak_saci")
    ekle("1002", "Saçak sacı (30'luk, 3'ü menfezli)", f"300 × {mm_m(ps)}", TAVAN(sacak_sc / (ps - bs)) - ob.get("sacak", 0), "Kural",
         f"saçak kenarları {od(sacak_sc)} m{haric(sacak_sc, sacak_m)} ÷ {sy(ps - bs)}" + (f" − özel büküm {ob['sacak']}" if ob.get("sacak") else ""),
         "PK-01 ve PK-02'de tuttu; PK-07 9 + 2")
    if ob.get("sacak"):
        ekle("1002", "Özel büküm saçak sacı", f"L {mm_m(ps)}", ob["sacak"], "Pafta", "özel büküm saçlar paftası", "PK-07 2 tuttu")
    alin_hepsi = sum(alin_boy(c, o) for c, o in C)
    pa_, ba_ = _ortak(k, "parca_boyu_m", "alin_saci"), _ortak(k, "bindirme_m", "alin_saci")
    ekle("1002", "Alın sacı (30'luk)", f"300 × {mm_m(pa_)}", TAVAN(alin / (pa_ - ba_)) - ob.get("alin", 0),
         "Kural", f"alın eğik kenarları {od(alin)} m{haric(alin, alin_hepsi)} ÷ {sy(pa_ - ba_)}" + (f" − özel büküm {ob['alin']}" if ob.get("alin") else ""),
         "PK-01 ve PK-02'de tuttu; PK-07'nin listesinde 9 + özel büküm 2 (iki kenar birlikte yuvarlanmış), kitap kenarları ayrı yuvarlar: 10 + sundurma kapama 2")
    if ob.get("alin"):
        ekle("1002", "Özel büküm alın sacı", f"L {mm_m(pa_)}", ob["alin"], "Pafta", "özel büküm saçlar paftası", "PK-07 2 tuttu")
    for anahtar, boy_k, kenar, ob_k in (("sacak", p_sacak, "saçakları", "sacak"), ("yan", p_yan, "eğik kenarları (yanları)", "alin")):
        if boy_k > 0:
            pr_ = pck[anahtar]
            ekle("1002", pr_["ad"], f"L {mm_m(pr_['parca_boyu_m'])}", TAVAN(boy_k / (pr_["parca_boyu_m"] - pr_["bindirme_m"])), "Kural kitabı",
                 f"çatı panelli parçanın {kenar} {od(boy_k)} m ÷ ({sy(pr_['parca_boyu_m'])} − {sy(pr_['bindirme_m'])} bindirme)",
                 "Lokman, 10 Ekim 10:18; prefabrikte 18 Ekim" + (f"; paftanın özel büküm saçlarında {ob0[ob_k]} (O6)" if ob0.get(ob_k) else ""))
    kk = lambda c: 0 if c.get("acik") else c["kalkan"]          # N1: açık çatı parçasının kalkanının altında duvar yok (PK-06 veranda)
    kalkan = sum((c["kalkan_duvar_cm"] / 100 if c.get("kalkan_duvar_cm") is not None else kk(c) * c["aciklik_cm"] / 100) for c, _o in C)   # 6.1: paftadaki kalkan duvarı
    kalkan_s = sum(kk(c) * (c["aciklik_cm"] / 100 + 2 * o["sac"]) for c, o in C)
    acik_not = " (açık çatı parçası sayılmaz, N1)" if any(c.get("acik") for c, _o in C) else ""
    bmo = r("bas_makas_omegasi_bolen_m")
    ekle("1002", "Baş makas omegası", f"L {mm_m(bmo)}", TAVAN(kalkan / bmo), "Kural (Portatifev)", f"baş makasların altı {od(kalkan)} m ÷ {sy(bmo)} (PK-01 dersi 5)" + acik_not,
         "PK-06 7 tuttu (N1)", aday=TAVAN(kalkan_s / bmo), aday_notu=f"Şablon B (PK-02 7 ✓): saçaklı makas boyu {od(kalkan_s)} m ÷ {sy(bmo)}")
    bzb = _ortak(k, "bas_makas_z", "parca_boyu_m")              # kitabın baş makas Z'si (L 2800); PK-02, PK-06, PK-07 paftalarında da
    ekle("1002", "Baş makas Z'si", f"L {mm_m(bzb)}", kk(ana) * (2 if ana["tip"] == "besik" else 1) * TAVAN(ao["egik"] / bzb), "Kural (O7)",
         f"ana çatının alın kenarları (beşikte her baş makasın iki eğik kenarı, tek yönde bir) × ⌈eğik ÷ {sy(bzb)}⌉",
         "PK-07 8, PK-06 8, PK-02 8 tuttu; PK-01'de 0")
    bmb = r("bas_makas_betopani")
    bet = 0
    for c, o in C:
        if kk(c):
            yuks = (c["aciklik_cm"] / (200 if c["tip"] == "besik" else 100) + o["sac"] * (1 if c["tip"] == "besik" else 2)) * o["eg"]
            bet += kk(c) * TAVAN(bmb["katsayi"] * 0.5 * (c["aciklik_cm"] / 100 + 2 * o["sac"]) * yuks / bmb["levha_m2"])
    ekle("1002", "Baş makas betopanı", levha("1250 × 2500", bmb["levha_m2"]), bet, "Kural (H5)", f"baş makas başına ⌈{sy(bmb['katsayi'])} × saçaklı üçgen ÷ {sy(bmb['levha_m2'])}⌉" + acik_not, "PK-01 4, PK-02 6, PK-06 6")
    acb = r("alt_cerceve_bolen_m")
    if ic_kal >= 100:                                           # O8: iç duvar 100 → tek satır (PK-07 16)
        ekle("1002", "100'lük alt çerçeve", f"100 × {mm_m(acb)}", TAVAN((N["dis_cevre_m"] + L_duvar) / acb), "Şablon formülü (H4, O8)",
             f"(dış duvarlar {od(N['dis_cevre_m'])} + 100'lük iç duvarlar {od(L_duvar)}) m ÷ {sy(acb)}", "PK-07 16 tuttu")
    else:
        ekle("1002", "100'lük alt çerçeve", f"100 × {mm_m(acb)}", TAVAN(N["dis_cevre_m"] / acb), "Şablon formülü (H4)", f"dış duvarlar {od(N['dis_cevre_m'])} m (veranda sayılmaz) ÷ {sy(acb)}",
             "PK-01 9, PK-02 9 tuttu")
        ekle("1002", "60'lık alt çerçeve", f"60 × {mm_m(acb)}", TAVAN(L_duvar / acb), "Kural (Lokman 13.10, R1)", f"iç duvarlar {od(L_duvar)} m ÷ {sy(acb)}",
             "Lokman: alt çerçeve her zaman 3750 (2026 listelerinde 60 × 2500 yazıyordu)", aday=TAVAN(L_duvar / r("alt_cerceve_60_aday_bolen_m")),
             aday_notu=f"listelerdeki L {mm_m(r('alt_cerceve_60_aday_bolen_m'))}")

    if kubbeler:
        kubbe_takimi("1002")

    # ── 1003 Kapı ve pencere ────────────────────────────────────────────────
    for a in (a for a in acl if a["tur"] == "dis_kapi"):
        kapi_alici = a.get("dograma") == "alıcıya ait" or "alıcı" in oz.get("dış kapı", "")
        ekle("1003", f"Prefabrik çelik kapı ({'SAĞ' if a.get('mentese') == 'sag' else 'SOL'})", "900 × 2000", 0 if kapi_alici else 1, "Sayım",
             kaynak_ad + ("; alıcıya ait" if kapi_alici else "") + f"; ölçü listede her zaman 90 × 200 (L4; çizimde {mm(a['genislik'])})")
    kapilar = Counter(a.get("mentese") for a in acl if a["tur"] == "ic_kapi")
    for ment, n in sorted(kapilar.items(), key=lambda x: str(x[0])):
        ekle("1003", f"Amerikan kapı (80'lik kanat) ({'SAĞ' if ment == 'sag' else 'SOL' if ment == 'sol' else '?'})", "82 × 196", n, "Sayım",
             "menteşe D-13 (PK-01 3 / 2, PK-02 1 / 3 tuttu)")
    if pencere_alici:
        ekle("1003", "Pencere grubu", "—", 0, "İş Emri", "alıcıya ait (PK-01 dersi 1)")
    else:
        for olcu, n in sorted(Counter(a["olcu"] for a in pen).items()):
            en, boy = pencere_olcusu(olcu)
            ekle("1003", "PVC vasistas" if (en <= ps_["vasistas_en_cm"] and boy <= ps_["vasistas_boy_cm"]) else "PVC pencere", f"{en}/{boy}", n, "Sayım", kaynak_ad)

    # ── 1004 Tavan ──────────────────────────────────────────────────────────
    ta, fire_t, lev_a = r("tavan_alcipani"), zay("tavan_alcipan"), lev("alcipan")
    # veranda tavanı (kitap `veranda_tavani.prefabrik`: prefabrikte yeşil alçıpan; Lokman, 7 Ekim 07:45; prefabrikte 18 Ekim 19:22). Çatı panelli açık
    # parçanın (veranda saçağı) tavanı çatının saçaklı planıyla (`panel_cati_kenarlari.acik_alan.tavan`); hangi açık mahali örttüğü girdide yok:
    # örttüğü alan, kalan açık alanı aşmadan planı kadar sayılır (çıkarım; PK-07'de plan veranda alanına eşit)
    ver_dis = sum(x["alan_m2"] for x in N["acik"])
    ver, ver_not = ver_dis, ""
    if N["acik"] and _ortak(k, "veranda_tavani", "prefabrik") != "yesil_alcipan":
        raise ValueError("veranda_tavani.prefabrik: prefabrik liste veranda tavanını yalnız yeşil alçıpanla yazar")
    acik_p = [(c, o) for c, o in C if panelli(c) and c.get("acik")]
    if acik_p:
        if pck["acik_alan"]["tavan"] != "cati_plani":
            raise ValueError("panel_cati_kenarlari.acik_alan.tavan: prefabrik liste yalnız çatının planını bilir")
        kalan = ver_dis
        for c, o in acik_p:
            plan = o["yuz"] * o["egik"] / math.sqrt(1 + o["eg"] ** 2) * o["mahya_boy"]
            ort = min(plan, kalan)
            kalan -= ort
            ver += plan - ort
        ver_not = f" (çatı panelli açık parçanın saçaklı planıyla; dış ölçüyle {od(ver_dis)})" if abs(ver - ver_dis) > 1e-9 else ""
    yesil = tavan_islak + ver
    n_beyaz = ASAGI(tavan_kuru * fire_t / lev_a + ta["kuru_ek"])
    n_yesil = ASAGI(yesil * fire_t / lev_a + ta["islak_ek"]) if yesil else 0
    ekle("1004", "Tavan beyaz alçıpan", levha("1200 × 2500", lev_a), n_beyaz, "Şablon formülü (H6)",
         f"kuru tavan {od(tavan_kuru)} m² × {sy(fire_t)} ÷ {sy(lev_a)} + {ta['kuru_ek']}, aşağı", "PK-02 18 tuttu; PK-01 elle 8",
         aday=TAVAN(bina_m2 / lev_a) - (TAVAN(ver_dis / lev_a) if N['acik'] else 0),
         aday_notu=f"sürüm 1–2 (P6001): brüt ÷ {sy(lev_a)}, veranda düşülür")
    ekle("1004", "Tavan yeşil alçıpan", levha("1200 × 2500", lev_a), n_yesil, "Şablon formülü (H6)",
         f"(ıslak hacim {od(tavan_islak)}" + (f" + veranda tavanı {od(ver)}{ver_not}" if N["acik"] or acik_p else "") +
         f") m² × {sy(fire_t)} ÷ {sy(lev_a)} + {ta['islak_ek']}, aşağı",
         "PK-02 3 tuttu" + ("; veranda tavanı yeşil alçıpan (kitap; 7.3'te ayrı Boardex satırı, PK-07 2)" if N["acik"] or acik_p else ""))
    # çatı panelli parçanın kenar Boardex şeridi (`panel_cati_kenarlari.<acik_alan | ek_yapi>.kenar_boardex`): açık alanda yok, kapalı ek yapıda
    # yalnız saçağın ve yanların altı (`ek_yapi_ve_korkuluk.cati_panelli_cati.sacak_kaplamasi`)
    sk_ = ep["sacak_kaplamasi"]

    def kenar_eni(c):
        kb = pck["acik_alan" if c.get("acik") else "ek_yapi"]["kenar_boardex"]
        if kb == "yalniz_alt":
            return [sk_["alt_m"]]
        if kb is True:
            return [sk_["yuz_m"], sk_["alt_m"]]
        if kb is False:
            return []
        raise ValueError(f"panel_cati_kenarlari: bilinmeyen kenar_boardex {kb!r}")
    serit = [(sum(o["hatlar"]) + alin_boy(c, o), sum(kenar_eni(c))) for c, o in C if panelli(c)]
    serit = [(b, e) for b, e in serit if b * e > 0]
    n_bx = 0
    if serit:
        fire_b, lev_b = zay("boardex"), lev("boardex")
        serit_m2 = sum(b * e for b, e in serit)
        n_bx = TAVAN(serit_m2 * fire_b / lev_b)
        ekle("1004", urun_adi("Dış cephe Boardex (çatı panelli parçanın saçak ve yan altı)"),
             levha(f"{sy(_ortak(k, 'levha_kalinligi_mm', 'boardex'))} × 1200 × 2400", lev_b), n_bx, "Kural kitabı",
             " + ".join(f"{od(b)} m × {sy(e)} m" for b, e in serit) + f" = {od(serit_m2)} m² × {sy(fire_b)} ÷ {sy(lev_b)}",
             "kapalı ek yapının saçak ve yan altı (Lokman, 10 Ekim; PK-05'te yaklaşık 1,5 m²); 7.3'te yoktu")
    if "alçıpan" in oz.get("açıklama", "") or "alçıpan" in oz.get("iç cephe kaplaması", ""):
        da, fire_d = r("duvar_alcipani"), zay("duvar_alcipan")
        L_dis_ic = sum(p["boy"] for p in N["panolar"] if p["duvar"] == "dis") / 100
        bosluk = sum((pencere_olcusu(a["olcu"])[0] * pencere_olcusu(a["olcu"])[1] / 1e4) for a in pen) + \
            sum(da["kapi_en_m"] * da["kapi_boy_m"] * (2 if a["tur"] == "ic_kapi" else 1) for a in acl if a["tur"] in ("ic_kapi", "dis_kapi"))
        yuzey = (2 * L_duvar + L_dis_ic) * H0 / 100 - bosluk
        islak_duvar = sum(2 * (x["en_cm"] + x["derin_cm"]) / 100 for x in N["kapali"] if x["tur"] in ISLAK) * H0 / 100
        duvar_top = TAVAN(yuzey * fire_d / lev_a); duvar_yesil = ASAGI(islak_duvar * fire_d / lev_a)
        ekle("1004", "Duvar alçıpanı beyaz", levha("1200 × 2500", lev_a), duvar_top - duvar_yesil, "Kural (uydurma)",
             f"duvar yüzeyi (2 × iç {od(L_duvar)} + dış iç yüzü {od(L_dis_ic)}) × {sy(H0 / 100)} − boşluklar {od(bosluk)} (iç kapı {sy(da['kapi_en_m'])} × "
             f"{sy(da['kapi_boy_m'])}, iki yüz) = {od(yuzey, 1)} m² × {sy(fire_d)} ÷ {sy(lev_a)} = {duvar_top} − yeşil {duvar_yesil}",
             "paftanın açıklaması \"iç cephede alçıpan kaplama\"; PK-03 toplam 61 (62 tahmin)")
        ekle("1004", "Duvar alçıpanı yeşil", levha("1200 × 2500", lev_a), duvar_yesil, "Kural (J7)",
             f"ıslak hacim duvarları {od(islak_duvar, 1)} m² × {sy(fire_d)} ÷ {sy(lev_a)}, aşağı", "PK-03 7 (banyo)")
        ekle("1004", "Alçıpan destek straforu", f"paket / {sy(da['strafor_m2'])} m²", TAVAN(yuzey / da["strafor_m2"]), "Kural (J7)",
             f"duvar yüzeyi {od(yuzey, 1)} m² ÷ {sy(da['strafor_m2'])}", "PK-03 3")
    if fugali:                                                  # O1: fugalı cephe; ayrı betopan levhası yok, latalar var (PK-07)
        fc = r("fugali_cephe")
        kose_n = kc.get("dis", 0) + (kc.get("ic", 0) if ic_kal >= 100 else 0)
        dis_ek = ec[("dis", "pano_eki")] + ec[("dis", "uclu")]
        ekle("1004", "H'lar için lata (10 mm betopan, oymalı)", "100 × 2500", dis_ek + fc["h_lata_yedek"], "Kural (Lokman 13.10, R5)",
             f"dış 100'lük duvar H'ları {dis_ek} (dış H + dış 3'lü H) + {fc['h_lata_yedek']} yedek", "PK-07 30 tuttu")
        ekle("1004", "Köşe latası", "150 × 2500", kose_n, "Kural (O1)", "10'luk köşe direği başına", "PK-07 5 tuttu")
        ekle("1004", "Köşe latası", "130 × 2500", kose_n, "Kural (O1)", "10'luk köşe direği başına", "PK-07 5 tuttu")
        cevre_l = sum(2 * sum(pencere_olcusu(a_["olcu"])) / 100 for a_ in pen) + sum(2 * fc["kapi_boy_m"] + fc["kapi_en_m"] for a_ in acl if a_["tur"] == "dis_kapi")
        n28 = ASAGI(cevre_l / fc["lata_boyu_m"] + 1e-9); kalan = cevre_l - n28 * fc["lata_boyu_m"]
        ekle("1004", "Pencere latası", f"100 × {mm_m(fc['lata_boyu_m'])}", n28, "Kural (O1)",
             f"pencere çevreleri + dış kapı (2 × {sy(fc['kapi_boy_m'])} + {sy(fc['kapi_en_m'])}) = {od(cevre_l)} m ÷ {sy(fc['lata_boyu_m'])}, aşağı", "PK-07 10 tuttu")
        ekle("1004", "Pencere latası", f"100 × {mm_m(fc['lata_kisa_boyu_m'])}", TAVAN(kalan / fc["lata_kisa_boyu_m"]) if kalan > fc["artik_esik_m"] else 0,
             "Kural (O1)", f"artan {od(kalan)} m ({sy(fc['artik_esik_m'])} m'yi geçerse) ÷ {sy(fc['lata_kisa_boyu_m'])}", "PK-07 1 tuttu")
    if not ters:
        okap = r("omega_kapak")
        okb = round(okap["parca_m"] - okap["pay_m"], 4)
        ekle("1004", "Tavan H'ı L 1185 (asma dizme tavan)", "adet", TAVAN(tavan_net / (ASMA_OMEGA_ARALIK_M * TAVAN_H_ARALIK_M) + r("tavan_h_ek")), "Şablon formülü (Portatifev)",
             f"net tavan {od(tavan_net)} m² ÷ ({sy(ASMA_OMEGA_ARALIK_M)} × {sy(TAVAN_H_ARALIK_M)}) + {r('tavan_h_ek')}", "PK-01 66, PK-02 75")
        ekle("1004", f"PVC omega kapak L {mm_m(okap['parca_m'])} (asma dizme tavan)", "adet", TAVAN(L_hat / okb + okap["ek"]), zayif("omega_kapak"),
             f"oda içi omega hatları {od(L_hat)} m ÷ {sy(okb)} + {okap['ek']} (\"+{okap['ek']}\" yalnız PK-01)", "PK-01'in gerçek listesinde 10 (formül 10,03): tutmuyor", aday=TAVAN(L_hat / okb),
             aday_notu=f"Şablon B (PK-02 11 ✓): \"+{okap['ek']}\" eklenmeden")
    silte = _ortak(k, "silte_adet_m2")
    ekle("1004", f"Çatı şiltesi / izolasyonu ({sy(silte)} m²/paket)", "paket", TAVAN(bina_m2 / silte), "Liste kuralı", f"brüt {od(bina_m2)} ÷ {sy(silte)}",
         "Portatifev kaba hesabı (PK-01 6,4; girilen 4)",
         aday=TAVAN(sum((c["aciklik_cm"] / 100 + 2 * o["sac"]) * o["mahya_boy"] for c, o in C if not c.get("acik")) / silte),
         aday_notu=f"Şablon B (PK-02 7, PK-06 11 ✓): saçaklı çatı tabanı ÷ {sy(silte)}; açık çatı parçası (veranda) şilte almaz (N1)")

    # ── 1005 Makas ──────────────────────────────────────────────────────────
    makas_ara = r("makas_aralik_cm")
    n_makas_top, asik_top = 0, 0
    for c, o in C:
        ad = c.get("ad", "çatı")
        if c.get("makas_yok"):
            ekle("1005", f"Çatı paneli (hafif çelik) · {ad}", "—", None, "Kural yok", "makas ve aşık yerine hafif çelik çatı paneli", c.get("not", ""), pafta=("cati_paneli",))
            continue
        n_m = TAVAN(c["makas_kosu_cm"] / makas_ara - 1e-6) + 1
        n_makas_top += n_m
        if c is not ana:
            ekle("1005", f"Yavru makas · {ad}", f"L {round((c['aciklik_cm'] + 2 * c['sacak_cm']) * 10)}", n_m, "Kural (J8)",
                 f"ek çatı parçasının pano koşusu {mm(c['makas_kosu_cm'])} ÷ {mm(makas_ara)} yukarı + 1", "PK-03: yavru makas 3 (MK10–MK12)")
        else:
            if c["kalkan"]:
                ekle("1005", f"Makas (baş) · {ad}", f"açıklık {mm(c['aciklik_cm'])}", c["kalkan"], "Kural", "çatının iki ucunda" if c["kalkan"] == 2 else "çatının ucunda", "",
                     pafta=("makas_bas",))
            ekle("1005", f"Makas (orta) · {ad}", f"açıklık {mm(c['aciklik_cm'])}", n_m - c["kalkan"], "Kural (P1)",
                 f"saçak duvarının pano koşusu {mm(c['makas_kosu_cm'])} ÷ {mm(makas_ara)} yukarı + 1 = {n_m}" + (f", − {c['kalkan']} baş" if c["kalkan"] else ""),
                 "baş ve orta toplamı PK-01 9, PK-02 7, PK-03 9 tuttu", pafta=("makas_orta",))
        sira = int(math.floor((o["egik"] - (r("asik_mahya_payi_m") if o["yuz"] == 2 else 0)) / _ortak(k, "asik", "aralik_m") + 0.5)) + 1   # O13: en yakın
        asik_boy = o["yuz"] * sira * o["mahya_boy"]
        asik_top += asik_boy
    aa, az_, ap_ = r("asik_aday"), 1 + _ortak(k, "asik", "zayiat"), pb("asik")
    ab_ = round(ap_ - aa["pay_m"], 4)                              # şablonun 4,1'i: parça boyu − pay
    ekle("1005", "Aşık", f"L {mm_m(ap_)}", TAVAN(asik_top * az_ / ap_), "Kural (P2)",
         f"aşık boyları {od(asik_top, 1)} m × {sy(az_)} ÷ {sy(ap_)} (yüz başına (eğik − {sy(r('asik_mahya_payi_m'))}; beşikte) ÷ "
         f"{sy(_ortak(k, 'asik', 'aralik_m'))} en yakın + 1 sıra)", "PK-01 36 (elle), PK-02 35",
         pafta=("asik",), aday=TAVAN(asik_top / ab_ + aa["ek"]), aday_notu=f"Portatifev kaba hesabı: ÷ {sy(ab_)} + {aa['ek']}")

    if kubbeler:
        kubbe_takimi("1005")

    # ── 1006 Çatı ───────────────────────────────────────────────────────────
    kap = oz.get("çatı kaplaması", "")
    sandvic = "sandvi" in kap
    trapez = "trapez" in kap
    kiremit = "kiremit" in kap and not (sandvic or trapez)          # 7.3: metal kiremit (TS-01 kaplama paftası "Kapatır: 105 cm")
    # kapatma ve panel boyu kural kitabından (Lokman, 4 Ekim 15:18 ve 7 Ekim 07:45; prefabrikte 18 Ekim 19:22): boy eğik boy + taşma, 10 mm'ye yukarı.
    # Kitabın uzatma kuralı (`panel_boyu_uzatma`) kırma çatının çapraz parçaları içindir: dikdörtgen yüzde adet boydan bağımsız
    kap_m = _ortak(k, "sandvic_panel_kapatma_m") if sandvic else (_ortak(k, "trapez_sac_kapatma_m") if trapez else
                                                                 (_ortak(k, "kiremit_kapatma_m") if kiremit else _ortak(k, "tek_kat_panel_kapatma_m")))
    tasma, yuvarla_mm = _ortak(k, "cati_kaplama_tasma_m"), _ortak(k, "panel_boyu_yuvarlama_mm")
    boy_mm = lambda e_: int(math.ceil((e_ + tasma) * 1000 / yuvarla_mm - 1e-9) * yuvarla_mm)
    n_pan = 0
    for c, o in C:
        L_pan = boy_mm(o["egik"])
        n = o["yuz"] * TAVAN(o["mahya_boy"] / kap_m - 1e-9) if c is ana else TAVAN(o["yuz"] * o["mahya_boy"] / kap_m)   # O9: ana çatı yüz başına
        n_pan += n
        ad = (f"Sandviç panel ({sy(kap_m * 100)} cm kapatır)" if sandvic else ("Trapez sac" if trapez else
              (f"Metal kiremit ({sy(kap_m * 100)} cm kapatır)" if kiremit else "Tek kat çatı paneli")))
        ekle("1006", f"{ad} · {c.get('ad', 'çatı')}", f"L {L_pan}", n, "Kural (P3, O9)",
             (f"{o['yuz']} yüz × ⌈{od(o['mahya_boy'])} m ÷ {sy(kap_m)}⌉" if c is ana else f"⌈{o['yuz']} yüz × {od(o['mahya_boy'])} m ÷ {sy(kap_m)}⌉")
             + f"; boy eğik {od(o['egik'], 3)} + taşma {sy(tasma)} m, {yuvarla_mm} mm'ye yukarı (kitap)",
             "PK-01 22, PK-07 18 (yüz başına) tuttu", pafta=("sandvic_panel",) if c is ana else None,
             aday=TAVAN(o["yuz"] * o["mahya_boy"] / kap_m) if c is ana and o["yuz"] > 1 else None,
             aday_notu="Şablon B (PK-02 17 ✓): iki yüz toplam yukarı" if c is ana and o["yuz"] > 1 else "")
    pm, bm = _ortak(k, "parca_boyu_m", "mahya"), _ortak(k, "bindirme_m", "mahya")
    if trapez:
        tp_, tb_ = pb("trapez_mahyasi"), _ortak(k, "bindirme_m", "trapez_mahyasi")
        mahya = sum(TAVAN(o["mahya_boy"] / (tp_ - tb_)) for c, o in C if c["tip"] == "besik")
        ekle("1006", "Trapez sac mahyası", f"L {mm_m(tp_)}", mahya, "Kural (J5)", f"beşik mahyaları ÷ {sy(tp_ - tb_)} (L {mm_m(tp_)}, {sy(tb_ * 100)} cm bindirme)",
             "parça boyu kitaptan (Excel motoru); 7.3'te L 1000 (PK-03 listesinde 15)")
    else:
        mahya = TAVAN(sum(o["mahya_boy"] for c, o in C if c["tip"] == "besik") / (pm - bm))   # O10: toplam ÷ 2,6 (PK-06 6, PK-07 4)
        ekle("1006", "Metal kiremit mahyası", f"L {mm_m(pm)}", mahya, "Kural (O10)", f"beşik mahyalarının toplamı ÷ {sy(pm - bm)}", "PK-01, PK-02, PK-06, PK-07 tuttu")
    ters_m = 0.0
    for c, o in C:
        if c is not ana and c["tip"] == "besik" and c.get("capraz", True):      # 5.1: ana çatıya paralel ek beşikte dere içi yok
            a_ = c["aciklik_cm"] / 200 + o["sac"]; h_ = a_ * o["eg"]; b_ = h_ / max(ao["eg"], 1e-6)
            ters_m += 2 * math.sqrt(a_ * a_ + b_ * b_ + h_ * h_)
    if ters_m:
        n_ters = TAVAN(ters_m / (pm - bm))
        ekle("1006", "Ters mahya (dere içi)", f"L {mm_m(pm)}", n_ters, "Kural (J5)", f"çapraz beşiğin iki deresi {od(ters_m)} m ÷ {sy(pm - bm)}",
             "PK-03 4 tuttu")
        tk = _ortak(k, "ters_mahya_kenar_kutusu")                  # kitap: cumbalı çatıda olmazsa olmaz (Lokman, 7 Ekim 08:02); 7.3'te yoktu
        if tk["varsayilan"]:
            ekle("1006", "Ters mahya kenar kutusu", tk["boyut"], n_ters * tk["ters_mahya_basina"], "Kural kitabı",
                 f"ters mahya {n_ters} × {tk['ters_mahya_basina']}", "Lokman, 7 Ekim 08:02 (Excel motoru ve Eylül 2026 listesi); 7.3'te yoktu")
    pkp = _ortak(k, "panel_kapamasi")                              # kitap: sandviçte var, tek kat panelde listeden çıktı (Lokman, 4 Ekim 16:18)
    if sandvic:
        if pkp["sandvic_panel"]:
            sk = _ortak(k, "sandvic_kapama")                         # kitap: kapama dere boyunca, saçakların toplamından (Lokman, 7 Ekim 07:45 ve 08:02)
            if sk["olcu"] != "sacak_toplami":
                raise ValueError(f"sandvic_kapama.olcu {sk['olcu']!r}: prefabrik liste yalnız saçak toplamını bilir")
            skb = round(sk["parca_boyu_m"] - sk["bindirme_m"], 4)
            ekle("1006", "Sandviç panel kapaması", f"L {mm_m(sk['parca_boyu_m'])}", TAVAN(sacak_m / skb), "Kural kitabı",
                 f"saçak kenarları toplamı {od(sacak_m)} m ÷ ({sy(sk['parca_boyu_m'])} − {sy(sk['bindirme_m'])} bindirme)",
                 "Lokman, 7 Ekim 07:45 ve 08:02; 7.3'te L 2800 ÷ 2,5 (PK-07 10, PK-02 7 tuttu)")
    elif kiremit or (pkp["tek_kat_panel"] and not trapez):     # trapez çatıda kapama olmaz, satır yazılmaz (Lokman, 20 Ekim 20:45; BK-12 PR-2d)
        pbk = pb("sandvic_kapama")
        ekle("1006", "Panel kapaması", f"L {mm_m(pbk)}", None, "Kural yok", "—", "PK-05 tek kat 6 (alın ÷ 2,5), PK-06 16",
             aday=TAVAN(sacak_m / pbk), aday_notu=f"saçak ÷ {sy(pbk)} (bindirmesiz)")
    mb = _ortak(k, "mahya_bandi")                                  # kitabın rulosu ve mahya parça boyu; yöntem farkı `kitapla_farkli`
    mbp = mb["parca_boyu_m"]["metal_kiremit_mahyasi"]
    ekle("1006", "Mahya bandı", f"rulo {sy(mb['rulo_m'])} m", TAVAN(mahya * mbp / mb["rulo_m"]), "Şablon formülü (Portatifev)",
         f"mahya {mahya} × {sy(mbp)} ÷ {sy(mb['rulo_m'])}", "PK-01 2 tuttu; Şablon B'de yok")
    # duvar dibi (kitap `duvar_dibi`; Lokman, 8 Ekim 00:45): alçak çatının bina duvarına dayandığı kenara özel mahya, toplam boy ÷ (parça − mahya
    # bindirmesi). Kenar paftadan (`duvar_dibi_m`) gelir; gelmezse ana çatı dışındaki tek yön parçanın yüksek kenarı (mahya boyu) sayılır (çıkarım)
    dd_k = [(c.get("ad", "çatı"), c["duvar_dibi_m"] if c.get("duvar_dibi_m") is not None else (o["mahya_boy"] if c is not ana and c["tip"] == "tek_yon" else 0.0))
            for c, o in C]
    dd_k = [(a, b) for a, b in dd_k if b > 0]
    if dd_k:
        dd = _ortak(k, "duvar_dibi")
        if dd["malzeme"] != "ozel_mahya":
            raise ValueError(f"duvar_dibi.malzeme {dd['malzeme']!r}: prefabrik liste yalnız özel mahyayı bilir")
        ekle("1006", "Özel mahya (geniş)", f"L {mm_m(dd['parca_boyu_m'])}", TAVAN(sum(b for _a, b in dd_k) / (dd["parca_boyu_m"] - bm)), "Kural kitabı",
             "çatının duvara dayandığı kenarlar " + " + ".join(f"{a} {od(b)} m" for a, b in dd_k) + f" ÷ ({sy(dd['parca_boyu_m'])} − {sy(bm)} bindirme)",
             "Lokman, 8 Ekim 00:45; kenar paftada işaretli değilse ek tek yön çatının yüksek kenarı (çıkarım); 7.3'te yoktu")
    cati_alani = sum(o["yuz"] * o["egik"] * o["mahya_boy"] for c, o in C)
    if "osb" in kap:                                                # 7.3: OSB + nem bariyeri kaplaması (TS-01; E2 / E3)
        oz_, lev_o = 1 + r("osb_cati.zayiat"), lev("osb")
        ekle("1006", f"OSB {sy(_ortak(k, 'levha_kalinligi_mm', 'osb'))} mm (çatı)", levha("1220 × 2440", lev_o), TAVAN(cati_alani * oz_ / lev_o), "Kural (ilk tahmin, 7.3)",
             f"çatı alanı {od(cati_alani, 1)} m² × {sy(oz_)} ÷ {sy(lev_o)}", "E2 / E3 29", pafta=("osb",))
    if "nem" in kap:
        ny = r("nem_bariyeri_yuvarlama_m2")
        ekle("1006", "Nem bariyeri", "m²", int(math.ceil(cati_alani / ny - 1e-9) * ny), "Kural (ilk tahmin, 7.3)",
             f"çatı alanı {od(cati_alani, 1)} m², {sy(ny)} m²'ye yukarı", "E2 / E3 80", birim="m²")

    if kubbeler:
        kubbe_takimi("1006")

    # ── 1007 Elektrik ───────────────────────────────────────────────────────
    # Noktalar montaj paftasındaki elektrik planının sayımından (kesin sayı, çelik hattındaki gibi; prefabrik.json › elektrik); sayım yoksa oda
    # kuralından (`elektrik_oda`; BK-12 PR-2f). Sayım varken oda kuralının sonucu aday sütununda (PR-3'te kıyas için). Zil her evde kitabın sayısı
    # (`elektrik.zil`; açık on bir listenin hepsinde 1, PK-07'nin paftasında yok), paftadaki sayım pafta sütununda
    el = P.get("elektrik") or {}
    E, Ea, Ek = r("elektrik"), r("elektrik_aday"), _ortak(k, "elektrik")
    ks, kd = elektrik_oda(N, r("elektrik_oda"), _ortak(k, "elektrik_oda", "odalar"), r("elektrik_acik_mutfak"))
    es = (lambda a: (el.get(a) or {}).get("adet")) if el else (lambda a: ks[a])
    v = lambda a: es(a) or 0
    sayim = ("Sayım (pafta)", "göz sayımı; prefabrik.json › elektrik")
    oda_k = ("Kural (Lokman 18.10, oda başına)",
             f"oda kuralı (prefabrik.json › elektrik_oda): oda ve veranda takımı Lokman, 18 Ekim 19:52; her {sy(r('elektrik_oda.takim_m2'))} m²'ye bir "
             "takım, yukarı (kartlar 19 Ekim 16:50 ve 22 Ekim 11:10); banyo, WC, mutfak ve hol kitaptaki gibi (kart 19 Ekim 16:50)")

    def nokta_satiri(kalem, a, formul_sayim="", kural_k=oda_k):
        if el:
            ekle("1007", kalem, "adet", es(a), sayim[0], formul_sayim or "elektrik planından", sayim[1], aday=ks[a],
                 aday_notu="oda kuralı: " + (kd[a] or "yok"))
        else:
            ekle("1007", kalem, "adet", ks[a], kural_k[0], kd[a] or "oda kuralında yok", kural_k[1])
    nokta_satiri("Tijli duy", "tavan_armaturu", "tavan armatürü")
    nokta_satiri("Yuvarlak glop", "glop", "ıslak hacim glopu (H1)")
    d, g = ks["tavan_armaturu"], ks["glop"]                         # ampul = duy + glop (kitap `elektrik.ampul`)
    if el:
        ekle("1007", "Ampul", "adet", v("tavan_armaturu") + v("glop"), sayim[0], "duy + glop; dış aplik girmez (H1)", sayim[1],
             aday=d + g, aday_notu=f"oda kuralı: duy {d} + glop {g}")
    else:
        ekle("1007", "Ampul", "adet", d + g, "Kural kitabı", f"duy {d} + glop {g}; dış aplik girmez (H1)", "kitap `elektrik.ampul`")
    for kalem, a in (("Tekli anahtar (takım)", "anahtar_tekli"), ("Çiftli anahtar (takım)", "anahtar_cift"), ("Tekli priz (takım)", "priz_tekli"),
                     ("Çiftli priz (takım)", "priz_cift")):
        nokta_satiri(kalem, a)
    nokta_satiri("Uydu prizi (takım)", "uydu_prizi", kural_k=("Kural (Lokman 22.10)", "Lokman, kart 22 Ekim 11:09 \"Her eve 1\" (salona; kitabın salonunda 1)"))
    z, sk = Ek["zil"], Ek["sigorta_kutusu_kat_basina"]
    ekle("1007", "Zil", "adet", z, "Kural kitabı", f"her evde {z}", "kitap `elektrik.zil`; açık on bir listenin hepsinde 1 (BK-12 PR-2f)", pafta=("elektrik", "zil"))
    if el:
        ekle("1007", "Sigorta kutusu (12'li)", "adet", es("sigorta_kutusu"), sayim[0], "elektrik planından", sayim[1], aday=sk, aday_notu=f"kitap: kat × {sk}")
    else:
        ekle("1007", "Sigorta kutusu (12'li)", "adet", sk, "Kural kitabı", f"kat × {sk}", "kitap `elektrik.sigorta_kutusu_kat_basina`")
    anah = v("anahtar_tekli") + 2 * v("anahtar_cift")
    # buat ve NYM kural kitabından (`elektrik.buat_kasa`, `elektrik.kablo`; Excel hesaplama motoru; prefabrikte Lokman, 18 Ekim 19:22)
    # oda sayısı adla: pafta girdisinde L biçimli oda aynı adlı parçalarla gelir (PK-03 9 parça, 6 oda); Motor'da her mahalin adı tektir
    anah_t, priz_t = v("anahtar_tekli") + v("anahtar_cift"), v("priz_tekli") + v("priz_cift") + v("uydu_prizi")
    oda = len({x["ad"] for x in N["kapali"]})
    ekle("1007", "Buat kasa", "adet", anah_t + priz_t + oda, "Kural kitabı", f"anahtar {anah_t} + priz {priz_t} (uydu dahil) + oda {oda} (veranda hariç)",
         "Excel hesaplama motoru; oda sayısı Lokman, 7 Ekim 07:45", aday=anah_t + priz_t + v("tavan_armaturu") + v("glop") + z,
         aday_notu=f"7.3 (O19): listedeki bütün elektrik noktaları (anahtar {anah_t} + priz {priz_t} + duy {v('tavan_armaturu')} + glop {v('glop')} + zil {z}; "
                   "PK-07'nin gerçek listesinde 31)")
    # sigorta adedi W otomat sayısıdır (kitapta da). En uzak mesafe kitabın yöntemiyle (Motor kipi: giriş kapısından kapalı kısmın en uzak köşesi);
    # pafta kipinde okunduysa `sigorta_en_uzak`, okunmadıysa dış ölçünün köşegeni (kitabın son çaresi kapalı kısmın köşegeni; `kitapla_farkli`)
    if _ortak(k, "kablo_en_uzak_mesafe") != "sigortadan":
        raise ValueError(f"kablo_en_uzak_mesafe {_ortak(k, 'kablo_en_uzak_mesafe')!r}: prefabrik liste yalnız sigortadan en uzak mesafeyi bilir")
    eu = N.get("sigorta_en_uzak") or {"m": math.hypot(N["W"], N["D"]) / 100, "nereden": "kapının yeri girdide yok: dış ölçünün köşegeni"}
    sig, kos, nm = E["w_otomat"], eu["m"], E["kablo_nokta_basina_m"]
    p_say = v("priz_tekli") + 2 * v("priz_cift") + v("uydu_prizi")
    for kalem, n_say, nokta_adi, aday_k in (("NYM kablo 3 × 2,5", p_say, "tekli priz + çiftli priz × 2 + uydu prizi", "nym_3x25_m"),
                                            ("NYM kablo 2 × 1,5", anah, "tekli anahtar + çiftli anahtar × 2", "nym_2x15_m")):
        ekle("1007", kalem, "metre", TAVAN(sig * kos + n_say * nm), "Kural kitabı",
             f"sigorta {sig} × en uzak {od(kos)} m ({eu['nereden']}) + ({nokta_adi} = {n_say}) × {sy(nm)} m",
             "Excel hesaplama motoru; sigortadan en uzak mesafe Lokman, 7 Ekim 07:45 ve 8 Ekim 00:45",
             birim="m", aday=Ea[aday_k], aday_notu=f"Portatifev şablonu sabit {sy(Ea[aday_k])} m (PK-01 130 / 100, PK-02 135 / 120)")
    uk, bk = Ek["uydu_kablo_priz_basina_m"], Ek["besleme_kablosu_kat_basina_m"]
    ekle("1007", "Uydu kablo", "metre", uk * v("uydu_prizi"), "Şablon formülü", f"uydu prizi {v('uydu_prizi')} × {sy(uk)} m", "PK-02 tuttu", birim="m")
    ekle("1007", "Besleme kablosu", "metre", bk, "Şablon formülü", f"kat × {sy(bk)} m", "PK-02 tuttu", birim="m")
    ekle("1007", "Besleme kablo borusu", "metre", E["besleme_boru_m"], "Şablon formülü", f"kat × {sy(E['besleme_boru_m'])} m", "PK-02 tuttu", birim="m")
    ekle("1007", "İzole bant", "adet", TAVAN(bina_m2 * Ek["izole_bant_m2_basina"]), "Şablon formülü",
         f"m² × {sy(Ek['izole_bant_m2_basina'])}", "PK-02 tuttu")
    ekle("1007", "Kaçak akım rölesi (ikili)", "adet", Ek["kacak_akim_rolesi"], "Şablon formülü", f"tek kat {Ek['kacak_akim_rolesi']} ikili", "PK-02 tuttu")
    ekle("1007", "W otomat 16 A", "adet", E["w_otomat"], "Kural (Lokman 13.10, R4)", f"Portatifev şablonu sabit {E['w_otomat']} (alandan bağımsız)",
         "PK-07, E2, E3, E5 8", aday=Ea["w_otomat"], aday_notu=f"Şablon B sabit {Ea['w_otomat']} (PK-02, -03, -05, -06, E1, E4)")

    # ── 1008 Vida ───────────────────────────────────────────────────────────
    V, Vk, va = r("vida"), _ortak(k, "vida"), r("vida_aday_yuvarlama")      # Vk: kitabın vida değerleri (çalışma kitabının notları)
    ekle("1008", "16 mm betopan ve kapı kolu vidası (3,9 × 32)", "adet", V["betopan_vidasi"], "Kural (O16)", f"sabit {V['betopan_vidasi']}", "PK-07 ve Şablon B 500 tuttu; PK-01 250")
    L_vida = sum(boy_mm(o["egik"]) / Vk["trapez_panel_boyu_bolu_mm"] * TAVAN(o["yuz"] * o["mahya_boy"] / kap_m) for c, o in C)
    ky = V["kaplama_yuvarlama"]
    ekle("1008", "Trapez vida 5,5 × 110 (sandviç panel)" if sandvic else ("Trapez vida 5,5 × 60 (trapez sac)" if trapez else
                                                                         ("Trapez vida 5,5 × 60 (metal kiremit)" if kiremit else "Trapez vida 5,5 × 76 (tek kat panel)")),
         "adet", int(math.ceil(L_vida / ky - 1e-9) * ky),
         "Şablon formülü (Portatifev)", f"panel boyu ÷ {Vk['trapez_panel_boyu_bolu_mm']} × panel adedi = {L_vida:.0f}, {ye(ky)} yukarı", "PK-01 385 → 400",
         aday=int(math.ceil(L_vida / va - 1e-9) * va), aday_notu=f"Şablon B (PK-02 500 ✓): {ye(va)} yukarı")
    ka = _ortak(k, "kapsam_alici", "pencere_aliciya_aitse")       # kitap: pencere alıcıya aitse vida ve mastik yazılmaz (KT-01; Lokman, 8 Ekim 00:45)
    if pen and (not pencere_alici or ka["pencere_vidasi"]):     # 7.3 (O12): alıcıya ait pencerede de vida yazıyordu (PK-07 120)
        ekle("1008", "Prefabrik pencere vidası (4,8 × 70)", "adet", Vk["pencere_vidasi_pencere_basina"] * len(pen), "Kural (H2)",
             f"pencere × {Vk['pencere_vidasi_pencere_basina']}", "PK-02 100 tuttu; pencere alıcıya aitse yazılmaz (kitap)")
    if not (trapez or kiremit):                                 # 7.1 / 7.3: trapez ve metal kiremitte 5,5 × 60 zaten kaplama vidası satırında
        ty = V["trapez_5560_yuvarlama"]
        ekle("1008", "Trapez vida 5,5 × 60 (trapez sac / metal kiremit)", "adet", int(math.ceil(bina_m2 * Vk["trapez_5_5x60_m2_basina"] / ty - 1e-9) * ty), "Kural (O16)",
             f"m² × {sy(Vk['trapez_5_5x60_m2_basina'])}, {ye(ty)} yukarı (m² başına adet kural kitabından: Excel motoru)", "PK-07 200 tuttu",
             aday=int(math.ceil(bina_m2 * Vk["trapez_5_5x60_m2_basina"] / va - 1e-9) * va), aday_notu=f"Şablon B: {ye(va)} yukarı")
    ekle("1008", "230'luk kesme taşı", "adet", TAVAN(bina_m2 * V["kesme_tasi_m2_basina"]), "Kural (O16)",
         f"m² × {sy(V['kesme_tasi_m2_basina'])}", "PK-06 2, PK-07 2 tuttu")
    ekle("1008", "Çırpı ipi", "adet", Vk["cirpi_ipi"], "Kural (O16)", f"sabit {Vk['cirpi_ipi']}", "PK-02, PK-05, PK-06, PK-07 1")
    inox_vb = ASAGI(bina_m2 / Vk["inox_tasi_m2_bolu"])            # N3 adayı: listedeki "VİDA BİLGİ" sayfası (PK-06)
    ub = r("uc_aday_inox_boleni")
    for kalem in ("8'lik trapez uç", "PH2 uç"):
        ekle("1008", kalem, "adet", TAVAN(bina_m2 / Vk["uc_m2_bolu"]), "Şablon formülü", f"m² ÷ {sy(Vk['uc_m2_bolu'])}", "PK-01 ve PK-02'de tuttu",
             aday=inox_vb // ub, aday_notu=f"\"VİDA BİLGİ\": inox {inox_vb} ÷ {ub}, aşağı (yalnız PK-06 4 ✓; PK-01…05 4–6)")
    ekle("1008", "İnox taş", "adet", TAVAN(bina_m2 / Vk["inox_tasi_m2_bolu"]), "Şablon formülü", f"m² ÷ {sy(Vk['inox_tasi_m2_bolu'])}", "PK-01 ve PK-02'de tuttu",
         aday=inox_vb, aday_notu=f"\"VİDA BİLGİ\": bina m² ÷ {sy(Vk['inox_tasi_m2_bolu'])}, aşağı (PK-01, -05, -06 ✓; PK-02, -03 ✗)")
    # kitap: alçıpan ve Boardex levhaları × 40 (çalışma kitabının vida notu; Lokman, 7 Ekim 07:45). Veranda tavanı yeşil alçıpanda sayılır
    lev_t = n_beyaz + n_yesil
    duvar_lev = sum(s_["adet"] or 0 for s_ in satirlar if s_["kalem"].startswith("Duvar alçıpanı"))
    avl, avy = Vk["alcipan_vidasi_levha_basina"], V["alcipan_vidasi_yuvarlama"]
    levhalar = f"tavan {lev_t}" + (f" + duvar {duvar_lev}" if duvar_lev else "") + (f" + Boardex {n_bx}" if n_bx else "")
    if duvar_lev:
        ekle("1008", "Alçıpan vidası", "adet", int(math.ceil((lev_t + duvar_lev + n_bx) * avl / avy - 1e-9) * avy), "Şablon formülü (J7)",
             f"({levhalar}) levha × {avl}, {ye(avy)} yukarı", "PK-03'ün gerçek listesinde 3750; alçıpan ve Boardex levhaları (kitap)")
    else:
        ekle("1008", "Alçıpan vidası", "adet", int(math.ceil((lev_t + n_bx) * avl / avy - 1e-9) * avy), "Şablon formülü (O16)",
             f"({levhalar}) levha × {avl}, {ye(avy)} yukarı", "PK-07 1000 tuttu; PK-01'de 0; alçıpan ve Boardex levhaları (kitap)",
             aday=va, aday_notu=f"Şablon B (PK-02, PK-05): sabit {va}")
    ry = V["rysb_yuvarlama"]
    ekle("1008", "RYSB pul başlı vida", "adet", int(math.ceil(bina_m2 * Vk["rysb_m2_basina"] / ry - 1e-9) * ry), "Şablon formülü (O16)",
         f"m² × {sy(Vk['rysb_m2_basina'])}, {ye(ry)} yukarı", "PK-07 550 tuttu; PK-01'de 0",
         aday=int(math.ceil(bina_m2 * Vk["rysb_m2_basina"] / va - 1e-9) * va), aday_notu=f"Şablon B (PK-02 500 ✓): {ye(va)} yukarı")

    # ── 1009 Depo ───────────────────────────────────────────────────────────
    # kitap: tek kalem, yapı başına 1 (Lokman, 7 Ekim 07:45, C6); çatı çıkış kapağı listede yok (10 Ekim 10:18). 7.3'ün ayrı "Çatı müdahale
    # kapağı" satırı (O16; PK-07 1) kalktı (Lokman, 18 Ekim 19:22)
    acil, acil_ad = _ortak(k, "cati_mudahale_kapagi", "yapi_basina"), _ortak(k, "cati_mudahale_kapagi", "ad")
    # PVC betopan H'ı: baş makaslarda betopanların birleşim yerlerine konur, tavanla bağı yok; her evde 7 (Lokman, 20 Ekim 19:45 ve kart 19:50;
    # BK-12 PR-2c). Portatifev listelerinde Depo grubunun ilk satırı
    ekle("1009", "PVC plastik betopan H'ı", "adet", r("pvc_betopan_h"), "Kural (Lokman 20.10)", f"her evde sabit {r('pvc_betopan_h')} (baş makas betopanlarının birleşimleri)",
         "PK-07, TS-01, AP-02, AP-03, AP-05 7 (baş makas betopanı 6–8 levha)", aday=r("pvc_betopan_h_aday"),
         aday_notu=f"Şablon B (PK-02, PK-03): {r('pvc_betopan_h_aday')}")
    ekle("1009", acil_ad, "adet", 0 if any("acil" in x for x in alici) else acil, "Şablon formülü (Portatifev)",
         f"yapı başına {acil}" + (" (alıcıya ait)" if any("acil" in x for x in alici) else ""), "Şablon B'de yok; 7.3'ün ayrı çatı müdahale kapağı satırı kitapta yok")
    ekle("1009", "Şase pul", "adet", dubelli, "Şablon formülü (Portatifev)", f"dübelli H adedi kadar (dış H {ec[('dis', 'pano_eki')]} + dış 3'lü H {ec[('dis', 'uclu')]})",
         "PK-01 24 tuttu", aday=0, aday_notu="Şablon B: şase pul yok")
    ekle("1009", "Çelik dübel", "adet", dubelli, "Şablon formülü (O16)", "dübelli H adedi kadar", "PK-07 27, PK-02 22, PK-06 24 tuttu; PK-01'de 0")

    # ── 1010 Sıhhi tesisat ──────────────────────────────────────────────────
    tes_alici = any("tesisat" in x for x in alici)
    if tes_alici:
        ekle("1010", "Sıhhi tesisat grubu", "—", 0, "İş Emri", "alıcıya ait")
    elif any(x["tur"] in ISLAK for x in N["kapali"]):           # O17: bir banyolu evde sabit takım (PK-03, PK-05, PK-07 birebir)
        tk = _ortak(k, "tesisat")                                  # takımın adetleri kitaptan (ıslak hacim başına); prefabrik ev başına bir takım
        for kalem, olcu, anahtar in r("tesisat_takimi"):
            n = tk[anahtar]
            ekle("1010", kalem, olcu, n, "Kural (O17)", f"sabit takım (bir banyo): {n}", "PK-03, PK-05, PK-07 tuttu; PK-06 (üç ıslak nokta) boru 10, dirsek 20")
        vit_alici = any("vitrifiye" in x for x in alici)
        ekle("1010", "Vitrifiye ve batarya (duş teknesi, klozet, lavabo, batarya grubu)", "takım", 0 if vit_alici else None, "İş Emri" if vit_alici else "Kural yok",
             "alıcıya ait" if vit_alici else "—", "PK-07'de 4 satır × 1", aday=None if vit_alici else r("vitrifiye_aday"),
             aday_notu="" if vit_alici else f"PK-07 (dört satır × 1): {r('vitrifiye_aday')} takım")
    else:
        ekle("1010", "Sıhhi tesisat grubu", "—", None, "Kural yok", "—", "ıslak hacim yok")

    # ── 1011 Dere ───────────────────────────────────────────────────────────
    # 7.1: `dere_yok` (paftası deresiz parça); O15 (7.3): makassız açık veranda saçağı dere almazdı (PK-07). Kitapta her çatı panelli saçakta dere
    # (`panel_cati_kenarlari.dere`; Lokman, 10 Ekim; prefabrikte 18 Ekim 19:22): çatı panelli parça, paftası deresiz olsa da dere alır
    kanopi = lambda c: bool(c.get("dere_yok") or (c.get("acik") and c.get("makas_yok"))) and not (panelli(c) and pck["dere"])
    dere_hat = [x for c, o in C if not kanopi(c) for x in o["hatlar"]]
    pd_, bd = _ortak(k, "parca_boyu_m", "dere"), _ortak(k, "bindirme_m", "dere")
    dere = TAVAN(sum(dere_hat) / (pd_ - bd))
    dy = r("dere_aday_yuvarlama_mm")
    ekle("1011", "Metal dere", f"L {mm_m(pd_)}", dere, "Şablon formülü (J3)",
         f"dere hatları {' + '.join(f'{od(x)}' for x in dere_hat)} = {od(sum(dere_hat))} m ÷ {sy(pd_ - bd)}", "PK-01 6, PK-03 5 tuttu",
         aday=" + ".join(f"{n} × L {L_}" for L_, n in sorted(Counter(int(math.ceil(x * 1000 / dy - 1e-9) * dy) for x in dere_hat).items())),
         aday_notu=f"Şablon B (PK-02 2 × L 8500 ✓): hat başına tek parça, {dy} mm'ye yukarı")
    ekle("1011", "Dere kelepçesi", "adet", dere * _ortak(k, "dere_kelepcesi_dere_basina"), "Kural", f"dere {dere} × {_ortak(k, 'dere_kelepcesi_dere_basina')}",
         "PK-01 48 tuttu (PK-02 50)")
    ins = _ortak(k, "inis")
    akose, ekp = r("ana_cati_kose"), r("ek_cati_parcasi_basina")
    n_cumba = sum(1 for c, _o in C[1:] if not kanopi(c))
    orta_esik = sum(1 for x in ao["hatlar"] if x > ins["orta_inis_esigi_m"])
    orta_her = len(ao["hatlar"])                                 # R3 (13 Ekim 14:35): her saçak hattının ortasına 1
    taban = akose["besik"] if ana["tip"] == "besik" else akose["tek_yon"]
    esik_m = sy(ins["orta_inis_esigi_m"])
    if r("inis_orta") == "esik":                                 # Lokman: orta iniş uzunluğa bağlı (13 Ekim 15:10), eşik kitabın 9 m'si (18 Ekim 19:22)
        orta, orta_aday = orta_esik, orta_her
        formul_orta = f"{esik_m} m'yi geçen saçak hattına 1 orta ({orta})"
        aday_notu_inis = "14:35 kuralı (R3): her saçak hattının ortasına 1"
        dayanak_inis = f"Kural (uzunluğa bağlı: Lokman 13.10 15:10; eşik {esik_m} m: Lokman 18.10)"
    else:
        orta, orta_aday = orta_her, orta_esik
        formul_orta = f"saçak hattı başına 1 orta ({orta})"
        aday_notu_inis = f"uzunluğa bağlı (Lokman 18.10): yalnız {esik_m} m'yi geçen saçağa orta"
        dayanak_inis = "Kural (Lokman 13.10 14:35, R3)"
    inis = taban * ins["kose_basina"] + orta + ekp * n_cumba
    ib = _ortak(k, "inis_basina")
    ekle("1011", "Metal dere inişi aparatı", "adet", inis * ib["inis_aparati"], dayanak_inis,
         f"ana çatıda {taban} köşe × {ins['kose_basina']} + {formul_orta} + ek çatı parçası başına {ekp} ({n_cumba}) = {inis} iniş × {ib['inis_aparati']}",
         "E1, E4, E5, PK-01, PK-03 6; PK-07 8", pafta=("inis",), aday=(taban * ins["kose_basina"] + orta_aday + ekp * n_cumba) * ib["inis_aparati"],
         aday_notu=aday_notu_inis)
    ib_ = r("inis_borusu")
    if "metal" in oz.get("yağmur iniş borusu", ""):
        ekle("1011", "Metal iniş borusu", f"L {mm_m(pb('inis_borusu'))}", inis * ib["inis_borusu"], "Kural (H3)",
             f"özellik: metal iniş borusu → iniş {inis} × {ib['inis_borusu']} × L {mm_m(pb('inis_borusu'))}", "PK-02 tuttu")
    else:
        p0, p1 = ib_["pvc"]
        ekle("1011", "70 mm PVC dere iniş borusu", p0, inis, "Kural (Lokman 13.10, R2)",
             f"iniş {inis} × {p0} (PVC; {p0[2:]} + {p1[2:]} = bina yüksekliği 2500)", "PK-03, -05, -06, E1–E4 L 2000",
             aday=f"{inis} × {r('inis_borusu_aday')}", aday_notu=f"PK-01, E5: {r('inis_borusu_aday')}")
        ekle("1011", "70 mm PVC dere iniş borusu", p1, inis, "Kural (PK-01)", f"iniş {inis} × {p1} (PVC)")
    for kalem, anahtar in (("Açık dirsek", "acik_dirsek"), ("Kapalı dirsek", "kapali_dirsek"), ("PVC iniş kelepçesi", "inis_kelepcesi")):
        ekle("1011", kalem, "adet", inis * ib[anahtar], "Kural", f"iniş {inis} × {ib[anahtar]}", "PK-01 ve PK-02'de tuttu")
    ekle("1011", "Dere kapağı", "adet", taban + ekp * n_cumba, "Kural (J4)",
         f"ana çatıda {taban} (beşik {akose['besik']}, tek yön {akose['tek_yon']}) + ek çatı parçası başına {ekp} ({n_cumba})", "PK-01 4, PK-02 4, PK-03 6 tuttu")

    # ── 1012 Boya ───────────────────────────────────────────────────────────
    B, Bk = r("boya"), _ortak(k, "boya")                             # Bk: kitabın cephe boyası, mastiğin pencere başına adedi, köpük
    boya_alici = any("boya" in x for x in alici) or ("alıcı" in oz.get("dış cephe boya", "") and "alıcı" in oz.get("iç cephe boya", ""))
    if boya_alici:
        ekle("1012", "Boya grubu", "—", 0, "İş Emri", "alıcıya ait")
    else:
        dc, ic_ = Bk["dis_cephe_kova_m2_basina"], Bk["ic_cephe_kova_m2_basina"]
        ekle("1012", "Dış cephe boya (17,5 kg kova)", "kova", TAVAN(bina_m2 * dc), "Şablon formülü", f"m² × {sy(dc)}", "PK-07 2 tuttu (O18)")
        ekle("1012", "İç cephe boya (17,5 kg kova)", "kova", TAVAN(bina_m2 * ic_), "Şablon formülü", f"m² × {sy(ic_)}", "PK-07 2 tuttu (O18)")
        ekle("1012", "Kenarlar için boya", "10 kg", B["kenar"], "Kural (O18)", f"sabit {B['kenar']}", "PK-07 1")
        ekle("1012", "Tavan boya (17,5 kg kova)", "kova", B["tavan"], "Kural (O18)", f"sabit {B['tavan']}", "PK-07 1")
        ekle("1012", "Astar (17,5 kg kova)", "kova", B["astar"], "Kural (O18)", f"sabit {B['astar']}", "PK-07 1")
    # mastik ve dayson kural kitabından (Lokman, 7 Ekim 07:45; prefabrikte 18 Ekim 19:22): mastik pencere başına, boyadan bağımsız; pencere
    # alıcıya aitse yazılmaz (`kapsam_alici`). 7.3'te pencere + m² × 2/3 (PK-02'de 60) ve dayson m² × 0,03 (PK-06 3, PK-07 3)
    if not pencere_alici or ka["silikonize_mastik"]:
        mp_ = Bk["mastik_pencere_basina"]
        ekle("1012", "Silikonize mastik", "adet", len(pen) * mp_, "Kural kitabı", f"pencere {len(pen)} × {sy(mp_)} (m² payı yok, boyadan bağımsız)",
             "Lokman, 7 Ekim 07:45: boyu ne olursa olsun pencere başı 1; 7.3'te pencere + m² × 2/3 (PK-02'de 60)")
    ekle("1012", "Dayson (çatı renginde)", "adet", TAVAN(bina_m2 * Bk["dayson_m2_basina"]), "Kural kitabı", f"m² × {sy(Bk['dayson_m2_basina'])}, yukarı",
         "Excel hesaplama motoru (Lokman, 7 Ekim 07:45); 7.3'te m² × 0,03 (PK-06 3, PK-07 3 tuttu)")
    ekle("1012", "Poliüretan köpük", "adet", Bk["kopuk"], "Şablon formülü (O18)", f"standart {Bk['kopuk']}", "PK-02, PK-05, PK-06, PK-07 2 tuttu; PK-01'de 0")

    say = {"geometri": N["kaynak"], "pano_dis": sum(p["duvar"] == "dis" for p in N["panolar"]), "pano_ic": sum(p["duvar"] == "ic" for p in N["panolar"]),
           "brut_m2": bina_m2, "dis_olcu_cm": [round(N["W"], 2), round(N["D"], 2)], "dis_cevre_m": round(N["dis_cevre_m"], 2),
           "cati": [{"ad": c.get("ad"), "tip": c["tip"], "egik_m": round(o["egik"], 3), "mahya_m": round(o["mahya_boy"], 3)} for c, o in C],
           "tavan_net_m2": round(tavan_net, 2), "tavan": tavan_tipi, "makas": n_makas_top, "omega_hat_m": round(L_hat, 2), "ic_duvar_m": round(L_duvar, 2)}
    return {"is_emri_no": N.get("is_emri_no"), "kod": N.get("kod"), "uretici_surum": SURUM,
            "uretildi": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "kural_seti": {"prefabrik": R.get("sema"), "ortak": k.get("surum") or k.get("sema"), "kitap_seti": R["kitap_seti"]}, "girdi_ozeti": say,
            "satirlar": satirlar,
            "ozet": {"satir": len(satirlar), "adetli": sum(s["adet"] is not None for s in satirlar), "kural_yok": sum(s["dayanak"] == "Kural yok" for s in satirlar),
                     "pafta_katmanli": sum(s["pafta"] is not None for s in satirlar), "aday_li": sum(s["aday"] is not None for s in satirlar)}}


def xlsx(L: dict, yol: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Liste"
    ws.append([f"{L['kod']} · prefabrik yükleme listesi (TASLAK; Motor'un hesabı) · {L['is_emri_no']} · üretici {L['uretici_surum']} · {L['uretildi']}"])
    ws.append(["Grup", "Kalem", "Ölçü", "Adet", "Birim", "Dayanak", "Formül", "Kaynak / not", "Pafta", "Pafta notu", "Aday", "Aday notu"])
    for c_ in ws[2]:
        c_.font = Font(bold=True, color="FFFFFF"); c_.fill = PatternFill("solid", fgColor="2F3B4C")
    renk = {"Kural yok": "F2F2F2", "Liste kuralı": "FFF2CC", "Kural (uydurma)": "FCE4D6", "Kural (Portatifev)": "DDEBF7", TEK_KAYNAK: "FFC7CE"}
    for s in L["satirlar"]:
        ws.append([f"{s['grup']} {s['grup_adi']}", s["kalem"], s["olcu"], s["adet"], s["birim"], s["dayanak"], s["formul"], s["kaynak"], s["pafta"],
                   s["pafta_notu"], s["aday"], s["aday_notu"]])
        r = renk.get(s["dayanak"]) or ("E2EFDA" if s["dayanak"].startswith("Şablon") else "FCE4D6" if s["dayanak"].startswith("Varsayım") else None)
        if r:
            for c_ in ws[ws.max_row]:
                c_.fill = PatternFill("solid", fgColor=r)
    for i, w in enumerate([16, 46, 22, 7, 7, 18, 60, 50, 8, 50, 16, 50], 1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=3):
        for c_ in row:
            c_.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "C3"
    wb.save(yol)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", type=Path, nargs="?"); ap.add_argument("cikti", type=Path)
    ap.add_argument("--yapi", type=Path, default=None, help="pafta kipi: paftadan okunmuş geometri (yapi_pafta.json)")
    ap.add_argument("--pafta", type=Path, default=None, help="pafta katmanı: o projenin paftasından okunan adetler (karşılaştırma sütunu)")
    a = ap.parse_args(argv)
    if bool(a.yapi) == bool(a.is_emri):
        ap.error("ya İş Emri ya --yapi verilir")
    ie = json.loads(a.is_emri.read_text(encoding="utf-8")) if a.is_emri else None
    if ie is not None:
        from .cati_prefabrik import TIPLER, TIP_ADI
        tip = (ie.get("cati") or {}).get("tip")
        if tip in TIPLER:                                       # İE-17: beşik kuralı tek yön sayardı; yanlış sayı yazılmaz (A5 PR-1b)
            print(f"prefabrik liste: {TIP_ADI[tip]} ana çatının çatı satırları bu sürümde yok (cumba İE-17 PR-1b; kırmada kitapta "
                  f"prefabrik kural yok); liste yazılmaz", file=sys.stderr)
            return 1
    N = model_pafta(json.loads(a.yapi.read_text(encoding="utf-8"))) if a.yapi else model_motor(ie)
    pafta = json.loads(a.pafta.read_text(encoding="utf-8")) if a.pafta else None
    L = liste(N, kurallari_oku(), pafta)
    a.cikti.mkdir(parents=True, exist_ok=True)
    kod = (L["kod"] or "PK").replace("-", "")
    (a.cikti / f"{kod}_liste.json").write_text(json.dumps(L, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    xlsx(L, a.cikti / f"{kod}_liste.xlsx")
    print(json.dumps(L["ozet"], ensure_ascii=False), "→", a.cikti / f"{kod}_liste.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
