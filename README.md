# 🪰 Drosophila — Gerçek Meyve Sineği Beyni Minecraft'ta

13.000+ nöronluk **MaleCNS v1.0** konektomu (Janelia/Cambridge/MRC LMB/Google) üzerinde
çalışan Leaky Integrate-and-Fire (LIF) simülasyonu. Minecraft'ta bir arı (Bee) olarak yaşar;
görme, koku, ses, rüzgâr, ısı ve tat duyularıyla dünyayı algılar.

---

## Proje Yapısı

```
Drosophila/
├── connectome/                  # Konektom verisi (~1.1 GB, git'te YOK)
│   ├── weights.feather          # Sinaptik ağırlıklar (1 GB)
│   ├── annotations.feather      # Nöron bilgileri (14 MB)
│   ├── neurotransmitters.feather # Nörotransmitter tipleri (41 MB)
│   └── malecns_behavior.*       # Derlenmiş davranış alt-grafiği (önbellek)
│
├── drosophila-paper/            # Minecraft Paper/Spigot eklentisi (Java 17)
│   ├── src/main/java/org/drosophila/
│   │   ├── DrosophilaPlugin.java          # Ana eklenti + komutlar
│   │   ├── controller/BeeController.java  # Arı bedeni, motor, uçuş fiziği
│   │   ├── network/BrainServer.java       # WebSocket sunucusu (Python beyin bağlantısı)
│   │   ├── vision/CompoundEyeRaytracer.java # 1536 ommatidium petek göz
│   │   ├── olfaction/OdorDiffusion.java   # Koku yayılımı + yiyecek tespiti
│   │   ├── auditory/AuditoryWindSampler.java # Johnston organı (ses + rüzgâr)
│   │   ├── item/BottleManager.java        # Şişe yakalama sistemi
│   │   └── i18n/LanguageManager.java      # Çoklu dil (i18n) yöneticisi
│   ├── src/main/resources/
│   │   ├── config.yml                     # ← ANA KONFİGÜRASYON
│   │   ├── plugin.yml                     # Eklenti manifest
│   │   └── languages/                     # Dil paketleri (messages_en.yml, messages_tr.yml)
│   ├── lib/spigot-api.jar                 # Spigot API (derleme bağımlılığı)
│   └── build.ps1                          # Derleme scripti (PowerShell)
│
├── fly_brain_real.py            # 🧠 MaleCNS LIF beyin simülasyonu
├── minecraft_real_bridge.py     # 🌉 WebSocket köprüsü + pygame dashboard
├── connectome_loader.py         # Konektom verisi yükleyici / alt-grafik çıkarıcı
├── fly_log.py                   # Nöral aktivite loglama
├── fly_sound.py                 # Kanat sesi simülasyonu (WingBeat)
├── run_real.py                  # ▶️ ANA ÇALIŞTIRICI (her şeyi başlatır)
├── setup.bat                    # 🪟 Windows otomatik kurulum betiği
├── start.bat                    # 🪟 Windows başlatıcı (yerel veya uzak IP)
├── setup.sh                     # 🐧 Linux/macOS otomatik kurulum betiği
├── start.sh                     # 🐧 Linux/macOS başlatıcı (yerel veya uzak IP)
├── dogrula.py                   # Beyin doğrulama / test aracı
├── requirements.txt             # Python bağımlılıkları
└── .gitignore
```

---

## Kurulum

### 1. Gereksinimler

| Bileşen | Sürüm |
|---------|-------|
| Python | 3.10+ |
| Java JDK | 17+ |
| Minecraft Sunucu | Paper/Spigot 1.21+ |
| RAM (Python tarafı) | ~2 GB |
| Disk | ~1.5 GB (konektom verisi) |

### 2. Minecraft Eklentisi (Beden / WebSocket Sunucusu)

Minecraft sunucusu açıldığında `0.0.0.0:8765` üzerinde bir WebSocket sunucusu başlatır.
Herhangi bir IP ayarlaması yapmanıza gerek yoktur, tak-çalıştırdır!

```powershell
# Derleme (PowerShell, JDK 17 gerekli)
cd drosophila-paper
powershell -ExecutionPolicy Bypass -File .\build.ps1

# Çıktı: target/DrosophilaBee.jar
# Bu JAR'ı Minecraft sunucunun plugins/ klasörüne kopyala
cp target/DrosophilaBee.jar /path/to/server/plugins/

# Sunucuyu başlat veya yeniden yükle
```

### 3. Python Tarafı (Beyin / İstemci)

Simülasyon varsayılan olarak yerel sunucuya (`ws://localhost:8765`) bağlanır. Uzak sunucu IP'sini ister argüman olarak verebilir, isterseniz `.env` dosyasıyla modüler olarak tanımlayabilirsiniz.

#### Hızlı Başlatma (1-Tık Kurulum & Çalıştırma):

**Windows İçin:**
```cmd
# 1. Kurulum (venv, kütüphaneler ve konektom modelini otomatik hazırlar):
setup.bat

# 2. Çalıştırma (Varsayılan: localhost:8765):
start.bat

# Minecraft başka bir sunucudaysa (Uzak IP / Domain):
start.bat 1.2.3.4
# veya port ile:
start.bat 1.2.3.4:8765
```

**Linux / macOS İçin:**
```bash
# 1. Kurulum:
./setup.sh

# 2. Çalıştırma (Varsayılan: localhost:8765):
./start.sh

# Minecraft başka bir sunucudaysa (Uzak IP / Domain):
./start.sh 1.2.3.4
```

