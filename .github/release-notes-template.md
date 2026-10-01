# 🪰 Drosophila v__VERSION__ — MaleCNS v1.0 Biological Connectome for Minecraft

MaleCNS v1.0 biological connectome simulation controlling a 3D flying entity in Minecraft PaperMC servers via real-time WebSocket telemetry.

---

### 📦 Downloadable Assets / İndirilebilir Paketler

| Dosya / File | Açıklama / Description | Kurulum / Installation |
|---|---|---|
| **`DrosophilaBee-v__VERSION__.jar`** | Minecraft Paper/Spigot Server Plugin | Sunucunun `plugins/` klasörüne atın |
| **`drosophila-brain-v__VERSION__.tar.gz`** | Python Beyin Simülasyonu (Linux) | Sunucuda veya harici makinede `./setup.sh` -> `./start.sh` |
| **`drosophila-brain-v__VERSION__.zip`** | Python Beyin Simülasyonu (Windows/Zip) | Zipten çıkarıp `./setup.sh` veya `python run_real.py` çalıştırın |

---

### 🎮 Compatibility / Uyumluluk

* **Minecraft Sunucu Sürümü:** **1.20 - 1.21.x+** (PaperMC, Purpur, Spigot)
  * NMS / internal dependency içermez; Bukkit & Spigot API sayesinde tüm 1.20.x ve 1.21.x sürümleriyle doğrudan uyumludur.
  * *Tavsiye edilen:* **PaperMC 1.20.4+** veya **Paper 1.21.x** (asenkron ışın izleme ve yüksek performans sağlar).
* **Java Sürümü:** **Java 17 - Java 21+** (Java 17 LTS bytecode uyumlu, Java 21+ ile sorunsuz çalışır).
* **Python Sürümü:** **Python 3.10 - 3.12+** (`numpy`, `scipy`, `pyarrow`, `websockets`, `pygame`).
* **Konektom Modeli:** **MaleCNS v1.0** (13.000+ nöron, 5.000.000+ sinaps, Janelia / Cambridge / MRC LMB / Google Research).

---

### 🚀 Quick Start / Hızlı Başlangıç

#### 1. Minecraft Sunucusu:
1. `DrosophilaBee-v__VERSION__.jar` dosyasını `plugins/` klasörüne atın ve sunucuyu başlatın.
2. `plugins/DrosophilaBee/config.yml` dosyasından `auth-token` ve dil seçiminizi (`en` / `tr`) yapın.

#### 2. Python Beyin Simülasyonu:
```bash
tar -xzf drosophila-brain-v__VERSION__.tar.gz
cd drosophila-brain-v__VERSION__
chmod +x setup.sh start.sh
./setup.sh
./start.sh
```
*(Minecraft sunucusu farklı bir IP'deyse: `./start.sh <SUNUCU_IP>`)*
