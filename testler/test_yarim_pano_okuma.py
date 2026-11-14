"""İE-39 PR-2 (D-90) · bayinin WhatsApp'ta yazdığı "sağa yarım pano uzat" komutu.

Kural bayinin kendi sözünü okur (`beyin/yarim_pano_okuma.py`, K18); komut havuz evinin İş Emri'ne `beyin/yarim_pano.uygula` ile işlenir
(`beyin/karar.py`). Ayar `yarim_pano.acik` kapalıyken (varsayılan) bugünkü yol: LLM'in değişikliği "otomatik yapılamıyor" diye yönlendirilir.
"1 pano" tam panodur: 125,5 cm (Lokman, kart 14 Kasım 2026 12:54:43 UTC "125,5 cm (tam pano)").
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür (LLM'in canlıda verdiği biçimde).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import yarim_pano as YP  # noqa: E402
from beyin import yarim_pano_okuma as YPO  # noqa: E402
from test_celik_revizyon_karar import Sohbet  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402

HAZIR = "Ön onay planınız hazır; plan görseli ve PDF ektedir."
YON = "Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak."


# ── okuma: bayinin cümlesi ──────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("soz,komut", [
    ("sağa yarım pano uzat", [("sag", 1)]),
    ("SAĞA YARIM PANO UZAT", [("sag", 1)]),
    ("Sağ duvarı yarım pano uzatın", [("sag", 1)]),
    ("evi öne doğru iki yarım pano büyütelim", [("on", 2)]),
    ("ön taraftan yarım pano kısalt", [("on", -1)]),
    ("sağa yarım pano uzatılsın", [("sag", 1)]),
    ("sağa yarım pano uzatmak istiyoruz", [("sag", 1)]),
    ("Sağa yarım pano uzatabilir misiniz?", [("sag", 1)]),           # rica biçimi komuttur
    ("Önce sağa yarım pano uzatın", [("sag", 1)]),                   # "önce" ön duvar değil
    ("yarım pano uzat sağa", [("sag", 1)]),
    # "1 pano" tam pano: 2 yarım pano (Lokman 14 Kasım 12:54:43 UTC)
    ("sağa 1 pano uzat", [("sag", 2)]),
    ("sağa bir pano uzat", [("sag", 2)]),
    ("sağa pano uzat", [("sag", 2)]),
    ("arkaya 2 pano uzat", [("arka", 4)]),
    ("sağa 3 yarım pano kısalt", [("sag", -3)]),
    # birden çok komut
    ("sağa yarım pano uzat, öne de yarım pano kısaltın.", [("sag", 1), ("on", -1)]),
    ("sağa ve öne yarım pano uzat", [("sag", 1), ("on", 1)]),
    ("Mutfak penceresi 120x120 olsun. Sağa yarım pano uzat", [("sag", 1)]),
    # sol ve arka da okunur (uygulamada dilim dışı)
    ("sola yarım pano uzat", [("sol", 1)]),
])
def test_komut_okunur(soz, komut):
    k, b = YPO.oku(soz)
    assert [(x.cephe, x.adim) for x in k] == komut and not b, (k, b)


@pytest.mark.parametrize("soz,neden", [
    ("yarım pano uzat", "hangi duvarın kayacağı yazılı değil"),
    ("sağa 1,5 pano uzat", "kaç pano kayacağı yazılı değil"),
    ("sağa bir buçuk pano uzat", "kaç pano kayacağı yazılı değil"),
    ("sağa yarım pano uzatmayın", "olumsuz istek"),
    ("sağa yarım pano uzatılmasın", "olumsuz istek"),
    ("sağa yarım pano uzatılabilir mi?", "soru biçiminde istek"),
    ("salonu sağa yarım pano büyüt", "oda adı"),
    ("mutfakta pano büyüt sağa", "oda adı"),
])
def test_komut_sayilmayan_pano_istegi(soz, neden):
    k, b = YPO.oku(soz)
    assert not k and len(b) == 1 and b[0].neden.startswith(neden), (k, b)


@pytest.mark.parametrize("soz", ["sağa uzat", "ön onay planını gönderin", "sağ tarafa pano ekleyin", "mutfak penceresi 120x120",
                                 "Onaylıyorum", "", None])
def test_pano_komutu_yok(soz):
    assert YPO.oku(soz) == ([], [])


def test_birlestir_duvar_basina_toplar():
    k = [{"cephe": "sag", "adim": 1}, {"cephe": "on", "adim": 1}, {"cephe": "sag", "adim": 1}, {"cephe": "on", "adim": -1}]
    assert YPO.birlestir(k) == [{"cephe": "sag", "adim": 2}]


# ── karar: havuz evinin açık planında ──────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=set(KABUL) | {"PA12", "PA23", "PA24"})


def _r01(s: Sohbet, kod: str, acik: bool = True):
    k = s.yaz(kod, katalog_kodu=kod)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1, k.mesaj
    s.k.yarim_pano = acik
    return k


def _yonlendirme(soz: str) -> dict:
    return {"tur": "olcu_degistir", "aciklama": soz}


def _sablon(kod: str) -> dict:
    return json.loads((KOK / "is_emri" / "adaylar" / f"{kod}.json").read_text(encoding="utf-8"))


def _geometri(ie: dict) -> tuple:
    return (json.dumps(ie["yapi"], sort_keys=True), json.dumps(ie["mahaller"], sort_keys=True), json.dumps(ie["acikliklar"], sort_keys=True))


def test_ayar_kapali_bugunku_yol(s):
    """Ayar kapalıyken (varsayılan) LLM'in değişikliği bugünkü gibi yönlendirilir; plan açık kalır."""
    _r01(s, "PA12", acik=False)
    k = s.yaz("Sağa yarım pano uzat", varyantlar=[_yonlendirme("Sağa yarım pano uzat")])
    assert k.eylem == "yonlendir" and k.mesaj.startswith('"Sağa yarım pano uzat" değişikliği otomatik yapılamıyor.'), k.mesaj
    assert s.plan["revizyon"] == 1


