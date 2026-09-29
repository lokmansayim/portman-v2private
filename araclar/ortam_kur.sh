#!/usr/bin/env bash
# PORTMAN · yerel geliştirme ortamını tek komutla kurar (bulut çalışma alanı her oturumda boş başlar).
#
#   bash araclar/ortam_kur.sh              # sanal ortam + paketler + yerel Postgres + içe aktarma denetimi
#   bash araclar/ortam_kur.sh --dogrula    # ayrıca: harness, bütün testler, P6001 altın testi (gerileme)
#
# Yalnız bu makinede çalışır: ağ yalnız paket kurulumu için (pip, apt) kullanılır. Canlı sunucuya, LLM'e, WhatsApp'a
# bağlanmaz; hiçbir veri paylaşmaz. Depodaki dosyaları değiştirmez (harness'in yazdıklarını geri alır).
# Ayarlar: PORTMAN_VENV (varsayılan ~/.cache/portman-venv), PORTMAN_PG_PORT (55432), PORTMAN_PG_KOK (/home/pgtest/pg).
set -uo pipefail
KOK="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${PORTMAN_VENV:-$HOME/.cache/portman-venv}"
PORT="${PORTMAN_PG_PORT:-55432}"
PGK="${PORTMAN_PG_KOK:-/home/pgtest/pg}"
DOGRULA=0; [[ "${1:-}" == "--dogrula" ]] && DOGRULA=1
say() { printf '%s\n' "$*"; }

say "== Portman yerel ortam · $(date '+%Y-%m-%d %H:%M:%S')"

# 1) Python 3.11 ve sanal ortam
PY="$(command -v python3.11 || command -v python3)"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)' || { say "DUR: Python 3.11+ gerekli ($("$PY" --version))"; exit 1; }
[[ -x "$VENV/bin/python" ]] || "$PY" -m venv "$VENV" || { say "DUR: sanal ortam açılamadı: $VENV"; exit 1; }
"$VENV/bin/python" -m pip install -q --upgrade pip >/dev/null 2>&1
if ! "$VENV/bin/python" -m pip install -q -r "$KOK/araclar/gereksinimler.txt"; then
  say "DUR: paketler kurulamadı (ağ izni ya da sürüm). Hata yukarıda."; exit 1
fi
say "-- Python: $("$VENV/bin/python" --version) · $VENV"

# 2) Yerel Postgres 16 (kalıcı akış testleri için; yoksa o testler atlanır, geri kalan iş yürür)
PG_OK=0
PGBIN="$(ls -d /usr/lib/postgresql/16/bin 2>/dev/null || true)"
if [[ -z "$PGBIN" && "$(id -u)" == "0" ]] && command -v apt-get >/dev/null; then
  say "-- Postgres 16 yok; apt ile kuruluyor"
  (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql-16) >/dev/null 2>&1 || true
  PGBIN="$(ls -d /usr/lib/postgresql/16/bin 2>/dev/null || true)"
fi
if [[ -z "$PGBIN" ]]; then
  say "-- UYARI: Postgres 16 kurulamadı; kalıcı akış testleri atlanacak."
else
  if [[ "$(id -u)" == "0" ]]; then
    id pgtest >/dev/null 2>&1 || useradd -m -s /bin/bash pgtest
    ASPG=(su pgtest -c)
  else
    ASPG=(bash -c)
  fi
  mkdir -p "$PGK" 2>/dev/null; [[ "$(id -u)" == "0" ]] && chown -R pgtest:pgtest "$PGK"
  if [[ ! -f "$PGK/data/PG_VERSION" ]]; then
    "${ASPG[@]}" "$PGBIN/initdb -D '$PGK/data' -U postgres --auth=trust -E UTF8 --locale=C.UTF-8" >/dev/null || say "-- UYARI: initdb başarısız"
  fi
  if ! "${ASPG[@]}" "$PGBIN/pg_ctl -D '$PGK/data' status" >/dev/null 2>&1; then
    "${ASPG[@]}" "setsid $PGBIN/pg_ctl -D '$PGK/data' -o '-p $PORT -k $PGK -c listen_addresses=127.0.0.1' -l '$PGK/log.txt' -w start" </dev/null >/dev/null 2>&1 \
      || say "-- UYARI: Postgres başlatılamadı (günlük: $PGK/log.txt)"
  fi
  if "$VENV/bin/python" -c "import psycopg; psycopg.connect('host=127.0.0.1 port=$PORT user=postgres dbname=postgres', connect_timeout=5).close()" 2>/dev/null; then
    PG_OK=1; say "-- Postgres 16: 127.0.0.1:$PORT (yalnız yerel; güven kipi yalnız bu test sunucusunda)"
  else
    say "-- UYARI: Postgres'e bağlanılamadı; kalıcı akış testleri atlanacak."
  fi
fi

# 3) İçe aktarma denetimi
cd "$KOK" || exit 1
"$VENV/bin/python" - <<'PY' || { say "DUR: içe aktarma başarısız"; exit 1; }
import ezdxf, fitz, ifcopenshell, matplotlib, psycopg, pydantic, shapely
import beyin.karar, motor.cikarici, motor.dxf_out
print(f"-- içe aktarma: ezdxf {ezdxf.__version__} · ifcopenshell {ifcopenshell.version} · psycopg {psycopg.__version__} · beyin, motor tamam")
PY

# 4) İsteğe bağlı doğrulama (gerileme)
if [[ $DOGRULA == 1 ]]; then
  if [[ -n "$(git status --porcelain beyin/testler)" ]]; then
    say "-- harness atlandı: beyin/testler'de kaydedilmemiş değişiklik var (üzerine yazmamak için)"
  else
    once="$(git ls-files --others --exclude-standard beyin/testler)"
    "$VENV/bin/python" -m beyin.harness 2>&1 | tail -1 | sed 's/^/-- harness: /'
    git checkout -q -- beyin/testler/
    comm -13 <(printf '%s\n' "$once" | sort) <(git ls-files --others --exclude-standard beyin/testler | sort) | while read -r f; do [[ -n "$f" ]] && rm -f -- "$f"; done
  fi
  # Bilinen (30.09): sır taraması vps/kapi_d_dogrula.sh:25'i işaretler. Yanlış pozitif: rolün parolası olup olmadığını
  # (rolpassword IS NOT NULL) yazdıran SQL satırı; dosyada sır yok. Bu yüzden "sir_taramasi FARKLI · beklenmeyen 1" ve
  # "2 kontrolde fark" beklenir; öteki satırlar AYNI olmalı.
  "$VENV/bin/python" testler/referans/dogrula.py 2>&1 | grep -E "FARKLI|SONUÇ|parmak izleri" | sed 's/^/-- referans: /'
  if [[ $PG_OK == 1 ]]; then export PORTMAN_TEST_PG="host=127.0.0.1 port=$PORT user=postgres"; fi
  "$VENV/bin/python" -m pytest -q -p no:cacheprovider testler 2>&1 | grep -E "passed|failed|error" | tail -1 | sed 's/^/-- testler: /'
fi

say ""
say "Hazır. Bu kabukta kullanmak için:"
say "  source $VENV/bin/activate"
[[ $PG_OK == 1 ]] && say "  export PORTMAN_TEST_PG=\"host=127.0.0.1 port=$PORT user=postgres\""
say "Aday karşılaştırması: python deneme/2026-09-30_asama2/kos.py --cikti <klasör>"
