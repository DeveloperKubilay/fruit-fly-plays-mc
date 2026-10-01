#!/usr/bin/env bash
# DrosophilaBee Linux/macOS Build Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# 1. Maven yüklüyse doğrudan Maven ile derle
if command -v mvn >/dev/null 2>&1; then
    echo "[Build] Maven bulundu, derleme başlatılıyor..."
    mvn clean package
    echo "[Build] Başarılı! Çıktı: target/DrosophilaBee.jar"
    exit 0
fi

# 2. Maven yoksa bağımsız javac ile derle
echo "[Build] Maven bulunamadı, JDK (javac/jar) ile doğrudan derleniyor..."

if ! command -v javac >/dev/null 2>&1 || ! command -v jar >/dev/null 2>&1; then
    echo "[Hata] javac veya jar bulunamadı! Lütfen JDK 17+ kurun (ör: sudo apt install openjdk-17-jdk)"
    exit 1
fi

mkdir -p lib target build/classes
rm -rf build/classes/* target/*

WS_JAR="lib/Java-WebSocket-1.5.7.jar"
if [ ! -f "$WS_JAR" ]; then
    echo "[Build] Java-WebSocket indiriliyor..."
    curl -sL -o "$WS_JAR" "https://repo1.maven.org/maven2/org/java-websocket/Java-WebSocket/1.5.7/Java-WebSocket-1.5.7.jar"
fi

SPIGOT_JAR="lib/spigot-api.jar"
if [ ! -f "$SPIGOT_JAR" ]; then
    echo "[Build] Spigot API indiriliyor..."
    curl -sL -o "$SPIGOT_JAR" "https://hub.spigotmc.org/nexus/content/repositories/snapshots/org/spigotmc/spigot-api/26.1-R0.1-SNAPSHOT/spigot-api-26.1-R0.1-20260329.091546-5.jar"
fi

CP_SEP=":"
if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32"* ]]; then
    CP_SEP=";"
fi

JAVA_FILES=$(find src/main/java -name "*.java")
echo "[Build] Java sınıfları derleniyor..."
javac -encoding UTF-8 -cp "$SPIGOT_JAR${CP_SEP}$WS_JAR" -d build/classes --release 17 $JAVA_FILES

echo "[Build] Kaynak dosyaları kopyalanıyor..."
cp -r src/main/resources/* build/classes/

echo "[Build] Java-WebSocket kütüphanesi ekleniyor (fat jar)..."
(cd build/classes && jar -xf "../../$WS_JAR" && rm -rf META-INF/maven* META-INF/MANIFEST.MF)

echo "[Build] JAR paketleniyor..."
jar --create --file target/DrosophilaBee.jar -C build/classes .

echo "========================================="
echo "BAŞARILI: target/DrosophilaBee.jar oluşturuldu!"
ls -lh target/DrosophilaBee.jar
echo "========================================="
