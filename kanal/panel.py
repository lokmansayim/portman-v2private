"""İE-06 · Yönetim paneli (WSGI). nginx (443, TLS) → gunicorn → bu uygulama; yalnız /panel/ altındaki yollar (hosting'teki PHP
panelin yerine; karar 4). Sunucu tarafı HTML, JavaScript yok.

  GET/POST /panel/giris               tek yönetici; parola scrypt özeti (panel.env); ön çerez + CSRF; 5 başarısız girişte 15 dk kilit (IP özeti başına)
  POST     /panel/cikis
  GET      /panel/                    gelen kutusu: bütün konuşmalar (sahiplenilen ve kayıtsız), son mesaj, bayi kartı, kanal durumu
  GET      /panel/konusma/<numara>    gelen ve giden mesajlar, gönderim ve teslim durumu, gelen dosyalar
  GET      /panel/dosya/<id>          indirilmiş gelen dosya (yalnız data/gelen_medya altındaki yol)
  GET      /panel/bayiler             bayi kimlik kartları
  GET/POST /panel/bayi/yeni           yeni kart (numara, kod, ad, hitap, firma, bolge, rol, aktif)
  GET/POST /panel/bayi/<numara>       düzenleme (numara değişmez; aktif kapatılır)
  GET      /panel/stil.css

Güvenlik: yalnız HTTPS (nginx); imzalı oturum çerezi (HMAC-SHA256, 12 saat; HttpOnly, Secure, SameSite=Strict); her POST'ta CSRF
belirteci; CSP default-src 'self'; kilit IP özeti başına (sha256 kısaltması, ham IP saklanmaz); hesap geneli kilit yok (Lokman, 9.10;
nginx limit_req, fail2ban ve en az 12 karakterlik parola kalır). Sır tutmaz: PANEL_SIR
(çerez imza anahtarı) ve PANEL_PAROLA (scrypt özeti) /etc/portman/panel.env'den (systemd EnvironmentFile) gelir; ikisi yoksa panel
503 verir ve giriş kabul etmez. Günlüğe parola, maskesiz numara ve mesaj metni yazılmaz.
Komut satırı: gunicorn --chdir /opt/portman/guncel/kanal --bind 127.0.0.1:8082 panel:uygulama
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sys
import time
import traceback
import urllib.parse
from pathlib import Path

KOD = Path(__file__).resolve().parent
for _yol in (KOD.parent, KOD):
    if str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))

import ayarlar as AY                                  # noqa: E402
from depo import Depo, maske                          # noqa: E402

SURUM = "kanal-v2.0"
OTURUM_SN = 12 * 3600               # oturum çerezi
ON_SN = 15 * 60                     # giriş sayfasının ön çerezi (CSRF için)
KILIT_DENEME = 5
KILIT_DK = 15
GOVDE_EN_COK = 64 * 1024
DOSYA_EN_COK = 10 * 1024 * 1024    # İE-07: panelden gönderilen PDF (nginx /panel/ client_max_body_size 12m; Lokman 11.10 karar 5)
PENCERE_SN = 86400                 # Meta 24 saat serbest cevap penceresi (kanal/gonderici.py ile aynı)
SCRYPT_N, SCRYPT_R, SCRYPT_P = 16384, 8, 1
ROLLER = ("bayi", "patron", "muhendis", "test")    # test: kuru koşunun sahte kartı (İE-07; vps/kuru_kosu.sh), gerçek numara değil
_NUMARA = re.compile(r"[1-9][0-9]{7,14}")
_KONTROL_FIYAT = re.compile(r"/panel/kontrol/([0-9]{1,12})/fiyat")      # İE-08 8b
KONUSMA_ISLEMLERI = ("gonder", "sablon", "karsilama", "bilgi")
_DOSYA_ADI = re.compile(r"[^A-Za-z0-9._-]+")
e = html.escape


def log(*p) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "panel", *p, flush=True)


# ───────────────────────── parola özeti (vps/panel_parola.py de kullanır) ─────────────────────────
def parola_ozeti(parola: str) -> str:
    tuz = secrets.token_bytes(16)
    h = hashlib.scrypt(str(parola).encode("utf-8"), salt=tuz, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${tuz.hex()}${h.hex()}"


def parola_dogru(parola: str, ozet: str) -> bool:
    """Sabit zamanlı karşılaştırma; biçimi bozuk özet her parolayı reddeder."""
    try:
        ad, n, r, p, tuz, h = str(ozet or "").split("$")
        if ad != "scrypt":
            return False
        beklenen = bytes.fromhex(h)
        y = hashlib.scrypt(str(parola or "").encode("utf-8"), salt=bytes.fromhex(tuz), n=int(n), r=int(r), p=int(p), dklen=len(beklenen))
        return hmac.compare_digest(y, beklenen)
    except (ValueError, TypeError):
        return False


# ───────────────────────── bağımlılıklar ve imzalı çerez ─────────────────────────
class Panel:
    """Uygulamanın bağımlılıkları; testte sahte depo, veri dizini, sır ve parola özeti verilir."""

    def __init__(self, depo: Depo | None = None, veri: Path | str | None = None, sir: str | None = None, parola: str | None = None, ayar_oku=None):
        self.veri = Path(veri or os.environ.get("PORTMAN_KANAL_DIR") or "/opt/portman/data")
        self.depo = depo or Depo()
        self.sir = str(sir if sir is not None else os.environ.get("PANEL_SIR") or "").encode("utf-8")
        self.parola = str(parola if parola is not None else os.environ.get("PANEL_PAROLA") or "")
        self._ayar_oku = ayar_oku or (lambda: AY.oku(self.veri))

    def hazir(self) -> bool:
        return len(self.sir) >= 32 and self.parola.startswith("scrypt$")

    def ayar(self) -> dict:
        return self._ayar_oku()

    def imzala(self, veri: dict) -> str:
        yuk = base64.urlsafe_b64encode(json.dumps(veri, separators=(",", ":")).encode("utf-8")).decode("ascii").rstrip("=")
        return yuk + "." + hmac.new(self.sir, yuk.encode("ascii"), hashlib.sha256).hexdigest()

    def coz(self, belirtec, tur: str) -> dict | None:
        """İmzası doğru, süresi dolmamış ve türü uyan çerez yükü; değilse None."""
        try:
            yuk, imza = str(belirtec or "").split(".", 1)
            if not hmac.compare_digest(hmac.new(self.sir, yuk.encode("ascii"), hashlib.sha256).hexdigest().encode("ascii"), imza.encode("utf-8")):
                return None
            v = json.loads(base64.urlsafe_b64decode(yuk + "=" * (-len(yuk) % 4)).decode("utf-8"))
        except (ValueError, TypeError, UnicodeError):
            return None
        if not isinstance(v, dict) or v.get("t") != tur or not isinstance(v.get("n"), str) or not v["n"]:
            return None
        if not isinstance(v.get("exp"), (int, float)) or v["exp"] < time.time():
            return None
        return v

    def belirtec(self, tur: str, sn: int) -> tuple[str, str]:
        n = secrets.token_hex(16)
        return n, self.imzala({"t": tur, "exp": int(time.time()) + sn, "n": n})

    def csrf(self, nonce: str) -> str:
        return hmac.new(self.sir, ("csrf:" + nonce).encode("utf-8"), hashlib.sha256).hexdigest()[:40]


class Buyuk(Exception):
    pass


class Istek:
    def __init__(self, environ: dict):
        self.environ = environ
        self.metod = environ.get("REQUEST_METHOD") or "GET"
        self.yol = environ.get("PATH_INFO") or "/"
        self.sorgu = {a: v[0] for a, v in urllib.parse.parse_qs(environ.get("QUERY_STRING") or "", keep_blank_values=True).items()}
        self.cerez: dict[str, str] = {}
        for parca in (environ.get("HTTP_COOKIE") or "").split(";"):
            if "=" in parca:
                a, v = parca.strip().split("=", 1)
                self.cerez[a.strip()] = v.strip()
        ip = (environ.get("HTTP_X_FORWARDED_FOR") or environ.get("REMOTE_ADDR") or "?").split(",")[0].strip()
        self.ip_ozeti = hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]        # ham IP saklanmaz
        self._form: dict | None = None
        self.dosyalar: dict[str, tuple[str, bytes]] = {}                          # İE-07: çok parçalı gövdedeki dosyalar (ad, içerik)

    def form(self) -> dict:
        if self._form is None:
            try:
                n = int(self.environ.get("CONTENT_LENGTH") or 0)
            except ValueError:
                n = 0
            ctype = str(self.environ.get("CONTENT_TYPE") or "")
            coklu = ctype.lower().startswith("multipart/form-data")
            if n > (DOSYA_EN_COK + GOVDE_EN_COK if coklu else GOVDE_EN_COK):
                raise Buyuk()
            govde = self.environ["wsgi.input"].read(n) if n > 0 else b""
            if coklu:
                self._form, self.dosyalar = _coklu_parca(ctype, govde)
            else:
                self._form = {a: v[0] for a, v in urllib.parse.parse_qs(govde.decode("utf-8", "replace"), keep_blank_values=True).items()}
        return self._form


def _coklu_parca(ctype: str, govde: bytes) -> tuple[dict, dict]:
    """multipart/form-data gövdesi (stdlib email; cgi modülü 3.13'te yok): alanlar → {ad: değer}, dosyalar → {ad: (dosya adı, içerik)}."""
    import email.parser
    import email.policy
    msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(b"Content-Type: " + ctype.encode("latin-1", "replace") + b"\r\nMIME-Version: 1.0\r\n\r\n" + govde)
    alanlar: dict = {}; dosyalar: dict = {}
    if not msg.is_multipart():
        return alanlar, dosyalar
    for part in msg.iter_parts():
        ad = part.get_param("name", header="content-disposition")
        if not ad:
            continue
        icerik = part.get_payload(decode=True) or b""
        dosya_adi = part.get_filename()
        if dosya_adi is not None:
            if icerik:
                dosyalar[str(ad)] = (str(dosya_adi), icerik)
        else:
            alanlar[str(ad)] = icerik.decode("utf-8", "replace")
    return alanlar, dosyalar


# ───────────────────────── HTML ─────────────────────────
STIL = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f0;color:#1a1a1a}
header{background:#1f3a5f;color:#fff;padding:.6rem 1rem;display:flex;gap:1rem;align-items:center}
header a{color:#fff;text-decoration:none;font-weight:600}header form{margin-left:auto}
main{max-width:1100px;margin:1rem auto;padding:0 1rem}h1{font-size:1.3rem}
table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid #ddd;padding:.4rem .5rem;text-align:left;vertical-align:top;font-size:.92rem}
th{background:#e9eef5}tr.pasif td{color:#888}.durum{background:#fff;border:1px solid #ddd;padding:.5rem;font-size:.9rem}
.hata{background:#fde8e8;border:1px solid #d33;padding:.5rem;margin:.5rem 0}.bilgi{background:#e8f4e8;border:1px solid #393;padding:.5rem;margin:.5rem 0}
.mesajlar{list-style:none;padding:0}.mesajlar li{margin:.4rem 0;padding:.5rem .7rem;border-radius:.5rem;max-width:75%;white-space:pre-wrap;word-break:break-word}
.mesajlar li.gelen{background:#fff;border:1px solid #ccc}.mesajlar li.giden{background:#d8ecff;border:1px solid #9cc;margin-left:auto}
.mesajlar .ust{font-size:.78rem;color:#555;margin-bottom:.2rem}form.kart label{display:block;margin:.5rem 0}form.kart input[type=text],form.kart select{width:100%;max-width:28rem;padding:.3rem}
button{padding:.35rem .8rem;cursor:pointer}form.giris{max-width:22rem;background:#fff;padding:1rem;border:1px solid #ddd}form.giris input{width:100%;padding:.4rem;margin:.3rem 0 .8rem}
footer{color:#777;font-size:.8rem;text-align:center;padding:1rem}"""

GUVENLIK_BASLIKLARI = [("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"),
                       ("X-Frame-Options", "DENY"), ("Referrer-Policy", "no-referrer"), ("X-Content-Type-Options", "nosniff")]


def zaman(t) -> str:
    try:
        return time.strftime("%d.%m.%Y %H:%M", time.localtime(float(t))) if t else "-"
    except (TypeError, ValueError, OverflowError):
        return "-"


def sayfa(baslik: str, govde: str, p: Panel | None = None, oturum: dict | None = None) -> str:
    cikis = ""
    if p is not None and oturum is not None:
        cikis = f'<form method="post" action="/panel/cikis"><input type="hidden" name="csrf" value="{p.csrf(oturum["n"])}"><button>Çıkış</button></form>'
    menu = '<a href="/panel/">Gelen kutusu</a> <a href="/panel/bayiler">Bayiler</a>' if oturum is not None else ""
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{e(baslik)} · Portman</title><link rel="stylesheet" href="/panel/stil.css"></head><body><header>{menu}{cikis}</header>'
            f'<main><h1>{e(baslik)}</h1>{govde}</main><footer>Portman paneli · {e(SURUM)}</footer></body></html>')


def giris_sayfasi(p: Panel, csrf: str, hata: str | None = None, bilgi: str | None = None) -> str:
    govde = (f'<p class="hata">{e(hata)}</p>' if hata else "") + (f'<p class="bilgi">{e(bilgi)}</p>' if bilgi else "")
    govde += (f'<form class="giris" method="post" action="/panel/giris"><input type="hidden" name="csrf" value="{csrf}">'
              f'<label for="parola">Yönetici parolası</label><input id="parola" name="parola" type="password" autocomplete="current-password" required>'
              f'<button>Giriş</button></form>')
    return sayfa("Giriş", govde, p)


def gelen_kutusu(p: Panel, oturum: dict) -> str:
    ayar = p.ayar()
    try:
        say = dict(p.depo.sayimlar())
    except Exception:
        say = {}
    durum = (f'<p class="durum">kanal: <b>{"açık" if ayar.get("enabled") is True else "KAPALI"}</b> · dry_run: {"evet" if ayar.get("dry_run") is True else "hayır"}'
             f' · mod: {e(str(ayar.get("mode") or "-"))} · açık iş: {say.get("acik_is", "-")} · bekleyen giden: {say.get("bekleyen_giden", "-")}'
             f' · son 24 saat gelen: {say.get("gelen_24s", "-")} · aktif bayi: {say.get("aktif_bayi", "-")}</p>')
    satirlar = []
    for k in p.depo.konusma_listesi():
        kim = f'{e(k["ad"] or "")} ({e(k["kod"] or "")}, {e(k["rol"] or "")})' if k.get("kod") or k.get("ad") else "<i>kayıtsız</i>"
        if k.get("kod") and not k.get("aktif"):
            kim += " <i>(pasif)</i>"
        son = e((k.get("son_metin") or "")[:90]) or f'<i>[{e(k.get("son_tur") or "-")}]</i>'
        sahip = "sahiplenildi" if k.get("sahiplenildi") else "kayıtsız / alınmadı"
        satirlar.append(f'<tr><td>{zaman(k["son"])}</td><td><a href="/panel/konusma/{e(k["gonderen"])}">{e(k["gonderen"])}</a></td>'
                        f'<td>{kim}</td><td>{son}</td><td>{k["n"]}</td><td>{sahip}</td></tr>')
    tablo = ('<table><tr><th>Son mesaj</th><th>Numara</th><th>Bayi</th><th>Metin</th><th>Mesaj</th><th>Son durum</th></tr>' + "".join(satirlar) + "</table>"
             if satirlar else "<p>Henüz mesaj yok.</p>")
    return sayfa("Gelen kutusu", durum + kontrol_tablosu(p, oturum) + tablo, p, oturum)


_HATA_METNI = (("reply_window_closed", "pencere kapalı (24 saat)"), ("sablon_gereksiz", "şablon gereksiz (pencere açıktı, metin gitti)"),
               ("sablon_yok", "şablon tanımsız (ayar.sh ile Meta şablon adı girilmeli)"), ("dry_run", "dry_run: gönderilmedi"),
               ("recipient_unknown", "alıcı bilinmiyor"), ("template_invalid", "şablon değişkeni geçersiz"))


def _hata_kisa(hata: str | None) -> str:
    h = str(hata or "")
    for anahtar, metin in _HATA_METNI:
        if anahtar in h:
            return metin
    return h[:80]


def cevap_formu(p: Panel, oturum: dict, numara: str, b: dict | None, hata: str | None = None, bilgi: str | None = None) -> str:
    """İE-07 P3/P5: metin + PDF formu, pencere durumu, 'dosyalar hazır' şablon düğmesi."""
    csrf = p.csrf(oturum["n"])
    son = p.depo.son_gelen_mesaj(numara)
    govde = (f'<p class="hata">{e(hata)}</p>' if hata else "") + (f'<p class="bilgi">{e(bilgi)}</p>' if bilgi else "")
    if son is None:
        return (govde + '<p class="durum">Bu numaradan hiç mesaj gelmedi; metin ve PDF gönderilemez. Aktif bayi kartına karşılama ya da '
                '"bilgi hazır" şablonu gönderilebilir (İE-08 8b).</p>' + ilk_temas_formu(p, oturum, numara, b, yazdi=False))
    kalan = PENCERE_SN - (time.time() - float(son.get("zaman") or 0))        # gönderici de bayinin son mesajından ölçer
    if kalan > 0:
        pencere = f'<p class="durum">24 saat penceresi <b>açık</b>; kalan yaklaşık {int(kalan // 3600)} saat {int(kalan % 3600 // 60)} dk. Metin ve PDF gönderilebilir.</p>'
    else:
        pencere = ('<p class="hata">24 saat penceresi <b>kapalı</b>: metin ve PDF gönderilmez (gönderici "pencere kapalı" der). '
                   'Bayiye "dosyalar hazır" şablonu gönderin; cevap verirse pencere açılır.</p>')
    form = (f'<form class="kart" method="post" action="/panel/konusma/{e(numara)}/gonder" enctype="multipart/form-data">'
            f'<input type="hidden" name="csrf" value="{csrf}">'
            f'<label>Metin<textarea name="metin" rows="3" maxlength="4000"></textarea></label>'
            f'<label>PDF (en çok 10 MB)<input type="file" name="pdf" accept="application/pdf"></label>'
            f'<label>PDF açıklaması<input type="text" name="aciklama" maxlength="1000"></label>'
            f'<button>Gönder</button></form>')
    neden = sablon_engeli(p, numara, b)
    if neden is None:
        no = p.depo.son_is_emri_no(numara)
        sablon = (f'<form class="kart" method="post" action="/panel/konusma/{e(numara)}/sablon"><input type="hidden" name="csrf" value="{csrf}">'
                  f'<button>"Dosyalar hazır" şablonu gönder ({e(no)})</button> <span class="durum">Meta onaylı şablon; pencere kapalıyken de gider (ücretli). '
                  f'Bayi "Dosyaları gönder"e basınca pencere açılır.</span></form>')
    else:
        sablon = f'<p class="durum">"Dosyalar hazır" şablonu: {e(neden)}; düğme kapalı.</p>'
    return govde + pencere + form + sablon + ilk_temas_formu(p, oturum, numara, b, yazdi=True)


def ilk_temas_engeli(b: dict | None) -> str | None:
    """İE-08 8b M4: karşılama ve 'bilgi hazır' şablonu kime gidebilir: kayıtlı, aktif, gerçek bayi kartı (test, Patron, mühendis değil)."""
    if not b:
        return "kayıtsız numara"
    if b.get("rol") != "bayi":
        return f"{b.get('rol')} kartı"
    if not b.get("aktif"):
        return "bayi pasif"
    return None


def ilk_temas_formu(p: Panel, oturum: dict, numara: str, b: dict | None, yazdi: bool) -> str:
    """Karşılama (yalnız hiç yazmamış karta) ve 'bilgi hazır' (her aktif bayi kartına) düğmeleri; Meta şablonu, pencere kapalıyken de gider (ücretli)."""
    neden = ilk_temas_engeli(b)
    if neden is not None:
        return f'<p class="durum">Karşılama / bilgi hazır şablonu: {e(neden)}; düğme kapalı.</p>'
    csrf = p.csrf(oturum["n"]); out = ""
    if not yazdi:
        out += (f'<form class="kart" method="post" action="/panel/konusma/{e(numara)}/karsilama"><input type="hidden" name="csrf" value="{csrf}">'
                f'<button>Karşılama şablonu gönder</button> <span class="durum">"Portman bayi kaydınız onaylandı…" + "Nasıl çalışır?" düğmesi '
                f'(PDF). Ücretli.</span></form>')
    out += (f'<form class="kart" method="post" action="/panel/konusma/{e(numara)}/bilgi"><input type="hidden" name="csrf" value="{csrf}">'
            f'<button>"Bilgi hazır" şablonu gönder</button> <span class="durum">Planı olmasa da gider. Bayi "Bilgiyi gönder"e basınca pencere açılır, '
            f'size bildirim gelir; sonra buradan yazarsınız. Ücretli.</span></form>')
    return out


def kontrol_tablosu(p: Panel, oturum: dict, bayi: str | None = None) -> str:
    """İE-08 8b M2/M3: mühendis teknik kontrolleri (durum, not, liste sürümleri, Patron hatırlatmaları) ve 'Fiyat verildi'."""
    try:
        kontroller = p.depo.kontroller(bayi=bayi, limit=20)
    except Exception:
        return ""
    if not kontroller:
        return ""
    csrf = p.csrf(oturum["n"]); satirlar = []
    durum_adi = {"bekliyor": "mühendiste", "patrona_gonderildi": "mühendis onayladı", "duzeltme": "düzeltme istendi", "kart_yok": "mühendis kartı yok"}
    for k in kontroller:
        surumler = [int(x.get("surum") or 0) for x in (k.get("listeler") or []) if x.get("kaynak") == "muhendis"]
        fiyat = ""
        if k["patron_durum"] == "bekliyor":
            fiyat = (f'<form method="post" action="/panel/kontrol/{k["id"]}/fiyat"><input type="hidden" name="csrf" value="{csrf}">'
                     f'<button>Fiyat verildi</button></form>')
        patron = {"yok": "-", "bekliyor": f'fiyat bekleniyor (hatırlatma {k["patron_hatirlatma_sayisi"]}/3)', "fiyat_verildi": "fiyat verildi",
                  "durdu": "durdu (panelden gönderim)"}.get(k["patron_durum"], k["patron_durum"])
        satirlar.append(f'<tr><td>{zaman(k["t_olusturuldu"])}</td><td><a href="/panel/konusma/{e(k["bayi"])}">{e(k["is_emri_no"])} r{int(k["rev"]):02d}</a></td>'
                        f'<td>{e(k["bayi_kod"] or "")}</td><td>{e(durum_adi.get(k["durum"], k["durum"]))}</td><td>{k["hatirlatma_sayisi"]}</td>'
                        f'<td>{e(", ".join(f"s{n}" for n in surumler) or "-")}</td><td>{e(k.get("not_") or "")}</td><td>{e(patron)}</td><td>{fiyat}</td></tr>')
    return ('<h2>Mühendis kontrolleri</h2><table><tr><th>Onay</th><th>İş</th><th>Bayi</th><th>Durum</th><th>Hatırlatma</th><th>Mühendisin listesi</th>'
            '<th>Not</th><th>Patron</th><th></th></tr>' + "".join(satirlar) + "</table>")


def sablon_engeli(p: Panel, numara: str, b: dict | None) -> str | None:
    """'Dosyalar hazır' şablonu kime gidebilir: kayıtlı ve aktif bayi (test kartı, Patron değil) ve doğrulanmış bir revizyonu var. Engel metni ya da None."""
    if not b:
        return "kayıtsız numara"
    if b.get("rol") == "test":
        return "test kartı (gerçek numara değil)"
    if b.get("rol") == "patron":
        return "Patron kartı"
    if not b.get("aktif"):
        return "bayi pasif"
    if not p.depo.son_is_emri_no(numara):
        return "bu bayinin doğrulanmış İş Emri kaydı yok (proje yok)"
    return None


def konusma_sayfasi(p: Panel, oturum: dict, numara: str, hata: str | None = None, bilgi: str | None = None) -> str:
    b = p.depo.bayi_oku(numara)
    if b:
        kart = (f'<p class="durum">Bayi: <b>{e(b["ad"] or "-")}</b> · kod {e(b["kod"] or "-")} · {e(b["rol"])} · {e(b["firma"] or "-")}'
                f' · {"aktif" if b["aktif"] else "PASİF"} · <a href="/panel/bayi/{e(numara)}">düzenle</a></p>')
    else:
        kart = f'<p class="durum">Kayıtsız numara · <a href="/panel/bayi/yeni?numara={e(numara)}">bayi olarak ekle</a></p>'
    ogeler = []
    for m in p.depo.konusma_mesajlari(numara):
        giden = m["yon"] == "giden"
        ust = f'{zaman(m["zaman"])} · {e(m["kind"] or "")}'
        if giden:
            ust += f' · {e(m["durum"] or "")}' + (f' · teslim: {e(m["teslim"])}' if m.get("teslim") else "")
            if m.get("kaynak") == "panel":
                ust += " · <b>panel</b>"
            if m.get("hata") and m.get("durum") in ("gonderilmedi", "belirsiz"):
                ust += f' · {e(_hata_kisa(m["hata"]))}'
        elif not m.get("sahiplenildi"):
            ust += " · alınmadı (kayıtsız ya da eski)"
        if m.get("dosya_adi"):
            ust += f' · {e(m["dosya_adi"])}'
        if m.get("reply_id"):
            ust += f' · cevap: {e(m["reply_id"])}'
        ogeler.append(f'<li class="{"giden" if giden else "gelen"}"><div class="ust">{ust}</div>{e(m["govde"] or "")}</li>')
    liste = '<ul class="mesajlar">' + "".join(ogeler) + "</ul>" if ogeler else "<p>Mesaj yok.</p>"
    liste += "<h2>Cevap yaz</h2>" + cevap_formu(p, oturum, numara, b, hata, bilgi)
    dosyalar = []
    for d in p.depo.gelen_dosyalari(numara):
        if d["indirildi"]:
            bag = f'<a href="/panel/dosya/{d["id"]}">indir</a>'
        else:
            bag = f'indirilmedi{(" (" + e(d["hata"]) + ")") if d.get("hata") else ""}'
        dosyalar.append(f'<tr><td>{zaman(d["zaman"])}</td><td>{e(d["dosya_adi"] or "-")}</td><td>{e(d["mime"] or "-")}</td><td>{d["boyut"] or "-"}</td><td>{bag}</td></tr>')
    dosya_tablo = ("<h2>Gelen dosyalar</h2><table><tr><th>Zaman</th><th>Ad</th><th>Tür</th><th>Bayt</th><th></th></tr>" + "".join(dosyalar) + "</table>") if dosyalar else ""
    return sayfa(f"Konuşma · {numara}", kart + kontrol_tablosu(p, oturum, bayi=numara) + liste + dosya_tablo, p, oturum)


def bayiler_sayfasi(p: Panel, oturum: dict) -> str:
    satirlar = []
    for b in p.depo.bayi_listesi():
        satirlar.append(f'<tr class="{"aktif" if b["aktif"] else "pasif"}"><td><a href="/panel/bayi/{e(b["numara"])}">{e(b["numara"])}</a></td><td>{e(b["kod"] or "")}</td>'
                        f'<td>{e(b["ad"] or "")}</td><td>{e(b["hitap"] or "")}</td><td>{e(b["firma"] or "")}</td><td>{e(b["bolge"] or "")}</td>'
                        f'<td>{e(b["rol"])}</td><td>{"evet" if b["aktif"] else "hayır"}</td><td>{zaman(b["guncellendi"].timestamp() if hasattr(b["guncellendi"], "timestamp") else None)}</td>'
                        f'<td><a href="/panel/konusma/{e(b["numara"])}">konuşma</a></td></tr>')     # 8b M4: hiç yazmamış karta karşılama buradan
    govde = '<p><a href="/panel/bayi/yeni">+ Yeni bayi</a></p>'
    govde += ('<table><tr><th>Numara</th><th>Kod</th><th>Ad</th><th>Hitap</th><th>Firma</th><th>Bölge</th><th>Rol</th><th>Aktif</th><th>Güncellendi</th><th></th></tr>'
              + "".join(satirlar) + "</table>") if satirlar else "<p>Kayıtlı bayi yok.</p>"
    return sayfa("Bayiler", govde, p, oturum)


VARSAYILAN_SECENEKLERI = (("yapi_turu", "Yapı tipi", (("prefabrik", "Prefabrik"), ("celik", "Çelik"))),
                          ("kat_sayisi", "Kat", (("1", "Tek kat"), ("2", "İki kat"))),
                          ("cati", "Çatı", (("besik", "Beşik"), ("tek_egimli", "Tek eğimli"), ("kirma", "Kırma"), ("teras", "Teras"))),
                          ("veranda", "Veranda", (("on", "Önde"), ("yan", "Yanda"), ("arka", "Arkada"), ("kose", "Köşede"))))


def varsayilan_alanlari(v: dict) -> str:
    """İE-20 PR-2 (satır 61): talep formunun bu bayide seçili geleceği değerler; boş = sabit varsayılan (prefabrik, tek kat, beşik, önde)."""
    out = "<fieldset><legend>Talep formu varsayılanları</legend>"
    for ad, etiket, secenekler in VARSAYILAN_SECENEKLERI:
        sec = '<option value="">(yok)</option>' + "".join(f'<option value="{a}"{" selected" if str(v.get(ad) or "") == a else ""}>{e(b)}</option>'
                                                         for a, b in secenekler)
        out += f'<label>{etiket}<select name="v_{ad}">{sec}</select></label>'
    return out + "</fieldset>"


def bayi_formu(p: Panel, oturum: dict, d: dict, yeni: bool, hata: str | None = None) -> str:
    def alan(ad, etiket, deger, salt_okunur=False):
        ek = " readonly" if salt_okunur else ""
        return f'<label>{etiket}<input type="text" name="{ad}" value="{e(str(deger or ""))}" maxlength="120"{ek}></label>'
    secenekler = "".join(f'<option value="{r}"{" selected" if d.get("rol") == r else ""}>{r}</option>' for r in ROLLER)
    govde = f'<p class="hata">{e(hata)}</p>' if hata else ""
    govde += (f'<form class="kart" method="post"><input type="hidden" name="csrf" value="{p.csrf(oturum["n"])}">'
              + alan("numara", "Numara (ülke koduyla, yalnız rakam; sonradan değişmez)", d.get("numara"), salt_okunur=not yeni)
              + alan("ad", "Ad", d.get("ad")) + alan("hitap", "Hitap", d.get("hitap")) + alan("firma", "Firma", d.get("firma")) + alan("bolge", "Bölge", d.get("bolge"))
              + f'<label>Rol<select name="rol">{secenekler}</select></label>'
              + alan("kod", "Kod (boşsa türetilir: PATRON ya da B + son 4 hane)", d.get("kod"))
              + f'<label><input type="checkbox" name="aktif" value="1"{" checked" if d.get("aktif", True) else ""}> Aktif</label>'
              + varsayilan_alanlari(d.get("varsayilanlar") or {})
              + '<button>Kaydet</button> <a href="/panel/bayiler">vazgeç</a></form>')
    return sayfa("Yeni bayi" if yeni else f"Bayi · {d.get('numara')}", govde, p, oturum)


# ───────────────────────── istek işleme ─────────────────────────
def _cerez(ad: str, deger: str, sn: int) -> tuple[str, str]:
    return ("Set-Cookie", f"{ad}={deger}; Path=/panel; Max-Age={sn}; HttpOnly; Secure; SameSite=Strict")


def _cerez_sil(ad: str) -> tuple[str, str]:
    return ("Set-Cookie", f"{ad}=; Path=/panel; Max-Age=0; HttpOnly; Secure; SameSite=Strict")


def _yonlendir(yol: str, ek: list | None = None) -> tuple:
    return 302, b"", "text/plain; charset=utf-8", [("Location", yol), *(ek or [])]


def _html(kod: int, metin: str, ek: list | None = None) -> tuple:
    return kod, metin.encode("utf-8"), "text/html; charset=utf-8", list(ek or [])


def giris(p: Panel, i: Istek) -> tuple:
    if p.coz(i.cerez.get("pm_oturum"), "oturum") is not None:
        return _yonlendir("/panel/")
    on = p.coz(i.cerez.get("pm_on"), "on")
    ek: list = []
    hata = None
    kod = 200
    if i.metod == "POST":
        try:
            f = i.form()
        except Buyuk:
            return 413, b"govde", "text/plain; charset=utf-8", []
        if on is None or not hmac.compare_digest(str(f.get("csrf", "")).encode("utf-8"), p.csrf(on["n"]).encode("utf-8")):
            on = None
            kod, hata = 403, "Giriş sayfasının süresi doldu ya da doğrulama uyuşmadı; yeniden deneyin."
        elif p.depo.panel_basarisiz_sayisi(KILIT_DK, i.ip_ozeti) >= KILIT_DENEME:    # yalnız IP özeti başına (hesap geneli kilit yok; Lokman 9.10)
            p.depo.panel_giris_kaydet("kilitli", i.ip_ozeti)
            log("giriş kilitli", i.ip_ozeti[:6])
            return _html(429, sayfa("Kilitli", f'<p class="hata">Çok fazla başarısız deneme. {KILIT_DK} dakika bekleyin.</p>', p),
                         [("Retry-After", str(KILIT_DK * 60))])
        elif parola_dogru(f.get("parola", ""), p.parola):
            p.depo.panel_giris_kaydet("basarili", i.ip_ozeti)
            log("giriş başarılı", i.ip_ozeti[:6])
            _, tok = p.belirtec("oturum", OTURUM_SN)
            return _yonlendir("/panel/", [_cerez("pm_oturum", tok, OTURUM_SN), _cerez_sil("pm_on")])
        else:
            p.depo.panel_giris_kaydet("basarisiz", i.ip_ozeti)
            log("giriş başarısız", i.ip_ozeti[:6])
            kod, hata = 401, "Parola yanlış."
    elif i.metod != "GET":
        return 405, b"method", "text/plain; charset=utf-8", []
    if on is None:
        n, tok = p.belirtec("on", ON_SN)
        on = {"n": n}
        ek.append(_cerez("pm_on", tok, ON_SN))
    return _html(kod, giris_sayfasi(p, p.csrf(on["n"]), hata), ek)


def dosya(p: Panel, id_: int) -> tuple:
    d = p.depo.gelen_dosya(id_)
    if not d or not d.get("yol"):
        return 404, b"yok", "text/plain; charset=utf-8", []
    kok = (p.veri / "gelen_medya").resolve()
    try:
        yol = Path(d["yol"]).resolve(strict=True)
    except OSError:
        return 404, b"yok", "text/plain; charset=utf-8", []
    if kok not in yol.parents or not yol.is_file():
        log("dosya yolu veri dizini dışında; reddedildi", id_)
        return 404, b"yok", "text/plain; charset=utf-8", []
    ad = _DOSYA_ADI.sub("_", str(d.get("dosya_adi") or yol.name)).strip("._")[:80] or "dosya"
    mime = str(d.get("mime") or "application/octet-stream").split(";")[0].strip() or "application/octet-stream"
    return 200, yol.read_bytes(), mime, [("Content-Disposition", f'attachment; filename="{ad}"')]


def bayi_kaydet(p: Panel, oturum: dict, i: Istek, numara: str | None) -> tuple:
    """numara None → yeni kart (numara formdan); değilse düzenleme (numara yoldan; formdaki yok sayılır)."""
    f = i.form()
    yeni = numara is None
    d = {"numara": (f.get("numara") or "").strip() if yeni else numara, "ad": f.get("ad", ""), "hitap": f.get("hitap", ""), "firma": f.get("firma", ""),
         "bolge": f.get("bolge", ""), "rol": f.get("rol", "bayi"), "kod": f.get("kod", ""), "aktif": f.get("aktif") == "1",
         "varsayilanlar": {a: f.get(f"v_{a}") or None for a, _e, _s in VARSAYILAN_SECENEKLERI}}
    try:
        if yeni and not _NUMARA.fullmatch(d["numara"]):
            raise ValueError("numara geçersiz: yalnız rakam, ülke koduyla 8–15 hane")
        if yeni and p.depo.bayi_oku(d["numara"]):
            raise ValueError("bu numara zaten kayıtlı; listeden açıp düzenleyin")
        varsayilan = any(f"v_{a}" in f for a, _e, _s in VARSAYILAN_SECENEKLERI)   # İE-20 PR-2: form varsayılanları (alanlar formdaysa)
        if varsayilan:
            p.depo.varsayilan_denetle(d["varsayilanlar"])                          # kart yazılmadan önce (yarım kayıt yok)
        p.depo.bayi_yaz(d["numara"], ad=d["ad"], kod=d["kod"] or None, hitap=d["hitap"], firma=d["firma"], bolge=d["bolge"], rol=d["rol"], aktif=d["aktif"], kaynak="panel")
        if varsayilan:
            p.depo.bayi_varsayilanlari_yaz(d["numara"], **d["varsayilanlar"])
    except ValueError as hata:
        return _html(400, bayi_formu(p, oturum, d, yeni, str(hata)))
    log("bayi kaydedildi", maske(d["numara"]), "yeni" if yeni else "güncelleme")
    return _yonlendir("/panel/bayiler")


def _pdf_kaydet(p: Panel, numara: str, dosya_adi: str, icerik: bytes) -> tuple[Path, str, str]:
    """Panelden yüklenen PDF: <veri>/projects/panel/<numara>/<zaman>_<ad>.pdf (gönderici dosya_denetle kökü projects/); sha256 döner."""
    if not icerik.startswith(b"%PDF-"):
        raise ValueError("dosya PDF değil (ilk baytlar %PDF- olmalı)")
    if len(icerik) > DOSYA_EN_COK:
        raise ValueError("PDF 10 MB'tan büyük")
    ad = _DOSYA_ADI.sub("_", Path(dosya_adi).name).strip("._")[:60] or "belge.pdf"
    if not ad.lower().endswith(".pdf"):
        ad += ".pdf"
    klasor = p.veri / "projects" / "panel" / numara
    klasor.mkdir(parents=True, exist_ok=True)
    yol = klasor / f"{time.strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}_{ad}"
    gecici = yol.with_name(yol.name + ".tmp"); gecici.write_bytes(icerik); os.replace(gecici, yol)
    try:
        os.chmod(yol, 0o600)
    except OSError:
        pass
    return yol, ad, hashlib.sha256(icerik).hexdigest()


def konusma_gonder(p: Panel, oturum: dict, i: Istek, numara: str) -> tuple:
    """İE-07 P3: POST /panel/konusma/<numara>/gonder — metin ve/veya PDF satırı (giden.kaynak 'panel'); gönderici kuralları aynen.
    Önce PDF doğrulanıp yazılır, sonra satırlar; bir satır yazılamazsa yazılan PDF dosyası kaldırılır (yarım gönderim olmaz)."""
    f = i.form()
    metin = str(f.get("metin") or "").strip()
    aciklama = str(f.get("aciklama") or "").strip()
    pdf = i.dosyalar.get("pdf")
    if not metin and not pdf:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata="Metin ya da PDF gerekli."))
    if p.depo.son_gelen_mesaj(numara) is None:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata="Bu numaradan hiç mesaj gelmedi; panelden gönderim yapılamaz."))
    yol = None
    try:
        if pdf:
            yol, ad, sha = _pdf_kaydet(p, numara, pdf[0], pdf[1])
    except ValueError as hata:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata=str(hata)))
    yazilan = []; pdf_yazildi = False
    try:
        if metin:
            yazilan.append(p.depo.panel_giden_ekle(numara, lambda g, n: _panel_metin(g, metin, n, numara)))
        if pdf:
            yazilan.append(p.depo.panel_giden_ekle(numara, lambda g, n: _panel_belge(g, yol, ad, aciklama, n, numara, sha)))
            pdf_yazildi = True
    except Exception as hata:
        if yol is not None and not pdf_yazildi:
            try:
                os.unlink(yol)                                        # satır yazılamadı: kendi yazdığımız dosya kalmasın
            except OSError:
                pass
        if isinstance(hata, ValueError) and str(hata) == "gelen_yok":
            return _html(400, konusma_sayfasi(p, oturum, numara, hata="Bu numaradan hiç mesaj gelmedi; panelden gönderim yapılamaz."))
        log("panel giden yazılamadı", maske(numara), type(hata).__name__)
        return _html(500, konusma_sayfasi(p, oturum, numara, hata="Satır yazılamadı; günlüğe bakın." + (" Metin satırı yazıldı." if (metin and yazilan) else "")))
    log("panel giden", maske(numara), "metin" if metin else "", "pdf" if pdf else "", *yazilan)
    _hatirlatma_durdur(p, numara)
    return _yonlendir(f"/panel/konusma/{numara}")


def _hatirlatma_durdur(p: Panel, numara: str) -> None:
    """İE-08 8b M3: Patron bayiye panelden yazınca o bayinin fiyat bekleyen kontrollerinde Patron hatırlatması durur."""
    try:
        n = p.depo.patron_hatirlatma_durdur(numara)
        if n:
            log("patron hatırlatması durdu", maske(numara), n)
    except Exception as hata:
        log("patron hatırlatması durdurulamadı", maske(numara), type(hata).__name__)


def _panel_metin(gelen: dict, metin: str, sira: int, numara: str) -> dict:
    from depo import metin_satiri
    return dict(metin_satiri(gelen, metin, sira, numara, "cevap"), kaynak="panel")


def _panel_belge(gelen: dict, yol: Path, ad: str, aciklama: str, sira: int, numara: str, sha: str) -> dict:
    from depo import metin_satiri
    r = dict(metin_satiri(gelen, aciklama[:1000], sira, numara, "belge"), kaynak="panel")
    r.update(kind="document", file=str(yol), filename=ad, mime="application/pdf", sha256=sha)
    return r


def konusma_sablon(p: Panel, oturum: dict, i: Istek, numara: str) -> tuple:
    """İE-07 P5: POST /panel/konusma/<numara>/sablon — bayiye 'dosyalarınız hazır' Meta şablonu ({{1}} hitap, {{2}} son doğrulanmış İş Emri no).
    Yalnız kayıtlı, aktif, gerçek bayiye (test kartı ve Patron değil)."""
    import sablonlar as S
    b = p.depo.bayi_oku(numara)
    neden = sablon_engeli(p, numara, b)
    if neden is not None:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata=f"Şablon gönderilemez: {neden}."))
    no = p.depo.son_is_emri_no(numara)
    try:
        kimlik = p.depo.panel_giden_ekle(numara, lambda g, n: S.bayi_dosyalar_hazir_satiri(g["id"], n, numara, b, no))
    except ValueError:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata="Bu numaradan hiç mesaj gelmedi; şablon satırı bağlanamadı."))
    log("panel şablon", maske(numara), S.BAYI_DOSYALAR_HAZIR["anahtar"], kimlik)
    _hatirlatma_durdur(p, numara)
    return _yonlendir(f"/panel/konusma/{numara}")


