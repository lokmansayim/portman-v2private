"""İE-14 r2 · oda programı: talepten koordinatsız program (LLM koordinat yazmaz; Lokman, 14.10.2026).

`PlanProgrami` yerleşimin girdisidir: oda sayıları, açık/ayrı mutfak, veranda isteği, çatı, hedef alan. İçinde koordinat ve ölçü yoktur;
sayı olarak yalnız bayinin söylediği değerler (m², adet) girer. Yerleşimi kod yapar: önce bankadan uyarlama (`plan_uyarlama`), uyan yoksa
deterministik çözücü (`plan_cozucu`).

Okuma sırası (K18: kural bayinin kendi sözünü okur):
1. `talepten`: çıkarımın yapısal alanları (oda programı, alan, dış ölçü, veranda, çatı) ve özel isteklerden tanınan kalıplar
   ("iki banyo", "mutfak ayrı", "kiler", "dış duvar 140") koddan okunur. Olumsuz ya da soru biçimli istek tanınmaz.
2. Tanınmayan özel istek kalırsa ve ayar açıksa `oku`: tek LLM çağrısı (`program_kaydet`; D-18, K05 istisnası). LLM yalnız şemayı doldurur;
   oda programı talepteki gibi kalır (LLM değiştiremez), çevrilemeyen istek `uygulanamayan`'a bayinin sözüyle yazılır.
3. Ayar kapalıysa ya da çağrı olmazsa tanınmayan istek "otomatik uygulayamadım" listesine gider (sessiz düşme yok, Lokman 13.10).
"""
from __future__ import annotations

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from beyin import numara
from beyin.plan_denetim import program_coz

ARAC_ADI = "program_kaydet"
ARAC_ACIKLAMA = "Tek kat çelik ev talebinin oda programını kaydet (koordinatsız). Yalnız bu araçla cevap ver."
VARSAYILAN_AYAR = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60, "max_tokens": 2000}


class OdaHedefi(BaseModel):
    islev: Literal["salon", "mutfak", "yatak_odasi", "banyo"]
    m2: float = Field(..., gt=0, le=60, description="Bayinin söylediği net alan, m²")


class VerandaIstegi(BaseModel):
    istiyor: Optional[bool] = None
    konum: Optional[Literal["on", "yan", "arka", "kose"]] = None
    ortu: Optional[Literal["cati", "pergola", "acik"]] = Field(None, description="çatı altında, pergola, açık; söylenmediyse boş")
    alan_m2: Optional[float] = Field(None, gt=0, le=60)


class PlanProgrami(BaseModel):
    """Yerleşimin girdisi. Koordinat yok."""
    yatak: int = Field(..., ge=1, le=5, description="Yatak odası sayısı ('3+1' → 3)")
    salon: int = Field(1, ge=1, le=1)
    banyo: int = Field(1, ge=1, le=2)
    mutfak: Optional[Literal["acik", "ayri"]] = Field(None, description="açık (salonla tek mahal) ya da ayrı; söylenmediyse boş")
    depo: int = Field(0, ge=0, le=1, description="kiler/depo/çamaşır odası istendiyse 1")
    alan_m2: Optional[float] = Field(None, gt=20, le=250, description="Brüt alan, m² (verandayla)")
    dis_olcu_cm: Optional[list[int]] = Field(None, description="Bayinin verdiği dış ölçü [en, boy] cm (talep şemasında en kısa, boy uzun kenar; yön belirtmez)")
    veranda: VerandaIstegi = Field(default_factory=VerandaIstegi)
    cati_tipi: Optional[Literal["besik", "kirma"]] = None
    egim_yuzde: Optional[float] = Field(None, ge=10, le=60)
    dis_karkas: Optional[Literal[80, 140]] = None
    oda_hedefleri: list[OdaHedefi] = Field(default_factory=list)
    uygulanamayan: list[str] = Field(default_factory=list, description="Bu sürümde plana çevrilemeyen istekler, bayinin sözüyle")
    varsayimlar: list[str] = Field(default_factory=list, description="Kodun yazdığı varsayımlar (ör. ölçü yuvarlama); boş bırak")


def sema() -> dict:
    return PlanProgrami.model_json_schema()


