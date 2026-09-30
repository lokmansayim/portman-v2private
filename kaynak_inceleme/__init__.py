"""Portman · kaynak inceleme (SKP kaynak modeli → geometrik IFC4, denetim, P9401 çatı karşılaştırması).

Bu paket Codex'in 30.09.2026 devrindeki yerel prototipi mevcut depoya bağlayan yerel adaydır
(docs/raporlar/2026-09-30_Codex_Devir_Kabul.md).

Ne DEĞİLDİR:
  - Üretim Motor'u değildir. Üretim geometrisi İş Emri → Motor (DXF/PDF, BOM) → IFC yolundan gelir; bu paket ona dokunmaz.
  - Semantik BIM ya da BOM üretmez: IFC elemanları `IfcBuildingElementProxy`, geometri referansıdır.
  - İkinci bir doğruluk kaydı değildir. Kaynak kimlikleri (SHA256, revizyon) `veri/kaynaklar.json`'da durur; kabul ve
    durum bilgisi DURUM.md ve rapordadır.

Büyük veri (SKP'den türetilmiş selected/scene JSON'ları, IFC, .blend) depoda değildir; yolu PORTMAN_KAYNAK_VERI ile
verilir (Codex devir klasörünün düzeni). Ayrıntı: kaynak_inceleme/README.md.
"""

SURUM = "0.1.0"
