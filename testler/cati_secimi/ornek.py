"""İE-25 · çatı setinin örneği (D-28 hedef örneği): "95 m² 3+1 tek kat çelik" → yeni plan 1 seçilir → "Çatı seçin" (1. Beşik 2. Kırma).

Canlıdaki kodla üretir, LLM ve WhatsApp yok: talep kayıtlı okuma gibi elle (`TALEP`), plan gerçek üreticiyle kör (`plan_uretici.uret`,
LLM kapalı; worker'ın `plan_sonucu` yolu), yeni plan seçimi worker'ın kendisiyle (`kanal/worker.isle`, düğme `s:<set>:<kod>`): çatı
setinin kararı, iki kart (`plan_karti`, genel motor, perspektifsiz) ve bayiye giden bileşik görsel (`secenek_satirlari`). Seçilen
çatıyla r01: düğme yine `worker.isle`'den, çizim gerçek genel motorla (`--r01`; yavaş, kıyasa girmez: kıyas r01'in tanım izini tutar).

    python -m testler.cati_secimi.ornek <çıktı klasörü> [--r01]

Çıktı: `ozet.json` (mesaj, düğmeler, kartların ve bileşik görselin içerik izleri, iki çatının r01 tanım izi) ve görseller. Kıyas
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
MESAJ = "95 m² 3+1 tek kat çelik"
TALEP = {"niyet": "yeni_talep", "guven": "yuksek", "ozet": MESAJ, "alan_m2": 95, "oda_programi": "3+1", "yapi_turu": "celik", "kat_sayisi": 1}
AYAR = {"llm": {"backend": "manuel"}, "patron_teknik_not": False, "mesaj_katmani": True, "plan_uretimi": {"acik": True}}
KIMLIK = ("wamid.CATIORNEK001", "wamid.CATIORNEK002", "wamid.CATIORNEK003")      # sabit: yeni planın kodu ve set kimliği bundan türer


def _gelen(mid: str, metin: str, reply_id: str | None = None) -> dict:
    g = {"id": mid, "sender": NUMARA, "name": "", "role": "bayi", "bayi": BAYI, "type": "interactive" if reply_id else "text", "text": metin}
    if reply_id:
        g["reply_id"] = reply_id
    return g


def _iz(yol) -> str | None:
    from motor.genel import iz
    return iz.dosya_izi(Path(yol)) if yol and Path(yol).is_file() else None


def uret(cikti: Path, r01: bool = False) -> dict:
    """Örneği `cikti`ya üretir ve özetini döner (ayrıca `cikti/ozet.json`)."""
    import worker as W
    from beyin import celik, karar as K, plan_uretici as PU
    from beyin.katalog import Katalog
    from beyin.konusma import Konusma
    from beyin.sema import Talep
    cikti = Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    hazirlik = cikti / "projeler"
    kat = Katalog(kabul_edilmis=None)                                       # yedi çelik aday görünür (harness gibi)
    k = Konusma(NUMARA, kok=cikti / "durum")
    # 1) talep → yeni plan seti (üretim kör; kartsız: yeni plan setinin görseli bu örneğin konusu değil)
    k.son_mesaj_id, k.plan_uretimi = KIMLIK[0], True
    r = K.karar_ver(Talep.model_validate(TALEP), k, BAYI, kat, MESAJ)
    assert r.gerekce == K.PLAN_URETIMI, r
    pu = PU.uret(k.d["plan_istegi"]["talep"], ayar={"acik": False})
    r = K.plan_sonucu(k, kat, pu, [None, None])
    assert r.eylem == "secenek", r
    yeni = next(a["kod"] for a in k.d["secenek_seti"]["adaylar"] if a.get("durum") == "uretilen")
    # 2) yeni plan seçilir → çatı seti (worker: karar, kartlar, bileşik görsel, satırlar)
    g = _gelen(KIMLIK[1], "1. Yeni plan", f"s:{k.d['secenek_seti']['id']}:{yeni}")         # metin: düğmenin başlığı (meta_api)
    s = W.isle(g, AYAR, k=k, proje_koku=hazirlik, katalog=kat)
    assert s["sonuc"]["eylem"] == "secenek", s["sonuc"]
    [satir] = [x for x in s["satirlar"] if x.get("kind") == "interactive"]
    st = k.d["secenek_seti"]

    def yerel(x):                                  # kalıcı akış kartı projects/'e taşır; konuşma oradaki yolu tutar (`kart_son_yeri`)
        return str(hazirlik / Path(x).relative_to(W.KANAL / "projects")) if x and str(x).startswith(str(W.KANAL / "projects")) else x
    kartlar = [yerel(v["gorsel"]) for v in k.d["cati_secenekleri"]["adaylar"]]
    ozet = {"talep": MESAJ, "yeni_plan": "Yeni plan (1)", "set_turu": st["tur"],
            "mesaj": satir["interactive"]["body"]["text"],
            "dugmeler": [[b["reply"]["id"].replace(st["id"], "{set}").replace(yeni, "{plan}"), b["reply"]["title"]]
                         for b in satir["interactive"]["action"]["buttons"]],
            "kartlar": {v["gosterim"]: {"cati": v["cati_tipi"], "cati_adi": v["sunum"]["cati_adi"], "kart_izi": _iz(yerel(v["gorsel"])),
                                        "tanim_izi": celik.tanim_sha_icerik({**v["tanim"], "kod": "{plan}"})}
                        for v in k.d["cati_secenekleri"]["adaylar"]},
            "secenekler_izi": _iz(satir["file"]) if satir.get("file") else None}
    dosyalar = {"secenekler.png": satir.get("file"), **{f"kart_{Path(x).parent.parent.name[-1]}.png": x for x in kartlar}}
    # 3) seçilen çatıyla r01: her çatı için konuşmanın kopyasında düğme (kıyas tanımı tutar; --r01 kırmayı çizer)
    ozet["r01"] = {}
    for tip in ("besik", "kirma"):
        kk = Konusma(NUMARA, kok=cikti / f"durum_{tip}")
        kk.d = copy.deepcopy(k.d)
        kod = f"{yeni}-{K.CATI_EKI[tip]}"
        g3 = _gelen(KIMLIK[2], f"{'1. Beşik' if tip == 'besik' else '2. Kırma'}", f"s:{st['id']}:{kod}")
        if r01 and tip == "kirma":
            s3 = W.isle(g3, AYAR, k=kk, proje_koku=hazirlik, katalog=kat)
            ie = kk.d["son_is_emri"]
            gorsel = next((x.get("file") for x in s3["satirlar"] if x.get("kind") == "interactive" and x.get("file")), None)
            pdf = next((x.get("file") for x in s3["satirlar"] if x.get("kind") == "document"), None)
            dosyalar.update({"r01_kirma_gorsel.png": gorsel, "r01_kirma.pdf": pdf})
            mesaj = next(x["interactive"]["body"]["text"] for x in s3["satirlar"] if x.get("kind") == "interactive")
        else:
            from kanal import etkilesim as ET
            etk = ET.coz(g3, kk.d)
            kk.son_mesaj_id, kk.plan_uretimi = KIMLIK[2], True
            r3 = K.karar_ver(Talep.model_validate(etk["talep"]), kk, BAYI, kat, etk["metin"])
            ie, mesaj = r3.is_emri, r3.mesaj
        y = ie["yapi"]
        ozet["r01"][tip] = {"kod": "{plan}" if y["kod"] == yeni else y["kod"], "revizyon": ie["revizyon"], "cati": y["tanim"]["cati"]["tip"],
                            "tanim_izi": celik.tanim_sha_icerik({**y["tanim"], "kod": "{plan}"}),
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
