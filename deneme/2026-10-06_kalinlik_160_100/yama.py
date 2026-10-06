"""Duvar kalınlığı seçeneği için Motor'un deneme kopyasını üretir (6 Ekim 2026).

Canlı Motor (`motor/`) değişmez. Bu betik `motor/` altındaki dört dosyayı okur, kalınlığın sabit yazıldığı yerleri
İş Emri'ndeki `yapi.duvar_kalinligi_cm` alanına bağlar ve sonucu `cikti/motor_k/` altına yazar (depoya girmez).
Her değişiklik kaynakta tam olarak beklenen sayıda bulunmak zorundadır; Motor değişirse betik durur, sessizce
yanlış yama uygulamaz. Alan verilmezse kalınlıklar 10 / 6 cm kalır ve çıktı canlı Motor'unkiyle aynıdır
(`kos.py` bunu P6001 ile sınar).

Kalınlığa bağlanan yerler:
  geometry  aks başlangıcı (X, Y), dış ölçü (W, H), duvar yarı kalınlıkları, katman adları
  katalog   pano kodunun anahtarına kalınlık ve yükseklik; köşe ve üçlü H bağlantı ölçüleri
  dxf_out   katman adları, üçlü H bloğunun ölçeği, iç kapı sembolünün yeri, lento, pafta yazıları
  validate  katman adları ve beklenen duvar kalınlığı
"""
from __future__ import annotations
import difflib, shutil
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
MOTOR = KOK / "motor"


def _degistir(src: str, eski: str, yeni: str, adet: int = 1, ad: str = "") -> str:
    n = src.count(eski)
    if n != adet:
        raise SystemExit(f"DUR: yama yeri bulunamadı ya da sayısı değişti ({ad}): {n} / beklenen {adet}\n  aranan: {eski!r}")
    return src.replace(eski, yeni)


def _geometry(s: str) -> str:
    ad = "geometry.py"
    s = _degistir(s, "    return 10.0 + MOD * i\n", "    return T_DIS + MOD * i\n", ad=ad)
    s = _degistir(s, "    return 5.0 + MOD * j\n", "    return T_DIS / 2.0 + MOD * j\n", ad=ad)
    s = _degistir(s, "W, H = MOD * nx + 20.0, MOD * ny + 10.0", "W, H = MOD * nx + 2.0 * T_DIS, MOD * ny + T_DIS", ad=ad)
    s = _degistir(s, '    yapi = is_emri["yapi"]\n    if yapi.get("sistem", "prefabrik") != "prefabrik":',
                  '    yapi = is_emri["yapi"]\n    _k = yapi.get("duvar_kalinligi_cm") or {}\n'
                  '    kalinlik_ayarla(float(_k.get("dis", 10.0)), float(_k.get("ic", 6.0)))\n'
                  '    if yapi.get("sistem", "prefabrik") != "prefabrik":', ad=ad)
    s = _degistir(s, "\nclass IsEmriHatasi(ValueError):\n    pass\n",
                  "\nclass IsEmriHatasi(ValueError):\n    pass\n\n\n"
                  "def kalinlik_ayarla(dis_cm: float, ic_cm: float) -> None:\n"
                  '    """Deneme: dış / iç duvar kalınlığı (cm). Verilmezse 10 / 6."""\n'
                  "    global T_DIS, T_IC\n"
                  "    if not (6.0 <= ic_cm <= dis_cm <= 30.0):\n"
                  '        raise IsEmriHatasi(f"Duvar kalınlığı aralık dışı: dış {dis_cm} / iç {ic_cm} cm")\n'
                  "    if dis_cm == ic_cm:\n"
                  '        raise IsEmriHatasi("Dış ve iç duvar aynı kalınlıkta: katman adları ayrışmıyor (deneme sınırı)")\n'
                  "    T_DIS, T_IC = float(dis_cm), float(ic_cm)\n\n\n"
                  "def _mm(cm: float) -> str:\n"
                  '    return f"{cm * 10:g}"\n\n\n'
                  "def katman(ad: str) -> str:\n"
                  '    """Kalınlık taşıyan katman adını geçerli kalınlığa çevirir (10 / 6 cm\'de ad değişmez)."""\n'
                  '    return {"DIS_DUVAR_100": f"DIS_DUVAR_{_mm(T_DIS)}", "IC_DUVAR_60": f"IC_DUVAR_{_mm(T_IC)}",\n'
                  '            "KOSE_PROFIL_100": f"KOSE_PROFIL_{_mm(T_DIS)}", "KOSE_PROFIL_60": f"KOSE_PROFIL_{_mm(T_IC)}",\n'
                  '            "IC_UCLU_H_60": f"IC_UCLU_H_{_mm(T_IC)}"}.get(ad, ad)\n', ad=ad)
    return s


