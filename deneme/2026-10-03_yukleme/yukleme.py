#!/usr/bin/env python3
"""Çelik yükleme listesi denemesi: metraj girdisinden kalemler.

Deneme kodudur; canlıda değildir. Hesapta LLM yoktur: aynı girdi her zaman aynı listeyi verir.

Kuralların kaynağı, öncelik sırasıyla:
  1. Lokman'ın söyledikleri (3 Ekim 2026 13:27 cevapları, 4 Ekim 01:24 ve 01:42 düzeltmeleri ve öncekiler),
  2. PortatifEv'in inşaat mühendisi Ubeydullah'ın cevapları (Lokman 3 Ekim 2026 18:14'te, 4 Ekim 01:24'te ve 12:14'te iletti),
  3. PortatifEv'in yükleme listesi çalışma kitaplarındaki formüller ve notlar,
  4. PortatifEv'in Excel hesaplama motoru (CTKBF V1.1): çelik birim ağırlıkları, vida, boya, tesisat formülleri,
  5. gerçek listelere uydurulan kurallar ve Claude'un varsayımları (teyit bekler).

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
  liste     örnek girdide gerçek listeden alınan sayı ve ona bağlı satırlar; karşılaştırmaya girmez

Terim: bu dosyada "alın" PortatifEv listelerindeki anlamıyla kullanılır: beşik çatının kalkan yüzü (alın sacı, çatı alnı).
Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü"dür.

Kullanım:
    python yukleme.py ornek_90m2_girdi.json --karsilastir ornek_90m2_gercek_liste.json
    python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
    python yukleme.py ornek_105m2_girdi.json --karsilastir ornek_105m2_gercek_liste.json
    python yukleme.py sonuc/C8201_girdi.json --cikti sonuc/C8201_yukleme_taslak.json --md sonuc/C8201_yukleme_taslak.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from cati_acilim import BASLANGIC_ADI, kapatma_genisligi, kural_dizilimi

BURADA = Path(__file__).resolve().parent
GRUP_SIRASI = ["Çelik panel", "Metal aksam", "Dış cephe kaplama", "İç cephe kaplama", "Çatı kaplamaları", "Dere", "Kapı ve pencere",
               "Elektrik", "Vida", "Sıhhi tesisat", "Boya"]
# Çatı kaplaması seçenekleri: Excel motorundaki altı seçenek (Ubeydullah, 3 Ekim 2026). İlk üçü gerçek listelerle karşılaştırıldı; son üçü yalnız motorun formülleriyle.
KAPLAMA_ADI = {"sandvic_panel": "sandviç panel", "tek_kat_panel": "tek kat panel", "osb_kiremit": "OSB + nem bariyeri + kiremit desen sac (metal kiremit)",
               "osb_trapez": "OSB + nem bariyeri + trapez sac", "trapez_sac": "trapez sac", "osb_shingle": "OSB + membran + shingle"}
OSBLI_KAPLAMA = ("osb_kiremit", "osb_trapez", "osb_shingle")
ISLEV_ADI = {"yatak_odasi": "yatak odası", "banyo": "banyo", "salon": "salon", "mutfak": "mutfak", "hol": "hol", "veranda": "veranda"}
ELEKTRIK_KALEMLERI = ("tijli_duy", "glop", "tekli_anahtar", "cift_anahtar", "tekli_priz", "cift_priz", "uydu_prizi")
YONTEM_ADI = {"panel": "A · çatı ve tavan paneli (çelik konstrüksiyon standardı)", "omega_asik": "B · tavan omegası, aşık, alın sacı, saçak sacı (prefabrik yöntemi)"}


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
    orta = sum(min(kr["cephe_basina_en_cok_orta"], 1) for x in c.get("cephe_kenarlari_m", []) if x >= kr["orta_inis_esigi_m"] - 1e-9)
    return kose * kr["kose_basina"] + orta, f"{kose} köşe + {orta} orta ({tr(kr['orta_inis_esigi_m'], 0)} m ve üzeri cepheler)"


def elektrik_kurali(odalar: list[dict] | None, k: dict) -> tuple[dict | None, dict]:
    """Oda başına elektrik kuralı (Ubeydullah, 3 Ekim 2026; doğruluk payı yaklaşık %75). Salon ile mutfak aynı mahaldeyse ikisi de uygulanır.
    Dönen: (sayım, kalem → döküm metni). Odaların işlevi bilinmiyorsa (None, {})."""
    if not odalar or not all(o.get("islev") for o in odalar):
        return None, {}
    ko = deg(k, "elektrik_oda")
    sayim = {x: 0 for x in ELEKTRIK_KALEMLERI}
    dokum: dict[str, list[str]] = {x: [] for x in ELEKTRIK_KALEMLERI}
    for islev, tablo in ko["odalar"].items():
        n = sum(o["islev"].count(islev) for o in odalar)
        for kalem, adet in tablo.items():
            if n:
                sayim[kalem] += n * adet
                dokum[kalem].append(f"{ISLEV_ADI[islev]} {n} × {adet}" if n > 1 else f"{ISLEV_ADI[islev]} {adet}")
    bilinmeyen = sorted({i for o in odalar for i in o["islev"]} - set(ko["odalar"]))
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
    h = g["kat_yuksekligi_m"]
    S: list[dict] = []

    def ekle(grup, kalem, boyut, adet, olcu=None, brut=None, birim="m²", formul="", durum="excel", kg=None, not_=None):
        S.append({"grup": grup, "kalem": kalem, "boyut": boyut, "adet": adet,
                  "olcu": None if olcu is None else round(olcu, 2), "brut": None if brut is None else round(brut, 2),
                  "birim": birim, "kg": None if kg is None else round(kg, 2), "formul": formul, "durum": durum, "not": not_})

    def adet_of(kalem):
        return next((s["adet"] or 0 for s in S if s["kalem"] == kalem), 0)

    c = g["cati"]
    yontem = c.get("yontem", "omega_asik")
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
        for taraf, ad in (("dis", "Dış cephe duvar panelleri"), ("ic", "İç cephe duvar panelleri")):
            x = ce.get(taraf)
            if not x:
                continue
            birim = deg(ck, "duvar_kg_m")[taraf].get(x["profil"])
            ekle("Çelik panel", ad, x["profil"].replace("x", " × "), x.get("panel_adedi"), x["boy_m"], birim="m",
                 kg=None if birim is None else x["boy_m"] * birim * oran,
                 formul=(f"duvar boyu × {tr(birim)} kg/m (motorun proje ortalaması)" if birim is not None else "bu profil için motorda birim ağırlık yok"),
                 durum="motor" if birim is not None else "soru", not_=x.get("not"))
        x = ce.get("dikme")
        if x and x.get("adet"):
            birim = deg(ck, "dikme_kg_m").get(x["profil"])
            boy = x["adet"] * x["boy_m"]
            ekle("Çelik panel", "Veranda dikmeleri (kolon paneli)", x["profil"].replace("x", " × "), x["adet"], boy, birim="m",
                 kg=None if birim is None else boy * birim, formul=f"adet × {tr(x['boy_m'])} m × {tr(birim)} kg/m (motorun proje ortalaması)", durum="motor", not_=x.get("not"))
        x = ce.get("kiris")
        if x and x.get("boy_m"):
            birim = deg(ck, "kiris_kg_m").get(x["profil"])
            ekle("Çelik panel", "Veranda kirişleri (kiriş paneli)", x["profil"].replace("x", " × "), tavan(x["boy_m"] / deg(ck, "kiris_panel_boyu_m")), x["boy_m"], birim="m",
                 kg=None if birim is None else x["boy_m"] * birim, formul=f"kiriş boyu × {tr(birim)} kg/m; adet = boy ÷ 4", durum="motor", not_=x.get("not"))
        x = ce.get("cati")
        if x:
            birim = deg(ck, "cati_kg_m2")[x["tip"]]
            ekle("Çelik panel", "Çatı makas panelleri", x["profil"].replace("x", " × "), deg(ck, "cati_panel_adedi")[x["tip"]], x["plan_m2"], birim="m²",
                 kg=x["plan_m2"] * birim, formul=f"saçak dahil çatı planı × {tr(birim)} kg/m² (motorun proje ortalaması); adet çatı tipine göre sabit", durum="motor",
                 not_="şimdilik Excel motoru kıstas (mühendis, 4 Ekim 12:14; Lokman, 4 Ekim 15:18); makas ölçüsü verilirse değişir")
        if yontem == "panel":   # yöntem A: tavan paneli ve çatı paneli (100 m² için kg: Lokman'ın 4 Ekim düzeltmesi; adet: mühendisin 3 Ekim cevabı)
            oturum = (ce.get("cati") or {}).get("oturum_m2")
            for ad, anahtar, kural, aciklama in (("Tavan paneli (makas arası)", "tavan_paneli_m2", "tavan_paneli", "tavan alanı"),
                                                  ("Çatı paneli (makas üstü, sırt 80 mm)", "cati_paneli_m2", "cati_paneli", "çatı yüzeyi")):
                if not ce.get(anahtar):
                    continue
                pk = deg(ck, kural)
                if oturum:
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
    dis_duvar = d["cevre_m"] * h
    kk = sum(x["adet"] * x["cevre_m"] * x["boy_m"] for x in d.get("kolon_kiris", []))
    alin = sum(d.get("alin_m2", []))
    dis_bosluk = sum(x["adet"] * x["en"] * x["boy"] for x in d["bosluklar"])
    dis_net = dis_duvar + kk + alin - dis_bosluk
    zb = deg(k, "zayiat", "boardex")                      # Boardex zayiatı (mühendis, 4 Ekim 2026 12:14: %8; önce %15)
    zb_carpan = tr(1 + zb)
    kal = deg(k, "levha_kalinligi_mm")                    # Boardex 12,5 mm, OSB 11 mm (mühendis, 4 Ekim 2026 12:14)
    boardex_boyut = f"{tr(kal['boardex'], 1)} × 1200 × 2400"
    osb_boyut = f"{tr(kal['osb'], 0)} × 1220 × 2440"      # adı "OSB 9 mm" olan satırlar 2025 listelerinin kalemleridir; onlarda kalınlık yazılmaz
    dis_zayiatli = dis_net * (1 + zb)
    kk_durum = "varsayim" if d.get("kolon_kiris_varsayim") else "excel"
    ekle("Dış cephe kaplama", "Dış cephe Boardex", boardex_boyut, tavan(dis_zayiatli / deg(k, "levha_m2", "boardex")), dis_net, dis_duvar + kk + alin,
         formul=f"(çevre × yükseklik + kolon/kiriş kaplaması + çatı alnı (kalkan) − boşluklar) × {zb_carpan} ÷ 2,88", durum=kk_durum,
         not_=f"zayiat %{tr(zb * 100, 0)}: mühendis, 4 Ekim 12:14; Lokman, 4 Ekim 15:18: bununla devam. 2025 listelerindeki adetler %15'e uyuyor; %15 ile {tavan(dis_net * 1.15 / deg(k, 'levha_m2', 'boardex'))} levha")
    if d.get("dis_osb"):
        zdo = deg(k, "zayiat", "dis_osb")                  # listedeki formül: Boardex ile aynı alan × 1,15 (Boardex zayiatından ayrı)
        ekle("Dış cephe kaplama", "Dış duvar OSB 9 mm", "1220 × 2440", tavan(dis_net * (1 + zdo) / deg(k, "levha_m2", "osb")), dis_net,
             formul=f"Boardex ile aynı alan (× {tr(1 + zdo)}) ÷ 2,98; üst paket", durum="excel")

    # ── İç cephe ─────────────────────────────────────────────────────────────
    ozet = {}
    za = deg(k, "zayiat", "duvar_alcipan")
    for tur, ad in (("beyaz", "beyaz"), ("yesil", "yeşil")):
        odalar = [o for o in g["odalar"] if o["tur"] == tur]
        brut = sum(o["cevre_m"] * h for o in odalar)
        net = brut - sum(sum(o["bosluk_m2"]) for o in odalar)
        ozet[tur] = (net, brut)
        if odalar:
            ekle("İç cephe kaplama", f"Duvar alçıpan {ad}", "1200 × 2500", tavan(net * (1 + za) / deg(k, "levha_m2", "alcipan")), net, brut,
                 formul="oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0" + ("; yeşil = ıslak hacimler" if tur == "yesil" else ""))
    for tur, ad in (("beyaz", "beyaz"), ("yesil", "yeşil")):
        a = g["tavan_m2"].get(tur)
        if a:
            ekle("İç cephe kaplama", f"Tavan alçıpan {ad}", "1200 × 2500",
                 tavan(a * (1 + deg(k, "zayiat", "tavan_alcipan")) / deg(k, "levha_m2", "alcipan")), a,
                 formul="tavan alanı × 1,05 ÷ 3,0" + ("; yeşil = ıslak hacim + veranda tavanı" if tur == "yesil" else ""),
                 durum="lokman" if tur == "yesil" else "motor")
    ic_net = ozet["beyaz"][0] + ozet["yesil"][0]
    zo = deg(k, "zayiat", "osb")
    if g.get("ic_osb_tum_duvarlar"):
        ekle("İç cephe kaplama", "İç duvar OSB 9 mm", "1220 × 2440", tavan(ic_net * (1 + zo) / deg(k, "levha_m2", "osb")), ic_net,
             formul="bütün iç yüzler (beyaz + yeşil net) × 1,05 ÷ 2,98; üst paket")
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
    ekle("İç cephe kaplama", "Duvar izolasyonu", "paket 8,64 m²", tavan(yal_net / deg(k, "yalitim_paket_m2")), yal_net, yal_brut,
         formul="dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64", durum="uydurma",
         not_=f"dış duvar {kat_sayisi} kat")

    # ── Çatı kaplaması (seçenek) ────────────────────────────────────────────
    sacak = c["sacak_boyu_toplam_m"]
    kenarlar = c["sacak_kenarlari_m"]
    pm, bm = deg(k, "parca_boyu_m", "mahya"), deg(k, "bindirme_m", "mahya")
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
        if d["uzatma"]:            # panel boyu kuralla uzatıldı (Lokman, 4 Ekim 16:18): adet düşüyorsa en çok 3 cm
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
        return "; panel boyu = eğimli boy + taşma" + (f" + {tr((dz['panel_boyu_m'] - dz['taban_boy_m']) * 100, 0)} cm (adet düşüyor)" if dz.get("uzatma") else "")

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
        if c.get("yuzey_m2") and c.get("panel_boyu_m"):
            n_, f_, d_, not__ = kaplama_adedi(kap, "panel")
            ekle("Çatı kaplamaları", ad, f"L {round(panel_boyu() * 1000)} · {round(kap * 100)} cm kapatır", n_, c["yuzey_m2"],
                 formul=f_ + boy_formulu(), durum=d_, not_=not__)
        ekle("Çatı kaplamaları", "Metal kiremit mahyası", "L 2800", tavan(c["mahya_hatti_m"] / (pm - bm)), c["mahya_hatti_m"], birim="m", formul=mahya_formul, durum="lokman")
        # Sac panel kapaması (2025 listelerinden). Tek kat panelde listeden çıktı (Lokman, 4 Ekim 2026 16:18: damlalıkla aynı gerekçe);
        # sandviç panelde soruldu. Girdide `cati.panel_kapamasi` yazıyorsa o: kapaması olan gerçek liste örnekleri öyle hesaplanır.
        if c.get("panel_kapamasi", deg(k, "panel_kapamasi")[kaplama]):
            ekle("Çatı kaplamaları", f"{ad} kapaması", "L 2500", kenar_kenar(kenarlar, deg(k, "parca_boyu_m", "sandvic_kapama")), sacak, birim="m",
                 formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma",
                 not_="listedeki uygulama (2025): sac kapama" if "panel_kapamasi" in c else
                      "2025 listelerindeki sac kapama. Tek kat panel kapaması listeden çıktı (Lokman, 4 Ekim 16:18); sandviç panelde de çıksın mı: soruldu (teyit bekliyor)")
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
            ekle("Çatı kaplamaları", ad, "L 2800", tavan(c["mahya_hatti_m"] / (pm - bm)), c["mahya_hatti_m"], birim="m", formul=mahya_formul, durum="lokman")
    if c.get("ozel_mahya_m"):
        ekle("Çatı kaplamaları", "Özel mahya (geniş)", "L 2800", tavan(c["ozel_mahya_m"] / (pm - bm)), c["ozel_mahya_m"], birim="m",
             formul="ana bina ile veranda çıkıntısının çatısı arasındaki birleşim boyu ÷ (2,8 − 0,30)", durum="lokman")
    if c.get("ters_mahya_m"):
        ekle("Çatı kaplamaları", "Ters mahya", "L 2800", tavan(c["ters_mahya_m"] / (pm - bm)), c["ters_mahya_m"], birim="m",
             formul="cumbalı çatıda çatıların birleştiği vadi boyu ÷ (2,8 − 0,30)", durum="lokman")
    # mahya bandı (mühendis, 4 Ekim 2026 12:14): (mahya adedi × 2,8 + ters mahya adedi × 2,8 + damlalık adedi × 2,5) ÷ 10.
    # Excel motorunda trapez sac mahyası × 0,8 de toplanır; OSB mahyası ve özel mahya toplanmaz.
    # Damlalık listeden tamamen çıktı (Lokman, 4 Ekim 2026 15:18: montajcılar kullanmıyor); terimi formülde yok.
    mb = deg(k, "mahya_bandi")
    bant_parcalari = [(s["kalem"], s["adet"], mb["parca_boyu_m"][anahtar]) for s in S for kalem, anahtar in
                      (("Metal kiremit mahyası", "metal_kiremit_mahyasi"), ("Ters mahya", "ters_mahya"), ("Trapez sac mahyası", "trapez_sac_mahyasi"))
                      if s["kalem"] == kalem and s["adet"]]
    bant_boyu = sum(n * boy for _, n, boy in bant_parcalari)
    if bant_boyu > 0:
        ekle("Çatı kaplamaları", "Mahya bandı", f"rulo / {tr(mb['rulo_m'], 0)} m", tavan(bant_boyu / mb["rulo_m"]), bant_boyu, birim="m",
             formul="(" + " + ".join(f"{ad.lower()} {n} × {tr(boy, 1)} m" for ad, n, boy in bant_parcalari) + f") ÷ {tr(mb['rulo_m'], 0)}",
             durum=k["mahya_bandi"]["durum"], not_="formül: mühendis, 4 Ekim 12:14 (Excel motorundaki gibi). Damlalık kullanılmıyor: listede yok, formüldeki terimi de çıkarıldı (Lokman, 4 Ekim 15:18)")
    # çatı müdahale kapağı: standart pakette gönderilmez; müşteri isterse eklenir (mühendis, 4 Ekim 2026)
    if g.get("cati_mudahale_kapagi"):
        ekle("Çatı kaplamaları", "Çatı müdahale kapağı", "adet", g.get("kat_adedi", 1) * deg(k, "cati_mudahale_kapagi")["kat_basina"], birim="",
             formul="müşteri isterse: kat adedi × 1", durum=k["cati_mudahale_kapagi"]["durum"])
    if c.get("cati_boyu_m") and c.get("bina_eni_m"):
        silte = c["cati_boyu_m"] * (c["bina_eni_m"] + deg(k, "silte_en_payi_m"))
        silte_kat = c.get("silte_kat", 1)
        ekle("Çatı kaplamaları", "Çatı şiltesi 80 mm", "9,6 m²/adet", silte_kat * tavan(silte / deg(k, "silte_adet_m2")), silte,
             formul="çatı boyu × (bina eni + 0,20) ÷ 9,6" + (f" × {silte_kat} kat" if silte_kat > 1 else ""), durum="uydurma")

    # ── Dere ────────────────────────────────────────────────────────────────
    pd, bd = deg(k, "parca_boyu_m", "dere"), deg(k, "bindirme_m", "dere")
    dere = tavan(sacak / (pd - bd))
    ekle("Dere", "Metal dere", "L 4000", dere, sacak, birim="m", formul=f"saçak boyu ÷ (4,0 − {tr(bd)} bindirme)", durum="motor")
    n_kural, n_not = inis_sayisi(c, k)
    if "inis_adedi" in c:
        n, n_durum = c["inis_adedi"], "liste"
        n_formul = f"listedeki iniş sayısı ({n}); " + (f"kural {n_kural} verir" if n_kural is not None else "kural hesaplanmadı: cephe ölçüleri yok")
    elif "inis_adedi_plan" in c:   # plana bakarak elle yerleştirilen inişler (Ubeydullah, 3 Ekim 2026)
        n, n_durum = c["inis_adedi_plan"], "model"
        n_formul = f"plana yerleştirilen iniş sayısı ({n}); " + (f"kural {n_kural} verir" if n_kural is not None else "kural hesaplanmadı")
    else:
        n, n_durum, n_formul = n_kural, "lokman", n_not
    ib = deg(k, "inis_basina")
    for ad, anahtar in (("Dere iniş borusu", "inis_borusu"), ("Dere iniş aparatı", "inis_aparati"), ("Açık dirsek", "acik_dirsek"),
                        ("Kapalı dirsek", "kapali_dirsek"), ("İniş kelepçesi", "inis_kelepcesi")):
        ekle("Dere", ad, "L 3000" if anahtar == "inis_borusu" else "adet", n * ib[anahtar], birim="",
             formul=(n_formul if anahtar == "inis_borusu" else f"iniş sayısı × {ib[anahtar]}"),
             durum=n_durum if (anahtar == "inis_borusu" or n_durum == "liste") else "motor",
             not_=("iniş plana bakarak yerleştirilir; düz saçakta ortalama 5 m'de bir (mühendis, 3 Ekim). Planda elle yerleştirilmediği için Lokman'ın kuralı kullanıldı"
                   if anahtar == "inis_borusu" and n_durum == "lokman" else None))
    if c.get("dere_kapagi") is not None:
        ekle("Dere", "Dere kapağı", "adet", c["dere_kapagi"], birim="", formul="listedeki sayı; motorda çatı tipine göre sabit", durum="liste")
    elif deg(k, "dere_kapagi").get(c["tip"]):
        ekle("Dere", "Dere kapağı", "adet", deg(k, "dere_kapagi")[c["tip"]], birim="", formul="çatı tipine göre sabit (dört omuzda yok)", durum="motor")
    ekle("Dere", "Dere kelepçesi", "adet", dere * deg(k, "dere_kelepcesi_dere_basina"), birim="", formul="dere adedi × 8", durum="motor")

    # ── Metal aksam ─────────────────────────────────────────────────────────
    ps = deg(k, "parca_boyu_m", "sacak_saci")
    tavan_toplam = sum(v for v in g["tavan_m2"].values() if v)
    if yontem == "omega_asik":
        bs = deg(k, "bindirme_m", "sacak_saci")
        ekle("Metal aksam", "Saçak sacı (30'luk)", "L 2500", tavan(sacak / (ps - bs)), sacak, birim="m",
             formul=f"saçak boyu ÷ (2,5 − {tr(bs)} bindirme)", durum="lokman",
             not_="30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden (Lokman'ın örneğinde L 2800 ÷ 2,5)")
        ekle("Metal aksam", c.get("sacak_omegasi", "Saçak omegası"), "L 2500", kenar_kenar(kenarlar, ps), sacak, birim="m",
             formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma")
        if c.get("alin_saci_m"):
            pa, ba = deg(k, "parca_boyu_m", "alin_saci"), deg(k, "bindirme_m", "alin_saci")
            ekle("Metal aksam", "Alın sacı (30'luk)", "300 × 2500", tavan(c["alin_saci_m"] / (pa - ba)), c["alin_saci_m"], birim="m",
                 formul=f"alın boyu ÷ (2,5 − {tr(ba)} bindirme)", durum="lokman", not_="30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden")
        om = tavan_toplam / deg(k, "tavan_omegasi_aralik_m")
        ekle("Metal aksam", "Tavan omegası (60'lık)", "L 3750", tavan(om / deg(k, "parca_boyu_m", "tavan_omegasi")), om, birim="m",
             formul="tavan alanı ÷ 0,60 ÷ 3,75", durum="uydurma")
        boy = 0.0
        if kirma or c.get("egimli_boy_m"):
            boy, not_ = asik_boyu(c, deg(k, "asik", "aralik_m"))
            ekle("Metal aksam", "Aşık", "L 4200", tavan(boy * (1 + deg(k, "asik", "zayiat")) / deg(k, "parca_boyu_m", "asik")), boy, birim="m",
                 formul="eğim boyunca 60 cm aralıkla sıralar + mahya aşığı; kırmada her sıra çatıyı dolanır; × 1,05 ÷ 4,2", durum="uydurma", not_=not_)
    else:
        boy = 0.0   # yöntem A'da saçak omegası gerekmez (Ubeydullah, 3 Ekim 2026)
    if c.get("sacak_alti") == "boardex":
        sa = sacak * c.get("sacak_alti_eni_m", deg(k, "sacak_alti_boardex_eni_m"))
        ekle("Metal aksam", "Saçaklar için Boardex", boardex_boyut, tavan(sa * (1 + zb) / deg(k, "levha_m2", "boardex")), sa,
             formul=f"saçak boyu × saçak eni × {zb_carpan} ÷ 2,88", durum="uydurma",
             not_="saçak altının Boardex olduğu: Lokman, 3 Ekim 13:27; formül 62 m² listeden" if yontem == "panel" else None)
    if c.get("sacak_yuzu_m2"):
        ekle("Metal aksam", "Saçak yüzü için Boardex", boardex_boyut, tavan(c["sacak_yuzu_m2"] * (1 + zb) / deg(k, "levha_m2", "boardex")), c["sacak_yuzu_m2"],
             formul=f"saçak ucu çevresi × saçak yüzü yüksekliği (topuk + panelin düşey ölçüsü) × {zb_carpan} ÷ 2,88", durum="muhendis",
             not_="saçak yüzü Boardex'le kaplanır: mühendis, 3 Ekim; kaplandığı: Lokman, 2 Ekim 22:05. Alan geometriden")
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
    ekle("Metal aksam", "Köşebent", "L 2500", tavan(kb_boy / kr["parca_boyu_m"]), kb_boy, birim="m",
         formul=(f"(oda tavan çevreleri {tr(cevre_top)} m" + (f" + veranda tavanı çevresi {tr(veranda_cevre)} m" if veranda_cevre else "")
                 + f" + {kose} iç köşe × {tr(kr['kose_boyu_m'], 1)} m) ÷ {tr(kr['parca_boyu_m'], 1)}"), durum="muhendis", not_=kose_notu)

    # ── Kapı ve pencere (modelden doğrudan) ─────────────────────────────────
    for x in g.get("kapi_pencere", []):
        ekle("Kapı ve pencere", x["kalem"], x["boyut"], x["adet"], birim="", formul=x.get("formul", "modeldeki açıklıklardan"), durum=x.get("durum", "model"))
    pencere = sum(x["adet"] for x in d["bosluklar"] if "kapı" not in x["ad"])

    # ── Elektrik ────────────────────────────────────────────────────────────
    # Sayılar: pafta sayımı varsa o (kesin); yoksa oda başına kural (Ubeydullah, 3 Ekim 2026; doğruluk payı yaklaşık %75).
    ek = deg(k, "elektrik")
    es_pafta = g.get("elektrik_sayim")
    es_kural, es_dokum = elektrik_kurali(g.get("elektrik_odalar"), k)
    es = es_pafta or es_kural
    kat_adedi = g.get("kat_adedi", 1)
    priz = 0
    if es:
        priz = es["tekli_priz"] + es["cift_priz"] + es["uydu_prizi"]
        anahtar = es["tekli_anahtar"] + es["cift_anahtar"]
        olcu_k = g.get("kapali_olcu_m") or g.get("dis_olcu_m")
        kosegen = math.hypot(*olcu_k) if olcu_k else None
        kural_notu = "oda başına kural; doğruluk payı yaklaşık %75 (mühendis, 3 Ekim). Kesin sayı elektrik paftasından gelir"
        cok_islevli = [f"{o['ad']} ({' + '.join(ISLEV_ADI[i] for i in o['islev'])})" for o in (g.get("elektrik_odalar") or []) if len(o["islev"]) > 1]
        if cok_islevli and not es_pafta:
            kural_notu += ". Salon ile mutfak aynı mahaldeyse iki kural birlikte uygulanır (mühendis, 4 Ekim): " + ", ".join(cok_islevli)
        for ad, kalem in (("Tijli duy", "tijli_duy"), ("Yuvarlak glop", "glop"), ("Ampul", None), ("Tekli anahtar", "tekli_anahtar"), ("Çiftli anahtar", "cift_anahtar"),
                          ("Tekli priz", "tekli_priz"), ("Çiftli priz", "cift_priz"), ("Uydu prizi", "uydu_prizi"), ("W otomat (sigorta)", "sigorta")):
            if kalem is None:
                ekle("Elektrik", ad, "adet", es["tijli_duy"] + es["glop"], birim="", formul="duy + glop", durum="motor")
            elif es_pafta:
                ekle("Elektrik", ad, "adet", es[kalem], birim="", formul="pafta sayımı", durum="liste")
            else:
                ekle("Elektrik", ad, "adet", es[kalem], birim="", formul="bina başına 9" if kalem == "sigorta" else (es_dokum[kalem] or "bu odalarda yok"),
                     durum="muhendis", not_=kural_notu if kalem == "tijli_duy" else None)
        if kosegen:
            ekle("Elektrik", "NYM kablo (3 × 2,5)", "metre", tavan(es["sigorta"] * kosegen + (es["tekli_priz"] + 2 * es["cift_priz"] + es["uydu_prizi"]) * 2), birim="",
                 formul=f"sigorta adedi × sigortadan en uzak mesafe (kapalı kısmın köşegeni, {tr(kosegen)} m) + (tekli priz + çiftli priz × 2 + uydu prizi) × 2 m", durum="motor")
            ekle("Elektrik", "NYM kablo (2 × 1,5)", "metre", tavan(es["sigorta"] * kosegen + (es["tekli_anahtar"] + 2 * es["cift_anahtar"]) * 2), birim="",
                 formul=f"sigorta adedi × sigortadan en uzak mesafe (kapalı kısmın köşegeni, {tr(kosegen)} m) + (tekli anahtar + çiftli anahtar × 2) × 2 m", durum="motor")
        ekle("Elektrik", "Buat kasa", "adet", anahtar + priz + g["oda_sayisi"], birim="", formul="anahtar + priz + oda sayısı (veranda hariç)", durum="motor")
    else:
        ekle("Elektrik", "Duy, glop, ampul, anahtar, priz, sigorta, buat ve NYM kablolar", "adet / metre", None, birim="",
             formul="elektrik paftası yok ve odaların işlevi bilinmiyor; pafta sayımı ya da oda başına kural gerekli", durum="bekliyor")
    ekle("Elektrik", "Uydu kablo", "metre", ek["uydu_kablo_priz_basina_m"] * (es["uydu_prizi"] if es else 1), birim="", formul="uydu prizi (1) × 25 m", durum="motor")
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
    alcipan_levha = sum(adet_of(x) for x in ("Duvar alçıpan beyaz", "Duvar alçıpan yeşil", "Tavan alçıpan beyaz", "Tavan alçıpan yeşil",
                                              "Dış cephe Boardex", "Saçaklar için Boardex", "Saçak yüzü için Boardex"))
    ekle("Vida", "Alçıpan vidası (3,5 × 35)", "adet", kat(alcipan_levha * v["alcipan_vidasi_levha_basina"], 250), alcipan_levha, birim="levha",
         formul="alçıpan ve Boardex levha sayısı × 40; 250'ye yuvarlandı")
    osb_levha = sum(s["adet"] or 0 for s in S if "OSB" in s["kalem"] and "mahya" not in s["kalem"].lower() and s["grup"] != "Vida")
    ov = v["osb_vidasi"]
    osb_say = (osb_levha * ov["osb_levha"] + priz * ov["priz"] + adet_of("Saçak sacı (30'luk)") * ov["sacak_saci"] + adet_of("Dere kelepçesi") * ov["dere_kelepcesi"])
    ekle("Vida", "OSB ve yalıpan vidası (3,9 × 32)", "adet", kat(osb_say, ov["yuvarlama"]), osb_say, birim="vida",
         formul="OSB levha × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; 500'e yuvarlandı", durum="motor",
         not_=None if es else "priz sayısı bilinmediği için priz payı yok")
    ekle("Vida", "Pencere vidası (4,8 × 70)", "adet", pencere * v["pencere_vidasi_pencere_basina"], pencere, birim="pencere", formul="pencere sayısı × 20")
    panel_adedi = g.get("celik_panel_adedi", celik_toplam_adet)
    if panel_adedi:
        t = v["trapez_5_5x25"]
        say = (adet_of("Aşık") * t["asik"] + adet_of("Tavan omegası (60'lık)") * t["omega_375"]
               + (adet_of(c.get("sacak_omegasi", "Saçak omegası")) if yontem == "omega_asik" else 0) * t["omega_240"]
               + panel_adedi * t["celik_panel"] + (g.get("kosebent_adedi") or adet_of("Köşebent")) * t["kosebent"])
        ekle("Vida", "Trapez vida (5,5 × 25)", "adet", kat(say, yv), say, birim="vida",
             formul="aşık × 10 + tavan omegası × 10 + saçak omegası × 6 + çelik panel × 10 + köşebent × 6; 250'ye yuvarlandı",
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

    # ── Boya ────────────────────────────────────────────────────────────────
    by = deg(k, "boya")
    if g.get("boya_dahil", True):
        for ad, anahtar in (("Dış cephe boyası", "dis_cephe_kova_m2_basina"), ("İç cephe boyası", "ic_cephe_kova_m2_basina"), ("Tavan boyası", "tavan_kova_m2_basina"), ("Astar", "astar_kova_m2_basina")):
            ekle("Boya", ad, "kova 17,5 kg", tavan(m2 * by[anahtar]), m2, formul=f"bina m² × {tr(by[anahtar] * 100, 0)}/100; 'boya dahil' ise", durum="motor")
    ekle("Boya", "Silikonize mastik", "adet", pencere * by["mastik_pencere_basina"], pencere, birim="pencere", formul="pencere adedi", durum="uydurma",
         not_="motorda mantolamasız cephede + m² × 2/3 var ('ayrıca eklenir'); üç gerçek listede de 8")
    ekle("Boya", "Dayson", "adet", tavan(m2 * by["dayson_m2_basina"]), m2, formul="bina m² × 0,06", durum="motor")
    ekle("Boya", "Poliüretan köpük", "adet", by["kopuk"], birim="", formul="standart 2", durum="motor")

    # ── bayi kuralı: gruplar ────────────────────────────────────────────────
    gruplar = {**deg(k, "bayi_kurali")["varsayilan_gruplar"], **(g.get("bayi") or {}).get("gruplar", {})}
    kapali = [ad for ad, acik in gruplar.items() if not acik]
    S[:] = [s for s in S if s["grup"] not in kapali]
    S.sort(key=lambda s: GRUP_SIRASI.index(s["grup"]))
    kaplama_adi = KAPLAMA_ADI.get(kaplama, kaplama) + (" (baz paket)" if kaplama == deg(k, "baz_paket_cati_kaplamasi") else "")
    return {"yontem": yontem, "yontem_adi": YONTEM_ADI[yontem], "cati_kaplamasi": kaplama_adi, "cati_kaplamasi_anahtar": kaplama, "kapali_gruplar": kapali,
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
    g["bayi"] = {"anahtar": anahtar, "gruplar": {**bk["varsayilan"]["gruplar"], **b.get("gruplar", {})}}
    for x in ("boya_dahil", "vitrifiye_dahil", "cati_mudahale_kapagi"):
        if x in b:
            g[x] = b[x]
    c = g["cati"]
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
        satir = f"  {s['kalem']:<52s} {s['boyut']:<26s} {'' if s['adet'] is None else s['adet']:>5}  {olcu:>18s} {kg:>9s}  [{s['durum']}]"
        if g:
            fark = "" if s["adet"] is None else ("AYNI" if s["adet"] == g["adet"] else f"fark {s['adet'] - g['adet']:+d}")
            satir += f"   listede {g['adet']}" + (f", {g['net']}" if "net" in g else "") + f" → {fark}"
        cik.append(satir)
    return "\n".join(cik)


def md_yaz(sonuc: dict, ad: str) -> str:
    satir = [f"# {ad}", "",
             f"Çatı yöntemi: {sonuc['yontem_adi']}. Çatı kaplaması (seçenek): {sonuc['cati_kaplamasi']}."
             + (f" Bayi kuralıyla kapalı gruplar: {', '.join(sonuc['kapali_gruplar'])}." if sonuc["kapali_gruplar"] else ""), "",
             "| Grup | Kalem | Boyut | Adet | Ölçü | kg | Kural | Durum | Not |", "|---|---|---|---|---|---|---|---|---|"]
    for x in sonuc["satirlar"]:
        olcu = "" if x["olcu"] is None else f"{x['olcu']:.1f} {x['birim']}".replace(".", ",")
        kg = "" if x["kg"] is None else f"{x['kg']:.0f}"
        satir.append(f"| {x['grup']} | {x['kalem']} | {x['boyut']} | {'' if x['adet'] is None else x['adet']} | {olcu} | {kg} | {x['formul']} | {x['durum']} | {x['not'] or ''} |")
    return "\n".join(satir) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", type=Path)
    ap.add_argument("--karsilastir", type=Path)
    ap.add_argument("--cikti", type=Path)
    ap.add_argument("--md", type=Path, help="tabloyu Markdown olarak yaz")
    ap.add_argument("--kaplama", choices=list(KAPLAMA_ADI), help="çatı kaplaması seçeneğini girdidekinin yerine kullan")
    ap.add_argument("--mudahale-kapagi", action="store_true", help="çatı müdahale kapağını ekle (standart pakette yok; müşteri isterse)")
    ap.add_argument("--bayi", help="bayi kuralı anahtarı (canlıda bayinin telefon numarası); bayi_kurallari_ornek.json içinden okunur")
    ap.add_argument("--bayi-kurallari", type=Path, default=BURADA / "bayi_kurallari_ornek.json")
    a = ap.parse_args()
    g = json.loads(a.girdi.read_text(encoding="utf-8"))
    if a.kaplama:
        g["cati"]["kaplama"] = a.kaplama
    if a.mudahale_kapagi:
        g["cati_mudahale_kapagi"] = True
    if a.bayi:
        bk = json.loads(a.bayi_kurallari.read_text(encoding="utf-8"))
        if a.bayi not in bk["bayiler"]:
            raise SystemExit(f"Bayi kuralı bulunamadı: {a.bayi}")
        bayi_uygula(g, a.bayi, bk)
    k = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))
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
                   "kiris_kolon": kg.get("Veranda dikmeleri (kolon paneli)", 0) + kg.get("Veranda kirişleri (kiriş paneli)", 0),
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
