"""İE-20 PR-1 · Görsel ve PDF ile talep: bayinin plan çiziminin okunması.

LLM anlar, kod karar verir: LLM bayinin gönderdiği resmi ya da PDF'i yalnız okur ve okuduğunu `CizimOkumasi` kalıbına yazar (araç
`cizim_oku`): dış ölçü, ölçü zincirleri, odalar (yazılı m² ve çizimdeki dikdörtgenleri), kapılar, pencereler, verandalar, çatı. Kod okunanı
düzeltmez, denetler: zincirlerin toplamı, oda alanları ile yazılı m², odaların gövdeyi örtmesi; prefabrikte oda sınırlarının pano ızgarasına
oturması. Tutmayan her şey bayiye "emin olamadım" diye sorulur (sessiz yuvarlama yok; ızgaraya oturtma bayiye yazılır). Bayinin teyidi
olmadan plan çizilmez: teyitten sonra okuma prefabrikte İş Emri'ne (`is_emri_prefabrik`; TK-01 teklif çalışmasının kuralları), çelikte
İE-14'ün plan şemasına (`plan_celik`) çevrilir; çizimi bugünkü Motor yapar.

Okumanın kendi istemi ve kalıbı vardır: `prompt.md`, `sema.py` (Talep) ve harness değişmez (İE-14'teki gibi). Bayinin düzeltmesi ve
çizilmiş planın revizyonu aynı kalıpla okunur (`duzelt`: önceki okuma + bayinin sözü → yeni okuma); kod iki okumayı kıyaslar ve değişeni
bayiye yazar (`degisenler`).

Çerçeveler: okuma çizimin kendi çerçevesindedir (köken gövdenin çizimdeki sol üst dış köşesi, x sağa, y aşağı, cm). `kanonik` girişi alta
çevirir: x soldan (sol dış yüz) sağa, y arkadan (arka dış yüz) öne; bu Pano Motor'unun `dizilim.baslangic: arka-sol` çerçevesidir.
"""
from __future__ import annotations

import base64
import json
import math
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from beyin import llm, numara

KAYNAK = "cizim-okuma"                  # İş Emri `talep.kaynak`: plan bayinin çiziminden okundu (revizyon da okumadan sürer)
ARAC_ADI = "cizim_oku"
ARAC_ACIKLAMA = "Bayinin plan çiziminden okuduklarını kaydet. Yalnız bu araçla cevap ver."
DUZELTME_ARACI = "okuma_duzelt"
DUZELTME_ACIKLAMA = "Bayinin düzeltmesini ya da revizyon isteğini önceki okumaya işle. Yalnız bu araçla cevap ver."
KENARLAR = ("ust", "alt", "sol", "sag")
ISLEVLER = ("salon", "mutfak", "yatak_odasi", "banyo", "wc", "hol", "antre", "depo", "calisma", "giyinme")
GORSEL_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")
PDF_MIME = "application/pdf"
EN_BUYUK_BAYT = 20 * 1024 * 1024        # Messages API'nin istek sınırının altında (base64 büyütür)
# Kod denetiminin eşikleri (ayarla değişebilir; `denetle(ayar=…)`)
ESIK = {"zincir_cm": 3.0,               # zincir toplamı ile yazılı toplam / dış ölçü farkı: bu kadarına not, üstüne soru
        "alan_m2": 0.6, "alan_oran": 0.12,   # yazılı m² ile okunan dikdörtgenlerin alanı: ikisinden büyüğü kadar fark olağan (duvar payı)
        "ortu_m2": 1.0,                 # odaların örtmediği gövde alanı
        "cakisma_m2": 0.3,              # iki odanın üst üste bindiği alan
        "pano_cm": 10.0}                # prefabrik: oda sınırı en yakın pano aksına bu kadar uzaksa oturtulur, ötesi sorulur
# Pano Motor'unun ölçüleri (motor/geometry.py; buraya kopya: beyin Motor'u içe aktarmadan çevirir, test eşitliği denetler)
MOD = 125.5
T_DIS = 10.0
PANO_YUKSEKLIKLERI = (250, 280, 300)
KAPI_CM = {"dis": 90, "ic": 82}         # TK-01 teklif çalışmasının çalışma kabulü (dış 90, iç 82)
PENCERE_VARSAYILAN = {"banyo": "60x40", "wc": "60x40"}     # ölçüsü yazmayan pencere; başka odalarda 120x120 (bayiye yazılır)
TUR = {"salon": "salon", "mutfak": "mutfak", "yatak_odasi": "yatak_odasi", "banyo": "banyo", "wc": "wc", "hol": "antre_hol",
       "antre": "antre_hol", "depo": "depo", "calisma": "calisma", "giyinme": "giyinme"}
CELIK_ISLEV = {"salon": "salon", "mutfak": "mutfak", "yatak_odasi": "yatak_odasi", "banyo": "banyo", "wc": "banyo", "hol": "hol",
               "antre": "hol", "depo": "depo", "calisma": "yatak_odasi", "giyinme": "yatak_odasi"}
CEPHE_ADI = {"on": "önde", "arka": "arkada", "sol": "solda", "sag": "sağda"}
VERANDA_ADI = {"on": "ÖN", "arka": "ARKA", "sol": "SOL", "sag": "SAĞ"}

PROMPT = """Sen PortatifEv'in bayi taleplerini okuyan yardımcısın. Bayi WhatsApp'tan bir ev planı çizimi (el çizimi, plan resmi ya da PDF)
gönderdi. Karar vermezsin, plan çizmezsin: çizimde gördüğünü cizim_oku aracıyla kaydedersin. Kod okuduğunu denetler ve bayiye "doğru mu?"
diye sorar.

Kurallar:
- `tur`: resim bir kat planı çizimiyse "plan"; bitmiş bir evin fotoğrafıysa "fotograf"; ikisi de değilse "diger" (öyleyse öteki alanları
  boş bırak).
- Koordinat çerçevesi: köken, gövdenin (verandalar hariç kapalı kısım) ÇİZİMDEKİ sol üst dış köşesi; x sağa, y aşağı; birim cm. Çizimi
  döndürme: çizimde nasıl duruyorsa öyle oku. Girişin (ön cephenin) çizimin hangi kenarında olduğunu `giris_kenari`na yaz.
- `dis_olcu`: gövdenin yazılı toplam ölçüleri (veranda hariç). `zincirler`: her kenardaki ölçü zinciri, yazıldığı gibi (sayıları
  değiştirme, yuvarlama); zincir verandayı da kapsıyorsa `kapsam: veranda_dahil`; aynı kenarda yazılı toplam varsa `toplam_cm`.
- `odalar`: her kapalı bölüm bir oda; adı çizimde yazdığı gibi (büyük harf). Aynı adlı odaları numaralandır (YATAK ODASI 1, 2, 3; önce
  yukarıdan aşağı, sonra soldan sağa). Adı yazmayan küçük bölüm (ör. giriş kapısıyla hol arası) ayrı odadır, işlevine uygun ad ver
  (ANTRE). `alan_m2` yalnız çizimde yazıyorsa. `dikdortgenler` oda sınırları (duvar ekseni); sınırları zincirlerin noktalarından al
  (zincir parçalarının birikimli toplamı); L biçimli oda birden çok dikdörtgen. Ölçüsü yazmayan bir sınırı oranla tahmin ettiysen
  `tahminler`e kısa yaz (ör. "banyo derinliği 256 cm").
- `kapilar`: iki oda arasındaki her kapı (`arasinda` iki oda adı); giriş kapısı `["DIŞ", "<oda>"]` ve `kenar`. `pencereler`: oda, çizimin
  hangi kenarında, yazılıysa ölçü ("ENxBOY", cm; ör. 120x180).
- `verandalar`: gövdenin dışındaki açık veranda: gövdenin hangi kenarında, kenar boyunca nerede başlayıp bittiği (üst/alt kenarda gövdenin
  sol dış yüzünden, sol/sağ kenarda üst dış yüzünden, cm) ve derinliği.
- `cati`: görünüş varsa çatı tipi; giriş cephesinin görünüşünde üçgen alın görünüyorsa mahya girişten arkaya ("giristen_arkaya"),
  görünmüyorsa "girise_paralel". `duvar_yuksekligi_cm` görünüşte yazıyorsa.
- `yapi_turu` (prefabrik / çelik) ve `kat_sayisi` yalnız çizimde ya da bayinin mesajında yazıyorsa.
- Okuyamadığın ve tahmin de edemediğin her şeyi `emin_olunamayanlar`a kısa, bayiye sorulabilecek biçimde yaz. Uydurma."""

