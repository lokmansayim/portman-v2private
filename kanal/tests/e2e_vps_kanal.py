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
    ok(rev["ekler"]["ifc"]["sema_hatasi"] == 0 and rev["ekler"]["ucb"]["url"] == f"https://ornek.invalid/portman/3d/{no}/r01/", "Postgres: ekler (IFC şema 0, 3D url)")
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
    ok(g[2]["interactive"]["action"]["parameters"]["url"].endswith(f"/{no}/r01/") and g[1]["document"]["id"] == "1002", "bağlantı butonu 3D url; PDF medya kimliğiyle")
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
finally:
    with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {dbad} WITH (FORCE)")
print(f"\n{sum(sonuc)}/{len(sonuc)} geçti — geçici dizin: {tmp}")
sys.exit(0 if sonuc and all(sonuc) else 1)
