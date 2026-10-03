#!/usr/bin/env python3
"""Çelik yükleme listesi denemesi: metraj girdisinden kalemler.

Deneme kodudur; canlıda değildir. Yöntem, PortatifEv'in kendi yükleme listesi çalışma kitaplarındaki
hesap sayfalarından alındı (dış cephe, iç cephe, vida notları). Listede elle yazılan kalemlerin kuralları
iki gerçek listeye uydurularak çıkarıldı (90 m² beşik çatı, 62 m² kırma çatı) ve teyit bekliyor.

Her satırın bir durumu vardır:
  excel     yöntem PortatifEv'in çalışma kitabındaki formül ya da not
  uydurma   iki gerçek listedeki adedi tutturan kural; teyit bekliyor
  varsayim  Claude'un varsayımı; teyit bekliyor
  soru      kural bilinmiyor; adet verilmez ya da geçicidir
  model     modelden doğrudan (kapı, pencere)

Kullanım:
    python yukleme.py ornek_90m2_girdi.json --karsilastir ornek_90m2_gercek_liste.json
    python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
    python yukleme.py sonuc/C8201_girdi.json --cikti sonuc/C8201_yukleme_taslak.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent


def deg(k: dict, *yol):
    for y in yol:
        k = k[y]
    return k["deger"]


def tavan(x: float) -> int:
    return math.ceil(x - 1e-9)


def kenar_kenar(kenarlar, parca: float) -> int:
    """Her saçak kenarı ayrı ayrı tam parçaya yuvarlanır."""
    return sum(tavan(x / parca) for x in kenarlar)


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

    def ekle(grup, kalem, boyut, adet, olcu=None, brut=None, birim="m²", formul="", durum="excel"):
        S.append({"grup": grup, "kalem": kalem, "boyut": boyut, "adet": adet,
                  "olcu": None if olcu is None else round(olcu, 2), "brut": None if brut is None else round(brut, 2),
                  "birim": birim, "formul": formul, "durum": durum})

    def adet_of(kalem):
        return next((s["adet"] or 0 for s in S if s["kalem"] == kalem), 0)

    # ── Dış cephe ────────────────────────────────────────────────────────────
    d = g["dis"]
    dis_duvar = d["cevre_m"] * h
    kk = sum(x["adet"] * x["cevre_m"] * x["boy_m"] for x in d.get("kolon_kiris", []))
    alin = sum(d.get("alin_m2", []))
    dis_bosluk = sum(x["adet"] * x["en"] * x["boy"] for x in d["bosluklar"])
    dis_net = dis_duvar + kk + alin - dis_bosluk
    dis_zayiatli = dis_net * (1 + deg(k, "zayiat", "boardex"))
    kk_durum = "varsayim" if d.get("kolon_kiris_varsayim") else "excel"
    ekle("Dış cephe kaplama", "Dış cephe Boardex", "1200 × 2400", tavan(dis_zayiatli / deg(k, "levha_m2", "boardex")), dis_net, dis_duvar + kk + alin,
         formul="(çevre × yükseklik + kolon/kiriş kaplaması + alın − boşluklar) × 1,15 ÷ 2,88", durum=kk_durum)
    if d.get("dis_osb"):
        ekle("Dış cephe kaplama", "Dış duvar OSB 9 mm", "1220 × 2440", tavan(dis_zayiatli / deg(k, "levha_m2", "osb")), dis_net,
             formul="Boardex ile aynı alan (× 1,15) ÷ 2,98; üst paket", durum="excel")

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
                 formul="oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0")
    for tur, ad in (("beyaz", "beyaz"), ("yesil", "yeşil")):
        a = g["tavan_m2"].get(tur)
        if a:
            ekle("İç cephe kaplama", f"Tavan alçıpan {ad}", "1200 × 2500",
                 tavan(a * (1 + deg(k, "zayiat", "tavan_alcipan")) / deg(k, "levha_m2", "alcipan")), a,
                 formul="tavan alanı × 1,05 ÷ 3,0" + ("; yeşil = ıslak hacim + veranda tavanı" if tur == "yesil" else ""), durum="uydurma")
    ic_net = ozet["beyaz"][0] + ozet["yesil"][0]
    if g.get("ic_osb_tum_duvarlar"):
        ekle("İç cephe kaplama", "İç duvar OSB 9 mm", "1220 × 2440", tavan(ic_net * (1 + deg(k, "zayiat", "osb")) / deg(k, "levha_m2", "osb")), ic_net,
             formul="bütün iç yüzler (beyaz + yeşil net) × 1,05 ÷ 2,98; üst paket")
    elif g.get("osb_duvar_m2"):
        ekle("İç cephe kaplama", "OSB 9 mm (duvar)", "1220 × 2440", tavan(g["osb_duvar_m2"] * (1 + deg(k, "zayiat", "osb")) / deg(k, "levha_m2", "osb")),
             g["osb_duvar_m2"], formul="girilen alan × 1,05 ÷ 2,98; alanın nasıl belirlendiği bilinmiyor", durum="soru")
    else:
        ekle("İç cephe kaplama", "OSB 9 mm (TV, klima ve mutfak dolabı arkası)", "1220 × 2440", None,
             formul="hangi duvarlara konduğu bilinmiyor", durum="soru")
    # yalıtım: bütün duvarlar; dış duvarda karkasa göre kat sayısı. İç duvar boyu oda çevrelerinden çıkarılır.
    ic_yuz = sum(o["cevre_m"] for o in g["odalar"])
    ic_boy = g.get("ic_duvar_boyu_m")
    if ic_boy is None:
        ic_boy = (ic_yuz - (d["cevre_m"] - 8 * d["duvar_kalinligi_m"])) / 2
    kat = deg(k, "yalitim_kat")[str(d["karkas_mm"])]
    yal_brut = kat * dis_duvar + ic_boy * h
    ik = deg(k, "kapi_boslugu_m", "ic")
    yal_net = yal_brut - dis_bosluk - g["ic_kapi_adedi"] * ik[0] * ik[1]
    ekle("İç cephe kaplama", "Duvar izolasyonu", "paket 8,64 m²", tavan(yal_net / deg(k, "yalitim_paket_m2")), yal_net, yal_brut,
         formul=f"dış duvar × {kat} kat + iç duvar × 1 kat − boşluklar; ÷ 8,64", durum="uydurma")

    # ── Çatı ────────────────────────────────────────────────────────────────
    c = g["cati"]
    kirma = c["tip"] == "kirma"
    sacak = c["sacak_boyu_toplam_m"]
    kenarlar = c["sacak_kenarlari_m"]
    pm, bm = deg(k, "parca_boyu_m", "mahya"), deg(k, "bindirme_m", "mahya")
    if c["ortu"] == "sandvic_panel":
        zp = deg(k, "zayiat", "sandvic_panel")
        ekle("Çatı kaplamaları", "Sandviç panel", f"L {round(c['panel_boyu_m'] * 1000)} · 100 cm kapatır",
             tavan(c["yuzey_m2"] * (1 + zp) / (c["panel_boyu_m"] * deg(k, "sandvic_panel_kapatma_m"))), c["yuzey_m2"],
             formul="çatı yüzeyi × 1,10 ÷ (panel boyu × 1,00); panel boyu = eğimli boy", durum="uydurma")
        ekle("Çatı kaplamaları", "Metal kiremit mahyası", "L 2800", tavan(c["mahya_hatti_m"] / (pm - bm)), c["mahya_hatti_m"], birim="m",
             formul="mahya hattı (tepe + kırmalar) ÷ (2,8 − 0,20 bindirme)", durum="varsayim")
        ekle("Çatı kaplamaları", "Sandviç panel kapaması", "L 2500", kenar_kenar(kenarlar, 2.5), sacak, birim="m",
             formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma")
    else:
        ekle("Çatı kaplamaları", "Çatı OSB", "1220 × 2440", tavan(c["yuzey_m2"] * (1 + deg(k, "zayiat", "osb")) / deg(k, "levha_m2", "osb")), c["yuzey_m2"],
             formul="çatı yüzeyi × 1,05 ÷ 2,98", durum="uydurma")
        ekle("Çatı kaplamaları", "Metal kiremit", "110 cm kapatır", tavan(sacak / deg(k, "kiremit_kapatma_m")), sacak, birim="m",
             formul="saçak boyu ÷ 1,10; boy = eğimli boy", durum="uydurma")
        for ad in ("Metal kiremit mahyası", "OSB mahyası"):
            ekle("Çatı kaplamaları", ad, "L 2800", tavan(c["mahya_hatti_m"] / (pm - bm)), c["mahya_hatti_m"], birim="m",
                 formul="mahya hattı ÷ (2,8 − 0,20 bindirme)", durum="varsayim")
    if c.get("ozel_mahya_m"):
        ekle("Çatı kaplamaları", "Özel mahya (geniş)", "L 2800", tavan(c["ozel_mahya_m"] / pm), c["ozel_mahya_m"], birim="m",
             formul="girilen boy ÷ 2,8; nereye konduğu bilinmiyor", durum="soru")
    silte = c["cati_boyu_m"] * (c["bina_eni_m"] + deg(k, "silte_en_payi_m"))
    ekle("Çatı kaplamaları", "Çatı şiltesi 80 mm", "9,6 m²/adet", tavan(silte / deg(k, "silte_adet_m2")), silte,
         formul="çatı boyu × (bina eni + 0,20) ÷ 9,6", durum="uydurma")

    # ── Dere ────────────────────────────────────────────────────────────────
    pd, bd = deg(k, "parca_boyu_m", "dere"), deg(k, "bindirme_m", "dere")
    dere = tavan(sacak / (pd - bd))
    ekle("Dere", "Metal dere", "L 4000", dere, sacak, birim="m", formul="saçak boyu ÷ (4,0 − 0,10 bindirme)", durum="varsayim")
    n = c.get("inis_adedi", deg(k, "inis_adedi_varsayilan"))
    ib = deg(k, "inis_basina")
    for ad, anahtar in (("Dere iniş borusu", "inis_borusu"), ("Dere iniş aparatı", "inis_aparati"), ("Açık dirsek", "acik_dirsek"),
                        ("Kapalı dirsek", "kapali_dirsek"), ("İniş kelepçesi", "inis_kelepcesi")):
        ekle("Dere", ad, "L 3000" if anahtar == "inis_borusu" else "adet", n * ib[anahtar], birim="",
             formul=f"iniş sayısı ({n}) × {ib[anahtar]}; iniş sayısının kuralı bilinmiyor (listelerde 7, 7 ve 10)", durum="soru" if "inis_adedi" not in c else "uydurma")
    if c.get("dere_kapagi") is not None:
        ekle("Dere", "Dere kapağı", "adet", c["dere_kapagi"], birim="", formul="girilen sayı; kuralı bilinmiyor", durum="soru")
    ekle("Dere", "Dere kelepçesi", "adet", dere * deg(k, "dere_kelepcesi_dere_basina"), birim="", formul="dere adedi × 8", durum="uydurma")

    # ── Metal aksam ─────────────────────────────────────────────────────────
    ps = deg(k, "parca_boyu_m", "sacak_saci")
    ekle("Metal aksam", "Saçak sacı (30'luk)", "L 2500", kenar_kenar(kenarlar, ps), sacak, birim="m",
         formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma")
    ekle("Metal aksam", c.get("sacak_omegasi", "Saçak omegası"), "L 2500", kenar_kenar(kenarlar, ps), sacak, birim="m",
         formul="her saçak kenarı ÷ 2,5, ayrı ayrı yukarı", durum="uydurma")
    if c.get("sacak_alti") == "boardex":
        sa = sacak * deg(k, "sacak_alti_boardex_eni_m")
        ekle("Metal aksam", "Saçaklar için Boardex", "1200 × 2400", tavan(sa * (1 + deg(k, "zayiat", "boardex")) / deg(k, "levha_m2", "boardex")), sa,
             formul="saçak boyu × 0,30 × 1,15 ÷ 2,88", durum="uydurma")
    if c.get("alin_saci_m"):
        ekle("Metal aksam", "Alın sacı (30'luk)", "300 × 2500",
             tavan(c["alin_saci_m"] * (1 + deg(k, "alin_saci_zayiat")) / deg(k, "parca_boyu_m", "alin_saci")), c["alin_saci_m"], birim="m",
             formul="alın boyu × 1,05 ÷ 2,5; alın boyunun nasıl ölçüldüğü bilinmiyor", durum="soru")
    tavan_toplam = sum(v for v in g["tavan_m2"].values() if v)
    om = tavan_toplam / deg(k, "tavan_omegasi_aralik_m")
    ekle("Metal aksam", "Tavan omegası (60'lık)", "L 3750", tavan(om / deg(k, "parca_boyu_m", "tavan_omegasi")), om, birim="m",
         formul="tavan alanı ÷ 0,60 ÷ 3,75", durum="uydurma")
    kb = deg(k, "kosebent_kati") * ic_yuz
    ekle("Metal aksam", "Köşebent", "L 2500", tavan(kb / deg(k, "parca_boyu_m", "kosebent")), kb, birim="m",
         formul="oda çevreleri toplamı × 2 ÷ 2,5; 62 m² listeyi tutturmuyor", durum="soru")
    boy, not_ = asik_boyu(c, deg(k, "asik", "aralik_m"))
    ekle("Metal aksam", "Aşık", "L 4200", tavan(boy * (1 + deg(k, "asik", "zayiat")) / deg(k, "parca_boyu_m", "asik")), boy, birim="m",
         formul=f"eğim boyunca 60 cm aralık, {not_}; × 1,05 ÷ 4,2", durum="uydurma")

    # ── Kapı ve pencere (modelden doğrudan) ─────────────────────────────────
    for x in g.get("kapi_pencere", []):
        ekle("Kapı ve pencere", x["kalem"], x["boyut"], x["adet"], birim="", formul="modeldeki açıklıklardan", durum=x.get("durum", "model"))

    # ── Vida (çalışma kitabındaki notlardan; 250'lik pakete yuvarlama varsayım) ───────────────
    v = deg(k, "vida")
    alcipan_levha = sum(adet_of(x) for x in ("Duvar alçıpan beyaz", "Duvar alçıpan yeşil", "Tavan alçıpan beyaz", "Tavan alçıpan yeşil",
                                              "Dış cephe Boardex", "Saçaklar için Boardex"))
    ekle("Vida", "Alçıpan vidası (3,5 × 35)", "adet", tavan(alcipan_levha * v["alcipan_vidasi_levha_basina"] / 250) * 250, alcipan_levha, birim="levha",
         formul="alçıpan ve Boardex levha sayısı × 40; 250'ye yuvarlandı")
    pencere = sum(x["adet"] for x in d["bosluklar"] if "kapı" not in x["ad"])
    ekle("Vida", "Pencere vidası (4,8 × 70)", "adet", pencere * v["pencere_vidasi_pencere_basina"], pencere, birim="pencere", formul="pencere sayısı × 20")
    if g.get("celik_panel_adedi"):
        t = v["trapez_5_5x25"]
        say = (adet_of("Aşık") * t["asik"] + adet_of("Tavan omegası (60'lık)") * t["omega_375"] + adet_of(c.get("sacak_omegasi", "Saçak omegası")) * t["omega_240"]
               + g["celik_panel_adedi"] * t["celik_panel"] + (g.get("kosebent_adedi") or adet_of("Köşebent")) * t["kosebent"])
        ekle("Vida", "Trapez vida (5,5 × 25)", "adet", tavan(say / 250) * 250, say, birim="vida",
             formul="aşık × 10 + tavan omegası × 10 + saçak omegası × 6 + çelik panel × 10 + köşebent × 6; 250'ye yuvarlandı")
    ekle("Vida", "İnox taş", "adet", tavan(g["bina_m2"] / v["inox_tasi_m2_bolu"]), g["bina_m2"], formul="bina m² ÷ 10")
    return {"satirlar": S, "ara": {"dis_net_m2": round(dis_net, 3), "beyaz_net_m2": round(ozet["beyaz"][0], 3), "yesil_net_m2": round(ozet["yesil"][0], 3),
                                    "ic_duvar_boyu_m": round(ic_boy, 2), "oda_cevreleri_m": round(ic_yuz, 2),
                                    "yalitim_brut_m2": round(yal_brut, 2), "yalitim_net_m2": round(yal_net, 2), "asik_boyu_m": round(boy, 1)}}


def yaz(sonuc: dict, gercek: dict | None = None) -> str:
    cik, grup = [], None
    for s in sonuc["satirlar"]:
        if s["grup"] != grup:
            grup = s["grup"]
            cik.append(f"\n{grup.upper()}")
        g = (gercek or {}).get(s["kalem"])
        olcu = "" if s["olcu"] is None else f"{s['olcu']:.2f} {s['birim']}".replace(".", ",")
        satir = f"  {s['kalem']:<44s} {s['boyut']:<24s} {'' if s['adet'] is None else s['adet']:>5}  {olcu:>15s}  [{s['durum']}]"
        if g:
            fark = "" if s["adet"] is None else ("AYNI" if s["adet"] == g["adet"] else f"fark {s['adet'] - g['adet']:+d}")
            satir += f"   listede {g['adet']}" + (f", {g['net']}" if "net" in g else "") + f" → {fark}"
        cik.append(satir)
    return "\n".join(cik)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", type=Path)
    ap.add_argument("--karsilastir", type=Path)
    ap.add_argument("--cikti", type=Path)
    ap.add_argument("--md", type=Path, help="tabloyu Markdown olarak yaz")
    a = ap.parse_args()
    g = json.loads(a.girdi.read_text(encoding="utf-8"))
    k = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))
    gercek = json.loads(a.karsilastir.read_text(encoding="utf-8"))["kalemler"] if a.karsilastir else None
    sonuc = hesapla(g, k)
    print(g["ad"])
    print(yaz(sonuc, gercek))
    print("\nara değerler:", sonuc["ara"])
    if gercek:
        es = [s for s in sonuc["satirlar"] if s["kalem"] in gercek and s["adet"] is not None]
        ayni = [s for s in es if s["adet"] == gercek[s["kalem"]]["adet"]]
        print(f"\nkarşılaştırılan {len(es)} kalemin {len(ayni)} tanesinde adet aynı; farklı olanlar: "
              + ", ".join(f"{s['kalem']} ({s['adet']} / {gercek[s['kalem']]['adet']})" for s in es if s not in ayni))
        eksik = [x for x in gercek if x not in {s["kalem"] for s in sonuc["satirlar"]}]
        if eksik:
            print("hesapta olmayan liste kalemleri:", ", ".join(eksik))
        sonuc["karsilastirma"] = {s["kalem"]: {"hesap": s["adet"], "liste": gercek[s["kalem"]]["adet"], "durum": s["durum"]} for s in es}
    if a.md:
        satir = ["| Grup | Kalem | Boyut | Adet | Ölçü | Durum |", "|---|---|---|---|---|---|"]
        for x in sonuc["satirlar"]:
            olcu = "" if x["olcu"] is None else f"{x['olcu']:.1f} {x['birim']}".replace(".", ",")
            satir.append(f"| {x['grup']} | {x['kalem']} | {x['boyut']} | {'' if x['adet'] is None else x['adet']} | {olcu} | {x['durum']} |")
        a.md.write_text("\n".join(satir) + "\n", encoding="utf-8")
    if a.cikti:
        a.cikti.parent.mkdir(parents=True, exist_ok=True)
        a.cikti.write_text(json.dumps({"ad": g["ad"], **sonuc}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
