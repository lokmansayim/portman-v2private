"""Arşivin 2019–2020 yükleme listesi (`araclar/hdd_turev/liste_oku.py`) ve plandan çıkan kalemlerin kıyası (`plan_kalem.py`).

Gerçek liste depoya girmez (TC kimlik no, telefon, adres); şablon burada kodla yazılır: TEKLİF (evin listesi), SEVKİYAT (şablondan kalan
başka ev), "KOD:" grup satırı. Kıyas: eski adlar kalem kalem eşlenir; dolu pano tam boy eşdeğeriyle; listede ölçüsüz pencere toplamla;
kolu pencere sayılmaz; 1250 mm'den geniş yazılmış dolu pano toplam ene girmez ve ayrıca yazılır.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "araclar" / "hdd_turev"))
openpyxl = pytest.importorskip("openpyxl")
import liste_oku  # noqa: E402
import plan_kalem as PK  # noqa: E402


def _sayfa(ws, satirlar):
    ws.append(["PORTATİF EV"]); ws.append([]); ws.append(["Müşteri: Deneme Kişi"]); ws.append([])
    ws.append(["S", "Malzeme", "Malzeme Ölçüsü", "Adet"])
    for i, r in enumerate(satirlar, 1):
        ws.append([i, *r])


def test_teklif_sayfasi_okunur_sevkiyat_okunmaz(tmp_path):
    wb = openpyxl.Workbook()
    _sayfa(wb.active, [("PANOLAR", "KOD:", None), ("100'LÜK YAPIŞTIRMA DOLU PANO", "100*1250*2500", 14), ("KÖŞE DİREĞİ", "100*100*2500", 4)])
    wb.active.title = "TEKLİF"
    _sayfa(wb.create_sheet("SEVKİYAT"), [("100'LÜK YAPIŞTIRMA DOLU PANO", "100*1250*2500", 99)])
    yol = tmp_path / "liste.xlsx"
    wb.save(yol)
    r = liste_oku.oku_liste(yol)
    assert r["sayfa"] == "TEKLİF"
    adet = {x["malzeme"]: x["adet"] for x in r["satirlar"] if x.get("adet")}
    assert adet == {"100'LÜK YAPIŞTIRMA DOLU PANO": 14, "KÖŞE DİREĞİ": 4}               # grup satırı ve SEVKİYAT yok
    assert "Deneme" not in json.dumps(r, ensure_ascii=False)


def test_teklif_yoksa_hata(tmp_path):
    wb = openpyxl.Workbook(); wb.active.title = "SEVKİYAT"
    yol = tmp_path / "liste.xlsx"; wb.save(yol)
    cikti = tmp_path / "l.json"
    assert liste_oku.main([str(tmp_path), json.dumps({"HD-1": "liste.xlsx"}), str(cikti)]) == 0
    assert "TEKLİF sayfası yok" in json.loads(cikti.read_text())["HD-1"]["hata"]


def test_plan_kalemleri():
    g = lambda m, b, n: {"malzeme": m, "boyut": b, "adet": n}
    gercek = [g("100'LÜK YAPIŞTIRMA DOLU PANO", "100*1250*2500", 14), g("100'LÜK YAPIŞTIRMA DOLU PANO", "100*6325*2500", 1),
              g("KÖŞE DİREĞİ", "100*100*2500", 4), g("H ( DÜBELLİ )", "100*100*2500", 10), g("3 LÜ H ( STANDART )", "60*60*2500", 2),
              g("ÇEKTİRME U'SU", "60*2440", 1), g("AMERİKAN KAPI / 2 SOL", "80*198", 2), g("ÇELİK KAPI / SAĞ", "90*205", 1),
              g("PVC PENCERE+PERVAZ+MATİK", "Adet", 3), g("PVC PENCERE KOLU", "Adet", 3)]
    m = lambda k, o, n: {"kalem": k, "olcu": o, "adet": n}
    motor = [m("100'lük yapıştırma dolu pano", "100 × 1250 × 2500", 12), m("100'lük yapıştırma dolu pano", "100 × 625 × 2500", 4),
             m("10'luk köşe direği 100 × 100", "100 × 100 × 2500", 4), m("H 100 (dış pano eki)", "100 × 100 × 2500", 10),
             m("3'lü H standart 60 (iç T)", "L 2500", 2), m("Çektirme U'su 60", "60 × 2440", 1),
             m("Amerikan kapı (80'lik kanat) (SOL)", "82 × 196", 2), m("Prefabrik çelik kapı (SAĞ)", "900 × 2000", 1),
             m("PVC pencere", "120/120", 2), m("PVC vasistas", "60/40", 1)]
    S = {s["kalem"]: s for s in PK.kiyasla(gercek, motor)}
    d = S["100'lük dolu pano"]
    assert (d["gercek"], d["motor"]) == (15, 16) and d["gercek_tam_boy"] == d["motor_tam_boy"] == 14 and PK.ayni_mi(d)
    assert d["gercek_gecersiz_en"] == [("100*6325*2500", 1)]                       # liste düzeltilmez, ayrıca yazılır
    for k in ("Köşe direği 100", "H 100 (dış pano eki)", "3'lü H 60", "Çektirme U'su 60", "İç kapı", "Dış kapı"):
        assert PK.ayni_mi(S[k]), S[k]
    p = S["Pencere (listede ölçü yok, toplam)"]
    assert (p["gercek"], p["motor"]) == (3, 3)                                       # kol pencere sayılmaz
