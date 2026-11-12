"""İE-37 (D-83) · prefabrik evde çatı seçiminin örneği (D-28 hedef örneği): "85 m² 2+1 prefabrik" (öncelik "fark etmez") → alan seti
(PA-06, PA-05, PA-04; her plan bir kez) → PA-06 seçilir → "Çatı seçin" (1. PA-06 evin çatısı, 2. PA-06-K kırma, 3. PA-06-C beşik + salonda
cumba) → seçilen çatıyla r01.

Main'deki kodla üretir, LLM ve WhatsApp yok: talep kayıtlı okuma gibi elle (`TALEP`), setlerin görseli worker'ın üreticisiyle
(`worker.secenek_satirlari`), plan seçimi worker'ın kendisiyle (`kanal/worker.isle`, düğme `s:<set>:<kod>`). Katalog kabul kümesiyle
kurulur (K-A10 kaydı olan kodlar gibi: `KABUL`). Seçilen çatıyla r01: düğme yine `worker.isle`'den, çizim gerçek pano Motor'uyla (`--r01`;
yavaş, kıyasa girmez: kıyas her çatının r01 kararını ve şablon izini tutar).

    python -m testler.cati_secimi.ornek_prefabrik <çıktı klasörü> [--r01 PA06C]

Çıktı: `ozet.json` (iki setin mesajı, düğmeleri ve bileşik görsellerinin içerik izleri, üç çatının r01 özeti) ve görseller. Kıyas
`testler/cati_secimi/test_prefabrik_cati_hedef.py`: `ozet.json` ↔ `prefabrik_hedef.json` (Lokman'ın onayıyla donar; D-02).
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
KIMLIK = ("wamid.PACATI001", "wamid.PACATI002", "wamid.PACATI003", "wamid.PACATI004")      # sabit: set kimlikleri bundan türer
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


def uret(cikti: Path, r01: str | None = None) -> dict:
    """Örneği `cikti`ya üretir ve özetini döner (ayrıca `cikti/ozet.json`). `r01`: o çatının planı gerçek Motor'la çizilir."""
    import worker as W
    from beyin import karar as K
    from beyin.katalog import Katalog, SABLON_DIR
    from beyin.konusma import Konusma
    from beyin.sema import Talep
    from kanal import etkilesim as ET
    cikti = Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    hazirlik = cikti / "projeler"
    kat = Katalog(kabul_edilmis=set(KABUL))
    k = Konusma(NUMARA, kok=cikti / "durum")
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
    dosyalar = {"alan_seti.png": s1.get("file")}
    # 2) plan seçilir (düğme) → çatı seti (worker: karar ve bileşik görsel)
    g = _gelen(KIMLIK[2], "1. PA-06", f"s:{st1['id']}:{PLAN}")             # metin: düğmenin başlığı (meta_api)
    s = W.isle(g, AYAR, k=k, proje_koku=hazirlik, katalog=kat)
    assert s["sonuc"]["eylem"] == "secenek", s["sonuc"]
    [s2] = [x for x in s["satirlar"] if x.get("kind") == "interactive"]
    st2 = k.d["secenek_seti"]
    ozet["cati_seti"] = _set_ozeti(s2, st2)
    ozet["alan_seti_kapanis"] = next(({"durum": e["durum"], "secilen_kod": e.get("secilen_kod")} for e in k.d.get("eski_setler") or []
                                      if e.get("id") == st1["id"]), None)
    dosyalar["cati_seti.png"] = s2.get("file")
    # 3) seçilen çatıyla r01: her çatı için konuşmanın kopyasında düğme (kıyas kararı tutar; --r01 o çatıyı çizer)
    ozet["r01"] = {}
    for kod, baslik in CATILAR:
        kk = Konusma(NUMARA, kok=cikti / f"durum_{kod}")
        kk.d = copy.deepcopy(k.d)
        g3 = _gelen(KIMLIK[3], baslik, f"s:{st2['id']}:{kod}")
        if r01 and kod == r01:
            s3 = W.isle(g3, AYAR, k=kk, proje_koku=hazirlik, katalog=kat)
            ie = kk.d["son_is_emri"]
            gorsel = next((x.get("file") for x in s3["satirlar"] if x.get("kind") == "interactive" and x.get("file")), None)
            pdf = next((x.get("file") for x in s3["satirlar"] if x.get("kind") == "document"), None)
            dosyalar.update({f"r01_{kod}_gorsel.png": gorsel, f"r01_{kod}.pdf": pdf})
            mesaj = next(x["interactive"]["body"]["text"] for x in s3["satirlar"] if x.get("kind") == "interactive")
        else:
            etk = ET.coz(g3, kk.d)
            kk.son_mesaj_id = KIMLIK[3]
            r3 = K.karar_ver(Talep.model_validate(etk["talep"]), kk, BAYI, kat, etk["metin"])
            ie, mesaj = r3.is_emri, r3.mesaj
        sablon = SABLON_DIR / kat.aday(kod)["sablon"]
        ozet["r01"][kod] = {"kaynak": ie["talep"]["kaynak"], "revizyon": ie["revizyon"], "referans_model": ie["yapi"]["referans_model"],
                            "cati": ie["cati"], "sablon": str(sablon.relative_to(KOK)),
                            "sablon_sha256": hashlib.sha256(sablon.read_bytes()).hexdigest(),
                            "mesaj": mesaj.replace(ie.get("is_emri_no") or "-", "{is_emri}")}
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet["_dosyalar"] = {a: b for a, b in dosyalar.items() if b}
    return ozet


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    r01 = sys.argv[sys.argv.index("--r01") + 1] if "--r01" in sys.argv[2:] else None
    o = uret(Path(sys.argv[1]), r01=r01)
    print(json.dumps({a: b for a, b in o.items() if a != "_dosyalar"}, ensure_ascii=False, indent=1))
    for a, b in o["_dosyalar"].items():
        print(f"{a}: {b}")
