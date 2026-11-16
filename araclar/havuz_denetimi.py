"""Havuz denetimi (yalnız okur): havuzdaki her evi bugünkü kodla yeniden kurar ve havuz hakeminin (`araclar/havuz_hakemi.py`)
bakmadığı kalemleri denetler. Hiçbir dosyayı değiştirmez, kayda yazmaz; sonucu JSON ve Markdown tablo olarak verir.

Neden (Lokman, 16 Kasım 2026 07:05:58 ve 07:07:03): "hepsinin kontrolleri yapılsın öyle girsin havuza hata olmasın", "kontrolcü her
yaptığımı ... kontrolleri yapsın öyle alsın havuza". Havuz hakemi bugün plan kimliğine bakar (dış ölçü, brüt, oda programı, pencere, kapı,
açık mahal, kat); kayıt aracı (`aday_kaydet.py`) ek olarak Motor doğrulamasının geçmesini ister. Aşağıdaki kalemler havuza girişte bugün
denetlenmiyordu; bu araç onları raporlar. Kayıt kapısı (D-112, Lokman 16 Kasım 2026 08:07:06 kartı "Evet, hatalı yeni ev girmesin"):
`aday_kaydet.py` ve `cati_varyanti_kaydet.py` havuza yeni ev yazmadan `kayit_kapisi`'nı koşar; hata sınıfındaki kalem kaydı durdurur.

Kalemler:
  HD-01  Motor kurar, çizim doğrulaması geçer                                  (hata)
  HD-02  Motor uyarısı yok (çatı, veranda, köşe, pano, pencere)                (uyarı: her biri ya düzelir ya Lokman'ın sözüyle kalır)
  HD-03  Yükleme listesi yazılır                                               (hata)
  HD-04  Listede adetsiz ya da "Kural yok" satırı yok                          (hata)
  HD-05  3D model (IFC) kurulur: canlıda kurulamazsa bayiye 3D sayfası gitmez  (hata)
  HD-06  3D modelde makas yeri uyarısı yok                                     (uyarı)
  HD-08  3D modeldeki makas sayısı her çatı parçasında listedekiyle aynı (kart modeli ve montaj rehberi makas yerini 3D'den okur)  (hata)
  HD-09  Listede makası olan her çatı parçası 3D modelde de makaslı                (uyarı)
  HD-10  3D modelin ana çatısı İş Emri'nin çatı biçiminde (kırma çatı 3D'de kırma) (hata)
  HD-07  Makas sayısı gerçek projenin kartıyla (yalnız --kart-klasoru verilirse; fark D-44 gibi bilinen bir kuraldan olabilir)  (bilgi)
  HD-11  Çelik: havuz evi standart çatı kaplamasıyla çizilir (kitabın baz paketi, tek kat panel; Lokman 16 Kasım 2026 08:27:26 kartı
         "Standart: tek kat panel": havuzdaki her çelik ev tek kat panelle çizilir, bayi kaplamayı formda seçer)   (uyarı)
  HD-12  Prefabrik: makas aksı kaymaz; saçak duvarlarının pano ekleri tek 62,75'lik ızgarada (D-121, Lokman 16 Kasım 2026 20:56:44
         "makas yönündeki akslar çok önemli makasları o akslara oturtuyoruz", kart 21:14:20 "Okuma 1"; `G.makas_aksi_denetimi`)   (uyarı)

Kullanım:
  python -m araclar.havuz_denetimi [--kart-klasoru <Proje_Karti>] [--json <çıktı.json>] [--md <çıktı.md>]
  python -m araclar.havuz_denetimi --is-emri <İş Emri.json> ... [--kart AP-NN ...]     # havuza girmemiş prefabrik ev
  python -m araclar.havuz_denetimi --tanim <Yapı Tanımı.json> ...                       # havuza girmemiş çelik ev
Kodu yoksa (--is-emri / --tanim) havuzdaki bütün geçerli evler denetlenir (prefabrik: `adaylar_prefabrik.json`, `havuz/PA*.json`,
çatı varyantları; çelik: `adaylar.json`, `havuz/KT*.json`, bankanın kabul modelleri). Çıkış kodu: 0 hata yok, 1 en az bir evde hata.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "beyin" / "veri"

KALEMLER = {
    "HD-01": "Motor kurar, çizim doğrulaması geçer",
    "HD-02": "Motor uyarısı yok",
    "HD-03": "Yükleme listesi yazılır",
    "HD-04": "Listede adetsiz ya da \"Kural yok\" satırı yok",
    "HD-05": "3D model (IFC) kurulur",
    "HD-06": "3D modelde makas yeri uyarısı yok",
    "HD-08": "3D'deki makas sayısı listedekiyle aynı",
    "HD-09": "Listedeki her makaslı çatı parçası 3D'de de makaslı",
    "HD-10": "3D'deki ana çatı İş Emri'nin çatı biçiminde",
    "HD-07": "Makas sayısı gerçek projenin kartıyla",
    "HD-11": "Çelik ev standart çatı kaplamasıyla",
    "HD-12": "Makas aksı kaymaz (saçak duvarında ek tam ya da yarım aksta)",
}
SINIF = {"HD-01": "hata", "HD-02": "uyari", "HD-03": "hata", "HD-04": "hata", "HD-05": "hata", "HD-06": "uyari", "HD-08": "hata", "HD-09": "uyari", "HD-10": "hata", "HD-07": "bilgi", "HD-11": "uyari", "HD-12": "uyari"}
# Motor'a göre denetlenen kalemler; tablo ötekilere "–" yazar.
DENETLENEN = {"prefabrik": {"HD-01", "HD-02", "HD-03", "HD-04", "HD-05", "HD-06", "HD-07", "HD-08", "HD-09", "HD-10", "HD-12"},
              "genel": {"HD-01", "HD-02", "HD-03", "HD-04", "HD-05", "HD-11"}}


# ---------------------------------------------------------------- havuz

def _kart_kodu(kayit: dict) -> str | None:
    """Gerçek projenin kart kodu (AP-NN): havuz kaydının kart kıyası, yoksa kaynak dosyasının adı (testler/cizim/evler/AP15.json)."""
    kk = ((kayit.get("kaynak") or {}).get("kart_kiyasi") or {}).get("kart")
    if kk:
        return kk
    m = re.search(r"AP(\d\d)", str((kayit.get("kaynak") or {}).get("dosya") or ""))
    return f"AP-{m.group(1)}" if m else None


def havuz_evleri(kok: Path = KOK) -> list[dict]:
    """Havuzdaki geçerli evler: {kod, gosterim, motor (prefabrik | genel), yol, m2, oda, kart}."""
    veri = kok / "beyin" / "veri"
    out = []

    def ekle(k: dict, motor: str, yol: Path, kart: str | None):
        if k.get("durum", "gecerli") != "gecerli":
            return
        out.append({"kod": k["kod"], "gosterim": k.get("gosterim") or k["kod"], "motor": motor, "yol": str(yol),
                    "m2": k.get("katalog_m2"), "oda": k.get("oda_programi"), "kart": kart})

    for k in json.loads((veri / "adaylar_prefabrik.json").read_text(encoding="utf-8")):
        ekle(k, "prefabrik", kok / "is_emri" / k["sablon"], _kart_kodu(k))
    for f in sorted((veri / "cati_varyantlari").glob("*.json")):
        for k in json.loads(f.read_text(encoding="utf-8")).get("varyantlar") or []:
            ekle(k, "prefabrik", kok / "is_emri" / k["sablon"], None)
    for f in sorted((veri / "havuz").glob("PA*.json")):
        k = json.loads(f.read_text(encoding="utf-8"))
        ekle(k, "prefabrik", kok / "is_emri" / k["sablon"], _kart_kodu(k))
    for k in json.loads((veri / "adaylar.json").read_text(encoding="utf-8")):
        ekle(k, "genel", kok / k["tanim"], None)
    for f in sorted((veri / "havuz").glob("KT*.json")):
        k = json.loads(f.read_text(encoding="utf-8"))
        ekle(k, "genel", kok / k["tanim"], None)
    banka = kok / "modeller" / "banka"
    for kf in sorted(banka.glob("*/kart.json")):
        k = json.loads(kf.read_text(encoding="utf-8"))
        if k.get("durum") == "kabul" and (kf.parent / "tanim.json").exists():
            t = json.loads((kf.parent / "tanim.json").read_text(encoding="utf-8"))
            out.append({"kod": k.get("kod") or kf.parent.name, "gosterim": k.get("kod") or kf.parent.name, "motor": "genel",
                        "yol": str(kf.parent / "tanim.json"), "m2": (t.get("bilgi") or {}).get("m2") or k.get("m2"),
                        "oda": k.get("oda_programi"), "kart": None})
    return out


# ---------------------------------------------------------------- yardımcılar

def _b(kalem: str, metin: str) -> dict:
    return {"kalem": kalem, "sinif": SINIF[kalem], "metin": metin}


def cati_yazisi(ie: dict) -> str:
    """İş Emri'nin çatısı tek satırda (tip, cumbalar, mahal çatıları, taşan verandalar, kubbe, girinti)."""
    c = ie.get("cati") or {}
    p = [c.get("tip", "besik")]
    for u in c.get("cumbalar") or []:
        p.append("cumba" + (f" (veranda {u['veranda']})" if u.get("veranda") else
                            (f" (çıkıntı {u['cikinti_cm']})" if u.get("cikinti_cm") else "")))
    for m in c.get("mahal_catilari") or []:
        p.append(f"{m.get('mahal')}: {m.get('tip')}")
    for v in ie.get("verandalar") or []:
        p.append(f"taşan veranda {v.get('ad')}: {(v.get('cati') or {}).get('tip') or 'İş Emri yazmıyor'}")
    if ie.get("kubbeler"):
        p.append(f"kubbe × {len(ie['kubbeler'])}")
    if ie.get("girintiler"):
        p.append("girintili gövde")
    return " + ".join(p)


