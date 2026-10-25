"""Çelik hakemi (İE-16 PR-1, D-25): mühürlü gerçek yükleme listesini ve montaj paftasını okur, kendi listemizle kıyaslar.

Sıra her koşuda aynı; bir adım tutmazsa araç `Durdu` ile durur ve sonrakine geçmez (prefabrik kör testinin sırası, BK-12 PR-3):

1. **Kendi listemiz kayıtlı mı?** `bizim_liste.json` depoda commit'li ve çalışma ağacında değişmemiş (yalnız `kiyas`): gerçek liste
   okunmadan önce bizim yanımız sabittir.
2. **Mühür tutuyor mu?** `testler/celik/muhur.json` depoda commit'li ve değişmemiş; dosyanın baytı ve SHA-256'sı bu projenin bir kaydıyla
   aynı. Kayıtta SHA yoksa (ilk indirmede alınır) `ilk_indirmeler`'de bu dosyanın kaydı olmalı ve Drive saati mühürdekiyle aynı olmalı.
   Tutmazsa dosyanın içeriği okunmaz (yalnız bayt sayısı ve özet alınır).
3. **Açılabilir mi?** Liste kaydı `acik` olmalı. `kor` ya da `kapali` kayıt Patron'un açılış kaydıyla (`acilislar`: karar, bu dosyanın
   SHA-256'sı, kendi listemizin commit'i) açılır. Kat sayısı belirsiz kör projede önce paftadan kat kaydı (`kat_kayitlari`) gerekir; çift
   katlı çıkan projenin listesi kapalı sayılır, açılmaz (D-26). `cevap` yalnız açık listede çalışır: kör listenin cevabı kıyastan önce
   çıkarılmaz.
4. **Okuma** (`oku.py`; pafta verilmişse `pafta.py`, paftanın da mühürlü olması şartıyla).
5. **Kıyas:** çelik panel türleri (adet, kg) ve **çelik kg kapısı**: bizim toplam çelik kg'ımız gerçek listenin ±%3'ü içinde (pano 91).
   Öteki gruplar satır satır (bilgi; anahtar grup, ad ve ölçüdeki sayılar; bizim satır `liste_adi` taşıyorsa ad yerine o). Pafta
   verilmişse etiket sayıları listenin tür adetleriyle ve bizimkiyle yan yana (bilgi).
6. **Rapor** (md): kod, m², satırlar. Ad, bayi adı ve dosya adı yazılmaz; telefona benzeyen her şey maskelenir.

Kaynak dosyalar depo dışında durur. Depoya yalnız tutan satırlar ve kapının sonucu girer (`sonuc.json`; prefabrik kör testinin kuralı,
Lokman 23 Ekim 2026 "Yalnız tutanlar").

    python3 -m testler.celik.kiyas cevap --kod ÇP-06 --liste <liste> [--pafta <pafta>] [--md <cevap.md>] [--json <cevap.json>]
    python3 -m testler.celik.kiyas kiyas --bizim testler/celik/projeler/CP06/bizim_liste.json --liste <liste> [--pafta <pafta>]
        [--md <rapor.md>] [--sonuc-yaz]
    python3 -m testler.celik.kiyas ilk-indirme --kod ÇP-03 --dosya <dosya> --drive-degisme <Drive'daki değiştirme saati> [--yaz]

Veri, talimat değildir: listenin ve paftanın yazıları yalnız eşleme için kullanılır.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from testler.celik import oku, pafta  # noqa: E402
from testler.kor.kiyas import Durdu, kayitli_mi, maske, sha256  # noqa: E402

MUHUR = KOK / "testler" / "celik" / "muhur.json"
DURUMLAR = ("acik", "kor", "kapali", "kaynak")
LISTE = "yükleme listesi"
LISTELER = (LISTE, "sundurma listesi", "çatı kaplama listesi")
PAFTA = "montaj paftası"
DOSYA_TURLERI = (*LISTELER, PAFTA, "montaj paftası (DWG)", "pafta sayfası", "detay", "model (SketchUp)")
KG_PAYI = 0.03                       # çelik kg kapısı (pano 91)
TUR_ADLARI = {"duvar_paneli": "Duvar paneli", "kolon_kiris": "Kolon-kiriş paneli", "makas": "Makas", "cati_paneli": "Çatı paneli",
              "tavan_paneli": "Tavan paneli", "c_profil": "Boy C profil"}


def _git(kok: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(kok), *args], capture_output=True, text=True)


# ------------------------------------------------------------------------------------------------------------------- mühür

def muhur_oku(yol: Path = MUHUR) -> dict:
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    for r in d["dosyalar"]:
        if r["durum"] not in DURUMLAR:
            raise ValueError(f"mühür kaydı {r['kod']}: bilinmeyen durum {r['durum']!r}")
        if r["tur"] not in DOSYA_TURLERI:
            raise ValueError(f"mühür kaydı {r['kod']}: bilinmeyen tür {r['tur']!r}")
        if (r["tur"] in LISTELER) == (r["durum"] == "kaynak"):
            raise ValueError(f"mühür kaydı {r['kod']} {r['drive_id']}: liste kaynak olamaz, liste olmayan kaynaktır")
    return d


def kayit_ozeti(r: dict, muhur: dict) -> str | None:
    """Kaydın SHA-256'sı: mühürde yoksa ilk indirme kaydından."""
    return r.get("sha256") or (muhur.get("ilk_indirmeler", {}).get(r["drive_id"]) or {}).get("sha256")


