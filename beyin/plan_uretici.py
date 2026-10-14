"""İE-14 · plan üreteci: talep → (LLM) plan taslağı → (kod) denetim → geçerli Yapı Tanımı ya da "uygulayamadım".

LLM anlar, kod karar verir: LLM yalnız plan şemasını doldurur (`beyin/plan_sema.py`, araç `plan_kaydet`); geçerlilik
`beyin/plan_denetim.denetle`'nin kararıdır. İhlaller aynı konuşmada araç sonucu (is_error) olarak geri gider; en çok `en_cok_cagri`
(varsayılan 3: 1 + 2 düzeltme; D-18) çağrı. Örnek olarak bankadaki en yakın 2–3 gerçek plan (`plan_sema.tanimdan`) verilir.

Her deneme kaydedilir (taslak, ihlaller, token): geri bildirim döngüsünün kaydı ve test seti budur. `manuel` arka uç kayıtlı
cevapları sırayla oynatır (LLM çağrısı yok; `testler/plan/kayitlar/`).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from beyin import llm
from beyin.plan_denetim import ISLEV_ADI, denetle, kurallar, program_coz
from beyin.plan_sema import ARAC_ACIKLAMA, ARAC_ADI, sema, tanimdan

ROOT = Path(__file__).resolve().parent.parent
PROMPT = (Path(__file__).resolve().parent / "plan_prompt.md").read_text(encoding="utf-8")
ADAYLAR = ROOT / "beyin" / "veri" / "adaylar.json"
VARSAYILAN_AYAR = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "medium", "en_cok_cagri": 3, "timeout_s": 180,
                   "max_tokens": 8000}
VERANDA_KONUM = {"on": "ön (güney) cephede", "arka": "arka (kuzey) cephede", "yan": "yan cephede", "kose": "bir köşede"}


@lru_cache(maxsize=1)
def _banka() -> tuple[dict, ...]:
    """Bankadaki çelik adaylar, çatı varyantları ayıklanmış (aynı plan): {kod, katalog_m2, oda_programi, odalar, plan}."""
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


def yakin_ornekler(alan: float | None, n: int = 3, haric: tuple[str, ...] = ()) -> list[dict]:
    """Brüt alanı en yakın n banka planı (kör üretimde modelin kendisi `haric`)."""
    banka = [b for b in _banka() if b["kod"] not in haric and not any(b["kod"].startswith(h) for h in haric)]
    return sorted(banka, key=lambda b: (abs((b["katalog_m2"] or 0) - (alan or 0)), b["kod"]))[:n]


def hedef_alan(talep: dict) -> float | None:
    if talep.get("alan_m2"):
        return float(talep["alan_m2"])
    d = talep.get("dis_olcu") or {}
    if d.get("en_m") and d.get("boy_m"):
        return round(float(d["en_m"]) * float(d["boy_m"]), 1)
    return None


def talep_metni(talep: dict, ornekler: list[dict], kural: dict) -> str:
    """Kullanıcı mesajı: talep, kurallar (oda en küçükleri), örnek planlar."""
    alan = hedef_alan(talep)
    tol = kural["alan_tolerans"]["deger"]
    satir = ["## Talep"]
    if alan:
        satir.append(f"- Brüt alan: yaklaşık {alan:g} m² (kabul: {alan * (1 - tol):.1f}–{alan * (1 + tol):.1f} m²)")
    d = talep.get("dis_olcu") or {}
    if d.get("en_m") and d.get("boy_m"):
        satir.append(f"- Bayinin verdiği dış ölçü: {d['en_m']:g} × {d['boy_m']:g} m")
    prog = program_coz(talep.get("oda_programi"))
    if prog:
        satir.append(f"- Oda programı: {prog[0]}+{prog[1]} ({prog[0]} yatak odası, {prog[1]} salon)")
    ct = (talep.get("cati") or {}).get("tip")
    satir.append(f"- Çatı: {'kırma' if ct == 'kirma' else 'beşik' if ct == 'besik' else 'belirtilmedi (beşik ya da kırma seç)'}"
                 + (" (istenen çatı tipi bu sürümde yok; beşik ya da kırma seç)" if ct in ("tek_egimli", "teras") else ""))
    v = talep.get("veranda") or {}
    if v.get("istiyor") is True:
        satir.append(f"- Veranda: istiyor" + (f", {VERANDA_KONUM[v['konum']]}" if v.get("konum") in VERANDA_KONUM else "")
                     + (f", yaklaşık {v['alan_m2']:g} m²" if v.get("alan_m2") else ""))
    elif v.get("istiyor") is False:
        satir.append("- Veranda: istemiyor")
    for o in talep.get("ozel_istekler") or []:
        satir.append(f"- Özel istek: {o}")
    if talep.get("ozet"):
        satir.append(f"- Talebin özeti: {talep['ozet']}")
    satir.append("\n## Oda kuralları (net ölçü; kod denetler)")
    for islev, r in kural["odalar"].items():
        if r.get("en_az_m2") or r.get("dar_kenar_cm"):
            satir.append(f"- {ISLEV_ADI[islev]}: en az {r['en_az_m2']:g} m², dar kenar en az {r['dar_kenar_cm']} cm (eksenden eksene "
                         f"en az {math.ceil((r['dar_kenar_cm'] + 10.5) / 5) * 5} cm)")
    satir.append("- Pencere zorunlu: " + ", ".join(ISLEV_ADI[i] for i in kural["pencere_zorunlu"]["deger"]))
    if ornekler:
        satir.append("\n## Bankadaki en yakın gerçek planlar (örnek; plan şemasında, yaklaşık çeviri)")
        for o in ornekler:
            satir.append(f"### {o['kod']} · {o['katalog_m2']:g} m² · {o['oda_programi']}")
            satir.append("Net oda alanları: " + ", ".join(f"{k} {v:g} m²" for k, v in o["odalar"].items()))
            satir.append("```json\n" + json.dumps(o["plan"], ensure_ascii=False, separators=(",", ":")) + "\n```")
    satir.append("\nBu talebe uyan yeni bir plan taslağı çiz ve plan_kaydet ile kaydet.")
    return "\n".join(satir)


def ihlal_metni(ihlaller: list[str]) -> str:
    return ("Taslak denetimden geçmedi. İhlaller:\n" + "\n".join(f"- {i}" for i in ihlaller) +
            "\nBu ihlallerin hepsini gideren düzeltilmiş tam planı yeniden plan_kaydet ile kaydet.")


def uret(talep: dict, ayar: dict | None = None, hazir: list[dict] | None = None, haric: tuple[str, ...] = (), kod: str = "YENI",
         ornek_sayisi: int = 3) -> dict:
    """Talep → plan. Dönüş: {durum: gecerli|gecersiz|hata, plan, tanim, ozet, denemeler[], cagri, girdi_token, cikti_token, hata}.
    `hazir`: manuel arka uçta sırayla oynatılan kayıtlı cevaplar. İstisna fırlatmaz."""
    a = {**VARSAYILAN_AYAR, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    kural = kurallar()
    ornekler = yakin_ornekler(hedef_alan(talep), ornek_sayisi, haric)
    mesajlar = [{"role": "user", "content": talep_metni(talep, ornekler, kural)}]
    sonuc = {"durum": "gecersiz", "plan": None, "tanim": None, "ozet": {}, "denemeler": [], "cagri": 0, "girdi_token": 0, "cikti_token": 0,
             "hata": None, "ornekler": [o["kod"] for o in ornekler], "model": a.get("model") if a["backend"] != "manuel" else None}
    for n in range(int(a["en_cok_cagri"])):
        if a["backend"] == "manuel" and n >= len(hazir or []):
            break
        try:
            plan, meta = llm.arac_cagir(PROMPT, mesajlar, ARAC_ADI, ARAC_ACIKLAMA, sema(), backend=a["backend"], model=a.get("model"),
                                        effort=a.get("effort"), max_tokens=int(a["max_tokens"]),
                                        hazir=(hazir[n] if a["backend"] == "manuel" else None), timeout=int(a["timeout_s"]))
        except (llm.LLMHatasi, ValueError) as e:
            sonuc.update(durum="hata", hata=str(e)[:300])
            break
        sonuc["cagri"] += 1 if a["backend"] != "manuel" else 0
        sonuc["girdi_token"] += meta.get("girdi_token") or 0
        sonuc["cikti_token"] += meta.get("cikti_token") or 0
        d = denetle(plan, talep, kural, kod=kod)
        sonuc["denemeler"].append({"plan": plan, "gecerli": d["gecerli"], "ihlaller": d["ihlaller"], "ozet": d["ozet"],
                                   "girdi_token": meta.get("girdi_token"), "cikti_token": meta.get("cikti_token"), "sure_ms": meta.get("sure_ms")})
        if d["gecerli"]:
            sonuc.update(durum="gecerli", plan=plan, tanim=d["tanim"], ozet=d["ozet"])
            return sonuc
        mesajlar += [{"role": "assistant", "content": meta["icerik"]},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": meta["arac_id"], "is_error": True,
                                                   "content": ihlal_metni(d["ihlaller"])}]}]
    if sonuc["denemeler"] and sonuc["durum"] != "hata":
        sonuc["ozet"] = sonuc["denemeler"][-1]["ozet"]
    return sonuc


def kayit(sonuc: dict, talep: dict, etiket: str) -> dict:
    """Test seti kaydı (`testler/plan/kayitlar/<etiket>.json`): talep, denemelerin ham taslakları ve ihlalleri, sayaçlar. Kişi adı ve
    numara yoktur (talep alanları yapısal; özel istekler numarasız olmalı — çağıran maskeler)."""
    return {"etiket": etiket, "talep": talep, "durum": sonuc["durum"], "model": sonuc.get("model"), "ornekler": sonuc.get("ornekler"),
            "cagri": sonuc["cagri"], "girdi_token": sonuc["girdi_token"], "cikti_token": sonuc["cikti_token"], "hata": sonuc.get("hata"),
            "denemeler": [{k: v for k, v in d.items() if k in ("plan", "gecerli", "ihlaller", "girdi_token", "cikti_token", "sure_ms")}
                          for d in sonuc["denemeler"]]}
