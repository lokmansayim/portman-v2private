"""SAHTE Meta Graph API (İE-06): kanal/meta_api.GraphIstemci'nin http(method, url, headers, data, timeout) bağımlılığı.
/messages → wamid; POST /media → medya kimliği; GET /<id> → indirme adresi; GET lookaside → içerik. hatalar sözlüğüyle hata enjekte
edilir. test_gonderici.py, test_surum.py ve kanal/tests/e2e_vps_kanal.py kullanır. Ağa çıkmaz."""
from __future__ import annotations

import json


class SahteMeta:
    """hatalar: {"messages"|"media"|"indir": True}; cevap_bozuk: contacts alanı olmayan cevap (send_response_uncertain)."""

    def __init__(self):
        self.istekler = []; self.hatalar = {}; self.sayac = 0; self.medya_sayac = 0; self.cevap_bozuk = False
        self.medya_icerik = b"\xff\xd8\xff" + b"j" * 20

    def __call__(self, method, url, headers, data, timeout):
        self.istekler.append({"method": method, "url": url, "data": data, "headers": headers})
        if url.endswith("/messages"):
            if self.hatalar.get("messages"):
                return 500, {}, b'{"error":{"message":"server","type":"Internal","code":1}}'
            govde = json.loads(data); self.sayac += 1
            if self.cevap_bozuk:
                return 200, {}, b'{"messages":[{"id":"wamid.OUT9"}]}'
            return 200, {}, json.dumps({"contacts": [{"input": govde["to"], "wa_id": govde["to"]}], "messages": [{"id": f"wamid.OUT{self.sayac:04d}"}]}).encode()
        if url.endswith("/media") and method == "POST":
            if self.hatalar.get("media"):
                return 500, {}, b'{"error":{"message":"upload failed","type":"x","code":2}}'
            self.medya_sayac += 1
            return 200, {}, json.dumps({"id": str(1000 + self.medya_sayac)}).encode()
        if url.startswith("https://graph.facebook.com/") and method == "GET":
            if self.hatalar.get("indir"):
                return 500, {}, b'{"error":{"message":"gone"}}'
            mid = url.rsplit("/", 1)[1]
            return 200, {}, json.dumps({"url": f"https://lookaside.invalid/m/{mid}", "mime_type": "image/jpeg", "file_size": len(self.medya_icerik)}).encode()
        if url.startswith("https://lookaside.invalid/"):
            return 200, {}, self.medya_icerik
        return 404, {}, b"{}"

    def gidenler(self):
        return [json.loads(i["data"]) for i in self.istekler if i["url"].endswith("/messages")]

    def tipler(self) -> list[str]:
        """Meta çağrılarının türü sırayla: media | text | document | image | interactive/<tür> (e2e_katman.py'nin ölçütü)."""
        out = []
        for i in self.istekler:
            if i["url"].endswith("/media") and i["method"] == "POST":
                out.append("media")
            elif i["url"].endswith("/messages"):
                b = json.loads(i["data"])
                out.append(b.get("type", "?") + ("/" + b["interactive"]["type"] if b.get("type") == "interactive" else ""))
        return out