DUZELTME_PROMPT = PROMPT + """

Şimdi önceki okuman ve bayinin yeni mesajı var. Mesaj bir düzeltme ya da (plan çizildiyse) değişiklik isteğiyse `niyet: duzeltme`,
okumanın tamamını yeniden yaz: yalnız bayinin söylediğini değiştir, öteki her şeyi aynen bırak; değiştirdiklerini `degisenler`e bayinin
anlayacağı kısa cümlelerle yaz. Bayi çizimden vazgeçiyorsa `niyet: iptal`; mesaj bu çizimle ilgisiz başka bir talepse `niyet: baska_talep`
(ikisinde `okuma` boş). Bayiye daha önce sorulanlara verdiği cevabı ("olur", "evet", "öyle çiz") sorulan değerle işle."""


# ───────────────────────── kalıp ─────────────────────────
class DisOlcuOkuma(BaseModel):
    yatay_cm: Optional[float] = Field(None, description="Gövdenin çizimdeki yatay toplam ölçüsü, cm (veranda hariç)")
    dusey_cm: Optional[float] = Field(None, description="Gövdenin çizimdeki düşey toplam ölçüsü, cm (veranda hariç)")


class Zincir(BaseModel):
    kenar: Literal["ust", "alt", "sol", "sag"]
    olculer_cm: list[float] = Field(..., min_length=1, description="Zincirin parçaları, yazıldığı sırayla (üst/alt: soldan, sol/sağ: yukarıdan)")
    toplam_cm: Optional[float] = Field(None, description="Aynı kenarda yazılı toplam ölçü (varsa)")
    kapsam: Literal["govde", "veranda_dahil"] = "govde"


class Oda(BaseModel):
    ad: str
    islev: Literal["salon", "mutfak", "yatak_odasi", "banyo", "wc", "hol", "antre", "depo", "calisma", "giyinme"]
    alan_m2: Optional[float] = Field(None, description="Çizimde yazan m²; yazmıyorsa boş")
    dikdortgenler: list[list[float]] = Field(..., min_length=1, description="[[x0, y0, x1, y1], …] cm, çizim çerçevesinde (köken gövdenin "
                                                                            "sol üst dış köşesi, x sağa, y aşağı)")


class KapiOkuma(BaseModel):
    arasinda: list[str] = Field(..., min_length=2, max_length=2, description="İki oda adı; giriş kapısı için ['DIŞ', '<oda>']")
    kenar: Optional[Literal["ust", "alt", "sol", "sag"]] = Field(None, description="Yalnız dış kapı: çizimin hangi kenarında")


class PencereOkuma(BaseModel):
    oda: str
    kenar: Literal["ust", "alt", "sol", "sag"]
    olcu: Optional[str] = Field(None, description="Yazılıysa 'ENxBOY' cm (ör. 120x180)")
    adet: int = Field(1, ge=1, le=4)


class VerandaOkuma(BaseModel):
    kenar: Literal["ust", "alt", "sol", "sag"]
    bas_cm: float = Field(..., description="Kenar boyunca başlangıç (üst/alt: gövdenin sol dış yüzünden; sol/sağ: üst dış yüzünden)")
    bit_cm: float
    derinlik_cm: float = Field(..., description="Gövdenin dış yüzünden dışarı")
    alan_m2: Optional[float] = None


class CatiOkuma(BaseModel):
    tip: Optional[Literal["besik", "kirma", "tek_egimli", "teras"]] = None
    mahya: Optional[Literal["giristen_arkaya", "girise_paralel"]] = None


class CizimOkumasi(BaseModel):
    tur: Literal["plan", "fotograf", "diger"]
    yapi_turu: Optional[Literal["prefabrik", "celik"]] = None
    kat_sayisi: Optional[int] = None
    giris_kenari: Optional[Literal["ust", "alt", "sol", "sag"]] = None
    dis_olcu: DisOlcuOkuma = Field(default_factory=DisOlcuOkuma)
    zincirler: list[Zincir] = Field(default_factory=list)
    odalar: list[Oda] = Field(default_factory=list)
    kapilar: list[KapiOkuma] = Field(default_factory=list)
    pencereler: list[PencereOkuma] = Field(default_factory=list)
    verandalar: list[VerandaOkuma] = Field(default_factory=list)
    cati: CatiOkuma = Field(default_factory=CatiOkuma)
    duvar_yuksekligi_cm: Optional[float] = None
    tahminler: list[str] = Field(default_factory=list, description="Ölçüsü yazmayıp oranla tahmin edilen değerler, kısa")
    emin_olunamayanlar: list[str] = Field(default_factory=list, description="Okunamayan ve tahmin edilemeyen noktalar; bayiye sorulur")
    ozet: str = Field("", description="Tek cümlelik Türkçe özet")


class Duzeltme(BaseModel):
    niyet: Literal["duzeltme", "iptal", "baska_talep"]
    okuma: Optional[CizimOkumasi] = None
    degisenler: list[str] = Field(default_factory=list, description="Bayinin isteğiyle değişenler, kısa")


# ───────────────────────── LLM (yalnız okur) ─────────────────────────
def dosya_blogu(yol: Path, mime: str) -> dict:
    """Messages API içerik bloğu: resim ya da PDF (base64)."""
    veri = base64.standard_b64encode(Path(yol).read_bytes()).decode("ascii")
    if mime == PDF_MIME:
        return {"type": "document", "source": {"type": "base64", "media_type": PDF_MIME, "data": veri}}
    return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": veri}}


def okunabilir_mi(mime: str | None, boyut: int | None) -> str | None:
    """Okunamayacak dosyanın nedeni (bayiye); okunabiliyorsa None."""
    if mime not in GORSEL_MIME and mime != PDF_MIME:
        return "Bu dosya türünü okuyamıyorum; planı resim (JPEG, PNG) ya da PDF olarak gönderebilirsiniz."
    if boyut and boyut > EN_BUYUK_BAYT:
        return "Dosya okuyabileceğimden büyük; planın sayfasını resim olarak ya da daha küçük bir PDF olarak gönderebilirsiniz."
    return None


def _ayar(ayar: dict | None, hazir) -> dict:
    a = {"backend": "anthropic", "model": "claude-opus-5-5", "effort": "medium", "timeout_s": 180, "max_tokens": 8000, **(ayar or {})}
    if hazir is not None:
        a["backend"] = "manuel"
    return a


def oku(yol: Path, mime: str, metin: str = "", ayar: dict | None = None, hazir: dict | None = None) -> dict:
    """Bir çağrı. Dönüş: {durum: tamam|hata, okuma, cagri, girdi_token, cikti_token, sure_ms, model, hata}. İstisna fırlatmaz.
    `hazir` (kayıtlı okuma) verilirse LLM çağrılmaz (manuel arka uç)."""
    a = _ayar(ayar, hazir)
    soz = numara.maskele((metin or "").strip())             # KVKK: LLM'e numara tam maskeli
    try:
        icerik = [] if a["backend"] == "manuel" else [dosya_blogu(yol, mime)]
        icerik.append({"type": "text", "text": "Bayinin mesajı: " + (soz or "(yazı yok, yalnız dosya)")})
        cevap, meta = llm.arac_cagir(PROMPT, [{"role": "user", "content": icerik}], ARAC_ADI, ARAC_ACIKLAMA, CizimOkumasi.model_json_schema(),
                                     backend=a["backend"], model=a.get("model"), effort=a.get("effort"), max_tokens=int(a["max_tokens"]),
                                     hazir=hazir, timeout=int(a["timeout_s"]))
        o = CizimOkumasi.model_validate(cevap)
    except Exception as e:
        return {"durum": "hata", "okuma": None, "cagri": 0 if a["backend"] == "manuel" else 1,
                "hata": f"{type(e).__name__}: {numara.maskele(str(e))[:240]}"}
    return {"durum": "tamam", "okuma": o.model_dump(mode="json"), "cagri": 0 if a["backend"] == "manuel" else 1,
            "girdi_token": meta.get("girdi_token") or 0, "cikti_token": meta.get("cikti_token") or 0, "sure_ms": meta.get("sure_ms"),
            "model": meta.get("model")}


