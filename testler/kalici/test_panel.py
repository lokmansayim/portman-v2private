"""İE-06 · kanal/panel.py: giriş (scrypt, ön çerez + CSRF), 5 başarısız girişte 15 dk kilit (IP ve hesap), imzalı oturum çerezi,
CSRF'siz POST reddi, bayi ekle/düzenle, gelen kutusu, konuşma sayfası, dosya indirme (yalnız gelen_medya altı), güvenlik başlıkları.
WSGI uygulaması doğrudan çağrılır; gerçek Postgres; ağ, LLM, WhatsApp yok."""
from __future__ import annotations

import hashlib
import re
import time
import urllib.parse
from io import BytesIO

import pytest

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import kalici
import panel as PN

SIR = "f" * 64
DOGRU = "deneme-" + "k" * 14                 # çalışma anında kurulan deneme değeri
NUMARA_X = "900000000777"                   # kayıtsız (gerçek olmayan)
NUMARA_Y = "900000000888"
AYAR_P = {**AYAR, "enabled": True, "dry_run": True, "mode": "patron"}


@pytest.fixture
def pn(depo, kanal_dizini):
    return PN.Panel(depo=depo, veri=kanal_dizini, sir=SIR, parola=PN.parola_ozeti(DOGRU), ayar_oku=lambda: dict(AYAR_P))


