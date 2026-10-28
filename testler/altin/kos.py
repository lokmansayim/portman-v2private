#!/usr/bin/env python3
"""İE-19 · Altın set: bayinin cümlesinden Portman'ın okuması ve kararı, sabit vakalarla (pano satırı 51; bağlı 22 ve 92).

Bir vaka, bir konuşmanın içindeki bir bayi mesajıdır ya da bir düğme. Aynı senaryonun vakaları sırayla, aynı konuşma durumuyla koşar.
Vakalar: harness'in 22 vakası (`beyin/testler/`; dokunulmaz, buradan okunur) + `testler/altin/vakalar.json` (açık) + kör dilim
(depo dışında; depoda yalnız mühür `kor_muhur.json`).

Üç ölçü:
- karar (K): beklenen okuma kural katmanına verilir (`karar_ver`; düğmeler `kanal/etkilesim.coz`, worker'daki gibi). LLM yok,
  Postgres yok, çizim yok; ücretsiz, her koşuda. Çelik revizyonlarını bugün kod okuduğu için (`celik_okuma`) onların okumasını da ölçer.
- okuma (O): kayıtlı LLM okuması beklenen okumayla alan alan kıyaslanır (kayıt oynatma ücretsiz). Harness vakalarının kaydı
  `beyin/testler/cikarim_*.json`; açık vakaların kaydı `testler/altin/kayitlar/<id>.json` (ücretli kayıtla gelir); ek kayıt
  `--kayit-dizini`yle.
- uçtan uca (U): kayıtlı okuma → karar. Senaryonun her mesajının kaydı varsa koşar.
Güvenlik sayacı: soru, yönlendirme ya da cevap beklenirken plan üretilen (İş Emri, seçenek seti ya da yeni plan) vaka sayısı.

Kör dilim (`--kor KLASÖR`): KLASÖR/vakalar.json mühürle (SHA-256, bayt) tutmazsa koşmaz; sonuç yalnız sayıdır, cümle ve beklenen
değer yazılmaz. Kör vakaya bakılarak kural ya da istem değiştirilmez.

Kullanım:
  python3 -m testler.altin.kos                                   # açık set: karar + okuma + uçtan uca, özet
  python3 -m testler.altin.kos --rapor R.md --json R.json        # vaka vaka rapor (açık set)
  python3 -m testler.altin.kos --kor <KLASÖR>                    # kör dilim: yalnız sayılar
  python3 -m testler.altin.kos --muhurle <KLASÖR> --onay "…"     # kör dilim değiştiyse (Lokman'ın kararıyla) yeniden mühür
  python3 -m testler.altin.kos --baz-yaz                         # baz çizgisini (testler/altin/baz.json) bugünkü sonuçla yazar
  python3 -m testler.altin.kos --kaydet --ucretli --tavan N --model M [--kayit-dizini D] [--ayarlar A]
                                                                 # ücretli: Lokman'ın onayı ve anahtar gerekir
Kör dilimin okuması: aynı kayıt komutu `--vakalar <KLASÖR>/vakalar.json --kayit-dizini <KLASÖR>/kayitlar` ile; kayıtlar klasörde kalır.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from beyin import harness as H, numara  # noqa: E402
from beyin.karar import PLAN_URETIMI, bayileri_yukle, karar_ver  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.celik_okuma import norm as _norm  # noqa: E402  (kural katmanının oda adı normalleştirmesi; kopya yok)
from beyin.sema import Karar, Talep  # noqa: E402

BURA = Path(__file__).resolve().parent
VAKALAR = BURA / "vakalar.json"
BAZ = BURA / "baz.json"
KAYITLAR = BURA / "kayitlar"            # açık vakaların kayıtlı LLM okumaları (<id>.json; ücretli kayıtla gelir, depoda)
MUHUR = BURA / "kor_muhur.json"
HARNESS_DIR = KOK / "beyin" / "testler"

OKUMA_ALANLARI = ("niyet", "katalog_kodu", "yapi_turu", "kat_sayisi", "oda_programi", "alan_m2", "dis_olcu", "pano", "veranda",
                  "cati", "pencereler", "varyantlar")
PLAN_EYLEMLERI = ("is_emri", "secenek")


# ── vakalar ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _harness_senaryosu(okumalar: dict) -> dict:
    """Harness'in 22 vakası tek senaryo (harness gibi: kimlik sırasıyla, gönderen başına durum). Beklenen karar mesajlar.json'dan;
    beklenen okuma vakalar.json › harness_okuma'dan (harness dosyalarına yazılmaz)."""
    mesajlar = json.loads((HARNESS_DIR / "mesajlar.json").read_text(encoding="utf-8"))
    adimlar = []
    for m in mesajlar:
        adimlar.append({"id": f"H{m['id']:02d}", "harness_id": m["id"], "gonderen": m["gonderen"], "mesaj": m["mesaj"],
                        "adim": (okumalar.get(str(m["id"])) or {}).get("adim"), "kaynak": "harness (Eylül 2026)",
                        "okuma": (okumalar.get(str(m["id"])) or {}).get("okuma"),
                        "okuma_kabul": (okumalar.get(str(m["id"])) or {}).get("okuma_kabul"),
                        "karar": {"eylem": m["beklenen"].split("|")}, "harness_kontrol": m.get("kontrol")})
    return {"id": "H", "ad": "harness'in 22 vakası", "adimlar": adimlar, "plan_uretimi": False}


