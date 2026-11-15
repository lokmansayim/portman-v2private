"""İE-25, İE-42 (D-94) · çatı seçiminin örneği (D-28 hedef örneği): "88 m² 2+1 tek kat çelik" → alan seti (her plan bir kez) → Ç8801
seçilir → r01 katalog çatısıyla → Onayla → "Planınız onaylandı (r01). Şimdi çatıyı seçin." (1. Ç8801 katalog çatısı, 2. Ç8801-K,
3. Ç8801-L) → katalog çatısı r01'i onaylar (plan teknik kontrole gider); başka çatı aynı planı o çatıyla r02 çizer → Onayla. Sıra Lokman'ın
14 Kasım 2026 20:33:41 kartı ("Onaydan sonra, eskizdeki gibi"; D-94); önce (İE-25) çatı seti plan seçilince, çizimden önce geliyordu.

Main'deki kodla üretir, LLM ve WhatsApp yok: talep kayıtlı okuma gibi elle (`TALEP`), alan setinin görseli worker'ın üreticisiyle
(`worker.secenek_satirlari`), onaydan sonraki çatı seti `kanal/worker.isle` ile (düğme `o:<no>:1`): kararı ve bayiye giden bileşik görsel
(banka modellerinin kart görselleri; tek görsel, üç düğme). Düğmeler `kanal/etkilesim`'le çözülür. Çizim (`--ciz`): r01 ve Ç8801-K'nın r02'si
`worker.isle`'den gerçek genel motorla (yavaş, kıyasa girmez: kıyas kararları ve tanım izini tutar; genel motorun izleri ayrıca dondurulu).

    python -m testler.cati_secimi.ornek <çıktı klasörü> [--ciz]

Çıktı: `ozet.json` (iki setin mesajı, düğmeleri ve bileşik görsellerinin içerik izleri, r01, üç çatı seçiminin sonucu ve r02'nin onayı) ve
görseller. Kıyas `testler/cati_secimi/test_cati_seti_hedef.py`: `ozet.json` ↔ `hedef.json` (Lokman'ın onayıyla donar; D-02).
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
KIMLIK = ("wamid.CATIORNEK001", "wamid.CATIORNEK002", "wamid.CATIORNEK003", "wamid.CATIORNEK004", "wamid.CATIORNEK005")      # sabit: set kimlikleri bundan türer
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


def _plan_ozeti(ie: dict, mesaj: str) -> dict:
    y = ie["yapi"]
    return {"kod": y["kod"], "revizyon": ie["revizyon"], "tanim": y["tanim"], "tanim_sha256": y["tanim_sha256"],
            "mesaj": mesaj.replace(ie.get("is_emri_no") or "-", "{is_emri}")}


def _onay_ozeti(r, k) -> dict:
    ie = k.d.get("son_is_emri") or {}
    return {"eylem": r.eylem, "gerekce": r.gerekce, "asama": k.d["asama"], "revizyon": ie.get("revizyon"),
            "mesaj": r.mesaj.replace(ie.get("is_emri_no") or "-", "{is_emri}")}


def uret(cikti: Path, ciz: bool = False, ciz_cati: str = "Ç8801K") -> dict:
    """Örneği `cikti`ya üretir ve özetini döner (ayrıca `cikti/ozet.json`). `ciz`: r01 ve `ciz_cati`nın r02'si gerçek motorla çizilir."""
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

    # 1) talep → alan seti (her plan bir kez) ve görseli (worker'ın üreticisi)
    k.son_mesaj_id = KIMLIK[0]
    r = K.karar_ver(Talep.model_validate(TALEP), k, BAYI, kat, MESAJ)
    assert r.eylem == "secenek" and k.d["secenek_seti"]["tur"] == "alan", r
    st1 = k.d["secenek_seti"]
    [s1] = [x for x in W.secenek_satirlari(_gelen(KIMLIK[0], MESAJ), r, kat, r.mesaj, hazirlik) if x.get("kind") == "interactive"
            and (x["interactive"].get("action") or {}).get("buttons")]
    ozet = {"talep": MESAJ, "alan_seti": _set_ozeti(s1, st1)}
    dosyalar["alan_seti.png"] = s1.get("file")
    # 2) plan seçilir (düğme) → r01 katalog çatısıyla (İE-42: çatı sorulmaz)
    r = dugme(k, KIMLIK[1], f"1. {PLAN}", f"s:{st1['id']}:{PLAN}", ciz, "r01")           # metin: düğmenin başlığı (meta_api)
    assert r.eylem == "is_emri" and r.revizyon == 1, r
    ozet["r01"] = _plan_ozeti(r.is_emri, r.mesaj)
    ozet["alan_seti_kapanis"] = next(({"durum": e["durum"], "secilen_kod": e.get("secilen_kod")}
                                      for e in [*(k.d.get("eski_setler") or []), k.d.get("secenek_seti") or {}] if e.get("id") == st1["id"]), None)
    # 3) Onayla → çatı seti (worker: karar ve bileşik görsel); onay henüz kaydedilmez, plan teknik kontrole gitmez
    no = k.d["son_is_emri"]["is_emri_no"]
    s = W.isle(_gelen(KIMLIK[2], "Onayla", f"o:{no}:1"), AYAR, k=k, proje_koku=hazirlik, katalog=kat)
    assert s["sonuc"]["eylem"] == "secenek", s["sonuc"]
    [s2] = [x for x in s["satirlar"] if x.get("kind") == "interactive"]
    st2 = k.d["secenek_seti"]
    ozet["cati_seti"] = {**_set_ozeti(s2, st2), "asama": k.d["asama"]}
    dosyalar["cati_seti.png"] = s2.get("file")
    # 4) çatı seçimi: her çatı için konuşmanın kopyasında düğme. Katalog çatısı → onay; başka çatı → r02 → Onayla
    ozet["secim"] = {}
    for kod, baslik in CATILAR:
        kk = Konusma(NUMARA, kok=cikti / f"durum_{kod}")
        kk.d = copy.deepcopy(k.d)
        r3 = dugme(kk, KIMLIK[3], baslik, f"s:{st2['id']}:{kod}", ciz and kod == ciz_cati, f"r02_{kod}")
        if r3.eylem != "is_emri":
            ozet["secim"][kod] = _onay_ozeti(r3, kk)
            continue
        ozet["secim"][kod] = _plan_ozeti(r3.is_emri, r3.mesaj)
        r4 = dugme(kk, KIMLIK[4], "Onayla", f"o:{kk.d['son_is_emri']['is_emri_no']}:{r3.revizyon}", False)
        ozet["secim"][kod]["onay"] = _onay_ozeti(r4, kk)
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet["_dosyalar"] = {a: b for a, b in dosyalar.items() if b}
    return ozet


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    o = uret(Path(sys.argv[1]), ciz="--ciz" in sys.argv[2:])
    print(json.dumps({a: b for a, b in o.items() if a != "_dosyalar"}, ensure_ascii=False, indent=1))
    for a, b in o["_dosyalar"].items():
        print(f"{a}: {b}")
