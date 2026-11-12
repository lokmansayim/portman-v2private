"""BK-28 (pano 196, 197) · bayiye giden tanıtım metinleri: "Nasıl çalışır?" sayfası ve selam / anlaşılmadı / yazılı olmayan mesaj cevabı.

Hedef örnek `testler/bayi_metinleri/` (hedef.json, nasil_calisir_hedef.txt); değişiklik yalnız Lokman'ın onayıyla (D-02, D-28). LLM'siz,
Postgres'siz. Ayrıca: metinlerdeki örnek talepler canlının kabul kümesiyle seçenek setine gider (eski "7x4 m" örneği yönlendirmeye
düşüyordu) ve sayfadaki model tablosu aday kaydıyla aynıdır (yeni model eklenince sayfa da güncellenir).
"""
from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
for p in (KOK, KOK / "kanal"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from beyin import karar as K  # noqa: E402
from beyin import secenek as SC  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.sema import Talep  # noqa: E402

HEDEF_DIR = KOK / "testler" / "bayi_metinleri"
HEDEF = json.loads((HEDEF_DIR / "hedef.json").read_text(encoding="utf-8"))
BAYI = {"kod": "B01", "ad": "Deneme Bayi", "rol": "bayi", "numara": "900000000101"}


class _Metin(HTMLParser):
    def __init__(self):
        super().__init__(); self.parca: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "p", "li", "tr", "ul", "ol", "table"):
            self.parca.append("\n")
        if tag in ("td", "th"):
            self.parca.append(" | ")

    def handle_data(self, data):
        self.parca.append(data)


def gorunen_metin(html: str) -> str:
    p = _Metin(); p.feed(html)
    return "\n".join(" ".join(s.split()) for s in "".join(p.parca).splitlines() if s.strip()) + "\n"


def _katalog() -> Katalog:
    return Katalog(kabul_edilmis=set(HEDEF["canli_kabul"]))


def _karar(tmp_path, ad: str, adimlar: list[tuple[str, dict]], bayi=BAYI):
    k = Konusma(BAYI["numara"], kok=tmp_path / ad); k.plan_uretimi = True
    kat = _katalog(); r = None
    for i, (metin, t) in enumerate(adimlar):
        k.son_mesaj_id = f"wamid.BK28{ad}{i}"
        r = K.karar_ver(Talep.model_validate({"guven": "yuksek", "ozet": metin, **t}), k, bayi, kat, metin)
    return r


def test_nasil_calisir_hedefle_ayni():
    html = (KOK / "kanal" / "belgeler" / "nasil_calisir.html").read_text(encoding="utf-8")
    assert gorunen_metin(html) == (KOK / HEDEF["nasil_calisir"]).read_text(encoding="utf-8")


def test_selam_ve_anlasilmadi_hedefle_ayni(tmp_path):
    assert _karar(tmp_path, "selam", [("Merhaba", {"niyet": "selam"})]).mesaj == HEDEF["selam_hitapli"]
    hitapsiz = {**BAYI, "ad": ""}
    assert _karar(tmp_path, "selam0", [("Merhaba", {"niyet": "selam"})], bayi=hitapsiz).mesaj == HEDEF["selam_hitapsiz"]
    assert _karar(tmp_path, "diger", [("hmm", {"niyet": "diger"})]).mesaj == HEDEF["anlasilmadi"]


def test_yazili_olmayan_mesaj_hedefle_ayni():
    import worker as W
    g = {"id": "wamid.BK28FOTO", "sender": BAYI["numara"], "name": "", "role": "bayi", "bayi": BAYI, "type": "image", "text": ""}
    s = W.isle(g, {"mesaj_katmani": True, "patron_teknik_not": False})
    bayiye = [x["body"] for x in s["satirlar"] if x["to"] == BAYI["numara"]]
    assert bayiye == [HEDEF["yazili_olmayan"]]


@pytest.mark.parametrize("ornek", list(HEDEF["ornekler"]))
def test_ornek_talep_secenek_setine_gider(tmp_path, ornek):
    """Metindeki örnek, canlının kabul kümesiyle yönlendirmeye düşmez: prefabrikte sıralama sorusu + set, çelikte doğrudan set."""
    assert ornek in (K.ORNEK_PREFABRIK, K.ORNEK_CELIK) and ornek in HEDEF["selam_hitapli"]
    beklenen = HEDEF["ornekler"][ornek]
    adimlar = [(ornek, {"niyet": "yeni_talep", **beklenen["talep"]})]
    if beklenen["talep"]["yapi_turu"] == "prefabrik":
        adimlar.append(("fark etmez", {"niyet": "yeni_talep"}))
    r = _karar(tmp_path, "ornek", adimlar)
    assert r.eylem == "secenek", (r.eylem, r.gerekce, r.mesaj)
    assert [a["kod"] for a in r.secenek_seti["adaylar"]] == beklenen["set"]


def test_eski_ornek_yonlendirmeye_dusuyordu(tmp_path):
    """Neden değişti: eski selam örneği ("7x4 m, 2+1, ön verandalı") hazır plana gitmez."""
    r = _karar(tmp_path, "eski", [("7x4 m, 2+1, ön verandalı", {"niyet": "yeni_talep", "oda_programi": "2+1",
                                                               "dis_olcu": {"en_m": 4, "boy_m": 7}})])
    assert r.eylem == "yonlendir"


def test_sayfadaki_model_tablosu_aday_kaydiyla_ayni():
    """Sayfa §3'teki m² listeleri canlıda görünen modellerle aynı (çatı seçenekleri ayrı plan sayılmaz). Yeni model kabul edilince bu
    test kırılır: sayfa ve hedef birlikte, Lokman'ın onayıyla güncellenir."""
    bugun: dict = {}
    for a in SC.tek_plan(_katalog().gorunur_adaylar()):
        tur = "celik" if a.get("yapi_turu") == "celik" else "prefabrik"
        bugun.setdefault(tur, {}).setdefault(a["oda_programi"], []).append(int(round(float(a["katalog_m2"]))))
    bugun = {t: {o: sorted(m) for o, m in d.items()} for t, d in bugun.items()}
    assert bugun == HEDEF["sayfadaki_modeller"]
    metin = (KOK / HEDEF["nasil_calisir"]).read_text(encoding="utf-8")
    for tur, d in HEDEF["sayfadaki_modeller"].items():
        for oda, m2 in d.items():
            liste = ", ".join(str(x) for x in m2[:-1]) + (" ve " if len(m2) > 1 else "") + str(m2[-1])
            assert f"{oda} için {liste} m²" in metin, (tur, oda, liste)


def test_nasil_calisir_tek_sayfa(tmp_path, monkeypatch):
    import fitz
    import worker as W
    monkeypatch.setattr(W, "KANAL", tmp_path)
    yol, _ = W.nasil_calisir_pdf()
    d = fitz.open(yol)
    assert d.page_count == 1 and "Tek kat prefabrik, 2+1, 85 m²" in d[0].get_text()
