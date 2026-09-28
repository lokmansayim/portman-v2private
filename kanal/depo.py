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
                 "model_veya_olcu": ("katalog_kodu", "dis_olcu", "pano"), "pencere_olcu": ("pencereler",), "pencere_mahal": ("pencereler",)}


def _cevap_mi(alan: str, d_eski: dict, d_yeni: dict, sonuc: dict, ozet: dict) -> bool:
    """Kapanan soru bu mesajla mı cevaplandı (değilse düştü)? D-01 ve B1 soruları kural katmanının notundan; eksik bilgi
    soruları, sorulan alanın bu mesajla dolup dolmadığından okunur. İptal cevap sayılmaz."""
    if alan == ESKI_TASLAK_SORUSU:
        return bool(ozet.get("d01_cevap"))
    if alan == "pencere_islem":
        return bool(ozet.get("pencere_cevap"))
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

    def acik_is_sayisi(self) -> int:
        with self.baglan() as c:
            return c.execute("SELECT count(*) AS n FROM isler WHERE durum IN ('sirada', 'isleniyor')").fetchone()["n"]

    def mesaj_durumu(self, mesaj_id: str) -> dict | None:
        """Bir gelen mesajın işi ve hosting'e devredilmemiş giden satır sayısı (tekrar gelen kanal mesajı için)."""
        with self.baglan() as c:
            return c.execute("SELECT j.id AS is_id, j.durum AS is_durum, (SELECT count(*) FROM giden g WHERE g.is_id = j.id "
                             "AND g.durum = 'bekliyor') AS bekleyen_giden FROM isler j WHERE j.mesaj_id = %s", (mesaj_id,)).fetchone()

    # ───────────────────────── gelen ─────────────────────────
    def mesaj_kaydet(self, gelen: dict) -> bool:
        """Kuyruk satırını (feature.php biçimi) mesaj ve iş olarak yazar. Yeni ise True; aynı kimlik daha önce geldiyse
        hiçbir şey değişmez ve False döner."""
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
                "INSERT INTO mesajlar (id, gonderen, bayi_kod, tur, metin, alinti_id, wa_zamani, ham) "
                "VALUES (%s, %s, %s, %s, %s, %s, to_timestamp(%s), %s) ON CONFLICT (id) DO NOTHING RETURNING id",
                (mid, str(gelen["sender"]), (bayi or {}).get("kod") if isinstance(bayi, dict) else None, gelen.get("type") or "text",
                 gelen.get("text") or "", gelen.get("context_id"), _zaman(gelen.get("timestamp")), Jsonb(gelen))).fetchone()
            if r is None:
                return False
            c.execute("INSERT INTO isler (mesaj_id, gonderen) VALUES (%s, %s)", (mid, str(gelen["sender"])))
            return True

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
                revizyon_id = c.execute(
                    "INSERT INTO revizyonlar (proje_id, rev, is_emri_no, gonderen, bayi_kod, kaynak_mesaj_id, is_emri, pdf_yolu, pdf_sha256, "
                    "dxf_sha256, dogrulandi, durum) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (proje_id, rev, sonuc["is_emri_no"], gelen["sender"], bayi_kod, gelen["id"], Jsonb(ie), cizim.get("pdf"),
                     cizim.get("pdf_sha256"), cizim.get("dxf_sha256"), gecti, "onay_bekliyor" if gecti else "dogrulanmadi")).fetchone()["id"]
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
            for s in cikti.get("satirlar") or []:
                c.execute(
                    "INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, dosya, sha256, revizyon_id, satir) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (s["id"], j["id"], gelen["id"], s["seq"], s["to"], s.get("tur") or "cevap", s.get("kind") or "text", s.get("body") or "",
                     s.get("file"), s.get("sha256"), revizyon_id if s.get("kind") == "document" else None, Jsonb(s)))
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

    @staticmethod
    def _gecerlilik(d: dict, alan: str):
        if alan == ESKI_TASLAK_SORUSU and d.get("bekleyen_zamani"):
            import datetime
            return datetime.datetime.fromtimestamp(int(d["bekleyen_zamani"]) + ESKI_SORU_SN, tz=datetime.timezone.utc)
        return None

    # ───────────────────────── revizyon onayı için ─────────────────────────
    def revizyon_iletimi(self, gonderen: str, is_emri_no: str, rev: int) -> dict | None:
        """Revizyonun PDF satırı: {"id", "rev", "durum", "pdf_durum", "pdf_wamid", "kabul", "teslim_durumu", "teslim"}.
        kabul: WhatsApp API'nin gönderimi kabul ettiği an; teslim: Meta bildirimindeki ilk 'delivered'/'read' anı. Kayıt yoksa None."""
        with self.baglan() as c:
            return c.execute(
                "SELECT r.id, r.rev, r.durum, g.durum AS pdf_durum, g.dis_id AS pdf_wamid, extract(epoch FROM g.kabul_zamani) AS kabul, "
                "g.teslim_durumu, extract(epoch FROM g.teslim_zamani) AS teslim "
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
            c.execute("UPDATE giden SET durum = 'gonderiliyor', deneme = deneme + 1, gonderim_basladi = now() WHERE id = %s", (r["id"],))
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

    def teslim_bildir(self, satir_id_: str, teslim_durumu: str, teslim_zamani: float | None = None) -> None:
        """Meta'nın imzalı durum bildirimi (hosting'ten okunur): sent / delivered / read / failed. Durum yalnız ileri gider;
        teslim_zamani ilk 'delivered' ya da 'read' anıdır."""
        sira = self._TESLIM_SIRASI
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
    def teslim_bekleyen_isler(self, en_fazla: int = 20) -> list[int]:
        """Bitmiş (ya da başarısız) ve satırları henüz hosting'e devredilmemiş işler, eskiden yeniye."""
        with self.baglan() as c:
            return [r["is_id"] for r in c.execute(
                "SELECT g.is_id FROM giden g JOIN isler j ON j.id = g.is_id WHERE g.durum = 'bekliyor' AND j.durum IN ('bitti', 'basarisiz') "
                "GROUP BY g.is_id ORDER BY g.is_id LIMIT %s", (en_fazla,))]

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

    def esitlenecek_satirlar(self, en_fazla: int = 200, gun: int = 3) -> list[str]:
        """Hosting'e devredilmiş ve gönderim ya da teslim sonucu henüz bilinmeyen satırlar (son 'gun' gün)."""
        with self.baglan() as c:
            return [r["id"] for r in c.execute(
                "SELECT id FROM giden WHERE hostinge_verildi IS NOT NULL AND (durum = 'hostingte' OR (durum = 'kabul_edildi' "
                "AND teslim_zamani IS NULL AND coalesce(teslim_durumu, '') <> 'failed')) "
                "AND olusturuldu > now() - make_interval(days => %s) ORDER BY olusturuldu LIMIT %s", (gun, en_fazla))]

    def hosting_durumu_isle(self, satir_id_: str, st: dict) -> None:
        """api.php giden_durum'un bir satırı → Postgres. Hosting durumları (feature.php): pending/uploading/sending → sürüyor;
        accepted/sent/delivered/read/failed (wamid'li) → API kabul etti (+ Meta teslim durumu); uncertain → belirsiz;
        held ya da tükenmiş upload_failed → gönderilmedi."""
        durum = st.get("state")
        if durum in ("accepted", "sent", "delivered", "read", "failed") and st.get("wamid"):
            self.gonderim_sonucu(satir_id_, "kabul_edildi", dis_id=st["wamid"], kabul_zamani=st.get("request_accepted_at"))
            if st.get("delivery_state"):
                self.teslim_bildir(satir_id_, st["delivery_state"], st.get("delivered_at"))
        elif durum == "uncertain":
            self.gonderim_sonucu(satir_id_, "belirsiz", hata=str(st.get("error") or "hosting: gönderim sonucu belirsiz")[:300])
        elif durum == "held" or (durum == "upload_failed" and int(st.get("attempts") or 0) >= 2):
            self.gonderim_sonucu(satir_id_, "gonderilmedi", hata=str(st.get("error") or f"hosting: {durum}")[:300])