def harness_kayitlari() -> dict:
    """Harness'in kayıtlı LLM okumaları (Eylül; harness'in eşlediği gibi, aynı kimlikte sonraki dosya kazanır)."""
    out = {}
    for f in sorted(HARNESS_DIR.glob("cikarim_*.json")):
        for kayit in json.loads(f.read_text(encoding="utf-8")):
            out[f"H{kayit['id']:02d}"] = kayit["talep"]
    return out


def yukle(yol: Path = VAKALAR, harness: bool = True) -> list[dict]:
    """Senaryo listesi. Vakalar dosyası: {"sema", "harness_okuma": {id: {adim, okuma}}, "senaryolar": [...]}"""
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    sen = list(d.get("senaryolar") or [])
    return ([_harness_senaryosu(d.get("harness_okuma") or {})] if harness else []) + sen


def vakalar(senaryolar: list[dict]) -> list[dict]:
    """Puanlanan adımlar. `hazirlik` adımları (vakadan önce konuşmayı kuran mesaj ya da düğme, ör. bir plan açmak) puanlanmaz,
    okuma kıyasına girmez ve her kipte beklenen okumayla koşar."""
    return [a for s in senaryolar for a in s["adimlar"] if not a.get("hazirlik")]


def kayit_dizininden(dizin: Path | None) -> dict:
    if not dizin or not Path(dizin).is_dir():
        return {}
    return {p.stem: json.loads(p.read_text(encoding="utf-8")).get("talep") for p in sorted(Path(dizin).glob("*.json"))}


# ── koşu ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _yer_tut(kimlik: str, d: dict) -> str:
    ie = d.get("son_is_emri") or {}
    rev = int(ie.get("revizyon") or 0)
    return (kimlik.replace("{set}", str((d.get("secenek_seti") or {}).get("id")))
                  .replace("{is_emri}", str(ie.get("is_emri_no"))).replace("{rev_onceki}", str(rev - 1)).replace("{rev}", str(rev)))


def gold_talep(adim: dict) -> Talep:
    o = dict(adim.get("okuma") or {})
    o.setdefault("guven", "yuksek")
    o.setdefault("ozet", (adim.get("mesaj") or "")[:80])
    return Talep.model_validate(o)


def _adim_kos(adim: dict, k: Konusma, bayi: dict | None, katalog: Katalog, talep: Talep | None) -> tuple[Karar, Talep | None]:
    """Worker'ın karar kısmı (kanal/worker.py isle): düğme → `etkilesim.coz` (geçersizse durum değişmez, eski buton cevabı);
    metin → verilen okuma (`talep`) ile `karar_ver`. LLM-önce revizyon kapalı (canlı ayar), plan üretimi senaryonun ayarıyla."""
    k.llm_yeni_plan = k.llm_degisiklik = None
    k.llm_golge = None
    if adim.get("dugme"):
        from kanal import etkilesim as ET
        etk = ET.coz({"reply_id": _yer_tut(adim["dugme"], k.d), "type": "interactive"}, k.d)
        if not etk.get("gecerli"):
            return Karar(eylem="cevapla", gerekce=f"eski buton: {etk.get('neden')}", mesaj=etk.get("mesaj") or ""), None
        t = Talep.model_validate(etk["talep"])
        return karar_ver(t, k, bayi, katalog, metin=etk["metin"]), t
    return karar_ver(talep, k, bayi, katalog, metin=adim["mesaj"]), talep           # worker ve harness gibi ham metin