def duzelt(okuma: dict, metin: str, sorulanlar: list[str] | None = None, yol: Path | None = None, mime: str | None = None,
           ayar: dict | None = None, hazir: dict | None = None, revizyon: bool = False) -> dict:
    """Bir çağrı: önceki okuma + bayinin mesajı (düzeltme ya da çizilmiş planın revizyonu) → {durum, niyet, okuma, degisenler, …}.
    Dosya hâlâ duruyorsa modele yeniden gösterilir (bayinin sözünü çizimle karşılaştırabilsin). İstisna fırlatmaz."""
    a = _ayar(ayar, hazir)
    soz = numara.maskele((metin or "").strip())
    try:
        icerik = []
        if a["backend"] != "manuel" and yol and mime and Path(yol).is_file():
            icerik.append(dosya_blogu(Path(yol), mime))
        bas = "Plan bu okumayla çizildi ve bayiye gönderildi; bayi değişiklik istiyor." if revizyon else "Bayiye okuduklarını gösterdin."
        sor = ("\n\n## Bayiye sorulanlar\n" + "\n".join(f"- {s}" for s in sorulanlar)) if sorulanlar else ""
        icerik.append({"type": "text", "text": f"{bas}\n\n## Önceki okuman\n{json.dumps(okuma, ensure_ascii=False)}{sor}\n\n## Bayinin mesajı\n{soz}"})
        cevap, meta = llm.arac_cagir(DUZELTME_PROMPT, [{"role": "user", "content": icerik}], DUZELTME_ARACI, DUZELTME_ACIKLAMA,
                                     Duzeltme.model_json_schema(), backend=a["backend"], model=a.get("model"), effort=a.get("effort"),
                                     max_tokens=int(a["max_tokens"]), hazir=hazir, timeout=int(a["timeout_s"]))
        d = Duzeltme.model_validate(cevap)
        if d.niyet == "duzeltme" and d.okuma is None:
            raise ValueError("düzeltmede okuma boş")
    except Exception as e:
        return {"durum": "hata", "niyet": None, "okuma": None, "degisenler": [], "cagri": 0 if a["backend"] == "manuel" else 1,
                "hata": f"{type(e).__name__}: {numara.maskele(str(e))[:240]}"}
    return {"durum": "tamam", "niyet": d.niyet, "okuma": d.okuma.model_dump(mode="json") if d.okuma else None,
            "degisenler": [numara.maskele(str(x))[:120] for x in d.degisenler], "cagri": 0 if a["backend"] == "manuel" else 1,
            "girdi_token": meta.get("girdi_token") or 0, "cikti_token": meta.get("cikti_token") or 0, "model": meta.get("model")}


# ───────────────────────── çerçeve ─────────────────────────
KENAR_CEPHE = {"alt": {"ust": "arka", "alt": "on", "sol": "sol", "sag": "sag"},
               "ust": {"ust": "on", "alt": "arka", "sol": "sag", "sag": "sol"},
               "sol": {"sol": "on", "sag": "arka", "ust": "sol", "alt": "sag"},
               "sag": {"sag": "on", "sol": "arka", "alt": "sol", "ust": "sag"}}


def _nokta(x: float, y: float, W: float, H: float, giris: str) -> tuple[float, float]:
    """Çizim çerçevesi (W × H) → kanonik (giriş altta): x sol dış yüzden, y arka dış yüzden."""
    if giris == "alt":
        return x, y
    if giris == "ust":
        return W - x, H - y
    if giris == "sol":
        return y, W - x
    return H - y, x


def _dortgen(r: list[float], W: float, H: float, giris: str) -> list[float]:
    x0, y0 = _nokta(r[0], r[1], W, H, giris)
    x1, y1 = _nokta(r[2], r[3], W, H, giris)
    return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]


def _bas_buyuk(s: str) -> str:
    return tr_buyuk(s[:1]) + s[1:]


def tr_buyuk(s: str) -> str:
    return " ".join(str(s).replace("i", "İ").replace("ı", "I").upper().split())


def _govde_olcusu(o: CizimOkumasi) -> tuple[float | None, float | None, str | None]:
    """Gövdenin çizimdeki (yatay, düşey) ölçüsü: yazılı toplam; yoksa gövde zincirinin toplamı; yoksa odaların kapsadığı. Üçüncü değer:
    yazılı değilse nereden alındığı (bayiye yazılır)."""
    W, H = o.dis_olcu.yatay_cm, o.dis_olcu.dusey_cm
    nereden = None
    if not W or not H:
        zin = {z.kenar: sum(z.olculer_cm) for z in o.zincirler if z.kapsam == "govde"}
        W = W or zin.get("ust") or zin.get("alt")
        H = H or zin.get("sol") or zin.get("sag")
        nereden = "ölçü zincirlerinden"
    if (not W or not H) and o.odalar:
        W = W or max(r[2] for x in o.odalar for r in x.dikdortgenler)
        H = H or max(r[3] for x in o.odalar for r in x.dikdortgenler)
        nereden = "odaların ölçülerinden"
    return (float(W) if W else None), (float(H) if H else None), nereden


def kanonik(okuma: dict | CizimOkumasi) -> dict:
    """Okuma → kanonik çerçeve (giriş altta; Pano Motor'unun arka-sol çerçevesi): {W, H, giris, odalar[{ad, islev, alan_m2, rects}],
    pencereler[{oda, cephe, olcu, adet}], kapilar[{arasinda, dis, cephe}], verandalar[{cephe, bas, bit, derinlik, alan_m2, rect}], notlar}.
    Veranda `bas`/`bit` BK-14'ün gerçek çerçevesinde (ön/arka: x sol dış yüzden; sol/sağ: y ön dış yüzden)."""
    o = okuma if isinstance(okuma, CizimOkumasi) else CizimOkumasi.model_validate(okuma)
    notlar = []
    giris = o.giris_kenari
    if giris is None:
        dk = next((k.kenar for k in o.kapilar if _dis_mi(k) and k.kenar), None)
        giris = dk or "alt"
        notlar.append("giriş cephesi " + ("giriş kapısından" if dk else "yazmadığı için çizimin alt kenarı") + " alındı")
    Wc, Hc, nereden = _govde_olcusu(o)
    if nereden:
        notlar.append(f"dış ölçü yazmıyordu, {nereden} alındı")
    if not Wc or not Hc:
        return {"W": None, "H": None, "giris": giris, "odalar": [], "pencereler": [], "kapilar": [], "verandalar": [], "notlar": notlar}
    W, H = (Wc, Hc) if giris in ("alt", "ust") else (Hc, Wc)
    cephe = KENAR_CEPHE[giris]
    odalar = [{"ad": x.ad, "islev": x.islev, "alan_m2": x.alan_m2, "rects": [_dortgen(r, Wc, Hc, giris) for r in x.dikdortgenler]}
              for x in o.odalar]
    ver = []
    for v in o.verandalar:
        d = v.derinlik_cm
        r = {"ust": [v.bas_cm, -d, v.bit_cm, 0], "alt": [v.bas_cm, Hc, v.bit_cm, Hc + d],
             "sol": [-d, v.bas_cm, 0, v.bit_cm], "sag": [Wc, v.bas_cm, Wc + d, v.bit_cm]}[v.kenar]
        x0, y0, x1, y1 = _dortgen(r, Wc, Hc, giris)
        c = cephe[v.kenar]
        bas, bit = (x0, x1) if c in ("on", "arka") else (H - y1, H - y0)
        ver.append({"cephe": c, "bas": bas, "bit": bit, "derinlik": d, "alan_m2": v.alan_m2, "rect": [x0, y0, x1, y1]})
    return {"W": W, "H": H, "giris": giris, "odalar": odalar,
            "pencereler": [{"oda": p.oda, "cephe": cephe[p.kenar], "olcu": p.olcu, "adet": p.adet} for p in o.pencereler],
            "kapilar": [{"arasinda": list(k.arasinda), "dis": _dis_mi(k), "cephe": cephe[k.kenar] if k.kenar else None} for k in o.kapilar],
            "verandalar": ver, "notlar": notlar}


def _dis_mi(k: KapiOkuma) -> bool:
    return any(_norm(a) in ("dis", "disari", "giris") for a in k.arasinda)


