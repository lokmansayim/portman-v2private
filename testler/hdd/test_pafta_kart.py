"""Arşiv montaj planından proje kartı taslağı (`araclar/hdd_turev/pafta_kart.py`): iki şablon, uydurma çizimle.

Gerçek pafta depoya girmez (kişisel veri); burada iki şablonun okunan biçimi kodla çizilir:
- 2019–2020: başlık "<ad> <n> M2" üstte, "MONTAJ VE ELEKTRİK PLANI" altta, oda yazısı "<ad>\\P<m²> m²", ölçüler cm;
  aynı plan ikinci kez (ölçüsüz) çizili, sağında komşu bir çizim (daha uzun ölçüsüyle) bölgeye yapışık.
- İkranur 2016–2018: kapalı sayfa çerçevesi, "Montaj Ve Elektrik Planı" sol altta, "<n> m² PREFABRİK BİNA" antette,
  teknik bilgiler tablosu ("Dış Duvarlar:" …), oda yazısı yok.
- İkranur A4 2019: kapalı sayfa çerçevesi, "Montaj Ve Elektrik Planı" altta ortada, antet sağ altta ("<ad>\\P74 m² PREFABRİK
  KONUT"), teknik tabloda değer etiketin altında, ölçüler patlatılmış (çizgi + "1014.00" yazısı), oda adı ve m²'si ayrı yazı.
- "TASLAK PLANI" alt yazılı plan ayrı okunur (alt_yazi = taslak); başlığı başka olan plan kopya sayılmaz.
Kart düzeltmez: paftada ne yazıyorsa o; ad karta yazılmaz.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "araclar" / "hdd_turev"))
ezdxf = pytest.importorskip("ezdxf")
import pafta_kart  # noqa: E402

AD = "Deneme Kişi"


def _yazi(m, t, x, y, h=12):
    m.add_text(t, dxfattribs={"height": h, "insert": (x, y)})


def _plan_2020(d, m, x0, y0, olculu=True, ad=AD, alt="MONTAJ VE ELEKTRİK PLANI"):
    W, H = 835.75, 951.25
    m.add_lwpolyline([(x0, y0), (x0 + W, y0), (x0 + W, y0 + H), (x0, y0 + H), (x0, y0)])
    m.add_line((x0 + 400, y0), (x0 + 400, y0 + H))
    _yazi(m, f"{ad} 72 M2", x0, y0 + H + 120, 40)
    _yazi(m, alt, x0 + 150, y0 - 140, 40)
    for t, x, y in (("Y.ODASI\\P9.14 m²", 100, 800), ("Y.ODASI\\P10.23 m²", 500, 800), ("WC\\P4.39 m²", 300, 600),
                    ("SALON+ MUTFAK\\P29.90 m²", 500, 400), ("VERANDA\\P11.97 m²", 100, 150)):
        m.add_mtext(t, dxfattribs={"insert": (x0 + x, y0 + y), "char_height": 12})
    for t, x, y in (("120/120   ÇİFT AÇILIM", 200, H + 10), ("60/40", 450, H + 10), ("{\\S120^180;} SÜRGÜ", 100, 300),
                    ("P.40x170", 600, -40), ("ÇELİK", 420, 330), ("100*100", 50, 20), ("100*100*3090", 60, 40)):
        _yazi(m, t, x0 + x, y0 + y)
    m.add_arc((x0 + 100, y0 + 700), 80, 0, 90)
    m.add_arc((x0 + 600, y0 + 700), 80, 90, 180)
    m.add_blockref("KAPI_YAYI", (x0 + 400, y0 + 350))
    if olculu:
        m.add_linear_dim(base=(x0, y0 + H + 60), p1=(x0, y0 + H), p2=(x0 + W, y0 + H), angle=0).render()
        m.add_linear_dim(base=(x0 + W + 60, y0), p1=(x0 + W, y0), p2=(x0 + W, y0 + H), angle=90).render()
        m.add_linear_dim(base=(x0, y0 + H + 30), p1=(x0, y0 + H), p2=(x0 + 120.5, y0 + H), angle=0).render()


def _ikranur(m, x0, y0):
    m.add_lwpolyline([(x0, y0), (x0 + 1759, y0), (x0 + 1759, y0 + 1193), (x0, y0 + 1193)], close=True)
    _yazi(m, "Montaj Ve Elektrik Planı", x0 + 9, y0 + 24, 14)
    _yazi(m, f"İKRANUR PREF. {AD.upper()}", x0 + 15, y0 + 1128, 14)
    _yazi(m, "66 m² PREFABRİK BİNA", x0 + 1502, y0 + 6, 14)
    px, py = x0 + 172, y0 + 291
    m.add_lwpolyline([(px, py), (px + 1014, py), (px + 1014, py + 710), (px, py + 710), (px, py)])
    m.add_linear_dim(base=(px, py + 750), p1=(px, py + 710), p2=(px + 1014, py + 710), angle=0).render()
    m.add_linear_dim(base=(px + 1056, py), p1=(px + 1014, py), p2=(px + 1014, py + 710), angle=90).render()
    for t, x, y in (("120/120", -20, 500), ("120/180", 150, 700), ("120/180", 780, 700), ("60/40", 540, 720),
                    ("Çelik", 540, 230), ("100*100*1780", 360, 50)):
        _yazi(m, t, px + x, py + y)
    satirlar = [("Bina Yüksekliği:", "2800", 1113), ("Dış Duvarlar:", "100'lük", 1070), ("İç Duvarlar:", "60'lık", 1027),
                ("Panel Türü:", "Pres Panel", 985), ("Çatı Şekli:", "Beşik Çatı", 943), ("Çatı Kaplaması:", "Usta Kiremit", 913),
                ("Dış Kapı:", "BEYAZ Çelik Kapı", 816)]
    _yazi(m, "TEKNİK BİLGİLER", x0 + 1524, y0 + 1158)
    for et, deger, y in satirlar:
        _yazi(m, et, x0 + 1526, y0 + (900 if et == "Çatı Kaplaması:" else y))
        _yazi(m, deger, x0 + 1526 + 95, y0 + y)


def _a4(m, x0, y0):
    m.add_lwpolyline([(x0, y0), (x0 + 1830, y0), (x0 + 1830, y0 + 1265), (x0, y0 + 1265)], close=True)
    _yazi(m, "Montaj Ve Elektrik Planı", x0 + 1012, y0 + 208, 40)
    m.add_mtext(f"{AD}\\P74 m² PREFABRİK KONUT", dxfattribs={"insert": (x0 + 1318, y0 + 140), "char_height": 20})
    _yazi(m, "ÇİZEN", x0 + 1318, y0 + 20)
    for et, deger, y in (("Bina Yüksekliği", "2500 mm", 1206), ("Dış Duvarlar", "100 mm", 1106), ("İç Duvarlar", "60 mm", 1006),
                         ("Panel Türü", "Pres Panel", 931), ("Çatı Şekli", "Beşik+Cumba", 831), ("Çatı Kaplaması", "Trapez Sac", 706),
                         ("Dış Kapı", "Çelik Standart", 531), ("İç Kapılar", "Standart Amerikan", 431)):
        _yazi(m, et, x0 + 10, y0 + y)
        _yazi(m, deger, x0 + 10, y0 + y - 25 if et != "Çatı Şekli" else y0 + y - 75)
    px, py = x0 + 420, y0 + 380
    m.add_lwpolyline([(px, py), (px + 1014, py), (px + 1014, py + 647.5), (px, py + 647.5)], close=True)
    m.add_line((px, py + 690), (px + 1014, py + 690))                     # patlatılmış ölçü: çizgi + yazı
    for t, x, y, aci in (("1014.00", 480, 695, 0), ("309.75", 150, -40, 0), ("635.50", 450, -60, 0),
                         ("647.50", -45, 300, 90), ("522.00", 1040, 380, 90), ("62.75", 350, 500, 90)):
        m.add_text(t, dxfattribs={"height": 10, "insert": (px + x, py + y), "rotation": aci})
    for ad, m2, x, y in (("Y. ODASI", "11.5 m²", 100, 500), ("SALON", "27.5 m²", 600, 420), ("Y. ODASI", "11.2 m²", 100, 220),
                         ("WC", "3.4m²", 420, 520), ("VERANDA", "16 m²", 600, 100)):
        _yazi(m, ad, px + x, py + y)
        _yazi(m, m2, px + x + 4, py + y - 25)
    for t, x, y in (("120/180", 150, 10), ("120/180", 800, 260), ("60/40", 450, 630), ("Çelik", 470, 300)):
        _yazi(m, t, px + x, py + y)
    m.add_text("120/120", dxfattribs={"height": 12, "insert": (px - 15, py + 450), "rotation": 90})
    m.add_arc((px + 300, py + 300), 80, 0, 90)
    m.add_arc((px + 700, py + 300), 80, 90, 180)


@pytest.fixture()
def cizim(tmp_path):
    d = ezdxf.new("R2018")
    b = d.blocks.new("KAPI_YAYI")
    b.add_arc((0, 0), 90, 0, 90)
    b.add_line((0, 0), (90, 0))
    m = d.modelspace()
    _plan_2020(d, m, 0, 0)
    # komşu çizim: plana 100 cm yakın, kendi uzun ölçüsüyle (alt yazının ortasından geçmez)
    m.add_lwpolyline([(935, 100), (2935, 100), (2935, 800), (935, 800)])
    m.add_linear_dim(base=(935, 860), p1=(935, 800), p2=(2935, 800), angle=0).render()
    _plan_2020(d, m, 6000, 0, olculu=False)
    _ikranur(m, 0, -3000)
    _plan_2020(d, m, 12000, 0, olculu=False, alt="TASLAK PLANI")           # aynı başlık, taslak: kopya değil
    _plan_2020(d, m, 18000, 0, olculu=False, ad="Öteki Müşteri")            # başka başlık: kopya değil
    _a4(m, 0, -6000)
    yol = tmp_path / "pafta.dxf"
    d.saveas(yol)
    return yol


def test_iki_sablon_okunur_kopya_ayrilir_ad_yazilmaz(cizim, tmp_path):
    P = pafta_kart.oku(str(cizim))
    assert len(P) == 6
    montaj72 = [p for p in P if p["baslik_m2"] == 72.0 and p["alt_yazi"] == "montaj"]
    asil = [p for p in montaj72 if not p["kopya"] and p["kutu_kaynagi"] == "olcu"]
    kopya = [p for p in montaj72 if p["kopya"]]
    assert len(montaj72) == 3 and len(asil) == 1 and len(kopya) == 1 and kopya[0]["kopya_sayisi"] == 1
    a = asil[0]
    assert a["kutu_kaynagi"] == "olcu" and a["sablon"] == "bantli"
    k = a["kart"]
    assert k["dis_olcu_cm"] == [835.75, 951.25]           # komşunun 2000'lik ölçüsü alınmadı
    assert k["baslik_m2"] == 72.0 and k["kutu_m2"] == 79.5
    assert k["oda_sayisi"] == "2+1" and k["yatak_odasi"] == 2 and k["veranda_adedi"] == 1
    assert k["net_m2"] == round(9.14 + 10.23 + 4.39 + 29.90 + 11.97, 2)
    assert k["acikliklar"] == {"120/120": 1, "120/180": 1, "60/40": 1}   # 100*100 dikme ölçüsü açıklık değil
    assert k["kubbe_pencereleri"] == {"40/170": 1}
    assert k["dis_kapi_adedi"] == 1 and k["ic_kapi_adedi"] == 2           # üç kapı yayı (biri blokta), biri çelik kapı
    ik = [p for p in P if p["baslik_m2"] == 66.0]
    assert len(ik) == 1
    i = ik[0]
    assert i["sablon"] == "cerceveli" and not i["kopya"]
    assert i["kart"]["dis_olcu_cm"] == [1014.0, 710.0]
    assert i["kart"]["acikliklar"] == {"120/120": 1, "120/180": 2, "60/40": 1}
    assert i["kart"]["dis_kapi_adedi"] == 1 and i["kart"]["oda_sayisi"] is None
    assert i["teknik"]["Çatı Kaplaması"] == "Usta Kiremit" and i["teknik"]["İç Duvarlar"] == "60'lık"
    assert i["kart"]["cati_sekli"] == "Beşik Çatı" and i["kart"]["dis_duvar"] == "100'lük"
    yazi = json.dumps(P, ensure_ascii=False)
    assert AD not in yazi and AD.upper() not in yazi and "KİŞİ" not in yazi


def test_ad_eslesmesi_yalniz_sonuc_yazar(cizim):
    P = pafta_kart.oku(str(cizim), {"klasor": "Deneme Kişi-Lokman", "dosya": "BAŞKA BİRİ 72 M2"})
    assert all(p["klasor_eslesir"] for p in P if p["baslik_m2"] != 72.0 or p["kutu_kaynagi"] == "olcu" or p["kopya"]
               or p["alt_yazi"] == "taslak")              # 2019–2020 başlığı, İkranur anteti ve A4 anteti
    assert sum(1 for p in P if not p["klasor_eslesir"]) == 1                    # yalnız öteki müşterinin planı
    assert not any(p["dosya_eslesir"] for p in P)
    assert not any(p["klasor_eslesir"] for p in pafta_kart.oku(str(cizim), {"klasor": "Kişi Deneyen"}))
    assert pafta_kart.ad_eslesir(["SAVAŞÇI EVREN 50 M2"], "Evren Savaşcı-Lokman")      # Türkçe harf ve sıra farkı
    assert not pafta_kart.ad_eslesir(["NURGÜL ÇELİK 70 M2"], "Ahmet Çelik")            # yalnız soyadı yetmez
    assert pafta_kart.ad_eslesir(["RESUL BEY 74 M2"], "Resul-Lokman")                  # tek sözcüklü ad
    assert pafta_kart.ad_eslesir(["ENSAR BEY 52 M2"], "Ensar Aksoy-Lokman")            # başlıkta yalnız ilk ad
    assert pafta_kart.ad_eslesir(["FARUKCAN BEY 110 M2"], "Faruk Can-Lokman")          # bitişik yazılmış ad
    assert not pafta_kart.ad_eslesir(["ÇELİK EV 70 M2"], "Ahmet Çelik")                # yalnız soyadı yetmez
    assert not pafta_kart.ad_eslesir(["AKSOY BEY 52 M2"], "Ensar Aksoy-Lokman")        # ilk ad yoksa yetmez
    yazi = json.dumps(P, ensure_ascii=False)
    assert AD not in yazi and "Deneme" not in yazi and "BAŞKA" not in yazi


def test_sikistirilmis_dxf_ve_komut(cizim, tmp_path):
    import gzip
    gz = tmp_path / "pafta.dxf.gz"
    gz.write_bytes(gzip.compress(cizim.read_bytes()))
    cikti = tmp_path / "kart.json"
    assert pafta_kart.main([str(gz), "--json", str(cikti)]) == 0
    P = json.loads(cikti.read_text(encoding="utf-8"))
    assert sorted(p["baslik_m2"] for p in P) == [66.0, 72.0, 72.0, 72.0, 72.0, 74.0]
    assert not any("klasor_eslesir" in p or "ek_eslesme" in p for p in P)


def test_ayni_dosya_iki_proje_klasorunde(cizim, tmp_path):
    """Aynı DWG iki proje klasöründe duruyorsa tek okuma iki klasörle de eşleşir; sıra komuttaki sıradır, ad yazılmaz."""
    cikti = tmp_path / "kart.json"
    assert pafta_kart.main([str(cizim), "--json", str(cikti), "--klasor-adi", "Kişi Deneyen", "--dosya-adi", "PLAN",
                            "--klasor-adi", "Deneme Kişi-Lokman", "--dosya-adi", "DENEME KİŞİ 72 M2"]) == 0
    P = json.loads(cikti.read_text(encoding="utf-8"))
    assert not any(p["klasor_eslesir"] for p in P)
    assert [e["klasor_eslesir"] for p in P for e in p["ek_eslesme"]].count(True) == 5
    assert all(len(p["ek_eslesme"]) == 1 for p in P)
    yazi = cikti.read_text(encoding="utf-8")
    assert "Deneme" not in yazi and "Deneyen" not in yazi and "PLAN\"" not in yazi


def test_a4_sayfa_patlatilmis_olcu_ayri_oda_yazisi(cizim):
    P = pafta_kart.oku(str(cizim), {"klasor": "Deneme Kişi-Lokman"})
    a4 = [p for p in P if p["baslik_m2"] == 74.0]
    assert len(a4) == 1
    p = a4[0]
    assert p["sablon"] == "cerceveli" and p["alt_yazi"] == "montaj" and not p["kopya"] and p["klasor_eslesir"]
    assert p["kutu_kaynagi"] == "olcu_yazisi" and p["olcu_kaynagi"] == "yazi"
    k = p["kart"]
    assert k["dis_olcu_cm"] == [1014.0, 647.5]
    assert sorted((m["ad"], m["m2"]) for m in p["mahaller"]) == [("SALON", 27.5), ("VERANDA", 16.0), ("WC", 3.4),
                                                                  ("Y. ODASI", 11.2), ("Y. ODASI", 11.5)]
    assert k["oda_sayisi"] == "2+1" and k["veranda_adedi"] == 1 and k["net_m2"] == 69.6
    assert k["acikliklar"] == {"120/120": 1, "120/180": 2, "60/40": 1}
    assert k["dis_kapi_adedi"] == 1 and k["ic_kapi_adedi"] == 1        # tablodaki "Çelik Standart" kapı sayılmaz
    assert p["teknik"]["Çatı Şekli"] == "Beşik+Cumba" and p["teknik"]["İç Duvarlar"] == "60 mm"
    assert p["teknik"]["Dış Kapı"] == "Çelik Standart" and k["cati_sekli"] == "Beşik+Cumba"


def test_taslak_ve_baska_baslik_kopya_degil(cizim):
    P = pafta_kart.oku(str(cizim))
    taslak = [p for p in P if p["alt_yazi"] == "taslak"]
    assert len(taslak) == 1 and not taslak[0]["kopya"] and taslak[0]["baslik_m2"] == 72.0
    assert sum(1 for p in P if p["baslik_m2"] == 72.0 and not p["kopya"]) == 3     # asıl, taslak, öteki müşteri
