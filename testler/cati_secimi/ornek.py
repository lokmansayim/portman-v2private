"""İE-25 · çatı seçiminin örneği (D-28 hedef örneği): "88 m² 2+1 tek kat çelik" → alan seti (her plan bir kez) → Ç8801 seçilir →
"Çatı seçin" (1. Ç8801 katalog çatısı, 2. Ç8801-K, 3. Ç8801-L) → seçilen çatıyla r01.

Main'deki kodla üretir, LLM ve WhatsApp yok: talep kayıtlı okuma gibi elle (`TALEP`), alan setinin görseli worker'ın üreticisiyle
(`worker.secenek_satirlari`), plan seçimi worker'ın kendisiyle (`kanal/worker.isle`, düğme `s:<set>:<kod>`): çatı setinin kararı ve bayiye
giden bileşik görsel (banka modellerinin kart görselleri; tek görsel, üç düğme). Seçilen çatıyla r01: düğme yine `worker.isle`'den, çizim
gerçek genel motorla (`--r01`; yavaş, kıyasa girmez: kıyas her çatının r01 kararını ve tanım izini tutar).

    python -m testler.cati_secimi.ornek <çıktı klasörü> [--r01]

Çıktı: `ozet.json` (iki setin mesajı, düğmeleri ve bileşik görsellerinin içerik izleri, üç çatının r01 özeti) ve görseller. Kıyas
`testler/cati_secimi/test_cati_seti_hedef.py`: `ozet.json` ↔ `hedef.json` (Lokman'ın onayıyla donar; D-02).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
for p in (KOK, KOK / "kanal"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

NUMARA = "900000000101"                        # gerçek olmayan deneme numarası
BAYI = {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi", "numara": NUMARA}
MESAJ = "88 m² 2+1 tek kat çelik"
TALEP = {"niyet": "yeni_talep", "guven": "yuksek", "ozet": MESAJ, "alan_m2": 88, "oda_programi": "2+1", "yapi_turu": "celik", "kat_sayisi": 1}
AYAR = {"llm": {"backend": "manuel"}, "patron_teknik_not": False, "mesaj_katmani": True}
KIMLIK = ("wamid.CATIORNEK001", "wamid.CATIORNEK002", "wamid.CATIORNEK003")      # sabit: set kimlikleri bundan türer
PLAN = "Ç8801"
CATILAR = (("Ç8801", "1. Ç8801"), ("Ç8801K", "2. Ç8801-K"), ("Ç8801L", "3. Ç8801-L"))


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


def uret(cikti: Path, r01: bool = False, r01_cati: str = "Ç8801K") -> dict:
    """Örneği `cikti`ya üretir ve özetini döner (ayrıca `cikti/ozet.json`)."""
    import worker as W
    from beyin import karar as K
    from beyin.katalog import Katalog
    from beyin.konusma import Konusma
    from beyin.sema import Talep
    from kanal import etkilesim as ET
    cikti = Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    hazirlik = cikti / "projeler"
    kat = Katalog(kabul_edilmis=None)                                       # yedi çelik aday görünür (harness gibi)
    k = Konusma(NUMARA, kok=cikti / "durum")
    # 1) talep → alan seti (her plan bir kez) ve görseli (worker'ın üreticisi)
    k.son_mesaj_id = KIMLIK[0]
    r = K.karar_ver(Talep.model_validate(TALEP), k, BAYI, kat, MESAJ)
    assert r.eylem == "secenek" and k.d["secenek_seti"]["tur"] == "alan", r
    st1 = k.d["secenek_seti"]
    [s1] = [x for x in W.secenek_satirlari(_gelen(KIMLIK[0], MESAJ), r, kat, r.mesaj, hazirlik) if x.get("kind") == "interactive"
            and (x["interactive"].get("action") or {}).get("buttons")]
    ozet = {"talep": MESAJ, "alan_seti": _set_ozeti(s1, st1)}
    dosyalar = {"alan_seti.png": s1.get("file")}
    # 2) plan seçilir (düğme) → çatı seti (worker: karar ve bileşik görsel)
    g = _gelen(KIMLIK[1], f"1. {PLAN}", f"s:{st1['id']}:{PLAN}")           # metin: düğmenin başlığı (meta_api)
    s = W.isle(g, AYAR, k=k, proje_koku=hazirlik, katalog=kat)
    assert s["sonuc"]["eylem"] == "secenek", s["sonuc"]
    [s2] = [x for x in s["satirlar"] if x.get("kind") == "interactive"]
    st2 = k.d["secenek_seti"]
    ozet["cati_seti"] = _set_ozeti(s2, st2)
    ozet["alan_seti_kapanis"] = next(({"durum": e["durum"], "secilen_kod": e.get("secilen_kod")} for e in k.d.get("eski_setler") or []
                                      if e.get("id") == st1["id"]), None)
    dosyalar["cati_seti.png"] = s2.get("file")
    # 3) seçilen çatıyla r01: her çatı için konuşmanın kopyasında düğme (kıyas kararı tutar; --r01 seçilen çatıyı çizer)
    ozet["r01"] = {}
    for kod, baslik in CATILAR:
        kk = Konusma(NUMARA, kok=cikti / f"durum_{kod}")
        kk.d = copy.deepcopy(k.d)
        g3 = _gelen(KIMLIK[2], baslik, f"s:{st2['id']}:{kod}")
        if r01 and kod == r01_cati:
            s3 = W.isle(g3, AYAR, k=kk, proje_koku=hazirlik, katalog=kat)
            ie = kk.d["son_is_emri"]
            gorsel = next((x.get("file") for x in s3["satirlar"] if x.get("kind") == "interactive" and x.get("file")), None)
            pdf = next((x.get("file") for x in s3["satirlar"] if x.get("kind") == "document"), None)
            dosyalar.update({f"r01_{kod}_gorsel.png": gorsel, f"r01_{kod}.pdf": pdf})
            mesaj = next(x["interactive"]["body"]["text"] for x in s3["satirlar"] if x.get("kind") == "interactive")
        else:
            etk = ET.coz(g3, kk.d)
            kk.son_mesaj_id = KIMLIK[2]
            r3 = K.karar_ver(Talep.model_validate(etk["talep"]), kk, BAYI, kat, etk["metin"])
            ie, mesaj = r3.is_emri, r3.mesaj
        y = ie["yapi"]
        ozet["r01"][kod] = {"kod": y["kod"], "revizyon": ie["revizyon"], "tanim": y["tanim"], "tanim_sha256": y["tanim_sha256"],
                            "mesaj": mesaj.replace(ie.get("is_emri_no") or "-", "{is_emri}")}
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet["_dosyalar"] = {a: b for a, b in dosyalar.items() if b}
    return ozet


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    o = uret(Path(sys.argv[1]), r01="--r01" in sys.argv[2:])
    print(json.dumps({a: b for a, b in o.items() if a != "_dosyalar"}, ensure_ascii=False, indent=1))
    for a, b in o["_dosyalar"].items():
        print(f"{a}: {b}")