class Istemci:
    """Çerezleri tutan küçük WSGI istemcisi."""

    def __init__(self, p: PN.Panel, ip: str = "10.0.0.1"):
        self.app = PN.uygulama_olustur(p); self.cerez = {}; self.ip = ip

    def git(self, metod: str, yol: str, form: dict | None = None, sorgu: str = "", cerezsiz: bool = False):
        govde = urllib.parse.urlencode(form).encode() if form is not None else b""
        env = {"REQUEST_METHOD": metod, "PATH_INFO": yol, "QUERY_STRING": sorgu, "CONTENT_LENGTH": str(len(govde)), "wsgi.input": BytesIO(govde),
               "REMOTE_ADDR": self.ip}
        if form is not None:
            env["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        if self.cerez and not cerezsiz:
            env["HTTP_COOKIE"] = "; ".join(f"{a}={v}" for a, v in self.cerez.items())
        out = {}

        def sr(status, headers):
            out["status"] = int(status.split()[0]); out["headers"] = headers
        govde = b"".join(self.app(env, sr))
        for a, v in out["headers"]:
            if a == "Set-Cookie":
                ad, deger = v.split(";", 1)[0].split("=", 1)
                if "Max-Age=0" in v:
                    self.cerez.pop(ad, None)
                else:
                    self.cerez[ad] = deger
        return out["status"], govde, out["headers"]

    @staticmethod
    def csrf(metin: bytes) -> str:
        return re.search(rb'name="csrf" value="([0-9a-f]+)"', metin).group(1).decode()

    def giris(self, deger: str):
        _, h, _ = self.git("GET", "/panel/giris")
        return self.git("POST", "/panel/giris", {"parola": deger, "csrf": self.csrf(h)})

    def baslik(self, basliklar, ad):
        return [v for a, v in basliklar if a == ad]


def test_yapilandirilmamis_panel_503_giris_kabul_etmez(depo, kanal_dizini):
    c = Istemci(PN.Panel(depo=depo, veri=kanal_dizini, sir="", parola="", ayar_oku=lambda: AYAR_P))
    for yol in ("/panel/", "/panel/giris", "/panel/bayiler"):
        assert c.git("GET", yol)[0] == 503
    assert c.git("POST", "/panel/giris", {"parola": DOGRU, "csrf": "x"})[0] == 503
    assert sorgu(depo, "SELECT count(*) AS n FROM panel_girisler")[0]["n"] == 0


def test_giris_sayfasi_on_cerez_csrf_ve_guvenlik_basliklari(pn):
    c = Istemci(pn)
    kod, h, b = c.git("GET", "/panel/giris")
    assert kod == 200 and b'name="csrf"' in h and b'type="password"' in h
    cerez = c.baslik(b, "Set-Cookie")[0]
    assert cerez.startswith("pm_on=") and "HttpOnly" in cerez and "Secure" in cerez and "SameSite=Strict" in cerez and "Path=/panel" in cerez
    assert c.baslik(b, "Content-Security-Policy")[0].startswith("default-src 'self'") and c.baslik(b, "X-Frame-Options") == ["DENY"]
    assert c.baslik(b, "Cache-Control") == ["no-store"] and c.baslik(b, "X-Content-Type-Options") == ["nosniff"]
    kod, css, b = c.git("GET", "/panel/stil.css")
    assert kod == 200 and c.baslik(b, "Content-Type")[0].startswith("text/css") and b"body{" in css
    assert c.git("GET", "/panel/yok")[0] == 302 and c.git("GET", "/webhook")[0] == 404 and c.git("GET", "/panel")[0] == 302   # girişsiz: önce giriş


def test_girissiz_sayfalar_girise_yonlendirir(pn):
    c = Istemci(pn)
    for metod, yol in (("GET", "/panel/"), ("GET", "/panel/bayiler"), ("GET", f"/panel/konusma/{NUMARA_A}"), ("GET", "/panel/dosya/1"),
                       ("POST", "/panel/bayi/yeni"), ("POST", "/panel/cikis")):
        kod, _, b = c.git(metod, yol, {} if metod == "POST" else None)
        assert (kod, c.baslik(b, "Location")) == (302, ["/panel/giris"]), (metod, yol)


def test_yanlis_parola_kaydedilir_dogru_parola_oturum_acar(pn, depo):
    c = Istemci(pn)
    kod, h, _ = c.giris("yanlis-" + "y" * 10)
    assert kod == 401 and "Parola yanlış".encode() in h
    assert [r["sonuc"] for r in sorgu(depo, "SELECT sonuc FROM panel_girisler ORDER BY id")] == ["basarisiz"]
    assert "pm_oturum" not in c.cerez and "pm_on" in c.cerez
    kod, _, b = c.giris(DOGRU)
    assert kod == 302 and c.baslik(b, "Location") == ["/panel/"]
    cerezler = c.baslik(b, "Set-Cookie")
    assert any(x.startswith("pm_oturum=") and "Max-Age=43200" in x and "HttpOnly" in x and "Secure" in x and "SameSite=Strict" in x for x in cerezler)
    assert "pm_on" not in c.cerez and "pm_oturum" in c.cerez
    assert [r["sonuc"] for r in sorgu(depo, "SELECT sonuc FROM panel_girisler ORDER BY id")] == ["basarisiz", "basarili"]
    ip = sorgu(depo, "SELECT DISTINCT ip_ozeti FROM panel_girisler")
    assert len(ip) == 1 and ip[0]["ip_ozeti"] == hashlib.sha256(b"10.0.0.1").hexdigest()[:16]        # ham IP saklanmaz
    kod, h, _ = c.git("GET", "/panel/")
    assert kod == 200 and "Gelen kutusu".encode() in h and b"KAPALI" not in h and b"dry_run: evet" in h
    assert c.git("GET", "/panel/giris")[0] == 302                                                     # oturum varken giriş sayfası yönlendirir


def test_csrf_ya_da_on_cerez_olmadan_giris_403_ve_sayilmaz(pn, depo):
    c = Istemci(pn)
    c.git("GET", "/panel/giris")
    assert c.git("POST", "/panel/giris", {"parola": DOGRU})[0] == 403                                   # csrf yok
    assert c.git("POST", "/panel/giris", {"parola": DOGRU, "csrf": "0" * 40})[0] == 403                 # csrf yanlış
    _, h, _ = c.git("GET", "/panel/giris")
    assert c.git("POST", "/panel/giris", {"parola": DOGRU, "csrf": c.csrf(h)}, cerezsiz=True)[0] == 403  # ön çerez yok
    assert sorgu(depo, "SELECT count(*) AS n FROM panel_girisler")[0]["n"] == 0 and "pm_oturum" not in c.cerez


def test_bes_basarisiz_giris_ipyi_kilitler_baska_ip_girer(pn, depo):
    """Kilit IP özeti başına; hesap geneli kilit yok (Lokman, 9.10): başka IP'den doğru parola kilitliyken de girer."""
    c = Istemci(pn)
    for n in range(5):
        assert c.giris("yanlis-" + str(n) * 10)[0] == 401
    kod, h, b = c.giris(DOGRU)
    assert kod == 429 and c.baslik(b, "Retry-After") == ["900"] and "15 dakika".encode() in h and "pm_oturum" not in c.cerez
    baska = Istemci(pn, ip="10.0.0.2")
    assert baska.giris(DOGRU)[0] == 302 and "pm_oturum" in baska.cerez                                  # başka IP kilitli değil
    assert c.giris(DOGRU)[0] == 429                                                                     # kilitli IP hâlâ kilitli
    assert [r["sonuc"] for r in sorgu(depo, "SELECT sonuc FROM panel_girisler ORDER BY id")] == ["basarisiz"] * 5 + ["kilitli", "basarili", "kilitli"]
    with depo.baglan() as k, k.transaction():                                                           # 16 dakika geçti
        k.execute("UPDATE panel_girisler SET zaman = zaman - interval '16 minutes'")
    assert c.giris(DOGRU)[0] == 302


def test_ip_kilidi_tek_ipden_bes_deneme(pn, depo):
    c = Istemci(pn, ip="10.0.0.9")
    for n in range(5):
        c.giris("yanlis-" + str(n) * 10)
    assert c.giris(DOGRU)[0] == 429
    assert tek(depo, "SELECT count(*) AS n FROM panel_girisler WHERE ip_ozeti = %s AND sonuc = 'basarisiz'", hashlib.sha256(b"10.0.0.9").hexdigest()[:16])["n"] == 5


def test_sahte_ve_suresi_dolmus_oturum_cerezi_reddedilir(pn):
    c = Istemci(pn)
    c.giris(DOGRU)
    dogru = c.cerez["pm_oturum"]
    yuk, imza = dogru.split(".", 1)
    c.cerez["pm_oturum"] = yuk + "." + ("0" if imza[0] != "0" else "1") + imza[1:]
    kod, _, b = c.git("GET", "/panel/")
    assert kod == 302 and any(x.startswith("pm_oturum=;") for x in c.baslik(b, "Set-Cookie"))         # bozuk çerez silinir
    c.cerez["pm_oturum"] = pn.imzala({"t": "oturum", "exp": int(time.time()) - 5, "n": "a" * 32})
    assert c.git("GET", "/panel/")[0] == 302
    c.cerez["pm_oturum"] = pn.imzala({"t": "on", "exp": int(time.time()) + 600, "n": "a" * 32})        # ön çerez oturum yerine geçmez
    assert c.git("GET", "/panel/")[0] == 302
    c.cerez["pm_oturum"] = dogru
    assert c.git("GET", "/panel/")[0] == 200


def test_oturumda_csrfsiz_post_403(pn, depo):
    c = Istemci(pn)
    c.giris(DOGRU)
    kod, h, _ = c.git("POST", "/panel/bayi/yeni", {"numara": NUMARA_Y, "ad": "Deneme"})
    assert kod == 403 and b"CSRF" in h
    assert c.git("POST", "/panel/bayi/yeni", {"numara": NUMARA_Y, "ad": "Deneme", "csrf": "0" * 40})[0] == 403
    assert depo.bayi_oku(NUMARA_Y) is None
    assert c.git("POST", "/panel/", {"csrf": "x"})[0] in (403, 405)                                    # sayfalara POST yok
    assert c.git("GET", "/panel/yok")[0] == 404 and c.git("GET", "/panel/dosya/")[0] == 404


def _csrf_oturum(c: Istemci) -> str:
    _, h, _ = c.git("GET", "/panel/bayiler")
    return c.csrf(h)


def test_bayi_ekle_ve_duzenle(pn, depo):
    c = Istemci(pn)
    c.giris(DOGRU)
    csrf = _csrf_oturum(c)
    kod, _, b = c.git("POST", "/panel/bayi/yeni", {"csrf": csrf, "numara": NUMARA_Y, "ad": "Deneme Bayi Y", "hitap": "Bey", "firma": "Y Yapı",
                                                   "bolge": "Ege", "rol": "bayi", "kod": "", "aktif": "1"})
    assert (kod, c.baslik(b, "Location")) == (302, ["/panel/bayiler"])
    assert depo.gelen_bayisi(NUMARA_Y) == {"kod": "B" + NUMARA_Y[-4:], "ad": "Deneme Bayi Y", "firma": "Y Yapı", "rol": "bayi"}
    kod, h, _ = c.git("GET", "/panel/bayiler")
    assert kod == 200 and NUMARA_Y.encode() in h and b"Deneme Bayi Y" in h and b"Ege" in h
    # düzenleme: numara yoldan gelir, formdaki numara yok sayılır; aktif kapanır
    kod, h, _ = c.git("GET", f"/panel/bayi/{NUMARA_Y}")
    assert kod == 200 and b"readonly" in h and b'value="Deneme Bayi Y"' in h
    kod, _, _ = c.git("POST", f"/panel/bayi/{NUMARA_Y}", {"csrf": csrf, "numara": "900000000999", "ad": "Deneme Bayi Y2", "hitap": "", "firma": "Y Yapı",
                                                           "bolge": "Ege", "rol": "muhendis", "kod": "YY"})
    assert kod == 302
    b2 = depo.bayi_oku(NUMARA_Y)
    assert (b2["ad"], b2["rol"], b2["kod"], b2["aktif"], b2["kaynak"]) == ("Deneme Bayi Y2", "muhendis", "YY", False, "panel")
    assert depo.bayi_oku("900000000999") is None and depo.gelen_bayisi(NUMARA_Y) is None               # pasif: kanal sahiplenmez
    # hatalar: geçersiz numara, geçersiz rol, var olan numara yeni olarak
    kod, h, _ = c.git("POST", "/panel/bayi/yeni", {"csrf": csrf, "numara": "12ab", "ad": "x", "rol": "bayi"})
    assert kod == 400 and "numara geçersiz".encode() in h and b'value="12ab"' in h
    kod, h, _ = c.git("POST", "/panel/bayi/yeni", {"csrf": csrf, "numara": "900000000555", "ad": "x", "rol": "kral"})
    assert kod == 400 and "rol geçersiz".encode() in h and depo.bayi_oku("900000000555") is None
    kod, h, _ = c.git("POST", "/panel/bayi/yeni", {"csrf": csrf, "numara": NUMARA_Y, "ad": "yine", "rol": "bayi"})
    assert kod == 400 and "zaten kayıtlı".encode() in h and depo.bayi_oku(NUMARA_Y)["ad"] == "Deneme Bayi Y2"
    assert c.git("GET", "/panel/bayi/900000000111")[0] == 404 and c.git("GET", "/panel/bayi/abc")[0] == 404
    # patron: kod türetilir
    c.git("POST", "/panel/bayi/yeni", {"csrf": csrf, "numara": "900000000909", "ad": "Patron", "rol": "patron", "aktif": "1"})
    assert depo.patron_numarasi() == "900000000909" and depo.bayi_oku("900000000909")["kod"] == "PATRON"
    # HTML kaçışı
    c.git("POST", f"/panel/bayi/{NUMARA_Y}", {"csrf": csrf, "ad": "<b>x</b>", "rol": "bayi", "aktif": "1"})
    _, h, _ = c.git("GET", "/panel/bayiler")
    assert b"&lt;b&gt;x&lt;/b&gt;" in h and b"<b>x</b>" not in h


def test_gelen_kutusu_ve_konusma_sayfasi(pn, depo, hizli_motor):
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"], rol="bayi")
    assert depo.mesaj_kaydet(mesaj("P6001 aynalı", talep(ozet="P6001 aynalı", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}])))
    r = kalici.bir_is(depo, AYAR, "t")
    assert r and r["durum"] == "bitti" and r["eylem"] == "is_emri"
    g = mesaj("merhaba, plan lazım", {}, numara=NUMARA_X)
    g["bayi"] = None; g["role"] = "bayi"; g["neden"] = "kayıtsız gönderen"
    assert depo.kayitsiz_mesaj_kaydet(g, "Bu hat yalnız kayıtlı bayilere açıktır.")["yeni"]
    c = Istemci(pn)
    c.giris(DOGRU)
    kod, h, _ = c.git("GET", "/panel/")
    assert kod == 200 and NUMARA_A.encode() in h and NUMARA_X.encode() in h and "kayıtsız".encode() in h and b"sahiplenildi" in h
    assert BAYI_A["ad"].encode() in h and "P6001 aynalı".encode() in h
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_A}")
    assert kod == 200 and b'class="gelen"' in h and b'class="giden"' in h and b"document" in h and "P6001 aynalı".encode() in h
    assert b"bekliyor" in h and f'/panel/bayi/{NUMARA_A}'.encode() in h
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_X}")
    assert kod == 200 and "Kayıtsız numara".encode() in h and f"/panel/bayi/yeni?numara={NUMARA_X}".encode() in h and "merhaba, plan lazım".encode() in h
    assert b'class="giden"' in h                                                                        # sabit cevap satırı da görünür
    kod, h, _ = c.git("GET", "/panel/bayi/yeni", sorgu=f"numara={NUMARA_X}")
    assert kod == 200 and f'value="{NUMARA_X}"'.encode() in h
    assert c.git("GET", "/panel/konusma/abc")[0] == 404


