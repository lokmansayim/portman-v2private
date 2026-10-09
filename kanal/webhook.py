"""İE-06 · Meta webhook (WSGI). nginx (443, TLS) → gunicorn → bu uygulama. Hosting'teki developer/webhook.php + feature.php
pm_kanal_capture / pm_kanal_status'un yerine; yakalama kuralları aynı (docs/is_emirleri/IE-06.md › Tasarım 1).

  GET  /webhook   Meta'nın kayıt doğrulaması (hub.verify_token)
  POST /webhook   imzalı olay: her gelen mesaj Postgres'e yazılır; sahiplenilene iş açılır; sahiplenilmeyene sabit cevap satırı;
                  durum bildirimleri giden satırlarına işlenir; medya kaydı açılır (indirmeyi gönderici yapar)
  GET  /saglik    sır ve numara içermeyen JSON; 200 / 503 (dış izleyici ve nabiz.sh)

Sır tutmaz: app secret ve verify token /etc/portman/whatsapp.env'den (systemd EnvironmentFile) gelir; erişim belirteci bu
süreçte gerekmez. Günlüğe numara ve mesaj metni yazılmaz (kimlik_izi, maske).
Komut satırı: gunicorn --chdir /opt/portman/guncel/kanal --bind 127.0.0.1:8081 webhook:uygulama
"""
from __future__ import annotations

import hashlib
import json
import os
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
import meta_api as M                                  # noqa: E402
import nabiz as NB                                    # noqa: E402
from depo import Depo, kimlik_izi, maske             # noqa: E402

SURUM = "kanal-v2.0"
ESKI_SN = 900                       # feature.php: 15 dakikadan eski (geç tekrar teslim) mesaj kuyruğa alınmaz
GELECEK_SN = 60
NABIZ_SINIR_SN = 180                # ajan ve gönderici nabzı bundan eskiyse /saglik 503
NABIZ_SH_SINIR_SN = 900             # nabiz.sh'nin dosyası bundan eskiyse /saglik 503 (zamanlayıcı 5 dk)
SURUM_DOSYASI = KOD.parent / "SURUM"


def log(*p) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "webhook", *p, flush=True)


def surum_etiketi() -> str:
    try:
        return SURUM_DOSYASI.read_text(encoding="utf-8").strip() or SURUM
    except OSError:
        return os.environ.get("PORTMAN_SURUM") or SURUM


class Kanal:
    """Uygulamanın bağımlılıkları; testte sahte depo, ayar ve Meta ayarı verilir."""

    def __init__(self, depo: Depo | None = None, meta: M.MetaAyar | None = None, veri: Path | str | None = None, ayar_oku=None):
        self.veri = Path(veri or os.environ.get("PORTMAN_KANAL_DIR") or "/opt/portman/data")
        self.depo = depo or Depo()
        self.meta = meta or M.MetaAyar.ortamdan()
        self._ayar_oku = ayar_oku or (lambda: AY.oku(self.veri))

    def ayar(self) -> dict:
        return self._ayar_oku()


# ───────────────────────── olay işleme ─────────────────────────
def kuyruk_satiri(m: dict, mid: str, gonderen: str, tur: str, ts: int, adlar: dict, bayi: dict | None, ayar: dict, pnid: str, simdi: int) -> dict:
    """feature.php::pm_kanal_capture'ın kuyruk satırı; Depo.mesaj_kaydet ve kalici.bir_is bu biçimi bekler."""
    ctx = (m.get("context") or {}).get("id") if isinstance(m.get("context"), dict) else None
    reply, reply_kind = M.cevap_kimligi(m)
    medya_id, dosya_adi, _mime = M.medya_bilgisi(m)
    return {"id": mid, "context_id": str(ctx) if ctx and M.wamid_gecerli(str(ctx)) else None, "reply_id": reply, "reply_kind": reply_kind,
            "sender": gonderen, "name": str(adlar.get(gonderen) or "")[:120], "role": (bayi or {}).get("rol") or "bayi", "bayi": bayi,
            "type": tur, "text": M.gelen_metin(m)[:M.METIN_EN_COK], "media_id": medya_id, "filename": dosya_adi, "timestamp": ts,
            "received_at": simdi, "phone_number_id": pnid, "source": "Meta imzalı webhook", "mode": str(ayar.get("mode") or "patron"),
            "state": "queued", "attempts": 0, "result": None, "error": None, "updated_at": simdi}


def izinli_mi(bayi: dict | None, mode: str) -> bool:
    """feature.php::pm_kanal_allowed: hepsi → herkes; kayitli → kayıtlı ve aktif; başka her değer (patron) → yalnız rol=patron."""
    if mode == "hepsi":
        return True
    if mode == "kayitli":
        return bayi is not None
    return bayi is not None and bayi.get("rol") == "patron"


