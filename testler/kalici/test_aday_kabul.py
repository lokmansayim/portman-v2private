"""İE-08 Adım 8 · `araclar/aday_kabul.py` (K-A10): yalnız verilen kodlar 'gecerli' + kabul kaydıyla yazılır, `kabul_edilmis_adaylar`
yalnız onları döndürür; yeniden koşu aynı sonucu verir (upsert); ad çıktıya girmez; adaylar.json'da olmayan kod DUR; --kuru yazmaz.
D-11 (Lokman, 13 Ekim 2026): geliştirme döneminde kabul eden Lokman — `--kim` verilmezse "Lokman", kayıtta dayanak `karar: D-11`
(13 Ekim'de güncellendi: önceki vaka "Deneme Mühendis" adıyla ve `karar`sız kayıt bekliyordu; gevşetme değil, kararın kendisi).
Gerçek Postgres (conftest `depo`), gerçek `beyin/veri/adaylar.json` (yedi çelik aday)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "araclar"))

import aday_kabul as AK  # noqa: E402

ADAYLAR = KOK / "beyin" / "veri" / "adaylar.json"
YEDI = ["Ç8201", "Ç8801", "Ç8801K", "Ç8801L", "KT01", "KT02", "KT03"]


def test_adaylar_json_yedi_celik_aday():
    d = json.loads(ADAYLAR.read_text(encoding="utf-8"))
    assert sorted(a["kod"] for a in d) == sorted(YEDI)
    assert all(a["durum"] == "gecerli" and a["motor"] == "genel" and a["yapi_turu"] == "celik" for a in d)


def test_d11_dayanagi_yalniz_gelistirme_donemi_kabul_edenine():
    """Kod incelemesi (13.10, CR21): `karar: D-11` yalnız kabul eden Lokman'sa yazılır; başka biri kabul ederse dayanak boş kalır."""
    adaylar = json.loads(ADAYLAR.read_text(encoding="utf-8"))
    kayit, _ = AK.kabul_kayitlari(adaylar, ["Ç8801"], AK.KABUL_EDEN, "2026-10-13", "", "p")
    assert kayit[0]["muhendis_kabulu"]["karar"] == "D-11"
    kayit, _ = AK.kabul_kayitlari(adaylar, ["Ç8801"], "Deneme Kabul", "2026-10-13", "", "p")
    assert kayit[0]["muhendis_kabulu"]["karar"] is None


def test_yalniz_verilen_kodlar_kabul_kaydi_olur(depo, monkeypatch, capsys):
    monkeypatch.setenv("PORTMAN_PG_DSN", depo.dsn)
    assert depo.kabul_edilmis_adaylar() == set()
    rc = AK.main(["--kodlar", "Ç8801,C8801-K, ç8801l", "--tarih", "2026-10-13", "--not", "üç çatı kabul", "--paket", "2026-10-13"])
    cikti = capsys.readouterr().out
    assert rc == 0 and "Lokman" not in cikti and "L…" in cikti                                   # --kim yok: kabul eden Lokman (D-11); ad çıktıya girmez
    assert depo.kabul_edilmis_adaylar() == {"Ç8801", "Ç8801K", "Ç8801L"}
    with depo.baglan() as c:
        r = c.execute("SELECT kod, durum, referans_model, muhendis_kabulu, kaynak, ozet, denetim FROM adaylar ORDER BY kod").fetchall()
    assert [x["kod"] for x in r] == ["Ç8801", "Ç8801K", "Ç8801L"] and all(x["durum"] == "gecerli" for x in r)
    assert r[0]["muhendis_kabulu"] == {"kim": "Lokman", "tarih": "2026-10-13", "not": "üç çatı kabul", "karar": "D-11"}
    assert r[1]["referans_model"] == "Ç8801" and r[1]["kaynak"]["motor"] == "genel" and r[1]["kaynak"]["tanim"] == "modeller/C8801K.json"
    assert r[0]["ozet"]["varyantlar"] == ["Ç8801K", "Ç8801L"] and r[0]["denetim"]["kabul_paketi"] == "2026-10-13"
    # yeniden koşu (aynı kodlar + bir yenisi), başka bir kabul edenle: upsert, eskiler aynı kalır; ad yine çıktıya girmez (K09)
    assert AK.main(["--kodlar", "Ç8801,Ç8801K,Ç8801L,KT01", "--kim", "Deneme Kabul", "--tarih", "2026-10-13"]) == 0
    cikti = capsys.readouterr().out
    assert "Deneme" not in cikti and "D…" in cikti
    assert depo.kabul_edilmis_adaylar() == {"Ç8801", "Ç8801K", "Ç8801L", "KT01"}
    # kabul edilmeyen aday: kayıt yok → kalıcı akışın kataloğunda görünmez (K-A10)
    from beyin.katalog import Katalog
    k = Katalog(kabul_edilmis=depo.kabul_edilmis_adaylar())
    assert k.aday("KT02") is None and k.aday("Ç8801") is not None and {a["kod"] for a in k.gorunur_adaylar()} == {"Ç8801", "Ç8801K", "Ç8801L", "KT01"}


def test_olmayan_kod_dur_ve_kuru_yazmaz(depo, monkeypatch, capsys):
    monkeypatch.setenv("PORTMAN_PG_DSN", depo.dsn)
    assert AK.main(["--kodlar", "Ç8801,Ç9999", "--kim", "X", "--tarih", "2026-10-13"]) == 2 and "Ç9999" in capsys.readouterr().out
    assert AK.main(["--kodlar", "Ç8801", "--kim", "X", "--tarih", "13.10.2026"]) == 2
    assert AK.main(["--kodlar", "Ç8801", "--kim", "X", "--tarih", "2026-10-13", "--kuru"]) == 0 and "KURU" in capsys.readouterr().out
    assert depo.kabul_edilmis_adaylar() == set()
