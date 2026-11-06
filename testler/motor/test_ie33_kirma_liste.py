"""İE-33 PR-2 · İki uçlu (dörtomuz) kırmanın (AP-01) yükleme listesi: çatı satırları çatının kendi kenarlarından, makas planı paftadan.

AP-01'in geometrisi İE-17'nin İş Emri'si (`testler/cizim/evler/AP01.json`; ön onay çizimini Lokman 6 Kasım 2026 21:23'te onayladı); kör
ölçümün İş Emri'si (`testler/kor/projeler/AP01/is_emri.json`) aynı geometri ve paftanın özellik tablosu. Makas sayıları paftanın makas ve
dere yerleşim planından (s. 6): M10–M20 ana makas (mahyaya dik, 11), M02–M08 ve M22–M28 kırma uçlarındaki kısa makaslar (7 + 7), M01, M09,
M21, M29 köşelerdeki çapraz makas (4); kırma uçlarının altında CP1–CP6 çatı paneli. Paftadaki ölçüler makas yüzünden yüzünedir
(117,5 + 8 = 125,5; 54,75 + 8 = 62,75): makaslar saçak duvarının pano eklemlerinde. Kendi listemiz gerçek liste açılmadan önce commit'lendi
(cd3a443); gerçek listede "ÇATI MAKAS PANELLERİ" 29 ve "ÇATI PANELLERİ" 6. Mahyası y boyunca olan iki uçlu kırma paftayla kıyaslanmadı:
liste yazılmaz. LLM yok.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

AP01 = KOK / "testler" / "cizim" / "evler" / "AP01.json"
AP01_KOR = KOK / "testler" / "kor" / "projeler" / "AP01" / "is_emri.json"
AP15 = KOK / "testler" / "cizim" / "evler" / "AP15.json"
AP27 = KOK / "testler" / "kor" / "projeler" / "AP27" / "is_emri.json"


def _ie(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _adet(L: dict, bas: str) -> dict:
    out: dict = {}
    for s in L["satirlar"]:
        if s["kalem"].startswith(bas):
            out[s["kalem"]] = out.get(s["kalem"], 0) + s["adet"]
    return out


def test_makas_plani_paftayla():
    c = PL.model_motor(_ie(AP01))["cati"][0]
    km = c["kirma_makas"]
    assert km["tur"] == "iki_uclu" and (km["ana"], km["kisa"], km["capraz"], km["kose_kisa"]) == (11, 14, 4, 0)
    # M10–M20: arka duvarın pano eklemleri (yarım panolarınki dahil); 1322,75 uç duvara 77 cm, makas yok
    assert km["ana_x_cm"] == [130.5, 256.0, 381.5, 507.0, 632.5, 758.0, 820.75, 946.25, 1071.75, 1134.5, 1260.0]
    sol, sag = km["uclar"]
    assert (sol["uc"], sol["kisa"], sol["cati_paneli"], sol["bant_cm"]) == ("sol", 7, 3, 130.5)
    assert (sag["uc"], sag["kisa"], sag["cati_paneli"], sag["bant_cm"]) == ("sağ", 7, 3, 140.0)
    # uç duvarın eklemleri iki uçta aynı (sağda veranda önünde duvar yok, 237 ızgarayla); soldaki 864,5 kırma noktasına 7 cm: makas yok
    assert sol["kisa_y_cm"][1:-1] == sag["kisa_y_cm"][1:-1] == [237.0, 362.5, 488.0, 613.5, 739.0]
    # kırma noktaları (paftada makas yüzünden: sol 128,46 ve 871,54; sağ 155,87 ve 844,13), en çok 1 cm
    for u, (a, b) in ((sol, (128.46, 871.54)), (sag, (155.87, 844.13))):
        assert abs(u["kisa_y_cm"][0] - a) < 1 and abs(u["kisa_y_cm"][-1] - b) < 1
    assert c["cati_paneli"] == 6 and c["kalkan"] == 0 and c["alin_kenarlari_m"] == [] and c["dere_serbest_uc"] == 0


def test_liste_satirlari():
    L = PL.is_emrinden(_ie(AP01))
    makas = {s["kalem"]: (s["olcu"], s["adet"]) for s in L["satirlar"] if s["kalem"].startswith(("Makas (", "Çatı paneli"))}
    assert makas == {"Makas (ana, mahyaya dik) · ana çatı": ("açıklık 10000", 11),
                     "Makas (kısa, sol uç) · ana çatı": ("L 1605", 7), "Makas (kısa, sağ uç) · ana çatı": ("L 1700", 7),
                     "Makas (çapraz, kırma, sol uç) · ana çatı": ("L 2253", 2), "Makas (çapraz, kırma, sağ uç) · ana çatı": ("L 2523", 2),
                     "Çatı paneli (makas arası) · ana çatı": ("—", 6)}
    assert L["girdi_ozeti"]["makas"] == 29
    # kalkan ve alın yok; dere dört saçakta kesintisiz
    assert {k: v for k, v in _adet(L, "Baş makas").items()} == {"Baş makas omegası": 0, "Baş makas Z'si": 0, "Baş makas betopanı": 0}
    assert _adet(L, "Alın sacı") == {"Alın sacı (30'luk)": 0} and _adet(L, "Dere kapağı") == {"Dere kapağı": 0}


def test_kor_is_emri_geometrisi_ayni():
    """Kör ölçümün İş Emri'si İE-17'ninkinin geometrisiyle aynı; yalnız özellikler, alıcıya ait kalemler ve varsayımlar eklendi."""
    a, b = _ie(AP01), _ie(AP01_KOR)
    for k in ("yapi", "mahaller", "acik_sinirlar", "acikliklar", "dikmeler", "cati"):
        assert a[k] == b[k], k
    assert b["ozellikler"]["Çatı Kaplaması"] == "Sandviç Panel" and b["alici_ait"]["kalemler"] == ["vitrifiye"]
    assert b["varsayimlar"][:len(a["varsayimlar"])] == a["varsayimlar"]
    L = PL.is_emrinden(b)
    assert L["girdi_ozeti"]["makas"] == 29 and sum(_adet(L, "Sandviç panel (").values()) == 36


def test_mahyasi_y_boyunca_yazilmaz():
    ie = _ie(AP15)
    ie["cati"] = {k: v for k, v in ie["cati"].items() if k in ("egim_yuzde", "sacak_cm", "topuk_cm", "makas_yonu", "makas_ekseni")}
    ie["cati"]["tip"] = "kirma"
    with pytest.raises(PL.ListeYazilmaz, match="mahya y boyunca"):
        PL.model_motor(ie)


def test_tek_uclu_kirma_aynen():
    """AP-27'nin tek uçlu kırması (İE-29) aynen: 25 makas, 6 panel."""
    L = PL.is_emrinden(_ie(AP27))
    assert L["girdi_ozeti"]["makas"] == 25 and _adet(L, "Çatı paneli") == {"Çatı paneli (makas arası) · ana çatı": 6}