def konusma_ilk_temas(p: Panel, oturum: dict, numara: str, tur: str) -> tuple:
    """İE-08 8b M4: POST /panel/konusma/<numara>/karsilama (yalnız hiç yazmamış karta) ve /bilgi (her aktif bayi kartına). Kartın gelen
    mesajı varsa satır son mesajına (panel_giden_ekle), yoksa başlangıç kaydına (ilk_temas_ekle) bağlanır."""
    import sablonlar as S
    b = p.depo.bayi_oku(numara)
    neden = ilk_temas_engeli(b)
    if neden is not None:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata=f"Şablon gönderilemez: {neden}."))
    yazdi = p.depo.son_gelen_mesaj(numara) is not None
    if tur == "karsilama" and yazdi:
        return _html(400, konusma_sayfasi(p, oturum, numara, hata="Karşılama yalnız hiç yazmamış karta gider; bu bayi yazmış."))
    uret = S.bayi_karsilama_satiri if tur == "karsilama" else S.bayi_bilgi_hazir_satiri
    satir = lambda g, n: uret(g["id"], n, numara, b)                            # noqa: E731
    kimlik = p.depo.panel_giden_ekle(numara, satir) if yazdi else p.depo.ilk_temas_ekle(numara, satir)
    log("panel şablon", maske(numara), (S.BAYI_KARSILAMA if tur == "karsilama" else S.BAYI_BILGI_HAZIR)["anahtar"], kimlik)
    if tur == "bilgi":
        _hatirlatma_durdur(p, numara)
    return _yonlendir(f"/panel/konusma/{numara}")


