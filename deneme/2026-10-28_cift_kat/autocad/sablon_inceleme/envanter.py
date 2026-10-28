#!/usr/bin/env python3
"""Güncel Şablon 2024 DXF envanteri — akışla (düşük bellek) tarar.

Çıktı: envanter.json (ham sayımlar) ve envanter.md (okunur özet).
Kullanım: python3 envanter.py Guncel_Sablon_2024.dxf
"""
import json, sys, re, time
from collections import Counter, defaultdict

yol = sys.argv[1]
t0 = time.time()

def taglar(f):
    """(kod, değer) çiftleri; satır sonları \r\n olabilir."""
    while True:
        k = f.readline()
        if not k:
            return
        v = f.readline()
        if not v:
            return
        try:
            kod = int(k)
        except ValueError:
            continue
        yield kod, v.rstrip("\r\n")

header = {}
katmanlar = {}          # ad -> {renk, cizgi}
blok_kayitlari = []     # BLOCK_RECORD adları
stiller, dimstiller, ltypes = [], [], []
layoutlar = []
bloklar = {}            # ad -> {varlik: Counter, insert: Counter, yazi: [..], katman: Counter}
entities = {            # model/pafta alanı varlıkları
    "varlik": Counter(), "katman": Counter(), "insert": Counter(),
    "yazi": [], "paperspace_varlik": Counter(), "dim": 0,
}
# ENTITIES içinde yazıların konumu (kümeleme için)
yazilar = []  # (x, y, yukseklik, metin, katman, paperspace)
insertler = []  # (ad, x, y, katman, dondurme, xolcek, yolcek)

bolum = None
varlik = None            # geçerli varlığın kayıt sözlüğü
tablo = None
blok_adi = None

def varlik_kapat():
    global varlik
    if varlik is None:
        return
    tip = varlik["tip"]
    kat = varlik.get("8", "0")
    ps = varlik.get("67") == "1"
    if bolum == "TABLES" and tip == "LAYER" and "ad" in varlik:
        katmanlar[varlik["ad"]] = {"renk": varlik.get("renk"), "cizgi": varlik.get("cizgi"), "bayrak": varlik.get("bayrak")}
        varlik = None
        return
    if bolum == "BLOCKS" and blok_adi is not None:
        b = bloklar[blok_adi]
        b["varlik"][tip] += 1
        b["katman"][kat] += 1
        if tip == "INSERT":
            b["insert"][varlik.get("2", "?")] += 1
        if tip in ("TEXT", "MTEXT", "ATTDEF") and len(b["yazi"]) < 40:
            b["yazi"].append(varlik.get("1", "") or varlik.get("3", ""))
    elif bolum == "ENTITIES":
        if ps:
            entities["paperspace_varlik"][tip] += 1
        else:
            entities["varlik"][tip] += 1
        entities["katman"][kat] += 1
        if tip == "INSERT":
            entities["insert"][varlik.get("2", "?")] += 1
            try:
                insertler.append((varlik.get("2", "?"), round(float(varlik.get("10", "0")), 1), round(float(varlik.get("20", "0")), 1), kat, round(float(varlik.get("50", "0")), 1), round(float(varlik.get("41", "1")), 3), round(float(varlik.get("42", "1")), 3)))
            except ValueError:
                pass
        if tip == "DIMENSION":
            entities["dim"] += 1
        if tip in ("TEXT", "MTEXT"):
            metin = varlik.get("1", "")
            if tip == "MTEXT":
                metin = "".join(varlik.get("3list", [])) + metin
                metin = re.sub(r"\\[A-Za-z][^;]*;|\{|\}|\\P", " ", metin)
            try:
                x = float(varlik.get("10", "0")); y = float(varlik.get("20", "0"))
                h = float(varlik.get("40", "0"))
            except ValueError:
                x = y = h = 0.0
            yazilar.append((round(x, 1), round(y, 1), round(h, 2), metin.strip(), kat, ps))
    varlik = None

with open(yol, "r", encoding="utf-8", errors="replace", newline="") as f:
    it = taglar(f)
    for kod, deger in it:
        if kod == 0:
            varlik_kapat()
            if deger == "SECTION":
                bolum = None
                continue
            if deger == "ENDSEC":
                bolum = None; tablo = None
                continue
            if bolum == "TABLES":
                if deger == "TABLE":
                    tablo = "?"; continue
                if deger == "ENDTAB":
                    tablo = None; continue
                varlik = {"tip": deger}
                continue
            if bolum == "BLOCKS":
                if deger == "BLOCK":
                    varlik = {"tip": "BLOCK"}; continue
                if deger == "ENDBLK":
                    blok_adi = None; varlik = None; continue
                varlik = {"tip": deger}
                continue
            if bolum == "ENTITIES":
                varlik = {"tip": deger}
                continue
            if bolum == "OBJECTS":
                varlik = {"tip": deger}
                continue
            continue
        if kod == 2 and bolum is None and varlik is None:
            if deger in ("HEADER", "TABLES", "BLOCKS", "ENTITIES", "OBJECTS", "CLASSES", "THUMBNAILIMAGE", "ACDSDATA"):
                bolum = deger
                continue
        if bolum == "HEADER":
            if kod == 9:
                hdr_key = deger
            elif deger and kod in (1, 10, 20, 70, 40, 3):
                header.setdefault(hdr_key, []).append(deger)
            continue
        if bolum == "TABLES":
            if tablo == "?" and kod == 2:
                tablo = deger; continue
            if varlik is not None:
                if varlik["tip"] == "LAYER":
                    if kod == 2: varlik["ad"] = deger
                    elif kod == 62: varlik["renk"] = deger
                    elif kod == 6: varlik["cizgi"] = deger
                    elif kod == 70: varlik["bayrak"] = deger
                elif varlik["tip"] == "BLOCK_RECORD" and kod == 2:
                    blok_kayitlari.append(deger)
                elif varlik["tip"] == "STYLE" and kod == 2:
                    stiller.append(deger)
                elif varlik["tip"] == "DIMSTYLE" and kod == 2:
                    dimstiller.append(deger)
                elif varlik["tip"] == "LTYPE" and kod == 2:
                    ltypes.append(deger)
            continue
        if bolum == "BLOCKS":
            if varlik is not None and varlik["tip"] == "BLOCK":
                if kod == 2:
                    blok_adi = deger
                    bloklar.setdefault(blok_adi, {"varlik": Counter(), "insert": Counter(), "yazi": [], "katman": Counter()})
                    varlik = None
                continue
            if varlik is not None:
                if kod == 3:
                    varlik.setdefault("3list", []).append(deger)
                else:
                    varlik[str(kod)] = deger
            continue
        if bolum == "ENTITIES":
            if varlik is not None:
                if kod == 3:
                    varlik.setdefault("3list", []).append(deger)
                elif str(kod) not in varlik:   # ilk değer (10/20 ilk nokta)
                    varlik[str(kod)] = deger
            continue
        if bolum == "OBJECTS":
            if varlik is not None and varlik["tip"] == "LAYOUT" and kod == 1:
                layoutlar.append(deger)
            continue
