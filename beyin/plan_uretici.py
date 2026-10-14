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
    kural = kurallar()
    ornekler = yakin_ornekler(hedef_alan(talep), ornek_sayisi, haric)
    s = _dongu([{"role": "user", "content": talep_metni(talep, ornekler, kural)}], talep, ayar, hazir, kod, kural)
    s["ornekler"] = [o["kod"] for o in ornekler]
    return s


def _dongu(mesajlar: list[dict], talep: dict, ayar: dict | None, hazir: list[dict] | None, kod: str, kural: dict | None = None) -> dict:
    """LLM çağrısı → denetim → ihlaller araç sonucu olarak geri; en çok `en_cok_cagri` çağrı. İstisna fırlatmaz."""
    a = {**VARSAYILAN_AYAR, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    kural = kural or kurallar()
    sonuc = {"durum": "gecersiz", "plan": None, "tanim": None, "ozet": {}, "denemeler": [], "cagri": 0, "girdi_token": 0, "cikti_token": 0,
             "hata": None, "model": a.get("model") if a["backend"] != "manuel" else None}
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


def duzenle_metni(plan: dict, istek: str, talep: dict, kural: dict) -> str:
    """Revizyon (LLM-önce, T3): mevcut plan + bayinin isteği; istenmeyen yer aynen kalır."""
    satir = ["## Mevcut plan (bayiye gönderildi)", "```json\n" + json.dumps(plan, ensure_ascii=False, separators=(",", ":")) + "\n```",
             "\n## Bayinin değişiklik isteği", istek.strip(),
             "\n## Yapılacak",
             "- İsteği planda uygula (oda büyüt/küçült, kapı, pencere, veranda, çatı, dış ölçü, dış duvar 140'lık: `dis_karkas`). İstenmeyen "
             "her şey olduğu gibi kalsın.",
             "- Oda büyürken komşusu küçülür ya da dış ölçü büyür; mahaller dış dikdörtgeni yine boşluksuz doldurur.",
             "- Uygulayamadığın isteği `uygulanamayan` listesine bayinin sözüyle yaz; tahminle başka bir şey değiştirme."]
    prog = program_coz(talep.get("oda_programi"))
    if prog:
        satir.append(f"- Oda programı {prog[0]}+{prog[1]} kalır (bayi açıkça değiştirmedikçe).")
    satir.append("\n## Oda kuralları (net ölçü; kod denetler)")
    for islev, r in kural["odalar"].items():
        if r.get("en_az_m2") or r.get("dar_kenar_cm"):
            satir.append(f"- {ISLEV_ADI[islev]}: en az {r['en_az_m2']:g} m², dar kenar en az {r['dar_kenar_cm']} cm")
    satir.append("\nDüzeltilmiş tam planı plan_kaydet ile kaydet.")
    return "\n".join(satir)


def duzenle(plan: dict, istek: str, talep: dict, ayar: dict | None = None, hazir: list[dict] | None = None, kod: str = "YENI") -> dict:
    """Yeni planın revizyonu: LLM mevcut planı istekle yeniden yazar, denetçi karar verir (en çok 3 çağrı). Alan ±%10 denetimi revizyonda
    yoktur (bayi alanı bilerek değiştirebilir); oda programı korunur. Dönüş `uret` ile aynı biçim; geçerliyse `uygulanamayan` ve `fark`."""
    t = {"oda_programi": talep.get("oda_programi")}
    s = _dongu([{"role": "user", "content": duzenle_metni(plan, istek, talep, kurallar())}], t, ayar, hazir, kod)
    if s["durum"] == "gecerli":
        s["uygulanamayan"] = list(s["plan"].get("uygulanamayan") or [])
        s["fark"] = plan_farki(plan, s["plan"])
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
    """Test seti kaydı (`testler/plan/kayitlar/<etiket>.json`): talep, denemelerin ham taslakları ve ihlalleri, sayaçlar. Kişi adı ve
    numara yoktur (talep alanları yapısal; özel istekler numarasız olmalı — çağıran maskeler)."""
    return {"etiket": etiket, "talep": talep, "durum": sonuc["durum"], "model": sonuc.get("model"), "ornekler": sonuc.get("ornekler"),
            "cagri": sonuc["cagri"], "girdi_token": sonuc["girdi_token"], "cikti_token": sonuc["cikti_token"], "hata": sonuc.get("hata"),
            "denemeler": [{k: v for k, v in d.items() if k in ("plan", "gecerli", "ihlaller", "girdi_token", "cikti_token", "sure_ms")}
                          for d in sonuc["denemeler"]]}
