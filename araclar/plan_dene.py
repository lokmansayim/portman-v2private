#!/usr/bin/env python3
"""İE-14 r3 · P6: kör üretim ölçümü (M1–M5) ve örnek talepler — LLM'siz, ücretsiz. Önce ölçülür, hedef sonra konur (Lokman 14.10, 6. madde).

Kör üretim: bankadaki beş planın (Ç8201, Ç8801, KT-01, KT-02, KT-03) programı modelin kendisinden okunur (oda programı, katalog m²,
banyo/mutfak/depo, veranda yeri ve örtüsü, çatı tipi); model hem uyarlama kaynağından hem örnekten dışlanır (`haric`); üretilen en iyi plan
gerçek tanımla kıyaslanır:
- M1 denetçiden geçme, brüt alan farkı (%), işlev bazında net oda alanı farkı (m², ortalama mutlak)
- M2 duvar boyu (dış + iç, m) farkı (%)
- M3 pencere ve kapı sayısı farkı
- M4 yükleme listesi: satır anahtarı (grup, kalem, boyut) eşleşmesi ve ortak satırlarda miktar farkı medyanı. İKİ LİSTE DE AYNI MOTORDAN
  (kural seti güncel): sevkiyat listesi doğruluğu değil, planın listeye etkisi ölçülür. Sevkiyat doğruluğu kör testlerin işidir (IE-05).
- M5 üretim süresi (yerel)
Örnek talepler (`--talepler`): brifteki "95 m² 3+1 tek kat çelik, kırma çatı" ve beş benzeri; üretim yolu, puan, süre, doğrulama özeti.

Kullanım:
    python araclar/plan_dene.py --kor --talepler --rapor docs/raporlar/2026-10-15_IE14_Olcum.md [--json <dosya>] [--liste]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from beyin import plan_cozucu, plan_dogrulama, plan_uretici as PU  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402
from beyin.plan_program import PlanProgrami  # noqa: E402
from beyin.plan_sema import tanimdan  # noqa: E402
from beyin.plan_uyarlama import _veranda_cephesi, hazirla_kaynak  # noqa: E402

KOR = [("Ç8201", "C8201"), ("Ç8801", "C8801"), ("KT01", "KT01"), ("KT02", "KT02"), ("KT03", "KT03")]
TALEPLER = [
    ("95 m² 3+1, kırma", {"alan_m2": 95, "oda_programi": "3+1", "cati": {"tip": "kirma"}}),
    ("120 m² 3+1, önde veranda", {"alan_m2": 120, "oda_programi": "3+1", "veranda": {"istiyor": True, "konum": "on"}}),
    ("70 m² 2+1, beşik", {"alan_m2": 70, "oda_programi": "2+1", "cati": {"tip": "besik"}}),
    ("60 m² 1+1", {"alan_m2": 60, "oda_programi": "1+1"}),
    ("140 m² 4+1, kırma, köşe veranda", {"alan_m2": 140, "oda_programi": "4+1", "cati": {"tip": "kirma"},
                                         "veranda": {"istiyor": True, "konum": "kose"}}),
    ("110 m² 3+1, iki banyo", {"alan_m2": 110, "oda_programi": "3+1", "ozel_istekler": ["iki banyo olsun"]}),
]
VERANDA_KONUM = {"G": "on", "K": "arka", "B": "yan", "D": "yan", "kose": "kose"}


def _json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def kor_programi(kod: str, dosya: str) -> tuple[dict, dict]:
    """Modelin kendi programı (koordinatsız) ve gerçek tanımı."""
    a = {x["kod"]: x for x in _json(PU.ADAYLAR)}[kod]
    t = _json(KOK / "modeller" / f"{dosya}.json")
    islev = [(m.get("islev") or [""])[0] for m in t["mahaller"] if m.get("sinif") != "veranda"]
    p = tanimdan(t)
    kaynak = hazirla_kaynak(p) or p
    vc = _veranda_cephesi(kaynak)
    ver = next((m for m in kaynak["mahaller"] if m["islev"] == "veranda"), None)
    yatak = int(str(a["oda_programi"]).split("+")[0])
    prog = {"yatak": yatak, "alan_m2": float(a["katalog_m2"]), "banyo": max(1, min(2, islev.count("banyo"))),
            "mutfak": "ayri" if "mutfak" in islev else "acik", "depo": 1 if "depo" in islev else 0,
            "veranda": ({"istiyor": True, "konum": VERANDA_KONUM.get(vc, "on"), "ortu": (ver or {}).get("ortu")} if vc else {"istiyor": False}),
            "cati_tipi": "kirma" if "kirma" in str(t["cati"].get("tip")) else "besik"}
    return PlanProgrami.model_validate(prog).model_dump(), t


def _net_islev(tanim: dict) -> dict[str, float]:
    from motor.genel import yapi as Y
    g = Y.kur(tanim)
    out: dict[str, float] = {}
    for m in tanim["mahaller"]:
        if m.get("sinif") == "veranda":
            continue
        i = (m.get("islev") or ["depo"])[0]
        i = i if i in ("salon", "mutfak", "yatak_odasi", "banyo", "hol") else "depo"
        out[i] = out.get(i, 0.0) + g["bolgeler"][m["ad"]]["alan_m2"]
    return {k: round(v, 2) for k, v in out.items()}


def _duvar_m(tanim: dict) -> float:
    return round(sum(max(d["kutu"][2] - d["kutu"][0], d["kutu"][3] - d["kutu"][1]) for d in tanim["duvarlar"]
                     if str(d.get("sinif") or "").startswith(("dis", "ic"))) / 100, 2)


def _aciklik(tanim: dict) -> tuple[int, int]:
    a = tanim["acikliklar"]
    return sum(1 for x in a if x["tur"] == "pencere"), sum(1 for x in a if x["tur"] in ("dis_kapi", "ic_kapi", "gecit"))


def _liste(tanim: dict, kok: Path) -> dict[tuple, float]:
    from motor.genel.uret import uret
    kok.mkdir(parents=True, exist_ok=True)
    y = kok / "tanim.json"
    y.write_text(json.dumps(tanim, ensure_ascii=False), encoding="utf-8")
    m = uret(y, kok / "c", perspektif=False, bayi=False, yalniz_liste=True)
    lst = _json(kok / "c" / m["yukleme_json"]) if m.get("yukleme_json") else _json(next((kok / "c").glob("*_yukleme.json")))
    out = {}
    for s in lst.get("satirlar") or []:
        q = s.get("adet") if s.get("adet") is not None else s.get("olcu")
        if isinstance(q, (int, float)):
            out[(s.get("grup"), s.get("kalem"), s.get("boyut"))] = float(q)
    return out


def liste_kiyasi(uretilen: dict, gercek: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        lu, lg = _liste(uretilen, Path(d) / "u"), _liste(gercek, Path(d) / "g")
    ortak = set(lu) & set(lg)
    farklar = [abs(lu[k] - lg[k]) / max(abs(lg[k]), 1e-9) for k in ortak if lg[k]]
    return {"gercek_satir": len(lg), "uretilen_satir": len(lu), "ortak": len(ortak), "eslesme": round(len(ortak) / max(1, len(lg)), 3),
            "miktar_farki_medyan": round(statistics.median(farklar), 3) if farklar else None}


def kor_olc(kod: str, dosya: str, liste: bool = False) -> dict:
    prog, gercek = kor_programi(kod, dosya)
    t0 = time.time()
    adaylar, nedenler, denetim = PU._uret_bir(prog, 1, (kod,), "KOR")
    sure = int((time.time() - t0) * 1000)
    s = {"model": kod, "program": prog, "sure_ms": sure, "denetim_sayisi": denetim, "gecti": bool(adaylar)}
    if not adaylar:
        s["nedenler"] = nedenler[:4]
        return s
    a = adaylar[0]
    u = a["tanim"]
    gm2, um2 = float(prog["alan_m2"]), a["ozet"]["brut_m2"]
    ni_g, ni_u = _net_islev(gercek), _net_islev(u)
    islevler = sorted(set(ni_g) | set(ni_u))
    s.update(yol=a["yol"], kaynak=a.get("kaynak"), puan=a["puan"], brut_m2=[gm2, um2], brut_fark_yuzde=round((um2 - gm2) / gm2 * 100, 1),
             oda_islev=({i: [ni_g.get(i, 0.0), ni_u.get(i, 0.0)] for i in islevler}),
             oda_fark_ort_m2=round(statistics.mean(abs(ni_g.get(i, 0) - ni_u.get(i, 0)) for i in islevler), 2),
             duvar_m=[_duvar_m(gercek), _duvar_m(u)], pencere_kapi=[_aciklik(gercek), _aciklik(u)],
             dogrulama=plan_dogrulama.rapor(a["denetim"], u)["ozet"])
    s["duvar_fark_yuzde"] = round((s["duvar_m"][1] - s["duvar_m"][0]) / s["duvar_m"][0] * 100, 1)
    if liste:
        s["liste"] = liste_kiyasi(u, gercek)
    return s


def talep_olc(etiket: str, talep: dict) -> dict:
    s = PU.uret(talep, ayar={"acik": False})
    return {"talep": etiket, "durum": s["durum"], "sure_ms": s["sure_ms"], "yol": s.get("yol"),
            "adaylar": [{"yol": a["yol"], "puan": a["puan"], "brut_m2": a["ozet"].get("brut_m2"), "odalar": a["ozet"].get("odalar_m2"),
                         "dogrulama": plan_dogrulama.rapor(a["denetim"], a["tanim"])["ozet"]} for a in s["adaylar"]],
            "notlar": s.get("notlar"), "okunamayan": s.get("okunamayan"), "ihlal": (s["denemeler"][-1].get("ihlaller") if not s["adaylar"] else None)}


def rapor(kor: list[dict], talepler: list[dict]) -> str:
    r = ["# İE-14 r3 · ölçüm, baz çizgisi (P6)", "",
         "Hedef yok: önce ölçülür, hedef sonra Lokman'ın kararıyla konur (14.10, 6. madde). LLM çağrısı yok (kör üretim ve örnek talepler "
         "yapısal programla koşar). Kapılar (hedef değil): denetçiden geçmeyen plan gösterilmez; P6001, yedi çelik model, harness ve referans değişmez.", ""]
    if kor:
        r += ["## Kör üretim (M1–M5)", "",
              "Program modelin kendisinden okunur; model uyarlama kaynağından ve örnekten dışlanır. KT-01/02/03'ün dış hattı dikdörtgen değil "
              "(müştemilat, sundurma); 14a dikdörtgen üretir, fark bunu da içerir.", "",
              "| Model | Geçti | Yol (kaynak) | Brüt m² gerçek → üretilen | Brüt fark | Oda alanı ort. fark | Duvar m gerçek → üretilen | "
              "Pencere/kapı gerçek → üretilen | Liste eşleşme · miktar farkı medyanı | Süre |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for s in kor:
            if not s["gecti"]:
                r.append(f"| {s['model']} | hayır | — | — | — | — | — | — | — | {s['sure_ms']} ms |")
                continue
            ls = s.get("liste")
            lm = f"{ls['ortak']}/{ls['gercek_satir']} ({ls['eslesme']:.0%}) · {ls['miktar_farki_medyan']:.0%}" if ls and ls["miktar_farki_medyan"] is not None else "—"
            (pg, kg), (pu, ku) = s["pencere_kapi"]
            r.append(f"| {s['model']} | evet | {s['yol']}{' (' + s['kaynak'] + ')' if s.get('kaynak') else ''} | {s['brut_m2'][0]:g} → {s['brut_m2'][1]:g} | "
                     f"{s['brut_fark_yuzde']:+.1f}% | {s['oda_fark_ort_m2']:.2f} m² | {s['duvar_m'][0]:g} → {s['duvar_m'][1]:g} ({s['duvar_fark_yuzde']:+.1f}%) | "
                     f"{pg}/{kg} → {pu}/{ku} | {lm} | {s['sure_ms']} ms |")
        r += ["", "İşlev bazında net oda alanı (m², gerçek → üretilen):", ""]
        for s in kor:
            if s["gecti"]:
                r.append(f"- {s['model']}: " + "; ".join(f"{i.replace('_', ' ')} {g:g} → {u:g}" for i, (g, u) in s["oda_islev"].items()))
        r.append("")
        r.append("M4 notu: iki liste de aynı motordan ve güncel kural setinden üretildi; sevkiyat listesi doğruluğu değil, planın listeye etkisi.")
        r.append("")
    if talepler:
        r += ["## Örnek talepler (M1, M5)", "", "| Talep | Durum | Yol | Adaylar (yol, puan, brüt m²) | Süre |", "|---|---|---|---|---|"]
        for t in talepler:
            ad = "; ".join(f"{a['yol']} {a['puan']:.1f} {a['brut_m2']:g} m²" for a in t["adaylar"]) or (", ".join(t["ihlal"] or [])[:120])
            r.append(f"| {t['talep']} | {t['durum']} | {t['yol'] or '—'} | {ad} | {t['sure_ms']} ms |")
        r.append("")
        r.append("Doğrulama özeti (ilk aday): " + (talepler[0]["adaylar"][0]["dogrulama"] if talepler and talepler[0]["adaylar"] else "—"))
    return "\n".join(r) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="İE-14 r3 ölçüm: kör üretim ve örnek talepler (LLM'siz)")
    ap.add_argument("--kor", action="store_true")
    ap.add_argument("--talepler", action="store_true")
    ap.add_argument("--liste", action="store_true", help="M4: yükleme listesi kıyası (genel motorla; yavaş)")
    ap.add_argument("--rapor", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    kor = [kor_olc(k, d, a.liste) for k, d in KOR] if a.kor else []
    tal = [talep_olc(e, t) for e, t in TALEPLER] if a.talepler else []
    if a.rapor:
        a.rapor.write_text(rapor(kor, tal), encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps({"kor": kor, "talepler": tal}, ensure_ascii=False, indent=1, default=list) + "\n", encoding="utf-8")
    for s in kor:
        print(s["model"], "geçti" if s["gecti"] else "geçmedi", s.get("yol"), s.get("brut_fark_yuzde"), s.get("oda_fark_ort_m2"), s.get("sure_ms"))
    for t in tal:
        print(t["talep"], t["durum"], t["yol"], t["sure_ms"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
