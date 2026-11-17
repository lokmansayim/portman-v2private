"""BK-37 · Havuz hakeminde birleşim profili kalemi: kaydın (Motor'un) 3'lü H ve çektirme U'su yerleri mühendis paftasının H profil
montaj planıyla aynı mı.

Dayanak: Lokman, 15 Kasım 2026 07:59:14 UTC ("bunlar hep mühendis hataları ... sen kuralları kontrolleri hakemleri ve kendi insiyatifini
aldın mı"); 143 m² 4+1'in veranda köşesinde paftanın özel 3'lü H'ı kayıtta köşe direğiydi ve normal kip geçmişti. Kalemin kapsamı CIO'nun
okumasıdır (varsayım), kural değildir. Hakem yalnız okur ve bulgu yazar; kayda, Motor'a ve listeye dokunmaz.

Kaydın birleşimleri yükleme listesinin saydığı gibidir (`motor/prefabrik_liste.model_motor`, İE-27): pano ekinde 3'lü H (iç duvar T'si,
dış duvar T bölmesi, giriş nişinin uç uca eki); iç duvarın T ucu pano ortasına geliyorsa, inceyse dış köşeye geliyorsa ya da serbest
bitiyorsa çektirme U'su. Motor'un montaj çizimindeki H simgesi (`plan.h_baglantilar`) kıyasa girmez: pano ortasındaki iç T'de liste
çektirme U'su sayar (ayrı bakım işi, 15 Kasım 2026). Sayılar listeyle aynı olmak zorundadır (`testler/test_havuz_birlesim_profili.py`).

Paftanın birleşimleri `testler/havuz/profil_kartlari.json`'dadır (`araclar/profil_karti.py` H profil montaj planından okur, kaydın
çerçevesine hizalar; pafta depoya girmez). Kalemler (konum payı 13 cm):
- paftada 3'lü ya da 4'lü H olan yerde kayıtta 3'lü H yok (çektirme U'su ya da pano ortası);
- paftada düz H olan yerde kayıtta 3'lü H var;
- kayıtta 3'lü H olan yerde paftada 3'lü ya da 4'lü H yok.
Dört kollu birleşimde (BK-14, `plan.arti_birlesimler`; liste uyarır) paftanın 4'lü H'ı fark sayılmaz.
Lokman'ın ev kartına göre (`farklar[].durum`, sözü ve saatiyle): "kabul" (kayıt doğru) fark bulgu sayılmaz; "kayit_hatasi" (pafta
doğru) kayıt düzeltilene kadar "KAYIT HATASI" diye yazılır ve hakemden geçmez (düzeltme ayrı iş; düzelince kart satırı silinir);
"bekleyen" kartı bekler ve hakemden geçmez. Köşe direği ve özel kaynaklı profiller (kolon, kiriş, pencere karkası) bu kalemde yok.

Lokman'ın cevapları (15 Kasım 2026): 125,5'lik panonun tam ortasına gelen iç duvarda paftanın 3'lü H'ı yerine çektirme U'su bir
uygulamadır (08:51:58; 140 m²); T panonun ortasına gelmiyorsa pafta panoyu bölüp 3'lü H koyar, kayıt hatalı (08:53:28 71 m²,
08:53:55 45 m²); dış duvar ekindeki 60'lık iç T'de kaydın 3'lü H'ı doğru (08:54:31; 84 m²). Sözler kart dosyasındadır; kalem bunları
genel kural diye uygulamaz, her farkı kendi kartıyla ayırır.

    python3 araclar/birlesim_hakemi.py PA-08
    python3 araclar/birlesim_hakemi.py hepsi
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
KARTLAR = KOK / "testler" / "havuz" / "profil_kartlari.json"
TOL_CM = 13.0
UCLU = ("uclu_h", "dortlu_h")


def kartlar() -> dict:
    return json.loads(KARTLAR.read_text(encoding="utf-8"))


def kartlari_yaz(K: dict) -> None:
    """Kart dosyasını yazar: her birleşim ve fark tek satırda (okunur diff)."""
    t = json.dumps(K, ensure_ascii=False, indent=1)
    t = re.sub(r"\[[^\[\]{}]*\]", lambda m: re.sub(r"\s+", " ", m.group(0)).replace("[ ", "[").replace(" ]", "]"), t)
    t = re.sub(r"\{(?:[^{}\[\]]|\[[^\[\]{}]*\])*\}", lambda m: re.sub(r"\s*\n\s*", " ", m.group(0)).replace("{ ", "{").replace(" }", "}"), t)
    KARTLAR.write_text(t + "\n", encoding="utf-8")


def kod_yaz(kod: str) -> str:
    n = re.sub(r"\D", "", kod)
    return f"PA-{int(n):02d}" if n else kod


def is_emri_yolu(kod: str) -> Path:
    return KOK / "is_emri" / "adaylar" / f"{kod_yaz(kod).replace('-', '')}.json"


def kayit_birlesimleri(ie: dict) -> dict:
    """Kaydın birleşimleri (gerçek çerçeve, cm: x sol dış yüzden, y ön dış yüzden). `prefabrik_liste.model_motor`'un T ve ek döngüsünün
    aynısı; yerleri de yazar. Dönüş: `uclu_h` (listenin "uclu" ekleri), `cektirme_u` (t_orta, dis_kose, serbest), `ekler` (bütün pano
    ekleri), `sayilar` (listeyle kıyas için)."""
    from motor import geometry as G
    plan = G.kur(json.loads(json.dumps(ie)))
    W_ = {d.id: d for d in plan.duvarlar}
    t_uclari: dict[int, list[float]] = {}
    cektirme: list[dict] = []
    for d in plan.duvarlar:
        if d.tur != "ic":
            continue
        for uc in (0, 1):
            n = d.uc_notu.get(uc, "")
            p = d.p0 if uc == 0 else d.p1
            if n == "serbest":
                cektirme.append({"xy": [p, d.c] if d.yon == "x" else [d.c, p], "alt": "serbest"})
                continue
            m = re.match(r"T→(\d+)(.*)$", n)
            if not m:
                continue
            o = W_[int(m.group(1))]
            xy = [o.c, d.c] if d.yon == "x" else [d.c, o.c]
            if "köşe" in m.group(2):                                # BK-38 (D-105 madde 2): her kalınlıkta, `model_motor` gibi
                cektirme.append({"xy": xy, "alt": "dis_kose"})
                continue
            if any(w is not d and w.yon == d.yon and abs(w.c - d.c) < 1e-6
                   and (abs(w.p1 - d.p0) < 1e-6 if uc == 0 else abs(w.p0 - d.p1) < 1e-6) for w in plan.duvarlar):
                continue
            if any(abs(q.a1 - d.c) <= o.h + 3.5 for q in o.panolar[:-1]):
                t_uclari.setdefault(o.id, []).append(d.c)
            else:
                cektirme.append({"xy": xy, "alt": "t_orta"})
    kubbe_tabani = lambda q: q.acilim is not None and q.acilim.tur == "kubbe"   # noqa: E731
    ekler = []
    for d in plan.duvarlar:
        for a_, b_ in zip(d.panolar, d.panolar[1:]):
            if kubbe_tabani(a_) or kubbe_tabani(b_):
                continue
            x, y = (a_.a1, d.c) if d.yon == "x" else (d.c, a_.a1)
            uclu = any(abs(h.x - x) <= d.h + 3.5 and abs(h.y - y) <= d.h + 3.5 for h in plan.h_baglantilar)
            if d.tur == "dis" and not uclu:
                uclu = any(abs(a_.a1 - c_) <= d.h + 3.5 for c_ in t_uclari.get(d.id, []))
            ekler.append({"xy": [x, y], "duvar": d.tur, "cins": "uclu" if uclu else "pano_eki"})
            if any(abs(ax - x) <= d.h + 3.5 and abs(ay - y) <= d.h + 3.5 for ax, ay in plan.arti_birlesimler):
                ekler[-1]["arti"] = True                        # BK-14: dört kollu birleşim; profili kitapta yok, liste uyarır
    for k in G.uc_uca_ekler(plan):
        ekler.append({"xy": [k["x"], k["y"]], "duvar": k["duvar"], "cins": k["cins"]})
    yuvarla = lambda v: [round(v[0], 2), round(v[1], 2)]   # noqa: E731
    for e in ekler + cektirme:
        e["xy"] = yuvarla(e["xy"])
    return {"W": round(plan.W, 2), "H": round(plan.H, 2), "ekler": ekler, "cektirme_u": cektirme,
            "uclu_h": [e for e in ekler if e["cins"] == "uclu"],
            "koseler": [yuvarla(((k.rect[0] + k.rect[2]) / 2, (k.rect[1] + k.rect[3]) / 2)) for k in plan.koseler],
            "sayilar": {"uclu_ek": sum(e["cins"] == "uclu" for e in ekler), "pano_eki": sum(e["cins"] == "pano_eki" for e in ekler),
                        "cektirme_yerleri": dict(Counter(c["alt"] for c in cektirme))}}


def _yakin(a, b, t=TOL_CM) -> bool:
    return abs(a[0] - b[0]) <= t and abs(a[1] - b[1]) <= t


def _tr(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def denetle(kod: str, ie: dict, kart: dict) -> tuple[list[dict], dict]:
    """(bulgular, kaydın birleşimleri). Bulgu: tür, yer (cm), paftadaki ve kayıttaki profil, yazı."""
    k = kayit_birlesimleri(ie)
    pafta = kart["h"]
    bul: list[dict] = []

    def kayitta(xy) -> str:
        if any(_yakin(xy, e["xy"]) for e in k["uclu_h"]):
            return "3'lü H"
        if any(_yakin(xy, e["xy"]) and e.get("arti") for e in k["ekler"]):
            return "dört kollu birleşim"
        if any(_yakin(xy, c["xy"]) for c in k["cektirme_u"]):
            return "çektirme U'su"
        if any(_yakin(xy, e["xy"]) for e in k["ekler"]):
            return "düz H"
        return "pano ortası"

    for p in pafta:
        ne = kayitta(p["xy"])
        if p["tur"] == "dortlu_h" and ne == "dört kollu birleşim":
            continue                                            # BK-14: liste satırı uyarır; profil adı kitapta yok
        if p["tur"] in UCLU and ne != "3'lü H":
            bul.append({"tur": "pafta_uclu_kayit_degil", "xy": p["xy"], "pafta": p["tur"], "kayit": ne})
        elif p["tur"] == "h" and ne == "3'lü H":
            bul.append({"tur": "pafta_duz_kayit_uclu", "xy": p["xy"], "pafta": "h", "kayit": ne})
    gor = []
    for e in k["uclu_h"]:
        if any(_yakin(e["xy"], g, 1.0) for g in gor):
            continue
        gor.append(e["xy"])
        yakin = [p for p in pafta if _yakin(e["xy"], p["xy"])]
        if not any(p["tur"] in UCLU for p in yakin) and not any(b["tur"] == "pafta_duz_kayit_uclu" and _yakin(b["xy"], e["xy"]) for b in bul):
            bul.append({"tur": "kayit_uclu_pafta_degil", "xy": e["xy"], "pafta": "-", "kayit": "3'lü H"})
    ad = {"uclu_h": "3'lü H", "dortlu_h": "4'lü H", "h": "düz H", "-": "profil yok"}
    for b in bul:
        b["xy"] = [round(b["xy"][0], 1), round(b["xy"][1], 1)]
        b["yazi"] = f"[{_tr(b['xy'][0])}; {_tr(b['xy'][1])}] paftada {ad.get(b['pafta'], b['pafta'])}, kayıtta {b['kayit']}"
    return bul, k


def durumlar(kod: str, bulgular: list[dict], farklar: list[dict]) -> dict:
    """Bulguları Lokman'ın kartlarına göre ayırır: kabul (kayıt doğru), kayit_hatasi (pafta doğru, kayıt düzeltilecek), bekleyen
    (kart Lokman'da), yeni (kayıtlı değil). Kayıtlı olup artık çıkmayan fark `kalkan` (kayıt düzeldiyse kart satırı silinir)."""
    out = {"kabul": [], "kayit_hatasi": [], "bekleyen": [], "yeni": [], "kalkan": []}
    kullanildi = set()
    for b in bulgular:
        f = next((i for i, f in enumerate(farklar) if f["tur"] == b["tur"] and _yakin(f["xy"], b["xy"], 2.0)), None)
        if f is None:
            out["yeni"].append(b)
            continue
        kullanildi.add(f)
        durum = farklar[f].get("durum")
        out[durum if durum in ("kabul", "kayit_hatasi") else "bekleyen"].append({**b, "kart": farklar[f].get("kart"),
                                                                                  "sonuc": farklar[f].get("sonuc")})
    out["kalkan"] = [f for i, f in enumerate(farklar) if i not in kullanildi]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kod", help="havuz kodu (PA-08) ya da hepsi")
    ap.add_argument("--is-emri", default=None, help="kaydın İş Emri'si (varsayılan is_emri/adaylar/PAnn.json)")
    a = ap.parse_args(argv)
    K = kartlar()
    kodlar = sorted(K["evler"]) if a.kod == "hepsi" else [kod_yaz(a.kod)]
    sonuc = 0
    for kod in kodlar:
        kart = K["evler"].get(kod)
        if kart is None:
            print(f"{kod}: DUR: profil kartı yok ({KARTLAR.relative_to(KOK)})"); sonuc = max(sonuc, 2); continue
        if kart.get("okunamadi"):
            print(f"{kod}: KIYAS YOK: {kart['okunamadi']}"); continue
        yol = Path(a.is_emri) if a.is_emri else is_emri_yolu(kod)
        ie = json.loads(yol.read_text(encoding="utf-8"))
        bul, _ = denetle(kod, ie, kart)
        d = durumlar(kod, bul, K.get("farklar", {}).get(kod, []))
        if d["yeni"] or d["kalkan"]:
            sonuc = max(sonuc, 1)
            print(f"{kod}: KALDI")
            for b in d["yeni"]:
                print(f"  - yeni fark: {b['yazi']}")
            for f in d["kalkan"]:
                print(f"  - kayıtlı fark artık yok: {f['tur']} {f['xy']}")
        elif d["kayit_hatasi"] or d["bekleyen"]:
            sonuc = max(sonuc, 1)
            if d["kayit_hatasi"]:
                print(f"{kod}: KAYIT HATASI (Lokman paftayı doğru buldu; düzeltme ayrı iş)")
                for b in d["kayit_hatasi"]:
                    print(f"  - {b['yazi']}: {b['sonuc']}")
            if d["bekleyen"]:
                print(f"{kod}: BEKLİYOR (Lokman'ın kartı)")
                for b in d["bekleyen"]:
                    print(f"  - {b['yazi']}")
        else:
            print(f"{kod}: GEÇTİ: birleşimler paftayla aynı" + (f" ({len(d['kabul'])} fark Lokman'ın kartıyla kabul)" if d["kabul"] else ""))
    return sonuc


if __name__ == "__main__":
    sys.exit(main())