def _sunulan(karar: Karar) -> list[str] | None:
    """Bayiye sunulan seçenekler: seçim düğmeleri (`s:<set>:<kod>`); düğme yoksa setin ilk üçü (setin kaydı sunulmayanları da tutar)."""
    kodlar = [b["id"].split(":", 2)[2] for b in karar.butonlar or [] if str(b.get("id") or "").startswith("s:")]
    if not kodlar:
        adaylar = sorted((karar.secenek_seti or {}).get("adaylar") or [], key=lambda a: a.get("sira") or 99)
        kodlar = [a.get("kod") for a in adaylar[:3]]
    return kodlar or None


def _ozet(karar: Karar) -> dict:
    ie = karar.is_emri or {}
    y = ie.get("yapi") or {}
    return {"eylem": karar.eylem, "gerekce": karar.gerekce, "soru_alani": karar.soru_alani,
            "secenek": _sunulan(karar),
            "plan_kodu": (y.get("kod") or (ie.get("talep") or {}).get("kaynak")) if ie else None,
            "revizyon": ie.get("revizyon") if ie else None,
            "degisiklikler": [f"{d.get('op')}:{d.get('aciklik') or d.get('kod') or ''}" for d in y.get("degisiklikler") or []] if ie else None,
            "plan_uretimi": karar.gerekce == PLAN_URETIMI}


def karar_uyumu(beklenen: dict, karar: Karar, adim: dict) -> list[str]:
    """Beklenen karardaki her alan tutmalı. Dönen liste boşsa uyumlu."""
    o = _ozet(karar)
    hata = []
    eylem = beklenen.get("eylem")
    izin = eylem if isinstance(eylem, list) else str(eylem).split("|")
    if karar.eylem not in izin:
        hata.append(f"eylem {karar.eylem} ≠ {'|'.join(izin)}")
    if "soru_alani" in beklenen:
        sa = beklenen["soru_alani"] if isinstance(beklenen["soru_alani"], list) else [beklenen["soru_alani"]]
        if o["soru_alani"] not in sa:
            hata.append(f"soru {o['soru_alani']} ≠ {'|'.join(map(str, sa))}")
    if "gerekce" in beklenen and beklenen["gerekce"] not in (karar.gerekce or ""):
        hata.append(f"gerekçe «{karar.gerekce}» içinde «{beklenen['gerekce']}» yok")
    if "plan_uretimi" in beklenen and o["plan_uretimi"] != bool(beklenen["plan_uretimi"]):
        hata.append(f"plan üretimi {o['plan_uretimi']} ≠ {beklenen['plan_uretimi']}")
    if "secenek" in beklenen and sorted(o["secenek"] or []) != sorted(beklenen["secenek"]):
        hata.append(f"seçenek {o['secenek']} ≠ {beklenen['secenek']}")
    if "secenek_icerir" in beklenen and not set(beklenen["secenek_icerir"]) <= set(o["secenek"] or []):
        hata.append(f"seçenek {o['secenek']} içinde {beklenen['secenek_icerir']} yok")
    if "plan_kodu" in beklenen and Katalog.kod_normalize(o["plan_kodu"]) != Katalog.kod_normalize(beklenen["plan_kodu"]):
        hata.append(f"plan {o['plan_kodu']} ≠ {beklenen['plan_kodu']}")
    if "revizyon" in beklenen and o["revizyon"] != beklenen["revizyon"]:
        hata.append(f"revizyon {o['revizyon']} ≠ {beklenen['revizyon']}")
    if "degisiklikler" in beklenen and sorted(o["degisiklikler"] or []) != sorted(beklenen["degisiklikler"]):
        hata.append(f"değişiklikler {o['degisiklikler']} ≠ {beklenen['degisiklikler']}")
    for s in beklenen.get("mesaj_icerir") or []:
        if s not in (karar.mesaj or ""):
            hata.append(f"mesajda «{s}» yok")
    for s in beklenen.get("mesaj_icermez") or []:
        if s in (karar.mesaj or ""):
            hata.append(f"mesajda «{s}» var")
    if adim.get("harness_kontrol"):
        hata += H._kontrol(adim["harness_kontrol"], karar.is_emri)
    return hata


