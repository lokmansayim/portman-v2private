#!/usr/bin/env python3
"""Şartname belgesini (`docs/sartname/yukleme_listesi_yontemi.md`) hesap çıktılarından üretir.

Belgedeki tablolar ve sayılar `sonuc/` altındaki çıktılardan okunur; elle yazılmaz. Önce `hepsini_kos.sh` koşulmalı.
Metin bu dosyanın içindedir: kural ya da kaynak değişince burada düzeltilir, belge yeniden üretilir.

Kullanım:
    python belge_uret.py --zaman "4 Ekim 2026 02:00"
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import kural

from cati_acilim import dizilim as _acilim_dizilimi
from motor_formul import BESIK_10, SABLON, motor_kaplama

BURADA = Path(__file__).resolve().parent
S = BURADA / "sonuc"
BELGE = BURADA.parents[1] / "docs" / "sartname" / "yukleme_listesi_yontemi.md"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--zaman", required=True, help="belgenin başındaki tarih ve saat")
A = ap.parse_args()
T = (S / "tablolar.md").read_text(encoding="utf-8")
K = kural.oku()
if (any(a not in K for a in ("urun_adlari", "yontem_a_kalkan_ust_kapamasi", "panel_cati_kenarlari", "taharet_muslugu")) or (K.get("duvar_dibi") or {}).get("deger", {}).get("malzeme") != "ozel_mahya"
        or not K["yontem_a_kalkan_ust_kapamasi"]["deger"].get("parca_boyu_m") or K["vida"]["deger"].get("trapez_5_5x25_c_profil_dahil") is not False
        or K["inis"]["deger"].get("alcak_cati_ustundeki_kose") != "kucuk_catida_yok" or not K["inis"]["deger"].get("kisa_dere_tek_inis_m")):
    raise SystemExit(f"Bu belge güncel kural setiyle (0.19 ve sonrası) üretilir; seçili set: {K.get('sema')} ({kural.yol().name}).")


def oku(ad: str) -> dict:
    return json.loads((S / ad).read_text(encoding="utf-8"))


def tr(x, n=0) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def bolum(baslik: str) -> str:
    a = T.index("## " + baslik)
    b = T.find("\n## ", a + 3)
    govde = T[a:(b if b != -1 else len(T))]
    return "\n".join(govde.split("\n")[2:]).strip()


def satir(v: dict, kalem: str) -> dict:
    return next(s for s in v["satirlar"] if s["kalem"] == kalem)


def adet(v: dict, kalem: str):
    return satir(v, kalem)["adet"]


def kg(v: dict, kalem: str) -> float:
    return satir(v, kalem)["kg"]


baz, d140, yb = oku("C8201_yukleme_taslak.json"), oku("C8201_dis_karkas_140_yukleme_taslak.json"), oku("C8201_yontem_B.json")
gb, g140 = oku("C8201_girdi.json"), oku("C8201_dis_karkas_140_girdi.json")
TOPLAM = "Toplam (adedi ve kg'ı bilinenler)"
tutmayan = bolum("Adedi tutmayan kalemler")
tam = bolum("Üç gerçek listeyle karşılaştırma")
ozet = next(x for x in tam.split("\n") if x.startswith("Özet:"))
ck = [x for x in tam.split("\n") if x.startswith(("| Çelik (kg)", "| Dış duvar |", "| İç duvar |", "| Duvar toplamı |", "| Kiriş ve kolon |", "| Çatı |", "| Toplam |"))]
celik_kg = "\n".join([ck[0], "|---|---|---|---|"] + ck[1:])
taslak = bolum("Ç8201 taslak: baz ve dış 140")
kaplama = bolum("Ç8201: çatı kaplaması seçenekleri")
kosebent = bolum("Köşebent: mühendisin formülü")
elektrik_sinama = bolum("Elektrik kuralının sınaması (105 m² liste)")
elektrik_oda = bolum("Ç8201: elektrik, oda oda")

ozetler = [oku(f"ornek_{n}m2_karsilastirma.json")["karsilastirma_ozeti"] for n in (90, 62, 105)]
kars_top, kars_ayni = sum(x["karsilastirilan"] for x in ozetler), sum(x["ayni"] for x in ozetler)
kg_m = K["celik"]["duvar_kg_m"]["deger"]
dis_boy, ic_boy, ic_boy_140 = gb["celik"]["dis"]["boy_m"], gb["celik"]["ic"]["boy_m"], g140["celik"]["ic"]["boy_m"]
kb = baz["ara"]["kosebent"]
ot = gb["osb_takviye"]
osb_s = satir(baz, "OSB (TV ve mutfak dolabı arkası takviyesi)")
tp, cp = satir(baz, "Tavan paneli (makas arası)"), satir(baz, "Çatı paneli (makas üstü, sırt 80 mm)")
dz = baz["ara"]["kirma_dizilim"]     # kırma çatıda kaplama dizilimi (baz kaplama)
dizilim_tablo = bolum("Kırma çatıda kaplama dizilimi")
# Excel motorunun köşebent formülü, Ç8201'in ölçüleriyle (kapalı kısım): (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5
uzun, kisa = gb["kapali_olcu_m"]
motor_kosebent = math.ceil((uzun * 6 + kisa * 6 + 9 * 4 * 2.7) / 2.5 - 1e-9)
pk_tavan, pk_cati = K["celik"]["tavan_paneli"]["deger"], K["celik"]["cati_paneli"]["deger"]
oturum = gb["celik"]["cati"]["oturum_m2"]
dz_H = min(gb["cati"]["plan_m"]) / 2 * math.sqrt(1 + gb["cati"]["egim"] ** 2)     # eğimli boy (m)
BAZ_KAPLAMA = {"tek_kat_panel": "Tek kat panel", "sandvic_panel": "Sandviç panel"}[K["baz_paket_cati_kaplamasi"]["deger"]]
kaplama_s = satir(baz, BAZ_KAPLAMA)


def secenek(kod: str, kalem: str) -> dict:
    return satir(oku(f"C8201_kaplama_{kod}.json"), kalem)


sandvic_s, trapez_s, kiremit_s = secenek("sandvic_panel", "Sandviç panel"), secenek("trapez_sac", "Trapez sac"), secenek("osb_kiremit", "Metal kiremit (kiremit desen sac)")
k62 = oku("ornek_62m2_karsilastirma.json")["karsilastirma"]["Sandviç panel"]
dis140_ince = dis_boy * kg_m["dis"]["140x45x0,8"]      # 0,8 mm olsaydı (3 Ekim varsayımı)
ic140_ince = ic_boy_140 * kg_m["ic"]["80x45x0,8"]
bant_s = satir(baz, "Mahya bandı")
# mahya bandının 01:24 uygulaması: mahya uzunluğu ÷ rulo boyu (üçüncü cevaplarla yerini parça adedi × parça boyu aldı)
onceki_bant = math.ceil(gb["cati"]["mahya_hatti_m"] / K["mahya_bandi"]["deger"]["rulo_m"] - 1e-9)
boardex_s = satir(baz, "Dış cephe Boardex")
boardex_15 = math.ceil(boardex_s["olcu"] * 1.15 / K["levha_m2"]["boardex"]["deger"] - 1e-9)      # önceki zayiatla (%15)
zb = K["zayiat"]["boardex"]["deger"]
tasma_cm = K["cati_kaplama_tasma_m"]["deger"] * 100
DZ_KR = K["kirma_cati_dizilim"]["deger"]
kesim_mm = DZ_KR["kesim_payi_m"] * 1000
dis_kose = sum(o["dis_kose"] for o in gb["odalar"])
boyle = [oku(f"ornek_{n}m2_karsilastirma.json")["karsilastirma"]["Dış cephe Boardex"] for n in (90, 62, 105)]     # Boardex: hesap / liste
YAYIMLANAN = {"kosebent": 51, "boardex": 33, "mahya_bandi": 3, "panel_boyu_mm": 4300, "sandvic": 24, "trapez": 30}      # 4 Ekim 02:58 sürümü (commit 61d1996)
# 4 Ekim 13:22 sürümü (commit 22ddf7e): taşma 5 cm, kesim payı 5 mm, en az paneli veren başlangıç; tek kat panel 87, kiremit desen sac 110 cm
S1322 = {"tek_kat": 28, "sandvic": 26, "trapez": 32, "kiremit": 26}
# 4 Ekim 16:13 sürümü (commit 21ed582): her yüzde sol köşeden, kapatma 100 cm, panel boyu eğimli boy + taşma (L 4315); liste 89 satır
S1613 = {"tek_kat": 27, "sandvic": 27, "trapez": 32, "kiremit": 30, "sandvic_80": 32, "kapama": 18, "satir": 89}
# 7 Ekim 03:46 sürümü (commit eff6a74; kural seti 0.12, `kurallar/liste/setler/0.12.json`): panel boyu mm'ye yukarı (taban L 4315), uzatma kuralıyla L 4325;
# bindirmeler 30 cm; veranda tavanı yeşil alçıpan; duvar izolasyonu listede; liste 88 satır; üç gerçek listeyle karşılaştırma 74 / 119
S0346 = {"taban_mm": 4315, "boy_mm": 4325, "esik_mm": 4318, "tek_kat": 25, "sandvic": 25, "trapez": 30, "kiremit": 28, "d87": ("L 4345", 28, 29), "d110": ("L 4315", 26),
         "satir": 88, "kars": (74, 119), "nym": (145, 121), "tavan_yesil": 8, "duvar_izolasyonu": 13, "trapez_vida_B": 2000, "uzatilan": 34}
osb_iki = baz["ara"]["osb_takviye"]          # OSB takviyesi: yalnız dolap ve TV duvarları / odanın bütün yüzeyi
# Montaj paftalarından okunanlar (4 Ekim 2026; üç gerçek listenin projeleri; paftalar depoda değil, Lokman'ın Mac'inde).
# 62 ve 90 m² projelerde ana DWG'deki "Omega ve Aşık" ölçü stiliyle yazılmış parça boyları ve iniş işaretleri; 105 m² projede PDF paftalardaki ölçü yazıları.
# (parça sayısı, toplam boy m, parçaların stok boya en iyi yerleşimi). Stok boy: omega 365, aşık 410 cm (paftadaki tam parça yazısı).
PAFTA = {"inis": {62: 7, 90: 8, 105: 10},
         "omega": {62: (29, 80.5, 25), 90: (50, 130.2, 39), 105: (53, 144.9, 43)},
         "asik": {62: (54, 155.6, 39), 90: (62, 218.4, 55), 105: (75, 276.3, 71)},
         "asik_liste_105": 71}
uz = dz["uzatma"]                              # panel boyu uzatma kuralının uyguladığı değişiklik (Lokman, 4 Ekim 16:18; pay koşulu tabanda: 7 Ekim)
UZ_KR = K["panel_boyu_uzatma"]["deger"]
YV_MM = K["panel_boyu_yuvarlama_mm"]["deger"]  # panel boyu bu adıma yukarı yuvarlanır (Lokman, 7 Ekim 07:45)
taban_mm, boy_mm = round(gb["cati"]["panel_boyu_m"] * 1000), round(dz["panel_boyu_m"] * 1000)
gereken_mm = (dz["egimli_boy_m"] + K["cati_kaplama_tasma_m"]["deger"]) * 1000     # eğimli boy + taşma (yuvarlanmadan)
fazla_cm = tr((boy_mm - gereken_mm) / 10, 1)   # tam boy giden panellerde mahya ucunda kalan fazlalık


def metre(n: int, mm: int) -> str:
    """Toplam boy (m, bir hane; yarım yukarı): adet × panel boyu. Tam sayıyla hesaplanır ki 129,45 → 129,5 olsun."""
    return tr((n * mm + 50) // 100 / 10, 1)


kesim_notu = "artığı kullanılmayan kesim yok" if not dz["tek"] else f"{dz['tek']} kesimde artan parça kullanılmıyor"
KAP = {a: K[a]["deger"] for a in ("tek_kat_panel_kapatma_m", "sandvic_panel_kapatma_m", "kiremit_kapatma_m", "trapez_sac_kapatma_m")}


def dz_oku(kod: str) -> dict:
    return oku(f"C8201_kaplama_{kod}.json")["ara"]["kirma_dizilim"]


dz_s, dz_t, dz_k = dz_oku("sandvic_panel"), dz_oku("trapez_sac"), dz_oku("osb_kiremit")
assert dz["tasma_cm"] == tasma_cm and dz["kesim_payi_mm"] == kesim_mm, "belge taşmayı ve kesim payını kuraldaki değerle anlatıyor"
assert not dz_k["artan_parca_karsi_yuzde"] and dz["artan_parca_karsi_yuzde"], "belge: artan parça yalnız kiremit desen sacda kullanılmaz"
assert DZ_KR["baslangic"] == "sol" == dz["baslangic"], "belge: dizilim her yüzde sol köşeden başlıyor diyor"
assert KAP == {"tek_kat_panel_kapatma_m": 1.0, "sandvic_panel_kapatma_m": 1.0, "kiremit_kapatma_m": 1.0, "trapez_sac_kapatma_m": 0.8}, "belge kapatma genişliklerini 100, 100, 100 ve 80 cm diye anlatıyor"
assert YV_MM == 10 and math.ceil(gereken_mm - 1e-6) == S0346["taban_mm"] and taban_mm == math.ceil(gereken_mm / YV_MM - 1e-9) * YV_MM == 4320, \
    "belge: Ç8201'de eğimli boy + taşma 4315 mm (mm'ye yukarı); 10 mm'ye yukarı yuvarlanınca taban L 4320 diyor"
assert uz and all(z["uzatma"] and z["uzatma"]["neden"] == "pay" and z["uzatma"]["boy_mm"] == boy_mm == 4330 and z["uzatma"]["taban_boy_mm"] == taban_mm
                  and z["uzatma"]["taban_adet"] == z["adet"] < z["uzatma"]["taban_saglamlik_adet"] for z in (dz, dz_s, dz_t, dz_k)), \
    "belge: dört kaplamada taban boyda pay ince; boy pay koşuluyla L 4330'a uzuyor, adet değişmiyor diyor"
assert (dz["adet"], dz_s["adet"], dz_t["adet"], dz_k["adet"]) == (S0346["tek_kat"], S0346["sandvic"], S0346["trapez"], S0346["kiremit"]), \
    "belge: adetler 7 Ekim 03:46 sürümündekilerle (L 4325) aynı diyor"
assert all(z["bir_cm_payla_adet"] == z["adet"] for z in (dz, dz_s, dz_t, dz_k)), "belge: listedeki boyda adet, kesim payı 1 cm olsa da aynı diyor"
assert UZ_KR == {"uygula": True, "en_cok_m": 0.03, "adim_m": 0.01, "saglamlik_kesim_payi_m": 0.01, "taban_icin_de": True}, \
    "belge uzatma kuralını 1 cm adım, en çok 3 cm, 1 cm kesim payına dayanıklı ve pay koşulu taban boyda da aranır diye anlatıyor"
assert K["osb_takviye"]["deger"]["baz"] == "duvarlar" and osb_iki["duvarlar_adet"] == adet(baz, "OSB (TV ve mutfak dolabı arkası takviyesi)") < osb_iki["butun_oda_adet"], \
    "belge: OSB takviyesinde geçerli kural dolap ve TV duvarları diyor"
assert not K["panel_kapamasi"]["deger"]["tek_kat_panel"] and not any(x["kalem"] == "Tek kat panel kapaması" for x in baz["satirlar"]) and S0346["satir"] == S1613["satir"] - 1, \
    "belge: tek kat panel kapaması listeden çıktı, liste bir satır kısaldı (89 → 88) diyor"
# 7 Ekim kararlarıyla baz listede değişenler: duvar izolasyonu çıktı; veranda tavanı (Boardex) ve acil müdahale kapağı girdi (88 → 89 satır; 7–9 Ekim'de 89).
# 10 Ekim 2026 (kural seti 0.18): taharet musluğu girdi (vitrifiye dahil; ıslak hacim başına 4) → 90.
BAZ_SATIR_0709 = S0346["satir"] - 1 + 2
th_s = satir(baz, "Taharet musluğu 20 mm")
assert len(baz["satirlar"]) == BAZ_SATIR_0709 + 1 == 90 and not any(x["kalem"] == "Duvar izolasyonu" for x in baz["satirlar"]) \
    and th_s["adet"] == th_s["olcu"] * K["taharet_muslugu"]["deger"]["islak_hacim_basina"] and th_s["olcu"] >= 1, \
    "belge: 7 Ekim kararlarıyla liste 88 → 89 satır (duvar izolasyonu çıktı; veranda tavanı Boardex'i ve acil müdahale kapağı girdi), 10 Ekim'de taharet musluğuyla 90 diyor"


def acilim_adedi(boy_mm_: int, pay_mm: float, kapatma: float = 1.0, paylas: bool = True) -> int:
    """Ç8201'in çatısında, verilen panel boyu ve kesim payıyla dizilimin adedi (kuraldaki başlangıç ve taşmayla)."""
    px, py, egim = gb["cati"]["plan_m"][0], gb["cati"]["plan_m"][1], gb["cati"]["egim"]
    return _acilim_dizilimi(px, py, egim, kapatma, boy_mm_ / 1000, paylas, DZ_KR["baslangic"], pay_mm / 1000, tasma_cm / 100)["adet"]


def pay_siniri(boy_mm_: int, kapatma: float = 1.0, paylas: bool = True) -> float:
    """Ç8201'de verilen panel boyunda adedin, kuraldaki kesim payıyla çıkan adetle aynı kaldığı en büyük kesim payı (mm; 0,1 mm adımla, 40 mm'ye kadar)."""
    n0, son = acilim_adedi(boy_mm_, kesim_mm, kapatma, paylas), kesim_mm
    for p10 in range(round(kesim_mm * 10), 401):
        if acilim_adedi(boy_mm_, p10 / 10, kapatma, paylas) != n0:
            break
        son = p10 / 10
    return son


def uz_satiri(ad: str, kapatma: float, paylas: bool, eski_taban: int, eski_kural: str, yeni_boy_mm: int, yeni_adet: int) -> str:
    """Panel boyu tablosunun bir satırı: 4 Ekim (taban L 4315 ve kuralla), 7 Ekim (taban L 4320'de kesim payı 5 mm / 1 cm ile adet; listede)."""
    a5, a10 = acilim_adedi(taban_mm, kesim_mm, kapatma, paylas), acilim_adedi(taban_mm, 10.0, kapatma, paylas)
    assert acilim_adedi(yeni_boy_mm, kesim_mm, kapatma, paylas) == yeni_adet == acilim_adedi(yeni_boy_mm, 10.0, kapatma, paylas), "belge: listedeki boyda adet 1 cm kesim payıyla da aynı"
    return f"| {ad} | {eski_taban} | {eski_kural} | {a5} / {a10} | L {yeni_boy_mm} × {yeni_adet} | {metre(yeni_adet, yeni_boy_mm)} m |"


# Çokgen sınamasının (`cati_acilim_saglama.py`) özeti: sınama her koşuda bu dosyayı yazar (hangi kural setiyle, kaç deneme, kaç uzatma)
_sg = oku("cati_acilim_saglama.json")
assert _sg["kural_seti"] == K["sema"] and _sg["sorun"] == 0 and (_sg["dizilim"], _sg["kural_denemesi"]) == (1440, 450) and _sg["uzatilanlarda_tam_saglam"] == _sg["uzatilan"], \
    "belge: çokgen sınaması güncel kural setiyle koştu, 1440 dizilim ve 450 kural denemesinde sorun yok, uzatılan her boy tam sağlam diyor (önce hepsini_kos.sh)"
SAGLAMA = {"uzatilan": _sg["uzatilan"], "payli": _sg["pay_kosulundan"]}
# Bağımsız denetimin 7 Ekim sonucu (bu koda ve çıktılara bakmayan ayrı bir oturum; 7 Ekim 09:10–09:30). Sayılar o oturumun raporundan; aşağıdaki denetim
# raporda yazanların bu belgedeki hesapla aynı olduğunu sınar (boylar, adetler, kesim payı sınırları).
BAGIMSIZ = {"boylar_mm": (4330, 4330, 4330, 4350, 4320), "adetler": (25, 30, 28, 28, 26), "pay_siniri_mm": {4320: 7.8, 4330: 17.8}, "hucre": 60, "en_az": 25, "alan_alt_siniri": 24}
# Kör test projesinin kararlardan sonraki durumu (`../2026-10-06_kor_test/kararlar_kos.sh`)
KT = json.loads((BURADA.parent / "2026-10-06_kor_test" / "sonuc" / "KT01_kararlar_kiyas.json").read_text(encoding="utf-8"))
# Genel motorun sağlamasının özeti (`../2026-10-06_kor_test/saglama.py` her koşuda yazar): iki motorun panel boyu kuralı rastgele kırma çatılarda
# birbirine karşı denenir (genel motor ↔ kırma motoru: boy, adet, uzatmanın nedeni)
GS = json.loads((BURADA.parent / "2026-10-06_kor_test" / "sonuc" / "saglama.json").read_text(encoding="utf-8"))
assert GS["kural_seti"] == K["sema"] and GS["sorun"] == 0 and GS["kural_denemesi"] >= 100 and 0 < GS["kural_pay_kosulundan"] <= GS["kural_uzayan"], \
    "belge: genel sağlama güncel kural setiyle koştu, iki motorun panel boyu kuralı en az 100 denemede aynı, içinde pay koşulundan uzayan da var diyor (önce ../2026-10-06_kor_test/saglama.py)"
# 8 Ekim 00:45 cevapları (kural seti 0.14): levhanın listede yazılan adı; KT-01'de özel mahya, mastik ve kalkan kenarı
LEVHA_ADI = K["urun_adlari"]["deger"]["degistir"][0][1]
levha_satirlari = [x for x in baz["satirlar"] if x.get("liste_adi")]
assert LEVHA_ADI == "OUTWEAR Dış Cephe Levhası" and len(levha_satirlari) == 4 and all(LEVHA_ADI in x["liste_adi"] for x in levha_satirlari), \
    "belge: Ç8201'de dört satırda levha üreticinin adıyla yazıyor diyor"


def kt_birim(ad: str) -> dict:
    return next(b for b in KT["birimler"] if b["ad"] == ad)


kt_ust = next((x for x in KT["a_listesinde_gercek_listede_olmayan"] if x["kalem"] == K["yontem_a_kalkan_ust_kapamasi"]["deger"]["ad"]), None)
assert kt_ust is not None, "belge: KT-01'in çelik standardı listesinde alın kapama satırı var diyor (önce ../2026-10-06_kor_test/kararlar_kos.sh)"
KT_A = json.loads((BURADA.parent / "2026-10-06_kor_test" / "sonuc" / "KT01_kararlar_A_yukleme.json").read_text(encoding="utf-8"))
KT_A_G = json.loads((BURADA.parent / "2026-10-06_kor_test" / "sonuc" / "KT01_kararlar_A_girdi.json").read_text(encoding="utf-8"))
kt_om = satir(KT_A, "Özel mahya (geniş)")
kt_om_ayri = sum(math.ceil(x["boy_m"] / (2.8 - K["bindirme_m"]["mahya"]["deger"]) - 1e-9) for x in KT_A_G["cati"]["duvar_dibi"])
kt_bant = adet(KT_A, "Mahya bandı")
kt_bant_ile = math.ceil((satir(KT_A, "Mahya bandı")["olcu"] + kt_om["adet"] * 2.8) / K["mahya_bandi"]["deger"]["rulo_m"] - 1e-9)      # özel mahya da sayılsaydı
assert kt_om["adet"] == 5 and kt_om_ayri == 6 and f"ayrı yuvarlansa {kt_om_ayri}" in kt_om["not"] and not kt_om.get("renk") and kt_bant == 3 and kt_bant_ile == 4 and "(çatı panelli ek yapının alınları hariç)" in satir(KT_A, kt_ust["kalem"])["formul"], \
    "belge: KT-01'de özel mahya 5 (yapı yapı yuvarlansa 6), satırda renk yok, mahya bandı 3 (özel mahya sayılsa 4), üst kapamanın ölçüsünde ek yapının alınları yok diyor"
kt_alin_bx = adet(KT_A, "Alın (kalkan kenarı) için Boardex")
kt_ust_olcu = satir(KT_A, kt_ust["kalem"])["olcu"]          # kalkan kenarlarının boyu (kıyas dökümünde yalnız adetsiz satırın ölçüsü yazar)
assert abs(kt_ust_olcu - 20.97) < 1e-6, "belge: KT-01'de kalkan kenarlarının boyu 20,97 m diyor"
assert (kt_ust["adet"], kt_ust["boyut"], kt_ust["durum"], satir(KT_A, kt_ust["kalem"]).get("renk")) == (10, "L 2500", "lokman", "antrasit gri") and kt_alin_bx == 2 \
    and kt_birim("Damlalık (bina ve müştemilat)")["b"] == 5 and kt_birim("Silikonize mastik")["b"] is None and kt_birim("Dere iniş borusu")["b"] == 9 and KT.get("inis_onayli"), \
    "belge: KT-01'de alın kapama 10 adet L 2500 (lokman, saçak ve alın renginde), kalkan Boardex'i 2 levha; özel mahya 5; mastik yok; iniş 9 (8–9 Ekim'de 7; 10 Ekim'den beri " \
    "müştemilatın deresiyle) ve eşik onaylı diyor"
# Bozma denemeleri (7 Ekim; elle koşuldu, betiği depoda değil): ölçüt iki motorda dokuz yerde bilerek bozuldu; yedisi yakalandı, ikisi eşdeğer çıktı
# (6000 rastgele çatının 162'sinde pay ince; hepsi 3 cm içinde tam düzeliyor: 160'ı 1 cm, biri 2 cm, biri adet düşerek). Sayılar belgede yazıyla durur.
assert not KT["denetim_sorunlari"] and KT["onceki"] == {"kor": 42, "duzeltilmis": 48, "sablon": 61, "pafta": 71}, "belge: kör testin 7 Ekim 03:46 sonuçları 42, 48, 61 ve 71 diyor"
kt_b, kt_a, kt_n = KT["ozet"]["b"]["ayni"], KT["ozet"]["a"]["ayni"], KT["ozet"]["b"]["gercek_satir"]
# 10 Ekim 2026 (kural seti 0.18): tek eğimli çatı panelli çatılar beş fotoğraftaki gibi; KT-01'in müştemilatına da dere, iniş, özel büküm saçak sacı ve sundurma kapama
# geldi. Gerçek listede müştemilatta dere yok: 0.17'de tutan dere, dere kapağı, dere kelepçesi ve beş iniş satırı karar farkı oldu (63 → 55).
KT_017 = {"b": 63, "a": 60}            # 9 Ekim 22:44 (kural seti 0.17; commit c939fe2'deki KT01_kararlar_kiyas.json)
kt_mus = [b for b in KT["birimler"] if (b.get("fark") or "").startswith("karar:") and "müştemilatta dere" in b["fark"]]
kt_mus_satir = sum(len(b["gercek_satirlar"]) for b in kt_mus)
kt_ek_satirlar = KT.get("b_listesinde_gercek_listede_olmayan") or []
assert kt_mus_satir == 8 and kt_b + kt_mus_satir == KT_017["b"] and [x["kalem"] for x in kt_ek_satirlar] == ["Özel büküm saçak sacı", "Sundurma kapama"] \
    and [x["adet"] for x in kt_ek_satirlar] == [3, 3], \
    "belge: KT-01'de 10 Ekim kararıyla 8 satır (dere, kapak, kelepçe, beş iniş satırı) karar farkı oldu (63 → 55); B listesine özel büküm saçak sacı 3 ve sundurma kapama 3 geldi diyor"
# İkinci kör test (KT-02, 9 Ekim 2026): 22:05 kıyası (kural seti 0.15; `kt02_kiyas_kos.sh`) ve Lokman'ın 22:22 cevaplarından sonraki tablo (`kt02_cevaplar_kos.sh`)
KT2 = BURADA.parent / "2026-10-09_kor_test_2" / "sonuc"
k2 = json.loads((KT2 / "KT02_kiyas.json").read_text(encoding="utf-8"))
k2c = json.loads((KT2 / "KT02_cevaplar_kiyas.json").read_text(encoding="utf-8"))
k2_birim = lambda kiyas, ad: next(b for b in kiyas["birimler"] if b["ad"] == ad)
k2_n, k2_kor, k2_duz = k2["ozet"]["kor_b"]["gercek_satir"], k2["ozet"]["kor_b"]["ayni"], k2["ozet"]["duz_b"]["ayni"]
k2_s, k2c_k = k2["siniflar"], k2c["kalan_siniflar"]
k2_bx = k2_birim(k2c, "Dış cephe Boardex (veranda tavanı dahil)")["duz_b"]
k2_k15 = k2_birim(k2c, "Kiriş (1,5)")
assert not k2["denetim_sorunlari"] and not k2c["denetim_sorunlari"] and (k2_n, k2_kor, k2_duz) == (85, 46, 57) and k2c["ozet"]["duz_b"]["ayni"] == k2_duz \
    and k2_s == {"girdi": 11, "kural": 5, "karar": 13, "elle": 7, "pafta": 3} and k2c_k["kural"] == 0 and k2c_k["karar"] == 18 and k2c_k["girdi"] == 0 and k2_bx == 51 \
    and k2_k15["duz_b_kg"] == k2_k15["gercek_kg"] == 46.89 and k2_k15["kor_b_kg"] is None, \
    "belge: KT-02'de 85 satırın kör 46'sı, düzeltilmiş 57'si aynı; sınıflar 11/5/13/7/3; cevaplardan sonra kural eksiği yok (karar 18), dış cephe levhası 51, 1,5 mm kiriş 46,89 kg diyor"
# Üçüncü kör test (KT-03, 9–10 Ekim 2026): 10 Ekim 00:24 kıyası (kural seti 0.17; `kt03_kiyas_kos.sh`). Üretim dosyası yoktu: çelik ağırlığı motorun ortalamasından.
KT3 = BURADA.parent / "2026-10-09_kor_test_3" / "sonuc"
k3 = json.loads((KT3 / "KT03_kiyas.json").read_text(encoding="utf-8"))
k3_n, k3_kor, k3_duz = k3["ozet"]["kor_b"]["gercek_satir"], k3["ozet"]["kor_b"]["ayni"], k3["ozet"]["duz_b"]["ayni"]
k3_s, k3_c = k3["siniflar"], k3["celik"]
k3_birim = lambda ad: next(b for b in k3["birimler"] if b["ad"] == ad)
# kural eksikleri konu konu (her konunun gerçek listedeki satırları); sorular "Açık sorular"da (10)
K3_KONU = {"panel_cati": ["Alın sacı (veranda ve sundurma)", "Özel büküm saçak sacı", "Dış cephe Boardex", "Veranda ve sundurma tavanı (Boardex)", "Metal dere",
                          "Dere kapağı", "Dere iniş aparatı", "Dere iniş borusu", "Açık dirsek", "Kapalı dirsek", "İniş kelepçesi", "Dere kelepçesi"],
           "cati_paneli": ["Çatı panelleri (1,2 ve 0,8)"], "cikis_kapagi": ["Çatı çıkış kapağı"],
           "baca_ici": ["Baca borusu", "Baca T'si", "Baca kör tapa", "Baca maşonu", "Baca şapkası"], "taharet": ["Taharet musluğu 20 mm"]}
