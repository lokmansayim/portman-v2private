#!/usr/bin/env python3
"""Ç8201 yükleme listesi taslağını okunur bir sayfaya (tek HTML dosyası) çevirir.

Sayılar `sonuc/` altındaki hesap çıktılarından alınır; elle yazılmaz. Önce `hepsini_kos.sh` koşulmalı.
Sayfa Claude'un artefakt biçimindedir (doctype, html, head, body etiketleri yok). Depoya çıktı yazılmaz.
Şimdilik Ç8201'e özgüdür: dosya adları, "değişenler", çatı açılımı ve "sizden beklenenler" metinleri bu modele göredir.
Sayfa Lokman'ın özel artefaktıdır ama paylaşılabilir; o yüzden kişi adı yazılmaz (mühendis "mühendis" diye geçer).

Kullanım:
    python sayfa_uret.py --cikti /tmp/C8201_yukleme_listesi.html --zaman "7 Ekim 2026 10:00"
"""
import argparse
import base64
import html
import json
from pathlib import Path

import kural

from motor_formul import BESIK_10, SABLON, motor_kaplama

S = Path(__file__).resolve().parent / "sonuc"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--cikti", type=Path, required=True)
ap.add_argument("--zaman", required=True, help="künyede görünecek tarih ve saat")
ap.add_argument("--dosya", action="store_true", help="tek başına açılan dosya üret (belge iskeleti ve karakter kümesi eklenir); varsayılan çıktı artefakt içindir (iskeleti yayın ekler)")
A = ap.parse_args()
baz = json.loads((S / "C8201_yukleme_taslak.json").read_text(encoding="utf-8"))
d140 = json.loads((S / "C8201_dis_karkas_140_yukleme_taslak.json").read_text(encoding="utf-8"))
KAPLAMALAR = [("Tek kat panel (baz paket)", baz, None)] + [
    (ad, json.loads((S / f"C8201_kaplama_{kod}.json").read_text(encoding="utf-8")), notu) for ad, kod, notu in (
        ("Sandviç panel", "sandvic_panel", None),
        ("OSB + nem bariyeri + kiremit desen sac", "osb_kiremit", "Motordaki adı: OSB + membran + metal kiremit"),
        ("OSB + nem bariyeri + trapez sac", "osb_trapez", "Gerçek listeyle karşılaştırılmadı"),
        ("Trapez sac", "trapez_sac", "Gerçek listeyle karşılaştırılmadı"),
        ("OSB + membran + shingle", "osb_shingle", "Yalnız motorun formülüyle; gerçek listeyle karşılaştırılmadı"))]

def tr(x, n=0):
    return f"{x:.{n}f}".replace(".", ",")

def e(s):
    return html.escape(str(s), quote=True)

# Sayfa bağlantıyla paylaşılabildiği için kişi adı taşımaz: hesap çıktısındaki notlarda geçen adlar okura hitaba ("siz") ya da role çevrilir.
SAYFA_DILI = (
    ("(Lokman, 4 Ekim düzeltmesi)", "(4 Ekim düzeltmeniz)"),
    ("Lokman makas ve kirişleri bir makas ölçüsünden ayrıca verecek", "makas ve kirişleri bir makas ölçüsünden ayrıca vereceksiniz"),
    ("Lokman'ın tarifinden", "tarifinizden"), ("Lokman'ın kararıyla", "kararınızla"),
    ("Lokman'ın kuralı", "sizin kuralınız"), ("Lokman'ın", "sizin"), ("Lokman,", "siz,"), ("Lokman", "siz"),
    ("Ubeydullah'ın", "mühendisin"), ("Ubeydullah", "mühendis"),
)


def sayfa_dili(s):
    for eski, yeni in SAYFA_DILI:
        s = s.replace(eski, yeni)
    return s

DURUM = {
    "lokman": ("Sizin kuralınız", "ok", "Kuralı ya da değeri siz verdiniz"),
    "muhendis": ("Mühendisin kuralı", "ok", "Kuralı ya da değeri inşaat mühendisi verdi (3 ve 4 Ekim'de ilettiğiniz cevaplar)"),
    "excel": ("Liste formülü", "kaynak", "Gerçek yükleme listelerinin çalışma kitabındaki formül"),
    "motor": ("Excel motoru", "kaynak", "CTKBF V1.1'deki formül ya da proje ortalaması"),
    "model": ("Modelden", "kaynak", "Çizimdeki açıklıklardan sayıldı"),
    "uydurma": ("Listeye uyduruldu", "bekle", "Gerçek listelerdeki adedi tutturan kural; teyit bekliyor"),
    "varsayim": ("Varsayım", "bekle", "Benim varsayımım; teyit bekliyor"),
    "soru": ("Soru", "eksik", "Kural bilinmiyor; adet yok"),
    "bekliyor": ("Değer yok", "eksik", "Ölçü ya da sayım gelince hesaplanacak"),
}

def es(s):
    for x in d140["satirlar"]:
        if x["grup"] == s["grup"] and x["kalem"] == s["kalem"] and (x["boyut"] == s["boyut"] or s["grup"] == "Çelik panel"):
            if s["grup"] == "Çelik panel" and s["kalem"] == "Boy C profil" and x["boyut"] != s["boyut"]:
                continue
            return x
    return None

def olcu(s):
    return "" if s["olcu"] is None else f"{tr(s['olcu'], 1)} {s['birim']}"

gruplar = []
for s in baz["satirlar"]:
    if s["grup"] not in gruplar:
        gruplar.append(s["grup"])

ACIK = ("tahmin", "teyit bekliyor", "karar bekliyor", "geçici", "priz sayısı bilinmediği", "katalog görsellerinden", "iki katı")


def bekleyen(s):
    return DURUM[s["durum"]][1] in ("bekle", "eksik") or any(k in (s.get("not") or "") for k in ACIK)


def satir_html(s):
    o = es(s)
    ad, sinif, _ = DURUM[s["durum"]]
    celik = s["grup"] == "Çelik panel"
    adet_baz = "" if s["adet"] is None else str(s["adet"])
    if celik:
        kg_baz = "" if s["kg"] is None else tr(s["kg"])
        if o is None:
            oteki = "—"
        else:
            parca = []
            if o["boyut"] != s["boyut"]:
                parca.append(e(o["boyut"]))
            if o["kg"] is not None and (o["kg"] != s["kg"] or o["boyut"] != s["boyut"]):
                parca.append(f"{tr(o['kg'])} kg")
            elif o["kg"] is None and o["olcu"] != s["olcu"]:
                parca.append(e(olcu(o)))
            oteki = " · ".join(parca) if parca else "aynı"
        hucre = f'<td class="say">{adet_baz}</td><td class="say">{kg_baz}</td><td class="oteki">{oteki}</td>'
    else:
        if o is None:
            oteki = "—"
        elif o["adet"] == s["adet"]:
            oteki = "aynı"
        else:
            oteki = f'<b>{o["adet"]}</b>'
        hucre = f'<td class="say">{adet_baz}</td><td class="oteki">{oteki}</td>'
    alt = []
    if s["olcu"] is not None:
        alt.append(e(olcu(s)))
    if s["formul"]:
        alt.append(e(sayfa_dili(s["formul"])))
    notu = f'<div class="not">{e(sayfa_dili(s["not"]))}</div>' if s.get("not") else ""
    return (f'<tr data-d="{"bekle" if bekleyen(s) else "tamam"}"><td class="kalem"><div class="ad">{e(s.get("liste_adi") or s["kalem"])}</div><div class="alt">{" · ".join(alt)}</div>{notu}</td>'
            f'<td class="boyut">{e(s["boyut"])}</td>{hucre}<td><span class="rozet {sinif}" title="{e(DURUM[s["durum"]][2])}">{ad}</span></td></tr>')

bolumler = []
for g in gruplar:
    celik = g == "Çelik panel"
    bas = ("<tr><th>Kalem</th><th>Boyut</th><th class='say'>Adet</th><th class='say'>kg</th><th>Dış 140</th><th>Kaynak</th></tr>" if celik
           else "<tr><th>Kalem</th><th>Boyut</th><th class='say'>Baz</th><th>Dış 140</th><th>Kaynak</th></tr>")
    govde = "\n".join(satir_html(s) for s in baz["satirlar"] if s["grup"] == g)
    n = sum(1 for s in baz["satirlar"] if s["grup"] == g)
    bolumler.append(f'<section class="grup"><h2>{e(g)} <span class="sayac">{n} kalem</span></h2><div class="kaydir"><table class="{"celik" if celik else ""}"><thead>{bas}</thead><tbody>{govde}</tbody></table></div></section>')