def muhur_denetle(dosya: Path, muhur: dict, kod: str, turler=(LISTE,)) -> dict:
    """Adım 2: dosyanın baytı ve özeti bu projenin bir kaydıyla aynı mı. İçerik okunmaz."""
    dosya = Path(dosya)
    if not dosya.is_file():
        raise Durdu(2, "dosya yok")
    bayt = dosya.stat().st_size
    if bayt == 0:
        raise Durdu(2, "dosya boş: mühür tutmuyor, dosya okunmadı")
    ozet = sha256(dosya)
    kayit = next((r for r in muhur["dosyalar"] if kayit_ozeti(r, muhur) == ozet), None)
    if kayit is None:
        bos = [r for r in muhur["dosyalar"] if r["kod"] == kod and r["bayt"] == bayt and not kayit_ozeti(r, muhur)]
        if bos:
            raise Durdu(2, f"{kod} kaydının SHA-256'sı ilk indirmede alınır ve henüz yok: önce `ilk-indirme` kaydı ayrı commit'le "
                           f"`ilk_indirmeler`'e yazılmalı ({bayt} bayt); dosya okunmadı")
        raise Durdu(2, f"mühür tutmuyor: SHA-256 {ozet[:12]}… ({bayt} bayt) hiçbir kayıtta yok; dosya okunmadı")
    if kayit["bayt"] != bayt:
        raise Durdu(2, f"mühür tutmuyor: bayt {bayt}, kayıtta {kayit['bayt']}; dosya okunmadı")
    if kayit["kod"] != kod:
        raise Durdu(2, f"mühür kaydı {kayit['kod']} için; proje {kod} değil; dosya okunmadı")
    ilk = muhur.get("ilk_indirmeler", {}).get(kayit["drive_id"])
    if not kayit.get("sha256") and ilk and ilk.get("drive_degisme") != kayit["drive_degisme"]:
        raise Durdu(2, f"ilk indirmedeki Drive saati ({ilk.get('drive_degisme')}) mühürdekinden ({kayit['drive_degisme']}) farklı: "
                       "dosya mühürden sonra değişmiş; dosya okunmadı")
    if kayit["tur"] not in turler:
        raise Durdu(2, f"dosya {kayit['tur']}; bu adımda {' / '.join(turler)} okunur")
    return kayit


