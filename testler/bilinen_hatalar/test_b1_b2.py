"""Bilinen hatalar B1 ve B2: bugünkü kodla (v1.1.1, ec4e9a3) BAŞARISIZ olması beklenen testler.

Kaynak: DURUM.md (23 Eylül 2026), bölüm 3; canlı test 22.09 22:33–38 (Patron, 3 mesajın 2'si doğru).
Hiçbir test ağa, LLM'e, WhatsApp'a ya da canlı sunucuya bağlanmaz: LLM'in çıkarımı elle verilir, konuşma durumu
geçici klasörde tutulur.

Koşum:
    python3 -m pytest testler/bilinen_hatalar -v      # xfail = hata sürüyor; XPASS (strict) = hata düzeldi, işareti kaldırın
    python3 testler/bilinen_hatalar/test_b1_b2.py      # pytest yoksa: her vakanın bugünkü sonucunu yazar

B1 (kritik): Bayinin kendi sözü belirsizken ("P6001, yatak odası 1, 120x180": ne "değiştir" ne "ekle" var) kural
   katmanı soru sormalı. Kod bayinin sözüne yalnız LLM pencere işlemini "ekle" verdiğinde bakıyor (beyin/karar.py,
   pencere döngüsü); işlem boş ya da "degistir" gelirse pencereyi sessizce değiştirip İş Emri üretiyor.
B2 (karar Lokman'ın): Görüşme durumunda zaman aşımı yok (beyin/konusma.py). 22.09'da 3,5 saat sonra gelen "P6001 …"
   mesajı eski aynalı taslağın revizyonu sayıldı; mesajda ayna yoktu ama çıktı aynalı geldi.
   Seçenekler (DURUM.md, 23.09): (a) böyle kalsın, (b) taslak N saat sonra kapansın, (c) model koduyla başlayan mesaj
   yeni talep sayılsın. Bu test (b) ve (c)'nin ortak sonucunu sınar: uzun aradan sonra, model koduyla başlayan
   mesajda eski taslağın varyantı sessizce devralınmaz. Sistemin sorması da kabul edilir. (a) seçilirse test silinir.
"""
from __future__ import annotations
import json, sys, tempfile, time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from beyin.sema import Talep, Pencere, Varyant          # noqa: E402
from beyin.katalog import Katalog                         # noqa: E402
from beyin.konusma import Konusma                         # noqa: E402
from beyin.karar import karar_ver, bayileri_yukle        # noqa: E402

try:
    import pytest
except ImportError:  # düz koşum
    pytest = None

SABLON = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))


def _konum(ie: dict, ad: str):
    m = next((x for x in ie.get("mahaller", []) if x["ad"] == ad), None)
    return [list(map(float, r)) for r in (m or {}).get("konum_pano") or []]


def _aynali_mi(ie: dict | None) -> bool:
    """Ayna yalnız mahal konumlarını taşır; pencere ölçüsü konumu değiştirmez."""
    return ie is not None and _konum(ie, "YATAK ODASI 1") != _konum(SABLON, "YATAK ODASI 1")


def _pencere_talebi(islem: str | None, ozet: str) -> Talep:
    return Talep(niyet="yeni_talep", katalog_kodu="P6001", guven="yuksek", ozet=ozet,
                 pencereler=[Pencere(mahal="Yatak Odası 1", olcu="120x180", islem=islem)])


def _karar(talep: Talep, metin: str, gonderen: str, kok: Path):
    k = Konusma(gonderen, kok)
    return karar_ver(talep, k, bayileri_yukle().get(gonderen), Katalog(), metin=metin), k


# ---------------------------------------------------------------- B1
BELIRSIZ = "P6001, yatak odası 1, 120x180"          # ne "değiştir" ne "ekle"
ACIK = "P6001 yatak odası 1 penceresi 120x180 olsun"  # açık değiştirme sözü ("olsun")


def b1_islem_bos():
    with tempfile.TemporaryDirectory() as d:
        karar, _ = _karar(_pencere_talebi(None, "P6001, yatak odası 1 penceresi 120x180."), BELIRSIZ, "BAYI-TEST-3", Path(d))
    return karar.eylem


def b1_islem_degistir():
    with tempfile.TemporaryDirectory() as d:
        karar, _ = _karar(_pencere_talebi("degistir", "P6001, yatak odası 1 penceresi 120x180."), BELIRSIZ, "BAYI-TEST-3", Path(d))
    return karar.eylem


def b1_kontrol_ekle():
    """Kontrol: işlem 'ekle' gelince bugün de soruluyor (harness vaka 20)."""
    with tempfile.TemporaryDirectory() as d:
        karar, _ = _karar(_pencere_talebi("ekle", "P6001, yatak odası 1 için 120x180 pencere."), BELIRSIZ, "BAYI-TEST-3", Path(d))
    return karar.eylem