def guvenlik_ihlali(beklenen: dict, karar: Karar) -> bool:
    """Soru, yönlendirme ya da cevap beklenirken plan üretildi mi (İş Emri, seçenek seti ya da yeni plan üretimi)."""
    eylem = beklenen.get("eylem")
    izin = set(eylem if isinstance(eylem, list) else str(eylem).split("|"))
    plan_bekleniyor = bool(izin & set(PLAN_EYLEMLERI)) or bool(beklenen.get("plan_uretimi"))
    plan_yapti = karar.eylem in PLAN_EYLEMLERI or karar.gerekce == PLAN_URETIMI
    return plan_yapti and not plan_bekleniyor


def kos(senaryolar: list[dict], kip: str = "K", kayitlar: dict | None = None) -> list[dict]:
    """kip K: beklenen okumayla; kip U: kayıtlı okumayla (kaydı eksik senaryo atlanır). Vaka başına sonuç satırı."""
    kayitlar = kayitlar or {}
    bayiler = bayileri_yukle()
    katalog = Katalog()
    out = []
    for s in senaryolar:
        metinli = [a for a in s["adimlar"] if not a.get("dugme") and not a.get("hazirlik")]
        if kip == "U" and not all(a["id"] in kayitlar for a in metinli):
            continue
        kok = Path(tempfile.mkdtemp(prefix="altin_"))
        konusmalar: dict[str, Konusma] = {}
        hazirlik_hatasi = None
        try:
            for a in s["adimlar"]:
                gon = a.get("gonderen") or s.get("gonderen") or "BAYI-TEST-1"
                k = konusmalar.setdefault(gon, Konusma(gon, kok))
                k.plan_uretimi = bool(s.get("plan_uretimi", True))
                satir = {"id": a["id"], "senaryo": s["id"], "adim": a.get("adim"), "dilim": s.get("dilim", "acik")}
                try:
                    talep = None
                    if not a.get("dugme"):
                        talep = gold_talep(a) if kip == "K" or a.get("hazirlik") else Talep.model_validate(kayitlar[a["id"]])
                    karar, _ = _adim_kos(a, k, bayiler.get(gon), katalog, talep)
                    k.kaydet()
                    if a.get("hazirlik"):
                        continue
                    hata = karar_uyumu(a.get("karar") or {}, karar, a) + ([hazirlik_hatasi] if hazirlik_hatasi else [])
                    satir.update(uyum=not hata, hata=hata, bugun=_ozet(karar), guvenlik=guvenlik_ihlali(a.get("karar") or {}, karar))
                except Exception as e:                       # bir vakanın hatası ötekileri durdurmaz
                    konusmalar[gon] = Konusma(gon, kok)      # worker gibi: yarım kalan adımın durumu kaydedilmez
                    if a.get("hazirlik"):
                        hazirlik_hatasi = f"hazırlık adımı {a['id']}: {type(e).__name__}: {str(e)[:120]}"
                        continue
                    satir.update(uyum=False, hata=[f"istisna: {type(e).__name__}: {str(e)[:160]}"], bugun=None, guvenlik=False)
                out.append(satir)
        finally:
            shutil.rmtree(kok, ignore_errors=True)
    return out


# ── okuma kıyası ────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _olcu(s) -> str | None:
    return re.sub(r"\s+", "", str(s)).lower().replace("*", "x") if s else None


def _alan_degeri(t: dict, alan: str):
    """Alanın kıyaslanan biçimi; boşsa None."""
    v = t.get(alan)
    if alan == "katalog_kodu":
        return Katalog.kod_normalize(v) if v else None
    if alan == "alan_m2":
        return round(float(v), 1) if v not in (None, "") else None
    if alan in ("dis_olcu", "pano"):
        if not v:
            return None
        a, b = (v.get("en_m"), v.get("boy_m")) if alan == "dis_olcu" else (v.get("nx"), v.get("ny"))
        if a is None and b is None:
            return None
        if a is None or b is None:                                   # tek değer: hangi alanda olduğu da sayılır
            return ("en" if b is None else "boy", round(float(a if b is None else b), 2))
        return tuple(sorted(round(float(x), 2) for x in (a, b)))    # iki kenarın sırası sayılmaz (kural katmanı sıralar)
    if alan == "veranda":
        if not v or v.get("istiyor") is None and not v.get("konum"):
            return None
        return (v.get("istiyor"), v.get("konum"))
    if alan == "cati":
        if not v or not any(v.get(x) for x in ("tip", "kaplama", "renk", "egim_yuzde")):
            return None
        egim = v.get("egim_yuzde")
        return (v.get("tip"), bool(v.get("kaplama")), bool(v.get("renk")),      # serbest metin alanlarında yalnız var/yok
                round(float(egim), 1) if egim not in (None, "") else None)
    if alan == "pencereler":
        # pencere değişikliği iki yoldan gelebilir (istem kural 5: varyant parametresi; şema: pencere satırı); ikisi birlikte sayılır,
        # oda ve ölçüyle (işlem türünü kural katmanı bayinin sözünden okur, B1)
        sat = {(_norm(p.get("mahal")), _olcu(p.get("olcu"))) for p in v or []}
        sat |= {(_norm((x.get("parametreler") or {}).get("mahal")), _olcu((x.get("parametreler") or {}).get("yeni") or (x.get("parametreler") or {}).get("olcu")))
                for x in t.get("varyantlar") or [] if str(x.get("tur") or "").startswith("pencere")}
        return tuple(sorted(sat, key=str)) if sat else None
    if alan == "varyantlar":
        turler = {x.get("tur") for x in v or [] if not str(x.get("tur") or "").startswith("pencere")}
        return tuple(sorted(turler)) if turler else None
    if alan == "oda_programi":
        return re.sub(r"\s+", "", str(v)).lower() if v else None
    return v if v not in ("", [], {}) else None