def acilabilir_mi(kayit: dict, muhur: dict, kod: str, liste: dict | None) -> dict:
    """Adım 3: liste kaydı açık mı; kör ya da kapalıysa Patron'un açılış kaydı bu dosyanın özetini ve kendi listemizin commit'ini taşıyor mu;
    kör projenin kat sayısı belirsizse kat kaydı var mı, çift değil mi. `liste` None ise (cevap) yalnız açık kayıt açılır."""
    durum = kayit["durum"]
    acilis = muhur.get("acilislar", {}).get(kod)
    if durum == "acik":
        return {"durum": durum, **(acilis or {})}
    if durum in ("kor", "kapali"):
        ad = "kör" if durum == "kor" else "kapalı"
        if liste is None:
            raise Durdu(3, f"{kod} listesi {ad}: cevabı kıyastan önce çıkarılmaz; liste açılmaz")
        if durum == "kor":
            kat = muhur["projeler"][kod]["kat"]
            if kat == "belirsiz":
                kat = ((muhur.get("kat_kayitlari") or {}).get(kod) or {}).get("kat")
                if kat not in ("tek", "çift"):
                    raise Durdu(3, f"{kod} kat sayısı belirsiz: önce paftadan kat kaydı `kat_kayitlari`'na ayrı commit'le yazılmalı; "
                                   "liste açılmaz")
            if kat == "çift":
                raise Durdu(3, f"{kod} çift katlı: liste kapalı sayılır (D-26); liste açılmaz")
        if not acilis or not str(acilis.get("karar") or "").strip():
            raise Durdu(3, f"{kod} listesi {ad}: Patron'un açılış kaydı yok; liste açılmaz")
        if acilis.get("sha256") != kayit_ozeti(kayit, muhur):
            raise Durdu(3, f"{kod} açılış kaydı bu dosya için değil (SHA-256 {str(acilis.get('sha256') or 'yok')[:12]}…); liste açılmaz")
        c = str(acilis.get("liste_commit") or "")
        if len(c) < 7 or not liste["commit"].startswith(c):
            raise Durdu(3, f"{kod} açılış kaydındaki liste commit'i ({c or 'yok'}) kendi listemizin commit'i değil "
                           f"({liste['commit'][:7]}); liste açılmaz")
        return {"durum": durum, **acilis}
    raise Durdu(3, f"kayıt durumu {durum}: liste değil")


def _oku(kayit: dict, dosya: Path, sayfa: int | None) -> tuple[dict, dict]:
    okunmayan = {"baslik": 0, "personel": 0, "adetli": 0}
    try:
        return oku.oku(Path(dosya), kayit["uzanti"], sayfa, okunmayan), okunmayan
    except oku.OkumaHatasi as e:
        raise Durdu(4, str(e)) from None


def _pafta(dosya: Path | None, muhur: dict, kod: str) -> tuple[dict | None, dict | None]:
    if dosya is None:
        return None, None
    kayit = muhur_denetle(dosya, muhur, kod, turler=(PAFTA,))
    return kayit, pafta.etiketler(Path(dosya))


# ------------------------------------------------------------------------------------------------------------------- kıyas

def bizim_celik(satirlar: list[dict]) -> dict:
    """Kendi listemizin çelik panel satırları türe ayrılmış: {tür: {adet, kg}}; kg'ı olmayan satır varsa kg None."""
    turler, eksik = {}, False
    for s in satirlar:
        if not oku.celik_grubu_mu(s.get("grup")):
            continue
        ad = s.get("malzeme") or s.get("kalem")
        if oku.katla(ad).startswith(oku.TOPLAM):
            continue
        t = oku.tur(ad)
        x = turler.setdefault(t, {"harf": oku.HARF[t], "adet": 0, "kg": 0.0})
        x["adet"] += s.get("adet") or 0
        if s.get("kg") is None:
            eksik = True
        else:
            x["kg"] = round(x["kg"] + s["kg"], 3)
    toplam_kg = None if eksik or not turler else round(sum(x["kg"] for x in turler.values()), 3)
    return {"turler": turler, "toplam": {"adet": sum(x["adet"] for x in turler.values()), "kg": toplam_kg}}