def test_dosya_indirme_yalniz_gelen_medya_altindan(pn, depo, kanal_dizini, tmp_path):
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"], rol="bayi")
    g = mesaj("foto", talep(), numara=NUMARA_A, tur="image")
    assert depo.mesaj_kaydet(g)
    for medya_id in ("1001", "1002", "1003"):
        depo.gelen_dosya_ekle(g["id"], medya_id, "ölçü krokisi.jpg", "image/jpeg")
    satirlar = sorgu(depo, "SELECT id, medya_id FROM gelen_dosyalar ORDER BY medya_id")
    kimlikler = {r["medya_id"]: r["id"] for r in satirlar}
    icerik = b"\xff\xd8\xff" + b"j" * 40
    icerde = kanal_dizini / "gelen_medya" / "abc" / "olcu_krokisi.jpg"; icerde.parent.mkdir(parents=True); icerde.write_bytes(icerik)
    disarda = tmp_path / "disari.jpg"; disarda.write_bytes(b"gizli")
    depo.gelen_dosya_indirildi(kimlikler["1001"], str(icerde), "image/jpeg", len(icerik), hashlib.sha256(icerik).hexdigest())
    depo.gelen_dosya_indirildi(kimlikler["1003"], str(disarda), "image/jpeg", 5, "x")                 # kayıt bozulmuş: yol dışarıda
    c = Istemci(pn)
    c.giris(DOGRU)
    kod, govde, b = c.git("GET", f"/panel/dosya/{kimlikler['1001']}")
    assert kod == 200 and govde == icerik and c.baslik(b, "Content-Type") == ["image/jpeg"]
    assert c.baslik(b, "Content-Disposition") == ['attachment; filename="l_krokisi.jpg"'] and c.baslik(b, "X-Content-Type-Options") == ["nosniff"]
    assert c.git("GET", f"/panel/dosya/{kimlikler['1002']}")[0] == 404                                 # indirilmemiş
    assert c.git("GET", f"/panel/dosya/{kimlikler['1003']}")[0] == 404                                 # veri dizini dışı
    assert c.git("GET", "/panel/dosya/999999")[0] == 404 and c.git("GET", "/panel/dosya/x")[0] == 404
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_A}")
    assert kod == 200 and f"/panel/dosya/{kimlikler['1001']}".encode() in h and b"indirilmedi" in h and "ölçü krokisi.jpg".encode() in h


def test_cikis_cerezi_siler(pn):
    c = Istemci(pn)
    c.giris(DOGRU)
    csrf = _csrf_oturum(c)
    assert c.git("POST", "/panel/cikis", {})[0] == 403
    kod, _, b = c.git("POST", "/panel/cikis", {"csrf": csrf})
    assert kod == 302 and c.baslik(b, "Location") == ["/panel/giris"] and "pm_oturum" not in c.cerez
    assert c.git("GET", "/panel/")[0] == 302


def test_parola_ozeti_birimi():
    o = PN.parola_ozeti(DOGRU)
    assert o.startswith("scrypt$16384$8$1$") and PN.parola_dogru(DOGRU, o) and not PN.parola_dogru(DOGRU + "x", o)
    assert PN.parola_ozeti(DOGRU) != o                                                                   # tuz rastgele
    assert not PN.parola_dogru(DOGRU, "") and not PN.parola_dogru(DOGRU, "md5$x") and not PN.parola_dogru("", o)
