# 🪰 Drosophila v__VERSION__ — MaleCNS v1.0 Biological Connectome for Minecraft

MaleCNS v1.0 biyolojik meyve sineği (*Drosophila melanogaster*) konektom simülasyonu. 13.000+ nöron ve 5.000.000+ sinaps ile Minecraft Paper/Bukkit/Spigot/Purpur sunucularında yaşayan gerçek bir 3D sinek varlığı kontrolü.

---

### 📢 Bilgilendirme / Important Notes

* **Ayrı Dağıtık Mimari:** Projenin mimarisinde Minecraft sunucusu ile Python yapay zeka modeli tamamen ayrı çalışır.
  * Eğer Minecraft sunucusu ile Python yapay zeka modelini **aynı makinede** çalıştırıyorsanız IP olarak `0.0.0.0` (veya `localhost` / Enter) kullanın.
  * Eğer **farklı makinelerde** çalıştırıyorsanız hedef sunucunun IP adresini (`IP` veya `IP:Port`) yazmanız yeterlidir.
* **Sunucu Sürümü ve Desteği:** Sunucunuzun **1.20 veya üzeri** olması gerekmektedir (**Paper, Purpur, Bukkit, Spigot** tam desteklenir).
  * *Performans optimizasyonları ve asenkron ışın izleme avantajı için **1.21 ve üzeri** Paper / Purpur kullanmanız şiddetle tavsiye edilir.*
* **Python Gereksinimi:** Bilgisayarınızda **Python 3.10 veya üzeri** yüklü olmalıdır. Ekran kartı (GPU) gerekmez, CPU üzerinde optimize çalışır.
* **Topluluk ve Destek:** Herhangi bir sorun yaşarsanız, geri bildirimde bulunmak veya destek almak isterseniz Discord sunucumuzdan bize ulaşabilirsiniz:  
  👉 **Discord Topluluğumuz:** [https://discord.gg/TQHAm67DmX](https://discord.gg/TQHAm67DmX)

---

### 📦 Downloadable Assets / İndirilebilir Paketler

| Dosya / File | Açıklama / Description | Kurulum / Installation |
|---|---|---|
| **`FruitFly-v__VERSION__.jar`** | Minecraft Sunucu Eklentisi (Beden) | Sunucunun `plugins/` klasörüne atın |
| **`drosophila-brain-v__VERSION__.zip`** | Python Beyin Simülasyonu (Windows) | `setup.bat` -> `start.bat` |
| **`drosophila-brain-v__VERSION__.tar.gz`** | Python Beyin Simülasyonu (Linux/macOS) | `./setup.sh` -> `./start.sh` |

---

### 🚀 Hızlı Kurulum & Başlatma / Quick Start

#### 1. Minecraft Sunucusu (Beden):
1. `FruitFly-v__VERSION__.jar` dosyasını sunucunuzun `plugins/` klasörüne atın.
2. Sunucunuzu başlatın veya `/reload` yapın (otomatik olarak `0.0.0.0:8765` üzerinde dinlemeye başlar).
3. `plugins/FruitFly/config.yml` dosyasından dilinizi (`en` / `tr`) seçebilirsiniz.

---

#### 2. Python Beyin Simülasyonu (Model):

**🪟 Windows İçin:**
```cmd
# Boş bir klasör açın ve içerisinde CMD (Komut İstemi) açarak indirin:
curl -L -o drosophila-brain-v__VERSION__.zip https://github.com/DeveloperKubilay/fruit-fly-plays-mc/releases/download/v__VERSION__/drosophila-brain-v__VERSION__.zip
tar -xf drosophila-brain-v__VERSION__.zip
cd drosophila-brain-v__VERSION__

# 1. Kurulum (Sanal ortamı hazırlar, kütüphaneleri kurar ve IP/şifre sorar):
setup.bat

# 2. Çalıştırma:
start.bat

# İsteğe bağlı alternatif başlatma seçenekleri:
start.bat --no-gui
start.bat 1.2.3.4:8765 "mypassword"
start.bat 1.2.3.4:8765 "mypassword" --no-gui
```

**🐧 Linux / macOS İçin:**
```bash
# Boş bir dizin oluşturup terminalde indirin:
curl -L -o drosophila-brain-v__VERSION__.tar.gz https://github.com/DeveloperKubilay/fruit-fly-plays-mc/releases/download/v__VERSION__/drosophila-brain-v__VERSION__.tar.gz
tar -xzf drosophila-brain-v__VERSION__.tar.gz
cd drosophila-brain-v__VERSION__

# İzinleri verin ve kurulumu çalıştırın:
chmod +x setup.sh start.sh
./setup.sh

# Başlatın:
./start.sh

# İsteğe bağlı alternatif başlatma seçenekleri:
./start.sh --no-gui
./start.sh 1.2.3.4:8765 "mypassword" --no-gui
```

---

### 🎮 Uyumluluk / Specifications

* **Minecraft Sunucu Sürümü:** 1.20 - 1.21.x+ (Bukkit, CraftBukkit, Spigot, PaperMC, Purpur)
* **Java Sürümü:** Java 17 - Java 21+
* **Python Sürümü:** Python 3.10 - 3.12+ (GPU gerektirmez, ~2 GB RAM)
* **Konektom Modeli:** MaleCNS v1.0 (13.000+ nöron, 5.000.000+ sinaps, Janelia / Cambridge / MRC LMB / Google Research)
* **Lisans:** MaleCNS CC BY 4.0 & MIT License (DeveloperKubilay)
