"""İE-06 · uçtan uca YEREL test (B1): sahte Meta → webhook (kanal/webhook.py, WSGI, süreç içi) → Postgres → ajan (vps/agent.py,
AYRI süreç, kayıtlı LLM çıkarımı) → gönderici (kanal/gonderici.py, süreç içi, sahte Graph API) → sahte Meta durum bildirimi →
buton cevabı → onay zinciri; mesaj katmanı kapalıyken v1.2 davranışı; kayıtsız numara (sabit cevap, 24 saatte bir); gelen görsel
(indirme, panelde dosya); panel; /saglik. Gerçek Postgres ve GERÇEK Motor; LLM, WhatsApp ve canlı yok.
e2e_katman.py (İE-04, gerçek PHP hattı; kaldırıldı) ve kapı G senaryosunun tek sunucu karşılığıdır; ölçütler aynı tutuldu.

Çalıştırma: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python3 kanal/tests/e2e_vps_kanal.py
(testler/kalici/test_e2e_vps_kanal.py aynı betiği pytest içinden koşturur; ortam_kur.sh --dogrula kapsar.)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "kanal"), str(ROOT), str(ROOT / "testler" / "kalici")]
ADMIN = os.environ.get("PORTMAN_TEST_PG", "")
if not ADMIN:
    raise SystemExit("PORTMAN_TEST_PG gerekli (Postgres)")
import psycopg                        # noqa: E402
from psycopg.types.json import Jsonb  # noqa: E402

import ayarlar as AY                  # noqa: E402
import gonderici as G                 # noqa: E402
import meta_api as M                  # noqa: E402
import panel as PN                    # noqa: E402
import webhook as WH                  # noqa: E402
from depo import Depo                 # noqa: E402
from sahte_meta import SahteMeta      # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="pm_e2e_vps_"))
VERI = tmp / "data"; (VERI / "nabiz").mkdir(parents=True)
PNID = "106000000000001"
PATRON = "900000000909"               # gerçek olmayan deneme numaraları
BAYI = "900000000101"
KAYITSIZ = "900000000777"
SIR = "e2e-app-" + "s" * 24           # sahte app secret (çalışma anında)
VERIFY = "dogrulama-" + "v" * 16
CEVAP = "Bu hat yalnız kayıtlı bayilere açıktır."
GIRIS = "panel-" + "g" * 16           # sahte panel parolası (çalışma anında)
for anahtar, deger in (("enabled", True), ("enabled_at", int(time.time()) - 3600), ("dry_run", False), ("mode", "patron"),
                       ("llm", {"backend": "manuel", "model": "test", "timeout_s": 5}), ("patron_teknik_not", True), ("mesaj_katmani", True),
                       ("ucb_taban_url", "https://ornek.invalid/portman/3d"), ("kayitsiz_cevap", CEVAP)):
    AY.yaz(VERI, anahtar, deger)
(VERI / "yayin" / "3d").mkdir(parents=True)        # İE-21: sunucuda vps/nginx_uygula.sh açar (nginx /3d/<anahtar>/)
(VERI / "self-test-result.json").write_text('{"state": "skipped", "not": "e2e: öz-test ayrı (vps/oz_test.sh)"}', encoding="utf-8")

dbad = "e2ev_" + uuid.uuid4().hex[:8]
with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
    c.execute(f"CREATE DATABASE {dbad}")
DSN = f"{ADMIN} dbname={dbad}"
depo = Depo(DSN); depo.goc_uygula()
depo.bayi_yaz(PATRON, ad="Patron", rol="patron")
depo.bayi_yaz(BAYI, ad="Deneme Bayi A", kod="TSTA", rol="bayi")

meta = M.MetaAyar(phone_number_id=PNID, access_token="t" * 40, app_secret=SIR, verify_token=VERIFY)
kanal = WH.Kanal(depo=depo, meta=meta, veri=VERI)
app_wh = WH.uygulama_olustur(kanal)
sahte = SahteMeta(); istemci = M.GraphIstemci(meta, http=sahte)
gonderen = G.GonderenMeta(depo, istemci, VERI)
app_pn = PN.uygulama_olustur(PN.Panel(depo=depo, veri=VERI, sir="f" * 64, parola=PN.parola_ozeti(GIRIS)))

sonuc = []
_say = [0]


def ok(c, ne):
    sonuc.append(bool(c)); print(("  ✓ " if c else "  ✗ ") + ne, flush=True)


def q(sql, *a):
    with depo.baglan() as c:
        return c.execute(sql, a).fetchall()


def istek(app, metod, yol, govde: bytes = b"", basliklar=None, cerez=None, sorgu=""):
    env = {"REQUEST_METHOD": metod, "PATH_INFO": yol, "QUERY_STRING": sorgu, "CONTENT_LENGTH": str(len(govde)), "wsgi.input": BytesIO(govde), "REMOTE_ADDR": "127.0.0.1"}
    for a, v in (basliklar or {}).items():
        if a.lower() == "content-type":
            env["CONTENT_TYPE"] = v                       # WSGI: Content-Type HTTP_ öneksizdir (panel çok parçalı gövdeyi bundan tanır)
        env["HTTP_" + a.upper().replace("-", "_")] = v
    if cerez:
        env["HTTP_COOKIE"] = "; ".join(f"{a}={v}" for a, v in cerez.items())
    out = {}

    def sr(status, headers):
        out["status"] = int(status.split()[0]); out["headers"] = headers
    body = b"".join(app(env, sr))
    return out["status"], body, out["headers"]


def webhook(yuk_: dict):
    govde = json.dumps(yuk_).encode("utf-8")
    kod, body, _ = istek(app_wh, "POST", "/webhook", govde, {"Content-Type": "application/json", "X-Hub-Signature-256": M.imzala(govde, SIR)})
    return kod, json.loads(body)


def yuk(mesajlar=(), durumlar=(), adlar=None) -> dict:
    v = {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "0", "phone_number_id": PNID}}
    if adlar:
        v["contacts"] = [{"wa_id": n, "profile": {"name": a}} for n, a in adlar.items()]
    if mesajlar:
        v["messages"] = list(mesajlar)
    if durumlar:
        v["statuses"] = list(durumlar)
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": v}]}]}


def _mid(mid):
    _say[0] += 1
    return mid or f"wamid.E2E{_say[0]:03d}{uuid.uuid4().hex[:6]}"


def metin(gonderen_, metin_, mid=None):
    return {"from": gonderen_, "id": _mid(mid), "timestamp": str(int(time.time())), "type": "text", "text": {"body": metin_}}


def buton(gonderen_, kimlik, baslik, context_wamid, mid=None):
    return {"from": gonderen_, "id": _mid(mid), "timestamp": str(int(time.time())), "type": "interactive", "context": {"id": context_wamid},
            "interactive": {"type": "button_reply", "button_reply": {"id": kimlik, "title": baslik}}}


def gorsel(gonderen_, medya_id, mid=None):
    return {"from": gonderen_, "id": _mid(mid), "timestamp": str(int(time.time())), "type": "image",
            "image": {"id": medya_id, "mime_type": "image/jpeg", "sha256": "0" * 64, "caption": "ölçü krokisi"}}


def durum(wamid, st, opaque=None, ts=None):
    d = {"id": wamid, "status": st, "timestamp": str(int(ts or time.time())), "recipient_id": PATRON}
    if opaque:
        d["biz_opaque_callback_data"] = opaque
    return d


def hazir_ekle(mid, cikarim):
    """Kayıtlı LLM çıkarımı (manuel arka uç): e2e_katman.py'deki hazir_ekle'nin karşılığı; ajan bu alanı mesajlar.ham'dan okur."""
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE mesajlar SET ham = ham || %s WHERE id = %s", (Jsonb({"test_cikarim": cikarim}), mid))


