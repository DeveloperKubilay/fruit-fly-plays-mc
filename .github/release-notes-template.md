# 🪰 Drosophila __VERSION__ — Real MaleCNS v1.0 Fruit Fly Connectome for Minecraft

Biological fruit fly (*Drosophila melanogaster*) connectome simulation powered by MaleCNS v1.0. Controls a living 3D entity in Minecraft Paper/Bukkit/Spigot/Purpur servers with 13,000+ biological neurons and 5,000,000+ synapses.

### 📢 Important Information
* **Distributed Architecture:** The Minecraft server and Python neural engine run completely decoupled.
  * If running the Minecraft server and Python brain on the **same machine**, use `0.0.0.0` or `localhost` (press Enter in setup).
  * If running on **different machines**, enter the target server's IP address (`IP` or `IP:Port`).
* **Server Compatibility:** Requires Minecraft **1.20 or newer** (**Paper, Purpur, Bukkit, Spigot** fully supported).
  * *Minecraft **1.21+** Paper/Purpur is strongly recommended for optimal performance and asynchronous raytracing.*
* **Python Requirement:** **Python 3.10 or newer** is required. No dedicated GPU needed; runs efficiently on CPU.
* **Community & Support:** Join our Discord for support, suggestions, or discussion:  
  👉 **Discord Community:** [https://discord.gg/TQHAm67DmX](https://discord.gg/TQHAm67DmX)

### 📦 Downloadable Assets

| File | Description | Installation |
|---|---|---|
| **`FruitFly-__VERSION__.jar`** | Minecraft Server Plugin (Body) | Place into server `plugins/` directory |
| **`drosophila-brain-__VERSION__.zip`** | Python Brain Simulation (Windows) | `setup.bat` -> `start.bat` |
| **`drosophila-brain-__VERSION__.tar.gz`** | Python Brain Simulation (Linux/macOS) | `./setup.sh` -> `./start.sh` |

### 🚀 Quick Start Guide

#### 1. Minecraft Server (Body):
1. Copy `FruitFly-__VERSION__.jar` into your Minecraft server's `plugins/` folder.
2. Start the server or run `/reload` (WebSocket server automatically starts on `0.0.0.0:8765`).
3. You can set your preferred language (`en` / `tr`) in `plugins/FruitFly/config.yml`.

#### 2. Python Brain Simulation (Brain):

**🪟 Windows:**

Open an empty folder, open Command Prompt (CMD), and paste this block (paste by right-clicking in CMD):
```cmd
curl -L -o drosophila-brain-__VERSION__.zip https://github.com/DeveloperKubilay/fruit-fly-plays-mc/releases/download/__VERSION__/drosophila-brain-__VERSION__.zip
tar -xf drosophila-brain-__VERSION__.zip
cd drosophila-brain-__VERSION__
setup.bat
```

After setup finishes, launch the simulation:
```cmd
start.bat
```

Optional launch options:
* Console mode only (Headless / No GUI): `start.bat --no-gui`
* Custom server address: `start.bat 1.2.3.4:8765`
* Custom address and token: `start.bat 1.2.3.4:8765 "mypassword"`

**🐧 Linux / macOS:**

Open an empty directory, open terminal, and paste (paste with `Ctrl + Shift + V`):
```bash
curl -L -o drosophila-brain-__VERSION__.tar.gz https://github.com/DeveloperKubilay/fruit-fly-plays-mc/releases/download/__VERSION__/drosophila-brain-__VERSION__.tar.gz
tar -xzf drosophila-brain-__VERSION__.tar.gz
cd drosophila-brain-__VERSION__
chmod +x setup.sh start.sh
./setup.sh
```

After setup finishes, launch the simulation:
```bash
./start.sh
```

Optional launch options:
* Console mode only: `./start.sh --no-gui`
* Custom server address: `./start.sh 1.2.3.4:8765`
* Custom address and token: `./start.sh 1.2.3.4:8765 "mypassword"`

### 🎮 Specifications
* **Minecraft Compatibility:** 1.20 - 1.21.x+ (Bukkit, CraftBukkit, Spigot, PaperMC, Purpur)
* **Java Version:** Java 17 - Java 21+
* **Python Version:** Python 3.10 - 3.12+ (No GPU required, ~2 GB RAM)
* **Connectome Model:** MaleCNS v1.0 (13,000+ neurons, 5,000,000+ synapses, Janelia / Cambridge / MRC LMB / Google Research)
* **License:** MaleCNS CC BY 4.0 & MIT License (DeveloperKubilay)

---

# 🪰 Drosophila __VERSION__ — Minecraft İçin Gerçek MaleCNS v1.0 Biyolojik Meyve Sineği Konektomu (Türkçe)

MaleCNS v1.0 biyolojik meyve sineği (*Drosophila melanogaster*) konektom simülasyonu. 13.000+ nöron ve 5.000.000+ sinaps ile Minecraft Paper/Bukkit/Spigot/Purpur sunucularında yaşayan gerçek bir 3D sinek varlığı kontrolü.

### 📢 Bilgilendirme
* **Ayrı Dağıtık Mimari:** Projenin mimarisinde Minecraft sunucusu ile Python yapay zeka modeli tamamen ayrı çalışır.
  * Eğer Minecraft sunucusu ile Python yapay zeka modelini **aynı makinede** çalıştırıyorsanız IP olarak `0.0.0.0` (veya `localhost` / Enter) kullanın.
  * Eğer **farklı makinelerde** çalıştırıyorsanız hedef sunucunun IP adresini (`IP` veya `IP:Port`) yazmanız yeterlidir.
* **Sunucu Sürümü ve Desteği:** Sunucunuzun **1.20 veya üzeri** olması gerekmektedir (**Paper, Purpur, Bukkit, Spigot** tam desteklenir).
  * *Performans optimizasyonları ve asenkron ışın izleme avantajı için **1.21 ve üzeri** Paper / Purpur kullanmanız şiddetle tavsiye edilir.*
* **Python Gereksinimi:** Bilgisayarınızda **Python 3.10 veya üzeri** yüklü olmalıdır. Ekran kartı (GPU) gerekmez, CPU üzerinde optimize çalışır.
* **Topluluk ve Destek:** Herhangi bir sorun yaşarsanız, geri bildirimde bulunmak veya destek almak isterseniz Discord sunucumuzdan bize ulaşabilirsiniz:  
  👉 **Discord Topluluğumuz:** [https://discord.gg/TQHAm67DmX](https://discord.gg/TQHAm67DmX)

### 📦 İndirilebilir Paketler

| Dosya | Açıklama | Kurulum |
|---|---|---|
| **`FruitFly-__VERSION__.jar`** | Minecraft Sunucu Eklentisi (Beden) | Sunucunun `plugins/` klasörüne atın |
| **`drosophila-brain-__VERSION__.zip`** | Python Beyin Simülasyonu (Windows) | `setup.bat` -> `start.bat` |
| **`drosophila-brain-__VERSION__.tar.gz`** | Python Beyin Simülasyonu (Linux/macOS) | `./setup.sh` -> `./start.sh` |

### 🚀 Hızlı Kurulum & Başlatma

#### 1. Minecraft Sunucusu (Beden):
1. `FruitFly-__VERSION__.jar` dosyasını sunucunuzun `plugins/` klasörüne atın.
2. Sunucunuzu başlatın veya `/reload` yapın (otomatik olarak `0.0.0.0:8765` üzerinde dinlemeye başlar).
3. `plugins/FruitFly/config.yml` dosyasından dilinizi (`en` / `tr`) seçebilirsiniz.

#### 2. Python Beyin Simülasyonu (Model):

**🪟 Windows İçin:**

Boş bir klasör açın, içerisinde CMD (Komut İstemi) açarak bu komutları kopyalayıp yapıştırın (CMD penceresine sağ tıklayarak yapıştırılır):
```cmd
curl -L -o drosophila-brain-__VERSION__.zip https://github.com/DeveloperKubilay/fruit-fly-plays-mc/releases/download/__VERSION__/drosophila-brain-__VERSION__.zip
tar -xf drosophila-brain-__VERSION__.zip
cd drosophila-brain-__VERSION__
setup.bat
```

Kurulum tamamlandıktan sonra başlatmak için:
```cmd
start.bat
```

İsteğe bağlı alternatif başlatma seçenekleri:
* Sadece terminal / konsol modu (GUI kapalı, düşük CPU): `start.bat --no-gui`
* Farklı bir sunucu IP'sine bağlanma: `start.bat 1.2.3.4:8765`
* Özel IP ve şifre ile başlatma: `start.bat 1.2.3.4:8765 "mypassword"`

**🐧 Linux / macOS İçin:**

Boş bir dizin oluşturup terminalde bu komutları yapıştırın (`Ctrl + Shift + V` ile yapıştırılır):
```bash
curl -L -o drosophila-brain-__VERSION__.tar.gz https://github.com/DeveloperKubilay/fruit-fly-plays-mc/releases/download/__VERSION__/drosophila-brain-__VERSION__.tar.gz
tar -xzf drosophila-brain-__VERSION__.tar.gz
cd drosophila-brain-__VERSION__
chmod +x setup.sh start.sh
./setup.sh
```

Kurulum tamamlandıktan sonra başlatmak için:
```bash
./start.sh
```

İsteğe bağlı alternatif başlatma seçenekleri:
* Sadece terminal modu (GUI kapalı): `./start.sh --no-gui`
* Farklı bir sunucu IP'sine bağlanma: `./start.sh 1.2.3.4:8765`
* Özel IP ve şifre ile başlatma: `./start.sh 1.2.3.4:8765 "mypassword"`

### 🎮 Uyumluluk
* **Minecraft Sunucu Sürümü:** 1.20 - 1.21.x+ (Bukkit, CraftBukkit, Spigot, PaperMC, Purpur)
* **Java Sürümü:** Java 17 - Java 21+
* **Python Sürümü:** Python 3.10 - 3.12+ (GPU gerektirmez, ~2 GB RAM)
* **Konektom Modeli:** MaleCNS v1.0 (13.000+ nöron, 5.000.000+ sinaps, Janelia / Cambridge / MRC LMB / Google Research)
* **Lisans:** MaleCNS CC BY 4.0 & MIT License (DeveloperKubilay)
