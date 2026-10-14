"""İE-14 · plan üreteci (r3; Lokman 14.10.2026): talep → oda programı → bankadan uyarlama → deterministik çözücü → en son sınırlı LLM.

LLM koordinat yazmaz. Sıra:
1. Bankadan en yakın plan: kararın bugünkü seçenek yolu (uyan model varsa üretim hiç çağrılmaz; `karar.plan_uretimi_uygun`).
2. Program (`plan_program.oku`): yapısal talepten koddan; tanınmayan serbest istek kalırsa ve ayar açıksa tek LLM çağrısı (koordinatsız).
3. Bankadan uyarlama (`plan_uyarlama.uyarla`) ve deterministik çözücü (`plan_cozucu.coz`); ikisinin adayları puanla sıralanır, en iyi `n`.
4. İkisi de boş dönerse ve ayar açıksa en çok `en_cok_cagri` (2) kez `plan_program.yeniden`: LLM programı ve yerleşim ipucunu en az
   değişiklikle yeniden önerir (adsız örnek özetleriyle); yerleşimi yine çözücü kurar, denetçi geçirir. Değişen her şey bayiye yazılır.
Her aday denetçiden geçmiştir (`plan_denetim.denetle`); sözleşmesi (`portman.plan/0.1`) ve doğrulama kalemleri yanındadır.

`manuel` arka uç kayıtlı cevapları oynatır: `hazir = {"program": {...} | None, "yeniden": [{...}, …]}` (LLM çağrısı yok).
"""
from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

from beyin import numara, plan_cozucu, plan_program, plan_uyarlama
from beyin.plan_sema import sozlesme, tanimdan

ROOT = Path(__file__).resolve().parent.parent
ADAYLAR = ROOT / "beyin" / "veri" / "adaylar.json"
VARSAYILAN_AYAR = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "low", "en_cok_cagri": 2, "timeout_s": 60,
                   "max_tokens": 2000}
YOL_ADI = {"uyarlama": "bankadaki bir modelden uyarlandı", "cozucu": "programdan çözüldü", "llm_program": "programdan çözüldü"}


@lru_cache(maxsize=1)
def _banka() -> tuple[dict, ...]:
    """Bankadaki çelik adaylar, çatı varyantları ayıklanmış (aynı plan): {kod, katalog_m2, oda_programi, odalar, plan}. Kod iç kayıttır."""
    adaylar = json.loads(ADAYLAR.read_text(encoding="utf-8"))
    varyant = {v for a in adaylar for v in (a.get("varyantlar") or [])}
    out = []
    for a in adaylar:
        if a.get("motor") != "genel" or a.get("durum") == "test" or a["kod"] in varyant:
            continue
        tanim = json.loads((ROOT / a["tanim"]).read_text(encoding="utf-8"))
        out.append({"kod": a["kod"], "katalog_m2": a.get("katalog_m2"), "oda_programi": a.get("oda_programi"),
                    "odalar": (a.get("ozet") or {}).get("odalar") or {}, "plan": tanimdan(tanim)})
    return tuple(out)


def hedef_alan(talep: dict) -> float | None:
    if talep.get("alan_m2"):
        return float(talep["alan_m2"])
    d = talep.get("dis_olcu") or {}
    if d.get("en_m") and d.get("boy_m"):
        return round(float(d["en_m"]) * float(d["boy_m"]), 1)
    return None


def _sec(gruplar: list[list[dict]], n: int) -> list[dict]:
    """Uyarlama ve çözücü adayları puanla birlikte sıralanır (küçük iyi); en iyi n."""
    hepsi = sorted((a for g in gruplar for a in g), key=lambda a: (a["puan"], a["yol"], json.dumps(a["plan"]["dis_olcu"], sort_keys=True)))
    return hepsi[:n]


def _uret_bir(program: dict, n: int, haric: tuple[str, ...], kod: str, ipucu: dict | None = None) -> tuple[list[dict], list[str], int]:
    u = plan_uyarlama.uyarla(program, n=n, haric=haric, kod=kod) if not ipucu else {"adaylar": [], "denetim": 0}
    c = plan_cozucu.coz(program, n=n, kod=kod, ipucu=ipucu)
    return _sec([u["adaylar"], c["adaylar"]], n), (c.get("notlar") or []) + ([] if c["adaylar"] else c.get("ihlaller") or []), \
        u["denetim"] + c["denetim"]


