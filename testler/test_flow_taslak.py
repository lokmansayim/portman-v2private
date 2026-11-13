"""İE-20 · vps/flow_taslak.py: talep ve revizyon formunu Meta'da taslak kuran betik, yerel sahte Graph sunucusuyla (ağ, Meta, WhatsApp yok).

Denenen: ilk koşu iki taslak kurar (publish false, /publish yok, flow_json depodaki formun aynısı); ikinci koşu taslağın JSON'unu
/assets ile günceller (yeni form kurmaz); yayımlanmış forma dokunmaz; --bak hiçbir şey kurmaz; Meta doğrulama hatası çıkış 2; belirteç
çıktıya girmez (hata iletisi dahil); WABA kimliği belirtecin kapsamından, birden çoksa durur; Mac'teki gibi stdin'den koşar; --yayimla
iki form hazırsa ikisini yayımlar, değilse hiçbirini, gönderilemeyen formda çıkış 1."""
from __future__ import annotations

import hashlib
import http.server
import json
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
BETIK = KOK / "vps" / "flow_taslak.py"
BELIRTEC = "EAAB" + "x" * 80
WABA = "777000111"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
sys.path.insert(0, str(KOK / "kanal"))
import talep_formu as TF  # noqa: E402


class SahteGraph:
    """Graph API'nin Flows uçları: debug_token, /<waba>/flows (GET, POST), /<flow>/assets (POST), /<flow> (GET)."""

    def __init__(self, kapsam=None, dogrulama=None, hata_mesaji=None, numaralar=None, isletme=None, saglik="AVAILABLE", yayim_hatasi=None):
        self.istekler, self.formlar, self.sayac = [], {}, 0
        self.saglik, self.yayim_hatasi = saglik, yayim_hatasi   # health_status.can_send_message · /publish'in hata iletisi
        self.numaralar = numaralar or {}                 # WABA → telefon numarası kimlikleri
        self.isletme = isletme or {}                     # işletme → sahip olduğu WABA'lar
        self.depo = {}                                   # --kaynak: commit'teki formlar
        self.kapsam = kapsam if kapsam is not None else [{"scope": "whatsapp_business_management", "target_ids": [WABA]},
                                                          {"scope": "whatsapp_business_messaging", "target_ids": [WABA]}]
        self.dogrulama = dogrulama or []
        self.hata_mesaji = hata_mesaji
        s = self

        class H(http.server.BaseHTTPRequestHandler):
            def _cevap(self, kod, veri):
                b = json.dumps(veri).encode()
                self.send_response(kod); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

            def _isle(self):
                n = int(self.headers.get("Content-Length") or 0)
                govde = self.rfile.read(n) if n else b""
                u = urllib.parse.urlsplit(self.path)
                yol, q = (u.path if u.path.startswith("/raw/") else u.path.removeprefix("/v23.0/")), dict(urllib.parse.parse_qsl(u.query))
                s.istekler.append({"m": self.command, "yol": yol, "q": q, "h": {k.lower(): v for k, v in self.headers.items()}, "govde": govde})
                if yol.startswith("/raw/"):                      # raw.githubusercontent.com yerine: /raw/<commit>/kanal/formlar/<tur>.json
                    parca = yol.split("/")
                    if len(parca) == 6 and parca[2] == COMMIT and parca[3:5] == ["kanal", "formlar"]:
                        return self._cevap(200, s.depo.get(parca[5].removesuffix(".json")) or {})
                    return self._cevap(404, {})
                if s.hata_mesaji:
                    return self._cevap(400, {"error": {"message": s.hata_mesaji, "type": "OAuthException", "code": 100}})
                if yol == "debug_token":
                    return self._cevap(200, {"data": {"is_valid": True, "type": "SYSTEM_USER", "expires_at": 0,
                                                      "scopes": [k["scope"] for k in s.kapsam] or ["business_management"],
                                                      "granular_scopes": s.kapsam}})
                if yol.endswith("/phone_numbers"):
                    return self._cevap(200, {"data": [{"id": n} for n in s.numaralar.get(yol.split("/")[0], [])]})
                if yol.endswith("/owned_whatsapp_business_accounts"):
                    return self._cevap(200, {"data": [{"id": w} for w in s.isletme.get(yol.split("/")[0], [])]})
                if yol.endswith("/client_whatsapp_business_accounts"):
                    return self._cevap(200, {"data": []})
                if yol == f"{WABA}/flows" and self.command == "GET":
                    return self._cevap(200, {"data": [{"id": i, "name": f["name"], "status": f["status"], "categories": ["OTHER"],
                                                       "validation_errors": []} for i, f in s.formlar.items()], "paging": {"cursors": {}}})
                if yol == f"{WABA}/flows" and self.command == "POST":
                    g = json.loads(govde)
                    s.sayac += 1
                    fid = f"9100{s.sayac}"
                    s.formlar[fid] = {"name": g["name"], "status": "DRAFT", "json": g["flow_json"]}
                    return self._cevap(200, {"id": fid, "success": True, "validation_errors": s.dogrulama})
                if yol.endswith("/assets") and self.command == "POST":
                    fid = yol.split("/")[0]
                    s.formlar[fid]["json"] = govde
                    return self._cevap(200, {"success": True, "validation_errors": []})
                if yol.endswith("/publish") and self.command == "POST":
                    fid = yol.split("/")[0]
                    if s.yayim_hatasi:
                        return self._cevap(400, {"error": {"message": s.yayim_hatasi, "code": 139001}})
                    s.formlar[fid]["status"] = "PUBLISHED"
                    return self._cevap(200, {"success": True})
                if yol in s.formlar and self.command == "GET":
                    f = s.formlar[yol]
                    if "health_status" in q.get("fields", ""):
                        hatalar = [{"error_code": 131000, "error_description": "app_check: You need to connect a Meta app to the flow",
                                    "possible_solution": "Connect an app"}] if s.saglik == "BLOCKED" else []
                        return self._cevap(200, {"id": yol, "status": f["status"], "health_status": {
                            "can_send_message": s.saglik, "entities": [{"entity_type": "FLOW", "id": yol, "can_send_message": s.saglik,
                                                                         "errors": hatalar}]}})
                    return self._cevap(200, {"id": yol, "name": f["name"], "status": f["status"], "json_version": "7.3",
                                             "validation_errors": s.dogrulama,
                                             "preview": {"preview_url": f"https://business.facebook.com/wa/manage/flows/{yol}/preview/?token=onz",
                                                         "expires_at": "2026-12-12T10:00:00+0000"}})
                return self._cevap(404, {"error": {"message": "yok", "code": 803}})

            do_GET = do_POST = _isle

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v23.0"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def kapat(self):
        self.httpd.shutdown()