def mesaj_isle(k: Kanal, m: dict, adlar: dict, ayar: dict, simdi: int) -> str:
    mid = str(m.get("id") or ""); gonderen = str(m.get("from") or ""); tur = str(m.get("type") or "")
    try:
        ts = int(m.get("timestamp") or 0)
    except (TypeError, ValueError):
        ts = 0
    if not M.wamid_gecerli(mid) or not M.numara_gecerli(gonderen) or tur == "reaction":
        return "atlandi"
    bayi = k.depo.gelen_bayisi(gonderen)
    mode = str(ayar.get("mode") or "patron")
    izinli = izinli_mi(bayi, mode)
    eski = ts < int(ayar.get("enabled_at") or 0) or ts > simdi + GELECEK_SN or simdi - ts >= ESKI_SN
    satir = kuyruk_satiri(m, mid, gonderen, tur, ts, adlar, bayi, ayar, k.meta.phone_number_id, simdi)
    medya_id, dosya_adi, mime = M.medya_bilgisi(m)
    if izinli and not eski:
        sonuc = "sahiplenildi" if k.depo.mesaj_kaydet(satir) else "tekrar"
    elif izinli:
        satir["neden"] = "eski mesaj (geç teslim); kuyruğa alınmadı"
        sonuc = "eski" if k.depo.kayitsiz_mesaj_kaydet(satir, None)["yeni"] else "tekrar"
    else:
        satir["neden"] = "kayıtsız gönderen" if bayi is None else f"mod {mode}: bu gönderen işlenmiyor"
        r = k.depo.kayitsiz_mesaj_kaydet(satir, None if eski else ayar.get("kayitsiz_cevap"))
        sonuc = ("kayitsiz" + ("+cevap" if r["cevap"] else "")) if r["yeni"] else "tekrar"
    if sonuc != "tekrar" and medya_id:
        k.depo.gelen_dosya_ekle(mid, medya_id, dosya_adi, mime)
    log("mesaj", kimlik_izi(mid), "kimden", maske(gonderen), "tür", tur, "→", sonuc)
    return sonuc


def durum_isle(k: Kanal, st: dict) -> str:
    """Meta durum bildirimi (sent/delivered/read/failed) → giden satırı; eşleşme wamid ya da biz_opaque_callback_data ile."""
    mid = str(st.get("id") or ""); durum = str(st.get("status") or ""); alici = str(st.get("recipient_id") or "")
    try:
        ts = int(st.get("timestamp") or 0)
    except (TypeError, ValueError):
        ts = 0
    if not M.wamid_gecerli(mid) or durum not in M.DURUMLAR:
        return "atlandi"
    anahtar = "durum:" + hashlib.sha256(f"{mid}|{durum}|{ts}".encode()).hexdigest()[:32]
    if k.depo.olay_var(anahtar):
        return "tekrar"
    satir = k.depo.giden_durum_satiri(mid, st.get("biz_opaque_callback_data") if isinstance(st.get("biz_opaque_callback_data"), str) else None)
    if satir is None:
        k.depo.olay_kaydet(anahtar, "durum"); return "eslesmedi"
    if satir.get("alici_cozuldu") and alici and satir["alici_cozuldu"] != alici:
        k.depo.olay_kaydet(anahtar, "durum"); return "alici_uyusmadi"
    if satir.get("dis_id") is None:
        k.depo.gonderim_sonucu(satir["id"], "kabul_edildi", dis_id=mid, kabul_zamani=float(ts) if ts else None)
    if durum == "failed":
        hatalar = [f"{(e or {}).get('code', 0)} {str((e or {}).get('title') or '')[:120]}" for e in (st.get("errors") or []) if isinstance(e, dict)]
        k.depo.teslim_hatasi_yaz(satir["id"], "Meta teslimat hatası: " + "; ".join(hatalar))
    k.depo.teslim_bildir(satir["id"], durum, teslim_zamani=float(ts) if ts and durum in ("delivered", "read") else None,
                         gonderildi_zamani=float(ts) if ts and durum == "sent" else None)
    k.depo.olay_kaydet(anahtar, "durum")
    return durum


def olaylari_isle(k: Kanal, p: dict) -> dict:
    """İmzası doğrulanmış yük. Dönen sayım günlük ve test içindir."""
    say: dict = {"mesaj": {}, "durum": {}}
    if not isinstance(p, dict) or p.get("object") != "whatsapp_business_account":
        say["atlandi"] = "object"; return say
    ayar = k.ayar()
    if ayar.get("enabled") is not True:                      # feature.php: kanal kapalıyken hiçbir olay işlenmez
        say["atlandi"] = "enabled"; return say
    simdi = int(time.time())
    for entry in (p.get("entry") or []):
        for ch in ((entry or {}).get("changes") or []):
            v = (ch or {}).get("value") or {}
            if (ch or {}).get("field") != "messages" or str((v.get("metadata") or {}).get("phone_number_id") or "") != k.meta.phone_number_id:
                continue
            for st in (v.get("statuses") or []):
                try:
                    r = durum_isle(k, st if isinstance(st, dict) else {})
                except Exception as e:
                    r = "hata"; log("durum bildirimi işlenemedi:", type(e).__name__, maske_metin(str(e))[:120])
                say["durum"][r] = say["durum"].get(r, 0) + 1
            adlar = {}
            for c in (v.get("contacts") or []):
                if isinstance(c, dict):
                    adlar[str(c.get("wa_id") or "")] = str((c.get("profile") or {}).get("name") or "")
            for m in (v.get("messages") or []):
                r = mesaj_isle(k, m if isinstance(m, dict) else {}, adlar, ayar, simdi)
                say["mesaj"][r] = say["mesaj"].get(r, 0) + 1
    return say