def kg_kapisi(bizim_kg, gercek_kg, pay: float = KG_PAYI) -> dict:
    if bizim_kg is None:
        return {"sonuc": "koşulmadı", "neden": "kendi listemizde çelik kg eksik"}
    if not gercek_kg:
        return {"sonuc": "koşulmadı", "neden": "gerçek listede çelik kg yok"}
    fark = (bizim_kg - gercek_kg) / gercek_kg
    return {"sonuc": "geçti" if abs(fark) <= pay + 1e-9 else "geçmedi", "fark_yuzde": round(100 * fark, 2), "pay_yuzde": 100 * pay}


def _olcu(t) -> tuple:
    return tuple(float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", str(t or "")))


def anahtar(grup, ad, boyut) -> tuple:
    g = re.sub(r"\bGRUBU\b", "", oku.katla(grup)).strip()
    a = re.sub(r"[^A-Z0-9]+", " ", oku.katla(ad)).strip()
    return (g, a, _olcu(boyut))


def satir_satir(bizim: list[dict], gercek: list[dict]) -> dict:
    """Çelik panel dışındaki gruplar: aynı anahtarda adet aynı mı (bilgi)."""
    B = {}
    for j, s in enumerate(bizim):
        if oku.celik_grubu_mu(s.get("grup")):
            continue
        k = anahtar(s.get("grup"), s.get("liste_adi") or s.get("malzeme") or s.get("kalem"), s.get("boyut", s.get("olcu")))
        B.setdefault(k, {"adet": 0, "satirlar": []})
        B[k]["adet"] += s.get("adet") or 0
        B[k]["satirlar"].append(j)
    G = {}
    for i, s in enumerate(gercek):
        if oku.celik_grubu_mu(s["grup"]):
            continue
        k = anahtar(s["grup"], s["malzeme"], s["boyut"])
        G.setdefault(k, {"adet": 0, "satirlar": []})
        G[k]["adet"] += oku.kor_oku.sayi(s["adet"]) or 0
        G[k]["satirlar"].append(i)
    out = []
    for k, g in G.items():
        b = B.get(k)
        sonuc = "bizde yok" if b is None else ("aynı" if b["adet"] == g["adet"] else "farklı")
        out.append({"anahtar": k, "gercek": g, "bizim": b, "sonuc": sonuc})
    fazla = [{"anahtar": k, "bizim": b} for k, b in B.items() if k not in G]
    sayilar = {x: sum(1 for o in out if o["sonuc"] == x) for x in ("aynı", "farklı", "bizde yok")}
    sayilar["bizde fazla"] = len(fazla)
    return {"satirlar": out, "fazla": fazla, "sayilar": sayilar}


def celik_tablosu(gercek: dict, bizim: dict | None, etiket: dict | None) -> list[dict]:
    turler = list(dict.fromkeys([*gercek["turler"], *((bizim or {}).get("turler") or {})]))
    out = []
    for t in sorted(turler, key=lambda t: list(TUR_ADLARI).index(t)):
        g = gercek["turler"].get(t)
        b = (bizim or {}).get("turler", {}).get(t)
        h = oku.HARF[t]
        e = ((etiket or {}).get("turler") or {}).get(h) if h else None
        out.append({"tur": t, "ad": TUR_ADLARI[t], "harf": h, "gercek_adet": g and g["adet"], "gercek_kg": g and g["kg"],
                    "bizim_adet": b and b["adet"], "bizim_kg": b and b["kg"], "pafta_etiket": e and e["adet"],
                    "pafta_liste": None if (etiket is None or not h) else ("aynı" if (e and e["adet"]) == (g and g["adet"]) else "farklı")})
    return out


def cevap(kod: str, liste: Path, pafta_yol: Path | None = None, *, kok: Path = KOK, muhur_yol: Path | None = None,
          sayfa: int | None = None) -> dict:
    """Açık listenin hakem cevabı: listedeki çelik panel türleri, adet ve kg; paftanın etiket sayıları; ikisinin sağlaması."""
    kok = Path(kok)
    muhur_yol = Path(muhur_yol) if muhur_yol else kok / "testler" / "celik" / "muhur.json"
    muhur_kaydi = kayitli_mi(muhur_yol, kok, 2)
    muhur = muhur_oku(muhur_yol)
    kayit = muhur_denetle(liste, muhur, kod)
    acilis = acilabilir_mi(kayit, muhur, kod, None)
    pk, etiket = _pafta(pafta_yol, muhur, kod)
    okunan, okunmayan = _oku(kayit, liste, sayfa)
    return {"kod": kod, "proje": muhur["projeler"][kod], "muhur": muhur_kaydi, "kayit": kayit, "ozet": kayit_ozeti(kayit, muhur),
            "acilis": acilis, "pafta_kaydi": pk, "pafta_ozet": pk and kayit_ozeti(pk, muhur),
            "celik": okunan["celik"], "etiket": etiket, "tablo": celik_tablosu(okunan["celik"], None, etiket),
            "grup_satirlari": dict(Counter(s["grup"] for s in okunan["satirlar"])), "okunmayan": okunmayan,
            "kiyas_commit": _git(kok, "rev-parse", "HEAD").stdout.strip()}


def kiyasla(bizim_yol: Path, liste: Path, pafta_yol: Path | None = None, *, kok: Path = KOK, muhur_yol: Path | None = None,
            sayfa: int | None = None) -> dict:
    kok, bizim_yol = Path(kok), Path(bizim_yol)
    muhur_yol = Path(muhur_yol) if muhur_yol else kok / "testler" / "celik" / "muhur.json"
    # 1. bizim yanımız
    liste_kaydi = kayitli_mi(bizim_yol, kok, 1)
    bizim = json.loads(bizim_yol.read_text(encoding="utf-8"))
    kod = bizim.get("kod")
    # 2. mühür
    muhur_kaydi = kayitli_mi(muhur_yol, kok, 2)
    muhur = muhur_oku(muhur_yol)
    if kod not in muhur["projeler"]:
        raise Durdu(1, f"kendi listemizin kodu ({kod}) mühürde yok")
    kayit = muhur_denetle(liste, muhur, kod)
    # 3. açılış
    acilis = acilabilir_mi(kayit, muhur, kod, liste_kaydi)
    pk, etiket = _pafta(pafta_yol, muhur, kod)
    # 4. okuma
    okunan, okunmayan = _oku(kayit, liste, sayfa)
    # 5. kıyas
    try:
        bc = bizim_celik(bizim["satirlar"])
    except oku.OkumaHatasi as e:
        raise Durdu(1, f"kendi listemiz: {e}") from None
    return {"kod": kod, "proje": muhur["projeler"][kod], "liste": liste_kaydi, "bizim": bizim, "muhur": muhur_kaydi, "kayit": kayit,
            "ozet": kayit_ozeti(kayit, muhur), "acilis": acilis, "pafta_kaydi": pk, "pafta_ozet": pk and kayit_ozeti(pk, muhur),
            "etiket": etiket, "celik": okunan["celik"], "bizim_celik": bc,
            "kapi": kg_kapisi(bc["toplam"]["kg"], okunan["celik"]["toplam"]["kg"]),
            "tablo": celik_tablosu(okunan["celik"], bc, etiket), "gercek": okunan["satirlar"], "okunmayan": okunmayan,
            "satir": satir_satir(bizim["satirlar"], okunan["satirlar"]), "kiyas_commit": _git(kok, "rev-parse", "HEAD").stdout.strip()}


def sonuc_kaydi(k: dict) -> dict:
    """Depoya giren sonuç: kapının sonucu, adedi tutan çelik türleri ve tutan satırlar (değerleri bizimkidir)."""
    return {
        "aciklama": ("Çelik hakeminin sonucu (İE-16). Yalnız tutanlar: çelik kg kapısının sonucu ve farkı, adedi tutan çelik türleri ve "
                     "adedi tutan öteki satırlar (anahtar ve bizim adedimiz). Tutmayan satırların gerçek değeri depoya girmez; sayilar "
                     "kıyasın özetidir."),
        "kod": k["kod"], "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "kiyas_commit": k["kiyas_commit"],
        "bizim_liste": {"yol": k["liste"]["yol"], "commit": k["liste"]["commit"]},
        "muhur": {"sha256": k["ozet"], "bayt": k["kayit"]["bayt"],
                  "durum": k["kayit"]["durum"], "muhur_commit": k["muhur"]["commit"]},
        "celik_kg_kapisi": k["kapi"],
        "celik_turleri_tutan": [{"tur": r["tur"], "adet": r["bizim_adet"]} for r in k["tablo"] if r["bizim_adet"] == r["gercek_adet"]],
        "sayilar": k["satir"]["sayilar"],
        "tutanlar": [{"grup": x["anahtar"][0], "ad": x["anahtar"][1], "olcu": list(x["anahtar"][2]), "adet": x["bizim"]["adet"]}
                     for x in k["satir"]["satirlar"] if x["sonuc"] == "aynı"],
    }


# ------------------------------------------------------------------------------------------------------------------- rapor

def _s(v) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).replace(".", ",") if isinstance(v, float) else str(v)