@pytest.fixture
def etc(tmp_path):
    d = tmp_path / "etc"; d.mkdir()
    (d / "whatsapp.env").write_text(f"WA_PHONE_NUMBER_ID=12345\nWA_ACCESS_TOKEN={BELIRTEC}\nWA_GRAPH_VERSION=v23.0\n")
    return d


def kos(etc: Path, graph: SahteGraph, *arg, stdin: bool = False) -> subprocess.CompletedProcess:
    env = {"PM_ETC": str(etc), "PM_GRAPH_BASE": graph.url, "PM_RAW_BASE": graph.url.removesuffix("/v23.0") + "/raw", "PATH": "/usr/bin:/bin"}
    if stdin:
        return subprocess.run([sys.executable, "-", "--kok", str(KOK), *arg], input=BETIK.read_text(), env=env, capture_output=True,
                              text=True, timeout=60)
    return subprocess.run([sys.executable, str(BETIK), *arg], env=env, capture_output=True, text=True, timeout=60)


def _yazma_istekleri(g: SahteGraph) -> list[dict]:
    return [i for i in g.istekler if i["m"] != "GET"]


def test_ilk_kosu_iki_taslak_kurar_yayimlamaz(etc):
    g = SahteGraph()
    try:
        r = kos(etc, g)
        assert r.returncode == 0, r.stdout + r.stderr
        cikti = r.stdout + r.stderr
        assert BELIRTEC not in cikti and "parmak izi " + hashlib.sha256(BELIRTEC.encode()).hexdigest()[:12] in cikti
        assert f"WABA) {WABA} (belirtecin kapsamından)" in cikti and "tür SYSTEM_USER" in cikti and "süre süresiz" in cikti
        olustur = [i for i in g.istekler if i["m"] == "POST" and i["yol"] == f"{WABA}/flows"]
        assert len(olustur) == 2 and len(_yazma_istekleri(g)) == 2
        for i, tur in zip(olustur, ("talep", "revizyon")):
            govde = json.loads(i["govde"])
            assert govde["name"] == {"talep": "Portman Talep Formu", "revizyon": "Portman Revizyon Formu"}[tur]
            assert govde["publish"] is False and govde["categories"] == ["OTHER"]
            assert json.loads(govde["flow_json"]) == TF.tanim(tur)
        assert not any(i["yol"].endswith("/publish") for i in g.istekler)
        assert all(i["h"].get("authorization") == "Bearer " + BELIRTEC for i in g.istekler)
        # belirteç yalnız debug_token'ın sorgusunda; başka hiçbir sorguda yok
        assert all(BELIRTEC not in json.dumps(i["q"]) for i in g.istekler if i["yol"] != "debug_token")
        assert "yeni taslak kuruldu" in cikti and cikti.count("durum DRAFT") == 2 and "Meta doğrulama hatası 0" in cikti
        assert "talep_flow_id 91001 · revizyon_flow_id 91002" in cikti
        assert "mesaj gönderilmedi · form yayımlanmadı" in cikti and "== sonuç: tamam" in cikti
        # etkileşimli önizleme: canlı kodun yeni bayiye sunduğu veriyle açılır
        link = next(s.strip() for s in r.stdout.splitlines() if "interactive=true" in s and "91001" in s)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(link).query))
        assert q["token"] == "onz" and q["flow_action"] == "navigate"
        assert json.loads(q["flow_action_payload"]) == {"screen": "TALEP", "data": TF.ekran_verisi(None, None)}
        link = next(s.strip() for s in r.stdout.splitlines() if "interactive=true" in s and "91002" in s)
        yuk = json.loads(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(link).query))["flow_action_payload"])
        assert yuk["screen"] == "REVIZYON" and set(yuk["data"]) == set(TF.tanim("revizyon")["screens"][0]["data"])
    finally:
        g.kapat()


