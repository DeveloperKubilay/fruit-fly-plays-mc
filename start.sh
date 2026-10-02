#!/usr/bin/env bash
# Drosophila Meyve Sineği Başlatıcı / Runner

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "[HATA / ERROR] venv bulunamadı! Lütfen önce ./setup.sh çalıştırın."
    exit 1
fi

source venv/bin/activate

# Hedef Minecraft sunucu adresi (Parametre yoksa TARGET değişkeni veya localhost)
# Kullanım:
#   ./start.sh                  -> localhost:8765
#   ./start.sh 192.168.1.105    -> Belirtilen IP
#   ./start.sh 192.168.1.105:8766
if [ -n "$*" ]; then
    SERVER_ARGS=("$@")
elif [ -n "$TARGET" ]; then
    SERVER_ARGS=("$TARGET")
else
    SERVER_ARGS=("localhost")
fi

echo "================================================================"
echo "  Hedef Minecraft Sunucusu: ws://${SERVER_ARGS[0]}"
echo "================================================================"

exec python run_real.py --sessiz "${SERVER_ARGS[@]}"
