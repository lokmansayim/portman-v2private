#!/usr/bin/env python3
"""Excel hesaplama motorundaki (CTKBF V1.1, MALZEMELER sayfası) çatı kaplaması adedi formülü.

Yükleme listesi kaplama adedini buradan ALMAZ (kırma çatıda `cati_acilim.py`). Bu dosya, motorun formülünü olduğu gibi
ve payda parantezi düzeltilmiş haliyle hesaplar; belge ve liste sayfası örnekleri buradan yazar (mühendisin 4 Ekim 2026
12:14'teki isteği: "Hangi hücreden neyi çekiyorum formül nasıl işliyor").

Motordaki hücreler (hepsi MUSTERI TALEP sayfasının C sütunundan):
    K10 bina dış uzun kenar · K11 bina dış kısa kenar · K13, K14 sundurma dış uzun ve kısa kenar ·
    K17 oturum dışı veranda dış kısa kenar · K23 çatı tipi · K24 çatı kaplama

Formül (61, 64, 67 ve 72. satırlar; 58 ve 59. satırlarda da aynı ifade var):
    yüzey   = (K11 + 0,6) × √(1 + 0,33²) × (K10 + K17) + K13 × K14
    sac boyu = ((K11 + 0,6) ÷ 2) × √(1 + 0,33²) + 0,05
    adet    = YUKARIYUVARLA(yüzey / (sac boyu) * kaplama katsayısı × çatı katsayısı)
Kaplama katsayısı: trapez sac 0,8 · tek kat ve sandviç panel 1 · metal kiremit 1,05.
Excel bölmeyi ve çarpmayı soldan sağa yaptığı için bu (yüzey ÷ sac boyu) × katsayıdır; kapatma genişliğine bölmek için
katsayının paydanın parantezi içinde olması gerekir.

Kullanım:
    python motor_formul.py
"""
from __future__ import annotations

import math

EGIM = 0.33
SACAK = 0.6          # kısa kenara eklenen iki saçak (m)
TASMA = 0.05         # sac boyuna eklenen taşma (m)
KAPLAMA_KATSAYISI = {"trapez": 0.8, "panel": 1.0, "kiremit": 1.05}
CATI_KATSAYISI = {"besik": 1.0, "besik_cumba": 1.14, "besik_2_cumba": 1.27, "kirma": 1.06}


def yukari(x: float) -> int:
    return math.ceil(x - 1e-9)


def motor_kaplama(k10: float, k11: float, k17: float, cati: str, k13: float = 0.0, k14: float = 0.0) -> dict:
    """Motorun kaplama adedi: `yazilan` formül yazıldığı gibi; `duzeltilmis` katsayı paydanın parantezine alınınca."""
    e = math.sqrt(1 + EGIM ** 2)
    yuzey = (k11 + SACAK) * e * (k10 + k17) + k13 * k14
    boy = (k11 + SACAK) / 2 * e + TASMA
    ck = CATI_KATSAYISI[cati]
    return {
        "yuzey_m2": yuzey, "sac_boyu_m": boy, "sac_boyu_mm": yukari(boy * 1000), "oran": yuzey / boy, "cati_katsayisi": ck,
        "yazilan": {ad: yukari(yuzey / boy * k * ck) for ad, k in KAPLAMA_KATSAYISI.items()},
        "duzeltilmis": {ad: yukari(yuzey / (boy * k) * ck) for ad, k in KAPLAMA_KATSAYISI.items()},
        "tek_kat_87": yukari(yuzey / (boy * 0.87) * ck),      # tek kat panel gerçek listelerde 87 cm kapatır; motorda 100 cm yazıyor
    }


# Motorun şablonunda kayıtlı örnek: 9,74 × 7,44; veranda kısa kenarı 2,12; dört omuz; OSB + membran + metal kiremit (hücrede kayıtlı adet 27)
SABLON = motor_kaplama(9.74, 7.44, 2.12, "kirma")
# Mühendisin 10 × 10 m beşik çatı metrajı: 28 trapez sac (her saçakta 10,6 ÷ 0,8 → 14)
BESIK_10 = motor_kaplama(10.0, 10.0, 0.0, "besik")
assert SABLON["sac_boyu_mm"] == 4284 and SABLON["yazilan"]["kiremit"] == 27, SABLON      # motordaki kayıtlı değerler (B72, C72)
assert (SABLON["yazilan"]["trapez"], SABLON["duzeltilmis"]["trapez"], SABLON["duzeltilmis"]["kiremit"]) == (20, 32, 24), SABLON
assert (BESIK_10["yazilan"]["trapez"], BESIK_10["duzeltilmis"]["trapez"]) == (16, 25), BESIK_10


def main() -> int:
    for ad, m in (("şablondaki örnek (9,74 × 7,44; veranda 2,12; dört omuz)", SABLON), ("10 × 10 m beşik çatı", BESIK_10)):
        print(f"{ad}: yüzey {m['yuzey_m2']:.2f} m² ÷ sac boyu {m['sac_boyu_m']:.3f} m = {m['oran']:.2f} · yazıldığı gibi {m['yazilan']} · düzeltilince {m['duzeltilmis']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