# ── koddan okuma ─────────────────────────────────────────────────────────────────────────────────────────────────────────
_OLUMSUZ = re.compile(r"(olmasın|olmasin|istemiyor|istemez|gerek yok|lazım değil|olmayacak|\bmı\b|\bmi\b|\bmu\b|\bmü\b|\?)", re.I)
_SAYI = {"bir": 1, "iki": 2, "1": 1, "2": 2}
_KALIPLAR = [
    (re.compile(r"\b(iki|2)\s*(adet\s*)?(banyo|wc|tuvalet)", re.I), lambda m, p: p.update(banyo=2), "banyo 2"),
    (re.compile(r"ebeveyn\s*banyo", re.I), lambda m, p: p.update(banyo=2), "banyo 2"),
    (re.compile(r"(ayrı|kapalı)\s+mutfak|mutfa(k|ğı)\s+(ayrı|kapalı)", re.I), lambda m, p: p.update(mutfak="ayri"), "mutfak ayrı"),
    (re.compile(r"(açık|amerikan)\s+mutfak|mutfa(k|ğı)\s+(açık|salonla)", re.I), lambda m, p: p.update(mutfak="acik"), "mutfak açık"),
    (re.compile(r"\b(kiler|depo|çamaşır\s*oda)", re.I), lambda m, p: p.update(depo=1), "depo 1"),
    # dış 140: "dış" sözü (ya da iç sözü olmadan "karkas") zorunlu; "iç duvarlar 140", "banyo duvarı 140" dış karkas değildir (inceleme C4)
    (re.compile(r"\bdış\s+(duvar\w*|karkas\w*)\D{0,12}140|140\s*('?l[ıi]k)?\s+dış\s+(duvar|karkas)|"
                r"^\s*karkas\w*\D{0,12}140", re.I),   # yalnız "karkas" cümle başında: "iç duvar karkası 140" dış değildir
     lambda m, p: p.update(dis_karkas=140), "dış 140"),
]


def _m(cm: float) -> str:
    """cm → bayinin okuyacağı metre ("7,52")."""
    return f"{cm / 100:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _talep_programi(talep: dict) -> dict:
    prog = program_coz(talep.get("oda_programi"))
    if not prog:
        raise ValueError("oda programı çözülemedi (ör. '3+1')")
    p: dict = {"yatak": prog[0], "salon": 1, "uygulanamayan": [], "varsayimlar": []}
    if prog[1] != 1:
        p["uygulanamayan"].append(f"{prog[0]}+{prog[1]} (bu sürümde tek salon)")
    if talep.get("alan_m2"):
        p["alan_m2"] = float(talep["alan_m2"])
    d = talep.get("dis_olcu") or {}
    if d.get("en_m") and d.get("boy_m"):
        # talep şemasında en kısa, boy uzun kenardır (yön değil: ön cephe bilinmez); 5 cm ızgaraya yuvarlama sessiz değil, varsayım
        # olarak yazılır (inceleme G2)
        ham = (float(d["en_m"]) * 100, float(d["boy_m"]) * 100)
        a, b = (int(round(v / 5)) * 5 for v in ham)
        p["dis_olcu_cm"] = [a, b]
        if any(abs(h - r) > 1e-6 for h, r in zip(ham, (a, b))):          # her yuvarlama yazılır (kayan nokta gürültüsü hariç)
            p["varsayimlar"].append(f"dış ölçü {_m(ham[0])} × {_m(ham[1])} m, 5 cm ızgaraya {_m(a)} × {_m(b)} m olarak alındı")
        p.setdefault("alan_m2", round(a * b / 1e4, 1))
    v = talep.get("veranda") or {}
    p["veranda"] = {k: v.get(k) for k in ("istiyor", "konum", "alan_m2") if v.get(k) is not None}
    if v.get("alan_m2") and p["veranda"].get("istiyor") is None:
        p["veranda"]["istiyor"] = True
    c = talep.get("cati") or {}
    if c.get("tip") in ("besik", "kirma"):
        p["cati_tipi"] = c["tip"]
    elif c.get("tip"):
        p["uygulanamayan"].append({"tek_egimli": "tek eğimli çatı", "teras": "teras çatı"}.get(c["tip"], str(c["tip"])) +
                                  " (bu sürümde beşik ya da kırma)")
    if c.get("egim_yuzde") and 10 <= float(c["egim_yuzde"]) <= 60:
        p["egim_yuzde"] = float(c["egim_yuzde"])
    return p