def kontrol_fiyat(p: Panel, oturum: dict, kid: int) -> tuple:
    """İE-08 8b M3: POST /panel/kontrol/<id>/fiyat — Patron fiyatı verdi; hatırlatmalar durur."""
    p.depo.fiyat_verildi(kid)
    log("fiyat verildi", kid)
    return _yonlendir("/panel/")


def isle(p: Panel, i: Istek) -> tuple:
    """(kod, gövde, içerik türü, ek başlıklar)"""
    if i.yol == "/panel":
        return _yonlendir("/panel/")
    if not i.yol.startswith("/panel/"):
        return 404, b"yok", "text/plain; charset=utf-8", []
    if not p.hazir():
        return 503, b"panel yapilandirilmadi (PANEL_SIR, PANEL_PAROLA)", "text/plain; charset=utf-8", []
    if i.yol == "/panel/stil.css":
        return 200, STIL.encode("utf-8"), "text/css; charset=utf-8", [("Cache-Control", "max-age=3600")]
    if i.yol == "/panel/giris":
        return giris(p, i)
    oturum = p.coz(i.cerez.get("pm_oturum"), "oturum")
    if oturum is None:
        return _yonlendir("/panel/giris", [_cerez_sil("pm_oturum")] if i.cerez.get("pm_oturum") else None)
    if i.metod == "POST":
        try:
            f = i.form()
        except Buyuk:
            return 413, b"govde", "text/plain; charset=utf-8", []
        if not hmac.compare_digest(str(f.get("csrf", "")).encode("utf-8"), p.csrf(oturum["n"]).encode("utf-8")):
            return _html(403, sayfa("Reddedildi", '<p class="hata">Form doğrulaması uyuşmadı (CSRF). Sayfayı yeniden açıp tekrar deneyin.</p>', p, oturum))
    elif i.metod != "GET":
        return 405, b"method", "text/plain; charset=utf-8", []
    if i.yol == "/panel/cikis":
        if i.metod != "POST":
            return 405, b"method", "text/plain; charset=utf-8", []
        return _yonlendir("/panel/giris", [_cerez_sil("pm_oturum")])
    konusma_post = i.yol.startswith("/panel/konusma/") and i.yol.rsplit("/", 1)[-1] in KONUSMA_ISLEMLERI   # İE-07; 8b karşılama, bilgi
    kontrol_post = _KONTROL_FIYAT.fullmatch(i.yol)                                                           # İE-08 8b: Fiyat verildi
    if i.metod == "POST" and i.yol not in ("/panel/bayi/yeni",) and not i.yol.startswith("/panel/bayi/") and not konusma_post and not kontrol_post:
        return 405, b"method", "text/plain; charset=utf-8", []
    if i.yol == "/panel/":
        return _html(200, gelen_kutusu(p, oturum))
    if i.yol == "/panel/bayiler":
        return _html(200, bayiler_sayfasi(p, oturum))
    if i.yol == "/panel/bayi/yeni":
        if i.metod == "POST":
            return bayi_kaydet(p, oturum, i, None)
        return _html(200, bayi_formu(p, oturum, {"numara": i.sorgu.get("numara", ""), "aktif": True}, True))
    if i.yol.startswith("/panel/bayi/"):
        numara = i.yol[len("/panel/bayi/"):]
        if not _NUMARA.fullmatch(numara):
            return 404, b"yok", "text/plain; charset=utf-8", []
        b = p.depo.bayi_oku(numara)
        if b is None:
            return 404, b"yok", "text/plain; charset=utf-8", []
        if i.metod == "POST":
            return bayi_kaydet(p, oturum, i, numara)
        return _html(200, bayi_formu(p, oturum, {**dict(b), "varsayilanlar": p.depo.bayi_varsayilanlari(b["numara"])}, False))
    if i.yol.startswith("/panel/konusma/"):
        numara = i.yol[len("/panel/konusma/"):]
        islem = None
        if konusma_post:
            numara, islem = numara.rsplit("/", 1)
        if not _NUMARA.fullmatch(numara):
            return 404, b"yok", "text/plain; charset=utf-8", []
        if islem == "gonder":
            return konusma_gonder(p, oturum, i, numara) if i.metod == "POST" else (405, b"method", "text/plain; charset=utf-8", [])
        if islem == "sablon":
            return konusma_sablon(p, oturum, i, numara) if i.metod == "POST" else (405, b"method", "text/plain; charset=utf-8", [])
        if islem in ("karsilama", "bilgi"):
            return konusma_ilk_temas(p, oturum, numara, islem) if i.metod == "POST" else (405, b"method", "text/plain; charset=utf-8", [])
        return _html(200, konusma_sayfasi(p, oturum, numara))
    if kontrol_post:
        return kontrol_fiyat(p, oturum, int(kontrol_post.group(1))) if i.metod == "POST" else (405, b"method", "text/plain; charset=utf-8", [])
    if i.yol.startswith("/panel/dosya/"):
        kimlik = i.yol[len("/panel/dosya/"):]
        if not kimlik.isdigit() or len(kimlik) > 12:
            return 404, b"yok", "text/plain; charset=utf-8", []
        return dosya(p, int(kimlik))
    return 404, b"yok", "text/plain; charset=utf-8", []


