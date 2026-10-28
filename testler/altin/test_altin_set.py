"""İE-19 · altın set: vakaların biçimi, gerileme kapısı (baz çizgisi), harness'le tutarlılık, kör mühür ve ücretli kaydın freni.

Her koşuda (LLM yok, Postgres yok, çizim yok): açık vakalar beklenen okumayla kural katmanından geçer; bugün uyumlu olan her vaka uyumlu
kalmalı, güvenlik sayacı (soru gerekirken plan) büyümemeli, kayıtlı okumanın sayıları düşmemeli. Bugün uyumsuz vakalar "rehberde var,
bugün çalışmıyor" listesidir (`baz.json`); düzelen vaka baz yeniden yazılınca kapıya girer (`--baz-yaz`, gerekçesiyle).

Kör dilim depo dışındadır; burada yalnız mührün biçimi ve "mühür tutmazsa koşmaz" kuralı uydurma bir dilimle denenir. Gerçek kör
dilimi koşmak için: `PORTMAN_ALTIN_KOR=<klasör> pytest -q testler/altin` (yalnız sayılar yazılır).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from testler.altin import kos as A  # noqa: E402

ADIMLAR = {"selam_soru", "kayitsiz_kapsam", "eksik_bilgi", "bilgi_tam", "katalog_kodu", "secim", "revizyon", "onay_eski"}
# İE-19 planı (27 Ekim): 78 yeni vaka rehberin adımlarına göre; kör 20 oranla, açık 58
YENI = {"selam_soru": 6, "kayitsiz_kapsam": 6, "eksik_bilgi": 14, "bilgi_tam": 12, "katalog_kodu": 10, "secim": 8, "revizyon": 16, "onay_eski": 6}
KOR = {"selam_soru": 2, "kayitsiz_kapsam": 1, "eksik_bilgi": 4, "bilgi_tam": 3, "katalog_kodu": 3, "secim": 2, "revizyon": 4, "onay_eski": 1}
KARAR_ALANLARI = {"eylem", "soru_alani", "gerekce", "plan_uretimi", "secenek", "secenek_icerir", "plan_kodu", "revizyon", "degisiklikler",
                  "mesaj_icerir", "mesaj_icermez"}


@pytest.fixture(scope="module")
def senaryolar():
    return A.yukle()


@pytest.fixture(scope="module")
def sonuc(senaryolar):
    kay = {**A.harness_kayitlari(), **A.kayit_dizininden(A.KAYITLAR)}      # aracın okuduğu kayıtlar (`kos.main` gibi)
    kk = A.kos(senaryolar, "K")
    return {"kk": kk, "o": A.okuma_olcusu(A.vakalar(senaryolar), kay), "uu": A.kos(senaryolar, "U", kay)}


def _baz() -> dict:
    return json.loads(A.BAZ.read_text(encoding="utf-8"))


# ── biçim ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_vakalar_bicimi(senaryolar):
    d = json.loads(A.VAKALAR.read_text(encoding="utf-8"))
    assert d["sema"] == "portman.altin_set/0.1"
    tum = [a for s in senaryolar for a in s["adimlar"]]
    kimlik = [a["id"] for a in tum]
    assert len(kimlik) == len(set(kimlik)), "vaka kimlikleri tekil olmalı"
    for a in A.vakalar(senaryolar):
        assert a.get("adim") in ADIMLAR, a["id"]
        assert set(a.get("karar") or {}) <= KARAR_ALANLARI and (a.get("karar") or {}).get("eylem"), a["id"]
        assert a.get("kaynak"), a["id"]
        assert bool(a.get("dugme")) != bool(a.get("mesaj")), a["id"]
        if a.get("mesaj"):
            A.gold_talep(a)                                     # beklenen okuma şemaya uyar
            if not a["id"].startswith("H"):
                assert A.maske(a["mesaj"]) == a["mesaj"], f"{a['id']}: vakaya numara ya da kişi adı yazılmaz"
            for alan in a.get("okuma_kabul") or {}:
                assert alan in A.OKUMA_ALANLARI, (a["id"], alan)


def test_harness_vakalari_kopyasiz_ve_tam(senaryolar):
    """22 harness vakası beyin/testler/'den okunur (kopya yok); her birinin beklenen okuması var."""
    h = next(s for s in senaryolar if s["id"] == "H")
    mesajlar = json.loads((A.HARNESS_DIR / "mesajlar.json").read_text(encoding="utf-8"))
    assert [a["id"] for a in h["adimlar"]] == [f"H{m['id']:02d}" for m in mesajlar] and len(mesajlar) == 22
    assert all(a["okuma"] and a["adim"] in ADIMLAR for a in h["adimlar"])
    d = json.loads(A.VAKALAR.read_text(encoding="utf-8"))
    assert not any(str(x.get("mesaj")) in {m["mesaj"] for m in mesajlar} for s in d["senaryolar"] for x in s["adimlar"])


