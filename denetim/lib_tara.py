#!/usr/bin/env python3
"""Kapı B (İE-02) · PHP dosyası sır taraması. SALT OKUNUR: taranan dosyaya yazmaz. DEĞER YAZDIRMAZ.

    python3 lib_tara.py lib.php                               # yalnız tarama
    python3 lib_tara.py lib.php --temiz-kopya lib.clean.php   # bulgu varsa yer tutuculu kopya yazar ve onu yeniden tarar

Çıktıda yalnız şunlar görünür: satır numarası, bulgunun türü, tanımlayıcı adı (kod adı), değerin uzunluğu, alan adları,
işlev adları ve sayılar. Değerin kendisi, bir parçası ya da ham satır yazılmaz; son bir denetim, bulunan her değerin
(ya da 8 karakterlik herhangi bir parçasının) çıktıda geçmediğini doğrular, geçen satırı gizler.

Temiz kopya: yalnız bulunan değerler, biçimi korunarak yer tutucuyla değiştirilir (rakam → aynı uzunlukta rakam, 9 ile
başlar; onaltılık → aynı uzunlukta; e-posta → gizliN@example.invalid; öteki → GIZLI_…). Kod değişmez: iki dosyanın
"iskeleti" (dizge ve yorum içerikleri çıkarılmış kod) birebir aynı olmalı, değişen her satır bir bulgu satırı olmalı ve
kopyanın yeniden taranması bulgu vermemeli; biri tutmazsa kopya silinir ve çıkış kodu 3 olur.
Yalnız Python standart kitaplığı (3.8+).
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

SURUM = "lib_tara 2026-09-28"

# ───────────────────────── PHP sözcük çözümleyici (dizge, yorum, heredoc sınırlarını bulmak için) ─────────────────────────
class Parca:
    __slots__ = ("tur", "bas", "son", "ic_bas", "ic_son")

    def __init__(self, tur, bas, son, ic_bas=None, ic_son=None):
        self.tur, self.bas, self.son = tur, bas, son          # tur: html | kod | tek | cift | yorum | heredoc | nowdoc
        self.ic_bas = bas if ic_bas is None else ic_bas       # içerik (tırnaklar ve heredoc başlığı hariç)
        self.ic_son = son if ic_son is None else ic_son


_HEREDOC = re.compile(r"<<<[ \t]*([\"']?)([A-Za-z_\x80-￿][A-Za-z0-9_\x80-￿]*)\1\r?\n")


def cozumle(s: str) -> list[Parca]:
    parcalar: list[Parca] = []
    n, i = len(s), 0
    kod_bas = None

    def kod_kapat(son):
        nonlocal kod_bas
        if kod_bas is not None and son > kod_bas:
            parcalar.append(Parca("kod", kod_bas, son))
        kod_bas = None

    php = False
    while i < n:
        if not php:
            adaylar = [(s.find(t, i), t) for t in ("<?php", "<?=")]
            adaylar = [(j, t) for j, t in adaylar if j >= 0]
            if not adaylar:
                parcalar.append(Parca("html", i, n)); break
            j, t = min(adaylar)
            if j > i:
                parcalar.append(Parca("html", i, j))
            kod_bas, i, php = j, j + len(t), True
            continue
        c = s[i]
        if s.startswith("?>", i):
            i += 2; kod_kapat(i); php = False; continue
        if c == "'":
            kod_kapat(i); j = i + 1
            while j < n and s[j] != "'":
                j += 2 if s[j] == "\\" else 1
            j = min(j, n)
            parcalar.append(Parca("tek", i, min(j + 1, n), i + 1, j)); i = min(j + 1, n); kod_bas = i; continue
        if c in "\"`":
            kod_kapat(i); j = i + 1
            while j < n and s[j] != c:
                if s[j] == "\\":
                    j += 2; continue
                if s.startswith("{$", j):                     # {$...} içinde tırnak olabilir
                    derin, j = 1, j + 1
                    while j < n and derin:
                        if s[j] in "'\"":
                            q, j = s[j], j + 1
                            while j < n and s[j] != q:
                                j += 2 if s[j] == "\\" else 1
                        elif s[j] == "{":
                            derin += 1
                        elif s[j] == "}":
                            derin -= 1
                        j += 1
                    continue
                j += 1
            j = min(j, n)
            parcalar.append(Parca("cift", i, min(j + 1, n), i + 1, j)); i = min(j + 1, n); kod_bas = i; continue
        if s.startswith("//", i) or (c == "#" and not s.startswith("#[", i)):
            kod_kapat(i); j = i
            while j < n and s[j] != "\n" and not s.startswith("?>", j):
                j += 1
            parcalar.append(Parca("yorum", i, j)); i = j; kod_bas = i; continue
        if s.startswith("/*", i):
            kod_kapat(i); j = s.find("*/", i + 2); j = n if j < 0 else j + 2
            parcalar.append(Parca("yorum", i, j)); i = j; kod_bas = i; continue
        if s.startswith("<<<", i):
            m = _HEREDOC.match(s, i)
            if m:
                kod_kapat(i)
                kapanis = re.compile(r"(?m)^[ \t]*" + re.escape(m.group(2)) + r"(?![A-Za-z0-9_\x80-￿])").search(s, m.end())
                govde_son = kapanis.start() if kapanis else n
                tur = "nowdoc" if m.group(1) == "'" else "heredoc"
                parcalar.append(Parca(tur, i, govde_son, m.end(), govde_son))
                i = govde_son; kod_bas = i; continue
        if kod_bas is None:
            kod_bas = i
        i += 1
    if php:
        kod_kapat(n)
    return parcalar


DIZGE = ("tek", "cift", "heredoc", "nowdoc")
METIN = DIZGE + ("yorum", "html")

# ───────────────────────── desenler ─────────────────────────
DESENLER = [
    ("ozel_anahtar", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)", re.S)),
    ("openai_anahtari", re.compile(r"sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{16,}")),
    ("meta_erisim_anahtari", re.compile(r"EAA[A-Za-z0-9]{20,}")),
    ("jwt", re.compile(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}")),
    ("bearer", re.compile(r"(?<=Bearer )[A-Za-z0-9._~+/=\-]{16,}")),
    ("parola_ozeti", re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}|\$argon2(?:id|i|d)\$[^\s'\"\\]{20,}")),
    ("url_kimlik", re.compile(r"(?<=://)[^/\s:@'\"\\]+:[^/\s@'\"\\]+(?=@)")),
    ("uzun_onaltilik", re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])")),
    ("rastgele_dizge", re.compile(r"(?<![A-Za-z0-9_\-])(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[a-z])(?=[A-Za-z0-9_\-]*[A-Z])[A-Za-z0-9_\-]{32,}(?![A-Za-z0-9_\-])")),
    ("iban", re.compile(r"TR\d{2}(?:[ ]?\d{4}){5}[ ]?\d{2}")),
    ("e_posta", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("telefon", re.compile(r"(?<![\d])(?:\+?90[ \-]?|0)?\(?5\d{2}\)?[ \-]?\d{3}[ \-]?\d{2}[ \-]?\d{2}(?![\d])")),
    ("uzun_rakam", re.compile(r"(?<![\d.])\d{10,}(?![\d.])")),
]
ORNEK_ALAN = re.compile(r"@(?:[\w\-]+\.)*(?:example\.(?:com|org|net)|[\w\-]+\.(?:example|invalid|test|localhost))$", re.I)
KOD_RAKAM = re.compile(r"(?<![\w.$])[1-9][\d_]{11,}(?![\w.])")          # kodda 12+ haneli sayı (telefon, WhatsApp/Meta kimliği)
SIR_ADI = re.compile(r"(?i)(token|secret|passw|parola|sifre|şifre|pwd|api_?key|access_?key|private_?key|credential|auth_?key|"
                     r"verify|salt|signing|client_?secret|app_?secret|(?:^|_)pin(?:$|_))")
YER_TUTUCU = re.compile(r"^(?:GIZLI_[A-Z_]+_\d+|(?:sk-(?:proj-|svcacct-|admin-)?|EAA)GIZLIX*\d+|9(?:0|[ \-()])*\d{1,3}|"
                        r"TR9(?:0|[ ])*\d{1,3}|0+\d{1,4}|gizli\d+@example\.invalid)$")
AD = re.compile(r"^[A-Za-z_\x80-￿][A-Za-z0-9_\x80-￿]{0,63}$")


def yer_tutucu_mu(deger: str) -> bool:
    return bool(YER_TUTUCU.search(deger.strip()))


def gizli_gibi(ad: str, deger: str) -> bool:
    d = deger.strip()
    if not d or yer_tutucu_mu(d):
        return False
    if re.search(r"(?i)(?:^|_)pin(?:$|_)", ad) and re.fullmatch(r"\d{4,8}", d):
        return True
    if len(d) < 8:
        return False
    if d.startswith(("/", "./", "../")) or re.search(r"\.(json|txt|php|log|lock|pem|key|env)$", d, re.I):
        return False                                              # dosya yolu ya da adı
    if re.fullmatch(r"[a-z][a-z0-9_.\-]*", d) and not re.search(r"\d", d):
        return False                                              # alan adı gibi (access_token, hub.verify_token)
    if re.fullmatch(r"https?://\S+", d) and not re.search(r"[?&](?:access_token|token|key|secret)=", d, re.I):
        return False
    if " " in d and not re.search(r"[A-Za-z0-9]{16,}", d):
        return False                                              # cümle (mesaj metni)
    return True


# ───────────────────────── tarama ─────────────────────────
class Tarama:
    def __init__(self, metin: str):
        self.s = metin
        self.p = cozumle(metin)
        self.satir_bas = [0] + [m.end() for m in re.finditer("\n", metin)]
        self.bulgular: list[dict] = []      # {tur, bas, son, satir, ad, uzunluk, butun}
        self._maskeli()
        self._islevler()
        self._desen_tara()
        self._ad_tara()

    def satir(self, ofset: int) -> int:
        return bisect.bisect_right(self.satir_bas, ofset)

    def _maskeli(self):
        """Dizgeler \\x00S<i>\\x00 ile, yorum ve html boşlukla değiştirilmiş kod; ofset eşlemesiyle."""
        parcalar, self.dizge = [], {}
        self.mask_ofset: list[tuple[int, int]] = []          # (maskeli konum, özgün konum)
        konum = 0
        for k, p in enumerate(self.p):
            self.mask_ofset.append((konum, p.bas))
            if p.tur == "kod":
                parca = self.s[p.bas:p.son]
            elif p.tur in DIZGE:
                self.dizge[k] = p; parca = f"\x00S{k}\x00"
            else:
                parca = " "
            parcalar.append(parca); konum += len(parca)
        self.m = "".join(parcalar)

    def ozgun(self, mkonum: int) -> int:
        i = bisect.bisect_right([a for a, _ in self.mask_ofset], mkonum) - 1
        a, b = self.mask_ofset[max(i, 0)]
        return b + (mkonum - a)

    def _islevler(self):
        self.islev_araliklari = []                         # (ad, maskeli başlangıç, maskeli bitiş)
        for m in re.finditer(r"\bfunction\s*&?\s*([A-Za-z_\x80-￿][\w\x80-￿]*)\s*\(", self.m):
            j = self.m.find("{", m.end())
            if j < 0:
                continue
            derin, k = 0, j
            while k < len(self.m):
                if self.m[k] == "{":
                    derin += 1
                elif self.m[k] == "}":
                    derin -= 1
                    if derin == 0:
                        break
                k += 1
            self.islev_araliklari.append((m.group(1), m.start(), k))

    def islev(self, mkonum: int) -> str:
        icinde = [(b, ad) for ad, b, s in self.islev_araliklari if b <= mkonum <= s]
        return max(icinde)[1] if icinde else "(işlev dışı)"

    def _ekle(self, tur, bas, son, ad="", butun=False):
        if any(b["bas"] < son and bas < b["son"] for b in self.bulgular):
            return
        self.bulgular.append({"tur": tur, "bas": bas, "son": son, "satir": self.satir(bas), "ad": ad, "uzunluk": son - bas, "butun": butun})

    def _desen_tara(self):
        for p in self.p:
            if p.tur in METIN:
                for tur, rx in DESENLER:
                    for m in rx.finditer(self.s, p.ic_bas, p.ic_son):
                        deger = m.group(0)
                        if yer_tutucu_mu(deger) or (tur == "e_posta" and ORNEK_ALAN.search(deger)):
                            continue
                        self._ekle(tur, m.start(), m.end())
            elif p.tur == "kod":
                for m in KOD_RAKAM.finditer(self.s, p.bas, p.son):
                    if not yer_tutucu_mu(m.group(0)):
                        self._ekle("kodda_uzun_sayi", m.start(), m.end())

    def _ad_tara(self):
        S = r"\x00S(\d+)\x00"
        kaliplar = [
            re.compile(r"\bdefine\s*\(\s*" + S + r"\s*,\s*" + S),
            re.compile(r"\bconst\s+([A-Za-z_]\w*)\s*=\s*" + S),
            re.compile(r"\$([A-Za-z_\x80-￿][\w\x80-￿]*)\s*=(?![=>])\s*" + S),
            re.compile(r"->\s*([A-Za-z_]\w*)\s*=(?![=>])\s*" + S),
            re.compile(r"\[\s*" + S + r"\s*\]\s*=(?![=>])\s*" + S),
            re.compile(S + r"\s*=>\s*" + S),
        ]
        for i, rx in enumerate(kaliplar):
            for m in rx.finditer(self.m):
                ad = self._dizge_ic(int(m.group(1))) if i in (0, 4, 5) else m.group(1)
                k = int(m.group(2))
                if re.match(r"\s*\.(?!=)", self.m[m.end():]):         # 'Bearer ' . $x gibi birleştirme: önek, değer değil
                    continue
                p = self.dizge[k]
                if not ad or not SIR_ADI.search(ad) or not gizli_gibi(ad, self.s[p.ic_bas:p.ic_son]):
                    continue
                if any(p.ic_bas <= b["bas"] and b["son"] <= p.ic_son for b in self.bulgular):
                    continue                                      # desen zaten buldu; daha belirgin tür kalır
                self._ekle("sir_adli_deger", p.ic_bas, p.ic_son, ad=ad if AD.match(ad) else "(ad yazılamaz)", butun=True)

    def _dizge_ic(self, k: int) -> str:
        p = self.dizge.get(k)
        return self.s[p.ic_bas:p.ic_son] if p else ""

    # ── bilgi (değer içermez) ──
    def kancalar(self) -> dict:
        sonuc = {}
        for ad in ("PM_OFFLINE_TEST", "pm_test_remote"):
            yerler = [(self.satir(self.ozgun(m.start())), self.islev(m.start())) for m in re.finditer(re.escape(ad), self.m)]
            yerler += [(self.satir(p.ic_bas), self.islev(self._mkonum_dizge(k)))
                       for k, p in self.dizge.items() if self.s[p.ic_bas:p.ic_son] == ad]
            sonuc[ad] = sorted(set(yerler))
        return sonuc

    def _mkonum_dizge(self, k: int) -> int:
        return self.m.find(f"\x00S{k}\x00")

    def ag_yerleri(self) -> list[tuple[str, int, str]]:
        """Ağa çıkabilecek çağrılar. file_get_contents/fopen/copy: ilk argüman URL dizgesiyse "ağ", değişkense "değişkenle"
        (ağ olabilir), yerel yol dizgesiyse sayılmaz."""
        cagrilar = r"\b(curl_init|curl_exec|curl_multi_exec|fsockopen|pfsockopen|stream_socket_client|stream_context_create|get_headers|" \
                   r"mail|socket_connect|file_get_contents|fopen|copy|shell_exec|exec|system|passthru|proc_open|popen)\s*\("
        yerler = []
        for m in re.finditer(cagrilar, self.m):
            if re.search(r"(?:->|::|\bfunction\s+)\s*$", self.m[max(0, m.start() - 12):m.start()]):
                continue                                          # yöntem çağrısı ya da aynı adlı işlev tanımı
            ad = m.group(1)
            if ad in ("file_get_contents", "fopen", "copy"):
                arg = re.match(r"\s*\x00S(\d+)\x00", self.m[m.end():])
                if arg:
                    if not re.match(r"(?i)(https?|ftp)://", self._dizge_ic(int(arg.group(1)))):
                        continue                                  # yerel dosya yolu
                elif re.match(r"\s*(?:__DIR__|dirname\s*\(|[A-Z][A-Z0-9_]*\s*\.)", self.m[m.end():]):
                    continue                                      # sabit klasörle kurulan yerel yol (PM_DATA . '/…')
                else:
                    ad += " (değişkenle; ağ olabilir)"
            yerler.append((ad, self.satir(self.ozgun(m.start())), self.islev(m.start())))
        return yerler

    def alan_adlari(self) -> list[str]:
        adlar = set()
        for p in self.p:
            if p.tur in METIN:
                for m in re.finditer(r"(?i)\b(?:https?|wss?|ftp)://([A-Za-z0-9.\-]+)", self.s[p.ic_bas:p.ic_son]):
                    adlar.add(re.sub(r"\d{5,}", "…", m.group(1).lower()))
        return sorted(adlar)

    def eklentiler(self) -> dict:
        onekler = {"curl": r"curl_\w+", "mbstring": r"mb_\w+", "openssl": r"openssl_\w+", "fileinfo": r"finfo_\w+|mime_content_type",
                   "session": r"session_\w+", "iconv": r"iconv\w*", "zlib": r"gz\w+", "zip": r"ZipArchive|zip_\w+", "json": r"json_\w+",
                   "hash": r"hash\w*", "sodium": r"sodium_\w+", "ctype": r"ctype_\w+", "filter": r"filter_\w+", "posix": r"posix_\w+",
                   "xml/dom": r"simplexml_\w+|DOMDocument|xml_\w+", "gd": r"image\w+|getimagesize", "pdo/mysqli": r"PDO|mysqli\w*",
                   "sockets": r"socket_\w+", "exif": r"exif_\w+", "bcmath": r"bc\w+", "intl": r"Normalizer|IntlChar|Collator|NumberFormatter"}
        return {ad: n for ad, rx in onekler.items() if (n := len(re.findall(r"\b(?:" + rx + r")\s*\(|\bnew\s+(?:" + rx + r")\b", self.m)))}

    def iskelet(self) -> str:
        out = []
        for p in self.p:
            if p.tur == "kod":
                out.append(KOD_RAKAM.sub("#", self.s[p.bas:p.son]))
            elif p.tur in DIZGE:
                out.append(self.s[p.bas:p.ic_bas] + "…" + self.s[p.ic_son:p.son])
            else:
                out.append("‹" + p.tur + "›")
        return "".join(out)


# ───────────────────────── yer tutucu ─────────────────────────
def yer_tutucu(tur: str, deger: str, n: int) -> str:
    rakamlar = sum(ch.isdigit() for ch in deger)
    if tur in ("telefon", "uzun_rakam", "kodda_uzun_sayi", "iban") or (tur == "sir_adli_deger" and deger.isdigit()):
        sira = str(n)
        yeni = list(("9" + "0" * max(rakamlar - 1 - len(sira), 0) + sira)[-rakamlar:] if rakamlar > len(sira) else sira.rjust(rakamlar, "9"))
        return "".join(yeni.pop(0) if ch.isdigit() else ch for ch in deger)
    if tur == "uzun_onaltilik":
        return str(n).rjust(len(deger), "0")
    if tur == "e_posta":
        return f"gizli{n}@example.invalid"
    if tur in ("openai_anahtari", "meta_erisim_anahtari"):
        onek = re.match(r"sk-(?:proj-|svcacct-|admin-)?|EAA", deger).group(0)
        kalan = len(deger) - len(onek)
        return onek + ("GIZLI" + "X" * kalan)[:max(kalan - len(str(n)), 5)] + str(n)
    return f"GIZLI_{tur.upper()}_{n}" + "\n" * deger.count("\n")          # çok satırlı değerde satır sayısı korunur


def temiz_metin(t: Tarama) -> str:
    s, parcalar, son = t.s, [], 0
    for n, b in enumerate(sorted(t.bulgular, key=lambda x: x["bas"]), 1):
        parcalar.append(s[son:b["bas"]]); parcalar.append(yer_tutucu(b["tur"], s[b["bas"]:b["son"]], n)); son = b["son"]
    parcalar.append(s[son:])
    return "".join(parcalar)


# ───────────────────────── çıktı ─────────────────────────
class Cikti:
    def __init__(self, gizliler: list[str]):
        self.gizliler = [g for g in gizliler if len(g) >= 4]
        self.satirlar: list[str] = []

    def yaz(self, satir: str = ""):
        for g in self.gizliler:
            parca = 8 if len(g) >= 8 else len(g)
            if any(g[i:i + parca] in satir for i in range(len(g) - parca + 1)):
                satir = "   [bu çıktı satırı gizlendi: bulunan bir değerin parçasını içeriyordu]"; break
        self.satirlar.append(satir); print(satir)


def rapor(t: Tarama, yol: Path, veri: bytes, c: Cikti):
    c.yaz(f"== Kapı B · sır taraması ({SURUM}) · salt okunur · değer yazılmaz")
    c.yaz(f"dosya: {yol.name} · {len(veri):,} bayt · {t.s.count(chr(10)) + (not t.s.endswith(chr(10)))} satır · sha256 {hashlib.sha256(veri).hexdigest()[:16]}…".replace(",", "."))
    c.yaz(f"-- bulgular: {len(t.bulgular)} (satır · tür · ad · uzunluk)")
    for b in sorted(t.bulgular, key=lambda x: x["bas"]):
        c.yaz(f"   satır {b['satir']} · {b['tur']}" + (f" · {b['ad']}" if b["ad"] else "") + f" · {b['uzunluk']} karakter")
    kanca = t.kancalar()
    c.yaz("-- test kancaları")
    for ad, yerler in kanca.items():
        c.yaz(f"   {ad}: {len(yerler)} yer" + (" · " + ", ".join(f"satır {s} ({i})" for s, i in yerler) if yerler else " · YOK"))
    c.yaz("-- ağ çağrısı yerleri (işlev adıyla)")
    ag = t.ag_yerleri()
    for ad, satir, isl in ag:
        c.yaz(f"   {ad}: satır {satir} ({isl})")
    if not ag:
        c.yaz("   yok")
    c.yaz(f"-- URL'lerdeki alan adları: {', '.join(t.alan_adlari()) or 'yok'}")
    c.yaz(f"-- kullanılan eklenti işlevleri: {', '.join(f'{k} {v}' for k, v in t.eklentiler().items()) or 'yok'}")
    c.yaz(f"-- işlev sayısı: {len(t.islev_araliklari)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dosya")
    ap.add_argument("--temiz-kopya", help="bulgu varsa yer tutuculu kopyanın yolu (özgün dosyanın yolu olamaz)")
    a = ap.parse_args()
    yol = Path(a.dosya)
    veri = yol.read_bytes()                                                # yalnız okuma
    metin = veri.decode("utf-8", errors="surrogateescape")
    t = Tarama(metin)
    c = Cikti([metin[b["bas"]:b["son"]] for b in t.bulgular])
    rapor(t, yol, veri, c)
    if not t.bulgular:
        c.yaz("SONUÇ: gizli ya da kişisel veri bulgusu yok" + (" → temiz kopya gerekmedi, yazılmadı" if a.temiz_kopya else ""))
        return 0
    if not a.temiz_kopya:
        c.yaz(f"SONUÇ: {len(t.bulgular)} bulgu. Temiz kopya için --temiz-kopya verin.")
        return 1
    hedef = Path(a.temiz_kopya)
    if hedef.resolve() == yol.resolve():
        c.yaz("DURDU: temiz kopya özgün dosyanın üzerine yazılamaz"); return 2
    temiz = temiz_metin(t)
    t2 = Tarama(temiz)
    ozgun_satir, temiz_satir = metin.split("\n"), temiz.split("\n")
    bulgu_satirlari = {t.satir(b["bas"]) + k for b in t.bulgular for k in range(metin[b["bas"]:b["son"]].count("\n") + 1)}
    degisen = {i + 1 for i, (x, y) in enumerate(zip(ozgun_satir, temiz_satir)) if x != y}
    ayni_iskelet = t.iskelet() == t2.iskelet() and len(t.p) == len(t2.p)
    kontroller = [("kopyanın yeniden taranması: bulgu 0", not t2.bulgular),
                  ("kod iskeleti özgünle birebir aynı (yalnız dizge ve yorum içerikleri değişti)", ayni_iskelet),
                  (f"satır sayısı aynı ({len(ozgun_satir)})", len(ozgun_satir) == len(temiz_satir)),
                  (f"değişen {len(degisen)} satırın hepsi bulgu satırı", degisen <= bulgu_satirlari),
                  ("test kancaları kopyada da aynı", t2.kancalar() == t.kancalar())]
    c.yaz(f"-- temiz kopya: {hedef.name}")
    for ad, ok in kontroller:
        c.yaz(f"   {'✓' if ok else '✗'} {ad}")
    if not all(ok for _, ok in kontroller):
        c.yaz("DURDU: temiz kopya doğrulanamadı; yazılmadı"); return 3
    fd, gecici = tempfile.mkstemp(prefix=".lib_tara_", dir=str(hedef.parent))
    with os.fdopen(fd, "wb") as f:
        f.write(temiz.encode("utf-8", errors="surrogateescape"))
    try:
        os.chmod(gecici, 0o600)
    except OSError:
        pass
    os.replace(gecici, hedef)
    yazilan = hedef.read_bytes()
    son = Tarama(yazilan.decode("utf-8", errors="surrogateescape"))
    c.yaz(f"   yazıldı: {len(yazilan):,} bayt · sha256 {hashlib.sha256(yazilan).hexdigest()[:16]}… · diskten yeniden tarama: bulgu {len(son.bulgular)}".replace(",", "."))
    c.yaz(f"   özgün dosyaya dokunulmadı: sha256 {hashlib.sha256(yol.read_bytes()).hexdigest()[:16]}… (taramanın başındakiyle {'aynı' if yol.read_bytes() == veri else 'FARKLI'})")
    c.yaz(f"SONUÇ: {len(t.bulgular)} bulgu → {hedef.name} yazıldı ve doğrulandı" if not son.bulgular else "SONUÇ: DURDU (diskteki kopyada bulgu)")
    return 0 if not son.bulgular else 3


if __name__ == "__main__":
    sys.exit(main())