#### Modüler Ortam Değişkeni Desteği (`.env`):
Projeyi her defasında IP parametresi vermeden çalıştırmak için `.env.example` dosyasını `.env` olarak kopyalayabilirsiniz:
```ini
# .env dosyası
MINECRAFT_HOST=1.2.3.4
MINECRAFT_PORT=8765
```

#### Manuel Çalıştırma (Geliştiriciler İçin):

```bash
# 1. Bağımlılıkları kur
pip install -r requirements.txt

# 2. Çalıştır (Varsayılan: ws://localhost:8765):
python run_real.py

# Uzak sunucuya bağlanma:
python run_real.py 1.2.3.4
python run_real.py 1.2.3.4:8765

# Sessiz mod (kanat vuruşu sesi kapalı):
python run_real.py --sessiz
```

İlk çalıştırmada `run_real.py`:
- `connectome/weights.feather` (~1 GB) yoksa [codex.flywire.ai](https://codex.flywire.ai) adresinden indirir
- `connectome/malecns_behavior.*` önbellek dosyalarını oluşturur (~18 MB)
- Kalibrasyon yapar (1-2 dakika)
- Minecraft sunucusuna bağlanarak beyin simülasyonunu başlatır

---

## Konfigürasyon (`config.yml`)

Sunucu ilk açılışta `plugins/DrosophilaBee/config.yml` oluşturur. Tüm parametreler ayrıntılı açıklamalarla belgelenmiştir:

```yaml
# Dil Ayarı ("en" İngilizce, "tr" Türkçe veya languages/ altındaki özel dil)
language: "en"

# Python Beyin WebSocket Sunucusu (0.0.0.0 üzerinde dinler)
brain:
  port: 8765                  # Dinlenecek WebSocket portu
  auth-token: "drosophila_secret_token_123"  # Güvenlik anahtarı
  smart-sleep:
    enabled: false            # Akıllı uyku modu (yakında oyuncu yoksa)
    player-distance: 48.0     # Oyuncu mesafe eşiği (blok)

# Sinek Ayarları
bee:
  auto-spawn: true            # Sunucu açılınca ve ölümde otomatik doğma
  display-name: ""            # Özel isim (boş bırakılırsa dil dosyası kullanılır)
  invulnerable: false         # Ölümsüzlük (God mode)
  speed-multiplier: 1.0       # Uçuş hızı çarpanı
  odor-range: 16.0            # Koku algılama menzili (blok)

# Görme Sistemi
vision:
  max-ray-range: 16.0         # 1536 ommatidium petek göz menzili (blok)
```

---

## Komutlar

Tüm komutlar OP yetkisi gerektirir. Alias: `/fruitfly` veya `/fluitfly`

| Komut | Açıklama |
|-------|----------|
| `/fruitfly help` | Komut listesi |
| `/fruitfly tp` | Sineğin yanına ışınlan |
| `/fruitfly come` | Sineği yanına çağır |
| `/fruitfly feed` | Önüne elma bırak |
| `/fruitfly feed full` | Anında doyur (Tokluk → 20) |
| `/fruitfly hungry` | Anında acıktır (Tokluk → 3) |
| `/fruitfly food [miktar]` | Tokluk seviyesi göster/ayarla |
| `/fruitfly spawnpoint` | Bulunduğun yeri kalıcı ev (spawnpoint) yap |
| `/fruitfly home` | Sineği evine gönder |
| `/fruitfly status` | Ayrıntılı telemetri (beyin, can, tokluk, koku, yön, tehdit) |
| `/fruitfly clear` | Beyin hafızasını sıfırla |

---

## Başka Sunucuya Taşıma

### Taşınacak Dosyalar

**Python tarafı** (beyin çalıştıracak makineye):
```
fly_brain_real.py          # Ana beyin
minecraft_real_bridge.py   # WebSocket köprü + dashboard
connectome_loader.py       # Konektom yükleyici
fly_log.py                 # Loglama
fly_sound.py               # Kanat sesi
run_real.py                # Çalıştırıcı
dogrula.py                 # Test aracı (opsiyonel)
requirements.txt           # pip bağımlılıkları
connectome/                # Konektom verisi klasörü (~1.1 GB)
```

**Minecraft sunucusuna**:
```
plugins/DrosophilaBee.jar  # Derlenmiş eklenti
```

### Adım Adım

1. `DrosophilaBee.jar`'ı Minecraft sunucunun `plugins/` klasörüne koy ve sunucuyu başlat (otomatik olarak 0.0.0.0:8765 portunda dinlemeye başlar).
2. Python makinesinde bağımlılıkları kur: `pip install -r requirements.txt`
3. Python beynini Minecraft sunucusuna bağla:
   - Aynı makinedeyse: `python run_real.py`
   - Uzak sunucudaysa: `python run_real.py <sunucu_ip_adresi>`
4. Minecraft eklentisi config dosyasında hiçbir IP ayarlaması yapmanıza gerek kalmaz!

> **Not:** `connectome/` klasörü ~1.1 GB. İlk `python run_real.py` çalıştırmasında otomatik
> indirilir, elle taşımana gerek yok (ama taşırsan daha hızlı başlar).

---

## Lisans

Konektom verisi: [MaleCNS v1.0](https://codex.flywire.ai/) — CC BY 4.0
(Janelia Research Campus / University of Cambridge / MRC LMB / Google)