def test_acik_dagilim(senaryolar):
    yeni = [a for a in A.vakalar(senaryolar) if not a["id"].startswith("H")]
    beklenen = {a: YENI[a] - KOR[a] for a in YENI}
    assert dict(Counter(a["adim"] for a in yeni)) == beklenen
    assert len(yeni) == 58 and sum(KOR.values()) == 20 and sum(YENI.values()) == 78


# ── gerileme kapısı ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_baz_vaka_listesi_guncel(sonuc):
    assert set(_baz()["karar"]) == {s["id"] for s in sonuc["kk"]}, "vaka eklendi ya da çıktı: baz çizgisi `--baz-yaz` ile yeniden yazılmalı"


def test_karar_gerilemesi_yok(sonuc):
    baz = _baz()["karar"]
    geriledi = [f"{s['id']}: {'; '.join(s['hata'])}" for s in sonuc["kk"] if baz.get(s["id"]) and not s["uyum"]]
    assert not geriledi, "bugün uyumlu olan vaka bozuldu:\n" + "\n".join(geriledi)


def test_guvenlik_sayaci_buyumedi(sonuc):
    yeni = sorted(s["id"] for s in sonuc["kk"] if s["guvenlik"] and s["id"] not in _baz()["guvenlik"])
    assert not yeni, f"soru ya da yönlendirme gerekirken plan üretilen yeni vaka: {yeni}"


def test_okuma_dusmedi(sonuc):
    baz = _baz()["okuma"]
    o = sonuc["o"]
    assert o["tam"][1] == baz["tam"][1] and o["tam"][0] >= baz["tam"][0]
    for alan, h in o["alanlar"].items():
        for tur in ("dolu", "bos"):
            assert h[tur][0] >= baz["alanlar"][alan][tur][0], (alan, tur)


def test_harness_uctan_uca_harness_ile_ayni(sonuc):
    """Kayıtlı okumayla harness'in 22 vakası harness'in kendisiyle aynı sonucu verir (araç harness'i doğru oynatıyor)."""
    h = [s for s in sonuc["uu"] if s["senaryo"] == "H"]
    assert len(h) == 22 and all(s["uyum"] for s in h), [s["id"] for s in h if not s["uyum"]]


def test_hazirlik_adimi_puanlanmaz(senaryolar, sonuc):
    hazirlik = {a["id"] for s in senaryolar for a in s["adimlar"] if a.get("hazirlik")}
    assert hazirlik and not hazirlik & {s["id"] for s in sonuc["kk"]}


