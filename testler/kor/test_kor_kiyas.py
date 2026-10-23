"""BK-12 PR-3 · kör test aracı (M7): mühür, açılış kaydı, sıra, eşleme ve açık sekiz projenin gerileme kapısı.

Her koşuda: aracın sırası (kendi listemiz kayıtlı → mühür → açılış kaydı) geçici bir depoda uydurma listeyle denenir; gerçek mühür
kaydının kör 19'u ve kapalı kayıtları açılış kaydı olmadan reddettiği gösterilir; açık sekiz projede tutan satırlar bugünkü Motor
çıktısıyla yeniden denetlenir (PK-01 bilgi, kapıya girmez). Kaynak liste gerekmez.

Tam koşu (`PORTMAN_KOR_TAM=1`, `PORTMAN_KOR_KAYNAK=<klasör>`): gerçek listeler depo dışındaki klasörden (SHA ile bulunur) yeniden
okunur; sayılar ve tutan satırlar `sonuc.json`'la aynı olmalı, bir baytı değiştirilmiş kopya okunmadan durmalı.
Uydurma listedeki ad ve numara uydurmadır; numara çalışma anında kurulur (dosyada düz yazılmaz).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from testler.kor import esle, kiyas as K, oku  # noqa: E402

PROJELER = sorted(p for p in (KOK / "testler" / "kor" / "projeler").iterdir() if (p / "proje.json").is_file())
KOR19 = ["AP-06", "AP-09", *[f"AP-{n:02d}" for n in range(11, 19)], *[f"AP-{n:02d}" for n in range(20, 29)]]
ACIK8 = ["PK-01", "PK-02", "PK-03", "PK-05", "PK-06", "PK-07", "PK-08", "TS-01"]
UYDURMA_AD = "Deneme Kişisi Uydurma"
UYDURMA_TEL = "0" + "5" + "00 000 07 77"


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _git(kok: Path, *args):
    subprocess.run(["git", "-C", str(kok), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


# ------------------------------------------------------------------------------------------------------- uydurma depo

GERCEK = [  # malzeme, boyut, adet → beklenen sonuç
    ("DENEME KALEM A", "1000", 4, "aynı"),
    ("DENEME KALEM B", "2000", 5, "ayrım"),
    ("DENEME KALEM C", "3000", 4, "pafta"),
    ("DENEME KALEM D", "4000", 6, "aday"),
    ("DENEME KALEM E", "5000", 7, "farklı"),
    ("DENEME KALEM F", "6000", 1, "bizde yok"),
]
BIZIM = [
    {"kalem": "Deneme kalem A", "olcu": "1000", "adet": 4},
    {"kalem": "Deneme kalem B", "olcu": "2000", "adet": 3},
    {"kalem": "Deneme kalem B", "olcu": "2000", "adet": 2},
    {"kalem": "Deneme kalem C", "olcu": "3000", "adet": 3, "pafta": 4},
    {"kalem": "Deneme kalem D", "olcu": "4000", "adet": 3, "aday": 6},
    {"kalem": "Deneme kalem E", "olcu": "5000", "adet": 2},
    {"kalem": "Deneme kalem G", "olcu": "7000", "adet": 1},          # bizde fazla
]


def _liste_xlsx(yol: Path) -> None:
    """Portatifev şablonu: başlık bloğunda uydurma ad ve numara, 10. satırda grup başlığı, sonda personel satırı."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = UYDURMA_AD                       # sayfa adı da okunmaz
    ws["B1"] = "PORTATİFEV YÜKLEME LİSTESİ"
    ws["B3"], ws["C3"] = "MÜŞTERİ ADI", UYDURMA_AD
    ws["B4"], ws["C4"] = "TELEFON", UYDURMA_TEL
    ws["B5"], ws["C5"] = "HAZIRLAYAN", UYDURMA_AD
    ws["B10"], ws["C10"], ws["D10"] = "DENEME GRUBU", "BOYUT", "ADET"
    for n, (m, b, a, _) in enumerate(GERCEK, 11):
        ws.cell(n, 2, m), ws.cell(n, 3, b), ws.cell(n, 4, a)
    ws.cell(20, 2, "SORUMLU ÜRETİM PERSONELİ AD SOYAD"), ws.cell(20, 4, UYDURMA_AD)
    ws.cell(21, 2, "DENEME KALEM H"), ws.cell(21, 3, "8000"), ws.cell(21, 4, UYDURMA_AD)   # adet yerine yazı: alınmaz
    wb.save(str(yol))


