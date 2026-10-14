#!/usr/bin/env python3
"""İE-14 · plan üretecinin geliştirme denemeleri: kör üretim ve örnek talepler (LLM'li, ÜCRETLİ) ya da kayıttan yeniden koşu (LLM'siz).

Kör üretim: bankadaki beş planın (Ç8201, Ç8801, KT-01, KT-02, KT-03) oda programı ve m²'si verilir, modelin kendisi örnek
listesinden çıkarılır; üretilen plan gerçekle kıyaslanır (denetim, dış ölçü, brüt alan, oda sayıları ve alanları, kapı komşulukları).
Örnek talepler: brifteki "95 m² 3+1 tek kat çelik, kırma çatı" ve beş benzeri (çıkarım çağrısı yapılmaz; talep yapısal yazılır).

Ücret (İE-14 › Sınırlar; D-18): LLM çağrısı yalnız `--ucretli` ile ve `--tavan` sayısına kadar yapılır; her çağrı
`testler/plan/kayitlar/cagri_defteri.json`'a (zaman, etiket, çağrı, token) yazılır ve tavan defterdeki toplamla denetlenir.
Cevaplar `testler/plan/kayitlar/<etiket>.json`'a yazılır; `--kayittan` onları manuel arka uçla oynatır (ücretsiz).
Anahtar ortamdan (`ANTHROPIC_API_KEY`); hiçbir yere yazılmaz.

Kullanım:
    python araclar/plan_dene.py --kor --talepler --ucretli --tavan 45 [--cikti <klasör>] [--rapor docs/raporlar/<ad>.md]
    python araclar/plan_dene.py --kayittan [--cikti <klasör>] [--rapor …]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from beyin import plan_uretici as PU  # noqa: E402
from beyin.plan_sema import tanimdan  # noqa: E402

KAYIT = KOK / "testler" / "plan" / "kayitlar"
DEFTER = KAYIT / "cagri_defteri.json"
KOR = [("Ç8201", "C8201"), ("Ç8801", "C8801"), ("KT01", "KT01"), ("KT02", "KT02"), ("KT03", "KT03")]
TALEPLER = [
    ("talep_95_3arti1_kirma", {"alan_m2": 95, "oda_programi": "3+1", "yapi_turu": "celik", "kat_sayisi": 1, "cati": {"tip": "kirma"},
                               "ozet": "95 m² 3+1 tek kat çelik, kırma çatı"}),
    ("talep_120_3arti1_veranda", {"alan_m2": 120, "oda_programi": "3+1", "yapi_turu": "celik", "kat_sayisi": 1,
                                  "veranda": {"istiyor": True, "konum": "on"}, "ozet": "120 m² 3+1 çelik, önde veranda"}),
    ("talep_70_2arti1_besik", {"alan_m2": 70, "oda_programi": "2+1", "yapi_turu": "celik", "kat_sayisi": 1, "cati": {"tip": "besik"},
                               "ozet": "70 m² 2+1 çelik, beşik çatı"}),
    ("talep_60_1arti1", {"alan_m2": 60, "oda_programi": "1+1", "yapi_turu": "celik", "kat_sayisi": 1, "ozet": "60 m² 1+1 çelik"}),
    ("talep_140_4arti1_kirma_veranda", {"alan_m2": 140, "oda_programi": "4+1", "yapi_turu": "celik", "kat_sayisi": 1, "cati": {"tip": "kirma"},
                                        "veranda": {"istiyor": True, "konum": "kose"}, "ozet": "140 m² 4+1 çelik, kırma çatı, köşe veranda"}),
    ("talep_110_3arti1_iki_banyo", {"alan_m2": 110, "oda_programi": "3+1", "yapi_turu": "celik", "kat_sayisi": 1,
                                    "ozel_istekler": ["iki banyo olsun"], "ozet": "110 m² 3+1 çelik, iki banyolu"}),
]


def defter_oku() -> list[dict]:
    try:
        return json.loads(DEFTER.read_text(encoding="utf-8"))
    except Exception:
        return []


def defter_ekle(kayit: dict) -> None:
    d = defter_oku()
    d.append(kayit)
    DEFTER.parent.mkdir(parents=True, exist_ok=True)
    DEFTER.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def kor_talepler() -> list[tuple[str, dict, str]]:
    """(etiket, talep, model dosyası) — talep yalnız gerçek modelin programı, m²'si, verandası ve çatı tipi."""
    adaylar = {a["kod"]: a for a in json.loads(PU.ADAYLAR.read_text(encoding="utf-8"))}
    out = []
    for kod, dosya in KOR:
        a = adaylar[kod]
        t = json.loads((KOK / "modeller" / f"{dosya}.json").read_text(encoding="utf-8"))
        veranda = any(m.get("sinif") == "veranda" for m in t["mahaller"])
        tip = "kirma" if "kirma" in str(t["cati"].get("tip")) else "besik"
        out.append((f"kor_{dosya}", {"alan_m2": a["katalog_m2"], "oda_programi": a["oda_programi"], "yapi_turu": "celik", "kat_sayisi": 1,
                                     "cati": {"tip": tip}, "veranda": {"istiyor": veranda},
                                     "ozet": f"{a['katalog_m2']:g} m² {a['oda_programi']} tek kat çelik ({'verandalı' if veranda else 'verandasız'})"},
                    dosya))
    return out


