"""İE-37 (D-83), İE-42 (D-94) · prefabrik evde çatı seçiminin örneği (D-28 hedef örneği): "85 m² 2+1 prefabrik" (öncelik "fark
etmez") → alan seti (PA-06, PA-05, PA-04; her plan bir kez) → PA-06 seçilir → r01 evin kendi çatısıyla → Onayla → "Planınız onaylandı (r01).
Şimdi çatıyı seçin." (1. PA-06 evin çatısı, 2. PA-06-K kırma, 3. PA-06-C beşik + salonda cumba) → evin çatısı r01'i onaylar; başka çatı aynı
planı o çatıyla r02 çizer → Onayla. Sıra Lokman'ın 14 Kasım 2026 20:33:41 kartı ("Onaydan sonra, eskizdeki gibi"; D-94).

Main'deki kodla üretir, LLM ve WhatsApp yok: talep kayıtlı okuma gibi elle (`TALEP`), setlerin görseli worker'ın üreticisiyle
(`worker.secenek_satirlari`, onaydan sonraki çatı seti `kanal/worker.isle` ile, düğme `o:<no>:1`), düğmeler `kanal/etkilesim`'le çözülür.
Katalog kabul kümesiyle kurulur (K-A10 kaydı olan kodlar gibi: `KABUL`). Çizim (`--ciz KOD`): r01 ve o çatının r02'si `worker.isle`'den
gerçek pano Motor'uyla (yavaş, kıyasa girmez: kıyas kararları ve şablon izini tutar).

    python -m testler.cati_secimi.ornek_prefabrik <çıktı klasörü> [--ciz PA06K]

Çıktı: `ozet.json` (iki setin mesajı, düğmeleri ve bileşik görsellerinin içerik izleri, r01, üç çatı seçiminin sonucu ve r02'nin onayı) ve
görseller. Kıyas `testler/cati_secimi/test_prefabrik_cati_hedef.py`: `ozet.json` ↔ `prefabrik_hedef.json` (Lokman'ın onayıyla donar; D-02).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
for p in (KOK, KOK / "kanal"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

NUMARA = "900000000101"                        # gerçek olmayan deneme numarası
BAYI = {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi", "numara": NUMARA}
MESAJ = "85 m² 2+1 prefabrik"
TALEP = {"niyet": "yeni_talep", "guven": "yuksek", "ozet": MESAJ, "alan_m2": 85, "oda_programi": "2+1", "yapi_turu": "prefabrik"}
ONCELIK = "fark etmez"
AYAR = {"llm": {"backend": "manuel"}, "patron_teknik_not": False, "mesaj_katmani": True}
KIMLIK = ("wamid.PACATI001", "wamid.PACATI002", "wamid.PACATI003", "wamid.PACATI004", "wamid.PACATI005", "wamid.PACATI006")      # sabit: set kimlikleri bundan türer
KABUL = {"PA04", "PA05", "PA06", "PA06K", "PA06C"}
PLAN = "PA06"
CATILAR = (("PA06", "1. PA-06"), ("PA06K", "2. PA-06-K"), ("PA06C", "3. PA-06-C"))


def _gelen(mid: str, metin: str, reply_id: str | None = None) -> dict:
    g = {"id": mid, "sender": NUMARA, "name": "", "role": "bayi", "bayi": BAYI, "type": "interactive" if reply_id else "text", "text": metin}
    if reply_id:
        g["reply_id"] = reply_id
    return g


def _iz(yol) -> str | None:
    from motor.genel import iz
    return iz.dosya_izi(Path(yol)) if yol and Path(yol).is_file() else None


def _set_ozeti(satir: dict, st: dict) -> dict:
    return {"tur": st["tur"], "adaylar": [a["kod"] for a in st["adaylar"]], "mesaj": satir["interactive"]["body"]["text"],
            "dugmeler": [[b["reply"]["id"].replace(st["id"], "{set}"), b["reply"]["title"]] for b in satir["interactive"]["action"]["buttons"]],
            "gorsel_izi": _iz(satir.get("file"))}


def _plan_ozeti(ie: dict, mesaj: str, kat) -> dict:
    from beyin.katalog import SABLON_DIR
    kod = ie["talep"]["kaynak"]
    sablon = SABLON_DIR / kat.aday(kod)["sablon"]
    return {"kaynak": kod, "revizyon": ie["revizyon"], "referans_model": ie["yapi"]["referans_model"], "cati": ie["cati"],
            "sablon": str(sablon.relative_to(KOK)), "sablon_sha256": hashlib.sha256(sablon.read_bytes()).hexdigest(),
            "mesaj": mesaj.replace(ie.get("is_emri_no") or "-", "{is_emri}")}


def _onay_ozeti(r, k) -> dict:
    ie = k.d.get("son_is_emri") or {}
    return {"eylem": r.eylem, "gerekce": r.gerekce, "asama": k.d["asama"], "revizyon": ie.get("revizyon"),
            "mesaj": r.mesaj.replace(ie.get("is_emri_no") or "-", "{is_emri}")}


def uret(cikti: Path, ciz: str | None = None) -> dict:
    """Örneği `cikti`ya üretir ve özetini döner (ayrıca `cikti/ozet.json`). `ciz`: r01 ve o çatının r02'si gerçek Motor'la çizilir."""
    import worker as W
    from beyin import karar as K
    from beyin.katalog import Katalog
    from beyin.konusma import Konusma
    from beyin.sema import Talep
    from kanal import etkilesim as ET
    cikti = Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    hazirlik = cikti / "projeler"
    kat = Katalog(kabul_edilmis=set(KABUL))
    k = Konusma(NUMARA, kok=cikti / "durum")
    dosyalar: dict = {}

    def dugme(kk, mid: str, baslik: str, kimlik: str, cizilsin: bool, ad: str = ""):
        """Düğme: kanalın çözümü ve karar (çizimsiz) ya da `worker.isle` (çizim; görsel ve PDF `dosyalar`a)."""
        g = _gelen(mid, baslik, kimlik)
        kk.son_mesaj_id = mid
        if not cizilsin:
            etk = ET.coz(g, kk.d)
            assert etk.get("gecerli"), etk
            return K.karar_ver(Talep.model_validate(etk["talep"]), kk, BAYI, kat, etk["metin"])
        s = W.isle(g, AYAR, k=kk, proje_koku=hazirlik, katalog=kat)
        assert s["sonuc"]["eylem"] == "is_emri", s["sonuc"]
        dosyalar[f"{ad}_gorsel.png"] = next((x.get("file") for x in s["satirlar"] if x.get("kind") == "interactive" and x.get("file")), None)
        dosyalar[f"{ad}.pdf"] = next((x.get("file") for x in s["satirlar"] if x.get("kind") == "document"), None)
        ie = kk.d["son_is_emri"]
        return K.Karar(eylem="is_emri", is_emri=ie, revizyon=ie["revizyon"], gerekce=s["sonuc"].get("gerekce") or "",
                       mesaj=next(x["interactive"]["body"]["text"] for x in s["satirlar"] if x.get("kind") == "interactive"))

    # 1) talep → öncelik sorusu → "fark etmez" → alan seti (her plan bir kez) ve görseli (worker'ın üreticisi)
    k.son_mesaj_id = KIMLIK[0]
    r = K.karar_ver(Talep.model_validate(TALEP), k, BAYI, kat, MESAJ)
    assert r.eylem == "sor" and r.soru_alani == "oncelik", r
    k.son_mesaj_id = KIMLIK[1]
    r = K.karar_ver(Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": ONCELIK}), k, BAYI, kat, ONCELIK)
    assert r.eylem == "secenek" and k.d["secenek_seti"]["tur"] == "alan", r
    st1 = k.d["secenek_seti"]
    [s1] = [x for x in W.secenek_satirlari(_gelen(KIMLIK[1], ONCELIK), r, kat, r.mesaj, hazirlik) if x.get("kind") == "interactive"
            and (x["interactive"].get("action") or {}).get("buttons")]
    ozet = {"talep": MESAJ, "oncelik": ONCELIK, "kabul": sorted(KABUL), "alan_seti": _set_ozeti(s1, st1)}
    dosyalar["alan_seti.png"] = s1.get("file")
    # 2) plan seçilir (düğme) → r01 evin kendi çatısıyla (İE-42: çatı sorulmaz)
    r = dugme(k, KIMLIK[2], "1. PA-06", f"s:{st1['id']}:{PLAN}", bool(ciz), "r01")       # metin: düğmenin başlığı (meta_api)
    assert r.eylem == "is_emri" and r.revizyon == 1, r
    ozet["r01"] = _plan_ozeti(r.is_emri, r.mesaj, kat)
    ozet["alan_seti_kapanis"] = next(({"durum": e["durum"], "secilen_kod": e.get("secilen_kod")}
                                      for e in [*(k.d.get("eski_setler") or []), k.d.get("secenek_seti") or {}] if e.get("id") == st1["id"]), None)
    # 3) Onayla → çatı seti (worker: karar ve bileşik görsel); onay henüz kaydedilmez
    no = k.d["son_is_emri"]["is_emri_no"]
    s = W.isle(_gelen(KIMLIK[3], "Onayla", f"o:{no}:1"), AYAR, k=k, proje_koku=hazirlik, katalog=kat)
    assert s["sonuc"]["eylem"] == "secenek", s["sonuc"]
    [s2] = [x for x in s["satirlar"] if x.get("kind") == "interactive"]
    st2 = k.d["secenek_seti"]
    ozet["cati_seti"] = {**_set_ozeti(s2, st2), "asama": k.d["asama"]}
    dosyalar["cati_seti.png"] = s2.get("file")
    # 4) çatı seçimi: her çatı için konuşmanın kopyasında düğme. Evin çatısı → onay; başka çatı → r02 → Onayla
    ozet["secim"] = {}
    for kod, baslik in CATILAR:
        kk = Konusma(NUMARA, kok=cikti / f"durum_{kod}")
        kk.d = copy.deepcopy(k.d)
        r3 = dugme(kk, KIMLIK[4], baslik, f"s:{st2['id']}:{kod}", ciz == kod and kod != PLAN, f"r02_{kod}")
        if r3.eylem != "is_emri":
            ozet["secim"][kod] = _onay_ozeti(r3, kk)
            continue
        ozet["secim"][kod] = _plan_ozeti(r3.is_emri, r3.mesaj, kat)
        r4 = dugme(kk, KIMLIK[5], "Onayla", f"o:{kk.d['son_is_emri']['is_emri_no']}:{r3.revizyon}", False)
        ozet["secim"][kod]["onay"] = _onay_ozeti(r4, kk)
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet["_dosyalar"] = {a: b for a, b in dosyalar.items() if b}
    return ozet


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ciz = sys.argv[sys.argv.index("--ciz") + 1] if "--ciz" in sys.argv[2:] else None
    o = uret(Path(sys.argv[1]), ciz=ciz)
    print(json.dumps({a: b for a, b in o.items() if a != "_dosyalar"}, ensure_ascii=False, indent=1))
    for a, b in o["_dosyalar"].items():
        print(f"{a}: {b}")