k3_kural = {b["ad"]: len(b["gercek_satirlar"]) for b in k3["birimler"] if b["sinif"] == "kural"}
k3_konu = {konu: sum(k3_kural[a] for a in adlar) for konu, adlar in K3_KONU.items() if all(a in k3_kural for a in adlar)}
k3_cati = [k3_birim("Çatı makas panelleri (1,2 ve 0,8)"), k3_birim("Çatı panelleri (1,2 ve 0,8)")]
k3_cati_kg = (sum(b["gercek_kg"] for b in k3_cati), sum(b["duz_b_kg"] for b in k3_cati))
k3_yuzde = round(100 * (k3_c["gercek"]["kg"] - k3_c["duz_b"]["kg"]) / k3_c["gercek"]["kg"])
assert not k3["denetim_sorunlari"] and (k3_n, k3_kor, k3_duz) == (102, 46, 48) and k3_s == {"girdi": 2, "kural": 21, "karar": 18, "elle": 9, "pafta": 6} \
    and k3["bizim_hatamiz"] == 23 and set(k3_kural) == {a for adlar in K3_KONU.values() for a in adlar} and list(k3_konu.values()) == [12, 2, 1, 5, 1] \
    and [b["ad"] for b in k3["birimler"] if b["sinif"] == "girdi"] == [k3_cati[0]["ad"]] and k3_cati[0]["duz_b_ayni"] and (k3_cati[0]["gercek"], k3_cati[0]["kor_b"]) == (34, 36) \
    and (k3["ozet"]["kor_a"]["ayni"], k3["ozet"]["sablon_b"]["ayni"], k3["ozet"]["ne_olur_b"]["ayni"]) == (45, 54, 55) \
    and (k3_c["gercek"]["kg"], round(k3_c["duz_b"]["kg"]), k3_yuzde) == (2847, 2556, 10) and k3_c["kor_b"]["kg"] == k3_c["duz_b"]["kg"] \
    and (k3_cati_kg[0], round(k3_cati_kg[1])) == (979, 746), \
    "belge: KT-03'te 102 satırın kör 46'sı, düzeltilmiş 48'i aynı; sınıflar 2/21/18/9/6 (girdi: makas 36 → 34); kural eksikleri 12/2/1/5/1; A 45, Eylül 2026 54, " \
    "ne olur 55; çelik 2847 / 2556 kg (yüzde 10), çatının çeliği 979 / 746 kg diyor"
# KT-03, Lokman'ın 10 Ekim 2026 cevaplarından sonra (kural seti 0.18; `kt03_cevaplar_kos.sh`): düzeltilmiş tanımdan iki liste
k3c = json.loads((KT3 / "KT03_cevaplar_kiyas.json").read_text(encoding="utf-8"))
k3c_k = k3c["kalan_siniflar"]
k3c_b, k3c_a = k3c["ozet"]["duz_b"]["ayni"], k3c["ozet"]["duz_a"]["ayni"]
k3c_birim = lambda ad: next(b for b in k3c["birimler"] if b["ad"] == ad)
# panel çatının kenarları konusunda (12 satır) cevaplardan sonra tutanlar; tutmayan tek satır dere kelepçesi (listede 110, formülsüz)
k3c_panel = sum(len(b["gercek_satirlar"]) for b in k3c["birimler"] if b["ad"] in K3_KONU["panel_cati"] and b["duz_b_ayni"])
k3c_ins = k3c_birim("Dere iniş borusu")
k3c_cp = k3c_birim("Çatı panelleri (1,2 ve 0,8)")
# 0.19 (Lokman, 10 Ekim 11:39): kısa derede tek iniş, alçak çatının üstüne düşen köşede iniş (yalnız tek inişli küçük çatıda yok). KT-03'te iniş yerleri paftadaki gibi.
# İniş noktaları girdiye yazılmaz (yalnız köşe adedi); dağılım genel motorla, düzeltilmiş tanımdan yeniden hesaplanır
import sys as _sys
_sys.path.insert(0, str(BURADA.parent / "2026-10-06_kor_test"))
import cati_genel as _cati_genel, ciz_genel as _ciz_genel   # noqa: E402
_t3 = json.loads((BURADA.parent / "2026-10-09_kor_test_3" / "tanim" / "KT03_duzeltilmis.json").read_text(encoding="utf-8"))
_c3 = _cati_genel.cati_kur(_t3["cati"], K)
k3c_inis, k3c_inis_sayim = _ciz_genel.inis_kurali(_c3, K, _t3["cati"].get("sacak", 30))
def _inis_catisi(p):
    for h in _c3["dere"]["hatlar"]:
        uclar = [h["p"], h["q"], ((h["p"][0] + h["q"][0]) / 2, (h["p"][1] + h["q"][1]) / 2)]
        if any(math.hypot(p[0] - u[0], p[1] - u[1]) < 1.0 for u in uclar):
            ad = h.get("duzlem") or h["duzlemler"][0]
            return ad if ad in ("veranda", "sundurma") else "ana çatı"
k3c_dagilim = {ad: sum(1 for x in k3c_inis if _inis_catisi(x) == ad) for ad in ("ana çatı", "veranda", "sundurma")}
k3c_g = json.loads((KT3 / "KT03_cevaplar_B_girdi.json").read_text(encoding="utf-8"))["cati"]
assert len(k3c_inis) == 11 and k3c_inis_sayim == {"kisa_dere": 1, "alcak": 1} and k3c_dagilim == {"ana çatı": 8, "veranda": 2, "sundurma": 1} \
    and k3c_g["kose_adedi"] == 10, "belge: KT-03'te 0.19 ile 11 iniş (10 köşe + 1 orta): ana çatı 8, veranda 2, sundurma 1 (paftadaki gibi) diyor"
assert not k3c["denetim_sorunlari"] and (k3c["ozet"]["duz_b"]["gercek_satir"], k3c_b, k3c_a) == (102, 59, 58) and k3c_k == {"girdi": 0, "kural": 2, "karar": 25, "elle": 10, "pafta": 6} \
    and k3c_panel == 11 and (k3c_birim("Dere kelepçesi")["duz_b"], k3c_birim("Dere kelepçesi")["gercek"]) == (104, 110) and k3c_ins["duz_b"] == k3c_ins["gercek"] == 11 \
    and (k3c_cp["duz_b"], k3c_cp["gercek"], len(k3c_cp["gercek_satirlar"])) == (4, 17, 2) and k3c_cp["kalan"].startswith("kural:") \
    and k3c_birim("Taharet musluğu 20 mm")["duz_b"] is None, \
    "belge: KT-03'te cevaplardan sonra 59 / 102 (A 58); kalan kural 2 (çatı panelleri), karar 25, elle 10, pafta 6; panel çatı konusunun 12 satırından 11'i tutuyor " \
    "(dere kelepçesi 104 / 110); iniş 11; taharet satırı yok (vitrifiye alıcıya ait) diyor"
# Ç8801 (katalog modeli; kural kitabının yeni bir modelde sınanması, 10 Ekim 2026; `deneme/2026-10-10_c8801/c8801_kos.sh`; gerçek liste yok).
# Çatı: Lokman 14:46, katalogdaki model "2. versiyon"; üç çatı da olur: katalog (C8801), K (doğu ucu kırma), L (ilk varsayım) saklanıyor.
C88 = BURADA.parent / "2026-10-10_c8801"
c88 = json.loads((C88 / "sonuc" / "C8801_yukleme.json").read_text(encoding="utf-8"))
c88_g = json.loads((C88 / "sonuc" / "C8801_girdi.json").read_text(encoding="utf-8"))
c88_t = json.loads((C88 / "tanim" / "C8801.json").read_text(encoding="utf-8"))
c88_tk = [s for s in c88["satirlar"] if s["kalem"] == "Tek kat panel"]
c88_kg = satir(c88, "Toplam (adedi ve kg'ı bilinenler)")["kg"]
c88_dere = c88_g["cati"]["dere"]
c88_v = {k: (json.loads((C88 / "sonuc" / f"{k}_yukleme.json").read_text(encoding="utf-8")), json.loads((C88 / "sonuc" / f"{k}_girdi.json").read_text(encoding="utf-8")))
         for k in ("C8801", "C8801K", "C8801L")}


def c88_ozet(k):
    """(tek kat panel adedi, panel dizilimi, dere m, dere parça, iniş, mahya, ters mahya, alın kapama, dış cephe Boardex)"""
    L, G = c88_v[k]
    tk = [s for s in L["satirlar"] if s["kalem"] == "Tek kat panel"]
    return (sum(s["adet"] for s in tk), " + ".join(f'{s["adet"]} × {s["boyut"].split(" ·")[0]}' for s in tk), G["cati"]["dere"]["boy_m"], adet(L, "Metal dere"),
            adet(L, "Dere iniş borusu"), adet(L, "Metal kiremit mahyası"), adet(L, "Ters mahya"), adet(L, "Alın kapama"), adet(L, "Dış cephe Boardex"))


assert len(c88["satirlar"]) == 93 and round(c88_kg) == 2332 and [(s["boyut"].split(" ·")[0], s["adet"]) for s in c88_tk] == [("L 3740", 21), ("L 2480", 10)] \
    and sorted({d["egim"] for d in c88_t["cati"]["duzlemler"]}) == [0.33] and c88_g["veranda_m2"]["catisiz"] == ["Veranda"] \
    and not any(s["kalem"].startswith("Veranda tavanı") for s in c88["satirlar"]) and c88_g["celik"]["cati"]["oturum_m2"] == 74.34 \
    and (adet(c88, "Dere iniş borusu"), adet(c88, "Dere kapağı"), adet(c88, "Metal dere"), c88_dere["boy_m"]) == (6, 6, 6, 21.48) \
    and (adet(c88, "Dış cephe Boardex"), adet(c88, "Çatı şiltesi 80 mm"), adet(c88, "Ters mahya")) == (37, 9, 3) \
    and [c88_ozet(k)[0] for k in c88_v] == [31, 32, 36] and [c88_ozet(k)[2] for k in c88_v] == [21.48, 28.48, 23.88] \
    and [c88_ozet(k)[4] for k in c88_v] == [6, 7, 7] and len({round(satir(L, "Toplam (adedi ve kg'ı bilinenler)")["kg"]) for L, _ in c88_v.values()}) == 1, \
    "belge: Ç8801'de (katalog çatısı) 93 satır, çelik 2332 kg, tek kat panel 21 × L 3740 + 10 × L 2480, bütün yüzler %33, veranda çatısız (tavanı yok, " \
    "çatı oturumu 74,34), dere 21,48 m (6), iniş 6, kapak 6, dış cephe Boardex 37, şilte 9, ters mahya 3; varyantlarda panel 32 ve 36, dere 28,48 ve 23,88, " \
    "iniş 7 ve 7, çelik üçünde aynı diyor"
kt_fark = KT["fark_turleri"]
# adedi 03:46'daki düzeltilmiş listeden farklı olan satırlar: kararla değişenler ve yalnız elektrik sayıları paftadan alındığı için değişenler
kt_kararla, kt_paftadan = KT["degisen"]["karar"], KT["degisen"]["pafta"]
# 03:46'da tutmayıp şimdi tutan satırlar: kararlardan (ayrıca iniş kuralından) ve pafta sayımından (`kararlar_kiyas.py` sayar). 0.17'ye kadar 03:46'da tutan
# hiçbir satır bozulmamıştı; 10 Ekim kararıyla (müştemilatın deresi) üç satır bozuldu: dere, dere kapağı, dere kelepçesi (iniş satırları 03:46'da da tutmuyordu).
kt_kazanc = KT["yeni_tutan"]
kt_bozulan = [b["ad"] for b in KT["birimler"] if b["duzeltilmis_ayni"] and not b["b_ayni"]]
assert kt_kazanc["toplam"] - kt_kazanc["bozulan"] == kt_b - KT["onceki"]["duzeltilmis"] and kt_bozulan == ["Metal dere", "Dere kapağı", "Dere kelepçesi"] \
    and kt_kazanc["bozulan"] == 3 and not kt_kazanc["inis"] and kt_kararla + kt_paftadan == KT["karardan_degisen_satir"] and all(b in kt_mus for b in KT["birimler"] if b["ad"] in kt_bozulan), \
    "belge: 03:46'da tutan satırlardan yalnız dere, dere kapağı ve dere kelepçesi bozuldu (10 Ekim kararı: müştemilatın deresi); iniş satırlarından tutan kalmadı diyor"
# trapez vida (5,5 × 25): parça C profiller sayılmıyor (Lokman, 8 Ekim 07:23: "göz ardı et"); sayılsaydı ne olurdu
tv_s = satir(baz, "Trapez vida (5,5 × 25)")
c_profil_adedi = sum(s["adet"] for s in baz["satirlar"] if s["kalem"] == "Boy C profil")
assert [(s["boyut"], s["adet"]) for s in baz["satirlar"] if s["kalem"] == "Boy C profil"] == [("80 × 45 × 0,8", 3), ("80 × 45 × 1,2", 3)], "belge: Boy C profil 0,8'den 3 ve 1,2'den 3 diyor"
TV_CARPAN, TV_KAT = K["vida"]["deger"]["trapez_5_5x25"]["celik_panel"], K["vida"]["deger"]["trapez_yuvarlama"]
tv_c_ile = tv_s["olcu"] + c_profil_adedi * TV_CARPAN
tv_c_ile_adet = math.ceil(tv_c_ile / TV_KAT - 1e-9) * TV_KAT
assert K["vida"]["deger"]["trapez_5_5x25_c_profil_dahil"] is False and c_profil_adedi == 6 and "parça C profiller hariç" in tv_s["formul"] \
    and (tv_s["olcu"], tv_s["adet"], tv_c_ile, tv_c_ile_adet) == (984, 1000, 1044, 1250), "belge: trapez vidada parça C profiller sayılmıyor: 984 → 1000 (sayılsa 1044 → 1250) diyor"
assert sum(kt_fark.values()) == kt_n - kt_b
yb_vida = adet(yb, "Trapez vida (5,5 × 25)")
vt_s = satir(baz, "Veranda tavanı (Boardex)")
kosegen = (uzun ** 2 + kisa ** 2) ** 0.5
IN_KR = K["inis"]["deger"]
SK_KR = K["sandvic_kapama"]["deger"]
PK_KR = K["panel_cati_kenarlari"]["deger"]
assert (PK_KR["dere"], PK_KR["sacak"], PK_KR["yan"], PK_KR["acik_alan"], PK_KR["ek_yapi"]) == (True, {"ad": "Özel büküm saçak sacı", "parca_boyu_m": 2.5, "bindirme_m": 0.2}, {"ad": "Sundurma kapama", "parca_boyu_m": 2.5, "bindirme_m": 0.2}, {"kenar_boardex": False, "tavan": "cati_plani"}, {"kenar_boardex": "yalniz_alt"}) and K["panel_cati_kenarlari"]["durum"] == "lokman", \
    "belge: tek eğimli çatı panelli çatıda saçakta dere ve özel büküm saçak sacı, yanlarda sundurma kapama (L 2500, 20 cm); açık alanda Boardex şeridi yok, tavan çatının planıyla; ek yapıda yalnız alt diyor"
assert K["cati_cikis_kapagi"]["deger"] == {"listede": False} and K["baca_ici"]["deger"] == {"listede": False} and K["taharet_muslugu"]["deger"] == {"islak_hacim_basina": 4, "kosul": "vitrifiye_dahil"}, \
    "belge: çatı çıkış kapağı ve bacanın içi listede yok; taharet musluğu vitrifiye dahilse ıslak hacim başına 4 diyor"
assert K["bindirme_m"]["mahya"]["deger"] == K["bindirme_m"]["sacak_saci"]["deger"] == K["bindirme_m"]["alin_saci"]["deger"] == K["bindirme_m"]["dere"]["deger"] == 0.2, "belge: bindirmeler 20 cm diyor"
assert K["celik_cati_yontemi"]["deger"] == "panel" and K["veranda_tavani"]["deger"] == {"celik": "boardex", "prefabrik": "yesil_alcipan"} and not K["duvar_izolasyonu"]["deger"]["listede"], \
    "belge: çelikte yöntem A, veranda tavanı Boardex, duvar izolasyonu listede değil diyor"
assert K["vida"]["deger"]["trapez_5_5x25"] == {"asik": 0, "omega_375": 0, "omega_240": 0, "celik_panel": 10, "kosebent": 6} and K["vida"]["deger"]["alcipan_vidasi_levha_basina"] == 40, \
    "belge: trapez vida (5,5 × 25) yalnız çelik panel × 10 + köşebent × 6; alçıpan vidası levha başına 40 diyor"
assert (IN_KR["olcu"], IN_KR["orta_inis_esigi_m"], IN_KR["cephe_basina_en_cok_orta"], K["inis"]["durum"]) == ("dere", 9.0, 1, "lokman") and (SK_KR["parca_boyu_m"], SK_KR["bindirme_m"], K["sandvic_kapama"]["durum"]) == (2.5, 0.2, "lokman"), \
    "belge: iniş eşiği 9 m dere boyu ve sandviç panel kapaması (L 2500, 20 cm bindirme) onaylandı diyor"
assert K["cati_mudahale_kapagi"]["deger"]["standart_pakette"] and adet(baz, "Acil müdahale kapağı") == 1 and K["ters_mahya_kenar_kutusu"]["deger"]["varsayilan"] \
    and K["kablo_en_uzak_mesafe"]["deger"] == "sigortadan" and gb["elektrik_en_uzak_m"] < kosegen, "belge: acil müdahale kapağı standart, kenar kutusu varsayılan, kablo sigortadan diyor"
assert (adet(baz, "NYM kablo (3 × 2,5)"), adet(baz, "NYM kablo (2 × 1,5)")) == (120, 96) and adet(baz, "Tavan alçıpan yeşil") == 2 and vt_s["adet"] == 7 and yb_vida == 1000, \
    "belge: Ç8201'de NYM 120 ve 96 m, yeşil tavan 2, veranda tavanı Boardex 7; yöntem B'de trapez vida 1000 diyor"
assert (kars_ayni, kars_top) == (72, 116), "belge: üç gerçek listeyle karşılaştırma 72 / 116 diyor"


PAY = {mm: pay_siniri(mm) for mm in (taban_mm, S0346["boy_mm"], boy_mm)}      # L 4320, L 4325, L 4330
assert PAY == {4320: 7.8, 4325: 12.8, 4330: 17.8} and uz["taban_pay_siniri_mm"] == PAY[taban_mm], "belge: adet L 4320'de kesim payı 7,8 mm'ye, L 4325'te 12,8 mm'ye, L 4330'da 17,8 mm'ye kadar aynı kalıyor diyor"


def dizilim_satiri(metin: str) -> list[str]:
    """Dizilim tablosundan bir satırın hücreleri (Çatı, Kaplama, Kapatır, Panel boyu, Adet, Taban boyla, …)."""
    satir_ = next(x for x in dizilim_tablo.split("\n") if metin in x)
    return [h.strip() for h in satir_.strip().strip("|").split("|")]


d87, d110 = dizilim_satiri("87 cm kapatan ürün"), dizilim_satiri("110 cm kapatan ürün")
assert (d87[3], d87[4].split(" ")[0], d87[5]) == ("L 4350", "28", "29 (L 4320)") and (d110[3], d110[4].split(" ")[0], d110[5]) == ("L 4320", "26", "uzatma adedi düşürmüyor"), \
    "belge: 87 cm'lik üründe boy L 4350'ye uzuyor (29 → 28), 110 cm'likte uzamıyor (L 4320, 26) diyor"


assert BAGIMSIZ["boylar_mm"] == (boy_mm, dz_t["uzatma"]["boy_mm"], dz_k["uzatma"]["boy_mm"], int(d87[3].split(" ")[1]), int(d110[3].split(" ")[1])) \
    and BAGIMSIZ["adetler"] == (dz["adet"], dz_t["adet"], dz_k["adet"], int(d87[4].split(" ")[0]), int(d110[4].split(" ")[0])) \
    and BAGIMSIZ["pay_siniri_mm"] == {taban_mm: PAY[taban_mm], boy_mm: PAY[boy_mm]} and BAGIMSIZ["en_az"] == dz["adet"] and BAGIMSIZ["alan_alt_siniri"] == dz["alan_alt_siniri"], \
    "belge: bağımsız denetimin bulduğu boylar, adetler ve kesim payı sınırları buradaki hesapla aynı diyor"
BAGIMSIZ_7EKIM = (
    f" 7 Ekim'de, yuvarlama ve pay koşulundan sonra yeniden: ayrı bir oturum bu koda ve çıktılara bakmadan beş durumu altı panel boyunda (L {S0346['taban_mm']}–L 4350) ve iki kesim payında "
    f"({tr(kesim_mm)} mm, 1 cm) hesapladı; {BAGIMSIZ['hucre']} adedin hepsi, kuralın seçtiği boylar (" + " · ".join(tr(x / 1000, 3) for x in BAGIMSIZ["boylar_mm"]) + " m) ve adetler ("
    + " · ".join(str(x) for x in BAGIMSIZ["adetler"]) + f") aynı çıktı. Tek kat panelde adedin aynı kaldığı en büyük kesim payı L {taban_mm}'de {tr(PAY[taban_mm], 1)} mm, "
    f"L {boy_mm}'da {tr(PAY[boy_mm], 1)} mm bulundu. L {boy_mm}'da {BAGIMSIZ['en_az']}'in bu şerit dizilimi ve kesim kuralı için en az olduğu gösterildi "
    f"(hiçbir ikilisi aynı panele giremeyen {BAGIMSIZ['en_az']} parça var; alan olarak alt sınır {BAGIMSIZ['alan_alt_siniri']}).")
BAGIMSIZ_KISA = " Bağımsız hesap 7 Ekim'de yenilendi: beş durumda aynı boylar ve adetler (yukarıda, \"Sağlama\")."
assert acilim_adedi(taban_mm + 20, kesim_mm, 0.87, True) == int(d87[4].split(" ")[0]) < acilim_adedi(taban_mm + 20, 10.0, 0.87, True), \
    "belge: 87 cm'lik üründe L 4340 ile de 28 çıkıyor ama 1 cm kesim payıyla 29 gerekiyor diyor"
assert adet(baz, "Dere iniş borusu") == 6 and adet(baz, "Metal kiremit mahyası") == 11, "belge: Ç8201'de iniş yine 6, mahya yine 11 diyor"


def aralik(den: dict) -> str:
    a, b = min(den.values()), max(den.values())
    return str(a) if a == b else f"{a}–{b}"


def dizilim_okuma(ad: str, z: dict) -> str:
    """Bir kaplamanın dizilim sonucunu ve neye duyarlı olduğunu hesap çıktısından yazar."""
    den = z["baslangica_gore"]
    p = [f"{z['adet']} adet ({z['tam_boy']} tam boy + {z['kesilen']} kesilen)"]
    if z["en_az_adet"] < z["adet"]:
        p.append(f"en az paneli veren dizilimle {z['en_az_adet']} olurdu (altı başlangıçla {aralik(den)})")
    else:
        p.append("altı başlangıcın hepsinde aynı" if len(set(den.values())) == 1 else f"altı başlangıçla {aralik(den)}")
    if z["paysiz_adet"] != z["adet"] or z["bir_cm_payla_adet"] != z["adet"]:
        p.append(f"kesim payı sıfır alınırsa {z['paysiz_adet']}, 1 cm alınırsa {z['bir_cm_payla_adet']}")
    else:
        p.append("kesim payı sıfır da olsa 1 cm de olsa aynı")
    if z.get("uzatma") and z["uzatma"].get("neden") == "pay":
        p.append(f"panel boyu L {z['uzatma']['taban_boy_mm']} → L {z['uzatma']['boy_mm']} (pay kalsın diye: taban boyla da {z['uzatma']['taban_adet']} çıkıyor, "
                 f"ama kesim payı {tr(z['uzatma']['taban_pay_siniri_mm'], 1)} mm'yi geçerse {z['uzatma']['taban_saglamlik_adet']} gerekir)")
    elif z.get("uzatma"):
        p.append(f"panel boyu L {z['uzatma']['taban_boy_mm']} → L {z['uzatma']['boy_mm']} (taban boyla {z['uzatma']['taban_adet']} gerekiyordu)")
    elif z.get("uzun_panelle"):
        p.append(f"panel L {z['uzun_panelle']['boy_mm']} ve daha uzun olsaydı {z['uzun_panelle']['adet']}")
    if not z["artan_parca_karsi_yuzde"]:
        p.append("artan parça kullanılmıyor (desen ters gelir: mühendis, 4 Ekim 12:14)")
    return f"- **{ad}.** " + "; ".join(p) + "."


def onceki_kural(kapatma: float) -> int:
    """Açılımdan önceki kural: yüzey × 1,10 ÷ (panel boyu × kapatma genişliği)."""
    return math.ceil(gb["cati"]["yuzey_m2"] * 1.10 / (gb["cati"]["panel_boyu_m"] * kapatma) - 1e-9)


# Excel motorunun kaplama formülü (`motor_formul.py`): şablondaki kayıtlı örnek, mühendisin 10 × 10 m beşik çatısı ve Ç8201'in ölçüleri.
# Ç8201'de K10 kapalı kısmın uzun kenarı, K11 kısa kenar, K17 verandanın kısa kenarı.
mk_ornek, mk_besik = SABLON, BESIK_10
mk_c = motor_kaplama(uzun, kisa, gb["dis_olcu_m"][0] - uzun, "kirma")
assert mk_c["sac_boyu_mm"] == S0346["taban_mm"] == math.ceil(gereken_mm - 1e-6), "belge: motorun sac boyu eğimli boy + taşmayla (mm'ye yukarı, L 4315) aynı diyor"

# Montaj paftaları ile üç gerçek liste: listedeki ve hesaptaki sayılar karşılaştırma çıktılarından, paftadakiler PAFTA sabitinden.
_kars = {n: oku(f"ornek_{n}m2_karsilastirma.json")["karsilastirma"] for n in (62, 90, 105)}
_girdi = {n: json.loads((BURADA / f"ornek_{n}m2_girdi.json").read_text(encoding="utf-8")) for n in (62, 90, 105)}
omega = {n: _kars[n]["Tavan omegası (60'lık)"] for n in (62, 90, 105)}
asik = {n: _kars[n]["Aşık"] for n in (62, 90)}
inis_liste = {62: _girdi[62]["cati"]["inis_adedi_liste"], 90: _girdi[90]["cati"]["inis_adedi_liste"], 105: _girdi[105]["cati"]["inis_adedi"]}
inis_hesap = {n: _kars[n]["Dere iniş borusu"]["hesap"] for n in (62, 90)}
sandvic_kapama = secenek("sandvic_panel", "Sandviç panel kapaması")
assert all(omega[n]["liste"] == PAFTA["omega"][n][2] + 1 for n in (62, 90, 105)), "belge: tavan omegasında liste, paftadaki en az boydan bir fazla diyor"
assert inis_liste == {62: 7, 90: 7, 105: 10} and inis_hesap == {62: 6, 90: 6} and PAFTA["inis"][62] == inis_liste[62] and PAFTA["inis"][105] == inis_liste[105], \
    "belge: iniş sayısı 62 ve 105 m² projelerde paftadakiyle aynı; kural 62 ve 90'da 6 veriyor diyor"
assert K["panel_kapamasi"]["deger"]["sandvic_panel"] and sandvic_kapama["adet"] > 0, "belge: sandviç panel kapaması şimdilik kalıyor diyor"
assert k62["liste"] == 27 and k62["hesap"] == 28, "belge: 62 m² projede sandviç panel listede 27, hesapta 28 diyor"
assert _kars[90]["Çatı OSB"]["liste"] == 39 and _kars[90]["Metal kiremit"]["liste"] == 28 + 2, "belge: 90 m² projede çatı OSB'si ve metal kiremit adedi paftadakinin aynısı diyor"


def _parca(t):
    return f"{t[0]} parça, {tr(t[1], 1)} m; en az boy {t[2]}"


pafta_tablosu = "\n".join([
    f"| Çatı kaplaması | 62 m² (kırma, sandviç panel) | 27 adet L 3200 + 2 adet L 1000 | {k62['liste']} (+ 2 kısa) | {k62['hesap']} |",
    "| Çatı kaplaması | 105 m² (beşik, tek kat panel 87 cm) | 24 adet L 3000 + 30 adet L 2800 | 24 + 30 | karşılaştırmada yok |",
    f"| Çatı OSB | 90 m² (beşik) | 39 adet (244 × 122) | {_kars[90]['Çatı OSB']['liste']} | {_kars[90]['Çatı OSB']['hesap']} |",
    f"| Metal kiremit | 90 m² (beşik) | 28 adet L 3450 + 2 adet L 3000 | {_kars[90]['Metal kiremit']['liste']} | {_kars[90]['Metal kiremit']['hesap']} |",
    f"| Dere inişi | 62 m² | {PAFTA['inis'][62]} işaret | {inis_liste[62]} | {inis_hesap[62]} |",
    f"| Dere inişi | 90 m² | {PAFTA['inis'][90]} işaret | {inis_liste[90]} | {inis_hesap[90]} |",
    f"| Dere inişi | 105 m² | {PAFTA['inis'][105]} işaret | {inis_liste[105]} | listeden alındı |",
] + [f"| Tavan omegası | {n} m² | {_parca(PAFTA['omega'][n])} | {omega[n]['liste']} | {omega[n]['hesap']} |" for n in (62, 90, 105)]
  + [f"| Aşık | {n} m² | {_parca(PAFTA['asik'][n])} | {asik[n]['liste']} | {asik[n]['hesap']} |" for n in (62, 90)]
  + [f"| Aşık | 105 m² | {_parca(PAFTA['asik'][105])} | {PAFTA['asik_liste_105']} | karşılaştırmada yok |"])