def maske_metin(s: str) -> str:
    return M.maskele(s)


# ───────────────────────── sağlık ─────────────────────────
def saglik(k: Kanal) -> tuple[int, dict]:
    sorunlar = []; sayim = None; pg = True
    try:
        sayim = dict(k.depo.sayimlar())
    except Exception as e:
        pg = False; sorunlar.append(f"postgres: {type(e).__name__}")
    ayar = k.ayar()
    yaslar = {ad: NB.yas(k.veri, ad) for ad in ("agent", "gonderici")}
    if ayar.get("enabled") is True:
        for ad, y in yaslar.items():
            if y is None or y > NABIZ_SINIR_SN:
                sorunlar.append(f"{ad}: nabız {'yok' if y is None else f'{int(y)} sn eski'}")
    nb = NB.oku(k.veri, "nabiz")                              # vps/nabiz.sh (5 dk): servisler, sertifika, disk, yedek yaşı
    if nb:
        y = NB.yas(k.veri, "nabiz")
        if y is not None and y > NABIZ_SH_SINIR_SN:
            sorunlar.append(f"nabiz.sh: {int(y)} sn eski (zamanlayıcı durmuş olabilir)")
        sorunlar += ["nabiz: " + s[:120] for s in (nb.get("sorunlar") or [])[:10] if isinstance(s, str)]
    govde = {"ok": not sorunlar, "surum": surum_etiketi(), "zaman": int(time.time()), "postgres": pg, "enabled": ayar.get("enabled") is True,
             "dry_run": ayar.get("dry_run") is True, "mode": ayar.get("mode"), "ajan_sn": None if yaslar["agent"] is None else int(yaslar["agent"]),
             "gonderici_sn": None if yaslar["gonderici"] is None else int(yaslar["gonderici"]), "sayimlar": sayim, "sorunlar": sorunlar}
    return (200 if govde["ok"] else 503), govde


# ───────────────────────── WSGI ─────────────────────────
def _cevap(start_response, kod: int, govde, ctype: str = "application/json; charset=utf-8"):
    metin = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
             413: "Payload Too Large", 503: "Service Unavailable"}.get(kod, "Error")
    veri = govde if isinstance(govde, bytes) else (json.dumps(govde, ensure_ascii=False) if isinstance(govde, dict) else str(govde)).encode("utf-8")
    start_response(f"{kod} {metin}", [("Content-Type", ctype), ("Content-Length", str(len(veri))), ("Cache-Control", "no-store"),
                                      ("X-Content-Type-Options", "nosniff")])
    return [veri]


def uygulama_olustur(k: Kanal):
    def uygulama(environ, start_response):
        yol = environ.get("PATH_INFO") or "/"; metod = environ.get("REQUEST_METHOD") or "GET"
        if yol == "/saglik":
            if metod != "GET":
                return _cevap(start_response, 405, {"hata": "method"})
            kod, govde = saglik(k)
            return _cevap(start_response, kod, govde)
        if yol != "/webhook":
            return _cevap(start_response, 404, {"hata": "yok"})
        if metod == "GET":
            sorgu = {a: v[0] for a, v in urllib.parse.parse_qs(environ.get("QUERY_STRING") or "", keep_blank_values=True).items()}
            c = M.hub_cevabi(sorgu, k.meta.verify_token)
            if c is None:
                return _cevap(start_response, 403, b"", "text/plain; charset=utf-8")
            return _cevap(start_response, 200, c.encode("utf-8"), "text/plain; charset=utf-8")
        if metod != "POST":
            return _cevap(start_response, 405, {"hata": "method"})
        try:
            n = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            n = 0
        if n > M.GOVDE_EN_COK:
            return _cevap(start_response, 413, {"hata": "govde"})
        govde = environ["wsgi.input"].read(n) if n > 0 else b""
        if not M.imza_gecerli(govde, environ.get("HTTP_X_HUB_SIGNATURE_256"), k.meta.app_secret):
            log("imza geçersiz; reddedildi")
            return _cevap(start_response, 401, {"hata": "imza"})
        try:
            p = json.loads(govde.decode("utf-8"))
        except ValueError:
            return _cevap(start_response, 400, {"hata": "json"})
        try:
            say = olaylari_isle(k, p)
        except Exception:
            log("olay işlenemedi:", maske_metin(traceback.format_exc()[-600:]))
            return _cevap(start_response, 503, {"hata": "islenemedi"})       # Meta yeniden dener; tekilleştirme çift kaydı önler
        return _cevap(start_response, 200, {"ok": True, **say})
    return uygulama


_varsayilan = {"k": None}


def uygulama(environ, start_response):
    """gunicorn giriş noktası (ayarlar ortamdan; ilk istekte kurulur)."""
    if _varsayilan["k"] is None:
        _varsayilan["k"] = Kanal()
    return uygulama_olustur(_varsayilan["k"])(environ, start_response)