def _fark(b, g) -> str:
    if b is None or not g:
        return "—"
    return f"{100 * (b - g) / g:+.1f} %".replace(".", ",")


def _ust(k: dict) -> list[str]:
    P = k["proje"]
    L = ["| | |", "|---|---|", f"| Proje | {k['kod']} · {_s(P['m2'])} m² · {P['kat']} kat · durum {P['durum']} |",
         f"| Liste mührü | SHA-256 {k['ozet'][:12]}… · {k['kayit']['bayt']} bayt · "
         f"{k['kayit']['tur']} {k['kayit']['uzanti']} · durum {k['kayit']['durum']} · mühür commit {k['muhur']['commit'][:7]} |"]
    if k.get("pafta_kaydi"):
        L.append(f"| Pafta mührü | SHA-256 {k['pafta_ozet'][:12]}… · {k['pafta_kaydi']['bayt']} bayt · "
                 f"{k['etiket']['sayfa_sayisi']} sayfa |")
    o = k["okunmayan"]
    L.append(f"| Okunmayan satır (başlık etiketi, personel) | {o['baslik']} + {o['personel']} |")
    return L


def _celik_md(k: dict, bizimli: bool) -> list[str]:
    bas = "| Tür | Pafta harfi | Liste adet | Liste kg |" + (" Bizim adet | Bizim kg | kg farkı |" if bizimli else "") + \
          (" Pafta etiketi | Pafta–liste |" if k.get("etiket") else "")
    L = [bas, "|" + "---|" * (bas.count("|") - 1)]
    for r in k["tablo"]:
        h = [r["ad"], r["harf"] or "—", _s(r["gercek_adet"]), _s(r["gercek_kg"])]
        if bizimli:
            h += [_s(r["bizim_adet"]), _s(r["bizim_kg"]), _fark(r["bizim_kg"], r["gercek_kg"])]
        if k.get("etiket"):
            h += [_s(r["pafta_etiket"]), r["pafta_liste"] or "—"]
        L.append("| " + " | ".join(h) + " |")
    t = k["celik"]["toplam"]
    h = ["**Toplam**", "", f"**{_s(t['adet'])}**", f"**{_s(t['kg'])}**"]
    if bizimli:
        bt = k["bizim_celik"]["toplam"]
        h += [f"**{_s(bt['adet'])}**", f"**{_s(bt['kg'])}**", f"**{_fark(bt['kg'], t['kg'])}**"]
    if k.get("etiket"):
        h += ["", ""]
    L.append("| " + " | ".join(h) + " |")
    return L


