"""SAHTE hosting API (yalnız ajanın Python tarafını sınamak için). kanal/api.php + feature.php'nin ajanı ilgilendiren
davranışını Python'da taklit eder: claim, result, giden_durum, settings, heartbeat, log ve gönderim (tick) ile Meta durum
bildirimi. GERÇEK PHP HATTININ DOĞRULAMASI DEĞİLDİR: gerçek hat kanal/tests/baglanti_test.php + e2e_vps.py (portman/lib.php
ile) ve canlı Patron denemesiyle doğrulanır. Taklit edilen kurallar api.php'den satır satır alındı; ayrıldığı yer yok.
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
    def __init__(self, kok: Path, token: str, api: str = "kanal-api-v1.2", worker: str = "vps"):
        self.kok = Path(kok); self.kok.mkdir(parents=True, exist_ok=True)
        self.token, self.api, self.worker = token, api, worker
        self.inbound: dict[str, dict] = {}
        self.outbound: dict[str, dict] = {}
        self.durum: dict[str, str] = {}
        self.cagri: list[str] = []
        self.result_sonrasi_kopar = 0          # >0: result işlenir ama istemciye cevap verilmez (bağlantı koptu)
        self.kilit = threading.Lock()
        self._n = 0
        self.sunucu = None

    # ── kuyruk (feature.php::pm_kanal_capture'ın yazdığı satır) ──
    def mesaj_gelir(self, g: dict) -> None:
        with self.kilit:
            if g["id"] not in self.inbound:          # PHP: aynı wamid ikinci satır açmaz
                self.inbound[g["id"]] = {**g, "state": "queued", "attempts": 0}

    def yeniden_sirala(self, mid: str) -> None:
        """Yönetici işlemi: işlenmiş bir mesajı kuyruğa geri koyar (aynı kanal mesajının yeniden işlenmesi)."""
        with self.kilit:
            self.inbound[mid]["state"] = "queued"

    # ── gönderim (feature.php::pm_kanal_tick) ve Meta durum bildirimi (pm_kanal_status) ──
    def tick(self, belirsiz: set[str] | None = None) -> None:
        with self.kilit:
            for rid, r in sorted(self.outbound.items(), key=lambda x: (x[1].get("created_at", 0), x[1].get("seq", 0))):
                if r["state"] != "pending":
                    continue
                if belirsiz and rid in belirsiz:
                    r.update(state="uncertain", attempts=1, error="Gönderim sonucu belirsiz; otomatik tekrar yok.")
                    continue
                self._n += 1
                r.update(state="accepted", wamid=f"wamid.HOST{self._n:04d}", request_accepted_at=int(time.time()), attempts=1)

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
        return {"api": self.api, "now": int(time.time()), "enabled": True, "worker": self.worker, "dry_run": False, "mode": "patron",
                "llm": {"backend": "manuel"}, "patron_teknik_not": False, "poll_s": 1, "vps_komut": False, "package": None}

    def claim(self) -> dict:
        if self.worker != "vps":
            return {"job": None, "reason": f"worker={self.worker}"}
        with self.kilit:
            aday = [r for r in self.inbound.values() if r["state"] == "queued"]
            if not aday:
                return {"job": None}
            r = min(aday, key=lambda x: (x.get("timestamp", 0), x.get("received_at", 0)))
            r.update(state="processing", attempts=r["attempts"] + 1, worker="vps")
            return {"job": dict(r), "durum": None}

    def result(self, alanlar: dict, dosyalar: dict) -> dict:
        cikti = json.loads(alanlar.get("cikti") or "null")
        iid = alanlar.get("inbound_id") or ""
        if not isinstance(cikti, dict) or not isinstance(cikti.get("satirlar"), list) or not iid:
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
            gelen.update(state="failed" if cikti.get("hata") else "done", result=cikti.get("sonuc"))
            return {"ok": True, "outbound": n, "files": len(yazilan)}

    def giden_durum(self, body: dict) -> dict:
        ids = [x for x in (body.get("ids") or []) if isinstance(x, str) and re.fullmatch(r"out_[0-9a-f]{24}", x)][:200]
        out = {}
        with self.kilit:
            for i in ids:
                r = self.outbound.get(i)
                if r is None:
                    continue
                teslim = [e["timestamp"] for e in (r.get("delivery_events") or {}).values() if e["status"] in ("delivered", "read")]
                out[i] = {"state": r["state"], "wamid": r.get("wamid"), "request_accepted_at": r.get("request_accepted_at"),
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
                if self.headers.get("X-Portman-Token") != hosting.token:
                    return self._yaz(401, {"error": "unauthorized"})
                govde = self.rfile.read(int(self.headers.get("Content-Length") or 0))
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