def test_uyum_kurallari():
    """Beklenen karar alanlarından her biri yanlışı yakalar (gevşek eşleşme yok)."""
    from beyin.sema import Karar
    k = Karar(eylem="sor", soru_alani="dis_olcu", gerekce="eksik: dis_olcu", mesaj="Dış ölçü?")
    assert not A.karar_uyumu({"eylem": "sor", "soru_alani": ["cati", "dis_olcu"]}, k, {})
    assert A.karar_uyumu({"eylem": "sor", "soru_alani": "cati"}, k, {})
    assert A.karar_uyumu({"eylem": ["is_emri", "secenek"]}, k, {})
    assert A.karar_uyumu({"eylem": "sor", "mesaj_icermez": ["Dış"]}, k, {})
    assert A.guvenlik_ihlali({"eylem": "sor"}, Karar(eylem="is_emri"))
    assert not A.guvenlik_ihlali({"eylem": "sor"}, Karar(eylem="yonlendir"))


def test_okuma_kiyasi_kurallari():
    adim = {"okuma": {"niyet": "yeni_talep", "katalog_kodu": "P6001", "pencereler": [{"mahal": "Yatak Odası 1", "olcu": "120x180"}]},
            "okuma_kabul": {"niyet": ["revizyon"]}}
    # pencere varyant parametresiyle de gelebilir; mahal büyük-küçük harf ve Türkçe harf farkı sayılmaz
    llm = {"niyet": "revizyon", "katalog_kodu": "p6001", "varyantlar": [{"tur": "pencere_degistir", "aciklama": "x",
                                                                          "parametreler": {"mahal": "yatak odası 1", "yeni": "120x180"}}]}
    k = A.okuma_kiyasi(adim, llm)
    assert all(d for _, d in k.values()), k
    k = A.okuma_kiyasi(adim, {**llm, "niyet": "onay", "alan_m2": 60})
    assert not k["niyet"][1] and k["alan_m2"] == (False, False)      # boş kalması gereken alan doldurulmuş


# ── kör dilim ───────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_kor_muhur_bicimi():
    m = json.loads(A.MUHUR.read_text(encoding="utf-8"))
    assert len(m["sha256"]) == 64 and int(m["sha256"], 16) >= 0 and m["bayt"] > 0
    assert m["vaka_sayisi"] == 20 and m["adim"] == dict(sorted(KOR.items()))
    assert set(m) == {"aciklama", "sha256", "bayt", "vaka_sayisi", "adim", "tarih", "onay"}, "mühürde cümle ya da beklenen değer olmaz"


def test_kor_muhur_tutmazsa_kosmaz(tmp_path):
    kor = tmp_path / "kor"; kor.mkdir()
    sen = [{"id": "u1", "dilim": "kor", "adimlar": [{"id": "u01", "adim": "selam_soru", "mesaj": "uydurma selam", "kaynak": "uydurma",
                                                    "okuma": {"niyet": "selam"}, "karar": {"eylem": "cevapla", "gerekce": "selam"}}]}]
    (kor / "vakalar.json").write_text(json.dumps({"sema": "portman.altin_set/0.1", "senaryolar": sen}, ensure_ascii=False), encoding="utf-8")
    muhur = tmp_path / "muhur.json"
    A.muhurle(kor, muhur, onay="uydurma")
    ok, satir = A.kor_kos(kor, muhur)
    assert ok and satir[0] == "kör dilim (mühür tuttu)" and "1/1" in satir[1]
    assert not any("uydurma selam" in x for x in satir), "kör sonuçta cümle yazılmaz"
    (kor / "vakalar.json").write_bytes((kor / "vakalar.json").read_bytes().replace(b"selam\"", b"selan\""))
    ok, satir = A.kor_kos(kor, muhur)
    assert not ok and "mühür tutmadı" in satir[0]


@pytest.mark.skipif(not os.environ.get("PORTMAN_ALTIN_KOR"), reason="kör dilim klasörü verilmedi (PORTMAN_ALTIN_KOR)")
def test_kor_dilim_gercek():
    ok, satir = A.kor_kos(Path(os.environ["PORTMAN_ALTIN_KOR"]))
    print("\n".join(satir))
    assert ok, satir