def cevap_md(c: dict, yol: Path) -> None:
    L = [f"# Hakem cevabı · {c['kod']}", "",
         "Araç: `testler/celik/kiyas.py cevap` (İE-16 PR-1). Ad, bayi adı ve dosya adı yazılmaz; listenin başlık bloğu okunmadı.", ""]
    L += _ust(c) + ["", "## Çelik panel grubu (listeden) ve panel etiketleri (paftadan)", ""] + _celik_md(c, False)
    if c.get("etiket"):
        L += ["", f"Pafta uyarıları: {'; '.join(c['etiket']['uyarilar']) or 'yok'}."]
    L += ["", "## Listenin öteki grupları (satır sayısı; içerik bu sayfaya yazılmaz)", "", "| Grup | Satır |", "|---|---|"]
    L += [f"| {maske(g)} | {n} |" for g, n in c["grup_satirlari"].items() if not oku.celik_grubu_mu(g)]
    Path(yol).write_text("\n".join(L) + "\n", encoding="utf-8")


def cevap_json(c: dict) -> dict:
    return {"kod": c["kod"], "m2": c["proje"]["m2"], "liste_sha256": c["ozet"], "pafta_sha256": c["pafta_ozet"],
            "celik": {"satirlar": [{k: s[k] for k in ("tur", "harf", "boyut", "adet", "kg")} for s in c["celik"]["satirlar"]],
                      "turler": c["celik"]["turler"], "toplam": c["celik"]["toplam"]},
            "pafta": c["etiket"] and {h: {k: v for k, v in x.items()} for h, x in c["etiket"]["turler"].items()},
            "pafta_uyarilari": c["etiket"] and c["etiket"]["uyarilar"],
            "pafta_liste": {r["tur"]: r["pafta_liste"] for r in c["tablo"] if r["pafta_liste"]}}


