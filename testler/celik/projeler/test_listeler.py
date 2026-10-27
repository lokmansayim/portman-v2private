"""İE-16 · öneren tarafının listeleri (`projeler/*/bizim_liste.json`): her liste girdilerinden araçla yeniden üretilir (elle yazılmadı;
atlanmaz), yazılış sözlüğü adet taşımaz, sayıyı değiştirmez, iki satırı bir anahtara toplamaz, çelik grubuna satır taşımaz, renk adını motorun renginden başka yazmaz ve adda kalemimizde olmayan renk sözcüğü (`RENKLER`)
yazmaz. Hakemin kendisi `testler/celik/test_celik_hakem.py`'dedir (değişmez)."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik.projeler import liste_yap  # noqa: E402

BURADA = Path(__file__).resolve().parent
# açık beşin listeleri; kör ve kapalı projelerin listeleri (sözlükleri listeyle donar; İE-16 PR-4) `test_kor_listeler.py`'de
LISTELER = sorted(p for p in BURADA.glob("*/bizim_liste.json")
                  if not liste_yap.sozluk_donar_mi(json.loads(p.read_text(encoding="utf-8"))["kod"]))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_listeler_var():
    """Açık dört proje ve hedef örnek (İE-16 PR-3a)."""
    assert [p.parent.name for p in LISTELER] == ["CP03", "CP06", "CP07", "CP13", "CP14"]


def kural_kopyalari(b: dict, tanim: Path) -> tuple[Path, Path | None]:
    """Listenin kural seti ve (tanım isterse) karkas kuralı kaydı: yolları kitabın yerinde, kopyaları `setler/`'de içerik adresli
    (`test_kor_listeler.py` de çağırır)."""
    ks = b["kural_seti"]
    assert ks["yol"].startswith("kurallar/liste/") and (KOK / ks["yol"]).is_file(), ks["yol"]
    kopya = KOK / ks["kopya"]
    assert kopya.parent == liste_yap.SETLER and kopya.name == ks["sha256"][:16] + ".json" and sha(kopya) == ks["sha256"]
    assert json.loads(kopya.read_text(encoding="utf-8")).get("sema") == ks["sema"]
    # karkas kuralı (İE-16 PR-3a): yalnız tanım isterse; kural seti gibi listeyle donan kopyasından okunur
    kk = b.get("karkas_kurali")
    assert bool(kk) == (json.loads(tanim.read_text(encoding="utf-8")).get("karkas") == "kural")
    kk_kopya = None
    if kk:
        assert kk["yol"] == liste_yap.VARSAYILAN_KARKAS.relative_to(KOK).as_posix() and (KOK / kk["yol"]).is_file(), kk["yol"]
        kk_kopya = KOK / kk["kopya"]
        assert kk_kopya.parent == liste_yap.SETLER and kk_kopya.name == kk["sha256"][:16] + ".json" and sha(kk_kopya) == kk["sha256"]
        assert json.loads(kk_kopya.read_text(encoding="utf-8")).get("sema") == kk["sema"]
    return kopya, kk_kopya


def sozluk_kurallari(s: dict, listeler: list[Path]) -> None:
    """Sözlük adet taşımaz, ölçüye sabit sayı yazmaz, iki kalem bir satırı tutmaz; METAL kalemleri motorun tek dere sistemi
    (`test_kor_listeler.py` donan sözlükle de çağırır)."""
    izinli = {"bizim", "ad", "olcu", "grup", "renkli", "not"}
    for k in s["kalemler"]:
        assert set(k) <= izinli, k
        olcu = k.get("olcu", "")
        assert set(re.findall(r"\{([^}]*)\}", olcu)) <= {"0", "1", "2", "a0", "a1"}, k
        assert not re.search(r"\d", re.sub(r"\{a?\d\}", "", olcu)), f"ölçü yazılışında sabit sayı: {k}"
        assert not re.search(r"\d", k.get("grup", "")), k
    assert not any(re.search(r"\d", g) for g in s["gruplar"].values())
    for yol in listeler:
        satirlar = json.loads(yol.read_text(encoding="utf-8"))["satirlar"]
        for satir in satirlar:
            assert sum(1 for k in s["kalemler"] if re.search(k["bizim"], satir["kalem"])) <= 1, satir["kalem"]
        # METAL: motorun tek dere sistemi (sözlüğün notu); motor başka dere yazarsa bu kalemler ayrılır
        if any((x.get("liste_adi") or "").startswith("METAL ") and x["kalem"] != "Metal dere" for x in satirlar):
            assert any(x["kalem"] == "Metal dere" for x in satirlar), yol


@pytest.mark.parametrize("yol", LISTELER, ids=[p.parent.name for p in LISTELER])
def test_liste_girdilerinden_yeniden_uretilir(yol, tmp_path):
    """Tanım ve sözlük öneren ağacında: değiştiyse liste yeniden üretilir. Kural seti listeyle donan kopyasından okunur (kitap sonra değişse de)."""
    b = json.loads(yol.read_text(encoding="utf-8"))
    tanim, ks = KOK / b["tanim"]["yol"], b["kural_seti"]
    assert tanim.parent == yol.parent and b["tanim"]["sha256"] == sha(tanim), "tanım değişti: liste liste_yap ile yeniden üretilir"
    assert b["sozluk"]["sha256"] == sha(liste_yap.SOZLUK), "sözlük değişti: liste liste_yap ile yeniden üretilir"
    kopya, kk_kopya = kural_kopyalari(b, tanim)
    kk = b.get("karkas_kurali")
    yukleme = liste_yap.motor(tanim, tmp_path, b["yontem"]["kod"], kopya, kk_kopya)
    assert liste_yap.liste(tanim, yukleme, b["yontem"]["kod"], ks, karkas_kaydi=kk) == b


def test_sozluk_adet_tasimaz_olcuye_sayi_yazmaz():
    sozluk_kurallari(json.loads(liste_yap.SOZLUK.read_text(encoding="utf-8")), LISTELER)


ALCIPAN = {"grup": "İç cephe kaplama", "kalem": "Duvar alçıpan beyaz", "boyut": "1200 × 2500", "adet": 57, "kg": None, "durum": "excel"}
BOARDEX = {"grup": "Dış cephe kaplama", "kalem": "Dış cephe Boardex", "boyut": "12,5 × 1200 × 2400", "adet": 41, "kg": None, "durum": "excel"}
NYM = {"grup": "Elektrik", "kalem": "NYM kablo (3 × 2,5)", "boyut": "metre", "adet": 139, "kg": None, "durum": "lokman"}
SANDVIC = {"grup": "Çatı kaplamaları", "kalem": "Sandviç panel", "boyut": "L 5080 · 100 cm kapatır", "adet": 18, "kg": None, "durum": "motor"}
KUTU = {"grup": "Çatı kaplamaları", "kalem": "Ters mahya kenar kutusu", "boyut": "L 21 × 40 × 21 × 2800", "adet": 4, "kg": None, "durum": "motor"}
OSB = {"grup": "İç cephe kaplama", "kalem": "İç duvar OSB 11 mm", "boyut": "1220 × 2440", "adet": 67, "kg": None, "durum": "excel"}


def sozluk(bizim: str, **k) -> dict:
    return {"gruplar": {}, "renk_adlari": {"antrasit gri": "ANTRASİT"}, "kalemler": [{"bizim": bizim, **k}]}


@pytest.mark.parametrize("satir,kalem,beklenen", [
    (ALCIPAN, {"ad": "Beyaz Alçıpan (DUVAR)", "olcu": "{0}x{1}"}, ("Beyaz Alçıpan (DUVAR)", "1200x2500")),
    (NYM, {"ad": "NYM KABLO", "olcu": "{a0} X {a1}"}, ("NYM KABLO", "3 X 2,5")),
    (SANDVIC, {"ad": "SANDVİÇ PANEL (100 CM KAPATIR)", "olcu": "L:{0}"}, ("SANDVİÇ PANEL (100 CM KAPATIR)", "L:5080")),
    ({**SANDVIC, "renk": "antrasit gri"}, {"ad": "SANDVİÇ PANEL (100 CM KAPATIR)", "olcu": "L:{0}", "renkli": True},
     ("SANDVİÇ PANEL (100 CM KAPATIR) (ANTRASİT)", "L:5080")),
    (KUTU, {"ad": "TERS MAHYA KENAR KUTULARI", "renkli": True}, ("TERS MAHYA KENAR KUTULARI", "L 21 × 40 × 21 × 2800")),
])
def test_sayi_kurali_yazilisi_cevirir(satir, kalem, beklenen):
    """Ölçünün yazılışı değişir, sayıları değişmez; adımızdaki sayı ölçüye, ölçümüzdeki sayı ada taşınabilir;
    renk yalnız motorun satırından (renkli kalemde motor renk yazmadıysa adda renk yok)."""
    out = liste_yap.cevir(satir, sozluk(re.escape(satir["kalem"]), **kalem))
    assert (out["liste_adi"], out["boyut"], out["adet"]) == (*beklenen, satir["adet"])


@pytest.mark.parametrize("satir,kalem", [
    (BOARDEX, {"ad": "BOARDEX", "olcu": "10x{1}x{2}"}),           # kalınlığımızı sabit bir sayıyla değiştirir (1. tur bulgusu)
    (ALCIPAN, {"ad": "Beyaz Alçıpan (DUVAR)", "olcu": "15x{0}x{1}"}),  # ölçüye sabit kalınlık ekler (1. tur bulgusu)
    (ALCIPAN, {"ad": "Beyaz Alçıpan (DUVAR)", "olcu": "{0}"}),        # ölçümüzden sayı atar
    (ALCIPAN, {"ad": "Beyaz Alçıpan 12,5 MM"}),                       # ada sayı ekler
    (SANDVIC, {"ad": "SANDVİÇ PANEL", "olcu": "L:{0}"}),              # örtme enini düşürür
    (OSB, {"ad": "Osb TAM", "olcu": "{0}x{1}"}),                      # adımızdaki kalınlığı düşürür (2. tur notu)
    (NYM, {"ad": "NYM KABLO", "olcu": "{a0}"}),                         # adımızdaki bir sayıyı düşürür (3. tur)
    (OSB, {"ad": "Osb TAM", "olcu": "{a0}x{a0}x{0}x{1}"}),            # adımızdaki sayıyı ikiler
])
def test_sayi_kurali_bozuk_sozlugu_durdurur(satir, kalem):
    with pytest.raises(SystemExit, match="sayılarını değiştiriyor"):
        liste_yap.cevir(satir, sozluk(re.escape(satir["kalem"]), **kalem))


def test_iki_satir_bir_anahtara_toplanmaz():
    """Hakem aynı anahtardaki adetleri toplar: duvar ve tavan alçıpanını aynı ada çeviren sözlük durur (2. tur bulgusu)."""
    s = {"gruplar": {}, "renk_adlari": {}, "kalemler": [{"bizim": "^(Duvar|Tavan) alçıpan beyaz$", "ad": "Beyaz Alçıpan", "olcu": "{0}x{1}"}]}
    tavan = {**ALCIPAN, "kalem": "Tavan alçıpan beyaz", "adet": 24}
    satirlar = [liste_yap.cevir(x, s) for x in (ALCIPAN, tavan)]
    with pytest.raises(SystemExit, match="bir anahtarına topluyor"):
        liste_yap.anahtar_denetimi(satirlar)
    liste_yap.anahtar_denetimi([liste_yap.cevir(x, sozluk(re.escape(x["kalem"]), ad=x["kalem"].upper())) for x in (ALCIPAN, tavan)])


def test_celik_grubuna_satir_tasinmaz():
    """Hakem çelik grubundaki satırın türünü addan okur: sözlük çelik dışı bir satırı çelik grubuna taşıyamaz (3. tur bulgusu)."""
    s = sozluk(re.escape(KUTU["kalem"]), ad="ÇATI PANELİ", grup="ÇELİK PANEL GRUBU")
    with pytest.raises(SystemExit, match="çelik grubuna"):
        liste_yap.cevir(KUTU, s)
    with pytest.raises(SystemExit, match="çelik grubuna"):
        liste_yap.cevir(KUTU, {"gruplar": {"Çatı kaplamaları": "ÇELİK PANEL GRUBU"}, "renk_adlari": {}, "kalemler": []})
    with pytest.raises(SystemExit, match="grup adında sayı"):
        liste_yap.cevir(KUTU, sozluk(re.escape(KUTU["kalem"]), ad="TERS MAHYA KENAR KUTULARI", grup="ÇATI 2 GRUBU"))


@pytest.mark.parametrize("renk_adi", ["KIRMIZI", "GRİ", "ANTRASİT GRİ KIRMIZI", ""])
def test_renk_adi_motorun_rengi(renk_adi):
    """Şablonun renk adı motorun renginin baştan kısaltmasıdır; sözlük rengi değiştiremez (3. tur), sözcük seçemez (4. tur notu)."""
    satir = {**SANDVIC, "renk": "antrasit gri"}
    k = {"ad": "SANDVİÇ PANEL (100 CM KAPATIR)", "olcu": "L:{0}", "renkli": True}
    s = {**sozluk(re.escape(satir["kalem"]), **k), "renk_adlari": {"antrasit gri": renk_adi}}
    with pytest.raises(SystemExit, match="motorun rengi"):
        liste_yap.cevir(satir, s)
    s["renk_adlari"]["antrasit gri"] = "ANTRASİT GRİ"
    assert liste_yap.cevir(satir, s)["liste_adi"] == "SANDVİÇ PANEL (100 CM KAPATIR) (ANTRASİT GRİ)"


@pytest.mark.parametrize("satir,ad", [
    (SANDVIC, "SANDVİÇ PANEL ANTRASİT (100 CM KAPATIR)"),             # renkli kalemde motor renk yazmadan adda renk (4. tur bulgusu)
    ({**SANDVIC, "renk": "antrasit gri"}, "KIRMIZI SANDVİÇ PANEL (100 CM KAPATIR)"),  # motorun renginden başka renk
    (KUTU, "TERS MAHYA KENAR KUTULARI (RAL 7016)"),                  # renksiz kalemde renk kodu (sayı da ekler; önce renk durur)
    (OSB, "Yeşil Osb 11 MM"),                                         # malzemeye renk ekler
])
def test_adda_renk_yazilmaz(satir, ad):
    """Renk yalnız motorun satırından gelir: sözlüğün adı bizim kalemimizde olmayan bir renk sözcüğü yazamaz (`RENKLER`)."""
    with pytest.raises(SystemExit, match="adına renk yazıyor"):
        liste_yap.cevir(satir, sozluk(re.escape(satir["kalem"]), ad=ad, renkli=True))
    beyaz = liste_yap.cevir(ALCIPAN, sozluk(re.escape(ALCIPAN["kalem"]), ad="Beyaz Alçıpan (DUVAR)", olcu="{0}x{1}"))
    assert beyaz["liste_adi"] == "Beyaz Alçıpan (DUVAR)"  # kalemimizdeki renk sözcüğü adda kalabilir