D = f"""# Çelik yükleme listesi: yöntem ve taslak (3–10 Ekim 2026)

Son güncelleme: {A.zaman}. Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Deneme kodu: `deneme/2026-10-03_yukleme/`. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir. Buradaki tablolar ve sayılar hesap çıktılarından üretilir (`belge_uret.py`; tablolar `sonuc/tablolar.md`).

## Kaynaklar

1. **Lokman'ın söyledikleri.** 3 Ekim 13:27'de on bir soruya verdiği cevaplar (aşağıda), 4 Ekim 01:24'teki düzeltmesi (tavan ve çatı panelinin ağırlığı), 4 Ekim 01:42'deki düzeltmesi (baz kaplama; kırma çatıda kaplama adedinin çatı açılımından bulunması), 4 Ekim 15:18'de altı soruya, 16:18'de üç soruya ve 17:46'da iki soruya verdiği cevaplar, 7 Ekim 07:45'te kör testin on iki sorusuna verdiği cevaplar ile 08:02'deki beş düzeltmesi, 8 Ekim 00:45'te dokuz soruya ve 07:23'te üç soruya verdiği cevaplar, 9 Ekim 22:22'de ikinci kör testin dört sorusuna ve 22:44'te korkuluğun malzemesine verdiği cevaplar, 10 Ekim 10:18'de üçüncü kör testin yedi sorusuna verdiği cevaplar, 10:29'da gönderdiği beş fotoğraf (tek eğimli panel çatının nasıl bittiği), 10:37'de gönderdiği KT-01'in yapılmış halinin üç fotoğrafı ve 10:39'daki cevabı, 11:39'daki üç cevabı (hepsi aşağıda) ve önceki kurallar. Lokman'ın söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerlidir (15:18: en iyi bilgiyi kendisi verecek).
2. **Mühendisin cevapları.** PortatifEv'in inşaat mühendisi Ubeydullah'ın üç tur cevabı: 3 Ekim 14:50 sürümündeki yedi soruya (Lokman 3 Ekim 18:14'te iletti), 19:12 sürümündeki yedi soruya (Lokman 4 Ekim 01:24'te iletti) ve 4 Ekim 02:58 sürümündeki on iki soruya (Lokman 4 Ekim 12:14'te iletti). Üçü de aşağıda. Kurallarda durumu `muhendis`. İkinci turun iki cevabını (baz kaplama; kırma çatıda kaplama adedi) Lokman 01:42'de düzeltti. Üçüncü turun mesajında cevapların kimden olduğu yazmıyor; 11. cevaptaki anlatım mühendisin olduğu için on iki cevap da mühendisin sayıldı.
3. **Gerçek yükleme listeleri.** Lokman'ın bağladığı klasördeki çalışma kitapları. Üçü hesap sayfalarıyla okundu. Üçünde de çatı yöntem B ile (tavan omegası, aşık, saçak sacı) hazırlanmış: PortatifEv bugüne kadar çelikte de bu yöntemi uygulamış. Şimdi baz alınan yöntem A için karşılaştırılacak gerçek liste yok.
   - **90 m²**, beşik çatı, OSB üstü metal kiremit, karkas 80 mm (30 Eylül 2025).
   - **62 m²**, kırma çatı, sandviç panel, dış karkas 140 mm, verandalı (19 Eylül 2025). Ç8201'e en yakın örnek.
   - **105 m²**, beşik + cumba çatı, tek kat panel, dış karkas 140 mm (dosya tarihi 26 Kasım 2025; 11 Kasım tarihli önceki sürümüne de bakıldı).
   - **98,7 m²**, beşik + cumba çatı, sandviç panel, müştemilatlı (Eylül 2026). Kör testte kullanıldı (KT-01): bu belgedeki kurallarla kendi listemiz çıkarıldıktan sonra açıldı. O da yöntem B ile hazırlanmış. Aşağıda "Kör test" bölümü.
   - **90 m²** (ikinci kör test, KT-02), dört omuz çatı, sandviç panel, korkuluklu veranda ve girişte kendi çatısı olan açık sundurma (Ağustos 2026). Model montaj paftasından ve üretim dosyasından (rulo form makinesinin CSV'leri) kuruldu; liste, kendi listemiz donduruluncaya kadar açılmadı. Yöntem B. Aşağıda "Kör test: KT-02" bölümü.
   - **80 m²** (üçüncü kör test, KT-03), kanatlı kırma çatı, sandviç panel, tek eğimli panel çatılı veranda ve giriş sundurması, iki baca (Eylül 2026; yeni şablon). Üretim dosyası yoktu: model yalnız montaj paftasından kuruldu; liste, kendi listemiz donduruluncaya kadar açılmadı. Yöntem B. Aşağıda "Kör test: KT-03" bölümü.
4. **Excel hesaplama motoru** (`CTKBF V1.1`). Lokman, 13:27: "biz Excel'de hesaplama motoru kullanırken…". Sayfaları: müşteri talebi (girdiler), proje detayları, dış ve iç duvar tonajı, çatı tonajı, çatı kaplama malzemesi, pencere, malzemeler (formüller), notlar. Buradan çelik birim ağırlıkları ile listede elle yazılan kalemlerin formülleri alındı. Fiyatlar alınmadı.
5. **Mühendisin 10 × 10 m çatı metrajı** (aynı klasörde; beşik ve dört omuz, yöntem B). Kuralları sınamak için kullanıldı; fiyatlar alınmadı.
6. **Montaj paftaları** (aynı klasörlerde). Lokman'ın 4 Ekim 17:46 mesajı üzerine bulundu ve incelendi: 13 klasörde 84 PDF, proje başına bir ana DWG. Üç gerçek listenin projelerinin paftaları listelerle karşılaştırıldı (aşağıda, 17:46 bölümü). Ayrıntı: `docs/sartname/montaj_paftasi.md`.

Bayi, müşteri ve öteki personel adları alınmadı. Çalışma kitapları depoda değil; Lokman'ın Mac'inde.

## Lokman'ın cevapları (3 Ekim 13:27) ve uygulanışı

| # | Konu | Cevap (özet) | Uygulama |
|---|---|---|---|
| 1 | Çelik kg | Excel motorundaki gibi: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek. İleride Blender eklentisi (şimdi değil). | Duvar kg = duvar boyu × motorun birim ağırlığı. Dikme, kiriş ve makas motorun ortalamasıyla, "şimdilik" notuyla (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"). Tavan ve çatı paneli 100 m² için verilen ağırlıktan, alana oranla (ağırlıklar Lokman'ın 4 Ekim düzeltmesiyle). |
| 2 | Çatı örtüsü | "Çatı kaplaması" seçenektir: tek kat panel, sandviç panel, OSB + nem bariyeri + kiremit desen sac vb.; ötekiler zamanla verilecek. Hafif çelikte normalde makas arasına tavan paneli, üstüne çatı paneli konur; "ama biz prefabrikte kullandığımız metod olan tavan omegası, aşık, alın sacı ve saçak sacı yöntemini uyguluyoruz". İki varyant var; şimdilik çatı ve tavan panelli yöntem baz. | Çatı yöntemi A; kaplama seçenek. Baz pakette tek kat panel (Lokman, 4 Ekim 01:42); motordaki altı kaplama da hesaplanıyor. Lokman 7 Ekim 07:45'te kesinleştirdi: çelikte her çatı tipinde çatı ve tavan paneli; omega ve aşıklı yöntem yalnız prefabrikte (aşağıda). |
| 3 | Veranda kolonu ve kirişi | Kaplanıyor. Her projede sırt 80 mm (çelik karkas), genişlik 30 cm. Bu projede verandanın bütün çerçevesi böyle: kirişler yanlarda ve karşıda; altlarında 240 cm, kiriş gibi dikmeler. | Ç8201: dikme 3 × 240 cm, kiriş 12,38 m; kaplama çevreleri 0,76 ve 0,68 m. Çizime işlendi. |
| 4 | Yeşil alçıpan | Doğru: duvarda ıslak hacim; tavanda ıslak hacim ile veranda tavanı. | O gün hesap değişmedi. Lokman 7 Ekim 07:45'te veranda tavanını ayırdı: çelik yapıda her zaman Boardex, prefabrikte yeşil alçıpan (aşağıda). |
| 5 | Köşebent | Kural olarak bina m² ÷ 2,5; 50 ya da 70 olması çok önemli değil. | Yerini mühendisin plandan hesaplayan formülü aldı (18:14): Ç8201'de {adet(baz, "Köşebent")} (m² ÷ 2,5 ile 33'tü; veranda tavanı eklenmeden önce {YAYIMLANAN["kosebent"]}). m² ÷ 2,5 kurallarda yedek olarak duruyor. Lokman, 7 Ekim: köşebent önemli bir detay değil; mevcut kural uygulanır. |
| 6 | Dere inişi | Her köşeye bir; 10 metrelik cephenin ortasına bir daha (14 metrede üç tane konmaz); 82 m²'de toplam 6. | Kural kodda. Ç8201: 6; çatı planında işaretli. Mühendis: iniş plana bakarak yerleştirilir (18:14); elle yerleştirilirse o sayı kullanılır. Lokman, 7 Ekim 07:45: "her saçak köşesine ve çok uzun dere boyarında ortaya 1 tane daha"; eşik artık dere boyuyla ölçülüyor ({tr(K["inis"]["deger"]["orta_inis_esigi_m"])} m; 8 Ekim 00:45'te onaylandı). Ç8201'de yine {adet(baz, "Dere iniş borusu")}. |
| 7 | Bindirme, mahyalar | Saçak, mahya ve alın sacında bindirme hep 30 cm (fire dahil); örnek: "saçak sacı L:2800 ise cephe 10 metre ÷ 2,5". Ters mahya: cumbalı çatıda vadi. Özel mahya: ana bina ile veranda çatısının birleşimi. | O gün: mahya (L 2800) ÷ 2,5 → 11; yöntem B'de saçak ve alın sacı listelerde L 2500 olduğu için ÷ 2,2 (çıkarım); dere sayılmadı, 20 cm'de kaldı. **Lokman 7 Ekim 07:45'te değiştirdi:** "Bindirmeleri 20 cm yap 30 cm banada çok geldi". Şimdi mahya ÷ 2,6 → {adet(baz, "Metal kiremit mahyası")}; saçak ve alın sacı ÷ 2,3; dere ÷ 3,8. |
| 8 | Saçak altı | İki yöntem birlikte kullanılmaz; saçak sacı varsa Boardex kaplanmaz. Ç8201 Boardex kaplamalı, çatı ve tavan panelli. | Baz listede saçak sacı yok; saçaklar için Boardex var. Saçak yüzü de Boardex; saçak omegası yok (mühendis, 18:14). |
| 9 | İç duvarda OSB | İçlerde OSB yoksa mutfak dolabı ve TV ünitesi takılırken mukavemet sağlasın diye gönderilen ürün; "salonun bir odası ile mutfağın 1 odasının tüm yüzeyini hesapla". | Mühendisin cevabıyla (18:14): yalnız dolap ve TV ünitesi gelen duvarlar. Ç8201: {tr(ot["net_m2"], 1)} m² → {osb_s["adet"]} levha (önce bütün Yaşam Alanı: 42,5 m², 15 levha). Duvar seçimini mühendis doğruladı (4 Ekim). |
| 10 | İç kapı | Boşluk en 90, yükseklik 214; kasa sağda, solda, üstte 5'er cm; altta 5 cm şap ve 2–3 cm parke; kanat 200'e düşer. | Dört iç kapı da 90 × 214 (banyo dahil); kanat 200. Kanat eni 80: listelerdeki "80'lik kanat"tan ve 90 − 2 × 5'ten. |
| 11 | Vida, boya, elektrik, tesisat | Bütün paketlerde var; bayilerle paylaşılan katalog ve fiyat listelerinde de. Bayi kuralı olarak ele alınacak (örnek: bir bayi için çelikte standart ne, bir başkası için prefabrikte standart ne); canlıda bayi numaraları birincil anahtar, liste mesajı atana göre. | Dört grup varsayılan olarak listede; bayi kuralıyla kapatılır. |

## Mühendisin ilk cevapları (Lokman 3 Ekim 18:14'te iletti) ve uygulanışı

Sorular 14:50 sürümündeki yedi soruydu. "Denetim" sütunu, cevabın elimizdeki kaynaklarla karşılaştırmasıdır. Sonradan değişenler "Uygulama" sütununda belirtildi.

| # | Soru | Cevap | Denetim | Uygulama |
|---|---|---|---|---|
| 1 | Et kalınlığı neye göre seçiliyor? | Duvarların kg/m değerleri: 80 × 0,8 iç 13; 80 × 1,2 dış 20,33 ve iç 19,75; 140 × 0,8 dış 18,20 ve iç 12,06; 140 × 1,2 dış 29,04. "140x0,8 duvarı 80x1,2 duvarına göre daha hafif olduğunu görebiliriz." | Değerler motorun duvar tonajı sayfasındakilerle aynı. Seçim ölçütü cevapta yok. 12,06 tek bir projenin 80 × 0,8 iç duvarı; 13,00 iki projenin ortalaması. Motorun verisinde 140 × 0,8 dış duvar yalnız iki katlı iki projenin üst katında; tek katlı 140'lık örnekte (55 m²) dış duvar 1,2 mm. | Birim ağırlıklar değişmedi; iç duvar 80 × 0,8 için 13,00. Seçim ölçütü ikinci cevaplarla geldi (aşağıda): tek katta ve zemin katta 1,2 mm. |
| 2 | Tavan ve çatı panelinin ölçüsü, adedi, kg'ı? Saçak omegası gerekiyor mu? Saçak yüzü Boardex mi? | Motor çatıları dört grupta (beşik, beşik + cumba, beşik + 2 cumba, dört omuz) ortalama ağırlıkla hesaplıyor; çatıdaki Boardex kaplaması motorda henüz hesaplanmıyor. "10 m x 10 m (100 m2) bir binada tavan paneli koyduğumuzu düşünürsek (8 adet) tavan paneli ağırlığı 429,83 kg, çatı paneli (12 parça) koyduğumuzda 561,6 kg geliyor. Saçak omegası gerekmiyor. Saçak yüzü de boardex ile kaplanıyor." | 429,83 ve 561,6 okunan çalışma kitaplarında bulunamadı; mühendisin beyanı olarak kayıtlı. Hangi çatı tipi, saçak ve eğim için olduğu yazılmadı. Motorda "saçaklar için Boardex" satırı gerçekten 0. | kg ve adet çatının örttüğü oturum alanına oranlandı: o gün Ç8201'de tavan paneli 353 kg, çatı paneli 461 kg; çelik toplamı 1902 → 2716 kg. Ağırlıkları Lokman 4 Ekim'de düzeltti (aşağıda). Saçak omegası satırı kalktı. Saçak yüzü için Boardex teyitli. |
| 3 | Baz pakette hangi çatı kaplaması var? | Motordaki kaplamalar: OSB + membran + shingle; OSB + nem bariyeri + trapez sac; trapez sac; tek kat panel; sandviç panel; OSB + membran + metal kiremit. | Motorun seçenek listesi aynı. Baz paket cevapta yok. Motorun trapez sac ve metal kiremit adedi formülü hatalı görünüyor (aşağıda "Excel motoruyla ilgili gözlemler"). | Altı seçenek hesaplanıyor. Lokman'ın "OSB + nem bariyeri + kiremit desen sac"ı motorun "OSB + membran + metal kiremit"iyle eşlendi (motor o seçenekte nem bariyeri hesaplıyor, membran hesaplamıyor). Baz paket: mühendis ikinci cevaplarda sandviç panel yazdı; Lokman tek kat panel diye düzeltti (4 Ekim 01:42). |
| 4 | OSB takviyesi bütün oda mı, yalnız o duvarlar mı? | "Bütün oda değil sadece dolap ve TV ünitesi gelen duvar metrajı alınır." | Gerçek listelerdeki alanlar (35 ve 39 m²) bütün odadan (72 ve 112 m²) küçük: cevapla aynı yönde. | Modelin tanımına dolap ve TV duvarları yazılır. Ç8201'de katalog görselinden üç duvar: {"; ".join(f"{x['duvar_adi']} {tr(x['boy_m'], 2)} m ({x['neden']})" for x in ot["duvarlar"])}. Net {tr(ot["net_m2"], 1)} m² → {osb_s["adet"]} levha. Duvar seçimini mühendis ikinci cevaplarda doğruladı. |
| 5 | Köşebent: m² ÷ 2,5 gerçek listelerin yarısını veriyor. | "Köşebent hesabı bina içerisinde bulunan bütün odaların tavan çevresi uzunluğu ile bütün oda iç köşe uzunlukları (standart kat yüksekliğimiz 2,7 metre alınır) toplamının 2,5 metreye bölünmesiyle bulunur." | Motordaki formül aynı yapıda ama plansız: (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5. Üç gerçek listede iç köşe sayısı bilinmiyor (planları yok); aşağıdaki tablo. | Ç8201 (planından): ({tr(kb["tavan_cevresi_m"], 2)} + veranda tavanı {tr(kb["veranda_tavan_cevresi_m"], 2)} + {kb["ic_kose"]} × 2,7) ÷ 2,5 → {adet(baz, "Köşebent")}. Yalnız iç köşeler sayılır. Veranda tavanının çevresi üçüncü cevaplarla eklendi (önce {YAYIMLANAN["kosebent"]}). |
| 6 | İniş sayısı iki listede kuraldan bir fazla. | "Dere inişi plana bakarak yerleştirilmesi doğru olur. Normalde düz bir saçakta ortalama 5 metrede bir dere inişi yazılır." | Mühendisin 10 × 10 m metrajında dört omuz çatıda 8, beşik çatıda 6 iniş var: Lokman'ın kuralı ikisini de veriyor. Motorun formülü farklı (dere adedi ÷ 5 + 6). | Kural değişmedi (Ç8201: {adet(baz, "Dere iniş borusu")}). Tanımda iniş yerleri elle verilirse (`cati.inis_noktalari`) o sayı kullanılır. Listelerdeki 7'ler plana göre yerleşimle açıklanıyor. |
| 7 | Elektrik sayıları paftadan mı, oda başına kuraldan mı? | Oda başına kural; "%75 lik bir doğruluk payı olacağı düşünülerek" (aşağıda). | 105 m² listenin pafta sayımıyla sınandı (aşağıda): kural 41, sayım 48 parça. | Pafta sayımı varsa o; yoksa kural. Ç8201: duy {adet(baz, "Tijli duy")}, glop {adet(baz, "Yuvarlak glop")}, tekli anahtar {adet(baz, "Tekli anahtar")}, çiftli anahtar {adet(baz, "Çiftli anahtar")}, tekli priz {adet(baz, "Tekli priz")}, çiftli priz {adet(baz, "Çiftli priz")}, uydu prizi {adet(baz, "Uydu prizi")}, sigorta {adet(baz, "W otomat (sigorta)")}. Yaşam Alanı'nda salon ve mutfak kuralları birlikte uygulandı (mühendis ikinci cevaplarda doğruladı). |

### Elektrik kuralı (mühendis)

| Oda | Duy | Glop | Tekli anahtar | Çiftli anahtar | Tekli priz | Çiftli priz | Uydu prizi |
|---|---|---|---|---|---|---|---|
| Yatak odası | 1 | | 1 | | 3 | | |
| Banyo | | 1 | 1 | | 2 | | |
| Salon | 2 | | | 1 | 3 | 1 | 1 |
| Mutfak | 1 | | 1 | | 5 | 1 | |
| Hol | 1 | | 1 | | | | |
| Veranda | | 2 | | 1 | | | |

- Her duy ve glop için bir ampul.
- Bina başına (cevapta holün altında): 12'li sigorta kutusu 1, sigorta 9, besleme kablosu 5 m, zil 1, kaçak akım rölesi 1; salonda 25 m uydu kablosu.
- Buat kasa = anahtar + priz + oda sayısı.
- 3 × 2,5 kablo = sigorta adedi × sigortadan evin en uzak mesafesi + (tekli priz + 2 × çiftli priz) × 2. 2 × 1,5 kablo = sigorta adedi × en uzak mesafe + (tekli anahtar + 2 × çiftli anahtar) × 2.
- Okuma: cevaptaki "anahtar" tekli anahtar, "priz" tekli priz sayıldı. "En uzak mesafe" o gün motordaki gibi kapalı kısmın köşegeni alınmıştı (Ç8201: {tr((uzun ** 2 + kisa ** 2) ** 0.5, 2)} m). Lokman 7 Ekim 07:45'te kuralı söyledi: sigorta × sigortadan en uzak mesafe. Sigorta kutusu, tanımda yeri yazmıyorsa giriş kapısında sayılır; mesafe oradan kapalı kısmın en uzak köşesine ölçülür (Ç8201: {tr(gb["elektrik_en_uzak_m"], 2)} m). Motor 3 × 2,5 kabloda uydu prizini de sayıyor, hesap öyle yapıldı (fark 2 m). Buat için oda sayısı planın mahal sayısı alındı (Ç8201: {gb["oda_sayisi"]}). Mühendis üçüncü cevaplarda ikisini de teyit etti: "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli."

Ç8201'de oda oda:

{elektrik_oda}

Kuralın sınaması: 105 m² gerçek listede pafta sayımı var. O listenin odalarına kural uygulanınca ("oda" yatak odası sayıldı; veranda bilgisi yok):

{elektrik_sinama}

Toplamda kural sayımın %85'ini veriyor; kalem kalem farklar büyük (çiftli anahtar 1 / 5, glop 2 / 4). Bu, mühendisin söylediği %75'lik doğruluk payıyla uyumlu. Tek liste; kanıt sayılmaz.

### Köşebent kuralının gerçek listelerle karşılaştırması

{kosebent}

Listelerdeki adetler, her odada ortalama 6–7 iç köşe varsa formülle çıkar. Salon, mutfak ve holün tek mahal olduğu planlarda bu olabilir; planlar elde olmadığı için sınanamadı. Ç8201'in planı sade: beş mahal, {kb["ic_kose"]} iç köşe. Veranda tavanının çevresi (üçüncü cevaplar) örneklerde bilinmediği için bu tabloya eklenmedi; verandalı projede eklenince fark azalır.

## Lokman'ın düzeltmesi ve mühendisin ikinci cevapları (4 Ekim 01:24) ve uygulanışı

**Düzeltme (Lokman).** 100 m² için "Tavan paneli ağırlık: 354,84 kg · Çatı paneli ağırlık: 440,32 kg"; "yine 82 m² ye oranlama yapabilirsin". Önceki değerler 429,83 ve 561,6 kg'dı. Ç8201'de (oturum {tr(oturum, 2)} m²) tavan paneli 353 → {tr(tp["kg"])} kg, çatı paneli 461 → {tr(cp["kg"])} kg; çelik toplamı 2716 → {tr(kg(baz, TOPLAM))} kg. Oranlama böylece Lokman'ın onayıyla. Adetler (100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]}) mühendisin ilk cevabından; düzeltmede adet verilmedi.

Sorular 19:12 sürümündeki yedi soruydu. 1. ve 6. cevabı Lokman 01:42'de düzeltti; öteki beşi geçerli.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Baz pakette altı seçenekten hangi çatı kaplaması var? | "Baz paket sandviç panel olarak al." | **Lokman düzeltti (01:42):** baz kaplama tek kat panel. Sandviç panel öteki dört kaplamayla birlikte seçenek olarak hesaplanıyor. |
| 2 | Tek katta dış 140'lık duvarın et kalınlığı 0,8 mi, 1,2 mi? | Tek katlı binada zemin kattaki çelik 140x45x12 ya da 80x45x12. İki katlı binada zemin kat yine böyle; 1. kat 140x45x0,8 ya da 80x45x0,8. İki katlıda "1. Katta büyük pencereler varsa mesela 200 cm ve daha geniş pencere varsa ozaman o duvarı 1,2 mm et kalınlığında alırız. Genelde 1. Katta 1 veya 2 adet duvar bu şekilde 1,2 mm et kalınlığı olacak şekilde tasarlanıyor." | Okuma: cevaptaki "12 mm" ve "8 mm", 1,2 ve 0,8 mm'dir. Tek katta ve zemin katta dış ve iç duvarlar 1,2 mm; üst katta 0,8 mm. Dış 140 seçeneği: dış 140 × 1,2 ve iç 80 × 1,2 → çelik {tr(kg(d140, TOPLAM))} kg, baz paketten {tr(kg(d140, TOPLAM) - kg(baz, TOPLAM))} kg ağır (3 Ekim'de 0,8 mm varsayılmış, daha hafif çıkmıştı). Üst katta geniş pencereli duvar kuralı kayıtlı; çift kat modeli gelince uygulanacak. 2025 tarihli iki tek katlı listede dış 140'lık duvarların çoğu 0,8 mm'di: kuralla uyuşmuyor. Mühendis üçüncü cevaplarda kuralı yineledi: tek katta 1,2 mm. |
| 3 | OSB takviyesi için seçilen üç duvar doğru mu? | "Evet doğru yeri almışsın. Ancak bunun yeri en doğru şekilde genel mimari planda mutfak tezgahı ve TV ünitesi yeri gösterilirse o kısımlar alınarak bulunabilir." | Seçim teyitli; satırdaki "teyit bekliyor" notu kalktı. Kural: yer, mimari plandaki tezgâh ve TV ünitesi yerinden alınır. "O kısımlar" sözü duvarın yalnız o bölümü diye de okunabiliyordu; üçüncü cevaplarla kapandı: "Duvarın tamamını al." |
| 4 | Yaşam Alanı'nda salon ve mutfak kuralları birlikte mi uygulanır? | "Evet doğru ikisini de uygulamamız gerekiyor. Çünkü mutfak eşyaları ayrı, salon eşyaları ayrı." | Teyitli; hesap değişmedi. |
| 5 | Makas ve kiriş ölçüsü gelene kadar çatı çeliği motorun ortalamasıyla; panel adedi alana oranlandı. | "Tamamdır." | Çatı çeliği motorun ortalamasıyla kalıyor (makas ölçüsü verilince değişecek; üçüncü cevaplar: "şimdilik Excel hesaplama motoruna uy"). Panel adedi alana oranlanıyor. |
| 6 | Kırma çatıda kaplama adedi yerleşimle mi bulunsun? | "Kırma çatıda çatı kaplama malzemesi hesabı sağlıklı olarak autocad üzerinden hesaplanarak yapılması daha sağlıklı. Ancak yüzeysel olarak çatı yüzey alanı m2 belirtilerek (%10 luk pay alınabilir) bu m2 olacak şekilde çatı kaplama malzemesi sipariş edilmeli şeklinde not edilebilir." | **Lokman düzeltti (01:42):** adet AutoCAD'e bırakılmaz; çatı açılımından ve dizilimden çıkar (aşağıda). %10 pay ve "sipariş bu m² olacak şekilde" notu listeden kalktı; pay kurallarda kayıt olarak duruyor. |
| 7 | Çatı müdahale kapağı ve mahya bandı listeye girsin mi? | "Çatı müdahale kapağı müşterinin talebine göre ekleniyor. Herhangi bir detay belirtilmemişse yani standart bir pakette çatı müdahale kapağı göndermiyoruz. Mahya bandını ekle." | Mahya bandı eklendi. O gün mahya uzunluğundan hesaplandı (Ç8201'de {onceki_bant} rulo); üçüncü cevaplardaki formülle {bant_s["adet"]} rulo. Çatı müdahale kapağı o gün standart listeden çıkarıldı (müşteri isterse eklenirdi). **Lokman 7 Ekim 07:45'te düzeltti:** acil müdahale kapağı her yapıya 1 adet, standart (aşağıda). |

## Lokman'ın ikinci düzeltmesi (4 Ekim 01:42): baz kaplama ve çatı açılımı

Lokman: "mühendis 2 cevapta hata yapmış onları düzeltmem gerekiyor".

1. **Baz kaplama.** "çatıda baz model Tek Kat panel olarak geçiyor". Uygulama: baz paketin çatı kaplaması tek kat panel; Ç8201'in tanımı ve listesi buna göre. Sandviç panel seçenek. O gün 87 cm kapatan panelle hesaplandı; güncel ürün {tr(KAP["tek_kat_panel_kapatma_m"] * 100)} cm kapatıyor (Lokman, 15:18).
2. **Kırma çatıda kaplama adedi.** "biz AutoCAD bulaşmak istemiyoruz"; "sen eğime göre 82 m² olduğu gibi çatıyı çizip sonra çatıyı açman lazım zarfı açar gibi yüzeye dizilimini bulmak için". "çatı formunun çapraz kesimleri diğer tarafa kullanabilirsin": sol taraftaki üçgende kullanılan panel sağ tarafa aynı açıyla; ön taraftaki yamuktan çıkan açılı kesilmiş parçalar arka taraftaki aynı biçimdeki açılı yere.

Uygulama (`deneme/2026-10-03_yukleme/cati_acilim.py`). Taşma mühendisin üçüncü cevaplarıyla (12:14) eklendi; dizilimin başladığı yer, kesim payı, yedek ve kapatma genişlikleri Lokman'ın 15:18 cevaplarıyla kesinleşti; panel boyunun uzatılması 16:18 cevabıyla kural oldu; panel boyu 7 Ekim 07:45 cevabıyla {YV_MM} mm'ye yukarı yuvarlanıyor (aşağıdaki bölümler):

- **Açılım.** Çatının dört yüzü gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ). Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Ç8201'de {tr(dz_H * 100, 1)} cm; saçaklar {tr(gb["cati"]["plan_m"][0] * 100)} ve {tr(gb["cati"]["plan_m"][1] * 100)} cm, mahya {tr((gb["cati"]["plan_m"][0] - gb["cati"]["plan_m"][1]) * 100)} cm. Kırma çizgisi açılımda dört yüzde de aynı açıdadır.
- **Dizilim.** Her yüz, saçağa dik, kaplamanın kapattığı genişlikte şeritlere bölünür. Dizilim her yüzde, dışarıdan bakışla sol köşeden başlar (Lokman, 4 Ekim 15:18: "her köşeden başlayacak gibi hesapla"); son şerit dar kalabilir. Mahyanın altındaki şeritler tam boydur; kırmaya gelen şeritler çapraz kesilir.
- **Kapatma genişliği.** Ürüne göre değişir (Lokman, 15:18). Güncel: tek kat panel {tr(KAP["tek_kat_panel_kapatma_m"] * 100)}, sandviç panel {tr(KAP["sandvic_panel_kapatma_m"] * 100)} (80 cm kapatanı da var), kiremit desen sac {tr(KAP["kiremit_kapatma_m"] * 100)}, trapez sac {tr(KAP["trapez_sac_kapatma_m"] * 100)} cm. 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Girdide `cati.kapatma_m` yazıyorsa o kullanılır.
- **Taşma** (mühendis, 4 Ekim 12:14). Kaplama saçaktan {tr(tasma_cm)} cm dışarı uzatılır. Panel boyunun tabanı = eğimli boy + {tr(tasma_cm)} cm, {YV_MM} mm'ye yukarı (Lokman, 7 Ekim 07:45: "yukarı yuvarla"; önce mm'ye yukarıydı): Ç8201'de {tr(gereken_mm, 1)} mm → L {taban_mm} (önce L {S0346["taban_mm"]}). Açılımda her parçanın boyu {tr(tasma_cm)} cm artar. Excel motorundaki sac boyu: eğimli boy + 0,05, mm'ye yukarı. Panel boyu gerçek listeden geliyorsa ona dokunulmaz; kısaysa taşma panelin yettiği kadar alınır (62 m² örnekte 3,8 cm).
- **Panel boyu uzatma** (Lokman, 4 Ekim 16:18; pay koşulu 7 Ekim'den beri taban boyda da aranır; 8 Ekim 00:45: boyda 3 cm'e kadar fark tolere edilebilir, hesap kapandı). Boy 1'er cm uzatılarak denenir, en çok 3 cm; adet düşüyorsa ya da taban boyda pay inceyse liste uzun boyu yazar. Taşma değişmez. Ç8201'de 4 Ekim'de L {S0346["taban_mm"]} → L {S0346["boy_mm"]} ({S1613["tek_kat"]} → {S0346["tek_kat"]} adet); şimdi taban L {taban_mm}, liste L {boy_mm} × {dz["adet"]}. Ayrıntı aşağıda, "Panel boyu uzatma kuralı" başlığında.
- **Artan parça.** Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır. Alt parça olduğu gibi kullanılır. Üst parça, düz ucu saçağa gelecek biçimde karşı yüze konur; orada aynı açılı yere oturur (ön yüzün sol kırması ↔ arka yüzün sol kırması, dışarıdan bakışla; planda çapraz köşeler). Parça ters yüz edilmez. Kiremit desen sacda artan parça kullanılmaz: desen ters gelir (mühendis, 4 Ekim 12:14).
- **Eşleme.** En uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır. İki parçanın birlikte istediği boy: uzun kenarlarının toplamı − bir şeritlik boy farkı + kesim payı.
- **Kesim payı** (Lokman onayladı, 4 Ekim 15:18). {tr(kesim_mm)} mm: çapraz kesimde iki parçanın arasına ve aynı panelden çıkan dikdörtgenlerin arasına.
- **Yedek ve bindirme.** Yedek panel eklenmez: kesim planı montajcıya verilir (Lokman, 15:18). Boy bindirmesi yok (panel tek boyda).
- **Öteki başlangıçlar.** Bilgi için beş başlangıç daha denenir: uzun yüzlerde sol köşeden, kısa yüzlerde ortadan · uzun yüzlerde ortadan, kısa yüzlerde sol köşeden · her yüzde ortadan · her yüzde sağ köşeden · karşılıklı yüzlerde planda aynı uçtan. En az paneli veren dizilim tabloda ayrı sütunda. "Ortadan": yüzün ortasına bir ek yeri gelir, şeritler iki yana eşit dağılır.

Ç8201, tek kat panel: **{kaplama_s["adet"]} adet L {boy_mm}** ({dz["tam_boy"]} tam boy + {dz["kesilen"]} kesilen: {dz["cift"]} kesimden ikişer parça çıkıyor, biri bir yüze, öteki karşı yüze; {kesim_notu}). Çizimler: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_acilim.png` (açılım; her parçada panel numarası) ve `C8201_cati_kesim.png` (her panelin kesimi); döküm `C8201_cati_acilim.json`; kesim ölçüleri `C8201_cati_kesim_olculeri.md`.

{dizilim_tablo}

Okuma:

- **Sağlama.** Aynı kural, bu koda bakmadan ayrıca hesaplandı (bağımsız denetim, 4 Ekim; 16:18 cevabından sonra yeniden). O günkü durumda (taban L {S0346["taban_mm"]}) panel boyu uzatma kuralı beş durumda uygulandı: 100 cm kapatma; 80 cm; 100 cm ve artan parça kullanılmadan; 87 cm; 110 cm ve artan parça kullanılmadan. Seçilen boylar 4,325 · 4,325 · 4,325 · 4,345 · 4,315 m, adetler {S0346["tek_kat"]} · {S0346["trapez"]} · {S0346["kiremit"]} · {S0346["d87"][1]} · {S0346["d110"][1]} (taban boyla {S1613["tek_kat"]} · {S1613["trapez"]} · {S1613["kiremit"]} · {S0346["d87"][2]} · {S0346["d110"][1]}): hepsi aynı çıktı. Tek kat panelde {S0346["tek_kat"]}'in bu şerit dizilimi için en az olduğu gösterildi (hiçbir ikilisi aynı panele sığmayan {S0346["tek_kat"]} parça var); adedin düştüğü en kısa boy 4,318 m. Önceki turlarda 90 adet (beş örnek × altı başlangıç × üç kesim payı) ve 16:13 sürümünün adetleri de aynı çıkmıştı.{BAGIMSIZ_7EKIM} Her paneldeki parçaların panele sığdığı, üst üste binmediği ve yüzdeki yerine tam oturduğu çokgenlerle sınanıyor (`cati_acilim_saglama.py`; rastgele 120 kırma çatıda, 1440 dizilimde sorun çıkmadı; uzatma kuralı 450 çatı ve kaplamada denendi: 4 Ekim kuralıyla {S0346["uzatilan"]}'ünde, şimdiki kuralla {SAGLAMA["uzatilan"]}'sinde boy uzadı, bunların {SAGLAMA["payli"]}'ünde pay koşulundan; kural bilerek bozulunca sınama yakalıyor). Çizim, ölçü tablosu ve sınama aynı yerleşimi kullanıyor.
{dizilim_okuma("Tek kat panel (baz paket)", dz)}
{dizilim_okuma("Sandviç panel", dz_s)}
{dizilim_okuma("Trapez sac", dz_t)}
{dizilim_okuma("Kiremit desen sac", dz_k)}
- **Panel boyu.** 4 Ekim'de kuralla L {S0346["taban_mm"]} → L {S0346["boy_mm"]} (Lokman, 16:18): taban boyla tek kat panel {S1613["tek_kat"]} gerekiyordu. 7 Ekim'de taban {YV_MM} mm'ye yukarı yuvarlanınca L {taban_mm} oldu: L {taban_mm} ile de {uz["taban_adet"]} çıkıyor, ama pay ince (kesim payı {tr(PAY[taban_mm], 1)} mm'yi geçerse {uz["taban_saglamlik_adet"]}); bu yüzden liste L {boy_mm} yazıyor (aşağıda "Panel boyu uzatma kuralı").
- **Sürümler.** 02:58 (taşma ve kesim payı yok; L {YAYIMLANAN["panel_boyu_mm"]}; tek kat panel 87, kiremit desen sac 110 cm): tek kat panel 28, sandviç panel {YAYIMLANAN["sandvic"]}, trapez sac {YAYIMLANAN["trapez"]}, kiremit desen sac 26. 13:22 (taşma {tr(tasma_cm)} cm, kesim payı {tr(kesim_mm)} mm, en az paneli veren başlangıç): {S1322["tek_kat"]}, {S1322["sandvic"]}, {S1322["trapez"]}, {S1322["kiremit"]}. 16:13 (her yüzde sol köşeden; tek kat panel ve kiremit desen sac 100 cm; L {S0346["taban_mm"]}): {S1613["tek_kat"]}, {S1613["sandvic"]}, {S1613["trapez"]}, {S1613["kiremit"]}. 16:18 (panel boyu uzatma kuralıyla L {S0346["boy_mm"]}): {S0346["tek_kat"]}, {S0346["sandvic"]}, {S0346["trapez"]}, {S0346["kiremit"]}. Şimdi (7 Ekim: boy {YV_MM} mm'ye yukarı, pay koşulu taban boyda da; L {boy_mm}): {dz["adet"]}, {dz_s["adet"]}, {dz_t["adet"]}, {dz_k["adet"]}.
- **Önceki kural** (yüzey + %10, taban panel boyu ve güncel kapatma genişlikleriyle): tek kat panelde {onceki_kural(KAP["tek_kat_panel_kapatma_m"])}, sandviç panelde {onceki_kural(KAP["sandvic_panel_kapatma_m"])}, trapez sacda {onceki_kural(KAP["trapez_sac_kapatma_m"])}, kiremit desen sacda {onceki_kural(KAP["kiremit_kapatma_m"])} verir.
- **62 m² gerçek liste** (kırma çatı, sandviç panel L 3200): listede {k62["liste"]} adet (ayrıca 2 adet L 1000); dizilim {k62["hesap"]} veriyor (02:58 sürümünde, taşmasız, 26'ydı). Listedeki {k62["liste"]} uzun ve 2 kısa panel alan olarak {tr(k62["liste"] + 2 * 1.0 / 3.2, 1)} panel eder. Kısa panellerin köşe parçaları için gönderilip gönderilmediği bilinmiyor.
- **Mühendisin 10 × 10 m dört omuz metrajı** (trapez sac L 5900): metrajda 36 adet var; dizilim tablonun son satırındaki adedi veriyor. Çatı planı saçak dahil 10,6 × 10,6 m ve eğim %33 alındı; yüzey metrajdaki 118 m²'yi tutuyor.
- **Dar yerler** (bağımsız denetimin notları). Panel boyu yuvarlanıp uzatılınca tam boy parçalarda {fazla_cm} cm fazlalık olur: mahya ucunda kalır ya da kesilir; kesilmezse o şeritlerde taşma artar. İki saçağın taşmalarının kesiştiği köşe (yaklaşık 5 × 5 cm) örtülmez: parçalar uzuyor, genişlemiyor. Kesim payı panel boyu yönünde ölçülüyor: çapraz kesim yaklaşık 46° olduğu için boyda 5 mm, 3,4 mm kalınlığında bir kesime denk gelir. Boyuna kesimin (dar son şerit) payı hesapta yok.
- **Sınır.** Yalnız dikdörtgen planlı, dört yanı eşit eğimli kırma çatı. Cumbalı çatıda (ters mahya) dizilim henüz yok.

## Mühendisin üçüncü cevapları (Lokman 4 Ekim 12:14'te iletti) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 02:58 sürümündeki on iki soruydu ("Sizden beklenenler"). Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Makas ve kiriş ölçüsü | "şimdilik Excel hesaplama motoruna uy" | Çatı çeliği, veranda dikmeleri ve kirişleri motorun ortalamasıyla kalıyor: {tr(kg(baz, "Çatı makas panelleri"))}, {tr(kg(baz, "Veranda dikmeleri (kolon paneli)"))} ve {tr(kg(baz, "Veranda kirişleri (kiriş paneli)"))} kg. Hesap değişmedi; makas ölçüsü verilirse değişir. |
| 2 | Tek katta et kalınlığı: kural mı, 2025 listelerindeki uygulama mı? | "Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz." | Kural geçerli; hesap değişmedi (baz {tr(kg(baz, TOPLAM))} kg, dış 140 {tr(kg(d140, TOPLAM))} kg). 2025 listelerindeki 0,8 mm eski uygulama olarak kayıtlı. |
| 3 | Çatı açılımı: başlangıç köşesi, kesim payı, yedek, kiremit desen sac | "5 cm çatı yüzeyinin dışında kalacak şekilde uzatıyoruz çatı kaplamalarını. Kiremit desen sacda artan parça karşı yüzde desen ters geldiğinden kullanılmaz." | Taşma {tr(tasma_cm)} cm eklendi: panel boyu L {YAYIMLANAN["panel_boyu_mm"]} → L {S0346["taban_mm"]}; tek kat panel o gün yine {S1322["tek_kat"]} adetti (87 cm kapatan panel, en az paneli veren başlangıç). Sandviç panel {YAYIMLANAN["sandvic"]} → {S1322["sandvic"]}, trapez sac {YAYIMLANAN["trapez"]} → {S1322["trapez"]}. Kiremit desen sacda artan parçanın kullanılmaması teyitli ({S1322["kiremit"]} adet; 110 cm kapatan sacla). Başlangıç köşesi, kesim payı ve yedek cevaplanmadı; Lokman 15:18'de cevapladı (aşağıda). |
| 4 | Tavan ve çatı panelinin adedi; hangi çatı tipi için? | "Genelde dörtomuz çatı tipinde tavan paneli ve çatı panelini kullanıyoruz. 100m2 için bu adetler üzerinden ilerleyebilrsin." | 100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]} adet geçerli; alana oranla Ç8201'de {tp["adet"]} ve {cp["adet"]}. Hesap değişmedi. |
| 5 | OSB takviyesi: duvarın tamamı mı, yalnız tezgâhın ve TV ünitesinin arkası mı? Klima duvarı? | "Duvarın tamamını al." | Hesap değişmedi ({osb_s["adet"]} levha). Klima duvarı cevaplanmadı; Lokman 15:18'de cevapladı (aşağıda). |
| 6 | Köşebent: çıkıntı yapan köşeler ve veranda tavanı sayılır mı? | "Odaya doğru çıkıntı yapan köşeler sayılmıyor. Veranda tavan çevresi sayılır." | Veranda tavanının çevresi ({tr(kb["veranda_tavan_cevresi_m"], 2)} m; brüt ölçüyle) eklendi: {YAYIMLANAN["kosebent"]} → {adet(baz, "Köşebent")}. Çıkıntı yapan {dis_kose} köşe sayılmıyor. Verandada köşe boyu eklenmedi. Buna bağlı trapez vida (5,5 × 25) 1000 → {adet(baz, "Trapez vida (5,5 × 25)")}. |
| 7 | Elektrik: buat için hangi odalar? Yatak odası ve banyodaki prizler tekli mi? | "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli." | İkisi de zaten öyleydi: oda sayısı {gb["oda_sayisi"]}, buat kasa {adet(baz, "Buat kasa")}. Hesap değişmedi. |
| 8 | Mahya bandı: mahya uzunluğundan mı, parça adedinden mi? | "Mahya bandı şu şekilde hesaplanır: “(Mahya Adedi * 2,8 (metre) + Ters Mahya Adedi * 2,8 (metre) + Damlalık adedi * 2,5 (metre))/10” şeklinde bulunur." | ({adet(baz, "Metal kiremit mahyası")} × 2,8 + 0 + 0) ÷ 10 → {onceki_bant} yerine {bant_s["adet"]} rulo. Damlalık okunan listelerde yok; sıfır alındı. Lokman 15:18'de damlalığı listeden tamamen çıkardı. Trapez sac seçeneklerinde motordaki gibi trapez sac mahyası × 0,8 m toplanır. |
| 9 | Dış kapı: 100 mü, 95 mi? | "Dış kapı boşluğu 95x210, iç oda kapı boşluğu 90x214 alınır." | Tanımda dış kapı boşluğu 100 → 95 cm (ekseni yerinde kaldı); plan ve paftalar yeniden çizildi. Liste hesabı zaten 95 × 210 ile yapılıyordu. |
| 10 | Boardex ve OSB kalınlığı; Boardex zayiatı | "Boardex 12.5 mm. OSB 11 mm. Boardex zayiatı %8." | Satırların boyutu 12,5 × 1200 × 2400 ve 11 × 1220 × 2440 oldu. Boardex zayiatı %15 → %{tr(zb * 100)}: dış cephe Boardex {YAYIMLANAN["boardex"]} → {boardex_s["adet"]}; saçak altı ve saçak yüzü aynı ({adet(baz, "Saçaklar için Boardex")} ve {adet(baz, "Saçak yüzü için Boardex")}). 2025 listelerindeki adetler %15'e uyuyor (aşağıda). Lokman 7 Ekim 07:45'te 12,5 mm'yi teyit etti: listelerdeki 8 mm hatalı girilmiş (aşağıda). |
| 11 | Excel motorundaki trapez sac formülü | Formülü yapıştırdı ve açıkladı: "Eğer K24 hücresi Trapez saç ise yüzey alanını ve trapez saç uzunluğunu hesaplayıp trapez saç uzunluğuyla trapez saç genişliği olan 0,8 metre ile çarpıyor." Yeniden kontrol edilmesini istedi: "Hangi hücreden neyi çekiyorum formül nasıl işliyor". | Formül yeniden okundu (aşağıda). Bulgu aynı: 0,8 paydanın parantezinin dışında. |
| 12 | Bayi standartları | "Şimdilik standartlarımız tam oturmadı. Tek tük bayilerin standartları var ancak bunu ileriki zamanlarda daha net söyleyebiliriz." | Bütün gruplar listede kalıyor; bayi kuralı örnek dosyasıyla duruyor. |

### Excel motorundaki çatı kaplaması formülü: hangi hücre ne, formül nasıl işliyor (11. cevap üzerine)

Motorun (`CTKBF V1.1`) MALZEMELER sayfası 4 Ekim'de yeniden okundu. Mühendisin yapıştırdığı formül 61. satırdaki (trapez sac) formüldür; aynı uzun ifade 58, 59, 61, 64, 67 ve 72. satırlarda da var. Her satırın başındaki EĞER, o satırın kaplaması seçili değilse 0 verir.

| Hücre | Ne |
|---|---|
| K10 | Bina dış uzun kenar (m) |
| K11 | Bina dış kısa kenar (m) |
| K13, K14 | Sundurma dış uzun ve kısa kenar |
| K17 | Oturum dışı veranda dış kısa kenar |
| K23 | Çatı tipi |
| K24 | Çatı kaplama |

Hepsi MUSTERI TALEP sayfasının C sütunundan gelir.

Formülün parçaları:

- **Çatı yüzeyi** = (K11 + 0,6) × √(1 + 0,33²) × (K10 + K17) + K13 × K14. Kısa kenara iki saçak (0,6 m) eklenir, %33 eğimle eğimli genişliğe çevrilir, uzun kenarla (veranda dahil) çarpılır; sundurma düz alanıyla eklenir.
- **Sac boyu** = ((K11 + 0,6) ÷ 2) × √(1 + 0,33²) + 0,05: saçaktan mahyaya eğimli boy + 5 cm taşma. B sütunu bunu mm olarak gösterir.
- **Adet** = yüzey ÷ sac boyu × kaplama katsayısı × çatı katsayısı, yukarı yuvarlanır. Kaplama katsayısı: trapez sac 0,8 · tek kat ve sandviç panel 1 · metal kiremit 1,05. Çatı katsayısı: beşik 1 · beşik + cumba 1,14 · beşik + 2 cumba 1,27 · dört omuz 1,06.

Bulgular:

1. **Parantez (işlem sırası).** Formülde `yüzey / (sac boyu) * 0,8` yazıyor. Excel bölmeyi ve çarpmayı soldan sağa yapar: sonuç (yüzey ÷ sac boyu) × 0,8'dir. Mühendisin anlattığı hesap (sac boyu × 0,8 = bir sacın kapattığı alan; yüzey ÷ o alan) için 0,8'in paydanın parantezi içinde olması gerekir: `yüzey / ((sac boyu) * 0,8)`. Şimdiki haliyle trapez sacda adet olması gerekenin 0,64 katı çıkar (0,8 × 0,8). Metal kiremitte 1,05 de aynı yerde: adet %10 fazla çıkar. Tek kat ve sandviç panelde katsayı 1 olduğu için fark yok.
2. **Uzun kenarda saçak yok.** Yüzeyde kısa kenara 0,6 eklenmiş, uzun kenara (K10 + K17) eklenmemiş. Aynı sayfadaki çatı izolasyonu satırı (84) uzun kenara da 0,6 ekliyor. 10 × 10 m binada formülün yüzeyi {tr(mk_besik["yuzey_m2"], 1)} m²; mühendisin kendi metrajında 118 m².
3. **Kapatma genişlikleri.** Motorda tek kat panel "100 cm kapatır", metal kiremit "105 cm kapatır" yazıyor. Kapatma ürüne göre değişiyor (Lokman, 4 Ekim 15:18): güncel ürünlerde tek kat panel, kiremit desen sac ve sandviç panel 100 cm (sandviç panelin 80 cm kapatanı da var); 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Güncel ürünle motorun tek kat panel katsayısı doğru; metal kiremit katsayısının 1,05 yerine 1 olması gerekir.
4. **Sac boyu hücresi (B61).** Yalnız "Trapez Saç" seçiliyken hesaplıyor; "OSB+Nem Bariyeri+Trapez Saç" seçiliyken 0 gösteriyor. Trapez vida (5,5 × 60) formülü (129. satır) sac boyunu bu hücreden aldığı için o seçenekte sacın vidası hesaba girmez.
5. **Sundurma.** Bu formülde sundurma alanı eğimle çarpılmıyor (K13 × K14); OSB ve nem bariyeri satırlarında (79, 81) çarpılıyor.

Örnekler (formül yazıldığı gibi → parantez düzeltilince):

| Örnek | Yüzey ÷ sac boyu | Trapez sac | Metal kiremit | Not |
|---|---|---|---|---|
| Motorun şablonundaki kayıtlı örnek (9,74 × 7,44; veranda 2,12; dört omuz) | {tr(mk_ornek["yuzey_m2"], 2)} ÷ {tr(mk_ornek["sac_boyu_m"], 3)} = {tr(mk_ornek["oran"], 2)} | {mk_ornek["yazilan"]["trapez"]} → {mk_ornek["duzeltilmis"]["trapez"]} | {mk_ornek["yazilan"]["kiremit"]} → {mk_ornek["duzeltilmis"]["kiremit"]} | Şablonda metal kiremit seçili; hücrede kayıtlı değer {mk_ornek["yazilan"]["kiremit"]} |
| Mühendisin 10 × 10 m beşik çatısı | {tr(mk_besik["yuzey_m2"], 2)} ÷ {tr(mk_besik["sac_boyu_m"], 3)} = {tr(mk_besik["oran"], 2)} | {mk_besik["yazilan"]["trapez"]} → {mk_besik["duzeltilmis"]["trapez"]} | {mk_besik["yazilan"]["kiremit"]} → {mk_besik["duzeltilmis"]["kiremit"]} | Metrajda 28 trapez sac var (her saçakta 10,6 ÷ 0,8 → 14). Düzeltilmiş formül 25 veriyor; kalan fark uzun kenara eklenmeyen saçaktan ve her saçağın ayrı yuvarlanmasından |
| Ç8201 (K10 {tr(uzun, 2)}; K11 {tr(kisa, 2)}; K17 {tr(gb["dis_olcu_m"][0] - uzun, 2)}; dört omuz) | {tr(mk_c["yuzey_m2"], 2)} ÷ {tr(mk_c["sac_boyu_m"], 3)} = {tr(mk_c["oran"], 2)} | {mk_c["yazilan"]["trapez"]} → {mk_c["duzeltilmis"]["trapez"]} | {mk_c["yazilan"]["kiremit"]} → {mk_c["duzeltilmis"]["kiremit"]} | Çatı açılımı trapez sacda {dz_t["adet"]}, kiremit desen sacda {dz_k["adet"]} veriyor (artan parça kullanılmadan). Motor tek kat panelde {mk_c["yazilan"]["panel"]} verir; açılım {dz["adet"]}. Kiremit desen sac 100 cm kapatırken motorun doğru formülü {mk_c["kiremit_100"]} verir |

Motorun sac boyu Ç8201'de {mk_c["sac_boyu_mm"]} mm: eğimli boy + taşma, mm'ye yukarı. Liste bunu {YV_MM} mm'ye yukarı yuvarlıyor (L {taban_mm}; Lokman, 7 Ekim 07:45) ve pay kalsın diye L {boy_mm} yazıyor (aşağıda "Panel boyu uzatma kuralı"). Yükleme listesi kaplama adedini bu formülden almıyor; kırma çatıda çatı açılımından alıyor. Bulgular motorun kendisi için.

## Lokman'ın cevapları (4 Ekim 15:18) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 13:22 sürümündeki altı soruydu. Cevaplar tırnak içinde, yazıldığı gibi. Lokman ayrıca en iyi bilgiyi kendisinin vereceğini söyledi: onun söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerli sayılır.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Çatı dizilimi: nereden başlar, kesim payı, yedek | "her köşeden başlayacak gibi hesapla yani 29 hesapla, evet kesim payı için 5 mm uygundur, senin yaptığın kesim planı ile yedek panele gerek yok bizde aynı kesim plan paftasını montajcıya vereceğiz" | Dizilim her yüzde sol köşeden başlıyor; kesim payı {tr(kesim_mm)} mm ve yedeksiz adet kesinleşti. 29, 87 cm kapatan panelle çıkan adetti; 2. cevapla panel 100 cm kapatır olunca aynı kural **{S1613["tek_kat"]}** veriyor (16:18'den sonra panel boyu uzatılınca {dz["adet"]}; aşağıda). Lokman 15:23'te teyit etti: "yok yanlış anlamadın aynen devam et". Açılım ve kesim planı yeniden çizildi; kesim ölçüleri tablosu eklendi. |
| 2 | Kapatma genişliği: tek kat panel 87 mi, 100 mü; kiremit desen sac 110 mu, 105 mi? | "aslında aldığımız ürünler değişiyor güncel olarak Tek Kat panelde 100 kapatır geliyor, kiremit desen sacıda 100 al sandviç panelde şimdilik 100 al ama 80 kapatırıda var bu bilgiyi daha sonra güncellenecek gibi hesaba kat" | Kurallarda tek kat panel 0,87 → 1,00; kiremit desen sac 1,10 → 1,00; sandviç panel 1,00 (80 cm kapatan ürün not edildi). Değerler ürüne göre değişir: girdide `cati.kapatma_m` yazıyorsa o kullanılır; üç gerçek liste örneği kendi ürünlerinin genişliğiyle (110, 100 ve 87 cm) hesaplanmaya devam ediyor, karşılaştırma o gün değişmedi ({S0346["kars"][0]} / {S0346["kars"][1]}). Seçeneklerde sandviç panel {S1322["sandvic"]} → {S1613["sandvic"]}, kiremit desen sac {S1322["kiremit"]} → {S1613["kiremit"]}; sandviç panelin 80 cm kapatanıyla {S1613["sandvic_80"]}. |
| 3 | Boardex zayiatı %8 ile 2025 listelerinden az | "devam et" | %{tr(zb * 100)} ile devam: dış cephe Boardex {boardex_s["adet"]}. |
| 4 | Damlalık hangi durumda listeye girer? | "damlalık uygulamasını yanlış buluyorum tamamen listeden çıkar, orijinal kapama aparatı var plastik ondan sipariş verirsek listeye sokarız damlalığı şimdilik çıkar hiçbir montajcı kullanmıyor" | Damlalık listede kalem olarak yoktu; mahya bandı formülündeki terimi çıkarıldı, adet değişmedi ({bant_s["adet"]} rulo). Plastik kapama aparatı kurallara not edildi (`kapama_aparati`); sipariş verilirse listeye girecek. Listedeki "tek kat panel kapaması" (L 2500, {S1613["kapama"]} adet; 2025 listelerinden) o gün duruyordu: Excel motorunda damlalıktan ayrı kalem. Soruldu; Lokman 16:18'de onu da çıkardı (aşağıda). |
| 5 | Klima duvarı OSB takviyesinde sayılır mı? | "sen ilk seferdeki gibi say bayi maliyeti de göz önüne alıyor bunu bayiye belirtmem lazım şimdilik hangisi az ise onu baz al" | Okuma: iki hesap yapılır, az olan baz alınır. Yalnız dolap ve TV duvarları: {tr(osb_iki["duvarlar_m2"], 1)} m² → {osb_iki["duvarlar_adet"]} levha (baz). Odanın bütün yüzeyi (ilk hesap; Lokman'ın 3 Ekim 13:27 kuralı): {tr(osb_iki["butun_oda_m2"], 1)} m² → {osb_iki["butun_oda_adet"]} levha; satırın notunda, bayiye belirtilmek üzere. Klima duvarı baz hesapta sayılmıyor. Okumanın teyidi istendi; Lokman 16:18'de geçerli kuralı söyledi (aşağıda). |
| 6 | Makas ve kiriş ölçüsü | "Tamam motoruda inceleyeceğim şimdilik motoru kastas al" | Çatı çeliği, veranda dikmeleri ve kirişleri Excel motorunun ortalamasıyla kalıyor: {tr(kg(baz, "Çatı makas panelleri"))}, {tr(kg(baz, "Veranda dikmeleri (kolon paneli)"))} ve {tr(kg(baz, "Veranda kirişleri (kiriş paneli)"))} kg. Lokman motoru inceleyecek. |

### Kesim planının ölçüleri

Kesim planı montajcıya verilecek (Lokman, 15:18). Çizimde ölçü yazmadığı için ölçüler ayrı bir dökümde: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_kesim_olculeri.md` (`cati_acilim.py --olcu-md`). İçinde üç tablo var:

- **Parçalar.** Yüz yüz, soldan sağa her şerit parçası: saçaktaki yeri, eni, sol ve sağ kenar boyu (saçak ucundan, taşma dahil), köşesi kesilen tam boy panelde aradaki kırık noktası, çıktığı panel.
- **Kesim ölçüleri.** Panel panel her parçanın paneldeki yeri: panelin sol ve sağ kenarında alt uçtan kaç cm ile kaç cm arası. Üst parça 180° çevrilerek karşı yüze konur; ters yüz edilmez.
- **Paneller.** Her panelden çıkan parçalar ve kullanılmayan boy.

Çizim, bu tablolar ve geometrik sağlama aynı yerleşimden üretilir. Ölçüler kaplamanın kapattığı genişliğe göredir; panelin bindirme payı ayrıca düşünülmedi. Panel boyu yuvarlandığı ve uzatıldığı için (4 Ekim 16:18; 7 Ekim) tam boy panellerde {fazla_cm} cm kullanılmayan boy görünür: panelin üst ucunda, mahya ucunda kalır.

## Lokman'ın cevapları (4 Ekim 16:18) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 16:13 sürümündeki ilk üç soruydu. Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Panel boyu: 1 cm uzun sipariş edelim mi? Kural yapayım mı: panel boyu en çok 3 cm uzatılınca adet düşüyorsa liste uzun boyu yazsın? | "evet 1. yi kural yap çok mantıklı bir çıkarım da bulunmuşsun tebrik ederim" | Kural yazıldı (`panel_boyu_uzatma`; aşağıda). Ç8201'de o gün: tek kat panel L {S0346["taban_mm"]} × {S1613["tek_kat"]} → **L {S0346["boy_mm"]} × {S0346["tek_kat"]}**. Seçeneklerde sandviç panel {S1613["sandvic"]} → {S0346["sandvic"]}, trapez sac {S1613["trapez"]} → {S0346["trapez"]}, kiremit desen sac {S1613["kiremit"]} → {S0346["kiremit"]}. Açılım, kesim planı ve kesim ölçüleri yeniden üretildi. 7 Ekim'den beri liste L {boy_mm} × {dz["adet"]} yazıyor (aşağıda). |
| 2 | OSB takviyesi: doğru mu anladım (az olan {osb_iki["duvarlar_adet"]} levha listede, {osb_iki["butun_oda_adet"]} levha notta)? | "evet 9 sayısını veren hangisi ise o kuralı geçerli say" | Geçerli kural: yalnız dolap ve TV ünitesi gelen duvarlar ({osb_iki["duvarlar_adet"]} levha). "Az olan baz" uygulaması kalktı; odanın bütün yüzeyi ({osb_iki["butun_oda_adet"]} levha) yalnız bilgi olarak satırın notunda duruyor (15:18: bayiye belirtilecek). Kuralın durumu `lokman`. Klima duvarı sayılmaz. Adet değişmedi. |
| 3 | Sac kapama: o da çıksın mı (tek kat panel kapaması, L 2500, {S1613["kapama"]} adet)? | "evet tek kat panel kapasınıda çıkar aynısı geçerli" | Tek kat panel kapaması listeden çıktı (`panel_kapamasi`): liste {S1613["satir"]} → {S0346["satir"]} satır. Plastik kapama aparatı sipariş verilirse listeye girecek. Sandviç panel seçeneğindeki sac kapama için cevap yoktu: soruldu; Lokman 17:46'da cevapladı (aşağıda): şimdilik kalıyor. Kapaması olan 2025 listesi örneği (105 m²) kendi uygulamasıyla hesaplanıyor (`cati.panel_kapamasi`); karşılaştırma o gün değişmedi ({S0346["kars"][0]} / {S0346["kars"][1]}). |

### Panel boyu uzatma kuralı

- **Taban boy.** Eğimli boy + taşma (mühendis, 4 Ekim 12:14; Excel motorundaki sac boyu). 4 Ekim'de mm'ye yukarı yuvarlanıyordu: Ç8201'de L {S0346["taban_mm"]}. 7 Ekim'den beri {YV_MM} mm'ye yukarı (Lokman, 07:45): L {taban_mm}.
- **Neden** (4 Ekim). L {S0346["taban_mm"]} ile en uzun kesik parça ve köşe parçası aynı panelden çıkmıyor: ikisi birlikte 4 × 105,3 + 2 × 5 + 0,5 = 431,7 cm ister; panel 431,5 cm, 2,2 mm eksik. 2. ve 3. şeritlerin eşleşmesi de aynı boyu ister. Bu yüzden o boyda her yüzün 4. şeridi bir paneli tek başına harcıyordu (4 panel).
- **Kural** (Lokman, 4 Ekim 16:18). Boy 1'er cm uzatılarak denenir, en çok 3 cm. Adet düşüyorsa liste o boyu yazar; birden çok boy düşürüyorsa en az adedi veren, eşitlikte en kısası alınır.
- **Pay koşulu** (uygulama ayrıntısı; öneride "pay kalsın diye L {S0346["boy_mm"]}" denmişti). Aday boyda adet, kesim payı 1 cm'ye çıksa da aynı kalmalı; kalmıyorsa o boy aday sayılmaz. 4 Ekim'de adedin düştüğü en kısa boy L {S0346["esik_mm"]}'di; L {S0346["boy_mm"]} kesim payı {tr(PAY[S0346["boy_mm"]], 1)} mm'ye kadar {S0346["tek_kat"]} veriyordu.
- **Pay koşulu taban boyda da** (7 Ekim; Claude'un uygulama ayrıntısı; Lokman, 8 Ekim 00:45: "3 cm'e kadar +- tolere edilebilir", hesap kapandı; kurallarda `panel_boyu_uzatma.taban_icin_de`). Yukarı yuvarlanınca taban L {taban_mm} oldu. L {taban_mm} ile de {uz["taban_adet"]} panel çıkıyor, ama pay ince: aynı iki parça 431,7 cm istiyor, panel 432,0 cm; {tr(PAY[taban_mm] - kesim_mm, 1)} mm kalıyor. Kesim payı {tr(PAY[taban_mm], 1)} mm'yi geçerse ya da panel 3 mm kısa gelirse {uz["taban_saglamlik_adet"]} panel gerekir. Üretici kataloglarında sandviç panelin boy toleransı, 3 m'den uzun panelde ± 10 mm yazıyor (PortatifEv'in tedarikçisininki sorulmadı). Bu yüzden koşul taban boy için de aranır: taban boyda adet, kesim payı 1 cm'ye çıkınca artıyorsa boy 1'er cm uzatılır (en çok 3 cm) ve adedi artırmadan koşulu sağlayan en kısa boy alınır. Ç8201: **L {boy_mm} × {dz["adet"]}**; kesim payı {tr(PAY[boy_mm], 1)} mm'ye kadar {dz["adet"]}, yani panel 10 mm kısa gelse de yetiyor. Bedeli: {dz["adet"]} panelde birer cm ({tr(dz["adet"] * (boy_mm - taban_mm) / 1000, 2)} m panel). Kuraldan `taban_icin_de` silinirse liste L {taban_mm} × {uz["taban_adet"]} yazar.
- **Taşma değişmez.** Parçalar uzamaz, panel uzar: tam boy giden {dz["tam_boy"]} panelde {fazla_cm} cm fazlalık mahya ucunda kalır ya da kesilir (kesilmezse o şeritlerde taşma {tr(tasma_cm + (boy_mm - gereken_mm) / 10, 1)} cm olur).
- **Kapsam.** Yalnız panel boyu kuraldan geldiğinde uygulanır (girdide `cati.panel_boyu_kaynak: kural`); boyu gerçek listeden gelen örneklerde uygulanmaz. Hesap deterministik: aynı çatı ve kaplama aynı boyu verir.

| Kaplama | 4 Ekim: taban L {S0346["taban_mm"]} ile | 4 Ekim: kuralla | 7 Ekim: taban L {taban_mm} ile (kesim payı {tr(kesim_mm)} mm / 1 cm) | 7 Ekim: listede | Toplam boy |
|---|---|---|---|---|---|
{uz_satiri("Tek kat panel ve sandviç panel (100 cm)", 1.0, True, S1613["tek_kat"], f"L {S0346['boy_mm']} × {S0346['tek_kat']}", boy_mm, dz["adet"])}
{uz_satiri("Trapez sac ve 80 cm kapatan sandviç panel", 0.8, True, S1613["trapez"], f"L {S0346['boy_mm']} × {S0346['trapez']}", dz_t["uzatma"]["boy_mm"], dz_t["adet"])}
{uz_satiri("Kiremit desen sac (100 cm; artan parça kullanılmaz)", 1.0, False, S1613["kiremit"], f"L {S0346['boy_mm']} × {S0346['kiremit']}", dz_k["uzatma"]["boy_mm"], dz_k["adet"])}
{uz_satiri("Tek kat panel, 87 cm kapatan ürün (2025 listeleri)", 0.87, True, S0346["d87"][2], f"{S0346['d87'][0]} × {S0346['d87'][1]}", int(d87[3].split(" ")[1]), int(d87[4].split(" ")[0]))}
{uz_satiri("Kiremit desen sac, 110 cm kapatan ürün (2025 listeleri)", 1.10, False, S0346["d110"][1], f"uzatma adedi düşürmüyor: {S0346['d110'][0]} × {S0346['d110'][1]}", int(d110[3].split(" ")[1]), int(d110[4].split(" ")[0]))}

- İlk üç satırda adet 4 Ekim'dekiyle aynı; değişen yalnız boy (L {S0346["boy_mm"]} → L {boy_mm}). 87 cm'lik üründe L {taban_mm + 20} ile de {d87[4].split(" ")[0]} çıkıyor ama pay koşulunu sağlamıyor; kural L {d87[3].split(" ")[1]} alıyor.
- 4 Ekim'de: kesim payı 2,8 mm ve altında kalsaydı L {S0346["taban_mm"]} ile de {S0346["tek_kat"]} çıkardı; liste buna güvenmedi, boyu uzattı. Şimdi aynı mantık L {taban_mm} için: {uz["taban_adet"]} panel, kesim payı {tr(PAY[taban_mm], 1)} mm'yi geçmedikçe çıkıyor; liste buna da güvenmiyor.
- Sağlama: 4 Ekim'de bağımsız hesap beş durumda aynı boyları ve adetleri buldu (o günkü kuralla). Şimdiki kuralla çokgen sınaması rastgele 450 çatı ve kaplamada yeniden koştu: {SAGLAMA["uzatilan"]}'sinde boy uzadı, {SAGLAMA["payli"]}'ünde pay koşulundan; sorun yok.{BAGIMSIZ_KISA}

## Lokman'ın cevapları (4 Ekim 17:46) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 16:54 sürümündeki ilk iki soruydu. Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Sandviç panel kapaması: o da çıksın mı? | "o kalsın şimdilik" | Sandviç panel seçeneğinde sac kapama duruyor (L 2500, {S1613["kapama"]} adet). Kuralın değeri değişmedi, kaynağı yazıldı (`panel_kapamasi`). Adet formülü o gün 2025 listelerindendi (her saçak kenarı ÷ 2,5; uydurma); 7 Ekim'de Lokman'ın tarifinden yeniden yazıldı (dere boyu ÷ 2,3; aşağıda): Ç8201'de yine {sandvic_kapama["adet"]} adet. Bir çift kat çelik projenin çatı kaplaması paftasındaki metrajda da kalem var: "Sandviç Panel Kapak L saç: 20 m" (iki ana yüzde onar şerit × 100 cm: kapama saçak boyunca). Baz listede sayı değişmedi. |
| 2 | Kesim planı paftası: açılımı, kesim planını ve ölçüleri tek bir PDF paftada toplayayım mı? | "BOM dan sonra montaj paftası için ayrı çalışacağız klasörleri dolaş ve montaj paftalarını bul ne demek istediğimi anlarsın" | Pafta şimdi hazırlanmıyor: montaj paftası, yükleme listesinden sonra ayrı bir iş. Klasörlerdeki montaj paftaları bulundu ve incelendi (`docs/sartname/montaj_paftasi.md`). Montaj paftası tek bir çizim değil; proje başına hazırlanan, ortak çerçeveli bir pafta seti. Ç8201 için üretilen açılım ve kesim planı, o setteki "çatı kaplaması yerleşim planı" paftasının kırma çatıdaki karşılığı. |

Bu turda hiçbir kuralın değeri ve listedeki hiçbir sayı değişmedi; kaynak notları eklendi.

### Montaj paftalarının yükleme listesiyle bağı

Üç gerçek listenin projelerinin paftaları listelerle karşılaştırıldı: 62 ve 90 m² projelerde ana DWG (parça boyları "Omega ve Aşık" ölçü stiliyle yazılmış), 105 m² projede PDF paftalar. "En az boy": paftadaki parçaların stok boya (omega 365, aşık 410 cm) en iyi yerleşimi; kesim payı sayılmadı; boydan uzun iki ölçü (105 m² aşık) tam boy ve artan parça diye bölündü.

| Kalem | Proje | Paftada | Listede | Hesap |
|---|---|---|---|---|
{pafta_tablosu}

Okuma:

- **Listelerdeki dizilime bağlı sayılar paftadan geliyor.** Çatı kaplamasının adedi ve boyu üç projede de paftadakinin aynısı; iniş sayısı 62 ve 105 m² projelerde paftadaki işaret sayısı. Elektrik sayımı için motorun notu da öyle diyor ("montaj paftasından sayılır").
- **Çatı kaplaması.** Pafta her yüzü şeritlere bölüp boy ve adet yazıyor; çatı alanını ve kaplama alanını da (62 m²: 77,5 ve 88,5 m²; 105 m²: 124 ve 135 m²). İncelenen sekiz çatı kaplaması paftasının hepsi beşik çatıda. Kırma çatılı tek projede (62 m²) pafta yalnız DWG'de ve dört yüz dikdörtgen çizilmiş: çapraz kesim ve artan parçanın karşı yüzde kullanılması paftada yok. Ç8201'in açılımı ve kesim planı bu boşluğu dolduruyor.
- **Dere inişi.** 62 m² projede {PAFTA["inis"][62]} iniş işareti var: dört köşe, arka cephede bir tane (ortaya yakın: köşelerden 655 ve 554 cm) ve giriş saçağının iki ön köşesi; ön cephenin ortasında yok. Liste de {inis_liste[62]}; kural dört köşe ve iki orta sayarak {inis_hesap[62]} veriyor. 90 m² projede (beşik çatı) {PAFTA["inis"][90]} işaret var: üç saçak çizgisinin (iki uzun saçak ve verandanın kademeli kısa saçağı) uçlarında altı, iki uzun saçağın ortasına yakın iki; kısa saçağın iç köşedeki ucundaki işaret çizginin üzerinde değil, yanında. Liste {inis_liste[90]}, kural {inis_hesap[90]}. Köşe, saçak çizgisinin bütün dış köşeleri olarak sayılırsa iki listedeki 7 çıkıyor (62 m²: altı dış köşe + arka cephe; 90 m²: beş dış köşe + iki orta). O gün kural değiştirilmedi; Lokman'a soruldu. Lokman 7 Ekim 07:45'te cevapladı: her saçak köşesine bir, çok uzun dere boylarında ortaya bir tane daha (aşağıda). Örnek girdilerde saçak çizgisi yok, dört köşe sayılıyor: 62 ve 90 m² projelerde karşılaştırma 6 / 7 görünmeye devam ediyor.
- **Tavan omegası.** Üç projede de listedeki adet, paftadaki parçaların en az boyundan bir fazla ({" · ".join(f"{PAFTA['omega'][n][2]} + 1 = {omega[n]['liste']}" for n in (62, 90, 105))}). Alan formülümüz {" · ".join(str(omega[n]["hesap"]) for n in (62, 90, 105))} veriyor. Omega hatları 60,0 cm aralıklı (62 ve 90 m² projelerde ölçüldü).
- **Aşık.** Hatlar 60,0 cm aralıklı (62 ve 90 m² projelerde ölçüldü; 62 m² proje sandviç panelli), mahya aşığı 20 cm'de. Listedeki adet ile paftadaki en az boy arasında sabit bir fark yok ({" · ".join(f"{PAFTA['asik'][n][2]} / {l}" for n, l in ((62, asik[62]["liste"]), (90, asik[90]["liste"]), (105, PAFTA["asik_liste_105"])))}).
- **Öteki izler.** Duvar panelleri paftasında "Dış duvarlarda çift kat izolasyon malzemesi kullanılacaktır" (105 m², dış karkas 140 mm: `yalitim_kat` kuralıyla aynı). Çerçevede "Saçak çıkması: 30 cm / saçak sacı üzerinde boardex" (62 m²: açık sorulardaki "iki yöntem aynı listede" için ipucu). OSB kaplama paftasında dolap ve TV arkası duvarlar işaretli (105 m²: üç duvar, 330 + 820 + 436 cm, brüt 42,8 m²; listede net 39,3 m², 15 levha). Çatı kaplaması paftasında "çatı izolasyonu: çift serim" (105 m²; listede şilte çift kat).
- **Makas aralığı.** Makas ve dere paftalarındaki 117 cm, makaslar arasındaki net açıklık (90 ve 105 m² projeler); makas 8 cm çizilmiş, eksen aralığı 125 cm (SketchUp modellerinde ölçülenle aynı; `skp_olcumleri.md`).
- **Sağlama.** Sayım, bu hesabı ve sonuçlarını görmeyen ayrı bir Claude oturumuna yeniden yaptırıldı (bağımsız denetim, 4 Ekim): parça sayıları, toplam boylar, en az boy sayıları, iniş işaretlerinin sayısı ve yeri, kaplama yazıları ve hat aralıkları aynı çıktı. En az boyun gerçekten en az olduğu alt sınırla gösterildi (yarım boydan uzun parçalar aynı boya giremez). 105 m² aşık paftasında saçak sırasındaki iki ölçü parça sayılmazsa en az boy 71 yerine 69 olur; öteki sayılar bundan etkilenmez.
- **Sonuç.** Omega ve aşık dizilimi (hatlar ve parça boyları) montaj paftası çalışmasında kurulacak; adet o zaman dizilimden sayılır, çatı kaplamasında yapıldığı gibi. O zamana kadar formüller duruyor. Ç8201'in baz listesinde (yöntem A) tavan omegası ve aşık yok; bu fark yalnız yöntem B'yi ilgilendiriyor. 7 Ekim: çelikte omega ve aşık artık hiç yok (Lokman, 07:45); dizilim işi prefabrik çalışılınca yapılacak.

## Listenin grupları ve bayi kuralı

105 m² listedeki ve Excel motorundaki sırayla: Çelik panel · Metal aksam · Dış cephe kaplama · İç cephe kaplama · Çatı kaplamaları · Dere · Kapı ve pencere · Elektrik · Vida · Sıhhi tesisat · Boya.

- Bir grubun listeye girip girmeyeceği bayinin standardına bağlıdır. Örnek: 90 m² gerçek listede vida, elektrik ve sıhhi tesisat yok; 62 ve 105 m² listelerde var.
- Denemede: kural kitabında `kurallar/bayi/ornek.json` ve `yukleme.py --bayi <anahtar>`. Anahtar canlıda bayinin telefon numarası olacak; dosyada gerçek numara ya da ad yok. Kural grupları açıp kapatır; boya kovası ve vitrifiyeyi dahil eder ya da etmez; çatı yöntemini ve kaplamasını bayinin standardına çevirir.
- Hangi bayinin standardının ne olduğu soruldu. Mühendis (4 Ekim 12:14): standartlar henüz oturmadı; tek tük bayinin standardı var, ileride netleşecek. O zamana kadar bütün gruplar listede.

## Çelik: birim ağırlıklar (Excel motorundan)

Motor, gerçek projelerin tonajını duvar uzunluğuna bölerek ortalama almış (kat yüksekliği 2,70 m):

| Profil (sırt × başlık × et) | Dış duvar kg/m | İç duvar kg/m | Dikme kg/m | Kiriş kg/m |
|---|---|---|---|---|
| 80 × 45 × 0,8 | — | 13,00 | — | — |
| 80 × 45 × 1,2 | 20,33 | 19,75 | 6,42 | 6,55 |
| 140 × 45 × 0,8 | 18,20 | — | — | — |
| 140 × 45 × 1,2 | 29,04 | — | 8,26 | 8,27 |
| 140 × 45 × 1,5 | — | — | — | 11,04 |

Mühendisin tablosunda 140 × 0,8 satırında iç duvar 12,06 yazıyor: motorun sayfasında o değer, dışı 140 × 0,8 olan bir projenin 80 × 0,8 iç duvarı. Hesapta iç duvar kendi profiliyle aranır (80 × 0,8 → 13,00).

Çatı çeliği (80 × 45 × 0,8), saçak dahil çatı planının m²'si başına: beşik 5,70 · dört omuz 7,55 · beşik + cumba 5,65 · beşik + 2 cumba 6,08 kg/m². Dört omuz değeri üç projenin ortalaması (9,46 · 6,86 · 6,33).

- Hesap: duvar kg = duvar boyu × birim ağırlık. Dış duvar boyu = dış çevre; iç duvar boyu plandan (iç duvarların toplam boyu).
- Motor girdi olarak yalnız dikdörtgenin kenarlarını ve bölme sayısını alıyor; iç duvar boyunu (uzun + kısa) × (0,1543 × bölme sayısı + 0,756) diye tahmin ediyor. Planımız olduğu için gerçek boylar kullanıldı.
- Dikme = adet × 2,40 m × birim ağırlık; kiriş = boy × birim ağırlık; çatı = çatı planı × kg/m². Bunlar şimdilik böyle (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"); Lokman kiriş ve makasları bir makas ölçüsünden verirse değişir.
- **Tavan paneli ve çatı paneli** (yöntem A). 100 m² binada tavan paneli {tr(pk_tavan["kg_100m2"], 2)} kg, çatı paneli {tr(pk_cati["kg_100m2"], 2)} kg (Lokman'ın 4 Ekim düzeltmesi; mühendisin ilk cevabında 429,83 ve 561,6 kg'dı). Adet 100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]} (mühendisin ilk cevabı; üçüncü cevaplarda teyit etti: bu adetlerle ilerlenir, paneller genelde dört omuz çatıda kullanılır). Hesap: çatının örttüğü oturum alanı ÷ 100 × bu değerler; adet yukarı yuvarlanır. Ç8201 ({tr(oturum, 2)} m²): {tr(tp["kg"])} kg / {tp["adet"]} adet ve {tr(cp["kg"])} kg / {cp["adet"]} adet. Oranlamayı Lokman onayladı; kesin adet panel yerleşiminden gelir.

### Üç gerçek listeyle karşılaştırma (kg)

{celik_kg}

- Toplamlar %0,5 ve %3,7 farkla tutuyor; ama parçalar tek tek tutmuyor: duvarlar %5–13 eksik, çatı %10–30 fazla. Toplamın tutması, farkların birbirini götürmesinden.
- 140 mm dış karkaslı iki listede dış duvarların çoğu 0,8 mm, üçer paneli 1,2 mm; bu iki örnekte hesap listedeki gibi 0,8 mm ile yapıldığı için dış duvar %8,5 ve %8,6 eksik çıkıyor. O iki listede dış duvar 19,9 kg/m'ye geliyor (577 kg ÷ 28,98 m ve 1055 kg ÷ 53,04 m).
- Üç liste de yöntem B'de: tavan ve çatı paneli bu karşılaştırmada yok.

### Et kalınlığı (mühendisin kuralı, 4 Ekim)

Kural: tek katlı binada ve iki katlının zemin katında duvarlar 1,2 mm (dış 140 × 45 × 1,2 ya da 80 × 45 × 1,2; iç 80 × 45 × 1,2). İki katlının üst katında 0,8 mm; üst katta 200 cm ve daha geniş pencereli duvar 1,2 mm (genelde bir ya da iki duvar). Dikme ve kiriş 1,2 mm, makas 0,8 mm: bunlar listelerden çıkarım.

| Kaynak | Dış karkas | Dış duvar | İç duvar | Kuralla |
|---|---|---|---|---|
| 90 m² liste (2025), tek kat | 80 mm | hepsi 1,2 mm | 1,2 mm | uyuyor |
| 62 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 7 panel 0,8 mm | 0,8 mm | uymuyor |
| 105 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 20 panel 0,8 mm | 0,8 mm | uymuyor |
| Motorun verisi: tek katlı 140'lık örnek (55 m²) | 140 mm | 1,2 mm | 1,2 mm | uyuyor |
| Motorun verisi: iki katlı iki projenin üst katı | 140 mm | 0,8 mm | 0,8 mm | uyuyor |
| Motorun verisi: iki katlı iki projenin zemin katı | 140 mm | 1,2 mm | 1,2 mm | uyuyor |

3 Ekim'de dış 140 için 0,8 mm varsayılmıştı (2025 listelerindeki gibi); kuralla 1,2 mm oldu. Bu yüzden Ç8201'de dış 140 seçeneği artık baz paketten ağır. 2025 tarihli iki tek katlı liste kurala uymuyor; mühendis üçüncü cevaplarda kuralı yineledi ("Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz."). O listeler eski uygulama olarak kayıtlı; üç gerçek listeyle karşılaştırma o listelerdeki kalınlıklarla yapılıyor.

| Ç8201 | Baz (dış 80) | Dış 140 |
|---|---|---|
| Dış duvar ({tr(dis_boy, 1)} m) | 80 × 1,2: {tr(dis_boy * kg_m["dis"]["80x45x1,2"])} kg | 140 × 1,2: {tr(dis_boy * kg_m["dis"]["140x45x1,2"])} kg (0,8 mm olsaydı {tr(dis140_ince)} kg) |
| İç duvar | {tr(ic_boy, 2)} m · 80 × 1,2: {tr(ic_boy * kg_m["ic"]["80x45x1,2"])} kg | {tr(ic_boy_140, 2)} m · 80 × 1,2: {tr(ic_boy_140 * kg_m["ic"]["80x45x1,2"])} kg (0,8 mm olsaydı {tr(ic140_ince)} kg) |
| Çelik toplamı | {tr(kg(baz, TOPLAM))} kg | {tr(kg(d140, TOPLAM))} kg |

## Öteki kurallar

Durum: `lokman` Lokman söyledi · `muhendis` mühendis söyledi · `excel` yükleme listesi çalışma kitabındaki formül · `motor` Excel motorundaki formül ya da not · `uydurma` gerçek listelerdeki adedi tutturan kural · `varsayim` Claude'un varsayımı · `soru` kural bilinmiyor · `bekliyor` değer henüz yok (sorulacak ya da paftadan gelecek) · `model` modeldeki açıklıklardan ya da plandan · `liste` örnekte gerçek listeden alınan sayı. Katsayılar ve kaynakları: `kurallar/liste/kurallar.json` (kural kitabı; çağrı sırası `kurallar/README.md`'de).

- **Terim.** PortatifEv listelerinde "alın" beşik çatının kalkan yüzüdür (alın sacı, çatı alnı). Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü" diye geçer; önceki kayıtlarda ve kodun içinde "alın" denmişti.
- **Dış cephe** (excel; zayiat muhendis). Net alan = çevre × kat yüksekliği + dikme ve kiriş kaplaması (adet × çevre × boy) + çatı alnı (kalkan) alanları − kapı ve pencere boşlukları. Boardex = net × {tr(1 + zb, 2)} ÷ (1,2 × 2,4): zayiat %{tr(zb * 100)} (mühendis, 4 Ekim 12:14; motorda ve bir hesap sayfasında da %8). Listelerin çalışma kitabındaki formül %15'ti ve üç listedeki adetler %15'e uyuyor (hesap / liste, 90 · 62 · 105 m²: 45 / 46, 32 / 32, 52 / 51); %8 ile {" · ".join(f"{b['hesap']} / {b['liste']}" for b in boyle)}. Ç8201'de %8 ile {boardex_s["adet"]}, %15 ile {boardex_15} levha.
- **Kalınlıklar** (muhendis, 4 Ekim 12:14; lokman, 7 Ekim 07:45). Boardex 12,5 mm; OSB 11 mm. 2025 listelerinde ve Eylül 2026 listesinde Boardex 8 mm, 2025 listelerinde OSB 9 mm yazıyor; motorda Boardex 8 mm, OSB 11 mm. Lokman, 7 Ekim: doğrusu 12,5 mm, 8 mm hatalı girilmiş; "resmi belgelerinde yazıyor". Kontrol edildi: üreticinin dış cephe levhasının performans beyanında kalınlık 12,5 mm; sistem kitabında 12,5 ve 15 mm; 8 mm yok. Çatı şiltesi 80 mm (lokman, 7 Ekim; listelerdeki 100 mm hatalı girilmiş).
- **İç cephe** (excel). Odalar "beyaz" ve "yeşil" diye ayrılır. Oda oda: iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan = net × 1,05 ÷ (1,2 × 2,5). Tavan alçıpanı = tavan alanı × 1,05 ÷ 3,0; yeşil tavan yalnız ıslak hacim.
- **Veranda tavanı** (lokman, 7 Ekim 07:45). Çelik konstrüksiyon binada her zaman Boardex, prefabrikte yeşil alçıpan. Boardex = veranda tavanı (dış ölçüyle) × {tr(1 + zb, 2)} ÷ 2,88; ayrı satır. Ç8201: {tr(vt_s["olcu"], 1)} m² → {vt_s["adet"]} levha; yeşil tavan alçıpanı {S0346["tavan_yesil"]} → {adet(baz, "Tavan alçıpan yeşil")}. Önceki kuralda veranda tavanı yeşil alçıpandı (Lokman, 3 Ekim 13:27). Veranda ya da sundurmanın kendi tek eğimli panel çatısı varsa tavan, çatının planıyla (saçağıyla) alınır (lokman, 10 Ekim 2026; `panel_cati_kenarlari.acik_alan.tavan`): aşağıda "Tek eğimli çatı panelli çatının kenarları".
- **OSB takviyesi** (lokman; ilk kez muhendis). Yalnız dolap ve TV ünitesi gelen duvarlar: modelin tanımında yazılır. Her duvarın o odaya bakan yüzünün boyu × kat yüksekliği − o yüzdeki boşluklar; × 1,05 ÷ 2,98. Duvarın tamamı alınır (Lokman: "tüm yüzeyini"; mühendis, 4 Ekim 12:14: "Duvarın tamamını al."). Geçerli kural bu (Lokman, 4 Ekim 16:18: "9 sayısını veren hangisi ise o kuralı geçerli say"). Odanın bütün yüzeyi (Lokman'ın 3 Ekim kuralı) yalnız bilgi olarak satırın notunda durur (15:18: bayiye belirtilecek). Klima duvarı sayılmaz. Tanımda duvar yazmıyorsa kalem hesaplanmaz.
- **Kapı boşlukları.** İç kapı 0,90 × 2,14 (lokman; çalışma kitaplarında da aynı). Dış kapı 0,95 × 2,10 (muhendis, 4 Ekim 12:14; 90 ve 105 m² listelerde de böyle, 62 m² listede 0,95 × 2,00).
- **Duvar izolasyonu** (lokman, 7 Ekim 07:45 ve 08:02). Gönderilmiyor; satır listeden çıktı ("Duvar izolasyonu göndermiyoruz yok say"; "evet çıkar"). Dört gerçek listede satır var. Hesabı kurallarda duruyor (dış duvar × kat sayısı + iç duvar − boşluklar; ÷ 8,64; Ç8201'de {S0346["duvar_izolasyonu"]} paketti): `duvar_izolasyonu.listede` açılırsa geri gelir.
- **Çatı kaplaması.** Baz pakette tek kat panel (lokman). Kırma çatıda panel ve sac adedi çatı açılımından (lokman; yukarıda "Lokman'ın ikinci düzeltmesi"): yüzler şerit şerit dizilir, çapraz kesimden artan parça karşı yüzde kullanılır. Dizilim her yüzde köşeden başlar; kesim payı 5 mm; yedek yok (lokman, 4 Ekim 15:18). Kaplama saçaktan 5 cm taşar: panel boyunun tabanı = eğimli boy + 5 cm (muhendis, 4 Ekim 12:14), {YV_MM} mm'ye yukarı (lokman, 7 Ekim 07:45); adet düşüyorsa ya da taban boyda pay inceyse boy en çok 3 cm uzatılır (lokman, 4 Ekim 16:18; pay koşulu taban boyda da aranır; 8 Ekim 00:45: boyda 3 cm'e kadar fark tolere edilebilir). Çatı planı girdide yoksa yüzey × 1,10 ÷ (boy × kapatma genişliği) (uydurma). Beşik çatıda saçak boyu ÷ kapatma genişliği (uydurma). Kapatma (lokman, 4 Ekim 15:18; ürüne göre değişir): tek kat panel, sandviç panel ve kiremit desen sac 100 cm; trapez sac 80 cm (motor). Sandviç panelin 80 cm kapatanı da var. 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Panel kapaması (sac, L 2500): tek kat panelde listeden çıktı (lokman, 4 Ekim 16:18); sandviç panelde var (lokman, 4 Ekim 17:46). Kapama dere boyunca gider (lokman, 7 Ekim 07:45): adet = saçak (dere) kenarlarının toplamı ÷ ({tr(SK_KR["parca_boyu_m"], 1)} − {tr(SK_KR["bindirme_m"], 2)}); parça L 2500 (lokman, 08:02). Hesap Lokman'ın tarifinden geliştirildi; 8 Ekim 00:45'te onaylandı. Önceki hesap 2025 listelerindendi: her saçak kenarı ÷ 2,5, ayrı ayrı yukarı.
- **Shingle ve membran** (motor). Adet = çatı yüzeyi × çatı katsayısı ÷ 8 ("adet / 8 m²"). Çatı katsayısı: beşik 1; beşik + cumba 1,14; beşik + 2 cumba 1,27; dört omuz 1,06. Gerçek listeyle karşılaştırılmadı.
- **Mahya** (lokman; bindirme 7 Ekim 07:45). Mahya hattı ÷ (2,8 − 0,20). Kırma çatıda hat = tepe + dört kırma. Trapez sac mahyası L 800: mahya hattı ÷ (0,8 − 0,20) (motor). Bindirme önce 30 cm'di (Lokman, 3 Ekim 13:27); Excel motorunda ve Eylül 2026 listesinde 20 cm.
- **Ters mahya ve kenar kutusu** (lokman, 7 Ekim 07:45 ve 08:02). Ters mahya, cumbalı çatıda iki çatı eğiminin birleştiği vadi deredir; boyu oradan hesaplanır: vadi boyu ÷ (2,8 − 0,20). Kenar kutusu cumbalı çatılarda olmazsa olmaz; adedi çatıya göre değişir: ters mahya adedi × {K["ters_mahya_kenar_kutusu"]["deger"]["ters_mahya_basina"]} (Excel motorundaki ve Eylül 2026 listesindeki formül). Ç8201'de vadi yok.
- **Mahya bandı** (muhendis, 4 Ekim 12:14). Mühendisin formülü: (mahya adedi × 2,8 m + ters mahya adedi × 2,8 m + damlalık adedi × 2,5 m) ÷ 10 m (rulo / 10 m), yukarı. Excel motorundaki formül aynı; motorda trapez sac mahyası × 0,8 m de toplanır, OSB mahyası ve özel mahya toplanmaz. Damlalık listeden tamamen çıkarıldı (Lokman, 4 Ekim 15:18: montajcılar kullanmıyor); terimi formülde yok. Ç8201: {adet(baz, "Metal kiremit mahyası")} × 2,8 ÷ 10 → {bant_s["adet"]} rulo. 01:24'teki uygulama mahya uzunluğundandı ({onceki_bant} rulo; açıklamalı prefabrik yükleme listesi çalışma kitabındaki formül).
- **Acil müdahale kapağı** (lokman, 7 Ekim 07:45). Dış kapı gibi her yapıya 1 adet, standart. Mühendis 4 Ekim'de "müşteri isterse" demişti; Lokman'ın söylediği geçerli. Çatı çıkış kapağı ayrı bir kalemdir ve listeye girmez (lokman, 10 Ekim 2026: "Çatı çıkış kapağı yok"; `cati_cikis_kapagi`).
- **Baca** (lokman, 10 Ekim 2026; `baca_ici`). Bacanın yalnız karkası (baca panelleri) ve çatı üstü kaplaması listeye girer; içi (baca borusu, T, kör tapa, maşon, şapka) girmez: "Bunu çok yapmıyoruz sadece karkasını yapıyoruz göz ardı et".
- **Tek eğimli çatı panelli çatının kenarları** (lokman, 10 Ekim 2026; `panel_cati_kenarlari`). Veranda, sundurma ve müştemilatın tek eğimli panel çatısı Lokman'ın 10:29'da gönderdiği beş fotoğraftaki gibi biter (10:39: "istediğim o 5 görseldeki gibi olması"): saçakta dere (dere hattı, kapak ve iniş kuralları öteki saçaklardaki gibi) ve derenin altında {PK_KR["sacak"]["ad"].lower()}; eğik kenarlarda (yanlarda) {PK_KR["yan"]["ad"].lower()} (sandviç panelin kenarını örter; adı Lokman'ın). İkisi de L {round(PK_KR["sacak"]["parca_boyu_m"] * 1000)}, adet = boy ÷ ({tr(PK_KR["sacak"]["parca_boyu_m"], 1)} − {tr(PK_KR["sacak"]["bindirme_m"], 2)}) (parça boyu KT-03'ün Eylül 2026 listesinden). Kenarda Boardex şeridi yok; veranda ve sundurmanın tavanı çatının planıyla (saçağıyla) Boardex. Müştemilat kapalı bir yapı, tavanı içeride: saçağının ve yanlarının altı Boardex kalır (15 cm), yüzü kapamayla kapanır (Claude'un okuması; Lokman'a yazıldı). Önceki kural (KT-01'in Eylül 2026 listesinden; `ek_yapi_ve_korkuluk.cati_panelli_cati`, eski setler için duruyor): dere, saçak sacı ve alın sacı yok, kenarlar 10 + 15 cm Boardex.
- **Dere** (motor; bindirme lokman, 7 Ekim). Metal dere = saçak boyu ÷ (4,0 − 0,20); tek eğimli çatı panelli çatıların (veranda, sundurma, müştemilat) saçağı dahil (lokman, 10 Ekim 2026). Kelepçe = dere × 8. İniş başına: boru 1, aparat 1, açık dirsek 2, kapalı dirsek 1, iniş kelepçesi 2.
- **Dere inişi** (lokman, 7 Ekim 07:45; eşik 8 Ekim 00:45'te onaylandı). Her saçak köşesine bir iniş; çok uzun dere boylarında ortaya bir tane daha. Kural: köşe, dere hatlarının uçlarıdır (iki hattın buluştuğu köşe tek sayılır); boyu {tr(IN_KR["orta_inis_esigi_m"])} m'yi geçen dere hattının ortasına bir iniş daha, bir hatta en çok bir orta iniş. Dere hattının boyu = cephe + uçlardaki saçak. Dayanak: paftalarda ve Lokman'ın 82 m² örneğinde orta inişi olan hatlar 9,64 · 11,54 · 12,15 · 15,98 m, olmayanlar 5,18 · 6,06 · 8,10 m; eşik 8,10 ile 9,64 m arasında herhangi bir değer olabilir, 9 m alındı. Önceki uygulamada eşik cephe boyuyla ölçülüyordu (10 m). Kısa derede tek iniş (lokman, 10 Ekim 2026 11:39: "olsun önerine uyalım"; `kisa_dere_tek_inis_m: {tr(IN_KR["kisa_dere_tek_inis_m"])}`): boyu {tr(IN_KR["kisa_dere_tek_inis_m"])} m'yi geçmeyen dere hattında tek iniş. Hattın iki ucu da başka dere hatlarına bağlıysa iki köşe kalır (köşedeki iniş öteki hattın da inişidir); bir ucu serbestse serbest uç düşer; iki ucu da serbestse (tek başına duran dere) başka bir inişe en yakın uç kalır. Alçak bir çatının üstüne düşen köşede de iniş olur: dere alçak çatının hemen üstünde, 15 cm içeride biter, su o çatıya iner (lokman, 11:39: "veranda çatısının üstüne iniş oluyor ama dere veranda çatısının hemen üstünde 15 cm içerde bitiyor akan su dereden verandaya iniyor"). Yalnız alçak çatı küçükse, yani kendi deresinde tek iniş varsa (giriş sundurması gibi), o köşeye iniş konmaz (10:18: "İniş olmasın"; `alcak_cati_ustundeki_kose: kucuk_catida_yok`); her dere hattının en az bir ucunda iniş kalır. Bu ayrım Claude'un okuması: iki cevabı ve KT-03'ün paftasını birlikte karşılıyor; Lokman'a yazıldı. Kural seti 0.18'de alçak çatının üstüne düşen her köşe düşüyordu. İniş plana elle yerleştirilmişse o sayı kullanılır (muhendis).
- **Köşebent** (muhendis). (Odaların tavan çevresi + veranda tavanının çevresi + iç köşe sayısı × 2,7 m) ÷ 2,5. İç köşe: iki duvarın odanın içinde buluştuğu köşe. Odaya doğru çıkıntı yapan köşeler sayılmaz; veranda tavanının çevresi sayılır (4 Ekim 12:14). Veranda çevresi brüt ölçüyle alınır; verandada köşe boyu eklenmez (okuma). Planı olmayan örnekte oda başına 4 iç köşe sayılır. Lokman, 7 Ekim 07:45 ve 08:02: köşebent önemli bir detay değil; mevcut kural uygulanır (Eylül 2026 şablonundaki + 3 ve çıkıntı köşeleri alınmadı).
- **Saçak altı ve saçak yüzü.** Yöntem A'da saçak altı Boardex (lokman); adet formülü 62 m² listeden (uydurma): saçak boyu × 0,30 × {tr(1 + zb, 2)} ÷ 2,88. Saçak yüzü de Boardex (muhendis): saçak ucu çevresi × yüz yüksekliği × {tr(1 + zb, 2)} ÷ 2,88. Zayiat Boardex'in %{tr(zb * 100)}'i (62 m² listenin formülünde %15'ti). Yöntem A'da saçak omegası yok (muhendis; lokman, 7 Ekim; 10 Ekim 2026: "Saçak omegası kullanılmayacak çatı ve tavan panelli sistemlerde"). Beşik çatıda kalkan kenarı (alın) yöntem A'da da Boardex kaplanır (lokman, 8 Ekim 00:45; ölçü saçaktaki gibi; `yontem_a_alin_kaplamasi`). Çatı kaplamasının üstüne bir malzeme gelmesi gerekiyor; hangisi olduğu soruldu, satırı adetsiz yazılıyor (`yontem_a_kalkan_ust_kapamasi`, soru). Dört omuz çatılı Ç8201'de böyle kenar yok. Çatının bir duvara dayandığı kenara özel mahya konur (lokman, 8 Ekim 00:45; `duvar_dibi`): L 2800, boy ÷ (2,8 − 0,20).
- **Yöntem B kalemleri** (prefabrik yöntemi). Çelikte kullanılmıyor (lokman, 7 Ekim 07:45): tavan omegası, aşık, saçak omegası, saçak sacı, alın sacı ve baş makas Z'si çelik listesinde yok; kuralları prefabrik çalışılınca birlikte kesinleşecek. O zamana kadar olduğu gibi duruyor ve yalnız karşılaştırma için hesaplanıyor: saçak sacı ve alın sacı = boy ÷ (2,5 − 0,20) (bindirme 20 cm: lokman, 7 Ekim; parça boyu L 2500 listelerden); saçak omegası, tavan omegası ve aşık kuralları iki listeye uydurulmuştu. Duvar yüzünde tavan omegası hattı yok; alın ve saçak sacı olmayınca baş makas Z'si de olmaz (lokman, 7 Ekim).
- **Vida, boya, tesisat** (motor ve excel). Alçıpan vidası = levha × 40 (lokman, 7 Ekim: levha başına 40 yeterli); OSB vidası = OSB × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; pencere vidası = pencere × 20; trapez (5,5 × 25) = çelik panel × 10 + köşebent × 6 (lokman, 7 Ekim: yalnız çelik birleşim yerleri, panel başına sağına soluna 5'er; omega ve aşık için konmaz; 08:02: köşebent terimi duruyor); trapez (5,5 × 60) = m² × 2,5 + sac boyu ÷ 200 × sac adedi; panel vidası = panel boyu ÷ 200 × adet; çelik dübel = duvar paneli × 2; uçlar ve kesme taşı = m² ÷ 15 (kesme taşı: lokman, 7 Ekim: formül ne veriyorsa); inox taş = m² ÷ 10; RYSB = m² × 7,5. Boya: 100 m²'ye dış 2, iç 2, tavan 1, astar 1 kova; dayson = m² × 0,06 (lokman, 7 Ekim: Excel motoruna uy); köpük 2; mastik = pencere adedi (lokman, 7 Ekim: pencere başına 1, boyu ne olursa olsun; pencereler alıcıya aitse yazılmaz: 8 Ekim 00:45). Tesisat: ıslak hacim başına 6 boru, 15 dirsek, 12 kulaklı dirsek, 6 düz T, 15 maşon, 6 iç dişli T, 3 atlama parçası; vitrifiye dahilse duşakabin, klozet, dolap ve batarya grubu, ıslak hacim (WC, banyo) başına {K["taharet_muslugu"]["deger"]["islak_hacim_basina"]} taharet musluğu (lokman, 10 Ekim 2026: "vitrifiye malzemesi varsa wc + banyo başı 4 adet"; Ç8201: {th_s["adet"]}).
- **Elektrik.** Pafta sayımı varsa o kullanılır (motorun notu: sayılar "montaj paftasından sayılır"). Yoksa mühendisin oda başına kuralı (yukarıda). Kabloda en uzak mesafe sigorta kutusundan ölçülür (lokman, 7 Ekim 07:45): kutu, tanımda yeri yazmıyorsa giriş kapısında sayılır; mesafe oradan kapalı kısmın en uzak köşesine. Buat, besleme kablosu, zil, sigorta kutusu, kaçak akım rölesi ve izole bant motorun formülleriyle.
- **Ölçü, renk, müştemilat** (lokman, 7 Ekim 07:45). Çevre ve alan kaplanmış yüzden alınır (gerçek listeler karkas yüzünden alıyor). Dere ve mastik çatı rengine bağlıdır. Müştemilat göz ardı edilir ("binde bir gelir"): kuralları için ayrıca çalışılmayacak. Tek eğimli panel çatısı 10 Ekim 2026'dan beri veranda ve sundurmanınki gibi biter (yukarıda).

## Üç gerçek listeyle karşılaştırma (adet)

{ozet}

Tam tablo: `deneme/2026-10-03_yukleme/sonuc/tablolar.md`. Adedi doğrudan listeden alınan satırlar karşılaştırmaya girmedi: dere kapağı, elektrik sayımı ve 105 m² listede iniş sayısı ile ona bağlı dört satır. 90 ve 62 m² listelerde iniş sayısı Lokman'ın kuralından hesaplandı (6; listelerde 7): bu tek fark beş satırda birden görünüyor, yani {kars_top - kars_ayni} farkın 10'u oradan.

7 Ekim 03:46 sürümünde {S0346["kars"][1]} karşılaştırmanın {S0346["kars"][0]}'ü aynıydı. Lokman'ın 7 Ekim kararlarıyla değişenler: duvar izolasyonu listeden çıktığı için karşılaştırılmıyor (üç satır; ikisi tutuyordu); bindirme 20 cm olunca saçak sacı 90 ve 62 m² listelerde de tutuyor (+ 2); 62 m² listede sandviç panel kapaması (16 → 17; liste 16) ve trapez vida (5,5 × 25) (1750 → 1000; liste 1750) artık tutmuyor (− 2). Sonuç {kars_ayni} / {kars_top}. Veranda tavanı kuralı bu üç örneğe uygulanamıyor: girdilerinde veranda tavanı ayrı yazmıyor (o listelerde veranda tavanı yeşil alçıpan satırında); satırın notunda yazıyor. Bu listeler omega ve aşıklı yöntemle hazırlanmış 2025 uygulamasıdır; kararlar onlara uymak için değil, bundan sonraki çelik listeleri için verildi.

**Bu bir sınama değil.** `uydurma` kuralların katsayıları 90 ve 62 m² listelere bakılarak seçilmişti; o listelerle tutması kanıt sayılmaz. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi, kesme taşı katsayısı 62 ve 105 m² listelere bakılarak seçildi. Onun da çatı planı yok: saçak, mahya, alın boyları ve elektrik sayımı listede yazan değerlerdir. Üç örnekte de çatı uzunlukları ve tavan alanları listelerdeki değerlerdir. Yani hiçbiri kör sınama değil; yöntem A için ise hiç gerçek liste yok. Mühendisin cevaplarıyla gelen kurallardan (tavan ve çatı paneli, OSB takviyesinin duvarları, saçak yüzü) hiçbiri bu üç listeyle sınanamıyor; köşebent ve elektrik kuralı yukarıda sınandı. Çatı açılımı tek bir gerçek listeyle (62 m²) karşılaştırılabildi.

Adedi tutmayan kalemler:

{tutmayan}

Okuma:

- **Köşebent.** Mühendisin formülü, oda başına 4 iç köşeyle listelerin altında kalıyor (57 / 70, 39 / 50, 70 / 85); önceki kural (m² ÷ 2,5) yarısını veriyordu. Gerçek iç köşe sayıları bilinmiyor.
- **Sandviç panel (62 m², kırma çatı).** Liste {k62["liste"]} adet L 3200 (ayrıca 2 adet L 1000); açılım dizilimi taşmayla {k62["hesap"]} veriyor (taşmasız 26'ydı). Önceki kural (yüzey + %10) 27'yi tutturuyordu, ama o listeye uydurulmuştu.
- **Dış cephe Boardex.** Zayiat %{tr(zb * 100)} olunca üç listede de 2–3 levha az: {" · ".join(f"{b['hesap']} / {b['liste']}" for b in boyle)}. %15 ile 45 / 46 · 32 / 32 · 52 / 51'di. Karşılaştırmadaki bir eksilme buradandı ({S0346["kars"][0]} / {S0346["kars"][1]}; önce 75).
- **İniş sayısı.** Kural 90 ve 62 m² projelerde 6 veriyor (dört köşe + iki uzun cephe); listelerde 7. Mühendis: iniş plana bakarak yerleştirilir. 105 m² listede 10; cephe ölçüleri olmadığı için kural hesaplanmadı. Montaj paftaları farkı gösteriyor (yukarıda, 17:46 bölümü): 62 m² projede 7 işaret (dört köşe, arka cephede bir, giriş saçağının iki ön köşesi), 105 m² projede 10, 90 m² projede 8.
- **Saçak sacı.** L 2500 parça ve 20 cm bindirme (÷ 2,3; Lokman, 7 Ekim) üç listeyi de tutturuyor (14, 17, 18). 30 cm ile (÷ 2,2) yalnız en yeni liste (Kasım 2025) tutuyordu; Eylül 2025 listelerinde birer fazla veriyordu.
- **Sandviç panel kapaması (62 m²).** Dere boyu toplamı ÷ 2,3 → 17; listede 16. Önceki hesap (her saçak kenarı ÷ 2,5, ayrı ayrı yukarı) o listeden alınmıştı ve 16 veriyordu.
- **Trapez vida (5,5 × 25) (62 m²).** Omega ve aşık terimleri kalkınca 1000; listede 1750 (o liste omega ve aşıklı yöntemle hazırlanmış).
- **Silikonize mastik.** Pencere başına 1 (Lokman, 7 Ekim): 90 ve 62 m² projelerde hesap 6, listelerde 8; 105 m² projede 8 / 8.
- **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var; kurala göre birlikte olmaz. 105 m² listede saçak altı 0,50 m alınmış (19,6 m² = 39,2 × 0,50).
- **Öteki levhalar** (alçıpan, OSB, saçak Boardex'i). Farklar 1 adet: listelerde yuvarlama bir yukarı, bir en yakına yapılmış. 105 m² listede beyaz duvar alçıpanındaki fark çalışma kitabındaki bir hücre hatasından: bir odada iki iç kapı boşluğu (3,85 m²) yerine 2 m² düşülmüş.
- **Sarf kalemleri** (RYSB, alçıpan vidası, izole bant). Motorun m² formülleri listelerdeki sayıları vermiyor.
- **Tutanlar.** Beyaz tavan alçıpanı, mahya, dere, dere kelepçesi, sıhhi tesisat (105 m²'de yedi kalemin yedisi), uçlar ve kesme taşı.

## Ç8201 taslak

Girdi: `deneme/2026-10-03_yukleme/sonuc/C8201_girdi.json` (geometri Yapı Tanımı taslağından; varsayımlar dosyanın içinde). Çatı yöntemi A; çatı kaplaması baz paketteki tek kat panel. "Dış 140" sütunu yalnız değişenleri gösterir. Bu modelin gerçek listesi yok: taslak yalnız kurallardan çıkıyor.

Not: saçaklar için Boardex'te alan liste yöntemiyle saçak boyu × 0,30 = 11,8 m² (köşeler iki kez sayılır); gerçek saçak altı 11,4 m². İkisi de 5 levha.

{taslak}

### Çatı kaplaması seçenekleri

Baz pakette tek kat panel (Lokman, 4 Ekim 01:42). Altı seçenekte değişen kalemler (son üç seçenek gerçek listeyle karşılaştırılmadı):

{kaplama}

### Aynı model yöntem B ile

Çelikte bu yöntem artık kullanılmıyor (Lokman, 7 Ekim 07:45); liste yalnız karşılaştırma için üretiliyor ve başında bunu söyleyen bir not var. Bayi kuralı çatıyı yöntem B'ye çevirirse (`--bayi ORNEK-BAYI-3`; çıktı `sonuc/C8201_yontem_B.md`): tavan ve çatı paneli ile saçak altı ve saçak yüzü Boardex'i çıkar; saçak sacı {adet(yb, "Saçak sacı (30'luk)")}, saçak omegası {adet(yb, "Saçak omegası")}, tavan omegası {adet(yb, "Tavan omegası (60'lık)")}, aşık {adet(yb, "Aşık")} girer. Çelik {tr(kg(yb, TOPLAM))} kg, trapez vida (5,5 × 25) {yb_vida} olur (omega ve aşık terimleri kalkmadan önce {S0346["trapez_vida_B"]}).

## Excel motoruyla ilgili gözlemler (mühendise iletilecek)

- **Trapez sac ve metal kiremit adedi.** Formülde 0,8 ve 1,05 paydanın parantezi dışında: kapatma genişliğine bölmek yerine çarpıyor. Hücreler, formülün işleyişi, örnekler ve öteki dört bulgu yukarıda ("Excel motorundaki çatı kaplaması formülü"). Mühendis 11. cevabında formülü yeniden kontrol etmemizi istedi; bulgu ona iletilecek. Trapez sacda motorun formülü kullanılmıyor.
- **Kırma çatıda kaplama adedi.** Motor yüzeyden hesaplıyor; notunda gerçek adedin AutoCAD'de yerleşimle bulunacağı yazıyor. Mühendisin 10 × 10 m dört omuz metrajında 118 m² yüzey için 36 adet L 5900 trapez sac var (yüzeyin 1,44 katı). 62 m² gerçek listede 27 adet L 3200 ve 2 adet L 1000 sandviç panel var (yüzeyin 1,15 katı). Lokman'ın 4 Ekim 01:42 kuralıyla adet artık çatı açılımından çıkıyor; karşılaştırma yukarıdaki tabloda.
- **Köşebent.** Motor plansız hesaplıyor: oda çevrelerini bina kenarlarının altı katı, iç köşeyi 36 sayıyor. Ç8201'in ölçüleriyle {motor_kosebent} verir; plandan {adet(baz, "Köşebent")}.
- **Elektrik.** Motorda sayılar sabit: duy 7, glop 3, tekli anahtar 9, çiftli anahtar 2, tekli priz 22, çiftli priz 3, uydu prizi 1, sigorta 9; buat = anahtar + priz + 9.
- **İniş borusu.** Motorda dere adedi ÷ 5 + 6; mühendisin 10 × 10 m metrajındaki sayıları (8 ve 6) vermiyor (9 ve 8 verir).
- **Motorda olup listede olmayan kalemler.** Kalmadı. Mahya bandı listeye eklendi (mühendis, 4 Ekim). Acil müdahale kapağı her yapıya 1 adet standart (Lokman, 7 Ekim 07:45; mühendis "müşteri isterse" demişti). Ters mahya kenar kutuları (ters mahya × 2) cumbalı çatıda listede (Lokman, 7 Ekim 08:02). Damlalık (L 2500; motorda 78. satır, adedi elle, şablonda 0): Lokman listeden tamamen çıkardı (4 Ekim 15:18; 7 Ekim 07:45: "Listeden çıkar"); yerine düşünülen plastik kapama aparatı sipariş verilirse listeye girecek. Motorda panel kapamaları damlalıktan ayrı kalemler: tek kat panel kapaması (66. satır, L 2500, adedi elle) ve sandviç panel kapaması (69. satır, L 2800; saçak boyu × çatı katsayısı ÷ 2,6). Tek kat panel kapaması Lokman'ın 4 Ekim 16:18 cevabıyla çıktı; sandviç panel kapaması kalıyor (4 Ekim 17:46) ve dere boyu ÷ (2,5 − 0,20) ile hesaplanıyor (7 Ekim 07:45 ve 08:02).

## Kör test: KT-01 (6–7 Ekim 2026)

Lokman, 6 Ekim 21:22: bir başka çelik projenin (98,7 m², beşik + cumba çatı, müştemilatlı; Eylül 2026) DWG'sinden bizim çizimlerimiz ve bu kurallarla kendi listemiz çıkarıldı; liste depoya dondurulduktan sonra gerçek listeyle satır satır kıyaslandı. Rapor: `docs/raporlar/2026-10-07_Kor_Test_KT01.md`; kod ve tablolar: `deneme/2026-10-06_kor_test/`.

- **Sonuç (7 Ekim 03:46; kural seti 0.12).** Gerçek listenin {kt_n} satırından kör listede {KT["onceki"]["kor"]}'si, yalnız bizim hatalarımız düzeltilince {KT["onceki"]["duzeltilmis"]}'i, Eylül 2026 listesinin uygulaması da kural olursa {KT["onceki"]["sablon"]}'i, elektrik ve iniş sayıları paftadan alınırsa {KT["onceki"]["pafta"]}'i aynıydı. Kör listedeki 56 farkın 29'u bizim hatamızdı (girdi 2, kural 27).
- **Varsayılan hesaba girenler** (bizim hatalarımız; `kurallar.json`'da durumu `liste`): model verilmişse çelik ağırlığı modeldeki profil boyundan ve okunan et kalınlığından (`celik.profil_kg_m`); çok düzlemli çatıda aşık sıraları (`cok_duzlemli_cati`); ek yapının kalemleri ayrı satır, çatı panelli çatıda dere, saçak sacı ve alın sacı yok (`ek_yapi_ve_korkuluk`; 10 Ekim 2026'dan beri saçakta dere ve özel büküm saçak sacı, yanlarda sundurma kapama: `panel_cati_kenarlari`); dış cephe nem bariyeri yalnız duvarlar × 1,08 (`nem_bariyeri_dis_cephe`); dere kapağı dere hatlarının serbest uçlarından (`dere_kapagi_serbest_uc`); baş makas Z'si (`bas_makas_z`; uydurma); depo için elektrik (`elektrik_oda_ek`); alıcıya ait kalemler kalem kalem (`kapsam_alici`); renk (`renkli_kalemler`).
- **Eylül 2026 uygulaması.** O listenin, o günkü kurallardan farklı yaptığı on yedi şey ayrı bir katmana konmuştu (`sablon_2026`; `yukleme.py --sablon 2026`; satırların durumu `sablon`). Lokman 7 Ekim 07:45'te on yedisini de cevapladı (aşağıdaki bölüm). Katman, 03:46 kıyası yeniden üretilebilsin diye duruyor (`kiyas_kos.sh`, 0.12 setine sabit); varsayılan hesaba karışmıyor.
- **Kararlardan sonra (7–10 Ekim; kural seti 0.19, KT-01'de 0.18'le aynı).** Aynı proje güncel kurallarla iki kez hesaplandı (`kararlar_kos.sh`; tablo `deneme/2026-10-06_kor_test/sonuc/KT01_kararlar_kiyas.md`). Yapıldığı yöntemle (B: tavan omegası ve aşık; elektrik sayıları paftadan) aynı satır **{kt_b}** / {kt_n}: düzeltilmiş listede {KT["onceki"]["duzeltilmis"]}, 9 Ekim'de 0.17 setiyle {KT_017["b"]}. 10 Ekim'deki düşüşün nedeni Lokman'ın kararı: tek eğimli çatı panelli çatılar beş fotoğraftaki gibi bitiyor, müştemilatın panel çatısına da dere, iniş, özel büküm saçak sacı ve sundurma kapama geldi. Bu listede ve dere paftasında müştemilatta dere yok: dere, dere kapağı, dere kelepçesi ve beş iniş satırı ({kt_mus_satir} satır) karar farkı oldu; iniş {kt_birim("Dere iniş borusu")["b"]} (liste ve pafta 7). B listesinde gerçek listede olmayan satırlar: {"; ".join(f'{x["kalem"].lower()} {x["adet"]}' for x in kt_ek_satirlar)} (müştemilatın saçağı ve eğik kenarları). 03:46'dan beri yeni tutan satır {kt_kazanc["toplam"]}: kararlardan {kt_kazanc["toplam"] - kt_kazanc["pafta"]}, elektrik sayılarının paftadan alınmasından {kt_kazanc["pafta"]}; 03:46'da tutup bu kararla bozulan satır {kt_kazanc["bozulan"]} (metal dere, dere kapağı, dere kelepçesi). Çelik standardıyla (A: çatı ve tavan paneli; bu proje bugün sipariş edilse çıkacak liste) aynı satır **{kt_a}** / {kt_n} (0.17 ile {KT_017["a"]}). B'de farklı kalan {kt_n - kt_b} satır: {kt_fark["karar"]} satırda Lokman'ın kararı o listeden farklı; {kt_fark["yöntem"]} satır yöntemden (omega, aşık, saçak omegası); {kt_fark["elle"]} satır listenin elle hesabı, yuvarlaması ya da elle dizilimi; {kt_fark["ölçü"]} satır ölçünün alındığı yüzden (karar: bizdeki){"; kural bekleyen satır kalmadı" if not kt_fark["soru"] else f"; {kt_fark['soru']} satır kural bekliyor"}. Adedi 03:46'dakinden farklı satır {KT["karardan_degisen_satir"]}: kararlarla {kt_kararla}, elektrik sayıları paftadan alındığı için {kt_paftadan}. A listesinde gerçek listede olmayan {len(KT["a_listesinde_gercek_listede_olmayan"])} satır var: {"; ".join(x.get("liste_adi") or x["kalem"] for x in KT["a_listesinde_gercek_listede_olmayan"])}. Çelik: gerçek liste {tr(KT["celik_kg"]["gercek"])} kg, B {tr(KT["celik_kg"]["b"])} kg, A {tr(KT["celik_kg"]["a"])} kg (tavan ve çatı panelleri eklenir).
- **Okuma.** Aynı satır sayısı kuralların o listeye ne kadar benzediğini gösterir, doğruluğunu değil: Lokman'ın kararlarının bir kısmı o listeyi düzeltiyor (Boardex kalınlığı, çatı şiltesi, duvar izolasyonu, vida katsayıları). Kararlardan sonraki tabloda her fark satırının nedeni yazılı; elle yazılan açıklamalar hesap çıktısıyla denetleniyor (`kararlar_kiyas.py`).

## Lokman'ın cevapları (7 Ekim 07:45 ve 08:02) ve uygulanışı

Sorular, kör test raporunun on iki sorusuydu (raporun 12. bölümü); birincisi Eylül 2026 listesinin farklı yaptığı on yedi şeydi (a–q). Cevaplar tırnak içinde, yazıldığı gibi. 08:02'de beş okuma soruldu; düzeltmeleri ilgili satırda. Lokman ayrıca: "bazı kuralları yeniden optimize edeceğiz hem çizimden hem doğrulama motorundan … tüm optimizasyonu beraber yapacağız".

Kurallar bu cevaplarla 0.13 sürümü oldu. Önceki set olduğu gibi saklanıyor (`kurallar/liste/setler/0.12.json`); `PORTMAN_KURALLAR` ile seçilince 7 Ekim 03:46'daki bütün çıktılar bayt bayt aynı üretiliyor. Yeni davranışların hepsi kurallardaki bir anahtara bağlı: kod değişmeden kural değişir.

| # | Konu | Cevap | Uygulama |
|---|---|---|---|
| 1 a | Bindirme | "Bindirmeleri 20 cm yap 30 cm banada çok geldi" | Mahya, saçak sacı ve alın sacında 30 → 20 cm; dere ve trapez mahyası zaten 20 cm'di (açık soru kapandı). Ç8201: mahya ÷ 2,6 → {adet(baz, "Metal kiremit mahyası")}; adet değişmedi. |
| 1 b; 7 | Köşebent | "Köşebent önemli değil"; "bizde ne çıkıyorsa onu uygula hiç önemli değil yani köşebent olmazsa bile binayı kurabilirler" | Kural değişmedi (mühendisin formülü; Ç8201'de {adet(baz, "Köşebent")}). Şablondaki + 3 ve çıkıntı köşeleri alınmadı. |
| 1 c, d, e; 2 | Saçak omegası, tavan omegası, aşık | "Çatı ve tavan paneli var ise saçak omegası kullanmıyoruz yine dediğim gibi prefabrikte kullanacağız"; "Aynısı geçerli"; "Duvar yüzünde tavan omegası yok … hangi çatı tipi olursa olsun özellikle 4 omuz ve Beşik çatı çatı ve tavan paneli kullanacağız o yüzden Çelik Konstrüksyion yapılarda omega ve aşık olmayacak artık göz ardı et ama Prefabrik yapılarda olacak ona sıra gelince kuralları yine beraber çalışırız" | Çelikte çatı yöntemi her zaman A (`celik_cati_yontemi`). Yöntem B'nin kalemleri çelik listesinde yok; kuralları prefabrik çalışılana kadar olduğu gibi duruyor. B ile hesaplanan listenin başına "çelikte kullanılmıyor" notu düşüyor. |
| 1 f | Ters mahya ve kenar kutusu | "Ters mahya cumba şekline bağlı iki çatı eğiminin birleşitiği vadi dere oradan hesaplanıyor"; 08:02 (kenar kutusu listeye girsin mi?): "evet girsin bu tarz cumbalı çatılarda olmazsa olmazdır her cumbalı çatı için aynı değil" | Ters mahya vadinin boyundan (öyleydi). Kenar kutusu artık varsayılan listede: ters mahya × 2. Ç8201'de vadi yok; KT-01'de 4 (liste 4). |
| 1 g | Damlalık | "Listeden çıkar" | Çıkıktı (4 Ekim 15:18); öyle kaldı. Çatının bir duvara dayandığı kenara ne konacağı o gün açıktı; 8 Ekim 00:45: özel mahya. |
| 1 h | Duvar izolasyonu | "Duvar izolasyonu göndermiyoruz yok say"; 08:02 (satır çıksın mı?): "evet çıkar" | Satır listeden çıktı (Ç8201'de {S0346["duvar_izolasyonu"]} paketti). |
| 1 i | Sandviç panel kapaması | "Aslında dere boyu ile aynı oradan yola çıkabilirsin yani binanı çatı eğiminin olduğu tarafa her zaman dere ve sandviç panel kapama gelir şöyle bizde saçaklar 30'ar cm ona göre sen bir hesap geliştir"; 08:02 (parça boyu): "en son 2500 dü diye biliyorum" | Geliştirilen hesap (8 Ekim 00:45'te onaylandı): kapama boyu = saçak (dere) kenarlarının toplamı; adet = boy ÷ (2,5 − 0,20). Ç8201, sandviç panel seçeneği: {tr(sandvic_kapama["olcu"], 2)} ÷ 2,3 → {sandvic_kapama["adet"]}. |
| 1 j | Veranda tavanı | "Çelik konstrüksyion binalarda her zaman boardex olmalı prefabrik yapılarda yeşil alçıpan" | Veranda tavanı Boardex satırı oldu: {tr(vt_s["olcu"], 1)} m² → {vt_s["adet"]} levha; yeşil tavan alçıpanı {S0346["tavan_yesil"]} → {adet(baz, "Tavan alçıpan yeşil")}. |
| 1 k | Boardex kalınlığı | "… 8 mm girmiş yanlış ver doğrusu 12.5mm resmi belgelerined yazıyor kontrol edebilirsin marka Aygyps (aytaş)" | 12,5 mm kuraldaydı (mühendis, 4 Ekim 12:14); teyit edildi. Kontrol edildi: üreticinin dış cephe levhasının performans beyanında kalınlık 12,5 mm; sistem kitabında 12,5 ve 15 mm; 8 mm yok. |
| 1 l | Çatı şiltesi | "Doğrusu 80mm ama listelerde yine boardexde olduğu gibi hatalı girilmiş" | 80 mm kuraldaydı; teyit edildi. |
| 1 m | Alçıpan ve OSB vidası | "Levha başına 40 yeterli" | Değişmedi (şablondaki 50 alınmadı). |
| 1 n | Trapez vida (5,5 × 25) | "Omega ve aşık için koyulmayacak sadece çelik birleşim yerlerine kaç panel varsa sağına soluna 5 ile çarp"; 08:02: "köşebenti çıkarma sadece mevcut kurala uy" | Aşık ve omega terimleri sıfırlandı; çelik panel × 10 ve köşebent × 6 duruyor. Ç8201 (yöntem A) değişmedi: {adet(baz, "Trapez vida (5,5 × 25)")}. Yöntem B listesinde {S0346["trapez_vida_B"]} → {yb_vida}. |
| 1 o | Kesme taşı | "Kesme taşı hiç önemli değil formül ne veriyorsa yeterli" | Değişmedi (m² ÷ 15). |
| 1 p | Dayson | "Tamam sen excel motoruna uy" | Değişmedi (m² × 0,06). |
| 1 q | NYM kablo | "Sigorta x sigortadan en uzak mesafe diye bir kural varsa onu uygula" | Kural Excel motorunun notunda yazılı. Mesafe artık sigorta kutusundan (tanımda yeri yoksa giriş kapısı) kapalı kısmın en uzak köşesine: Ç8201'de {tr(gb["elektrik_en_uzak_m"], 2)} m (köşegen {tr(kosegen, 2)} m'ydi). NYM 3 × 2,5: {S0346["nym"][0]} → {adet(baz, "NYM kablo (3 × 2,5)")} m; 2 × 1,5: {S0346["nym"][1]} → {adet(baz, "NYM kablo (2 × 1,5)")} m. |
| 3 | Müştemilat | "Müştemilatı göz ardı et binde bir gelir önemli bir konu değil" | Müştemilatla ilgili sorular kapandı; mevcut hesap olduğu gibi duruyor. |
| 4 | Dere inişi | "yani her saçak köşesine ve çok uzun dere boyarında ortaya 1 tane daha koyuyoruz nasıl kurallaştırabiliriz?" | Kural (eşiği 8 Ekim 00:45'te onaylandı): köşe = dere hatlarının uçları; boyu {tr(IN_KR["orta_inis_esigi_m"])} m'yi geçen dere hattının ortasına bir iniş daha; bir hatta en çok bir. Ç8201: {adet(baz, "Dere iniş borusu")} (değişmedi). KT-01: 5 → 7 (pafta ve liste 7). Ayrıntı "Öteki kurallar"da. |
| 5 | Baş makas Z'si | "Alın ve Saçak sacı olmayınca baş makas Z side olmaz" | Yalnız yöntem B'de hesaplanıyordu; çelikte yok. |
| 6 | Mastik, acil müdahale kapağı, menfezli saçak sacı, buat | "silikonize mastik pencereler için koyuluyor boyu ne olursa olsun pencere başı 1 adet koy acil müdehale kapağı dış kapı gibi her yapıya 1 adet standart menfezli saçak sacı önemli değil prefabrik için ayrıca çalışacağız bizdekine uy" | Mastik = pencere adedi (Ç8201: {adet(baz, "Silikonize mastik")}); pencereler alıcıya aitse yazılmaz (8 Ekim 00:45). Acil müdahale kapağı her yapıya 1: Ç8201'de yeni satır. Menfezli saçak sacı prefabrikle birlikte. Buat kasada oda sayısı bizdeki gibi. |
| 8 | Ölçü | "bizdekini al" | Çevre ve alan kaplanmış yüzden (değişmedi). |
| 9 | Sandviç panel boyu | "sandviç panelde o kadar tolerans var önemli değil yukarı yuvarla"; 08:02 ({YV_MM} mm'ye yukarı mı?): "evet" | Kuraldan gelen panel boyu {YV_MM} mm'ye yukarı. Ç8201: taban L {S0346["taban_mm"]} → L {taban_mm}; pay koşuluyla liste L {boy_mm} × {dz["adet"]} (yukarıda "Panel boyu uzatma kuralı"). |
| 10 | Dere ve mastiğin rengi | "çatı rengine" | Çatı rengine bağlı (`renkli_kalemler`). |
| 11 | Çelik birim ağırlıkları | "profil uzunluklarını çizmeden nasıl bileceğiz ki çelik karkas çizimi iş imalata verilince çıkar yani teklif ve BOM listesi için neredeyse en son aşama şimdilik bunu geç" | Geçildi. Karkas çizimi yokken çelik, Excel motorunun ortalamalarıyla hesaplanıyor; model verilmişse modeldeki profil boyundan. |
| 12 | Çizimler | "Çizimlerin bu halini çok beğendim burada kalalım sadece açıklamalar kısmını düzelteceğiz"; "çizimler persfektifler çok güzel olmuş bunları kurala ekle paftadaki açıklamaları düzelteceğiz" | Çizim seti standart olarak kaydedildi (`docs/sartname/cizim_seti.md`). Paftadaki açıklamalar birlikte düzeltilecek. Depoya eklenmesi sorusu cevaplanmadı: KT-01'in tanımı ve çizimleri depoda değil. |

Ç8201'in baz listesinde değişenler ({S0346["satir"]} → {BAZ_SATIR_0709} satır): duvar izolasyonu çıktı; veranda tavanı (Boardex) ve acil müdahale kapağı girdi; yeşil tavan alçıpanı {S0346["tavan_yesil"]} → {adet(baz, "Tavan alçıpan yeşil")}; NYM kablolar {S0346["nym"][0]} → {adet(baz, "NYM kablo (3 × 2,5)")} ve {S0346["nym"][1]} → {adet(baz, "NYM kablo (2 × 1,5)")} m; panel L {S0346["boy_mm"]} → L {boy_mm} (adet aynı). Öteki satırlarda adet değişmedi; kaynak ve durum notları güncellendi.

Cevaplardan çıkarılan yedi uygulama (iniş eşiği, kapama hesabı, panel boyunda pay, alıcıya ait pencerede mastik, sigorta kutusunun yeri, yöntem A'da kalkan kenarı, trapez vidada parça C profil) Lokman'a soruldu; 8 Ekim 00:45'te altısı cevaplandı (aşağıdaki bölüm), parça C profil sorusu yeniden soruldu.

Sağlama (7 Ekim): kararlarla değişen kalemler (mahya, ters mahya ve kenar kutusu, saçak ve alın sacı, kapama, veranda tavanı ve yeşil tavan, kablolar, iniş ve ona bağlı dört kalem, trapez ve alçıpan vidası, acil müdahale kapağı, mastik, panel boyu) beş listede (Ç8201 baz, sandviç panel ve yöntem B; KT-01 A ve B) ayrı bir oturumda, hesap koduna bakılmadan, girdilerden ve bu kurallardan yeniden hesaplandı: 138 karşılaştırmanın hepsi aynı çıktı. Ç8201'de sigortadan en uzak mesafe tanımdaki geometriden ayrıca bulundu (8,598 m → 8,60). O denetim, trapez vidada panel sayısının iki hatta farklı sayıldığını gösterdi (katalog modelinde parça C profiller toplamın içindeydi, modelden sayılan panellerde değildi); iki hat eşitlendi ve parça C profillerin sayılıp sayılmayacağı soruldu. Kod ayrıca üçüncü bir oturumda incelendi; bulduğu hatalar (dere hattı olmayan çatıda orta iniş, şablon katmanıyla kapama satırının notu, yeşil tavanın eksiye düşebilmesi, çizim setinde yöntem seçeneğinin IFC'ye geçmemesi, panel boyu ölçütünün iki motorda ayrışması) düzeltildi.

Panel boyu kuralı iki motorda ayrı ayrı kurulu olduğu için birbirine bağlandı: genel motorun seçtiği boy, adet ve uzatmanın nedeni rastgele {GS["kural_denemesi"]} kırma çatı ve kaplamada kırma motorununkiyle karşılaştırılıyor (boyu uzayan {GS["kural_uzayan"]}, bunlardan pay koşuluyla uzayan {GS["kural_pay_kosulundan"]}; fark yok). Sağlamaların kendisi de sınandı: ölçüt iki motorda dokuz yerde bilerek bozuldu; yedisi yakalandı. Yakalanmayan ikisi aynı bozmanın iki motordaki eşi (pay koşulunda "1 cm payla gereken adedi düşürüyorsa" yerine "artırmıyorsa") ve sonucu değiştirmiyor: pay inceyken 3 cm içindeki bir uzatma her zaman tam düzeltiyor (6000 rastgele çatının 162'sinde pay inceydi: 160'ında 1 cm, birinde 2 cm yetti; birinde adet de düştü). Pratikte: taban boyda pay inceyse boy çoğunlukla 1 cm uzar.

## Lokman'ın cevapları (8 Ekim 00:45) ve uygulanışı

7 Ekim'de sorulan dokuz soruya verildi. Cevaplar tırnak içinde, yazıldığı gibi. Kurallar bu cevaplarla 0.14 sürümü oldu; 0.13 seti saklanıyor (`kurallar/liste/setler/0.13.json`) ve onunla 7 Ekim'deki çıktılar bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | İniş: "çok uzun" için {tr(IN_KR["orta_inis_esigi_m"])} m dere boyu uygun mu? | "evet uygundur" | Kural kesinleşti: dere hatlarının uçlarına birer iniş, boyu {tr(IN_KR["orta_inis_esigi_m"])} m'yi geçen hattın ortasına bir tane daha. Ç8201: {adet(baz, "Dere iniş borusu")}; KT-01: 7 (10 Ekim'den beri müştemilatın deresiyle {kt_birim("Dere iniş borusu")["b"]}). |
| 2 | Sandviç panel kapaması: dere boyu toplamı ÷ (2,5 − 0,20) uygun mu? | "evet uygun" | Kesinleşti. Ç8201, sandviç panel seçeneği: {sandvic_kapama["adet"]}; KT-01: {kt_birim("Sandviç panel kapaması (bina ve müştemilat)")["b"]}. |
| 3 | Panel boyunda pay: L {taban_mm} mi, L {boy_mm} mi; pay nasıl alınsın? | "3 cm'e kadar +- tolere edilebilir artık sandviç panel hesabını sonlandır" | Hesap bu haliyle kapandı: eğimli boy + taşma, {YV_MM} mm'ye yukarı; adedi düşürüyorsa ya da taban boyda pay inceyse en çok 3 cm uzatma. Ç8201: L {boy_mm} × {dz["adet"]}. Bu konuda yeni soru sorulmayacak. |
| 4 | Çatı ve tavan panelli beşik çatıda kalkan kenarı (alın) neyle kapanıyor? | "beşik çatıda da boardex kaplama yapılıyor ama çatı kaplamasının üstüne bir malzeme gelmesi lazım" | Kalkan kenarının Boardex kaplandığı kesinleşti. Ölçü saçağınki gibi alındı (kenar boyu × (saçak eni + saçak yüzü); soruda "saçak gibi" denmişti): kalkan kenarının çıkıntısı için ayrı bir ölçü yok. Çatı kaplamasının üstüne gelecek malzeme için satır açıldı: kalkan kenarının boyuyla, adetsiz, durumu `soru`; malzemenin adı ve parça boyu soruldu. Satır saçak altının malzemesine bağlı değil. KT-01 (çelik standardı): {tr(kt_ust_olcu, 2)} m (çatı panelli ek yapının alınları hariç). |
| 5 | Çatının bir duvara dayandığı kenara ne konuyor? | "özel mahya" | O kenarların boyu özel mahya satırına yazılıyor: L 2800, boy ÷ (2,8 − 0,20). KT-01: 11,35 m → {kt_birim("Damlalık (bina ve müştemilat)")["b"]}. Geçici "duvar dibi sacı" satırı kalktı. Adet hesabı benim uygulamam: mahyada ve kapamada olduğu gibi boylar toplanıp bir kez yuvarlanıyor; her yapının kenarı ayrı yuvarlansa {kt_om_ayri} olurdu (satırın notunda yazıyor; soruldu). Özel mahya mahya bandı hesabına girmiyor (Excel motorundaki formülde yok) ve satıra renk yazılmıyor: ikisi de soruldu. |
| 6 | Pencereler alıcıya aitse mastik yine yazılsın mı? | "hayır yazılmasın" | Yazılmıyor (pencere vidası gibi). Pencere listedeyse pencere başına 1 (Ç8201: {adet(baz, "Silikonize mastik")}). KT-01'de mastik satırı yok (o listede 3). |
| 7 | Sigorta kutusu tanımda yoksa giriş kapısında sayılsın mı? | "evet uygun" | Kesinleşti. |
| 8 | Listede "Boardex" mi yazsın, üreticinin adı mı? | "üreticide ne yazıyorsa onu yaz" | Listede yazılan ad üreticinin ürün sayfasındaki ad: {LEVHA_ADI}. Ç8201'de {len(levha_satirlari)} satır. Hesabın iç anahtarı ile formül ve not metinleri şirketteki adla (Boardex) kalıyor; gerçek listelerle karşılaştırma o adla yapılıyor (bu belgedeki karşılaştırma tablolarında satır o adla, Ç8201 taslağında üreticinin adıyla görünür). Üretici ya da ürün değişirse yalnız `urun_adlari` kuralı değişir. |
| 9 | Trapez vidada parça C profiller de panel gibi sayılsın mı? | "soruyu anlamadım" | Uygulama değişmedi (sayılıyor). Soru örnekle yeniden soruldu (aşağıda, açık sorular). |

Ç8201'de hiçbir adet değişmedi ({BAZ_SATIR_0709} satır): levhanın yazılan adı, iniş satırının durumu ve notlar değişti; sandviç panel seçeneğinin listesinde kapama satırının durumu da değişti. KT-01'de mastik satırı çıktı; geçici duvar dibi sacı satırı özel mahya oldu (adet aynı); çelik standardı listesine kalkan kenarı üst kapaması satırı eklendi (adetsiz). Gerçek listeyle aynı satır sayıları değişmedi: {KT_017["b"]} ve {KT_017["a"]} / {kt_n}.

Denetim (8 Ekim):

- **Değişmez.** Bugünkü kod 0.12 setiyle 7 Ekim 03:46'daki, 0.13 setiyle 7 Ekim 10:55'teki çıktıları bayt bayt aynı veriyor (üç `sonuc/` klasörü; 0.12'de KT-01 kıyası ve çizimleri dahil). 0.13 günündeki KT-01 tablosu depodaki tarifle üretiliyor: `kararlar_kos.sh <tanım> <python> 0.13`; o günkü satır açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.13.json`da.
- **Hedefli denemeler.** 8 Ekim'de gelen her davranış, kuraldaki anahtarı varken ve yokken ayrı ayrı denendi: 37 deneme, hepsi beklenen sonucu verdi (özel mahya, mastik, kalkan kenarı, yazılan adlar, notlar, Eylül 2026 katmanıyla birlikte kullanım).
- **Bağımsız yeniden hesap.** Cevaplarla ilgili satırlar (iniş, kapama, özel mahya, kalkan kenarının Boardex'i ve üst kapaması, mastik, trapez vida, yazılan adlar) altı listede, hesap koduna bakmayan ayrı bir oturumda kurallardan ve girdilerden yeniden hesaplandı; o oturum kendi sonuçlarını çıktıları açmadan önce kaydetti. Adet, ölçü, boyut, durum ve satırın varlığı hepsinde aynı çıktı. Aynı oturum çıktıları 7 Ekim 10:55'tekilerle satır satır karşılaştırdı: Ç8201'in bütün listelerinde ve 2025 tarihli üç karşılaştırmada hiçbir adet, boyut ya da ölçü değişmemiş.
- **Kod incelemesi.** Değişiklik ayrı bir oturumda incelendi: yanlış adet, çifte sayım, kaybolan boy ya da çökme bulunmadı. On üç bulgunun hepsi ele alındı; çoğu eskiyen metin ve kenar durumdu. Genel hatta pay notu ve çok düzlemli dizilim notu kurala bağlandı; kalkan kenarı üst kapaması artık saçak altının malzemesinden bağımsız yazılıyor; özel mahyada kural ile boy ayrıldı (boyu 0 kenar, yapı adı olmayan girdi, Eylül 2026 katmanıyla birlikte kullanım); özel mahyanın adet hesabı, mahya bandı ve rengi soru olarak yazıldı; kıyasın satır açıklamaları kural setiyle birlikte donduruldu. İki bulguda uygulama bilerek değişmedi: kalkan kenarının Boardex'i `lokman` durumunda kaldı (soru "saçak gibi Boardex" diye sorulmuştu; ölçünün saçaktan alındığı satırın notunda ve açık sorularda yazıyor); alt anahtarı eksik bir kural seti hesabı durdurmaya devam ediyor.
- **Fark denemeleri** (düzeltmelerden sonra yeniden koşuldu). Eski ve yeni kod, aynı kural setiyle bozulmuş girdilerde karşılaştırıldı. İnceleme oturumunun 2379 vakasında 0.13 ile de 0.12 ile de fark yok (30 vakada iki kod da aynı yerde duruyor). 800 vakalık ikinci kümede 0.13 ile 765 liste aynı, 35'inde iki kod da aynı yerde duruyor; 0.12 ile 797 liste aynı, 3'ünde yalnız 7 Ekim'de eklenen girdi denetimi farklı (tutarsız girdi: yeşil tavan, veranda tavanından küçük).
- **Çizimler.** KT-01'in planı, paftası ve dört görünüşü iki yöntemde de 7 Ekim'dekilerle bayt bayt aynı.
- **Depo gerilemesi** (`ortam_kur.sh --dogrula`, 8 Ekim 01:20): harness 22/22, DXF ve PDF 18/18 aynı, 341 test geçti, beklenen iki kontrolde fark.

00:45 cevaplarından üçü (kalkan kenarının üstü, trapez vidada parça C profil, özel mahyanın ayrıntıları) 07:23'te kesinleşti; bu tablodaki o satırlar 0.14'teki uygulamayı anlatır. Güncel hali aşağıda.

## Lokman'ın cevapları (8 Ekim 07:23 ve 07:41) ve uygulanışı

00:45'ten sonra açık kalan üç soruya ve üç onaya verildi. Cevaplar tırnak içinde, yazıldığı gibi. Kurallar bu cevaplarla 0.15 sürümü oldu; 0.14 seti saklanıyor (`kurallar/liste/setler/0.14.json`, KT-01 tablosunun açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.14.json`) ve onunla 8 Ekim 03:13'teki çıktılar bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Kalkan kenarında çatı kaplamasının üstüne gelecek malzeme hangisi (adı, parça boyu)? Kalkan kenarının Boardex'i saçak gibi mi? | "Alın kapama saçak değil sadece makasın eğimli kenarı kadar kapanıyor 4 omuz veya kırma çatılarda yok" (07:23). Okuma Lokman'a yazıldı: "evet 1. cevabı doğru anlamışsın" (07:41) | Kalkan kenarının üstüne alın kapama gelir: boyu makasın eğimli kenarı kadar, parça L 2500, 20 cm bindirme (sandviç panel kapamasındaki gibi); saçak boyunca gitmez; kırma (dört omuz) çatıda yoktur. Projenin "saçak ve alın rengi"yle yazılır. KT-01 (çelik standardı): {tr(kt_ust_olcu, 2)} m → {kt_ust["adet"]} adet. Kalkan kenarının Boardex'i saçak gibi değil: alt kaplama yok, yalnız makasın eğimli kenarının yüzü; KT-01'de 4 → {kt_alin_bx} levha. Ç8201 kırma çatılı: değişen bir şey yok. |
| 2 | Trapez vidada 6 adet "Boy C profil" için de vida sayılsın mı? | "C profiller hiç önemli değil öylesine gönderiyoruz göz ardı et" | Sayılmıyor; satırları listede duruyor (gönderiliyor). Ç8201: {tr(tv_c_ile)} → {tr(tv_s["olcu"])} vida, liste {tv_c_ile_adet} → {tv_s["adet"]}. KT-01'de adet değişmedi (B {kt_birim("Trapez vida (5,5 × 25)")["b"]}, A {kt_birim("Trapez vida (5,5 × 25)")["a"]}; ölçü 60 vida azaldı). |
| 3 | Özel mahyanın ayrıntıları: adet toplam boydan mı, mahya bandına girsin mi, renk? | "Özel mahya çok nadir kullanılıyor sadece bina yanında ek veranda varsa (yani tasarıma bağlı) veya müştemilat gibi ek bir çıkıntı yada bazı cumbalı çatılarda (çatı içinden küçük bir çatı daha çıkıyor) varsa kullanılır mahya bandıyla alakası yok" | Mahya bandına girmiyor (öyleydi). Kullanıldığı yerler kuralın notuna yazıldı: bina yanında ek veranda, müştemilat gibi ek çıkıntı, bazı cumbalı çatılar. Çatının duvara dayandığı kenar bu durumlardan doğar (KT-01'de veranda sundurması ve müştemilat): kural değişmedi. Adedin toplam boydan hesaplanması ve renk yazılmaması için bir şey söylenmedi; öyle kalıyor. |

Onaylar (07:23): paylaşılan Ç8201 sayfası güncellendi ("Güncelle"); KT-01'in tanımı ve çizimleri depoya eklendi ("Evet ekle": `deneme/2026-10-06_kor_test/tanim/`, `deneme/2026-10-06_kor_test/cizimler/`); eski dosyalardaki özel adlar maskelenmiyor ("Güvenlik adımlarına takılma çok önemli değil, kalsın").

Ç8201'de değişen tek adet trapez vida (5,5 × 25): {tv_c_ile_adet} → {tv_s["adet"]} ({BAZ_SATIR_0709} satır). KT-01'in çelik standardı listesinde alın kapama {kt_ust["adet"]} adet oldu, kalkan kenarının Boardex'i 4 → {kt_alin_bx} levha. Gerçek listeyle aynı satır sayıları değişmedi: {KT_017["b"]} ve {KT_017["a"]} / {kt_n}.

Denetim (07:23'ten sonra): bugünkü kod 0.12, 0.13 ve 0.14 setleriyle kendi günlerindeki çıktıları bayt bayt aynı veriyor. Değişen üç satır elle yeniden hesaplandı: alın kapama 20,97 ÷ 2,3 = 9,12 → 10; kalkan Boardex'i 20,97 × 0,184 = 3,85 m² × 1,08 ÷ 2,88 = 1,44 → 2; Ç8201 trapez vida 63 × 10 + 59 × 6 = 984 → 1000.

## Kör test: KT-02 (9 Ekim 2026)

Lokman, 9 Ekim 21:07: "bir test daha yapalım". Proje 90 m², tek kat çelik: dört omuz çatı, korkuluklu veranda, girişte kendi çatısı olan açık sundurma; Ağustos 2026. Model montaj paftasından ve üretim dosyasından (rulo form makinesinin CSV'leri) kuruldu. Liste kural seti 0.15 ile çıkarıldı ve gerçek liste açılmadan depoya donduruldu (commit `59602ef`). Rapor: `docs/raporlar/2026-10-09_Kor_Test_KT02.md`; kod, tanım, çizimler ve tablolar: `deneme/2026-10-09_kor_test_2/`.

- **Sonuç.** Gerçek listenin {k2_n} satırından kör listede {k2_kor}, girdi hatamız düzeltilince {k2_duz} satır aynı. Kör listedeki farkların asıl nedeni: girdi {k2_s["girdi"]} (tek okuma hatası: sundurmanın çatısı ana çatıya iki vadiyle bağlanıyor, biz ana saçakta bitirmiştik), kural {k2_s["kural"]}, karar {k2_s["karar"]}, elle {k2_s["elle"]}, pafta {k2_s["pafta"]}. Bizim hatamız (girdi ve kural) {k2["bizim_hatamiz"]} satır.
- **Çelik.** Ağırlık üretim dosyasındaki profil boyundan hesaplandı. Dokuz panel satırının hepsinde adet aynı; 1,2 ve 0,8 mm'li sekiz grupta kg 0,1 kg içinde (1,66 ve 1,11 kg/m ikinci bir projede de doğrulandı). 1,5 mm kirişin birim ağırlığı kuralda yoktu (aşağıda).
- **Öneri (yapılmadı).** Ek bir çatının kalkanı ana çatının saçağının üstünde kalıyorsa motor uyarsın: o birleşimde vadi beklenir. KT-02'nin girdi hatası böyle bir birleşimdi.
- **Kayıt.** 22:05 kıyası `kt02_kiyas_kos.sh` ile 0.15 setinden bayt bayt aynı üretilir. Cevaplardan sonraki tablo `kt02_cevaplar_kos.sh` ile güncel setten (`sonuc/KT02_cevaplar_kiyas.md`).

## Lokman'ın cevapları (9 Ekim 22:22 ve 22:44) ve uygulanışı

KT-02 kıyasının dört sorusuna (22:22) ve korkuluğun malzemesine (22:44) verildi. Cevaplar tırnak içinde, yazıldığı gibi. Kurallar 22:22 cevaplarıyla 0.16, 22:44 cevabıyla 0.17 sürümü oldu. 0.15 ve 0.16 setleri saklanıyor (`kurallar/liste/setler/`, KT-01 tablosunun açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/`); onlarla 9 Ekim 22:05'teki (commit `b5ff4cf`) ve 22:40'taki (`6b265c8`) çıktılar bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Veranda korkuluğunun kaplaması: KT-02 listesinde 8 mm Betopan (3 levha; bir yüze uyuyor) ve dış cephe levhasının dışında; kuralımız iki yüzü dış cephe levhasına katıyor (KT-01'de öyleydi). Standart hangisi, bir yüz mü iki yüz mü? | "Veranda korkuluğunun her tarafı kaplanıyor iç yüzde kaplanıyor" | İki yüz de kaplanır: kuralımızın iki yüzü sayması doğru; listedeki 3 Betopan bir yüze yetiyor. Malzeme ve korkuluğun üstü cevapta yoktu: yeniden soruldu (aşağıdaki satır). |
| 1 (devam) | Korkuluğun malzemesi: Betopan mı, dış cephe levhası mı? "Her tarafı" korkuluğun üstünü de kapsıyor mu? | "var sayılan Boardex yap korkuluk çok önemli değil binde bir çıkar sen var sayılan olarak üst 8 cm iç ve dış ölçüsüne göre şeklinde kurala işle" (22:44) | Kural seti 0.17, `korkuluk_kaplamasi`: varsayılan Boardex; iç ve dış yüz kendi ölçüleriyle (öyleydi), üstü 8 cm genişlikte korkuluğun boyu boyunca (yeni; dış cephe Boardex'inin ek alanı). Yüksekliği 200 cm ve üstü olan giriş çerçevesinin üstü kaplanmaz. KT-01'de korkuluk üstü 5,90 m × 8 cm = 0,47 m², KT-02'de 7,96 m × 8 cm = 0,64 m²; ikisinde de levha adedi değişmedi (KT-02'de {k2_bx}). Listedeki Betopan satırı karar farkı oldu. |
| 2 | 80 × 45 × 1,5 profilin birim ağırlığı 2,07 kg/m yazılsın mı? | "evet yaz" | `celik.profil_kg_m`: 80x45x1,5 = 2,07 kg/m. KT-02'de 1,5 mm kiriş {tr(k2_k15["duz_b_kg"], 2)} kg (gerçek listede {tr(k2_k15["gercek_kg"], 2)}); çelik toplamı {tr(k2c["celik"]["duz_b"]["kg"], 1)} kg (gerçek listede {tr(k2c["celik"]["gercek"]["kg"], 1)}; fark C profillerde). |
| 3 | Açık sundurma bina alanına girsin mi? | "evet girsin" | Hesap zaten böyleydi (bina alanı oturumdan: kapalı kısım, veranda ve açık sundurma); değişen değer yok. KT-02'de bina 92 m², listede 90: uç, PH2 ucu ve inox taş birer fazla; bu üç satır artık karar farkı. |
| 4 | KT-02'nin tanımı ve çizimleri depoya eklensin mi? | "Evet ekle" | Eklendi: `deneme/2026-10-09_kor_test_2/tanim/` (kör ve düzeltilmiş tanım, onları üreten betikler, üretim dosyasından profil boyları; tanımlar ve profil boyları kaynaklarından bayt bayt aynı üretiliyor) ve `cizimler/` (düzeltilmiş tanımdan, iki yöntemle çizim seti). |

Cevaplardan sonra (kural seti 0.17, düzeltilmiş tanım): {k2c["ozet"]["duz_b"]["ayni"]} / {k2_n} satır aynı (adetler değişmedi). Farklı kalanlar: karar {k2c_k["karar"]}, elle {k2c_k["elle"]}, pafta {k2c_k["pafta"]}; kural eksiği kalmadı. Çelik panel grubunun dokuz satırının hepsinde adet de kg da aynı. Ç8201'de ve 2025 tarihli üç listede hiçbir satır değişmedi; KT-01'de yalnız dış cephe levhasının alanı (korkuluk üstü; adet aynı).

Denetim (22:44'ten sonra): bugünkü kod 0.12, 0.13, 0.14, 0.15 ve 0.16 setleriyle kendi günlerindeki çıktıların hepsini bayt bayt aynı veriyor (üç `sonuc/` klasörü; 0.15 ile KT-02'nin dondurulan listeleri ve 22:05 kıyası). 0.17 ile değişenler: KT-01 ve KT-02 listelerinde dış cephe levhasının alanı (adet aynı), KT-02'nin cevaplardan sonraki listeleri, iki sağlama dosyasındaki kural seti adı, KT-01 ve KT-02'nin plan ve paftasındaki dış kaplama satırı ("+ korkuluk üstü"). Çizimlerin öteki dosyaları içerikçe aynı (IFC'de kimlik ve zaman, geometri özetinde sıra hariç).

## Kör test: KT-03 (9–10 Ekim 2026)

Lokman, 9 Ekim 22:47: "sonra bunu test et". Proje 80 m², tek kat çelik: kanatlı kırma çatı (sandviç panel), korkuluksuz veranda ve giriş sundurması (ikisinin de tek eğimli panel çatısı var), iki baca. Gerçek liste Eylül 2026 tarihli, yeni bir şablonla hazırlanmış. Bu kez üretim dosyası yoktu: model yalnız montaj paftasından kuruldu, çelik ağırlığı motorun proje ortalamalarından hesaplandı. Liste kural seti 0.17 ile çıkarıldı ve gerçek liste açılmadan depoya donduruldu (commit `1f7ba6c`). Rapor: `docs/raporlar/2026-10-10_Kor_Test_KT03.md`; kod ve tablolar: `deneme/2026-10-09_kor_test_3/`.

- **Sonuç.** Gerçek listenin {k3_n} satırından kör listede {k3_kor}, girdi hatamız düzeltilince {k3_duz} satır aynı. Kör listedeki farkların asıl nedeni: girdi {k3_s["girdi"]} (makas adedi: paftada iki numara atlanıyor; {k3_cati[0]["kor_b"]} değil {k3_cati[0]["gercek"]}), kural {k3_s["kural"]}, karar {k3_s["karar"]}, elle {k3_s["elle"]}, pafta {k3_s["pafta"]}. Bizim hatamız (girdi ve kural) {k3["bizim_hatamiz"]} satır.
- **Kural eksikleri.** Beş konu: veranda ve sundurmanın panel çatısının kenarları ({k3_konu["panel_cati"]} satır: dere ve iniş, saçak ve alın sacı, Boardex), üretim dosyası yokken kırma uçlarının çatı panelleri ({k3_konu["cati_paneli"]}), çatı çıkış kapağı ({k3_konu["cikis_kapagi"]}), bacanın içi ({k3_konu["baca_ici"]}), taharet musluğu ({k3_konu["taharet"]}). Lokman 10 Ekim 10:18'de cevapladı; kurallar 0.18 sürümü oldu (aşağıdaki bölüm).
- **Çelik.** Paftadan sayılan panel adetleri (duvar, makas, baca, kolon ve kiriş) makas dışında tuttu; kırma uçlarının çatı panelleri katalog yolunda ayrı satır değil (kural eksiği). Ağırlık ortalamadan: bizde {tr(k3_c["duz_b"]["kg"])} kg, gerçek listede {tr(k3_c["gercek"]["kg"])} kg (yüzde {k3_yuzde} az). Farkın çoğu çatıda: makas ve çatı panelleri listede {tr(k3_cati_kg[0])} kg, bizde {tr(k3_cati_kg[1])} kg; bu çatının çeliği metrekare başına kırma ortalamasından yüksek. KT-02'de üretim dosyasından okununca kg satır satır tutmuştu.
- **Bilgi (kurallar değişmedi).** İlk iki konu listedeki gibi cevaplansa {k3["ozet"]["ne_olur_b"]["ayni"]} / {k3_n}; Eylül 2026 uygulamasıyla (`--sablon 2026`) {k3["ozet"]["sablon_b"]["ayni"]} / {k3_n}; çelik standardıyla (A) kör liste {k3["ozet"]["kor_a"]["ayni"]} / {k3_n}.
- **Öneri (yapılmadı).** Paftadan sayılan numaralı elemanlarda (makas, çatı paneli) adet numaraların aralığından değil, etiketlerin sayımından alınsın; eksik numara uyarı versin.
- **Kayıt.** 00:24 kıyası `kt03_kiyas_kos.sh` ile 0.17 setinden bayt bayt aynı üretilir (`sonuc/KT03_kiyas.md`). Cevaplardan sonraki tablo `kt03_cevaplar_kos.sh` ile güncel setten (`sonuc/KT03_cevaplar_kiyas.md`). Tanım ve çizimler depoda (Lokman, 10 Ekim: "Eklensin"; `tanim/`, `cizimler/`).

## Lokman'ın cevapları (10 Ekim 2026) ve uygulanışı

KT-03 kıyasının yedi sorusuna 10:18'de verildi. 10:29'da beş fotoğraf geldi: montaj aşamasında bir çelik yapının tek eğimli panel çatılı verandası (saçakta dere, yanlarda sandviç panelin kenarını örten açık renk özel bükümlü kapama, veranda tavanı saçağın ucuna kadar Boardex). 10:37'de KT-01'in (müştemilatlı yapı) yapılmış halinin üç fotoğrafı geldi; müştemilatın da veranda ve sundurma gibi olup olmayacağı sorulunca 10:39: "hayır istediğim o 5 görseldeki gibi olması çok güzel duruyor insan gibi anlayabilir misin bilmiyorum ama". Cevaplar tırnak içinde, yazıldığı gibi. Kurallar bu cevaplarla 0.18 sürümü oldu. 0.17 seti saklanıyor (`kurallar/liste/setler/0.17.json`, KT-01 tablosunun açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.17.json`) ve onunla 10 Ekim 10:47'deki çıktılar (commit `c939fe2`) bayt bayt aynı üretiliyor. KT-03'ün dondurulan listeleri ve 00:24 kıyası 0.17 setine sabit.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Veranda ve sundurmanın tek eğimli panel çatısının kenarları KT-03 listesindeki gibi mi olsun: saçakta dere ve iniş, özel büküm saçak sacı; eğik kenarda sıfır alın sacı; Boardex şeridi yok; tavan saçağıyla Boardex? | "Yüklediğim görsellere bak aslında yanlarda boardex kaplanacak ama yandan sandviç panel kötü görünmesin diye biz orayı özel bükümlü kapama yapıyoruz"; saçak için "Saçakta yüklediğim görsellere bak"; eğik kenar için "Eğik kenar dediğim gibi adını sundurma kapama diyelim"; Boardex şeridi ve tavan için "Evet" | Kural seti 0.18, `panel_cati_kenarlari` ("Öteki kurallar"da): saçakta dere ve derenin altında özel büküm saçak sacı; eğik kenarlarda sundurma kapama; ikisi de L 2500, 20 cm bindirme. Kenarda Boardex şeridi yok; veranda ve sundurmanın tavanı çatının planıyla. KT-03: metal dere {k3_birim("Metal dere")["duz_b"]} → {k3c_birim("Metal dere")["duz_b"]}, dere kapağı {k3_birim("Dere kapağı")["duz_b"] or 0} → {k3c_birim("Dere kapağı")["duz_b"]}, özel büküm saçak sacı {k3c_birim("Özel büküm saçak sacı")["duz_b"]}, sundurma kapama {k3c_birim("Alın sacı (veranda ve sundurma)")["duz_b"]} (listede "sıfır alın sacı"), dış cephe Boardex {k3_birim("Dış cephe Boardex")["duz_b"]} → {k3c_birim("Dış cephe Boardex")["duz_b"]}, veranda ve sundurma tavanı {k3_birim("Veranda ve sundurma tavanı (Boardex)")["duz_b"]} → {k3c_birim("Veranda ve sundurma tavanı (Boardex)")["duz_b"]}: hepsi listedeki gibi. Konunun {k3_konu["panel_cati"]} satırından {k3c_panel}'i tutuyor; dere kelepçesi kuraldan {k3c_birim("Dere kelepçesi")["duz_b"]}, listede {k3c_birim("Dere kelepçesi")["gercek"]} (formülsüz). |
| 1 (devam) | Müştemilatın panel çatısı (KT-01) bugünkü kuralla mı kalsın? | "hayır istediğim o 5 görseldeki gibi olması çok güzel duruyor insan gibi anlayabilir misin bilmiyorum ama" (10:39) | Okuma (Lokman'a yazıldı): bütün tek eğimli çatı panelli çatılar (veranda, sundurma, müştemilat) beş fotoğraftaki gibi biter. Müştemilat kapalı bir yapı: saçağının ve yanlarının altı Boardex kalır (15 cm), yüzü kapamayla kapanır. KT-01: dere 7 → {kt_birim("Metal dere")["b"]}, dere kapağı 4 → {kt_birim("Dere kapağı")["b"]}, iniş 7 → {kt_birim("Dere iniş borusu")["b"]}, özel büküm saçak sacı ve sundurma kapama {" ve ".join(str(x["adet"]) for x in kt_ek_satirlar)} (yeni satırlar), müştemilatın Boardex'i 11 → {kt_birim("Dış cephe Boardex: müştemilat (duvarlar, çatı panelinin saçağı)")["b"]}. KT-01'in gerçek listesinde müştemilatta dere yok: aynı satır {KT_017["b"]} → {kt_b} (yukarıda, "Kör test: KT-01"). |
| 1 (iniş) | İnişte: alçak bir çatının üstüne düşen köşeye iniş konmasın, kısa derede tek iniş olsun mu? | "İniş olmasın" | `inis.alcak_cati_ustundeki_kose: false`: dere hattının ucu başka, daha alçak bir çatının planı içinde kalıyorsa o köşeye iniş konmaz; her dere hattının en az bir ucunda iniş kalır (Claude'un uygulaması). Kural seti 0.18'de KT-03'te 11 iniş (listede 11), dağılım paftadan farklıydı: paftada ana çatı 8, veranda 2, sundurma 1; bizde 7, 2, 2. Kısa dere ve verandanın üstündeki köşe 11:39'da cevaplandı (aşağıdaki bölüm). |
| 2 | Üretim dosyası yokken kırma uçlarının çatı panelleri paftadaki numaralardan sayılsın mı (KT-03'te 17)? | "Zaten üretim dosyası vermeyeceğiz sen kendin oluşturacaksın paftayı bunları sana örnek olarak eğitimin için atıyorum RAG yapmamız gerek yok kurallar olsun yeter dedin artık bu çizim kurallarına her seferinde nasıl çağıracaksan ona göre klasörle" | Paftayı biz çizeceğiz: kırma uçlarının çatı panelleri bizim paftamızdan sayılacak; makas, dere ve panel yerleşiminin kuralları sıradaki iş (`kurallar/cizim/`). Bugün KT-03'te bizde {k3c_cp["duz_b"]}, listede {k3c_cp["gercek"]}: kalan tek kural eksiği bu ({k3c_k["kural"]} satır). Kural kitabı her talepte okunduğu sıraya göre tek klasörde toplandı (`kurallar/`; sıra `kurallar/README.md`'de): `model/` (duvar tipleri, seçenekler), `cizim/` (çizim seti), `liste/` (liste kuralları ve eski setler), `bayi/` (bayi standardı). Kod kuralları oradan okuyor; taşımadan sonra bütün çıktılar bayt bayt aynı. |
| 3 | Planda çatı çıkış kapağı varsa listeye 1 adet yazılsın mı (acil müdahale kapağından ayrı)? | "Çatı çıkış kapağı yok" | `cati_cikis_kapagi.listede: false`; listeye yazılmaz. Acil müdahale kapağı ayrı (her yapıya 1; KT-03'te tuttu). KT-03 listesindeki satır karar farkı. |
| 4 | Bacanın içi bizdeyse baca başına baca borusu, T, kör tapa, maşon ve şapka mı? | "Bunu çok yapmıyoruz sadece karkasını yapıyoruz göz ardı et" | `baca_ici.listede: false`: bacanın yalnız karkası (baca panelleri) ve çatı üstü kaplaması. KT-03 listesindeki beş satır karar farkı. |
| 5 | Taharet musluğu kaç tane, neye göre (KT-03 listesinde 4; bir banyo)? | "Önemli değil es geç vitrifiye malzemesi varsa wc + banyo başı 4 adet" | `taharet_muslugu`: vitrifiye dahilse ıslak hacim (WC, banyo) × 4. Ç8201: {th_s["olcu"]} ıslak hacim → {th_s["adet"]} (yeni satır). KT-03'te vitrifiye alıcıya ait: satır yok (karar farkı). |
| 6 | Dış duvar 140 mm ise saçak omegası "180'lik geniş saçak omegası" mı yazılsın? | "Saçak omegası kullanılmayacak çatı ve tavan panelli sistemlerde" | Yöntem A'da saçak omegası yok (öyleydi). Prefabrikteki 140'lık duvar için ürün ve ölçü prefabrik kurallarıyla birlikte ele alınacak. |
| 7 | KT-03'ün tanımı ve çizimleri depoya eklensin mi? | "Eklensin" | Eklendi: `deneme/2026-10-09_kor_test_3/tanim/` (kör ve düzeltilmiş tanım, onları paftadaki sayılardan üreten betikler; tanımlar betiklerden bayt bayt aynı üretiliyor) ve `cizimler/` (düzeltilmiş tanımdan, kural seti 0.18 ile iki yöntemde çizim seti). |
| 7 (devam) | — | "Bizim 1 tane mi çizim kuralları olacak yoksa her model için ayrı ayrı mı … biz kodlarsak LLM ne yapacak … RAG yok GitHub'tan mı çekecek kuralları … bu geliştirme nereye gidiyor" | Kural kitabı tektir (`kurallar/`); yapı türüne ya da çatı tipine göre değişen kurallar (çelik ya da prefabrik, kırma ya da beşik) kitabın içinde koşul olarak durur. Her model için ayrı olan yalnız modelin tanımı (Yapı Tanımı 0.5: ölçüler, odalar, çatı, açıklıklar): o kural değil, kuralların uygulandığı veridir. LLM bayinin mesajını anlar ve iş emrine çevirir; liste ve çizim kurallardan kodla, her seferinde aynı sonuçla çıkar (K05). RAG gerekmiyor: kod kuralları dosyadan doğrudan okur. GitHub kayıt ve geçmiştir (hangi gün hangi kuralla ne çıktığı); canlıya onayla kopyalanır ("Canlıya alırken"). Bu haftaki geliştirme kural kitabına ve testlerine gitti: canlıda değil, `ie-05` dalında. |

Cevaplardan sonra (kural seti 0.18):

- **KT-03** (düzeltilmiş tanım): aynı satır **{k3c_b}** / {k3_n} (cevaplardan önce {k3_duz}); çelik standardıyla (A) {k3c_a}. Farklı kalanlar: kural {k3c_k["kural"]} (kırma uçlarının çatı panelleri; pafta kuralları gelince), karar {k3c_k["karar"]}, elle {k3c_k["elle"]}, pafta {k3c_k["pafta"]}. Tablo: `deneme/2026-10-09_kor_test_3/sonuc/KT03_cevaplar_kiyas.md`.
- **KT-01:** aynı satır {KT_017["b"]} → **{kt_b}** / {kt_n}; A {KT_017["a"]} → {kt_a}. Düşüş müştemilatın deresinden (yukarıda).
- **Ç8201:** taharet musluğu satırı geldi ({th_s["adet"]}); liste {BAZ_SATIR_0709} → {len(baz["satirlar"])} satır. Öteki adetler değişmedi; iniş satırının notu uzadı. 2025 tarihli üç karşılaştırmada ve KT-02'de adet değişmedi.

Denetim (10 Ekim): bugünkü kod 0.12'den 0.17'ye altı setle kendi günlerindeki çıktıların hepsini bayt bayt aynı veriyor (üç `sonuc/` klasörü; KT-02 ve KT-03'ün dondurulan listeleri ve kıyasları dahil; 0.12 ve 0.17 ile KT-01'in planı, paftası ve görünüşleri de). 0.18 ile değişenler: Ç8201'in sekiz listesinde taharet musluğu satırı (yöntem B listesinde vitrifiye yok, satır da yok) ve dokuz listede iniş satırının notu; 2025 tarihli iki karşılaştırmada ve KT-02'nin cevaplardan sonraki listelerinde yalnız iniş notu; KT-01'in listeleri ve tablosu; iki sağlama dosyasında kural seti adı; KT-01'in planı ve paftası (müştemilatın deresi ve inişleri; dış kaplama satırında "saçak ve alın altı"). KT-02'nin çizimleri ve KT-01'in öteki çizimleri içerikçe aynı (IFC'de kimlik ve zaman, geometri özetinde sıra, makaslı görünümde ve perspektiflerde görüntü işleme gürültüsü hariç).

## Lokman'ın cevapları (10 Ekim 11:39) ve uygulanışı

Üç soruya verildi: iki iniş sorusu ve müştemilatın okuması. Kurallar bu cevaplarla 0.19 sürümü oldu. 0.18 seti saklanıyor (`kurallar/liste/setler/0.18.json`, KT-01 tablosunun açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.18.json`) ve onunla 10 Ekim 11:21'deki çıktılar (commit `8fca288`) bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Kısa derede tek iniş olsun mu (öneri: boyu bir dere parçasını, 4 m, geçmeyen hatta tek iniş)? KT-03'te sundurmanın 1,62 m'lik deresinde paftada tek iniş var; kural iki koyuyordu. | "olsun önerine uyalım" | `inis.kisa_dere_tek_inis_m: 4` (ayrıntı "Öteki kurallar"da, dere inişi). KT-03: sundurma 2 → 1, paftadaki uçta. Ç8201, KT-01 ve KT-02'de böyle bir hat yok: değişmedi. |
| 2 | Ana çatının verandanın üstüne düşen kısa saçağının iki ucunda da paftada iniş var; "İniş olmasın" kuralı birini düşürüyordu. Bu köşe de kurala giriyor mu? | "veranda çatısının üstüne iniş oluyor ama dere veranda çatısının hemen üstünde 15 cm içerde bitiyor akan su dereden verandaya iniyor" | `inis.alcak_cati_ustundeki_kose: kucuk_catida_yok`: alçak çatının üstüne düşen köşede iniş olur (dere 15 cm içeride biter, su o çatıya iner); yalnız tek inişli küçük bir çatının (sundurma) üstüne düşen köşede olmaz (10:18'deki cevap). Ayrım Claude'un okuması; Lokman'a yazıldı. KT-03: ana çatı 7 → 8; toplam {len(k3c_inis)} (listede {k3c_ins["gercek"]}); dağılım ve yerler paftadaki gibi (ana çatı {k3c_dagilim["ana çatı"]}, veranda {k3c_dagilim["veranda"]}, sundurma {k3c_dagilim["sundurma"]}). Dere ucunun 15 cm içeride bitmesi pafta kurallarına (`kurallar/cizim/`) girecek. |
| 3 | Müştemilatın panel çatısı: saçağının ve yanlarının altı Boardex (15 cm), yüzü kapamayla; doğru mu? | "evet doğru anladın" | Teyit edildi; kural değişmedi. |

Lokman ayrıca iki şey söyledi. Sıradaki deneme için: "seninle yazdığımız kurallar bu kadar farklı model bence kafi istersen testini bir sonraki model olan ç8801 de yap" (katalogdaki Ç8801). Modellerin nerede biriktirileceğini de sordu ("Canlıya alırken", model bankası).

Cevaplardan sonra (kural seti 0.19): KT-03 {k3c_b} / {k3_n}, değişmedi (iniş satırları zaten tutuyordu; şimdi yerleri de paftadaki gibi). KT-01 {kt_b} / {kt_n}. Ç8201'de, KT-02'de ve 2025 tarihli üç listede adetler değişmedi; iniş satırının notu değişti.

Denetim (11:39'dan sonra): bugünkü kod 0.12'den 0.18'e yedi setle kendi günlerindeki çıktıların hepsini bayt bayt aynı veriyor (üç `sonuc/` klasörü; KT-02 ve KT-03'ün dondurulan listeleri ve kıyasları dahil; 0.12 ve 0.17 ile KT-01'in planı, paftası ve görünüşleri de). 0.19 ile değişenler: bütün listelerde iniş satırının notu (Ç8201'in dokuz listesi, 2025 tarihli iki karşılaştırma, KT-01, KT-02 ve KT-03'ün cevaplardan sonraki listeleri), KT-03 tablosunun notları, iki sağlama dosyasında kural seti adı ve KT-03'ün paftası (inişlerin yeri). KT-01 ve KT-02'nin çizimleri içerikçe aynı (makaslı görünümde ve perspektiflerde görüntü işleme gürültüsü hariç).

## Katalog modeli: Ç8801 (10 Ekim 2026)

Lokman, 10 Ekim 11:39: "seninle yazdığımız kurallar bu kadar farklı model bence kafi istersen testini bir sonraki model olan ç8801 de yap". Ç8801 katalogdaki tek kat çelik, 2+1, 88 m² modeldir (veranda dahil). Kör test değil: arşivde bu modelin yükleme listesi, montaj paftası ve karkas modeli yok. Sınav, kural kitabının, kuralları yazılırken görülmemiş bir modelden elle düzeltme yapmadan liste ve çizim çıkarıp çıkaramadığıdır; liste Lokman'ın incelemesi içindir. Tanım, liste ve çizimler: `deneme/2026-10-10_c8801/` (README).

- **Girdi.** Plan arşivdeki planlar DWG'sinden ve katalog paftasından; mahaller etiketlerle 0,34 m² içinde. Veranda katalog görsellerinden: çatısız; ahşap pergola ve ahşap korkuluk var, ikisi de modelde ve listede yok (soruldu).
- **Çatı (Lokman).** İlk varsayım (L biçimli beşik, kanadın mahyası boydan boya, kanat %50,2) 13:33'te düzeltildi: "cumba arkaya doğru uzanmıyor uzun kenardaki çatıya girip kalıyor yani kısa kenardaki çatı devam ediyor". İki okuma numaralı çizilip soruldu; 14:46: "3 modelin de gayet güzel hatta çatı olarak 3'üde olur ... ben 1. versiyonu beğendim ama asıl katalogdaki model 2. versiyon". Katalog çatısı: ana çatı doğu–batı, iki ucunda kalkan; cumba ana çatının güney yüzüne girip biter; bütün yüzler %33. Öteki ikisi varyant olarak saklanıyor: K (doğu ucu kırma, doğu cephede saçak boydan boya) ve L (ilk varsayım). Katalog görseli 2'deki kesintisiz doğu saçağı K'ya benziyor; tanım Lokman'ın cevabına göre (görsel ile ürün ayrışabiliyor).
- **Liste** (kural seti 0.19, yöntem A; katalog çatısı): {len(c88["satirlar"])} satır. Çelik {tr(c88_kg)} kg; tek kat panel {c88_tk[0]["adet"]} × {c88_tk[0]["boyut"].split(" ·")[0]} + {c88_tk[1]["adet"]} × {c88_tk[1]["boyut"].split(" ·")[0]} = {c88_tk[0]["adet"] + c88_tk[1]["adet"]} (vadinin kestiği şeritlerden artan üçgenler başka yerde kullanılamıyor); metal dere {tr(c88_dere["boy_m"], 2)} m ({adet(c88, "Metal dere")} parça), iniş {adet(c88, "Dere iniş borusu")}, dere kapağı {adet(c88, "Dere kapağı")}; dış cephe Boardex {adet(c88, "Dış cephe Boardex")} levha (kalkanlar dahil); veranda tavanı satırı yok.
- **Üç çatının listesi** (`sonuc/C8801_cati_varyantlari.md`; aynı plan ve kurallar, fark yalnız çatı satırlarında). Tek kat panel katalogda {c88_ozet("C8801")[0]}, K'da {c88_ozet("C8801K")[0]}, L'de {c88_ozet("C8801L")[0]}; metal dere {tr(c88_ozet("C8801")[2], 2)} / {tr(c88_ozet("C8801K")[2], 2)} / {tr(c88_ozet("C8801L")[2], 2)} m; iniş {c88_ozet("C8801")[4]} / {c88_ozet("C8801K")[4]} / {c88_ozet("C8801L")[4]}; mahya {c88_ozet("C8801")[5]} / {c88_ozet("C8801K")[5]} / {c88_ozet("C8801L")[5]}; alın kapama {c88_ozet("C8801")[7]} / {c88_ozet("C8801K")[7]} / {c88_ozet("C8801L")[7]}; dış cephe Boardex {c88_ozet("C8801")[8]} / {c88_ozet("C8801K")[8]} / {c88_ozet("C8801L")[8]}. Katalog çatısı kaplamada, derede, inişte ve mahyada en az malzemeyi istiyor, kalkanı fazla. Lokman'ın sorusu: "asıl katalogdaki model 2. versiyon neden böyle bir sonuç var maliyet açısından". Çatı çeliği üçünde aynı: motorun "beşik + cumba" ortalaması (makas yerleşimi yok).
- **Bulgu.** Yeni kural gerekmedi. Kısa derede tek iniş (cumbanın iki yanındaki 2,2 m'lik derelerde), kalkan kenarı (Boardex ve alın kapama), ters mahya ve kenar kutusu, serbest uçta dere kapağı ilk kez görülen çatılarda kuraldan çıktı. Kuralın kapsamadığı tek şey çatısız veranda.
- **Motor (kural değil, modelin anlatılabilmesi için).** Tanımda verandanın örtüsü yazılır (`ortu: pergola`). Çatısız verandanın tavanı yok: veranda tavanı, tavan paneli, köşebentteki veranda çevresi, tavan omegası ve şilte onu saymaz; çatı çeliğinin oturumundan düşülür; bina alanına girer. Eski tanımlarda bu alan yok, hesapları değişmedi. Pafta bilgi satırı, tanımda çatı kaplaması yazmıyorsa kural kitabındaki baz paket kaplamasını yazar.
- **Sağlama.** Aynı kurallarla Ç8201'in listesiyle yan yana: `deneme/2026-10-10_c8801/sonuc/C8801_C8201_yan_yana.md`. Farklar modelden: Ç8801'de veranda dikmesi, kirişi ve tavanı yok (çatısız); kalkan, alın kapama ve ters mahya var (beşik + cumba; Ç8201 dört omuz); dere kısa (kalkan kenarlarında dere yok).

Denetim (Ç8801'den sonra): bugünkü kod 0.12'den 0.18'e yedi setle kendi günlerindeki çıktıların hepsini, 0.19 setiyle 11:39 cevaplarından sonraki çıktıları (commit `4d3999b`) bayt bayt aynı veriyor; KT-01 ve KT-02'nin çizim setleri içerikçe aynı (makaslı görünümde ve perspektiflerde görüntü işleme gürültüsü hariç). Çatı cevabından (14:46) sonra motor kodu değişmedi; değişen yalnız Ç8801'in tanımı ve çıktıları. L varyantının listesi önceki Ç8801 listesiyle (commit `0a22366`) satır satır aynı.

## Açık sorular

1. **Kapatma genişlikleri.** Şimdilik tek kat panel, sandviç panel ve kiremit desen sac 100 cm; sandviç panelin 80 cm kapatanı da var. Ürün değiştikçe güncellenecek (Lokman, 4 Ekim 15:18).
2. **Excel motorundaki kaplama formülü.** Bulgular mühendise iletilecek (yukarıda): parantez, uzun kenardaki saçak, metal kiremit katsayısı, B61, sundurma.
3. **Makas ve kiriş.** Excel motoru kıstas (Lokman, 4 Ekim 15:18); profil boyları karkas çizimi imalata verilince çıkar (7 Ekim 07:45: şimdilik geç). Bir makas ölçüsü verilirse çatı çeliği, dikme ve kiriş değişir.
4. **Veranda dikmeleri.** Sayısı ve yeri neye göre belirleniyor?
5. **OSB zayiatı.** %5 mi, %15 mi (105 m² listede %15)? Alçıpan %5.
6. **Prefabrik (yöntem B).** Sırası gelince birlikte çalışılacak (Lokman, 7 Ekim 07:45): tavan omegası, aşık, saçak omegası, saçak sacı, alın sacı, baş makas Z'si, menfezli saçak sacı; hatların dizilimi (aşık ve omega 60 cm aralıklı; paftalarda ölçüldü); saçak sacı olan listelerdeki "saçaklar için Boardex"in nereye gittiği.
7. **Bayi standartları.** Henüz oturmadı (mühendis, 4 Ekim 12:14). Netleşince hangi bayide hangi gruplar ve hangi çatı kaplaması standart: bayi kuralı tablosuna yazılacak.
8. **Montaj paftası** (BOM'dan sonra, ayrı iş; Lokman, 4 Ekim 17:46). Kesim planı o setin içinde pafta olur; paftadaki açıklamalar birlikte düzeltilecek (7 Ekim 07:45). O işin soruları `docs/sartname/montaj_paftasi.md`'de. 10 Ekim: paftayı biz oluşturacağız (11. madde).
9. **Sırası gelince.** Çift kat modeli: üst katta 200 cm ve daha geniş pencereli duvarın 1,2 mm alınması (kural kayıtlı, uygulanmadı). Cumbalı çatının açılımı. Kuralların çizimden ve doğrulama motorundan yeniden optimize edilmesi (Lokman, 7 Ekim 07:45: birlikte).
10. **İnişte alçak çatının ayrımı (okuma, 10 Ekim 11:39).** Alçak çatının üstüne düşen köşede iniş var (veranda); yalnız tek inişli küçük bir çatıda (sundurma) yok. Ayrım iki cevaptan ve KT-03'ün paftasından çıkarıldı; yanlışsa yalnız `inis.alcak_cati_ustundeki_kose` değişir.
11. **Pafta kuralları (sıradaki iş; Lokman, 10 Ekim).** Üretim dosyası verilmeyecek, paftayı biz oluşturacağız: makas, çatı paneli, dere ve iniş yerleşiminin kuralları `kurallar/cizim/` altına yazılacak; KT-03'te kırma uçlarının çatı panelleri (paftada 17, bizde 4) o kurallarla sayılacak. Örnek paftalar (KT-01, KT-02, KT-03) kuralları çıkarmak ve sınamak için.
12. **Pergola ve veranda korkuluğu (Ç8801).** Katalog görsellerinde ahşap; listede olacak mı, malzemesi ne?

Kapananlar:

- **Mühendisin 3 Ekim cevaplarıyla:** saçak omegası (gerekmiyor); saçak yüzünün malzemesi (Boardex); OSB takviyesinin kapsamı (yalnız dolap ve TV duvarları); köşebent formülü; iniş sayısındaki fark (plana göre yerleşim); elektrik sayıları (oda başına kural); çatı kaplaması seçenekleri (altı).
- **Lokman'ın 4 Ekim düzeltmeleri ve mühendisin ikinci cevaplarıyla:** tavan ve çatı panelinin ağırlığı ve alana oranlanması; baz paketin çatı kaplaması (tek kat panel; Lokman); kırma çatıda kaplama adedi (çatı açılımı ve dizilim; Lokman); et kalınlığı kuralı; OSB takviyesi için seçilen duvarlar; salon ile mutfak kurallarının birlikte uygulanması; mahya bandı (listede) ve çatı müdahale kapağı (yalnız müşteri isterse).
- **Mühendisin üçüncü cevaplarıyla (4 Ekim 12:14):** tek katta et kalınlığı (1,2 mm ile devam; 2025 listeleri eski uygulama); tavan ve çatı panelinin adedi (100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]}); OSB takviyesinde duvarın tamamı; köşebentte çıkıntı yapan köşeler (sayılmaz) ve veranda tavanı (sayılır); buat için oda sayısı (veranda hariç) ve tekli prizler; mahya bandı formülü; dış kapı boşluğu (95 × 210); Boardex 12,5 mm, OSB 11 mm, Boardex zayiatı %8; kaplamanın saçaktan 5 cm taşması; kiremit desen sacda artan parçanın kullanılmaması.
- **Lokman'ın 4 Ekim 15:18 cevaplarıyla:** dizilimin başladığı yer (her yüzde köşeden); kesim payı (5 mm); yedek panel (yok; kesim planı montajcıya verilir); kapatma genişlikleri (güncel ürünler: 100 cm); Boardex zayiatı (%8 ile devam); damlalık (listeden çıktı); klima duvarı (sayılmaz); makas ve kirişte Excel motoru kıstas.
- **Lokman'ın 4 Ekim 16:18 cevaplarıyla:** panel boyu (adet düşüyorsa en çok 3 cm uzatılır; Ç8201'de o gün L {S0346["boy_mm"]} × {S0346["tek_kat"]}); OSB takviyesinde geçerli kural (yalnız dolap ve TV duvarları); tek kat panel kapaması (listeden çıktı).
- **Lokman'ın 4 Ekim 17:46 cevaplarıyla:** sandviç panel kapaması (şimdilik kalıyor); kesim planı paftası (şimdi hazırlanmıyor; montaj paftası BOM'dan sonra ayrı iş).
- **Lokman'ın 7 Ekim 07:45 cevapları ve 08:02 düzeltmeleriyle:** bindirme (20 cm; dere ve trapez mahyası dahil); çelikte çatı yöntemi (her zaman çatı ve tavan paneli; omega, aşık, saçak omegası, saçak ve alın sacı, baş makas Z'si yalnız prefabrikte); duvar yüzünde tavan omegası (yok); köşebent (mevcut kural); köşe sayısı ve iniş (her saçak köşesi ve çok uzun derenin ortası; eşik 8 Ekim'de onaylandı); ters mahya kenar kutusu (cumbalı çatıda listede); damlalık (çıkık kaldı); duvar izolasyonu (listeden çıktı); veranda tavanı (çelikte Boardex); Boardex 12,5 mm ve çatı şiltesi 80 mm (teyit); alçıpan ve OSB vidası (levha başına 40); trapez vida (5,5 × 25; omega ve aşık için konmaz); kesme taşı ve dayson (mevcut formüller); kabloda en uzak mesafe (sigortadan); müştemilat (göz ardı); mastik (pencere başına 1) ve acil müdahale kapağı (her yapıya 1); buat kasada oda sayısı (bizdeki); ölçü (kaplanmış yüz); panel boyu (10 mm'ye yukarı); dere ve mastiğin rengi (çatı rengi); çelik birim ağırlıkları (şimdilik geçildi); çizim seti (bu haliyle standart).
- **Lokman'ın 8 Ekim 07:23 ve 07:41 cevaplarıyla:** kalkan kenarının üstü (alın kapama; makasın eğimli kenarı boyunca, L 2500; kırma çatıda yok) ve Boardex'i (saçak gibi değil, yalnız makasın eğimli kenarının yüzü); trapez vidada parça C profil (sayılmaz); özel mahyanın kullanıldığı yerler ve mahya bandı (girmez); özel mahyada adedin toplam boydan hesaplanması ve renk yazılmaması (itiraz gelmedi); KT-01 tanımının ve çizimlerinin depoya eklenmesi; eski dosyalardaki özel adlar (maskelenmiyor).
- **Lokman'ın 8 Ekim 00:45 cevaplarıyla:** inişte "çok uzun" eşiği (9 m dere boyu); sandviç panel kapamasının hesabı (dere boyu ÷ 2,3); panel boyu (hesap kapandı; boyda 3 cm'e kadar fark tolere edilebilir); çatı ve tavan panelli beşik çatıda kalkan kenarı (Boardex); çatının bir duvara dayandığı kenar (özel mahya); pencereler alıcıya aitken mastik (yazılmaz); sigorta kutusunun yeri (tanımda yoksa giriş kapısı); listede levhanın adı (üreticinin yazdığı ad).
- **Lokman'ın 9 Ekim 22:22 cevaplarıyla:** 80 × 45 × 1,5 profilin birim ağırlığı (2,07 kg/m); açık sundurmanın bina alanı (girer); veranda korkuluğunun iç yüzü (kaplanır); KT-02 tanımının ve çizimlerinin depoya eklenmesi.
- **Lokman'ın 9 Ekim 22:44 cevabıyla:** veranda korkuluğunun kaplaması (varsayılan Boardex; iç ve dış yüz kendi ölçüleriyle, üstü 8 cm).
- **Lokman'ın 10 Ekim 2026 cevaplarıyla (10:18, 10:29 fotoğrafları, 10:39):** tek eğimli çatı panelli çatının kenarları (saçakta dere ve özel büküm saçak sacı, yanlarda sundurma kapama, kenarda Boardex şeridi yok, veranda ve sundurmanın tavanı saçağıyla; müştemilat da böyle); alçak bir çatının üstüne düşen köşede iniş (konmaz; 11:39'da yalnız küçük çatıya daraldı); üretim dosyası (verilmeyecek; paftayı biz oluşturacağız); çatı çıkış kapağı (listede yok); bacanın içi (göz ardı; yalnız karkas); taharet musluğu (vitrifiye dahilse ıslak hacim başına 4); saçak omegası (çatı ve tavan panelli sistemlerde yok); KT-03 tanımının ve çizimlerinin depoya eklenmesi; kural kitabının çağrı sırasına göre klasörlenmesi (`kurallar/`).
- **Lokman'ın 10 Ekim 11:39 cevaplarıyla:** kısa derede tek iniş (4 m'yi geçmeyen hatta); verandanın üstüne düşen köşede iniş (var: dere 15 cm içeride biter, su verandaya iner); müştemilatın panel çatısının okuması (teyit).
- **Lokman'ın 10 Ekim 13:33 ve 14:46 cevaplarıyla:** Ç8801'in çatısı (katalogdaki model 2. versiyon: ana çatı iki ucunda kalkan, cumba ana çatıya girip biter, bütün yüzler %33; öteki iki çatı varyant olarak saklanıyor: "çatı olarak 3'üde olur").

## Canlıya alırken (öneri; ayrı onay gerekir)

- Kurallar veridir: kural kitabındaki (`kurallar/`; çağrı sırası `kurallar/README.md`'de) her değer kaynağı ve durumuyla bir PostgreSQL tablosuna taşınır; kural değişince kod değişmez.
- Kural setleri sürümlüdür: her set olduğu gibi saklanır, liste hangi setle üretildiyse o setle yeniden üretilebilir (7–10 Ekim'de denendi: 0.12'den 0.18'e yedi set kendi günlerindeki çıktıların hepsini bayt bayt aynı veriyor). Tek istisna: 0.13 kopyasında bir kaynak notundaki ifade sadeleştirildi; değerler, durumlar ve çıktılar aynı.
- Model bankası (Lokman'ın 10 Ekim 11:39 sorusu: "bu modelleri nerede biriktireceğiz yani bayiden bize gelen modellerde veri tabınana girmeli hem daha çok seçenek birikmeli hemde hangi model daha çok satılıyor görmeliyiz"; öneri): katalog modelleri ve bayi taleplerinden türeyen modeller sürümleriyle, talepler, teklifler ve satışlar Portman'ın veritabanında birikir; çizim ve liste dosyaları dosya deposunda, veritabanında yolları ve özetleri. Hangi modelin ve hangi değişikliğin ne kadar istendiği, teklif edildiği ve satıldığı oradan okunur; aynı değişiklik tekrar tekrar gelirse kataloğa yeni model adayı olur. Ayrı bir iş emriyle, önce yerelde.
- Portman'ın iki işi (Lokman, 10 Ekim 14:46): "1 devamlı modelde üreteceksin 2. bayilerede bu modelleri sunacaksın". Ürün sınırlı: tek kat ve çift kat çatılar belli biçimlerde, alan en çok 250 m² gibi sınırlar var ("buda elimizi güçlendiriyor"). Aynı plana birden çok çatı (Ç8801: katalog, K, L) bunun ilk örneği: varyantlar model bankasına aday, bayiye numaralı seçenek olarak sunulur.
- Bayi kuralı: bayinin telefon numarası birincil anahtar; karşısında standardı (listeye giren gruplar, çatı yöntemi, çatı kaplaması, paket). Liste, mesajı atan bayinin standardına göre kurulur.
- Modelin tanımı listenin girdisidir: odaların işlevi (elektrik kuralı), dolap ve TV duvarları (OSB takviyesi), elle yerleştirilmiş iniş yerleri tanımda durur.
- Hesap deterministik bir modüldür; LLM yalnız talebi anlar (K05). Çatı açılımı da öyle: aynı çatı ve kaplama her zaman aynı dizilimi verir.
- Bunların hiçbiri yapılmadı: sunucu ve canlı değişiklik Lokman'ın ayrı onayıyla yapılır.
"""
BELGE.write_text(D, encoding="utf-8")
print("yazıldı:", BELGE.relative_to(BURADA.parents[1]), "·", len(D.split("\n")), "satır")
