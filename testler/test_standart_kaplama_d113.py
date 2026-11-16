"""D-113 (BK-48; Lokman, kart 16 Kasım 2026 08:27:26 UTC "Standart: tek kat panel") · havuzdaki çelik ev standart kaplamayla.

Seçenek metni: "Havuzdaki her çelik ev tek kat panelle çizilir, bayi kaplamayı formda seçer. Bugün sandviç panelli 10 çelik ev değişir."
Tanım dosyaları asıl projedir ve değişmez (D-103, D-07); karar yeni projenin zarfına `standart_kaplama` işlemini koyar, worker çizimi ve
listeyi bu işlemle üretir. Bu dosya beş şeyi denetler:
1. Depoda işlem alan evler tam bu on evdir (KT-01 … KT-10); öteki çelik tanımlar zaten standarttır.
2. İşlem yalnız `cati.kaplama`'yı değiştirir; girdi değişmez; standart tanımda tanım aynen.
3. Karar: yeni projede işlem zarfta ilk sırada, bayiye "Uygulanan" diye yazılmaz; revizyonda birikir; bu karardan önce açılmış projenin
   revizyonu işlemsiz sürer (bugünkü plan bugünkü kaplamayla).
4. Worker'ın çizim tanımı standart kaplamayı okur; Ç8801'in zarfı değişmez.
5. Liste (KT-06, en küçük fark): yalnız çatı kaplaması satırları değişir; panel adedi ve boyu aynı, kapama düşer, vida 5,5 × 76 olur.
6. Hedef örnek (D-28): 10 evin önce/sonra kıyası Lokman'ın onayladığı tabloyla (`testler/celik/d113/hedef.json`; kart 16 Kasım 2026
   08:57:28 UTC "Doğru, böyle kalsın") aynı.

LLM, Postgres, ağ ve WhatsApp yok. Koşum: python -m pytest testler/test_standart_kaplama_d113.py -q
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from araclar import celik_kaplama_kiyas as KK
from beyin import celik, varyant
from beyin import karar as K
from beyin.katalog import Katalog
from beyin.konusma import Konusma
from beyin.sema import Talep
from kanal import worker

KOK = Path(__file__).resolve().parents[1]
BAYI = {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi", "numara": "900000000101"}
ON_EV = {"KT-01", "KT-02", "KT-03", "KT-04", "KT-05", "KT-06", "KT-07", "KT-08", "KT-09", "KT-10"}


def _tanim(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def test_islem_alan_evler_tam_on_ev():
    alan, almayan = set(), set()
    for yol in KK.celik_tanimlari():
        t = json.loads(yol.read_text(encoding="utf-8"))
        (alan if varyant.standart_kaplama_islemi(t) else almayan).add(KK.kod(t, yol))
    assert alan == ON_EV
    assert {"Ç8801", "Ç8201", "KT-11", "KT-12", "KT-13"} <= almayan and not alan & almayan
    # işlemin değeri kitabın baz paketi (çelikte tek kat panel, M-16); asıl kaplama kayıtta
    [op] = varyant.standart_kaplama_islemi(_tanim("modeller/KT02.json"))
    assert op == {"op": "standart_kaplama", "kaplama": "tek_kat_panel", "asil": "sandvic_panel",
                  "aciklama": "çatı kaplaması tek kat panel (standart)"}


def test_islem_yalniz_cati_kaplamasini_degistirir():
    t0 = _tanim("modeller/havuz/KT05.json")
    once = copy.deepcopy(t0)
    [op] = varyant.standart_kaplama_islemi(t0)
    t1 = varyant.tanim_uygula(t0, op)
    assert t0 == once and t1 is not t0                                            # saf: tanım dosyasının içeriği (asıl proje) değişmez
    assert varyant.kaplama_oku(t1) == "tek_kat_panel" and t1["cati"]["kaplama_kaynak"].startswith("standart (D-113)")
    assert {a: v for a, v in t1.items() if a != "cati"} == {a: v for a, v in t0.items() if a != "cati"}
    assert {a: v for a, v in t1["cati"].items() if not a.startswith("kaplama")} == \
        {a: v for a, v in t0["cati"].items() if not a.startswith("kaplama")}
    c = _tanim("modeller/C8801.json")
    assert varyant.standart_kaplama_islemi(c) == [] and varyant.tanim_uygula(c, op) == c   # standart tanım aynen
    for kotu in ("trapez_sac", None):
        with pytest.raises(varyant.VaryantHatasi):
            varyant.tanim_uygula(t0, {"op": "standart_kaplama", "kaplama": kotu})
    # bayinin formdaki seçimi standart işlemden sonra gelir (D-97): son söz bayinin
    t2 = varyant.tanim_uygula(t1, {"op": "cati_kaplamasi", "kaplama": "sandvic_panel"})
    assert varyant.kaplama_oku(t2) == "sandvic_panel"


class Sohbet:
    def __init__(self, kok: Path):
        self.k = Konusma("900000000101", kok=kok)
        self.kat = Katalog()

    def yaz(self, metin: str, **alan):
        alan.setdefault("niyet", "revizyon" if self.k.d.get("son_is_emri") else "yeni_talep")
        t = Talep(guven="yuksek", ozet=alan.pop("ozet", metin[:80]), **alan)
        return K.karar_ver(t, self.k, BAYI, self.kat, metin)

    @property
    def yapi(self) -> dict:
        return (self.k.d.get("son_is_emri") or {}).get("yapi") or {}


def test_karar_yeni_projede_standart_kaplama(tmp_path):
    s = Sohbet(tmp_path)
    k = s.yaz("KT-01", katalog_kodu="KT01", yapi_turu="celik")
    assert k.eylem == "is_emri" and k.revizyon == 1, k.mesaj
    assert [d["op"] for d in s.yapi["degisiklikler"]] == ["standart_kaplama"] and s.yapi["bu_revizyon"] == []
    assert s.yapi["uygulanan"] == [] and "Uygulanan" not in k.mesaj and "standart" not in k.mesaj and "kaplama" not in k.mesaj
    assert s.yapi["tanim"] == "modeller/KT01.json" and celik.tanim_dogrula(s.yapi)        # tanım dosyası (asıl proje) aynen, sha tutar
    t = worker._cizim_tanimi(s.yapi["tanim"], s.yapi["degisiklikler"])
    assert varyant.kaplama_oku(t) == "tek_kat_panel" and varyant.kaplama_oku(celik.tanim_oku(s.yapi)) == "sandvic_panel"
    # revizyonda işlem birikir, bayinin değişikliği ondan sonra
    k = s.yaz("dış boya rengi beyaz olsun", bina_ozellikleri={"Dış Boya Rengi": "beyaz"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and [d["op"] for d in s.yapi["degisiklikler"]] == ["standart_kaplama"], k.mesaj
    assert s.yapi["onceki"]["degisiklikler"][0]["op"] == "standart_kaplama"                # önce/sonra görselinin "önce"si de standart


def test_karardan_once_acilmis_proje_bugunku_kaplamayla_surer(tmp_path):
    s = Sohbet(tmp_path)
    assert s.yaz("KT-02", katalog_kodu="KT02", yapi_turu="celik").eylem == "is_emri"
    s.k.d["son_is_emri"]["yapi"]["degisiklikler"] = []                                    # D-113'ten önce çizilmiş r01'in zarfı
    k = s.yaz("dış boya rengi beyaz olsun", bina_ozellikleri={"Dış Boya Rengi": "beyaz"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.yapi["degisiklikler"] == [], k.mesaj
    assert varyant.kaplama_oku(worker._cizim_tanimi(s.yapi["tanim"], s.yapi["degisiklikler"])) == "sandvic_panel"


def test_standart_modelin_zarfi_degismez(tmp_path):
    s = Sohbet(tmp_path)
    k = s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik")
    assert k.eylem == "is_emri" and s.yapi["degisiklikler"] == [], k.mesaj


def test_liste_yalniz_cati_kaplamasi_satirlari_degisir(tmp_path):
    t = _tanim("modeller/havuz/KT06.json")
    [op] = varyant.standart_kaplama_islemi(t)
    once = KK._uret(t, tmp_path / "once")
    sonra = KK._uret(varyant.tanim_uygula(t, op), tmp_path / "sonra")
    assert once["cati_kaplamasi_anahtar"] == "sandvic_panel" and sonra["cati_kaplamasi_anahtar"] == "tek_kat_panel"
    fark = {(f["kalem"], f["boyut"]): (f["once"] and f["once"]["adet"], f["sonra"] and f["sonra"]["adet"]) for f in KK.liste_farki(once, sonra)}
    assert fark == {("Sandviç panel", "L 5260 · 100 cm kapatır"): (22, None), ("Sandviç panel kapaması", "L 2500"): (9, None),
                    ("Trapez vida (5,5 × 110; sandviç panel)", "adet"): (750, None),
                    ("Tek kat panel", "L 5260 · 100 cm kapatır"): (None, 22), ("Trapez vida (5,5 × 76; tek kat panel)", "adet"): (None, 750)}


def test_on_evin_listesi_hedefle_ayni(tmp_path):
    """D-28 kıyası: araç bugünkü kodla 18 çelik tanımı yeniden kıyaslar; sonuç onaylı hedefle satır satır aynı olmalı."""
    hedef = json.loads((KOK / "testler" / "celik" / "d113" / "hedef.json").read_text(encoding="utf-8"))
    assert KK.kiyas(tmp_path) == hedef["evler"]