def _katalog(s: str) -> str:
    ad = "katalog.py"
    s = _degistir(s, 'return (fam, round(float(dims[0]), 1), _kind_from_label(m["label"]))',
                  'return (fam, round(float(dims[0]), 1), _kind_from_label(m["label"]), round(float(dims[1]), 1), round(float(dims[2]), 1))', ad=ad)
    s = _degistir(s, "        self.yeni = []          # bu işte tahsis edilen yeni kodlar\n",
                  "        self.yeni = []          # bu işte tahsis edilen yeni kodlar\n"
                  "        self.t_dis_cm, self.t_ic_cm, self.yukseklik_cm = 10.0, 6.0, 250.0   # deneme: Cizici İş Emri'nden ayarlar\n", ad=ad)
    s = _degistir(s, '    def pano(self, dis: bool, boy_cm: float, kind: str, yukseklik_cm: float = 250) -> str:\n'
                     '        fam = "D" if dis else "I"; L = round(boy_cm * 10, 1)\n'
                     '        key = (fam, L, kind)\n',
                  '    def pano(self, dis: bool, boy_cm: float, kind: str, yukseklik_cm: float | None = None) -> str:\n'
                  '        fam = "D" if dis else "I"; L = round(boy_cm * 10, 1)\n'
                  '        yukseklik_cm = self.yukseklik_cm if yukseklik_cm is None else yukseklik_cm\n'
                  '        kal = round((self.t_dis_cm if dis else self.t_ic_cm) * 10, 1)\n'
                  '        key = (fam, L, kind, kal, round(yukseklik_cm * 10, 1))\n', ad=ad)
    s = _degistir(s, "[L, 100 if dis else 60, round(yukseklik_cm * 10)])", "[L, int(kal) if kal == int(kal) else kal, round(yukseklik_cm * 10)])", ad=ad)
    s = _degistir(s, '        keys = {"ic_kose": ("B", (30.0, 60.0)), "dis_kose": ("B", (50.0, 100.0)), "uclu_h": ("B", (60.0,)), "dikme": ("B", (100.0, 100.0))}\n',
                  '        td, ti = round(self.t_dis_cm * 10, 1), round(self.t_ic_cm * 10, 1)\n'
                  '        keys = {"ic_kose": ("B", (ti / 2, ti)), "dis_kose": ("B", (td / 2, td)), "uclu_h": ("B", (ti,)), "dikme": ("B", (100.0, 100.0))}\n', ad=ad)
    s = _degistir(s, '        labels = {"ic_kose": ("İç köşe bağlantısı", [30, 60, None]), "dis_kose": ("100×50 köşe bağlantısı", [50, 100, None]),\n'
                     '                  "uclu_h": ("Üçlü H bağlantı", [60, None, None]), "dikme": ("Veranda dikmesi", [100, 100, None])}\n',
                  '        labels = {"ic_kose": (f"{ti:g}×{ti / 2:g} iç köşe bağlantısı", [ti / 2, ti, None]), "dis_kose": (f"{td:g}×{td / 2:g} köşe bağlantısı", [td / 2, td, None]),\n'
                  '                  "uclu_h": (f"Üçlü H bağlantı {ti:g}", [ti, None, None]), "dikme": ("Veranda dikmesi", [100, 100, None])}\n', ad=ad)
    return s