def uret(talep: dict, ayar: dict | None = None, hazir: dict | None = None, haric: tuple[str, ...] = (), kod: str = "YENI", n: int = 2) -> dict:
    """Talep → en çok n plan. Dönüş: {durum: gecerli|gecersiz|hata, adaylar: [{plan, tanim, ozet, puan, yol, kaynak?, islemler?, kalip?,
    denetim, sozlesme}], program, degisen, okunamayan, notlar, cagri, girdi_token, cikti_token, hata, model, denemeler, sure_ms} ve geriye
    uyum için ilk adayın plan/tanim/ozet/puan/yol'u. `ayar['acik']` yanlışsa LLM hiç çağrılmaz (kör üretim). İstisna fırlatmaz."""
    t0 = time.time()
    a = {**VARSAYILAN_AYAR, **(ayar or {})}
    hz = hazir or {}
    if hazir is not None:
        a["backend"] = "manuel"
    llm_acik = bool(a.get("acik")) or hazir is not None
    s = {"durum": "gecersiz", "adaylar": [], "program": None, "degisen": [], "okunamayan": [], "notlar": [], "cagri": 0, "girdi_token": 0,
         "cikti_token": 0, "hata": None, "model": a.get("model") if (a["backend"] != "manuel" and llm_acik) else None, "denemeler": [],
         "plan": None, "tanim": None, "ozet": {}, "puan": None, "yol": None}

    def say(x: dict) -> None:
        s["cagri"] += x.get("cagri") or 0
        s["girdi_token"] += x.get("girdi_token") or 0
        s["cikti_token"] += x.get("cikti_token") or 0

    pr = plan_program.oku(talep, ayar={**a, "acik": llm_acik}, hazir=hz.get("program"))
    say(pr)
    if pr.get("hata") and not pr.get("program"):
        s.update(durum="hata", hata=pr["hata"], sure_ms=int((time.time() - t0) * 1000))
        return s
    program = pr["program"]
    s["program"], s["okunamayan"] = program, list(pr.get("okunamayan") or [])
    adaylar, nedenler, denetim = _uret_bir(program, n, haric, kod)
    s["denemeler"].append({"basamak": "uyarlama+cozucu", "aday": len(adaylar), "denetim": denetim, "ihlaller": [] if adaylar else nedenler[:8]})
    s["notlar"] += plan_cozucu.hazirla(program)["notlar"]
    for i in range(int(a["en_cok_cagri"]) if (not adaylar and llm_acik) else 0):
        hz_y = (hz.get("yeniden") or [])
        if a["backend"] == "manuel" and i >= len(hz_y):
            break
        y = plan_program.yeniden(program, nedenler, ayar=a, hazir=hz_y[i] if a["backend"] == "manuel" else None, haric=haric)
        say(y)
        if not y.get("program"):
            s["denemeler"].append({"basamak": "llm_program", "aday": 0, "hata": y.get("hata")})
            if y.get("hata"):
                s["hata"] = y["hata"]
            break
        adaylar, nedenler, denetim = _uret_bir(y["program"], n, haric, kod, ipucu=y.get("ipucu") or None)
        s["denemeler"].append({"basamak": "llm_program", "aday": len(adaylar), "denetim": denetim, "degisen": y["degisen"],
                               "ipucu": y.get("ipucu"), "ihlaller": [] if adaylar else nedenler[:8]})
        if adaylar:
            for x in adaylar:
                x["yol"] = "llm_program"
            s["degisen"], s["program"] = y["degisen"], y["program"]
            break
    for x in adaylar:
        x["sozlesme"] = sozlesme(x["plan"], "tek_kat_celik", {"yol": x["yol"], "kod": x.get("kaynak"), "islemler": x.get("islemler") or []},
                                 varsayimlar=s["notlar"])
    s["adaylar"] = adaylar
    if adaylar:
        s.update(durum="gecerli", hata=None, **{k: adaylar[0][k] for k in ("plan", "tanim", "ozet", "puan", "yol")})
    s["sure_ms"] = int((time.time() - t0) * 1000)
    return s


