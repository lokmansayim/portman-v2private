"""SAHTE hosting API (yalnız ajanın Python tarafını sınamak için). kanal/api.php + feature.php'nin ajanı ilgilendiren
davranışının bir kısmını Python'da taklit eder. GERÇEK PHP HATTININ DOĞRULAMASI DEĞİLDİR: gerçek hat
kanal/tests/baglanti_test.php, e2e_vps.py ve e2e_kalici.py (portman/lib.php ile, kapı B) ve canlı Patron denemesiyle
(kapı F, G) doğrulanır.

Taklit edilenler (api.php / feature.php'deki karşılığıyla):
  claim        worker/enabled denetimi; 600 sn'den eski 'processing' satırı 'failed' yapma (PM_KANAL_STALE, saat elle
               ilerletilebilir: self.saat); en eski 'queued' satır → 'processing', worker 'vps'.
  result       cikti/satirlar/sonuc biçimi; gelen satır 'processing' + worker 'vps' değilse 422 inbound_not_claimed_by_vps;
               yol, belge dosyası ve sha denetimi; satır kimliğiyle tekilleştirme; gelen satır done/failed.
  giden_durum  salt okunur; state, wamid, request_accepted_at, sent_at, delivery_state, delivered_at, attempts, error.
  tick/teslim  pending → accepted (wamid) ya da seçilen satırlar için uncertain / held / upload_failed; Meta durum
               bildirimi (sent/delivered/read/failed) delivery_events'e yazılır, durum yalnız ileri gider.
  hata         self.hatalar[op] = [(http_kodu, {"error": ...}), ...]: sıradaki çağrı bu cevabı alır (işlem yapılmaz).
               self.kopar[op] = n: sıradaki n çağrıda bağlantı cevapsız kapanır, işlem yapılmaz (ör. büyük gövdede sunucunun
               erken reddi istemciye bağlantı kopması olarak gelir).
Taklit EDİLMEYENLER (ayrım bilerek bırakıldı; gerçek PHP testleri ya da canlı denemede görülür):
  claim cevabındaki ham durum/<numara>.json metni (hep None); tick'te 24 saat penceresi, dry_run, PDF yüklemenin ikinci
  denemesi, Meta'ya gerçek istek; biz_opaque ile eşleşen geç bildirimin 'uncertain' satıra wamid yazması; state.json kilidi,
  dosya izinleri, api-audit, 401'de 1 sn bekleme, heartbeat/log içeriği; PHP'nin her istisnayı 422 döndürmesi (burada yalnız
  bilinen nedenler).
"""
from __future__ import annotations