def test_hedef_ornekle_ayni_plan(s):
    """85 m² 3+1 ev, sağ duvar 1 yarım pano: WhatsApp'tan gelen komutun İş Emri'nin geometrisi Lokman'ın onayladığı hedef örnekle aynı
    (testler/yarim_pano/PA12_sag_arti1.json; kart 14 Kasım 10:11:06 UTC "Doğru, örnek olsun")."""
    _r01(s, "PA12")
    k = s.yaz("Sağa yarım pano uzatın", varyantlar=[_yonlendirme("Sağa yarım pano uzatın")])
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2, k.mesaj
    assert k.mesaj == ("PA-12 r02. Değişiklik: sağ duvar yarım pano uzadı (dış ölçü 1166 × 726 → 1228,75 × 726 cm; YATAK ODASI 2 11,8 → "
                       f"14,6 m²; YATAK ODASI 3 13,5 → 15,2 m²). {HAZIR}")
    hedef = json.loads((KOK / "testler" / "yarim_pano" / "PA12_sag_arti1.json").read_text(encoding="utf-8"))
    assert hedef["onay"]["zaman_utc"] == "2026-11-14T10:11:06Z"
    assert _geometri(k.is_emri)[1:] == _geometri(hedef["is_emri"])[1:]
    assert k.is_emri["yapi"]["dis_olcu_cm"] == hedef["is_emri"]["yapi"]["dis_olcu_cm"]


def test_llm_kopyasi_ikinci_kez_girmez(s):
    """LLM aynı cümleyi değişiklik ve özel istek olarak da yazsa komut bir kez uygulanır; özel istek İş Emri'ne geçmez."""
    _r01(s, "PA12")
    soz = "Sağa yarım pano uzat"
    k = s.yaz(soz, varyantlar=[_yonlendirme(soz), {"tur": "diger", "aciklama": "yapıyı sağa doğru yarım pano uzat"}], ozel_istekler=[soz])
    assert k.eylem == "is_emri" and k.is_emri["yapi"]["dis_olcu_cm"]["x"] == pytest.approx(1228.75), k.mesaj
    assert soz not in k.is_emri["ozel_istekler"]
    assert not [v for v in s.k.d["taslak"].get("varyantlar") or [] if "pano" in v.get("aciklama", "")]


def test_tam_pano(s):
    """"1 pano" 125,5 cm (Lokman, 14 Kasım 12:54:43 UTC)."""
    _r01(s, "PA12")
    k = s.yaz("Sağa 1 pano uzat")
    assert k.eylem == "is_emri", k.mesaj
    assert k.mesaj.startswith("PA-12 r02. Değişiklik: sağ duvar 1 pano uzadı (dış ölçü 1166 × 726 → 1291,5 × 726 cm;")
    beklenen = YP.uygula(_sablon("PA12"), "sag", 2)["is_emri"]
    assert _geometri(k.is_emri)[1:] == _geometri(beklenen)[1:]
    assert k.is_emri["yapi"]["dis_olcu_cm"] == beklenen["yapi"]["dis_olcu_cm"]