def _sha(yol: Path) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


@pytest.fixture
def depo(tmp_path):
    """Geçici depo: gerçek sözlük, uydurma mühür ve proje; kaynak liste depo dışında."""
    kok = tmp_path / "depo"
    kor = kok / "testler" / "kor"
    pd = kor / "projeler" / "DN01"
    pd.mkdir(parents=True)
    shutil.copy(KOK / "testler" / "kor" / "sozluk.json", kor / "sozluk.json")
    kaynak = tmp_path / "disari" / "liste.xlsx"
    kaynak.parent.mkdir()
    _liste_xlsx(kaynak)
    muhur = {"aciklama": "uydurma", "acilislar": {},
             "dosyalar": [{"kod": ["DN-01"], "tur": "yükleme listesi", "uzanti": ".xlsx", "bayt": kaynak.stat().st_size,
                           "sha256": _sha(kaynak), "durum": "acik"}]}
    (kor / "muhur.json").write_text(json.dumps(muhur, ensure_ascii=False), encoding="utf-8")
    (pd / "proje.json").write_text(json.dumps({"kod": "DN-01", "kip": "pafta", "girdi": {}, "liste_sha256": _sha(kaynak)}),
                                   encoding="utf-8")
    (pd / "bizim_liste.json").write_text(json.dumps({"kod": "DN-01", "girdi_ozeti": {"brut_m2": 12.5}, "satirlar": BIZIM},
                                                    ensure_ascii=False), encoding="utf-8")
    _git(kok, "init", "-q")
    _git(kok, "add", ".")
    _git(kok, "commit", "-q", "-m", "uydurma")
    return {"kok": kok, "pd": pd, "kaynak": kaynak, "muhur": kor / "muhur.json"}


def _muhur_degistir(depo, **alan):
    m = _oku(depo["muhur"])
    for k, v in alan.items():
        if k == "acilislar":
            m["acilislar"] = v
        else:
            m["dosyalar"][0][k] = v
    depo["muhur"].write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    _git(depo["kok"], "commit", "-q", "-am", "mühür")


@pytest.fixture
def okunmaz(monkeypatch):
    """Okuyucu çağrılırsa test düşer: mühür ya da açılış tutmadığında dosya içeriği okunmamalı."""
    def dur(*a, **k):
        raise AssertionError("dosya okundu")
    monkeypatch.setattr(K.oku, "oku", dur)


# ------------------------------------------------------------------------------------------------------- sıra ve mühür

def test_yedi_sonuc_ve_dogru_toplam(depo):
    k = K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    sonuc = {k["gercek"][x["i"]]["malzeme"]: x["sonuc"] for x in k["esle"]["gercek"]}
    assert sonuc == {m: s for m, _, _, s in GERCEK}
    assert [BIZIM[j]["kalem"] for j in k["esle"]["fazla"]] == ["Deneme kalem G"]
    s = k["esle"]["sayilar"]
    assert (s["aynı"], s["ayrım"], s["pafta"], s["aday"], s["farklı"], s["bizde yok"], s["bizde fazla"]) == (1, 1, 1, 1, 1, 1, 1)
    assert s["dogru"] == 4 and s["gercek_dolu"] == 6
    assert k["sinif_sayilari"][K.SINIFSIZ] == 3                     # farklı, bizde yok, bizde fazla


def test_baslik_blogu_ve_personel_okunmaz(depo, tmp_path):
    k = K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    metin = json.dumps(k["gercek"], ensure_ascii=False)
    assert UYDURMA_AD not in metin and "000 07 77" not in metin
    assert [s["malzeme"] for s in k["gercek"]] == [m for m, *_ in GERCEK] + ["DENEME KALEM H"]
    assert k["gercek"][-1]["adet"] is None                             # adet sütunundaki yazı alınmaz
    K.rapor_md(k, tmp_path / "r.md")
    K.rapor_xlsx(k, tmp_path / "r.xlsx")
    import openpyxl
    wb = openpyxl.load_workbook(tmp_path / "r.xlsx")
    hucre = " ".join(str(c.value) for ws in wb.worksheets for r in ws.iter_rows() for c in r if c.value is not None)
    for t in ((tmp_path / "r.md").read_text(encoding="utf-8"), hucre, " ".join(wb.sheetnames), "liste.xlsx"):
        assert UYDURMA_AD not in t and "000 07 77" not in t
    assert "liste.xlsx" not in (tmp_path / "r.md").read_text(encoding="utf-8")   # dosya adı yazılmaz


