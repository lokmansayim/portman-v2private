"""Beyin v0.1 — talep şeması.

`Talep`: LLM'in bir bayi mesajından çıkardığı yapılandırılmış veri (yorum yok, geometri yok, hesap yok).
`Karar`: kural katmanının verdiği sonuç (soru / İş Emri / yönlendirme / cevap).
Şema JSON Schema olarak dışa aktarılır; hangi model kullanılırsa kullanılsın aynı sözleşme geçerlidir.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DisOlcu(BaseModel):
    en_m: Optional[float] = Field(None, description="Kısa kenar, metre (örn. 4.0)")
    boy_m: Optional[float] = Field(None, description="Uzun kenar, metre (örn. 7.0)")


class PanoGrid(BaseModel):
    nx: Optional[float] = Field(None, description="Kısa kenar pano adedi (yarım pano 0.5 adımı serbest)")
    ny: Optional[float] = Field(None, description="Uzun kenar pano adedi")


class Veranda(BaseModel):
    istiyor: Optional[bool] = Field(None, description="Veranda istiyor mu; belirtilmediyse null")
    konum: Optional[Literal["on", "yan", "arka", "kose"]] = None
    alan_m2: Optional[float] = None


class Cati(BaseModel):
    tip: Optional[Literal["besik", "kirma", "tek_egimli", "teras"]] = None
    egim_yuzde: Optional[float] = None
    kaplama: Optional[str] = Field(None, description="örn. trapez sac, metal kiremit, shingle")
    renk: Optional[str] = None


class Pencere(BaseModel):
    mahal: Optional[str] = Field(None, description="Pencerenin ait olduğu oda (mesajda geçtiği gibi)")
    olcu: Optional[Literal["120x120", "120x180", "60x40", "120x100", "120x160", "160x120", "160x180", "180x180", "80x120", "120x50"]] = None
    adet: Optional[int] = None
    duvar: Optional[Literal["on", "arka", "sol", "sag"]] = None
    islem: Optional[Literal["ekle", "kaldir", "degistir"]] = Field(None, description="Var olan bir modelde değişiklikse")


class Varyant(BaseModel):
    tur: Literal[
        "ayna_x", "ayna_y", "pencere_degistir", "pencere_ekle", "pencere_kaldir",
        "kapi_degistir", "veranda_ekle", "veranda_kaldir", "veranda_degistir",
        "olcu_degistir", "oda_ekle", "oda_kaldir", "cati_degistir", "yukseklik_degistir", "diger",
    ]
    aciklama: str = Field(..., description="Bayinin kendi sözleriyle istenen değişiklik")
    parametreler: dict = Field(default_factory=dict)


class Musteri(BaseModel):
    ad: Optional[str] = None
    telefon: Optional[str] = None
    sevk_adresi: Optional[str] = None


class Talep(BaseModel):
    """Bir bayi mesajının yapılandırılmış hali. Mesajda OLMAYAN hiçbir alan doldurulmaz (null kalır)."""
    niyet: Literal["yeni_talep", "revizyon", "onay", "red", "soru", "selam", "diger"] = Field(
        ..., description="yeni_talep: yeni plan/teklif istiyor; revizyon: önceki plana değişiklik; onay: planı onaylıyor; "
                         "red: beğenmedi/iptal; soru: fiyat/süre/genel soru; selam: sadece selam; diger: alakasız")
    katalog_kodu: Optional[str] = Field(None, description="P6001, Ç8201 gibi katalog kodu; sadece mesajda geçiyorsa. "
                                                          "'6001' gibi eksik yazımı P6001'e tamamla, ancak emin değilsen belirsizliklere yaz")
    yapi_turu: Optional[Literal["prefabrik", "celik"]] = Field(None, description="Sadece açıkça söylendiyse")
    kat_sayisi: Optional[int] = None
    oda_programi: Optional[str] = Field(None, description="'2+1', '3+1', '1+1', 'tek oda' → '1+0'")
    alan_m2: Optional[float] = None
    dis_olcu: Optional[DisOlcu] = None
    pano: Optional[PanoGrid] = None
    veranda: Optional[Veranda] = None
    cati: Optional[Cati] = None
    yukseklik_cm: Optional[int] = None
    pencereler: list[Pencere] = Field(default_factory=list)
    dis_kapi: Optional[str] = Field(None, description="çelik / pvc / alüminyum / sac; sadece söylendiyse")
    ic_kapi: Optional[str] = Field(None, description="amerikan / pvc; sadece söylendiyse")
    varyantlar: list[Varyant] = Field(default_factory=list, description="Var olan bir katalog modeline istenen değişiklikler")
    bina_ozellikleri: dict[str, str] = Field(default_factory=dict, description="Dış boya rengi, iç kapı rengi gibi pafta tablosu alanları; anahtar Türkçe, sadece söylenenler")
    ozel_istekler: list[str] = Field(default_factory=list, description="'çatıya OSB + nem bariyeri' gibi serbest istekler, bayinin sözleriyle")
    musteri: Optional[Musteri] = None
    belirsizlikler: list[str] = Field(default_factory=list, description="Çelişkili veya emin olunamayan noktalar, Türkçe kısa cümle")
    guven: Literal["dusuk", "orta", "yuksek"]
    ozet: str = Field(..., description="Anlaşılanın tek cümlelik Türkçe özeti; bayiye geri okunacak")


class Karar(BaseModel):
    eylem: Literal["sor", "is_emri", "yonlendir", "cevapla", "yoksay"]
    mesaj: str = Field("", description="Bayiye gidecek WhatsApp metni")
    soru_alani: Optional[str] = None
    is_emri: Optional[dict] = None
    revizyon: int = 0
    gerekce: str = ""


def json_schema() -> dict:
    return Talep.model_json_schema()


if __name__ == "__main__":
    import json
    print(json.dumps(json_schema(), ensure_ascii=False, indent=1))
