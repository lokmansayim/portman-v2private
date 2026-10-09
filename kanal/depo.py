"""İE-02 · Postgres deposu: mesaj, iş, konuşma, soru, proje, revizyon ve giden kayıtları.

Kurallar (docs/is_emirleri/IE-02.md):
  - Mesaj ve iş aynı ifadede yazılır; WhatsApp kimliği benzersiz (tekrar/eşzamanlı mesaj ikinci iş doğurmaz).
  - İş kiralanarak alınır; bir göndericinin en eski bitmemiş işi, o göndericinin başka işi işlenmiyorsa alınır.
  - Konuşma, soru kaydı, revizyon, giden satırlar ve işin bitişi tek işlemde yazılır; konuşma okunduğu sürümle yazılır.
  - Kirası dolan iş en çok EN_COK_DENEME kez yeniden alınır (D-03); sonra başarısız sayılır, bayiye ve Patron'a bildirim yazılır.
  - Giden satır 'gonderiliyor' iken süreç düşerse ya da sonuç belirsizse 'belirsiz' olur; otomatik yeniden gönderilmez.
Bu modül WhatsApp'a ya da LLM'e bağlanmaz. Sır tutmaz: bağlantı adresi PORTMAN_PG_DSN ortam değişkeninden gelir.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

GOC_DIR = Path(__file__).resolve().parent / "goc"
KIRA_SN = 600                 # worker.STALE_S ile aynı: bu süre ilerlemeyen iş sahipsiz sayılır
EN_COK_DENEME = 3             # D-03: kirası dolan iş en çok bu kadar kez alınır
GONDERIM_ZAMAN_ASIMI_SN = 600 # 'gonderiliyor' bu süreden eskiyse 'belirsiz' (feature.php PM_KANAL_STALE ile aynı yaklaşım)
ESKI_TASLAK_SORUSU = "yeni_mi_degisiklik"   # beyin/karar.py ile aynı ad
ESKI_SORU_SN = 24 * 3600                    # beyin/karar.py ile aynı süre
HATA_BAYIYE = "Mesajınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak."


# Eksik bilgi sorusu → cevabın düşeceği taslak alanları (beyin/karar.py::_soru çağrıları)
SORU_ALANLARI = {"oda_programi": ("oda_programi",), "katalog_kodu": ("katalog_kodu",), "dis_olcu": ("dis_olcu", "alan_m2", "pano"),
                 "model_veya_olcu": ("katalog_kodu", "dis_olcu", "pano"), "pencere_olcu": ("pencereler",), "pencere_mahal": ("pencereler",),
                 "secenek": ("katalog_kodu",)}          # İE-04: seçenek setinden seçim (buton ya da metin) katalog_kodu'nu doldurur


def _cevap_mi(alan: str, d_eski: dict, d_yeni: dict, sonuc: dict, ozet: dict) -> bool:
    """Kapanan soru bu mesajla mı cevaplandı (değilse düştü)? D-01 ve B1 soruları kural katmanının notundan; eksik bilgi
    soruları, sorulan alanın bu mesajla dolup dolmadığından okunur. İptal cevap sayılmaz."""
    if alan == ESKI_TASLAK_SORUSU:
        return bool(ozet.get("d01_cevap"))
    if alan == "pencere_islem":
        return bool(ozet.get("pencere_cevap"))
    if alan == "oncelik":
        return bool(ozet.get("oncelik_cevap"))     # İE-04: cevap olmayan mesaj öncelik sorusunu düşürür ("yok"), cevap saymaz
    if sonuc.get("gerekce") == "iptal":
        return False
    te, ty = (d_eski or {}).get("taslak") or {}, (d_yeni or {}).get("taslak") or {}
    alanlar = SORU_ALANLARI.get(alan)
    if alanlar is None:                       # ör. revizyon_ne: taslak bu mesajla değiştiyse cevap
        return ty != te
    return any(ty.get(f) not in (None, [], {}, "") and ty.get(f) != te.get(f) for f in alanlar)


def soru_ayrintisi(d: dict, alan: str) -> tuple:
    """(bekletilen_talep, bekletilen_metin, pencere_satiri, deneme) — sorular tablosu için."""
    d01 = alan == ESKI_TASLAK_SORUSU
    return (Jsonb(d["bekleyen_talep"]) if d01 and d.get("bekleyen_talep") else None,
            d.get("bekleyen_metin") if d01 else None,
            Jsonb(d["pencere_islem_satiri"]) if alan == "pencere_islem" and d.get("pencere_islem_satiri") is not None else None,
            int(d.get("eski_taslak_soru") or 1) if d01 else 1)


def metin_satiri(gelen: dict, metin: str, sira: int, alici: str, tur: str) -> dict:
    """kanal/worker.py::giden_metin ile aynı biçim (testle denetlenir): depo, worker'ı yüklemeden hata satırı yazabilsin."""
    simdi = int(time.time())
    return {"id": satir_id(gelen["id"], sira), "kind": "text", "to": alici, "body": metin[:4000], "tur": tur, "inbound_id": gelen["id"],
            "seq": sira, "state": "pending", "wamid": None, "media_id": None, "attempts": 0, "error": None, "delivery_state": None,
            "created_at": simdi, "updated_at": simdi}


class Cakisma(Exception):
    """Konuşma okunduktan sonra başka bir yazma oldu; sonuç yazılmadı (iş yeniden sıraya girer)."""


class KiraKaybi(Exception):
    """İşin kirası dolmuş ve iş başka bir işleyiciye geçmiş; bu işleyicinin sonucu atılır."""


def satir_id(gelen_id: str, sira: int) -> str:
    """kanal/worker.py::satir_id ile aynı (testle denetlenir); depo worker'ı yüklemeden hata satırı yazabilsin diye burada da var."""
    return "out_" + hashlib.sha256(f"{gelen_id}|{sira}".encode()).hexdigest()[:24]


def kimlik_izi(mesaj_id: str | None) -> str:
    """WhatsApp mesaj kimliğinin (wamid) kısa özeti. wamid karşı tarafın numarasını base64 olarak içerdiği için kimlik
    günlüğe ve kanıt çıktısına yazılmaz; yerine bu yazılır (SQL karşılığı: left(md5(id), 10))."""
    return hashlib.md5(str(mesaj_id).encode()).hexdigest()[:10] if mesaj_id else "-"