@pytest.mark.parametrize("bozma", ["bir_bayt", "eksik_bayt", "bos"])
def test_muhur_tutmazsa_okumadan_durur(depo, tmp_path, okunmaz, bozma):
    b = bytearray(depo["kaynak"].read_bytes())
    if bozma == "bir_bayt":
        b[len(b) // 2] ^= 0x01
    elif bozma == "eksik_bayt":
        b = b[:-1]
    else:
        b = bytearray()
    kopya = tmp_path / "kopya.xlsx"
    kopya.write_bytes(bytes(b))
    with pytest.raises(K.Durdu) as e:
        K.kiyasla(depo["pd"], kopya, kok=depo["kok"])
    assert e.value.adim == 2 and ("mühür tutmuyor" in e.value.neden)


def test_liste_olmayan_ya_da_baska_projenin_dosyasi_okunmaz(depo, okunmaz):
    _muhur_degistir(depo, tur="montaj paftası")
    with pytest.raises(K.Durdu, match="yükleme listesi değil"):
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    _muhur_degistir(depo, tur="yükleme listesi", kod=["DN-02"])
    with pytest.raises(K.Durdu, match="DN-01 değil"):
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])


def test_muhur_kaydi_degismisse_durur(depo, okunmaz):
    m = _oku(depo["muhur"])
    m["dosyalar"][0]["durum"] = "acik"
    depo["muhur"].write_text(json.dumps(m) + " ", encoding="utf-8")   # commit'lenmemiş değişiklik
    with pytest.raises(K.Durdu) as e:
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    assert e.value.adim == 2 and "çalışma ağacında değişmiş" in e.value.neden


@pytest.mark.parametrize("durum", ["kor", "kapali"])
def test_kor_ve_kapali_acilis_kaydi_olmadan_reddedilir(depo, okunmaz, durum):
    _muhur_degistir(depo, durum=durum)
    with pytest.raises(K.Durdu) as e:
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    assert e.value.adim == 3 and "açılış kaydı yok" in e.value.neden
    _muhur_degistir(depo, acilislar={"DN-01": {"karar": "uydurma", "tarih": "2026-10-23", "liste_commit": "0" * 7}})
    with pytest.raises(K.Durdu, match="kendi listemizin commit'i değil"):
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])


def test_kor_liste_acilis_kaydiyla_acilir(depo):
    _muhur_degistir(depo, durum="kor")
    liste = K.kayitli_mi(depo["pd"] / "bizim_liste.json", depo["kok"])
    _muhur_degistir(depo, acilislar={"DN-01": {"karar": "uydurma Patron kararı", "tarih": "2026-10-23",
                                              "liste_commit": liste["commit"][:7]}})
    k = K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    assert k["acilis"]["durum"] == "kor" and k["esle"]["sayilar"]["dogru"] == 4


def test_kendi_listemiz_kayitli_degilse_acilmaz(depo, okunmaz):
    y = depo["pd"] / "bizim_liste.json"
    d = _oku(y)
    d["satirlar"][0]["adet"] = 5
    y.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")      # değiştirilmiş, commit'siz
    with pytest.raises(K.Durdu) as e:
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    assert e.value.adim == 1 and "çalışma ağacında değişmiş" in e.value.neden
    _git(depo["kok"], "rm", "-q", "--cached", str(y.relative_to(depo["kok"])))   # yalnız indeksten çıkar: commit'siz liste
    with pytest.raises(K.Durdu) as e:
        K.kiyasla(depo["pd"], depo["kaynak"], kok=depo["kok"])
    assert e.value.adim == 1 and "commit'li değil" in e.value.neden


# ------------------------------------------------------------------------------------------------------- gerçek mühür kaydı

