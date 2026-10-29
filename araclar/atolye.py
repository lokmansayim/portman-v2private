"""İE-09 · Model atölyesi (D-20; Görev 6e): kontrollü model üretimi ve banka hattı. Tarif `.claude/skills/atolye/SKILL.md`, iş emri
`docs/is_emirleri/IE-09.md`. Araç canlı yola girmez, genel motoru yalnız çağırır; LLM yok.

    python3 araclar/atolye.py ac <KOD> --ad "…" [--aile "tek kat çelik"] [--kat 1] [--kaynak-metni "…"] [--proje AP-NN|ÇP-NN]
                              [--kaynak-dosya <yol>[=etiket] …] [--musteri-projesi] [--tanim <Yapı Tanımı>]
    python3 araclar/atolye.py varyant <KOD> --taban Ç8801 --cati <çatı.json> --ad "…" [--kaynak-metni "…"]
    python3 araclar/atolye.py kaynak <KOD> --kaynagi "…" [--oda "AD=m²" …] [--brut-m2 N] [--oda-programi 2+1] [--pencere N] [--kapi N]
                              [--cati-tipi T] [--proje AP-NN|ÇP-NN]
    python3 araclar/atolye.py ciz <KOD> [--cikti <klasör>]
    python3 araclar/atolye.py duzelt <KOD> --tur okuma|tercih|kural|motor --metin "…"
    python3 araclar/atolye.py metraj <KOD> --celik ÇP-NN
    python3 araclar/atolye.py kabul <KOD> [--kim Lokman] [--tarih YYYY-AA-GG] [--not "…"]
    python3 araclar/atolye.py ret <KOD> --neden "…"
    python3 araclar/atolye.py gunluk [--tarih YYYY-AA-GG]
    python3 araclar/atolye.py kontrol [--tam] [<KOD> …]
    python3 araclar/atolye.py dondur <KOD> --gerekce "…" --karar D-NN     # yalnız ayrı, Patron onaylı PR'da (D-02, D-20)

Durum: `taslak` → (`ciz`) `kontrolde` → `kabul` ya da `ret`. Metraj kabul testi geçmezse `beklemede`: kabul edilemez. Düzeltme kartı
`taslak`'a döndürür; tanım değişince yeniden çizilir (Lokman'ın gördüğü çizim kabul edilen çizimdir: kabulde tanımın özeti son çizimle aynı
olmalı). Kabul edilen tanım donar (D-07): değişirse `kontrol` düşer, yeni kod ya da sürüm gerekir.

Kurallar (İE-09; CIO kıyası 16.10, Patron onaylı):
- **Metraj kabul testi:** gerçek yükleme listesi olan modelde çelik kg farkı ±%3'ü aşarsa model `beklemede`. Listesi olmayan
  modelin kartında "metraj testi yok" yazar. İE-09 PR-1'den (29 Ekim 2026) beri kapı tek koddan (D-28 madde 1, Z-03): atölye listeyi
  kendisi okumaz, çelik hakeminin (İE-16, `testler/celik/`) o projede yazdığı sonucu okur (`metraj --celik`). Bankadaki tanım hakemin
  ölçtüğü tanımla (kod ve ad dışında), kural seti ve karkas kuralı ölçümdekiyle aynı olmalı; açık projede kapı hakemin kendi
  işlevleriyle yeniden hesaplanır ve tür tür tablo kontrol sayfasına girer. Model o ölçümdeki kural setiyle çizilir ve pimlenir.
- **Kör test seti açılmaz:** AIPrefabrik'te yükleme listesi hiç açılmamış 20 proje (Mimari Rapor › 1.4) kaynak ya da kıyas olarak alınmaz.
  Açılmış listeler `KOR_TEST_ACIK`; AIPrefabrik'in bunun dışındaki her liste dosyası reddedilir (proje kodu okunamazsa da).
- **Kaynak dosyalar depoya girmez:** karta yalnız etiket (sizin yazdığınız, kişi adı taşımayan), uzantı, boyut ve SHA-256 yazılır.
- **Hakem değişmez:** `dondur` yalnız ayrı PR'da, gerekçe ve `KARARLAR/` altındaki bir kararla; model PR'ında koşulmaz.
- **Kabul kapısı:** kabulde harness 22/22 ve `pytest testler` yeniden koşar (`--kapisiz` yalnız bu aracın kendi testinde); model bir
  sonucu değiştiriyorsa kabul durur ve kart `kontrolde` kalır.

Çıktı: `ciz` çizim setini ve kontrol sayfasını (`<DOSYA>_kontrol_cNN.pdf`) `--cikti` altına yazar (varsayılan `cikti/atolye/`, git dışı).
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from beyin import banka as B  # noqa: E402

DURUMLAR = ("taslak", "kontrolde", "beklemede", "kabul", "ret")
DUZELTME_TURLERI = {"okuma": "kaynağı yanlış ya da eksik okudum", "tercih": "Lokman'ın kararı (çatı, ölçü, açıklık)",
                    "kural": "kural kitabında eksik ya da yanlış", "motor": "çizim ya da hesap kusuru (kusur defterine de)"}
METRAJ_YOK = "referans yok: modelin çelik hakemi ölçümü yok; metraj kapısı koşulmadı (kabul metraj doğrulaması sayılmaz)"
METRAJ_ESIGI_YUZDE = 3.0            # Patron onaylı (Portman_Arastirma_Yol_Haritasi_2026-10-16.md › 3; CIO kıyası 16.10); hakemde KG_PAYI
CELIK_PROJELER = KOK / "testler" / "celik" / "projeler"             # çelik hakeminin projeleri (İE-16; yalnız okunur)
CELIK_CEVAPLAR = KOK / "testler" / "celik" / "veri"                 # açık projelerin hakem cevapları (İE-16 PR-1; yalnız okunur)
CELIK_GRUBU = "Çelik panel"                                          # motorun yükleme listesindeki çelik grubu (motor/genel/yukleme.py)
TOPLAM_SATIRI = "Toplam (adedi ve kg'ı bilinenler)"                  # motorun çelik grubundaki sağlama satırı (motor/genel/yukleme.py)
TANIM_ESLIK_DISI = ("kod", "ad")                                     # bankadaki tanım hakemin ölçtüğü tanımdan yalnız bunlarda ayrılır
# Mimari Rapor › 1.4 (14 Ekim): 28 AIPrefabrik projesinden yükleme listesi açılmış olanlar (AP-19 = PK-01, AP-08 = PK-07, AP-07 = TS-01,
# AP-01…05 = E1–E5). Geri kalan 20'si kör test setidir: açılmaz.
KOR_TEST_ACIK = frozenset({"AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-07", "AP-08", "AP-19"})
LISTE_UZANTILARI = (".xlsx", ".xlsm", ".xls", ".ods", ".csv")
LISTE_SOZCUKLERI = ("liste", "yukleme", "yükleme", "metraj", "bom")
KUSUR_DEFTERI = KOK / "docs" / "notlar" / "IE-09_motor_kusurlari.md"
CIKTI_VARSAYILAN = KOK / "cikti" / "atolye"
PLAN_ANAHTARLARI = ("duvarlar", "mahaller", "acikliklar")             # "aynı plan" denetimi bunlardan
SABIT_ZAMAN = "1760000000"                                           # tam izlerde üretim tarihi sabit (testler/referans/sabit_zaman)
TR = timezone(timedelta(hours=3))                                     # Türkiye saati (UTC+3, yaz saati yok)


# ── yardımcılar ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def simdi() -> str:
    return datetime.now(TR).strftime("%Y-%m-%dT%H:%M%z")


def bugun() -> str:
    return datetime.now(TR).strftime("%Y-%m-%d")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def kanonik_sha(veri) -> str:
    return hashlib.sha256(json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def kod_normalize(s: str) -> str:
    from beyin.katalog import Katalog
    return Katalog.kod_normalize(s) or s.strip().upper()


def gosterim(kod: str) -> str:
    """Ç8801D → Ç8801-D, KT04 → KT-04 (adaylar.json'daki gösterim gibi); başka kod olduğu gibi."""
    m = re.fullmatch(r"(Ç\d{4})([A-Z])", kod) or re.fullmatch(r"(KT)(\d{2})", kod)
    return f"{m.group(1)}-{m.group(2)}" if m else kod


def dur(*metin) -> int:
    print("DUR:", *metin)
    return 2


def cekirdek_adaylar() -> list[dict]:
    return json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8"))


def kok_dizin(banka_kok: Path) -> Path:
    return banka_kok.parent.parent                                        # modeller/banka → depo kökü


def klasor(kod: str, banka_kok: Path) -> Path:
    return banka_kok / B.dosya_adi(kod)


def kart_oku(kod: str, banka_kok: Path) -> dict | None:
    p = klasor(kod, banka_kok) / "kart.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def kart_yaz(kart: dict, banka_kok: Path) -> None:
    k = klasor(kart["kod"], banka_kok); k.mkdir(parents=True, exist_ok=True)
    (k / "kart.json").write_text(json.dumps({x: v for x, v in kart.items() if not x.startswith("_")}, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")


def olay(kart: dict, ad: str, **ayrinti) -> None:
    kart.setdefault("gecmis", []).append({"zaman": simdi(), "olay": ad, **{k: v for k, v in ayrinti.items() if v not in (None, "", [])}})


def proje_kodu(metin: str | None) -> str | None:
    m = re.search(r"\bAP[\s_-]?(\d{1,2})\b", str(metin or ""), re.IGNORECASE)
    return f"AP-{int(m.group(1)):02d}" if m else None


def kaynak_proje_kodu(metin: str | None) -> str | None:
    """Kartın kaynak projesi: AIPrefabrik (AP-NN) ya da çelik hattı (ÇP-NN, İE-16). Kör test engeli yalnız AP'ye bakar (`proje_kodu`)."""
    m = re.search(r"(?<![a-zç])[ÇC]P[\s_-]?(\d{1,2})\b", str(metin or ""), re.IGNORECASE)
    return proje_kodu(metin) or (f"ÇP-{int(m.group(1)):02d}" if m else None)


def kor_test_engeli(yol: Path, proje: str | None = None) -> str | None:
    """Kör test setindeki bir yükleme listesi mi? (dosya okunmadan, adından ve yolundan). Engel nedeni ya da None."""
    ad = yol.name.casefold()
    liste_mi = yol.suffix.lower() in LISTE_UZANTILARI or any(s in ad for s in LISTE_SOZCUKLERI)
    if not liste_mi:
        return None
    ap = proje_kodu(proje) or proje_kodu(str(yol))
    aiprefabrik = "aiprefabrik" in str(yol).casefold() or ap is not None
    if not aiprefabrik:
        return None
    if ap is None:
        return "AIPrefabrik'teki bir liste dosyası, proje kodu okunamadı: kör test setinden olabilir (açılmaz)"
    if ap not in KOR_TEST_ACIK:
        return f"{ap} yükleme listesi kör test setinde (Mimari Rapor › 1.4): açılmaz, kaynak ya da kıyas olarak alınmaz"
    return None


def tanim_yolu(kod: str, banka_kok: Path) -> Path:
    return klasor(kod, banka_kok) / "tanim.json"


def taban_kaydi(kod: str, banka_kok: Path) -> dict | None:
    """Çekirdek bankada ya da atölye bankasında (kabul) bir model kaydı; `tanim` depo köküne göre."""
    k = kod_normalize(kod)
    for a in cekirdek_adaylar() + B.kayitlar(banka_kok):
        if str(a.get("kod")).upper() == k and a.get("motor") == "genel":
            return a
    return None


def tum_tanimlar(banka_kok: Path, haric: str | None = None) -> dict[str, dict]:
    """Bankadaki bütün çelik tanımlar (çekirdek + atölye kartları, her durumda; ret hariç): {kod: tanım}."""
    out = {}
    for a in cekirdek_adaylar():
        if a.get("motor") == "genel" and a.get("tanim"):
            out[str(a["kod"])] = json.loads((KOK / a["tanim"]).read_text(encoding="utf-8"))
    for kart in B.kartlar(banka_kok):
        if kart.get("_hata") or kart.get("durum") == "ret" or str(kart.get("kod")) == haric:
            continue
        p = kart["_klasor"] / "tanim.json"
        if p.is_file():
            out[str(kart["kod"])] = json.loads(p.read_text(encoding="utf-8"))
    return out


def plan_izi(t: dict) -> str:
    return kanonik_sha({k: t.get(k) for k in PLAN_ANAHTARLARI})


# ── ölçüm (hızlı yol: yapı, çatı, metraj, liste; çizim yok) ──────────────────────────────────────────────────────────────
def liste_ozeti(liste: dict) -> dict:
    """Grup grup satır ve kg; çelik kg yalnız "Çelik panel" grubunun malzeme satırları. Motorun grup sağlaması (`TOPLAM_SATIRI`) malzeme
    değildir, sayılmaz (İE-09 PR-1: 17 Ekim'deki özet onu da topluyordu, Ç8801-D'nin "4990,5 kg"ı 2 × 2495,25'ti)."""
    gruplar: dict[str, dict] = {}
    for s in liste.get("satirlar") or []:
        g = gruplar.setdefault(s.get("grup") or "?", {"satir": 0, "kg": 0.0})
        g["satir"] += 1
        if s.get("kalem") != TOPLAM_SATIRI:
            g["kg"] += float(s.get("kg") or 0)
    celik = round((gruplar.get(CELIK_GRUBU) or {}).get("kg", 0.0), 2)
    return {"satir": len(liste.get("satirlar") or []), "celik_kg": celik, "iz": kanonik_sha(liste),
            "gruplar": {k: {"satir": v["satir"], "kg": round(v["kg"], 2)} for k, v in gruplar.items()}}


def olc(t: dict, set_yolu: Path | None = None, liste: dict | None = None, karkas_yolu: Path | None = None) -> dict:
    """Tanımın ölçümü: dış ölçü, brüt oturum, odalar, açıklıklar, çatı; liste verilmezse yalnız-liste koşusuyla (≈ 1 sn). `karkas_yolu`
    karkas kuralının dosyası (yalnız tanım `karkas: kural` isterse okunur; verilmezse güncel kural)."""
    from motor.genel import yapi, cati_genel, kural, girdi_genel
    from motor.genel import uret as U
    from motor.genel.bayi_gorseli import oda_programi
    with kural.secili(set_yolu), U.karkas_kurali(karkas_yolu):
        kur = kural.oku()
        y = yapi.kur(t)
        c = cati_genel.cati_kur(t["cati"], kur)
        m = girdi_genel.metraj(y, c, kur)
        set_adi = str(kural.yol())
    if liste is None:
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp) / "tanim.json"
            tp.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
            with contextlib.redirect_stdout(sys.stderr):
                U.uret(tp, Path(tmp) / "c", set_yolu=set_yolu, yontem="panel", perspektif=False, bayi=False, yalniz_liste=True,
                       kaynak=f"Yapı Tanımı 0.5 ({t['kod']})", karkas_yolu=karkas_yolu)
            lp = Path(tmp) / "c" / f"{U.kod_govde(t)}_yukleme.json"
            liste = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {"satirlar": []}
    acl = y["acikliklar"]
    vm = m.get("veranda_m2") or 0
    return {"dis_olcu_cm": [round(x, 1) for x in m["dis_olcu_cm"]], "oturum_m2": round(float(m["oturum_m2"]), 2),
            "veranda_m2": round(float(vm), 2),
            "odalar": {ad: round(b["alan_m2"], 2) for ad, b in y["bolgeler"].items() if b.get("sinif") != "dis"},
            "oda_programi": oda_programi(t),
            "pencere": sum(1 for x in acl if x["tur"] == "pencere"), "kapi": sum(1 for x in acl if x["tur"] in ("dis_kapi", "ic_kapi")),
            "acikliklar": sorted(f"{x['tur']} {x.get('mahal') or ''} {x.get('etiket') or ''}".strip() for x in acl),
            "cati": {"tip": t["cati"].get("tip"), "duzlem": len(c["duzlemler"]), "yuzey_m2": round(float(c["yuzey_m2"]), 2),
                     "kenar_cm": {k: round(float(v), 1) for k, v in sorted((c.get("kenar_toplam_cm") or {}).items())}},
            "liste": liste_ozeti(liste), "kural_seti": Path(set_adi).name}


# ── ac / varyant / kaynak ────────────────────────────────────────────────────────────────────────────────────────────────
def _yeni_kart(kod: str, ad: str, aile: str, kat: int, kaynak: dict, musteri: bool, taban: str | None = None) -> dict:
    return {"sema": B.KART_SEMASI, "kod": kod, "gosterim": gosterim(kod), "ad": ad, "aile": aile, "yapi_turu": "celik", "kat": kat,
            "musteri_projesi": musteri, "taban_model": taban, "varyant_turu": "cati" if taban else None, "varyantlar": [],
            "kaynak": kaynak, "kaynak_degerleri": {}, "durum": "taslak",
            "metraj_testi": {"durum": "yok", "not": METRAJ_YOK}, "pim": None, "olcum": None, "son_cizim": None,
            "duzeltmeler": [], "gecmis": [], "kabul": None, "aday": None}


def pim_yollari(kart: dict) -> tuple[Path | None, Path | None]:
    """Kartın kural seti ve karkas kuralı pimi (metraj kapısının ölçüldüğü kopyalar; `metraj --celik` yazar): (set, karkas); pimsiz
    kartta (None, None): çizim güncel kuralla, kontrol dosyası dondurulmuş setlerin en yenisiyle (`pim_seti`)."""
    p = kart.get("pim") or {}
    yol = lambda x: KOK / x["yol"] if x else None                        # noqa: E731
    return yol(p.get("kural_seti")), yol(p.get("karkas"))


def _kod_serbest(kod: str, banka_kok: Path) -> str | None:
    if any(str(a.get("kod")).upper() == kod for a in cekirdek_adaylar()):
        return f"{kod} çekirdek bankada var (beyin/veri/adaylar.json)"
    if klasor(kod, banka_kok).exists():
        return f"{kod} atölye bankasında var ({klasor(kod, banka_kok).relative_to(kok_dizin(banka_kok))})"
    return None


def ac(a) -> int:
    kod = kod_normalize(a.kod)
    if not re.fullmatch(r"[A-ZÇ0-9-]{3,12}", kod):
        return dur(f"kod biçimi: {kod!r} (harf, rakam, tire; 3–12)")
    if (e := _kod_serbest(kod, a.banka)):
        return dur(e)
    dosyalar = []
    for i, s in enumerate(a.kaynak_dosya or [], 1):
        yol_s, _, etiket = s.partition("=")
        yol = Path(yol_s).expanduser()
        if (e := kor_test_engeli(yol, a.proje)):
            return dur(e)
        if not yol.is_file():
            return dur(f"kaynak dosya yok: {yol.name}")
        dosyalar.append({"etiket": etiket.strip() or f"kaynak {i}", "uzanti": yol.suffix.lower(), "boyut": yol.stat().st_size, "sha256": sha256(yol)})
    t = None
    if a.tanim:
        t = json.loads(Path(a.tanim).read_text(encoding="utf-8"))
        if kod_normalize(str(t.get("kod"))) != kod:
            return dur(f"tanımın kodu {t.get('kod')!r}, kart {kod}")
    kart = _yeni_kart(kod, a.ad, a.aile, a.kat, {"tur": "proje" if a.proje or dosyalar else "istek", "metin": a.kaynak_metni,
                                                 "proje": kaynak_proje_kodu(a.proje), "dosyalar": dosyalar}, bool(a.musteri_projesi))
    olay(kart, "ac", kaynak=a.kaynak_metni)
    kart_yaz(kart, a.banka)
    if t is not None:
        tanim_yolu(kod, a.banka).write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{gosterim(kod)}: kart açıldı (taslak) → {klasor(kod, a.banka).relative_to(kok_dizin(a.banka))}"
          + ("" if t is not None else " · tanım henüz yok: tanim.json yazılınca `ciz`"))
    return 0


def varyant(a) -> int:
    kod = kod_normalize(a.kod)
    if (e := _kod_serbest(kod, a.banka)):
        return dur(e)
    taban = taban_kaydi(a.taban, a.banka)
    if taban is None:
        return dur(f"taban model bankada yok: {a.taban}")
    if taban.get("referans_model") and kod_normalize(taban["referans_model"]) != taban["kod"]:
        return dur(f"{taban['kod']} kendisi bir varyant; taban olarak {taban['referans_model']} verin")
    taban_yolu = kok_dizin(a.banka) / taban["tanim"] if taban.get("banka") else KOK / taban["tanim"]
    t = json.loads(taban_yolu.read_text(encoding="utf-8"))
    cati = json.loads(Path(a.cati).read_text(encoding="utf-8"))
    for k, v in tum_tanimlar(a.banka).items():
        if plan_izi(v) == plan_izi(t) and kanonik_sha(v.get("cati")) == kanonik_sha(cati):
            return dur(f"bu çatı bankada zaten var: {k}")
    t = copy.deepcopy(t)
    t["kod"], t["ad"], t["cati"] = kod, a.ad, cati
    kaynak = dict(t.get("kaynak") or {})
    kaynak["cati"] = f"Çatı varyantı (İE-09 atölyesi, {bugun()}): {a.kaynak_metni}".rstrip(": ")
    t["kaynak"] = kaynak
    ozet = taban.get("ozet") or {}
    etiket = f"bankada {taban['kod']} kaydı (koddan; adaylar.json)" if not taban.get("banka") else f"bankada {taban['kod']} kartı (koddan)"
    kart = _yeni_kart(kod, a.ad, a.aile or "tek kat çelik", int(taban.get("kat") or 1),
                      {"tur": "varyant", "metin": a.kaynak_metni, "taban": taban["kod"], "taban_tanim": taban["tanim"],
                       "taban_sha256": sha256(taban_yolu), "dosyalar": []}, bool(taban.get("musteri_projesi")), taban=taban["kod"])
    kart["kaynak_degerleri"] = {"odalar": {ad: {"deger": m2, "kaynak": etiket} for ad, m2 in (ozet.get("odalar") or {}).items()},
                                "brut_m2": {"deger": ozet.get("oturum_m2"), "kaynak": etiket},
                                "oda_programi": {"deger": taban.get("oda_programi"), "kaynak": etiket},
                                "pencere": {"deger": ozet.get("pencere"), "kaynak": etiket}, "kapi": {"deger": ozet.get("kapi"), "kaynak": etiket},
                                "dis_olcu_cm": {"deger": ozet.get("dis_olcu_cm"), "kaynak": etiket}}
    olay(kart, "varyant", taban=taban["kod"], kaynak=a.kaynak_metni)
    kart_yaz(kart, a.banka)
    tanim_yolu(kod, a.banka).write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{gosterim(kod)}: {taban['kod']}'in çatı varyantı açıldı (taslak; taban tanım değişmedi) → {klasor(kod, a.banka).relative_to(kok_dizin(a.banka))}")
    return 0


def kaynak(a) -> int:
    kart = kart_oku(kod_normalize(a.kod), a.banka)
    if kart is None:
        return dur("kart yok")
    if kart["durum"] in ("kabul", "ret"):
        return dur(f"kart {kart['durum']}; değişmez")
    if a.proje is not None:
        if not (pk := kaynak_proje_kodu(a.proje)):
            return dur(f"proje kodu okunamadı: {a.proje!r} (AP-NN ya da ÇP-NN)")
        kart["kaynak"] = {**(kart.get("kaynak") or {}), "tur": "proje", "proje": pk}
    kd = kart.setdefault("kaynak_degerleri", {})
    for s in a.oda or []:
        ad, _, m2 = s.partition("=")
        kd.setdefault("odalar", {})[ad.strip()] = {"deger": float(m2.replace(",", ".")), "kaynak": a.kaynagi}
    for alan, v in (("brut_m2", a.brut_m2), ("oda_programi", a.oda_programi), ("pencere", a.pencere), ("kapi", a.kapi), ("cati_tipi", a.cati_tipi)):
        if v is not None:
            kd[alan] = {"deger": v, "kaynak": a.kaynagi}
    olay(kart, "kaynak", kaynak=a.kaynagi, proje=kaynak_proje_kodu(a.proje))
    kart_yaz(kart, a.banka)
    print(f"{kart['gosterim']}: kaynak değerleri yazıldı ({a.kaynagi})")
    return 0


# ── çizim ve denetimler ──────────────────────────────────────────────────────────────────────────────────────────────────
@contextlib.contextmanager
def yazi_denetimi(rapor: dict):
    """Bayiye giden figürler kaydedilmeden önce yazı çakışması denetlenir (testler/genel/test_yazi_cakismasi.py ile aynı yol)."""
    import matplotlib.figure
    from matplotlib.backends.backend_pdf import PdfPages
    from motor.genel import yazi_cakisma as YC
    asil_fig, asil_pdf = matplotlib.figure.Figure.savefig, PdfPages.savefig

    def fig_savefig(self, fname, *x, **k):
        if not hasattr(fname, "write"):
            rapor[Path(str(fname)).name] = YC.denetle(self, Path(str(fname)).name)
        return asil_fig(self, fname, *x, **k)

    def pdf_savefig(self, figure=None, **k):
        n = sum(1 for r in rapor if r.startswith("pafta_sayfa_")) + 1
        rapor[f"pafta_sayfa_{n}"] = YC.denetle(figure, f"pafta_sayfa_{n}")
        return asil_pdf(self, figure, **k)

    matplotlib.figure.Figure.savefig, PdfPages.savefig = fig_savefig, pdf_savefig
    try:
        yield rapor
    finally:
        matplotlib.figure.Figure.savefig, PdfPages.savefig = asil_fig, asil_pdf


def _yazi_bulgulari(rapor: dict, gk: str) -> list[str]:
    out = []
    for ad in (f"{gk}_plan_bayi.png", f"{gk}_bayi_gorsel_alt.png", "pafta_sayfa_1", "pafta_sayfa_2"):
        r = rapor.get(ad)
        if r is None:
            out.append(f"{ad}: denetlenemedi"); continue
        for anahtar, ad_tr in (("cakisan", "çakışan"), ("cizgi_kapatan", "ölçüyü kapatan"), ("yay_kapatan", "kapı yayını kesen"), ("sayfa_disi", "sayfa dışı")):
            for x in r.get(anahtar) or []:
                out.append(f"{ad}: {ad_tr} {' / '.join(str(y) for y in x[:-1])}")
    return out


def denetimler(kart: dict, t: dict, m: dict, v: dict, olcum: dict, yazi: list[str], kisa: list, banka_kok: Path) -> list[dict]:
    d = []

    def ekle(ad, durum, ayrinti=""):
        d.append({"ad": ad, "durum": durum, "ayrinti": ayrinti})

    ekle("Motor doğrulaması", "geçti" if m.get("passed") else "kaldı", "; ".join(v.get("errors") or []) or f"çıktılar {v['ciktilar']['var']}/{v['ciktilar']['beklenen']}"
         + (" (perspektif yok: bu ortamda VTK yok)" if (v.get("perspektif") or {}).get("durum") != "TAMAM" else ""))
    ifc = v.get("ifc") or {}
    ekle("IFC şema denetimi", "geçti" if ifc.get("sema_hatasi") == 0 else "kaldı", f"şema hatası {ifc.get('sema_hatasi')}")
    ekle("Yazı çakışması (bayiye giden 4 figür)", "geçti" if not yazi else "uyarı", "; ".join(yazi[:6]) or "bulgu yok")
    ekle("15 cm ve daha kısa parçalar (bayi paftası)", "bilgi" if kisa else "geçti",
         "; ".join(f"{x['zincir']} {x['parca_cm']:g} cm" for x in kisa[:6]) or "yok")
    # kartla çizimin tutarlılığı (kaynak değerleri)
    kd = kart.get("kaynak_degerleri") or {}
    farklar = []
    for ad, x in (kd.get("odalar") or {}).items():
        c = olcum["odalar"].get(ad)
        if c is None:
            farklar.append(f"{ad}: çizimde yok")
        elif abs(c - float(x["deger"])) > max(0.5, 0.03 * float(x["deger"])):
            farklar.append(f"{ad}: çizim {c:g}, kaynak {x['deger']:g}")
    for alan, cizim in (("brut_m2", olcum["oturum_m2"]), ("oda_programi", olcum["oda_programi"]), ("pencere", olcum["pencere"]),
                        ("kapi", olcum["kapi"]), ("cati_tipi", olcum["cati"]["tip"]), ("dis_olcu_cm", olcum["dis_olcu_cm"])):
        if alan not in kd or kd[alan].get("deger") is None:
            continue
        k = kd[alan]["deger"]
        esit = abs(float(cizim) - float(k)) <= 0.5 if alan == "brut_m2" else (
            [round(float(x)) for x in cizim] == [round(float(x)) for x in k] if alan == "dis_olcu_cm" else str(cizim) == str(k))
        if not esit:
            farklar.append(f"{alan}: çizim {cizim}, kaynak {k}")
    ekle("Kartla çizimin tutarlılığı (m², oda programı, açıklık, çatı)", ("uyarı" if farklar else "geçti") if kd else "bilgi",
         "; ".join(farklar) or ("kaynak değerleri çizimle aynı" if kd else "kaynak değeri girilmedi"))
    # bankada aynı kod ya da aynı plan
    tumu = tum_tanimlar(banka_kok, haric=kart["kod"])
    ayni_plan = sorted(k for k, x in tumu.items() if plan_izi(x) == plan_izi(t))
    ayni_cati = sorted(k for k in ayni_plan if kanonik_sha(tumu[k].get("cati")) == kanonik_sha(t.get("cati")))
    if ayni_cati:
        ekle("Bankada aynı model", "kaldı", f"aynı plan ve aynı çatı: {', '.join(ayni_cati)}")
    elif ayni_plan and kart.get("taban_model") and kart["taban_model"] in ayni_plan:
        ekle("Bankada aynı model", "geçti", f"aynı plan: {', '.join(ayni_plan)} (çatı varyantı; çatı farklı)")
    elif ayni_plan:
        ekle("Bankada aynı model", "uyarı", f"aynı plan bankada var: {', '.join(ayni_plan)}")
    else:
        ekle("Bankada aynı model", "geçti", "aynı kod ve aynı plan yok")
    return d


def metraj_hesapla(kart: dict, olcum: dict) -> None:
    """Metraj kapısı çizimden değil, çelik hakeminin ölçümünden gelir (`metraj --celik`); ölçümü olmayan kartta "yok"."""
    if (kart.get("metraj_testi") or {}).get("kaynak") != "celik_hakemi":
        kart["metraj_testi"] = {"durum": "yok", "not": METRAJ_YOK}


def ciz(a) -> int:
    kod = kod_normalize(a.kod)
    kart = kart_oku(kod, a.banka)
    if kart is None:
        return dur("kart yok (önce `ac` ya da `varyant`)")
    if kart["durum"] in ("kabul", "ret"):
        return dur(f"kart {kart['durum']}: kabul edilen tanım donar (D-07), yeni kod ya da sürüm açın")
    tp = tanim_yolu(kod, a.banka)
    if not tp.is_file():
        return dur("tanim.json yok")
    t = json.loads(tp.read_text(encoding="utf-8"))
    from motor.genel import uret as U
    gk = U.kod_govde(t)
    no = 1 + sum(1 for x in kart.get("gecmis") or [] if x.get("olay") == "ciz")
    hedef = Path(a.cikti) / B.dosya_adi(kod) / f"c{no:02d}"
    if hedef.exists() and any(hedef.iterdir()):
        return dur(f"çıktı klasörü dolu: {hedef}")
    if (e := _pim_denetle(kart)):
        return dur(e)
    set_yolu, karkas_yolu = pim_yollari(kart)
    rapor: dict = {}
    with yazi_denetimi(rapor), contextlib.redirect_stdout(sys.stderr):
        m = U.uret(tp, hedef, is_emri_no=None, revizyon=None, set_yolu=set_yolu, yontem="panel", perspektif=a.perspektif, bayi=True,
                   kaynak=f"Yapı Tanımı 0.5 ({gk}; İE-09 atölyesi)", karkas_yolu=karkas_yolu)
    v = json.loads((hedef / "validation.json").read_text(encoding="utf-8"))
    liste = json.loads((hedef / f"{gk}_yukleme.json").read_text(encoding="utf-8")) if (hedef / f"{gk}_yukleme.json").exists() else {"satirlar": []}
    olcum = olc(t, set_yolu, liste, karkas_yolu)
    ozet_p = hedef / f"{gk}_pafta_ozet.json"
    kisa = (json.loads(ozet_p.read_text(encoding="utf-8")).get("kontrol_notlari") or []) if ozet_p.exists() else []
    dn = denetimler(kart, t, m, v, olcum, _yazi_bulgulari(rapor, gk), kisa, a.banka)
    metraj_hesapla(kart, olcum)
    kart["olcum"] = olcum
    kart["brut_m2"], kart["oda_programi"] = olcum["oturum_m2"], olcum["oda_programi"]
    kart["cati_tipi"] = t["cati"].get("tip")
    kart["cati_adi"] = cati_adi(t)
    kart["son_cizim"] = {"no": no, "zaman": simdi(), "tanim_sha256": sha256(tp), "kural_seti": olcum["kural_seti"], "pim": kart.get("pim"),
                         "passed": bool(m.get("passed")),
                         "cikti": _goreli(hedef), "denetimler": dn, "sure_s": v.get("sure_s"), "perspektif": (v.get("perspektif") or {}).get("durum")}
    kart["durum"] = "beklemede" if kart["metraj_testi"]["durum"] == "beklemede" else "kontrolde"
    from araclar import atolye_sayfa
    pdf = hedef / f"{B.dosya_adi(kod)}_kontrol_c{no:02d}.pdf"
    atolye_sayfa.kontrol_pdf(kart, hedef, gk, pdf)
    kart["son_cizim"]["kontrol_pdf"] = _goreli(pdf)
    olay(kart, "ciz", no=no, durum=kart["durum"], passed=bool(m.get("passed")))
    kart_yaz(kart, a.banka)
    kalan = [x for x in dn if x["durum"] == "kaldı"]
    print(f"{kart['gosterim']} c{no:02d}: motor {'geçti' if m.get('passed') else 'GEÇMEDİ'} · liste {olcum['liste']['satir']} satır, çelik {olcum['liste']['celik_kg']:g} kg"
          f" · metraj testi {kart['metraj_testi']['durum']} · denetim: {len(kalan)} kaldı, {sum(1 for x in dn if x['durum'] == 'uyarı')} uyarı · durum {kart['durum']}")
    print(f"kontrol sayfası: {pdf}")
    return 0 if m.get("passed") and not kalan else 1


def _goreli(p: Path) -> str:
    try:
        return p.resolve().relative_to(KOK).as_posix()
    except ValueError:
        return str(p)


def cati_adi(t: dict) -> str:
    try:
        adlar = (json.loads((KOK / "kurallar" / "cizim" / "pafta_sablonu.json").read_text(encoding="utf-8")).get("cati_tipi_adi") or {}).get("deger") or {}
    except Exception:
        adlar = {}
    ct = t.get("cati") or {}
    ad = (ct.get("tip_adi") or "").split(":")[0].strip() or adlar.get(ct.get("tip"), ct.get("tip") or "")
    return ad[:1].upper() + ad[1:]


# ── düzeltme, metraj, ret ────────────────────────────────────────────────────────────────────────────────────────────────
def duzelt(a) -> int:
    kart = kart_oku(kod_normalize(a.kod), a.banka)
    if kart is None:
        return dur("kart yok")
    if kart["durum"] in ("kabul", "ret"):
        return dur(f"kart {kart['durum']}: kabul edilen tanım donar (D-07), yeni kod ya da sürüm açın")
    no = (kart.get("son_cizim") or {}).get("no")
    kart.setdefault("duzeltmeler", []).append({"zaman": simdi(), "tur": a.tur, "metin": a.metin, "cizim": no})
    kart["durum"] = "taslak"
    olay(kart, "duzelt", tur=a.tur)
    kart_yaz(kart, a.banka)
    if a.tur == "motor":
        kusur_yaz(kart, a.metin)
    print(f"{kart['gosterim']}: düzeltme ({a.tur}) kayıtlı; tanımı düzeltip yeniden çizin")
    return 0


def kusur_yaz(kart: dict, metin: str) -> None:
    if not KUSUR_DEFTERI.exists():
        KUSUR_DEFTERI.parent.mkdir(parents=True, exist_ok=True)
        KUSUR_DEFTERI.write_text("# İE-09 · Motor kusurları defteri\n\n| Tarih | Model | Çizim | Ne görüldü | Durum |\n|---|---|---|---|---|\n", encoding="utf-8")
    no = (kart.get("son_cizim") or {}).get("no")
    with KUSUR_DEFTERI.open("a", encoding="utf-8") as f:
        f.write(f"| {bugun()} | {kart['gosterim']} | {'c%02d' % no if no else '-'} | {metin.replace('|', '/')} | açık |\n")


def _git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=str(KOK), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _sadelestir(t: dict) -> dict:
    return {k: v for k, v in t.items() if k not in TANIM_ESLIK_DISI}


def _pim_kaydi(kayit: dict | None, ne: str) -> tuple[dict | None, str | None]:
    """Hakemin listesindeki kural kaydından pim ({yol, sha256}; içerik adresli kopya): (pim, sorun)."""
    if not kayit:
        return None, None
    kopya = KOK / str(kayit.get("kopya") or "")
    if not kayit.get("kopya") or not kopya.is_file() or sha256(kopya) != kayit.get("sha256"):
        return None, f"{ne} kopyası yok ya da özeti tutmuyor ({kayit.get('kopya')})"
    return {"yol": kopya.relative_to(KOK).as_posix(), "sha256": kayit["sha256"], "sema": kayit.get("sema")}, None


def _pim_denetle(kart: dict) -> str | None:
    for ne, x in (("kural seti", (kart.get("pim") or {}).get("kural_seti")), ("karkas kuralı", (kart.get("pim") or {}).get("karkas"))):
        if x and (not (KOK / x["yol"]).is_file() or sha256(KOK / x["yol"]) != x["sha256"]):
            return f"pimdeki {ne} yok ya da değişti ({x['yol']})"
    return None


def celik_olcumu(proje: str, t: dict) -> tuple[dict | None, str | None]:
    """Çelik hakeminin `proje`deki ölçümü bu tanım için geçerli mi; geçerliyse kartın metraj testi ve pimi: (kayıt, sorun).

    Hakem yalnız okunur (Z-03): kendi listemiz (`bizim_liste.json`), hakemin sonucu (`sonuc.json`; `kiyas --sonuc-yaz` yazar) ve açık
    projede hakemin cevabı (`veri/<CPnn>_hakem_cevabi.json`). Açılan projede yeniden ölçüm klasörü (`acik/`) önceliklidir (İE-16 PR-6a)."""
    from testler.celik import kiyas
    kok = CELIK_PROJELER / kiyas.kod_klasoru(proje)
    klasor_ = kok / kiyas.YENIDEN if (kok / kiyas.YENIDEN / "sonuc.json").is_file() else kok
    bl, sp = klasor_ / "bizim_liste.json", klasor_ / "sonuc.json"
    if not bl.is_file() or not sp.is_file():
        return None, f"{proje}: hakemin listesi ya da sonucu yok ({klasor_.relative_to(KOK).as_posix()})"
    bizim, sonuc = json.loads(bl.read_text(encoding="utf-8")), json.loads(sp.read_text(encoding="utf-8"))
    if bizim.get("kod") != proje or sonuc.get("kod") != proje:
        return None, f"{proje}: listenin ya da sonucun kodu farklı"
    # 1. ölçülen tanım bu tanım mı (kod ve ad dışında)
    tk = KOK / str((bizim.get("tanim") or {}).get("yol") or "")
    if not tk.is_file() or sha256(tk) != (bizim.get("tanim") or {}).get("sha256"):
        return None, f"{proje}: hakemin listesi bugünkü tanımdan üretilmemiş (liste yeniden üretilmeli)"
    if _sadelestir(json.loads(tk.read_text(encoding="utf-8"))) != _sadelestir(t):
        return None, f"{proje}: bankadaki tanım hakemin ölçtüğü tanımdan farklı (yalnız {', '.join(TANIM_ESLIK_DISI)} ayrılabilir)"
    # 2. sonuç bu listenin sonucu mu (liste, sonucun yazıldığı commit'ten beri değişmedi)
    lc = (sonuc.get("bizim_liste") or {}).get("commit")
    yol = bl.relative_to(KOK).as_posix()
    if (sonuc.get("bizim_liste") or {}).get("yol") != yol or not lc or _git("rev-parse", f"{lc}:{yol}") != _git("hash-object", yol):
        return None, f"{proje}: hakemin sonucu bugünkü listenin sonucu değil (liste sonuçtan sonra değişmiş ya da commit yok)"
    # 3. pim: ölçümdeki kural seti ve karkas kuralı
    ks, s1 = _pim_kaydi(bizim.get("kural_seti"), "kural seti")
    kk, s2 = _pim_kaydi(bizim.get("karkas_kurali"), "karkas kuralı")
    if s1 or s2 or ks is None:
        return None, f"{proje}: {s1 or s2 or 'kural seti kaydı yok'}"
    kapi = sonuc.get("celik_kg_kapisi") or {}
    # 4. açık projede kapı hakemin işlevleriyle yeniden hesaplanır; tür tür tablo
    turler, cevap_yolu = None, CELIK_CEVAPLAR / f"{kiyas.kod_klasoru(proje)}_hakem_cevabi.json"
    if (sonuc.get("muhur") or {}).get("durum") == "acik" and cevap_yolu.is_file():
        cv = json.loads(cevap_yolu.read_text(encoding="utf-8"))
        if cv.get("liste_sha256") != (sonuc.get("muhur") or {}).get("sha256"):
            return None, f"{proje}: hakemin cevabı sonuçtaki listeyle aynı liste değil"
        gercek = {**cv["celik"], "kgsiz_turler": sorted({s["tur"] for s in cv["celik"]["satirlar"] if s["kg"] is None})}   # oku.turler gibi
        bc = kiyas.bizim_celik(bizim["satirlar"])
        yeni = kiyas.kapi(bc, gercek)
        if yeni["sonuc"] != kapi.get("sonuc") or (kapi.get("fark_yuzde") is not None and yeni.get("fark_yuzde") != kapi["fark_yuzde"]):
            return None, f"{proje}: hakemin sonucu yeniden hesaplanan kapıyla tutmuyor ({kapi.get('sonuc')} ↔ {yeni['sonuc']})"
        turler = [{k: r[k] for k in ("tur", "ad", "harf", "bizim_adet", "gercek_adet", "bizim_kg", "gercek_kg")}
                  for r in kiyas.celik_tablosu(gercek, bc, None)]
        kapi = {**kapi, "fark_yuzde": yeni.get("fark_yuzde"), "bizim_kapi_kg": yeni.get("bizim_kapi_kg"), "gercek_kapi_kg": yeni.get("gercek_kapi_kg")}
    durum = {"geçti": "gecti", "geçmedi": "beklemede"}.get(kapi.get("sonuc"), "beklemede")
    kayit = {"durum": durum, "kaynak": "celik_hakemi", "proje": proje, "hakem_sonucu": kapi.get("sonuc"),
             "neden": None if durum == "gecti" else (kapi.get("neden") or "çelik kg farkı ±%3'ü aşıyor"),
             "fark_yuzde": kapi.get("fark_yuzde"), "esik_yuzde": kapi.get("pay_yuzde") or METRAJ_ESIGI_YUZDE,
             "kapi_disi": kapi.get("kapi_disi") or [], "bizim_kapi_kg": kapi.get("bizim_kapi_kg"), "gercek_kapi_kg": kapi.get("gercek_kapi_kg"),
             "turler": turler, "muhur_durumu": (sonuc.get("muhur") or {}).get("durum"), "liste_sha256": (sonuc.get("muhur") or {}).get("sha256"),
             "sonuc": sp.relative_to(KOK).as_posix(), "sonuc_tarihi": sonuc.get("tarih"), "kiyas_commit": sonuc.get("kiyas_commit"),
             "bizim_liste_commit": lc, "yontem": bizim.get("yontem"), "zaman": simdi()}
    return {"metraj_testi": {k: v for k, v in kayit.items() if v is not None}, "pim": {"kural_seti": ks, "karkas": kk}}, None


def metraj(a) -> int:
    kart = kart_oku(kod_normalize(a.kod), a.banka)
    if kart is None:
        return dur("kart yok")
    if kart["durum"] in ("kabul", "ret"):
        return dur(f"kart {kart['durum']}")
    tp = tanim_yolu(kart["kod"], a.banka)
    if not tp.is_file():
        return dur("tanim.json yok")
    sonuc, sorun = celik_olcumu(a.celik.strip(), json.loads(tp.read_text(encoding="utf-8")))
    if sorun:
        return dur(sorun)
    pim_degisti = kart.get("son_cizim") is not None and (kart["son_cizim"].get("pim") != sonuc["pim"])
    kart.update(sonuc)
    if pim_degisti:
        kart["durum"] = "taslak"                                          # çizim başka kural setiyle: kabul edilen çizim pimle çizilmeli
    elif kart["durum"] in ("kontrolde", "beklemede"):
        kart["durum"] = "beklemede" if kart["metraj_testi"]["durum"] == "beklemede" else "kontrolde"
    mt = kart["metraj_testi"]
    olay(kart, "metraj", durum=mt["durum"], proje=mt["proje"], fark_yuzde=mt.get("fark_yuzde"))
    kart_yaz(kart, a.banka)
    print(f"{kart['gosterim']}: metraj testi {mt['durum']} (çelik hakemi, {mt['proje']}: {mt['hakem_sonucu']}"
          + (f", fark {isaretli(mt['fark_yuzde'])}" if mt.get("fark_yuzde") is not None else "") + f"; eşik ±%{mt['esik_yuzde']:g})"
          + f" · pim {kart['pim']['kural_seti']['yol']}" + (f" + {kart['pim']['karkas']['yol']}" if kart["pim"].get("karkas") else "")
          + (" · çizim başka kural setiyle: yeniden çizin" if pim_degisti else ""))
    return 0 if mt["durum"] != "beklemede" else 1


def ret(a) -> int:
    kart = kart_oku(kod_normalize(a.kod), a.banka)
    if kart is None:
        return dur("kart yok")
    if kart["durum"] == "kabul":
        return dur("kabul edilmiş model reddedilmez; bankadan çıkarmak ayrı karar (D-20)")
    kart["durum"] = "ret"
    olay(kart, "ret", neden=a.neden)
    kart_yaz(kart, a.banka)
    print(f"{kart['gosterim']}: ret (kart kalır; silme yok)")
    return 0


# ── kabul ve kontrol dosyası ─────────────────────────────────────────────────────────────────────────────────────────────
def pim_seti() -> Path:
    """Kabuldeki kural seti pimi: dondurulmuş setlerin en yenisi (kurallar/liste/setler/*.json; bugün 0.19)."""
    setler = sorted((KOK / "kurallar" / "liste" / "setler").glob("*.json"), key=lambda p: tuple(int(x) for x in p.stem.split(".")))
    return setler[-1]


def tam_izler(tp: Path, set_yolu: Path, karkas_yolu: Path | None = None) -> dict[str, str]:
    """Çizim setinin içerik izleri (PNG bayt, PDF içerik, JSON kanonik, IFC içerik, DXF içerik; `testler/referans/parmak_izi.genel_ozet`),
    sabit üretim zamanıyla ve perspektifsiz, ayrı süreçte (referans koşusu gibi); karkas kuralı pimlenmişse o kopyayla."""
    sys.path.insert(0, str(KOK / "testler" / "referans"))
    from parmak_izi import genel_ozet
    with tempfile.TemporaryDirectory() as tmp:
        ortam = {**os.environ, "TEST_SABIT_ZAMAN": SABIT_ZAMAN, "PYTHONHASHSEED": "0",
                 "PYTHONPATH": os.pathsep.join([str(KOK / "testler" / "referans" / "sabit_zaman"), str(KOK)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else []))}
        r = subprocess.run([sys.executable, "-m", "motor.genel.uret", str(tp), str(Path(tmp) / "c"), "--set", str(set_yolu), "--yontem", "panel", "--perspektifsiz"]
                           + (["--karkas", str(karkas_yolu)] if karkas_yolu else []),
                           cwd=str(KOK), env=ortam, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"tam izler üretilemedi: {r.stdout[-300:]} {r.stderr[-300:]}")
        c = Path(tmp) / "c"
        return {p.name: genel_ozet(p) for p in sorted(c.iterdir())
                if p.is_file() and p.suffix.lower() in (".png", ".pdf", ".json", ".ifc", ".dxf") and p.name not in ("validation.json", "manifest.json")}


def kontrol_kaydi(kart: dict, tp: Path, tam: bool = True) -> dict:
    """Modelin kontrol dosyası: kartın pimi (metraj kapısının ölçüldüğü kural seti ve karkas kuralı) varsa onunla, yoksa dondurulmuş
    setlerin en yenisiyle."""
    t = json.loads(tp.read_text(encoding="utf-8"))
    set_yolu, karkas_yolu = pim_yollari(kart)
    pim = set_yolu or pim_seti()
    k = {"sema": B.KONTROL_SEMASI, "kod": kart["kod"], "tanim_sha256": sha256(tp), "kural_seti": pim.relative_to(KOK).as_posix(),
         "kural_seti_sha256": sha256(pim)}
    if karkas_yolu:
        k |= {"karkas_kurali": karkas_yolu.relative_to(KOK).as_posix(), "karkas_kurali_sha256": sha256(karkas_yolu)}
    k["hizli"] = olc(t, pim, None, karkas_yolu)
    if tam:
        k["tam"] = tam_izler(tp, pim, karkas_yolu)
    return k


def aday_kaydi(kart: dict, tp: Path, cizim: Path, banka_kok: Path) -> dict:
    """`aday_kaydet.genel` ile aynı alanlar (Katalog, karar, worker ve aday_kabul aynı kaydı okur); yol depo köküne göre, görsel `is_emri/`e göre."""
    t = json.loads(tp.read_text(encoding="utf-8"))
    from motor.genel import uret as U
    from motor.genel.bayi_gorseli import oda_programi, musteri_projesi
    gk = U.kod_govde(t)
    girdi = json.loads((cizim / f"{gk}_girdi.json").read_text(encoding="utf-8"))
    v = json.loads((cizim / "validation.json").read_text(encoding="utf-8"))
    o = kart["olcum"]
    bina = round(float(girdi["bina_m2"]), 2)
    oturum = round(float(girdi.get("oturum_m2") or girdi["bina_m2"]), 2)
    vm = girdi.get("veranda_m2") or 0
    veranda = round(float(vm.get("net") or vm.get("brut") or 0) if isinstance(vm, dict) else float(vm), 2)
    kd = kok_dizin(banka_kok)
    gorece = tp.resolve().relative_to(kd.resolve()).as_posix()
    gorsel = os.path.relpath(klasor(kart["kod"], banka_kok) / "kart.png", kd / "is_emri").replace(os.sep, "/")
    mp = bool(kart.get("musteri_projesi") or musteri_projesi(t))
    return {"kod": kart["kod"], "gosterim": kart["gosterim"], "durum": "gecerli", "motor": "genel", "tanim": gorece, "tanim_sha256": sha256(tp),
            "gorsel": gorsel, "referans_model": kart.get("taban_model") or kart["kod"], "yapi_turu": "celik", "kat": int(kart.get("kat") or 1),
            "oda_programi": oda_programi(t), "katalog_m2": bina, "kapali_m2": round(oturum - veranda, 2), "veranda_m2": veranda, "varyantlar": [],
            "musteri_projesi": mp, "sunum": {"cati_adi": cati_adi(t), "ad": "" if mp else t.get("ad", "")},
            "ozet": {"dis_olcu_cm": o["dis_olcu_cm"], "oturum_m2": oturum, "odalar": o["odalar"], "pencere": o["pencere"], "kapi": o["kapi"],
                     "cati": t["cati"].get("tip"), "liste_satir": v.get("liste_satir"), "kural_seti": Path(v.get("set", "")).name,
                     "perspektif": (v.get("perspektif") or {}).get("durum")},
            "kaynak": {"metin": (kart.get("kaynak") or {}).get("metin") or "", "dosya": gorece,
                       "dogrulama": f"İE-09 atölyesi, kontrol sayfası c{kart['son_cizim']['no']:02d} ({kart['kabul']['tarih']}); metraj kapısı: "
                                     + metraj_metni(kart["metraj_testi"]),
                       "karar": "D-20; D-11"},
            "not": kart["kabul"].get("not") or ""}


def isaretli(x) -> str:
    """Yüzde farkı, işaret yüzde imisinden önce: +%0.93, −%12.83 (yoksa "…")."""
    return "…" if x is None else ("−" if x < 0 else "+" if x > 0 else "") + f"%{abs(x):g}"


def metraj_metni(mt: dict) -> str:
    if mt.get("durum") == "gecti":
        return f"geçti (çelik hakemi, {mt.get('proje')}, fark {isaretli(mt.get('fark_yuzde'))}, ±%{mt.get('esik_yuzde', METRAJ_ESIGI_YUZDE):g})"
    return {"yok": "koşulmadı, referans yok"}.get(mt.get("durum"), str(mt.get("durum")))


def kapilar() -> list[str]:
    """Kabul kapısı: harness 22/22 ve pytest testler (model bankadayken). Bulgu listesi; boşsa geçti."""
    bulgu = []
    with tempfile.TemporaryDirectory() as tmp:
        kod = ("import sys; from pathlib import Path; from beyin import harness; "
               f"ok, n = harness.main(durum_dir=Path({str(Path(tmp) / 'durum')!r}), sessiz=True, rapor_yaz=False); print(ok, n); sys.exit(0 if ok == n == 22 else 1)")
        r = subprocess.run([sys.executable, "-c", kod], cwd=str(KOK), capture_output=True, text=True)
        if r.returncode != 0:
            bulgu.append(f"harness: {r.stdout.strip()[-200:]} {r.stderr.strip()[-300:]}")
    print("kabul kapısı: pytest testler koşuyor (birkaç dakika)…", file=sys.stderr)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "testler"], cwd=str(KOK), capture_output=True, text=True)
    if r.returncode != 0:
        bulgu.append("pytest: " + " | ".join(x for x in r.stdout.splitlines() if x.startswith(("FAILED", "ERROR")) or " failed" in x)[-1500:])
    return bulgu


