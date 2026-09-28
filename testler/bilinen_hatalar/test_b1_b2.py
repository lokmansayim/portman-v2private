"""Bilinen hatalar B1 ve B2: v1.1.1'de (ec4e9a3) başarısız olan, İE-02'de (dal ie-02) düzeltilen davranışların testleri.

Kaynak: DURUM.md (23 Eylül 2026), bölüm 3; canlı test 22.09 22:33–38 (Patron, 3 mesajın 2'si doğru).
Hiçbir test ağa, LLM'e, WhatsApp'a ya da canlı sunucuya bağlanmaz: LLM'in çıkarımı elle verilir, konuşma durumu
geçici klasörde tutulur.

Koşum:
    python3 -m pytest testler/bilinen_hatalar -v
    python3 testler/bilinen_hatalar/test_b1_b2.py      # pytest yoksa: her vakanın bugünkü sonucunu yazar

B1 (düzeltildi, İE-02): Bayinin kendi sözü belirsizken ("P6001, yatak odası 1, 120x180": ne "değiştir" ne "ekle" var)
   kural katmanı soru sormalı. v1.1.1 bayinin sözüne yalnız LLM pencere işlemini "ekle" verdiğinde bakıyordu; işlem boş
   ya da "degistir" gelince pencereyi sessizce değiştiriyordu. Artık mahalde tek pencere varsa LLM ne derse desin ölçüt
   bayinin sözüdür (K18, K21): değiştir → ölçü değişikliği, ekle → ekleme (v0.1'de yönlendirme), belirsiz → soru. Söz,
   pencere satırının geldiği mesajdan kaydedilir; sonraki bir revizyonun sözü ("ayna") eski satırı yeniden yorumlamaz.
B2 (düzeltildi, İE-02): Görüşme durumunda zaman aşımı yoktu (beyin/konusma.py). 22.09'da 3,5 saat sonra gelen
   "P6001 …" mesajı eski aynalı taslağın revizyonu sayıldı; mesajda ayna yoktu ama çıktı aynalı geldi.
   Karar D-01 (Lokman, 28.09; KARARLAR/D-01.md): taslak 2 saatten eskiyse ve bayinin mesajı model koduyla başlıyorsa
   sistem sorar: "yeni" → eski taslak kapanır, mesaj yeni talep olarak işlenir; "değişiklik" → mesaj o taslağa eklenir.
   Kısa arada gelen ya da model koduyla başlamayan mesajda soru sorulmaz (kontrol testleri).
"""
from __future__ import annotations
import json, sys, tempfile
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


# ---------------------------------------------------------------- B2 (D-01)
GONDEREN_B2 = "BAYI-TEST-2"
PENCERE_SOZU = "yatak odası 1 penceresi 120x180 olsun"   # model kodu yok


def _talep(niyet="diger", ozet="", guven="dusuk", **kw) -> Talep:
    return Talep(niyet=niyet, guven=guven, ozet=ozet, **kw)


T_AYNA = _talep("yeni_talep", "P6001 aynalı.", "yuksek", katalog_kodu="P6001", varyantlar=[Varyant(tur="ayna_x", aciklama="aynalı")])


def T_PENCERE(niyet="revizyon", mahal="Yatak Odası 1", olcu="120x180", islem="degistir"):
    return _talep(niyet, f"P6001 {mahal.lower()} penceresi {olcu}.", "yuksek", katalog_kodu="P6001",
                  pencereler=[Pencere(mahal=mahal, olcu=olcu, islem=islem)])


def kisa(metin: str) -> tuple:
    """Bayinin kısa mesajı; LLM'in ona anlamlı bir niyet vermediği varsayılır ('diger', içerik yok)."""
    return (0, metin, _talep("diger", metin))


def _geri_al(yol: Path, saat: float):
    """Durum dosyasındaki bütün zamanları `saat` saat geriye alır (o kadar zaman geçmiş gibi)."""
    dur = json.loads(yol.read_text())
    geri = int(saat * 3600)
    for a in ("guncellendi", "taslak_zamani", "bekleyen_zamani"):
        if dur.get(a):
            dur[a] -= geri
    for g in dur.get("gecmis", []):
        g["t"] -= geri
    yol.write_text(json.dumps(dur, ensure_ascii=False))


