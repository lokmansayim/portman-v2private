#!/usr/bin/env python3
"""Çelik yükleme listesi denemesi: metraj girdisinden kalemler.

Deneme kodudur; canlıda değildir. Hesapta LLM yoktur: aynı girdi her zaman aynı listeyi verir.

Kuralların kaynağı, öncelik sırasıyla:
  1. Lokman'ın söyledikleri (3 Ekim 2026 13:27 cevapları, 4 Ekim 01:24 ve 01:42 düzeltmeleri ve öncekiler),
  2. PortatifEv'in inşaat mühendisi Ubeydullah'ın cevapları (Lokman 3 Ekim 2026 18:14'te, 4 Ekim 01:24'te ve 12:14'te iletti),
  3. PortatifEv'in yükleme listesi çalışma kitaplarındaki formüller ve notlar,
  4. PortatifEv'in Excel hesaplama motoru (CTKBF V1.1): çelik birim ağırlıkları, vida, boya, tesisat formülleri,
  5. gerçek listelere uydurulan kurallar ve Claude'un varsayımları (teyit bekler).
Kör test projesinin (KT-01) Eylül 2026 tarihli gerçek listesinden çıkanlar `liste` durumundadır (6 Ekim 2026 kıyası). Varsayılan hesaba yalnız o projede
ilk kez karşılaşılan durumlar girdi: model verilmişse çelik ağırlığı profil boyundan, aşık sıraları yüz yüz, ek yapının satırları ayrı, çatı panelli
çatıda dere ve saçak sacı yok, dere kapağı dere hatlarının serbest uçlarından. O listenin ve paftalarının, mevcut kuralların zaten kapsadığı konularda
farklı yaptığı her şey (tavan omegası dizilimi ve formülü, aşık formülü, bindirme, ters mahya kenar kutusu, damlalık, vida katsayıları…)
varsayılan değildir: `--sablon 2026` ile denenir (kurallar: `sablon_2026`); hangilerinin kural olacağına Lokman karar verir.

Çatı işlemede iki yöntem vardır ve birlikte kullanılmaz (Lokman, 3 Ekim 13:27):
  panel       (A) çelik konstrüksiyon standardı: makas arasına tavan paneli, makas üstüne çatı paneli; saçak altı Boardex. Baz budur.
  omega_asik  (B) prefabrikte kullanılan, bugüne kadar çelikte de uygulanan yöntem: tavan omegası, aşık, alın sacı, saçak sacı.
              Üç gerçek örnek liste bu yöntemdedir; yöntem A için karşılaştırılacak gerçek liste yoktur.

Her satırın bir durumu vardır:
  lokman    kuralı Lokman söyledi
  muhendis  kuralı ya da değeri inşaat mühendisi Ubeydullah verdi
  excel     yükleme listesi çalışma kitabındaki formül ya da not
  motor     Excel hesaplama motorundaki formül, not ya da proje ortalaması
  uydurma   gerçek listelerdeki adedi tutturan kural; teyit bekliyor
  varsayim  Claude'un varsayımı; teyit bekliyor
  soru      kural bilinmiyor; adet verilmez ya da geçicidir
  bekliyor  değer Lokman'dan ya da paftadan gelecek; adet verilmez
  model     modelden doğrudan (kapı, pencere)
  liste     gerçek listeden alınan sayı, formül ya da uygulama (örnek girdide listeden alınan sayılar karşılaştırmaya girmez)
  sablon    Eylül 2026 uygulaması: o listenin şablonundaki formül ya da paftalarındaki dizilim; yalnız `--sablon 2026` ile, karar bekliyor

Terim: bu dosyada "alın" PortatifEv listelerindeki anlamıyla kullanılır: beşik çatının kalkan yüzü (alın sacı, çatı alnı).
Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü"dür.

Kullanım:
    python yukleme.py ornek_90m2_girdi.json --karsilastir ornek_90m2_gercek_liste.json
    python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
    python yukleme.py ornek_105m2_girdi.json --karsilastir ornek_105m2_gercek_liste.json
    python yukleme.py sonuc/C8201_girdi.json --cikti sonuc/C8201_yukleme_taslak.json --md sonuc/C8201_yukleme_taslak.md
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from . import kural

from .cati_acilim import BASLANGIC_ADI, kapatma_genisligi, kural_dizilimi

BURADA = Path(__file__).resolve().parent
GRUP_SIRASI = ["Çelik panel", "Metal aksam", "Dış cephe kaplama", "İç cephe kaplama", "Çatı kaplamaları", "Dere", "Kapı ve pencere",
               "Elektrik", "Vida", "Sıhhi tesisat", "Boya"]
# Çatı kaplaması seçenekleri: Excel motorundaki altı seçenek (Ubeydullah, 3 Ekim 2026). İlk üçü gerçek listelerle karşılaştırıldı; son üçü yalnız motorun formülleriyle.
KAPLAMA_ADI = {"sandvic_panel": "sandviç panel", "tek_kat_panel": "tek kat panel", "osb_kiremit": "OSB + nem bariyeri + kiremit desen sac (metal kiremit)",
               "osb_trapez": "OSB + nem bariyeri + trapez sac", "trapez_sac": "trapez sac", "osb_shingle": "OSB + membran + shingle"}
OSBLI_KAPLAMA = ("osb_kiremit", "osb_trapez", "osb_shingle")
ISLEV_ADI = {"yatak_odasi": "yatak odası", "banyo": "banyo", "salon": "salon", "mutfak": "mutfak", "hol": "hol", "veranda": "veranda", "depo": "depo (müştemilat)"}
ELEKTRIK_KALEMLERI = ("tijli_duy", "glop", "tekli_anahtar", "cift_anahtar", "tekli_priz", "cift_priz", "uydu_prizi")
YONTEM_ADI = {"panel": "A · çatı ve tavan paneli (çelik konstrüksiyon standardı)", "omega_asik": "B · tavan omegası, aşık, alın sacı, saçak sacı (prefabrik yöntemi)"}
SABLON = "sablon"       # `--sablon 2026` katmanından gelen satırların durumu


def deg(k: dict, *yol):
    for y in yol:
        k = k[y]
    return k["deger"]


def tavan(x: float) -> int:
    return math.ceil(x - 1e-9)


def kat(x: float, adim: int) -> int:
    """x'i `adim`in katına yukarı yuvarlar."""
    return tavan(x / adim) * adim