# ───────────────────────── WSGI ─────────────────────────
_METIN = {200: "OK", 302: "Found", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
          413: "Payload Too Large", 429: "Too Many Requests", 500: "Internal Server Error", 503: "Service Unavailable"}


def uygulama_olustur(p: Panel):
    def uygulama(environ, start_response):
        try:
            kod, govde, ctype, ek = isle(p, Istek(environ))
        except Exception:
            log("istek işlenemedi:", traceback.format_exc()[-600:])
            kod, govde, ctype, ek = 500, b"hata", "text/plain; charset=utf-8", []
        basliklar = [("Content-Type", ctype), ("Content-Length", str(len(govde))), *GUVENLIK_BASLIKLARI]
        if not any(a == "Cache-Control" for a, _ in ek):
            basliklar.append(("Cache-Control", "no-store"))
        start_response(f"{kod} {_METIN.get(kod, 'Error')}", basliklar + list(ek))
        return [govde]
    return uygulama


_varsayilan = {"p": None}


def uygulama(environ, start_response):
    """gunicorn giriş noktası (ayarlar ortamdan; ilk istekte kurulur)."""
    if _varsayilan["p"] is None:
        _varsayilan["p"] = Panel()
    return uygulama_olustur(_varsayilan["p"])(environ, start_response)