def talepten(talep: dict) -> tuple[dict, list[str]]:
    """Yapısal talep → (program sözlüğü, tanınmayan özel istekler). LLM yok. Oda programı yoksa ValueError."""
    p = _talep_programi(talep)
    kalan = []
    for istek in talep.get("ozel_istekler") or []:
        s = str(istek).strip()
        if not s:
            continue
        if _OLUMSUZ.search(s):
            kalan.append(s)
            continue
        tanindi = False
        for desen, uygula, _ in _KALIPLAR:
            m = desen.search(s)
            if m:
                uygula(m, p)
                tanindi = True
        if not tanindi:
            kalan.append(s)
    return PlanProgrami.model_validate(p).model_dump(), kalan


# ── LLM ile okuma (yalnız tanınmayan istek kaldıysa) ─────────────────────────────────────────────────────────────────────
PROMPT = """Sen PortatifEv'in tek kat çelik evleri için talep okuyan yardımcısın. Bayinin talebinden ODA PROGRAMI çıkaracaksın; plan
çizmeyeceksin, koordinat ya da ölçü yazmayacaksın. Yerleşimi kod yapar.

Kurallar:
- `yatak` ve `salon` talepteki oda programıyla aynı kalır; değiştirme.
- Yalnız bayinin açıkça söylediğini yaz: banyo sayısı (1–2), mutfak açık/ayrı, depo/kiler (0–1), verandanın yeri ve örtüsü (çatı altı,
  pergola, açık), çatı tipi (beşik/kırma), dış duvar 140'lık, bayinin söylediği oda alanları (`oda_hedefleri`, m²).
- Söylenmeyeni boş bırak; tahmin etme.
- Bu sürümde plana çevrilemeyen her isteği (çift kat, L ya da cumbalı dış hat, şömine, ikinci salon, malzeme dışı her şey) `uygulanamayan`
  listesine bayinin sözüyle yaz. Renk, malzeme, kaplama gibi istekler plan değildir: onları da `uygulanamayan`'a yazma, atla.
"""


def _metin(program: dict, kalan: list[str]) -> str:
    satir = ["## Koddan okunan program", "```json\n" + json.dumps(program, ensure_ascii=False, separators=(",", ":")) + "\n```",
             "\n## Bayinin koddan okunamayan istekleri"]
    satir += [f"- {numara.maskele(s)}" for s in kalan]
    satir.append("\nBu istekleri programa işle ve program_kaydet ile kaydet.")
    return "\n".join(satir)


def birlestir(kod_prog: dict, llm_prog: dict, kalan: list[str]) -> dict:
    """LLM'in programı koddan okunanla birleşir: yatak ve salon koddan; LLM yalnız boş alanları ve bayinin isteğine bağlı alanları doldurur."""
    p = dict(kod_prog)
    p["yatak"], p["salon"] = kod_prog["yatak"], kod_prog["salon"]
    for a in ("banyo", "depo"):
        if llm_prog.get(a) is not None and llm_prog[a] != PlanProgrami.model_fields[a].default:
            p[a] = llm_prog[a]
    for a in ("mutfak", "cati_tipi", "egim_yuzde", "dis_karkas"):
        if p.get(a) is None and llm_prog.get(a) is not None:
            p[a] = llm_prog[a]
    v = dict(p.get("veranda") or {})
    for a, deger in (llm_prog.get("veranda") or {}).items():
        if v.get(a) is None and deger is not None:
            v[a] = deger
    p["veranda"] = v
    p["oda_hedefleri"] = list(llm_prog.get("oda_hedefleri") or [])
    p["uygulanamayan"] = list(kod_prog.get("uygulanamayan") or []) + [str(s) for s in llm_prog.get("uygulanamayan") or []]
    p["varsayimlar"] = list(kod_prog.get("varsayimlar") or [])                 # yalnız kodun; LLM yazamaz
    p["dis_olcu_cm"] = kod_prog.get("dis_olcu_cm")                             # bayinin ölçüsü LLM'le değişmez
    return PlanProgrami.model_validate(p).model_dump()


