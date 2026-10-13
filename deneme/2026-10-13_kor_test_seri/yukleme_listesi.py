"""Prefabrik kör test serisi · kendi yükleme listemiz, sürüm 3 (İE-11 PR-2; protokol `docs/sartname/prefabrik_kor_test.md` adım 3).

    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py <İş Emri.json> <çıktı> [--pafta <pafta_katmani.json>]
    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py --yapi <yapi_pafta.json> <çıktı> [--pafta <pafta_katmani.json>]

Gerçek liste AÇILMADAN yazılır ve depoya kaydedilir; kıyas ondan sonra. Hiçbir adet elle yazılmaz. Geometri iki yoldan gelir:
  - **Motor kipi** (İş Emri): canlı pano Motor'unun planı (`motor.geometry.kur`).
  - **Pafta kipi** (`--yapi`): Motor'un çizemediği projelerde pano geometrisi montaj paftasının vektörlerinden okunmuş hali
    (Lokman 13.10 11:45, "ikisi birden"; Motor'un çizemedikleri ayrı bulgu). İkisi aynı ara yapıya (`N`) çevrilir.
Üç sütun: **adet** (varsayılan), **pafta** (o projenin paftasından okunan adet), **aday** (karar bekleyen ya da öteki uygulama).

Varsayılan uygulama **Portatifev şablonu** (Lokman 13.10 11:45; "PORTATİFEV YÜKLEME LİSTESİ", Ubeydullah, 1 Ekim 2026). Loftev şablonunun
(Kasım 2025; PK-02) farklı yaptığı kalemlerde Loftev uygulaması "aday" sütunundadır.

Sürüm geçmişi: 1 `deneme/2026-10-13_pk_01/yukleme_listesi.py` (PK-01, `aebcfca`); 2 (PK-02, `d31c35c`); 3 bu dosya.
Sürüm 2'deki değişiklikler (PK-01 dersleri 1–10, PK-02 paftasından P1–P3) aynen sürer. Sürüm 3'te (PK-02 kıyası, `PK02_kiyas.md`):
  H1. Elektrik: dış aplik ışık sayımına girmez; glop yalnız ıslak hacim, ampul = duy + glop.
  H2. Pencere vidası (4,8 × 70): pencere bizimse pencere × 20 (PK-01 dersi 9 fazla genellenmişti).
  H3. İniş borusu özelliğe bağlı: "Yağmur İniş Borusu: Metal" → metal L 3000; PVC → L 2500 + L 500.
  H4. 100'lük alt çerçeve = dış çevre ÷ 3,75 (Portatifev şablonu formülü; PK-01 ve PK-02'de tuttu).
  H5. Baş makas betopanı: kalkan başına ⌈1,5 × saçaklı üçgen ÷ 3,125⌉ (PK-01 4, PK-02 6).
  H6. Alçıpan: Portatifev formülü — kuru tavan × 1,05 ÷ 3 + 2 beyaz, ıslak × 1,05 ÷ 3 + 1 yeşil, aşağı yuvarlanır (PK-02 18 / 3).
  H7. Pencere boyları genel: alt panel = 200 − pencere boyu (120/120 → 80, 120/180 → 20, 160/180 → 20); vasistas dışındaki her
      pencereye karkas; 60'tan geniş her pencere sayılır.
  H8. Tavan tipi: asma (dizme) tavanda 125,5'te bir omega + tavan H'ı + kapak + betopan H'ı; **ters tavanda** omega 60'ta bir
      (oda alanı ÷ 0,60 ÷ 3,75; sürüm 1'in "yöntem B" kuralı), tavan H'ı ve kapak yok.
  H9. Çatı parçaları: beşik ve tek yön; her parçanın dere hattı, aşığı, kaplaması, makası ayrı hesaplanır, sonra toplanır.
Sürüm 4'te (PK-03 kıyası, `deneme/2026-10-13_pk_03/sonuc/PK03_kiyas.md`):
  J1. Modül katı pano sipariş boyu n × 1250 (251 → 2500); iki modüllük pencere panosu tek satır "karkaslı özel pencere panosu", ayrı karkası yok.
  J2. 100'lük duvar omegası: çatı kenarına gelmeyen dış duvarlar ÷ 2,5 (`N["ic_kalan_dis_duvar_m"]`; dikdörtgen planda 0).
  J3. Metal dere toplam boy ÷ 3,8 (Portatifev formülü); dere kelepçesi dere × 8.
  J4. Dere kapağı beşikte 4 + cumba (ek çatı parçası) başına 2; iniş ana beşikte 4 + 9 m'yi geçen saçağa 1, cumba başına 2.
  J5. Trapez çatıda trapez sac mahyası L 1000 (0,8 etkin); çapraz beşikte iki ters mahya (dere içi) √(a² + b² + h²) ÷ 2,6.
  J6. PVC plastik betopan H'ı tavan tipinden bağımsız.
  J7. Duvar alçıpanı varsa: ıslak hacim duvarları yeşil, öteki beyaz; alçıpan vidası bütün levhalar × 40 (250'nin katı); destek straforu yüzey ÷ 60 m².
  J8. Ek çatı parçasının makasları "yavru makas".
Sürüm 5'te (PK-05 kıyası, `deneme/2026-10-13_pk_05/sonuc/PK05_kiyas.md`):
  L1. Standart pencereler (120/120, 120/180) üst + alt panel; vasistas (en ≤ 60) ayrı; ötekiler (80/120, 160/180 …) "karkaslı özel pencere panosu".
  L2. Tek yön çatıda saçak yalnız alçak kenarda: eğik boy = (açıklık + saçak) × √(1 + e²) (PK-05 makas üst başlığı 6648 → L 6650).
  L3. Tek kat panel 87 cm kapatır, boy 50 mm'ye yukarı (kurallar.json'daki 1,0 bu ürün için yanlış; kural kitabı adayı).
  L4. Çelik dış kapı listede 900 × 2000 (paftada 100/220 ya da 100'lük yay çizilse de; PK-02, PK-03, PK-05).
  L5. Tek kat panel vidası 5,5 × 76.
Sürüm 5.1 (PK-06 okumasıyla, gerçek liste açılmadan; kural değil model alanı): ek çatı parçasında `capraz: false` (ana çatıya paralel
  beşik, PK-06 verandası) ters mahya (dere içi) almaz; anahtarsız parça eskisi gibi çapraz beşik sayılır.
Sürüm 6'da (PK-06 kıyası, `deneme/2026-10-13_pk_06/sonuc/PK06_kiyas.md`):
  N1. Açık çatı parçası (`acik: true`; altı veranda, kalkanı kirişte): baş makas omegası, Z'si ve betopanı bu parçanın kalkanını saymaz;
      Loftev şilte adayı da bu parçayı saymaz (PK-06 7 / 8 / 6 ve 11).
  N2. Veranda tavan omegası ayrı satır değil (PK-01, PK-03 ve PK-06 listelerinde tek satır).
  N3. Aday sütununa: W otomat 9, PVC iniş borusu L 2000, profil vidalama kolon × 3 (Loftev), inox m² ÷ 10 aşağı ve uçlar inox ÷ 2
      (listenin "VİDA BİLGİ" sayfası; veri, kural kitabı adayı).
  Kulaklı H (makasın denk geldiği her dış ek) okuyucuda: `deneme/2026-10-13_pk_06/pafta_oku.py`.
Sürüm 6.1 (PK-07 okumasıyla, gerçek liste açılmadan; model alanları ve ilk tahmin): iç duvar kalınlığı `kal_mm`'den (100'lük iç pano,
  H standart 100, iç köşe 10'luk); çatı parçasında `kalkan_duvar_cm` (kalkanın altındaki duvar, paftadan); açıklamada "dış cephe … betopan"
  varsa dış cephe betopanı ilk tahmini; H ve pencere karkası satırlarına pafta sütunu.
Sürüm 7'de (PK-07 kıyası, `deneme/2026-10-13_pk_07/sonuc/PK07_kiyas.md`; PK-07 şablon sahibinin Portatifev listesi, PK-01'in boş bıraktığı
kalemlerde varsayılan PK-07'ye geçti, soru açık):
  O1. Açıklamada "fugalı" → dış panolar "(FUGALI)" ayrı satır; ayrı dış betopan yok; H latası, köşe latası 150 + 130, pencere latası.
  O2. Dış çizginin iç köşesi "özel köşe direği D" ayrı satır (`koseler.ozel`).  O3. Köşebent 7 (şablon notu "tek kat 7").
  O4. Kolon boyu paftadan (`kolon_boylari_cm`).  O5. İç duvar 100: duvar üstleri 100'lük duvar omegası; ters tavan hatları iki duvar yüzünden.
  O6. Paftadaki özel büküm saçak / alın sacı (`ozel_bukum`) düz saçtan düşülür.  O7. Baş makas Z'si ana çatının alın kenarları × ⌈eğik ÷ 2,8⌉.
  O8. İç duvar 100: alt çerçeve tek satır (dış çevre + iç duvar) ÷ 3,75.  O9. Ana çatı kaplaması yüz başına yukarı.
  O10. Mahya toplam ÷ 2,6.  O11. Sandviç panel kapaması saçak ÷ 2,5.  O12. Pencere alıcıya ait olsa da karkas ve montaj vidası bizde.
  O13. Aşık sırası en yakın tamsayı.  O14. Veranda tavan Boardex veranda × 1,08 ÷ 2,88.  O15. Kanopi (açık, makassız) dere almaz.
  O16. Vida / depo: betopan vidası 500, 5,5 × 60 m² × 2,5, kesme taşı m² × 0,02, çırpı ipi 1, alçıpan vidası tavan levhası × 40,
       RYSB m² × 7,5 (50'ye), çelik dübel = dübelli H, çatı müdahale kapağı 1.
  O17. Bir banyolu evde sıhhi tesisat sabit takımı (7 satır).  O18. Boya dış / iç / kenar / tavan / astar; dayson yukarı; köpük 2.
  O19. Buat kasa = elektrik noktaları.
Sürüm 7.1 (PK-08 okumasıyla, gerçek liste açılmadan; model anlamı): 120 genişlikteki her pencere standart (üst + alt panel; 120/100 dahil);
  vasistas yalnız en ≤ 60 ve boy ≤ 60 (59/170 dar uzun pencere karkaslı özel pano); çatı parçasında `dere_yok`; vitrifiye alıcıya aitse 0;
  trapez çatıda O16'nın 5,5 × 60 satırı yazılmaz (kaplama vidası satırı zaten 5,5 × 60).
Sürüm 7.2 (Lokman'ın 13.10 öğleden sonra cevapları, AIPrefabrik inceleme seti E1–E5; `deneme/2026-10-13_aiprefabrik/INCELEME.md`):
  R1. Alt çerçeve her zaman L 3750 (Lokman): 60'lık da 60 × 3750, iç duvar ÷ 3,75.
  R2. PVC iniş borusu L 2000 + L 500 (Lokman: "iniş borusu 2000, toplam bina yüksekliği 2500").
  R3. İniş: ana çatıda köşeler + her saçak hattının ortasına 1 (beşikte 4 + 2 = 6) + ek çatı parçası başına 2 (Lokman; E1, E4, E5,
      PK-01, PK-03, PK-07 paftaları). Eski 9 m eşiği aday sütununda.
  R4. W otomat Portatifev 8 (Lokman; 10 listede şablona bağlı), Loftev 9 aday.
  R5. Fugalı cephede H latası = dış 100'lük duvar H'ları + 3 yedek (Lokman; PK-07 27 + 3 = 30).
  R6. Kubbeli cumba (`kubbe: true` çatı parçası): genel çatı satırlarına girmez; Abdulselam takımı (E2 − E3) eklenir (Lokman).
  Islak hacim yalnız banyo ve WC (Lokman; ISLAK zaten böyle). Dörtomuz çatıda baş makas Z'si yok (Lokman; kalkan 0 → Z, omega, betopan 0).
LLM yok, ağ yok.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

SURUM = "7.2 (13 Ekim 2026; Portatifev varsayılan, PK-02, PK-03, PK-05, PK-06 ve PK-07 dersleri, pafta kipi; pencere sınıfları; Lokman cevapları R1–R6)"
GRUPLAR = {"1001": "Panel", "1002": "Metal aksam", "1003": "Kapı ve pencere", "1004": "Tavan", "1005": "Makas", "1006": "Çatı",
           "1007": "Elektrik", "1008": "Vida", "1009": "Depo", "1010": "Sıhhi tesisat", "1011": "Dere", "1012": "Boya"}
TAVAN = lambda x: int(math.ceil(x - 1e-9))
ASAGI = lambda x: int(math.floor(x + 1e-9))
MOD = 125.5
PENCERE_UST_KOTU_CM = 200.0           # Motor: pencere üst kotu / kapı üstü 200 (lento = h − 200)
ASMA_OMEGA_ARALIK_M = 1.255           # PK-02 tavan omega planı: "omega profiller 125 cm'de bir"; PK-01 şablonu: "125,5 cm'de bir"
TERS_OMEGA_ARALIK_M = 0.60            # PK-03 tavan omega planı: "ters tavan, omega profiller 60 cm'de bir"
TAVAN_H_ARALIK_M = 0.625              # PK-01 şablonu: "duvar omegalarına dik, 62,5 cm'de bir"
ISLAK = ("banyo", "wc", "islak", "lavabo")
STANDART_PENCERE = ("120x120", "120x180")          # L1: üst + alt panelle listelenen pencereler
TEK_KAT_KAPATMA_M = 0.87                            # L3: PK-05 listesi "TEK KAT PANEL (87 CM KAPATIR)"
KUBBE_TAKIMI = (                                    # R6: bir kubbeli cumba (E2 − E3; Lokman 13.10 "Abdulselam takımı")
    ("1001", "Kubbe özel pano", "100 × 2500 × 500", 1),
    ("1002", "Kubbe üstü H", "100 × 100 × 500", 2),
    ("1002", "Özel açılı köşe direği + kapaması", "100 × 100 × 2330", 4),
    ("1002", "Kubbe saçak sacı (antrasit)", "170 × 1500", 3),
    ("1005", "Kubbe makası", "80 × 0,8", 3),
    ("1006", "Kubbe OSB 11 mm", "1220 × 2440", 1),
    ("1006", "Kubbe üstü membran", "paket", 1),
    ("1006", "Kubbe antrasit shingle", "paket", 1),
)


def _kural(k: dict, *yol):
    v = k
    for a in yol:
        v = v[a]
        if isinstance(v, dict) and "deger" in v and a == yol[-1]:
            return v["deger"]
        if isinstance(v, dict) and "deger" in v:
            v = v["deger"]
    return v


def siparis(cm: float) -> int:
    """Pano sipariş boyu (PK-01 dersi 2, Portatifev): net boy − 2,5 mm, 5 mm'ye aşağı. PK-01'de 50 / 50; PK-02'de (Loftev) 39 → 390, 31 → 310.
    Modül katı (n × 125,5) panoda n × 1250 (J1; PK-03: 251 → 2500)."""
    n = round(cm / MOD)
    if n >= 1 and abs(cm - n * MOD) < 0.06:
        return 1250 * n
    return int(math.floor((cm * 10 - 2.5) / 5 + 1e-6) * 5)


def mm(cm: float) -> str:
    v = round(cm * 10, 1)
    return f"{v:g}".replace(".", ",")


def pencere_olcusu(olcu: str) -> tuple[int, int]:
    en, boy = olcu.lower().replace("/", "x").split("x")
    return int(float(en)), int(float(boy))


# ── geometri: Motor kipi ────────────────────────────────────────────────────────
def model_motor(ie: dict) -> dict:
    from motor import geometry as G
    from shapely.geometry import LineString, box
    from shapely.ops import unary_union
    plan = G.kur(json.loads(json.dumps(ie)))
    y = ie["yapi"]; c = ie.get("cati") or {}
    mx = c.get("makas_ekseni", "x") == "x"                     # makaslar x'i geçiyorsa saçak duvarları y yönünde koşar
    eave_yon = "y" if mx else "x"
    panolar, ekler = [], []
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            panolar.append({"duvar": d.tur, "kal_mm": round(2 * d.h * 10), "boy": p.boy,
                            "aciklik": None if a is None else {"tur": a.tur, "olcu": a.olcu, "genislik": a.genislik, "mentese": a.mentese,
                                                                "dograma": a.dograma}})
        for a_, _b in zip(d.panolar, d.panolar[1:]):
            x, yy = (a_.a1, d.c) if d.yon == "x" else (d.c, a_.a1)
            uclu = any(abs(h.x - x) <= d.h + 3.5 and abs(h.y - yy) <= d.h + 3.5 for h in plan.h_baglantilar)
            ekler.append({"duvar": d.tur, "cins": "uclu" if uclu else "pano_eki", "sacak": d.yon == eave_yon})
    kapali = [m for m in plan.mahaller.values() if not (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    acik = [m for m in plan.mahaller.values() if (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    g = unary_union([plan.footprint()] + [m.poly for m in plan.mahaller.values() if m.poly is not None] + [box(*r) for r in plan.dikmeler])
    bx0, by0, bx1, by1 = g.bounds
    W, D = bx1 - bx0, by1 - by0

    def oda(m):
        x0, y0, x1, y1 = m.poly.bounds
        en, derin = ((y1 - y0), (x1 - x0)) if mx else ((x1 - x0), (y1 - y0))
        return {"ad": m.ad, "tur": m.tur, "alan_m2": m.alan_m2, "en_cm": en, "derin_cm": derin}
    kirisler = []
    if plan.dikmeler and acik:
        for v in acik:
            vx0, vy0, vx1, vy1 = v.poly.bounds
            yanlar = set()
            for (x0, y0, x1, y1, *_r) in plan.acik_kenarlar:
                if v.poly.buffer(1.0).contains(LineString([(x0, y0), (x1, y1)])):
                    yanlar.add("x" if abs(y1 - y0) < 1e-6 else "y")
            kirisler += [((vx1 - vx0) if e == "x" else (vy1 - vy0)) - 10 for e in sorted(yanlar)]
    t_dis = 2 * next(d.h for d in plan.duvarlar if d.tur == "dis")
    aciklik, bina_boyu = (W, D) if mx else (D, W)
    return {"kaynak": "Motor", "H0": float(y.get("duvar_yuksekligi_cm", 250)), "W": W, "D": D, "brut_m2": round(W * D / 1e4, 3),
            "dis_cevre_m": 2 * (W + D) / 100, "t_dis": t_dis, "panolar": panolar, "ekler": ekler,
            "koseler": dict(Counter("dis" if kk.tur == "dis" else "ic" for kk in plan.koseler)), "dikmeler": len(plan.dikmeler),
            "veranda_kirisleri_cm": kirisler, "kapali": [oda(m) for m in kapali], "acik": [{**oda(m), "tur": "veranda"} for m in acik],
            "cati": [{"ad": "ana çatı", "tip": c.get("tip", "besik"), "aciklik_cm": aciklik, "boy_cm": bina_boyu,
                      "egim_yuzde": float(c.get("egim_yuzde", 33)), "sacak_cm": float(c.get("sacak_cm", 30)), "kalkan": 2,
                      "makas_kosu_cm": bina_boyu - 2 * t_dis}],
            "ozellikler": ie.get("ozellikler") or {}, "alici_ait": ie.get("alici_ait") or {}, "is_emri_no": ie.get("is_emri_no"),
            "kod": y.get("referans_model")}


# ── geometri: pafta kipi ────────────────────────────────────────────────────────
def model_pafta(yp: dict) -> dict:
    """`yapi_pafta.json`: paftadan okunmuş geometri (proje klasöründeki `pafta_oku.py` yazar). Alanlar `model_motor` ile aynı."""
    N = dict(yp)
    N["kaynak"] = "pafta"
    N.setdefault("brut_m2", round(yp["W"] * yp["D"] / 1e4, 3))
    N.setdefault("dis_cevre_m", 2 * (yp["W"] + yp["D"]) / 100)
    for c in N["cati"]:
        c.setdefault("kalkan", 2 if c["tip"] == "besik" else 0)
        c.setdefault("makas_kosu_cm", c["boy_cm"] - 2 * N["t_dis"])
    return N


def omega_hatlari(kapali, aralik_m: float, duvar_yuzu: bool = False) -> tuple[float, int]:
    """Tavan omega hatları: her kapalı odada mahyaya paralel, `aralik_m`'de bir; hat sayısı oda derinliği ÷ aralık en yakın tamsayı
    (en az 1), hat boyu oda net genişliği (PK-02 tavan planı: banyo 2, yatak 2, hol 1, mutfak 2, salon 3). Döner: (toplam m, hat).
    `duvar_yuzu` (O5; PK-07 ters tavan planı): her gözde iki duvar yüzünde de hat → ⌊derinlik ÷ aralık⌋ + 1."""
    L, n_top = 0.0, 0
    for m in kapali:
        n = (int(math.floor(m["derin_cm"] / 100 / aralik_m + 1e-9)) + 1) if duvar_yuzu else max(1, int(math.floor(m["derin_cm"] / 100 / aralik_m + 0.5)))
        L += n * m["en_cm"] / 100; n_top += n
    return L, n_top


def cati_olculeri(c: dict) -> dict:
    sac = c["sacak_cm"] / 100; eg = c["egim_yuzde"] / 100
    if c["tip"] == "besik":
        egik = (c["aciklik_cm"] / 200 + sac) * math.sqrt(1 + eg * eg); yuz = 2; sacak_hat = 2
    else:                                                       # tek yön: tek yüz, tek dere hattı; saçak yalnız alçak kenarda (L2)
        egik = (c["aciklik_cm"] / 100 + sac) * math.sqrt(1 + eg * eg); yuz = 1; sacak_hat = 1
    mahya_boy = c["mahya_boy_cm"] / 100 if c.get("mahya_boy_cm") else c["boy_cm"] / 100 + 2 * sac
    hatlar = list(c.get("sacak_hatlari_m") or [mahya_boy] * sacak_hat)      # pafta kipi: paftadaki gerçek saçak / dere hatları
    return {"sac": sac, "eg": eg, "egik": egik, "yuz": yuz, "sacak_hat": sacak_hat, "mahya_boy": mahya_boy, "hatlar": hatlar}


def liste(N: dict, k: dict, pafta: dict | None = None) -> dict:
    H0 = N["H0"]
    kucuk = lambda x: str(x).replace("İ", "i").replace("I", "ı").lower()
    oz = {kucuk(kk): kucuk(v) for kk, v in (N.get("ozellikler") or {}).items()}
    alici = [kucuk(x) for x in ((N.get("alici_ait") or {}).get("kalemler") or [])]
    pencere_alici = any("pencere" in x for x in alici) or "alıcı" in oz.get("pencere rengi", "")
    satirlar = []
    P = pafta or {}
    kaynak_ad = "Motor planından" if N["kaynak"] == "Motor" else "paftadan okunan geometriden"

    def pk(*yol):
        v = P
        for a in yol:
            v = (v or {}).get(a)
        return (v or {}).get("adet"), (v or {}).get("not", "")

    def ekle(grup, kalem, olcu, adet, dayanak, formul, kaynak="", birim="adet", pafta=None, aday=None, aday_notu=""):
        pa, pn = pk(*pafta) if pafta else (None, "")
        satirlar.append({"grup": grup, "grup_adi": GRUPLAR[grup], "kalem": kalem, "olcu": olcu, "adet": adet, "birim": birim, "dayanak": dayanak,
                         "formul": formul, "kaynak": kaynak, "pafta": pa, "pafta_notu": pn, "aday": aday, "aday_notu": aday_notu})

    bina_m2 = N["brut_m2"]
    tavan_kuru = sum(x["alan_m2"] for x in N["kapali"] if x["tur"] not in ISLAK)
    tavan_islak = sum(x["alan_m2"] for x in N["kapali"] if x["tur"] in ISLAK)
    tavan_net = tavan_kuru + tavan_islak
    kubbeler = [c for c in N["cati"] if c.get("kubbe")]          # R6: kubbe genel çatı satırlarına girmez, takımı ayrı
    C = [(c, cati_olculeri(c)) for c in N["cati"] if not c.get("kubbe")]
    ana, ao = C[0]

    def kubbe_takimi(grup):
        for g, kalem, olcu, n in KUBBE_TAKIMI:
            if g == grup:
                ekle(g, kalem, olcu, n * len(kubbeler), "Kural (Lokman 13.10, R6)", f"kubbeli cumba takımı × {len(kubbeler)}",
                     "E2 − E3 (Abdulselam 65 kubbeli − kubbesiz); PK-08 aynı takım, makas ve membransız")
    acl = [p["aciklik"] for p in N["panolar"] if p["aciklik"]]
    pen = [a for a in acl if a["tur"] == "pencere"]
    vasistas = lambda a: pencere_olcusu(a["olcu"])[0] <= 60 and pencere_olcusu(a["olcu"])[1] <= 60   # 7.1: 59/170 gibi dar uzun pencere vasistas değil
    standart = lambda a: pencere_olcusu(a["olcu"])[0] == 120                                          # 7.1: 120 genişlikte her pencere üst + alt panel (H7)
    cift = {id(a) for a in pen if not standart(a) and not vasistas(a)}                               # L1: karkaslı özel pencere panosu
    pen_k = [a for a in pen if not vasistas(a) and id(a) not in cift]   # ayrı karkaslı pencereler (vasistas ve iki modüllük hariç)

    # ── 1001 Panel ──────────────────────────────────────────────────────────
    fugali = "fugalı" in oz.get("açıklama", "") or "fugali" in oz.get("açıklama", "")
    ic_kal = Counter(p["kal_mm"] for p in N["panolar"] if p["duvar"] == "ic").most_common(1)[0][0] if any(p["duvar"] == "ic" for p in N["panolar"]) else 60
    sayac = Counter()
    for p in N["panolar"]:
        kal_mm = p["kal_mm"]
        kal = "100'lük" if kal_mm >= 100 else "60'lık"          # 6.1: iç duvar 100 mm olabilir (PK-07 özellik tablosu)
        fg = " (FUGALI)" if (fugali and p["duvar"] == "dis") else ""   # O1: fugalı dış cephede dış panolar ayrı satır (PK-07)
        L = siparis(p["boy"]); a = p["aciklik"]
        if a is None:
            sayac[(f"{kal} yapıştırma dolu pano{fg}", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "sipariş boyu (PK-01 dersi 2)")] += 1
        elif a["tur"] == "pencere":
            en, boy = pencere_olcusu(a["olcu"])
            if vasistas(a):
                sayac[(f"{kal} yapıştırma dolu vasistaslı pano ({en}/{boy}){fg}", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "vasistaslı pano")] += 1
            elif id(a) in cift:
                sayac[(f"Karkaslı özel pencere panosu ({en}/{boy}){fg}", f"{kal_mm} × {L} × {mm(H0)}", "Kural (L1)", "standart dışı pencere panosu tek parça (PK-03 160/180, PK-05 80/120)")] += 1
            else:
                ust = H0 - PENCERE_UST_KOTU_CM
                sayac[(f"Pencere üst panel{fg}", f"{kal_mm} × {L} × {mm(ust)}", "Liste kuralı", "pencereli pano listede üst + alt panel")] += 1
                sayac[(f"Pencere alt panel ({en}/{boy}){fg}", f"{kal_mm} × {L} × {mm(PENCERE_UST_KOTU_CM - boy)}", "Liste kuralı",
                       "alt panel = 200 − pencere boyu (H7)")] += 1
        elif a["tur"] == "dis_kapi":
            sayac[(f"Karkaslı çelik kapı panosu{fg}", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "dış kapı boşluklu pano")] += 1
        elif a["tur"] == "ic_kapi":
            sayac[(f"{kal} karkaslı + kasalı pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "iç kapı boşluklu pano")] += 1
        else:
            sayac[(f"{kal} geçişli pano", f"{kal_mm} × {L} × {mm(H0)}", "Sayım", "kapısız geçiş")] += 1
    for (kalem, olcu, dayanak, kaynak), n in sorted(sayac.items(), key=lambda x: (x[0][0], -int(x[0][1].split(" × ")[1]))):
        ekle("1001", kalem, olcu, n, dayanak, f"{kaynak_ad} sayım", kaynak)

    if kubbeler:
        kubbe_takimi("1001")

    # ── 1002 Metal aksam ────────────────────────────────────────────────────
    kc = N["koseler"]
    if ic_kal >= 100:                                          # 6.1: iç duvar 100 → iç köşe de 10'luk (PK-07)
        ekle("1002", "10'luk köşe direği 100 × 100", f"100 × 100 × {mm(H0)}", kc.get("dis", 0) + kc.get("ic", 0), "Sayım",
             f"köşe parçası (dış {kc.get('dis', 0)} + iç {kc.get('ic', 0)}; iç duvar 100)", "PK-07 5 tuttu")
    else:
        ekle("1002", "10'luk köşe direği 100 × 100", f"100 × 100 × {mm(H0)}", kc.get("dis", 0), "Sayım", "köşe parçası", "özel köşe B, C, D'nin kuralı yok (soru 2)")
        ekle("1002", "6'lık köşe direği 60 × 60", f"60 × 60 × {mm(H0)}", kc.get("ic", 0), "Sayım", "iç köşe")
    if kc.get("ozel"):                                          # O2: L planın iç köşesi "özel köşe direği D" (PK-07)
        ekle("1002", "Özel köşe direği (D) 100 × 100", f"100 × 100 × {mm(H0)}", kc["ozel"], "Sayım", "dış çizginin iç köşesi (çektirme U'lu)", "PK-07 1 tuttu")
    ekle("1002", "Köşebent", "L 2500", 7, "Kural (Portatifev)", "şablon notu \"tek kat 7\" (O3; PK-07 7, PK-06 7 tuttu; PK-01'de 0)", "",
         aday=3, aday_notu="Loftev PK-02 3, PK-03 ve PK-05 5")
    if N["dikmeler"]:
        for L_k, n_k in sorted(Counter(N.get("kolon_boylari_cm") or [H0] * N["dikmeler"]).items(), reverse=True):   # O4: kolon boyu paftadan
            ekle("1002", "Özel kutu profil (kolon) 100 × 100", f"L {mm(L_k)}", n_k, "Sayım", "veranda dikmesi" + (" (boy paftadan, O4)" if N.get("kolon_boylari_cm") else ""))
        ekle("1002", "Profil vidalama aparatı", "adet", 2, "Kural (Portatifev)", "özel profil varsa 2 (PK-01: \"ekstradan ekledik\")",
             aday=3 * N["dikmeler"], aday_notu="Loftev (PK-03 6, PK-06 6 ✓): kolon × 3")
    for L_ in N["veranda_kirisleri_cm"]:
        ekle("1002", "Kutu profil (kiriş) 100 × 100", f"L {mm(L_)}", 1, "Liste kuralı", "açık kenar dış ölçüsü − 100", "PK-01'de tuttu")
    ec = Counter((e["duvar"], e["cins"]) for e in N["ekler"])
    ek_s = Counter((e["duvar"], e["cins"]) for e in N["ekler"] if e["sacak"])
    ekle("1002", "H 100 (dış pano eki)", f"100 × 100 × {mm(H0)}", ec[("dis", "pano_eki")], "Sayım", "her dış ekte bir H", "kulaklı / dübelli ayrımı: aday",
         aday=f"kulaklı {ek_s[('dis', 'pano_eki')]} / dübelli {ec[('dis', 'pano_eki')] - ek_s[('dis', 'pano_eki')]}",
         aday_notu="makasın denk geldiği dış ek kulaklı; PK-01 12 / 7, PK-02 8 / 9, PK-06 13 / 6 tuttu", pafta=("h_plani", "dis"))
    ekle("1002", f"H standart {ic_kal} (iç pano eki)", f"{ic_kal} × {ic_kal} × {mm(H0)}", ec[("ic", "pano_eki")], "Sayım", "her iç ekte bir H", pafta=("h_plani", "h_standart"))
    ekle("1002", f"3'lü H 100 × 100 × {ic_kal} (dış duvar T'si)", f"L {mm(H0)}", ec[("dis", "uclu")], "Sayım", "iç duvarın dış duvara geldiği T", "",
         aday=f"kulaklı {ek_s[('dis', 'uclu')]} / dübelli {ec[('dis', 'uclu')] - ek_s[('dis', 'uclu')]}", aday_notu="aynı kural; PK-01 2 / 3, PK-02 2 / 3",
         pafta=("h_plani", "uclu_dis"))
    ekle("1002", f"3'lü H standart {ic_kal} (iç T)", f"L {mm(H0)}", ec[("ic", "uclu")], "Sayım", "iç–iç T birleşimi", pafta=("h_plani", "uclu_standart"))
    dubelli = ec[("dis", "pano_eki")] + ec[("dis", "uclu")]
    for olcu, n in sorted(Counter(a["olcu"] for a in pen_k).items()):   # O12: pencere alıcıya ait olsa da karkas bizde (PK-07 C × 4)
        en, boy = pencere_olcusu(olcu)
        ekle("1002", f"Özel pencere karkası ({en}×{boy}) (100'lük çektirme U'su + 100'lük H geçen)", f"{en * 10} × {boy * 10}", n, "Kural (Portatifev)",
             "her karkaslı pencereye bir (PK-01 dersi 3; PK-07 alıcıya ait pencerede de 4)", "", aday=0, aday_notu="Loftev (PK-02): hazır karkas yok, U'lar yerinde",
             pafta=("pencere_karkasi",))
    if not pencere_alici:
        ekle("1002", "Çektirme U'su 100", "100 × 2440", 2, "Kural (Portatifev)", "karkas hazır gidince 2 sabit (PK-01: \"pencere özel iletiliyor, 2 fix\")",
             aday=TAVAN(sum(2 * pencere_olcusu(a["olcu"])[0] for a in pen_k) / 244 + 2), aday_notu="Loftev (PK-02 6 ✓): karkaslı pencerelerde (2 × en) ÷ 244 + 2")
        ekle("1002", "100'lük pencere U'su H geçen", "L 2500", 1, "Kural (Portatifev)", "PK-01'de 1",
             aday=2 * len(pen_k), aday_notu="Loftev (PK-02 8 ✓): karkaslı pencere × 2")
    ekle("1002", f"Çektirme U'su {ic_kal} (iç duvar)" if ic_kal >= 100 else "Çektirme U'su 60", f"{ic_kal} × 2440", 2, "Kural (Portatifev)", "PK-01 ve PK-02'de 2")
    # tavan taşıyıcısı (H8)
    L_duvar = sum(p["boy"] for p in N["panolar"] if p["duvar"] == "ic") / 100
    tavan_tipi = oz.get("tavan", oz.get("tavan şekli", "asma"))
    ters = "ters" in tavan_tipi
    if ters and ic_kal >= 100:                                  # O5: iç duvar 100 → duvar üstleri 100'lük duvar omegasında; hatlar duvar yüzünden
        L_hat, n_hat = omega_hatlari(N["kapali"], TERS_OMEGA_ARALIK_M, duvar_yuzu=True)
        ekle("1002", "60'lık tavan omegası (ters tavan)", "60 × 3750", TAVAN(L_hat / 3.65 + 5), "Şablon formülü (Portatifev)",
             f"oda hatları {L_hat:.2f} m [{n_hat} hat, 60'ta bir, iki duvar yüzünde de] ÷ 3,65 + 5 (iç duvar üstleri 100'lük omegada)",
             "PK-07 36 tuttu (O5)", pafta=("tavan_omegasi",), aday=TAVAN(L_hat / 3.65), aday_notu="\"+5\"siz")
    elif ters:
        L_hat, n_hat = omega_hatlari(N["kapali"], TERS_OMEGA_ARALIK_M)
        ekle("1002", "60'lık tavan omegası (ters tavan)", "60 × 3750", TAVAN((L_hat + L_duvar) / 3.65 + 5), "Şablon formülü (Portatifev)",
             f"(oda içi hatlar {L_hat:.2f} m [{n_hat} hat, 60'ta bir] + iç duvar üstleri {L_duvar:.2f} m) ÷ 3,65 + 5",
             "tavan: " + tavan_tipi + "; duvar üstleri PK-03 tavan planında da var", pafta=("tavan_omegasi",),
             aday=TAVAN((L_hat + L_duvar) / 3.65), aday_notu="Loftev (PK-02): \"+5\"siz")
    else:
        L_hat, n_hat = omega_hatlari(N["kapali"], ASMA_OMEGA_ARALIK_M)
        ekle("1002", "60'lık duvar omegası (asma dizme tavan)", "60 × 3750", TAVAN((L_hat + L_duvar) / 3.65 + 5), "Şablon formülü (Portatifev)",
             f"(oda içi hatlar {L_hat:.2f} m [{n_hat} hat, 125,5'te bir] + iç duvar üstleri {L_duvar:.2f} m) ÷ 3,65 + 5",
             "PK-01'de formül 21, girilen 8 (soru 1)", pafta=("duvar_omegasi_asma",), aday=TAVAN((L_hat + L_duvar) / 3.65), aday_notu="Loftev (PK-02 16 ✓): \"+5\"siz")
    # N2 (sürüm 6): veranda tavanının omegası ayrı satır değil — PK-01, PK-03 ve PK-06 listelerinde tek omega satırı var (PK-03 dersi 10, PK-06)
    ic_kalan = N.get("ic_kalan_dis_duvar_m", 0.0)
    ust100 = L_duvar if ic_kal >= 100 else 0.0                  # O5: 100'lük iç duvarların üstü de 100'lük omega (PK-07 10)
    ekle("1002", "100'lük duvar omegası", "100 × 2500", TAVAN((ic_kalan + ust100) / 2.5), "Kural (J2, O5)",
         (f"çatı kenarına gelmeyen dış duvarlar {ic_kalan:.2f} m" + (f" + 100'lük iç duvarlar {ust100:.2f} m" if ust100 else "") + " ÷ 2,5")
         if (ic_kalan or ust100) else "dikdörtgen beşikte bütün dış duvarlar saçak ya da baş makas omegası alır",
         "PK-01 0, PK-03 3, PK-06 3, PK-07 10 tuttu")
    sacak_m = sum(sum(o["hatlar"]) for _c, o in C)
    ekle("1002", "100'lük saçak omegası", "100 × 2500", TAVAN(sacak_m / 2.5), "Kural (PK-01)", f"saçak kenarları {sacak_m:.2f} m ÷ 2,5, bir kez yukarı", "PK-01 9, PK-02 7 tuttu")
    ps, bs = _kural(k, "parca_boyu_m", "sacak_saci"), _kural(k, "bindirme_m", "sacak_saci")
    ob = N.get("ozel_bukum") or {}                              # O6: paftadaki özel büküm saçlar düz saçtan düşülür (PK-07 2 + 2)
    ekle("1002", "Saçak sacı (30'luk, 3'ü menfezli)", "300 × 2500", TAVAN(sacak_m / (ps - bs)) - ob.get("sacak", 0), "Kural",
         f"saçak kenarları {sacak_m:.2f} m ÷ 2,3" + (f" − özel büküm {ob['sacak']}" if ob.get("sacak") else ""), "PK-01 ve PK-02'de tuttu; PK-07 9 + 2")
    if ob.get("sacak"):
        ekle("1002", "Özel büküm saçak sacı", "L 2500", ob["sacak"], "Pafta", "özel büküm saçlar paftası", "PK-07 2 tuttu")
    alin = sum((2 * c["kalkan"] if c["tip"] == "besik" else 2) * o["egik"] for c, o in C)
    ekle("1002", "Alın sacı (30'luk)", "300 × 2500", TAVAN(alin / (_kural(k, "parca_boyu_m", "alin_saci") - _kural(k, "bindirme_m", "alin_saci"))) - ob.get("alin", 0),
         "Kural", f"alın eğik kenarları {alin:.2f} m ÷ 2,3" + (f" − özel büküm {ob['alin']}" if ob.get("alin") else ""), "PK-01 ve PK-02'de tuttu; PK-07 9 + 2")
    if ob.get("alin"):
        ekle("1002", "Özel büküm alın sacı", "L 2500", ob["alin"], "Pafta", "özel büküm saçlar paftası", "PK-07 2 tuttu")
    kk = lambda c: 0 if c.get("acik") else c["kalkan"]          # N1: açık çatı parçasının kalkanının altında duvar yok (PK-06 veranda)
    kalkan = sum((c["kalkan_duvar_cm"] / 100 if c.get("kalkan_duvar_cm") is not None else kk(c) * c["aciklik_cm"] / 100) for c, _o in C)   # 6.1: paftadaki kalkan duvarı
    kalkan_s = sum(kk(c) * (c["aciklik_cm"] / 100 + 2 * o["sac"]) for c, o in C)
    acik_not = " (açık çatı parçası sayılmaz, N1)" if any(c.get("acik") for c, _o in C) else ""
    ekle("1002", "Baş makas omegası", "L 2500", TAVAN(kalkan / 2.5), "Kural (Portatifev)", f"kalkan duvarları {kalkan:.2f} m ÷ 2,5 (PK-01 dersi 5)" + acik_not,
         "PK-06 7 tuttu (N1)", aday=TAVAN(kalkan_s / 2.5), aday_notu=f"Loftev (PK-02 7 ✓): saçaklı makas boyu {kalkan_s:.2f} m ÷ 2,5")
    ekle("1002", "Baş makas Z'si", "L 2800", kk(ana) * (2 if ana["tip"] == "besik" else 1) * TAVAN(ao["egik"] / 2.8), "Kural (O7)",
         "ana çatının alın kenarları (beşikte kalkan × 2, tek yönde kalkan × 1) × ⌈eğik ÷ 2,8⌉",
         "PK-07 8, PK-06 8, PK-02 8 tuttu; PK-01'de 0")
    bet = 0
    for c, o in C:
        if kk(c):
            yuks = (c["aciklik_cm"] / (200 if c["tip"] == "besik" else 100) + o["sac"] * (1 if c["tip"] == "besik" else 2)) * o["eg"]
            bet += kk(c) * TAVAN(1.5 * 0.5 * (c["aciklik_cm"] / 100 + 2 * o["sac"]) * yuks / 3.125)
    ekle("1002", "Baş makas betopanı", "1250 × 2500", bet, "Kural (H5)", "kalkan başına ⌈1,5 × saçaklı üçgen ÷ 3,125⌉" + acik_not, "PK-01 4, PK-02 6, PK-06 6")
    dis_boy = sum(p["boy"] for p in N["panolar"] if p["duvar"] == "dis") / 100
    if ic_kal >= 100:                                           # O8: iç duvar 100 → tek satır (PK-07 16)
        ekle("1002", "100'lük alt çerçeve", "100 × 3750", TAVAN((N["dis_cevre_m"] + L_duvar) / 3.75), "Şablon formülü (H4, O8)",
             f"(dış çevre {N['dis_cevre_m']:.2f} + iç duvar {L_duvar:.2f}) m ÷ 3,75", "PK-07 16 tuttu")
    else:
        ekle("1002", "100'lük alt çerçeve", "100 × 3750", TAVAN(N["dis_cevre_m"] / 3.75), "Şablon formülü (H4)", f"dış çevre {N['dis_cevre_m']:.2f} m ÷ 3,75",
             "PK-01 9, PK-02 9 tuttu")
        ekle("1002", "60'lık alt çerçeve", "60 × 3750", TAVAN(L_duvar / 3.75), "Kural (Lokman 13.10, R1)", f"iç duvarlar {L_duvar:.2f} m ÷ 3,75",
             "Lokman: alt çerçeve her zaman 3750 (2026 listelerinde 60 × 2500 yazıyordu)", aday=TAVAN(L_duvar / 2.5), aday_notu="listelerdeki L 2500")

    if kubbeler:
        kubbe_takimi("1002")

    # ── 1003 Kapı ve pencere ────────────────────────────────────────────────
    for a in (a for a in acl if a["tur"] == "dis_kapi"):
        kapi_alici = a.get("dograma") == "alıcıya ait" or "alıcı" in oz.get("dış kapı", "")
        ekle("1003", f"Prefabrik çelik kapı ({'SAĞ' if a.get('mentese') == 'sag' else 'SOL'})", "900 × 2000", 0 if kapi_alici else 1, "Sayım",
             kaynak_ad + ("; alıcıya ait" if kapi_alici else "") + f"; ölçü listede her zaman 90 × 200 (L4; çizimde {mm(a['genislik'])})")
    kapilar = Counter(a.get("mentese") for a in acl if a["tur"] == "ic_kapi")
    for ment, n in sorted(kapilar.items(), key=lambda x: str(x[0])):
        ekle("1003", f"Amerikan kapı (80'lik kanat) ({'SAĞ' if ment == 'sag' else 'SOL' if ment == 'sol' else '?'})", "82 × 196", n, "Sayım",
             "menteşe D-13 (PK-01 3 / 2, PK-02 1 / 3 tuttu)")
    if pencere_alici:
        ekle("1003", "Pencere grubu", "—", 0, "İş Emri", "alıcıya ait (PK-01 dersi 1)")
    else:
        for olcu, n in sorted(Counter(a["olcu"] for a in pen).items()):
            en, boy = pencere_olcusu(olcu)
            ekle("1003", "PVC vasistas" if (en <= 60 and boy <= 60) else "PVC pencere", f"{en}/{boy}", n, "Sayım", kaynak_ad)

    # ── 1004 Tavan ──────────────────────────────────────────────────────────
    ekle("1004", "Tavan beyaz alçıpan", "1200 × 2500", ASAGI(tavan_kuru * 1.05 / 3 + 2), "Şablon formülü (H6)",
         f"kuru tavan {tavan_kuru:.2f} m² × 1,05 ÷ 3 + 2, aşağı", "PK-02 18 tuttu; PK-01 elle 8", aday=TAVAN(bina_m2 / 3) - (TAVAN(sum(x['alan_m2'] for x in N['acik']) / 3) if N['acik'] else 0),
         aday_notu="sürüm 1–2 (P6001): brüt ÷ 3, yeşil düşülür")
    ekle("1004", "Tavan yeşil alçıpan", "1200 × 2500", ASAGI(tavan_islak * 1.05 / 3 + 1) if tavan_islak else 0, "Şablon formülü (H6)",
         f"ıslak hacim {tavan_islak:.2f} m² × 1,05 ÷ 3 + 1, aşağı", "PK-02 3 tuttu; veranda tavanı soru 5")
    if "alçıpan" in oz.get("açıklama", "") or "alçıpan" in oz.get("iç cephe kaplaması", ""):
        L_dis_ic = sum(p["boy"] for p in N["panolar"] if p["duvar"] == "dis") / 100
        bosluk = sum((pencere_olcusu(a["olcu"])[0] * pencere_olcusu(a["olcu"])[1] / 1e4) for a in pen) + \
            sum(0.82 * 2.0 * (2 if a["tur"] == "ic_kapi" else 1) for a in acl if a["tur"] in ("ic_kapi", "dis_kapi"))
        yuzey = (2 * L_duvar + L_dis_ic) * H0 / 100 - bosluk
        islak_duvar = sum(2 * (x["en_cm"] + x["derin_cm"]) / 100 for x in N["kapali"] if x["tur"] in ISLAK) * H0 / 100
        duvar_top = TAVAN(yuzey * 1.05 / 3); duvar_yesil = ASAGI(islak_duvar * 1.05 / 3)
        ekle("1004", "Duvar alçıpanı beyaz", "1200 × 2500", duvar_top - duvar_yesil, "Kural (uydurma)",
             f"duvar yüzeyi (2 × iç {L_duvar:.2f} + dış iç yüzü {L_dis_ic:.2f}) × {H0 / 100:g} − boşluklar {bosluk:.2f} = {yuzey:.1f} m² × 1,05 ÷ 3 = {duvar_top}, yeşil düşülür",
             "paftanın açıklaması \"iç cephede alçıpan kaplama\"; PK-03 toplam 61 (62 tahmin)")
        ekle("1004", "Duvar alçıpanı yeşil", "1200 × 2500", duvar_yesil, "Kural (J7)", f"ıslak hacim duvarları {islak_duvar:.1f} m² × 1,05 ÷ 3, aşağı", "PK-03 7 (banyo)")
        ekle("1004", "Alçıpan destek straforu", "paket / 60 m²", TAVAN(yuzey / 60), "Kural (J7)", f"duvar yüzeyi {yuzey:.1f} m² ÷ 60", "PK-03 3")
    if fugali:                                                  # O1: fugalı cephe; ayrı betopan levhası yok, latalar var (PK-07)
        kose_n = kc.get("dis", 0) + (kc.get("ic", 0) if ic_kal >= 100 else 0)
        dis_ek = ec[("dis", "pano_eki")] + ec[("dis", "uclu")]
        ekle("1004", "H'lar için lata (10 mm betopan, oymalı)", "100 × 2500", dis_ek + 3, "Kural (Lokman 13.10, R5)",
             f"dış 100'lük duvar H'ları {dis_ek} (dış H + dış 3'lü H) + 3 yedek", "PK-07 30 tuttu")
        ekle("1004", "Köşe latası", "150 × 2500", kose_n, "Kural (O1)", "10'luk köşe direği başına", "PK-07 5 tuttu")
        ekle("1004", "Köşe latası", "130 × 2500", kose_n, "Kural (O1)", "10'luk köşe direği başına", "PK-07 5 tuttu")
        cevre_l = sum(2 * sum(pencere_olcusu(a_["olcu"])) / 100 for a_ in pen) + sum(2 * 2.0 + 0.9 for a_ in acl if a_["tur"] == "dis_kapi")
        n28 = ASAGI(cevre_l / 2.8 + 1e-9); kalan = cevre_l - n28 * 2.8
        ekle("1004", "Pencere latası", "100 × 2800", n28, "Kural (O1)", f"pencere çevreleri + dış kapı (2 boy + en) = {cevre_l:.2f} m ÷ 2,8, aşağı", "PK-07 10 tuttu")
        ekle("1004", "Pencere latası", "100 × 2500", TAVAN(kalan / 2.5) if kalan > 0.05 else 0, "Kural (O1)", f"artan {kalan:.2f} m ÷ 2,5", "PK-07 1 tuttu")
    if N["acik"]:
        ver = sum(x["alan_m2"] for x in N["acik"])
        ekle("1004", "Veranda tavan Boardex", "8 × 1200 × 2400", TAVAN(ver * 1.08 / 2.88), "Şablon formülü (O14)", f"veranda {ver:.2f} m² × 1,08 ÷ 2,88",
             "PK-07 2 tuttu; PK-01'de 0")
    if not ters:
        ekle("1004", "Tavan H'ı L 1185 (asma dizme tavan)", "adet", TAVAN(tavan_net / (ASMA_OMEGA_ARALIK_M * TAVAN_H_ARALIK_M) + 5), "Şablon formülü (Portatifev)",
             f"net tavan {tavan_net:.2f} m² ÷ (1,255 × 0,625) + 5", "PK-01 66, PK-02 75")
        ekle("1004", "PVC omega kapak L 3750 (asma dizme tavan)", "adet", TAVAN(L_hat / 3.65 + 3), "Şablon formülü (Portatifev)",
             f"oda içi omega hatları {L_hat:.2f} m ÷ 3,65 + 3", "PK-01 10 tuttu", aday=TAVAN(L_hat / 3.65), aday_notu="Loftev (PK-02 11 ✓): \"+3\"süz")
    ekle("1004", "PVC plastik betopan H'ı", "adet", 5, "Kural (Portatifev)", "standart 3–5; PK-01 5 (J6: tavan tipinden bağımsız)", aday=3, aday_notu="Loftev (PK-02, PK-03): 3")
    ekle("1004", "Çatı şiltesi / izolasyonu (9,6 m²/paket)", "paket", TAVAN(bina_m2 / _kural(k, "silte_adet_m2")), "Liste kuralı", f"brüt {bina_m2:.2f} ÷ 9,6",
         "Portatifev kaba hesabı ≈ brüt ÷ 9,6 (PK-01 6,4; girilen 4)",
         aday=TAVAN(sum((c["aciklik_cm"] / 100 + 2 * o["sac"]) * o["mahya_boy"] for c, o in C if not c.get("acik")) / 9.6),
         aday_notu="Loftev (PK-02 7, PK-06 11 ✓): saçaklı çatı tabanı ÷ 9,6; açık çatı parçası (veranda) şilte almaz (N1)")

    # ── 1005 Makas ──────────────────────────────────────────────────────────
    n_makas_top, asik_top, asik_aday = 0, 0, 0
    for c, o in C:
        ad = c.get("ad", "çatı")
        if c.get("makas_yok"):
            ekle("1005", f"Çatı paneli (hafif çelik) · {ad}", "—", None, "Kural yok", "makas ve aşık yerine hafif çelik çatı paneli", c.get("not", ""), pafta=("cati_paneli",))
            continue
        n_m = TAVAN(c["makas_kosu_cm"] / MOD - 1e-6) + 1
        n_makas_top += n_m
        if c is not ana:
            ekle("1005", f"Yavru makas · {ad}", f"L {round((c['aciklik_cm'] + 2 * c['sacak_cm']) * 10)}", n_m, "Kural (J8)",
                 f"ek çatı parçasının pano koşusu {mm(c['makas_kosu_cm'])} ÷ 1255 yukarı + 1", "PK-03: yavru makas 3 (MK10–MK12)")
        else:
            if c["kalkan"]:
                ekle("1005", f"Makas (baş) · {ad}", f"açıklık {mm(c['aciklik_cm'])}", c["kalkan"], "Kural", "kalkan duvarlarının üstünde", "", pafta=("makas_bas",))
            ekle("1005", f"Makas (orta) · {ad}", f"açıklık {mm(c['aciklik_cm'])}", n_m - c["kalkan"], "Kural (P1)",
                 f"saçak duvarının pano koşusu {mm(c['makas_kosu_cm'])} ÷ 1255 yukarı + 1 = {n_m}" + (f", − {c['kalkan']} baş" if c["kalkan"] else ""),
                 "PK-01 9, PK-02 7, PK-03 9 tuttu", pafta=("makas_orta",))
        sira = int(math.floor((o["egik"] - (0.20 if o["yuz"] == 2 else 0)) / _kural(k, "asik", "aralik_m") + 0.5)) + 1   # O13: en yakın (PK-06, PK-07 paftaları 8)
        asik_boy = o["yuz"] * sira * o["mahya_boy"]
        asik_top += asik_boy
    ekle("1005", "Aşık", "L 4200", TAVAN(asik_top * (1 + _kural(k, "asik", "zayiat")) / _kural(k, "parca_boyu_m", "asik")), "Kural (P2)",
         f"aşık boyları {asik_top:.1f} m × 1,05 ÷ 4,2 (yüz başına (eğik − 0,20) ÷ 0,60 en yakın + 1 sıra)", "PK-01 36 (elle), PK-02 35",
         pafta=("asik",), aday=TAVAN(asik_top / 4.1 + 5), aday_notu="Portatifev kaba hesabı: ÷ 4,1 + 5")

    if kubbeler:
        kubbe_takimi("1005")

    # ── 1006 Çatı ───────────────────────────────────────────────────────────
    kap = oz.get("çatı kaplaması", "")
    sandvic = "sandvi" in kap
    trapez = "trapez" in kap
    kap_m = _kural(k, "sandvic_panel_kapatma_m") if sandvic else (_kural(k, "trapez_sac_kapatma_m") if trapez else TEK_KAT_KAPATMA_M)
    yuvarla_mm = 100 if (sandvic or trapez) else 50
    boy_mm = lambda e_: int(math.ceil(e_ * 1000 / yuvarla_mm - 1e-9) * yuvarla_mm)
    n_pan = 0
    for c, o in C:
        L_pan = boy_mm(o["egik"])
        n = o["yuz"] * TAVAN(o["mahya_boy"] / kap_m - 1e-9) if c is ana else TAVAN(o["yuz"] * o["mahya_boy"] / kap_m)   # O9: ana çatı yüz başına
        n_pan += n
        ad = "Sandviç panel (100 cm kapatır)" if sandvic else ("Trapez sac" if trapez else "Tek kat çatı paneli")
        ekle("1006", f"{ad} · {c.get('ad', 'çatı')}", f"L {L_pan}", n, "Kural (P3, O9)",
             (f"{o['yuz']} yüz × ⌈{o['mahya_boy']:.2f} m ÷ {kap_m:g}⌉" if c is ana else f"⌈{o['yuz']} yüz × {o['mahya_boy']:.2f} m ÷ {kap_m:g}⌉") + f"; boy eğik {o['egik']:.3f} m yukarı",
             "PK-01 22, PK-07 18 (yüz başına) tuttu", pafta=("sandvic_panel",) if c is ana else None,
             aday=TAVAN(o["yuz"] * o["mahya_boy"] / kap_m) if c is ana and o["yuz"] > 1 else None, aday_notu="Loftev (PK-02 17 ✓): iki yüz toplam yukarı" if c is ana and o["yuz"] > 1 else "")
    pm, bm = _kural(k, "parca_boyu_m", "mahya"), _kural(k, "bindirme_m", "mahya")
    if trapez:
        mahya = sum(TAVAN(o["mahya_boy"] / 0.8) for c, o in C if c["tip"] == "besik")
        ekle("1006", "Trapez sac mahyası", "L 1000", mahya, "Kural (J5)", "beşik mahyaları ÷ 0,8 (L 1000, 20 cm bindirme)", "PK-03 15 tuttu")
    else:
        mahya = TAVAN(sum(o["mahya_boy"] for c, o in C if c["tip"] == "besik") / (pm - bm))   # O10: toplam ÷ 2,6 (PK-06 6, PK-07 4)
        ekle("1006", "Metal kiremit mahyası", "L 2800", mahya, "Kural (O10)", "beşik mahyalarının toplamı ÷ 2,6", "PK-01, PK-02, PK-06, PK-07 tuttu")
    ters_m = 0.0
    for c, o in C:
        if c is not ana and c["tip"] == "besik" and c.get("capraz", True):      # 5.1: ana çatıya paralel ek beşikte dere içi yok
            a_ = c["aciklik_cm"] / 200 + o["sac"]; h_ = a_ * o["eg"]; b_ = h_ / max(ao["eg"], 1e-6)
            ters_m += 2 * math.sqrt(a_ * a_ + b_ * b_ + h_ * h_)
    if ters_m:
        ekle("1006", "Ters mahya (dere içi)", "L 2800", TAVAN(ters_m / 2.6), "Kural (J5)", f"çapraz beşiğin iki deresi {ters_m:.2f} m ÷ 2,6", "PK-03 4 tuttu")
    if sandvic:
        ekle("1006", "Sandviç panel kapaması", "L 2800", TAVAN(sacak_m / 2.5), "Kural (O11)", f"saçak kenarları {sacak_m:.2f} m ÷ 2,5",
             "PK-07 10, PK-02 7 tuttu; PK-01'de 0")
    else:
        ekle("1006", "Panel kapaması", "L 2500", None, "Kural yok", "—", "PK-05 tek kat 6 (alın ÷ 2,5), PK-06 16", aday=TAVAN(sacak_m / 2.5), aday_notu="saçak ÷ 2,5")
    ekle("1006", "Mahya bandı", "rulo 10 m", TAVAN(mahya * 2.8 / 10), "Şablon formülü (Portatifev)", f"mahya {mahya} × 2,8 ÷ 10", "PK-01 2 tuttu; Loftev'de yok")

    if kubbeler:
        kubbe_takimi("1006")

    # ── 1007 Elektrik (montaj paftasındaki elektrik planından; kurallar.json › elektrik) ──
    el = P.get("elektrik") or {}
    if el:
        es = lambda a: (el.get(a) or {}).get("adet")
        priz = (es("priz_tekli") or 0) + 2 * (es("priz_cift") or 0)
        anah = (es("anahtar_tekli") or 0) + 2 * (es("anahtar_cift") or 0)
        for kalem, adet, formul in (("Tijli duy", es("tavan_armaturu"), "tavan armatürü"), ("Yuvarlak glop", es("glop"), "ıslak hacim glopu (H1)"),
                                    ("Ampul", (es("tavan_armaturu") or 0) + (es("glop") or 0), "duy + glop; dış aplik girmez (H1)"),
                                    ("Tekli anahtar (takım)", es("anahtar_tekli"), ""), ("Çiftli anahtar (takım)", es("anahtar_cift"), ""),
                                    ("Tekli priz (takım)", es("priz_tekli"), ""), ("Çiftli priz (takım)", es("priz_cift"), ""), ("Uydu prizi (takım)", es("uydu_prizi"), ""),
                                    ("Zil", es("zil"), ""), ("Sigorta kutusu (12'li)", es("sigorta_kutusu"), "")):
            ekle("1007", kalem, "adet", adet, "Sayım (pafta)", formul or "elektrik planından", "göz sayımı; kurallar.json › elektrik")
        nokta = sum((es(a_) or 0) for a_ in ("anahtar_tekli", "anahtar_cift", "priz_tekli", "priz_cift", "uydu_prizi", "zil", "tavan_armaturu", "glop"))
        ekle("1007", "Buat kasa", "adet", nokta, "Kural (O19)", "bütün elektrik noktaları (anahtar, priz, uydu, zil, duy, glop)", "PK-07 31 tuttu")
        ekle("1007", "NYM kablo 3 × 2,5", "metre", 130, "Kural (Portatifev)", "PK-01 130 (PK-02 135)", aday=20 + priz * 2, aday_notu="şablon: sigorta × en uzun (≈ 20 m) + priz × 2")
        ekle("1007", "NYM kablo 2 × 1,5", "metre", 100, "Kural (Portatifev)", "PK-01 100 (PK-02 120)", aday=20 + anah * 2, aday_notu="şablon: sigorta × en uzun (≈ 20 m) + anahtar × 2")
        ekle("1007", "Uydu kablo", "metre", 25 * (es("uydu_prizi") or 0), "Şablon formülü", "uydu prizi × 25 m", "PK-02 tuttu")
        ekle("1007", "Besleme kablosu", "metre", 5, "Şablon formülü", "kat × 5 m", "PK-02 tuttu")
        ekle("1007", "Besleme kablo borusu", "metre", 5, "Şablon formülü", "kat × 5 m", "PK-02 tuttu")
        ekle("1007", "İzole bant", "adet", TAVAN(bina_m2 * 6 / 100), "Şablon formülü", "m² × 6 ÷ 100", "PK-02 tuttu")
        ekle("1007", "Kaçak akım rölesi (ikili)", "adet", 1, "Şablon formülü", "tek kat 1 ikili", "PK-02 tuttu")
        ekle("1007", "W otomat 16 A", "adet", 8, "Kural (Lokman 13.10, R4)", "Portatifev şablonu sabit 8 (alandan bağımsız)",
             "PK-07, E2, E3, E5 8", aday=9, aday_notu="Loftev şablonu sabit 9 (PK-02, -03, -05, -06, E1, E4)")
    else:
        ekle("1007", "Elektrik grubu", "—", None, "Kural yok", "elektrik planı yok", "kurallar.json › elektrik")

    # ── 1008 Vida ───────────────────────────────────────────────────────────
    ekle("1008", "16 mm betopan ve kapı kolu vidası (3,9 × 32)", "adet", 500, "Kural (O16)", "sabit 500", "PK-07 ve Loftev 500 tuttu; PK-01 250")
    L_vida = sum(boy_mm(o["egik"]) / 200 * TAVAN(o["yuz"] * o["mahya_boy"] / kap_m) for c, o in C)
    ekle("1008", "Trapez vida 5,5 × 110 (sandviç panel)" if sandvic else ("Trapez vida 5,5 × 60 (trapez sac)" if trapez else "Trapez vida 5,5 × 76 (tek kat panel)"),
         "adet", int(math.ceil(L_vida / 100 - 1e-9) * 100),
         "Şablon formülü (Portatifev)", f"panel boyu ÷ 200 × panel adedi = {L_vida:.0f}, 100'e yukarı", "PK-01 385 → 400",
         aday=int(math.ceil(L_vida / 250 - 1e-9) * 250), aday_notu="Loftev (PK-02 500 ✓): 250'nin katına yukarı")
    if pen:                                                     # O12: pencere alıcıya ait olsa da montaj vidası bizde (PK-07 120)
        ekle("1008", "Prefabrik pencere vidası (4,8 × 70)", "adet", 20 * len(pen), "Kural (H2, O12)", "pencere × 20", "PK-02 100, PK-07 120 tuttu; PK-01'de 0")
    if not trapez:                                              # 7.1: trapez çatıda 5,5 × 60 zaten kaplama vidası satırında
        ekle("1008", "Trapez vida 5,5 × 60 (trapez sac / metal kiremit)", "adet", int(math.ceil(bina_m2 * 2.5 / 100 - 1e-9) * 100), "Kural (O16)",
             "m² × 2,5, 100'e yukarı (kural kitabı: Excel motoru)", "PK-07 200 tuttu", aday=int(math.ceil(bina_m2 * 2.5 / 250 - 1e-9) * 250), aday_notu="Loftev: 250'nin katı")
    ekle("1008", "230'luk kesme taşı", "adet", TAVAN(bina_m2 * 0.02), "Kural (O16)", "m² × 0,02 (kural kitabı)", "PK-06 2, PK-07 2 tuttu")
    ekle("1008", "Çırpı ipi", "adet", 1, "Kural (O16)", "sabit 1", "PK-02, PK-05, PK-06, PK-07 1")
    inox_vb = ASAGI(bina_m2 / 10)                                # N3 adayı: listedeki "VİDA BİLGİ" sayfası (PK-06)
    ekle("1008", "8'lik trapez uç", "adet", TAVAN(bina_m2 / 15), "Şablon formülü", "m² ÷ 15", "PK-01 ve PK-02'de tuttu",
         aday=inox_vb // 2, aday_notu="\"VİDA BİLGİ\": inox ÷ 2 (yalnız PK-06 4 ✓; PK-01…05 4–6)")
    ekle("1008", "PH2 uç", "adet", TAVAN(bina_m2 / 15), "Şablon formülü", "m² ÷ 15", "PK-01 ve PK-02'de tuttu",
         aday=inox_vb // 2, aday_notu="\"VİDA BİLGİ\": inox ÷ 2 (yalnız PK-06 4 ✓; PK-01…05 4–6)")
    ekle("1008", "İnox taş", "adet", TAVAN(bina_m2 / 10), "Şablon formülü", "m² ÷ 10", "PK-01 ve PK-02'de tuttu",
         aday=inox_vb, aday_notu="\"VİDA BİLGİ\": bina m² ÷ 10, aşağı (PK-01, -05, -06 ✓; PK-02, -03 ✗)")
    lev = ASAGI(tavan_kuru * 1.05 / 3 + 2) + (ASAGI(tavan_islak * 1.05 / 3 + 1) if tavan_islak else 0)
    duvar_lev = sum(s_["adet"] or 0 for s_ in satirlar if s_["kalem"].startswith("Duvar alçıpanı"))
    if duvar_lev:
        ekle("1008", "Alçıpan vidası", "adet", int(math.ceil((lev + duvar_lev) * 40 / 250 - 1e-9) * 250), "Şablon formülü (J7)",
             f"(tavan {lev} + duvar {duvar_lev}) levha × 40, 250'nin katına", "PK-03 3750 tuttu")
    else:
        ekle("1008", "Alçıpan vidası", "adet", int(math.ceil(lev * 40 / 250 - 1e-9) * 250), "Şablon formülü (O16)", f"tavan {lev} levha × 40, 250'nin katına",
             "PK-07 1000 tuttu; PK-01'de 0", aday=250, aday_notu="Loftev (PK-02, PK-05): 250")
    ekle("1008", "RYSB pul başlı vida", "adet", int(math.ceil(bina_m2 * 7.5 / 50 - 1e-9) * 50), "Şablon formülü (O16)", "m² × 7,5, 50'ye yukarı",
         "PK-07 550 tuttu; PK-01'de 0", aday=int(math.ceil(bina_m2 * 7.5 / 250 - 1e-9) * 250), aday_notu="Loftev (PK-02 500 ✓): 250'nin katına")

    # ── 1009 Depo ───────────────────────────────────────────────────────────
    ekle("1009", "Acil müdahale kapağı", "adet", 0 if any("acil" in x for x in alici) else 1, "Şablon formülü (Portatifev)",
         "sabit 1" + (" (alıcıya ait)" if any("acil" in x for x in alici) else ""), "Loftev'de yok")
    ekle("1009", "Şase pul", "adet", dubelli, "Şablon formülü (Portatifev)", f"dübelli H adedi kadar (dış H {ec[('dis', 'pano_eki')]} + dış 3'lü H {ec[('dis', 'uclu')]})",
         "PK-01 24 tuttu", aday=0, aday_notu="Loftev: şase pul yok")
    ekle("1009", "Çelik dübel", "adet", dubelli, "Şablon formülü (O16)", "dübelli H adedi kadar", "PK-07 27, PK-02 22, PK-06 24 tuttu; PK-01'de 0")
    ekle("1009", "Çatı müdahale kapağı", "adet", 1, "Kural (O16)", "sabit 1", "PK-07 1")

    # ── 1010 Sıhhi tesisat ──────────────────────────────────────────────────
    tes_alici = any("tesisat" in x for x in alici)
    if tes_alici:
        ekle("1010", "Sıhhi tesisat grubu", "—", 0, "İş Emri", "alıcıya ait")
    elif any(x["tur"] in ISLAK for x in N["kapali"]):           # O17: bir banyolu evde sabit takım (PK-03, PK-05, PK-07 birebir)
        for kalem, olcu, n in (("Temiz su borusu", "L 4000", 6), ("Normal dirsek 20 mm", "adet", 15), ("Kulaklı dirsek 20 mm", "adet", 12),
                               ("Düz T 20 mm", "adet", 6), ("Maşon 20 mm", "adet", 15), ("İç dişli T 20 mm", "adet", 6), ("Atlama parçası yarım parmak", "adet", 3)):
            ekle("1010", kalem, olcu, n, "Kural (O17)", "sabit takım (bir banyo)", "PK-03, PK-05, PK-07 tuttu; PK-06 (üç ıslak nokta) boru 10, dirsek 20")
        vit_alici = any("vitrifiye" in x for x in alici)
        ekle("1010", "Vitrifiye ve batarya (duş teknesi, klozet, lavabo, batarya grubu)", "takım", 0 if vit_alici else None, "İş Emri" if vit_alici else "Kural yok",
             "alıcıya ait" if vit_alici else "—", "PK-07'de 4 satır × 1", aday=None if vit_alici else 1, aday_notu="" if vit_alici else "PK-07")
    else:
        ekle("1010", "Sıhhi tesisat grubu", "—", None, "Kural yok", "—", "ıslak hacim yok")

    # ── 1011 Dere ───────────────────────────────────────────────────────────
    kanopi = lambda c: bool(c.get("dere_yok") or (c.get("acik") and c.get("makas_yok")))   # O15: veranda saçağı (makassız sandviç) dere almaz (PK-07); 7.1: `dere_yok`
    dere_hat = [x for c, o in C if not kanopi(c) for x in o["hatlar"]]
    pd_, bd = _kural(k, "parca_boyu_m", "dere"), _kural(k, "bindirme_m", "dere")
    dere = TAVAN(sum(dere_hat) / (pd_ - bd))
    ekle("1011", "Metal dere", "L 4000", dere, "Şablon formülü (J3)", f"dere hatları {' + '.join(f'{x:.2f}' for x in dere_hat)} = {sum(dere_hat):.2f} m ÷ 3,8",
         "PK-01 6, PK-03 5 tuttu",
         aday=" + ".join(f"{n} × L {L_}" for L_, n in sorted(Counter(int(math.ceil(x * 2 - 1e-9) * 500) for x in dere_hat).items())),
         aday_notu="Loftev (PK-02 2 × L 8500 ✓): hat başına tek parça, 500'e yukarı")
    ekle("1011", "Dere kelepçesi", "adet", dere * _kural(k, "dere_kelepcesi_dere_basina"), "Kural", "dere × 8", "PK-01 48 tuttu (PK-02 50)")
    ins = _kural(k, "inis")
    n_cumba = sum(1 for c, _o in C[1:] if not kanopi(c))
    orta_esik = sum(1 for x in ao["hatlar"] if x > ins["orta_inis_esigi_m"])
    orta = len(ao["hatlar"])                                     # R3: her saçak hattının ortasına 1 (Lokman 13.10)
    taban = 4 if ana["tip"] == "besik" else 2
    inis = taban * ins["kose_basina"] + orta + 2 * n_cumba
    ekle("1011", "Metal dere inişi aparatı", "adet", inis, "Kural (Lokman 13.10, R3)",
         f"ana çatıda {taban} köşe + saçak hattı başına 1 orta ({orta}) + ek çatı parçası başına 2 ({n_cumba})",
         "E1, E4, E5, PK-01, PK-03 6; PK-07 8", pafta=("inis",), aday=taban * ins["kose_basina"] + orta_esik + 2 * n_cumba,
         aday_notu=f"eski kural: yalnız {ins['orta_inis_esigi_m']:g} m'yi geçen saçağa orta")
    if "metal" in oz.get("yağmur iniş borusu", ""):
        ekle("1011", "Metal iniş borusu", "L 3000", inis, "Kural (H3)", "özellik: metal iniş borusu → iniş başına L 3000", "PK-02 tuttu")
    else:
        ekle("1011", "70 mm PVC dere iniş borusu", "L 2000", inis, "Kural (Lokman 13.10, R2)", "iniş başına L 2000 (PVC; 2000 + 500 = bina yüksekliği 2500)",
             "PK-03, -05, -06, E1–E4 L 2000", aday=f"{inis} × L 2500", aday_notu="PK-01, E5: L 2500")
        ekle("1011", "70 mm PVC dere iniş borusu", "L 500", inis, "Kural (PK-01)", "iniş başına L 500 (PVC)")
    ib = _kural(k, "inis_basina")
    for kalem, anahtar in (("Açık dirsek", "acik_dirsek"), ("Kapalı dirsek", "kapali_dirsek"), ("PVC iniş kelepçesi", "inis_kelepcesi")):
        ekle("1011", kalem, "adet", inis * ib[anahtar], "Kural", f"iniş × {ib[anahtar]}", "PK-01 ve PK-02'de tuttu")
    ekle("1011", "Dere kapağı", "adet", taban + 2 * n_cumba, "Kural (J4)", f"ana çatıda {taban} (beşik 4, tek yön 2) + ek çatı parçası başına 2 (kurallar.json › dere_kapagi.besik_cumba 6)",
         "PK-01 4, PK-02 4, PK-03 6 tuttu")

    # ── 1012 Boya ───────────────────────────────────────────────────────────
    boya_alici = any("boya" in x for x in alici) or ("alıcı" in oz.get("dış cephe boya", "") and "alıcı" in oz.get("iç cephe boya", ""))
    if boya_alici:
        ekle("1012", "Boya grubu ve mastik", "—", 0, "İş Emri", "alıcıya ait")
    else:
        ekle("1012", "Dış cephe boya (17,5 kg kova)", "kova", TAVAN(bina_m2 * 2 / 100), "Şablon formülü", "m² × 2 ÷ 100", "PK-07 2 tuttu (O18)")
        ekle("1012", "İç cephe boya (17,5 kg kova)", "kova", TAVAN(bina_m2 * 2 / 100), "Şablon formülü", "m² × 2 ÷ 100", "PK-07 2 tuttu (O18)")
        ekle("1012", "Kenarlar için boya", "10 kg", 1, "Kural (O18)", "sabit 1", "PK-07 1")
        ekle("1012", "Tavan boya (17,5 kg kova)", "kova", 1, "Kural (O18)", "sabit 1", "PK-07 1")
        ekle("1012", "Astar (17,5 kg kova)", "kova", 1, "Kural (O18)", "sabit 1", "PK-07 1")
        ekle("1012", "Silikonize mastik", "adet", len(pen) + TAVAN(bina_m2 * 2 / 3), "Şablon formülü", "mantolama yok: pencere + m² × 2/3", "PK-02'de 60")
    ekle("1012", "Dayson (çatı renginde)", "adet", TAVAN(bina_m2 * 0.03), "Şablon formülü (O18)", "beşikte m² × 0,03, yukarı", "PK-06 3, PK-07 3 tuttu; PK-01 1 (aşağı)")
    ekle("1012", "Poliüretan köpük", "adet", 2, "Şablon formülü (O18)", "standart 2", "PK-02, PK-05, PK-06, PK-07 2 tuttu; PK-01'de 0")

    say = {"geometri": N["kaynak"], "pano_dis": sum(p["duvar"] == "dis" for p in N["panolar"]), "pano_ic": sum(p["duvar"] == "ic" for p in N["panolar"]),
           "brut_m2": bina_m2, "dis_olcu_cm": [round(N["W"], 2), round(N["D"], 2)], "dis_cevre_m": round(N["dis_cevre_m"], 2),
           "cati": [{"ad": c.get("ad"), "tip": c["tip"], "egik_m": round(o["egik"], 3), "mahya_m": round(o["mahya_boy"], 3)} for c, o in C],
           "tavan_net_m2": round(tavan_net, 2), "tavan": tavan_tipi, "makas": n_makas_top, "omega_hat_m": round(L_hat, 2), "ic_duvar_m": round(L_duvar, 2)}
    return {"is_emri_no": N.get("is_emri_no"), "kod": N.get("kod"), "uretici_surum": SURUM,
            "uretildi": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "kural_seti": k.get("surum") or k.get("sema"), "girdi_ozeti": say,
            "satirlar": satirlar,
            "ozet": {"satir": len(satirlar), "adetli": sum(s["adet"] is not None for s in satirlar), "kural_yok": sum(s["dayanak"] == "Kural yok" for s in satirlar),
                     "pafta_katmanli": sum(s["pafta"] is not None for s in satirlar), "aday_li": sum(s["aday"] is not None for s in satirlar)}}


def xlsx(L: dict, yol: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Liste"
    ws.append([f"{L['kod']} · kendi yükleme listemiz (kör test; gerçek liste açılmadan) · {L['is_emri_no']} · üretici {L['uretici_surum']} · {L['uretildi']}"])
    ws.append(["Grup", "Kalem", "Ölçü", "Adet", "Birim", "Dayanak", "Formül", "Kaynak / not", "Pafta", "Pafta notu", "Aday", "Aday notu"])
    for c_ in ws[2]:
        c_.font = Font(bold=True, color="FFFFFF"); c_.fill = PatternFill("solid", fgColor="2F3B4C")
    renk = {"Kural yok": "F2F2F2", "Liste kuralı": "FFF2CC", "Kural (uydurma)": "FCE4D6", "Kural (Portatifev)": "DDEBF7"}
    for s in L["satirlar"]:
        ws.append([f"{s['grup']} {s['grup_adi']}", s["kalem"], s["olcu"], s["adet"], s["birim"], s["dayanak"], s["formul"], s["kaynak"], s["pafta"],
                   s["pafta_notu"], s["aday"], s["aday_notu"]])
        r = renk.get(s["dayanak"]) or ("E2EFDA" if s["dayanak"].startswith("Şablon") else None)
        if r:
            for c_ in ws[ws.max_row]:
                c_.fill = PatternFill("solid", fgColor=r)
    for i, w in enumerate([16, 46, 22, 7, 7, 18, 60, 50, 8, 50, 16, 50], 1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=3):
        for c_ in row:
            c_.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "C3"
    wb.save(yol)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", type=Path, nargs="?"); ap.add_argument("cikti", type=Path)
    ap.add_argument("--yapi", type=Path, default=None, help="pafta kipi: paftadan okunmuş geometri (yapi_pafta.json)")
    ap.add_argument("--pafta", type=Path, default=None)
    a = ap.parse_args()
    if bool(a.yapi) == bool(a.is_emri):
        ap.error("ya İş Emri ya --yapi verilir")
    N = model_pafta(json.loads(a.yapi.read_text(encoding="utf-8"))) if a.yapi else model_motor(json.loads(a.is_emri.read_text(encoding="utf-8")))
    k = json.loads((KOK / "kurallar" / "liste" / "kurallar.json").read_text(encoding="utf-8"))
    pafta = json.loads(a.pafta.read_text(encoding="utf-8")) if a.pafta else None
    L = liste(N, k, pafta)
    a.cikti.mkdir(parents=True, exist_ok=True)
    kod = (L["kod"] or "PK").replace("-", "")
    (a.cikti / f"{kod}_liste.json").write_text(json.dumps(L, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    xlsx(L, a.cikti / f"{kod}_liste.xlsx")
    print(json.dumps(L["ozet"], ensure_ascii=False), "→", a.cikti / f"{kod}_liste.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
