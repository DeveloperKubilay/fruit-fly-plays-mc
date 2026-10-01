#!/usr/bin/env bash
# Drosophila Meyve Sineği Başlatıcı / Runner

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "[HATA / ERROR] venv bulunamadı! Lütfen önce ./setup.sh çalıştırın."
    exit 1
fi

source venv/bin/activate

# Sunucuda varsayılan olarak sessiz/ekransız modda başlar (--sessiz)
# GUI veya ses istenirse ek argümanlar parametre olarak iletilebilir
exec python run_real.py --sessiz "$@"