def rapor_md(k: dict, yol: Path) -> None:
    kp = k["kapi"]
    kapi = (f"**{kp['sonuc']}** (fark {_s(kp['fark_yuzde'])} %, pay ±{_s(kp['pay_yuzde'])} %)" if "fark_yuzde" in kp
            else f"**{kp['sonuc']}** ({kp['neden']})")
    L = [f"# Çelik hakemi kıyası · {k['kod']}", "",
         "Araç: `testler/celik/kiyas.py kiyas` (İE-16 PR-1). Ad, bayi adı ve dosya adı yazılmaz; listenin başlık bloğu okunmadı.", ""]
    L += _ust(k) + [f"| Kendi listemiz | {k['liste']['yol']} · commit {k['liste']['commit'][:7]} ({k['liste']['tarih']}) |",
                    f"| Çelik kg kapısı | {kapi} |", "", "## Çelik panel grubu", ""] + _celik_md(k, True)
    s = k["satir"]["sayilar"]
    L += ["", f"## Öteki gruplar satır satır (bilgi): aynı {s['aynı']}, farklı {s['farklı']}, bizde yok {s['bizde yok']}, "
              f"bizde fazla {s['bizde fazla']}", "", "| # | Grup | Gerçek malzeme | Boyut | Adet | Sonuç | Bizim adet |", "|---|---|---|---|---|---|---|"]
    g = k["gercek"]
    for x in k["satir"]["satirlar"]:
        i = x["gercek"]["satirlar"][0]
        L.append("| " + " | ".join(str(v).replace("|", "/") for v in (
            i + 1, maske(g[i]["grup"]), maske(g[i]["malzeme"]), maske(g[i]["boyut"]), _s(x["gercek"]["adet"]), x["sonuc"],
            _s(x["bizim"]["adet"]) if x["bizim"] else "—")) + " |")
    if k["satir"]["fazla"]:
        L += ["", "## Bizde fazla", "", "| Grup | Ad | Ölçü | Adet |", "|---|---|---|---|"]
        L += [f"| {maske(f['anahtar'][0])} | {maske(f['anahtar'][1])} | {' × '.join(_s(v) for v in f['anahtar'][2])} | "
              f"{_s(f['bizim']['adet'])} |" for f in k["satir"]["fazla"]]
    Path(yol).write_text("\n".join(L) + "\n", encoding="utf-8")


def sonuc_yaz(kayit: dict, yol: Path) -> None:
    ust = {k: v for k, v in kayit.items() if k != "tutanlar"}
    metin = json.dumps(ust, ensure_ascii=False, indent=1)[:-2]
    satirlar = ",\n".join("  " + json.dumps(t, ensure_ascii=False) for t in kayit["tutanlar"])
    Path(yol).write_text(metin + ',\n "tutanlar": [\n' + satirlar + "\n ]\n}\n", encoding="utf-8")


# -------------------------------------------------------------------------------------------------------------- ilk indirme

