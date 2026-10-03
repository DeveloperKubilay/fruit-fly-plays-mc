# 🪰 Drosophila — Gerçek Meyve Sineği Beyni Minecraft'ta

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

> 📹 *Çok yakında detaylı videolu kurulum rehberi eklenecektir!*

### 1. Dosyaları İndirme
[GitHub Releases](../../releases) sayfasından en güncel sürümü indirin:
* Minecraft sunucusu için: **`FruitFly.jar`**
* Python beyin simülasyonu için: **`drosophila-brain-vX.X.X.zip`** (Windows) veya **`drosophila-brain-vX.X.X.tar.gz`** (Linux/macOS)

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
|-------|----------|
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
│   ├── neurotransmitters.feather    # Nörotransmitter türleri (41 MB)
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