def _nulsuz(x):
    """Postgres metin ve jsonb alanları NUL (U+0000) karakteri kabul etmez; PHP satırı olduğu gibi geçirir. Mesajın
    yazılamayıp kuyruğu tıkamaması için NUL karakterleri atılır (metnin geri kalanı aynı kalır)."""
    if isinstance(x, str):
        return x.replace("\x00", "")
    if isinstance(x, dict):
        return {_nulsuz(k): _nulsuz(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_nulsuz(v) for v in x]
    return x


def maske(numara: str) -> str:
    n = str(numara or "")
    return (n[:3] + "…" + n[-2:]) if len(n) > 6 else "…"


def _zaman(saniye) -> float:
    try:
        return float(saniye)
    except (TypeError, ValueError):
        return time.time()


class Depo:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.environ.get("PORTMAN_PG_DSN") or ""
        if not self.dsn:
            raise ValueError("PORTMAN_PG_DSN tanımlı değil")

    def baglan(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    # ───────────────────────── göç ─────────────────────────
    def goc_uygula(self) -> list[int]:
        """kanal/goc/NNN_*.sql dosyalarını sırayla, her birini tek işlemde uygular. Aynı anda iki çalıştırıcı olursa
        danışma kilidi birini bekletir. Uygulanan sürümler sema_surumu tablosunda."""
        uygulanan = []
        with self.baglan() as c:
            c.execute("SELECT pg_advisory_lock(7401001)")
            try:
                c.execute("CREATE TABLE IF NOT EXISTS sema_surumu (surum int PRIMARY KEY, ad text NOT NULL, "
                          "uygulandi timestamptz NOT NULL DEFAULT now())")
                c.commit()
                var = {r["surum"] for r in c.execute("SELECT surum FROM sema_surumu")}
                for p in sorted(GOC_DIR.glob("[0-9][0-9][0-9]_*.sql")):
                    n = int(p.name[:3])
                    if n in var:
                        continue
                    with c.transaction():
                        c.execute(p.read_text(encoding="utf-8"))
                        c.execute("INSERT INTO sema_surumu (surum, ad) VALUES (%s, %s)", (n, p.name))
                    uygulanan.append(n)
            finally:
                c.execute("SELECT pg_advisory_unlock(7401001)")
                c.commit()
        return uygulanan

    def eksik_goc(self) -> list[int]:
        """Pakette olup veritabanına uygulanmamış göçler (ajan bunlar varken çalışmaz; göç ayrı ve onaylı bir adımdır)."""
        paket = sorted(int(p.name[:3]) for p in GOC_DIR.glob("[0-9][0-9][0-9]_*.sql"))
        with self.baglan() as c:
            var = c.execute("SELECT to_regclass('sema_surumu') IS NOT NULL AS v").fetchone()["v"]
            uygulanan = {r["surum"] for r in c.execute("SELECT surum FROM sema_surumu")} if var else set()
        return [n for n in paket if n not in uygulanan]

    def olu_kiralari_birak(self, makine: str, ben: str) -> int:
        """Ajan yeniden başlarken: bu makinedeki başka (artık yaşamayan) süreçlerin kiraları hemen düşer, iş kira süresini
        beklemeden yeniden alınır (D-03). Makinede tek ajan süreci çalışır (systemd); başka makinenin kiralarına dokunulmaz."""
        with self.baglan() as c, c.transaction():
            return c.execute("UPDATE isler SET kira_bitis = now() WHERE durum = 'isleniyor' AND split_part(sahip, ':', 1) = %s "
                             "AND sahip <> %s", (makine, ben)).rowcount

    def saglik(self) -> None:
        """Postgres'e bağlanılabiliyor mu? Bağlanılamıyorsa hata yükselir (ajan o turda hosting'ten iş almaz)."""
        with self.baglan() as c:
            c.execute("SELECT 1")

    def acik_is_sayisi(self) -> int:
        with self.baglan() as c:
            return c.execute("SELECT count(*) AS n FROM isler WHERE durum IN ('sirada', 'isleniyor')").fetchone()["n"]

    def mesaj_durumu(self, mesaj_id: str) -> dict | None:
        """Bir gelen mesajın işi, hosting'e devredilmemiş giden satır sayısı ve hosting'e hiç verilemeden 'gonderilmedi'
        sayılmış satır sayısı (tekrar gelen kanal mesajı için)."""
        with self.baglan() as c:
            return c.execute("SELECT j.id AS is_id, j.durum AS is_durum, "
                             "(SELECT count(*) FROM giden g WHERE g.is_id = j.id AND g.durum = 'bekliyor') AS bekleyen_giden, "
                             "(SELECT count(*) FROM giden g WHERE g.is_id = j.id AND g.durum = 'gonderilmedi' "
                             " AND g.hostinge_verildi IS NULL) AS verilemeyen_giden "
                             "FROM isler j WHERE j.mesaj_id = %s", (mesaj_id,)).fetchone()

    # ───────────────────────── gelen ─────────────────────────
    def mesaj_kaydet(self, gelen: dict, kaynak: str = "vps") -> bool:
        """Kuyruk satırını (webhook'un ürettiği, feature.php biçimi) mesaj ve iş olarak yazar. Yeni ise True; aynı kimlik daha
        önce geldiyse hiçbir şey değişmez ve False döner. Satırdaki bayi bilgisi bayiler tablosundan türetilmiştir; burada
        yalnız kod/ad/rol tazelenir (kimlik kartının öteki alanlarına dokunulmaz)."""
        gelen = _nulsuz(gelen)
        mid = str(gelen.get("id") or "")
        if not mid or len(mid) > 300:
            raise ValueError("mesaj kimliği yok ya da çok uzun")
        bayi = gelen.get("bayi") or None
        with self.baglan() as c, c.transaction():
            if isinstance(bayi, dict):          # kimlik numaradır; kod yalnız etiket (benzersiz değil, bkz. goc/001)
                c.execute("INSERT INTO bayiler (numara, kod, ad, rol) VALUES (%s, %s, %s, %s) ON CONFLICT (numara) DO UPDATE "
                          "SET kod = EXCLUDED.kod, ad = EXCLUDED.ad, rol = EXCLUDED.rol, guncellendi = now()",
                          (str(gelen["sender"]), bayi.get("kod"), bayi.get("ad") or "",
                           "patron" if (gelen.get("role") or bayi.get("rol")) == "patron" else "bayi"))
            r = c.execute(
                "INSERT INTO mesajlar (id, gonderen, bayi_kod, tur, metin, alinti_id, wa_zamani, ham, kaynak, sahiplenildi) "
                "VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s), %s, %s, true) ON CONFLICT (id) DO NOTHING RETURNING id",
                (mid, str(gelen["sender"]), (bayi or {}).get("kod") if isinstance(bayi, dict) else None, gelen.get("type") or "text",
                 gelen.get("text") or "", gelen.get("context_id"), _zaman(gelen.get("timestamp")), Jsonb(gelen), kaynak)).fetchone()
            if r is None:
                return False
            c.execute("INSERT INTO isler (mesaj_id, gonderen) VALUES (%s, %s)", (mid, str(gelen["sender"])))
            return True

    def kayitsiz_mesaj_kaydet(self, gelen: dict, cevap_metni: str | None, sinir_sn: int = 86400, kaynak: str = "vps") -> dict:
        """İE-06: sahiplenilmeyen mesaj (kayıtsız gönderen ya da modun işlemediği kayıtlı gönderen). Mesaj panelde görünsün diye
        yazılır; iş açılmaz (isler satırı 'bitti', eylem 'kayitsiz'); varsa sabit cevap satırı yazılır, gönderen başına sinir_sn'de bir.
        Dönen: {"yeni": bool, "cevap": bool}."""
        gelen = _nulsuz(gelen)
        mid = str(gelen.get("id") or "")
        if not mid or len(mid) > 300:
            raise ValueError("mesaj kimliği yok ya da çok uzun")
        gonderen = str(gelen["sender"]); cevap = False
        with self.baglan() as c, c.transaction():
            r = c.execute(
                "INSERT INTO mesajlar (id, gonderen, bayi_kod, tur, metin, alinti_id, wa_zamani, ham, kaynak, sahiplenildi) "
                "VALUES (%s, %s, NULL, %s, %s, %s, to_timestamp(%s), %s, %s, false) ON CONFLICT (id) DO NOTHING RETURNING id",
                (mid, gonderen, gelen.get("type") or "text", gelen.get("text") or "", gelen.get("context_id"),
                 _zaman(gelen.get("timestamp")), Jsonb(gelen), kaynak)).fetchone()
            if r is None:
                return {"yeni": False, "cevap": False}
            sonuc = {"eylem": "kayitsiz", "gerekce": "sahiplenilmedi: " + str(gelen.get("neden") or "kayıtsız gönderen")}
            j = c.execute("INSERT INTO isler (mesaj_id, gonderen, durum, sonuc, basladi, bitti) VALUES (%s, %s, 'bitti', %s, now(), now()) RETURNING id",
                          (mid, gonderen, Jsonb(sonuc))).fetchone()
            if cevap_metni and str(cevap_metni).strip():
                son = c.execute("SELECT son FROM kayitsiz_cevaplar WHERE gonderen = %s FOR UPDATE", (gonderen,)).fetchone()
                yeni_cevap = son is None or c.execute("SELECT %s < now() - make_interval(secs => %s) AS g", (son["son"], sinir_sn)).fetchone()["g"]
                if yeni_cevap:
                    govde = str(cevap_metni)[:4000]
                    c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, satir) VALUES (%s, %s, %s, 1, %s, 'cevap', 'text', %s, %s) "
                              "ON CONFLICT (id) DO NOTHING", (satir_id(mid, 1), j["id"], mid, gonderen, govde, Jsonb(metin_satiri(gelen, govde, 1, gonderen, "cevap"))))
                    c.execute("INSERT INTO kayitsiz_cevaplar (gonderen, son) VALUES (%s, now()) ON CONFLICT (gonderen) DO UPDATE SET son = now(), sayi = kayitsiz_cevaplar.sayi + 1",
                              (gonderen,))
                    cevap = True
            return {"yeni": True, "cevap": cevap}

    # ───────────────────────── iş alma ─────────────────────────
    def is_al(self, sahip: str, kira_sn: int = KIRA_SN, en_cok: int = EN_COK_DENEME) -> dict | None:
        """Sıradaki işi kiralar: {"is": iş satırı, "gelen": kuyruk satırı}. Kirası dolmuş ve deneme hakkı bitmiş işler
        önce başarısız sayılır (bayiye ve Patron'a bildirim satırı yazılır)."""
        with self.baglan() as c:
            while True:
                with c.transaction():
                    j = c.execute(
                        """SELECT j.* FROM isler j
                           WHERE (j.durum = 'sirada' OR (j.durum = 'isleniyor' AND j.kira_bitis < now()))
                             AND NOT EXISTS (SELECT 1 FROM isler e WHERE e.gonderen = j.gonderen AND e.id < j.id
                                             AND e.durum IN ('sirada', 'isleniyor'))
                           ORDER BY j.id LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
                    if j is None:
                        return None
                    m = c.execute("SELECT ham FROM mesajlar WHERE id = %s", (j["mesaj_id"],)).fetchone()
                    if j["durum"] == "isleniyor" and j["deneme"] >= en_cok:
                        self._basarisiz_yaz(c, j, m["ham"], f"{j['deneme']} denemede bitmedi (kira doldu); otomatik tekrar yok")
                        continue
                    j = c.execute(
                        "UPDATE isler SET durum = 'isleniyor', sahip = %s, kira_bitis = now() + make_interval(secs => %s), "
                        "deneme = deneme + 1, basladi = now() WHERE id = %s RETURNING *", (sahip, kira_sn, j["id"])).fetchone()
                    return {"is": j, "gelen": m["ham"]}

    def _basarisiz_yaz(self, c, j: dict, gelen: dict, neden: str) -> None:
        c.execute("UPDATE isler SET durum = 'basarisiz', hata = %s, bitti = now(), sahip = NULL, kira_bitis = NULL WHERE id = %s",
                  (neden, j["id"]))
        satirlar = [(1, gelen["sender"], "cevap", HATA_BAYIYE)]
        if (gelen.get("role") or "bayi") != "patron":
            satirlar.append((2, "PATRON", "bildirim",
                             f"Portman: {maske(gelen['sender'])} mesajı işlenemedi ({neden}). Panelden bakabilirsiniz."))
        for sira, alici, tur, govde in satirlar:
            c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, satir) "
                      "VALUES (%s, %s, %s, %s, %s, %s, 'text', %s, %s) ON CONFLICT (id) DO NOTHING",
                      (satir_id(gelen["id"], sira), j["id"], gelen["id"], sira, alici, tur, govde,
                       Jsonb(metin_satiri(gelen, govde, sira, alici, tur))))

    def cikarim_kaydet(self, is_id: int, sahip: str, cikarim: dict) -> bool:
        with self.baglan() as c, c.transaction():
            r = c.execute("UPDATE isler SET cikarim = %s WHERE id = %s AND sahip = %s AND durum = 'isleniyor' RETURNING id",
                          (Jsonb(cikarim), is_id, sahip)).fetchone()
            return r is not None

    def is_geri_birak(self, is_id: int, sahip: str, neden: str) -> None:
        """Çakışmada iş sıraya geri döner; çakışma bir çöküş olmadığı için deneme hakkından düşülmez. Sahibi değilse dokunulmaz."""
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE isler SET durum = 'sirada', sahip = NULL, kira_bitis = NULL, hata = %s, deneme = greatest(deneme - 1, 0) "
                      "WHERE id = %s AND sahip = %s AND durum = 'isleniyor'", (neden, is_id, sahip))

    # ───────────────────────── konuşma ─────────────────────────
    def konusma_oku(self, gonderen: str) -> tuple[dict | None, int]:
        """(durum, sürüm); konuşma yoksa (None, 0)."""
        with self.baglan() as c:
            r = c.execute("SELECT durum, surum FROM konusmalar WHERE gonderen = %s", (gonderen,)).fetchone()
        return (r["durum"], r["surum"]) if r else (None, 0)

    def konusma_yaz(self, c, gonderen: str, bayi_kod, d: dict, surum: int) -> None:
        """Okunan sürümle yazar; arada başka bir yazma olduysa Cakisma."""
        if surum == 0:
            r = c.execute("INSERT INTO konusmalar (gonderen, bayi_kod, durum) VALUES (%s, %s, %s) ON CONFLICT (gonderen) DO NOTHING "
                          "RETURNING surum", (gonderen, bayi_kod, Jsonb(d))).fetchone()
        else:
            r = c.execute("UPDATE konusmalar SET durum = %s, surum = surum + 1, guncellendi = now(), bayi_kod = coalesce(%s, bayi_kod) "
                          "WHERE gonderen = %s AND surum = %s RETURNING surum", (Jsonb(d), bayi_kod, gonderen, surum)).fetchone()
        if r is None:
            raise Cakisma(f"konuşma {maske(gonderen)}: okunan sürüm {surum} artık güncel değil")

    # ───────────────────────── işin bitişi (tek işlem) ─────────────────────────
    def isi_bitir(self, is_kaydi: dict, sahip: str, gelen: dict, surum: int, d_eski: dict | None, d_yeni: dict, cikti: dict,
                  karar_ozeti: dict | None = None) -> dict:
        """Konuşma, proje/revizyon, soru kaydı, giden satırlar ve işin bitişi tek işlemde. Kira kaybedildiyse KiraKaybi,
        konuşma arada değiştiyse Cakisma; ikisinde de hiçbir şey yazılmaz. Dönen: {"proje_id", "revizyon_id"}."""
        karar_ozeti = karar_ozeti or {}
        sonuc = cikti.get("sonuc") or {}
        bayi_kod = (gelen.get("bayi") or {}).get("kod") if isinstance(gelen.get("bayi"), dict) else None
        try:
            return self._isi_bitir(is_kaydi, sahip, gelen, surum, d_eski, d_yeni, cikti, karar_ozeti, sonuc, bayi_kod)
        except psycopg.errors.UniqueViolation as e:
            # ör. iki işleyici aynı saniyede aynı bayi koduyla aynı İş Emri numarasını üretti: sonuç yazılmaz, iş yeniden sıraya girer
            raise Cakisma(f"benzersizlik: {str(e).splitlines()[0][:160]}") from e

    def _isi_bitir(self, is_kaydi, sahip, gelen, surum, d_eski, d_yeni, cikti, karar_ozeti, sonuc, bayi_kod) -> dict:
        with self.baglan() as c, c.transaction():
            j = c.execute("SELECT * FROM isler WHERE id = %s FOR UPDATE", (is_kaydi["id"],)).fetchone()
            if j is None or j["durum"] != "isleniyor" or j["sahip"] != sahip:
                raise KiraKaybi(f"iş {is_kaydi['id']}: artık bu işleyicide değil ({j['durum'] if j else 'yok'})")
            # proje ve revizyon
            proje_id = d_yeni.get("proje_id")          # konusma sıfırlandıysa (yeni talep) yok: yeni proje açılır
            revizyon_id = None
            if sonuc.get("eylem") == "is_emri" and sonuc.get("is_emri_no"):
                ie = d_yeni.get("son_is_emri") or {}
                rev = int(sonuc.get("revizyon") or ie.get("revizyon") or 1)
                if rev == 1 or not proje_id:
                    proje_id = c.execute("INSERT INTO projeler (gonderen, bayi_kod, ilk_is_emri_no) VALUES (%s, %s, %s) RETURNING id",
                                         (gelen["sender"], bayi_kod, sonuc["is_emri_no"])).fetchone()["id"]
                cizim = sonuc.get("cizim") or {}
                gecti = bool(cizim.get("passed"))
                c.execute("UPDATE revizyonlar SET durum = 'yerini_aldi' WHERE proje_id = %s AND durum = 'onay_bekliyor'", (proje_id,))
                ekler = {k: v for k, v in (cizim.get("ekler") or {}).items()}          # İE-04: aynı İş Emri'nden görsel, IFC, 3D (yol + özet)
                revizyon_id = c.execute(
                    "INSERT INTO revizyonlar (proje_id, rev, is_emri_no, gonderen, bayi_kod, kaynak_mesaj_id, is_emri, pdf_yolu, pdf_sha256, "
                    "dxf_sha256, dogrulandi, durum, ekler) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (proje_id, rev, sonuc["is_emri_no"], gelen["sender"], bayi_kod, gelen["id"], Jsonb(ie), cizim.get("pdf"),
                     cizim.get("pdf_sha256"), cizim.get("dxf_sha256"), gecti, "onay_bekliyor" if gecti else "dogrulanmadi", Jsonb(ekler))).fetchone()["id"]
            if karar_ozeti.get("onaylanan_is_emri_no"):
                c.execute("UPDATE revizyonlar SET durum = 'onaylandi', onay_mesaj_id = %s, onaylandi = now() "
                          "WHERE is_emri_no = %s AND rev = %s AND gonderen = %s AND durum = 'onay_bekliyor'",
                          (gelen["id"], karar_ozeti["onaylanan_is_emri_no"], karar_ozeti.get("onaylanan_rev"), gelen["sender"]))
            if d_yeni.get("son_is_emri") or proje_id:
                d_yeni["proje_id"] = proje_id
            else:
                d_yeni.pop("proje_id", None)
            self.konusma_yaz(c, gelen["sender"], bayi_kod, d_yeni, surum)
            self._soru_kaydi(c, gelen, d_eski or {}, d_yeni, sonuc, karar_ozeti)
            self._set_kaydi(c, gelen, d_eski or {}, d_yeni, proje_id)
            for s in cikti.get("satirlar") or []:
                # Revizyona bağlı satırlar: PDF ve aynı İş Emri'nin görsel/etkileşim satırları (onay butonu → revizyon; alıntı → revizyon)
                bagli = revizyon_id if (s.get("kind") == "document" or (s.get("is_emri_no") and s.get("is_emri_no") == sonuc.get("is_emri_no"))) else None
                c.execute(
                    "INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, dosya, sha256, revizyon_id, satir) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (s["id"], j["id"], gelen["id"], s["seq"], s["to"], s.get("tur") or "cevap", s.get("kind") or "text", s.get("body") or "",
                     s.get("file"), s.get("sha256"), bagli, Jsonb(s)))
            c.execute("UPDATE isler SET durum = %s, sonuc = %s, hata = %s, bitti = now(), sahip = NULL, kira_bitis = NULL WHERE id = %s",
                      ("basarisiz" if cikti.get("hata") else "bitti", Jsonb(sonuc), cikti.get("hata"), j["id"]))
        return {"proje_id": proje_id, "revizyon_id": revizyon_id}

    def _soru_kaydi(self, c, gelen: dict, d_eski: dict, d_yeni: dict, sonuc: dict, karar_ozeti: dict) -> None:
        """Konuşmadaki askıdaki soruyu sorular tablosuna işler (aynı işlemde). Kural katmanının okuduğu kaynak konuşma
        kaydıdır; bu tablo hangi mesajın soruyu doğurduğunu, hangisinin kapattığını ve nasıl kapandığını tutar."""
        acik = c.execute("SELECT * FROM sorular WHERE gonderen = %s AND durum = 'acik' FOR UPDATE", (gelen["sender"],)).fetchone()
        alan = d_yeni.get("son_soru_alani")
        eylem = sonuc.get("eylem")
        simdi = time.time()
        ayni = (acik is not None and not karar_ozeti.get("sifirlandi") and alan == acik["alan"]
                and (alan != ESKI_TASLAK_SORUSU or (d_yeni.get("bekleyen_metin") or "") == (acik["bekletilen_metin"] or "")))
        if acik is not None and not ayni:
            # Sorulan bilgi bu mesajla geldiyse cevaplandi. Talep insana devredildiyse devredildi (devirde taslak boşaldığı
            # için cevabın gelip gelmediği okunamaz). Konuşma sıfırlandıysa (yeni talep, iptal, başka model) ya da soru
            # başka yoldan kalktıysa dustu.
            if _cevap_mi(acik["alan"], d_eski, d_yeni, sonuc, karar_ozeti):
                kapanis = "cevaplandi"
            elif eylem == "yonlendir" and not karar_ozeti.get("sifirlandi"):
                kapanis = "devredildi"
            else:
                kapanis = "dustu"
            c.execute("UPDATE sorular SET durum = %s, cevap_mesaj_id = %s, kapandi = now() WHERE id = %s", (kapanis, gelen["id"], acik["id"]))
            acik = None
        if alan is None:
            return
        if acik is not None:
            if eylem == "sor":      # aynı soru bu işte yeniden soruldu
                deneme = int(d_yeni.get("eski_taslak_soru") or 0) if alan == ESKI_TASLAK_SORUSU else acik["deneme"] + 1
                c.execute("UPDATE sorular SET deneme = %s, son_soruldu = now(), gecerlilik_sonu = %s WHERE id = %s",
                          (max(deneme, acik["deneme"]), self._gecerlilik(d_yeni, alan), acik["id"]))
            return
        if eylem != "sor":
            return                  # bu işte sorulmadı (ör. kaydı olmayan eski soru): bu mesaj onun kaynağı değil
        c.execute(
            "INSERT INTO sorular (gonderen, proje_id, alan, kaynak_mesaj_id, bekletilen_talep, bekletilen_metin, pencere_satiri, deneme, "
            "soruldu, son_soruldu, gecerlilik_sonu) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, to_timestamp(%s), to_timestamp(%s), %s)",
            (gelen["sender"], d_yeni.get("proje_id"), alan, gelen["id"], *soru_ayrintisi(d_yeni, alan), simdi, simdi,
             self._gecerlilik(d_yeni, alan)))

    def _set_kaydi(self, c, gelen: dict, d_eski: dict, d_yeni: dict, proje_id) -> None:
        """İE-04: konuşmadaki seçenek setini secenek_setleri tablosuna işler (aynı işlemde). Bir göndericinin tek açık seti olur;
        yeni set açılınca eskisi 'eskidi', seçimle 'secildi', sıfırlanma ve devirle 'dustu'."""
        acik = c.execute("SELECT * FROM secenek_setleri WHERE gonderen = %s AND durum = 'acik' FOR UPDATE", (gelen["sender"],)).fetchone()
        yeni = d_yeni.get("secenek_seti") or None
        if acik is not None and (yeni is None or yeni.get("id") != acik["id"] or yeni.get("durum") != "acik"):
            if yeni is not None and yeni.get("id") == acik["id"] and yeni.get("durum") in ("secildi", "dustu", "eskidi"):
                kapanis = yeni["durum"]
            elif yeni is not None and yeni.get("id") != acik["id"] and yeni.get("durum") == "acik":
                kapanis = "eskidi"
            else:
                kapanis = "dustu"
            c.execute("UPDATE secenek_setleri SET durum = %s, secilen_kod = %s, secim_mesaj_id = %s, kapandi = now() WHERE id = %s",
                      (kapanis, (yeni or {}).get("secilen_kod") if kapanis == "secildi" else None, gelen["id"] if kapanis == "secildi" else None, acik["id"]))
            acik = None
        if yeni is not None and yeni.get("durum") == "acik" and acik is None:
            c.execute("INSERT INTO secenek_setleri (id, gonderen, proje_id, kaynak_mesaj_id, adaylar, agirliklar) VALUES (%s, %s, %s, %s, %s, %s) "
                      "ON CONFLICT (id) DO UPDATE SET durum = 'acik', adaylar = EXCLUDED.adaylar, kapandi = NULL",
                      (yeni["id"], gelen["sender"], proje_id, gelen["id"], Jsonb(yeni.get("adaylar") or []), Jsonb(yeni.get("agirliklar"))))

    def giden_satiri(self, dis_id: str | None) -> dict | None:
        """WhatsApp kimliği (wamid) verilen giden satırın hosting biçimi (satir). Buton cevabının hangi mesaja verildiğini doğrulamak için."""
        if not dis_id:
            return None
        with self.baglan() as c:
            r = c.execute("SELECT satir FROM giden WHERE dis_id = %s ORDER BY olusturuldu DESC LIMIT 1", (dis_id,)).fetchone()
        return r["satir"] if r else None

    def kabul_edilmis_adaylar(self) -> set[str]:
        """K-A10: mühendis kabulü kayıtlı 'gecerli' adaylar; yalnız bunlar bayiye sunulur (test adayları ayarla, kalıcı modda yok)."""
        with self.baglan() as c:
            return {r["kod"] for r in c.execute("SELECT kod FROM adaylar WHERE durum = 'gecerli' AND muhendis_kabulu IS NOT NULL")}

    def aday_yaz(self, kod: str, durum: str, referans_model: str | None = None, kaynak: dict | None = None, ozet: dict | None = None,
                 denetim: dict | None = None, muhendis_kabulu: dict | None = None, not_: str | None = None) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("INSERT INTO adaylar (kod, durum, referans_model, kaynak, ozet, denetim, muhendis_kabulu, not_) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                      "ON CONFLICT (kod) DO UPDATE SET durum = EXCLUDED.durum, referans_model = EXCLUDED.referans_model, kaynak = EXCLUDED.kaynak, "
                      "ozet = EXCLUDED.ozet, denetim = EXCLUDED.denetim, muhendis_kabulu = EXCLUDED.muhendis_kabulu, not_ = EXCLUDED.not_, guncellendi = now()",
                      (kod, durum, referans_model, Jsonb(kaynak) if kaynak is not None else None, Jsonb(ozet) if ozet is not None else None,
                       Jsonb(denetim) if denetim is not None else None, Jsonb(muhendis_kabulu) if muhendis_kabulu is not None else None, not_))

    @staticmethod
    def _gecerlilik(d: dict, alan: str):
        if alan == ESKI_TASLAK_SORUSU and d.get("bekleyen_zamani"):
            import datetime
            return datetime.datetime.fromtimestamp(int(d["bekleyen_zamani"]) + ESKI_SORU_SN, tz=datetime.timezone.utc)
        return None

    # ───────────────────────── revizyon onayı için ─────────────────────────
    def revizyon_iletimi(self, gonderen: str, is_emri_no: str, rev: int) -> dict | None:
        """Revizyonun PDF satırı: {"id", "rev", "durum", "pdf_durum", "pdf_wamid", "kabul", "gonderildi", "teslim_durumu", "teslim"}.
        kabul: hosting'in WhatsApp API kabulünü kaydettiği an (hosting saati); gonderildi: Meta'nın ilk 'sent' bildirimi; teslim:
        Meta bildirimindeki ilk 'delivered'/'read' anı (ikisi Meta saati). Kayıt yoksa None."""
        with self.baglan() as c:
            return c.execute(
                "SELECT r.id, r.rev, r.durum, g.durum AS pdf_durum, g.dis_id AS pdf_wamid, extract(epoch FROM g.kabul_zamani) AS kabul, "
                "extract(epoch FROM g.gonderildi_zamani) AS gonderildi, g.teslim_durumu, extract(epoch FROM g.teslim_zamani) AS teslim "
                "FROM revizyonlar r LEFT JOIN giden g ON g.revizyon_id = r.id AND g.kind = 'document' "
                "WHERE r.gonderen = %s AND r.is_emri_no = %s AND r.rev = %s ORDER BY g.olusturuldu DESC NULLS LAST LIMIT 1",
                (gonderen, is_emri_no, rev)).fetchone()

    def alintinin_revizyonu(self, gonderen: str, dis_id: str) -> dict | None:
        """Bayinin alıntıladığı giden mesaj bir revizyona aitse o revizyon (yalnız bu göndericinin kayıtları)."""
        with self.baglan() as c:
            return c.execute(       # PDF satırı revizyona bağlı; aynı işin metin satırı da o revizyona sayılır
                "SELECT r.id, r.rev, r.is_emri_no FROM giden g JOIN revizyonlar r "
                "ON r.id = g.revizyon_id OR (g.revizyon_id IS NULL AND r.kaynak_mesaj_id = g.mesaj_id) "
                "WHERE g.dis_id = %s AND r.gonderen = %s ORDER BY r.id DESC LIMIT 1", (dis_id, gonderen)).fetchone()

    # ───────────────────────── bayi kapsamlı okuma ─────────────────────────
    # Kapsam anahtarı bayinin WhatsApp numarasıdır (Meta imzalı webhook'un doğruladığı gönderen); bayi kodu benzersiz değildir.
    # Bugün bu işlevleri akışın kendisi çağırmıyor (akış zaten gönderen numarasına bağlı); panel ya da yeniden gönderim için.
    def projeler(self, gonderen: str) -> list[dict]:
        with self.baglan() as c:
            return c.execute("SELECT id, ilk_is_emri_no, olusturuldu FROM projeler WHERE gonderen = %s ORDER BY id", (gonderen,)).fetchall()

    def revizyon(self, gonderen: str, is_emri_no: str, rev: int | None = None) -> dict | None:
        """Başka bayinin revizyonu için None (numara bilinse bile). rev verilmezse o numaranın son revizyonu."""
        with self.baglan() as c:
            return c.execute("SELECT id, proje_id, rev, is_emri_no, durum, pdf_yolu, pdf_sha256 FROM revizyonlar "
                             "WHERE gonderen = %s AND is_emri_no = %s AND (%s::int IS NULL OR rev = %s) ORDER BY rev DESC LIMIT 1",
                             (gonderen, is_emri_no, rev, rev)).fetchone()

    def cikti_yolu(self, gonderen: str, is_emri_no: str, rev: int | None = None) -> str | None:
        r = self.revizyon(gonderen, is_emri_no, rev)
        return r["pdf_yolu"] if r else None

    # ───────────────────────── gönderim ─────────────────────────
    def yarim_gonderimleri_belirsiz_say(self, esik_sn: int = GONDERIM_ZAMAN_ASIMI_SN) -> int:
        with self.baglan() as c, c.transaction():
            return c.execute("UPDATE giden SET durum = 'belirsiz', hata = 'Gönderim teyit edilmeden kaldı; otomatik tekrar yok.' "
                             "WHERE durum = 'gonderiliyor' AND gonderim_basladi < now() - make_interval(secs => %s)", (esik_sn,)).rowcount

    def gonderime_al(self) -> dict | None:
        """Sıradaki 'bekliyor' satırı 'gonderiliyor' yapar (ayrı işlem: dış çağrıdan önce kalıcı)."""
        with self.baglan() as c, c.transaction():
            r = c.execute("SELECT g.*, m.ham AS gelen FROM giden g JOIN mesajlar m ON m.id = g.mesaj_id WHERE g.durum = 'bekliyor' "
                          "ORDER BY g.olusturuldu, g.mesaj_id, g.sira LIMIT 1 FOR UPDATE OF g SKIP LOCKED").fetchone()
            if r is None:
                return None
            r.update(c.execute("UPDATE giden SET durum = 'gonderiliyor', deneme = deneme + 1, gonderim_basladi = now() WHERE id = %s "
                               "RETURNING durum, deneme, gonderim_basladi", (r["id"],)).fetchone())
            return r

    def gonderim_sonucu(self, satir_id_: str, durum: str, dis_id: str | None = None, hata: str | None = None,
                        kabul_zamani: float | None = None) -> None:
        """'kabul_edildi' = WhatsApp API gönderimi kabul etti; bayinin telefonuna teslim DEĞİLDİR (teslim: teslim_bildir).
        Belirsiz sayıldıktan sonra gelen kabul teyidi de yazılır (bilgi kaybolmaz; yeniden gönderim değildir). Öteki sonuçlar
        yalnız gönderimi süren ('gonderiliyor', 'hostingte') satıra yazılır."""
        assert durum in ("kabul_edildi", "belirsiz", "gonderilmedi")
        with self.baglan() as c, c.transaction():
            if durum == "kabul_edildi":
                c.execute("UPDATE giden SET durum = 'kabul_edildi', dis_id = %s, kabul_zamani = coalesce(to_timestamp(%s::float8), now()), "
                          "hata = CASE WHEN durum = 'belirsiz' THEN 'Belirsiz sayıldıktan sonra kabul teyidi geldi.' END "
                          "WHERE id = %s AND durum IN ('gonderiliyor', 'hostingte', 'belirsiz')", (dis_id, kabul_zamani, satir_id_))
            else:
                c.execute("UPDATE giden SET durum = %s, hata = %s WHERE id = %s AND durum IN ('gonderiliyor', 'hostingte')",
                          (durum, hata, satir_id_))

    _TESLIM_SIRASI = {"sent": 1, "failed": 2, "delivered": 3, "read": 4}      # feature.php::pm_kanal_status ile aynı sıra

    def teslim_bildir(self, satir_id_: str, teslim_durumu: str | None, teslim_zamani: float | None = None,
                      gonderildi_zamani: float | None = None) -> None:
        """Meta'nın imzalı durum bildirimi (hosting'ten okunur): sent / delivered / read / failed. Durum yalnız ileri gider;
        teslim_zamani ilk 'delivered' ya da 'read' anı, gonderildi_zamani ilk 'sent' (ya da sonraki) anıdır."""
        sira = self._TESLIM_SIRASI
        if gonderildi_zamani is not None:
            with self.baglan() as c, c.transaction():
                c.execute("UPDATE giden SET gonderildi_zamani = least(coalesce(gonderildi_zamani, to_timestamp(%s::float8)), "
                          "to_timestamp(%s::float8)) WHERE id = %s", (gonderildi_zamani, gonderildi_zamani, satir_id_))
        if teslim_durumu not in sira:
            return
        with self.baglan() as c, c.transaction():
            r = c.execute("SELECT teslim_durumu FROM giden WHERE id = %s FOR UPDATE", (satir_id_,)).fetchone()
            if r is None:
                return
            yeni = teslim_durumu if sira[teslim_durumu] >= sira.get(r["teslim_durumu"], 0) else r["teslim_durumu"]
            zaman = teslim_zamani if teslim_durumu in ("delivered", "read") else None
            c.execute("UPDATE giden SET teslim_durumu = %s, teslim_zamani = CASE WHEN %s::float8 IS NULL THEN teslim_zamani "
                      "ELSE least(coalesce(teslim_zamani, to_timestamp(%s::float8)), to_timestamp(%s::float8)) END WHERE id = %s",
                      (yeni, zaman, zaman, zaman, satir_id_))

    # ───────────────────────── hosting'e devir (VPS ajanı, kalıcı mod) ─────────────────────────
    def teslim_bekleyen_isler(self, en_fazla: int = 100, haric: list[int] | tuple = (), risk_sn: float = 480) -> list[dict]:
        """Bitmiş (ya da başarısız) ve satırları henüz hosting'e devredilmemiş işler, eskiden yeniye: {"is_id", "aldi"}.
        aldi: ajanın mesajı hosting'ten son aldığı an (epoch, VPS saati; ham._ajan_aldi, yoksa Postgres'e yazıldığı an).
        haric: şimdilik denenmeyecek işler (ajanın aralıklı yeniden denemesi); sıradaki işleri bekletmesinler. Mesaj alınalı
        'risk_sn' saniye olduysa haric'te olsa da döner (hosting'in süpürmesinden önce son deneme)."""
        aldi = "coalesce((m.ham->>'_ajan_aldi')::float8, extract(epoch FROM m.alindi)::float8)"
        with self.baglan() as c:
            return c.execute(
                f"SELECT j.id AS is_id, {aldi} AS aldi FROM isler j JOIN mesajlar m ON m.id = j.mesaj_id "
                "WHERE j.durum IN ('bitti', 'basarisiz') AND EXISTS (SELECT 1 FROM giden g WHERE g.is_id = j.id AND g.durum = 'bekliyor') "
                f"AND NOT (j.id = ANY(%s) AND {aldi} > extract(epoch FROM now()) - %s) ORDER BY j.id LIMIT %s",
                (list(haric), risk_sn, en_fazla)).fetchall()

    def teslim_paketi(self, is_id: int) -> dict:
        """Hosting'in result çağrısının beklediği biçim: {"inbound_id", "gonderen", "cikti": {"satirlar", "sonuc", "hata"},
        "durum", "dosyalar": [(satir_id, yol, sha256)]}. Konuşma durumu hosting'teki durum/ aynası içindir (kaynak Postgres)."""
        with self.baglan() as c:
            j = c.execute("SELECT * FROM isler WHERE id = %s", (is_id,)).fetchone()
            satirlar = c.execute("SELECT * FROM giden WHERE is_id = %s AND durum = 'bekliyor' ORDER BY sira", (is_id,)).fetchall()
            k = c.execute("SELECT durum FROM konusmalar WHERE gonderen = %s", (j["gonderen"],)).fetchone()
        durum = {kk: v for kk, v in k["durum"].items() if kk != "proje_id"} if k else None
        return {"inbound_id": j["mesaj_id"], "gonderen": j["gonderen"],
                "cikti": {"satirlar": [dict(s["satir"]) for s in satirlar], "sonuc": j["sonuc"] or {}, "hata": j["hata"]},
                "durum": durum, "dosyalar": [(s["id"], s["dosya"], s["sha256"]) for s in satirlar if s["kind"] == "document"]}

    def hostinge_verildi(self, satir_idleri: list[str]) -> int:
        with self.baglan() as c, c.transaction():
            return c.execute("UPDATE giden SET durum = 'hostingte', hostinge_verildi = now() WHERE id = ANY(%s) AND durum = 'bekliyor'",
                             (list(satir_idleri),)).rowcount

    def hostinge_verilemedi(self, satir_idleri: list[str], neden: str) -> int:
        """Hosting satırları kesin olarak reddetti (ör. gelen mesaj orada artık işlenmekte değil): gönderilmedi."""
        with self.baglan() as c, c.transaction():
            return c.execute("UPDATE giden SET durum = 'gonderilmedi', hata = %s WHERE id = ANY(%s) AND durum = 'bekliyor'",
                             (neden[:300], list(satir_idleri))).rowcount

    def alinma_anini_yenile(self, mesaj_id: str, an: float) -> None:
        """Aynı kanal mesajı hosting'ten yeniden alındı: hosting'teki satırın 600 sn'lik süresi bu andan yeniden başlar."""
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE mesajlar SET ham = jsonb_set(ham, '{_ajan_aldi}', to_jsonb(%s::float8)) WHERE id = %s", (an, mesaj_id))

    def hostinge_yeniden_dene(self, is_id: int) -> int:
        """Aynı kanal mesajı hosting kuyruğuna yeniden konup yeniden alındı: ilk işin hosting'e hiç verilemeyen (hosting
        reddetti ya da gelen satırı orada artık işlenmekte değildi) satırları yeniden 'bekliyor' olur ve bu yeni alımla
        hosting'e verilir. Hosting'e bir kez verilmiş satırlara dokunulmaz (gönderim tekrarı değildir)."""
        with self.baglan() as c, c.transaction():
            return c.execute("UPDATE giden SET durum = 'bekliyor', hata = NULL WHERE is_id = %s AND durum = 'gonderilmedi' "
                             "AND hostinge_verildi IS NULL", (is_id,)).rowcount

    def gonderilemeyen_sayisi(self, saat: int = 24, devir_sn: int = 300) -> dict:
        """Sağlık uyarısı için, son 'saat' saatte: gönderilmediği kesin (gonderilmedi), sonucu belirsiz (belirsiz), Meta'nın
        iletemedim dediği (teslim 'failed') satırlar; ve (süre sınırı olmadan) işi 'devir_sn' saniyeden uzun süre önce bittiği
        hâlde hâlâ hosting'e verilemeyen (bekliyor) satırlar."""
        with self.baglan() as c:
            r = c.execute("WITH s AS (SELECT now() - make_interval(hours => %s) AS t) "
                          "SELECT count(*) FILTER (WHERE g.durum = 'gonderilmedi' AND g.olusturuldu > s.t) AS gonderilmedi, "
                          "count(*) FILTER (WHERE g.durum = 'belirsiz' AND g.olusturuldu > s.t) AS belirsiz, "
                          "count(*) FILTER (WHERE g.teslim_durumu = 'failed' AND g.olusturuldu > s.t) AS meta_iletemedi, "
                          "count(*) FILTER (WHERE g.durum = 'bekliyor' AND j.durum IN ('bitti', 'basarisiz') "
                          "                 AND j.bitti < now() - make_interval(secs => %s)) AS devir_bekliyor "
                          "FROM giden g JOIN isler j ON j.id = g.is_id CROSS JOIN s", (saat, devir_sn)).fetchone()
        return dict(r)

    def esitlenecek_satirlar(self, en_fazla: int = 200, gun: int = 3) -> list[str]:
        """Hosting'e devredilmiş ve sonucu hosting'te değişebilecek satırlar, yeniden eskiye (son 'gun' gün; en çok 'en_fazla'):
        gönderimi süren (hostingte), sonucu belirsiz (Meta'nın imzalı durum bildirimi sonradan kabulü gösterebilir) ve kabul
        edilip teslim ya da hata bildirimi henüz gelmemiş satırlar (PDF: onay denetimi; metin: Meta 'failed' derse uyarı)."""
        with self.baglan() as c:
            return [r["id"] for r in c.execute(
                "SELECT id FROM giden WHERE hostinge_verildi IS NOT NULL AND (durum IN ('hostingte', 'belirsiz') OR (durum = 'kabul_edildi' "
                "AND teslim_zamani IS NULL AND coalesce(teslim_durumu, '') <> 'failed')) "
                "AND olusturuldu > now() - make_interval(days => %s) ORDER BY olusturuldu DESC LIMIT %s", (gun, en_fazla))]

    def hosting_durumu_isle(self, satir_id_: str, st: dict) -> None:
        """api.php giden_durum'un bir satırı → Postgres. Hosting durumları (feature.php): pending/uploading/sending → sürüyor;
        accepted/sent/delivered/read/failed (wamid'li) → API kabul etti (+ Meta'nın 'sent' anı ve teslim durumu); uncertain →
        belirsiz; held (hosting sonradan da göndermez) ya da yeniden denenmeyecek upload_failed (PDF'te 2. deneme, metinde
        ilki; feature.php::pm_kanal_tick) → gönderilmedi."""
        durum = st.get("state")
        if durum in ("accepted", "sent", "delivered", "read", "failed") and st.get("wamid"):
            self.gonderim_sonucu(satir_id_, "kabul_edildi", dis_id=st["wamid"], kabul_zamani=st.get("request_accepted_at"))
            if st.get("delivery_state") or st.get("sent_at"):
                self.teslim_bildir(satir_id_, st.get("delivery_state"), st.get("delivered_at"), st.get("sent_at"))
        elif durum == "uncertain":
            self.gonderim_sonucu(satir_id_, "belirsiz", hata=str(st.get("error") or "hosting: gönderim sonucu belirsiz")[:300])
        elif durum == "held" or (durum == "upload_failed" and (self._tur(satir_id_) != "document" or int(st.get("attempts") or 0) >= 2)):
            self.gonderim_sonucu(satir_id_, "gonderilmedi", hata=str(st.get("error") or f"hosting: {durum}")[:300])

    def _tur(self, satir_id_: str) -> str | None:
        with self.baglan() as c:
            r = c.execute("SELECT kind FROM giden WHERE id = %s", (satir_id_,)).fetchone()
        return r["kind"] if r else None

    # ───────────────────────── İE-06: bayi kimlik kartı (kaynak bu tablodur) ─────────────────────────
    ROLLER = ("bayi", "patron", "muhendis")
    _BAYI_SUTUNLAR = "numara, kod, ad, hitap, firma, bolge, rol, aktif, kaynak, olusturuldu, guncellendi"

    def bayi_oku(self, numara) -> dict | None:
        with self.baglan() as c:
            return c.execute(f"SELECT {self._BAYI_SUTUNLAR} FROM bayiler WHERE numara = %s", (str(numara or ""),)).fetchone()

    def bayi_listesi(self) -> list[dict]:
        with self.baglan() as c:
            return c.execute(f"SELECT {self._BAYI_SUTUNLAR} FROM bayiler ORDER BY aktif DESC, (rol = 'patron') DESC, ad, numara").fetchall()

    def bayi_yaz(self, numara, *, ad: str = "", kod: str | None = None, hitap: str = "", firma: str = "", bolge: str = "", rol: str = "bayi",
                 aktif: bool = True, kaynak: str = "panel") -> dict:
        """Kimlik kartını yazar (yeni ya da güncelleme; numara değişmez). kod boşsa türetilir: patron → 'PATRON', değilse 'B' + son 4 hane
        (feature.php pm_kanal_bayi ile aynı). Değer denetimi: numara 8–15 hane, rol bilinen, metinler kırpılır."""
        numara = str(numara or "").strip()
        if not re.fullmatch(r"[1-9][0-9]{7,14}", numara):
            raise ValueError("numara geçersiz: yalnız rakam, ülke koduyla 8–15 hane")
        if rol not in self.ROLLER:
            raise ValueError(f"rol geçersiz: {rol!r}")
        kod = (str(kod or "").strip() or ("PATRON" if rol == "patron" else "B" + numara[-4:]))[:40]
        alanlar = (numara, kod, str(ad or "").strip()[:120], str(hitap or "").strip()[:40], str(firma or "").strip()[:120], str(bolge or "").strip()[:80],
                   rol, bool(aktif), kaynak)
        with self.baglan() as c, c.transaction():
            return c.execute(
                "INSERT INTO bayiler (numara, kod, ad, hitap, firma, bolge, rol, aktif, kaynak) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (numara) DO UPDATE SET kod = EXCLUDED.kod, ad = EXCLUDED.ad, hitap = EXCLUDED.hitap, firma = EXCLUDED.firma, "
                "bolge = EXCLUDED.bolge, rol = EXCLUDED.rol, aktif = EXCLUDED.aktif, kaynak = EXCLUDED.kaynak, guncellendi = now() "
                f"RETURNING {self._BAYI_SUTUNLAR}", alanlar).fetchone()

    def patron_numarasi(self) -> str | None:
        with self.baglan() as c:
            r = c.execute("SELECT numara FROM bayiler WHERE rol = 'patron' AND aktif ORDER BY olusturuldu, numara LIMIT 1").fetchone()
        return r["numara"] if r else None

    def gelen_bayisi(self, numara) -> dict | None:
        """Gelen satırın 'bayi' alanı (feature.php pm_kanal_bayi biçimi: kod, ad, firma, rol); kayıtlı ve aktif değilse None."""
        b = self.bayi_oku(numara)
        if not b or not b["aktif"]:
            return None
        return {"kod": b["kod"] or ("PATRON" if b["rol"] == "patron" else "B" + str(numara)[-4:]), "ad": b["ad"] or str(numara),
                "firma": b["firma"] or "", "rol": b["rol"]}

    # ───────────────────────── İE-06: webhook olayları, durum bildirimi, gönderim yardımcıları ─────────────────────────
    def olay_kaydet(self, anahtar: str, tur: str) -> bool:
        """Olay ilk kez görülüyorsa True (yazılır); Meta aynı olayı yeniden gönderdiyse False."""
        with self.baglan() as c, c.transaction():
            return c.execute("INSERT INTO webhook_olaylar (anahtar, tur) VALUES (%s, %s) ON CONFLICT (anahtar) DO NOTHING RETURNING anahtar",
                             (str(anahtar)[:200], tur)).fetchone() is not None

    def olay_var(self, anahtar: str) -> bool:
        with self.baglan() as c:
            return c.execute("SELECT 1 FROM webhook_olaylar WHERE anahtar = %s", (str(anahtar)[:200],)).fetchone() is not None

    def teslim_hatasi_yaz(self, satir_id_: str, hata: str) -> None:
        """Meta 'failed' bildirimi: hata metni yazılır, durum değişmez (feature.php pm_kanal_status ile aynı)."""
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE giden SET hata = %s WHERE id = %s", (hata[:300], satir_id_))

    def son_gelen_zamani(self, numara) -> float | None:
        """Numaradan gelen son mesajın WhatsApp zamanı (epoch): Patron bildirimlerinde 24 saat penceresi için."""
        with self.baglan() as c:
            r = c.execute("SELECT extract(epoch FROM max(wa_zamani))::float8 AS t FROM mesajlar WHERE gonderen = %s AND wa_zamani <= now()",
                          (str(numara),)).fetchone()
        return float(r["t"]) if r and r["t"] is not None else None

    def giden_durum_satiri(self, wamid: str, opaque: str | None) -> dict | None:
        """Meta durum bildiriminin satırı: wamid ile; yoksa biz_opaque_callback_data (= satır id) ile, yalnız wamid'i yazılamamış ve en az
        bir kez denenmiş satırda (feature.php pm_kanal_status ile aynı)."""
        with self.baglan() as c:
            r = c.execute("SELECT id, durum, dis_id, deneme, alici_cozuldu, teslim_durumu FROM giden WHERE dis_id = %s ORDER BY olusturuldu DESC LIMIT 1",
                          (wamid,)).fetchone()
            if r is None and opaque:
                r = c.execute("SELECT id, durum, dis_id, deneme, alici_cozuldu, teslim_durumu FROM giden WHERE id = %s AND dis_id IS NULL AND deneme >= 1",
                              (str(opaque)[:64],)).fetchone()
        return r

    def medya_id_kaydet(self, satir_id_: str, medya_id: str) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE giden SET medya_id = %s WHERE id = %s", (medya_id, satir_id_))

    def alici_cozuldu_kaydet(self, satir_id_: str, alici: str) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE giden SET alici_cozuldu = %s WHERE id = %s", (alici, satir_id_))

    def gonderim_geri_birak(self, satir_id_: str, hata: str) -> None:
        """Dış çağrı yapılmadan vazgeçildi ve bir kez daha denenecek (ör. medya yüklenemedi): satır yeniden 'bekliyor'."""
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE giden SET durum = 'bekliyor', hata = %s WHERE id = %s AND durum = 'gonderiliyor'", (hata[:300], satir_id_))

    def dry_run_tut(self) -> int:
        """dry_run: bekleyen satırlar gönderilmez, sonradan da gönderilmez (feature.php 'held')."""
        with self.baglan() as c, c.transaction():
            return c.execute("UPDATE giden SET durum = 'gonderilmedi', hata = 'dry_run: gönderilmedi (sonradan da gönderilmez)' "
                             "WHERE durum = 'bekliyor'").rowcount

    # ───────────────────────── İE-06: gelen medya ─────────────────────────
    def gelen_dosya_ekle(self, mesaj_id: str, medya_id: str, dosya_adi: str | None, mime: str | None) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("INSERT INTO gelen_dosyalar (mesaj_id, medya_id, dosya_adi, mime) VALUES (%s, %s, %s, %s) ON CONFLICT (mesaj_id, medya_id) DO NOTHING",
                      (mesaj_id, str(medya_id)[:64], (dosya_adi or None) and str(dosya_adi)[:200], (mime or None) and str(mime)[:100]))

    def bekleyen_gelen_dosyalar(self, en_fazla: int = 20) -> list[dict]:
        with self.baglan() as c:
            return c.execute("SELECT d.id, d.mesaj_id, d.medya_id, d.dosya_adi, d.mime, d.deneme, m.gonderen FROM gelen_dosyalar d "
                             "JOIN mesajlar m ON m.id = d.mesaj_id WHERE d.yol IS NULL AND d.deneme < 3 ORDER BY d.olusturuldu LIMIT %s", (en_fazla,)).fetchall()

    def gelen_dosya_indirildi(self, id_: int, yol: str, mime: str, boyut: int, sha256: str) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE gelen_dosyalar SET yol = %s, mime = %s, boyut = %s, sha256 = %s, indirildi = now(), hata = NULL WHERE id = %s",
                      (yol, mime, boyut, sha256, id_))

    def gelen_dosya_hatasi(self, id_: int, hata: str) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("UPDATE gelen_dosyalar SET deneme = deneme + 1, hata = %s WHERE id = %s", (hata[:300], id_))

    def gelen_dosya(self, id_: int) -> dict | None:
        with self.baglan() as c:
            return c.execute("SELECT d.*, m.gonderen FROM gelen_dosyalar d JOIN mesajlar m ON m.id = d.mesaj_id WHERE d.id = %s", (id_,)).fetchone()

    # ───────────────────────── İE-06: panel sorguları ─────────────────────────
    def konusma_listesi(self, en_fazla: int = 200) -> list[dict]:
        """Gelen kutusu: gönderen başına son mesaj, sayı ve (varsa) bayi kartı; yeniden eskiye."""
        with self.baglan() as c:
            return c.execute(
                "SELECT g.gonderen, g.n, extract(epoch FROM g.son)::float8 AS son, s.metin AS son_metin, s.tur AS son_tur, s.sahiplenildi, "
                "b.ad, b.kod, b.rol, b.firma, b.aktif FROM (SELECT gonderen, count(*) AS n, max(wa_zamani) AS son FROM mesajlar GROUP BY gonderen) g "
                "LEFT JOIN LATERAL (SELECT metin, tur, sahiplenildi FROM mesajlar WHERE gonderen = g.gonderen ORDER BY wa_zamani DESC, alindi DESC LIMIT 1) s ON true "
                "LEFT JOIN bayiler b ON b.numara = g.gonderen ORDER BY g.son DESC LIMIT %s", (en_fazla,)).fetchall()

    def konusma_mesajlari(self, numara: str, en_fazla: int = 300) -> list[dict]:
        """Bir numaranın gelen ve giden mesajları, zaman sırasıyla (giden: durum ve teslim durumu ile)."""
        with self.baglan() as c:
            return c.execute(
                "SELECT * FROM ("
                " SELECT 'gelen' AS yon, id, tur AS kind, metin AS govde, extract(epoch FROM wa_zamani)::float8 AS zaman, NULL::text AS durum, "
                "        NULL::text AS teslim, sahiplenildi, ham->>'reply_id' AS reply_id, NULL::text AS dosya_adi FROM mesajlar WHERE gonderen = %s "
                " UNION ALL "
                " SELECT 'giden', id, kind, govde, extract(epoch FROM olusturuldu)::float8, durum, teslim_durumu, true, NULL, (satir->>'filename') "
                "        FROM giden WHERE alici = %s OR alici_cozuldu = %s"
                ") x ORDER BY zaman DESC, id LIMIT %s", (numara, numara, numara, en_fazla)).fetchall()[::-1]

    def gelen_dosyalari(self, numara: str) -> list[dict]:
        with self.baglan() as c:
            return c.execute("SELECT d.id, d.mesaj_id, d.dosya_adi, d.mime, d.boyut, d.yol IS NOT NULL AS indirildi, d.hata, "
                             "extract(epoch FROM d.olusturuldu)::float8 AS zaman FROM gelen_dosyalar d JOIN mesajlar m ON m.id = d.mesaj_id "
                             "WHERE m.gonderen = %s ORDER BY d.olusturuldu DESC", (numara,)).fetchall()

    def panel_giris_kaydet(self, sonuc: str, ip_ozeti: str | None) -> None:
        with self.baglan() as c, c.transaction():
            c.execute("INSERT INTO panel_girisler (sonuc, ip_ozeti) VALUES (%s, %s)", (sonuc, ip_ozeti))

    def panel_basarisiz_sayisi(self, dakika: int = 15, ip_ozeti: str | None = None) -> int:
        """Son 'dakika' dakikadaki başarısız girişler (ip_ozeti verilirse yalnız o IP'den)."""
        with self.baglan() as c:
            return c.execute("SELECT count(*) AS n FROM panel_girisler WHERE sonuc = 'basarisiz' AND zaman > now() - make_interval(mins => %s) "
                             "AND (%s::text IS NULL OR ip_ozeti = %s)", (dakika, ip_ozeti, ip_ozeti)).fetchone()["n"]

    def sayimlar(self) -> dict:
        """/saglik ve durum.sh için sayılar (numara ve metin yok)."""
        with self.baglan() as c:
            return c.execute(
                "SELECT (SELECT count(*) FROM isler WHERE durum IN ('sirada', 'isleniyor')) AS acik_is, "
                "(SELECT count(*) FROM giden WHERE durum = 'bekliyor') AS bekleyen_giden, "
                "(SELECT count(*) FROM giden WHERE durum = 'belirsiz' AND olusturuldu > now() - interval '24 hours') AS belirsiz_24s, "
                "(SELECT count(*) FROM giden WHERE durum = 'gonderilmedi' AND olusturuldu > now() - interval '24 hours') AS gonderilmedi_24s, "
                "(SELECT count(*) FROM mesajlar WHERE alindi > now() - interval '24 hours') AS gelen_24s, "
                "(SELECT count(*) FROM gelen_dosyalar WHERE yol IS NULL AND deneme < 3) AS bekleyen_medya, "
                "(SELECT count(*) FROM bayiler WHERE aktif) AS aktif_bayi").fetchone()