def kap(v):
    return [s for s in v["satirlar"] if s["grup"] == "Çatı kaplamaları" or (s["grup"] == "Vida" and ("5,5 × 60" in s["kalem"] or "panel)" in s["kalem"] or "OSB ve yalıpan" in s["kalem"]))]

def dizilim_notu(v):
    """Kırma çatıda dizilimle ilgili not (hesap çıktısından): panel boyunun uzatılması, en az paneli veren dizilim, artan parçanın kullanılmaması."""
    z = v["ara"].get("kirma_dizilim")
    if not z:
        return None
    parca = []
    if z.get("uzatma") and z["uzatma"].get("neden") == "pay":
        parca.append(f"Panel boyu L {z['uzatma']['taban_boy_mm']} → L {z['uzatma']['boy_mm']}: pay kalsın diye (adet aynı; L {z['uzatma']['taban_boy_mm']} ile kesim payı "
                     f"{tr(z['uzatma']['taban_pay_siniri_mm'], 1)} mm'yi geçerse {z['uzatma']['taban_saglamlik_adet']} gerekir)")
    elif z.get("uzatma"):
        parca.append(f"Panel boyu L {z['uzatma']['taban_boy_mm']} → L {z['uzatma']['boy_mm']}: taban boyla {z['uzatma']['taban_adet']} gerekiyordu")
    elif z.get("uzun_panelle"):
        parca.append(f"Panel L {z['uzun_panelle']['boy_mm']} ve daha uzun olsaydı {z['uzun_panelle']['adet']} yeterdi")
    if z["en_az_adet"] < z["adet"]:
        parca.append(f"En az paneli veren dizilimle {z['en_az_adet']} olurdu")
    if not z["artan_parca_karsi_yuzde"]:
        parca.append("Desen ters geldiği için artan parça karşı yüzde kullanılmaz (mühendis)")
    return ". ".join(parca) or None


def kap_tablo(ad, v, notu):
    r = "".join(f'<tr><td>{e(s.get("liste_adi") or s["kalem"])}</td><td class="boyut">{e(s["boyut"])}</td><td class="say">{s["adet"]}</td></tr>' for s in kap(v))
    notlar = [x for x in (notu, dizilim_notu(v)) if x]
    alt = f'<p class="secenek-not">{e(". ".join(notlar))}</p>' if notlar else ""
    return f'<div class="secenek"><h3>{e(ad)}</h3><table><tbody>{r}</tbody></table>{alt}</div>'

def kg(v, kalem):
    return next(s["kg"] for s in v["satirlar"] if s["kalem"] == kalem)
def adet(v, kalem):
    return next(s["adet"] for s in v["satirlar"] if s["kalem"] == kalem)

