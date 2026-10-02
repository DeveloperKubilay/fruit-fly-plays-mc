#!/usr/bin/env bash
# Drosophila Meyve Sineği Başlatıcı / Runner

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "[HATA / ERROR] venv bulunamadı! Lütfen önce ./setup.sh çalıştırın."
    exit 1
fi

source venv/bin/activate

# .env dosyası varsa yükle
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Hedef Minecraft sunucu adresi (Varsayılan: localhost)
# Sıralama: 1. Komut satırı argümanı ($@) -> 2. MINECRAFT_HOST / TARGET env -> 3. localhost
if [ -n "$*" ]; then
    SERVER_ARGS=("$@")
elif [ -n "$MINECRAFT_HOST" ]; then
    SERVER_ARGS=("$MINECRAFT_HOST")
elif [ -n "$TARGET" ]; then
    SERVER_ARGS=("$TARGET")
elif [ -n "$SERVER_HOST" ]; then
    SERVER_ARGS=("$SERVER_HOST")
else
    SERVER_ARGS=("localhost")
fi

echo "================================================================"
echo "  Hedef Minecraft Sunucusu: ws://${SERVER_ARGS[0]}"
echo "================================================================"

exec python run_real.py --sessiz "${SERVER_ARGS[@]}"