# ── ücretli kayıt freni ─────────────────────────────────────────────────────────────────────────────────────────────────────

def test_kaydet_ucretli_onaysiz_cagirmaz(tmp_path):
    with pytest.raises(SystemExit, match="ücretli"):
        A.kaydet([], tmp_path / "k", "anthropic", None, 5, ucretli=False)


def test_kaydet_tavani_tekrari_sayar(tmp_path, monkeypatch):
    """Şema hatasındaki tekrar ikinci ücretli çağrıdır: tavan en kötü duruma göre (mesaj başına iki) uygulanır, hata koşuyu durdurur.
    Gerçek arka uç çağrılmaz (çıkarım sahte)."""
    from beyin import llm
    from beyin.sema import Talep
    sayac = []

    def sahte(mesaj, baglam="", backend="manuel", model=None, hazir=None, **kw):
        sayac.append(mesaj)
        if mesaj == "patla":
            raise TimeoutError("sahte")
        return Talep(niyet="selam", guven="yuksek", ozet="x"), {"backend": backend, "tekrar": 1}
    monkeypatch.setattr(llm, "cikar_guvenli", sahte)
    sen = [{"id": "t", "adimlar": [{"id": f"t0{i}", "adim": "selam_soru", "mesaj": f"selam {i}", "kaynak": "uydurma", "okuma": {"niyet": "selam"},
                                    "karar": {"eylem": "cevapla"}} for i in range(1, 4)]}]
    r = A.kaydet(sen, tmp_path / "k", "anthropic", "uydurma", 5, ucretli=True)
    assert r == {"cagri": 4, "yazilan": 2, "atlanan": 0, "durdu": "tavan"} and len(sayac) == 2
    sen[0]["adimlar"].append({**sen[0]["adimlar"][0], "id": "t09", "mesaj": "patla"})
    sen[0]["adimlar"][2]["id"] = "t08"
    r = A.kaydet(sen, tmp_path / "k", "anthropic", "uydurma", 10, ucretli=True)
    assert r["durdu"] == "hata t09: TimeoutError" and r["atlanan"] == 2 and r["yazilan"] == 1 and r["cagri"] == 4


def test_kaydet_manuel_ve_oynatma(tmp_path):
    """Kayıt aracı (manuel arka uç, LLM yok): her mesajın okuması `<id>.json`'a yazılır, var olan kayıt yeniden çağrılmaz; yazılan kayıtla
    uçtan uca ve okuma ölçüsü koşar."""
    sen = [{"id": "m", "adimlar": [
        {"id": "m01", "adim": "katalog_kodu", "mesaj": "P6001 aynalı", "kaynak": "uydurma", "okuma": {"niyet": "yeni_talep", "katalog_kodu": "P6001",
         "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}]}, "karar": {"eylem": "is_emri", "plan_kodu": "P6001"}},
        {"id": "m02", "adim": "onay_eski", "dugme": "o:{is_emri}:{rev}", "kaynak": "uydurma", "karar": {"eylem": "cevapla", "gerekce": "plan onaylandı"}}]}]
    hazir = {"m01": {"niyet": "yeni_talep", "katalog_kodu": "P6001", "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}], "guven": "yuksek",
                     "ozet": "P6001 aynalı"}}
    r = A.kaydet(sen, tmp_path / "k", "manuel", None, 0, ucretli=False, hazir=hazir)
    assert r == {"cagri": 0, "yazilan": 1, "atlanan": 0, "durdu": None}
    assert A.kaydet(sen, tmp_path / "k", "manuel", None, 0, ucretli=False, hazir={})["atlanan"] == 1
    kay = A.kayit_dizininden(tmp_path / "k")
    uu = A.kos(sen, "U", kay)
    assert [s["uyum"] for s in uu] == [True, True]
    o = A.okuma_olcusu(A.vakalar(sen), kay)
    assert o["tam"] == [1, 1]