varlik_kapat()

# --- özet ---
def c2d(c): return dict(c.most_common())
cikti = {
    "dosya": yol, "sure_sn": round(time.time() - t0, 1),
    "header": {k: v for k, v in header.items() if k in ("$ACADVER", "$INSUNITS", "$EXTMIN", "$EXTMAX", "$DWGCODEPAGE", "$LASTSAVEDBY", "$MEASUREMENT", "$DIMSCALE", "$LTSCALE", "$TEXTSTYLE", "$CLAYER")},
    "katman_sayisi": len(katmanlar), "katmanlar": katmanlar,
    "blok_kaydi_sayisi": len(blok_kayitlari),
    "blok_sayisi": len(bloklar),
    "bloklar": {ad: {"varlik": c2d(b["varlik"]), "ic_insert": c2d(b["insert"]), "katman": c2d(b["katman"]), "yazi": b["yazi"]} for ad, b in bloklar.items()},
    "stiller": stiller, "dimstiller": dimstiller, "cizgi_tipleri": ltypes, "layoutlar": layoutlar,
    "model_varlik": c2d(entities["varlik"]), "pafta_varlik": c2d(entities["paperspace_varlik"]),
    "varlik_katman": c2d(entities["katman"]), "insert_sayimi": c2d(entities["insert"]),
    "olcu_sayisi": entities["dim"], "yazi_sayisi": len(yazilar),
    "yazilar": yazilar,
    "insertler": insertler,
}
with open("envanter.json", "w", encoding="utf-8") as g:
    json.dump(cikti, g, ensure_ascii=False, indent=1)

# okunur özet
L = []
L.append(f"# Güncel Şablon 2024 · DXF envanteri ({time.strftime('%Y-%m-%d %H:%M')})\n")
L.append(f"Kaynak: `{yol}` · tarama {cikti['sure_sn']} sn · sürüm {header.get('$ACADVER')} · INSUNITS {header.get('$INSUNITS')} · EXTMIN {header.get('$EXTMIN')} · EXTMAX {header.get('$EXTMAX')}\n")
L.append(f"- Katman: {len(katmanlar)} · Blok tanımı: {len(bloklar)} · Model varlığı: {sum(entities['varlik'].values())} · Pafta varlığı: {sum(entities['paperspace_varlik'].values())} · Ölçü: {entities['dim']} · Yazı: {len(yazilar)} · Layout: {layoutlar}\n")
L.append("\n## Model alanı varlık türleri\n")
for k, v in entities["varlik"].most_common(): L.append(f"- {k}: {v}")
L.append("\n## Katmanlar (ad · renk · çizgi · varlık sayısı)\n")
for ad in sorted(katmanlar):
    k = katmanlar[ad]; L.append(f"- {ad} · {k.get('renk')} · {k.get('cizgi')} · {entities['katman'].get(ad, 0)}")
L.append("\n## En çok kullanılan bloklar (INSERT sayısı, model+pafta)\n")
for ad, n in entities["insert"].most_common(80): L.append(f"- {ad}: {n}")
L.append(f"\n## Bütün blok tanımları ({len(bloklar)})\n")
for ad in sorted(bloklar, key=str.lower):
    b = bloklar[ad]; v = sum(b["varlik"].values())
    ic = ", ".join(f"{k}×{n}" for k, n in b["insert"].most_common(5))
    yz = " | ".join(x for x in b["yazi"][:4] if x)
    L.append(f"- {ad} · {v} varlık · iç blok: {ic or '-'} · yazı: {yz or '-'}")
L.append("\n## Yazı stilleri / ölçü stilleri / çizgi tipleri\n")
L.append(f"- STYLE: {stiller}\n- DIMSTYLE: {dimstiller}\n- LTYPE: {ltypes}")
with open("envanter.md", "w", encoding="utf-8") as g:
    g.write("\n".join(L) + "\n")
print("bitti", cikti["sure_sn"], "sn; katman", len(katmanlar), "blok", len(bloklar), "varlık", sum(entities["varlik"].values()), "yazı", len(yazilar))