@pytest.fixture(scope="module")
def muhur():
    return K.muhur_oku()


def test_muhur_yalniz_kod_ve_ozet_tasir(muhur):
    alanlar = {"kod", "tur", "uzanti", "bayt", "sha256", "durum", "not"}
    shas = [r["sha256"] for r in muhur["dosyalar"]]
    assert len(shas) == len(set(shas)) == 82
    for r in muhur["dosyalar"]:
        assert set(r) <= alanlar, r["kod"]
        assert all(k[:3] in ("PK-", "TS-", "AP-") and len(k) == 5 for k in r["kod"])
    assert muhur["sayilar"] == {"acik": 17, "kaynak": 32, "kor": 19, "kapali": 14}


def test_kor19_ve_ap10_acilis_kaydi_olmadan_reddedilir(muhur):
    kor = {k: r for r in muhur["dosyalar"] if r["durum"] == "kor" for k in r["kod"]}
    assert sorted(kor) == KOR19
    ap10 = [r for r in muhur["dosyalar"] if "AP-10" in r["kod"] and r["tur"] == K.LISTE]
    assert len(ap10) == 1 and ap10[0]["durum"] == "kapali"
    liste = {"commit": "f" * 40}
    for kod, r in [*kor.items(), ("AP-10", ap10[0])]:
        assert r["tur"] == K.LISTE
        with pytest.raises(K.Durdu) as e:
            K.acilabilir_mi(r, muhur, kod, liste)
        assert e.value.adim == 3, kod
    assert not set(KOR19 + ["AP-10"]) & set(muhur["acilislar"])


def test_acik_sekiz_projenin_listesi_acik_kayitta(muhur):
    assert [_oku(p / "proje.json")["kod"] for p in PROJELER] == ACIK8
    for p in PROJELER:
        P = _oku(p / "proje.json")
        r = [r for r in muhur["dosyalar"] if r["sha256"] == P["liste_sha256"]]
        assert len(r) == 1 and r[0]["durum"] == "acik" and P["kod"] in r[0]["kod"], P["kod"]
        assert muhur["acilislar"][P["kod"]]["liste_commit"]
        if P.get("ap"):
            assert P["ap"] in r[0]["kod"]


# ------------------------------------------------------------------------------------------------------- gerileme kapısı

@pytest.fixture(scope="module")
def sozluk():
    return esle.sozluk_oku(K.SOZLUK)


@pytest.mark.parametrize("pd", PROJELER, ids=[p.name for p in PROJELER])
def test_kayitta_bizim_degerimizden_baska_deger_yok(pd, sozluk):
    """"Yalnız tutanlar": her tutan satırın değeri kıyas anındaki kendi listemizden yeniden çıkar."""
    kayit, bizim = _oku(pd / "sonuc.json"), _oku(pd / "bizim_liste.json")
    assert kayit["kod"] == bizim["kod"] == _oku(pd / "proje.json")["kod"]
    assert set(kayit) == {"aciklama", "kod", "ap", "kip", "kapi", "not", "tarih", "kiyas_commit", "bizim_liste", "muhur", "sozluk",
                          "gercek_satir", "sayilar", "sinif_sayilari", "tutanlar"}
    assert kayit["sayilar"]["dogru"] == sum(kayit["sayilar"][s] for s in esle.DOGRU)
    assert sum(t["gercek_satir"] for t in kayit["tutanlar"]) == kayit["sayilar"]["dogru"]
    bozuk = [t for t in kayit["tutanlar"] if esle.tutuyor_mu(bizim["satirlar"], sozluk, t) is None]
    assert not bozuk


@pytest.fixture(scope="module")
def bugun():
    return {p.name: K.bizim_liste_uret(p) for p in PROJELER}


@pytest.mark.parametrize("pd", [p for p in PROJELER if _oku(p / "proje.json").get("kapi", True)],
                         ids=[p.name for p in PROJELER if _oku(p / "proje.json").get("kapi", True)])