def _kapi_komsuluklari(plan: dict) -> Counter:
    islev = {m["ad"]: m["islev"] for m in plan["mahaller"]}
    c = Counter()
    for k in plan.get("kapilar", []):
        a, b = (list(k["arasinda"]) + ["", ""])[:2]
        ia, ib = islev.get(a, "dis" if a == "dis" else "?"), islev.get(b, "dis" if b == "dis" else "?")
        ia, ib = ("dis" if ia == "veranda" else ia), ("dis" if ib == "veranda" else ib)
        c[tuple(sorted((ia, ib)))] += 1
    return c


def kiyas(uretilen: dict, gercek_plan: dict, gercek_odalar: dict, gercek_m2: float) -> dict:
    """Üretilen ile gerçek: brüt farkı, dış ölçü, işlev sayıları, oda alanı farkı (işlev içinde büyükten küçüğe eşleşme), kapı komşuluğu."""
    p, oz = uretilen["plan"], uretilen["ozet"]
    gi = Counter(m["islev"] for m in gercek_plan["mahaller"] if m["islev"] != "veranda")
    ui = Counter(m["islev"] for m in p["mahaller"] if m["islev"] != "veranda")
    islev_g = {m["ad"]: m["islev"] for m in gercek_plan["mahaller"]}
    farklar = []
    for isl in set(gi) | set(ui):
        g = sorted((v for k, v in gercek_odalar.items() if islev_g.get(k) == isl), reverse=True)
        u = sorted((v for k, v in (oz.get("odalar_m2") or {}).items() if any(m["ad"] == k and m["islev"] == isl for m in p["mahaller"])), reverse=True)
        farklar += [abs(a - b) for a, b in zip(g, u)]
    kg, ku = _kapi_komsuluklari(gercek_plan), _kapi_komsuluklari(p)
    kesisim, birlesim = sum((kg & ku).values()), sum((kg | ku).values())
    return {"brut_m2": oz.get("brut_m2"), "gercek_m2": gercek_m2, "brut_fark_yuzde": round(100 * (oz.get("brut_m2", 0) - gercek_m2) / gercek_m2, 1),
            "dis_olcu": oz.get("dis_olcu_cm"), "gercek_dis_olcu": [gercek_plan["dis_olcu"]["en"], gercek_plan["dis_olcu"]["boy"]],
            "islev_ayni": gi == ui, "islev": dict(ui), "gercek_islev": dict(gi),
            "oda_alan_fark_ort_m2": round(sum(farklar) / len(farklar), 2) if farklar else None,
            "kapi_komsuluk_benzerligi": round(kesisim / birlesim, 2) if birlesim else None}


def ciz(tanim: dict, hedef: Path, etiket: str) -> str | None:
    from motor.genel import uret
    hedef.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        yol = Path(tmp) / "tanim.json"
        yol.write_text(json.dumps(tanim, ensure_ascii=False), encoding="utf-8")
        m = uret.uret(yol, hedef / etiket, is_emri_no=f"PM-DENEME-{etiket}", revizyon=1, perspektif=False, bayi=True)
    return "passed" if m.get("passed") else "HATALI"