def makas_satirlari(satirlar: list[dict]) -> list[dict]:
    """Yükleme listesinin makas satırları (1005 grubu; "makas arası" çatı paneli makas değildir)."""
    return [s for s in satirlar if s.get("grup") == "1005" and "makas" in str(s.get("kalem", "")).lower()
            and "makas arası" not in str(s.get("kalem", "")).lower()]


def makas_sayisi(satirlar: list[dict]) -> int | None:
    """Yükleme listesindeki makas adedi."""
    n = [s.get("adet") for s in makas_satirlari(satirlar)]
    return int(sum(a for a in n if isinstance(a, (int, float)))) if n else None


def parca_makaslari(satirlar: list[dict]) -> dict[str, int]:
    """Listedeki makas adedi çatı parçası başına: "Makas (orta) · ana çatı" → {"ana çatı": …}. Kubbe makasının satırında parça eki yok
    ("Kubbe makası"): parçası "kubbe" (3D'de `uret()["kubbe"]`, BK-46)."""
    out: dict[str, int] = {}
    for s in makas_satirlari(satirlar):
        kalem = str(s.get("kalem", ""))
        parca = kalem.split(" · ")[-1].strip().lower() if " · " in kalem else "kubbe" if kalem.startswith("Kubbe makası") else "?"
        if isinstance(s.get("adet"), (int, float)):
            out[parca] = out.get(parca, 0) + int(s["adet"])
    return out