def oku(talep: dict, ayar: dict | None = None, hazir: dict | None = None) -> dict:
    """Talep → program. Dönüş: {program, kaynak: kod|llm, cagri, girdi_token, cikti_token, hata, okunamayan[]}. İstisna fırlatmaz
    (oda programı yoksa durum 'hata'). `ayar['acik']` yanlışsa ya da istek kalmadıysa LLM çağrılmaz. `hazir`: manuel arka uç."""
    from beyin import llm
    s = {"program": None, "kaynak": "kod", "cagri": 0, "girdi_token": 0, "cikti_token": 0, "hata": None, "okunamayan": []}
    try:
        prog, kalan = talepten(talep)
    except (ValueError, ValidationError) as e:
        s["hata"] = str(e)[:200]
        return s
    s["program"] = prog
    a = {**VARSAYILAN_AYAR, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    if not kalan:
        return s
    if not (a.get("acik") or hazir is not None):
        s["okunamayan"] = kalan
        return s
    try:
        cevap, meta = llm.arac_cagir(PROMPT, [{"role": "user", "content": _metin(prog, kalan)}], ARAC_ADI, ARAC_ACIKLAMA, sema(),
                                     backend=a["backend"], model=a.get("model"), effort=a.get("effort"), max_tokens=int(a["max_tokens"]),
                                     hazir=hazir, timeout=int(a["timeout_s"]))
    except (llm.LLMHatasi, ValueError) as e:
        s["cagri"] = 1 if a["backend"] != "manuel" else 0                  # ücretli olabilir: temkinli sayılır
        s.update(hata=numara.maskele(str(e))[:300], okunamayan=kalan)
        return s
    s["cagri"] = 1 if a["backend"] != "manuel" else 0
    s["girdi_token"], s["cikti_token"] = meta.get("girdi_token") or 0, meta.get("cikti_token") or 0
    try:
        s["program"] = birlestir(prog, cevap, kalan)
        s["kaynak"] = "llm"
    except ValidationError as e:
        s.update(hata=f"program şeması: {str(e)[:160]}", okunamayan=kalan)
    return s


# ── son basamak: sınırlı LLM ile program yeniden önerisi (İE-14 r3, P2; koordinat yok) ─────────────────────────────────────
YENIDEN_ARAC = "program_onerisi_kaydet"
YENIDEN_ACIKLAMA = "Kodun yerleşim bulamadığı programın en az değişiklikli uygulanabilir önerisini kaydet (koordinatsız)."


class YerlesimIpucu(BaseModel):
    """Çözücü kalıbına süzgeç (koordinat değil)."""
    yatak_on: Optional[int] = Field(None, ge=0, le=2, description="Ön (gündüz) bantta kaç yatak odası")
    banyo_yeri: Optional[Literal["orta", "arka"]] = Field(None, description="banyo hol bandının ucunda mı, arka bantta mı")
    mutfak_yeri: Optional[Literal["on", "arka"]] = Field(None, description="ayrı mutfak önde mi, arkada mı")


class ProgramOnerisi(BaseModel):
    program: PlanProgrami
    ipucu: YerlesimIpucu = Field(default_factory=YerlesimIpucu)
    gerekce: str = Field("", description="Kısa; bayiye gitmez")


YENIDEN_PROMPT = """Sen PortatifEv'in tek kat çelik evleri için yerleşim danışmanısın. Kodun deterministik yerleşim çözücüsü bayinin oda programını
kurallara uyan bir plana yerleştiremedi. Sen KOORDİNAT YAZMAZSIN, plan çizmezsin: yalnız programı en az değişiklikle uygulanabilir hâle
getirirsin ve isteğe bağlı bir yerleşim ipucu verirsin; yerleşimi yine kod kurar ve denetler.

Kurallar:
- `yatak` ve `salon` değişmez (bayinin oda programı). Brüt alan istenenin ±%10'u içinde kalır.
- Değiştirebileceklerin, en azından başlayarak: ayrı mutfağı açık mutfak yapmak, depoyu kaldırmak, ikinci banyoyu kaldırmak, verandanın yerini
  ya da örtüsünü değiştirmek, alanı ±%10 içinde büyütmek.
- Her değişiklik bayiye "sığdıramadım; şu değişti" diye yazılacak: gereksiz değişiklik yapma.
- Örnekler bankadaki gerçek planların adsız özetidir; yol gösterir, kopyalanmaz.
"""


def ornek_ozetleri(n: int = 2, haric: tuple[str, ...] = ()) -> list[str]:
    """Bankadaki gerçek planların ADSIZ özeti (Lokman 14.10, 5. madde): kod, model adı, mahal adı, gerekçe yok; yalnız işlev, alan, ölçü."""
    from beyin.plan_uyarlama import kaynaklar
    from beyin.plan_denetim import denetle
    out = []
    for i, k in enumerate(kaynaklar(haric)[:n]):
        p = k["plan"]
        d = denetle(p, {})
        alan = (d.get("ozet") or {}).get("odalar_m2") or {}
        islev = {m["ad"]: m["islev"] for m in p["mahaller"]}
        say: dict[str, list[float]] = {}
        for ad, a in alan.items():
            say.setdefault(islev[ad], []).append(a)
        ver = next((m for m in p["mahaller"] if m["islev"] == "veranda"), None)
        oda = ", ".join(f"{i_.replace('_', ' ')} {' + '.join(f'{v:.1f}' for v in sorted(vs, reverse=True))} m²" for i_, vs in sorted(say.items()))
        W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
        out.append(f"Örnek {chr(65 + i)}: {sum(1 for m in p['mahaller'] if m['islev'] == 'yatak_odasi')}+1, brüt {W * H / 1e4:.0f} m², "
                   f"dış {W}×{H} cm; net odalar: {oda}; veranda: {'var (' + (ver.get('ortu') or 'cati') + ')' if ver else 'yok'}")
    return out


def _yeniden_metin(program: dict, nedenler: list[str], ornekler: list[str]) -> str:
    satir = ["## Bayinin programı (koddan)", "```json\n" + json.dumps(program, ensure_ascii=False, separators=(",", ":")) + "\n```",
             "\n## Çözücünün bulamama nedenleri"] + [f"- {numara.maskele(x)}" for x in nedenler[:8]]
    if ornekler:
        satir += ["\n## Bankadaki gerçek planlar (adsız özet)"] + [f"- {o}" for o in ornekler]
    satir.append("\nEn az değişiklikli uygulanabilir programı program_onerisi_kaydet ile kaydet.")
    return "\n".join(satir)


_VERANDA_SOZ = {"istiyor": {True: "var", False: "yok"}, "konum": {"on": "önde", "yan": "yanda", "arka": "arkada", "kose": "köşede"},
               "ortu": {"cati": "çatı altında", "pergola": "pergola", "acik": "açık"}}


def program_farki(eski: dict, yeni: dict) -> list[str]:
    """Bayiye yazılacak değişiklikler (kodun hesabı; LLM'in sözü değil). Bayinin söylediği her alan kıyaslanır; bayinin söylemediği ama LLM'in
    eklediği kısıt (dış 140, veranda) da yazılır (inceleme C3)."""
    out = []
    if (yeni.get("mutfak") or "acik") != (eski.get("mutfak") or "acik"):
        out.append("mutfak salonla birlikte (açık)" if yeni.get("mutfak") == "acik" else "mutfak ayrı")
    if int(yeni.get("banyo") or 1) != int(eski.get("banyo") or 1):
        out.append(f"banyo {eski.get('banyo') or 1} → {yeni.get('banyo') or 1}")
    if int(yeni.get("depo") or 0) != int(eski.get("depo") or 0):
        out.append("depo çıkarıldı" if not yeni.get("depo") else "depo eklendi")
    ev, yv = eski.get("veranda") or {}, yeni.get("veranda") or {}
    for a, ad in (("istiyor", "veranda"), ("konum", "veranda yeri"), ("ortu", "veranda örtüsü")):
        if ev.get(a) != yv.get(a) and (ev.get(a) is not None or yv.get(a) is not None):
            sz = _VERANDA_SOZ[a]
            out.append(f"{ad}: {sz.get(ev.get(a), 'belirtilmemiş')} → {sz.get(yv.get(a), 'belirtilmemiş')}")
    if ev.get("alan_m2") != yv.get("alan_m2") and ev.get("alan_m2"):
        out.append(f"veranda alanı {float(ev['alan_m2']):g} → " + (f"{float(yv['alan_m2']):g} m²" if yv.get("alan_m2") else "belirtilmemiş"))
    if eski.get("alan_m2") and yeni.get("alan_m2") and abs(float(eski["alan_m2"]) - float(yeni["alan_m2"])) >= 0.5:
        out.append(f"alan {float(eski['alan_m2']):g} → {float(yeni['alan_m2']):g} m²")
    if eski.get("dis_olcu_cm") and list(yeni.get("dis_olcu_cm") or []) != list(eski["dis_olcu_cm"]):
        e, y = eski["dis_olcu_cm"], yeni.get("dis_olcu_cm")
        out.append(f"dış ölçü {_m(e[0])} × {_m(e[1])} m → " + (f"{_m(y[0])} × {_m(y[1])} m" if y else "alana göre"))
    if (eski.get("dis_karkas") or 80) != (yeni.get("dis_karkas") or 80):
        out.append("dış duvarlar 140'lık" if yeni.get("dis_karkas") == 140 else "dış duvarlar 80'lik (140 uygulanmadı)")
    if eski.get("cati_tipi") and yeni.get("cati_tipi") != eski.get("cati_tipi"):
        out.append(f"çatı {eski['cati_tipi']} → {yeni.get('cati_tipi')}")
    if eski.get("egim_yuzde") and yeni.get("egim_yuzde") != eski.get("egim_yuzde"):
        out.append(f"çatı eğimi %{float(eski['egim_yuzde']):g} → " + (f"%{float(yeni['egim_yuzde']):g}" if yeni.get("egim_yuzde") else "varsayılan"))
    eh = sorted((h["islev"], float(h["m2"])) for h in eski.get("oda_hedefleri") or [])
    yh = sorted((h["islev"], float(h["m2"])) for h in yeni.get("oda_hedefleri") or [])
    if eh != yh and eh:
        out += [f"{i.replace('_', ' ')} {m:g} m² isteği alınmadı" for i, m in eh if (i, m) not in yh]
    return out


def yeniden(program: dict, nedenler: list[str], ayar: dict | None = None, hazir: dict | None = None, haric: tuple[str, ...] = ()) -> dict:
    """Son basamak (tek çağrı): program + bulamama nedenleri + adsız örnekler → öneri. Kod denetler: yatak/salon değişmez, alan ±%10.
    Dönüş: {program, ipucu, degisen[], cagri, girdi_token, cikti_token, hata, metin}. İstisna fırlatmaz."""
    from beyin import llm
    a = {**VARSAYILAN_AYAR, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    s = {"program": None, "ipucu": {}, "degisen": [], "cagri": 0, "girdi_token": 0, "cikti_token": 0, "hata": None}
    metin = _yeniden_metin(program, nedenler, ornek_ozetleri(2, haric))
    s["metin"] = metin
    try:
        cevap, meta = llm.arac_cagir(YENIDEN_PROMPT, [{"role": "user", "content": metin}], YENIDEN_ARAC, YENIDEN_ACIKLAMA,
                                     ProgramOnerisi.model_json_schema(), backend=a["backend"], model=a.get("model"), effort=a.get("effort"),
                                     max_tokens=int(a["max_tokens"]), hazir=hazir, timeout=int(a["timeout_s"]))
    except (llm.LLMHatasi, ValueError) as e:
        s["cagri"] = 1 if a["backend"] != "manuel" else 0
        s["hata"] = numara.maskele(str(e))[:300]
        return s
    s["cagri"] = 1 if a["backend"] != "manuel" else 0
    s["girdi_token"], s["cikti_token"] = meta.get("girdi_token") or 0, meta.get("cikti_token") or 0
    try:
        o = ProgramOnerisi.model_validate(cevap).model_dump()
    except ValidationError as e:
        s["hata"] = f"öneri şeması: {str(e)[:160]}"
        return s
    yeni = dict(o["program"])
    yeni["yatak"], yeni["salon"] = program["yatak"], program.get("salon", 1)       # oda programı değişmez (kod karar verir)
    if program.get("alan_m2"):
        A0 = float(program["alan_m2"])
        if not yeni.get("alan_m2") or abs(float(yeni["alan_m2"]) - A0) > 0.1 * A0:
            yeni["alan_m2"] = A0
    yeni["uygulanamayan"] = list(program.get("uygulanamayan") or [])
    yeni["varsayimlar"] = list(program.get("varsayimlar") or [])
    s["program"] = PlanProgrami.model_validate(yeni).model_dump()
    s["ipucu"] = {k: v for k, v in (o.get("ipucu") or {}).items() if v is not None}
    s["degisen"] = program_farki(program, s["program"])
    return s