def kabul(a) -> int:
    kod = kod_normalize(a.kod)
    kart = kart_oku(kod, a.banka)
    if kart is None:
        return dur("kart yok")
    if kart["durum"] == "beklemede":
        mt = kart["metraj_testi"]
        return dur(f"metraj kabul testi geçmedi (çelik fark {isaretli(mt.get('fark_yuzde'))}, eşik ±%{METRAJ_ESIGI_YUZDE:g}): model beklemede, kabul edilemez")
    if kart["durum"] != "kontrolde":
        return dur(f"kart {kart['durum']}: kabul yalnız çizilip kontrole gönderilmiş modele ({'önce `ciz`' if kart['durum'] == 'taslak' else 'değişmez'})")
    tp = tanim_yolu(kod, a.banka)
    sc = kart.get("son_cizim") or {}
    if sc.get("tanim_sha256") != sha256(tp):
        return dur("tanım son çizimden sonra değişti: yeniden çizin, kontrol sayfasını gösterin")
    if (e := _pim_denetle(kart)):
        return dur(e)
    if sc.get("pim") != kart.get("pim"):
        return dur("son çizim kartın pimindeki kural setiyle çizilmedi: yeniden çizin, kontrol sayfasını gösterin")
    if (kart.get("metraj_testi") or {}).get("durum") == "beklemede":
        return dur("metraj kabul testi geçmedi: beklemede")
    kalan = [x for x in sc.get("denetimler") or [] if x["durum"] == "kaldı"]
    if kalan:
        return dur("denetim kaldı: " + "; ".join(f"{x['ad']} ({x['ayrinti']})" for x in kalan))
    cizim = Path(sc["cikti"]) if Path(sc["cikti"]).is_absolute() else KOK / sc["cikti"]
    from motor.genel import uret as U
    gk = U.kod_govde(json.loads(tp.read_text(encoding="utf-8")))
    gorsel = cizim / f"{gk}_bayi_gorsel.png"
    if not gorsel.is_file():
        return dur(f"son çizimin bayi görseli yok ({_goreli(gorsel)}); aynı tanımla yeniden çizin")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.tarih):
        return dur("tarih YYYY-AA-GG")
    yedek = copy.deepcopy(kart)
    k = klasor(kod, a.banka)
    kontrol = kontrol_kaydi(kart, tp, tam=not a.izsiz)
    (k / "kontrol.json").write_text(json.dumps(kontrol, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shutil.copyfile(gorsel, k / "kart.png")
    kart["durum"] = "kabul"
    kart["kabul"] = {"kim": a.kim, "tarih": a.tarih, "karar": "D-11" if a.kim == "Lokman" else None, "not": a.not_, "cizim": sc["no"],
                     "kural_seti": kontrol["kural_seti"], "metraj_kapisi": kart["metraj_testi"]["durum"],
                     "metraj_proje": kart["metraj_testi"].get("proje")}   # "yok": kabul metraj doğrulaması değildir
    kart["aday"] = aday_kaydi(kart, tp, cizim, a.banka)
    olay(kart, "kabul", cizim=sc["no"])
    kart_yaz(kart, a.banka)
    sorun = [s for d, s in B.denetle(a.banka) if d == k.name]
    bulgu = [f"banka: {'; '.join(x)}" for x in sorun] + ([] if a.kapisiz else kapilar())
    if bulgu:
        olay(yedek, "kabul_durdu", neden="; ".join(bulgu)[:500])
        kart_yaz(yedek, a.banka)
        print("KABUL DURDU: model bankadayken bir sonuç değişti ya da kayıt geçersiz; kart kontrolde kaldı (D-20: test ayrı PR'da, Patron onayıyla)")
        for b in bulgu:
            print("  -", b)
        return 1
    print(f"{kart['gosterim']}: kabul (kim {a.kim[:1]}…, {a.tarih}, D-11) · kontrol dosyası {'hızlı + tam' if 'tam' in kontrol else 'hızlı'} · "
          f"kural seti pimi {kontrol['kural_seti']} · bayiye sunulma K-A10 kaydıyla (haftalık sürüm)")
    return 0


def _kontrol_farki(kart: dict, k: dict, tp: Path, tam: bool) -> list[str]:
    f = []
    if sha256(tp) != k.get("tanim_sha256"):
        f.append("tanım değişti (D-07: yeni kod ya da sürüm)")
    pim = KOK / k["kural_seti"]
    if not pim.is_file() or sha256(pim) != k.get("kural_seti_sha256"):
        f.append(f"kural seti pimi değişti ya da yok ({k['kural_seti']})")
        return f
    karkas = KOK / k["karkas_kurali"] if k.get("karkas_kurali") else None
    if karkas and (not karkas.is_file() or sha256(karkas) != k.get("karkas_kurali_sha256")):
        f.append(f"karkas kuralı pimi değişti ya da yok ({k['karkas_kurali']})")
        return f
    t = json.loads(tp.read_text(encoding="utf-8"))
    yeni = olc(t, pim, None, karkas)
    for alan, eski in k["hizli"].items():
        if yeni.get(alan) != eski:
            f.append(f"hızlı: {alan}")
    if tam and "tam" in k:
        izler = tam_izler(tp, pim, karkas)
        for ad in sorted(set(izler) | set(k["tam"])):
            if izler.get(ad) != k["tam"].get(ad):
                f.append(f"tam: {ad}" + (" (yok)" if ad not in izler else " (yeni)" if ad not in k["tam"] else ""))
    return f


def kontrol(a) -> int:
    kotu = 0
    for d, s in B.denetle(a.banka):
        print(f"FARKLI  {d}: {'; '.join(s)}"); kotu += 1
    istenen = {kod_normalize(x) for x in a.kodlar}
    for kart in B.kartlar(a.banka):
        if kart.get("durum") != "kabul" or (istenen and kart.get("kod") not in istenen):
            continue
        kp = kart["_klasor"] / "kontrol.json"
        if not kp.is_file():
            continue                                                       # denetle() zaten bildirdi
        f = _kontrol_farki(kart, json.loads(kp.read_text(encoding="utf-8")), kart["_klasor"] / "tanim.json", a.tam)
        print(f"{'AYNI  ' if not f else 'FARKLI'}  {kart['gosterim']}" + (f": {'; '.join(f)}" if f else (" (hızlı + tam)" if a.tam else " (hızlı)")))
        kotu += bool(f)
    print("SONUÇ:", "banka kontrol dosyalarıyla aynı" if not kotu else f"{kotu} modelde fark var")
    return 0 if not kotu else 1


def dondur(a) -> int:
    kod = kod_normalize(a.kod)
    kart = kart_oku(kod, a.banka)
    if kart is None or kart.get("durum") != "kabul":
        return dur("yalnız kabul edilmiş modelin kontrol dosyası yeniden dondurulur")
    if not a.gerekce.strip():
        return dur("--gerekce gerekli")
    if not re.fullmatch(r"[A-Z]-\d{2}|K\d{2}|Z-\d{2}", a.karar) or not any((KOK / "KARARLAR").glob(f"{a.karar}*")):
        return dur(f"--karar KARARLAR/ altında var olan bir karar olmalı: {a.karar}")
    tp = tanim_yolu(kod, a.banka)
    k = kontrol_kaydi(kart, tp, tam=True)
    k["dondurma"] = {"tarih": bugun(), "gerekce": a.gerekce, "karar": a.karar}
    (klasor(kod, a.banka) / "kontrol.json").write_text(json.dumps(k, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    olay(kart, "dondur", karar=a.karar)
    kart_yaz(kart, a.banka)
    print(f"{kart['gosterim']}: kontrol dosyası yeniden donduruldu ({a.karar}). Bu değişiklik ayrı PR'da, Patron'un açık onayıyla birleşir (D-20).")
    return 0


# ── gün sonu ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def gunluk(a) -> int:
    tarih = a.tarih or bugun()
    say = {"ac": set(), "ciz": 0, "cizilen": set(), "kabul": set(), "ret": set(), "beklemede": set()}
    turler: dict[str, int] = {}
    kusurlar = []
    for kart in B.kartlar(a.banka):
        if kart.get("_hata"):
            continue
        g = kart.get("gosterim") or kart.get("kod")
        for o in kart.get("gecmis") or []:
            if not str(o.get("zaman", "")).startswith(tarih):
                continue
            if o["olay"] in ("ac", "varyant"):
                say["ac"].add(g)
            elif o["olay"] == "ciz":
                say["ciz"] += 1; say["cizilen"].add(g)
                if o.get("durum") == "beklemede":
                    say["beklemede"].add(g)
            elif o["olay"] in ("kabul", "ret"):
                say[o["olay"]].add(g)
        for d in kart.get("duzeltmeler") or []:
            if str(d.get("zaman", "")).startswith(tarih):
                turler[d["tur"]] = turler.get(d["tur"], 0) + 1
                if d["tur"] == "motor":
                    kusurlar.append(f"{g}: {d['metin']}")
    s = [f"## Atölye günü {tarih}", "",
         f"- Açılan: {len(say['ac'])} ({', '.join(sorted(say['ac'])) or '-'})",
         f"- Çizilen: {len(say['cizilen'])} model, {say['ciz']} çizim",
         f"- Kabul: {len(say['kabul'])} ({', '.join(sorted(say['kabul'])) or '-'}) · ret: {len(say['ret'])} · beklemede: {len(say['beklemede'])}",
         "- Düzeltme türleri: " + (", ".join(f"{k} {v}" for k, v in sorted(turler.items())) or "yok"),
         "- Motor kusurları: " + ("; ".join(kusurlar) or "yok")]
    print("\n".join(s))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banka", type=Path, default=B.BANKA_DIR, help=argparse.SUPPRESS)          # yalnız aracın kendi testinde
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("ac"); p.add_argument("kod"); p.add_argument("--ad", required=True); p.add_argument("--aile", default="tek kat çelik")
    p.add_argument("--kat", type=int, default=1); p.add_argument("--kaynak-metni", default=""); p.add_argument("--proje", default=None)
    p.add_argument("--kaynak-dosya", action="append"); p.add_argument("--musteri-projesi", action="store_true"); p.add_argument("--tanim", default=None)
    p = alt.add_parser("varyant"); p.add_argument("kod"); p.add_argument("--taban", required=True); p.add_argument("--cati", required=True)
    p.add_argument("--ad", required=True); p.add_argument("--aile", default=None); p.add_argument("--kaynak-metni", default="")
    p = alt.add_parser("kaynak"); p.add_argument("kod"); p.add_argument("--kaynagi", required=True); p.add_argument("--oda", action="append")
    p.add_argument("--brut-m2", type=float); p.add_argument("--oda-programi"); p.add_argument("--pencere", type=int); p.add_argument("--kapi", type=int)
    p.add_argument("--cati-tipi"); p.add_argument("--proje", default=None, help="kartın kaynak projesi (AP-NN ya da ÇP-NN)")
    p = alt.add_parser("ciz"); p.add_argument("kod"); p.add_argument("--cikti", default=str(CIKTI_VARSAYILAN))
    p.add_argument("--perspektif", action="store_true", help="VTK varsa perspektifli bayi görseli")
    p = alt.add_parser("duzelt"); p.add_argument("kod"); p.add_argument("--tur", required=True, choices=sorted(DUZELTME_TURLERI)); p.add_argument("--metin", required=True)
    p = alt.add_parser("metraj"); p.add_argument("kod"); p.add_argument("--celik", required=True, help="çelik hakeminin projesi (ÇP-NN)")
    p = alt.add_parser("kabul"); p.add_argument("kod"); p.add_argument("--kim", default="Lokman"); p.add_argument("--tarih", default=bugun())
    p.add_argument("--not", dest="not_", default=""); p.add_argument("--kapisiz", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--izsiz", action="store_true", help=argparse.SUPPRESS)
    p = alt.add_parser("ret"); p.add_argument("kod"); p.add_argument("--neden", required=True)
    p = alt.add_parser("gunluk"); p.add_argument("--tarih", default=None)
    p = alt.add_parser("kontrol"); p.add_argument("kodlar", nargs="*"); p.add_argument("--tam", action="store_true")
    p = alt.add_parser("dondur"); p.add_argument("kod"); p.add_argument("--gerekce", required=True); p.add_argument("--karar", required=True)
    a = ap.parse_args(argv)
    return {"ac": ac, "varyant": varyant, "kaynak": kaynak, "ciz": ciz, "duzelt": duzelt, "metraj": metraj, "kabul": kabul, "ret": ret,
            "gunluk": gunluk, "kontrol": kontrol, "dondur": dondur}[a.komut](a)


if __name__ == "__main__":
    sys.exit(main())