AENV = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI", "ANTHROPIC"))}
AENV.update(PORTMAN_PG_DSN=DSN, PORTMAN_KANAL_DIR=str(VERI), PORTMAN_AGENT_ONESHOT="1")


def ajan() -> int:
    r = subprocess.run([sys.executable, str(ROOT / "vps" / "agent.py")], env=AENV, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-2000:])
    return r.returncode


def gonder() -> dict:
    return G.tur(depo, gonderen, istemci, VERI)


try:
    print("1) katman açık: imzalı Patron metni → webhook → ajan (gerçek Motor) → görsel başlıklı buton mesajı + PDF + 3D bağlantısı → sahte Meta")
    kod, c = webhook(yuk([metin(PATRON, "P6001 aynalı", mid="wamid.E2EK1")], adlar={PATRON: "Patron"}))
    ok(kod == 200 and c.get("mesaj") == {"sahiplenildi": 1}, f"webhook: Patron metni sahiplenildi ({c})")
    hazir_ekle("wamid.E2EK1", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "P6001 aynalı", "katalog_kodu": "P6001",
                               "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}]})
    ok(ajan() == 0, "ajan (oneshot) iş işledi ve çıktı")
    i1 = q("SELECT durum, sonuc FROM isler WHERE mesaj_id = 'wamid.E2EK1'")[0]
    ok(i1["durum"] == "bitti" and i1["sonuc"]["eylem"] == "is_emri", f"iş: bitti, is_emri ({i1['sonuc'].get('gerekce')})")
    kinds = [r["kind"] for r in q("SELECT kind FROM giden WHERE mesaj_id = 'wamid.E2EK1' ORDER BY sira")]
    ok(kinds == ["interactive", "document", "interactive", "text"], f"giden satırları (son metin: Patron teknik notu): {kinds}")
    rev = q("SELECT is_emri_no, rev, ekler, durum FROM revizyonlar")[0]
    no = rev["is_emri_no"]
    u1 = rev["ekler"]["ucb"]
    ok(rev["ekler"]["ifc"]["sema_hatasi"] == 0 and re.fullmatch(r"https://ornek\.invalid/portman/3d/[A-Za-z0-9_-]{22}/", u1["url"] or "") and no not in u1["url"]
       and (VERI / "yayin" / "3d" / u1["anahtar"] / "index.html").read_bytes() == Path(u1["dosya"]).read_bytes(),
       "Postgres: ekler (IFC şema 0, 3D url rastgele anahtarlı; sayfa data/yayin/3d'de bayt bayt aynı)")
    pdf_yol = depo.cikti_yolu(PATRON, no, 1)
    ok(pdf_yol and Path(pdf_yol).is_file() and Path(pdf_yol).read_bytes()[:4] == b"%PDF" and str(VERI / "projects") in pdf_yol, "PDF data/projects altında")
    say = gonder()
    ok(say.get("kabul_edildi") == 4, f"gönderici: 4 satır kabul edildi ({ {k: v for k, v in say.items() if k != 'medya'} })")
    tipler = sahte.tipler()
    ok(tipler == ["media", "interactive/button", "media", "document", "interactive/cta_url", "text"], f"Meta çağrıları: {tipler}")
    g = sahte.gidenler()
    ilk = q("SELECT id, dis_id FROM giden WHERE mesaj_id = 'wamid.E2EK1' ORDER BY sira")
    ok(g[0]["interactive"]["header"]["image"]["id"] == "1001" and len(g[0]["interactive"]["action"]["buttons"]) == 2
       and g[0].get("biz_opaque_callback_data") == ilk[0]["id"], "buton mesajı: medya kimlikli başlık görseli, 2 buton, satır kimliği (biz_opaque_callback_data)")
    ok(sorted(b["reply"]["id"] for b in g[0]["interactive"]["action"]["buttons"]) == sorted([f"o:{no}:1", f"r:{no}:1"]), "butonlar: o:/r: kimlikleri revizyonla aynı")
    ok(g[2]["interactive"]["action"]["parameters"] == {"display_text": "3D'yi aç", "url": u1["url"]} and g[1]["document"]["id"] == "1002",
       "\"3D'yi aç\" düğmesi 3D url'siyle; PDF medya kimliğiyle")
    ok(all(r["dis_id"] and r["dis_id"].startswith("wamid.OUT") for r in ilk), "Postgres: dört satırın wamid'i kayıtlı")
    buton_wamid = ilk[0]["dis_id"]; pdf = ilk[1]

    print("2) sahte Meta durum bildirimi (delivered, biz_opaque_callback_data ile) ve tekilleştirme")
    d = durum(pdf["dis_id"], "delivered", pdf["id"])
    kod, c = webhook(yuk(durumlar=[d]))
    ok(kod == 200 and c.get("durum") == {"delivered": 1}, f"durum bildirimi işlendi ({c.get('durum')})")
    ok(q("SELECT teslim_durumu FROM giden WHERE id = %s", pdf["id"])[0]["teslim_durumu"] == "delivered", "Postgres: PDF satırı teslim edildi")
    ok(webhook(yuk(durumlar=[d]))[1].get("durum") == {"tekrar": 1}, "aynı bildirim ikinci kez: tekilleştirildi")
    ok(webhook(yuk([metin(PATRON, "P6001 aynalı", mid="wamid.E2EK1")]))[1].get("mesaj") == {"tekrar": 1} and q("SELECT count(*) AS n FROM isler")[0]["n"] == 1,
       "aynı mesaj yeniden: ikinci iş yok")

    print("3) buton cevabı: eski/yanlış kimlik reddedilir; doğru 'Onayla' doğru revizyona bağlar; LLM çağrılmaz")
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(PATRON, f"o:{no}:9", "Onayla", buton_wamid, mid="wamid.E2EB1")]))
    ham = q("SELECT ham FROM mesajlar WHERE id = 'wamid.E2EB1'")[0]["ham"]
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ham["reply_id"] == f"o:{no}:9" and ham["context_id"] == buton_wamid, "kuyruk satırı: reply_id + context_id")
    ok(ajan() == 0, "ajan: eski kimlik işlendi")
    r1 = q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2EB1'")[0]["sonuc"]
    ok(r1["eylem"] == "cevapla" and "eski buton" in r1["gerekce"] and q("SELECT durum FROM revizyonlar")[0]["durum"] == "onay_bekliyor", "eski kimlik: cevap verildi, revizyon değişmedi")
    webhook(yuk([buton(PATRON, f"o:{no}:1", "Onayla", buton_wamid, mid="wamid.E2EB2")]))
    ok(ajan() == 0, "ajan: onay butonu işlendi")
    r2 = q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2EB2'")[0]["sonuc"]
    j = q("SELECT cikarim FROM isler WHERE mesaj_id = 'wamid.E2EB2'")[0]["cikarim"]
    ok(r2["gerekce"] == "plan onaylandı" and j["meta"]["backend"] == "etkilesim", "onay: plan onaylandı, çıkarım kaynağı 'etkilesim' (LLM yok)")
    z = q("SELECT revizyon_durumu, onay_alintisi FROM onay_zinciri")[0]
    ok(z["revizyon_durumu"] == "onaylandi" and z["onay_alintisi"] == buton_wamid, "onay zinciri: onaylandı; alıntı = buton mesajı")
    say = gonder()
    ok(say.get("kabul_edildi") == 4 and sahte.tipler()[6:] == ["text"] * 4, "cevaplar (ve Patron teknik notları) metin olarak gönderildi")
    ok(not any("o:" + no in json.dumps(x) for x in sahte.gidenler()[6:]), "cevap metinlerinde buton kimliği yok")

    print("4) mesaj katmanı kapalı (mode kayitli): kayıtlı bayi → yalnız metin + PDF (v1.2 davranışı)")
    AY.yaz(VERI, "mesaj_katmani", False); AY.yaz(VERI, "mode", "kayitli")
    kod, c = webhook(yuk([metin(BAYI, "P6001 aynalı", mid="wamid.E2EK4")], adlar={BAYI: "Deneme"}))
    ok(c.get("mesaj") == {"sahiplenildi": 1}, "kayıtlı bayinin mesajı sahiplenildi")
    hazir_ekle("wamid.E2EK4", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "P6001 aynalı", "katalog_kodu": "P6001",
                               "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}]})
    ok(ajan() == 0, "ajan: bayinin işi işlendi")
    kinds = [r["kind"] for r in q("SELECT kind FROM giden WHERE mesaj_id = 'wamid.E2EK4' ORDER BY sira")]
    ok(kinds[:2] == ["text", "document"] and "interactive" not in kinds and "image" not in kinds, f"giden satırları: {kinds}")
    onceki = len(sahte.istekler)
    say = gonder()
    yeni = sahte.tipler()[sum(1 for i in sahte.istekler[:onceki] if i['url'].endswith('/media') or i['url'].endswith('/messages')):]
    ok(say.get("kabul_edildi") == len(kinds) and yeni[:3] == ["text", "media", "document"] and "interactive/button" not in yeni, f"Meta çağrıları: {yeni}")

    print("5) kayıtsız numara: mesaj kaydedilir, sabit cevap bir kez (24 saat), iş açılmaz")
    kod, c = webhook(yuk([metin(KAYITSIZ, "merhaba, plan lazım", mid="wamid.E2EX1")]))
    ok(c.get("mesaj") == {"kayitsiz+cevap": 1}, f"webhook: kayıtsız + cevap satırı ({c.get('mesaj')})")
    m = q("SELECT sahiplenildi FROM mesajlar WHERE id = 'wamid.E2EX1'")[0]
    i2 = q("SELECT durum, sonuc FROM isler WHERE mesaj_id = 'wamid.E2EX1'")[0]
    ok(m["sahiplenildi"] is False and i2["durum"] == "bitti" and i2["sonuc"]["eylem"] == "kayitsiz", "Postgres: sahiplenilmedi, iş 'bitti/kayitsiz'")
    say = gonder()
    son = sahte.gidenler()[-1]
    ok(say.get("kabul_edildi") == 1 and son["to"] == KAYITSIZ and son["text"]["body"] == CEVAP, "sabit cevap kayıtsız numaraya gitti")
    kod, c = webhook(yuk([metin(KAYITSIZ, "yine ben", mid="wamid.E2EX2")]))
    ok(c.get("mesaj") == {"kayitsiz": 1} and gonder().get("kabul_edildi", 0) == 0, "24 saat içinde ikinci mesaj: cevap yok")
    ok(ajan() == 0 and q("SELECT count(*) AS n FROM isler WHERE gonderen = %s AND durum <> 'bitti'", KAYITSIZ)[0]["n"] == 0, "ajan: kayıtsız için iş yok")

    print("6) gelen görsel (kayıtsız numaradan): kayıt → gönderici indirir → data/gelen_medya; panelde dosya")
    kod, c = webhook(yuk([gorsel(KAYITSIZ, "7001", mid="wamid.E2EX3")]))
    ok(c.get("mesaj") == {"kayitsiz": 1} and q("SELECT count(*) AS n FROM gelen_dosyalar WHERE yol IS NULL")[0]["n"] == 1, "gelen dosya kaydı açıldı (indirilmedi)")
    say = gonder()
    df = q("SELECT id, yol, boyut, mime FROM gelen_dosyalar")[0]
    ok(say.get("medya", {}).get("indirildi") == 1 and df["yol"] and Path(df["yol"]).is_file() and df["yol"].startswith(str(VERI / "gelen_medya"))
       and df["boyut"] == len(sahte.medya_icerik) and df["mime"] == "image/jpeg", "gönderici medyayı indirdi (sahte lookaside), kayıt tamam")

    print("7) panel: giriş, gelen kutusu, konuşmalar, dosya indirme; /saglik")
    kod, body, basliklar = istek(app_pn, "GET", "/panel/giris")
    on = dict(h for h in basliklar if h[0] == "Set-Cookie")["Set-Cookie"].split(";")[0].split("=", 1)
    import re
    csrf = re.search(rb'name="csrf" value="([0-9a-f]+)"', body).group(1).decode()
    form = urllib.parse.urlencode({"parola": GIRIS, "csrf": csrf}).encode()
    kod, body, basliklar = istek(app_pn, "POST", "/panel/giris", form, {"Content-Type": "application/x-www-form-urlencoded"}, cerez={on[0]: on[1]})
    oturum = next(h[1] for h in basliklar if h[0] == "Set-Cookie" and h[1].startswith("pm_oturum=")).split(";")[0].split("=", 1)
    ok(kod == 302 and oturum[0] == "pm_oturum", "panel girişi")
    cerez = {oturum[0]: oturum[1]}
    kod, body, _ = istek(app_pn, "GET", "/panel/", cerez=cerez)
    ok(kod == 200 and all(x.encode() in body for x in (PATRON, BAYI, KAYITSIZ, "kayıtsız", "sahiplenildi", "Patron", "Deneme Bayi A")), "gelen kutusu: üç konuşma")
    kod, body, _ = istek(app_pn, "GET", f"/panel/konusma/{PATRON}", cerez=cerez)
    ok(kod == 200 and b"document" in body and b"teslim: delivered" in body and b"Onayla" in body and b'class="giden"' in body, "Patron konuşması: PDF teslimi ve buton cevabı görünür")
    kod, body, _ = istek(app_pn, "GET", f"/panel/konusma/{KAYITSIZ}", cerez=cerez)
    ok(kod == 200 and CEVAP.encode() in body and f"/panel/dosya/{df['id']}".encode() in body and "ölçü krokisi".encode() in body, "kayıtsız konuşması: sabit cevap ve dosya bağlantısı")
    kod, body, basliklar = istek(app_pn, "GET", f"/panel/dosya/{df['id']}", cerez=cerez)
    ok(kod == 200 and body == sahte.medya_icerik and dict(basliklar).get("Content-Type") == "image/jpeg", "dosya indirme: içerik sahte Meta'dan gelenle aynı")
    kod, body, _ = istek(app_wh, "GET", "/saglik")
    s = json.loads(body)
    ok(kod == 200 and s["ok"] and s["postgres"] and s["sayimlar"]["aktif_bayi"] == 2 and s["sayimlar"]["acik_is"] == 0, f"/saglik 200 ({s['sorunlar']})")
    ok(PATRON not in body.decode() and SIR not in body.decode(), "/saglik: numara ve sır yok")

    print("8) İE-07: panelden metin + PDF, 24 saat penceresi, 'dosyalar hazır' şablonu, bayinin düğme cevabı, Patron şablonu")
    import sablonlar as S

    def coklu(yol, alanlar, dosyalar=None):
        sinir = "----pmE2E" + uuid.uuid4().hex
        parcalar = [f'--{sinir}\r\nContent-Disposition: form-data; name="{a}"\r\n\r\n{v}\r\n'.encode("utf-8") for a, v in alanlar.items()]
        for a, (ad, icerik) in (dosyalar or {}).items():
            parcalar.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{a}"; filename="{ad}"\r\nContent-Type: application/pdf\r\n\r\n'.encode("utf-8") + icerik + b"\r\n")
        govde = b"".join(parcalar) + f"--{sinir}--\r\n".encode()
        return istek(app_pn, "POST", yol, govde, {"Content-Type": f"multipart/form-data; boundary={sinir}"}, cerez=cerez)

    no_b = q("SELECT is_emri_no FROM revizyonlar WHERE gonderen = %s", BAYI)[0]["is_emri_no"]
    kod, body, _ = istek(app_pn, "GET", f"/panel/konusma/{BAYI}", cerez=cerez)
    csrf = re.search(rb'name="csrf" value="([0-9a-f]+)"', body).group(1).decode()
    ok(kod == 200 and "24 saat penceresi <b>açık</b>".encode() in body and f"şablonu gönder ({no_b})".encode() in body, "konuşma sayfası: cevap formu, pencere açık, şablon düğmesi")
    pdf_icerik = Path(pdf_yol).read_bytes()
    kod, body, basliklar = coklu(f"/panel/konusma/{BAYI}/gonder", {"csrf": csrf, "metin": "Panelden: çelik çizim seti ekte", "aciklama": "Ç8201 çizim seti"}, {"pdf": ("Ç8201 çizim seti.pdf", pdf_icerik)})
    pr = q("SELECT kind, durum, kaynak, sira, dosya FROM giden WHERE kaynak = 'panel' ORDER BY sira")
    ok(kod == 302 and [r["kind"] for r in pr] == ["text", "document"] and pr[0]["sira"] == 101 and pr[1]["dosya"].startswith(str(VERI / "projects" / "panel" / BAYI)),
       f"panel satırları: metin + PDF (kaynak panel, sıra 101–102; PDF projects/panel altında)")
    onceki = len(sahte.gidenler())
    say = gonder()
    g8 = sahte.gidenler()[onceki:]
    ok(say.get("kabul_edildi") == 2 and [x["type"] for x in g8] == ["text", "document"] and all(x["to"] == BAYI for x in g8), f"gönderici: panel metni ve PDF bayiye gitti ({[x['type'] for x in g8]})")
    kod, body, _ = istek(app_pn, "GET", f"/panel/konusma/{BAYI}", cerez=cerez)
    ok(b"<b>panel</b>" in body and "Panelden: çelik çizim seti ekte".encode() in body and b"kabul_edildi" in body, "sayfada panel etiketi ve durum")
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE mesajlar SET wa_zamani = now() - interval '25 hours' WHERE gonderen = %s", (BAYI,))
    kod, body, _ = istek(app_pn, "GET", f"/panel/konusma/{BAYI}", cerez=cerez)
    ok("24 saat penceresi <b>kapalı</b>".encode() in body, "bayinin son mesajı 25 saat önce: sayfa 'pencere kapalı' der")
    kod, body, _ = istek(app_pn, "POST", f"/panel/konusma/{BAYI}/gonder", urllib.parse.urlencode({"csrf": csrf, "metin": "pencere kapalıyken"}).encode(),
                         {"Content-Type": "application/x-www-form-urlencoded"}, cerez=cerez)
    say = gonder()
    kapali = q("SELECT durum, hata FROM giden WHERE kaynak = 'panel' ORDER BY sira DESC LIMIT 1")[0]
    ok(kod == 302 and say.get("gonderilmedi") == 1 and kapali["hata"] == "Gönderilmedi: reply_window_closed", "pencere kapalı: panel metni gönderilmedi (reply_window_closed)")
    AY.yaz(VERI, "sablon_bayi_dosyalar_hazir", "portman_dosyalar_hazir_v1"); AY.yaz(VERI, "sablon_patron_bildirim", "portman_patron_bekliyor_v1")
    kod, body, _ = istek(app_pn, "POST", f"/panel/konusma/{BAYI}/sablon", urllib.parse.urlencode({"csrf": csrf}).encode(),
                         {"Content-Type": "application/x-www-form-urlencoded"}, cerez=cerez)
    say = gonder()
    son = sahte.gidenler()[-1]
    ok(kod == 302 and say.get("kabul_edildi") == 1 and son["type"] == "template" and son["to"] == BAYI and son["template"]["name"] == "portman_dosyalar_hazir_v1"
       and son["template"]["language"] == {"code": "tr"}, "'dosyalar hazır' şablonu pencere kapalıyken gitti (Meta template yükü)")
    ok(son["template"]["components"][0]["parameters"][0]["text"] == "Deneme Bayi A" and son["template"]["components"][0]["parameters"][1]["text"] == no_b
       and son["template"]["components"][1]["parameters"] == [{"type": "payload", "payload": f"dosya:{no_b}"}], "şablon değişkenleri: ad (hitap boş), İş Emri no; hızlı yanıt payload")
    dugme = {"from": BAYI, "id": "wamid.E2ED1", "timestamp": str(int(time.time())), "type": "button", "button": {"text": "Dosyaları gönder", "payload": f"dosya:{no_b}"}}
    kod, c = webhook(yuk([dugme]))
    ok(kod == 200 and c.get("mesaj") == {"sahiplenildi": 1} and q("SELECT ham FROM mesajlar WHERE id = 'wamid.E2ED1'")[0]["ham"]["reply_id"] == f"dosya:{no_b}", "bayinin hızlı yanıtı (type=button, payload dosya:) kuyrukta")
    ok(ajan() == 0, "ajan: düğme cevabı işlendi")
    r8 = q("SELECT sonuc, cikarim FROM isler WHERE mesaj_id = 'wamid.E2ED1'")[0]
    k8 = q("SELECT alici, kind, govde FROM giden WHERE mesaj_id = 'wamid.E2ED1' ORDER BY sira")
    ok(r8["sonuc"]["eylem"] == "cevapla" and r8["sonuc"]["gerekce"] == "şablon cevabı: dosya penceresi açıldı" and (r8["cikarim"] or {}).get("meta", {}).get("backend") == "etkilesim",
       "düğme cevabı LLM'siz (çıkarım kaynağı etkileşim)")
    ok([(x["alici"], x["kind"]) for x in k8] == [(BAYI, "text"), ("PATRON", "text"), ("PATRON", "template")] and k8[0]["govde"] == S.BAYI_DOSYA_CEVABI,
       "satırlar: bayiye onaylı sabit cevap, Patron'a metin + şablon")
    say = gonder()
    ps = q("SELECT kind, durum, hata FROM giden WHERE mesaj_id = 'wamid.E2ED1' AND alici = 'PATRON' ORDER BY sira")
    ok(say.get("kabul_edildi") == 2 and ps[0]["durum"] == "kabul_edildi" and ps[1]["durum"] == "gonderilmedi" and ps[1]["hata"].startswith("Gönderilmedi: sablon_gereksiz"),
       "Patron penceresi açık: metin gitti, şablon 'sablon_gereksiz' (ücretli şablon boşa gitmez)")
    kod, body, _ = istek(app_pn, "POST", f"/panel/konusma/{BAYI}/gonder", urllib.parse.urlencode({"csrf": csrf, "metin": "pencere açıldı, dosyalar geliyor"}).encode(),
                         {"Content-Type": "application/x-www-form-urlencoded"}, cerez=cerez)
    say = gonder()
    ok(kod == 302 and say.get("kabul_edildi") == 1 and sahte.gidenler()[-1]["to"] == BAYI and sahte.gidenler()[-1]["type"] == "text", "bayinin cevabı pencereyi açtı: panel metni gitti")
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE mesajlar SET wa_zamani = now() - interval '25 hours' WHERE gonderen = %s", (PATRON,))
    kod, c = webhook(yuk([metin(BAYI, "P8501 olsun", mid="wamid.E2EY1")]))
    hazir_ekle("wamid.E2EY1", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "P8501", "katalog_kodu": "P8501"})
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0 and q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2EY1'")[0]["sonuc"]["eylem"] == "yonlendir",
       "bayi çizilemeyen model istedi: yönlendirme")
    say = gonder()
    py = q("SELECT kind, durum, hata FROM giden WHERE mesaj_id = 'wamid.E2EY1' AND alici = 'PATRON' ORDER BY sira")
    son = sahte.gidenler()[-1]
    ok(py[0]["hata"] == "Gönderilmedi: reply_window_closed" and py[1]["durum"] == "kabul_edildi" and son["type"] == "template" and son["to"] == PATRON
       and son["template"]["name"] == "portman_patron_bekliyor_v1", "Patron penceresi kapalı: metin düştü, Patron şablonu gitti (24 saat kuralına takılmadan)")
    ok(son["template"]["components"][0]["parameters"] == [{"type": "text", "text": "TSTA"}, {"type": "text", "text": no_b}]
       and son["template"]["components"][1] == {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": f"konusma/{BAYI}"}]},
       "Patron şablonu: bayi kodu, talep kimliği (taslağın son İş Emri no'su), panel konuşma bağlantısı")
    kod, body, _ = istek(app_pn, "GET", f"/panel/konusma/{PATRON}", cerez=cerez)
    ok(b"template" in body and "pencere kapalı (24 saat)".encode() in body and "şablon gereksiz".encode() in body, "Patron konuşma sayfası: şablon satırı ve hata etiketleri")

    print("9) İE-08 çelik (A2–A3): kabul kaydı → 'Ç8801' → üç çatı seçeneği tek görselde → düğme → r01 genel motordan (perspektifli bayi görseli + pafta PDF)")
    AY.yaz(VERI, "mesaj_katmani", True)
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE mesajlar SET wa_zamani = now() WHERE gonderen = %s", (BAYI,))        # bayinin penceresi açık
    for kod9 in ("Ç8801", "Ç8801K", "Ç8801L"):                                                 # K-A10: kabul kaydı (vps/ie08_adaylar.sh'nin yazdığı; D-11)
        depo.aday_yaz(kod9, "gecerli", referans_model="Ç8801", muhendis_kabulu={"kim": "e2e", "tarih": "2026-10-13", "not": ""})
    time.sleep(1.2)
    kod, c = webhook(yuk([metin(BAYI, "Ç8801 olsun", mid="wamid.E2EC1")]))
    hazir_ekle("wamid.E2EC1", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "Ç8801 istiyor", "katalog_kodu": "Ç8801"})
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: 'Ç8801' işlendi")
    i9 = q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2EC1'")[0]["sonuc"]
    s9 = q("SELECT id, durum, adaylar FROM secenek_setleri ORDER BY olusturuldu DESC LIMIT 1")[0]
    ok(i9["eylem"] == "secenek" and [a["kod"] for a in s9["adaylar"]] == ["Ç8801", "Ç8801K", "Ç8801L"] and s9["durum"] == "acik",
       f"çatı seçenek seti: katalog, K, L ({i9.get('gerekce')})")
    k9 = q("SELECT kind, satir FROM giden WHERE mesaj_id = 'wamid.E2EC1' ORDER BY sira")
    ok([x["kind"] for x in k9] == ["interactive"] and [b["reply"]["title"] for b in k9[0]["satir"]["interactive"]["action"]["buttons"]] == ["1. Ç8801", "2. Ç8801-K", "3. Ç8801-L"]
       and Path(k9[0]["satir"]["file"]).is_file(), "tek etkileşim satırı: bileşik görsel + 3 düğme; öncelik sorusu yok")
    say = gonder()
    g9 = sahte.gidenler()[-1]
    ok(say.get("kabul_edildi") == 1 and g9["type"] == "interactive" and "image" in g9["interactive"]["header"] and len(g9["interactive"]["action"]["buttons"]) == 3,
       "Meta: görsel başlıklı 3 düğmeli seçenek mesajı")
    set_wamid = q("SELECT dis_id FROM giden WHERE mesaj_id = 'wamid.E2EC1'")[0]["dis_id"]
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(BAYI, f"s:{s9['id']}:Ç8801K", "2. Ç8801-K", set_wamid, mid="wamid.E2EC2")]))
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: çatı K düğmesi işlendi (gerçek genel motor)")
    i9b = q("SELECT sonuc, cikarim FROM isler WHERE mesaj_id = 'wamid.E2EC2'")[0]
    r9 = q("SELECT is_emri_no, rev, is_emri, durum, pdf_yolu, ekler FROM revizyonlar WHERE gonderen = %s ORDER BY id DESC LIMIT 1", BAYI)[0]
    ok(i9b["sonuc"]["eylem"] == "is_emri" and i9b["cikarim"]["meta"]["backend"] == "etkilesim" and i9b["sonuc"]["cizim"]["motor"] == "genel"
       and i9b["sonuc"]["cizim"]["passed"] is True, f"iş: is_emri, genel motor geçti (perspektif {i9b['sonuc']['cizim'].get('perspektif')}, {i9b['sonuc']['cizim'].get('sure_s')} s)")
    ok(r9["rev"] == 1 and r9["durum"] == "onay_bekliyor" and r9["is_emri"]["yapi"]["sistem"] == "celik" and r9["is_emri"]["yapi"]["tanim"] == "modeller/C8801K.json"
       and "mahaller" not in r9["is_emri"] and r9["is_emri"]["bilgi"]["bayi_telefonu"] == BAYI and "kunye" not in r9["is_emri"],
       "revizyon r01: zarf yapi.sistem celik, tanım gömülü değil, antet numarası bayi kartından (D-09)")
    ok(Path(r9["pdf_yolu"]).is_file() and Path(r9["pdf_yolu"]).name == "C8801K_pafta.pdf" and str(VERI / "projects") in r9["pdf_yolu"]
       and r9["ekler"]["gorsel"]["filename"] == "C8801K_bayi_gorsel.png" and r9["ekler"]["ifc"]["sema_hatasi"] == 0
       and (VERI / "yayin" / "3d" / r9["ekler"]["ucb"]["anahtar"] / "index.html").read_bytes() == Path(r9["ekler"]["ucb"]["dosya"]).read_bytes(),
       "pafta PDF ve bayi görseli data/projects altında; IFC şema 0; 3D sayfası genel motorun IFC'sinden, yayımlandı (İE-21)")
    import fitz
    with fitz.open(r9["pdf_yolu"]) as d9:
        s9w = [w[4] for w in d9[0].get_text("words")]
        ok(len(d9) == 2 and "TASLAK" in s9w and BAYI in s9w and "Deneme" in s9w, "PDF 2 sayfa; 1. sayfada TASLAK, antette bayinin adı ve kart numarası")
    k9b = q("SELECT kind, satir FROM giden WHERE mesaj_id = 'wamid.E2EC2' ORDER BY sira")
    ok([x["kind"] for x in k9b][:3] == ["interactive", "document", "interactive"] and k9b[1]["satir"]["filename"] == f"Portman_{r9['is_emri_no']}_r01.pdf"
       and sorted(b["reply"]["id"] for b in k9b[0]["satir"]["interactive"]["action"]["buttons"]) == sorted([f"o:{r9['is_emri_no']}:1", f"r:{r9['is_emri_no']}:1"])
       and k9b[2]["satir"]["interactive"]["action"]["parameters"]["url"] == r9["ekler"]["ucb"]["url"],
       "satırlar: Onayla/Revize et + bayi görseli, PDF Portman_<no>_r01.pdf adıyla, \"3D'yi aç\" düğmesi")
    say = gonder()
    t9 = sahte.tipler()[-(say.get("kabul_edildi") or 0) * 2:]
    ok(say.get("kabul_edildi") >= 2 and "interactive/button" in t9 and "document" in t9, f"Meta: bayi görseli + düğmeler ve PDF gitti ({t9})")
    ok(BAYI not in json.dumps(i9b["sonuc"]) and q("SELECT durum, secilen_kod FROM secenek_setleri WHERE id = %s", s9["id"])[0]["secilen_kod"] == "Ç8801K",
       "iş sonucunda ham numara yok; set seçildi olarak kapandı")

    print("10) İE-08 A4: serbest metin revizyon → r02 aynı projede (önce–sonra görseli) → belirsiz cümle → görselli '1 / 2 / Hiçbiri' → düğme 2 → r03")
    time.sleep(1.2)
    kod, c = webhook(yuk([metin(BAYI, "mutfak penceresi 120x120 olsun", mid="wamid.E2ER1")]))
    hazir_ekle("wamid.E2ER1", {"niyet": "revizyon", "guven": "yuksek", "ozet": "mutfak penceresi 120x120",
                               "pencereler": [{"mahal": "mutfak", "olcu": "120x120", "islem": "degistir"}]})
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: serbest metin revizyonu işlendi (gerçek genel motor)")
    i10 = q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2ER1'")[0]["sonuc"]
    rv = q("SELECT proje_id, rev, durum, is_emri, ekler, is_emri_no FROM revizyonlar WHERE gonderen = %s ORDER BY id DESC LIMIT 2", BAYI)
    y10 = rv[0]["is_emri"]["yapi"]
    ok(i10["eylem"] == "is_emri" and rv[0]["rev"] == 2 and rv[0]["proje_id"] == rv[1]["proje_id"] and rv[1]["durum"] == "yerini_aldi"
       and [(d["op"], d["aciklik"], d["en"], d["yuk"]) for d in y10["degisiklikler"]] == [("pencere_olcu", "P5", 120, 120)],
       f"r02 aynı projede; değişiklik zarfta ({i10.get('gerekce')})")
    g10 = rv[0]["ekler"].get("gorsel") or {}
    t10 = json.loads((Path(g10.get("file", "/yok")).parent / "tanim.json").read_text(encoding="utf-8")) if g10.get("file") else {}
    ok(g10.get("kaynak") == "once_sonra" and Path(g10["file"]).is_file() and Path(g10["file"]).stat().st_size <= 5 * 1024 * 1024
       and next((a["etiket"] for a in t10.get("acikliklar", []) if a["ad"] == "P5"), None) == "120/120",
       f"başlık görseli önce–sonra (perspektif {i10['cizim'].get('perspektif')}); çizilen tanımda P5 120/120")
    k10 = q("SELECT kind, satir FROM giden WHERE mesaj_id = 'wamid.E2ER1' ORDER BY sira")
    ok([x["kind"] for x in k10][:2] == ["interactive", "document"] and k10[0]["satir"]["file"].endswith("_once_sonra.png")
       and k10[1]["satir"]["filename"] == f"Portman_{rv[0]['is_emri_no']}_r02.pdf", "satırlar: önce–sonra görselli Onayla/Revize et + PDF r02")
    say = gonder()
    t10 = sahte.tipler()[-(say.get("kabul_edildi") or 0) * 2:]                    # her dosyalı satır önce medya yükler
    ok(say.get("kabul_edildi", 0) >= 2 and "interactive/button" in t10 and "document" in t10, f"Meta: önce–sonra görseli + düğmeler ve PDF gitti ({t10})")
    time.sleep(1.2)
    kod, c = webhook(yuk([metin(BAYI, "salondaki sol taraftaki pencere 120x180 olsun", mid="wamid.E2ER2")]))
    hazir_ekle("wamid.E2ER2", {"niyet": "revizyon", "guven": "yuksek", "ozet": "salonun sol penceresi 120x180",
                               "pencereler": [{"mahal": "salon", "olcu": "120x180", "duvar": "sol", "islem": "degistir"}]})
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0 and q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2ER2'")[0]["sonuc"]["eylem"] == "sor",
       "belirsiz cümle: soru (okuma), çizim yok")
    k11 = q("SELECT satir FROM giden WHERE mesaj_id = 'wamid.E2ER2' ORDER BY sira")[0]["satir"]
    ok([b["reply"]["id"] for b in k11["interactive"]["action"]["buttons"]] == ["q:okuma:1", "q:okuma:2", "q:okuma:0"] and k11["file"].endswith("_okuma.png")
       and Path(k11["file"]).is_file(), "görselli '1 / 2 / Hiçbiri' (iki okuma numaralı tek görselde)")
    say = gonder()
    okuma_wamid = q("SELECT dis_id FROM giden WHERE mesaj_id = 'wamid.E2ER2' ORDER BY sira")[0]["dis_id"]
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(BAYI, "q:okuma:2", "2", okuma_wamid, mid="wamid.E2ER3")]))
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: '2' düğmesi işlendi (LLM'siz)")
    i12 = q("SELECT sonuc, cikarim FROM isler WHERE mesaj_id = 'wamid.E2ER3'")[0]
    r12 = q("SELECT rev, is_emri FROM revizyonlar WHERE gonderen = %s ORDER BY id DESC LIMIT 1", BAYI)[0]
    ok(i12["sonuc"]["eylem"] == "is_emri" and i12["cikarim"]["meta"]["backend"] == "etkilesim" and r12["rev"] == 3
       and [(d["aciklik"], d["en"], d["yuk"]) for d in r12["is_emri"]["yapi"]["degisiklikler"]] == [("P5", 120, 120), ("P4", 120, 180)],
       "r03: seçilen okuma (P4 120/180) önceki değişikliğin üstüne birikti")
    d12, _ = depo.konusma_oku(BAYI)
    ok(d12["revizyon"] == 2 and BAYI not in json.dumps(i12["sonuc"]) and q("SELECT durum FROM sorular WHERE gonderen = %s ORDER BY id DESC LIMIT 1", BAYI)[0]["durum"] == "cevaplandi",
       "sayaç 2 (r03), soru cevaplandı, iş sonucunda ham numara yok")

    print("11) İE-08 8b: bayi r03'ü onaylar → mühendise şablon → Gönder → görsel, PDF, Excel, DXF → Patron'a gönder → Patron şablonu; panel tablosu")
    MUH = "900000000303"                                                                         # gerçek olmayan deneme numarası
    depo.bayi_yaz(MUH, ad="Deneme Mühendis", rol="muhendis")
    AY.yaz(VERI, "mode", "kayitli")
    for a11, d11 in (("sablon_muhendis_kontrol", "portman_muhendis_kontrol_v1"), ("sablon_muhendis_hatirlatma", "portman_hatirlatma_v1")):
        AY.yaz(VERI, a11, d11)
    gonder()                                                                                       # r03 bayiye gider (onay ona bağlanır)
    no11 = q("SELECT is_emri_no FROM revizyonlar WHERE gonderen = %s ORDER BY id DESC LIMIT 1", BAYI)[0]["is_emri_no"]
    r03_wamid = q("SELECT dis_id FROM giden WHERE mesaj_id = 'wamid.E2ER3' AND kind = 'interactive'")[0]["dis_id"]
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(BAYI, f"o:{no11}:3", "Onayla", r03_wamid, mid="wamid.E2EM1")]))
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: bayinin Onayla düğmesi işlendi")
    k11 = q("SELECT durum, muhendis, bayi, onay_mesaj_id FROM muhendis_kontrolleri")
    rv11 = q("SELECT durum, ekler FROM revizyonlar WHERE is_emri_no = %s AND rev = 3", no11)[0]
    ok(len(k11) == 1 and k11[0]["durum"] == "bekliyor" and k11[0]["muhendis"] == MUH and k11[0]["onay_mesaj_id"] == "wamid.E2EM1" and rv11["durum"] == "onaylandi",
       "kontrol kaydı açıldı (mühendiste), revizyon onaylandı")
    ok(Path(rv11["ekler"]["excel"]["dosya"]).is_file() and rv11["ekler"]["excel"]["dosya"].endswith("_r03_yukleme_listesi.xlsx") and Path(rv11["ekler"]["dxf"]["dosya"]).is_file(),
       "r03'ün Excel'i sunucuda (gerçek genel motorun listesinden; D-17) ve DXF'i klasörde")
    b11 = q("SELECT alici, kind, govde FROM giden WHERE mesaj_id = 'wamid.E2EM1' ORDER BY sira")
    ok(b11[0]["alici"] == BAYI and b11[0]["govde"].endswith("Plan teknik kontrole gönderildi; sonucu size bildireceğiz.")
       and [(x["alici"], x["kind"]) for x in b11[1:]] == [("MUHENDIS", "template")], "bayiye 'teknik kontrole gönderildi'; mühendise şablon satırı")
    say = gonder()
    m11 = [y for y in sahte.gidenler() if y["to"] == MUH]
    ok(say.get("kabul_edildi") == 2 and len(m11) == 1 and m11[0]["template"]["name"] == "portman_muhendis_kontrol_v1"
       and m11[0]["template"]["components"][0]["parameters"] == [{"type": "text", "text": no11}, {"type": "text", "text": "r03"}],
       "Meta: mühendis kartına şablon (iş no, r03) ve Gönder düğmesi")
    sab_wamid = q("SELECT dis_id FROM giden WHERE mesaj_id = 'wamid.E2EM1' AND alici = 'MUHENDIS'")[0]["dis_id"]
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(MUH, f"muh:gonder:{no11}:3", "Gönder", sab_wamid, mid="wamid.E2EM2")]))
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0 and q("SELECT cikarim FROM isler WHERE mesaj_id = 'wamid.E2EM2'")[0]["cikarim"] is None,
       "ajan: mühendisin Gönder düğmesi (LLM'siz)")
    say = gonder()
    m11b = [y for y in sahte.gidenler() if y["to"] == MUH][1:]
    belge11 = [y["document"]["filename"] for y in m11b if y["type"] == "document"]
    ok(say.get("kabul_edildi") == 5 and [y["type"] for y in m11b] == ["image", "document", "document", "document", "interactive"]
       and belge11 == [f"Portman_{no11}_r03.pdf", f"Portman_{no11}_r03_yukleme_listesi.xlsx", f"Portman_{no11}_r03.dxf"],
       f"Meta: mühendise görsel, TASLAK pafta, Excel, DXF ve iki düğme ({belge11})")
    dug_wamid = q("SELECT dis_id FROM giden WHERE mesaj_id = 'wamid.E2EM2' AND kind = 'interactive'")[0]["dis_id"]
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(MUH, f"muh:patron:{no11}:3", "Patron'a gönder", dug_wamid, mid="wamid.E2EM3")]))
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: mühendisin 'Patron'a gönder' düğmesi")
    say = gonder()
    p11 = q("SELECT kind, durum, hata FROM giden WHERE mesaj_id = 'wamid.E2EM3' AND alici = 'PATRON' ORDER BY sira")
    son11 = [y for y in sahte.gidenler() if y["to"] == PATRON][-1]
    ok([x["kind"] for x in p11] == ["text", "template", "document"] and p11[1]["durum"] == "kabul_edildi" and son11["template"]["name"] == "portman_patron_bekliyor_v1"
       and son11["template"]["components"][0]["parameters"] == [{"type": "text", "text": "TSTA"}, {"type": "text", "text": no11}],
       "Patron'a 'mühendis onayladı, fiyat sizde': penceresi kapalı → şablon gitti (bayi kodu, iş no)")
    ok(q("SELECT durum, patron_durum FROM muhendis_kontrolleri")[0] == {"durum": "patrona_gonderildi", "patron_durum": "bekliyor"}
       and MUH not in json.dumps(q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2EM3'")[0]["sonuc"]), "kontrol: Patron'a gönderildi, fiyat bekleniyor; iş sonucunda numara yok")
    kod, body, _ = istek(app_pn, "GET", "/panel/", cerez=cerez)
    ok(kod == 200 and "Mühendis kontrolleri".encode() in body and "fiyat bekleniyor".encode() in body, "panel: mühendis kontrolleri tablosu ve Fiyat verildi düğmesi")

    print("12) İE-14 r3: '95 m² 3+1 tek kat çelik' (bankada 3+1 yok) → 'hazırlıyorum' → üretim (LLM'siz: program → uyarlama/çözücü) → iki "
          "yeni plan + bankadan en yakını tek görselde → '1. Yeni plan' → r01 gerçek genel motordan, tanım zarfta gömülü; plan_uretimleri "
          "kaydı ve doğrulama raporu")
    for kod12 in ("Ç8201", "KT01", "KT02", "KT03"):
        depo.aday_yaz(kod12, "gecerli", referans_model=kod12, muhendis_kabulu={"kim": "e2e", "tarih": "2026-10-14", "not": ""})
    hazir12 = tmp / "plan_hazir.json"                    # manuel arka uç: yapısal talepte LLM gerekmez; kayıt yalnız güvenlik için boş
    hazir12.write_text(json.dumps({"uretim": {"program": None, "yeniden": []}}, ensure_ascii=False), encoding="utf-8")
    AY.yaz(VERI, "plan_uretimi", {"acik": True, "backend": "manuel", "hazir_dosya": str(hazir12)})
    t12 = time.time()
    time.sleep(1.2)
    kod, c = webhook(yuk([metin(BAYI, "95 m² 3+1 tek kat çelik, kırma çatı", mid="wamid.E2EP1")]))
    hazir_ekle("wamid.E2EP1", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "95 m² 3+1 tek kat çelik, kırma çatı", "alan_m2": 95,
                               "oda_programi": "3+1", "yapi_turu": "celik", "kat_sayisi": 1, "cati": {"tip": "kirma"}})
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: '95 m² 3+1 tek kat çelik' işlendi")
    i12 = q("SELECT sonuc, cikarim FROM isler WHERE mesaj_id = 'wamid.E2EP1'")[0]
    s12 = q("SELECT id, adaylar FROM secenek_setleri ORDER BY olusturuldu DESC LIMIT 1")[0]
    yeni12 = s12["adaylar"][0]["kod"]
    pu12a = i12["cikarim"]["plan_uretimi"]
    ok(i12["sonuc"]["eylem"] == "secenek" and yeni12.startswith("YENI-") and s12["adaylar"][1]["kod"].startswith("YENI-")
       and [a["kod"] for a in s12["adaylar"][2:]] == ["KT03"] and pu12a["durum"] == "gecerli" and len(pu12a["adaylar"]) == 2 and pu12a["cagri"] == 0,
       f"seçenek seti: iki yeni plan + KT03; üretim LLM'siz ({pu12a.get('yol')}, {pu12a.get('sure_ms')} ms), iş satırında")
    ok(time.time() - t12 < 180, f"K5 (ölçüm): talepten seçenek görseline {time.time() - t12:.0f} s (gerçek genel motorla iki kart)")
    k12 = q("SELECT kind, govde, satir FROM giden WHERE mesaj_id = 'wamid.E2EP1' ORDER BY olusturuldu, sira")   # gönderim sırası (erken satır önce)
    ok([x["kind"] for x in k12] == ["text", "interactive"] and "hazırlıyorum" in k12[0]["govde"] and Path(k12[1]["satir"]["file"]).is_file()
       and k12[1]["satir"]["interactive"]["action"]["buttons"][0]["reply"]["title"] == "1. Yeni plan", "önce 'hazırlıyorum', sonra görselli 3 düğmeli set")
    say = gonder()
    ok(say.get("kabul_edildi") == 2 and sahte.gidenler()[-1]["type"] == "interactive", "Meta: metin + seçenek görseli gitti")
    set12 = q("SELECT dis_id FROM giden WHERE mesaj_id = 'wamid.E2EP1' AND kind = 'interactive'")[0]["dis_id"]
    time.sleep(1.2)
    kod, c = webhook(yuk([buton(BAYI, f"s:{s12['id']}:{yeni12}", "1. Yeni plan", set12, mid="wamid.E2EP2")]))
    ok(c.get("mesaj") == {"sahiplenildi": 1} and ajan() == 0, "ajan: 'Yeni plan' düğmesi işlendi (gerçek genel motor)")
    i12b = q("SELECT sonuc FROM isler WHERE mesaj_id = 'wamid.E2EP2'")[0]["sonuc"]
    r12 = q("SELECT is_emri_no, rev, is_emri, durum, pdf_yolu, ekler FROM revizyonlar WHERE gonderen = %s ORDER BY id DESC LIMIT 1", BAYI)[0]
    y12 = r12["is_emri"]["yapi"]
    ok(i12b["eylem"] == "is_emri" and i12b["cizim"]["passed"] is True and r12["rev"] == 1 and isinstance(y12["tanim"], dict) and y12["kod"] == yeni12,
       f"r01 genel motordan geçti, tanım zarfta gömülü ({i12b['cizim'].get('sure_s')} s)")
    with fitz.open(r12["pdf_yolu"]) as d12:
        ok(len(d12) == 2 and "TASLAK" in [w[4] for w in d12[0].get_text("words")], "pafta PDF 2 sayfa, TASLAK")
    pu12 = q("SELECT durum, plan_kodu, is_emri_no, cagri, yol, adaylar FROM plan_uretimleri")
    ok(len(pu12) == 1 and pu12[0]["plan_kodu"] == yeni12 and pu12[0]["is_emri_no"] == r12["is_emri_no"] and pu12[0]["cagri"] == 0,
       "plan_uretimleri: üretim kaydı, r01'e bağlandı (ücretli çağrı 0)")
    dg12 = pu12[0]["adaylar"][0]["dogrulama"]
    ok(dg12["kalemler"]["cizim"]["durum"] == "GECTI" and dg12["kalemler"]["geometri"]["durum"] == "GECTI"
       and dg12["kalemler"]["yukleme_listesi"]["durum"] == "DOGRULANMADI" and dg12["kalemler"]["yapisal"]["durum"] == "YAPILMADI",
       f"doğrulama raporu (gerçek motor): {dg12['ozet']}")
    say = gonder()
    ok(say.get("kabul_edildi") >= 2, "Meta: yeni planın bayi görseli + düğmeler ve PDF gitti")
finally:
    with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {dbad} WITH (FORCE)")
print(f"\n{sum(sonuc)}/{len(sonuc)} geçti — geçici dizin: {tmp}")
sys.exit(0 if sonuc and all(sonuc) else 1)