def kos(isler: list[tuple[str, dict, str | None]], kayittan: bool, ucretli: bool, tavan: int, ayar: dict, cikti: Path | None) -> list[dict]:
    satirlar = []
    for etiket, talep, model in isler:
        yol = KAYIT / f"{etiket}.json"
        haric = (dict((d, k) for k, d in KOR)[model],) if model else ()
        if kayittan:
            if not yol.exists():
                print(f"  {etiket}: kayıt yok, atlandı")
                continue
            k = json.loads(yol.read_text(encoding="utf-8"))
            s = PU.uret(k["talep"], hazir=[d["plan"] for d in k["denemeler"]], haric=haric)
            talep = k["talep"]
        else:
            harcanan = sum(x.get("cagri", 0) for x in defter_oku())
            en_cok = int(ayar.get("en_cok_cagri", 3))
            if not ucretli or harcanan + en_cok > tavan:
                print(f"  {etiket}: DURDU — ücretli çağrı izni yok ya da tavan ({harcanan} + {en_cok} > {tavan})")
                break
            s = PU.uret(talep, ayar=ayar, haric=haric)
            KAYIT.mkdir(parents=True, exist_ok=True)
            yol.write_text(json.dumps(PU.kayit(s, talep, etiket), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            defter_ekle({"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "etiket": etiket, "cagri": s["cagri"],
                         "girdi_token": s["girdi_token"], "cikti_token": s["cikti_token"], "model": s.get("model"), "durum": s["durum"]})
        satir = {"etiket": etiket, "durum": s["durum"], "deneme": len(s["denemeler"]), "cagri": s["cagri"],
                 "son_ihlaller": (s["denemeler"][-1]["ihlaller"] if s["denemeler"] and s["durum"] != "gecerli" else []), "hata": s.get("hata")}
        if model and s["durum"] == "gecerli":
            gt = json.loads((KOK / "modeller" / f"{model}.json").read_text(encoding="utf-8"))
            a = next(x for x in json.loads(PU.ADAYLAR.read_text(encoding="utf-8")) if x["tanim"] == f"modeller/{model}.json")
            satir["kiyas"] = kiyas(s, tanimdan(gt), a["ozet"]["odalar"], a["katalog_m2"])
        if cikti and s["durum"] == "gecerli":
            satir["cizim"] = ciz(s["tanim"], cikti, etiket)
        print(f"  {etiket}: {s['durum']} · deneme {satir['deneme']} · çağrı {s['cagri']}" + (f" · {satir.get('kiyas')}" if satir.get("kiyas") else ""))
        satirlar.append(satir)
    return satirlar


def rapor_yaz(yol: Path, satirlar: list[dict], kayittan: bool) -> None:
    defter = defter_oku()
    s = [f"# İE-14 · plan üreteci denemesi ({dt.date.today():%d.%m.%Y})", "",
         f"Kaynak: `araclar/plan_dene.py` {'--kayittan (LLM çağrısı yok)' if kayittan else '(LLM, ücretli)'}; kayıtlar `testler/plan/kayitlar/`.",
         f"Çağrı defteri toplamı: {sum(x.get('cagri', 0) for x in defter)} çağrı, {sum(x.get('girdi_token') or 0 for x in defter)} girdi + "
         f"{sum(x.get('cikti_token') or 0 for x in defter)} çıktı token.", "",
         "| Deneme | Sonuç | Deneme sayısı | Brüt m² (gerçek) | Dış ölçü (gerçek) | İşlevler aynı | Oda alanı farkı ort. | Kapı komşuluğu | Çizim |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        k = r.get("kiyas") or {}
        s.append(f"| {r['etiket']} | {r['durum']} | {r['deneme']} | "
                 + (f"{k['brut_m2']} ({k['gercek_m2']:g}; {k['brut_fark_yuzde']:+.1f} %)" if k else "—") + " | "
                 + (f"{k['dis_olcu']} ({k['gercek_dis_olcu']})" if k else "—") + " | "
                 + (("evet" if k["islev_ayni"] else f"hayır: {k['islev']} ↔ {k['gercek_islev']}") if k else "—") + " | "
                 + (f"{k['oda_alan_fark_ort_m2']} m²" if k.get("oda_alan_fark_ort_m2") is not None else "—") + " | "
                 + (f"{k['kapi_komsuluk_benzerligi']}" if k.get("kapi_komsuluk_benzerligi") is not None else "—") + " | "
                 + (r.get("cizim") or "—") + " |")
    gecmeyen = [r for r in satirlar if r["durum"] != "gecerli"]
    if gecmeyen:
        s += ["", "## Geçmeyenler (son denemenin ihlalleri)"]
        for r in gecmeyen:
            s.append(f"- **{r['etiket']}** ({r['durum']}): " + ("; ".join(r["son_ihlaller"][:6]) or (r.get("hata") or "")))
    yol.write_text("\n".join(s) + "\n", encoding="utf-8")
    print("rapor:", yol)


def main(argv=None):
    ap = argparse.ArgumentParser(description="İE-14 plan üreteci: kör üretim ve örnek talepler")
    ap.add_argument("--kor", action="store_true")
    ap.add_argument("--talepler", action="store_true")
    ap.add_argument("--kayittan", action="store_true", help="kayıtlı cevapları LLM'siz oynat")
    ap.add_argument("--ucretli", action="store_true", help="LLM çağrısına izin (Lokman'ın onayıyla)")
    ap.add_argument("--tavan", type=int, default=0, help="defterdeki toplam çağrı üst sınırı")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--cikti", type=Path)
    ap.add_argument("--rapor", type=Path)
    a = ap.parse_args(argv)
    isler: list[tuple[str, dict, str | None]] = []
    if a.kor or a.kayittan:
        isler += kor_talepler()
    if a.talepler or a.kayittan:
        isler += [(e, t, None) for e, t in TALEPLER]
    if not isler:
        ap.error("--kor, --talepler ya da --kayittan")
    satirlar = kos(isler, a.kayittan, a.ucretli, a.tavan, {"backend": "anthropic", "model": a.model, "effort": a.effort}, a.cikti)
    if a.rapor:
        rapor_yaz(a.rapor, satirlar, a.kayittan)


if __name__ == "__main__":
    main()