def okuma_kiyasi(adim: dict, llm: dict) -> dict:
    """Alan başına: {alan: (beklenen_dolu, dogru)}. Beklenen okumada olmayan alan boş kalmalı. `okuma_kabul` ({alan: [değer, …]})
    istemin iki okumaya da izin verdiği alanlarda (ör. katalog kodu + değişiklik içeren ilk mesajda yeni_talep ya da revizyon) öteki
    kabul edilen değerlerdir."""
    b = dict(adim.get("okuma") or {})
    kabul = adim.get("okuma_kabul") or {}
    out = {}
    for alan in OKUMA_ALANLARI:
        bv, lv = _alan_degeri(b, alan), _alan_degeri(llm, alan)
        dogru = bv == lv or any(_alan_degeri({**b, alan: x}, alan) == lv for x in kabul.get(alan) or [])
        out[alan] = (bv is not None, dogru)
    return out


def okuma_olcusu(vakalar_: list[dict], kayitlar: dict) -> dict:
    """{alan: {dolu: [doğru, toplam], bos: [boş kalan, toplam]}, tam: [doğru, toplam], vaka: {id: [yanlış alanlar]}}"""
    say = {a: {"dolu": [0, 0], "bos": [0, 0]} for a in OKUMA_ALANLARI}
    tam = [0, 0]
    vaka = {}
    for a in vakalar_:
        if a.get("dugme") or a["id"] not in kayitlar or a.get("okuma") is None:
            continue
        k = okuma_kiyasi(a, kayitlar[a["id"]])
        yanlis = [x for x, (_, d) in k.items() if not d]
        for x, (dolu, dogru) in k.items():
            h = say[x]["dolu" if dolu else "bos"]
            h[0] += dogru; h[1] += 1
        tam[0] += not yanlis; tam[1] += 1
        vaka[a["id"]] = yanlis
    return {"alanlar": say, "tam": tam, "vaka": vaka}


# ── özet, rapor, baz, kör ───────────────────────────────────────────────────────────────────────────────────────────────────

def ozet(sonuc: list[dict]) -> dict:
    adim = defaultdict(lambda: [0, 0])
    for s in sonuc:
        adim[s.get("adim") or "—"][0] += s["uyum"]; adim[s.get("adim") or "—"][1] += 1
    return {"uyumlu": sum(s["uyum"] for s in sonuc), "toplam": len(sonuc), "guvenlik": sum(s["guvenlik"] for s in sonuc),
            "adim": {a: v for a, v in sorted(adim.items())}}