def test_komutlar_birikir_ve_geri_alinir(s):
    _r01(s, "PA12")
    s.yaz("sağa yarım pano uzat")
    k = s.yaz("sağa yarım pano daha uzat")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 3 and k.is_emri["yapi"]["dis_olcu_cm"]["x"] == pytest.approx(1291.5), k.mesaj
    s.yaz("sağa yarım pano kısalt")
    k = s.yaz("sağa yarım pano kısalt")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 5, k.mesaj
    assert k.mesaj == f"PA-12 r05. Değişiklik: sağ duvar ilk yerine döndü. {HAZIR}"
    assert _geometri(k.is_emri)[1:] == _geometri(_sablon("PA12"))[1:]


def test_on_duvar_d30(s):
    """49 m² 1+1 ev, ön duvar: Motor son panoyu tamamlar (D-30), dış ölçü 63 cm büyür; mesaj Motor'un ölçüsünü yazar."""
    _r01(s, "PA23")
    k = s.yaz("öne yarım pano uzat")
    assert k.eylem == "is_emri", k.mesaj
    assert k.mesaj.startswith("PA-23 r02. Değişiklik: ön duvar yarım pano uzadı (dış ölçü 700 × 700 → 700 × 763 cm; SALON & MUTFAK")


def test_ilk_planda_komut(s):
    """Ev seçilirken yazılan komut ilk planda uygulanır."""
    s.k.yarim_pano = True
    k = s.yaz("PA12 sağa yarım pano uzat", katalog_kodu="PA12", varyantlar=[{"tur": "diger", "aciklama": "sağa yarım pano uzat"}])
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1, k.mesaj
    assert k.mesaj.startswith("PA-12 seçildi. Değişiklik: sağ duvar yarım pano uzadı (dış ölçü 1166 × 726 → 1228,75 × 726 cm;")


def test_pencereyle_birlikte(s):
    """Aynı mesajdaki pencere değişikliği de uygulanır (yarım pano önce, pencere sonra)."""
    _r01(s, "PA24")
    k = s.yaz("Sağa yarım pano uzat. Yatak odası penceresi 120x180 olsun",
              pencereler=[{"mahal": "YATAK ODASI", "olcu": "120x180", "islem": "degistir"}])
    assert k.eylem == "is_emri", k.mesaj
    assert "sağ duvar yarım pano uzadı" in k.mesaj and "YATAK ODASI penceresi 120x180" in k.mesaj
    assert k.is_emri["yapi"]["dis_olcu_cm"]["x"] == pytest.approx(835.75)


@pytest.mark.parametrize("kod,soz,neden", [
    ("PA12", "öne yarım pano uzat", "veranda bu duvara değiyor; veranda uzamaz"),
    ("PA12", "sola yarım pano uzat", "bugün yalnız sağ ve ön duvar uzatılıp kısaltılabiliyor"),
    ("PA23", "sağa yarım pano kısalt", "kapı ya da pencere yerinde kalmıyor"),
    ("PA01", "sağa yarım pano uzat", "bu evin planı sabit, değiştirilemiyor"),
])
def test_kural_tutmazsa_gerekce_plan_acik(s, kod, soz, neden):
    _r01(s, kod)
    no = s.plan["is_emri_no"]
    k = s.yaz(soz, varyantlar=[_yonlendirme(soz)])
    assert k.eylem == "yonlendir" and k.gerekce.startswith("yarım pano komutu durdu"), k.mesaj
    assert f"isteği bu evde otomatik yapılamıyor: {neden}. {YON}" in k.mesaj
    assert k.mesaj.endswith(f"Planınız ({no} r01) değişmedi. Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.")
    assert s.plan["revizyon"] == 1 and s.k.d["asama"] == "onay_bekliyor" and not s.k.d["taslak"].get("yarim_pano")


def test_okunamayan_pano_istegi_soylenir(s):
    _r01(s, "PA12")
    no = s.plan["is_emri_no"]
    k = s.yaz("yarım pano uzat", varyantlar=[_yonlendirme("yarım pano uzat")])
    assert k.eylem == "cevapla", k.mesaj
    assert k.mesaj == ('"yarım pano uzat" isteğini uygulamadım: hangi duvarın kayacağı yazılı değil. Örnek: "sağa yarım pano uzat" ya da '
                       f'"öne 1 pano kısalt". Planınız ({no} r01) değişmedi. Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.')
    assert s.plan["revizyon"] == 1