def senaryo(*adimlar):
    """adimlar: (kaç saat sonra, bayinin metni, LLM'in çıkarımı). Döner: kararlar ve son durum."""
    with tempfile.TemporaryDirectory() as d:
        kok = Path(d); yol = kok / f"{GONDEREN_B2}.json"; kararlar = []
        for adim in adimlar:
            if callable(adim):          # adımlar arasında durum dosyasına müdahale (eski sürümden kalan kayıt gibi)
                adim(yol); continue
            saat, metin, talep = adim
            if saat and yol.exists():
                _geri_al(yol, saat)
            kr, _k = _karar(talep, metin, GONDEREN_B2, kok)
            kararlar.append(kr)
        return kararlar, json.loads(yol.read_text())


def _pencere_var(ie: dict | None, mahal: str, olcu: str) -> bool:
    return bool(ie) and any(a["tur"] == "pencere" and a.get("mahal") == mahal and a.get("olcu") == olcu for a in ie["acikliklar"])


SORU = ("sor", "yeni_mi_degisiklik")
ILK = (0, "P6001 aynalı olsun", T_AYNA)
UC_BUCUK_SAAT_SONRA = (3.5, ACIK, T_PENCERE())


def b2_uzun_aradan_sonra():
    """Düz koşum çıktısı için: (ilk_aynali, ikinci_eylem, ikinci_aynali, ikinci_revizyon)."""
    (k1, k2), _ = senaryo(ILK, UC_BUCUK_SAAT_SONRA)
    return _aynali_mi(k1.is_emri), k2.eylem, _aynali_mi(k2.is_emri), k2.revizyon


