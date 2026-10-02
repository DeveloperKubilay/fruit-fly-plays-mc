#!/usr/bin/env bash
# Drosophila Meyve Sineği Başlatıcı / Runner

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "[HATA / ERROR] venv bulunamadı! Lütfen önce ./setup.sh çalıştırın."
    exit 1
fi

source venv/bin/activate

# 1. config.json veya .env yükle
CFG_HOST=""
CFG_PORT=8765
CFG_PASS=""

if [ -f "config.json" ]; then
    CFG_HOST=$(grep -o '"minecraft_host"[^,]*' config.json 2>/dev/null | cut -d'"' -f4)
    CFG_PASS=$(grep -o '"auth_token"[^,]*' config.json 2>/dev/null | cut -d'"' -f4)
    [ -z "$CFG_PASS" ] && CFG_PASS=$(grep -o '"password"[^,]*' config.json 2>/dev/null | cut -d'"' -f4)
    P_TMP=$(grep -o '"minecraft_port"[^,}]*' config.json 2>/dev/null | tr -dc '0-9')
    [ -n "$P_TMP" ] && CFG_PORT="$P_TMP"
fi

if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    [ -z "$CFG_HOST" ] && CFG_HOST="$MINECRAFT_HOST"
    [ -z "$CFG_PASS" ] && CFG_PASS="${MINECRAFT_PASSWORD:-${FLY_AUTH_TOKEN:-${PASSWORD:-${AUTH_TOKEN}}}}"
    [ -n "$MINECRAFT_PORT" ] && CFG_PORT="$MINECRAFT_PORT"
fi

# 2. Komut satırı argümanlarını ayrıştır: [IP veya IP:PORT] [PASSWORD] [--no-gui]
ARG_HOST=""
ARG_PASS=""
NO_GUI=""

for arg in "$@"; do
    case "$arg" in
        --no-gui|--nogui|--headless)
            NO_GUI="--no-gui"
            ;;
        *)
            if [ -z "$ARG_HOST" ]; then
                ARG_HOST="$arg"
            elif [ -z "$ARG_PASS" ]; then
                ARG_PASS="$arg"
            fi
            ;;
    esac
done

TARGET_HOST="$ARG_HOST"
[ -z "$TARGET_HOST" ] && TARGET_HOST="$CFG_HOST"
[ -z "$TARGET_HOST" ] && TARGET_HOST="${TARGET:-localhost}"

# IP:PORT ayrıştırma desteği (örn: 1.2.3.4:8765 veya localhost:8765)
if [[ "$TARGET_HOST" == *":"* ]]; then
    CFG_PORT="${TARGET_HOST##*:}"
    TARGET_HOST="${TARGET_HOST%:*}"
fi

TARGET_PASS="$ARG_PASS"
[ -z "$TARGET_PASS" ] && TARGET_PASS="$CFG_PASS"
[ -z "$TARGET_PASS" ] && TARGET_PASS="${FLY_AUTH_TOKEN:-$MINECRAFT_PASSWORD}"

if [ -z "$TARGET_PASS" ]; then
    echo "================================================================"
    echo "  GÜVENLİK ŞİFRESİ GEREKLİ / PASSWORD REQUIRED"
    echo "================================================================"
    echo "Minecraft sunucusundaki brain.auth-token ile eşleşen şifreyi girin:"
    read -r -p "Şifre / Token: " TARGET_PASS
    echo
fi

export FLY_AUTH_TOKEN="$TARGET_PASS"
export MINECRAFT_PASSWORD="$TARGET_PASS"

echo "================================================================"
echo "  Hedef Minecraft Sunucusu: ws://${TARGET_HOST}:${CFG_PORT}"
if [ -n "$NO_GUI" ]; then
    echo "  Arayüz: Sadece Terminal Modu (--no-gui)"
else
    echo "  Arayüz: Grafik Dashboard (Pygame)"
fi
echo "================================================================"

exec python run_real.py "${TARGET_HOST}:${CFG_PORT}" --token "$TARGET_PASS" $NO_GUI --sessiz