def test_ikinci_kosu_taslagi_gunceller_yeni_form_kurmaz(etc):
    g = SahteGraph()
    try:
        assert kos(etc, g).returncode == 0
        g.istekler.clear()
        r = kos(etc, g)
        assert r.returncode == 0, r.stdout + r.stderr
        yaz = _yazma_istekleri(g)
        assert [i["yol"] for i in yaz] == ["91001/assets", "91002/assets"]
        for i, tur in zip(yaz, ("talep", "revizyon")):
            assert i["h"]["content-type"].startswith("multipart/form-data; boundary=")
            b = i["govde"]
            assert b'name="name"\r\n\r\nflow.json\r\n' in b and b'name="asset_type"\r\n\r\nFLOW_JSON\r\n' in b
            assert b'name="file"; filename="flow.json"' in b
            icerik = b.split(b'filename="flow.json"\r\nContent-Type: application/json\r\n\r\n', 1)[1].rsplit(b"\r\n--", 1)[0]
            assert json.loads(icerik) == TF.tanim(tur)
        assert r.stdout.count("taslak vardı; JSON'u sürümdeki formla güncellendi") == 2 and len(g.formlar) == 2
    finally:
        g.kapat()


def test_yayimlanmis_forma_dokunmaz_bak_kipi_hicbir_sey_kurmaz(etc):
    g = SahteGraph()
    try:
        g.formlar["91009"] = {"name": "Portman Talep Formu", "status": "PUBLISHED", "json": "{}"}
        r = kos(etc, g, "--bak")
        assert r.returncode == 0, r.stdout + r.stderr
        assert _yazma_istekleri(g) == []
        assert "durum PUBLISHED: yayımlanmış form değiştirilemez; dokunulmadı" in r.stdout and "yok; --bak: kurulmadı" in r.stdout
        r = kos(etc, g)
        assert [i["yol"] for i in _yazma_istekleri(g)] == [f"{WABA}/flows"]          # yalnız revizyon kuruldu; yayımlanmışa dokunulmadı
        assert json.loads(_yazma_istekleri(g)[0]["govde"])["name"] == "Portman Revizyon Formu"
    finally:
        g.kapat()


def test_meta_dogrulama_hatasi_cikis_2(etc):
    g = SahteGraph(dogrulama=[{"error": "INVALID_PROPERTY_VALUE", "message": "init-value boş olamaz", "line_start": 12,
                               "pointers": [{"path": "screens[0].layout"}]}])
    try:
        r = kos(etc, g)
        assert r.returncode == 2 and "Meta doğrulama hatası 1" in r.stdout and "init-value boş olamaz" in r.stdout
        assert "== sonuç: Meta doğrulama hatası var" in r.stdout
    finally:
        g.kapat()