def tr(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def kenar_kenar(kenarlar, parca: float) -> int:
    """Her saçak kenarı ayrı ayrı tam parçaya yuvarlanır."""
    return sum(tavan(x / parca) for x in kenarlar)


def inis_sayisi(c: dict, k: dict) -> tuple[int | None, str]:
    """Dere inişi (Lokman, 3 Ekim 13:27): her köşeye bir; 10 m ve üzeri cephenin ortasına bir (cephe başına en çok bir)."""
    kr = deg(k, "inis")
    if "cephe_kenarlari_m" not in c:
        return None, "cephe ölçüleri girdide yok"
    kose = c.get("kose_adedi", 4)
    if kr.get("olcu") == "dere":
        # Lokman, 7 Ekim 2026 07:45: "her saçak köşesine ve çok uzun dere boylarında ortaya 1 tane daha". Eşik dere hattının boyuyla ölçülür
        # (eşik kuralda: 9 m; Lokman 8 Ekim 2026 00:45'te onayladı; dört paftaya ve 82 m² örneğine uyar): boyu eşiği geçen her hattın ortasına bir iniş,
        # hat başına en çok bir.
        dere_hatlari = (c.get("dere") or {}).get("hatlar_m")      # boş liste: dere hattı yok (saçak kenarlarına dönülmez)
        hatlar = c["sacak_kenarlari_m"] if dere_hatlari is None else dere_hatlari
        orta = sum(min(kr["cephe_basina_en_cok_orta"], 1) for x in hatlar if x > kr["orta_inis_esigi_m"] + 1e-9)
        return kose * kr["kose_basina"] + orta, f"{kose} köşe + {orta} orta (boyu {tr(kr['orta_inis_esigi_m'], 0)} m'yi geçen dere hatları)"
    orta = sum(min(kr["cephe_basina_en_cok_orta"], 1) for x in c.get("cephe_kenarlari_m", []) if x >= kr["orta_inis_esigi_m"] - 1e-9)
    return kose * kr["kose_basina"] + orta, f"{kose} köşe + {orta} orta ({tr(kr['orta_inis_esigi_m'], 0)} m ve üzeri cepheler)"


def elektrik_kurali(odalar: list[dict] | None, k: dict) -> tuple[dict | None, dict]:
    """Oda başına elektrik kuralı (Ubeydullah, 3 Ekim 2026; doğruluk payı yaklaşık %75). Salon ile mutfak aynı mahaldeyse ikisi de uygulanır.
    Dönen: (sayım, kalem → döküm metni). Odaların işlevi bilinmiyorsa (None, {})."""
    if not odalar or not all(o.get("islev") for o in odalar):
        return None, {}
    ko = deg(k, "elektrik_oda")
    # mühendisin kuralında olmayan işlevler (ör. depo) için ek tablo: varsayım; yalnız o işlev girdide varsa devreye girer
    ek_tablo = (k.get("elektrik_oda_ek") or {}).get("deger", {})
    odalar_tablosu = {**ko["odalar"], **{i: t for i, t in ek_tablo.items() if any(i in o["islev"] for o in odalar)}}
    sayim = {x: 0 for x in ELEKTRIK_KALEMLERI}
    dokum: dict[str, list[str]] = {x: [] for x in ELEKTRIK_KALEMLERI}
    for islev, tablo in odalar_tablosu.items():
        n = sum(o["islev"].count(islev) for o in odalar)
        for kalem, adet in tablo.items():
            if n:
                sayim[kalem] += n * adet
                dokum[kalem].append(f"{ISLEV_ADI[islev]} {n} × {adet}" if n > 1 else f"{ISLEV_ADI[islev]} {adet}")
    bilinmeyen = sorted({i for o in odalar for i in o["islev"]} - set(odalar_tablosu))
    if bilinmeyen:
        raise SystemExit(f"Elektrik kuralında bu oda işlevleri yok: {', '.join(bilinmeyen)}")
    sayim["sigorta"] = ko["sigorta"]
    return sayim, {x: " + ".join(v) for x, v in dokum.items()}


def asik_boyu(c: dict, aralik: float) -> tuple[float, str]:
    e = c["egim"]
    kok = math.sqrt(1 + e * e)
    if c["tip"] == "kirma":
        px, py = c["plan_m"]
        boy, i = 0.0, 0
        while i * aralik / kok < min(px, py) / 2 - 1e-9:      # saçaktan mahyaya, her sırada çatıyı dolanan halka
            dd = i * aralik / kok
            boy += 2 * ((px - 2 * dd) + (py - 2 * dd))
            i += 1
        boy += 2 * abs(px - py)                               # mahyanın iki yanında birer mahya aşığı
        return boy, f"{i} halka + mahya aşıkları"
    sira = math.floor(c["egimli_boy_m"] / aralik + 1e-9) + 1 + 1   # saçaktan itibaren sıralar + mahya aşığı
    return 2 * sira * c["cati_boyu_m"], f"yüzey başına {sira} sıra"


def hesapla(g: dict, k: dict) -> dict:
    """Yükleme listesi. Girdide `sablon: "2026"` varsa Eylül 2026 katmanı da uygulanır ve satırların `sablon` durumu varsayılan hesapla
    karşılaştırılarak konur: adedi, ölçüsü, ağırlığı, boyutu ya da formülü varsayılan hesaptakinden farklı olan (ya da orada hiç olmayan) her satır
    `sablon`dur; aynı kalan satır varsayılan hesaptaki durumu ve notuyla yazılır. Böylece katmandan gelen her fark işaretlidir, işaretli her satır
    da gerçekten farklıdır. Farklı satırda, varsayılan hesapta aynı adla bir satır varsa oradaki adet `bugunku_adet` alanına yazılır."""
    if g.get("sablon") not in (None, "2026"):
        raise SystemExit(f"Bilinmeyen şablon: {g['sablon']} (yalnız 2026).")
    sonuc = _hesapla(g, k)
    if g.get("sablon"):
        taban = _hesapla({a: v for a, v in copy.deepcopy(g).items() if a != "sablon"}, k)
        anahtar = lambda x: (x["grup"], x["kalem"], x["boyut"])
        kalan: dict[tuple, list[dict]] = {}
        for x in taban["satirlar"]:
            kalan.setdefault(anahtar(x), []).append(x)
        for x in sonuc["satirlar"]:
            esler = kalan.get(anahtar(x)) or []
            d = esler.pop(0) if esler else None
            if d is not None and all(x[a] == d[a] for a in ("adet", "olcu", "brut", "birim", "kg", "formul")):
                x["durum"], x["not"] = d["durum"], d["not"]
            else:
                x["durum"] = SABLON
                if d is not None and d["adet"] != x["adet"]:
                    x["bugunku_adet"] = d["adet"]
    return sonuc


def _hesapla(g: dict, k: dict) -> dict:
    h = g["kat_yuksekligi_m"]
    S: list[dict] = []

    def ekle(grup, kalem, boyut, adet, olcu=None, brut=None, birim="m²", formul="", durum="excel", kg=None, not_=None):
        S.append({"grup": grup, "kalem": kalem, "boyut": boyut, "adet": adet,
                  "olcu": None if olcu is None else round(olcu, 2), "brut": None if brut is None else round(brut, 2),
                  "birim": birim, "kg": None if kg is None else round(kg, 2), "formul": formul, "durum": durum, "not": not_})

    def adet_of(kalem):
        return next((s["adet"] or 0 for s in S if s["kalem"] == kalem), 0)

    def kural_degeri(ad: str):
        """Kural dosyasında bu anahtar varsa değeri, yoksa None. Yeni anahtarlar eski kural setlerinde yoktur: o zaman eski davranış sürer."""
        return (k.get(ad) or {}).get("deger")

    c = g["cati"]
    # çatı panelli çatının satır notlarındaki adı: ek yapı (KT-01) ya da ek yapı yokken örttüğü açık alanlar (KT-03: veranda ve sundurma)
    pc_ad = f"çatı panelli {c['panelli_cati_adi']} çatılarının" if c.get("panelli_cati_adi") else "çatı panelli ek yapının"
    # Çelikte çatı yöntemi kesinleştiyse (Lokman, 7 Ekim 2026 07:45: hangi çatı tipi olursa olsun çatı ve tavan paneli) yöntem B yalnız prefabrik içindir
    celik_yontemi = kural_degeri("celik_cati_yontemi")
    # Eylül 2026 şablonunun, bugünkü kurallardan farklı formülleri (yalnız girdide `sablon: "2026"` varsa; varsayılan değil)
    sb = deg(k, "sablon_2026") if g.get("sablon") == "2026" else {}
    sbv = sb.get("vida") or {}
    yontem = c.get("yontem") or celik_yontemi or "omega_asik"     # girdide yazmıyorsa: çelik standardı kuralda yazıyorsa o, yoksa eski varsayılan
    kaplama = c.get("kaplama") or c.get("ortu")
    kirma = c["tip"] == "kirma"
    m2 = g["bina_m2"]
    d = g["dis"]

    # ── Çelik panel ─────────────────────────────────────────────────────────
    ce = g.get("celik")
    celik_toplam_adet = None
    panel_eksik = False
    if ce:
        ck = k["celik"]
        oran = h / 2.7                                         # motorun birim ağırlıkları 2,70 m kat yüksekliği içindir
        profil_kg = deg(ck, "profil_kg_m")

        def model_kg(x: dict):
            """Karkas modeli verilmişse (girdide grubun profil boyu) ağırlık oradan: profil boyu × profilin birim ağırlığı (kör test listesi).
            Dönen: (kg, formül, durum); model yoksa ya da profilin birim ağırlığı bilinmiyorsa None."""
            if ce.get("karkas"):      # karkas kuralı (İE-16 PR-3a): profil boyu kuraldan; kitapta olmayan birim ağırlık kuralda türetilmiş
                birim = profil_kg.get(x.get("profil"), x.get("birim_kg_m"))
                if x.get("profil_boyu_m") is None or birim is None:
                    return None
                return (x["profil_boyu_m"] * birim, f"karkas kuralının profil boyu {tr(x['profil_boyu_m'])} m × {tr(birim, 2 if x.get('profil') in profil_kg else 3)} kg/m"
                        + ("" if x.get("profil") in profil_kg else " (birim ağırlık karkas kuralında türetilmiş)"), "varsayim")
            if x.get("profil_boyu_m") is None or x.get("profil") not in profil_kg:
                return None
            return (x["profil_boyu_m"] * profil_kg[x["profil"]], f"modeldeki profil boyu {tr(x['profil_boyu_m'])} m × {tr(profil_kg[x['profil']])} kg/m",
                    ck["profil_kg_m"]["durum"])

        for taraf, ad in (("dis", "Dış cephe duvar panelleri"), ("ic", "İç cephe duvar panelleri")):
            x = ce.get(taraf)
            if not x:
                continue
            birim = deg(ck, "duvar_kg_m")[taraf].get(x["profil"])
            mk = model_kg(x)
            ekle("Çelik panel", ad, x["profil"].replace("x", " × "), x.get("panel_adedi"), x["boy_m"], birim="m",
                 kg=mk[0] if mk else (None if birim is None else x["boy_m"] * birim * oran),
                 formul=mk[1] if mk else (f"duvar boyu × {tr(birim)} kg/m (motorun proje ortalaması)" if birim is not None else "bu profil için motorda birim ağırlık yok"),
                 durum=mk[2] if mk else ("motor" if birim is not None else "soru"), not_=x.get("not"))
        # ek duvar grupları (genel model): ek yapı duvarları, korkuluk, baca. Model yoksa motorun birim ağırlığı (2,70 m için) yüksekliğe oranlanır.
        for x in ce.get("ek_duvarlar") or []:
            birim = deg(ck, "duvar_kg_m")[x["birim_taraf"]].get(x["profil"])
            mk = model_kg(x)
            ekle("Çelik panel", x["ad"], x["profil"].replace("x", " × "), x.get("panel_adedi"), x["boy_m"], birim="m",
                 kg=mk[0] if mk else (None if birim is None else x["boy_m"] * birim * x["yukseklik_m"] / 2.7),
                 formul=mk[1] if mk else (f"boy × {tr(birim)} kg/m ({'dış' if x['birim_taraf'] == 'dis' else 'iç'} duvarın motordaki ortalaması) × yükseklik {tr(x['yukseklik_m'])} m ÷ 2,70"
                                          if birim is not None else "bu profil için motorda birim ağırlık yok"),
                 durum=mk[2] if mk else ("varsayim" if birim is not None else "soru"), not_=x.get("not"))
        x = ce.get("dikme")
        if x and x.get("adet"):
            birim = deg(ck, "dikme_kg_m").get(x["profil"])
            boy = x["adet"] * x["boy_m"]
            mk = model_kg(x)
            ekle("Çelik panel", "Veranda dikmeleri (kolon paneli)", x["profil"].replace("x", " × "), x["adet"], boy, birim="m",
                 kg=mk[0] if mk else (None if birim is None else boy * birim),
                 formul=mk[1] if mk else f"adet × {tr(x['boy_m'])} m × {tr(birim)} kg/m (motorun proje ortalaması)", durum=mk[2] if mk else "motor", not_=x.get("not"))
        x = ce.get("kiris")
        if x and x.get("boy_m"):
            birim = deg(ck, "kiris_kg_m").get(x["profil"])
            kural_adet = tavan(x["boy_m"] / deg(ck, "kiris_panel_boyu_m"))
            mk = model_kg(x)
            ekle("Çelik panel", "Veranda kirişleri (kiriş paneli)" if "adet" not in x else "Kirişler (kiriş paneli)", x["profil"].replace("x", " × "), x.get("adet", kural_adet), x["boy_m"], birim="m",
                 kg=mk[0] if mk else (None if birim is None else x["boy_m"] * birim),
                 formul=(mk[1] + (("; adet tanımdan" if ce.get("karkas") else "; adet modelden") if "adet" in x else "; adet = boy ÷ 4")) if mk else
                        (f"kiriş boyu × {tr(birim)} kg/m; adet = boy ÷ 4" if "adet" not in x else f"kiriş boyu × {tr(birim)} kg/m; adet modelden (kural: boy ÷ 4 = {kural_adet})"),
                 durum=mk[2] if mk else "motor", not_=x.get("not"))
        x = ce.get("cati")
        if x:
            birim = deg(ck, "cati_kg_m2")[x["tip"]]
            kural_adet = deg(ck, "cati_panel_adedi")[x["tip"]]
            mk = model_kg(x)
            ekle("Çelik panel", "Çatı makas panelleri", x["profil"].replace("x", " × "), x.get("panel_adedi") or kural_adet, x["plan_m2"], birim="m²",
                 kg=mk[0] if mk else x["plan_m2"] * birim,
                 formul=(mk[1] + (("; adet makas kuralından" if ce.get("karkas") else "; adet modelden") if x.get("panel_adedi") else "; adet çatı tipine göre sabit")) if mk else
                        (f"saçak dahil çatı planı × {tr(birim)} kg/m² (motorun proje ortalaması); adet çatı tipine göre sabit" if not x.get("panel_adedi") else
                         f"saçak dahil çatı planı × {tr(birim)} kg/m² (motorun proje ortalaması); adet modelden (motorda çatı tipine göre sabit: {kural_adet})"),
                 durum=mk[2] if mk else "motor",
                 not_=x.get("not") if mk else "şimdilik Excel motoru kıstas (mühendis, 4 Ekim 12:14; Lokman, 4 Ekim 15:18); makas ölçüsü verilirse değişir")
        x = ce.get("ek_cati_paneli")
        if x:   # ek yapının çatısı çatı paneliyle kapatılıyorsa (yöntem B'de de): model yoksa 100 m² için verilen ağırlık alana oranlanır
            pk = deg(ck, "cati_paneli")
            mk = model_kg(x)
            ekle("Çelik panel", x.get("ad", "Çatı paneli (ek yapının çatısı)"), x["profil"].replace("x", " × ") if mk else "roll form çelik",
                 x.get("adet") or tavan(x["oturum_m2"] / 100 * pk["adet_100m2"]), x["oturum_m2"], birim="m²",
                 kg=mk[0] if mk else x["oturum_m2"] / 100 * pk["kg_100m2"],
                 formul=mk[1] if mk else f"çatı panelinin örttüğü mahal alanı ÷ 100 × {tr(pk['kg_100m2'])} kg", durum=mk[2] if mk else "varsayim", not_=x.get("not"))
        # karkas modelindeki öteki gruplar (genel model; KT-02, 9 Ekim 2026): her grup ayrı satır, ağırlık modeldeki profil boyundan.
        # Profilin birim ağırlığı kuralda yoksa ağırlık yazılmaz (soru); toplama girmez.
        for x in ce.get("ek_satirlar") or []:
            mk = model_kg(x)
            ekle("Çelik panel", x["ad"], x["profil"].replace("x", " × "), x["panel_adedi"], x["profil_boyu_m"], birim="m",
                 kg=mk[0] if mk else None,
                 formul=mk[1] if mk else f"modeldeki profil boyu {tr(x['profil_boyu_m'])} m; {x['profil'].replace('x', ' × ')} profilin birim ağırlığı kuralda yok",
                 durum=mk[2] if mk else "soru", not_=x.get("not"))
        if yontem == "panel":   # yöntem A: tavan paneli ve çatı paneli (100 m² için kg: Lokman'ın 4 Ekim düzeltmesi; adet: mühendisin 3 Ekim cevabı)
            oturum = (ce.get("cati") or {}).get("oturum_m2")
            for ad, anahtar, kural, aciklama in (("Tavan paneli (makas arası)", "tavan_paneli_m2", "tavan_paneli", "tavan alanı"),
                                                  ("Çatı paneli (makas üstü, sırt 80 mm)", "cati_paneli_m2", "cati_paneli", "çatı yüzeyi")):
                if not ce.get(anahtar):
                    continue
                pk = deg(ck, kural)
                ap = (ce.get("a_panelleri") or {}).get({"tavan_paneli": "tavan_paneli", "cati_paneli": "ust_paneli"}[kural])
                mk = model_kg(ap) if ap else None
                if mk:          # karkas kuralı (İE-16 PR-3b): adet ve profil boyu kuraldan; 100 m² oranı kullanılmaz
                    ekle("Çelik panel", ad, ap["profil"].replace("x", " × "), ap["adet"], ap["profil_boyu_m"], birim="m", kg=mk[0],
                         formul=f"{mk[1]}; adet karkas kuralından ({aciklama} {tr(ce[anahtar], 1)} m²)", durum=mk[2], not_=ap.get("not"))
                elif oturum:
                    ekle("Çelik panel", ad, "roll form çelik", tavan(oturum / 100 * pk["adet_100m2"]), oturum, birim="m²", kg=oturum / 100 * pk["kg_100m2"],
                         formul=f"çatının örttüğü oturum alanı ÷ 100 × {tr(pk['kg_100m2'])} kg; adet: ÷ 100 × {pk['adet_100m2']}, yukarı ({aciklama} {tr(ce[anahtar], 1)} m²)",
                         durum=ck[kural]["durum"],
                         not_=f"100 m² için verilen ağırlık oturum alanına oranlandı (Lokman, 4 Ekim düzeltmesi). Adet 100 m²'deki {pk['adet_100m2']} adetten aynı oranla (mühendis, 4 Ekim 12:14: bu adetlerle ilerle; dört omuz çatı için)")
                else:
                    ekle("Çelik panel", ad, "roll form çelik", None, ce[anahtar], birim="m²", formul=f"{aciklama}; kg ve adet için çatının örttüğü oturum alanı gerekli", durum="bekliyor")
        if ce.get("cati"):   # çatısı hesaplanamayan örnekte toplam da eksik kalır; boy C profil eklenmez
            for profil, x in deg(ck, "boy_c_profil").items():
                ekle("Çelik panel", "Boy C profil", profil.replace("x", " × "), x["adet"], birim="", kg=x["kg"], formul="motorda sabit", durum="motor")
        cs = [s for s in S if s["grup"] == "Çelik panel"]
        celik_toplam_adet = sum(s["adet"] or 0 for s in cs)
        panel_eksik = any(s["kalem"].startswith(("Tavan paneli", "Çatı paneli")) and s["kg"] is None for s in cs)
        ekle("Çelik panel", "Toplam (adedi ve kg'ı bilinenler)", "", celik_toplam_adet or None, birim="", kg=sum(s["kg"] or 0 for s in cs),
             formul="tavan ve çatı panelleri hariç" if panel_eksik else ("tavan ve çatı panelleri dahil" if yontem == "panel" else ""), durum="motor")

    # ── Dış cephe ────────────────────────────────────────────────────────────
    dis_duvar = d.get("duvar_m2", d["cevre_m"] * h)       # genel modelde yüz yüz: her duvar kendi yüksekliğiyle
    kk = sum(x["adet"] * x["cevre_m"] * x["boy_m"] for x in d.get("kolon_kiris", []))
    alin = sum(d.get("alin_m2", []))
    dis_ek = sum(x["alan_m2"] for x in d.get("ek_m2", []))
    dis_bosluk = sum(x["adet"] * x["en"] * x["boy"] for x in d["bosluklar"])
    dis_net = dis_duvar + kk + alin + dis_ek - dis_bosluk
    zb = deg(k, "zayiat", "boardex")                      # Boardex zayiatı (mühendis, 4 Ekim 2026 12:14: %8; önce %15)
    zb_carpan = tr(1 + zb)
    kal = deg(k, "levha_kalinligi_mm")                    # Boardex 12,5 mm, OSB 11 mm (mühendis, 4 Ekim 2026 12:14)
    boardex_boyut = f"{tr(sb.get('boardex_kalinligi_mm', kal['boardex']), 1).replace(',0', '')} × 1200 × 2400" if sb else f"{tr(kal['boardex'], 1)} × 1200 × 2400"
    osb_boyut = f"{tr(kal['osb'], 0)} × 1220 × 2440"      # adı "OSB 9 mm" olan satırlar 2025 listelerinin kalemleridir; onlarda kalınlık yazılmaz
    dis_zayiatli = dis_net * (1 + zb)
    kk_durum = "varsayim" if d.get("kolon_kiris_varsayim") else "excel"
    ey = d.get("ek_yapi")                                 # genel model: ek yapının (müştemilat) dış kaplaması ayrı satır
    ey_net = (ey["net_m2"] + sum(x["alan_m2"] for x in ey.get("ek_m2", []))) if ey else 0.0
    bina_net = dis_net - (ey["net_m2"] if ey else 0.0)     # ek yapının duvarları kendi satırında
    bina_brut = dis_duvar + kk + alin + dis_ek - (ey.get("brut_m2", ey["net_m2"]) if ey else 0.0)
    if ey:
        dis_zayiatli = bina_net * (1 + zb)
    ekle("Dış cephe kaplama", "Dış cephe Boardex", boardex_boyut, tavan(dis_zayiatli / deg(k, "levha_m2", "boardex")), bina_net, bina_brut,
         formul=(f"(çevre × yükseklik + kolon/kiriş kaplaması + çatı alnı (kalkan) − boşluklar) × {zb_carpan} ÷ 2,88" if "duvar_m2" not in d else
                 f"({'bina duvarlarının dışa bakan yüzleri' if ey else 'dışa bakan duvar yüzleri'}, her biri kendi yüksekliğiyle + kolon/kiriş kaplaması + çatı alnı (kalkan)"
                 + (" + " + ", ".join(x["ad"] for x in d["ek_m2"]) if d.get("ek_m2") else "") + f" − boşluklar) × {zb_carpan} ÷ 2,88"
                 + ("; ek yapı ayrı satırda" if ey else "")),
         durum=kk_durum,
         not_=f"zayiat %{tr(zb * 100, 0)}: mühendis, 4 Ekim 12:14; Lokman, 4 Ekim 15:18: bununla devam. 2025 listelerindeki adetler %15'e uyuyor; %15 ile {tavan(bina_net * 1.15 / deg(k, 'levha_m2', 'boardex'))} levha")
    if ey:
        ekle("Dış cephe kaplama", f"Dış cephe Boardex ({ey['ad'].lower()})", boardex_boyut, tavan(ey_net * (1 + zb) / deg(k, "levha_m2", "boardex")), ey_net,
             formul=f"(ek yapının dışa bakan duvar yüzleri − boşluklar" + ("".join(" + " + x["ad"] for x in ey.get("ek_m2", []))) + f") × {zb_carpan} ÷ 2,88", durum=kk_durum,
             not_="ek yapının kalemleri ayrı satırda (gerçek listedeki gibi); duvarlar kendi yüksekliğiyle (gerçek listede 2,70 m ile çarpılmış)")
    if d.get("dis_osb"):
        zdo = deg(k, "zayiat", "dis_osb")                  # listedeki formül: Boardex ile aynı alan × 1,15 (Boardex zayiatından ayrı)
        ekle("Dış cephe kaplama", "Dış duvar OSB 9 mm", "1220 × 2440", tavan(dis_net * (1 + zdo) / deg(k, "levha_m2", "osb")), dis_net,
             formul=f"Boardex ile aynı alan (× {tr(1 + zdo)}) ÷ 2,98; üst paket", durum="excel")
    # Eylül 2026 şablonu: veranda tavanı Boardex (Lokman'ın kuralında yeşil alçıpan)
    # Kural (Lokman, 7 Ekim 2026 07:45): çelik konstrüksiyon binalarda veranda tavanı her zaman Boardex; prefabrikte yeşil alçıpan.
    vt_kural = (kural_degeri("veranda_tavani") or {}).get("celik") == "boardex"
    veranda_boardex = (g.get("veranda_m2") or {}).get("brut") if (sb.get("veranda_tavani") == "boardex" or vt_kural) else None
    vt_notu = (k.get("veranda_tavani") or {}).get("satir_notu") or "çelik konstrüksiyon binalarda veranda tavanı Boardex (Lokman, 7 Ekim 07:45)"
    # çatısız veranda (genel model; Ç8801, 10 Ekim 2026): girdide `veranda_m2.catisiz`. Bütün verandalar çatısızsa tavan yok: yeşil tavan
    # yalnız ıslak hacimdir ve "veranda tavanı ayrı yazmıyor" notu yazılmaz. Eski girdilerde alan yok: eski metin.
    catisiz_v = bool((g.get("veranda_m2") or {}).get("catisiz")) and not veranda_boardex
    if veranda_boardex:
        ekle("Dış cephe kaplama", "Veranda tavanı (Boardex)", boardex_boyut, tavan(veranda_boardex * (1 + zb) / deg(k, "levha_m2", "boardex")), veranda_boardex,
             formul=f"veranda tavanı (dış ölçüyle) × {zb_carpan} ÷ 2,88", durum=k["veranda_tavani"]["durum"] if vt_kural else SABLON,
             not_=vt_notu if vt_kural else "Eylül 2026 şablonu: veranda tavanı Boardex. Bugünkü kuralda yeşil alçıpan (Lokman)")
    if d.get("nem_bariyeri_m2"):   # yalnız duvarlar; bina ve ek yapı ayrı (kör test projesinin gerçek listesi)
        nk = deg(k, "nem_bariyeri_dis_cephe")
        for x in d["nem_bariyeri_m2"]:
            ekle("Dış cephe kaplama", f"Nem bariyeri ({x['ad']} dış cephesi)", "m²", tavan(x["alan_m2"] * (1 + nk["zayiat"])), x["alan_m2"],
                 formul=f"dışa bakan duvar yüzleri − boşluklar; × {tr(1 + nk['zayiat'])}", durum=k["nem_bariyeri_dis_cephe"]["durum"],
                 not_="projenin notunda dış cephe paneli Boardex + nem bariyeri; yalnız duvarlar (kalkan, baca ve korkuluk hariç): gerçek listedeki gibi")
    elif d.get("nem_bariyeri"):   # proje notunda dış cephe paneli "Boardex + nem bariyeri" ise; listelerde kuralı yok
        ekle("Dış cephe kaplama", "Nem bariyeri (dış cephe)", "m²", tavan(dis_net), dis_net, formul="Boardex ile aynı alan; fire hariç", durum="varsayim",
             not_="projenin notunda dış cephe paneli Boardex + nem bariyeri; okunan listelerde bu kalemin kuralı yok")

    # ── İç cephe ─────────────────────────────────────────────────────────────
    ozet = {}
    za = deg(k, "zayiat", "duvar_alcipan")
    # odanın içinden geçen kirişin kaplaması duvar alçıpanında değil, tavan alçıpanında sayılır (kör test listesi: tavan alanı + kiriş çevresi × boy).
    # Girdide odanın `kiris_kaplamasi_m2` değeri duvar brüt alanının içindedir; buradan düşülür, tavana eklenir.
    kiris_m2 = {tur: sum(o.get("kiris_kaplamasi_m2", 0.0) for o in g["odalar"] if o["tur"] == tur and not o.get("yapi")) for tur in ("beyaz", "yesil")}
    ek_kiris: dict[tuple, float] = {}                      # (ek yapı, tür) → o yapının mahallerindeki kiriş kaplaması
    ek_yapilar = sorted({o["yapi"] for o in g["odalar"] if o.get("yapi")})      # genel model: ek yapının mahalleri ayrı satır
    ek_net = {}
    for tur, ad in (("beyaz", "beyaz"), ("yesil", "yeşil")):
        odalar = [o for o in g["odalar"] if o["tur"] == tur and not o.get("yapi")]
        brut = sum(o.get("duvar_brut_m2", o["cevre_m"] * h) for o in odalar) - kiris_m2[tur]
        net = brut - sum(sum(o["bosluk_m2"]) for o in odalar)
        ozet[tur] = (net, brut)
        if odalar:
            ekle("İç cephe kaplama", f"Duvar alçıpan {ad}", "1200 × 2500", tavan(net * (1 + za) / deg(k, "levha_m2", "alcipan")), net, brut,
                 formul="oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0" + ("; yeşil = ıslak hacimler" if tur == "yesil" else "")
                        + ("; odanın içinden geçen kirişin kaplaması tavan satırında" if kiris_m2[tur] else ""))
        for yp in ek_yapilar:
            eo = [o for o in g["odalar"] if o["tur"] == tur and o.get("yapi") == yp]
            if not eo:
                continue
            ek_kiris[(yp, tur)] = sum(o.get("kiris_kaplamasi_m2", 0.0) for o in eo)
            ebrut = sum(o.get("duvar_brut_m2", o["cevre_m"] * h) for o in eo) - ek_kiris[(yp, tur)]
            enet = ebrut - sum(sum(o["bosluk_m2"]) for o in eo)
            ek_net[yp] = ek_net.get(yp, 0.0) + enet
            ekle("İç cephe kaplama", f"Duvar alçıpan {ad} ({yp.lower()})", "1200 × 2500", tavan(enet * (1 + za) / deg(k, "levha_m2", "alcipan")), enet, ebrut,
                 formul="ek yapının iç yüzleri (duvarlar kendi yüksekliğiyle) − boşluklar; × 1,05 ÷ 3,0", not_="ek yapının kalemleri ayrı satırda (gerçek listedeki gibi)")
    for tur, ad in (("beyaz", "beyaz"), ("yesil", "yeşil")):
        a = g["tavan_m2"].get(tur)
        if a and tur == "yesil" and veranda_boardex:      # şablonda veranda tavanı Boardex: yeşil alçıpandan düşülür
            if veranda_boardex > a + 1e-9:
                raise SystemExit(f"Girdide yeşil tavan alanı ({tr(a, 2)} m²) veranda tavanından ({tr(veranda_boardex, 2)} m²) küçük: `tavan_m2.yesil` ıslak hacimlerle "
                                 "birlikte veranda tavanını (brüt) içermeli; girdi düzeltilmeli.")
            a = round(a - veranda_boardex, 2)
        if a and kiris_m2[tur]:
            a = round(a + kiris_m2[tur], 2)
        if a:
            ekle("İç cephe kaplama", f"Tavan alçıpan {ad}", "1200 × 2500",
                 tavan(a * (1 + deg(k, "zayiat", "tavan_alcipan")) / deg(k, "levha_m2", "alcipan")), a,
                 formul="tavan alanı × 1,05 ÷ 3,0" + ("; yeşil = ıslak hacim + veranda tavanı" if tur == "yesil" and not veranda_boardex and not catisiz_v else "")
                        + ("; yeşil = ıslak hacim" if tur == "yesil" and (veranda_boardex or catisiz_v) else "") + ("; kiriş kaplaması dahil" if kiris_m2[tur] else ""),
                 durum=SABLON if tur == "yesil" and veranda_boardex and not vt_kural else ("lokman" if tur == "yesil" else "motor"),
                 not_=". ".join(x for x in (
                     f"odanın içinden geçen kirişin kaplaması ({tr(kiris_m2[tur])} m²) tavanda sayıldı (gerçek listedeki gibi)" if kiris_m2[tur] else None,
                     # kural veranda tavanını Boardex'e ayırıyor ama girdi veranda tavanını ayrı vermiyor: satırda yazsın (sessizce yeşilde kalmasın)
                     "veranda tavanı girdide ayrı yazmıyor: varsa yeşil alçıpanın içinde kaldı (çelikte Boardex olmalı: Lokman, 7 Ekim 07:45)"
                     if tur == "yesil" and vt_kural and not veranda_boardex and not catisiz_v else None,
                     g["veranda_m2"]["not"] if tur == "yesil" and catisiz_v else None) if x) or None)
    for x in g.get("tavan_m2_ek") or []:                  # ek yapının tavanı ayrı satır
        ad = {"beyaz": "beyaz", "yesil": "yeşil"}[x["tur"]]
        ek_alan = x["alan_m2"] + ek_kiris.get((x["yapi"], x["tur"]), 0.0)
        ekle("İç cephe kaplama", f"Tavan alçıpan {ad} ({x['yapi'].lower()})", "1200 × 2500",
             tavan(ek_alan * (1 + deg(k, "zayiat", "tavan_alcipan")) / deg(k, "levha_m2", "alcipan")), ek_alan,
             formul="ek yapının tavan alanı × 1,05 ÷ 3,0" + ("; kiriş kaplaması dahil" if ek_kiris.get((x["yapi"], x["tur"])) else ""), durum="motor",
             not_="ek yapının kalemleri ayrı satırda (gerçek listedeki gibi)")
    ic_net = ozet["beyaz"][0] + ozet["yesil"][0]
    zo = deg(k, "zayiat", "osb")
    if g.get("ic_osb_tum_duvarlar"):
        # kalınlık girdide yazıyorsa (genel model: kuraldaki 11 mm) o; yazmıyorsa 2025 listelerindeki ad
        osb_adi = f"İç duvar OSB {g['ic_osb_kalinlik_mm']} mm" if g.get("ic_osb_kalinlik_mm") else "İç duvar OSB 9 mm"
        ekle("İç cephe kaplama", osb_adi, "1220 × 2440", tavan(ic_net * (1 + zo) / deg(k, "levha_m2", "osb")), ic_net,
             formul="bütün iç yüzler (beyaz + yeşil net) × 1,05 ÷ 2,98; üst paket")
        for yp, enet in ek_net.items():
            ekle("İç cephe kaplama", f"{osb_adi} ({yp.lower()})", "1220 × 2440", tavan(enet * (1 + zo) / deg(k, "levha_m2", "osb")), enet,
                 formul="ek yapının iç yüzleri (net) × 1,05 ÷ 2,98", not_="ek yapının kalemleri ayrı satırda (gerçek listedeki gibi)")
    elif g.get("osb_takviye"):   # yalnız dolap ve TV ünitesi gelen duvarlar (Ubeydullah, 3 Ekim 2026)
        ot = g["osb_takviye"]
        duvarlar = "; ".join(f"{x['duvar_adi']} {tr(x['boy_m'])} m ({x['neden']})" for x in ot["duvarlar"])
        duvar_adet = tavan(ot["net_m2"] * (1 + zo) / deg(k, "levha_m2", "osb"))
        # Geçerli kural yalnız dolap ve TV duvarları (Lokman, 4 Ekim 2026 16:18: "9 sayısını veren hangisi ise o kuralı geçerli say").
        # Odanın bütün yüzeyi (Lokman, 3 Ekim 13:27; ilk hesap) yalnız bilgi: satırın notunda durur (15:18: bayiye belirtilecek).
        oda_adlari = {x["mahal"] for x in ot["duvarlar"]}
        oda_net = sum(o["cevre_m"] * h - sum(o["bosluk_m2"]) for o in g["odalar"] if o["ad"] in oda_adlari)
        oda_adet = tavan(oda_net * (1 + zo) / deg(k, "levha_m2", "osb")) if oda_net else None
        ozet["osb_takviye"] = {"duvarlar_m2": round(ot["net_m2"], 2), "duvarlar_adet": duvar_adet, "butun_oda_m2": round(oda_net, 2), "butun_oda_adet": oda_adet}
        assert deg(k, "osb_takviye")["baz"] == "duvarlar", "OSB takviyesinde geçerli kural: dolap ve TV duvarları"
        ekle("İç cephe kaplama", "OSB (TV ve mutfak dolabı arkası takviyesi)", osb_boyut, duvar_adet, ot["net_m2"], ot["brut_m2"],
             formul="dolap ve TV ünitesi gelen duvarlar: (duvar yüzünün boyu × yükseklik − boşluklar) × 1,05 ÷ 2,98", durum=k["osb_takviye"]["durum"],
             not_=f"{duvarlar}. Duvarların seçimi katalog görselinden; "
                  + ("mühendis doğruladı (4 Ekim). Duvar yüzünün tamamı alınır (mühendis, 4 Ekim 12:14)" if g.get("osb_takviye_teyit") == "muhendis" else "teyit bekliyor")
                  + ". Geçerli kural bu: yalnız dolap ve TV duvarları (Lokman, 4 Ekim 16:18)"
                  + (f". Bilgi: odanın bütün yüzeyi sayılsaydı {tr(oda_net, 1)} m² → {oda_adet} levha (bayiye belirtilecek). Klima duvarı sayılmaz" if oda_adet else ""))
    elif "osb_takviye" in g:
        ekle("İç cephe kaplama", "OSB (TV ve mutfak dolabı arkası takviyesi)", osb_boyut, None,
             formul="dolap ve TV ünitesi gelen duvarlar modelin tanımında yazılı değil", durum="bekliyor")
    elif g.get("osb_duvar_m2"):
        ekle("İç cephe kaplama", "OSB 9 mm (duvar)", "1220 × 2440", tavan(g["osb_duvar_m2"] * (1 + zo) / deg(k, "levha_m2", "osb")),
             g["osb_duvar_m2"], formul="listede yazan alan × 1,05 ÷ 2,98; alanın nasıl seçildiği listede yazmıyor", durum="excel")
    # yalıtım: bütün duvarlar; dış duvarda karkasa göre kat sayısı. İç duvar boyu verilmemişse oda çevrelerinden çıkarılır.
    ic_yuz = sum(o["cevre_m"] for o in g["odalar"])
    ic_boy = g.get("ic_duvar_boyu_m")
    if ic_boy is None:
        ic_boy = (ic_yuz - (d["cevre_m"] - 8 * d["duvar_kalinligi_m"])) / 2
    kat_sayisi = deg(k, "yalitim_kat")[str(d["karkas_mm"])]
    yal_brut = kat_sayisi * dis_duvar + ic_boy * h
    ik = deg(k, "kapi_boslugu_m", "ic")
    yal_net = yal_brut - dis_bosluk - g["ic_kapi_adedi"] * ik[0] * ik[1]
    if g.get("yalitim"):   # genel model: yalıtılan duvarların (bina dış duvarı ve iç duvar) alanı ve onlardaki boşluklar
        yal_brut = kat_sayisi * g["yalitim"]["dis_brut_m2"] + g["yalitim"]["ic_brut_m2"]
        yal_net = yal_brut - g["yalitim"]["bosluk_m2"]
    yz = sb.get("yalitim_zayiat", 0.0)                    # Eylül 2026 şablonunda × 1,05; bugünkü kuralda zayiat yok
    # Kural (Lokman, 7 Ekim 2026 07:45): duvar izolasyonu gönderilmiyor; listede yok. Şablon katmanında (o listenin uygulaması) satır durur.
    # 0.20 (Lokman, 27 Ekim 2026): mineral yün gönderilir, listede; yalıtılan duvarı olmayan iş ("sadece çelik") satır yazmaz (`bos_yazilmaz`).
    di = kural_degeri("duvar_izolasyonu") or {}
    if (di.get("listede", True) or yz) and not (di.get("bos_yazilmaz") and yal_net <= 0):
        ekle("İç cephe kaplama", "Duvar izolasyonu", "paket 8,64 m²", tavan(yal_net * (1 + yz) / deg(k, "yalitim_paket_m2")), yal_net, yal_brut,
             formul="dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; " + (f"× {tr(1 + yz)} " if yz else "") + "÷ 8,64",
             durum=SABLON if yz else "uydurma", not_=f"dış duvar {kat_sayisi} kat")

    # ── Çatı kaplaması (seçenek) ────────────────────────────────────────────
    sacak = c["sacak_boyu_toplam_m"]
    kenarlar = c["sacak_kenarlari_m"]
    pm, bm = deg(k, "parca_boyu_m", "mahya"), (sb.get("bindirme_m") or {}).get("mahya", deg(k, "bindirme_m", "mahya"))
    mahya_durum = SABLON if "mahya" in (sb.get("bindirme_m") or {}) else "lokman"
    mahya_notu = "Eylül 2026 şablonu: 20 cm bindirme. Bugünkü kuralda 30 cm (Lokman, 3 Ekim 13:27)" if mahya_durum == SABLON else None
    mahya_formul = f"mahya hattı (tepe + kırmalar) ÷ ({tr(pm, 1)} − {tr(bm)} bindirme)"
    zc = deg(k, "zayiat", "cati_kaplama_kirma")
    dz: dict = {}

    def kirma_dizilim():
        """Kırma çatıda kaplama adedi: çatı açılır, kaplama yüzlere dizilir; çapraz kesimden artan parça karşı yüzde kullanılır
        (Lokman, 4 Ekim 2026 01:42; taşma ve kiremit desen sac: mühendis, 12:14; bkz. cati_acilim.py).
        Dönen: (adet, formül, durum, not); çatı planı girdide yoksa ya da panel kısaysa None."""
        d = kural_dizilimi(k, c, kaplama) if kirma else None
        if d is None:
            return None
        paylas, den = d["paylas"], d["denemeler"]
        dz.update(adet=d["adet"], tam_boy=d["tam_boy_adedi"], kesilen=d["adet"] - d["tam_boy_adedi"], alan_alt_siniri=d["alan_alt_siniri"],
                  artan_parca_karsi_yuzde=paylas, baslangic=d["baslangic"], baslangic_adi=BASLANGIC_ADI[d["baslangic"]], baslangica_gore=den,
                  kapatma_m=d["kapatma_m"], tasma_cm=round(d["tasma_m"] * 100, 1), tasma_kural_cm=round(d["tasma_kural_m"] * 100, 1),
                  kesim_payi_mm=round(d["kesim_payi_m"] * 1000, 1), paysiz_adet=d["paysiz_adet"], bir_cm_payla_adet=d["bir_cm_payla_adet"],
                  en_az_adet=d["en_az_adet"], baslangic_kurali=d["baslangic_kurali"], cift=d["cift_adedi"], tek=d["tek_adedi"], uzun_panelle=d["uzun_panelle"],
                  panel_boyu_m=d["boy_m"], taban_boy_m=d["taban_boy_m"], taban_adet=d["taban_adet"], uzatma=d["uzatma"],
                  en_dar_pay_cm=None if d["en_dar_pay_m"] is None else round(d["en_dar_pay_m"] * 100, 1), egimli_boy_m=round(d["egimli_boy_m"], 4))
        formul = "çatı açılımı: yüzler şerit şerit dizilir; " + ("çapraz kesimden artan parça karşı yüzde kullanılır" if paylas else "çapraz kesimden artan parça kullanılmaz")
        n = (f"{d['tam_boy_adedi']} panel tam boy, {d['adet'] - d['tam_boy_adedi']} panel kesilerek; alan olarak en az {d['alan_alt_siniri']}. "
             f"Dizilim {BASLANGIC_ADI[d['baslangic']]} başlar")
        if d["baslangic_kurali"] == "en_az":
            if len(set(den.values())) > 1:
                n += f" (en az paneli veren başlangıç; her yüzde sol köşeden başlanırsa {den['sol']}, öteki başlangıçlarla {min(den.values())}–{max(den.values())})"
        else:   # başlangıç kuralda yazılı (Lokman, 4 Ekim 15:18: her yüzde köşeden)
            n += " (Lokman, 4 Ekim 15:18)"
            if d["en_az_adet"] < d["adet"]:
                n += f"; en az paneli veren dizilimle {d['en_az_adet']} olurdu"
        n += f". Kaplama saçaktan {tr(d['tasma_m'] * 100, 1).replace(',0', '')} cm taşar"
        if d["tasma_m"] + 1e-9 < d["tasma_kural_m"]:
            n += f" (kural {tr(d['tasma_kural_m'] * 100, 0)} cm; listedeki panel boyu o kadarına yetiyor)"
        n += f"; kesim payı {tr(d['kesim_payi_m'] * 1000, 0)} mm; yedek panel yok: kesim planı montajcıya verilir (Lokman, 4 Ekim 15:18)"
        if d["uzatma"] and d["uzatma"].get("neden") == "pay":      # adet aynı; taban boyda pay inceydi (kuralda `taban_icin_de`; 7 Ekim 2026)
            u = d["uzatma"]
            n += (f". Panel boyu {tr((d['boy_m'] - d['taban_boy_m']) * 100, 0)} cm uzatıldı (pay kalsın diye; {k['panel_boyu_uzatma'].get('satir_notu_pay') or '4 Ekim 16:18 kuralındaki pay koşulu taban boya da uygulandı, teyit bekliyor'}): "
                  f"L {u['taban_boy_mm']} ile de {u['taban_adet']} çıkıyor ama pay ince, kesim payı {tr(u['taban_pay_siniri_mm'], 1)} mm'yi geçerse {u['taban_saglamlik_adet']} gerekir; "
                  f"L {u['boy_mm']} ile kesim payı 1 cm olsa " + (f"da {u['adet']}. " if u["saglamlik_adet"] == u["adet"] else f"{u['saglamlik_adet']}. ")
                  + f"Tam boy giden {d['tam_boy_adedi']} panelde fazlalık mahya ucunda kalır; taşma {tr(d['tasma_m'] * 100, 1).replace(',0', '')} cm")
        elif d["uzatma"]:          # panel boyu kuralla uzatıldı (Lokman, 4 Ekim 16:18): adet düşüyorsa en çok 3 cm
            u = d["uzatma"]
            n += (f". Panel boyu {tr((d['boy_m'] - d['taban_boy_m']) * 100, 0)} cm uzatıldı (Lokman, 4 Ekim 16:18: adet düşüyorsa en çok 3 cm): "
                  f"L {u['taban_boy_mm']} ile {u['taban_adet']} gerekiyordu, L {u['boy_mm']} ile {u['adet']} yetiyor. "
                  f"Tam boy giden {d['tam_boy_adedi']} panelde fazlalık mahya ucunda kalır; taşma {tr(d['tasma_m'] * 100, 1).replace(',0', '')} cm")
            if d["bir_cm_payla_adet"] != d["adet"]:
                n += f"; kesim payı 1 cm olsa {d['bir_cm_payla_adet']}"
        elif d["uzun_panelle"]:    # boy listeden: biraz uzun panelle adet düşerdi (yalnız bilgi)
            n += f". Panel L {d['uzun_panelle']['boy_mm']} ve daha uzun olsaydı {d['uzun_panelle']['adet']} panel yeterdi (bilgi; boy listeden)"
        else:
            if d["paysiz_adet"] != d["adet"]:
                n += f"; kesim payı sıfır olsa {d['paysiz_adet']}"
            if d["bir_cm_payla_adet"] != d["adet"]:
                n += f"; 1 cm olsa {d['bir_cm_payla_adet']}"
        if not paylas:
            n += ". Desen ters geldiği için artan parça karşı yüzde kullanılmaz (mühendis, 4 Ekim 12:14)"
        return d["adet"], formul, k["kirma_cati_dizilim"]["durum"], n

    def panel_boyu() -> float:
        """Listeye yazılan panel boyu: kırma dizilim uzattıysa o, değilse girdideki."""
        return dz.get("panel_boyu_m") or c["panel_boyu_m"]

    def boy_formulu() -> str:
        yv_mm = kural_degeri("panel_boyu_yuvarlama_mm")    # Lokman, 7 Ekim 2026 07:45: panel boyu yukarı yuvarlanır
        return ("; panel boyu = eğimli boy + taşma" + (f", {yv_mm} mm'ye yukarı" if yv_mm and c.get("panel_boyu_kaynak") == "kural" else "")
                + (f" + {tr((dz['panel_boyu_m'] - dz['taban_boy_m']) * 100, 0)} cm ({'pay kalsın diye' if dz['uzatma'].get('neden') == 'pay' else 'adet düşüyor'})"
                   if dz.get("uzatma") else ""))

    def kaplama_adedi(kapatma: float, parca: str):
        """Panel ya da sac adedi: kırma çatıda açılım dizilimi; çatı planı yoksa yüzey + %10. Dönen: (adet, formül, durum, not)."""
        kd = kirma_dizilim()
        if kd:
            return kd
        return (tavan(c["yuzey_m2"] * (1 + zc) / (c["panel_boyu_m"] * kapatma)), f"çatı yüzeyi × 1,10 ÷ ({parca} boyu × {tr(kapatma)})", "uydurma",
                ("çatı planı girdide yok; açılım yapılamadı. " if kirma else "") + "gerçek adet yerleşimden bulunur")

    if kaplama in ("sandvic_panel", "tek_kat_panel"):
        sandvic = kaplama == "sandvic_panel"
        kap = kapatma_genisligi(k, c, kaplama)             # ürüne göre değişir (Lokman, 4 Ekim 15:18); girdide yazıyorsa o
        ad = "Sandviç panel" if sandvic else "Tek kat panel"
        if c.get("dizilim"):   # genel model (çok düzlemli çatı): dizilim yüz yüz yapılmıştır; her panel boyu ayrı satır
            dg = c["dizilim"]
            if abs(dg["kapatma_m"] - kap) > 1e-9:
                raise SystemExit(f"Girdideki kaplama dizilimi {tr(dg['kapatma_m'])} m kapatma genişliğiyle üretilmiş; {ad.lower()} {tr(kap)} m kapatır. "
                                 "Girdi o kaplamayla yeniden üretilmeli (tanımda `cati.kaplama`).")
            for i, sat in enumerate(dg["satirlar"]):
                ekle("Çatı kaplamaları", ad, f"L {round(sat['boy_m'] * 1000)} · {round(kap * 100)} cm kapatır", sat["adet"], c["yuzey_m2"] if i == 0 else None,
                     formul="çatı açılımı: her yüz şerit şerit dizilir; panel boyları tam boy şeritlerin boyu; çapraz kesilen parçalar eşlenir",
                     durum="varsayim" if len(dg["satirlar"]) > 1 else k["kirma_cati_dizilim"]["durum"],
                     not_=(f"toplam {dg['adet']} panel ({tr(dg['panel_m2'], 1)} m²; çatı yüzeyi {tr(c['yuzey_m2'], 1)} m²): {dg['tam_boy']} şerit tam boy, {dg['karma']} köşesi kesilen, "
                           f"{dg['cift']} çift ve {dg['tek']} tek kesik parça. Kırma çatı kuralının (Lokman, 4 Ekim 01:42 ve 15:18) çok düzlemli çatıya genellemesi: "
                           f"saçaktan {tr(dg['tasma_cm'], 0)} cm taşma, kesim payı {tr(dg['kesim_payi_mm'], 0)} mm, yedek panel yok; "
                           f"{(k.get('cok_duzlemli_cati') or {}).get('satir_notu_son') or 'teyit bekliyor'}"
                           # panel boyu uzatma kuralının uyguladığı değişiklik (yalnız nedeni yazılı girdide: `taban_icin_de` kuralı, 7 Ekim 2026)
                           + "".join(f". Panel boyu L {round(u['taban_boy_cm'] * 10)} → L {round(u['boy_cm'] * 10)} ("
                                     + (f"pay kalsın diye: adet aynı ({u['adet']}); kısa boyla kesim payı 1 cm olsa {u['taban_saglamlik_adet']} gerekirdi"
                                        + (f", bu boyla {u['saglamlik_adet']}" if u.get("saglamlik_adet", u["adet"]) != u["adet"] else "")
                                        + f"; {k['panel_boyu_uzatma'].get('satir_notu_pay') or 'teyit bekliyor'}"
                                        if u["neden"] == "pay" else f"adet {u['taban_adet']} → {u['adet']}; Lokman, 4 Ekim 16:18") + ")"
                                     for u in dg.get("uzatma") or [] if "neden" in u)) if i == 0 else None)
        elif c.get("yuzey_m2") and c.get("panel_boyu_m"):
            n_, f_, d_, not__ = kaplama_adedi(kap, "panel")
            ekle("Çatı kaplamaları", ad, f"L {round(panel_boyu() * 1000)} · {round(kap * 100)} cm kapatır", n_, c["yuzey_m2"],
                 formul=f_ + boy_formulu(), durum=d_, not_=not__)
        ekle("Çatı kaplamaları", "Metal kiremit mahyası", "L 2800", tavan(c["mahya_hatti_m"] / (pm - bm)), c["mahya_hatti_m"], birim="m", formul=mahya_formul, durum=mahya_durum, not_=mahya_notu)
        # Sac panel kapaması (2025 listelerinden). Tek kat panelde listeden çıktı (Lokman, 4 Ekim 2026 16:18: damlalıkla aynı gerekçe);
        # sandviç panelde şimdilik kalıyor (Lokman, 4 Ekim 2026 17:46). Girdide `cati.panel_kapamasi` yazıyorsa o: kapaması olan gerçek liste örnekleri öyle hesaplanır.
        if c.get("panel_kapamasi", deg(k, "panel_kapamasi")[kaplama]):
            sk_k = kural_degeri("sandvic_kapama") if sandvic else None      # Lokman, 7 Ekim 2026 07:45: kapama dere boyunca gider
            sk_ = sb.get("sandvic_kapama") if sandvic else None       # Eylül 2026 şablonu (yalnız `--sablon 2026`)
            if sk_k and not sk_:    # kural: boy = saçak kenarlarının toplamı (dere boyu; çatı panelli ek yapının saçağı dahil); adet = boy ÷ (parça boyu − bindirme)
                ekle("Çatı kaplamaları", f"{ad} kapaması", f"L {round(sk_k['parca_boyu_m'] * 1000)}", tavan(sacak / (sk_k["parca_boyu_m"] - sk_k["bindirme_m"])), sacak, birim="m",
                     formul=(f"saçak boyu toplamı (dere hatları {tr((c.get('dere') or {})['boy_m'])} m + deresiz saçak {tr(sacak - (c.get('dere') or {})['boy_m'])} m)"
                             if (c.get("dere") or {}).get("boy_m") and sacak - c["dere"]["boy_m"] > 0.005 else "saçak (dere) boyu toplamı")
                            + f" ÷ ({tr(sk_k['parca_boyu_m'], 1)} − {tr(sk_k['bindirme_m'])} bindirme)", durum=k["sandvic_kapama"]["durum"],
                     not_=k["sandvic_kapama"].get("satir_notu"))
            elif sk_:   # Eylül 2026 şablonu: L 2800, bütün saçakların toplamı ÷ (2,8 − 0,20)
                ekle("Çatı kaplamaları", f"{ad} kapaması", f"L {round(sk_['parca_boyu_m'] * 1000)}", tavan(sacak / (sk_["parca_boyu_m"] - sk_["bindirme_m"])), sacak, birim="m",
                     formul=f"saçak boyu toplamı ÷ ({tr(sk_['parca_boyu_m'], 1)} − {tr(sk_['bindirme_m'])} bindirme)", durum=SABLON,
                     not_="Eylül 2026 şablonu: L 2800, toplamdan. Bugünkü kuralda " + (
                         f"L {round(sk_k['parca_boyu_m'] * 1000)}, saçak (dere) boyu toplamı ÷ ({tr(sk_k['parca_boyu_m'], 1)} − {tr(sk_k['bindirme_m'])}) (Lokman, 7 Ekim 07:45)"
                         if sk_k else "L 2500, her saçak kenarı ayrı ayrı yukarı (2025 listelerinden)"))
            else:
                ekle("Çatı kaplamaları", f"{ad} kapaması", "L 2500", kenar_kenar(kenarlar, deg(k, "parca_boyu_m", "sandvic_kapama")), sacak, birim="m",
                     formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma",
                     not_="listedeki uygulama (2025): sac kapama" if "panel_kapamasi" in c else
                          "2025 listelerindeki sac kapama. Tek kat panel kapaması listeden çıktı (Lokman, 4 Ekim 16:18); sandviç panelde şimdilik kalıyor "
                          "(Lokman, 4 Ekim 17:46). Adet formülü 2025 listelerinden çıkarıldı")
    elif (kaplama in OSBLI_KAPLAMA or kaplama == "trapez_sac") and not c.get("yuzey_m2"):
        ekle("Çatı kaplamaları", f"Çatı kaplaması ({KAPLAMA_ADI[kaplama]})", "", None, birim="",
             formul="çatı yüzeyi girdide yok; kaplama kalemleri hesaplanmadı", durum="bekliyor")
    elif kaplama in OSBLI_KAPLAMA or kaplama == "trapez_sac":
        ckat = deg(k, "cati_katsayisi").get(c["tip"], 1.0)
        if kaplama in OSBLI_KAPLAMA:
            ekle("Çatı kaplamaları", "Çatı OSB", osb_boyut, tavan(c["yuzey_m2"] * (1 + zo) / deg(k, "levha_m2", "osb")), c["yuzey_m2"],
                 formul="çatı yüzeyi × 1,05 ÷ 2,98", durum="uydurma",
                 not_=(f"kırma çatıda gerçek listeyle sınanmadı; motorun çatı katsayısıyla (× {tr(ckat)}) {tavan(c['yuzey_m2'] * ckat / deg(k, 'levha_m2', 'osb'))} adet; "
                       "mühendisin 10 × 10 m dört omuz metrajında yüzeyin 1,13 katı OSB var") if kirma else None)
            if c.get("nem_bariyeri", yontem == "panel"):
                ekle("Çatı kaplamaları", "Nem bariyeri", "m²", tavan(c["yuzey_m2"] * ckat), c["yuzey_m2"],
                     formul=f"çatı yüzeyi × çatı katsayısı ({tr(ckat)})", durum="motor")
        if kaplama == "osb_kiremit":
            kk_m = kapatma_genisligi(k, c, kaplama)
            if kirma:
                n_, f_, d_, not__ = kaplama_adedi(kk_m, "sac")
                ekle("Çatı kaplamaları", "Metal kiremit (kiremit desen sac)", f"L {round(panel_boyu() * 1000)} · {round(kk_m * 100)} cm kapatır",
                     n_, c["yuzey_m2"], formul=f_ + boy_formulu(), durum=d_, not_=not__ + ". Kırma çatıda gerçek listeyle sınanmadı")
            else:
                ekle("Çatı kaplamaları", "Metal kiremit", f"{round(kk_m * 100)} cm kapatır", tavan(sacak / kk_m), sacak, birim="m",
                     formul=f"saçak boyu ÷ {tr(kk_m)}; boy = eğimli boy", durum="uydurma")
            mahyalar = ("Metal kiremit mahyası", "OSB mahyası")
        elif kaplama in ("osb_trapez", "trapez_sac"):
            tk = kapatma_genisligi(k, c, kaplama)
            trapez_notu = ("Gerçek listeyle karşılaştırılmadı. Excel motorundaki formül yüzey ÷ sac boyu × 0,8 yapıyor: 0,8 paydanın parantezi dışında kaldığı için "
                           "kapatma genişliğine bölmek yerine çarpıyor (4 Ekim'de yeniden okundu); mühendisin 10 × 10 m beşik çatı metrajındaki 28 adedi ÷ 0,8 veriyor, "
                           "o yüzden motorun formülü kullanılmadı")
            if kirma:
                n_, f_, d_, not__ = kaplama_adedi(tk, "sac")
                ekle("Çatı kaplamaları", "Trapez sac", f"L {round(panel_boyu() * 1000)} · {round(tk * 100)} cm kapatır",
                     n_, c["yuzey_m2"], formul=f_ + boy_formulu(), durum=d_, not_=not__ + ". " + trapez_notu)
            else:
                ekle("Çatı kaplamaları", "Trapez sac", f"{round(tk * 100)} cm kapatır", kenar_kenar(kenarlar, tk), sacak, birim="m",
                     formul=f"her saçak kenarı ÷ {tr(tk)}, ayrı ayrı yukarı; boy = eğimli boy", durum="uydurma",
                     not_="gerçek adet yerleşimden bulunur. " + trapez_notu)
            pt, bt = deg(k, "parca_boyu_m", "trapez_mahyasi"), deg(k, "bindirme_m", "trapez_mahyasi")
            ekle("Çatı kaplamaları", "Trapez sac mahyası", f"L {round(pt * 1000)}", tavan(c["mahya_hatti_m"] / (pt - bt)), c["mahya_hatti_m"], birim="m",
                 formul=f"mahya hattı (tepe + kırmalar) ÷ ({tr(pt, 1)} − {tr(bt)} bindirme)", durum="motor",
                 not_="bindirme motordaki 20 cm; Lokman'ın 30 cm kuralı uygulanırsa ÷ 0,5. Gerçek listeyle karşılaştırılmadı")
            mahyalar = ("OSB mahyası",) if kaplama == "osb_trapez" else ()
        else:   # osb_shingle
            for ad, anahtar in (("Membran", "membran_adet_m2"), ("Shingle", "shingle_adet_m2")):
                b = deg(k, anahtar)
                ekle("Çatı kaplamaları", ad, f"adet / {tr(b, 0)} m²", tavan(c["yuzey_m2"] * ckat / b), c["yuzey_m2"],
                     formul=f"çatı yüzeyi × çatı katsayısı ({tr(ckat)}) ÷ {tr(b, 0)}", durum="motor",
                     not_="yalnız Excel motorunun formülüyle; gerçek listeyle karşılaştırılmadı")
            mahyalar = ("OSB mahyası",)
        for ad in mahyalar:
            ekle("Çatı kaplamaları", ad, "L 2800", tavan(c["mahya_hatti_m"] / (pm - bm)), c["mahya_hatti_m"], birim="m", formul=mahya_formul, durum=mahya_durum, not_=mahya_notu)
    # Çatının bir duvara dayandığı kenarlar (alçak çatının bina duvarına ya da kalkana dayandığı yer): Lokman, 8 Ekim 2026 00:45: o kenara özel mahya konur
    # (kurallar: `duvar_dibi.malzeme`). Kural öyle diyorsa boyları özel mahya satırına yazılır; demiyorsa aşağıdaki geçici satır (eski davranış).
    # Eylül 2026 katmanı (`--sablon 2026`) o kenara damlalık yazar; ama yalnız kenarlar yapı yapı verilmişse. Verilmemişse bugünkü kural uygulanır.
    dd_liste = c.get("duvar_dibi") or []
    dd_boy = (sum(x["boy_m"] for x in dd_liste) if dd_liste else c.get("duvar_dibi_m")) or 0.0
    dd_kural_ozel = (kural_degeri("duvar_dibi") or {}).get("malzeme") == "ozel_mahya"
    dd_damlalik = bool(sb.get("duvar_dibi") and dd_liste)
    dd_ozel = dd_boy if dd_kural_ozel and not dd_damlalik else 0.0
    dd_ozel_notu = None         # satır notları (`satir_notlari`) uygulandıktan sonra özel mahya satırına eklenir
    if dd_ozel:
        om_boy = (c.get("ozel_mahya_m") or 0.0) + dd_ozel
        dd_dokum = (" + ".join(f"{x.get('yapi') or 'kenar'} {tr(x['boy_m'])} m" for x in dd_liste) if dd_liste else f"{tr(dd_ozel)} m")
        om_adet = tavan(om_boy / (pm - bm))
        # bilgi: boylar toplanmadan, yapı yapı yuvarlansaydı (Eylül 2026 listesi o kenardaki damlalığı böyle yuvarlamıştı)
        om_ayri = ((tavan(c["ozel_mahya_m"] / (pm - bm)) if c.get("ozel_mahya_m") else 0)
                   + (sum(tavan(x["boy_m"] / (pm - bm)) for x in dd_liste) if dd_liste else tavan(dd_ozel / (pm - bm))))
        dd_ozel_notu = k["duvar_dibi"].get("satir_notu")
        if dd_ozel_notu and om_ayri != om_adet:
            dd_ozel_notu += f"; her yapının kenarı ayrı yuvarlansa {om_ayri} olurdu"
        ekle("Çatı kaplamaları", "Özel mahya (geniş)", "L 2800", om_adet, om_boy, birim="m",
             formul=((f"(ana bina ile veranda çıkıntısının çatısı arasındaki birleşim {tr(c['ozel_mahya_m'])} m + çatının duvara dayandığı kenarlar: {dd_dokum}) ÷ (2,8 − {tr(bm)})")
                     if c.get("ozel_mahya_m") else f"çatının duvara dayandığı kenarların boyu ({dd_dokum}) ÷ (2,8 − {tr(bm)})"),
             durum=k["duvar_dibi"]["durum"] if mahya_durum != SABLON else mahya_durum, not_=mahya_notu)
    elif c.get("ozel_mahya_m"):
        # katmanla, kural özel mahya derken: duvara dayanan kenarlar damlalık satırına gitti; bu satırda yalnız birleşim kaldı (farkın nedeni bu, bindirme değil)
        ekle("Çatı kaplamaları", "Özel mahya (geniş)", "L 2800", tavan(c["ozel_mahya_m"] / (pm - bm)), c["ozel_mahya_m"], birim="m",
             formul=f"ana bina ile veranda çıkıntısının çatısı arasındaki birleşim boyu ÷ (2,8 − {tr(bm)})", durum=mahya_durum,
             not_=("Eylül 2026 şablonu: çatının duvara dayandığı kenarlar damlalık satırında. Bugünkü kuralda o kenarlar da bu satırdadır (Lokman, 8 Ekim 00:45)"
                   if dd_kural_ozel and dd_damlalik else mahya_notu))
    if c.get("ters_mahya_m"):
        ekle("Çatı kaplamaları", "Ters mahya", "L 2800", tavan(c["ters_mahya_m"] / (pm - bm)), c["ters_mahya_m"], birim="m",
             formul=f"cumbalı çatıda çatıların birleştiği vadi boyu ÷ (2,8 − {tr(bm)})", durum=mahya_durum, not_=mahya_notu)
        tk_ = kural_degeri("ters_mahya_kenar_kutusu") or {}
        if tk_.get("varsayilan"):               # Lokman, 7 Ekim 2026 08:02: cumbalı çatılarda olmazsa olmaz; adet çatıya göre değişir (ters mahyaya bağlı)
            ekle("Çatı kaplamaları", "Ters mahya kenar kutusu", tk_["boyut"], adet_of("Ters mahya") * tk_["ters_mahya_basina"], birim="",
                 formul=f"ters mahya adedi × {tk_['ters_mahya_basina']}", durum=k["ters_mahya_kenar_kutusu"]["durum"], not_=k["ters_mahya_kenar_kutusu"].get("satir_notu"))
        elif sb.get("ters_mahya_kenar_kutusu"):   # Eylül 2026 listesi ve Excel motoru: ters mahyanın iki yanına kenar kutusu. 2025 listelerinde yok; soruldu
            ekle("Çatı kaplamaları", "Ters mahya kenar kutusu", tk_["boyut"], adet_of("Ters mahya") * tk_["ters_mahya_basina"], birim="",
                 formul=f"ters mahya adedi × {tk_['ters_mahya_basina']}", durum=SABLON,
                 not_="Eylül 2026 listesinde ve Excel motorunda var; 2025 tarihli cumbalı listede yoktu")
    # Aynı kenarlar, Eylül 2026 katmanıyla ve eski kural setleriyle. Eylül 2026 listesinde bu kenarda damlalık (L 2500) var; Lokman damlalığı listeden
    # tamamen çıkarmıştı (4 Ekim 2026 15:18): yalnız `--sablon 2026` ile. Kuralın malzeme söylemediği setlerde (0.13 ve öncesi) satır geçicidir (soru).
    dd_s = sb.get("duvar_dibi")
    damlalik_adi = f"{dd_s['parca']} (çatının duvara dayandığı kenar)" if dd_s else None
    if c.get("duvar_dibi") and dd_s:
        etkin = dd_s["parca_boyu_m"] - dd_s["bindirme_m"]
        toplam = sum(x["boy_m"] for x in c["duvar_dibi"])
        ekle("Çatı kaplamaları", damlalik_adi, f"L {round(dd_s['parca_boyu_m'] * 1000)}",
             sum(tavan(x["boy_m"] / etkin) for x in c["duvar_dibi"]), toplam, birim="m",
             formul=" + ".join(f"{x['yapi']} {tr(x['boy_m'])} m" for x in c["duvar_dibi"]) + f"; her biri ÷ ({tr(dd_s['parca_boyu_m'], 1)} − {tr(dd_s['bindirme_m'])} bindirme), ayrı ayrı yukarı",
             durum=SABLON,
             not_="Eylül 2026 listesi: alçak çatının bina duvarına ya da kalkana dayandığı kenarda damlalık. Bugünkü kuralda damlalık listede yok "
                  "(Lokman, 4 Ekim 15:18); " + ("o kenara özel mahya konur (Lokman, 8 Ekim 00:45)" if dd_kural_ozel else "duvar dibindeki kullanım soruldu"))
    elif (c.get("duvar_dibi") or c.get("duvar_dibi_m")) and not dd_kural_ozel:
        dd_boy = sum(x["boy_m"] for x in c["duvar_dibi"]) if c.get("duvar_dibi") else c["duvar_dibi_m"]
        pdd = deg(k, "duvar_dibi")["parca_boyu_m"]           # geçici: mahya parçası gibi (L 2800, bugünkü kuraldaki mahya bindirmesiyle)
        bdd = deg(k, "bindirme_m", "mahya")
        ekle("Çatı kaplamaları", "Duvar dibi sacı (çatının duvara dayandığı kenar)", f"L {round(pdd * 1000)}", tavan(dd_boy / (pdd - bdd)), dd_boy, birim="m",
             formul=f"duvara dayanan çatı kenarlarının boyu ÷ ({tr(pdd, 1)} − {tr(bdd)}); mahya parçası gibi sayıldı", durum=k["duvar_dibi"]["durum"],
             not_="kural yok: alçak çatının bina duvarına ya da kalkana dayandığı yerde hangi parçanın gittiği sorulacak; adet mahya parçası kuralıyla geçici"
                  + (". Eylül 2026 listesinde bu kenarda damlalık (L 2500) var; damlalık listeden çıkmıştı (Lokman, 4 Ekim 15:18): soruldu" if c.get("duvar_dibi") else ""))
    # mahya bandı (mühendis, 4 Ekim 2026 12:14): (mahya adedi × 2,8 + ters mahya adedi × 2,8 + damlalık adedi × 2,5) ÷ 10.
    # Excel motorunda trapez sac mahyası × 0,8 de toplanır; OSB mahyası ve özel mahya toplanmaz.
    # Damlalık listeden tamamen çıktı (Lokman, 4 Ekim 2026 15:18: montajcılar kullanmıyor): varsayılan hesapta terimi yok. Listede damlalık satırı
    # varsa (yalnız `--sablon 2026` ile) terimi de sayılır. Baca çatıyı deliyorsa çevresi eklenir (kör test listesi).
    mb = deg(k, "mahya_bandi")
    bant_parcalari = [(s["kalem"], s["adet"], mb["parca_boyu_m"][anahtar]) for s in S for kalem, anahtar in
                      (("Metal kiremit mahyası", "metal_kiremit_mahyasi"), ("Ters mahya", "ters_mahya"), ("Trapez sac mahyası", "trapez_sac_mahyasi"), (damlalik_adi, "damlalik"))
                      if s["kalem"] == kalem and s["adet"]]
    bant_boyu = sum(n * boy for _, n, boy in bant_parcalari)
    damlalikli = any(ad == damlalik_adi for ad, _, _ in bant_parcalari)
    baca_cevresi = (c.get("baca_cevresi_m") or 0.0) if mb.get("baca_cevresi") else 0.0      # baca çatıyı deliyorsa çevresi de bantlanır (kör test listesi)
    if bant_boyu > 0:
        ekle("Çatı kaplamaları", "Mahya bandı", f"rulo / {tr(mb['rulo_m'], 0)} m", tavan((bant_boyu + baca_cevresi) / mb["rulo_m"]), bant_boyu + baca_cevresi, birim="m",
             formul="(" + " + ".join(f"{ad.split(' (')[0].lower() if ad == damlalik_adi else ad.lower()} {n} × {tr(boy, 1)} m" for ad, n, boy in bant_parcalari)
                    + (f" + baca çevresi {tr(baca_cevresi)} m" if baca_cevresi else "") + f") ÷ {tr(mb['rulo_m'], 0)}",
             durum=SABLON if damlalikli else k["mahya_bandi"]["durum"],
             not_=("formül: mühendis, 4 Ekim 12:14 (Excel motorundaki gibi); damlalık (duvar dibi) terimi Eylül 2026 listesindeki gibi formülde "
                   "(bugünkü kuralda damlalık yok: Lokman, 4 Ekim 15:18); bacanın çatıdaki çevresi eklendi" if damlalikli else
                   "formül: mühendis, 4 Ekim 12:14 (Excel motorundaki gibi). Damlalık terimi yok (Lokman, 4 Ekim 15:18); bacanın çatıdaki çevresi eklendi (gerçek listedeki gibi)" if baca_cevresi else
                   "formül: mühendis, 4 Ekim 12:14 (Excel motorundaki gibi). Damlalık kullanılmıyor: listede yok, formüldeki terimi de çıkarıldı (Lokman, 4 Ekim 15:18)"))
    # çatı müdahale kapağı: standart pakette gönderilmez; müşteri isterse eklenir (mühendis, 4 Ekim 2026)
    mkp = deg(k, "cati_mudahale_kapagi")
    if mkp.get("standart_pakette"):    # Lokman, 7 Ekim 2026 07:45: dış kapı gibi her yapıya 1 adet, standart
        ekle("Çatı kaplamaları", mkp["ad"], "adet", mkp["yapi_basina"], birim="", formul=f"her yapıya {mkp['yapi_basina']} adet (standart)",
             durum=k["cati_mudahale_kapagi"]["durum"], not_=k["cati_mudahale_kapagi"].get("satir_notu"))
    elif g.get("cati_mudahale_kapagi"):
        ekle("Çatı kaplamaları", "Çatı müdahale kapağı", "adet", g.get("kat_adedi", 1) * mkp["kat_basina"], birim="",
             formul="müşteri isterse: kat adedi × 1", durum=k["cati_mudahale_kapagi"]["durum"])
    if c.get("cati_boyu_m") and c.get("bina_eni_m"):
        silte = c["cati_boyu_m"] * (c["bina_eni_m"] + deg(k, "silte_en_payi_m"))
        sd = c.get("silte_dusulen_m2")                         # genel model: dikdörtgenin içinde kalan çatısız veranda (Ç8801); tavanı yok
        if sd:
            silte -= sd
        silte_kat = c.get("silte_kat", 1)
        si_mm = sb.get("cati_izolasyonu_kalinligi_mm")       # Eylül 2026 şablonu: "çatı izolasyonu 100 mm"; 2025 listelerinde "çatı şiltesi 80 mm"
        sa = tr(deg(k, "silte_adet_m2"), 1)                   # paket alanı (0.20: İzocam 80 mm, 9,0; önceki setlerde 9,6)
        ekle("Çatı kaplamaları", f"Çatı izolasyonu {si_mm} mm" if si_mm else "Çatı şiltesi 80 mm", f"{sa} m²/adet", silte_kat * tavan(silte / deg(k, "silte_adet_m2")), silte,
             formul=(f"(çatı boyu × (bina eni + 0,20) − çatısız veranda {tr(sd, 2)} m²) ÷ {sa}" if sd else f"çatı boyu × (bina eni + 0,20) ÷ {sa}")
                    + (f" × {silte_kat} kat" if silte_kat > 1 else ""), durum=SABLON if si_mm else "uydurma",
             not_=(f"Eylül 2026 şablonu: kalem 'çatı izolasyonu {si_mm} mm'; 2025 listelerinde 'çatı şiltesi 80 mm'. Adet formülü aynı "
                   "(şablonda: çatı taban alanı, 30 cm saçak payıyla, ÷ 9,6)") if si_mm else None)

    # ── Dere ────────────────────────────────────────────────────────────────
    pd, bd = deg(k, "parca_boyu_m", "dere"), deg(k, "bindirme_m", "dere")
    dr = c.get("dere")                                     # genel model: dere hatları (çatı panelli ek yapının saçağında dere yok)
    dere_boyu = dr["boy_m"] if dr else sacak
    deresiz = bool(dr) and sacak - dere_boyu > 0.005
    dere = tavan(dere_boyu / (pd - bd))
    ekle("Dere", "Metal dere", "L 4000", dere, dere_boyu, birim="m", formul=("dere hatlarının boyu" if deresiz else "saçak boyu") + f" ÷ (4,0 − {tr(bd)} bindirme)", durum="motor",
         not_=(f"{pc_ad} saçağında ({tr(sacak - dere_boyu)} m) dere yok "
               + ("(kural `ek_yapi_ve_korkuluk`: KT-01'in gerçek listesi ve dere paftası)" if c.get("panelli_cati_adi") else "(gerçek liste ve dere paftası)")) if deresiz else
              (f"{pc_ad} saçağı dahil ({tr(c['panel_kenari']['sacak_m'])} m; Lokman, 10 Ekim 2026)" if kural_degeri("panel_cati_kenarlari") and c.get("panel_kenari") else None))
    n_kural, n_not = inis_sayisi(c, k)
    if "inis_adedi" in c:
        n, n_durum = c["inis_adedi"], "liste"
        n_formul = f"listedeki iniş sayısı ({n}); " + (f"kural {n_kural} verir" if n_kural is not None else "kural hesaplanmadı: cephe ölçüleri yok")
    elif "inis_adedi_plan" in c:   # plana bakarak elle yerleştirilen inişler (Ubeydullah, 3 Ekim 2026)
        n, n_durum = c["inis_adedi_plan"], "model"
        n_formul = f"plana yerleştirilen iniş sayısı ({n}); " + (f"kural {n_kural} verir" if n_kural is not None else "kural hesaplanmadı")
    else:
        n, n_durum, n_formul = n_kural, "lokman", n_not
    inis_kuraldan = n_durum == "lokman"
    inis_notu = ("iniş plana bakarak yerleştirilir; düz saçakta ortalama 5 m'de bir (mühendis, 3 Ekim). Planda elle yerleştirilmediği için Lokman'ın kuralı kullanıldı")
    if inis_kuraldan and deg(k, "inis").get("olcu") == "dere":     # durum ve not kural dosyasından (eşik 7 Ekim'de öneriydi; 8 Ekim 2026'da onaylandı)
        n_durum, inis_notu = k["inis"]["durum"], k["inis"].get("satir_notu", inis_notu)
    ib = deg(k, "inis_basina")
    for ad, anahtar in (("Dere iniş borusu", "inis_borusu"), ("Dere iniş aparatı", "inis_aparati"), ("Açık dirsek", "acik_dirsek"),
                        ("Kapalı dirsek", "kapali_dirsek"), ("İniş kelepçesi", "inis_kelepcesi")):
        ekle("Dere", ad, "L 3000" if anahtar == "inis_borusu" else "adet", n * ib[anahtar], birim="",
             formul=(n_formul if anahtar == "inis_borusu" else f"iniş sayısı × {ib[anahtar]}"),
             durum=n_durum if (anahtar == "inis_borusu" or n_durum == "liste") else "motor",
             not_=inis_notu if anahtar == "inis_borusu" and inis_kuraldan else None)
    if c.get("dere_kapagi") is not None:
        ekle("Dere", "Dere kapağı", "adet", c["dere_kapagi"], birim="", formul="listedeki sayı; motorda çatı tipine göre sabit", durum="liste")
    elif dr and deg(k, "dere_kapagi_serbest_uc"):          # genel model: kapak, başka bir dere hattıyla buluşmayan uçlara gelir
        if dr["serbest_uc"]:
            ekle("Dere", "Dere kapağı", "adet", dr["serbest_uc"], birim="", formul=f"dere hatlarının serbest uçları ({len(dr['hatlar_m'])} hat, {dr['uc']} uç; iki hattın buluştuğu köşede kapak yok)",
                 durum=k["dere_kapagi_serbest_uc"]["durum"], not_=f"motorun çatı tipine göre sabiti: {deg(k, 'dere_kapagi').get(c['tip'], 0)}")
    elif deg(k, "dere_kapagi").get(c["tip"]):
        ekle("Dere", "Dere kapağı", "adet", deg(k, "dere_kapagi")[c["tip"]], birim="", formul="çatı tipine göre sabit (dört omuzda yok)", durum="motor")
    ekle("Dere", "Dere kelepçesi", "adet", dere * deg(k, "dere_kelepcesi_dere_basina"), birim="", formul="dere adedi × 8", durum="motor")

    # ── Metal aksam ─────────────────────────────────────────────────────────
    ps = deg(k, "parca_boyu_m", "sacak_saci")
    tavan_toplam = sum(v for v in g["tavan_m2"].values() if v)
    if yontem == "omega_asik":
        sbb = sb.get("bindirme_m") or {}
        sablon_notu = "Eylül 2026 şablonu: 20 cm bindirme. Bugünkü kuralda 30 cm (Lokman, 3 Ekim 13:27)"
        # saçak sacı ve saçak omegası: genel modelde çatı panelli ek yapının saçağı hariç (kurallar: `ek_yapi_ve_korkuluk`)
        sacli = c.get("sacak_saci_kenarlari_m", kenarlar)
        sacli_boy = sum(sacli) if "sacak_saci_kenarlari_m" in c else sacak
        bs = sbb.get("sacak_saci", deg(k, "bindirme_m", "sacak_saci"))
        panelsiz = (f"{pc_ad} saçağı ({tr(sacak - sacli_boy)} m) hariç" if sacak - sacli_boy > 0.005 else None)
        ekle("Metal aksam", "Saçak sacı (30'luk)", "L 2500", tavan(sacli_boy / (ps - bs)), sacli_boy, birim="m",
             formul=f"saçak boyu ÷ (2,5 − {tr(bs)} bindirme)", durum=SABLON if "sacak_saci" in sbb else "lokman",
             not_=(sablon_notu if "sacak_saci" in sbb else
                   k["bindirme_m"]["sacak_saci"].get("satir_notu", "30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden (Lokman'ın örneğinde L 2800 ÷ 2,5)"))
                  + (f"; {panelsiz}" if panelsiz else ""))
        so = sb.get("sacak_omegasi") or {}
        if so.get("olcu") == "cephe" and c.get("sacak_omegasi_cephe_m"):   # Eylül 2026 şablonu: saçaksız cephe boyunun toplamı ÷ 2,5
            cephe_top = sum(c["sacak_omegasi_cephe_m"])
            ekle("Metal aksam", c.get("sacak_omegasi", "Saçak omegası"), "L 2500", tavan(cephe_top / ps), cephe_top, birim="m",
                 formul="saçağın altındaki cephe boyu (saçak payı hariç) toplamı ÷ 2,5", durum=SABLON,
                 not_="Eylül 2026 şablonu. Bugünkü kuralda her saçak kenarı ÷ 2,5, ayrı ayrı yukarı (2025 listelerinden)" + (f"; {panelsiz}" if panelsiz else ""))
        else:
            ekle("Metal aksam", c.get("sacak_omegasi", "Saçak omegası"), "L 2500", kenar_kenar(sacli, ps), sacli_boy, birim="m",
                 formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma", not_=panelsiz)
        if c.get("alin_saci_m"):
            pa, ba = deg(k, "parca_boyu_m", "alin_saci"), sbb.get("alin_saci", deg(k, "bindirme_m", "alin_saci"))
            ekle("Metal aksam", "Alın sacı (30'luk)", "300 × 2500", tavan(c["alin_saci_m"] / (pa - ba)), c["alin_saci_m"], birim="m",
                 formul=f"alın boyu ÷ (2,5 − {tr(ba)} bindirme)", durum=SABLON if "alin_saci" in sbb else "lokman",
                 not_=(sablon_notu if "alin_saci" in sbb else k["bindirme_m"]["alin_saci"].get("satir_notu", "30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden"))
                      + (f"; {pc_ad} alınları hariç" if c.get("ek_cati") else ""))
            if c.get("alin_saci_kenarlari_m"):   # genel model: baş makasın (kalkan makası) alnı boyunca Z profil (105 m² ve kör test listeleri)
                bz = deg(k, "bas_makas_z")
                pz = bz["parca_boyu_m"]
                z_adet = kenar_kenar(c["alin_saci_kenarlari_m"], pz) if bz["kenar_kenar"] else tavan(c["alin_saci_m"] / pz)
                ekle("Metal aksam", "Baş makas Z'si", f"L {round(pz * 1000)}", z_adet, c["alin_saci_m"], birim="m",
                     formul=(f"her alın kenarı ÷ {tr(pz, 1)}, ayrı ayrı yukarı ({len(c['alin_saci_kenarlari_m'])} kenar)" if bz["kenar_kenar"] else f"alın boyu ÷ {tr(pz, 1)}"),
                     durum=k["bas_makas_z"]["durum"],
                     not_=f"Eylül 2026 şablonundaki formül toplam alın boyu ÷ {tr(pz, 1)} ({tavan(c['alin_saci_m'] / pz)} verir); iki gerçek listede yazılan adet formülün "
                          "üstünde (8 ve 9). Kenar kenar yuvarlama bu iki sayıya uydurulmuş bir kuraldır; teyit bekliyor. 90 m² listede kalem yok: her beşik çatıda "
                          "gidip gitmediği soruldu")
        # Tavan omegası. Bugünkü kural (2025 listelerine uydurma): tavan alanı ÷ 0,60 ÷ 3,75; 2025 paftalarındaki dizilimin (ilk hat duvardan 60 cm içeride)
        # toplamına denk gelir. Eylül 2026 uygulaması (`--sablon 2026`): dizilim modelden (her tavan gözünde ilk hat duvar yüzünde; `tavan_omegasi_dizilim`),
        # adet şablondaki ve Excel motorundaki formülle: toplam boy ÷ (3,75 − 0,10 bindirme) + 5.
        to = g.get("tavan_omegasi")
        s26 = (k.get("sablon_2026") or {}).get("deger") or {}     # varsayılan satırların notunda "şablonla şu kadar" demek için; katman yoksa not da yok
        s26_om, s26_as = s26.get("tavan_omegasi"), s26.get("asik")
        so_ = sb.get("tavan_omegasi") or {}
        po = deg(k, "parca_boyu_m", "tavan_omegasi")
        om = g.get("tavan_omegasi_m2", tavan_toplam) / deg(k, "tavan_omegasi_aralik_m")
        alan_formulu = ("tavan alanı ÷ 0,60" if "tavan_omegasi_m2" not in g else
                        f"makasların altındaki tavan alanı ({g.get('tavan_omegasi_haric', 'çatı paneli olan ek yapı')} hariç) ÷ 0,60")
        if to and so_.get("dizilim"):
            td = deg(k, "tavan_omegasi_dizilim")
            ekle("Metal aksam", "Tavan omegası (60'lık)", "L 3750", tavan(to["boy_m"] / (po - so_["bindirme_m"]) + so_["yedek_adet"]), to["boy_m"], birim="m",
                 formul=f"tavan gözlerinde makaslara dik, {round(to.get('aralik_m', td['aralik_m']) * 100)} cm aralıkla hatlar, ilk hat duvar yüzünde ({to['hat']} hat); "
                        f"toplam boy ÷ ({tr(po)} − {tr(so_['bindirme_m'])} bindirme) + {so_['yedek_adet']}",
                 durum=SABLON,
                 not_="Eylül 2026 projesinin paftasındaki dizilim ve şablondaki formül. " + ", ".join(f"{gz['mahal']} {gz['hat']} hat {tr(gz['boy_m'], 1)} m" for gz in to["gozler"])
                      + f". Bugünkü kuralla (alan ÷ 0,60 ÷ 3,75) {tavan(om / po)}")
        elif so_:
            ekle("Metal aksam", "Tavan omegası (60'lık)", "L 3750", tavan(om / (po - so_["bindirme_m"]) + so_["yedek_adet"]), om, birim="m",
                 formul=f"{alan_formulu} ÷ ({tr(po)} − {tr(so_['bindirme_m'])} bindirme) + {so_['yedek_adet']}", durum=SABLON,
                 not_="Eylül 2026 şablonundaki ve Excel motorundaki formül; dizilim girdide yok, toplam boy alandan")
        else:
            ekle("Metal aksam", "Tavan omegası (60'lık)", "L 3750", tavan(om / po), om, birim="m", formul=f"{alan_formulu} ÷ 3,75", durum="uydurma",
                 not_=(f"Eylül 2026 projesinin paftasındaki dizilimle (her gözde ilk hat duvar yüzünde) toplam {tr(to['boy_m'], 1)} m; şablondaki formülle "
                       f"{tavan(to['boy_m'] / (po - s26_om['bindirme_m']) + s26_om['yedek_adet'])} adet. Hangisinin kural olduğu soruldu")
                 if to and s26_om and not celik_yontemi else None)
        # Aşık. Adet formülü bugünkü kuralla toplam boy × 1,05 ÷ 4,2 (2025 listelerine uydurma); Eylül 2026 şablonunda × 1,15 ÷ (4,2 − 0,10 bindirme).
        sa_ = sb.get("asik") or {}
        az, ab, pas = sa_.get("zayiat", deg(k, "asik", "zayiat")), sa_.get("bindirme_m", 0.0), deg(k, "parca_boyu_m", "asik")
        asik_bolu = f"× {tr(1 + az)} ÷ ({tr(pas, 1)} − {tr(ab)} bindirme)" if ab else f"× {tr(1 + az)} ÷ {tr(pas, 1)}"
        asik_durum = SABLON if sa_ else "uydurma"

        def asik_adedi(boy_m: float) -> int:
            return tavan(boy_m * (1 + az) / (pas - ab))

        boy = 0.0
        ar_cm = round(deg(k, "asik", "aralik_m") * 100)
        if c.get("asik"):          # genel model: sıralar yüz yüz dizilmiştir (`cok_duzlemli_cati`)
            cdk = deg(k, "cok_duzlemli_cati")
            boy = c["asik"]["boy_m"]
            ekle("Metal aksam", "Aşık", "L 4200", asik_adedi(boy), boy, birim="m",
                 formul=f"yüz yüz: alt kenardan itibaren {round(c['asik'].get('aralik_m', deg(k, 'asik', 'aralik_m')) * 100)} cm aralıkla sıralar; üst kenarla son sıra arasında "
                        f"{round(c['asik'].get('ust_sira_esigi_m', cdk['ust_sira_esigi_m']) * 100)} cm'den fazla boşluk varsa kenara bir sıra daha; "
                        f"sıranın boyu yüzün o yükseklikteki genişliği; {asik_bolu}",
                 durum=asik_durum,
                 not_=(c["asik"].get("not") or "") + ("" if sa_ or not s26_as or celik_yontemi else
                       f". Eylül 2026 şablonundaki formülle (× {tr(1 + s26_as['zayiat'])} ÷ {tr(pas - s26_as['bindirme_m'], 1)}) "
                       f"{tavan(boy * (1 + s26_as['zayiat']) / (pas - s26_as['bindirme_m']))} adet; hangisinin kural olduğu soruldu"))
        elif c.get("asik_boyu_m"):   # 6 Ekim'de dondurulan listenin girdisi: sıralar yüz yüz çıkarılmıştır
            boy = c["asik_boyu_m"]
            ekle("Metal aksam", "Aşık", "L 4200", asik_adedi(boy), boy, birim="m",
                 formul=f"yüz yüz: saçaktan itibaren {ar_cm} cm aralıkla sıralar + her üst kenarın altında mahya aşığı; sıranın boyu yüzün o yükseklikteki genişliği; {asik_bolu}",
                 durum=asik_durum, not_=c.get("asik_notu"))
        elif "asik" in c or ((kirma and "plan_m" not in c) and not c.get("egimli_boy_m")):   # genel modelin girdisi yöntem A için üretilmiş: aşık sıraları yok
            ekle("Metal aksam", "Aşık", "L 4200", None, birim="m", formul="aşık sıraları girdide yok: girdi yöntem B ile yeniden üretilmeli", durum="bekliyor")
        elif kirma or c.get("egimli_boy_m"):
            boy, not_ = asik_boyu(c, deg(k, "asik", "aralik_m"))
            ekle("Metal aksam", "Aşık", "L 4200", asik_adedi(boy), boy, birim="m",
                 formul=f"eğim boyunca {ar_cm} cm aralıkla sıralar + mahya aşığı; kırmada her sıra çatıyı dolanır; {asik_bolu}", durum=asik_durum, not_=not_)
    else:
        boy = 0.0   # yöntem A'da saçak omegası gerekmez (Ubeydullah, 3 Ekim 2026)
    if c.get("sacak_alti") == "boardex":
        # genel modelde çatı panelli ek yapının saçağı hariç: onun saçak ve alın kaplaması ek yapının Boardex satırındadır (`ek_yapi_ve_korkuluk`)
        sacak_altli = sum(c["sacak_saci_kenarlari_m"]) if celik_yontemi and c.get("ek_cati") and "sacak_saci_kenarlari_m" in c else sacak
        sa = sacak_altli * c.get("sacak_alti_eni_m", deg(k, "sacak_alti_boardex_eni_m"))
        ekle("Metal aksam", "Saçaklar için Boardex", boardex_boyut, tavan(sa * (1 + zb) / deg(k, "levha_m2", "boardex")), sa,
             formul=f"saçak boyu × saçak eni × {zb_carpan} ÷ 2,88", durum="uydurma",
             not_="saçak altının Boardex olduğu: Lokman, 3 Ekim 13:27; formül 62 m² listeden" if yontem == "panel" else None)
    if c.get("sacak_yuzu_m2"):
        ekle("Metal aksam", "Saçak yüzü için Boardex", boardex_boyut, tavan(c["sacak_yuzu_m2"] * (1 + zb) / deg(k, "levha_m2", "boardex")), c["sacak_yuzu_m2"],
             formul=f"saçak ucu çevresi × saçak yüzü yüksekliği (topuk + panelin düşey ölçüsü) × {zb_carpan} ÷ 2,88", durum="muhendis",
             not_="saçak yüzü Boardex'le kaplanır: mühendis, 3 Ekim; kaplandığı: Lokman, 2 Ekim 22:05. Alan geometriden")
    # Yöntem A'da beşik çatının kalkan kenarı (alın): alın sacı yok. Kalkan kenarı Boardex kaplanır (kurallar: `yontem_a_alin_kaplamasi`; Lokman,
    # 8 Ekim 2026 00:45; 0.13'te geçiciydi, soru). 0.14'te saçak gibi (alt + yüz); 0.15'ten beri yalnız makasın eğimli kenarının yüzü (8 Ekim 07:23:
    # "Alın kapama saçak değil sadece makasın eğimli kenarı kadar kapanıyor"). Kırma çatıda alın yoktur.
    if yontem == "panel" and kural_degeri("yontem_a_alin_kaplamasi") and c.get("alin_saci_m") and c.get("sacak_alti") == "boardex":
        sacak_eni = c.get("sacak_alti_eni_m", deg(k, "sacak_alti_boardex_eni_m"))
        yuz_h = c["sacak_yuzu_m2"] / sacak_altli if c.get("sacak_yuzu_m2") and sacak_altli else 0.0
        yalniz_yuz = deg(k, "yontem_a_alin_kaplamasi").get("olcu") == "yalniz_yuz"      # Lokman, 8 Ekim 2026 07:23: kalkan kenarı saçak değil
        alin_alan = c["alin_saci_m"] * ((0.0 if yalniz_yuz else sacak_eni) + yuz_h)
        if alin_alan > 0 or not yalniz_yuz:
            ekle("Metal aksam", "Alın (kalkan kenarı) için Boardex", boardex_boyut, tavan(alin_alan * (1 + zb) / deg(k, "levha_m2", "boardex")), alin_alan,
                 formul=(f"makasın eğimli kenarı (kalkan kenarlarının boyu) {tr(c['alin_saci_m'])} m × saçak yüzü yüksekliği {tr(yuz_h)} m × {zb_carpan} ÷ 2,88"
                         if yalniz_yuz else
                         f"alın kenarlarının boyu {tr(c['alin_saci_m'])} m × (saçak eni {tr(sacak_eni)} + saçak yüzü yüksekliği {tr(yuz_h)} m) × {zb_carpan} ÷ 2,88"),
                 durum=k["yontem_a_alin_kaplamasi"]["durum"], not_=k["yontem_a_alin_kaplamasi"]["satir_notu"])
    # Lokman, 8 Ekim 2026 00:45: kalkan kenarında "çatı kaplamasının üstüne bir malzeme gelmesi lazım" (0.14: adı bilinmediği için adetsiz satır).
    # 07:23: malzeme alın kapama, boyu makasın eğimli kenarı kadar (0.15: parça boyu kuralda). Saçak altının malzemesine bağlı değildir.
    uk = kural_degeri("yontem_a_kalkan_ust_kapamasi")
    if yontem == "panel" and uk and c.get("alin_saci_m"):
        kenar = "kalkan kenarlarının boyu" + (f" ({pc_ad} alınları hariç)" if c.get("ek_cati") else "")
        if uk.get("parca_boyu_m"):      # Lokman, 8 Ekim 2026 07:23: alın kapama, makasın eğimli kenarı kadar; parça boyu kuralda (varsayım)
            ekle("Metal aksam", uk["ad"], f"L {round(uk['parca_boyu_m'] * 1000)}", tavan(c["alin_saci_m"] / (uk["parca_boyu_m"] - uk["bindirme_m"])), c["alin_saci_m"], birim="m",
                 formul=f"makasın eğimli kenarı boyunca: {kenar} {tr(c['alin_saci_m'])} m ÷ ({tr(uk['parca_boyu_m'], 1)} − {tr(uk['bindirme_m'])} bindirme)",
                 durum=k["yontem_a_kalkan_ust_kapamasi"]["durum"], not_=k["yontem_a_kalkan_ust_kapamasi"]["satir_notu"])
        else:
            bilgi_adet = tavan(c["alin_saci_m"] / (uk["bilgi_parca_boyu_m"] - uk["bilgi_bindirme_m"]))
            ekle("Metal aksam", uk["ad"], "", None, c["alin_saci_m"], birim="m", formul=kenar + "; malzeme ve parça boyu bilinmiyor",
                 durum=k["yontem_a_kalkan_ust_kapamasi"]["durum"],
                 not_=k["yontem_a_kalkan_ust_kapamasi"]["satir_notu"]
                      + f". Bilgi: alın sacının ölçüsüyle (L {round(uk['bilgi_parca_boyu_m'] * 1000)}, {tr(uk['bilgi_bindirme_m'] * 100, 0)} cm bindirme) {bilgi_adet} adet ederdi")
    # Tek eğimli çatı panelli çatıların (veranda, sundurma, müştemilat) kenarları (Lokman, 10 Ekim 2026: "o 5 görseldeki gibi"; kural `panel_cati_kenarlari`):
    # saçakta derenin altında özel büküm saçak sacı, yanlarda (eğik kenarlar) sundurma kapama. İki yöntemde de.
    pkk = kural_degeri("panel_cati_kenarlari")
    if pkk and c.get("panel_kenari"):
        for anahtar, boy_anahtari, kenar_adi in (("sacak", "sacak_m", "saçakları"), ("yan", "yan_m", "eğik kenarları (yanları)")):
            pr, boy_k = pkk[anahtar], c["panel_kenari"][boy_anahtari]
            if boy_k > 0:
                ekle("Metal aksam", pr["ad"], f"L {round(pr['parca_boyu_m'] * 1000)}", tavan(boy_k / (pr["parca_boyu_m"] - pr["bindirme_m"])), boy_k, birim="m",
                     formul=f"{pc_ad} {kenar_adi} {tr(boy_k)} m ÷ ({tr(pr['parca_boyu_m'], 1)} − {tr(pr['bindirme_m'])} bindirme)",
                     durum=k["panel_cati_kenarlari"]["durum"], not_=k["panel_cati_kenarlari"].get(f"satir_notu_{anahtar}"))
    # köşebent (Ubeydullah, 3 Ekim 2026): (bütün odaların tavan çevresi + iç köşeler × 2,7 m) ÷ 2,5
    kr = deg(k, "kosebent")
    cevre_top = sum(o["cevre_m"] for o in g["odalar"])
    if all("ic_kose" in o for o in g["odalar"]):
        kose = sum(o["ic_kose"] for o in g["odalar"])
        dis_kose = sum(o.get("dis_kose", 0) for o in g["odalar"])
        kose_notu = f"odaya doğru çıkıntı yapan {dis_kose} köşe sayılmaz (mühendis, 4 Ekim 12:14)" if dis_kose else None
    else:
        kose = len(g["odalar"]) * kr["plan_yoksa_oda_basina_ic_kose"]
        kose_notu = f"planı yok: oda başına {kr['plan_yoksa_oda_basina_ic_kose']} iç köşe sayıldı (alt sınır)"
    # veranda tavanının çevresi de sayılır (mühendis, 4 Ekim 2026 12:14); çevre bilinmiyorsa eklenmez
    veranda_cevre = (g.get("veranda_tavan_cevresi_m") or 0.0) if kr.get("veranda_tavani") else 0.0
    if veranda_cevre:
        kose_notu = (kose_notu + "; " if kose_notu else "") + "veranda tavanının çevresi sayıldı (mühendis, 4 Ekim 12:14)"
    kb_boy = cevre_top + veranda_cevre + kose * kr["kose_boyu_m"]
    kb_yedek = sb.get("kosebent_yedek_adet", 0)            # Eylül 2026 şablonunda + 3
    if kb_yedek:
        kose_notu = (kose_notu + "; " if kose_notu else "") + f"Eylül 2026 şablonu: + {kb_yedek} yedek (mühendisin 3 Ekim tarifinde yok)"
    ekle("Metal aksam", "Köşebent", "L 2500", tavan(kb_boy / kr["parca_boyu_m"] + kb_yedek), kb_boy, birim="m",
         formul=(f"(oda tavan çevreleri {tr(cevre_top)} m" + (f" + veranda tavanı çevresi {tr(veranda_cevre)} m" if veranda_cevre else "")
                 + f" + {kose} iç köşe × {tr(kr['kose_boyu_m'], 1)} m) ÷ {tr(kr['parca_boyu_m'], 1)}" + (f" + {kb_yedek}" if kb_yedek else "")),
         durum=SABLON if kb_yedek else "muhendis", not_=kose_notu)

    # ── Kapı ve pencere (modelden doğrudan) ─────────────────────────────────
    for x in g.get("kapi_pencere", []):
        ekle("Kapı ve pencere", x["kalem"], x["boyut"], x["adet"], birim="", formul=x.get("formul", "modeldeki açıklıklardan"), durum=x.get("durum", "model"))
    pencere = sum(x["adet"] for x in d["bosluklar"] if "kapı" not in x["ad"])

    # ── Elektrik ────────────────────────────────────────────────────────────
    # Sayılar: pafta sayımı varsa o (kesin); yoksa oda başına kural (Ubeydullah, 3 Ekim 2026; doğruluk payı yaklaşık %75).
    ek = deg(k, "elektrik")
    es_pafta = g.get("elektrik_sayim")
    es_kural, es_dokum = elektrik_kurali(g.get("elektrik_odalar"), k)
    if es_pafta is not None:
        eksik = [x for x in ELEKTRIK_KALEMLERI if not isinstance(es_pafta.get(x), int) or es_pafta[x] < 0]
        fazla = sorted(set(es_pafta) - set(ELEKTRIK_KALEMLERI) - {"sigorta"})
        if eksik or fazla:
            raise SystemExit("Elektrik sayımı eksik ya da hatalı: " + ", ".join([f"{x} yok ya da sayı değil" for x in eksik] + [f"{x} bilinmiyor" for x in fazla]))
        es_pafta = {**es_pafta, "sigorta": es_pafta.get("sigorta", deg(k, "elektrik_oda")["sigorta"])}
    es = es_pafta if es_pafta is not None else es_kural
    kat_adedi = g.get("kat_adedi", 1)
    priz = 0
    if es:
        priz = es["tekli_priz"] + es["cift_priz"] + es["uydu_prizi"]
        anahtar = es["tekli_anahtar"] + es["cift_anahtar"]
        olcu_k = g.get("kapali_olcu_m") or g.get("dis_olcu_m")
        kosegen = math.hypot(*olcu_k) if olcu_k else None
        uzak_adi, kablo_durum, kablo_notu = "kapalı kısmın köşegeni", "motor", None
        kablo_kurali = kural_degeri("kablo_en_uzak_mesafe") == "sigortadan"     # Lokman, 7 Ekim 2026 07:45: sigorta × sigortadan en uzak mesafe
        if (sb.get("kablo_en_uzak_mesafe") == "sigortadan" or kablo_kurali) and g.get("elektrik_en_uzak_m"):   # şablonda: "sigortadan eve en uzun uzaklık"
            kosegen, uzak_adi = g["elektrik_en_uzak_m"], "sigorta kutusundan (girişte) kapalı kısmın en uzak köşesine"
            kablo_durum, kablo_notu = (k["kablo_en_uzak_mesafe"]["durum"], k["kablo_en_uzak_mesafe"].get("satir_notu")) if kablo_kurali else (SABLON, None)
        elif kablo_kurali:
            kablo_notu = "sigorta kutusunun yeri girdide yok: en uzak mesafe yerine kapalı kısmın köşegeni alındı (Excel motorundaki gibi)"
        kural_notu = "oda başına kural; doğruluk payı yaklaşık %75 (mühendis, 3 Ekim). Kesin sayı elektrik paftasından gelir"
        cok_islevli = [f"{o['ad']} ({' + '.join(ISLEV_ADI[i] for i in o['islev'])})" for o in (g.get("elektrik_odalar") or []) if len(o["islev"]) > 1]
        if cok_islevli and not es_pafta:
            kural_notu += ". Salon ile mutfak aynı mahaldeyse iki kural birlikte uygulanır (mühendis, 4 Ekim): " + ", ".join(cok_islevli)
        for ad, kalem in (("Tijli duy", "tijli_duy"), ("Yuvarlak glop", "glop"), ("Ampul", None), ("Tekli anahtar", "tekli_anahtar"), ("Çiftli anahtar", "cift_anahtar"),
                          ("Tekli priz", "tekli_priz"), ("Çiftli priz", "cift_priz"), ("Uydu prizi", "uydu_prizi"), ("W otomat (sigorta)", "sigorta")):
            if kalem is None:
                ekle("Elektrik", ad, "adet", es["tijli_duy"] + es["glop"], birim="", formul="duy + glop", durum="motor")
            elif es_pafta is not None and (kalem != "sigorta" or "sigorta" in g["elektrik_sayim"]):
                ekle("Elektrik", ad, "adet", es[kalem], birim="", formul="pafta sayımı", durum="liste")
            else:
                ekle("Elektrik", ad, "adet", es[kalem], birim="", formul=f"bina başına {es[kalem]}" if kalem == "sigorta" else (es_dokum[kalem] or "bu odalarda yok"),
                     durum="muhendis", not_=kural_notu if kalem == "tijli_duy" else None)
        if kosegen:
            ekle("Elektrik", "NYM kablo (3 × 2,5)", "metre", tavan(es["sigorta"] * kosegen + (es["tekli_priz"] + 2 * es["cift_priz"] + es["uydu_prizi"]) * 2), birim="",
                 formul=f"sigorta adedi × sigortadan en uzak mesafe ({uzak_adi}, {tr(kosegen)} m) + (tekli priz + çiftli priz × 2 + uydu prizi) × 2 m", durum=kablo_durum,
                 not_=kablo_notu)
            ekle("Elektrik", "NYM kablo (2 × 1,5)", "metre", tavan(es["sigorta"] * kosegen + (es["tekli_anahtar"] + 2 * es["cift_anahtar"]) * 2), birim="",
                 formul=f"sigorta adedi × sigortadan en uzak mesafe ({uzak_adi}, {tr(kosegen)} m) + (tekli anahtar + çiftli anahtar × 2) × 2 m", durum=kablo_durum,
                 not_=kablo_notu)
        ekle("Elektrik", "Buat kasa", "adet", anahtar + priz + g.get("oda_sayisi", len(g["odalar"])), birim="", formul="anahtar + priz + oda sayısı (veranda hariç)", durum="motor")
    else:
        ekle("Elektrik", "Duy, glop, ampul, anahtar, priz, sigorta, buat ve NYM kablolar", "adet / metre", None, birim="",
             formul="elektrik paftası yok ve odaların işlevi bilinmiyor; pafta sayımı ya da oda başına kural gerekli", durum="bekliyor")
    uydu = es["uydu_prizi"] if es else 1
    ekle("Elektrik", "Uydu kablo", "metre", ek["uydu_kablo_priz_basina_m"] * uydu, birim="", formul=f"uydu prizi ({uydu}) × {ek['uydu_kablo_priz_basina_m']} m", durum="motor")
    ekle("Elektrik", "Besleme kablosu (sigorta kutuları arası)", "metre", ek["besleme_kablosu_kat_basina_m"] * kat_adedi, birim="", formul="kat adedi × 5 m", durum="motor")
    ekle("Elektrik", "Besleme kablo borusu", "metre", ek["besleme_kablosu_kat_basina_m"] * kat_adedi, birim="", formul="kat adedi × 5 m", durum="motor")
    ekle("Elektrik", "Zil", "adet", ek["zil"], birim="", formul="1", durum="motor")
    ekle("Elektrik", "Sigorta kutusu (12'li)", "adet", ek["sigorta_kutusu_kat_basina"] * kat_adedi, birim="", formul="kat adedi", durum="motor")
    ekle("Elektrik", "İzole bant", "adet", tavan(m2 * ek["izole_bant_m2_basina"]), m2, formul="bina m² × 0,06", durum="motor")
    ekle("Elektrik", "Kaçak akım rölesi", "adet", ek["kacak_akim_rolesi"], birim="", formul="tek katta 1 (ikili)", durum="motor")

    # ── Vida ────────────────────────────────────────────────────────────────
    v = deg(k, "vida")
    yv = v["trapez_yuvarlama"]
    ekle("Vida", "RYSB pul başlı (3,9 × 32)", "adet", tavan(m2 * v["rysb_m2_basina"]), m2, formul="bina m² × 7,5", durum="motor",
         not_="gerçek listelerde daha az (62 m²'de 400, 105 m²'de 500)")
    alcipan_levha = sum(s["adet"] or 0 for s in S if s["kalem"].startswith(("Duvar alçıpan", "Tavan alçıpan", "Dış cephe Boardex"))
                        or s["kalem"] in ("Saçaklar için Boardex", "Saçak yüzü için Boardex", "Veranda tavanı (Boardex)", "Alın (kalkan kenarı) için Boardex"))
    va = sbv.get("alcipan_vidasi_levha_basina", v["alcipan_vidasi_levha_basina"])      # Eylül 2026 şablonunda 50; 2025 çalışma kitabının notunda 40
    ekle("Vida", "Alçıpan vidası (3,5 × 35)", "adet", kat(alcipan_levha * va, 250), alcipan_levha, birim="levha",
         formul=f"alçıpan ve Boardex levha sayısı × {va}; 250'ye yuvarlandı", **({"durum": SABLON} if "alcipan_vidasi_levha_basina" in sbv else {}))
    osb_levha = sum(s["adet"] or 0 for s in S if "OSB" in s["kalem"] and "mahya" not in s["kalem"].lower() and s["grup"] != "Vida")
    ov = v["osb_vidasi"]
    ov_levha = sbv.get("osb_levha", ov["osb_levha"])
    osb_say = (osb_levha * ov_levha + priz * ov["priz"] + adet_of("Saçak sacı (30'luk)") * ov["sacak_saci"] + adet_of("Dere kelepçesi") * ov["dere_kelepcesi"])
    ekle("Vida", "OSB ve yalıpan vidası (3,9 × 32)", "adet", kat(osb_say, ov["yuvarlama"]), osb_say, birim="vida",
         formul=f"OSB levha × {ov_levha} + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; 500'e yuvarlandı", durum=SABLON if "osb_levha" in sbv else "motor",
         not_=None if es else "priz sayısı bilinmediği için priz payı yok")
    pencere_dahil = g.get("pencere_dahil", True)           # pencereler alıcıya aitse pencere sayısına bağlı kalemler listeye girmez (kurallar: `kapsam_alici`)
    ka = deg(k, "kapsam_alici")["pencere_aliciya_aitse"]
    if pencere_dahil or ka["pencere_vidasi"]:
        ekle("Vida", "Pencere vidası (4,8 × 70)", "adet", pencere * v["pencere_vidasi_pencere_basina"], pencere, birim="pencere", formul="pencere sayısı × 20")
    panel_adedi = g.get("celik_panel_adedi", celik_toplam_adet)
    if panel_adedi:
        t = {**v["trapez_5_5x25"], **{x: sbv[x] for x in ("omega_375", "omega_240") if x in sbv}}      # Eylül 2026 şablonu: omega × 6; saçak omegası formülde yok
        # Parça C profiller: şablonda (Eylül 2026) çelik panel sayısına dahildir; 0.4 hattında toplam (`celik_toplam_adet`) onları zaten içerir. Genel modelde
        # `celik_panel_adedi` C profilsizdir. Kural (`vida.trapez_5_5x25_c_profil_dahil`; 7 Ekim 2026) iki hattı da yönetir: sayılacaksa genel modelde eklenir,
        # sayılmayacaksa 0.4 hattında toplamdan düşülür. Anahtar kuralda yoksa eski davranış: 0.4 hattı sayar, genel model saymaz (şablon isterse sayar).
        c_profil = sum(s["adet"] or 0 for s in S if s["kalem"] == "Boy C profil")
        c_kural = v.get("trapez_5_5x25_c_profil_dahil")
        genel_model = "celik_panel_adedi" in g
        c_dahil = bool(sbv.get("celik_panel_c_profil_dahil") or (c_kural if c_kural is not None else not genel_model))
        panel_vida = panel_adedi + (c_profil if c_dahil and genel_model else 0) - (c_profil if not c_dahil and not genel_model else 0)
        panel_ustu = 0     # yöntem A'da modelden sayılan panellere tavan ve çatı panelleri eklenir (0.4 hattında toplam zaten onları içerir)
        if celik_yontemi and yontem == "panel" and "celik_panel_adedi" in g:
            panel_ustu = sum(s["adet"] or 0 for s in S if s["kalem"] in ("Tavan paneli (makas arası)", "Çatı paneli (makas üstü, sırt 80 mm)"))
            panel_vida += panel_ustu
        say = (adet_of("Aşık") * t["asik"] + adet_of("Tavan omegası (60'lık)") * t["omega_375"]
               + (adet_of(c.get("sacak_omegasi", "Saçak omegası")) if yontem == "omega_asik" else 0) * t["omega_240"]
               + panel_vida * t["celik_panel"] + (g.get("kosebent_adedi") or adet_of("Köşebent")) * t["kosebent"])
        c_sayildi = bool(c_profil) and c_dahil and (genel_model or c_kural is not None)      # anahtar yokken 0.4 hattının metni eskisi gibi kalır
        c_dusuldu = bool(c_profil) and not c_dahil and not genel_model
        panel_adi = ("çelik panel ve parça C profil" if c_sayildi else "çelik panel") + (
            f" (tavan ve çatı panelleri dahil: {panel_vida})" if panel_ustu else f" ({panel_vida})" if c_sayildi
            else f" (parça C profiller hariç: {panel_vida})" if c_dusuldu else "")
        ekle("Vida", "Trapez vida (5,5 × 25)", "adet", kat(say, yv), say, birim="vida",
             # kuralda çarpanı sıfır olan terim (7 Ekim 2026: aşık ve omega için vida konmaz) formülde yazılmaz
             formul=" + ".join(f"{ad} × {carpan}" for ad, carpan in (("aşık", t["asik"]), ("tavan omegası", t["omega_375"]), ("saçak omegası", t["omega_240"]),
                                                                    (panel_adi, t["celik_panel"]), ("köşebent", t["kosebent"]))
                               if carpan or all(v["trapez_5_5x25"].values())) + "; 250'ye yuvarlandı",
             **({"durum": SABLON} if sbv else {}),
             not_=((("tavan ve çatı panellerinin vidası hariç; " if panel_eksik else "") + "çelik panel adedi tahmin")
                   if yontem == "panel" and "celik_panel_adedi" not in g else None))
    say60 = m2 * v["trapez_5_5x60_m2_basina"]
    sac_adedi = (adet_of("Metal kiremit (kiremit desen sac)") + adet_of("Trapez sac")) if c.get("panel_boyu_m") else 0
    if sac_adedi:   # motor: + metal kiremit boyu ÷ 200 × adet + trapez sac boyu ÷ 200 × adet
        say60 += (dz.get("panel_boyu_m") or c["panel_boyu_m"]) * 1000 / v["trapez_panel_boyu_bolu_mm"] * sac_adedi
    ekle("Vida", "Trapez vida (5,5 × 60)", "adet", kat(say60, yv), say60, birim="vida",
         formul="bina m² × 2,5" + (" + sac boyu ÷ 200 × sac adedi" if sac_adedi else "") + "; 250'ye yuvarlandı", durum="motor")
    for anahtar, ad, vida_adi in (("tek_kat_panel", "Tek kat panel", "Trapez vida (5,5 × 76; tek kat panel)"), ("sandvic_panel", "Sandviç panel", "Trapez vida (5,5 × 110; sandviç panel)")):
        if kaplama == anahtar and adet_of(ad):
            if c.get("dizilim"):
                say = sum(sat["boy_m"] * 1000 / v["trapez_panel_boyu_bolu_mm"] * sat["adet"] for sat in c["dizilim"]["satirlar"])
            else:
                say = (dz.get("panel_boyu_m") or c["panel_boyu_m"]) * 1000 / v["trapez_panel_boyu_bolu_mm"] * adet_of(ad)
            ekle("Vida", vida_adi, "adet", kat(say, yv), say, birim="vida", formul="panel boyu (mm) ÷ 200 × panel adedi; 250'ye yuvarlandı", durum="motor",
                 not_="62 m² gerçek listede 750 var; bu formül o listede 500 veriyor" if anahtar == "sandvic_panel" else None)
    duvar_paneli = g.get("duvar_paneli_adedi")
    if duvar_paneli is None and ce:
        duvar_paneli = sum((ce.get(x) or {}).get("panel_adedi") or 0 for x in ("dis", "ic")) or None
    if duvar_paneli:
        for ad in ("Çelik dübel (klipsli)", "Şase pul"):
            ekle("Vida", ad, "adet", duvar_paneli * v["celik_dubel_duvar_paneli_basina"], duvar_paneli, birim="panel",
                 formul="duvar paneli adedi × 2" if ad.startswith("Çelik") else "çelik dübel adedi kadar", durum="motor",
                 not_=None if "duvar_paneli_adedi" in g else "duvar paneli adedi tahmin")
    for ad in ("8'lik trapez uç", "PH2 uç"):
        ekle("Vida", ad, "adet", tavan(m2 / v["uc_m2_bolu"]), m2, formul="bina m² ÷ 15", durum="motor")
    if sb.get("kesme_tasi_m2_basina"):   # Eylül 2026 şablonu ve Excel motoru: m² × 0,02
        ekle("Vida", "230'luk kesme taşı", "adet", tavan(m2 * sb["kesme_tasi_m2_basina"]), m2, formul=f"bina m² × {tr(sb['kesme_tasi_m2_basina'])}", durum=SABLON,
             not_="Eylül 2026 şablonu ve Excel motoru. Bugünkü kuralda m² ÷ 15 (iki 2025 listesinden: 5 ve 7)")
    else:
        ekle("Vida", "230'luk kesme taşı", "adet", tavan(m2 / v["kesme_tasi_m2_bolu"]), m2, formul="bina m² ÷ 15", durum="uydurma",
             not_="motorda m² × 0,02; iki gerçek listede m² ÷ 15'e denk (5 ve 7)")
    ekle("Vida", "İnox taş", "adet", tavan(m2 / v["inox_tasi_m2_bolu"]), m2, formul="bina m² ÷ 10")
    ekle("Vida", "Çırpı ipi", "adet", v["cirpi_ipi"], birim="", formul="1", durum="motor")

    # ── Sıhhi tesisat ───────────────────────────────────────────────────────
    ts = deg(k, "tesisat")
    islak = g.get("islak_hacim_sayisi", sum(1 for o in g["odalar"] if o["tur"] == "yesil"))
    for ad, anahtar, boyut in (("Temiz su borusu", "temiz_su_borusu_4m", "L 4000"), ("Normal dirsek 20 mm", "normal_dirsek_20", "adet"),
                               ("Kulaklı dirsek 20 mm", "kulakli_dirsek_20", "adet"), ("Düz T 20 mm", "duz_t_20", "adet"), ("Maşon 20 mm", "mason_20", "adet"),
                               ("İç dişli T 20 mm", "ic_disli_t_20", "adet"), ("Atlama parçası (yarım parmak)", "atlama_parcasi", "adet")):
        ekle("Sıhhi tesisat", ad, boyut, islak * ts[anahtar], islak, birim="ıslak hacim", formul=f"ıslak hacim sayısı × {ts[anahtar]}", durum="motor")
    if g.get("vitrifiye_dahil", True):
        for ad, anahtar in (("Duşakabin (90 × 90)", "dusakabin_90x90"), ("Klozet", "klozet"), ("Banyo dolabı", "banyo_dolabi"), ("Banyo batarya grubu", "batarya_grubu")):
            ekle("Sıhhi tesisat", ad, "takım", islak * ts["vitrifiye"][anahtar], islak, birim="ıslak hacim", formul="ıslak hacim sayısı × 1; 'vitrifiye dahil' ise", durum="motor")
        th = kural_degeri("taharet_muslugu")
        if th:      # Lokman, 10 Ekim 2026: "vitrifiye malzemesi varsa wc + banyo başı 4 adet"
            ekle("Sıhhi tesisat", "Taharet musluğu 20 mm", "adet", islak * th["islak_hacim_basina"], islak, birim="ıslak hacim",
                 formul=f"ıslak hacim (WC, banyo) sayısı × {th['islak_hacim_basina']}; 'vitrifiye dahil' ise", durum=k["taharet_muslugu"]["durum"],
                 not_=k["taharet_muslugu"].get("satir_notu"))

    # ── Boya ────────────────────────────────────────────────────────────────
    by = deg(k, "boya")
    kb = g.get("kapsam_boya")                              # boya kalemleri ayrı ayrı (genel model): alıcıya ait olanlar yazılmaz
    for ad, anahtar, kapsam_anahtari in (("Dış cephe boyası", "dis_cephe_kova_m2_basina", "dis_cephe_boyasi"), ("İç cephe boyası", "ic_cephe_kova_m2_basina", "ic_cephe_boyasi"),
                                         ("Tavan boyası", "tavan_kova_m2_basina", "tavan_boyasi"), ("Astar", "astar_kova_m2_basina", "astar")):
        if g.get("boya_dahil", True) and (kb.get(kapsam_anahtari, True) if kb else True):
            ekle("Boya", ad, "kova 17,5 kg", tavan(m2 * by[anahtar]), m2,
                 formul=f"bina m² × {tr(by[anahtar] * 100, 0)}/100; " + ("teknik özelliklerde alıcıya ait yazmıyorsa" if kb else "'boya dahil' ise"), durum="motor")
    if pencere_dahil or ka["silikonize_mastik"]:
        ekle("Boya", "Silikonize mastik", "adet", pencere * by["mastik_pencere_basina"], pencere, birim="pencere", formul="pencere adedi", durum="uydurma",
             not_="motorda mantolamasız cephede + m² × 2/3 var ('ayrıca eklenir'); üç gerçek listede de 8")
    dy = (sb.get("dayson_m2_basina") or {}).get(c["tip"], by["dayson_m2_basina"])      # Eylül 2026 şablonunun notu: beşik çatıda 0,03, kırmada 0,06
    ekle("Boya", "Dayson", "adet", tavan(m2 * dy), m2, formul=f"bina m² × {tr(dy)}", durum=SABLON if dy != by["dayson_m2_basina"] else "motor")
    ekle("Boya", "Poliüretan köpük", "adet", by["kopuk"], birim="", formul="standart 2", durum="motor")

    # Boardex kalınlığı şablondan geliyorsa (8 mm; bugünkü kuralda 12,5 mm) o boyutla yazılan her satır şablon satırıdır: adet aynı, sipariş edilen levha başka
    if sb.get("boardex_kalinligi_mm", kal["boardex"]) != kal["boardex"]:
        bx_notu = (f"Eylül 2026 şablonu: Boardex {tr(sb['boardex_kalinligi_mm'], 1).replace(',0', '')} mm; bugünkü kuralda {tr(kal['boardex'], 1)} mm "
                   "(mühendis, 4 Ekim 12:14). Adet formülü aynı")
        for s in S:
            if s["boyut"] == boardex_boyut:
                s["durum"] = SABLON
                s["not"] = (s["not"] + ". " if s["not"] else "") + bx_notu

    # Kararla durumu ya da notu değişen kalemler (kurallar: `satir_notlari`; ör. Lokman'ın 7 Ekim 2026 cevapları). Adet ve formül burada değişmez.
    for s in S:
        o = (kural_degeri("satir_notlari") or {}).get(s["kalem"])
        if o and s["durum"] != SABLON:
            s["durum"] = o.get("durum", s["durum"])
            if "not" in o:
                s["not"] = o["not"]
            if "not_eki" in o:
                s["not"] = (s["not"] + ". " if s["not"] else "") + o["not_eki"]

    # Çatının duvara dayandığı kenarlar özel mahya satırına yazıldıysa (kurallar: `duvar_dibi.satir_notu`) nedeni satırın notuna eklenir.
    if dd_ozel_notu:
        for s in S:
            if s["kalem"] == "Özel mahya (geniş)":
                s["not"] = (s["not"] + ". " if s["not"] else "") + dd_ozel_notu

    # Listede yazılan ad (kurallar: `urun_adlari`; Lokman, 8 Ekim 2026 00:45: "üreticide ne yazıyorsa onu yaz"). Hesabın iç anahtarı (`kalem`) değişmez:
    # gerçek listelerle karşılaştırma ve öteki betikler o adı kullanır. Yazılan ad farklıysa satıra `liste_adi` olarak eklenir.
    ua = kural_degeri("urun_adlari")
    if ua:
        for s in S:
            for eski_ad, yeni_ad in ua["degistir"]:
                if eski_ad in s["kalem"]:
                    s["liste_adi"] = s["kalem"].replace(eski_ad, yeni_ad)
                    break

    # Renk (genel model: projenin teknik özelliklerinden). Gerçek listede renk kalemin adında yazar; hangi kalemlerde yazdığı `renkli_kalemler` kuralında.
    if g.get("renk"):
        bilinmeyen = sorted(set(g["renk"]) - set(deg(k, "renkli_kalemler"))) if isinstance(g["renk"], dict) else ["(sözlük değil)"]
        if bilinmeyen:
            raise SystemExit(f"Girdideki `renk` alanında bilinmeyen anahtar: {', '.join(bilinmeyen)} (beklenen: {', '.join(deg(k, 'renkli_kalemler'))}).")
        basta = kural_degeri("renk_adin_basinda")         # 0.20 (Lokman, 27 Ekim 2026, C3): 2026 listelerindeki gibi renk adın başında
        for anahtar, kalemler in deg(k, "renkli_kalemler").items():
            if g["renk"].get(anahtar):
                for s in S:
                    if s["kalem"] in kalemler:
                        s["renk"] = g["renk"][anahtar]
                        if basta:                     # Türkçe büyük-küçük harf (i/İ, ı/I); kısaltma (OUTWEAR) küçülmez
                            ad, r = s.get("liste_adi") or s["kalem"], s["renk"]
                            ad = (ad[:1].replace("İ", "i").replace("I", "ı").lower() + ad[1:]) if ad[1:2].islower() else ad
                            s["liste_adi"], s["renk_adda"] = r[:1].replace("i", "İ").replace("ı", "I").upper() + r[1:] + " " + ad, True

    # ── bayi kuralı: gruplar ────────────────────────────────────────────────
    gruplar = {**deg(k, "bayi_kurali")["varsayilan_gruplar"], **(g.get("bayi") or {}).get("gruplar", {})}
    kapali = [ad for ad, acik in gruplar.items() if not acik]
    S[:] = [s for s in S if s["grup"] not in kapali]
    S.sort(key=lambda s: GRUP_SIRASI.index(s["grup"]))
    kaplama_adi = KAPLAMA_ADI.get(kaplama, kaplama) + (" (baz paket)" if kaplama == deg(k, "baz_paket_cati_kaplamasi") else "")
    return {"yontem": yontem, "yontem_adi": YONTEM_ADI[yontem], "cati_kaplamasi": kaplama_adi, "cati_kaplamasi_anahtar": kaplama, "kapali_gruplar": kapali,
            **({"yontem_notu": k["celik_cati_yontemi"]["yontem_b_notu"]} if celik_yontemi and yontem != celik_yontemi else {}),
            **({"sablon": g["sablon"]} if sb else {}),
            "satirlar": S,
            "ara": {"dis_net_m2": round(dis_net, 3), "beyaz_net_m2": round(ozet["beyaz"][0], 3), "yesil_net_m2": round(ozet["yesil"][0], 3),
                    "ic_duvar_boyu_m": round(ic_boy, 2), "oda_cevreleri_m": round(ic_yuz, 2),
                    "yalitim_brut_m2": round(yal_brut, 2), "yalitim_net_m2": round(yal_net, 2), "asik_boyu_m": round(boy, 1),
                    "inis_kural": n_kural, "inis_kural_aciklama": n_not, "celik_panel_adedi": panel_adedi,
                    "kosebent": {"tavan_cevresi_m": round(cevre_top, 3), "veranda_tavan_cevresi_m": round(veranda_cevre, 3), "ic_kose": kose, "boy_m": round(kb_boy, 3)},
                    "elektrik_kaynagi": "pafta" if es_pafta else ("kural" if es_kural else None), "elektrik_kural": es_kural,
                    "kirma_dizilim": dz or None, "osb_takviye": ozet.get("osb_takviye")}}


def bayi_uygula(g: dict, anahtar: str, bk: dict) -> None:
    """Bayi kuralı (Lokman, 3 Ekim 13:27): listeye giren gruplar ve bayinin standardı. Girdiyi yerinde değiştirir."""
    b = bk["bayiler"][anahtar]
    # projenin kendi kapsamında kapalı olan grup (genel model: çizimde "alıcıya ait") bayinin standardıyla geri açılmaz
    proje_kapali = {ad: False for ad, acik in ((g.get("bayi") or {}).get("gruplar") or {}).items() if not acik}
    g["bayi"] = {"anahtar": anahtar, "gruplar": {**bk["varsayilan"]["gruplar"], **b.get("gruplar", {}), **proje_kapali}}
    for x in ("boya_dahil", "vitrifiye_dahil", "cati_mudahale_kapagi"):
        if x in b:
            g[x] = b[x]
    c = g["cati"]
    yeni_kaplama = b.get("cati", {}).get("kaplama")
    if "dizilim" in c and yeni_kaplama and yeni_kaplama != c.get("kaplama") and yeni_kaplama not in ("sandvic_panel", "tek_kat_panel"):
        raise SystemExit("Bu girdi genel modelden üretilmiş: genel model şimdilik yalnız sandviç panel ve tek kat panel kaplamasını hesaplar "
                         f"(bayi kuralındaki kaplama: {KAPLAMA_ADI.get(yeni_kaplama, yeni_kaplama)}).")
    yeni_yontem = b.get("cati", {}).get("yontem")
    if "dizilim" in c and yeni_yontem and yeni_yontem != c.get("yontem", "omega_asik"):
        raise SystemExit("Bu girdi genel modelden üretilmiş: bayi kuralındaki çatı yöntemi için girdi o yöntemle yeniden üretilmeli (tanımda `cati.yontem`); "
                         "aşık sıraları, alın kenarları ve tavan omegası dizilimi yönteme göre çıkarılır.")
    for x in ("yontem", "kaplama"):
        if x in b.get("cati", {}):
            c[x] = b["cati"][x]
    if c.get("yontem") == "omega_asik":   # iki yöntem birlikte kullanılmaz: saçak sacı varsa saçak altı ve saçak yüzü Boardex kaplanmaz
        c["sacak_alti"] = "sac"
        c.pop("sacak_yuzu_m2", None)
        c.setdefault("sacak_omegasi", "Geniş saçak omegası (180 × 2500)" if g["dis"]["karkas_mm"] >= 140 else "Saçak omegası")


def yaz(sonuc: dict, gercek: dict | None = None) -> str:
    cik, grup = [f"çatı yöntemi: {sonuc['yontem_adi']} · çatı kaplaması: {sonuc['cati_kaplamasi']}"], None
    for s in sonuc["satirlar"]:
        if s["grup"] != grup:
            grup = s["grup"]
            cik.append("\n" + grup.replace("i", "İ").upper())
        g = (gercek or {}).get(s["kalem"])
        olcu = "" if s["olcu"] is None else f"{s['olcu']:.2f} {s['birim']}".replace(".", ",")
        kg = "" if s["kg"] is None else f"{s['kg']:.0f} kg"
        satir = f"  {s.get('liste_adi') or s['kalem']:<52s} {s['boyut']:<26s} {'' if s['adet'] is None else s['adet']:>5}  {olcu:>18s} {kg:>9s}  [{s['durum']}]"
        if g:
            fark = "" if s["adet"] is None else ("AYNI" if s["adet"] == g["adet"] else f"fark {s['adet'] - g['adet']:+d}")
            satir += f"   listede {g['adet']}" + (f", {g['net']}" if "net" in g else "") + f" → {fark}"
        cik.append(satir)
    return "\n".join(cik)


def md_yaz(sonuc: dict, ad: str) -> str:
    satir = [f"# {ad}", "",
             f"Çatı yöntemi: {sonuc['yontem_adi']}." + (f" {sonuc['yontem_notu']}" if sonuc.get("yontem_notu") else "") + f" Çatı kaplaması (seçenek): {sonuc['cati_kaplamasi']}."
             + (f" Kapalı gruplar (bayi kuralı ya da proje kapsamı): {', '.join(sonuc['kapali_gruplar'])}." if sonuc["kapali_gruplar"] else "")
             + (" Kural seti: bugünkü kurallar + Eylül 2026 uygulaması (o listenin şablonundaki formüller ve paftalarındaki dizilim; deneme, karar bekliyor)."
                if sonuc.get("sablon") else ""), "",
             "| Grup | Kalem | Boyut | Adet | Ölçü | kg | Kural | Durum | Not |", "|---|---|---|---|---|---|---|---|---|"]
    for x in sonuc["satirlar"]:
        olcu = "" if x["olcu"] is None else f"{x['olcu']:.1f} {x['birim']}".replace(".", ",")
        kg = "" if x["kg"] is None else f"{x['kg']:.0f}"
        not_ = (x["not"] or "") + (((". " if x["not"] else "") + f"Bugünkü kurallarla: {x['bugunku_adet']}") if "bugunku_adet" in x else "")
        satir.append(f"| {x['grup']} | {x.get('liste_adi') or x['kalem']}{' (' + x['renk'] + ')' if x.get('renk') and not x.get('renk_adda') else ''} | {x['boyut']} | {'' if x['adet'] is None else x['adet']} | {olcu} | {kg} | {x['formul']} | {x['durum']} | {not_} |")
    return "\n".join(satir) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", type=Path)
    ap.add_argument("--karsilastir", type=Path)
    ap.add_argument("--cikti", type=Path)
    ap.add_argument("--md", type=Path, help="tabloyu Markdown olarak yaz")
    ap.add_argument("--kaplama", choices=list(KAPLAMA_ADI), help="çatı kaplaması seçeneğini girdidekinin yerine kullan")
    ap.add_argument("--mudahale-kapagi", action="store_true", help="çatı müdahale kapağını ekle (kural standart pakette saymıyorsa; 7 Ekim 2026'dan beri her yapıda 1 adet standart)")
    ap.add_argument("--bayi", help="bayi kuralı anahtarı (canlıda bayinin telefon numarası); kural kitabındaki kurallar/bayi/ornek.json içinden okunur")
    ap.add_argument("--bayi-kurallari", type=Path, default=BURADA.parents[1] / "kurallar" / "bayi" / "ornek.json")
    ap.add_argument("--sablon", choices=["2026"], help="Eylül 2026 şablonunun bugünkü kurallardan farklı formüllerini de uygula (deneme; kurallar: sablon_2026)")
    ap.add_argument("--elektrik-sayimi", type=Path, help="elektrik paftasından sayım (JSON: tijli_duy, glop, tekli_anahtar, cift_anahtar, tekli_priz, cift_priz, uydu_prizi, sigorta)")
    ap.add_argument("--inis-plan", type=int, help="dere paftasındaki (plana yerleştirilen) iniş sayısı")
    a = ap.parse_args()
    g = json.loads(a.girdi.read_text(encoding="utf-8"))
    if a.sablon:
        g["sablon"] = a.sablon
    if a.elektrik_sayimi:
        g["elektrik_sayim"] = json.loads(a.elektrik_sayimi.read_text(encoding="utf-8"))
    if a.inis_plan is not None and a.inis_plan < 0:
        raise SystemExit("--inis-plan negatif olamaz.")
    if a.inis_plan is not None:                            # paftadaki sayı verilmişse girdideki sayının (listeden) önüne geçer
        g["cati"].pop("inis_adedi", None)
        g["cati"]["inis_adedi_plan"] = a.inis_plan
    if a.kaplama:
        if "dizilim" in g["cati"] and a.kaplama not in ("sandvic_panel", "tek_kat_panel"):
            raise SystemExit("Bu girdi genel modelden üretilmiş: genel model şimdilik yalnız sandviç panel ve tek kat panel kaplamasını hesaplar.")
        g["cati"]["kaplama"] = a.kaplama
    if a.mudahale_kapagi:
        g["cati_mudahale_kapagi"] = True
    if a.bayi:
        bk = json.loads(a.bayi_kurallari.read_text(encoding="utf-8"))
        if a.bayi not in bk["bayiler"]:
            raise SystemExit(f"Bayi kuralı bulunamadı: {a.bayi}")
        bayi_uygula(g, a.bayi, bk)
    k = kural.oku()
    gercek_tum = json.loads(a.karsilastir.read_text(encoding="utf-8")) if a.karsilastir else None
    gercek = gercek_tum["kalemler"] if gercek_tum else None
    sonuc = hesapla(g, k)
    print(g["ad"])
    print(yaz(sonuc, gercek))
    print("\nara değerler:", sonuc["ara"])
    if gercek:
        # adedi doğrudan listeden alınan satırlar (durum: liste) karşılaştırmaya girmez
        es = [s for s in sonuc["satirlar"] if s["kalem"] in gercek and s["adet"] is not None and s["durum"] != "liste"]
        ayni = [s for s in es if s["adet"] == gercek[s["kalem"]]["adet"]]
        print(f"\nkarşılaştırılan {len(es)} kalemin {len(ayni)} tanesinde adet aynı; farklı olanlar: "
              + ", ".join(f"{s['kalem']} ({s['adet']} / {gercek[s['kalem']]['adet']})" for s in es if s not in ayni))
        eksik = [x for x in gercek if x not in {s["kalem"] for s in sonuc["satirlar"]}]
        if eksik:
            print("hesapta olmayan liste kalemleri:", ", ".join(eksik))
        sonuc["karsilastirma"] = {s["kalem"]: {"hesap": s["adet"], "liste": gercek[s["kalem"]]["adet"], "durum": s["durum"]} for s in es}
        sonuc["karsilastirma_ozeti"] = {"karsilastirilan": len(es), "ayni": len(ayni)}
        lk = gercek_tum.get("celik_kg")
        if lk:   # çelik: adet değil kg karşılaştırılır
            kg = {s["kalem"]: s["kg"] or 0 for s in sonuc["satirlar"] if s["grup"] == "Çelik panel"}
            hes = {"dis": kg.get("Dış cephe duvar panelleri", 0), "ic": kg.get("İç cephe duvar panelleri", 0),
                   "kiris_kolon": kg.get("Veranda dikmeleri (kolon paneli)", 0) + kg.get("Veranda kirişleri (kiriş paneli)", 0) + kg.get("Kirişler (kiriş paneli)", 0),
                   "cati": kg.get("Çatı makas panelleri", 0)}
            hes["duvar"] = hes["dis"] + hes["ic"]
            hes["toplam"] = kg.get("Toplam (adedi ve kg'ı bilinenler)", 0) if hes["cati"] else 0
            print("\nçelik (kg): hesap / liste / fark")
            ck_sonuc = {}
            for anahtar, ad in (("dis", "dış duvar"), ("ic", "iç duvar"), ("duvar", "duvar toplamı"), ("kiris_kolon", "kiriş ve kolon"), ("cati", "çatı"), ("toplam", "toplam")):
                if anahtar in lk and hes[anahtar]:
                    fark = (hes[anahtar] - lk[anahtar]) / lk[anahtar] * 100
                    print(f"  {ad:<16s} {hes[anahtar]:7.0f} / {lk[anahtar]:5d} / {fark:+5.1f} %")
                    ck_sonuc[anahtar] = {"hesap": round(hes[anahtar]), "liste": lk[anahtar], "fark_yuzde": round(fark, 1)}
            sonuc["celik_kg_karsilastirma"] = ck_sonuc
    if a.md:
        a.md.write_text(md_yaz(sonuc, g["ad"]), encoding="utf-8")
    if a.cikti:
        a.cikti.parent.mkdir(parents=True, exist_ok=True)
        a.cikti.write_text(json.dumps({"ad": g["ad"], **sonuc}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
