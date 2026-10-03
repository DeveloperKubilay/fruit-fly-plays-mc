# 🪰 Drosophila — Real Fruit Fly Brain in Minecraft

[![Minecraft](https://img.shields.io/badge/Minecraft-Paper%20%7C%20Bukkit%20%7C%20Spigot%20%7C%20Purpur%20(1.20--1.21.x)-brightgreen)](https://papermc.io)
[![Java](https://img.shields.io/badge/Java-17%2B-orange)](https://www.oracle.com/java/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Connectome](https://img.shields.io/badge/Connectome-MaleCNS%20v1.0%20(13k%2B%20neurons)-blueviolet)](https://codex.flywire.ai/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Our%20Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/TQHAm67DmX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An advanced neurobiological simulation that integrates the **real MaleCNS v1.0 biological fruit fly (*Drosophila melanogaster*) connectome**—electron-microscopy mapped neuron-by-neuron by the **Janelia Research Campus**, **University of Cambridge**, **MRC LMB**, and **Google Research** consortium, containing **13,000+ neurons** and **5,000,000+ synapses**—directly into Minecraft.

The simulation runs a Leaky Integrate-and-Fire (LIF) biophysical neural model. It commands a physical body (Bee) within Minecraft; seeing through 1,536-ommatidia compound eyes, smelling airborne odor molecules, hearing acoustic shocks and wind via Johnston's organ, and experiencing pain, taste, and hunger.

---

## 🌟 Vision and Philosophy

When examining existing connectome experiments and alternative projects, two common approaches emerge:

1. **Extreme Pruning and Dynamic Loss:** Some projects prune the ~1 GB biological dataset down to 20–22 MB. We believe a drastically amputated network can never exhibit genuine fruit fly neurodynamics or organic decision-making. Our goal is **to preserve the full biological connectome weights without structural compromise.**
2. **Artificial Task Forcing (Crypto Trading / Flying Airplanes):** Many try to force connectome models to fly airplanes or trade cryptocurrency using external reinforcement learning (RL). That is not biological intelligence—it is standard machine learning. Any generic artificial neural network can be trained on crypto. Forcing a fruit fly through artificial rewards and dopamine overrides destroys its biological authenticity.

> ### 🎯 Core Principle
> Our purpose is not to train the fly on artificial tasks. We provide authentic biological sensory inputs (1,536 compound eye raytracing, olfactory gradient diffusion, air currents, Johnston's organ acoustic shocks, nociception, and hunger) and **observe how an authentic 13,000-neuron connectome survives, navigates, and reacts organically in a Minecraft ecosystem without artificial interference.**

---

## 🏗️ Distributed Architecture

The project decouples the physical body from the biological brain through a high-performance distributed architecture:

```
[ Minecraft Server (Java) ]                      [ Biological Neural Engine (Python) ]
  Paper / Bukkit / Spigot / Purpur                 MaleCNS v1.0 LIF Simulation
  ├── 1,536 Ommatidia Compound Eye                 ├── 13,000+ Biological Neurons
  ├── Olfactory Diffusion (Fruits, Leaves)         ├── 5,000,000+ Synaptic Connections
  ├── Johnston's Organ (Sound & Wind)   ◀======▶   ├── Pygame Real-Time Telemetry Dashboard
  └── 3D Aerodynamics & Flight Motor   WebSocket   └── Smart Sleep / Power Management
      (Listens on 0.0.0.0:8765)                        (Connects as zero-config client)
```

* **Server Platform Support:** **Paper, Bukkit, Spigot, Purpur (1.20 - 1.21.x+)** are fully supported as plugins. No client-side mods (*Forge/Fabric*) required.
* **Decoupled Execution:** The neural engine can run locally on your machine or on an external server, connecting over WebSocket to your Minecraft server anywhere in the world.

---

## 💻 System Requirements

| Component | Requirement | Details |
|---|---|---|
| **Python** | 3.10 or newer | For the connectome LIF engine and telemetry bridge |
| **Java JDK** | 17 or newer | For the Minecraft server plugin |
| **Minecraft Server** | Paper / Bukkit / Spigot / Purpur 1.20 - 1.21.x+ | Server where FruitFly plugin runs |
| **RAM** | ~2 GB | Sufficient for the Python connectome simulation |
| **GPU** | **NOT REQUIRED!** | Simulation is heavily CPU-vectorized (NumPy/SciPy) |
| **Disk Space** | ~1.5 GB | For raw connectome data (~1.1 GB) and compiled behavior cache |

---

## 🚀 Installation & Quick Start

### 1. Download Release Files
From the [GitHub Releases](../../releases) page:
* For Minecraft server: **`FruitFly.jar`**
* For Python brain simulation: **`drosophila-brain-X.X.X.zip`** (Windows) or **`drosophila-brain-X.X.X.tar.gz`** (Linux/macOS)

---

### 2. Minecraft Server Setup (Body)
1. Place `FruitFly.jar` into your Minecraft server's `plugins/` directory.
2. Start the server or run `/reload`.
3. The plugin automatically starts a WebSocket listener on `0.0.0.0:8765`. Zero complex network configuration required on the server side!

---

### 3. Python Brain Setup (Brain)

#### 🪟 Windows:
```cmd
# Step 1: Run the automated wizard (creates venv, installs requirements, sets IP & token):
setup.bat

# Step 2: Launch:
start.bat
```

#### 🐧 Linux / macOS:
```bash
# Extract archive and navigate into directory:
tar -xzf drosophila-brain-*.tar.gz
cd drosophila-brain-*

# Grant permissions and run setup:
chmod +x setup.sh start.sh
./setup.sh

# Launch:
./start.sh
```

---

### ⚙️ Runner Options & Parameters

`setup.bat` (and `setup.sh`) prompts for your Minecraft server address (`localhost` or remote IP) and auth token on first run, saving them to `config.json` and `.env`.

You can also launch with custom arguments:

```cmd
# 1. Start with saved configuration (config.json / .env):
start.bat

# 2. Headless Terminal Mode (no Pygame GUI, minimal CPU usage for servers):
start.bat --no-gui

# 3. Specify custom IP or IP:Port (uses saved password):
start.bat 1.2.3.4
start.bat 1.2.3.4:8765

# 4. Specify custom IP:Port and password explicitly:
start.bat 1.2.3.4:8765 "mypassword"
start.bat 1.2.3.4:8765 "mypassword" --no-gui
```

*(Linux/macOS users can pass the same arguments to `./start.sh`).*

---

### 📄 Configuration Files & Environment Variables (`.env`)

You can configure connection parameters via `.env`:

```env
# ================================================================
# Drosophila Simulation - Environment Variables (.env)
# ================================================================

# Target Minecraft server address (default: localhost)
# Supports IP or IP:Port (e.g. 1.2.3.4:8765)
MINECRAFT_HOST=1.2.3.4

# Target WebSocket port (default: 8765)
MINECRAFT_PORT=8765

# Security Password / Auth Token (Must match brain.auth-token in plugins/FruitFly/config.yml)
MINECRAFT_PASSWORD=drosophila_secret_token_123
FLY_AUTH_TOKEN=drosophila_secret_token_123
```

Or via `config.json`:
```json
{
  "minecraft_host": "1.2.3.4",
  "minecraft_port": 8765,
  "auth_token": "drosophila_secret_token_123"
}
```

---

### 🔄 What Happens on First Launch?
When `run_real.py` (or `start.bat`) runs for the first time:
1. `connectome/weights.feather` (~1 GB) is automatically fetched from [codex.flywire.ai](https://codex.flywire.ai) if missing.
2. The behavioral sub-graph (`malecns_behavior.*`) compiles and caches locally.
3. Spontaneous firing rates and motor tonic levels calibrate (~1-2 minutes).
4. **Dashboard:** Pygame opens a real-time HUD displaying the 1,536-pixel compound eye view, olfactory vectors, dopamine/state indicators, and descending motor neurons. (Use `--no-gui` to run headless).

---

## 🔧 Server Plugin Configuration (`config.yml`)

The plugin creates `plugins/FruitFly/config.yml` on first launch:

```yaml
# Language selection ("en" for English, "tr" for Turkish, or custom in languages/)
language: "en"

# Python Brain WebSocket Server (listens on 0.0.0.0)
brain:
  port: 8765                  # WebSocket listening port
  auth-token: "drosophila_secret_token_123"  # Shared security password / token
  smart-sleep:
    enabled: true             # Skips heavy sensory raytracing when no players are nearby (0% CPU)
    player-distance: 48.0     # Player proximity threshold in blocks

# Entity Settings
bee:
  auto-spawn: true            # Spawns automatically on server start and on death
  display-name: ""            # Custom display name (leave empty for language default)
  invulnerable: false         # God mode toggle
  speed-multiplier: 1.0       # Flight speed multiplier
  odor-range: 16.0            # Olfactory perception radius in blocks

# Vision System
vision:
  max-ray-range: 16.0         # 1,536-ray compound eye raytracing range in blocks
```

---

## 🎮 In-Game Commands

All commands require **OP permission** (`drosophila.admin`).  
Command Alias: `/fruitfly` or `/fluitfly`

| Command | Description |
|---|---|
| `/fruitfly help` | Displays list of all available commands |
| `/fruitfly tp` | Teleports you directly to the fruit fly |
| `/fruitfly come` | Summons the fruit fly to your position |
| `/fruitfly feed` | Drops an apple in front of the fruit fly |
| `/fruitfly feed full` | Instantly satiates the fly (Satiety level → 20) |
| `/fruitfly hungry` | Instantly starves the fly (Triggers dNPF hunger hormone) |
| `/fruitfly food [amount]` | Views or adjusts the fly's satiety level (3–20) |
| `/fruitfly spawnpoint` | Sets your current location as the fly's permanent home |
| `/fruitfly home` | Sends the fly back to its home spawnpoint |
| `/fruitfly status` | Shows real-time telemetry (health, satiety, odor, dopamine mood, heading) |
| `/fruitfly clear` | Resets Mushroom Body memory cache back to baseline connectome |

---

## 📁 Repository Structure

```
Drosophila/
├── connectome/                     # Raw connectome weights (~1.1 GB, omitted from git)
│   ├── weights.feather             # Synaptic connection weights (1 GB)
│   ├── annotations.feather         # Neuron annotations and side tags (14 MB)
│   ├── neurotransmitters.feather   # Neurotransmitter classifications (41 MB)
│   └── malecns_behavior.*          # Cached compiled behavior subgraph
│
├── drosophila-paper/               # Minecraft Paper/Bukkit/Spigot Plugin (Java 17)
│   ├── src/main/java/org/drosophila/
│   │   ├── DrosophilaPlugin.java          # Main plugin class and command handlers
│   │   ├── controller/BeeController.java  # Bee entity physics and 3D flight motor
│   │   ├── network/BrainServer.java       # WebSocket server and telemetry broadcaster
│   │   ├── vision/CompoundEyeRaytracer.java # 1,536-ommatidia compound eye raytracing
│   │   ├── olfaction/OdorDiffusion.java   # Olfactory scent diffusion & source tracking
│   │   ├── auditory/AuditoryWindSampler.java # Johnston's organ (acoustic & wind shocks)
│   │   ├── item/BottleManager.java        # Bottle capture and rest mechanic
│   │   └── i18n/LanguageManager.java      # Dynamic multilingual (en/tr) subsystem
│   └── src/main/resources/
│       ├── config.yml                     # Main plugin configuration
│       ├── plugin.yml                     # Bukkit/Spigot plugin manifest
│       └── languages/                     # Language packs (messages_en.yml, messages_tr.yml)
│
├── fly_brain_real.py               # 🧠 MaleCNS LIF biological connectome simulation
├── minecraft_real_bridge.py        # 🌉 WebSocket bridge + Pygame HUD dashboard
├── connectome_loader.py            # Connectome importer and subgraph compiler
├── fly_log.py                      # Real-time neural event & telemetry logger
├── fly_sound.py                    # Wingbeat synthesis & auditory playback
├── run_real.py                     # ▶️ Main Python launcher & configuration wizard
├── setup.bat                       # 🪟 Windows automated setup script
├── start.bat                       # 🪟 Windows runner script
├── setup.sh                        # 🐧 Linux/macOS automated setup script
├── start.sh                        # 🐧 Linux/macOS runner script
├── requirements.txt                # Python dependencies
├── config.json.example             # JSON configuration template
└── .env.example                    # Environment variable template
```

---

## 💬 Community & Support

Need assistance, want to share ideas, or discuss the simulation? Join our Discord server:  
👉 **Discord Community:** [https://discord.gg/TQHAm67DmX](https://discord.gg/TQHAm67DmX)

---

## 📜 Citations & License

* **Biological Connectome Data:** [MaleCNS v1.0](https://codex.flywire.ai/) — [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)  
  *(Janelia Research Campus / University of Cambridge / MRC Laboratory of Molecular Biology / Google Research)*
* **Project Source Code:** **MIT License** © [DeveloperKubilay](https://github.com/DeveloperKubilay)

---

# 🪰 Drosophila — Gerçek Meyve Sineği Beyni Minecraft'ta (Türkçe)

[![Minecraft](https://img.shields.io/badge/Minecraft-Paper%20%7C%20Bukkit%20%7C%20Spigot%20%7C%20Purpur%20(1.20--1.21.x)-brightgreen)](https://papermc.io)
[![Java](https://img.shields.io/badge/Java-17%2B-orange)](https://www.oracle.com/java/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Connectome](https://img.shields.io/badge/Connectome-MaleCNS%20v1.0%20(13k%2B%20neurons)-blueviolet)](https://codex.flywire.ai/)
[![Discord](https://img.shields.io/badge/Discord-Topluluğumuza%20Katıl-5865F2?logo=discord&logoColor=white)](https://discord.gg/TQHAm67DmX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Janelia Research Campus**, **University of Cambridge**, **MRC LMB** ve **Google Research** konsorsiyumu tarafından elektron mikroskobuyla nöron nöron haritalandırılan **13.000+ nöronluk** ve **5.000.000+ sinapslık** gerçek **MaleCNS v1.0** biyolojik meyve sineği (*Drosophila melanogaster*) beynini Minecraft dünyasına entegre eden ileri düzey biyolojik simülasyon projesidir.

Simülasyon, Leaky Integrate-and-Fire (LIF) nörofizyolojik modeli ile çalışır. Minecraft dünyasındaki bir arı (Bee) bedenini kontrol eder; 1536 ommatidiumluk petek gözleriyle görür, koku moleküllerini koklar, Johnston organıyla ses ve rüzgârı dinler, acıyı ve tokluğu hisseder.

---

## 🌟 Projenin Amacı ve Vizyonu

İnternette yapılan alternatifleri ve konektom projelerini incelediğimizde sıkça karşılaştığımız iki temel yaklaşım bulunmaktadır:

1. **Aşırı Sıkıştırma ve Model Kaybı:** Bazı projeler bu ~1 GB'lık devasa biyolojik konektom verisini 20–22 MB seviyelerine kadar kırpıp sıkıştırmıştır. Biz bu derece budanmış bir ağın gerçek bir meyve sineği sinir sistemini ve dinamik karar mekanizmalarını asla yansıtamayacağına inanıyoruz. Bizim ana amacımız, **biyolojik yapıyı bozmadan gerçek bir sineğin sinir sistemini tam ağırlıklarıyla Minecraft'a aktarmaktır.**
2. **Yapay Zorlama ve Görev Dayatması (Kripto / Uçak Uçurma):** İnsanlar konektom modellerine yapay ödül/ceza fonksiyonları bağlayarak uçak uçurtmaya veya kripto para al-sat yaptırmaya çalışıyor. Ancak bu bir biyolojik zeka simülasyonu değildir; bu standart bir takviyeli öğrenme (RL) problemidir. Sıradan bir yapay zekaya da kripto oynatmayı zaten öğretebilirsiniz. Bir meyve sineğini yapay ceza veya dopamin manipülasyonuyla alakasız görevlere zorlamak onun biyolojik gerçekliğini yok eder.

> ### 🎯 Temel Felsefemiz
> Bu projenin amacı sineğe dışarıdan yapay hiçbir özel bilgi eğitmeksizin; doğadaki tüm duyusal olayları (1536 petek gözle görme, koku yayılımı, hava akımları, Johnston organı akustik şokları, tokluk ve tehdit) biyolojik gerçekçilikle aktarmak ve **13.000 nöronluk konektomun hiçbir yapay müdahale olmadan Minecraft ekosisteminde nasıl hayatta kaldığını, nasıl gezindiğini ve ne gibi doğal tepkiler verdiğini gözlemlemektir.**

---

## 🏗️ Dağıtık Mimari (Distributed Architecture)

Proje, fiziksel beden ile biyolojik beyni birbirinden ayıran modern bir dağıtık mimari kullanır:

```
[ Minecraft Sunucusu (Java) ]                    [ Biyolojik Beyin Motoru (Python) ]
  Paper / Bukkit / Spigot / Purpur                 MaleCNS v1.0 LIF Simülasyonu
  ├── 1536 Ommatidium Petek Göz                    ├── 13.000+ Nöron (Görsel / Koku / Motor)
  ├── Koku Difüzyonu (Meyve, Çiçek, Yaprak)        ├── 5.000.000+ Biyolojik Sinaps
  ├── Johnston Organı (Ses & Rüzgâr)    ◀======▶   ├── Pygame Canlı Telemetri Dashboard
  └── 3D Uçuş ve Aerodinamik Motoru    WebSocket   └── Akıllı Uyku / Güç Yönetimi
      (0.0.0.0:8765 dinler)                           (İstemci olarak bağlanır)
```

* **Sunucu Desteği:** **Paper, Bukkit, Spigot, Purpur (1.20 - 1.21.x+)** tam desteklenir. Mod yükleyicileri (*Forge, NeoForge, Fabric*) için tasarlanmamıştır; standart Spigot/Bukkit API'si kullanıldığından eklenti olarak kurulur.
* **Dağıtık Çalıştırma:** Yapay zeka modeli ayrı bir bilgisayarda/sunucuda, Minecraft sunucunuz ise bambaşka bir uzak sunucuda çalışabilir (veya her ikisi aynı makinede çalıştırılabilir).

---

## 💻 Sistem Gereksinimleri

| Bileşen | Gereksinim | Açıklama |
|---------|------------|----------|
| **Python** | 3.10 veya üstü | Konektom LIF motoru ve köprü için |
| **Java JDK** | 17 veya üstü | Minecraft eklentisi için |
| **Minecraft Sunucu** | Paper / Bukkit / Spigot / Purpur 1.20 - 1.21.x+ | Eklentinin çalışacağı sunucu |
| **RAM (Bellek)** | ~2 GB | Python beyin simülasyonu için yeterlidir |
| **GPU (Ekran Kartı)** | **GEREKMEZ!** | Simülasyon CPU üzerinde son derece optimize çalışır |
| **Disk Alanı** | ~1.5 GB | Ham konektom verisi (~1.1 GB) ve derlenmiş grafik için |

---

## 🚀 Kurulum ve Başlatma

### 1. Dosyaları İndirme
[GitHub Releases](../../releases) sayfasından en güncel sürümü indirin:
* Minecraft sunucusu için: **`FruitFly.jar`**
* Python beyin simülasyonu için: **`drosophila-brain-X.X.X.zip`** (Windows) veya **`drosophila-brain-X.X.X.tar.gz`** (Linux/macOS)

---

### 2. Minecraft Sunucu Kurulumu (Beden)
1. `FruitFly.jar` dosyasını Minecraft sunucunuzun `plugins/` klasörüne atın.
2. Sunucuyu başlatın veya `/reload` yapın.
3. Eklenti otomatik olarak `0.0.0.0:8765` portunda tak-çalıştır bir WebSocket sunucusu başlatır. Sunucu tarafında hiçbir karmaşık IP yapılandırmasına gerek yoktur!

---

### 3. Python Beyin Simülasyonu Kurulumu (Beyin)

#### 🪟 Windows İçin Hızlı Kurulum:
```cmd
# 1. Adım: Kurulumu çalıştırın (Sanal ortamı kurar, kütüphaneleri yükler ve ayarları sorar):
setup.bat

# 2. Adım: Başlatın:
start.bat
```

#### 🐧 Linux / macOS İçin Hızlı Kurulum:
```bash
# Arşivi açın ve klasöre girin:
tar -xzf drosophila-brain-*.tar.gz
cd drosophila-brain-*

# İzinleri verin ve kurulumu yapın:
chmod +x setup.sh start.sh
./setup.sh

# Başlatın:
./start.sh
```

---

### ⚙️ Çalıştırma Seçenekleri ve Parametreler

`setup.bat` (veya `setup.sh`) ilk kurulumda sunucu adresini (`localhost` veya uzak IP) ve güvenlik şifrenizi (token) sorar ve bunları `config.json` ile `.env` dosyalarına otomatik kaydeder.

Ardından farklı senaryolara göre dilediğiniz gibi başlatabilirsiniz:

```cmd
# 1. Kayıtlı ayarlarla (config.json / .env) başlatma:
start.bat

# 2. Sadece Terminal Modu (Ekran kartsız sunucular / düşük CPU kullanımı, GUI kapalı):
start.bat --no-gui

# 3. Özel IP veya IP:Port belirterek başlatma (Şifreyi kayıtlı dosyalardan alır):
start.bat 1.2.3.4
start.bat 1.2.3.4:8765

# 4. Özel IP:Port ve Şifre ile başlatma:
start.bat 1.2.3.4:8765 "mypassword"
start.bat 1.2.3.4:8765 "mypassword" --no-gui
```

*(Linux/macOS kullanıcıları aynı parametreleri `./start.sh` ile kullanabilir).*

---

### 📄 Ortam Değişkenleri (`.env`) ve Yapılandırma Dosyaları

Sunucu bağlantı ayarlarını modüler olarak `.env` dosyasında da saklayabilirsiniz:

```env
# ================================================================
# Drosophila Meyve Sineği Simülasyonu - Ortam Değişkenleri (.env)
# ================================================================

# Hedef Minecraft sunucusunun IP veya Domain adresi (Varsayılan: localhost)
# Doğrudan IP:Port olarak da tanımlayabilirsiniz (Örn: 1.2.3.4:8765)
MINECRAFT_HOST=1.2.3.4

# Hedef WebSocket portu (Varsayılan: 8765)
MINECRAFT_PORT=8765

# Güvenlik Şifresi / Token (Minecraft config.yml'deki brain.auth-token ile eşleşmelidir)
MINECRAFT_PASSWORD=drosophila_secret_token_123
FLY_AUTH_TOKEN=drosophila_secret_token_123
```

Aynı şekilde `config.json` dosyası da desteklenir:
```json
{
  "minecraft_host": "1.2.3.4",
  "minecraft_port": 8765,
  "auth_token": "drosophila_secret_token_123"
}
```

---

### 🔄 İlk Çalıştırmada Neler Olur?
`run_real.py` (veya `start.bat`) ilk kez çalıştığında:
1. `connectome/weights.feather` (~1 GB) dosyası eksikse doğrudan [codex.flywire.ai](https://codex.flywire.ai) adresinden otomatik indirilir.
2. Davranış alt-grafiği (`malecns_behavior.*`) derlenir ve önbelleğe alınır.
3. Spontane ateşleme ve motor tonik kalibrasyonu tamamlanır (1-2 dakika).
4. **Grafik Arayüz (Dashboard):** Pygame penceresi açılarak sineğin 1536 piksellik gözünden dünyayı, koku/tehdit sensörlerini ve nöron ateşlemelerini canlı olarak izlemenizi sağlar. İsterseniz `--no-gui` ile arayüzsüz çalıştırabilirsiniz.

---

## 🔧 Eklenti Konfigürasyonu (`config.yml`)

Sunucu ilk açıldığında `plugins/FruitFly/config.yml` dosyasını otomatik oluşturur:

```yaml
# Dil Ayarı ("en" İngilizce, "tr" Türkçe veya languages/ altındaki özel dil)
language: "en"

# Python Beyin WebSocket Sunucusu (0.0.0.0 üzerinde dinler)
brain:
  port: 8765                  # Dinlenecek WebSocket portu
  auth-token: "drosophila_secret_token_123"  # Güvenlik anahtarı / şifre
  smart-sleep:
    enabled: true             # Akıllı uyku modu (yakında oyuncu yoksa işlemci tasarrufu sağlar)
    player-distance: 48.0     # Oyuncu mesafe eşiği (blok)

# Sinek Ayarları
bee:
  auto-spawn: true            # Sunucu açılınca ve ölümde otomatik doğma
  display-name: ""            # Özel isim (boş bırakılırsa dil dosyasındaki varsayılan kullanılır)
  invulnerable: false         # Ölümsüzlük (God mode)
  speed-multiplier: 1.0       # Uçuş hızı çarpanı
  odor-range: 16.0            # Koku algılama menzili (blok)

# Görme Sistemi
vision:
  max-ray-range: 16.0         # 1536 ommatidium petek göz ışın menzili (blok)
```

---

## 🎮 Oyun İçi Komutlar

Tüm komutlar sunucuda **OP yetkisi** (`drosophila.admin`) gerektirir.  
Kısayol (Alias): `/fruitfly` veya `/fluitfly`

| Komut | Açıklama |
|---|---|
| `/fruitfly help` | Tüm komutların listesini ve açıklamalarını gösterir |
| `/fruitfly tp` | Sineğin yanına anında ışınlanmanızı sağlar |
| `/fruitfly come` | Sineği bulunduğunuz konuma çağırır |
| `/fruitfly feed` | Sineğin önüne anında bir elma bırakır |
| `/fruitfly feed full` | Sineği anında tamamen doyurur (Tokluk seviyesi → 20) |
| `/fruitfly hungry` | Sineği acıktırır (Tokluk seviyesi → 3) |
| `/fruitfly food [miktar]` | Sineğin anlık tokluk seviyesini görüntüler veya ayarlar |
| `/fruitfly spawnpoint` | Bulunduğunuz konumu sineğin kalıcı yuvası/evi (spawnpoint) yapar |
| `/fruitfly home` | Sineği belirlenen ev/doğma noktasına gönderir |
| `/fruitfly status` | Ayrıntılı canlı telemetri (can, tokluk, koku mesafesi, baş açısı, tehdit seviyesi) |
| `/fruitfly clear` | Sineğin mantar cisimciği (öğrenme/hafıza) önbelleğini sıfırlar |

---

## 📁 Proje Dosya Yapısı

```
Drosophila/
├── connectome/                     # Konektom ham verileri (~1.1 GB, git'e dahil değildir)
│   ├── weights.feather             # Sinaptik bağlantı ağırlıkları (1 GB)
│   ├── annotations.feather         # Nöron kimlikleri ve bölge etiketleri (14 MB)
│   ├── neurotransmitters.feather   # Nörotransmitter türleri (41 MB)
│   └── malecns_behavior.*          # Derlenmiş davranış alt-grafiği (önbellek)
│
├── drosophila-paper/               # Minecraft Paper/Bukkit/Spigot eklentisi (Java 17)
│   ├── src/main/java/org/drosophila/
│   │   ├── DrosophilaPlugin.java          # Ana eklenti sınıfı ve komut yöneticisi
│   │   ├── controller/BeeController.java  # Arı bedeni, 3D tırmanma ve uçuş fiziği
│   │   ├── network/BrainServer.java       # WebSocket telemetri sunucusu
│   │   ├── vision/CompoundEyeRaytracer.java # 1536 ommatidium petek göz ışın izleme
│   │   ├── olfaction/OdorDiffusion.java   # Koku difüzyonu ve ağaç/yaprak/meyve tespiti
│   │   ├── auditory/AuditoryWindSampler.java # Johnston organı (ses, şok dalgası, rüzgâr)
│   │   ├── item/BottleManager.java        # Şişede yakalama/taşıma mekaniği
│   │   └── i18n/LanguageManager.java      # Çoklu dil (en/tr) altyapısı
│   └── src/main/resources/
│       ├── config.yml                     # Sunucu ana konfigürasyon dosyası
│       ├── plugin.yml                     # Bukkit/Spigot eklenti tanımlayıcısı
│       └── languages/                     # Dil paketleri (messages_en.yml, messages_tr.yml)
│
├── fly_brain_real.py               # 🧠 MaleCNS LIF biyolojik beyin simülasyonu
├── minecraft_real_bridge.py        # 🌉 WebSocket köprüsü + Pygame görsel dashboard
├── connectome_loader.py            # Konektom yükleyici ve alt-grafik derleyici
├── fly_log.py                      # Canlı nöral aktivite kayıt sistemi
├── fly_sound.py                    # Kanat çırpış ve uçuş sesi simülasyonu (WingBeat)
├── run_real.py                     # ▶️ Ana Python başlatıcısı (bütün motorları yönetir)
├── setup.bat                       # 🪟 Windows otomatik kurulum betiği
├── start.bat                       # 🪟 Windows modüler başlatıcı
├── setup.sh                        # 🐧 Linux/macOS otomatik kurulum betiği
├── start.sh                        # 🐧 Linux/macOS modüler başlatıcı
├── requirements.txt                # Python bağımlılıkları listesi
├── config.json.example             # JSON bağlantı şablonu
└── .env.example                    # Ortam değişkenleri şablonu
```

---

## 💬 Destek ve Topluluk

Herhangi bir sorun yaşarsanız, öneride bulunmak veya simülasyon hakkında fikir alışverişi yapmak isterseniz Discord sunucumuza katılabilirsiniz:  
👉 **Discord Topluluğumuz:** [https://discord.gg/TQHAm67DmX](https://discord.gg/TQHAm67DmX)

---

## 📜 Lisans ve Atıflar

* **Biyolojik Konektom Verisi:** [MaleCNS v1.0](https://codex.flywire.ai/) — [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)  
  *(Janelia Research Campus / University of Cambridge / MRC Laboratory of Molecular Biology / Google Research)*
* **Proje Kodları:** **MIT Lisansı** © [DeveloperKubilay](https://github.com/DeveloperKubilay)