def test_belirtec_hata_iletisinde_de_yazilmaz(etc):
    g = SahteGraph(hata_mesaji=f"Invalid OAuth access token - Cannot parse access token {BELIRTEC}")
    try:
        r = kos(etc, g)
        assert r.returncode == 1 and BELIRTEC not in r.stdout + r.stderr and "<belirteç>" in r.stdout and "HTTP 400" in r.stdout
    finally:
        g.kapat()


def test_waba_kimligi_kapsamdan_durur_ya_da_secilir(etc, tmp_path):
    iki = [{"scope": "whatsapp_business_management", "target_ids": [WABA, "777000222"]}]
    g = SahteGraph(kapsam=iki)                           # iki hesap, numara hiçbirinde değil: durur
    try:
        r = kos(etc, g)
        assert r.returncode == 1 and "birden çok WhatsApp hesabını" in r.stdout and _yazma_istekleri(g) == []
        r = kos(etc, g, "--waba", WABA)
        assert r.returncode == 0 and "(komut satırından)" in r.stdout
        assert kos(etc, g, "--waba", "12;rm").returncode == 1
    finally:
        g.kapat()
    g = SahteGraph(kapsam=iki, numaralar={WABA: ["12345"], "777000222": ["99999"]})   # kanalın numarası (12345) WABA'da
    try:
        r = kos(etc, g)
        assert r.returncode == 0 and f"WABA) {WABA} (kanalın numarasının bağlı olduğu hesap)" in r.stdout
    finally:
        g.kapat()
    g = SahteGraph(kapsam=[{"scope": "whatsapp_business_management"}, {"scope": "business_management", "target_ids": ["555000999"]}],
                   isletme={"555000999": [WABA]})        # belirteç bütün varlıklara açık: işletmenin hesabı
    try:
        r = kos(etc, g)
        assert r.returncode == 0 and f"WABA) {WABA} (işletmenin WhatsApp hesaplarından)" in r.stdout
    finally:
        g.kapat()
    g = SahteGraph(kapsam=[])
    try:
        r = kos(etc, g)
        assert r.returncode == 1 and "whatsapp_business_management izni yok" in r.stdout
    finally:
        g.kapat()
    bos = tmp_path / "bos"; bos.mkdir()
    r = kos(bos, g)
    assert r.returncode == 1 and "WA_ACCESS_TOKEN yok" in r.stdout