def _norm(s: str) -> str:
    q = str(s or "").translate(str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc")).lower()
    return re.sub(r"[^a-z0-9]+", " ", q).strip()


def _alan(rects: list[list[float]]) -> float:
    from shapely.geometry import box
    from shapely.ops import unary_union
    return unary_union([box(*r) for r in rects if r[2] > r[0] and r[3] > r[1]]).area / 1e4 if rects else 0.0


def _m(cm: float) -> str:
    """cm → "8,98" (metre, iki hane)."""
    return f"{cm / 100:.2f}".replace(".", ",")


def _tr(v: float, n: int = 2) -> str:
    s = f"{v:.{n}f}".rstrip("0").rstrip(".") if n else f"{v:.0f}"
    return s.replace(".", ",")


# ───────────────────────── denetim (kod karar verir) ─────────────────────────
def denetle(okuma: dict, ayar: dict | None = None, veranda_destegi: bool | None = None) -> dict:
    """Okumanın kod denetimi ve plana çevirisi. Dönüş: {plan_mi, yapi_turu, sorular[], cizilemez[], notlar[], tahminler[], odalar[],
    kanonik, cevrim}. `sorular` bayiye sorulur (teyit yok); `cizilemez` Motor'un bugün çizemediği (bayiye söylenir, Patron'a gider);
    `notlar` bayiye yazılan ama soru olmayanlar (küçük zincir farkı, ızgaraya oturtma, varsayılanlar). `cevrim`: prefabrikte
    {"is_emri": şablon}, çelikte {"plan": PlanTaslagi sözlüğü}; soru ya da çizilemezlik varsa None."""
    e = {**ESIK, **(ayar or {})}
    o = CizimOkumasi.model_validate(okuma)
    sonuc = {"plan_mi": o.tur == "plan", "yapi_turu": o.yapi_turu or "prefabrik", "sorular": [], "cizilemez": [], "notlar": [],
             "tahminler": [numara.maskele(str(t))[:120] for t in o.tahminler], "odalar": [], "kanonik": None, "cevrim": None}
    if o.tur != "plan":
        return sonuc
    sor, notlar = sonuc["sorular"], sonuc["notlar"]
    if o.yapi_turu is None:
        notlar.append("yapı tipi yazmıyordu, prefabrik aldım")
    if (o.kat_sayisi or 1) > 1:
        sonuc["cizilemez"].append(f"{o.kat_sayisi} katlı plan (bugün yalnız tek katı otomatik çizebiliyorum)")
    for s in o.emin_olunamayanlar:
        sor.append(numara.maskele(str(s))[:160])
    if not o.odalar:
        sor.append("Odaları ve ölçülerini çizimden okuyamadım.")
        return sonuc
    kan = kanonik(o)
    sonuc["kanonik"] = kan
    notlar.extend(kan["notlar"])
    if not kan["W"]:
        sor.append("Gövdenin dış ölçüsünü okuyamadım; kaça kaç metre?")
        return sonuc
    Wc, Hc, _ = _govde_olcusu(o)
    # 1) ölçü zincirleri: parçaların toplamı yazılı toplamla ve gövde zinciriyse dış ölçüyle
    farklar = []
    for z in o.zincirler:
        top = sum(z.olculer_cm)
        hedefler = [("yazılı toplam", z.toplam_cm)] if z.toplam_cm else []
        if z.kapsam == "govde":
            hedefler.append(("dış ölçü", Wc if z.kenar in ("ust", "alt") else Hc))
        for ad, h in hedefler:
            fark = abs(top - float(h))
            parca = " + ".join(_tr(x, 1) for x in z.olculer_cm)
            if fark > e["zincir_cm"] + 1e-9:
                sor.append(f"{_kenar_adi(z.kenar)} ölçü zinciri {parca} = {_tr(top, 1)} cm, {ad} {_tr(float(h), 1)} cm; hangisi doğru?")
            elif fark > 0.01:
                farklar.append(f"{KENAR_YERI[z.kenar]} {_tr(fark, 1)} cm")
    if farklar:
        notlar.append("ölçü zincirleri toplamla küçük farkla tutuyor (" + ", ".join(dict.fromkeys(farklar)) + ")")
    sonuc["zincir_tutuyor"] = not any("ölçü zinciri" in s for s in sor)
    # 2) odalar: gövdenin içinde mi, yazılı m² ile okunan ölçü, örtme ve çakışma
    from shapely.geometry import box
    from shapely.ops import unary_union
    govde = box(0, 0, kan["W"], kan["H"])
    adlar = [x["ad"] for x in kan["odalar"]]
    for ad in sorted({a for a in adlar if adlar.count(a) > 1}):
        sor.append(f"Çizimde birden çok \"{ad}\" var; hangisinin hangisi olduğunu ayırt edemedim.")
    poligon = {}
    for x in kan["odalar"]:
        rects = [r for r in x["rects"] if r[2] - r[0] > 1 and r[3] - r[1] > 1]
        if not rects:
            sor.append(f"{_oda_adi(x['ad'])} için ölçü okuyamadım.")
            continue
        p = unary_union([box(*r) for r in rects])
        poligon[x["ad"]] = p
        okunan = p.area / 1e4
        sonuc["odalar"].append({"ad": x["ad"], "islev": x["islev"], "yazili_m2": x["alan_m2"], "okunan_m2": round(okunan, 2)})
        if p.difference(govde).area / 1e4 > e["cakisma_m2"]:
            sor.append(f"{_oda_adi(x['ad'])} gövdenin dışına taşıyor; ölçüsünü yazar mısınız?")
        if x["alan_m2"]:
            fark = abs(okunan - float(x["alan_m2"]))
            if fark > max(e["alan_m2"], e["alan_oran"] * float(x["alan_m2"])):
                sor.append(f"{_oda_adi(x['ad'])} için {_tr(float(x['alan_m2']))} m² yazıyor, okuduğum ölçüler {_tr(okunan)} m² veriyor; "
                           "doğru ölçüsü nedir?")
    adlar_l = list(poligon)
    for i, a in enumerate(adlar_l):
        for b in adlar_l[i + 1:]:
            if poligon[a].intersection(poligon[b]).area / 1e4 > e["cakisma_m2"]:
                sor.append(f"{_oda_adi(a)} ile {_oda_adi(b)} çizimde üst üste biniyor gibi okudum; sınırları nerede?")
    if poligon:
        bos = govde.difference(unary_union(list(poligon.values()))).area / 1e4
        if bos > e["ortu_m2"]:
            sor.append(f"Gövdenin yaklaşık {_tr(bos, 1)} m²'lik kısmı hiçbir odaya ait görünmüyor; orası neresi?")
    # 3) kapı ve pencere odaları; giriş kapısı
    bilinen = {_norm(a) for a in adlar}
    for p in kan["pencereler"]:
        if _norm(p["oda"]) not in bilinen:
            sor.append(f"\"{p['oda']}\" penceresinin hangi odaya ait olduğunu bulamadım.")
    for k in kan["kapilar"]:
        for a in k["arasinda"]:
            if _norm(a) not in bilinen and _norm(a) not in ("dis", "disari", "giris"):
                sor.append(f"\"{a}\" kapısının hangi odaya açıldığını bulamadım.")
    if not any(k["dis"] for k in kan["kapilar"]):
        sor.append("Giriş kapısını çizimde göremedim; hangi odadan giriliyor?")
    if sor or sonuc["cizilemez"]:
        return sonuc
    if sonuc["yapi_turu"] == "celik":
        plan, cz, nt = plan_celik(kan, o)
        sonuc["cizilemez"].extend(cz); notlar.extend(nt)
        if not cz:
            from beyin import plan_denetim
            d = plan_denetim.denetle(plan, {}, kod="CIZIM")          # İE-14 denetçisi: oda kuralları, geometri, açıklıklar, çatı
            if d.get("gecerli"):
                sonuc["cevrim"] = {"plan": plan, "tanim": d["tanim"], "ozet": d.get("ozet")}
            else:
                sonuc["cizilemez"].extend(f"çelik plan kuralı: {x}" for x in (d.get("ihlaller") or [])[:3])
        return sonuc
    ie, sr, cz, nt = is_emri_prefabrik(kan, o, veranda_destegi=veranda_destegi, tol=e["pano_cm"])
    sor.extend(sr); sonuc["cizilemez"].extend(cz); notlar.extend(nt)
    if not sr and not cz:
        sonuc["cevrim"] = {"is_emri": ie}
    return sonuc


KENAR_YERI = {"ust": "üstte", "alt": "altta", "sol": "solda", "sag": "sağda"}


def _kenar_adi(k: str) -> str:
    return {"ust": "Üstteki", "alt": "Alttaki", "sol": "Soldaki", "sag": "Sağdaki"}[k]


def _oda_adi(ad: str) -> str:
    return " ".join(w[:1] + w[1:].replace("I", "ı").replace("İ", "i").lower() for w in str(ad).split())


# ───────────────────────── prefabrik: okuma → İş Emri ─────────────────────────
def veranda_destegi_var() -> bool:
    """Pano Motor'u gövdeden taşan verandayı çizebiliyor mu (BK-14, PR #50)? Birleşmeden verandalı plan çizilmez (sapmalı plan yok)."""
    try:
        from motor import geometry as G
        return hasattr(G, "_dis_verandalar")
    except Exception:
        return False


def pano_akslari(uzunluk: float, bas: float) -> tuple[float, list[float]]:
    """Dış ölçü (cm) → (pano sayısı, yarım adım aksları). Son aks dış ölçüye kesilir (motor/geometry.olcu_ayarla): x'te bas = 10 (köşe),
    y'de 5. Son pano 62,75'ten büyük ve 125,5'ten küçük ya da eşit."""
    son = uzunluk - bas
    n = math.ceil(2 * (son - bas) / MOD - 1e-9) / 2
    return n, [bas + MOD / 2 * k for k in range(int(round(2 * n)))] + [son]


def is_emri_prefabrik(kan: dict, o: CizimOkumasi, veranda_destegi: bool | None = None, tol: float = ESIK["pano_cm"]
                      ) -> tuple[dict | None, list[str], list[str], list[str]]:
    """Kanonik okuma → Pano Motor'u İş Emri şablonu (numarasız; `karar._is_emri_uret` numara ve künyeyi yazar). Teklif çalışmasının
    kuralları (TK-01 r04): dış ölçüye kesilmiş ızgara, oda sınırları yarım pano akslarına (en çok `tol` cm kayma; bayiye yazılır),
    dizilim arka-sol, ızgaraya hizalı, oda ortası pencere, kapı mantığı; dış kapı 90, iç kapı 82; çatı kural kitabından (eğim %33, saçak 30,
    topuk 10). Dönüş: (şablon | None, sorular, çizilemezler, notlar)."""
    sor, cz, nt = [], [], []
    W, H = float(kan["W"]), float(kan["H"])
    nx, xs = pano_akslari(W, T_DIS)
    ny, ys = pano_akslari(H, T_DIS / 2)
    if nx < 2 or ny < 2:
        return None, [], [f"gövde {_m(W)} × {_m(H)} m pano ızgarası için çok küçük"], []
    kaymalar = []

    def yasla(v: float, eksen: list[float], uz: float, ad: str) -> float | None:
        if v <= T_DIS + tol:
            return eksen[0]
        if v >= uz - T_DIS - tol:
            return eksen[-1]
        a = min(eksen[1:-1], key=lambda t: abs(t - v)) if len(eksen) > 2 else None
        if a is None or abs(a - v) > tol + 1e-9:
            sor.append(f"{_oda_adi(ad)} sınırı ({_tr(v, 1)} cm) pano ızgarasına oturmuyor; en yakın pano aksı {_tr(a, 2)} cm. "
                       "Öyle çizebilir miyim?")
            return None
        if abs(a - v) > 2:
            kaymalar.append(abs(a - v))
        return a
    mahaller = []
    sirali = sorted(kan["odalar"], key=lambda x: (min(r[1] for r in x["rects"]), min(r[0] for r in x["rects"])))
    sira = {x["ad"]: i for i, x in enumerate(sirali)}
    for x in kan["odalar"]:
        rects = []
        for r in x["rects"]:
            q = [yasla(r[0], xs, W, x["ad"]), yasla(r[1], ys, H, x["ad"]), yasla(r[2], xs, W, x["ad"]), yasla(r[3], ys, H, x["ad"])]
            if None in q:
                continue
            if q[2] - q[0] < 1 or q[3] - q[1] < 1:
                sor.append(f"{_oda_adi(x['ad'])} pano ızgarasına oturtunca kayboluyor (yarım panodan dar); ölçüsünü yazar mısınız?")
                continue
            rects.append(q)
        mahaller.append({"ad": tr_buyuk(x["ad"]), "tur": TUR[x["islev"]], "konum_cm": rects, "_sira": sira[x["ad"]]})
    if sor:
        return None, sor, cz, nt
    if kaymalar:
        nt.append(f"oda sınırlarını pano ızgarasına oturttum (en çok {_tr(max(kaymalar), 1)} cm kayma)")
    # ızgaranın her yarım hücresi tek odaya (Motor da denetler; burada bayiye anlaşılır soru)
    sahip: dict[tuple[int, int], str] = {}
    for m in mahaller:
        for q in m["konum_cm"]:
            for u in range(xs.index(q[0]), xs.index(q[2])):
                for w in range(ys.index(q[1]), ys.index(q[3])):
                    if (u, w) in sahip and sahip[(u, w)] != m["ad"]:
                        sor.append(f"Pano ızgarasına oturtunca {_oda_adi(sahip[(u, w)])} ile {_oda_adi(m['ad'])} çakışıyor; aradaki duvar nerede?")
                        return None, list(dict.fromkeys(sor)), cz, nt
                    sahip[(u, w)] = m["ad"]
    if len(sahip) != (len(xs) - 1) * (len(ys) - 1):
        sor.append("Pano ızgarasına oturtunca gövdede hiçbir odaya ait olmayan bir bölüm kalıyor; orası neresi?")
        return None, sor, cz, nt
    for m in mahaller:
        m.pop("_sira")
    ad_haritasi = {_norm(x["ad"]): tr_buyuk(x["ad"]) for x in kan["odalar"]}
    kenar_degeri = {"sol": ("x", xs[0]), "sag": ("x", xs[-1]), "arka": ("y", ys[0]), "on": ("y", ys[-1])}

    def disa_bakar(ad: str, cephe: str) -> bool:
        yon, deger = kenar_degeri[cephe]
        for m in mahaller:
            if m["ad"] == ad:
                return any((q[0] if cephe == "sol" else q[2] if cephe == "sag" else q[1] if cephe == "arka" else q[3]) == deger for q in m["konum_cm"])
        return False
    acik = []
    varsayilan = []
    for p in kan["pencereler"]:
        ad = ad_haritasi.get(_norm(p["oda"]))
        if not disa_bakar(ad, p["cephe"]):
            sor.append(f"{_oda_adi(ad)} penceresini {CEPHE_ADI[p['cephe']]} okudum ama oda o cepheye değmiyor; pencere hangi duvarda?")
            continue
        olcu = (p.get("olcu") or "").lower().replace(" ", "").replace("*", "x").replace("×", "x") or None
        if olcu is None:
            olcu = PENCERE_VARSAYILAN.get(_islev(kan, ad), "120x120")
            varsayilan.append(f"{_oda_adi(ad)} {olcu}")
        elif not pencere_gecerli(olcu):
            sor.append(f"{_oda_adi(ad)} penceresinin ölçüsünü ({p.get('olcu')}) okuyamadım; eni ve boyu kaç cm?")
            continue
        for _ in range(int(p.get("adet") or 1)):
            acik.append({"tur": "pencere", "olcu": olcu, "mahal": ad, "duvar": p["cephe"]})
    if varsayilan:
        nt.append("ölçüsü yazmayan pencereler: " + ", ".join(varsayilan))
    kapilar = sorted(kan["kapilar"], key=lambda k: not k["dis"])
    for k in kapilar:
        if k["dis"]:
            ic = next(ad_haritasi[_norm(a)] for a in k["arasinda"] if _norm(a) in ad_haritasi)
            cephe = k["cephe"] or next((c for c in ("on", "sol", "sag", "arka") if disa_bakar(ic, c)), None)
            if cephe is None or not disa_bakar(ic, cephe):
                sor.append(f"Giriş kapısını {_oda_adi(ic)} için okudum ama oda dış duvara değmiyor; giriş hangi odadan?")
                continue
            acik.append({"tur": "dis_kapi", "olcu": KAPI_CM["dis"], "arasi": ["__DIS__", ic], "duvar": cephe})
        else:
            a, b = (ad_haritasi[_norm(x)] for x in k["arasinda"])
            if not _komsu(mahaller, a, b):
                sor.append(f"{_oda_adi(a)} ile {_oda_adi(b)} arasında kapı okudum ama iki oda yan yana değil; kapı nerede?")
                continue
            acik.append({"tur": "ic_kapi", "olcu": KAPI_CM["ic"], "arasi": [a, b]})
    if sor:
        return None, list(dict.fromkeys(sor)), cz, nt
    # duvar yüksekliği ve çatı
    hy = o.duvar_yuksekligi_cm
    if hy is None:
        hy = 250
        nt.append("duvar yüksekliği yazmıyordu, 2,50 m aldım")
    elif int(round(hy)) not in PANO_YUKSEKLIKLERI:
        sor.append(f"Duvar yüksekliğini {_m(hy)} m okudum; prefabrikte 2,50 / 2,80 / 3,00 m var, hangisi olsun?")
        return None, sor, cz, nt
    tip = o.cati.tip or "besik"
    if o.cati.tip is None:
        nt.append("çatı tipi görünmüyordu, beşik aldım")
    if tip != "besik":
        cz.append({"kirma": "kırma çatı", "tek_egimli": "tek eğimli çatı", "teras": "teras çatı"}[tip] + " (prefabrikte bugün beşik çiziyorum)")
    kural = _cati_kurali()
    if o.cati.mahya:
        makas = "x" if o.cati.mahya == "giristen_arkaya" else "y"
    else:
        makas = "x" if W <= H + 50 else "y"
    verandalar = []
    for i, v in enumerate(kan["verandalar"]):
        ad = f"{VERANDA_ADI[v['cephe']]} VERANDA"
        verandalar.append({"ad": ad, "cephe": v["cephe"], "bas_cm": _yuvarla(v["bas"]), "bit_cm": _yuvarla(v["bit"]),
                           "derinlik_cm": _yuvarla(v["derinlik"]), "cati": {"tip": "besik", "egim_yuzde": kural["egim_yuzde"]}})
    if len({v["ad"] for v in verandalar}) != len(verandalar):
        for i, v in enumerate(verandalar, 1):
            v["ad"] = f"{v['ad']} {i}"
    if verandalar and veranda_destegi is None:
        veranda_destegi = veranda_destegi_var()
    if verandalar and not veranda_destegi:
        cz.append("gövdenin dışına taşan veranda")
    if cz:
        return None, sor, cz, nt
    ie = {
        "is_emri_no": "", "revizyon": 0,
        "talep": {},
        "yapi": {"sistem": "prefabrik", "kat_sayisi": 1, "duvar_yuksekligi_cm": int(round(hy)), "duvar_kalinligi_cm": {"dis": 10, "ic": 6},
                 "olcu_kaynagi": "dis_olcu", "dis_olcu_cm": {"x": _yuvarla(W), "y": _yuvarla(H)}, "referans_model": "CIZIM",
                 "grid": {"x_pano": _yuvarla(nx), "y_pano": _yuvarla(ny)}, "kisa_kenar": "x", "giris_cephesi": "on", "dis_dusey_duvar": "cevre_aks_disinda",
                 "dizilim": {"baslangic": "arka-sol", "hiza": "izgara", "dis_duvar_t_bolme": True, "pencere": "oda_ortasi", "kapi": "mantik",
                             "kose": "oda"},
                 "ek_akslar_cm": {"x": [], "y": []}},
        "mahaller": mahaller,
        "acik_sinirlar": [],
        "acikliklar": acik,
        "cati": {"tip": "besik", "egim_yuzde": kural["egim_yuzde"], "sacak_cm": kural["sacak_cm"], "topuk_cm": 10, "makas_yonu": "kisa_kenar",
                 "makas_ekseni": makas},
        "cikti": {"pdf": True, "dxf": True, "pafta": "A2",
                  "icerik": ["aksli_plan", "alanli_kopya", "montaj_kopyasi", "on_gorunus", "cati_profili", "ozellik_tablosu"]},
        "ozellikler": {"Çatı Şekli": "Beşik"},
        "alici_ait": {"kalemler": [], "kaynak": "bayi çizimi"},
        "varsayimlar": [f"Ölçüler bayi çiziminden okundu ve bayi teyit etti: gövde {_tr(W, 1)} × {_tr(H, 1)} cm, {nx:g} × {ny:g} pano."]
                       + [_bas_buyuk(n) + "." for n in nt],
        "eksikler": [],
        "dikmeler": [],
    }
    if verandalar:
        ie["verandalar"] = verandalar
    return ie, sor, cz, nt


def pencere_gecerli(olcu: str) -> bool:
    """Pencere ölçüsü Pano Motor'unun tek kuralına uyuyor mu (`motor/geometry.pencere_kurali`: "ENxBOY", en 30–247, boy 20–180)?"""
    from motor.geometry import IsEmriHatasi, pencere_kurali
    try:
        pencere_kurali(olcu)
        return True
    except IsEmriHatasi:
        return False


def _yuvarla(v: float):
    return int(v) if abs(v - round(v)) < 1e-9 and float(v).is_integer() else round(float(v), 2)


def _islev(kan: dict, ad: str) -> str:
    return next((x["islev"] for x in kan["odalar"] if tr_buyuk(x["ad"]) == ad), "")


def _komsu(mahaller: list[dict], a: str, b: str) -> bool:
    """İki mahal en az bir kapı genişliği kadar ortak sınırı paylaşıyor mu (yarım pano akslarında)?"""
    from shapely.geometry import box
    from shapely.ops import unary_union
    pa = unary_union([box(*q) for m in mahaller if m["ad"] == a for q in m["konum_cm"]])
    pb = unary_union([box(*q) for m in mahaller if m["ad"] == b for q in m["konum_cm"]])
    return pa.boundary.intersection(pb.boundary).length >= KAPI_CM["ic"] - 1e-6


def _cati_kurali() -> dict:
    """Kural kitabının çatı varsayılanı (kurallar/plan/oda_kurallari.json › cati: eğim %33, saçak 30; TK-01 r04)."""
    yol = Path(__file__).resolve().parent.parent / "kurallar" / "plan" / "oda_kurallari.json"
    c = json.loads(yol.read_text(encoding="utf-8")).get("cati") or {}
    return {"egim_yuzde": c.get("egim_yuzde", 33), "sacak_cm": c.get("sacak_cm", 30)}


# ───────────────────────── çelik: okuma → plan şeması (İE-14) ─────────────────────────
def plan_celik(kan: dict, o: CizimOkumasi) -> tuple[dict | None, list[str], list[str]]:
    """Kanonik okuma → İE-14 plan şeması (köken güneybatı dış köşe, +y kuzey = arka, 5 cm ızgara). Veranda şerit olarak mahal olur
    (denetçi kuralına uymazsa çizilemez). Dönüş: (plan, çizilemezler, notlar). Plan denetimi (`plan_denetim.denetle`) `denetle`de."""
    nt, cz = [], []
    W, H = kan["W"], kan["H"]
    vy = list(kan["verandalar"])
    xmin = min([0.0] + [v["rect"][0] for v in vy]); xmax = max([W] + [v["rect"][2] for v in vy])
    ymin = min([0.0] + [v["rect"][1] for v in vy]); ymax = max([H] + [v["rect"][3] for v in vy])
    kayma = []

    def izg(v: float) -> int:
        r = int(round(v / 5) * 5)
        if abs(r - v) > 0.5:
            kayma.append(abs(r - v))
        return r

    def donustur(r: list[float]) -> list[int]:
        """kanonik (x soldan, y arkadan öne) → plan (köken güneybatı dış köşe; ön güney, +y kuzey = arka)"""
        return [izg(r[0] - xmin), izg(ymax - r[3]), izg(r[2] - xmin), izg(ymax - r[1])]
    en, boy = izg(xmax - xmin), izg(ymax - ymin)
    mahaller = [{"ad": _oda_adi(x["ad"]), "islev": CELIK_ISLEV[x["islev"]], "dikdortgenler": [donustur(r) for r in x["rects"]]}
                for x in kan["odalar"]]
    for i, v in enumerate(vy, 1):
        mahaller.append({"ad": "Veranda" if len(vy) == 1 else f"Veranda {i}", "islev": "veranda", "dikdortgenler": [donustur(v["rect"])],
                         "ortu": "cati"})
    if kayma:
        nt.append(f"ölçüleri 5 cm ızgaraya oturttum (en çok {_tr(max(kayma), 1)} cm)")
    cephe_harf = {"on": "G", "arka": "K", "sol": "B", "sag": "D"}
    ad_haritasi = {_norm(x["ad"]): _oda_adi(x["ad"]) for x in kan["odalar"]}
    from beyin.plan_sema import PENCERE_OLCULERI
    pencereler = []
    for p in kan["pencereler"]:
        olcu = (p.get("olcu") or "").lower().replace(" ", "").replace("×", "x") or None
        if olcu not in PENCERE_OLCULERI:
            yeni = "60x40" if _islev(kan, tr_buyuk(p["oda"])) in ("banyo", "wc") else "120x120"
            nt.append(f"{ad_haritasi[_norm(p['oda'])]} penceresi {yeni}" + (f" ({p.get('olcu')} çelik ölçülerinde yok)" if olcu else ""))
            olcu = yeni
        pencereler.append({"mahal": ad_haritasi[_norm(p["oda"])], "cephe": cephe_harf[p["cephe"]], "olcu": olcu, "adet": int(p.get("adet") or 1)})
    kapilar = []
    for k in kan["kapilar"]:
        if k["dis"]:
            ic = next(ad_haritasi[_norm(a)] for a in k["arasinda"] if _norm(a) in ad_haritasi)
            kapilar.append({"arasinda": ["dis", ic], **({"cephe": cephe_harf[k["cephe"]]} if k["cephe"] else {})})
        else:
            kapilar.append({"arasinda": [ad_haritasi[_norm(a)] for a in k["arasinda"]]})
    tip = o.cati.tip or "besik"
    if tip not in ("besik", "kirma"):
        cz.append({"tek_egimli": "tek eğimli çatı", "teras": "teras çatı"}[tip])
    mahya = None
    if o.cati.mahya:
        mahya = "y" if o.cati.mahya == "giristen_arkaya" else "x"
    plan = {"dis_olcu": {"en": en, "boy": boy}, "mahaller": mahaller, "kapilar": kapilar, "pencereler": pencereler,
            "cati": {"tip": tip if tip in ("besik", "kirma") else "besik", **({"mahya_yonu": mahya} if mahya and tip == "besik" else {})},
            "gerekce": "bayi çiziminden okundu (İE-20)"}
    return plan, cz, nt


# ───────────────────────── bayiye ─────────────────────────
ISLEV_ADI = {"salon": "salon", "mutfak": "mutfak", "yatak_odasi": "yatak odası", "banyo": "banyo", "wc": "WC", "hol": "hol",
             "antre": "antre", "depo": "depo", "calisma": "çalışma odası", "giyinme": "giyinme odası"}


def ozet_satirlari(okuma: dict, den: dict) -> list[str]:
    """Okunanın bayiye kısa özeti (madde madde)."""
    o = CizimOkumasi.model_validate(okuma)
    kan = den.get("kanonik") or kanonik(o)
    s = []
    yapi = "çelik" if den.get("yapi_turu") == "celik" else "prefabrik"
    kat = "tek katlı" if (o.kat_sayisi or 1) == 1 else f"{o.kat_sayisi} katlı"
    parca = [f"{kat} {yapi}"]
    if kan.get("W"):
        parca.append(f"gövde {_m(kan['W'])} × {_m(kan['H'])} m")
    if o.duvar_yuksekligi_cm:
        parca.append(f"duvar {_m(o.duvar_yuksekligi_cm)} m")
    if o.cati.tip:
        parca.append({"besik": "beşik", "kirma": "kırma", "tek_egimli": "tek eğimli", "teras": "teras"}[o.cati.tip] + " çatı")
    s.append(_bas_buyuk(", ".join(parca) + "."))
    gruplar: dict[str, list] = {}
    for x in den.get("odalar") or []:
        gruplar.setdefault(x["islev"], []).append(x)
    oda = []
    for islev in ("salon", "mutfak", "yatak_odasi", "banyo", "wc", "hol", "antre", "calisma", "giyinme", "depo"):
        g = gruplar.get(islev) or []
        if not g:
            continue
        m2 = [_tr(float(x["yazili_m2"]), 1) if x.get("yazili_m2") else None for x in g]
        if islev in ("banyo", "wc") and len(g) > 1:
            oda.extend(f"{_oda_adi(x['ad']).lower()}" + (f" {m} m²" if m else "") for x, m in zip(g, m2))
        elif len(g) > 1:
            yazili = [m for m in m2 if m]
            oda.append(f"{len(g)} {ISLEV_ADI[islev]}" + (f" ({' / '.join(yazili)} m²)" if yazili else ""))
        else:
            oda.append(ISLEV_ADI[islev] + (f" {m2[0]} m²" if m2[0] else ""))
    if oda:
        s.append("Odalar: " + ", ".join(oda) + ".")
    if kan.get("verandalar"):
        s.append("Veranda: " + ", ".join(f"{CEPHE_ADI[v['cephe']]} {_m(v['bit'] - v['bas'])} × {_m(v['derinlik'])} m"
                                         for v in kan["verandalar"]) + ".")
    pencere = sum(int(p.get("adet") or 1) for p in kan.get("pencereler") or [])
    giris = next((k for k in kan.get("kapilar") or [] if k["dis"]), None)
    kp = [f"{pencere} pencere"] if pencere else []
    if giris and giris.get("cephe"):
        kp.append(f"giriş kapısı {CEPHE_ADI[giris['cephe']]}")
    if kp:
        s.append(_bas_buyuk(", ".join(kp) + "."))
    if den.get("zincir_tutuyor") and not any("küçük farkla" in n for n in den.get("notlar") or []) and o.zincirler:
        s.append("Ölçü zincirleri toplamla tutuyor.")
    for n in den.get("notlar") or []:
        s.append(_bas_buyuk(n) + ".")
    if den.get("tahminler"):
        s.append("Ölçüsü yazmayanları oranla aldım: " + "; ".join(den["tahminler"][:4]) + ".")
    return s


def teyit_metni(okuma: dict, den: dict, gorsel_var: bool = True, on: str = "") -> str:
    """[Doğru] [Düzelt] mesajının gövdesi (≤ 1000; WhatsApp gövde ve altyazı sınırı 1024). `on`: başa ek ("Düzelttim: …")."""
    son = ("\n\nOkuduğum yerleşim görselde. " if gorsel_var else "\n\n") + "Doğru mu? Düzeltme varsa yazmanız yeterli."
    return _sigdir(on + "Çiziminizden şunları okudum:\n", ozet_satirlari(okuma, den), son)


def soru_metni(okuma: dict, den: dict, gorsel_var: bool = True, on: str = "") -> str:
    """Emin olunamayanlar varken (teyit yok): okunan + sorular (≤ 1000)."""
    sorular = list(dict.fromkeys(den.get("sorular") or []))
    son = "\n\nŞunlardan emin olamadım:\n" + "\n".join(f"{i}. {q}" for i, q in enumerate(sorular[:5], 1)) + \
          ("\n\nOkuduğum yerleşim görselde." if gorsel_var else "") + "\nDoğrusunu yazar mısınız?"
    return _sigdir(on + "Çiziminizden şunları okudum:\n", ozet_satirlari(okuma, den), son)


def cizilemez_metni(okuma: dict, den: dict, on: str = "", ek: str = "") -> str:
    """Motor'un bugün çizemediği okuma: okunan + neden (≤ 1000). `ek`: sona (yönlendirme cümlesi)."""
    neden = "; ".join(str(x) for x in den.get("cizilemez") or [])
    son = f"\n\nBu planı şu an otomatik çizemiyorum: {neden}." + ek
    return _sigdir(on + "Çiziminizden şunları okudum:\n", ozet_satirlari(okuma, den), son)


def _sigdir(bas: str, satirlar: list[str], son: str, sinir: int = 1000) -> str:
    """Özet satırları sığmazsa sondan atılır; baş ve son (soru, teyit cümlesi) her zaman kalır."""
    govde = [f"• {x}" for x in satirlar]
    while govde and len(bas + "\n".join(govde) + son) > sinir:
        govde.pop()
    metin = bas + "\n".join(govde) + son
    if len(metin) > sinir:                      # baş ve son tek başına sığmıyor: baş kısalır, son (soru, teyit) kalır
        metin = (bas[:max(0, sinir - len(son) - 1)] + "…" + son)[-sinir:]
    return metin


def degisenler(eski: dict, yeni: dict) -> list[str]:
    """İki okumanın bayinin anlayacağı farkı (kodun kıyası; LLM'in `degisenler`i yanında): oda alanı ve ölçüsü, eklenen ve çıkan oda,
    pencere, kapı, veranda, dış ölçü, ölçü zinciri, giriş cephesi, yapı tipi, duvar yüksekliği, çatı; başka fark yoksa cevaplanan soru."""
    a, b = CizimOkumasi.model_validate(eski), CizimOkumasi.model_validate(yeni)
    out = []
    if (a.dis_olcu.yatay_cm, a.dis_olcu.dusey_cm) != (b.dis_olcu.yatay_cm, b.dis_olcu.dusey_cm):
        out.append(f"dış ölçü {_olcu(a)} → {_olcu(b)}")
    for alan, ad in (("yapi_turu", "yapı tipi"), ("kat_sayisi", "kat"), ("duvar_yuksekligi_cm", "duvar yüksekliği")):
        if getattr(a, alan) != getattr(b, alan):
            out.append(f"{ad} {getattr(a, alan) or '—'} → {getattr(b, alan) or '—'}")
    if a.cati != b.cati:
        out.append("çatı değişti")
    oa, ob = {_norm(x.ad): x for x in a.odalar}, {_norm(x.ad): x for x in b.odalar}
    for k in oa.keys() - ob.keys():
        out.append(f"{_oda_adi(oa[k].ad)} çıkarıldı")
    for k in ob.keys() - oa.keys():
        out.append(f"{_oda_adi(ob[k].ad)} eklendi")
    for k in oa.keys() & ob.keys():
        x, y = oa[k], ob[k]
        if x.dikdortgenler != y.dikdortgenler:
            out.append(f"{_oda_adi(y.ad)} ölçüsü değişti ({_tr(_alan(x.dikdortgenler))} → {_tr(_alan(y.dikdortgenler))} m²)")
        elif x.alan_m2 != y.alan_m2:
            out.append(f"{_oda_adi(y.ad)} {_tr(x.alan_m2 or 0)} → {_tr(y.alan_m2 or 0)} m²")
    pa = sorted((_norm(p.oda), p.kenar, p.olcu or "", p.adet) for p in a.pencereler)
    pb = sorted((_norm(p.oda), p.kenar, p.olcu or "", p.adet) for p in b.pencereler)
    if pa != pb:
        out.append("pencereler değişti")
    ka = sorted(tuple(sorted(_norm(x) for x in k.arasinda)) for k in a.kapilar)
    kb = sorted(tuple(sorted(_norm(x) for x in k.arasinda)) for k in b.kapilar)
    if ka != kb:
        out.append("kapılar değişti")
    if [v.model_dump() for v in a.verandalar] != [v.model_dump() for v in b.verandalar]:
        out.append("veranda değişti")
    za = {z.kenar: z for z in a.zincirler}
    for z in b.zincirler:
        x = za.get(z.kenar)
        if x is None or (x.olculer_cm, x.toplam_cm) != (z.olculer_cm, z.toplam_cm):
            out.append(f"{KENAR_YERI[z.kenar]} ölçü zinciri " + " + ".join(_tr(v, 1) for v in z.olculer_cm))
    if a.giris_kenari != b.giris_kenari:
        out.append("giriş cephesi değişti")
    cevaplanan = [x for x in a.emin_olunamayanlar if x not in b.emin_olunamayanlar]
    if cevaplanan and not out:
        out.append("sorduğum " + ("nokta" if len(cevaplanan) == 1 else f"{len(cevaplanan)} nokta") + " cevabınızla kapandı")
    return out


def _olcu(o: CizimOkumasi) -> str:
    x, y = o.dis_olcu.yatay_cm, o.dis_olcu.dusey_cm
    return f"{_tr((x or 0) / 100)} × {_tr((y or 0) / 100)} m" if x and y else "—"


# ───────────────────────── okunan yerleşimin görseli ─────────────────────────
def yerlesim_gorseli(okuma: dict, den: dict, hedef: Path) -> Path:
    """Okunan yerleşim (kanonik çerçeve, giriş altta): gövde, odalar (ad ve yazılı m²), verandalar (kesikli), pencereler (mavi) ve giriş
    kapısı (ok); üstte dış ölçü. Plan değil, "doğru okudum mu?" görseli: oda sınırları okunduğu gibidir (ızgaraya oturtulmamış)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    kan = den.get("kanonik") or kanonik(okuma)
    W, H = float(kan["W"]), float(kan["H"])
    yaz = {x["ad"]: x for x in den.get("odalar") or []}
    xs = [0, W] + [v["rect"][0] for v in kan["verandalar"]] + [v["rect"][2] for v in kan["verandalar"]]
    ys = [0, H] + [v["rect"][1] for v in kan["verandalar"]] + [v["rect"][3] for v in kan["verandalar"]]
    x0, x1, y0, y1 = min(xs) - 80, max(xs) + 80, min(ys) - 110, max(ys) + 80
    oran = (x1 - x0) / (y1 - y0)
    fig = plt.figure(figsize=(8, 8 / oran) if oran >= 1 else (8 * oran, 8), dpi=130)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal"); ax.axis("off")
    renk = {"salon": "#f4efe1", "mutfak": "#eaf2e3", "yatak_odasi": "#e6eef7", "banyo": "#e3f1f3", "wc": "#e3f1f3", "hol": "#f2f2f2",
            "antre": "#f2f2f2"}
    from shapely.geometry import box
    from shapely.ops import unary_union
    from matplotlib.patches import Polygon as Cokgen
    for v in kan["verandalar"]:
        r = v["rect"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ls="--", lw=1.2, ec="#9a3b2e"))
        dx, dy = {"on": (0, 1), "arka": (0, -1), "sol": (-1, 0), "sag": (1, 0)}[v["cephe"]]
        mx = (r[0] + r[2]) / 2 if dx == 0 else (r[2] - 30 if dx > 0 else r[0] + 30)
        my = (r[1] + r[3]) / 2 if dy == 0 else (r[3] - 30 if dy > 0 else r[1] + 30)
        ax.text(mx, my, f"VERANDA {_m(v['bit'] - v['bas'])} × {_m(v['derinlik'])} m", ha="center", va="center", fontsize=7, color="#9a3b2e",
                rotation=0 if dx == 0 else 90)
    for x in kan["odalar"]:
        g = unary_union([box(*r) for r in x["rects"] if r[2] > r[0] and r[3] > r[1]])
        for parca in getattr(g, "geoms", [g]):
            ax.add_patch(Cokgen(list(parca.exterior.coords), closed=True, fc=renk.get(x["islev"], "#f7f7f7"), ec="#555", lw=1.0))
        b = max(x["rects"], key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        m2 = (yaz.get(x["ad"]) or {}).get("yazili_m2")
        boy = min(8.5, max(5.0, (b[2] - b[0]) / 40))
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, _sar(x["ad"], b[2] - b[0], boy) + (f"\n{_tr(float(m2), 1)} m²" if m2 else ""),
                ha="center", va="center", fontsize=boy)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="#222", lw=2.4))
    for p in kan["pencereler"]:
        oda = next((x for x in kan["odalar"] if _norm(x["ad"]) == _norm(p["oda"])), None)
        if not oda:
            continue
        r = _cephe_parcasi(oda["rects"], p["cephe"], W, H)
        if r:
            (a0, b0), (a1, b1) = r
            ax.plot([a0, a1], [b0, b1], color="#1f6fb2", lw=4, solid_capstyle="butt")
    giris = next((k for k in kan["kapilar"] if k["dis"] and k.get("cephe")), None)
    if giris:
        oda = next((x for x in kan["odalar"] if any(_norm(x["ad"]) == _norm(a) for a in giris["arasinda"])), None)
        r = _cephe_parcasi(oda["rects"], giris["cephe"], W, H) if oda else None
        if r:
            (a0, b0), (a1, b1) = r
            mx, my = (a0 + a1) / 2, (b0 + b1) / 2
            dx, dy = {"on": (0, 1), "arka": (0, -1), "sol": (-1, 0), "sag": (1, 0)}[giris["cephe"]]
            ax.annotate("GİRİŞ", xy=(mx, my), xytext=(mx + dx * 45, my + dy * 45), ha="center", va="center", fontsize=7,
                        arrowprops={"arrowstyle": "->", "lw": 1.2})
    ax.text(W / 2, min(ys) - 40, f"{_tr(W / 100)} m", ha="center", va="bottom", fontsize=8)
    ax.text(max(xs) + 40, H / 2, f"{_tr(H / 100)} m", ha="left", va="center", fontsize=8, rotation=90)
    ax.text(x0 + 10, y1 - 10, "Okuduğum yerleşim (ön cephe altta) · plan değildir", ha="left", va="bottom", fontsize=6.5, color="#666")
    hedef = Path(hedef)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(hedef, dpi=130, facecolor="white", metadata={"Software": None})
    plt.close(fig)
    return hedef


def _sar(ad: str, en_cm: float, boy: float) -> str:
    """Oda adı dar odada iki satıra bölünür (yazı odadan taşmasın)."""
    sigan = max(4, int(en_cm / (boy * 2.2)))
    if len(ad) <= sigan or " " not in ad:
        return ad
    p = ad.split(" ")
    return " ".join(p[:len(p) // 2]) + "\n" + " ".join(p[len(p) // 2:])


def _cephe_parcasi(rects: list[list[float]], cephe: str, W: float, H: float):
    """Odanın verilen dış cepheye değen kenar parçasının ortadaki 1,2 m'si (görselde pencere ya da kapı yeri); değmiyorsa None."""
    for r in rects:
        if cephe == "on" and abs(r[3] - H) < 15:
            m = (r[0] + r[2]) / 2; return (m - 60, H), (m + 60, H)
        if cephe == "arka" and r[1] < 15:
            m = (r[0] + r[2]) / 2; return (m - 60, 0), (m + 60, 0)
        if cephe == "sol" and r[0] < 15:
            m = (r[1] + r[3]) / 2; return (0, m - 60), (0, m + 60)
        if cephe == "sag" and abs(r[2] - W) < 15:
            m = (r[1] + r[3]) / 2; return (W, m - 60), (W, m + 60)
    return None
