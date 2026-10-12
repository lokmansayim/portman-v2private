"""İE-08 Adım 6 · denetim/kos.py sır taraması: telefon deseni ondalık sayıları numara sanmaz, gerçek numarayı yakalar;
bilinen yanlış pozitif (vps/kapi_d_dogrula.sh:25) beklenen sayılır.

Örnek sır dizileri bilerek parçalı kurulur: bu dosya da taranır (kos.py doğrudan koşulursa) ve hook'lar sır arar; kaynakta
tam kalıp bulunmaz, yalnız çalışma anında birleşir. kos.py içe aktarılınca depo köküne chdir eder; testler zaten kökte koşar."""
from __future__ import annotations
import importlib.util
import shutil
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
NUMARA = "9053" + "21234567"                       # 12 haneli örnek cep numarası (sahte)
ANAHTAR = "sk-" + "abcdefghij" + "klmnop"
PAROLA_SATIRI = "paro" + "la: 'gizli1234'"
PEM = "-----BEGIN " + "RSA PRIVATE" + " KEY-----"
BEARER = "Authorization: Bea" + "rer abcdefghijklmnopqrstu"


def _kos():
    spec = importlib.util.spec_from_file_location("denetim_kos", KOK / "denetim" / "kos.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _ara(satir: str):
    kos = _kos()
    return kos.SIR_RX.search(kos._ondaliksiz(satir))


def test_telefon_deseni_ondalik_sayiyi_numara_sanmaz():
    for satir in ["#12= IFCCARTESIANPOINT((6.9050000000000002,3.8905000000000003,0.));", "x = 3.8905000000000003", "{\"alan\": 19050000000.5}",
                  "1" + NUMARA + " (13 hane, numara değil)", "oda çevreleri 82,27 m; 0," + NUMARA + " oran"]:
        assert _ara(satir) is None, satir


def test_telefon_deseni_gercek_numarayi_yakalar():
    for satir in [NUMARA, "tel: " + NUMARA, "(" + NUMARA + ")", "numara " + NUMARA + ".", "wa_id=" + NUMARA + ";", NUMARA + " aradı"]:
        assert _ara(satir) is not None, satir


def test_telefon_deseni_virgullu_listeyi_yakalar():
    # kod incelemesi (12.10): "[905…,905…]" listesinde iki numara da, "905…,1,bayi" alanında numara bulunmalı (tam kısmı 12 haneli: ondalık değil)
    kos = _kos()
    ikinci = NUMARA[:-1] + "8"
    assert len(kos.SIR_RX.findall(kos._ondaliksiz("\"wa_ids\": [" + NUMARA + "," + ikinci + "]"))) == 2
    assert len(kos.SIR_RX.findall(kos._ondaliksiz(NUMARA + ",1,bayi"))) == 1
    assert len(kos.SIR_RX.findall(kos._ondaliksiz(NUMARA + ".5"))) == 1


def test_oteki_desenler_degismedi():
    rx = _kos().SIR_RX
    assert rx.search("key = " + ANAHTAR)
    assert rx.search(PAROLA_SATIRI)
    assert rx.search(PEM)
    assert rx.search(BEARER)
    assert rx.search("sk-kisa") is None


def _kapi_d_satirlari() -> list[str]:
    # gerçek dosyadaki gibi: 25. satırda rolün parolası olup olmadığını yazdıran SQL (parola deseni yanlış pozitifi)
    sql = "SELECT rolname || ' paro" + "la=' || (rolpassword IS NOT NULL) FROM pg_authid"
    return ["echo satir"] * 24 + ["echo \"rol: $(pgs -c \\\"" + sql + "\\\")\""]


def test_sir_taramasi_bilinen_yanlis_pozitifler_beklenen(tmp_path: Path):
    kos = _kos()
    (tmp_path / "vps").mkdir(); (tmp_path / "denetim").mkdir(); (tmp_path / "model").mkdir()
    (tmp_path / "vps" / "kapi_d_dogrula.sh").write_text("\n".join(_kapi_d_satirlari()) + "\n", encoding="utf-8")
    shutil.copy(KOK / "denetim" / "kos.py", tmp_path / "denetim" / "kos.py")
    (tmp_path / "model" / "deneme.ifc").write_text("#1= IFCCARTESIANPOINT((6.9050000000000002,0.,3.8905000000000003));\n", encoding="utf-8")
    r = kos.sir_taramasi(tmp_path)
    assert r["passed"] is True, r["bulgular"]
    assert r["sayilar"]["bulgu"] == r["sayilar"]["beklenen_sahte"] == 1          # kos.py'nin kendi metni artık eşleşmiyor (örnek numara yorumu kalktı)
    assert [(b["dosya"], b["satir"]) for b in r["bulgular"]] == [("vps/kapi_d_dogrula.sh", 25)]
    # aynı dosyada başka bir satırdaki parola deseni beklenen değildir
    (tmp_path / "vps" / "kapi_d_dogrula.sh").write_text("\n".join(_kapi_d_satirlari() + [PAROLA_SATIRI]) + "\n", encoding="utf-8")
    r2 = kos.sir_taramasi(tmp_path)
    assert r2["passed"] is False and r2["sayilar"]["bulgu"] == r2["sayilar"]["beklenen_sahte"] + 1


def test_sir_taramasi_gercek_numarayi_bulur_ve_maskeler(tmp_path: Path):
    kos = _kos()
    (tmp_path / "not.md").write_text("Bayi aradı: " + NUMARA + "\n", encoding="utf-8")
    r = kos.sir_taramasi(tmp_path)
    assert r["passed"] is False and r["sayilar"]["bulgu"] == 1 and r["bulgular"][0]["dosya"] == "not.md"
    assert NUMARA not in r["bulgular"][0]["ornek"]      # örnek maskeli yazılır