def test_mac_teki_gibi_stdin_den_kosar(etc):
    g = SahteGraph()
    try:
        r = kos(etc, g, stdin=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert f"formlar: {KOK}/kanal/formlar · talep Flow JSON 7.3 · revizyon Flow JSON 7.3" in r.stdout
        assert len([i for i in g.istekler if i["m"] == "POST"]) == 2
    finally:
        g.kapat()


def test_kaynak_commit_formlari_depodan_okur_taslagi_gunceller(etc):
    """Sürüm kurulmadan düzeltilmiş formu taslağa yüklemek (12 Kasım: Meta "max-length" tamsayı istedi)."""
    g = SahteGraph()
    try:
        g.formlar["91001"] = {"name": "Portman Talep Formu", "status": "DRAFT", "json": "{}"}
        g.formlar["91002"] = {"name": "Portman Revizyon Formu", "status": "DRAFT", "json": "{}"}
        g.depo = {t: {**TF.tanim(t), "_isaret": t} for t in ("talep", "revizyon")}
        r = kos(etc, g, "--kaynak", COMMIT, stdin=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert f"formlar: depo commit {COMMIT[:8]} (--kaynak)" in r.stdout
        raw = [i for i in g.istekler if i["yol"].startswith("/raw/")]
        assert len(raw) == 2 and all("authorization" not in i["h"] for i in raw)          # belirteç GitHub'a gitmez
        yaz = _yazma_istekleri(g)
        assert [i["yol"] for i in yaz] == ["91001/assets", "91002/assets"]
        for i, tur in zip(yaz, ("talep", "revizyon")):
            icerik = i["govde"].split(b'filename="flow.json"\r\nContent-Type: application/json\r\n\r\n', 1)[1].rsplit(b"\r\n--", 1)[0]
            assert json.loads(icerik)["_isaret"] == tur                                    # sunucudaki sürüm değil, commit'teki form
        assert kos(etc, g, "--kaynak", "main").returncode == 1                             # yalnız 40 haneli commit
        r = kos(etc, g, "--kaynak", "f" * 40)                                              # commit'te dosya yok: durur, Meta'ya yazmaz
        assert r.returncode == 1 and "formlar okunamadı" in r.stdout and len(_yazma_istekleri(g)) == 2
    finally:
        g.kapat()


def _yayim_istekleri(g: SahteGraph) -> list[str]:
    return [i["yol"] for i in g.istekler if i["m"] == "POST" and i["yol"].endswith("/publish")]


def test_yayimla_iki_formu_yayimlar_sonra_dokunmaz(etc):
    g = SahteGraph()
    try:
        assert kos(etc, g).returncode == 0                                   # önce iki taslak (bugünkü hâl)
        g.istekler.clear()
        r = kos(etc, g, "--yayimla")
        cikti = r.stdout + r.stderr
        assert r.returncode == 0, cikti
        assert [i["yol"] for i in _yazma_istekleri(g)] == ["91001/assets", "91002/assets", "91001/publish", "91002/publish"]
        assert {f["status"] for f in g.formlar.values()} == {"PUBLISHED"}
        alanlar = [i["q"]["fields"] for i in g.istekler if i["m"] == "GET" and "health_status" in i["q"].get("fields", "")]
        assert alanlar == ["id,status,health_status.phone_number(12345)"] * 2   # kanalın numarasıyla
        assert "talep formu yayımlandı · kimlik 91001 · durum PUBLISHED · gönderilebilirlik AVAILABLE" in cikti
        assert "talep formu yayımlandı · revizyon formu yayımlandı (geri alınmaz)" in cikti and "== sonuç: tamam" in cikti
        for i, tur in zip([i for i in g.istekler if i["yol"].endswith("/assets")], ("talep", "revizyon")):
            assert TF.tanim(tur) == json.loads(i["govde"].split(b'filename="flow.json"\r\nContent-Type: application/json\r\n\r\n', 1)[1]
                                         .rsplit(b"\r\n--", 1)[0])                 # yayımlanan = depodaki
        g.istekler.clear()
        r = kos(etc, g, "--yayimla")                                         # yeniden: yayımlanmışa dokunmaz
        assert r.returncode == 0 and not _yazma_istekleri(g), r.stdout
        assert "talep formu zaten yayımlıydı" in r.stdout and "== mesaj gönderilmedi · form yayımlanmadı" in r.stdout
    finally:
        g.kapat()


def test_yayimla_hazir_olmayan_formda_hicbirini_yayimlamaz(etc):
    g = SahteGraph(dogrulama=[{"error": "INVALID_PROPERTY_TYPE", "message": "max-length", "pointers": []}])
    try:
        r = kos(etc, g, "--yayimla")
        assert r.returncode == 2 and not _yayim_istekleri(g), r.stdout
        assert "YAYIMLANMADI (iki form da hazır olmalı)" in r.stdout and "form yayımlanmadı" in r.stdout
        assert {f["status"] for f in g.formlar.values()} == {"DRAFT"}
    finally:
        g.kapat()
    g = SahteGraph()
    try:
        r = kos(etc, g, "--yayimla", "--bak")
        assert r.returncode == 1 and not g.istekler and "DUR: --yayimla ve --bak birlikte olmaz" in r.stdout
    finally:
        g.kapat()


def test_yayimla_gonderilemeyen_ya_da_reddedilen_formda_cikis_1(etc):
    g = SahteGraph(saglik="BLOCKED")
    try:
        r = kos(etc, g, "--yayimla")
        assert r.returncode == 1, r.stdout                                   # ayarı açan komut `&&` ile koşmaz
        assert "gönderilebilirlik BLOCKED" in r.stdout and "! FLOW: app_check: You need to connect a Meta app" in r.stdout
        assert "== sonuç: durdu" in r.stdout
    finally:
        g.kapat()
    g = SahteGraph(yayim_hatasi=f"Flow cannot be published (token {BELIRTEC})")
    try:
        r = kos(etc, g, "--yayimla")
        cikti = r.stdout + r.stderr
        assert r.returncode == 1 and _yayim_istekleri(g) == ["91001/publish"], cikti   # ilki reddedilince ikincisi denenmez
        assert "talep formu: DURDU, yayımlanamadı (POST /<flow>/publish: HTTP 400" in cikti and BELIRTEC not in cikti
        assert "form yayımlanmadı" in cikti
    finally:
        g.kapat()