def kart_oku(kart_klasoru: Path | None, kart: str | None) -> dict | None:
    if not (kart_klasoru and kart):
        return None
    f = kart_klasoru / kart / "kart.json"
    if not f.exists():
        return None
    K = json.loads(f.read_text(encoding="utf-8"))
    c = K.get("cati") or {}
    return {"sekil": c.get("sekil"), "makas": c.get("makas_adedi")}


# ---------------------------------------------------------------- prefabrik

def denetle_prefabrik(ie: dict, kart: dict | None = None) -> dict:
    from motor import dxf_out, geometry as G, ifc_uret, prefabrik_liste as PL

    r = {"cati": cati_yazisi(ie), "bulgular": []}
    B = r["bulgular"]
    kopya = lambda: json.loads(json.dumps(ie))                          # noqa: E731 — her adım kendi kopyasıyla (Motor girdiyi değiştirir)
    try:
        plan = G.kur(kopya())
        for u in plan.uyarilar:
            B.append(_b("HD-02", u))
        for u in G.makas_aksi_denetimi(plan, (ie.get("cati") or {}).get("makas_ekseni", "x"), (ie.get("cati") or {}).get("tip")):   # D-121
            B.append(_b("HD-12", u))
    except Exception as e:                                               # IsEmriHatasi dahil: ev kurulamıyor
        B.append(_b("HD-01", f"Motor kuramadı: {type(e).__name__}: {e}"))
        return r
    with tempfile.TemporaryDirectory() as t:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                dxf_out.uret(kopya(), Path(t))
            v = json.loads((Path(t) / "validation.json").read_text(encoding="utf-8"))
            if not v.get("passed"):
                B.append(_b("HD-01", "çizim doğrulaması geçmedi: " + "; ".join(map(str, v.get("errors") or []))[:400]))
        except Exception as e:
            B.append(_b("HD-01", f"çizim üretilemedi: {type(e).__name__}: {e}"))
        sat: list[dict] = []
        try:
            L = PL.is_emrinden(kopya())
            sat = L.get("satirlar") or []
            for s in sat:
                if s.get("adet") in (None, "") or "kural yok" in str(s.get("dayanak", "")).lower():
                    B.append(_b("HD-04", f"{s.get('kalem')} · {s.get('olcu') or ''}: {s.get('dayanak') or 'adet yok'}"))
            r["makas"] = makas_sayisi(sat)
            r["makas_parca"] = parca_makaslari(sat)
        except PL.ListeYazilmaz as e:
            B.append(_b("HD-03", f"liste yazılmaz: {e.neden}"))
        except Exception as e:
            B.append(_b("HD-03", f"liste hatası: {type(e).__name__}: {e}"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                oz = ifc_uret.uret(kopya(), Path(t) / "model.ifc")
            cati = (oz or {}).get("cati") or {}
            tip = (ie.get("cati") or {}).get("tip", "besik")
            if tip == "kirma":                                           # 3D sayfası IFC'den (İE-21): bayi çatıyı orada görür
                import ifcopenshell
                cesit = sorted({str(x.PredefinedType) for x in ifcopenshell.open(str(Path(t) / "model.ifc")).by_type("IfcRoof")})
                if "HIP_ROOF" not in cesit:
                    B.append(_b("HD-10", f"İş Emri'nde kırma çatı; 3D modelin çatısı {', '.join(cesit) or 'yok'} (beşik çiziliyor)"))
            if cati.get("uyari"):
                B.append(_b("HD-06", str(cati["uyari"])))
            kubbe = sum(int(k.get("makas") or 0) for k in (oz or {}).get("kubbe") or [])   # BK-46: kubbe makası çatının özetinde değil
            n3 = len(cati["makaslar"]) if cati.get("makaslar") else cati.get("makas")
            r["makas_3d"] = (n3 or 0) + kubbe if (n3 is not None or kubbe) else None
            uc: dict[str, int] = {}
            for m in cati.get("makaslar") or []:
                k = str(m.get("parca") or "?").strip().lower()
                uc[k] = uc.get(k, 0) + 1
            ozet_yolu = not cati.get("makaslar") and cati.get("makas") is not None
            if ozet_yolu:                                                # parça kırılımı olmayan özet (makaslar y'yi geçer ya da kırma)
                uc = {"ana çatı": int(cati["makas"])}
            if kubbe:
                uc["kubbe"] = kubbe
            r["makas_3d_parca"] = uc
            liste_p = r.get("makas_parca") or {}
            for parca in sorted(set(liste_p) | set(uc)):
                a, b = liste_p.get(parca), uc.get(parca)
                if a is not None and b is not None and a != b:
                    kirilim = "; ".join(f"{x['kalem'].split(' · ')[0]} {x['adet']}" for x in makas_satirlari(sat)
                                        if str(x.get("kalem", "")).lower().endswith(parca)) if ozet_yolu else ""
                    B.append(_b("HD-08", f"{parca}: 3D modelde {b} makas, yükleme listesinde {a}" + (f" ({kirilim})" if kirilim else "")))
                elif a and b is None:
                    B.append(_b("HD-09", f"{parca}: listede {a} makas, 3D modelde bu parçanın makası yok"))
                elif b and a is None and liste_p:
                    B.append(_b("HD-08", f"{parca}: 3D modelde {b} makas, yükleme listesinde bu parça yok"))
        except Exception as e:
            B.append(_b("HD-05", f"3D kurulamadı: {type(e).__name__}: {str(e)[:300]}"))
    if kart:
        r["kart"] = kart
        if kart.get("makas") is not None and r.get("makas") is not None and kart["makas"] != r["makas"]:
            B.append(_b("HD-07", f"makas: liste {r['makas']}, gerçek proje {kart['makas']} (kart çatısı: {kart.get('sekil')})"))
    return r


# ---------------------------------------------------------------- çelik (genel motor)

def denetle_genel(tanim: Path) -> dict:
    from motor.genel import uret as U

    t = json.loads(tanim.read_text(encoding="utf-8"))
    r = {"cati": (t.get("cati") or {}).get("tip"), "bulgular": []}
    B = r["bulgular"]
    with tempfile.TemporaryDirectory() as h:
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                U.uret(tanim, Path(h), perspektif=False)
        except BaseException as e:                                       # SystemExit dahil
            B.append(_b("HD-01", f"genel motor üretemedi: {type(e).__name__}: {str(e)[:300]}"))
            return r
        v = json.loads((Path(h) / "validation.json").read_text(encoding="utf-8"))
        if not v.get("passed"):
            B.append(_b("HD-01", "çizim doğrulaması geçmedi: " + "; ".join(map(str, v.get("errors") or []))[:400]))
        log = (Path(h) / "uret.log").read_text(encoding="utf-8") if (Path(h) / "uret.log").exists() else ""
        for satir in log.splitlines():
            s = satir.strip()
            if s.startswith("UYARI"):
                B.append(_b("HD-02", s))
        listeler = list(Path(h).glob("*_yukleme.json"))
        if not listeler:
            B.append(_b("HD-03", "yükleme listesi yazılmadı"))
        for f in listeler:
            L = json.loads(f.read_text(encoding="utf-8"))
            for s in L.get("satirlar") or []:
                if s.get("adet") in (None, ""):
                    B.append(_b("HD-04", f"{s.get('kalem') or s.get('ad')}: adet yok"))
        if not any(Path(h).glob("*.ifc")):
            B.append(_b("HD-05", "3D model (IFC) yazılmadı"))
    B.extend(kaplama_bulgusu(t))
    return r


def kaplama_bulgusu(t: dict) -> list[dict]:
    """HD-11: bayiye çizilen çatı kaplaması (`cati.kaplama`, yoksa kitabın baz paketi) havuzun standardı mı (Lokman, 16 Kasım 2026
    08:27:26 kartı "Standart: tek kat panel"). D-113'ten (BK-48) beri tanım dosyası asıl projedir ve değişmez; yeni projenin zarfına konan
    `standart_kaplama` işlemi (`varyant.standart_kaplama_islemi`) uygulanmış tanım denetlenir. Gerçek projenin kaplaması bilgi olarak yazılır."""
    from beyin import varyant
    from motor.genel.girdi_genel import KAPLAMA_ADI
    baz = json.loads((KOK / "kurallar" / "liste" / "kurallar.json").read_text(encoding="utf-8"))["baz_paket_cati_kaplamasi"]["deger"]
    for op in varyant.standart_kaplama_islemi(t):
        t = varyant.tanim_uygula(t, op)
    tanim = (t.get("cati") or {}).get("kaplama") or baz
    if tanim == baz:
        return []
    gercek = (t.get("teknik_ozellikler") or {}).get("Çatı kaplaması")
    return [_b("HD-11", f"tanım {KAPLAMA_ADI.get(tanim, tanim)} çiziyor; havuz standardı {KAPLAMA_ADI.get(baz, baz)}"
                        + (f" (gerçek projede \"{gercek}\")" if gercek else ""))]


# ---------------------------------------------------------------- kayıt kapısı (D-112)

def havuza_mi(havuz: bool, durum: str, test_dosyasi: bool = False) -> bool:
    """Kayıt bayiye giden havuza mı yazılıyor (D-112): `--havuz` ya da durum gecerli / kosullu; test kaydı değil."""
    return (havuz or durum in ("gecerli", "kosullu")) and not test_dosyasi


def kayit_kapisi(r: dict) -> tuple[list[str], list[str]]:
    """D-112 (Lokman, 16 Kasım 2026 08:07:06 kartı "Evet, hatalı yeni ev girmesin"): (kaydı durduran hata bulguları, kayda yazılan
    uyarılar). Hata sınıfı: HD-01, HD-03, HD-04, HD-05, HD-08, HD-10; uyarı: HD-02, HD-06, HD-09, HD-11, HD-12; bilgi (HD-07) kapıya girmez."""
    dur = [f"{b['kalem']} {KALEMLER[b['kalem']]}: {b['metin']}" for b in r["bulgular"] if b["sinif"] == "hata"]
    uyari = [f"{b['kalem']}: {b['metin']}" for b in r["bulgular"] if b["sinif"] == "uyari"]
    return dur, uyari


# ---------------------------------------------------------------- rapor

def isaret(bulgular: list[dict], kalem: str) -> str:
    b = [x for x in bulgular if x["kalem"] == kalem]
    if not b:
        return "✓"
    return {"hata": "✗", "uyari": "!", "bilgi": "≠"}[b[0]["sinif"]] + (f" {len(b)}" if len(b) > 1 else "")


def _denetlendi(r: dict, kalem: str) -> bool:
    if kalem == "HD-07" and not r.get("kart"):
        return False
    return kalem in DENETLENEN.get(r.get("motor") or "prefabrik", DENETLENEN["prefabrik"])


def markdown(sonuc: dict) -> str:
    kal = list(KALEMLER)
    sat = ["| Ev | m² | Oda | Çatı | " + " | ".join(kal) + " |", "|" + "---|" * (4 + len(kal))]
    for kod, r in sonuc.items():
        sat.append(f"| {r.get('gosterim', kod)} | {r.get('m2') or ''} | {r.get('oda') or ''} | {r.get('cati') or ''} | "
                   + " | ".join(isaret(r["bulgular"], k) if _denetlendi(r, k) else "–" for k in kal) + " |")
    ayrinti = []
    for kod, r in sonuc.items():
        for b in r["bulgular"]:
            ayrinti.append(f"- **{r.get('gosterim', kod)}** · {b['kalem']} ({b['sinif']}): {b['metin']}")
    acik = "\n".join(f"- {k}: {v} ({SINIF[k]})" for k, v in KALEMLER.items())
    return ("İşaret: ✓ temiz · ✗ hata · ! uyarı · ≠ gerçek projeyle fark · – denetlenmedi (kart yok ya da o Motor'da yok).\n\n" + acik + "\n\n" + "\n".join(sat)
            + "\n\n### Bulgular\n\n" + ("\n".join(ayrinti) or "Bulgu yok."))


def _ev_denetle(is_: tuple[dict, Path | None]) -> dict:
    """Bir ev (süreç havuzunda da koşar): Motor'a göre denetler, kaydın kimlik alanlarını ekler."""
    e, kart_klasoru = is_
    if str(KOK) not in sys.path:
        sys.path.insert(0, str(KOK))
    yol = Path(e["yol"])
    if e["motor"] == "prefabrik":
        r = denetle_prefabrik(json.loads(yol.read_text(encoding="utf-8")), kart_oku(kart_klasoru, e.get("kart")))
    else:
        r = denetle_genel(yol)
    r.update({k: e.get(k) for k in ("gosterim", "m2", "oda", "motor", "yol")})
    r["kart_kodu"] = e.get("kart")
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--is-emri", nargs="*", default=[], help="havuza girmemiş prefabrik İş Emri(leri)")
    ap.add_argument("--kart", nargs="*", default=[], help="--is-emri sırasıyla gerçek projenin kart kodu (AP-NN)")
    ap.add_argument("--tanim", nargs="*", default=[], help="havuza girmemiş çelik Yapı Tanımı(ları)")
    ap.add_argument("--kart-klasoru", type=Path, help="proje kartları (…/Proje_Karti); verilirse HD-07 denetlenir")
    ap.add_argument("--yalniz", nargs="*", default=[], help="yalnız bu havuz kodları (ör. PA16 KT07)")
    ap.add_argument("--json", type=Path, help="sonucu JSON olarak yaz")
    ap.add_argument("--md", type=Path, help="sonucu Markdown tablo olarak yaz")
    ap.add_argument("--is", type=int, default=1, dest="isci", help="aynı anda kaç ev (ayrı süreçler; varsayılan 1)")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(KOK))

    if a.is_emri or a.tanim:
        evler = [{"kod": Path(p).stem, "motor": "prefabrik", "yol": p, "kart": (a.kart[i] if i < len(a.kart) else None)}
                 for i, p in enumerate(a.is_emri)]
        evler += [{"kod": Path(p).stem, "motor": "genel", "yol": p, "kart": None} for p in a.tanim]
    else:
        evler = havuz_evleri()
        if a.yalniz:
            evler = [e for e in evler if e["kod"] in a.yalniz]

    isler = [(e, a.kart_klasoru) for e in evler]
    sonuc = {}
    if a.isci > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(a.isci) as ex:
            sonuclar = list(ex.map(_ev_denetle, isler))
    else:
        sonuclar = map(_ev_denetle, isler)
    for e, r in zip(evler, sonuclar):
        sonuc[e["kod"]] = r
        sinif = sorted({b["sinif"] for b in r["bulgular"]})
        print(f"{e.get('gosterim') or e['kod']:<10} {', '.join(sinif) or 'temiz'}", flush=True)

    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.md:
        a.md.write_text(markdown(sonuc) + "\n", encoding="utf-8")
    n_hata = sum(1 for r in sonuc.values() if any(b["sinif"] == "hata" for b in r["bulgular"]))
    print(f"== {len(sonuc)} ev; hatalı {n_hata}; uyarılı "
          f"{sum(1 for r in sonuc.values() if any(b['sinif'] == 'uyari' for b in r['bulgular']))}", flush=True)
    return 1 if n_hata else 0


if __name__ == "__main__":
    sys.exit(main())