def test_oda_buyutme_yonlendirilir(s):
    _r01(s, "PA12")
    k = s.yaz("Salonu sağa yarım pano büyüt", varyantlar=[{"tur": "oda_ekle", "aciklama": "Salonu sağa yarım pano büyüt"}])
    assert k.eylem == "yonlendir" and k.gerekce == "yarım pano: oda büyütme", k.mesaj
    assert k.mesaj.startswith('"Salonu sağa yarım pano büyüt" isteği otomatik yapılamıyor: yarım pano komutu evin dış duvarını kaydırır')


def test_celik_evde_bugunku_yol(s):
    """Çelik evde (genel motor) komut okunmaz: bugünkü çelik okuması karar verir."""
    from beyin import karar as K
    from beyin.sema import Talep
    assert s.kat.aday("KT01")["motor"] == "genel"
    t = Talep(guven="yuksek", ozet="x", niyet="revizyon", katalog_kodu="KT01")
    assert K._yarim_pano_sozu(s.k, t, "sağa yarım pano uzat", s.kat) is None


def test_ayar_varsayilan_kapali():
    sys.path.insert(0, str(KOK / "kanal"))
    from kanal import ayarlar
    assert ayarlar.VARSAYILAN["yarim_pano"] == {"acik": False}
    sys.path.insert(0, str(KOK / "vps"))
    import importlib
    agent = importlib.import_module("vps.agent")
    assert agent.isleme_ayari({"yarim_pano": {"acik": True}})["yarim_pano"] == {"acik": True}
    assert agent.isleme_ayari({})["yarim_pano"] == {}


# ── bayiye giden metin: hedef örnek (85 m² 3+1 ev) ─────────────────────────────────────────────────────────────────────────────────
# Bayiye giden metin bir çıktıdır (D-28): hedef `testler/yarim_pano/whatsapp_ornek.json`, Lokman'ın onayı `onay` alanında.
# Yeniden üretmek: `python testler/test_yarim_pano_okuma.py --dondur` (onay alanı korunur).

ORNEK = KOK / "testler" / "yarim_pano" / "whatsapp_ornek.json"
ORNEK_ADIMLAR = [("PA12", {"katalog_kodu": "PA12"}),
                 ("Sağa yarım pano uzatın", {"varyantlar": [{"tur": "olcu_degistir", "aciklama": "Sağa yarım pano uzatın"}]}),
                 ("Sola da yarım pano uzatın", {"varyantlar": [{"tur": "olcu_degistir", "aciklama": "Sola da yarım pano uzatın"}]}),
                 ("Öne yarım pano uzatın", {}),
                 ("yarım pano daha uzat", {}),
                 ("Sağa yarım pano kısaltın", {}),
                 ("Sağa 1 pano uzatın", {})]
_NO = __import__("re").compile(r"PM-[A-Z0-9]+-\d{8}-\d+")


def konusma_ornegi(kok: Path) -> list[dict]:
    s = Sohbet(kok, kabul=set(KABUL) | {"PA12"})
    s.k.yarim_pano = True
    out = []
    for soz, alan in ORNEK_ADIMLAR:
        k = s.yaz(soz, **alan)
        out.append({"bayi": soz, "eylem": k.eylem, "revizyon": s.plan.get("revizyon"), "mesaj": _NO.sub("PM-…", k.mesaj),
                    "dis_olcu_cm": [s.plan["yapi"]["dis_olcu_cm"]["x"], s.plan["yapi"]["dis_olcu_cm"]["y"]]})
    return out


def test_whatsapp_ornegi(tmp_path):
    hedef = json.loads(ORNEK.read_text(encoding="utf-8"))
    assert konusma_ornegi(tmp_path) == hedef["konusma"]


def _dondur():
    import tempfile
    eski = json.loads(ORNEK.read_text(encoding="utf-8")) if ORNEK.exists() else {}
    veri = {"aciklama": "İE-39 PR-2: 85 m² 3+1 havuz evinde bayinin WhatsApp yazışması (ayar yarim_pano.acik). Plan numarası PM-… diye "
                        "yazılır (saate bağlı). Üreten: testler/test_yarim_pano_okuma.py --dondur.",
            "onay": eski.get("onay"), "konusma": konusma_ornegi(Path(tempfile.mkdtemp()))}
    ORNEK.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(veri, ensure_ascii=False, indent=1))


if __name__ == "__main__" and "--dondur" in sys.argv:
    _dondur()