def _dxf_out(s: str) -> str:
    ad = "dxf_out.py"
    s = _degistir(s, "        self.plan, self.kat = plan, katalog\n",
                  "        self.plan, self.kat = plan, katalog\n"
                  "        katalog.t_dis_cm, katalog.t_ic_cm = G.T_DIS, G.T_IC\n"
                  '        katalog.yukseklik_cm = float(plan.is_emri["yapi"].get("duvar_yuksekligi_cm", 250))\n', ad=ad)
    s = _degistir(s, "        for name, color, lt in LAYERS:\n", "        for name, color, lt in [(G.katman(n), c, l) for n, c, l in LAYERS]:\n", ad=ad)
    s = _degistir(s, 'self.h_blok_adi = f"BOM_{kod}_UCLU_H_60"', 'self.h_blok_adi = f"BOM_{kod}_UCLU_H_{G._mm(G.T_IC)}"', ad=ad)
    s = _degistir(s, "            blk.add_line((float(d[10]) - ax, float(d[20]) - ay), (float(d[11]) - ax, float(d[21]) - ay), dxfattribs",
                  "            kk = G.T_IC / 6.0   # kaynak blok 60 mm iç duvar içindir\n"
                  "            blk.add_line(((float(d[10]) - ax) * kk, (float(d[20]) - ay) * kk), ((float(d[11]) - ax) * kk, (float(d[21]) - ay) * kk), dxfattribs", ad=ad)
    s = _degistir(s, '            (ix, iy), rot, xs = IC_KAPI_VARYANT[var]; dname, _ = self.dograma["ic82"]\n',
                  '            (ix, iy), rot, xs = IC_KAPI_VARYANT[var]; dname, _ = self.dograma["ic82"]\n'
                  '            if var.startswith("SAG"): ix += t - 6.0   # kaynak yerleşim 60 mm duvarın +x yüzüne göredir\n', ad=ad)
    # pencere sembolü 100 mm duvarda kalınlığın ortasındadır; kalın duvarda da ortada tutulur
    s = _degistir(s, '            if nat == "V": ins, rot = (t - bb[2], s - bb[1]), 0.0\n'
                     '            else:          ins, rot = (t - bb[3], s + bb[2]), 270.0\n',
                  '            orta = (t - 10.0) / 2.0\n'
                  '            if nat == "V": ins, rot = (t - bb[2] - orta, s - bb[1]), 0.0\n'
                  '            else:          ins, rot = (t - bb[3] - orta, s + bb[2]), 270.0\n', ad=ad)
    s = _degistir(s, 'layer = "DIS_DUVAR_100" if d.tur == "dis" else "IC_DUVAR_60"', 'layer = G.katman("DIS_DUVAR_100") if d.tur == "dis" else G.katman("IC_DUVAR_60")', ad=ad)
    s = _degistir(s, '("KOSE_PROFIL_100" if k.tur == "dis" else "KOSE_PROFIL_60")', '(G.katman("KOSE_PROFIL_100") if k.tur == "dis" else G.katman("KOSE_PROFIL_60"))', ad=ad)
    s = _degistir(s, '"MONTAJ_STANDART" if montaj else "IC_UCLU_H_60"', '"MONTAJ_STANDART" if montaj else G.katman("IC_UCLU_H_60")', ad=ad)
    s = _degistir(s, "topuk = float(cati.get(\"topuk_cm\", 10)); lento = 50.0\n",
                  "topuk = float(cati.get(\"topuk_cm\", 10)); lento = hy - PENCERE_UST_KOTU\n", ad=ad)
    s = _degistir(s, 'LABEL = "ÖN ONAYA SUNULAN TASLAK — ÜRETİM/STATİK PROJESİ DEĞİLDİR"\n',
                  'LABEL = "ÖN ONAYA SUNULAN TASLAK — ÜRETİM/STATİK PROJESİ DEĞİLDİR"\n'
                  "PENCERE_UST_KOTU = 200.0   # 250 cm duvarda lento 50; yükseklik değişince üst kot sabit tutulur (çıkarım, teyit bekliyor)\n", ad=ad)
    s = _degistir(s, "    plan = G.kur(is_emri)\n    t0 = time.time()\n",
                  "    plan = G.kur(is_emri)\n    plan.uyarilar[:0] = list(is_emri.get(\"pafta_uyarilari\", []))\n    t0 = time.time()\n", ad=ad)
    s = _degistir(s, '"Pencereler pano ortasında. Pencere üstünden duvar üstüne (lento): 50 cm."',
                  'f"Pencereler pano ortasında. Pencere üstünden duvar üstüne (lento): {fmt(float(yapi.get(\'duvar_yuksekligi_cm\', 250)) - PENCERE_UST_KOTU)} cm."', ad=ad)
    s = _degistir(s, '("Dış duvar / iç duvar", "100 mm / 60 mm")', '("Dış duvar / iç duvar", f"{G._mm(G.T_DIS)} mm / {G._mm(G.T_IC)} mm")', ad=ad)
    s = _degistir(s, 'c.text(f"Duvar: 10 / 6 cm | ', 'c.text(f"Duvar: {fmt(G.T_DIS)} / {fmt(G.T_IC)} cm | ', ad=ad)
    # pafta yerleşimi: çatı yükseldikçe ve duvar uzadıkça alt sıra aşağı kayar (773 cm genişlik ve 250 cm duvarda kayma 0)
    s = _degistir(s, "    c.ciz_on_gorunus(0.0, -600.0)\n    c.ciz_cati_profili(gap, -550.0)\n",
                  "    _cati = is_emri.get(\"cati\", {})\n"
                  "    _rise = float(_cati.get(\"topuk_cm\", 10)) + (W + 2 * float(_cati.get(\"sacak_cm\", 30))) / 2 * float(_cati.get(\"egim_yuzde\", 33)) / 100.0\n"
                  "    kay = max(0.0, _rise - 147.445)\n"
                  "    kay2 = kay + max(0.0, float(yapi.get(\"duvar_yuksekligi_cm\", 250)) - 250.0)\n"
                  "    c.ciz_on_gorunus(0.0, -600.0 - kay)\n    c.ciz_cati_profili(gap, -550.0 - kay)\n", ad=ad)
    s = _degistir(s, "(cx, -1090), 18,", "(cx, -1090 - kay2), 18,", ad=ad)
    s = _degistir(s, "(cx, -1130), 14,", "(cx, -1130 - kay2), 14,", ad=ad)
    s = _degistir(s, "(cx, -1165), 13,", "(cx, -1165 - kay2), 13,", ad=ad)
    s = _degistir(s, "(cx, -1200 - 25 * i), 12,", "(cx, -1200 - kay2 - 25 * i), 12,", ad=ad)
    s = _degistir(s, '"generator": "portman-motor-v1.1",', '"generator": "portman-motor-v1.1+deneme-kalinlik-2026-10-06",', ad=ad)
    s = _degistir(s, 'sha256(ROOT / "motor" / f)', "sha256(Path(__file__).resolve().parent / f)", ad=ad)
    return s