_KISI = re.compile(r"\b(Müşteri|müşteri|Bay|Bayan)\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?")
_HITAP = re.compile(r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?\s+(Bey|Hanım|bey|hanım)\b")


def maske(metin: str) -> str:
    """Dışa aktarılan cümle (rapor, onay tablosu): numara maskeli; "Müşteri Ad Soyad" ve "Ad Bey / Hanım" kalıbındaki kişi adı da
    (AGENTS.md). Bayi ve firma adı kalıpla yakalanmaz: vakalara yazılmaz (`test_altin_set` denetler)."""
    m = _KISI.sub(lambda x: x.group(1) + " [ad]", numara.maskele(metin or ""))
    return _HITAP.sub(lambda x: "[ad] " + x.group(2), m)


def _yuzde(a: int, b: int) -> str:
    return f"{a}/{b} (%{100 * a / b:.0f})" if b else "—"


def ozet_metni(k: dict, o: dict | None, u: dict | None) -> list[str]:
    s = [f"karar (beklenen okumayla): {_yuzde(k['uyumlu'], k['toplam'])} · güvenlik sayacı {k['guvenlik']}"]
    for a, (x, y) in k["adim"].items():
        s.append(f"  {a}: {x}/{y}")
    if o and o["tam"][1]:
        s.append(f"okuma (kayıtlı LLM): tam okuma {_yuzde(*o['tam'])}")
        for a, h in o["alanlar"].items():
            if h["dolu"][1] or h["bos"][1]:
                s.append(f"  {a}: dolu {_yuzde(*h['dolu'])} · boş kalmalı {_yuzde(*h['bos'])}")
    if u and u["toplam"]:
        s.append(f"uçtan uca (kayıtlı okuma → karar): {_yuzde(u['uyumlu'], u['toplam'])} · güvenlik sayacı {u['guvenlik']}")
    return s


def rapor_md(senaryolar: list[dict], kk: list[dict], o: dict, uu: list[dict]) -> str:
    vk = {a["id"]: a for a in vakalar(senaryolar)}
    uyol = {s["id"]: s for s in uu}
    satir = ["# Altın set · açık vakalar", "", *[f"- {x}" for x in ozet_metni(ozet(kk), o, ozet(uu) if uu else None)], "",
             "| Vaka | Adım | Cümle | Beklenen | Bugün (beklenen okumayla) | Karar | Okuma | Uçtan uca |", "|---|---|---|---|---|---|---|---|"]
    for s in kk:
        a = vk[s["id"]]
        cumle = ("düğme " + a["dugme"]) if a.get("dugme") else maske(a.get("mesaj") or "")
        b = a.get("karar") or {}
        bek = "|".join(b["eylem"]) if isinstance(b.get("eylem"), list) else str(b.get("eylem"))
        bek += "".join(f" · {x}={b[x]}" for x in ("soru_alani", "secenek", "plan_kodu", "degisiklikler", "gerekce") if x in b)
        g = s.get("bugun") or {}
        bug = f"{g.get('eylem')} · {g.get('gerekce')}" + (f" · {g['soru_alani']}" if g.get("soru_alani") else "") + \
              (f" · {g['secenek']}" if g.get("secenek") else "") + (f" · {g['plan_kodu']} r{g.get('revizyon')}" if g.get("plan_kodu") else "") + \
              (f" · {g['degisiklikler']}" if g.get("degisiklikler") else "")
        ok = o["vaka"].get(s["id"])
        oku = "—" if ok is None else ("tam" if not ok else "yanlış: " + ", ".join(ok))
        un = uyol.get(s["id"])
        satir.append(f"| {s['id']} | {s.get('adim') or ''} | {cumle.replace('|', '/')[:90]} | {bek.replace('|', '/')} | {bug.replace('|', '/')[:120]} | "
                     f"{'✓' if s['uyum'] else '✗ ' + '; '.join(s['hata'])[:120].replace('|', '/')} | {oku} | {'—' if un is None else ('✓' if un['uyum'] else '✗')} |")
    return "\n".join(satir) + "\n"


def baz_kaydi(kk: list[dict], o: dict) -> dict:
    return {"aciklama": "Açık vakaların bugünkü sonucu (gerileme kapısı): uyumlu vakalar uyumlu kalmalı; uyumsuz vakalar 'rehberde var, "
                        "bugün çalışmıyor' listesidir. Değişirse gerekçesiyle `--baz-yaz`.",
            "karar": {s["id"]: s["uyum"] for s in kk},
            "guvenlik": sorted(s["id"] for s in kk if s["guvenlik"]),
            "okuma": {"tam": o["tam"], "alanlar": o["alanlar"]}}


def dosya_ozeti(yol: Path) -> dict:
    b = Path(yol).read_bytes()
    return {"sha256": hashlib.sha256(b).hexdigest(), "bayt": len(b)}


def muhurle(klasor: Path, muhur_yolu: Path = MUHUR, onay: str = "") -> dict:
    """Kör dilimin mührü: SHA-256, bayt, vaka sayısı ve adım dağılımı (cümle ve beklenen değer yazılmaz). Kör dilim değişirse
    (Lokman'ın kararıyla bir vaka açığa alınır, yerine yenisi konur) yeniden mühürlenir."""
    yol = Path(klasor) / "vakalar.json"
    v = vakalar(yukle(yol, harness=False))
    m = {"aciklama": "İE-19 kör dilimin mührü. Dilim depo dışında (proje klasörü Altin_Set/kor/vakalar.json); araç mühür tutmazsa koşmaz.",
         **dosya_ozeti(yol), "vaka_sayisi": len(v), "adim": dict(sorted(Counter(a.get("adim") for a in v).items())),
         "tarih": time.strftime("%Y-%m-%d"), "onay": onay}
    Path(muhur_yolu).write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return m


def kor_kos(klasor: Path, muhur_yolu: Path = MUHUR) -> tuple[bool, list[str]]:
    """Kör dilim: mühür tutmazsa koşmaz. Sonuç yalnız sayılar; vaka içeriği yazılmaz."""
    yol = Path(klasor) / "vakalar.json"
    muhur = json.loads(Path(muhur_yolu).read_text(encoding="utf-8"))
    if not yol.is_file():
        return False, [f"kör dilim dosyası yok: {yol.name}"]
    oz = dosya_ozeti(yol)
    if oz != {"sha256": muhur["sha256"], "bayt": muhur["bayt"]}:
        return False, ["mühür tutmadı: kör dilim değişmiş ya da başka bir dosya; koşulmadı"]
    sen = yukle(yol, harness=False)
    if len(vakalar(sen)) != muhur["vaka_sayisi"]:
        return False, ["mühürdeki vaka sayısı tutmadı; koşulmadı"]
    kk = kos(sen, "K")
    kay = kayit_dizininden(Path(klasor) / "kayitlar")
    o = okuma_olcusu(vakalar(sen), kay)
    uu = kos(sen, "U", kay) if kay else []
    return True, ["kör dilim (mühür tuttu)", *ozet_metni(ozet(kk), o, ozet(uu) if uu else None)]


# ── ücretli kayıt ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def kaydet(senaryolar: list[dict], dizin: Path, backend: str, model: str | None, tavan: int, ucretli: bool,
           hazir: dict | None = None, ayarlar_json: str | None = None) -> dict:
    """Senaryoları LLM okumasıyla oynatır ve her mesajın okumasını `dizin/<id>.json`'a yazar (canlıdaki bağlamla: bayinin hitabı ve
    konuşma özeti, `kanal/worker.cikar` gibi). Ücretli: `ucretli` ve Lokman'ın onayı olmadan gerçek arka uç çağrılmaz. `manuel`
    arka uç (yalnız test) `hazir`'daki okumayı yazar. Var olan kayıt yeniden çağrılmaz."""
    from beyin import llm
    from kanal.worker import baglam_ozeti, bayi_tanimi
    if backend != "manuel" and not ucretli:
        raise SystemExit("ücretli kayıt için --ucretli gerekir (Lokman'ın onayı)")
    dizin = Path(dizin); dizin.mkdir(parents=True, exist_ok=True)
    bayiler, katalog = bayileri_yukle(), Katalog()
    cagri, yazilan, atlanan = 0, 0, 0
    for s in senaryolar:
        kok = Path(tempfile.mkdtemp(prefix="altin_kayit_"))
        konusmalar: dict[str, Konusma] = {}
        try:
            for a in s["adimlar"]:
                gon = a.get("gonderen") or s.get("gonderen") or "BAYI-TEST-1"
                k = konusmalar.setdefault(gon, Konusma(gon, kok))
                k.plan_uretimi = bool(s.get("plan_uretimi", True))
                talep = None
                if a.get("hazirlik") and not a.get("dugme"):
                    talep = gold_talep(a)
                elif not a.get("dugme"):
                    hedef = dizin / f"{a['id']}.json"
                    if hedef.exists():
                        talep = Talep.model_validate(json.loads(hedef.read_text(encoding="utf-8"))["talep"]); atlanan += 1
                    else:
                        # bir mesaj en çok iki çağrıdır (şema hatasında tek tekrar, `llm.cikar_guvenli`): tavan en kötü duruma göre
                        if backend != "manuel" and cagri + 2 > tavan:
                            return {"cagri": cagri, "yazilan": yazilan, "atlanan": atlanan, "durdu": "tavan"}
                        baglam = "; ".join(x for x in (bayi_tanimi(bayiler.get(gon)), baglam_ozeti(k)) if x)
                        metin = numara.maskele(a["mesaj"])
                        try:
                            talep, meta = llm.cikar_guvenli(metin, baglam, backend=backend, model=model,
                                                            hazir=(hazir or {}).get(a["id"]) if backend == "manuel" else None,
                                                            **({"ayarlar_json": ayarlar_json} if ayarlar_json else {}))
                        except Exception as e:               # ücretli koşu hatada durur (aynı hata yeniden ücret doğurmasın), sayım yazılır
                            cagri += 2 if backend != "manuel" else 0     # kaç çağrı yapıldığı bilinmez: üst sınır
                            return {"cagri": cagri, "yazilan": yazilan, "atlanan": atlanan, "durdu": f"hata {a['id']}: {type(e).__name__}"}
                        cagri += (1 + int(meta.get("tekrar") or 0)) if backend != "manuel" else 0
                        hedef.write_text(json.dumps({"id": a["id"], "talep": talep.model_dump(mode="json"),
                                                     "meta": {x: meta.get(x) for x in ("backend", "model", "girdi_token", "cikti_token", "sure_ms")}},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
                        yazilan += 1
                _adim_kos(a, k, bayiler.get(gon), katalog, talep)
                k.kaydet()
        finally:
            shutil.rmtree(kok, ignore_errors=True)
    return {"cagri": cagri, "yazilan": yazilan, "atlanan": atlanan, "durdu": None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vakalar", type=Path, default=VAKALAR)
    ap.add_argument("--kayit-dizini", type=Path, help="kayıtlı LLM okumaları (<id>.json); harness kayıtları her zaman okunur")
    ap.add_argument("--rapor", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--kor", type=Path, help="kör dilim klasörü (vakalar.json, kayitlar/); yalnız sayılar")
    ap.add_argument("--muhurle", type=Path, help="kör dilim klasörünü mühürler (kor_muhur.json); yalnız dilim değiştiğinde")
    ap.add_argument("--onay", default="", help="--muhurle ile: onay notu (ör. 'Lokman, 28.10.2026')")
    ap.add_argument("--baz-yaz", action="store_true")
    ap.add_argument("--kaydet", action="store_true")
    ap.add_argument("--ucretli", action="store_true")
    ap.add_argument("--tavan", type=int, default=0)
    ap.add_argument("--backend", default="anthropic")
    ap.add_argument("--model")
    ap.add_argument("--ayarlar", help="--kaydet ile: LLM ayar dosyasının yolu (worker'daki ayarlar_json; anahtar dosyada kalır)")
    x = ap.parse_args(argv)
    if x.muhurle:
        m = muhurle(x.muhurle, onay=x.onay)
        print(f"mühür yazıldı: {m['vaka_sayisi']} vaka, {m['bayt']} bayt")
        return 0
    if x.kor:
        ok, satirlar = kor_kos(x.kor)
        print("\n".join(satirlar))
        return 0 if ok else 2
    sen = yukle(x.vakalar)
    if x.kaydet:
        print(json.dumps(kaydet([s for s in sen if s["id"] != "H"], x.kayit_dizini or KAYITLAR, x.backend, x.model, x.tavan, x.ucretli,
                                ayarlar_json=x.ayarlar), ensure_ascii=False))
        return 0
    if x.baz_yaz and (x.vakalar != VAKALAR or x.kayit_dizini):
        ap.error("--baz-yaz yalnız depodaki vakalar ve kayıtlarla (pytest'in kıyasladığı set); --vakalar ve --kayit-dizini verilmez")
    kay = {**harness_kayitlari(), **kayit_dizininden(KAYITLAR), **kayit_dizininden(x.kayit_dizini)}
    kk = kos(sen, "K")
    o = okuma_olcusu(vakalar(sen), kay)
    uu = kos(sen, "U", kay)
    print("\n".join(ozet_metni(ozet(kk), o, ozet(uu))))
    if x.rapor:
        x.rapor.write_text(rapor_md(sen, kk, o, uu), encoding="utf-8")
    if x.json:
        x.json.write_text(json.dumps({"karar": kk, "okuma": o, "uctan_uca": uu}, ensure_ascii=False, indent=1), encoding="utf-8")
    if x.baz_yaz:
        BAZ.write_text(json.dumps(baz_kaydi(kk, o), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"baz çizgisi yazıldı: {BAZ.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
