"""BK-92 (D-169) · Portman WhatsApp kullanma kılavuzu (araclar/kilavuz): kılavuzdaki Portman mesajları main'deki karar kodunun bugünkü
cevaplarıyla aynı (hedef örnek testler/kilavuz/hedef.json, D-28 madde 3); sayfa kurulur ve Portman'ın /rehber/ yayın denetiminden geçer
(kanal/rehber_yayin.py); kılavuz imi montaj rehberinin denetimini gevşetmez. LLM, WhatsApp, Postgres ve canlı yok.

Bir Portman mesajı bilerek değiştiyse: kılavuzun o adımı yeniden okunur, hedef Lokman'ın onayıyla yeniden yazılır (D-02); test gevşetilmez.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
for _y in (KOK, KOK / "kanal"):
    if str(_y) not in sys.path:
        sys.path.insert(0, str(_y))

import rehber_yayin as RY  # noqa: E402
from araclar.kilavuz import senaryo as S, uret as U  # noqa: E402

HEDEF = KOK / "testler" / "kilavuz" / "hedef.json"


@pytest.fixture(scope="module")
def sayfa():
    return U.sayfa()


def test_portman_mesajlari_hedefle_ayni(sayfa):
    hedef = json.loads(HEDEF.read_text(encoding="utf-8"))["mesajlar"]
    simdi = U.hedef_ozeti(sayfa[1])
    farkli = sorted(a for a in set(hedef) | set(simdi) if hedef.get(a) != simdi.get(a))
    assert not farkli, "kılavuzdaki Portman mesajı değişti (kılavuzun adımına bakın, hedef Lokman'ın onayıyla): " + ", ".join(
        f"{a}: {simdi.get(a)!r} ≠ hedef {hedef.get(a)!r}" for a in farkli)[:3000]


def test_sayfa_yayin_denetiminden_gecer(sayfa):
    s = sayfa[0]
    sorun, bilgi = RY.denetle(s.encode("utf-8"))
    assert sorun == [] and bilgi["baslik"] == "Portman WhatsApp Kılavuzu"
    assert "__VERI__" not in s and "__GORSELLER__" not in s
    veri = json.loads(re.search(r"const VERI=(\{.*?\});\n", s).group(1))
    assert [len(b["adimlar"]) for b in veri["bolumler"]] == [8, 7, 4]
    gorsel = json.loads(re.search(r"const IMG=(\{.*?\});\n", s).group(1))
    assert sorted(gorsel) == ["cati", "kaynak", "plan", "plan3", "r02", "set", "yerlesim"]
    assert all(v.startswith("data:image/jpeg;base64,") for v in gorsel.values())


def test_kilavuzda_ic_not_yok(sayfa):
    """Bayiye giden sayfada iç not (pano, "için not", "yeni sürümle") ve bayi numarası yok."""
    metin = json.dumps(json.loads(U.METIN.read_text(encoding="utf-8"))["bolumler"], ensure_ascii=False).lower()
    for y in ("pano 2", "için not", "yeni sürümle", "lokman bey için"):
        assert y not in metin, y
    assert S.BAYI["numara"] not in sayfa[0]


def test_bilinmeyen_kaynak_durur():
    m = S.uret()
    with pytest.raises(S.KilavuzHatasi):
        U.ogeleri_coz({"bolumler": [{"baslik": "x", "adimlar": [{"baslik": "x", "metin": "x",
                                                                    "ogeler": [{"tur": "in", "kaynak": "yok", "saat": "1"}]}]}]}, m)
    with pytest.raises(S.KilavuzHatasi):
        U.ogeleri_coz({"bolumler": [{"baslik": "x", "adimlar": [{"baslik": "x", "metin": "x",
                                                                    "ogeler": [{"tur": "sec", "kaynak": "b1.cati", "sira": 0}]}]}]}, m)


def test_kilavuz_imi_denetimi_gevsetmez(sayfa):
    s = sayfa[0]
    assert "başlık" in " ".join(RY.denetle(s.replace(RY.KILAVUZ_BASLIGI, "<title>X</title>").encode())[0])
    dis = s.replace("</body>", '<img src="https://ornek.com/x.png"></body>')
    assert any("izinsiz dış adres" in x for x in RY.denetle(dis.encode())[0])
    tel = s.replace("</body>", "<p>0532 123 45 67</p></body>")
    assert any("telefon" in x for x in RY.denetle(tel.encode())[0])
    # İmsiz sayfa montaj rehberi gibi denetlenir: kılavuzun başlığı rehber imlerini karşılamaz.
    imsiz = RY.denetle(s.replace(RY.KILAVUZ_IMI, "").encode())[0]
    assert any("Montaj Rehberi" in x for x in imsiz) and any("rehber imi yok" in x for x in imsiz)
