#!/usr/bin/env bash
set -e

# Renkler / Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_color() {
    printf "%b\n" "$1"
}

echo_color "${CYAN}================================================================${NC}"
echo_color "${CYAN}  🪰 Drosophila — Meyve Sineği Beyin Simülasyonu Kurulumu        ${NC}"
echo_color "${CYAN}  🧠 MaleCNS v1.0 Connectome Simulation Setup                   ${NC}"
echo_color "${CYAN}================================================================${NC}"

# 1. Python kontrolü
if ! command -v python3 >/dev/null 2>&1; then
    echo_color "${RED}[HATA / ERROR] python3 bulunamadı! Lütfen kurun: sudo apt install python3${NC}"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo_color "${GREEN}[OK] Python sürümü: $PY_VER${NC}"

# 2. Virtual Environment (venv) Kurulumu
if [ ! -d "venv" ]; then
    echo_color "${CYAN}[1/3] Python sanal ortamı (venv) oluşturuluyor...${NC}"
    if ! python3 -m venv venv 2>/dev/null; then
        echo_color "${YELLOW}[UYARI] python3-venv eksik olabilir. Kuruluyor...${NC}"
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y python3-venv python3-pip
        fi
        python3 -m venv venv
    fi
else
    echo_color "${GREEN}[OK] venv zaten mevcut.${NC}"
fi

# 3. Bağımlılıkların Kurulumu
echo_color "${CYAN}[2/3] Bağımlılıklar yükleniyor (requirements.txt)...${NC}"
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo_color "${GREEN}[OK] Bağımlılıklar başarıyla yüklendi.${NC}"

# 4. Model / Konektom Verisi Kontrolü
echo_color "${CYAN}[3/3] Konektom modeli kontrol ediliyor...${NC}"
mkdir -p connectome

GRAPH_FILE="connectome/malecns_behavior.W.npz"

if [ -f "$GRAPH_FILE" ]; then
    echo_color "${GREEN}[OK] Hazır davranış grafiği bulundu (19 MB). Ek indirme gerekmez!${NC}"
else
    echo_color "${YELLOW}[BİLGİ] Davranış alt-grafiği bulunamadı. Ham konektom verisi (~1.1 GB) indirilecek...${NC}"
    BASE_URL="https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"

    if [ ! -f "connectome/weights.feather" ]; then
        echo_color "${CYAN}  -> weights.feather (~1 GB) indiriliyor...${NC}"
        curl -L -o "connectome/weights.feather" "$BASE_URL/connectome-weights-male-cns-v1.0-minconf-0.5.feather"
    fi

    if [ ! -f "connectome/annotations.feather" ]; then
        echo_color "${CYAN}  -> annotations.feather (~14 MB) indiriliyor...${NC}"
        curl -L -o "connectome/annotations.feather" "$BASE_URL/body-annotations-male-cns-v1.0-minconf-0.5.feather"
    fi

    if [ ! -f "connectome/neurotransmitters.feather" ]; then
        echo_color "${CYAN}  -> neurotransmitters.feather (~41 MB) indiriliyor...${NC}"
        curl -L -o "connectome/neurotransmitters.feather" "$BASE_URL/body-neurotransmitters-male-cns-v1.0.feather"
    fi

    echo_color "${CYAN}  -> Davranış alt-grafiği derleniyor (1-2 dakika sürer)...${NC}"
    python connectome_loader.py
    echo_color "${GREEN}[OK] Davranış grafiği başarıyla derlendi!${NC}"
fi

# 5. Bağlantı ve Güvenlik Yapılandırması
echo_color ""
echo_color "${CYAN}================================================================${NC}"
echo_color "${CYAN}  [4/4] BAĞLANTI VE GÜVENLİK AYARLARI / CONFIGURATION           ${NC}"
echo_color "${CYAN}================================================================${NC}"
echo_color "Minecraft Sunucu Adresi (IP veya IP:Port):"
echo_color "  - Başka bir sunucuya bağlamak istiyorsanız IP veya IP:Port yazın (örn: 1.2.3.4 veya 1.2.3.4:8765)."
echo_color "  - Yerel sunucu için doğrudan [ENTER]'a basın (varsayılan: localhost)."
read -r -p "Sunucu IP [localhost]: " INPUT_HOST
[ -z "$INPUT_HOST" ] && INPUT_HOST="localhost"

INPUT_PORT="8765"
if [[ "$INPUT_HOST" == *":"* ]]; then
    INPUT_PORT="${INPUT_HOST##*:}"
    INPUT_HOST="${INPUT_HOST%:*}"
fi

while true; do
    echo_color ""
    echo_color "Minecraft Güvenlik Şifresi / Token (ZORUNLU):"
    echo_color "(Minecraft sunucusundaki plugins/DrosophilaBee/config.yml dosyasındaki"
    echo_color " brain.auth-token değeri ile birebir aynı olmalıdır)"
    read -r -p "Şifre / Token: " INPUT_PASS
    if [ -n "$INPUT_PASS" ]; then
        break
    fi
    echo_color "${RED}[UYARI / WARNING] Şifre zorunludur, boş bırakılamaz!${NC}"
done

echo_color "${CYAN}[BİLGİ] Ayarlar config.json ve .env dosyalarına kaydediliyor...${NC}"

cat <<EOF > config.json
{
  "minecraft_host": "${INPUT_HOST}",
  "minecraft_port": ${INPUT_PORT},
  "auth_token": "${INPUT_PASS}"
}
EOF

cat <<EOF > .env
# Drosophila Otomatik Yapılandırma
MINECRAFT_HOST=${INPUT_HOST}
MINECRAFT_PORT=${INPUT_PORT}
MINECRAFT_PASSWORD=${INPUT_PASS}
FLY_AUTH_TOKEN=${INPUT_PASS}
EOF

echo_color "${GREEN}[OK] Yapılandırma başarıyla kaydedildi! (config.json, .env)${NC}"

# 6. Başlatıcı izinleri
chmod +x start.sh 2>/dev/null || true

echo_color "${CYAN}================================================================${NC}"
echo_color "${GREEN}  KURULUM TAMAMLANDI / SETUP COMPLETED!${NC}"
echo_color "  Çalıştırma Seçenekleri / Run Options:"
echo_color ""
echo_color "  1. Kayıtlı Ayarlarla Başlatma (Grafik Arayüz / GUI):"
echo_color "     ${YELLOW}./start.sh${NC}"
echo_color ""
echo_color "  2. Sadece Terminal Modu (GUI Yok, Düşük Kaynak Kullanımı):"
echo_color "     ${YELLOW}./start.sh --no-gui${NC}"
echo_color ""
echo_color "  3. Özel IP veya IP:Port ve Şifre ile Başlatma:"
echo_color "     ${YELLOW}./start.sh 1.2.3.4${NC}"
echo_color "     ${YELLOW}./start.sh 1.2.3.4:8765${NC}"
echo_color "     ${YELLOW}./start.sh 1.2.3.4:8765 mypassword${NC}"
echo_color "     ${YELLOW}./start.sh 1.2.3.4:8765 mypassword --no-gui${NC}"
echo_color "     ${YELLOW}./start.sh 1.2.3.4 mypassword --no-gui${NC}"
echo_color "${CYAN}================================================================${NC}"
