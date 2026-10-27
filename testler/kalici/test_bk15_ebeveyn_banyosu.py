"""BK-15 · O1 uçtan uca: bayi rehberinin konuşması (Bölüm 3). "Tek kat çelik, 3+1, 90 m² civarı" → yeni plan seçilir (r01) → "Ebeveyn
banyosu ekleyelim" → r02: kayıtlı işlem listesiyle (`plan_islem`, manuel arka uç; LLM çağrısı yok), gerçek genel motor, önce–sonra görseli,
bayiye "Uygulanan:" satırları. Kalıcı akış (gerçek Postgres, sahte WhatsApp).

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_bk15_ebeveyn_banyosu.py -q
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import fitz

from conftest import NUMARA_A, mesaj, sorgu, talep
from test_celik_akisi import BAYI_KART, YEDI, buton, isle_hepsi, kabul, son_rev
from test_plan_akisi import URETIM, duzenleyici, ornek, uretici  # noqa: F401 (fikstür)

T90 = talep(ozet="Tek kat çelik, 3+1, 90 m² civarı, kırma çatı", alan_m2=90, oda_programi="3+1", yapi_turu="celik", kat_sayisi=1,
            cati={"tip": "kirma"})


def test_o1_rehberdeki_konusma_ebeveyn_banyosu_r02(depo, wa, uretici, duzenleyici):
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("Tek kat çelik, 3+1, 90 m² civarı, kırma çatı", T90, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "secenek", r
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    assert st["adaylar"][0]["kod"].startswith("YENI-")
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{st['adaylar'][0]['kod']}"))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri", r
    time.sleep(1.1)
    d, _ = depo.konusma_oku(NUMARA_A)
    plan = d["uretilen_plan"]["plan"]
    assert {k: plan[k] for k in ("dis_olcu", "mahaller")} == {k: ornek("rehber_3arti1_90")[k] for k in ("dis_olcu", "mahaller")}

    duzenleyici["cevap"] = {"islemler": [{"op": "oda_ekle", "islev": "banyo", "alinti": "Ebeveyn banyosu ekleyelim"}], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("Ebeveyn banyosu ekleyelim", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri", r
    assert duzenleyici["cagri"] == 1 and duzenleyici["metin"] == "Ebeveyn banyosu ekleyelim"
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert rev["rev"] == 2 and y["uygulanan"] == ["Yatak Odası 3 17,1 → 12,7 m²", "Ebeveyn Banyo eklendi (4,4 m²)",
                                                  "pencere eklendi: Ebeveyn Banyo sağ 60/40", "kapı eklendi: Ebeveyn Banyo – Yatak Odası 3"]
    assert any(m["ad"] == "Ebeveyn Banyo" and m["islev"] == ["banyo"] for m in y["tanim"]["mahaller"])
    # r02: önce–sonra görseli, pafta PDF'i (gerçek genel motor), bayiye giden satır
    assert rev["ekler"]["gorsel"]["kaynak"] == "once_sonra" and Path(rev["ekler"]["gorsel"]["file"]).is_file()
    pdf = Path(sorgu(depo, "SELECT pdf_yolu FROM revizyonlar ORDER BY id DESC")[0]["pdf_yolu"])
    with fitz.open(pdf) as belge:
        assert len(belge) == 2 and "r02" in " ".join(w[4] for s in belge for w in s.get_text("words"))
    ozet = json.loads(next(pdf.parent.glob("*_pafta_ozet.json")).read_text(encoding="utf-8"))
    assert "Ebeveyn Banyo" in ozet["mahal_etiket_cm"]                                  # paftada etiketli (plan yazıları çizgi olarak basılır)
    govde = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC")[0]["govde"]
    assert "Uygulanan:" in govde and "Ebeveyn Banyo eklendi (4,4 m²)" in govde and "uygulayamadım" not in govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert any(m["ad"] == "Ebeveyn Banyo" for m in d["uretilen_plan"]["plan"]["mahaller"])
    assert NUMARA_A not in json.dumps(sorgu(depo, "SELECT sonuc FROM isler")[-1]["sonuc"])