def _validate(s: str) -> str:
    ad = "validate.py"
    s = _degistir(s, "    msp = doc.modelspace(); W, H = plan.W, plan.H\n",
                  "    msp = doc.modelspace(); W, H = plan.W, plan.H\n"
                  '    WALL_LAYERS = {G.katman("IC_DUVAR_60"), G.katman("DIS_DUVAR_100")}\n'
                  '    KOSE_LAYERS = {G.katman("KOSE_PROFIL_60"), G.katman("KOSE_PROFIL_100")}\n', ad=ad)
    s = _degistir(s, '            th = 6 if L == "IC_DUVAR_60" else 10\n', '            th = G.T_IC if L == G.katman("IC_DUVAR_60") else G.T_DIS\n', ad=ad)
    s = _degistir(s, """msp.query('INSERT[layer=="IC_UCLU_H_60"]')""", """msp.query(f'INSERT[layer=="{G.katman("IC_UCLU_H_60")}"]')""", ad=ad)
    # Dış ölçü denetimi: duvarların kapladığı kutu Plan'ın ayak iziyle, açık mahallerle birlikte de (0,0,W,H) ile aynı olmalı.
    # Canlı denetim duvarların (0,0,W,H)'yi doldurmasını bekler; cephenin tamamı veranda olunca duvarlar y=0'a inmez.
    s = _degistir(s, "    if max(abs(a - b) for a, b in zip(ext, (0, 0, W, H))) > 1e-6:\n"
                     '        hatalar.append(f"Dış ölçüler {ext} beklenen (0,0,{W},{H})")\n',
                  "    if max(abs(a - b) for a, b in zip(ext, fp_plan.bounds)) > 1e-6:\n"
                  '        hatalar.append(f"Duvarların kutusu {ext} Plan ayak izi {fp_plan.bounds} ile uyuşmuyor")\n'
                  "    tum = unary_union([fp_plan] + [m.poly for m in plan.mahaller.values() if m.acik]).bounds\n"
                  "    if max(abs(a - b) for a, b in zip(tum, (0, 0, W, H))) > 1e-6:\n"
                  '        hatalar.append(f"Dış ölçüler {tum} beklenen (0,0,{W},{H})")\n', ad=ad)
    return s


YAMALAR = {"geometry.py": _geometry, "katalog.py": _katalog, "dxf_out.py": _dxf_out, "validate.py": _validate}


def uret(hedef: Path) -> Path:
    """`hedef/motor_k/` paketini yazar; yama farkını `hedef/motor_k.diff` olarak bırakır. Paketin yolunu döndürür."""
    paket = Path(hedef) / "motor_k"
    if paket.exists():
        shutil.rmtree(paket)
    paket.mkdir(parents=True)
    fark = []
    for ad, yama in YAMALAR.items():
        eski = (MOTOR / ad).read_text(encoding="utf-8")
        yeni = yama(eski)
        (paket / ad).write_text(yeni, encoding="utf-8")
        fark += difflib.unified_diff(eski.splitlines(keepends=True), yeni.splitlines(keepends=True), f"motor/{ad}", f"motor_k/{ad}", n=1)
    (paket / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(MOTOR / "malzeme_katalogu.json", paket / "malzeme_katalogu.json")
    (Path(hedef) / "motor_k.diff").write_text("".join(fark), encoding="utf-8")
    return paket


if __name__ == "__main__":
    p = uret(Path(__file__).resolve().parent / "cikti")
    print(f"yazıldı: {p}")