# ---------------------------------------------------------------- pytest
if pytest is not None:
    def T_B1(islem, niyet="yeni_talep"):
        return _talep(niyet, "P6001, yatak odası 1 penceresi 120x180.", "yuksek", katalog_kodu="P6001",
                      pencereler=[Pencere(mahal="Yatak Odası 1", olcu="120x180", islem=islem)])

    def test_b1_islem_bos_iken_sorulmali():
        assert b1_islem_bos() == "sor"

    def test_b1_islem_degistir_ama_soz_belirsiz_iken_sorulmali():
        assert b1_islem_degistir() == "sor"

    @pytest.mark.parametrize("islem", [None, "degistir", "ekle"])
    def test_b1_belirsiz_sozde_llm_ne_derse_desin_pencere_sorusu(islem):
        (k1,), _ = senaryo((0, BELIRSIZ, T_B1(islem)))
        assert (k1.eylem, k1.soru_alani) == ("sor", "pencere_islem")

    def test_b1_acik_ekleme_sozu_llm_degistir_dese_de_ekleme_sayilir():
        """Ekleme v0.1'de otomatik yapılmıyor: yönlendirilir. Pencere sessizce değiştirilmez."""
        (k1,), _ = senaryo((0, "P6001 yatak odası 1'e bir tane daha 120x180 pencere ekle", T_B1("degistir")))
        assert k1.eylem == "yonlendir"

    def test_b1_acik_degistirme_sozu_llm_ekle_dese_de_degisiklik_sayilir():
        (k1,), _ = senaryo((0, ACIK, T_B1("ekle")))
        assert k1.eylem == "is_emri" and _pencere_var(k1.is_emri, "YATAK ODASI 1", "120x180")

    @pytest.mark.parametrize("islem", [None, "degistir"])
    def test_b1_soru_cevabi_degistir_ise_olcu_degisir(islem):
        (_, k2), _ = senaryo((0, BELIRSIZ, T_B1(islem)), kisa("değiştir"))
        assert k2.eylem == "is_emri" and _pencere_var(k2.is_emri, "YATAK ODASI 1", "120x180")

    def test_b1_soru_cevabi_ekle_ise_yonlendirilir():
        (_, k2), _ = senaryo((0, BELIRSIZ, T_B1(None)), kisa("ekle"))
        assert k2.eylem == "yonlendir"

    def T_ODA(mahal, olcu, islem=None, niyet="yeni_talep"):
        return _talep(niyet, f"P6001, {mahal.lower()} penceresi {olcu}.", "yuksek", katalog_kodu="P6001",
                      pencereler=[Pencere(mahal=mahal, olcu=olcu, islem=islem)])

    def test_b1_pencere_sorusu_askidayken_ilgisiz_mesaj_cevap_sayilmaz():
        """'aynalı olsun' içindeki 'olsun' pencere sorusunun cevabı değildir; pencere sessizce değişmez, soru yinelenir."""
        ayna = _talep("revizyon", "Aynalı olsun.", "yuksek", varyantlar=[Varyant(tur="ayna_x", aciklama="aynalı")])
        (_, k2), _ = senaryo((0, BELIRSIZ, T_B1(None)), (0, "aynalı olsun", ayna))
        assert (k2.eylem, k2.soru_alani) == ("sor", "pencere_islem")

    @pytest.mark.parametrize("metin, islem", [("P6001, yaşam alanı, 120x180", None),
                                              ("P6001 yaşam alanı penceresi 120x180 olsun", None),
                                              ("P6001 yaşam alanına bir tane daha 120x180 pencere ekle", "degistir")])
    def test_b1_cok_pencereli_odada_pencere_sessizce_degismez(metin, islem):
        (k1,), _ = senaryo((0, metin, T_ODA("Yaşam Alanı", "120x180", islem)))
        assert k1.eylem == "yonlendir"

    def test_b1_cevap_yalniz_sorulan_satiri_cozer():
        """İki belirsiz satır: YO1 sorulur, 'değiştir' yalnız YO1'i çözer; sonra YO2 ayrıca sorulur."""
        iki = _talep("yeni_talep", "P6001 iki pencere.", "yuksek", katalog_kodu="P6001",
                     pencereler=[Pencere(mahal="Yatak Odası 1", olcu="120x180", islem=None),
                                 Pencere(mahal="Yatak Odası 2", olcu="120x120", islem="ekle")])
        k1, k2 = senaryo((0, "P6001 yatak odası 1 120x180 olsun, yatak odası 2'ye bir pencere daha ekle 120x120", iki),
                         kisa("değiştir"))[0]
        assert (k1.eylem, k1.soru_alani) == ("sor", "pencere_islem") and "YATAK ODASI 1" in k1.mesaj
        assert (k2.eylem, k2.soru_alani) == ("sor", "pencere_islem") and "YATAK ODASI 2" in k2.mesaj

    def test_b1_belirsiz_satir_acik_sozle_yeniden_gelince_yeniden_sorulmaz():
        """Bayi soruya cevap yerine talebi açıkça yeniden yazar, LLM bu kez 'degistir' der: eski belirsiz satır düşer."""
        (_, k2), d = senaryo((0, BELIRSIZ, T_B1(None)), (0, ACIK, T_B1("degistir")))
        assert k2.eylem == "is_emri" and _pencere_var(k2.is_emri, "YATAK ODASI 1", "120x180")
        assert len([p for p in d["taslak"]["pencereler"] if p["mahal"].lower() == "yatak odası 1"]) == 1

    def test_b1_plan_ciktiktan_sonra_eski_pencere_sorusu_askida_kalmaz():
        """Soru yerine açık yeniden yazımla plan çıkınca 'tamam olsun' onaydır, pencere cevabı değil; taslak silinmez."""
        onay = _talep("onay", "Onaylıyor.", "yuksek")
        (_, k2, k3), _ = senaryo((0, BELIRSIZ, T_B1(None)), (0, ACIK, T_B1("degistir")), (0, "tamam olsun", onay))
        assert k2.eylem == "is_emri"
        assert k3.eylem == "cevapla" and "Onayınız kaydedildi" in k3.mesaj
        assert f"revizyon {k2.revizyon}" in k3.mesaj and k3.revizyon == k2.revizyon == 1    # onay, gönderilen planın numarasını söyler

    def test_b1_oda_adi_yazimi_farkli_olsa_da_eski_satir_duser():
        (_, k2), d = senaryo((0, BELIRSIZ, T_ODA("Yatak odasi 1", "120x180")), (0, ACIK, T_B1("degistir")))
        assert k2.eylem == "is_emri" and len(d["taslak"]["pencereler"]) == 1

    def test_b1_baska_odanin_belirsiz_satiri_onceki_odayi_yeniden_sordurmaz():
        (k1, k2), _ = senaryo((0, ACIK, T_B1(None)), (0.5, "yatak odası 2, 120x120", T_ODA("Yatak Odası 2", "120x120", None, "revizyon")))
        assert k1.eylem == "is_emri"
        assert (k2.eylem, k2.soru_alani) == ("sor", "pencere_islem") and "YATAK ODASI 2" in k2.mesaj

    def test_b1_eski_surumden_kalan_kayit_yeniden_sorulmaz():
        """v1.1.1 durum dosyasında pencere satırında 'soz_niyeti' yoktur; İş Emri'ne girmiş satır değişiklik sayılır."""
        def soz_sil(yol):
            d = json.loads(yol.read_text())
            for p in d["taslak"].get("pencereler", []):
                p.pop("soz_niyeti", None)
            yol.write_text(json.dumps(d, ensure_ascii=False))
        ayna = _talep("revizyon", "Aynalı olsun.", "yuksek", varyantlar=[Varyant(tur="ayna_x", aciklama="ayna")])
        (_, k2), _ = senaryo((0, ACIK, T_B1(None)), soz_sil, (0.5, "ayna", ayna))
        assert k2.eylem == "is_emri" and _aynali_mi(k2.is_emri) and _pencere_var(k2.is_emri, "YATAK ODASI 1", "120x180")

    def test_b1_sonraki_revizyonun_sozu_eski_pencere_satirini_yeniden_yorumlamaz():
        """1) 'penceresi 120x180 olsun' → İş Emri. 2) yarım saat sonra yalnız 'ayna' → aynalı İş Emri; pencere yine sorulmaz."""
        ayna = _talep("revizyon", "Aynalı olsun.", "yuksek", varyantlar=[Varyant(tur="ayna_x", aciklama="ayna")])
        (k1, k2), _ = senaryo((0, ACIK, T_B1(None)), (0.5, "ayna", ayna))
        assert k1.eylem == "is_emri"
        assert (k2.eylem, _aynali_mi(k2.is_emri)) == ("is_emri", True) and _pencere_var(k2.is_emri, "YATAK ODASI 1", "120x180")

    def test_b1_kontrol_islem_ekle_iken_soruluyor():
        assert b1_kontrol_ekle() == "sor"

    def test_b1_kontrol_acik_sozde_is_emri():
        assert b1_kontrol_acik_soz() == "is_emri"

    def test_b2_on_kosul_ilk_taslak_aynali():
        """Ön koşul ayrı sınanır: ilk İş Emri aynalı değilse B2 testleri anlamsızdır ve bu test düşer."""
        (k1,), _ = senaryo(ILK)
        assert k1.eylem == "is_emri" and _aynali_mi(k1.is_emri)

    def test_b2_uzun_aradan_sonra_model_koduyla_gelen_mesajda_sorulur():
        (_, k2), d = senaryo(ILK, UC_BUCUK_SAAT_SONRA)
        assert (k2.eylem, k2.soru_alani) == SORU and d.get("bekleyen_talep")

    @pytest.mark.parametrize("cevap", ["yeni", "yeni talep", "yenisi", "başka bir talep", "sıfırdan", "Yeni."])
    def test_b2_cevap_yeni_ise_eski_taslak_kapanir(cevap):
        (_, _, k3), d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, kisa(cevap))
        assert (k3.eylem, _aynali_mi(k3.is_emri), k3.revizyon) == ("is_emri", False, 1)
        assert _pencere_var(k3.is_emri, "YATAK ODASI 1", "120x180") and not d.get("bekleyen_talep")
        assert k3.kullanilan_talep and k3.kullanilan_talep["katalog_kodu"] == "P6001"   # worker PDF başlığını buradan alır

    @pytest.mark.parametrize("cevap", ["değişiklik", "o taslağın değişikliği", "önceki", "eskisinin devamı", "aynı proje"])
    def test_b2_cevap_degisiklik_ise_eski_taslaga_eklenir(cevap):
        (_, _, k3), _ = senaryo(ILK, UC_BUCUK_SAAT_SONRA, kisa(cevap))
        assert (k3.eylem, _aynali_mi(k3.is_emri), k3.revizyon) == ("is_emri", True, 2)

    @pytest.mark.parametrize("cevap", ["yeni değil", "değişiklik yok", "hayır yeni", "yeni değişiklik", "evet", "yeniden çiz",
                                       "değişiklik ama ayna olmasın", "yeni ev", "yenile", "Eskişehir"])
    def test_b2_belirsiz_olumsuz_ya_da_ekli_cevapta_soru_yinelenir(cevap):
        (_, _, k3), d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, kisa(cevap))
        assert (k3.eylem, k3.soru_alani) == SORU and d.get("bekleyen_talep")

    def test_b2_anlasilmayan_cevapta_yinelenir_sonra_insana_devredilir():
        kararlar, d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, kisa("bilmiyorum"), kisa("hmm"), kisa("tamam"))
        assert [x.eylem for x in kararlar[1:]] == ["sor", "sor", "sor", "yonlendir"]
        assert "bekleyen mesaj" in kararlar[-1].gerekce and "P6001" in kararlar[-1].gerekce   # Lokman'a giden bildirimde
        assert not d.get("bekleyen_talep") and d.get("son_soru_alani") is None

    def test_b2_selam_sonrasi_da_sorulur():
        """2 saatlik süre taslağın değiştiği andan sayılır; araya giren selam süreyi yenilemez."""
        (_, _, k3), _ = senaryo(ILK, (3.5, "Merhaba", _talep("selam", "selam", "yuksek")), (0, ACIK, T_PENCERE()))
        assert (k3.eylem, k3.soru_alani) == SORU

    @pytest.mark.parametrize("metin", ["Merhaba, P6001 yatak odası 1 penceresi 120x180 olsun",
                                       "*P6001* yatak odası 1 penceresi 120x180 olsun", "P 6001 yatak odası 1 penceresi 120x180 olsun",
                                       "6001 yatak odası 1 penceresi 120x180 olsun", "P6001'in yatak odası 1 penceresi 120x180 olsun"])
    def test_b2_model_kodu_bicimleri_taninir(metin):
        (_, k2), _ = senaryo(ILK, (3.5, metin, T_PENCERE()))
        assert (k2.eylem, k2.soru_alani) == SORU

    def test_b2_soru_askidayken_baska_model_yeni_talep_olarak_islenir():
        t = _talep("yeni_talep", "P7401 istiyorum.", "yuksek", katalog_kodu="P7401")
        (_, _, k3), d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, (0, "P7401 istiyorum", t))
        assert (k3.eylem, k3.soru_alani) != SORU and not d.get("bekleyen_talep")
        assert "P7401" in k3.mesaj          # P7401 yeni talep olarak işlendi (şablonu yok → Lokman'a yönlendirilir)

    def test_b2_soru_askidayken_uzun_mesaj_normal_islenir_eski_mesaj_dirilmez():
        uzun = "müşteri aslında yatak odası penceresini de büyük istiyor sanırım"
        kararlar, d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, kisa(uzun), kisa("yeni"))
        assert (kararlar[2].eylem, kararlar[2].soru_alani) != SORU and kararlar[3].eylem != "is_emri"
        assert "işlemedim" in kararlar[2].mesaj and not d.get("bekleyen_talep")      # düşen mesaj bayiye söylenir

    @pytest.mark.parametrize("cevap, aynali", [("P6001 yeni", False), ("P6001 değişiklik", True), ("*P6001* yeni talep", False)])
    def test_b2_ayni_model_koduyla_verilen_cevap_cevap_sayilir(cevap, aynali):
        niyet = "yeni_talep" if "yeni" in cevap else "revizyon"
        t = _talep(niyet, cevap, "orta", katalog_kodu="P6001")
        (_, _, k3), _ = senaryo(ILK, UC_BUCUK_SAAT_SONRA, (0, cevap, t))
        assert (k3.eylem, _aynali_mi(k3.is_emri)) == ("is_emri", aynali)
        assert _pencere_var(k3.is_emri, "YATAK ODASI 1", "120x180")                # bekletilen pencere değişikliği kaybolmadı

    def test_b2_soru_askidayken_genel_soru_bekleyeni_dusurur_bayiye_soyler_sayac_kalmaz():
        t = _talep("soru", "P6001 fiyatı soruluyor.", "yuksek", katalog_kodu="P6001")
        (_, _, k3), d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, (0, "P6001 fiyatı ne kadar", t))
        assert k3.eylem == "cevapla" and "işlemedim" in k3.mesaj
        assert not d.get("bekleyen_talep") and "eski_taslak_soru" not in d

    def test_b2_soru_askidayken_iptal_edilebilir():
        (_, _, k3), d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, (0, "iptal", _talep("red", "iptal", "yuksek")))
        assert (k3.eylem, k3.soru_alani) == ("sor", "revizyon_ne") and not d.get("bekleyen_talep")

    def test_b2_soru_askidayken_yeni_model_kodlu_mesaj_bekleyeni_degistirir():
        yo2 = (0, "P6001 yatak odası 2 penceresi 60x40 olsun", T_PENCERE(mahal="Yatak Odası 2", olcu="60x40"))
        kararlar, _ = senaryo(ILK, UC_BUCUK_SAAT_SONRA, yo2, kisa("yeni"))
        assert (kararlar[2].eylem, kararlar[2].soru_alani) == SORU
        son = kararlar[3]
        assert son.eylem == "is_emri" and not _aynali_mi(son.is_emri)
        assert _pencere_var(son.is_emri, "YATAK ODASI 2", "60x40") and not _pencere_var(son.is_emri, "YATAK ODASI 1", "120x180")

    def test_b2_cevapta_bekletilen_mesajin_sozu_okunur():
        """Kurallar bayinin sözünü bekletilen mesajdan okur, kısa cevaptan değil ('ekle' → desteklenmiyor, İş Emri yok)."""
        ekle = (3.5, "P6001 yatak odası 1'e bir tane daha 120x180 pencere ekle", T_PENCERE(islem="ekle"))
        (_, _, k3), _ = senaryo(ILK, ekle, kisa("değişiklik"))
        assert k3.eylem != "is_emri"

    def test_b2_cevap_yeni_toplanan_taslakta_da_eskiyi_kapatir():
        """İş Emri çıkmamış, bilgi toplanan bir taslakta da 'yeni' eski aynayı taşımamalı."""
        eksik = (0, "P6001 aynalı, yatak odası 1 penceresi", _talep("yeni_talep", "P6001 aynalı, yatak odası 1 penceresi.", "yuksek",
                 katalog_kodu="P6001", varyantlar=[Varyant(tur="ayna_x", aciklama="aynalı")],
                 pencereler=[Pencere(mahal="Yatak Odası 1", olcu=None, islem="degistir")]))
        kararlar, _ = senaryo(eksik, (3.5, ACIK, T_PENCERE("yeni_talep")), kisa("yeni"))
        assert kararlar[0].eylem == "sor", "ön koşul: ilk mesaj bilgi toplayan bir taslak bırakmalı"
        assert (kararlar[1].eylem, kararlar[1].soru_alani) == SORU
        assert (kararlar[2].eylem, _aynali_mi(kararlar[2].is_emri)) == ("is_emri", False)

    def test_b2_bir_gunden_eski_soru_yok_sayilir():
        kararlar, d = senaryo(ILK, UC_BUCUK_SAAT_SONRA, (25, "yeni", _talep("diger", "yeni")))
        assert kararlar[2].eylem != "is_emri" and not d.get("bekleyen_talep")

    def test_b2_kontrol_kisa_arada_sorulmaz():
        """2 saatten kısa arada gelen mesaj taslağın devamıdır (bugünkü davranış korunur)."""
        (_, k2), _ = senaryo(ILK, (1.0, ACIK, T_PENCERE()))
        assert (k2.eylem, _aynali_mi(k2.is_emri), k2.revizyon) == ("is_emri", True, 2)

    def test_b2_kontrol_model_kodu_yoksa_sorulmaz():
        """Uzun aradan sonra da olsa model koduyla başlamayan mesaj taslağın devamıdır (D-01 kapsamı)."""
        (_, k2), _ = senaryo(ILK, (3.5, PENCERE_SOZU, T_PENCERE()))
        assert (k2.eylem, _aynali_mi(k2.is_emri), k2.revizyon) == ("is_emri", True, 2)

    def test_b2_kontrol_model_kodu_ortada_ise_sorulmaz():
        """D-01 'model koduyla başlayan' der; kod ortada geçiyorsa bugünkü davranış sürer."""
        (_, k2), _ = senaryo(ILK, (3.5, "yatak odası 1 penceresi P6001 için 120x180 olsun", T_PENCERE()))
        assert (k2.eylem, k2.soru_alani) != SORU


if __name__ == "__main__":
    print("B1 işlem boş      :", b1_islem_bos(), "(beklenen: sor)")
    print("B1 işlem degistir :", b1_islem_degistir(), "(beklenen: sor)")
    print("Kontrol işlem ekle:", b1_kontrol_ekle(), "(beklenen: sor)")
    print("Kontrol açık söz  :", b1_kontrol_acik_soz(), "(beklenen: is_emri)")
    ilk, e, a, r = b2_uzun_aradan_sonra()
    print(f"B2 3,5 saat sonra : ilk aynalı={ilk}; ikinci eylem={e}, aynalı={a}, revizyon={r} (beklenen: sor)")