def b1_kontrol_acik_soz():
    """Kontrol: bayinin sözü açıksa ('olsun') soru sorulmaz, İş Emri çıkar. Düzeltme bunu bozmamalı."""
    with tempfile.TemporaryDirectory() as d:
        karar, _ = _karar(_pencere_talebi(None, "P6001, yatak odası 1 penceresi 120x180 olsun."), ACIK, "BAYI-TEST-3", Path(d))
    return karar.eylem


# ---------------------------------------------------------------- B2
def b2_uzun_aradan_sonra():
    """1) 'P6001 aynalı' → aynalı İş Emri. 2) 3,5 saat sonra 'P6001 yatak odası 1 penceresi 120x180 olsun' (aynasız),
    LLM niyeti 'revizyon'. Döner: (ilk_aynali, ikinci_eylem, ikinci_aynali, ikinci_revizyon)."""
    with tempfile.TemporaryDirectory() as d:
        kok = Path(d)
        t1 = Talep(niyet="yeni_talep", katalog_kodu="P6001", guven="yuksek", ozet="P6001 aynalı.",
                   varyantlar=[Varyant(tur="ayna_x", aciklama="aynalı")])
        k1, k = _karar(t1, "P6001 aynalı olsun", "BAYI-TEST-2", kok)
        ilk_aynali = _aynali_mi(k1.is_emri)
        # 3,5 saat geçmiş gibi: kayıt zamanlarını geri al
        yol = kok / "BAYI-TEST-2.json"
        dur = json.loads(yol.read_text())
        geri = 3.5 * 3600
        dur["guncellendi"] = int(dur["guncellendi"] - geri)
        for g in dur.get("gecmis", []):
            g["t"] = int(g["t"] - geri)
        yol.write_text(json.dumps(dur, ensure_ascii=False))
        t2 = Talep(niyet="revizyon", katalog_kodu="P6001", guven="yuksek", ozet="P6001 yatak odası 1 penceresi 120x180.",
                   pencereler=[Pencere(mahal="Yatak Odası 1", olcu="120x180", islem="degistir")])
        k2, _ = _karar(t2, ACIK, "BAYI-TEST-2", kok)
        return ilk_aynali, k2.eylem, _aynali_mi(k2.is_emri), k2.revizyon


# ---------------------------------------------------------------- pytest
if pytest is not None:
    # raises=AssertionError: yalnız beklenen davranış farkı "bilinen hata" sayılır; kurulum hatası (ImportError vb.) testi düşürür.
    xfail_b1 = pytest.mark.xfail(strict=True, raises=AssertionError,
                                 reason="B1: belirsiz sözde işlem boş/degistir gelince soru sorulmuyor (karar.py)")
    xfail_b2 = pytest.mark.xfail(strict=True, raises=AssertionError,
                                 reason="B2: görüşmede zaman aşımı yok; eski aynalı taslak sessizce devralınıyor (konusma.py)")

    @xfail_b1
    def test_b1_islem_bos_iken_sorulmali():
        assert b1_islem_bos() == "sor"

    @xfail_b1
    def test_b1_islem_degistir_ama_soz_belirsiz_iken_sorulmali():
        assert b1_islem_degistir() == "sor"

    def test_b1_kontrol_islem_ekle_iken_soruluyor():
        assert b1_kontrol_ekle() == "sor"

    def test_b1_kontrol_acik_sozde_is_emri():
        assert b1_kontrol_acik_soz() == "is_emri"

    def test_b2_on_kosul_ilk_taslak_aynali():
        """Ön koşul ayrı sınanır: ilk İş Emri aynalı değilse B2 testi anlamsızdır ve bu test düşer."""
        ilk_aynali, *_ = b2_uzun_aradan_sonra()
        assert ilk_aynali

    @xfail_b2
    def test_b2_uzun_aradan_sonra_eski_varyant_sessizce_devralinmamali():
        _ilk, eylem, aynali, _rev = b2_uzun_aradan_sonra()
        assert eylem == "sor" or (eylem == "is_emri" and not aynali)


if __name__ == "__main__":
    print("B1 işlem boş      :", b1_islem_bos(), "(beklenen: sor)")
    print("B1 işlem degistir :", b1_islem_degistir(), "(beklenen: sor)")
    print("Kontrol işlem ekle:", b1_kontrol_ekle(), "(beklenen: sor)")
    print("Kontrol açık söz  :", b1_kontrol_acik_soz(), "(beklenen: is_emri)")
    ilk, e, a, r = b2_uzun_aradan_sonra()
    print(f"B2 3,5 saat sonra : ilk aynalı={ilk}; ikinci eylem={e}, aynalı={a}, revizyon={r} "
          "(beklenen: aynasız yeni İş Emri ya da soru)")
