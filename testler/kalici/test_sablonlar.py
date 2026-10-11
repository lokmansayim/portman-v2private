"""İE-07 · kanal/sablonlar.py: onaylı şablon metinleri (Karar 2), değişkenler (boş gitmez), giden satırı biçimi. Postgres gerekmez."""
from __future__ import annotations

import depo as D
import sablonlar as S
import worker as W


def test_metinler_karar_2_ile_ayni_ve_degiskenle_baslamaz_bitmez():
    assert S.PATRON_BILDIRIM["metin"] == "Portman: {{1}} kodlu bayinin {{2}} numaralı talebi sizi bekliyor. Ayrıntıyı panelden görebilirsiniz."
    assert S.BAYI_DOSYALAR_HAZIR["metin"] == "Merhaba {{1}}, {{2}} numaralı projenizin dosyaları hazır. Bu mesaja yanıt verirseniz dosyaları buradan gönderebiliriz."
    for s in (S.PATRON_BILDIRIM, S.BAYI_DOSYALAR_HAZIR):
        assert not s["metin"].startswith("{{") and not s["metin"].endswith("}}")       # Meta: gövde değişkenle başlamaz/bitmez
        assert s["anahtar"].startswith("sablon_") and s["dugme"] in ("url", "quick_reply") and len(s["ornek"]) == 2
    assert S.BAYI_DOSYA_CEVABI == "Teşekkürler, dosyalarınızı bu sohbetten iletiyoruz."


def test_satir_id_worker_ve_depo_ile_ayni():
    assert S.satir_id("wamid.X", 101) == W.satir_id("wamid.X", 101) == D.satir_id("wamid.X", 101)


def test_talep_kimligi_hic_bos_gitmez():
    assert S.talep_kimligi("PM-B1-20261011-3", None, "wamid.A") == "PM-B1-20261011-3"
    assert S.talep_kimligi(None, "PM-B1-20261011-2", "wamid.A") == "PM-B1-20261011-2"
    assert S.talep_kimligi("  ", "", "wamid.A").startswith("T-") and len(S.talep_kimligi(None, None, "wamid.A")) == 10
    assert S.talep_kimligi(None, None, "wamid.A") == "T-" + D.kimlik_izi("wamid.A")[:8].upper()   # günlükteki izle aynı
    assert S.bayi_kodu({"kod": "B0101"}, "900000000101") == "B0101" and S.bayi_kodu(None, "900000000101") == "B0101"


def test_hitap_sirasi():
    assert S.hitap_metni({"hitap": "Ahmet Bey", "ad": "Ahmet"}) == "Ahmet Bey"
    assert S.hitap_metni({"hitap": "", "ad": "Ayşe Yılmaz"}) == "Ayşe Yılmaz"
    assert S.hitap_metni({"hitap": " ", "ad": ""}) == "Sayın Bayimiz" and S.hitap_metni(None) == "Sayın Bayimiz"


def test_patron_ve_bayi_satirlari():
    gelen = {"id": "wamid.G1", "sender": "900000000101"}
    p = S.patron_bildirim_satiri(gelen, 3, {"kod": "B0101"}, None, None)
    assert p["id"] == W.satir_id("wamid.G1", 3) and p["kind"] == "template" and p["to"] == "PATRON" and p["tur"] == "bildirim"
    assert p["sablon_anahtari"] == "sablon_patron_bildirim" and p["pencere_kapaliysa"] is True and p["kaynak"] == "ajan"
    assert p["sablon"] == {"dil": "tr", "govde": ["B0101", "T-" + D.kimlik_izi("wamid.G1")[:8].upper()],
                           "dugmeler": [{"sub_type": "url", "index": 0, "text": "konusma/900000000101"}]}
    assert "ad" not in p["sablon"]                                  # Meta adı gönderim anında ayardan
    assert p["body"].startswith("Portman: B0101 kodlu bayinin T-") and p["body"].endswith("panelden görebilirsiniz.")
    b = S.bayi_dosyalar_hazir_satiri("wamid.G1", 101, "900000000101", {"hitap": "Ahmet Bey"}, "PM-B0101-20261011-1")
    assert b["seq"] == 101 and b["to"] == "900000000101" and b["kaynak"] == "panel" and b["pencere_kapaliysa"] is False
    assert b["sablon"]["govde"] == ["Ahmet Bey", "PM-B0101-20261011-1"]
    assert b["sablon"]["dugmeler"] == [{"sub_type": "quick_reply", "index": 0, "payload": "dosya:PM-B0101-20261011-1"}]
    assert b["body"] == "Merhaba Ahmet Bey, PM-B0101-20261011-1 numaralı projenizin dosyaları hazır. Bu mesaja yanıt verirseniz dosyaları buradan gönderebiliriz."
    for r in (p, b):                                                # worker.giden_metin ile aynı anahtarlar + şablon alanları
        assert set(W.giden_metin(gelen, "x", 1)) <= set(r)