def _tr(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


def plan_farki(eski: dict, yeni: dict) -> list[str]:
    """İki plan arasındaki bayiye söylenecek farklar (kodun okuması; LLM'in özeti değil, K18 yönü): dış ölçü, mahal alanı (eksenden),
    eklenen/kaldırılan mahal, pencere ve kapı."""
    def alan(m):
        return sum((r[2] - r[0]) * (r[3] - r[1]) for r in m["dikdortgenler"]) / 1e4
    out = []
    e, y = eski["dis_olcu"], yeni["dis_olcu"]
    if (e["en"], e["boy"]) != (y["en"], y["boy"]):
        out.append(f"dış ölçü {e['en']}×{e['boy']} → {y['en']}×{y['boy']} cm")
    em, ym = {m["ad"]: m for m in eski["mahaller"]}, {m["ad"]: m for m in yeni["mahaller"]}
    for ad in ym:
        if ad not in em:
            out.append(f"{ad} eklendi ({_tr(alan(ym[ad]))} m²)")
        elif abs(alan(ym[ad]) - alan(em[ad])) >= 0.25:
            out.append(f"{ad} {_tr(alan(em[ad]))} → {_tr(alan(ym[ad]))} m²")
    out += [f"{ad} kaldırıldı" for ad in em if ad not in ym]

    def pencereler(p):
        c = {}
        for x in p["pencereler"]:
            c[(x["mahal"], x["cephe"], x["olcu"])] = c.get((x["mahal"], x["cephe"], x["olcu"]), 0) + int(x.get("adet") or 1)
        return c
    pe, py = pencereler(eski), pencereler(yeni)
    for (m, c, o), n in py.items():
        if n > pe.get((m, c, o), 0):
            out.append(f"pencere eklendi: {m} {o.replace('x', '/')}")
    for (m, c, o), n in pe.items():
        if n > py.get((m, c, o), 0):
            out.append(f"pencere kaldırıldı: {m} {o.replace('x', '/')}")
    ke = {tuple(sorted(k["arasinda"])) for k in eski["kapilar"]}
    ky = {tuple(sorted(k["arasinda"])) for k in yeni["kapilar"]}
    out += [f"kapı eklendi: {' – '.join(x for x in k if x != 'dis') or 'dış'}" for k in sorted(ky - ke)]
    out += [f"kapı kaldırıldı: {' – '.join(x for x in k if x != 'dis') or 'dış'}" for k in sorted(ke - ky)]
    if (eski.get("dis_karkas") or 80) != (yeni.get("dis_karkas") or 80):
        out.append("dış duvarlar 140'lık karkas" if yeni.get("dis_karkas") == 140 else "dış duvarlar 80'lik karkas")
    if (eski.get("cati") or {}).get("tip") != (yeni.get("cati") or {}).get("tip"):
        out.append(f"çatı {(yeni.get('cati') or {}).get('tip')}")
    return out


def kayit(sonuc: dict, talep: dict, etiket: str) -> dict:
    """Test seti ve göç 007 kaydı: talep (yapısal; ad ve numara yok, özel istekler numarasız), program, basamaklar, adaylar (yol, puan,
    iç kaynak kodu, işlemler, plan), sayaçlar, süre. Kaynak kodu iç kayıttır (bayiye ve LLM'e gitmez)."""
    return {"etiket": etiket, "talep": talep, "durum": sonuc["durum"], "model": sonuc.get("model"), "program": sonuc.get("program"),
            "yol": sonuc.get("yol"), "puan": sonuc.get("puan"), "sure_ms": sonuc.get("sure_ms"), "degisen": sonuc.get("degisen") or [],
            "okunamayan": [numara.maskele(str(x)) for x in sonuc.get("okunamayan") or []],
            "cagri": sonuc["cagri"], "girdi_token": sonuc["girdi_token"], "cikti_token": sonuc["cikti_token"], "hata": sonuc.get("hata"),
            "denemeler": sonuc.get("denemeler") or [],
            "adaylar": [{k: x.get(k) for k in ("yol", "puan", "kaynak", "islemler", "kalip", "plan")} for x in sonuc.get("adaylar") or []]}