toplam_baz, toplam_140 = kg(baz, "Toplam (adedi ve kg'ı bilinenler)"), kg(d140, "Toplam (adedi ve kg'ı bilinenler)")
_kars = [json.loads((S / f"ornek_{n}m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma_ozeti"] for n in (90, 62, 105)]
kars_toplam, kars_ayni = sum(x["karsilastirilan"] for x in _kars), sum(x["ayni"] for x in _kars)
toplam_satir = len(baz["satirlar"])
bekleyen_sayisi = sum(1 for s in baz["satirlar"] if bekleyen(s))

def satir(v, kalem):
    return next(s for s in v["satirlar"] if s["kalem"] == kalem)

# 7 Ekim 07:45 cevapları ve 08:02 düzeltmeleriyle değişenler. "Önce" değerleri 7 Ekim 03:46 sürümünden (commit eff6a74; kural seti 0.12; sabit),
# "sonra" değerleri hesap çıktısından.
ONCE = {"tek_kat": 25, "panel_boyu_mm": 4325, "taban_mm": 4315, "sandvic": 25, "trapez": 30, "kiremit": 28, "mahya_bandi": 4, "boardex": 31, "osb": 9, "kapama": 18, "satir": 88,
        "nym": (145, 121), "tavan_yesil": 8, "duvar_izolasyonu": 13, "trapez_vida_B": 2000}
K = kural.oku()
G = json.loads((S / "C8201_girdi.json").read_text(encoding="utf-8"))
assert baz["cati_kaplamasi_anahtar"] == K["baz_paket_cati_kaplamasi"]["deger"] == "tek_kat_panel", "sayfa metinleri baz kaplama tek kat panel diye yazıldı"
pk_t, pk_c = K["celik"]["tavan_paneli"]["deger"], K["celik"]["cati_paneli"]["deger"]
osb_s, kose_s = satir(baz, "OSB (TV ve mutfak dolabı arkası takviyesi)"), satir(baz, "Köşebent")
tp, cp = satir(baz, "Tavan paneli (makas arası)"), satir(baz, "Çatı paneli (makas üstü, sırt 80 mm)")
kap_s, bant_s, boardex_s = satir(baz, "Tek kat panel"), satir(baz, "Mahya bandı"), satir(baz, "Dış cephe Boardex")
dz = baz["ara"]["kirma_dizilim"]
osb_iki = baz["ara"]["osb_takviye"]
uz = dz["uzatma"]                                  # panel boyu uzatma kuralının uyguladığı değişiklik
kap_cm, boy_mm, taban_mm = round(dz["kapatma_m"] * 100), round(dz["panel_boyu_m"] * 1000), round(G["cati"]["panel_boyu_m"] * 1000)


def metre(n: int, mm: int) -> str:
    """Toplam boy (m, bir hane; yarım yukarı): adet × panel boyu."""
    return tr((n * mm + 50) // 100 / 10, 1)
k62 = json.loads((S / "ornek_62m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma"]["Sandviç panel"]
zb = K["zayiat"]["boardex"]["deger"]
tasma_cm, kesim_mm = K["cati_kaplama_tasma_m"]["deger"] * 100, K["kirma_cati_dizilim"]["deger"]["kesim_payi_m"] * 1000


def dz_oku(kod):
    return json.loads((S / f"C8201_kaplama_{kod}.json").read_text(encoding="utf-8"))["ara"]["kirma_dizilim"]


dz_s, dz_t, dz_k = dz_oku("sandvic_panel"), dz_oku("trapez_sac"), dz_oku("osb_kiremit")
# Bağımsız denetimin 7 Ekim sonucu (bu koda ve çıktılara bakmayan ayrı bir oturum): L 4330 × 25; bu dizilim ve kesim kuralıyla en az 25 (belge_uret.py'deki BAGIMSIZ ile aynı kayıt).
BAGIMSIZ = {"boy_mm": 4330, "adet": 25}
assert (round(dz["panel_boyu_m"] * 1000), dz["adet"]) == (BAGIMSIZ["boy_mm"], BAGIMSIZ["adet"]), "sayfa: bağımsız hesap aynı boyu ve adedi buldu diyor"
BAGIMSIZ_NOTU: list[str] = ["Aynı kuralı, bu koda bakmayan ayrı bir hesaba da yaptırdım: aynı boy ve aynı adetler çıktı; bu dizilimde ve bu kesim kuralıyla "
                            f"{BAGIMSIZ['adet']}'ten az panelle olmuyor."]
EK_NOT = {"Sandviç panel": f"80 cm kapatan ürün gelirse {dz_t['adet']} (trapez sacla aynı dizilim). Sac kapama dere boyunca: L 2500, 20 cm bindirme (7 Ekim cevabınız; hesabı 8 Ekim'de onayladınız)"}
kaplama = "".join(kap_tablo(ad, v, ". ".join(x for x in (notu, EK_NOT.get(ad)) if x) or None) for ad, v, notu in KAPLAMALAR)
# Sayfadaki sabit cümlelerin dayandığı durumlar; hesap değişirse sayfa üretilmez, metin gözden geçirilir.
assert kap_s["adet"] == dz["adet"] and dz["baslangic"] == "sol" == K["kirma_cati_dizilim"]["deger"]["baslangic"], "sayfa: dizilim her yüzde sol köşeden başlıyor diyor"
assert kap_cm == 100 and K["kiremit_kapatma_m"]["deger"] == K["sandvic_panel_kapatma_m"]["deger"] == 1.0, "sayfa: tek kat panel, kiremit desen sac ve sandviç panel 100 cm kapatıyor diyor"
assert dz["tasma_cm"] == tasma_cm == 5 and dz["kesim_payi_mm"] == kesim_mm == 5, "sayfa: taşma 5 cm, kesim payı 5 mm diyor"
assert not dz_k["artan_parca_karsi_yuzde"], "sayfa: kiremit desen sacda artan parça kullanılmıyor diyor"
assert uz and uz.get("neden") == "pay" and (uz["taban_boy_mm"], uz["taban_adet"], uz["boy_mm"], uz["adet"]) == (taban_mm, kap_s["adet"], boy_mm, kap_s["adet"]) \
    and (taban_mm, boy_mm) == (4320, 4330) and kap_s["adet"] == ONCE["tek_kat"] and dz["tek"] == 0, \
    "sayfa: taban L 4320; pay kalsın diye L 4330; adet önceki sürümdekiyle aynı; tek parça için harcanan panel yok diyor"
assert dz["bir_cm_payla_adet"] == dz["adet"] == dz["en_az_adet"] and uz["taban_saglamlik_adet"] > dz["adet"], "sayfa: listedeki boyda adet kesim payı 1 cm olsa da aynı; taban boyda artardı diyor"
assert all(z["uzatma"] and z["uzatma"]["boy_mm"] == boy_mm and z["uzatma"].get("neden") == "pay" for z in (dz_s, dz_t, dz_k)) \
    and (dz_s["adet"], dz_t["adet"], dz_k["adet"]) == (ONCE["sandvic"], ONCE["trapez"], ONCE["kiremit"]), \
    "sayfa: öteki kaplamalarda da boy aynı boya uzuyor; adetler önceki sürümdekiler diyor"
assert bant_s["adet"] == ONCE["mahya_bandi"] and boardex_s["adet"] == ONCE["boardex"] and osb_s["adet"] == ONCE["osb"] == osb_iki["duvarlar_adet"] < osb_iki["butun_oda_adet"] \
    and K["osb_takviye"]["deger"]["baz"] == "duvarlar", "sayfa: mahya bandı, Boardex ve OSB takviyesi adedi değişmedi; OSB'de geçerli kural dolap ve TV duvarları diyor"
assert not any(x["kalem"] in ("Tek kat panel kapaması", "Duvar izolasyonu") for x in baz["satirlar"]) and toplam_satir == ONCE["satir"] + 1 == 89, \
    "sayfa: duvar izolasyonu çıktı; veranda tavanı Boardex'i ve acil müdahale kapağı girdi; liste 88 → 89 satır diyor"
sandvic_kapama = next(x for x in json.loads((S / "C8201_kaplama_sandvic_panel.json").read_text(encoding="utf-8"))["satirlar"] if x["kalem"] == "Sandviç panel kapaması")

# Montaj paftalarından okunanlar (üç gerçek listenin projeleri; paftalar depoda değil). Sayılar `belge_uret.py`'deki PAFTA sabitiyle aynı.
PAFTA = {"klasor": 13, "pdf": 84, "pafta_pdf": 80, "liste_pdf": 4, "inis": {62: 7, 90: 8, 105: 10}, "omega_en_az": {62: 25, 90: 39, 105: 43}}
_kars = {n: json.loads((S / f"ornek_{n}m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma"] for n in (62, 90, 105)}
omega = {n: _kars[n]["Tavan omegası (60'lık)"] for n in (62, 90, 105)}
inis_hesap = _kars[62]["Dere iniş borusu"]["hesap"]
assert all(omega[n]["liste"] == PAFTA["omega_en_az"][n] + 1 for n in (62, 90, 105)), "sayfa: tavan omegası üç projede de paftadaki kesimden bir fazla diyor"
assert _kars[62]["Dere iniş borusu"]["liste"] == PAFTA["inis"][62] == 7 and inis_hesap == 6 and adet(baz, "Dere iniş borusu") == 6, \
    "sayfa: 62 m² projede paftada ve listede 7 iniş, kuralda 6; Ç8201'de 6 diyor"
assert K["panel_kapamasi"]["deger"]["sandvic_panel"] and sandvic_kapama["adet"] > 0, "sayfa: sandviç panel kapaması şimdilik kalıyor diyor"
yb = json.loads((S / "C8201_yontem_B.json").read_text(encoding="utf-8"))
KESME_TASI = "230'luk kesme taşı"
# trapez vida (5,5 × 25): parça C profiller panel gibi sayılıyor (soruldu); sayılmazsa ne olurdu
tv_s = satir(baz, "Trapez vida (5,5 × 25)")
c_profil_adedi = sum(s["adet"] for s in baz["satirlar"] if s["kalem"] == "Boy C profil")
assert [(s["boyut"], s["adet"]) for s in baz["satirlar"] if s["kalem"] == "Boy C profil"] == [("80 × 45 × 0,8", 3), ("80 × 45 × 1,2", 3)], "sayfa: Boy C profil 0,8'den 3 ve 1,2'den 3 diyor"
tv_c_ile = tv_s["olcu"] + c_profil_adedi * K["vida"]["deger"]["trapez_5_5x25"]["celik_panel"]
tv_c_ile_adet = -(-tv_c_ile // K["vida"]["deger"]["trapez_yuvarlama"]) * K["vida"]["deger"]["trapez_yuvarlama"]
assert K["vida"]["deger"]["trapez_5_5x25_c_profil_dahil"] is False and c_profil_adedi == 6 and "parça C profiller hariç" in tv_s["formul"] \
    and (tv_s["olcu"], tv_s["adet"], tv_c_ile, tv_c_ile_adet) == (984, 1000, 1044, 1250), "sayfa: trapez vidada parça C profiller sayılmıyor: 984 → 1000 (7 Ekim'de 1044 → 1250) diyor"
assert (_kars[62]["Sandviç panel kapaması"]["liste"], _kars[62]["Sandviç panel kapaması"]["hesap"]) == (16, 17), "sayfa: 62 m² listede kapama 16, hesap 17 diyor"
vt_s = satir(baz, "Veranda tavanı (Boardex)")
kosegen = (G["kapali_olcu_m"][0] ** 2 + G["kapali_olcu_m"][1] ** 2) ** 0.5
IN_KR, SK_KR = K["inis"]["deger"], K["sandvic_kapama"]["deger"]
assert (adet(baz, "NYM kablo (3 × 2,5)"), adet(baz, "NYM kablo (2 × 1,5)")) == (120, 96) and adet(baz, "Tavan alçıpan yeşil") == 2 and vt_s["adet"] == 7 \
    and adet(baz, "Acil müdahale kapağı") == 1 and adet(yb, "Trapez vida (5,5 × 25)") == 1000 and adet(baz, "Metal kiremit mahyası") == 11, \
    "sayfa: NYM 120 ve 96 m; yeşil tavan 2; veranda tavanı Boardex 7; acil müdahale kapağı 1; yöntem B'de trapez vida 1000; mahya 11 diyor"
assert (IN_KR["olcu"], IN_KR["orta_inis_esigi_m"]) == ("dere", 9.0) and (SK_KR["parca_boyu_m"], SK_KR["bindirme_m"]) == (2.5, 0.2) and sandvic_kapama["adet"] == ONCE["kapama"], \
    "sayfa: iniş eşiği 9 m dere boyu; sandviç panel kapaması L 2500, 20 cm bindirme, adet önceki sürümle aynı diyor"
assert K["bindirme_m"]["mahya"]["deger"] == 0.2 and K["celik_cati_yontemi"]["deger"] == "panel" and K["panel_boyu_yuvarlama_mm"]["deger"] == 10, "sayfa: bindirme 20 cm; çelikte yöntem A; panel boyu 10 mm'ye yukarı diyor"
# 8 Ekim 00:45 cevapları: iniş eşiği ve kapama hesabı onaylandı; panel boyu kapandı; levhanın adı üreticinin adı; duvara dayanan kenara özel mahya; alıcıya ait pencerede mastik yok.
# 07:23 ve 07:41: kalkan kenarına alın kapama, Boardex yalnız yüz (bu modelde kalkan kenarı yok); trapez vidada parça C profil sayılmaz; özel mahya bant hesabına girmez
LEVHA_ADI = K["urun_adlari"]["deger"]["degistir"][0][1]
levha_satirlari = [x for x in baz["satirlar"] if x.get("liste_adi")]
assert K["inis"]["durum"] == K["sandvic_kapama"]["durum"] == "lokman" == satir(baz, "Dere iniş borusu")["durum"] == sandvic_kapama["durum"], \
    "sayfa: iniş eşiği ve sandviç panel kapaması hesabı onaylandı diyor"
assert K["panel_boyu_uzatma"].get("satir_notu_pay") and "teyit bekliyor" not in (kap_s["not"] or ""), "sayfa: panel boyu konusu kapandı diyor"
assert LEVHA_ADI == "OUTWEAR Dış Cephe Levhası" and len(levha_satirlari) == 4 and all(LEVHA_ADI in x["liste_adi"] and "Boardex" in x["kalem"] for x in levha_satirlari) \
    and satir(baz, "Dış cephe Boardex")["liste_adi"] == LEVHA_ADI, "sayfa: dört satırda levha üreticinin adıyla yazıyor diyor"
assert K["duvar_dibi"]["deger"].get("malzeme") == "ozel_mahya" and K["kapsam_alici"]["deger"]["pencere_aliciya_aitse"]["silikonize_mastik"] is False \
    and K["yontem_a_alin_kaplamasi"]["durum"] == "lokman" and K["yontem_a_kalkan_ust_kapamasi"]["durum"] == "lokman" \
    and K["yontem_a_kalkan_ust_kapamasi"]["deger"]["ad"] == "Alın kapama" and K["yontem_a_alin_kaplamasi"]["deger"]["olcu"] == "yalniz_yuz" \
    and not any(x["kalem"] in ("Özel mahya (geniş)", "Alın kapama", "Alın (kalkan kenarı) için Boardex") for x in baz["satirlar"]), \
    "sayfa: özel mahya, mastik ve kalkan kenarı kararlarının bu modelde (kırma çatı, pencereler dahil) karşılığı yok diyor"

degisenler_8 = [
    ("Bir sayı değişti", f"Trapez vida (5,5 × 25) {tv_c_ile_adet} → {tv_s['adet']}; öteki satırların adedi aynı. Liste yine {toplam_satir} satır; "
                         f"teyit ya da değer bekleyen satır sayısı {bekleyen_sayisi} (7 Ekim'de 10'du)."),
    ("Trapez vidada C profil yok", f"\"C profiller hiç önemli değil öylesine gönderiyoruz göz ardı et\" dediniz: {c_profil_adedi} adet \"Boy C profil\" vida hesabında "
                                   f"sayılmıyor, satırları listede duruyor. {tr(tv_c_ile)} → {tr(tv_s['olcu'])} vida; pakete yuvarlanınca {tv_c_ile_adet} → {tv_s['adet']}."),
    ("İniş kuralı kesinleşti", f"9 m eşiğini onayladınız: her dere hattının iki ucuna birer iniş, boyu 9 m'yi geçen hattın ortasına bir tane daha. Bu modelde {adet(baz, 'Dere iniş borusu')}."),
    ("Sandviç panel kapaması kesinleşti", f"Dere boyu ÷ (2,5 − 0,20): sandviç panel seçeneğinde {sandvic_kapama['adet']}."),
    ("Panel boyu kapandı", f"\"3 cm'e kadar +- tolere edilebilir\" dediniz: liste L {boy_mm} × {kap_s['adet']} ile kalıyor. Kural: eğimli boy + taşma, 10 mm'ye yukarı; "
                           "adedi düşürüyorsa ya da pay inceyse en çok 3 cm uzatma. Bu konuda başka soru sormayacağım."),
    ("Levhanın adı", f"\"üreticide ne yazıyorsa onu yaz\" dediniz: listede artık {LEVHA_ADI} yazıyor ({len(levha_satirlari)} satır). Şirkette Boardex denen levha bu; "
                     "notlarda ve formüllerde Boardex adı geçebilir."),
    ("Sigorta kutusu", "Tanımda yeri yazmıyorsa giriş kapısında sayılmasını onayladınız."),
    ("Bu modelde karşılığı olmayanlar", "Çatının duvara dayandığı kenara özel mahya (yalnız ek veranda, müştemilat gibi çıkıntı ya da bazı cumbalı çatılarda; "
                                        "mahya bandına girmez); pencereler alıcıya aitse mastik yazılmaz; beşik çatıda kalkan kenarının üstüne alın kapama "
                                        "(makasın eğimli kenarı boyunca, L 2500), Boardex yalnız o kenarın yüzüne. Bu model kırma çatılı ve pencereleri dahil: "
                                        "bu kalemlerin hiçbiri bu listede yok."),
]

degisenler = [
    ("Veranda tavanı Boardex", f"Çelik yapıda veranda tavanı her zaman Boardex dediniz: {tr(vt_s['olcu'], 1)} m² → {vt_s['adet']} levha, ayrı satır. "
                               f"Yeşil tavan alçıpanı {ONCE['tavan_yesil']} → {adet(baz, 'Tavan alçıpan yeşil')}."),
    ("Duvar izolasyonu çıktı", f"\"Göndermiyoruz yok say\" dediniz: {ONCE['duvar_izolasyonu']} paketlik satır listeden çıktı."),
    ("Acil müdahale kapağı girdi", "Her yapıya 1 adet, standart."),
    ("Kabloda mesafe sigortadan", f"Sigorta kutusunu giriş kapısında saydım: kapalı kısmın en uzak köşesi {tr(G['elektrik_en_uzak_m'], 2)} m (önce köşegen alınıyordu: {tr(kosegen, 2)} m). "
                                  f"NYM 3 × 2,5: {ONCE['nym'][0]} → {adet(baz, 'NYM kablo (3 × 2,5)')} m; 2 × 1,5: {ONCE['nym'][1]} → {adet(baz, 'NYM kablo (2 × 1,5)')} m."),
    ("Panel boyu L 4330", f"\"Yukarı yuvarla\" dediniz: taban L {ONCE['taban_mm']} → L {taban_mm}. L {taban_mm} ile de {kap_s['adet']} panel çıkıyor ama pay ince: "
                          f"kesim payı {tr(uz['taban_pay_siniri_mm'], 1)} mm'yi geçerse {uz['taban_saglamlik_adet']} gerekir. Pay kalsın diye L {boy_mm} yazdım; adet aynı ({kap_s['adet']})."),
    ("Bindirme 20 cm", f"Mahya ÷ 2,6: yine {adet(baz, 'Metal kiremit mahyası')}. Sandviç panel seçeneğinde kapama dere boyunca, L 2500: yine {sandvic_kapama['adet']}."),
    ("Çelikte omega ve aşık yok", "Bu liste zaten çatı ve tavan paneliyle. Omega ve aşıklı liste yalnız karşılaştırma için duruyor; "
                                  f"orada trapez vida (5,5 × 25) {ONCE['trapez_vida_B']} → {adet(yb, 'Trapez vida (5,5 × 25)')}."),
    ("Adedi değişmeyenler", f"Köşebent {kose_s['adet']}, iniş {adet(baz, 'Dere iniş borusu')}, alçıpan vidası {adet(baz, 'Alçıpan vidası (3,5 × 35)')}, "
                            f"trapez vida (5,5 × 25) {tv_c_ile_adet}, kesme taşı {adet(baz, KESME_TASI)}, "
                            f"dayson {adet(baz, 'Dayson')}, mastik {adet(baz, 'Silikonize mastik')}. Bu satırlarda kararınız mevcut hesabı teyit etti."),
    ("Liste", f"{ONCE['satir']} → {toplam_satir} satır."),
]


def baslikli(b, m):
    """Liste maddesi: kalın başlık + metin. Başlık soru işaretiyle bitiyorsa arkasına nokta konmaz."""
    return f"<li><b>{e(b)}{'' if b.endswith('?') else '.'}</b> {e(m)}</li>"


degisen_html = "".join(baslikli(b, m) for b, m in degisenler)
degisen8_html = "".join(baslikli(b, m) for b, m in degisenler_8)

sorular = [
    ("Excel motorundaki formül", "Sayfanın sonundaki \"Excel motorundaki kaplama formülü\" bölümünü mühendise iletir misiniz? "
                                 "Kiremit desen sac 100 cm kapatıyorsa motordaki 1,05 katsayısının da 1 olması gerekir."),
]
soru_html = "".join(baslikli(b, m) for b, m in sorular)

# Montaj paftası: klasörlerde bulunanlar (ayrıntı depoda: docs/sartname/montaj_paftasi.md). Pafta işi yükleme listesinden sonra.
PAFTALAR = (
    ("Müşteri onay paftası", "Tefrişli kat planı, oda adları ve alanları, doğrama etiketleri, pencere görünüşleri", "Yok", "Portman'ın ön onay paftası bunun karşılığı"),
    ("Duvar panelleri yerleşim planı", "Panel adları (D01…), ölçü zinciri, birleşim detayları", "Çelik kg, köşebent", "Panel bölümlemesi yok; kg formülle"),
    ("Tavan omega yerleşim planı", "Omega hatları ve parça boyları (tam parça 365)", "Tavan omegası adedi", "Dizilim yok; alan formülü (yöntem B)"),
    ("Makas ve dere yerleşim planı", "Makas adları ve aralıkları, dere hattı, iniş işaretleri", "Dere, iniş ve dirsek adetleri", "İniş kuralı var; makas dizilimi yok"),
    ("Aşık yerleşim planı", "Açılmış çatı yüzleri, 60 cm aralıklı aşık hatları, parça boyları (tam parça 410)", "Aşık adedi", "Dizilim yok; formül (yöntem B)"),
    ("Çatı kaplaması yerleşim planı", "Açılmış yüzler, şeritler, boy ve adet, çatı alanı ve kaplama alanı", "Kaplama adedi ve boyu", "Var: açılım, kesim planı, kesim ölçüleri (kırma çatı)"),
    ("Duvar kaplamaları yerleşim planı", "OSB gelen duvarlar: dolap ve TV arkası", "OSB takviyesi", "Var: kural ve duvarlar"),
    ("Elektrik yerleşim planı", "Tefrişli plan, anahtar, priz ve aydınlatma işaretleri, lejant", "Elektrik sayımı", "Sayım var (oda başına kural); yerleşim yok"),
    ("Çift katta ek paftalar", "Döşeme, döşeme kaplaması, merdiven, 1. kat duvar ve tavan omega, özel büküm saclar", "Çift kat kalemleri", "Kapsam dışı; çift kat sırası gelince"),
)
PAFTA_BASLIK = ("Pafta", "Üzerinde ne var", "Listedeki karşılığı", "Bugün elimizde")


def pafta_hucresi(i: int, h: str) -> str:
    """İlk sütun paftanın adı; öteki hücreler dar ekranda başlığıyla birlikte görünsün diye `data-b` taşır."""
    return f"<td>{e(h)}</td>" if i == 0 else f'<td data-b="{e(PAFTA_BASLIK[i])}">{e(h)}</td>'


pafta_satirlari = "".join("<tr>" + "".join(pafta_hucresi(i, h) for i, h in enumerate(r)) + "</tr>" for r in PAFTALAR)
pafta_notlari = [
    ("Listedeki sayılar paftadan geliyor",
     "Üç gerçek listenin projelerinde karşılaştırdım. Çatı kaplamasının adedi ve boyu paftadakinin aynısı (62 m²: 27 + 2 kısa; 90 m²: 28 + 2; 105 m²: 24 + 30). "
     f"İniş sayısı paftadaki işaret sayısı ({PAFTA['inis'][62]} ve {PAFTA['inis'][105]}). Tavan omegası üç projede de paftadaki parçaların kesiminden bir fazla "
     f"({' · '.join(str(omega[n]['liste']) for n in (62, 90, 105))}); alan formülümüz {' · '.join(str(omega[n]['hesap']) for n in (62, 90, 105))} veriyor. "
     "Sayımı ayrı bir hesaba da yaptırdım: aynı sayılar çıktı."),
    ("Kırma çatıda kesim planı yok",
     "Sekiz çatı kaplaması paftasının hepsi beşik çatıda. Kırma çatılı tek projede yüzler dikdörtgen çizilmiş; çapraz kesim ve artan parçanın karşı yüzde "
     "kullanılması gösterilmemiş. Ç8201 için ürettiğim açılım ve kesim planı, bu paftanın kırma çatıdaki karşılığı."),
    ("Çatı ve tavan panelli yöntem için örnek yok",
     "Paftaların hepsi tavan omegası ve aşıkla hazırlanmış (yöntem B). Baz aldığımız yöntemde bu iki paftanın yerini tavan ve çatı paneli yerleşimi alacak; "
     "klasörlerde örneği yok."),
    ("Şablondan kalan yazılar",
     "\"Çatı m²: 120\" yazısı çatısı 77,5, 107 ve 124 m² olan üç projenin aşık paftasında da aynı. Paftalar listeyle aynı hesaptan üretilirse böyle farklar kalmaz."),
]
pafta_html = (
    '<section><h2>Montaj paftası: klasörlerde bulduklarım</h2>'
    f'<p class="aciklama" style="margin-bottom:10px">Montaj paftası tek bir çizim değil; her proje için hazırlanan, ortak çerçeveli bir pafta seti. '
    f'Klasörlerinizde {PAFTA["klasor"]} montaj klasöründe {PAFTA["pdf"]} PDF buldum ({PAFTA["pafta_pdf"]} pafta, {PAFTA["liste_pdf"]} yükleme listesi; 2019\'dan Ocak 2026\'ya). '
    'Her projenin bir ana DWG\'si var: paftalar onun içinde yan yana çizilmiş, PDF\'ler oradan basılmış. '
    'Pafta işine yükleme listesinden sonra başlayacağız; burada yalnız ne anladığımı yazıyorum.</p>'
    '<div class="kaydir"><table class="pafta"><thead><tr>' + "".join(f"<th>{e(b)}</th>" for b in PAFTA_BASLIK) + '</tr></thead>'
    f'<tbody>{pafta_satirlari}</tbody></table></div>'
    '<ul class="degisen" style="margin-top:14px">' + "".join(baslikli(b, m) for b, m in pafta_notlari) + '</ul></section>')

# Excel motorundaki kaplama formülü (mühendisin isteği: hangi hücreden ne geliyor, formül nasıl işliyor). Sayılar `motor_formul.py`'den.
uzun, kisa = G["kapali_olcu_m"]
mk_c = motor_kaplama(uzun, kisa, G["dis_olcu_m"][0] - uzun, "kirma")
assert mk_c["sac_boyu_mm"] == ONCE["taban_mm"], "sayfa: motorun sac boyu eğimli boy + taşma (mm'ye yukarı, 4315 mm) diyor"
HUCRELER = (("K10", "Bina dış uzun kenar (m)"), ("K11", "Bina dış kısa kenar (m)"), ("K13, K14", "Sundurma dış uzun ve kısa kenar"),
            ("K17", "Oturum dışı veranda dış kısa kenar"), ("K23", "Çatı tipi"), ("K24", "Çatı kaplama"))
hucre_html = "".join(f"<tr><td class='boyut'>{e(h)}</td><td>{e(a)}</td></tr>" for h, a in HUCRELER)
motor_bulgular = [
    ("Parantez", "Formülde yüzey ÷ sac boyu × 0,8 yazıyor. Excel bölmeyi ve çarpmayı soldan sağa yapar: sonuç (yüzey ÷ sac boyu) × 0,8 olur. "
                 "Anlatılan hesap (sac boyu × 0,8 = bir sacın kapattığı alan; yüzey ÷ o alan) için 0,8 paydanın parantezi içinde olmalı. "
                 "Şimdiki haliyle trapez sacda adet olması gerekenin 0,64 katı çıkıyor. Metal kiremitte 1,05 de aynı yerde: adet %10 fazla çıkıyor. "
                 "Tek kat ve sandviç panelde katsayı 1 olduğu için fark yok."),
    ("Uzun kenarda saçak yok", "Yüzeyde kısa kenara 0,6 eklenmiş, uzun kenara (K10 + K17) eklenmemiş. Aynı sayfadaki çatı izolasyonu satırı uzun kenara da 0,6 ekliyor. "
                               f"10 × 10 m binada formülün yüzeyi {tr(BESIK_10['yuzey_m2'], 1)} m²; mühendisin kendi metrajında 118 m²."),
    ("Kapatma genişlikleri", "Motorda tek kat panel \"100 cm kapatır\", metal kiremit \"105 cm kapatır\" yazıyor. Güncel ürünlerde tek kat panel, kiremit desen sac ve sandviç panel 100 cm kapatıyor "
                             "(2025 listelerinde 87 ve 110 cm'di). Tek kat panel katsayısı güncel ürünle doğru; metal kiremit katsayısının 1,05 yerine 1 olması gerekir."),
    ("Sac boyu hücresi (B61)", "Yalnız \"Trapez Saç\" seçiliyken hesaplıyor; \"OSB+Nem Bariyeri+Trapez Saç\" seçiliyken 0 gösteriyor. "
                               "Trapez vida (5,5 × 60) formülü sac boyunu bu hücreden aldığı için o seçenekte sacın vidası hesaba girmiyor."),
]
motor_bulgu_html = "".join(baslikli(b, m) for b, m in motor_bulgular)
motor_ornekler = [
    ("Motorun şablonundaki kayıtlı örnek (9,74 × 7,44; veranda 2,12; dört omuz)", SABLON, f"Hücrede kayıtlı metal kiremit adedi {SABLON['yazilan']['kiremit']}"),
    ("10 × 10 m beşik çatı", BESIK_10, "Mühendisin metrajında 28 trapez sac var (her saçakta 10,6 ÷ 0,8 → 14). Düzeltilince kalan fark uzun kenara eklenmeyen saçaktan ve her saçağın ayrı yuvarlanmasından"),
    (f"Ç8201 (K10 {tr(uzun, 2)}; K11 {tr(kisa, 2)}; K17 {tr(G['dis_olcu_m'][0] - uzun, 2)}; dört omuz)", mk_c,
     f"Çatı açılımı trapez sacda {dz_t['adet']}, kiremit desen sacda {dz_k['adet']} veriyor (artan parça kullanılmadan). Tek kat panelde motor {mk_c['yazilan']['panel']} verir; açılım {dz['adet']}"),
]
motor_ornek_html = "".join(
    f"<tr><td>{e(ad)}<div class='alt'>Yüzey {tr(m['yuzey_m2'], 1)} m² ÷ sac boyu {tr(m['sac_boyu_m'], 3)} m = {tr(m['oran'], 2)}. {e(notu)}.</div></td>"
    f"<td class='say'>{m['yazilan']['trapez']} → {m['duzeltilmis']['trapez']}</td><td class='say'>{m['yazilan']['kiremit']} → {m['duzeltilmis']['kiremit']}</td></tr>"
    for ad, m, notu in motor_ornekler)
motor_html = f'''<section>
  <h2>Excel motorundaki kaplama formülü</h2>
  <p class="aciklama" style="margin-bottom:10px">Mühendisin isteği üzerine motorun MALZEMELER sayfasını yeniden okudum: hangi hücreden ne geliyor, formül nasıl işliyor. Yapıştırılan formül 61. satırdaki trapez sac formülü; aynı ifade tek kat panel (64), sandviç panel (67) ve metal kiremit (72) satırlarında da var.</p>
  <div class="kaydir"><table class="dar hucre"><thead><tr><th>Hücre</th><th>Ne</th></tr></thead><tbody>{hucre_html}</tbody></table></div>
  <ul class="degisen" style="margin-top:12px">
    <li><b>Çatı yüzeyi</b> = (K11 + 0,6) × √(1 + 0,33²) × (K10 + K17) + K13 × K14. Kısa kenara iki saçak eklenir, %33 eğimle eğimli genişliğe çevrilir, uzun kenarla (veranda dahil) çarpılır; sundurma düz alanıyla eklenir.</li>
    <li><b>Sac boyu</b> = ((K11 + 0,6) ÷ 2) × √(1 + 0,33²) + 0,05: saçaktan mahyaya eğimli boy + 5 cm taşma.</li>
    <li><b>Adet</b> = yüzey ÷ sac boyu × kaplama katsayısı (trapez sac 0,8 · tek kat ve sandviç panel 1 · metal kiremit 1,05) × çatı katsayısı (dört omuzda 1,06), yukarı yuvarlanır.</li>
  </ul>
  <h3 style="margin-top:16px">Bulgular</h3>
  <ol class="sorular">{motor_bulgu_html}</ol>
  <h3 style="margin-top:16px">Düzeltme</h3>
  <p class="aciklama" style="margin-bottom:8px">Trapez sac için formülün ilgili yeri (metal kiremitte 0,8 yerine 1,05):</p>
  <div class="formul">
    <div><span class="etiket">Şimdi</span><code>…+(K13*K14))/(((K11+0,6)/2)*KAREKÖK(1+0,33^2)+0,05)<b>*0,8</b></code></div>
    <div><span class="etiket">Olması gereken</span><code>…+(K13*K14))/<b>(</b>(((K11+0,6)/2)*KAREKÖK(1+0,33^2)+0,05)<b>*0,8)</b></code></div>
  </div>
  <h3 style="margin-top:16px">Örnekler: formül yazıldığı gibi → parantez düzeltilince</h3>
  <div class="kaydir"><table class="dar"><thead><tr><th>Örnek</th><th class="say">Trapez sac</th><th class="say">Metal kiremit</th></tr></thead><tbody>{motor_ornek_html}</tbody></table></div>
  <p class="aciklama" style="margin-top:10px">Bu liste kaplama adedini motorun formülünden almıyor; çatı açılımından alıyor. Motorun sac boyu Ç8201'de {mk_c["sac_boyu_mm"]} mm. Liste bunu 10 mm'ye yukarı yuvarlıyor (L {taban_mm}) ve pay kalsın diye L {boy_mm} yazıyor.</p>
</section>'''

# Plan görseli (OSB takviyesi gelen duvarlar turuncu çizgili): çizim denemesinin son çıktısı, sayfanın içine gömülür.
_plan = S.parents[1] / "2026-10-02_celik" / "sonuc" / "C8201_plan.png"
plan_html = ""
if _plan.is_file():
    plan_html = ('<section><h2>Plan</h2><p class="aciklama" style="margin-bottom:10px">OSB takviyesi gelen duvarlar turuncu çizgiyle işaretli; '
                 'kesik çizgi veranda kirişi, siyah kutular dikmeler.</p><div class="plan"><img alt="Ç8201 planı: beş mahal ve veranda; OSB takviyesi gelen üç duvar turuncu çizgiyle işaretli" '
                 f'src="data:image/png;base64,{base64.b64encode(_plan.read_bytes()).decode("ascii")}"></div></section>')

def gorsel(yol: Path, alt: str) -> str:
    return f'<div class="plan"><img alt="{e(alt)}" src="data:image/png;base64,{base64.b64encode(yol.read_bytes()).decode("ascii")}"></div>'


_acilim, _kesim = S / "C8201_cati_acilim.png", S / "C8201_cati_kesim.png"
acilim_html = ""
if _acilim.is_file() and _kesim.is_file():
    acilim_notlari = [
        f"Tek kat panel: {kap_s['adet']} adet L {boy_mm} ({dz['tam_boy']} tam boy + {dz['kesilen']} kesilen). Çatı yüzeyi alan olarak en az {dz['alan_alt_siniri']} panel ediyor.",
        "Dizilim her yüzde, dışarıdan bakışla sol köşeden başlıyor (kararınız).",
        f"Kaplama saçaktan {tr(tasma_cm)} cm taşıyor. Panel boyunun tabanı eğimli boy {tr(dz['egimli_boy_m'] * 100, 1)} cm + {tr(tasma_cm)} cm, 10 mm'ye yukarı: L {taban_mm}. "
        f"Pay kalsın diye {tr((boy_mm - taban_mm) / 10)} cm uzatıldı: L {boy_mm}.",
        f"Kesim payı {tr(kesim_mm)} mm; yedek panel yok (onayınızla).",
        f"1. ve 4., 2. ve 3. şeritler aynı panelden çıkıyor. L {taban_mm} ile en uzun kesik parça ve köşe parçası aynı panele {tr(uz['taban_pay_siniri_mm'] - kesim_mm, 1)} mm payla sığıyordu; "
        f"L {boy_mm} ile en sıkı panelde {tr(dz['en_dar_pay_cm'], 1)} cm pay kalıyor.",
        f"Tam boy giden {dz['tam_boy']} panelde {tr((boy_mm - (dz['egimli_boy_m'] * 1000 + tasma_cm * 10)) / 10, 1)} cm fazlalık panelin üst ucunda, mahya ucunda kalır.",
        *BAGIMSIZ_NOTU,
        f"62 m² gerçek listede (kırma çatı, sandviç panel) {k62['liste']} adet L 3200 ve 2 adet L 1000 var; aynı yöntem {k62['hesap']} veriyor.",
        "Bu çizim ve ölçüler, montaj paftası çalışmasında \"çatı kaplaması yerleşim planı\" paftası olacak; kısa yüzlerdeki 10 cm'lik son şerit orada ayrıca işaretlenecek.",
    ]
    # kesim ölçüleri: hesap çıktısındaki markdown tablolarından (cati_acilim.py --olcu-md)
    _olcu = (S / "C8201_cati_kesim_olculeri.md").read_text(encoding="utf-8")

    def md_tablo(baslik: str) -> tuple[str, int]:
        """Ölçü dökümündeki bir bölümün tablosunu HTML'e çevirir; (tablo, satır sayısı)."""
        a = _olcu.index("## " + baslik)
        b = _olcu.find("\n## ", a + 3)
        satirlar = [x for x in _olcu[a:(b if b != -1 else len(_olcu))].split("\n") if x.startswith("|")]
        huc = [[h.strip() for h in x.strip().strip("|").split("|")] for x in satirlar]
        bas, govde = huc[0], huc[2:]
        th = "".join(f"<th>{e(h)}</th>" for h in bas)
        tr_ = "".join("<tr>" + "".join(f"<td>{e(h)}</td>" for h in r) + "</tr>" for r in govde)
        return f'<div class="kaydir"><table class="olcu"><thead><tr>{th}</tr></thead><tbody>{tr_}</tbody></table></div>', len(govde)

    _kesim_t, _kesim_n = md_tablo("Kesim ölçüleri (panel panel)")
    _parca_t, _parca_n = md_tablo("Parçalar (yüz yüz, soldan sağa)")
    _panel_t, _panel_n = md_tablo("Paneller (özet)")
    assert _panel_n == kap_s["adet"] and _kesim_n == _parca_n, "ölçü dökümü listeyle aynı dizilimden üretilmeli (önce hepsini_kos.sh)"
    olcu_html = (
        f'<details class="olcu" open><summary>Kesim ölçüleri: {_kesim_n} parçanın paneldeki yeri (cm)</summary>'
        '<p class="aciklama">Her satır bir parça. Panelin sol ve sağ kenarında, alt uçtan (saçak ucu) kaç cm ile kaç cm arası olduğu yazıyor; parça bu iki aralığın arasında kalan dörtgen. '
        '"180° çevrilerek" yazan parça, düz ucu saçağa gelecek biçimde çevrilip karşı yüze konur; ters yüz edilmez. Ölçüler kaplamanın kapattığı genişliğe göre.</p>'
        f'{_kesim_t}</details>'
        f'<details class="olcu"><summary>Parça ölçüleri: yüz yüz, soldan sağa ({_parca_n} parça)</summary>'
        '<p class="aciklama">Parçanın çatıdaki yeri ve kenar boyları (cm). Boylar saçak ucundan, taşma dahil; sol ve sağ, çatıya dışarıdan bakışla.</p>'
        f'{_parca_t}</details>'
        f'<details class="olcu"><summary>Paneller: hangi panelden hangi parçalar ({_panel_n} panel)</summary>{_panel_t}</details>')
    acilim_html = ('<section><h2>Çatı açılımı ve kaplama dizilimi</h2>'
                   f'<p class="aciklama" style="margin-bottom:10px">Çatı mahyadan dışarı doğru açıldı; dört yüz gerçek boyutunda. Paneller saçaktan mahyaya, {kap_cm} cm\'lik şeritler halinde; saçaktan {tr(tasma_cm)} cm taşıyor. '
                   'Sayı panel numarası: aynı numara iki yüzde görünüyorsa iki parça aynı panelden çıkıyor.</p>'
                   + gorsel(_acilim, f"Ç8201 çatı açılımı: iki yamuk ve iki üçgen yüz, {kap_cm} cm'lik şeritlere bölünmüş; her parçada panel numarası; toplam {kap_s['adet']} panel")
                   + '<p class="aciklama" style="margin-block:14px 10px">Kesim planı: her dikdörtgen bir panel. Yeşil parça olduğu gibi kullanılır; turuncu parça, düz ucu saçağa gelecek biçimde karşı yüze konur. '
                   + ('Sarı parçanın artanı kullanılmıyor.' if dz["tek"] else 'Taralı yer kullanılmayan boy.') + '</p>'
                   + gorsel(_kesim, f"Ç8201 kesim planı: {kap_s['adet']} panelin her biri; {dz['tam_boy']} panel tam boy, {dz['kesilen']} panel çapraz kesilip iki yüze paylaştırılıyor")
                   + olcu_html
                   + '<ul class="degisen" style="margin-top:14px">' + "".join(f"<li>{e(x)}</li>" for x in acilim_notlari) + "</ul></section>")

kullanilan = {s["durum"] for s in baz["satirlar"]}
lejant = "".join(f'<li><span class="rozet {v[1]}">{v[0]}</span><span>{e(v[2])}</span></li>' for k, v in DURUM.items() if k in kullanilan)

sayfa = f"""<title>Ç8201 Yükleme Listesi</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Düzen: sevk listesi gibi tek sütun; üstte künye ve özet, altında grup grup tablolar. Sayılar eş aralıklı yazıyla sağa hizalı. */
:root {{
  --zemin: #f3f5f6; --kagit: #ffffff; --yazi: #17212b; --soluk: #5b6875; --cizgi: #d5dbe0; --vurgu: #1f5f7a;
  --ok-z: #dff1e6; --ok-y: #1c6b3c; --kay-z: #e3ebf2; --kay-y: #2f4a63; --bek-z: #fdebc8; --bek-y: #7a4d00; --eks-z: #f8d9d6; --eks-y: #8a2118;
  --cizim-z: #ffffff; /* çizimin kendi zemini beyaz: iki temada da beyaz kalır */
  --sans: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }}
body {{ background: var(--zemin); color: var(--yazi); font-family: var(--sans); font-size: 15px; line-height: 1.5; }}
.sayfa {{ max-width: 980px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: flex; flex-direction: column; gap: 26px; }}
header {{ display: flex; flex-direction: column; gap: 10px; }}
.kunye {{ font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
h1 {{ font-size: clamp(24px, 4.6vw, 34px); line-height: 1.15; margin: 0; font-weight: 600; text-wrap: balance; }}
.aciklama {{ color: var(--soluk); max-width: 68ch; margin: 0; }}
.taslak {{ display: inline-block; font-family: var(--mono); font-size: 12px; border: 1px solid var(--bek-y); color: var(--bek-y); padding: 2px 8px; border-radius: 3px; letter-spacing: .05em; }}
.ozet {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--cizgi); border: 1px solid var(--cizgi); }}
.ozet div {{ background: var(--kagit); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.ozet b {{ font-family: var(--mono); font-size: 20px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.ozet span {{ font-size: 12.5px; color: var(--soluk); }}
h2 {{ font-size: 15px; margin: 0 0 8px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; display: flex; align-items: baseline; gap: 10px; }}
h2 .sayac {{ font-family: var(--mono); font-size: 11.5px; font-weight: 400; color: var(--soluk); letter-spacing: 0; text-transform: none; }}
h3 {{ font-size: 14px; margin: 0 0 6px; font-weight: 600; }}
.kaydir {{ overflow-x: auto; background: var(--kagit); border: 1px solid var(--cizgi); }}
table {{ border-collapse: collapse; width: 100%; min-width: 620px; }}
th, td {{ padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--cizgi); }}
tbody tr:last-child td {{ border-bottom: 0; }}
th {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); font-weight: 500; white-space: nowrap; }}
.say {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.say {{ font-size: 15px; font-weight: 500; }}
.boyut {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); white-space: nowrap; }}
.oteki {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); }}
.oteki b {{ color: var(--yazi); font-weight: 500; font-size: 15px; }}
.kalem {{ min-width: 240px; }}
.ad {{ font-weight: 500; }}
.alt {{ font-size: 12.5px; color: var(--soluk); max-width: 62ch; }}
.not {{ font-size: 12.5px; color: var(--bek-y); max-width: 62ch; }}
.rozet {{ display: inline-block; font-size: 11.5px; padding: 2px 8px; border-radius: 10px; white-space: nowrap; font-weight: 500; }}
.rozet.ok {{ background: var(--ok-z); color: var(--ok-y); }}
.rozet.kaynak {{ background: var(--kay-z); color: var(--kay-y); }}
.rozet.bekle {{ background: var(--bek-z); color: var(--bek-y); }}
.rozet.eksik {{ background: var(--eks-z); color: var(--eks-y); }}
.suzgec {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
.suzgec button {{ font: inherit; font-size: 13.5px; padding: 6px 12px; border: 1px solid var(--cizgi); background: var(--kagit); color: var(--yazi); border-radius: 4px; cursor: pointer; }}
.suzgec button[aria-pressed="true"] {{ background: var(--vurgu); border-color: var(--vurgu); color: var(--kagit); }}
.suzgec button:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
.lejant {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 6px 18px; font-size: 13px; color: var(--soluk); }}
.lejant li {{ display: flex; gap: 8px; align-items: baseline; }}
.secenekler {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 14px; }}
.secenek {{ background: var(--kagit); border: 1px solid var(--cizgi); padding: 12px 14px; min-width: 0; }}
.secenek table {{ min-width: 0; }}
.secenek td {{ padding: 5px 0; font-size: 13.5px; }}
.secenek td.boyut {{ padding-inline: 8px; white-space: normal; }}
.secenek-not {{ margin: 8px 0 0; font-size: 12.5px; color: var(--bek-y); }}
.degisen {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; max-width: 76ch; }}
table.dar {{ min-width: 0; }}
details.olcu {{ background: var(--kagit); border: 1px solid var(--cizgi); padding: 10px 12px; margin-top: 10px; }}
details.olcu summary {{ cursor: pointer; font-weight: 500; }}
details.olcu summary:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
details.olcu[open] summary {{ margin-bottom: 8px; }}
details.olcu .aciklama {{ font-size: 13px; margin-bottom: 10px; }}
details.olcu .kaydir {{ border: 0; }}
table.olcu {{ min-width: 560px; }}
table.olcu td {{ font-family: var(--mono); font-size: 12.5px; white-space: nowrap; padding: 5px 10px; font-variant-numeric: tabular-nums; }}
table.olcu th {{ padding: 6px 10px; }}
table.hucre td:first-child, table.hucre th:first-child {{ width: 92px; }}
table.pafta {{ min-width: 720px; }}
table.pafta td {{ font-size: 13.5px; }}
table.pafta td:first-child {{ font-weight: 500; min-width: 150px; }}
@media (max-width: 640px) {{
  table.pafta {{ min-width: 0; }}
  table.pafta thead {{ display: none; }}
  table.pafta tr {{ display: block; padding: 10px 12px; border-bottom: 1px solid var(--cizgi); }}
  table.pafta tbody tr:last-child {{ border-bottom: 0; }}
  table.pafta td {{ display: block; padding: 2px 0; border: 0; min-width: 0; }}
  table.pafta td:first-child {{ font-size: 14.5px; padding-bottom: 4px; }}
  table.pafta td[data-b]::before {{ content: attr(data-b) ": "; color: var(--soluk); font-size: 12px; }}
}}
.formul {{ background: var(--kagit); border: 1px solid var(--cizgi); padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }}
.formul > div {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.formul code {{ font-family: var(--mono); font-size: 12.5px; overflow-wrap: anywhere; }}
.formul code b {{ background: var(--bek-z); color: var(--bek-y); font-weight: 500; padding: 0 2px; border-radius: 2px; }}
.formul .etiket {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
.plan {{ background: var(--cizim-z); border: 1px solid var(--cizgi); padding: 8px; }}
.plan img {{ display: block; width: 100%; height: auto; }}
.sorular {{ margin: 0; padding-left: 28px; display: flex; flex-direction: column; gap: 8px; max-width: 76ch; }}
.dip {{ font-size: 12.5px; color: var(--soluk); max-width: 76ch; }}
[data-gizli] {{ display: none; }}
@media (max-width: 560px) {{ .ozet {{ grid-template-columns: 1fr 1fr; }} .ozet div:last-child {{ grid-column: 1 / -1; }} }}
</style>
<div class="sayfa" lang="tr">
<header>
  <div class="kunye">PortatifEv · Portman · İE-05 · {e(A.zaman)}</div>
  <h1>Ç8201 yükleme listesi</h1>
  <p class="aciklama">Tek kat çelik, 2+1, 82 m². Çatı: kırma, çatı ve tavan panelli yöntem; kaplama baz paketteki tek kat panel. Her sayının yanında nereden geldiği yazıyor.</p>
  <div><span class="taslak">TASLAK · ÜRETİM LİSTESİ DEĞİLDİR</span></div>
</header>

<div class="ozet">
  <div><b>{tr(toplam_baz)} kg</b><span>Çelik, baz paket (tavan ve çatı paneli dahil)</span></div>
  <div><b>{tr(toplam_140)} kg</b><span>Çelik, dış 140 (duvarlar 1,2 mm: mühendisin kuralı)</span></div>
  <div><b>{adet(baz, "Dış cephe Boardex")} + {adet(baz, "Saçaklar için Boardex")} + {adet(baz, "Saçak yüzü için Boardex")}</b><span>Dış cephe levhası ({e(LEVHA_ADI)}): cephe, saçak altı, saçak yüzü</span></div>
  <div><b>{adet(baz, "Duvar alçıpan beyaz") + adet(baz, "Tavan alçıpan beyaz")} + {adet(baz, "Duvar alçıpan yeşil") + adet(baz, "Tavan alçıpan yeşil")}</b><span>Alçıpan: beyaz + yeşil</span></div>
  <div><b>{bekleyen_sayisi} / {toplam_satir}</b><span>Teyit ya da değer bekleyen satır</span></div>
</div>

<section>
  <h2>8 Ekim cevaplarınızla</h2>
  <ul class="degisen">{degisen8_html}</ul>
</section>

<section>
  <h2>7 Ekim cevaplarınızla değişenler</h2>
  <ul class="degisen">{degisen_html}</ul>
</section>

<section>
  <h2>Sizden beklenenler</h2>
  <ol class="sorular">{soru_html}</ol>
</section>

{pafta_html}

<section>
  <h2>Kaynak işaretleri</h2>
  <ul class="lejant">{lejant}</ul>
</section>

<div class="suzgec" role="group" aria-label="Satırları süz">
  <button type="button" id="s-hepsi" aria-pressed="true">Bütün satırlar</button>
  <button type="button" id="s-bekle" aria-pressed="false">Yalnız teyit ya da değer bekleyenler</button>
</div>

{chr(10).join(bolumler)}

{acilim_html}

<section>
  <h2>Çatı kaplaması seçenekleri</h2>
  <p class="aciklama" style="margin-bottom:10px">Baz pakette tek kat panel var (4 Ekim düzeltmeniz). Altı seçenek Excel motorundaki listeden; kapatma genişlikleri güncel ürünlere göre. Seçeneğe göre değişen kalemler:</p>
  <div class="secenekler">{kaplama}</div>
</section>

{plan_html}

{motor_html}

<p class="dip">Kaynaklar: 3 Ekim 13:27, 4 Ekim 15:18, 16:18 ve 17:46, 7 Ekim 07:45 ve 08:02, 8 Ekim 00:45, 07:23 ve 07:41 cevaplarınız, 4 Ekim 01:24 ve 01:42 düzeltmeleriniz; inşaat mühendisinin üç tur cevabı (3 Ekim 18:14, 4 Ekim 01:24 ve 12:14'te ilettiniz); üç gerçek yükleme listesinin çalışma kitapları (62, 90 ve 105 m²); Excel hesaplama motoru (CTKBF V1.1); klasörlerinizdeki montaj paftaları. Bu modelin kendi gerçek listesi yok: sayılar yalnız kurallardan çıkıyor. Üç gerçek listeyle karşılaştırmada {kars_toplam} kalemin {kars_ayni} tanesinde adet aynı; bu bir sınama değil, çünkü katsayıların bir kısmı o listelere bakılarak seçildi. Ayrıntı depoda: docs/sartname/yukleme_listesi_yontemi.md ve docs/sartname/montaj_paftasi.md.</p>
</div>
<script>
(function () {{
  var hepsi = document.getElementById('s-hepsi'), bekle = document.getElementById('s-bekle');
  function uygula(yalniz) {{
    document.querySelectorAll('tr[data-d]').forEach(function (tr) {{
      var d = tr.getAttribute('data-d');
      if (yalniz && d !== 'bekle') tr.setAttribute('data-gizli', ''); else tr.removeAttribute('data-gizli');
    }});
    document.querySelectorAll('section.grup').forEach(function (s) {{
      var gorunen = s.querySelectorAll('tbody tr:not([data-gizli])').length;
      if (gorunen === 0) s.setAttribute('data-gizli', ''); else s.removeAttribute('data-gizli');
    }});
    hepsi.setAttribute('aria-pressed', String(!yalniz));
    bekle.setAttribute('aria-pressed', String(yalniz));
  }}
  hepsi.addEventListener('click', function () {{ uygula(false); }});
  bekle.addEventListener('click', function () {{ uygula(true); }});
}})();
</script>
"""
for ad in ("Lokman", "Ubeydullah"):   # sayfada kişi adı kalmamalı
    if ad in sayfa:
        raise SystemExit(f"Sayfada kişi adı kaldı: {ad}")
if A.dosya:   # dosya olarak verilecekse: tarayıcı karakter kümesini ve ekran genişliğini bilsin
    sayfa = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
             + sayfa.replace("</style>\n", "</style>\n</head>\n<body>\n", 1) + "</body>\n</html>\n")
A.cikti.write_text(sayfa, encoding="utf-8")
print("yazıldı:", A.cikti, "·", toplam_satir, "satır; teyit ya da değer bekleyen", bekleyen_sayisi)