def ilk_indirme(kod: str, dosya: Path, drive_degisme: str, muhur: dict) -> dict:
    """Mühürde SHA'sı olmayan bir kaydın ilk indirme kaydı: dosyanın baytı mühürdekiyle, Drive saati mühürdekiyle aynı olmalı.
    Dosyanın içeriği okunmaz."""
    dosya = Path(dosya)
    bayt = dosya.stat().st_size
    aday = [r for r in muhur["dosyalar"] if r["kod"] == kod and r["bayt"] == bayt and r["uzanti"] == dosya.suffix.lower()
            and not kayit_ozeti(r, muhur)]
    if len(aday) != 1:
        raise Durdu(2, f"{kod} için {bayt} baytlık, SHA'sı bekleyen {'kayıt yok' if not aday else 'birden çok kayıt var'}; dosya okunmadı")
    r = aday[0]
    if drive_degisme != r["drive_degisme"]:
        raise Durdu(2, f"Drive saati {drive_degisme}, mühürde {r['drive_degisme']}: dosya mühürden sonra değişmiş; kayıt yazılmaz")
    return {r["drive_id"]: {"sha256": sha256(dosya), "bayt": bayt, "drive_degisme": drive_degisme,
                            "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%d")}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    c = alt.add_parser("cevap", help="açık listenin hakem cevabı")
    c.add_argument("--kod", required=True)
    c.add_argument("--liste", type=Path, required=True)
    c.add_argument("--pafta", type=Path)
    c.add_argument("--sayfa", type=int)
    c.add_argument("--md", type=Path)
    c.add_argument("--json", type=Path)
    k = alt.add_parser("kiyas", help="kendi listemizle kıyas")
    k.add_argument("--bizim", type=Path, required=True)
    k.add_argument("--liste", type=Path, required=True)
    k.add_argument("--pafta", type=Path)
    k.add_argument("--sayfa", type=int)
    k.add_argument("--md", type=Path)
    k.add_argument("--sonuc-yaz", action="store_true", help="kapının sonucunu ve tutan satırları bizim listenin yanındaki sonuc.json'a yaz")
    i = alt.add_parser("ilk-indirme", help="SHA'sı ilk indirmede alınacak kaydın kaydı")
    i.add_argument("--kod", required=True)
    i.add_argument("--dosya", type=Path, required=True)
    i.add_argument("--drive-degisme", required=True)
    i.add_argument("--yaz", action="store_true", help="muhur.json › ilk_indirmeler'e yaz (sonra ayrı commit)")
    a = ap.parse_args(argv)
    try:
        if a.komut == "cevap":
            r = cevap(a.kod, a.liste, a.pafta, sayfa=a.sayfa)
            t = r["celik"]["toplam"]
            print(f"{r['kod']}: çelik {t['adet']} parça {_s(t['kg'])} kg; "
                  + ", ".join(f"{x['ad']} {x['gercek_adet']}" + (f" (pafta {_s(x['pafta_etiket'])})" if x['pafta_liste'] else "")
                              for x in r["tablo"]))
            if a.md:
                cevap_md(r, a.md)
            if a.json:
                a.json.write_text(json.dumps(cevap_json(r), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        elif a.komut == "kiyas":
            r = kiyasla(a.bizim, a.liste, a.pafta, sayfa=a.sayfa)
            kp = r["kapi"]
            print(f"{r['kod']}: çelik kg kapısı {kp['sonuc']}" + (f" (fark {kp['fark_yuzde']} %)" if "fark_yuzde" in kp else "")
                  + f"; öteki satırlar {r['satir']['sayilar']}")
            if a.md:
                rapor_md(r, a.md)
            if a.sonuc_yaz:
                sonuc_yaz(sonuc_kaydi(r), a.bizim.parent / "sonuc.json")
        else:
            m = muhur_oku()
            kayit = ilk_indirme(a.kod, a.dosya, a.drive_degisme, m)
            print(json.dumps(kayit, ensure_ascii=False))
            if a.yaz:
                m.setdefault("ilk_indirmeler", {}).update(kayit)
                MUHUR.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except Durdu as e:
        print(f"DURDU · {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