def test_gerileme_kapisi(pd, sozluk, bugun):
    """Bugünkü Motor çıktısı, gerçek listeyle tutan her satırı aynı adetle veriyor. Bozma bilerek yapılıyorsa protokol adım 7."""
    kayit, L = _oku(pd / "sonuc.json"), bugun[pd.name]
    bozuk = []
    for t in kayit["tutanlar"]:
        if esle.tutuyor_mu(L["satirlar"], sozluk, t) is None:
            sec = esle.bizim_secimi(L["satirlar"], sozluk, t)
            bozuk.append(f"{t['grup'] or t['ad']} [{t['b_anahtar']}] gerçek {t['deger']}, bugün "
                         + (" + ".join(str(s['adet']) for s in sec) or "satır yok"))
    assert not bozuk, f"{kayit['kod']}: {len(bozuk)} tutan satır bozuldu:\n" + "\n".join(bozuk)


def test_kapi_bozulan_satiri_yakalar(sozluk, bugun):
    """Bir kural tutan satırın adedini değiştirirse kapı o satırda durur (uydurma bozma, TS-01)."""
    kayit, L = _oku(KOK / "testler/kor/projeler/TS01/sonuc.json"), json.loads(json.dumps(bugun["TS01"]))
    t = next(t for t in kayit["tutanlar"] if t["sonuc"] == "aynı")
    sec = esle.bizim_secimi(L["satirlar"], sozluk, t)
    assert esle.tutuyor_mu(L["satirlar"], sozluk, t) == "aynı" and len(sec) == 1
    sec[0]["adet"] += 1
    assert esle.tutuyor_mu(L["satirlar"], sozluk, t) is None
    sec[0]["adet"] -= 1
    sec[0]["olcu"] += " (değişti)"
    assert esle.tutuyor_mu(L["satirlar"], sozluk, t) is None


def test_pk01_bilgi_kapiya_girmez(sozluk, bugun):
    pd = next(p for p in PROJELER if p.name == "PK01")
    P, kayit = _oku(pd / "proje.json"), _oku(pd / "sonuc.json")
    assert P["kapi"] is False and kayit["kapi"] is False and "stoktan" in P["not"]
    tutan = sum(1 for t in kayit["tutanlar"] if esle.tutuyor_mu(bugun["PK01"]["satirlar"], sozluk, t))
    print(f"PK-01 (bilgi): {tutan} / {len(kayit['tutanlar'])} tutan anahtar bugün de tutuyor")


# ------------------------------------------------------------------------------------------------------- tam koşu

TAM = os.environ.get("PORTMAN_KOR_TAM") == "1"


def _kaynak_bul(kayit: dict) -> Path:
    klasor = os.environ.get("PORTMAN_KOR_KAYNAK")
    assert klasor and Path(klasor).is_dir(), "PORTMAN_KOR_KAYNAK: gerçek listelerin klasörü (depo dışında)"
    assert not Path(klasor).resolve().is_relative_to(KOK), "kaynak klasörü depo dışında olmalı"
    for f in sorted(Path(klasor).rglob("*")):
        if f.is_file() and f.stat().st_size == kayit["bayt"] and K.sha256(f) == kayit["sha256"]:
            return f
    raise AssertionError(f"kaynak klasöründe mühürlü liste yok ({kayit['sha256'][:12]}…)")


@pytest.mark.skipif(not TAM, reason="tam koşu: PORTMAN_KOR_TAM=1 ve PORTMAN_KOR_KAYNAK")
@pytest.mark.parametrize("pd", PROJELER, ids=[p.name for p in PROJELER])
def test_tam_kosu_sonuc_kayitla_ayni(pd, tmp_path):
    kayit = _oku(pd / "sonuc.json")
    kaynak = _kaynak_bul(kayit["muhur"])
    k = K.kiyasla(pd, kaynak)
    yeni = K.sonuc_kaydi(k)
    assert (yeni["gercek_satir"], yeni["sayilar"], yeni["tutanlar"]) == (kayit["gercek_satir"], kayit["sayilar"], kayit["tutanlar"])
    assert yeni["bizim_liste"]["commit"] == kayit["bizim_liste"]["commit"]
    b = bytearray(kaynak.read_bytes())
    b[len(b) // 3] ^= 0x01
    kopya = tmp_path / ("kopya" + kaynak.suffix)
    kopya.write_bytes(bytes(b))
    with pytest.raises(K.Durdu) as e:
        K.kiyasla(pd, kopya)
    assert e.value.adim == 2