import email.parser
import email.policy
import hashlib
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class SahteHosting:
    STALE = 600                                   # feature.php PM_KANAL_STALE

    def __init__(self, kok: Path, token: str, api: str = "kanal-api-v1.2", worker: str = "vps"):
        self.kok = Path(kok); self.kok.mkdir(parents=True, exist_ok=True)
        self.token, self.api, self.worker = token, api, worker
        self.enabled = True
        self.kayma = 0.0                          # hosting saatinin ileri alınması (sn): 600 sn'lik süpürmeyi sınamak için
        self.hatalar: dict[str, list[tuple[int, dict]]] = {}
        self.kopar: dict[str, int] = {}
        self.inbound: dict[str, dict] = {}
        self.outbound: dict[str, dict] = {}
        self.durum: dict[str, str] = {}
        self.cagri: list[str] = []
        self.result_sonrasi_kopar = 0          # >0: result işlenir ama istemciye cevap verilmez (bağlantı koptu)
        self.kilit = threading.Lock()
        self._n = 0
        self.sunucu = None

    # ── kuyruk (feature.php::pm_kanal_capture'ın yazdığı satır) ──
    def saat(self) -> int:
        return int(time.time() + self.kayma)

    def mesaj_gelir(self, g: dict) -> None:
        with self.kilit:
            if g["id"] not in self.inbound:          # PHP: aynı wamid ikinci satır açmaz
                self.inbound[g["id"]] = {**g, "state": "queued", "attempts": 0, "updated_at": self.saat()}

    def yeniden_sirala(self, mid: str) -> None:
        """Yönetici işlemi: işlenmiş bir mesajı kuyruğa geri koyar (aynı kanal mesajının yeniden işlenmesi)."""
        with self.kilit:
            self.inbound[mid].update(state="queued", updated_at=self.saat())

    # ── gönderim (feature.php::pm_kanal_tick) ve Meta durum bildirimi (pm_kanal_status) ──
    def tick(self, belirsiz: set[str] | None = None, tutulan: set[str] | None = None, yuklenemeyen: set[str] | None = None) -> None:
        with self.kilit:
            for rid, r in sorted(self.outbound.items(), key=lambda x: (x[1].get("created_at", 0), x[1].get("seq", 0))):
                if r["state"] != "pending":
                    continue
                if belirsiz and rid in belirsiz:
                    r.update(state="uncertain", attempts=1, error="Gönderim sonucu belirsiz; otomatik tekrar yok.")
                    continue
                if tutulan and rid in tutulan:
                    r.update(state="held", error="Gönderilmedi: reply_window_closed")
                    continue
                if yuklenemeyen and rid in yuklenemeyen:
                    r.update(state="upload_failed", attempts=r.get("attempts", 0) + (1 if r.get("kind") == "document" else 0),
                             error="Yükleme/doğrulama başarısız; gönderilmedi.")
                    continue
                self._n += 1
                r.update(state="accepted", wamid=f"wamid.HOST{self._n:04d}", request_accepted_at=self.saat(), attempts=1)

    def teslim(self, wamid: str, durum: str = "delivered", zaman: int | None = None) -> None:
        with self.kilit:
            for r in self.outbound.values():
                if r.get("wamid") == wamid:
                    ev = r.setdefault("delivery_events", {})
                    ev[f"{durum}{len(ev)}"] = {"status": durum, "timestamp": int(zaman or time.time())}
                    sira = {"accepted": 0, "sent": 1, "failed": 2, "delivered": 3, "read": 4}
                    if sira[durum] >= sira.get(r.get("delivery_state") or "accepted", 0):
                        r["delivery_state"] = durum; r["state"] = durum

    # ── API (api.php) ──
    def settings(self) -> dict:
        return {"api": self.api, "now": self.saat(), "enabled": self.enabled, "worker": self.worker, "dry_run": False, "mode": "patron",
                "llm": {"backend": "manuel"}, "patron_teknik_not": False, "poll_s": 1, "vps_komut": False, "package": None}

    def claim(self) -> dict:
        if not self.enabled:
            return {"job": None, "reason": "disabled"}
        if self.worker != "vps":
            return {"job": None, "reason": f"worker={self.worker}"}
        with self.kilit:
            simdi = self.saat()
            for r in self.inbound.values():               # api.php: takılı 'processing' → failed, otomatik tekrar yok
                if r["state"] == "processing" and r.get("updated_at", 0) < simdi - self.STALE:
                    r.update(state="failed", error="İşlem teyit edilmeden bitti; otomatik tekrar yok.", updated_at=simdi)
            aday = [r for r in self.inbound.values() if r["state"] == "queued"]
            if not aday:
                return {"job": None}
            r = min(aday, key=lambda x: (x.get("timestamp", 0), x.get("received_at", 0)))
            r.update(state="processing", attempts=r["attempts"] + 1, worker="vps", started_at=simdi, updated_at=simdi)
            return {"job": dict(r), "durum": None}

    def result(self, alanlar: dict, dosyalar: dict) -> dict:
        cikti = json.loads(alanlar.get("cikti") or "null")
        iid = alanlar.get("inbound_id") or ""
        if not isinstance(cikti, dict) or not isinstance(cikti.get("satirlar"), list) or not isinstance(cikti.get("sonuc"), dict) or not iid:
            raise ValueError("bad_result")
        with self.kilit:
            gelen = self.inbound.get(iid)
            if gelen is None:
                raise ValueError("inbound_unknown")
            if gelen["state"] != "processing" or gelen.get("worker") != "vps":
                raise ValueError("inbound_not_claimed_by_vps")
            yazilan = {}
            for alan, (ad, veri) in dosyalar.items():
                hedef = alanlar.get(f"path_{alan}") or ""
                if not re.fullmatch(r"projects/[A-Za-z0-9_.-]{1,80}/r[0-9]{2}/[A-Za-z0-9_.-]{1,120}", hedef) or ".." in hedef:
                    raise ValueError("bad_path")
                p = self.kok / hedef; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(veri); yazilan[hedef] = p
            for r in cikti["satirlar"]:
                if r.get("kind") == "document":
                    if r.get("file") not in yazilan:
                        raise ValueError("document_file_missing")
                    if r.get("sha256") and hashlib.sha256(yazilan[r["file"]].read_bytes()).hexdigest() != r["sha256"]:
                        raise ValueError("document_sha_mismatch")
                if r.get("inbound_id") != iid:
                    raise ValueError("row_inbound_mismatch")
            if alanlar.get("durum"):
                self.durum[gelen["sender"]] = alanlar["durum"]
            n = 0
            for r in cikti["satirlar"]:
                if r["id"] not in self.outbound:
                    self.outbound[r["id"]] = {**r, "state": "pending"}; n += 1
            gelen.update(state="failed" if cikti.get("hata") else "done", result=cikti.get("sonuc"), updated_at=self.saat(),
                         outbound_ids=[r["id"] for r in cikti["satirlar"]])
            return {"ok": True, "outbound": n, "files": len(yazilan)}

    def giden_durum(self, body: dict) -> dict:
        ids = [x for x in (body.get("ids") or []) if isinstance(x, str) and re.fullmatch(r"out_[0-9a-f]{24}", x)][:200]
        out = {}
        with self.kilit:
            for i in ids:
                r = self.outbound.get(i)
                if r is None:
                    continue
                olaylar = list((r.get("delivery_events") or {}).values())
                teslim = [e["timestamp"] for e in olaylar if e["status"] in ("delivered", "read")]
                gonderildi = [e["timestamp"] for e in olaylar if e["status"] in ("sent", "delivered", "read")]
                out[i] = {"state": r["state"], "wamid": r.get("wamid"), "request_accepted_at": r.get("request_accepted_at"),
                          "sent_at": min(gonderildi) if gonderildi else None,
                          "delivery_state": r.get("delivery_state"), "delivered_at": min(teslim) if teslim else None,
                          "attempts": r.get("attempts", 0), "error": r.get("error")}
        return {"satirlar": out, "now": int(time.time())}

    # ── HTTP ──
    def basla(self) -> str:
        hosting = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _yaz(self, kod: int, govde: dict):
                veri = json.dumps(govde, ensure_ascii=False).encode()
                self.send_response(kod); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(veri)))
                self.end_headers(); self.wfile.write(veri)

            def _isle(self):
                op = (parse_qs(urlparse(self.path).query).get("op") or [""])[0]
                hosting.cagri.append(op)
                govde = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if self.headers.get("X-Portman-Token") != hosting.token:
                    return self._yaz(401, {"error": "unauthorized"})
                with hosting.kilit:
                    enjekte = (hosting.hatalar.get(op) or [None]).pop(0) if hosting.hatalar.get(op) else None
                if enjekte is not None:
                    return self._yaz(*enjekte)
                with hosting.kilit:
                    kes = hosting.kopar.get(op, 0) > 0
                    if kes:
                        hosting.kopar[op] -= 1
                if kes:
                    self.close_connection = True
                    return
                try:
                    if op == "settings":
                        return self._yaz(200, hosting.settings())
                    if op == "claim":
                        return self._yaz(200, hosting.claim())
                    if op in ("heartbeat", "log"):
                        return self._yaz(200, {"ok": True, "n": len(json.loads(govde or b"{}").get("lines") or [])})
                    if op == "giden_durum":
                        return self._yaz(200, hosting.giden_durum(json.loads(govde or b"{}")))
                    if op == "result":
                        ctype = self.headers.get("Content-Type", "")
                        msg = email.parser.BytesParser(policy=email.policy.default).parsebytes(
                            f"Content-Type: {ctype}\r\n\r\n".encode() + govde)
                        alanlar, dosyalar = {}, {}
                        for parca in msg.iter_parts():
                            ad = parca.get_param("name", header="content-disposition")
                            if parca.get_filename():
                                dosyalar[ad] = (parca.get_filename(), parca.get_payload(decode=True))
                            else:
                                alanlar[ad] = parca.get_payload(decode=True).decode("utf-8")
                        sonuc = hosting.result(alanlar, dosyalar)
                        if hosting.result_sonrasi_kopar > 0:
                            hosting.result_sonrasi_kopar -= 1
                            self.close_connection = True
                            return                       # işlendi ama cevap yok: istemcide bağlantı hatası
                        return self._yaz(200, sonuc)
                    return self._yaz(400, {"error": "unknown_op"})
                except ValueError as e:
                    return self._yaz(422, {"error": str(e)})

            do_GET = _isle
            do_POST = _isle

        self.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self.sunucu.server_address[1]}/kanal_api.php"

    def dur(self):
        if self.sunucu:
            self.sunucu.shutdown()
