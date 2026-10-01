"""
================================================================================
 GERÇEK ERKEK MEYVE SİNEĞİ BEYNİ  —  MaleCNS v1.0 konektomu üzerinde LIF
================================================================================

Bu dosyada UYDURMA DEVRE YOKTUR. Nöronlar ve aralarındaki bağlantıların tamamı
elektron mikroskobuyla ölçülmüş MaleCNS v1.0 rekonstrüksiyonundan gelir:

    101.115 nöron | 3.284.595 yönlü bağlantı | 27.144.242 sinaptik temas
    FlyEM / HHMI Janelia + Cambridge + MRC LMB + Google Research  (CC BY 4.0)

Sinek nasıl davranacağına KENDİ BAĞLANTI HARİTASIYLA karar verir. Bizim
yaptığımız üç şey var ve üçü de açıkça modelleme varsayımıdır:

  1) DUYU ENJEKSİYONU — ekrandaki görüntüyü hangi nörona akım olarak vereceğiz.
     Lamina hücreleri L1 (ON), L2 (OFF), L3 (sürekli parlaklık) gerçek
     retinotopik hex koordinatlarına sahiptir; görüntü oraya basılır.
     (Fotoreseptörlerin somaları görüntüleme hacminin dışında kaldığı için
      hex koordinatları yok; bu yüzden onların gerçek hedefleri sürülür.)

  2) NÖRON DİNAMİĞİ — LIF parametreleri konektomdan gelmez, literatürden gelir.

  3) MOTOR ÇÖZÜMÜ — hangi inen nöronun ateşlemesi hangi tuşa karşılık gelir.
     Gerçek isimleriyle:
        DNp20    : bilateral dönüş farkı        (sağ/sol yalpalama)
        DNpe017  : ileri yürüyüş sürücüsü
        MDN      : geri yürüyüş (Bidaye ve ark., Science 2014)
        DNp09    : hızlı kaçış lokomosyonu
        DNp01    : GIANT FIBER — acil sıçrama refleksi
        DNa02    : yürüyüş sırasında dönüş
     Aradaki her şeyi (görme -> karar -> hareket) konektom halleder.

"Konektom NE OLAN'ı söyler, NASIL ÇALIŞTIĞINI değil." Yukarıdaki üç varsayım
olmadan hiçbir konektom simülasyonu davranış üretemez — bizimki de dahil.
"""

import math
import os
import numpy as np

try:
    import scipy.sparse as sp
except ImportError:                                        # pragma: no cover
    sp = None

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.path.join(HERE, "connectome", "malecns_behavior")
ANNOT = os.path.join(HERE, "connectome", "annotations.feather")

# ---- Motor çıkış nöronları (gerçek MaleCNS tip adları) ----
MOTOR_TYPES = {
    "turn":     "DNp20",      # bilateral dönüş
    "forward":  "DNpe017",    # ileri yürüyüş
    "backward": "MDN",        # geri yürüyüş (Moonwalker)
    "fast":     "DNp09",      # hızlı lokomosyon
    "escape":   "DNp01",      # Giant Fiber (sıçrama)
    "steer2":   "DNa02",      # yürüyüşte dönüş
    # LOOMING KAÇIŞI — üzerine gelen cisimden (mob, el, kuş) kaçış.
    # Nöron seçimi ÖLÇÜLDÜ, varsayılmadı. İnen nöronların girdi payları:
    #     DNp04  LC4 %57,6 + LPLC2 %16,8  -> girdisinin ~%74'ü looming
    #     DNp11  LC4 %20,0
    #     DNp01  LC4 %17,5 + LPLC2 %13,3
    #     DNp09  LC4 %0,00 + LPLC2 %0,65  <- looming ile ALAKASI YOK
    # Eskiden kaçışı DNp09'dan okuyorduk ve sinek mobdan hiç kaçamıyordu:
    # göz cismi görüyordu (LPLC2 Cohen d = 0,82) ama sinyal motora
    # ulaşmıyordu, DNp09 sabit 0,00 Hz kalıyordu.
    # Literatür de aynı yeri gösteriyor: von Reyn 2014, Ache ve ark. 2019 —
    # LC4 -> DNp04/DNp11 kaçış yolu.
    "loom":     "DNp04",      # LC4 sürümlü kaçış
    "loom2":    "DNp11",      # ikinci LC4 hedefi
    # BESLENME — Proboscis Uzatma Refleksi (PER) motor nöronu (Dethier 1976).
    # claw_tpGRN (ayak tat reseptörü) --2 sinaps--> MN9.
    "feed":     "MN9",        # proboscis uzatma
}

# ---- DUYU GİRİŞİ: gerçek fotoreseptörler ----
# Drosophila fotoreseptörleri HİSTAMİNERJİKTİR, yani hedeflerini İNHİBE ederler.
# Işık -> fotoreseptör depolarize -> L1/L2/L3 hiperpolarize. ON/OFF ayrımını
# aşağıdaki medulla devresi (Mi1/Tm3 vs Tm1/Tm2) kendisi yapar.
# Bu yüzden ışığı L1'e DEĞİL, doğrudan fotoreseptörlere basıyoruz; işaret
# çevrimini konektomun kendi ölçülmüş nörotransmitterleri hallediyor.
PHOTORECEPTORS = {
    "R1-R6": "lum",      # geniş bantlı hareket/parlaklık kanalı
    "R7p": "uv", "R7y": "uv", "R7d": "uv",
    "R8p": "blue", "R8y": "green", "R8d": "blue",
}
# Hex koordinatı taşıyan referans katmanlar (fotoreseptör konumu bunlardan türetilir)
HEX_REFERENCE = ("L1", "L2", "L3", "L5", "Mi1", "Tm1", "Tm2", "Tm9", "Tm20", "T1", "C2", "C3")

# Drosophila'da fotoreseptörler ve lamina monopolar hücreleri GRADED'dir —
# spike ATMAZLAR. Spike kodlaması medulla'dan itibaren başlar. Bu hücreleri
# ateşletmek biyolojik olarak yanlış olur; bunun yerine fotoreseptörün
# histaminerjik (inhibitör) graded sinapsı doğrudan akım olarak L1/L2/L3'e
# uygulanır: ışık artınca hedef hiperpolarize olur.
# Fotoreseptörler VE lamina monopolar hücreleri graded'dir.
GRADED_TYPES = ("R1-R6", "R7p", "R7y", "R7d", "R8p", "R8y", "R8d",
                "L1", "L2", "L3", "L4", "L5", "T1")
# Işık doğrudan fotoreseptörlere basılır; gerisini konektom yapar:
#   ışık -> R depolarize -> histamin (inhibitör) -> L1/L2/L3 hiperpolarize
#   L1 glutamaterjik (inhibitör) -> salgısı düşünce Mi1 serbest kalır = ON yolu
#   L2 kolinerjik  (uyarıcı)     -> salgısı düşünce Tm1/Tm2 susar   = OFF yolu
# ON/OFF ayrımını biz YAPMIYORUZ — ölçülmüş nörotransmitterler yapıyor.
PHOTO_INPUT = {"R1-R6": "lum", "R7p": "uv", "R7y": "uv", "R7d": "uv",
               "R8p": "blue", "R8y": "green", "R8d": "blue"}
# Duyusal enjeksiyon kazançları (modelleme varsayımı — veriden gelmez).
# Görüntünün fotoreseptöre basılmasıyla aynı kategoridedir.
# Model sürümü: kalibrasyon önbelleğini doğrulamak için kullanılır.
MODEL_VERSION = 4
# Tonik taban akımı — köprü ve doğrulama betiği buradan okur, tek yerden ayarlanır.
TONIC_FLOOR = 0.42
ODOR_GAIN = 1.10        # koku -> ORN
# --- KOKU RESEPTÖRÜ UYUMU (adaptasyon) ---
# Gerçek ORN'ler sabit kokuya saniyenin onda birleri içinde uyum sağlar; çıktı
# konsantrasyonun KENDİSİNE değil, DEĞİŞİMİNE orantılı hale gelir (Nagel &
# Wilson 2011; Martelli ve ark. 2013). Bu bir ayrıntı değil, kokuyu bulmanın
# TEK yolu: iki anten 0,3 mm arayladır, aralarındaki anlık fark neredeyse
# ölçülemez. Sinek kokuyu YÜRÜYEREK bulur — ilerledikçe örnekler, koku
# artıyorsa devam eder, azalıyorsa döner (Álvarez-Salvado ve ark. 2018).
# Bizde uyum yoktu: sabit koku sabit akım veriyordu, yani gradyan bilgisi
# hiç üretilmiyordu. Ölçüldü: koku PN/LH/KC'ye güçlü giriyor (d≈5) ama
# inen nöronlara ulaşan yön farkı d≈0,2 — davranış için çok zayıf.
ORN_ADAPT_TAU_MS = 550.0   # uyum zaman sabiti
ORN_ADAPT_K = 0.72         # uyumun ne kadarı çıkarılır (1.0 = tam uyum)
ORN_ADAPT_GAIN = 2.30      # geçici tepkinin kazancı (uyum kaybını telafi)
ORN_OFF_LIMIT = 0.55       # koku KESİLİNCE reseptörün tabanın ne kadar altına ineceği

# --- KOKUYA YANIT VEREN İNEN NÖRONLAR ---
# Girdi bileşimi ölçüldü (bkz. README). Dönüş için okuduğumuz nöronlara koku
# HİÇ gitmiyor — ve bu bir veri boşluğu değil, konektomun cevabı:
#     DNp20    görsel %71,1   koku %0,000   (girdisinin yalnızca %3,3'ü eksik)
#     DNa02    görsel  %2,5   koku %0,000
#     DNpe017  görsel %33,2   koku %0,000
# Kokuyu motora taşıyan inen nöronlar BAŞKA:
#     DNp44  PN %53,1        DNp29  lateral horn %31,2
#     DNp32  lateral horn %20,7 (MANC alt sınıfı 'xl' = tüm bacak nöropilleri)
#     DNc01  PN %11,6        DNc02  PN %12,1        DNb05  PN %10,6
# Ölçüm (26 tur): koku VARLIĞI bunlara güçlü ulaşıyor —
#     DNc01 4,23 -> 10,19 Hz (d 2,40), DNc02 4,08 -> 9,54 (d 2,12),
#     DNb05 4,92 -> 8,08 (d 1,42), DNp29 2,00 -> 4,38 (d 1,20)
# ama koku YÖNÜ ulaşmıyor (en iyisi DNp32 d −0,56; her tip sol/sağ TEK hücre,
# bir spike 0,77 Hz — yön için çözünürlük yok). Gerçek sinekte de yönü veren
# şey antenler arası fark değil, merkezî komplekstir; bizde halka çekicisi yok.
DN_ODOR_TYPES = ("DNc01", "DNc02", "DNb05", "DNp29")
# Bu topluluk artık yalnızca GÖSTERGEDİR; uyarılmışlığı sürmez (neden
# değiştiğini aşağıdaki ölçüm anlatıyor). Uyarılmışlığın kendisi:
# Neden meşru: `locomotor` zaten bir modelleme varsayımıydı — sineğin
# "sebepsiz yürümesini" sağlayan oktopaminerjik uyarılmışlık devresi
# alt-grafikte yok, biz de yerine SABİT bir akım koymuştuk. Burada o sabiti
# ÖLÇÜLMÜŞ bir nöron sinyaliyle değiştiriyoruz; yeni bir kablo eklemiyoruz,
# uydurma bir sabiti gerçek bir ateşleme hızına bağlıyoruz.
# Davranış eşlemesi de uydurma değil, ölçülmüş sinek davranışı: yürüyen
# Drosophila koku bulutuna girince ileri hızını artırır ve dönüş hızını
# azaltır; koku kesilince yavaşlar ve dönmeye başlar (Álvarez-Salvado ve ark.
# 2018, eLife, Şek. 2). Sinek kokunun YÖNÜNÜ bilmez — bulduğu yol budur.
AROUSAL_FWD_GAIN = 0.55    # koku varken ileri dürtü ne kadar artar
AROUSAL_TURN_DROP = 0.45   # koku varken kendiliğinden dönme ne kadar azalır

# ---------------------------------------------------------------------------
# UYARILMIŞLIK VE KOKU KODLAMASI (Mantar Cisimciği / Kenyon Hücreleri)
# ---------------------------------------------------------------------------
# Koku varlığı Mantar Cisimciğindeki (Mushroom Body) Kenyon hücrelerinin (KC)
# aktivitesinden okunur:
#
#   katman      kokulu / kokusuz Hz   kokusuz en yüksek   ayrım
#   ORN         28,9 / 13,1                22,7          oran 2,2x
#   PN          24,4 / 13,7                23,5          oran 1,8x
#   LH           9,8 /  5,9                 9,7          oran 1,7x
#   KC           4,6 /  0,32                3,07         oran 14x
#
# Kenyon hücreleri SEYREK kodlar: koku yokken gerçekten susarlar (~0.32 Hz).
# Bu nedenle mutlak bir eşik değeri ile koku algısı güvenle tespit edilir:
#     eşik 1,5 Hz -> %98 tespit, %0,04 gürültü eşiği.
# Ölçek, KC'nin ölçülmüş koku-tepki eğrisinden gelir:
#   koku  0,00  0,05  0,10  0,20  0,30  0,45  0,60  0,80  1,00
#   KC Hz 0,34  1,59  2,47  4,21  5,42  5,44  6,69  9,00  8,49
# İlk ölçek 3 Hz idi ve koku 0,2'nin üstünde sinyal DOYUYORDU — yani sinek
# elmaya yaklaşırken, tam da gradyana ihtiyacı olan yerde körleşiyordu.
# 7 Hz bütün aralığı açıyor. (Eğri zaten sıkıştırıcı olduğu için doğrusal
# eşleme kabaca log(konsantrasyon) verir; Weber yasasına uygun.)
KC_ODOR_THR = 1.20          # altı gürültü (kokusuz %99,7 bu eşiğin altında)
# Ölçek kapalı döngüde de tarandı (arena, 30 deneme, aynı tohumlar, 1 m
# gerçek toplama yarıçapı) — farklar gürültü içinde, varış sayısı eşit:
#     ölçek 7,0 -> en yakın 3,23 m, varış 8/30, 2 m'ye 17/30
#     ölçek 4,5 -> en yakın 2,59 m, varış 9/30, 2 m'ye 16/30   <-- seçilen
#     ölçek 3,0 -> en yakın 2,28 m, varış 9/30, 2 m'ye 16/30
# 3,0 mesafede en iyi görünüyor ama koku 0,2'nin üstünde DOYUYOR; 4,5 hem
# ölçümde eşit hem de kaynağa yaklaşırken gradyanı koruyor.
KC_ODOR_SPAN = 4.50         # eşik üstü 0..1'e ölçek
AROUSAL_SMOOTH = 0.80       # yumuşatma (τ ≈ 0,25 s)

# --- KOKU KAYBI VE ARAMA DAVRANIŞI (Surge-to-Cast) ---
# Drosophila koku gradyanını klinotaksi ile takip eder (Álvarez-Salvado et al. 2018).
# Koku yoğunluğu artarken ileri hız artar (surge), koku kaybedildiğinde ise
# arama dönüşleri (cast) tetiklenerek koku izi yeniden taranır.
CAST_GAIN = 0.85            # arama dönüşünün gücü
CAST_PEAK_DECAY = 0.985     # "az önce koku vardı" tepe izi (τ ≈ 3,3 s)
CAST_MIN_LOST = 0.35        # bu kadar düşmeden arama başlamaz
CAST_MAX_NOW = 0.25         # koku halen güçlüyse arama yok (dalgalanma ≠ kayıp)
# Kokunun zaman türevi: hızlı ve yavaş izin farkı (bant geçiren).
# Sinek yönü doğrudan ölçemez; koku konsantrasyonu artıyorsa düz ilerler,
# azalıyorsa klinotaksi dönüşü yapar (Gomez-Marin & Louis 2011, Álvarez-Salvado 2018).
ODOR_FAST_A = 0.82          # hızlı iz (τ ≈ 0,25 s)
ODOR_SLOW_A = 0.965         # yavaş iz (τ ≈ 1,4 s)
CAST_DERIV_GAIN = 8.0       # düşüş -> arama dönüşü kazancı
SOUND_GAIN = 1.30           # ses -> JO-A/JO-B
WIND_GAIN = 0.45            # hava akımı -> JO-C/JO-E
TURN_AWAY_GAIN = 1.45       # nosiseptif kaçış dönüşü
OCELLI_GAIN = 1.25          # tepe göz ışığı -> OCG01
TASTE_GAIN = 1.40           # ayak tat reseptörü -> proboscis (PER) kazancı
HEAT_GAIN = 1.30            # sıcaklık -> termosensör PN'leri
LOOM_GAIN = 1.60            # yaklaşan cisim -> LC4/LPLC2 (bkz. inject_loom)

# Mekanoreseptör -> MDN (Moonwalker Descending Neuron / geri yürüyüş) kazancı (Bidaye et al. 2014).
STEER2_WEIGHT = 0.25
MECH_MDN_GAIN = 0.30
OBSTACLE_TURN_GAIN = 1.25   # engel -> dönüş (geri yürüyüş değil)

# Hücreye özgü tonik uyarım ölçeği. Düz bir taban herkese aynı uyarımı verir,
# ama iki hücre grubunun SESSİZ olduğu ölçülmüş bir gerçektir:
#
#   Kenyon hücreleri: bir kokuya/sahneye hücrelerin yalnızca %5-10'u yanıt verir
#       (Turner, Bazhenov & Laurent 2008). Seyreklik mantar cisimciğinin
#       öğrenme kapasitesinin TEMELİDİR; tonik uyarımla doldurulursa bütün
#       sahneler aynı desene benzer ve öğrenme çöker.
#   DNp01 (Giant Fiber): dinlenmede ateşlemez. Eşiği çok yüksektir, ancak
#       çakışan güçlü looming girdisiyle tetiklenir (Card & Dickinson 2008).
#       Tonik sürülürse sinek durup dururken zıplar.
#
# Bu ölçekler ölçülmüş davranışı geri getirir; bağlantı yapısına dokunmaz.
TONIC_SCALE = {"KC": 0.18, "DNp01": 0.0, "DNp09": 0.30}

# Kas ve motor nöron havuzu, inen nöron spike'larını alçak-geçiren filtreler
# (kasılma toplanması). Modelde bu ayrıca ŞART: DNp20 taraf başına TEK
# nörondur, 50 ms'lik pencerede hızı 0/20/40 Hz'e kuantalanır ve dönüş
# aç-kapa olur. Zaman sabiti ~150 ms.
MOTOR_TAU_MS = 150.0

GRADED_REST_DRIVE = 0.38    # graded hücreleri çalışma aralığının ortasında tutar
GRADED_SCALE = 0.55         # graded salgı -> spike-eşdeğeri ölçek

# ---------------------------------------------------------------------------
#  HÜCRE TİPİNE ÖZGÜ ZAMAN SABİTLERİ  (ms)
# ---------------------------------------------------------------------------
#  ÖNEMLİ: Bu bilgi KONEKTOMDA YOKTUR. Konektom kimin kime bağlı olduğunu
#  söyler, o hücrenin ne kadar hızlı olduğunu söylemez. Buradaki değerler
#  fizyoloji literatüründen gelir ve açık bir modelleme varsayımıdır.
#
#  Neden gerekli: T4/T5 yön seçiciliği, komşu sütunlardan gelen sinyallerin
#  FARKLI GECİKMELERLE buluşmasından doğar (Hassenstein-Reichardt). Mi9/Mi4/Tm9
#  yavaş-sürekli kol, Mi1/Tm3/Tm2 hızlı-geçici koldur. Tüm hücrelere aynı
#  zaman sabitini verirsek gecikme farkı olmaz ve yön seçiciliği ÇIKMAZ.
TAU_BY_TYPE = {
    # hızlı / geçici kol
    "Mi1": 9.0, "Tm3": 9.0, "Tm2": 9.0, "Tm4": 11.0, "L1": 8.0, "L2": 8.0,
    # yavaş / sürekli kol  (gecikmeyi bu hücreler taşır)
    "Mi9": 55.0, "Mi4": 48.0, "Tm9": 55.0, "Tm1": 40.0, "L3": 35.0, "CT1": 60.0,
    # yön-seçici çıkış
    "T4a": 14.0, "T4b": 14.0, "T4c": 14.0, "T4d": 14.0,
    "T5a": 14.0, "T5b": 14.0, "T5c": 14.0, "T5d": 14.0,
    # geniş alan / bütünleştirici
    "LPLC2": 25.0, "LC4": 25.0, "APL": 60.0,
}


class RealFlyBrain:
    """MaleCNS konektomu üzerinde çalışan Leaky Integrate-and-Fire beyni."""

    # Literatürden LIF parametreleri (konektomdan gelmez — varsayım)
    V_REST = -52.0
    V_RESET = -55.0
    V_THRESH = -45.0
    TAU_M = 20.0          # ms
    TAU_SYN = 5.0         # ms
    R_M = 10.0
    T_REFRAC = 2.2        # ms

    def __init__(self, dt=8.33, frame_ms=50.0, gain=4.0, noise=0.28, seed=7,
                 tonic_floor=0.30, graph_path=GRAPH, floor_scope="all",
                 verbose=True):
        if sp is None:
            raise RuntimeError("scipy gerekli:  pip install scipy")

        self.dt = float(dt)
        self.frame_ms = float(frame_ms)
        self.substeps = max(1, int(round(frame_ms / dt)))
        self.rng = np.random.default_rng(seed)
        self.noise = float(noise)

        # ---------- konektomu yükle ----------
        self.graph_path = graph_path
        W = sp.load_npz(graph_path + ".W.npz").astype(np.float32).tocsr()
        meta = np.load(graph_path + ".meta.npz", allow_pickle=False)
        self.bodyIds = meta["bodyIds"]
        self.types = meta["types"].astype(str)
        self.superclass = meta["superclass"].astype(str)
        # Gövde tarafı (L/R). hex koordinatı olmayan hücrelerde de doludur —
        # T4/T5 gibi yön-seçici hücreleri göze göre ayırmak için şart.
        _ss = meta["somaSide"].astype(str) if "somaSide" in meta.files else None
        self.soma_side = (np.where(_ss == "L", 0, np.where(_ss == "R", 1, -1)).astype(np.int8)
                          if _ss is not None else np.full(W.shape[0], -1, dtype=np.int8))
        self.signs = meta["signs"].astype(np.float32)
        self.N = W.shape[0]

        # --- GİRDİ NORMALİZASYONU (modelleme varsayımı) ---
        # Konektom temas SAYISINI verir, sinaptik GÜCÜ değil. Ham sayıları
        # doğrudan akıma çevirmek işe yaramaz: ortalama nöron 267 temas alırken
        # MBON01 21.354 alıyor — 80 kat fazla akımla anında doyuyor.
        # Her nöronun toplam girdi ağırlığını eşitliyoruz; böylece konektomun
        # asıl bilgisi olan GÖRELİ ağırlıklar (kim kimin girdisine hakim)
        # korunur, keyfi ölçek farkı kalkar. Homeostatik sinaptik ölçeklemenin
        # karşılığıdır ve bağlantı yapısına dokunmaz.
        row_abs = np.asarray(abs(W).sum(axis=1)).ravel()
        row_abs[row_abs <= 0] = 1.0
        scale = (1.0 / row_abs).astype(np.float32)
        W = sp.diags(scale, format="csr", dtype=np.float32).dot(W).tocsr()
        W.data *= float(gain)
        self.W = W
        self.row_input_total = row_abs

        # ---------- durum ----------
        self.V = np.full(self.N, self.V_REST, dtype=np.float32)
        self.I_syn = np.zeros(self.N, dtype=np.float32)
        self.I_ext = np.zeros(self.N, dtype=np.float32)
        self.refrac = np.zeros(self.N, dtype=np.float32)
        self.spikes = np.zeros(self.N, dtype=np.float32)
        self.spike_count = np.zeros(self.N, dtype=np.float32)
        # Hücre tipine özgü membran zaman sabiti (varsayılan TAU_M)
        self.tau_m = np.full(self.N, self.TAU_M, dtype=np.float32)
        self._dm = np.exp(-self.dt / self.tau_m).astype(np.float32)
        self._ds = float(np.exp(-self.dt / self.TAU_SYN))
        # Gürültü havuzu: her alt-adımda 101k randn üretmek kare süresinin
        # yarısını yiyordu. Havuzdan rastgele kaydırmayla okumak aynı işi görür.
        self._noise_pool = (self.rng.standard_normal(self.N * 4)
                            .astype(np.float32))
        self._noise_n = self._noise_pool.size

        # ---------- tip indeksleri ----------
        self.idx_of_type = {}
        for t in np.unique(self.types):
            self.idx_of_type[t] = np.where(self.types == t)[0]

        self.motor_idx = {}
        for role, tname in MOTOR_TYPES.items():
            self.motor_idx[role] = self.idx_of_type.get(tname, np.array([], dtype=int))

        # tip bazlı zaman sabitlerini uygula
        for _t, _tau in TAU_BY_TYPE.items():
            _ix = self.idx_of_type.get(_t)
            if _ix is not None and len(_ix):
                self.tau_m[_ix] = _tau
        self._dm = np.exp(-self.dt / self.tau_m).astype(np.float32)

        # graded maskesi retinotopiden ÖNCE hazır olmalı
        self.graded_mask = np.zeros(self.N, dtype=bool)
        for _t in GRADED_TYPES:
            _ix = self.idx_of_type.get(_t)
            if _ix is not None and len(_ix):
                self.graded_mask[_ix] = True
        self._spiking_mask = ~self.graded_mask
        self._n_graded = int(self.graded_mask.sum())
        self._act_buf = np.zeros(self.N, dtype=np.float32)
        self._g_norm = np.float32(1.0 / (self.V_THRESH - self.V_REST))

        # ---------- retinotopi ----------
        self._build_retinotopy(verbose=verbose)

        # ---------- mantar cisimciği (öğrenme) ----------
        self.kc_idx = np.concatenate([v for k, v in self.idx_of_type.items()
                                      if k.startswith("KC")]) if any(
            k.startswith("KC") for k in self.idx_of_type) else np.array([], dtype=int)
        self.mbon_idx = np.concatenate([v for k, v in self.idx_of_type.items()
                                        if k.startswith("MBON")]) if any(
            k.startswith("MBON") for k in self.idx_of_type) else np.array([], dtype=int)
        self.pam_idx = np.concatenate([v for k, v in self.idx_of_type.items()
                                       if k.startswith("PAM")]) if any(
            k.startswith("PAM") for k in self.idx_of_type) else np.array([], dtype=int)
        self.ppl1_idx = np.concatenate([v for k, v in self.idx_of_type.items()
                                        if k.startswith("PPL1")]) if any(
            k.startswith("PPL1") for k in self.idx_of_type) else np.array([], dtype=int)

        # KC -> MBON sinapslarının konumu (plastik olanlar bunlar)
        self._locate_sensory(verbose=verbose)
        self._locate_motor_sides(verbose=verbose)
        self._locate_kc_mbon()
        # Görsel bağlamın mantar cisimciğine giren yolu: lobula görsel
        # projeksiyon nöronları -> gamma-d Kenyon hücreleri. Bu yol gerçek
        # konektomda var (KCg-d girdisinin %1.5'i LoVP). Ölçebilmek için
        # indislerini ayrı tutuyoruz.
        # Looming (yaklaşan cisim) dedektörleri, sol/sağ ayrı.
        self.lc4_L, self.lc4_R = self._sided("LC4")
        self.lplc2_L, self.lplc2_R = self._sided("LPLC2")
        # Ayak (tarsal) tat reseptörleri — besleme devresinin girişi.
        self.grn_idx = np.where(self.types == "claw_tpGRN")[0]
        self.kcd_idx = np.where(self.types == "KCg-d")[0]
        # Kokuya yanıt veren inen nöron topluluğu (bkz. DN_ODOR_TYPES)
        _dno = [self.idx_of_type.get(t, np.array([], dtype=int))
                for t in DN_ODOR_TYPES]
        _dno = [x for x in _dno if len(x)]
        self.dn_odor_idx = (np.concatenate(_dno) if _dno
                            else np.array([], dtype=int))
        self.dn_odor_base = None
        self.dn_odor_dev_s = 0.0
        self.arousal = 0.0
        # mantar cisimciği koku okuması (uyarılmışlığın gerçek kaynağı)
        self.odor_now = 0.0       # koku var mı (0..1), KC hızından
        self.odor_peak = 0.0      # son birkaç saniyenin tepesi
        self.odor_fast = 0.0      # hızlı iz
        self.odor_slow = 0.0      # yavaş iz
        self.odor_d = 0.0         # türev: + yaklaşıyor, − uzaklaşıyor
        self.odor_drop = 0.0      # düşüşten doğan arama dürtüsü
        self.odor_lost = 0.0      # tepeye göre ne kadar düştü (0..1)
        self.cast_side = 0.0      # o anki arama dönüş yönü (0 = arama yok)
        self._cast_flip = 1.0     # bir sonraki arama hangi tarafa başlasın
        self.cast_drive = 0.0     # o karede arama dönüşüne verilen akım
        self._esc_side = 0        # seçilmiş kaçış yönü (kilitli kalır)
        self.lovp_idx = np.where(np.char.startswith(
            self.types.astype(str), "LoVP"))[0]
        _ts = self.types.astype(str)
        # --- SICAKLIK / NEM: VP hattı projeksiyon nöronları ---
        self.thermo_idx = np.where(np.char.startswith(_ts, "VP"))[0]
        # --- TEMİZLENME (grooming) inen nöronları ---
        # DNg11 ve DNg12 grooming refleksini başlatan inen nöronlardır (Seeds et al. 2014).
        self.groom_idx = np.where(np.char.startswith(_ts, "DNg12")
                                  | np.char.startswith(_ts, "DNg11"))[0]
        self.groom_base = None
        self.groom_dev_s = 0.0
        self.kc_trace = np.zeros(len(self.kc_idx), dtype=np.float32)
        self.da_baseline = 0.0

        # Graded (spike atmayan) hücreler — dinamikten çıkarılır
        self.graded_mask = np.zeros(self.N, dtype=bool)
        for t in GRADED_TYPES:
            ix = self.idx_of_type.get(t)
            if ix is not None and len(ix):
                self.graded_mask[ix] = True
        self._spiking_mask = ~self.graded_mask

        # --- TONİK UYARIM = ALT-GRAFİĞE GİRMEYEN GİRDİNİN YERİNE ---
        # Her nöron için "tam konektomda aldığı girdinin yüzde kaçı bizim
        # alt-grafiğimizde YOK" hesaplanmıştır. Tonik uyarım yalnızca o eksiği
        # doldurur. Ölçülen değerler:
        #     Mi1  %5 eksik   (optik lob neredeyse tam)
        #     KC   %39 eksik
        #     DNp20 %95 eksik (inen nöronlar tüm beyinden girdi alır)
        # Böylece Kenyon hücrelerine yapay uyarım BASILMAZ; seyrek kodlamayı
        # APL geri-besleme inhibisyonu kendisi üretir.
        self.missing_input = np.ones(self.N, dtype=np.float32)
        _ip = graph_path + ".inputs.npz"
        if os.path.exists(_ip):
            _d = np.load(_ip)
            self.missing_input = _d["missing"].astype(np.float32)
            self.full_input_total = _d["full_in"].astype(np.float32)
        # Hücreye özgü tonik ölçek (yukarıdaki TONIC_SCALE gerekçesi)
        self.tonic_scale = np.ones(self.N, dtype=np.float32)
        for _pref, _sc in TONIC_SCALE.items():
            _m = np.array([t.startswith(_pref) for t in self.types])
            if _m.any():
                self.tonic_scale[_m] = _sc

        self.tonic = np.zeros(self.N, dtype=np.float32)
        self.tonic0 = 0.0
        self.tonic_floor = float(tonic_floor)
        self.floor_scope = str(floor_scope)
        # Optik lob maskesi: tabanın disinhibisyon gerekçesi burada geçerli
        self._optic_mask = np.isin(
            self.superclass, ("ol_intrinsic", "ol_sensory", "visual_centrifugal")
        ).astype(np.float32)
        self.calibrated = False

        self.prev_lum = None
        # ORN uyum durumu (sol/sağ anten ayrı) — bkz. ORN_ADAPT_*
        self.orn_adapt_l = 0.0
        self.orn_adapt_r = 0.0
        self._orn_a = float(np.exp(-self.frame_ms / ORN_ADAPT_TAU_MS))
        self.odor_phasic = (0.0, 0.0)   # gösterge için
        self.last_rates = {}
        # İnen nöron hızlarının alçak-geçiren hali (kas filtresi)
        self._motor_a = float(np.exp(-self.frame_ms / MOTOR_TAU_MS))
        self.pam_base = None      # dopamin taban hızı (göstergeler için)
        self.ppl_base = None
        self.pam_dev_s = 0.0      # ekran için yumuşatılmış sapma
        self.ppl_dev_s = 0.0
        self.esc_base = None      # DNp01 taban hızı
        self.loom_base = None     # DNp04 taban hızı
        self.esc_dev_s = 0.0
        self.motor_smooth = {}
        # Rekonstrüksiyon asimetrisinden doğan sabit dönüş sapması
        # (calibrate_steering ile ölçülür)
        self.steer_bias = 0.0
        # Dönüş işareti (calibrate_turn_sign ile ölçülür)
        self.steer_sign = 1.0
        self.sign_evidence = {}

        if verbose:
            print("[GerçekBeyin] %d nöron | %d bağlantı | %d alt-adım x %.1f ms"
                  % (self.N, self.W.nnz, self.substeps, self.dt))
            print("[GerçekBeyin] retinotopik giriş: %d sütun (sol %d / sağ %d)"
                  % (len(self.col_index), int((self.col_side == 0).sum()),
                     int((self.col_side == 1).sum())))
            for role, ix in self.motor_idx.items():
                print("    motor %-9s %-9s %d nöron" % (role, MOTOR_TYPES[role], len(ix)))

    # ------------------------------------------------------------------
    def _build_retinotopy(self, verbose=True):
        """
        Gerçek hex koordinatlarından ekran eşlemesi kurar.

        Fotoreseptörlerin somaları görüntüleme hacminin dışında olduğu için
        assignedOlHex değerleri yoktur. Konumlarını KONEKTOMUN KENDİSİNDEN
        türetiyoruz: her fotoreseptörün hedeflediği lamina/medulla hücrelerinin
        (hex koordinatı olan) ağırlıklı ortalama konumu = o fotoreseptörün
        retinotopik konumu. Yani retinotopi de uydurma değil, ölçülmüş.
        """
        import pyarrow.feather as ft
        df = ft.read_table(ANNOT).select(
            ["bodyId", "assignedOlHex1", "assignedOlHex2", "somaSide"]).to_pandas()
        df = df.dropna(subset=["assignedOlHex1", "assignedOlHex2"])
        df = df[df["somaSide"].isin(["L", "R"])]
        hexmap = {int(b): (float(h1), float(h2), 0 if sd == "L" else 1)
                  for b, h1, h2, sd in zip(df["bodyId"], df["assignedOlHex1"],
                                           df["assignedOlHex2"], df["somaSide"])}

        # Ağdaki her nöron için hex konumu (varsa)
        hx = np.full(self.N, np.nan, dtype=np.float32)
        hy = np.full(self.N, np.nan, dtype=np.float32)
        hs = np.full(self.N, -1, dtype=np.int8)
        for i, bid in enumerate(self.bodyIds):
            p = hexmap.get(int(bid))
            if p is not None:
                h1, h2, sd = p
                hx[i] = h1 + 0.5 * h2          # eğik hex -> kartezyen
                hy[i] = h2 * 0.8660254
                hs[i] = sd
        n_direct = int(np.isfinite(hx).sum())

        # --- Fotoreseptör konumlarını hedeflerinden türet ---
        pr_idx = []
        for t in PHOTORECEPTORS:
            ix = self.idx_of_type.get(t)
            if ix is not None and len(ix):
                pr_idx.append(ix)
        pr_idx = np.concatenate(pr_idx) if pr_idx else np.array([], dtype=int)

        ref_mask = np.zeros(self.N, dtype=bool)
        for t in HEX_REFERENCE:
            ix = self.idx_of_type.get(t)
            if ix is not None and len(ix):
                ref_mask[ix] = True
        ref_mask &= np.isfinite(hx)

        Wc = self.W.tocsc()          # sütun = presinaptik nöronun çıkışları
        n_derived = 0
        for i in pr_idx:
            lo, hi = Wc.indptr[i], Wc.indptr[i + 1]
            post = Wc.indices[lo:hi]
            wts = np.abs(Wc.data[lo:hi])
            m = ref_mask[post]
            if not m.any():
                continue
            p, w = post[m], wts[m]
            hx[i] = float(np.average(hx[p], weights=w))
            hy[i] = float(np.average(hy[p], weights=w))
            sd = hs[p]
            hs[i] = 0 if (w[sd == 0].sum() >= w[sd == 1].sum()) else 1
            n_derived += 1
        del Wc

        self.hex_x, self.hex_y, self.hex_side = hx, hy, hs

        # --- Giriş katmanları: GERÇEK fotoreseptörler ---
        self.layer_idx, self.layer_uv, self.layer_side, self.layer_kind = {}, {}, {}, {}
        tot = 0
        for t in PHOTO_INPUT:
            ix = self.idx_of_type.get(t)
            if ix is None or len(ix) == 0:
                continue
            ok = ix[np.isfinite(hx[ix]) & (hs[ix] >= 0)]
            if len(ok) == 0:
                continue
            u = hx[ok].copy(); v = hy[ok].copy(); sd = hs[ok].copy()
            for side in (0, 1):
                m = sd == side
                if m.any():
                    u[m] = (u[m] - u[m].min()) / max(1e-6, float(np.ptp(u[m])))
                    v[m] = (v[m] - v[m].min()) / max(1e-6, float(np.ptp(v[m])))
            self.layer_idx[t] = ok
            self.layer_uv[t] = (u, v)
            self.layer_side[t] = sd
            self.layer_kind[t] = PHOTO_INPUT[t]
            tot += len(ok)

        self.col_index = (np.concatenate(list(self.layer_idx.values()))
                          if self.layer_idx else np.array([], dtype=np.int64))
        self.col_side = (np.concatenate(list(self.layer_side.values()))
                         if self.layer_side else np.array([], dtype=np.int8))
        self._sample_cache = {}
        self._retino_stats = {"hex_direct": n_direct, "pr_derived": n_derived,
                              "input_cells": tot}
        if verbose:
            print("[GerçekBeyin] hex konumu doğrudan olan: %d | fotoreseptör konumu "
                  "konektomdan türetilen: %d" % (n_direct, n_derived))

    # ------------------------------------------------------------------
    def _sampler(self, layer, cols, rows):
        """
        Her ommatidium için retina ızgarasında BİLİNEER örnekleme ağırlıkları.

        Neden bilineer: gözde göz başına ~890 ommatidyal sütun var, ekranda ise
        64. En yakın-komşu örneklemede ~14 komşu ommatidium AYNI pikseli görür.
        Hassenstein-Reichardt korelatörü komşular arası FAZ FARKINA dayanır;
        komşular aynı değeri görürse yön seçiciliği matematiksel olarak
        imkansızdır. Bilineer örnekleme her ommatidyuma kendi tam konumundaki
        değeri verir ve uzamsal gradyanı geri kazandırır.
        """
        key = (layer, cols, rows)
        if key in self._sample_cache:
            return self._sample_cache[key]
        u, v = self.layer_uv[layer]
        side = self.layer_side[layer]
        half = cols * 0.56
        fu = np.where(side == 0, u * half, (cols - 1) - (1.0 - u) * half)
        fu = np.clip(fu, 0, cols - 1 - 1e-4)
        fv = np.clip(v * (rows - 1), 0, rows - 1 - 1e-4)

        x0 = fu.astype(np.int64); y0 = fv.astype(np.int64)
        x1 = np.minimum(x0 + 1, cols - 1); y1 = np.minimum(y0 + 1, rows - 1)
        ax = (fu - x0).astype(np.float32); ay = (fv - y0).astype(np.float32)
        idx = (y0 * cols + x0, y0 * cols + x1, y1 * cols + x0, y1 * cols + x1)
        wts = ((1 - ax) * (1 - ay), ax * (1 - ay), (1 - ax) * ay, ax * ay)
        self._sample_cache[key] = (idx, wts)
        return self._sample_cache[key]

    @staticmethod
    def _sample(src, sampler):
        idx, w = sampler
        return (src[idx[0]] * w[0] + src[idx[1]] * w[1]
                + src[idx[2]] * w[2] + src[idx[3]] * w[3])

    # ------------------------------------------------------------------
    def _effective_sides(self):
        """
        Her nöron için KULLANILABİLİR gövde tarafı.

        Koku (ORN) ve işitme (Johnston organı) nöronlarının somaları antendedir,
        yani görüntüleme hacminin DIŞINDA — tıpkı fotoreseptörler gibi konektomda
        somaSide alanları boştur.

        ÖNCEKİ HATA: tarafı bağlantıdan TAHMİN ediyorduk (bir ORN çoğunlukla sol
        antennal loba bağlanıyorsa sol sayılıyordu). Ama Drosophila ORN'leri
        HER İKİ antennal loba birden projekte eder, yani bu tahminin dayanağı
        yok. Ölçtük: tahmin ORN'lerde yalnızca %78,7, JO-A'da (ses nöronları)
        %50,0 tutturuyordu — yani sesin yönü YAZI TURA idi. Bazı glomerüller
        şanstan da kötüydü (ORN_DL3 %44, ORN_VA2 %53).

        Oysa doğru cevap konektomun kendi annotasyonunda duruyor: 'rootSide'
        alanı (yoksa 'instance' adının _L/_R soneki). Artık oradan okunuyor;
        bağlantı tahminine yalnızca ikisi de boşsa düşülüyor (409 ORN).
        """
        side = self.soma_side.copy()
        unknown = np.where(side < 0)[0]
        if len(unknown) == 0:
            return side

        # --- 1) KONEKTOMUN KENDİ CEVABI ---
        self._n_side_annot = 0
        try:
            import pyarrow.feather as ft
            _df = ft.read_table(ANNOT).select(
                ["bodyId", "rootSide", "instance"]).to_pandas()
            _rs, _in = {}, {}
            for _b, _r, _i in zip(_df["bodyId"], _df["rootSide"], _df["instance"]):
                _b = int(_b)
                if _r in ("L", "R"):
                    _rs[_b] = 0 if _r == "L" else 1
                elif isinstance(_i, str) and _i[-2:] in ("_L", "_R"):
                    _in[_b] = 0 if _i.endswith("_L") else 1
            for _i2 in unknown:
                _b = int(self.bodyIds[_i2])
                _v = _rs.get(_b, _in.get(_b))
                if _v is not None:
                    side[_i2] = _v
                    self._n_side_annot += 1
        except Exception as _e:
            print("[GerçekBeyin] rootSide okunamadı (%s), tahmine düşülüyor"
                  % type(_e).__name__)

        unknown = np.where(side < 0)[0]
        if len(unknown) == 0:
            self._n_side_derived = 0
            return side

        # --- 2) KALANLAR İÇİN bağlantı tahmini ---
        A = abs(self.W).tocsr()
        sL = (self.soma_side == 0).astype(np.float32)
        sR = (self.soma_side == 1).astype(np.float32)
        wl = A.T.dot(sL)
        wr = A.T.dot(sR)
        tot = wl + wr
        ok = unknown[tot[unknown] > 0]
        side[ok] = np.where(wl[ok] >= wr[ok], 0, 1).astype(np.int8)
        self._n_side_derived = int(len(ok))
        return side

    def _locate_sensory(self, verbose=True):
        """
        Koku (ORN) ve işitme (Johnston organı) nöronlarını GÖVDE TARAFINA göre
        indeksler. İkisi de gerçek MaleCNS hücreleridir; uydurma yoktur.

            ORN_*      : 53 gerçek glomerül tipinde koku reseptör nöronu
            JO-A / B   : ses ve titreşim (Kamikouchi ve ark. 2009, Nature)
            JO-C/E/F   : yerçekimi ve hava akımı (statik anten sapması)

        Sinek iki anteniyle duyar ve koklar; iki taraf arasındaki FARK yönü
        verir. Bu yüzden her grubu sol/sağ olarak ayrı tutuyoruz.
        """
        self._n_side_derived = 0
        self.side_eff = self._effective_sides()

        def _split(mask):
            ix = np.where(mask)[0]
            return (ix[self.side_eff[ix] == 0], ix[self.side_eff[ix] == 1])

        orn_m = np.array([t.startswith("ORN") for t in self.types])
        self.orn_L, self.orn_R = _split(orn_m)

        jo_snd = np.array([t.startswith("JO-A") or t.startswith("JO-B")
                           for t in self.types])
        jo_wnd = np.array([t.startswith("JO-C") or t.startswith("JO-E")
                           or t.startswith("JO-F") for t in self.types])
        self.jo_sound_L, self.jo_sound_R = _split(jo_snd)
        self.jo_wind_L, self.jo_wind_R = _split(jo_wnd)
        self.jo_idx = np.where(jo_snd | jo_wnd)[0]

        # --- OCELLI (basit gözler) ---
        # Sineğin petek gözlerinden ayrı, başının tepesinde ÜÇ basit gözü
        # vardır: bir medyan, iki yan. Uzamsal çözünürlükleri yok; çok hızlı
        # ışık ölçerdirler ve ufku/duruşu saptamaya yararlar.
        #
        # Bunu eklememizin sebebi bir tercih değil, ölçüm: tam konektomda
        # DNp20'nin (dönüş nöronumuz) girdisinin %43,6'sı OCG01 hücrelerinden
        # geliyor. OCG01'e hiçbir şey vermezsek DNp20 girdisinin yarısını
        # gürültü olarak alır ve dönüş kararı gürültüye döner — ölçtük, öyle
        # oluyordu.
        #
        # Ocellar fotoreseptörlerin somaları görüntüleme hacminin dışındadır
        # (petek göz fotoreseptörleri gibi), bu yüzden ışığı bir sinaps
        # ileriye, OCG01'in kendisine veriyoruz.
        ocg = np.array([t.startswith("OCG01") for t in self.types])
        self.ocg_L, self.ocg_R = _split(ocg)
        self.ocg_idx = np.where(ocg)[0]
        self.lh_idx = np.where(np.array([t.startswith("LH") for t in self.types]))[0]
        self.pn_idx = np.where(np.array([t.endswith("PN") for t in self.types]))[0]

        if verbose:
            print("[GerçekBeyin] gövde tarafı: %d nöron annotasyondan (rootSide), "
                  "%d nöron bağlantıdan tahmin"
                  % (getattr(self, "_n_side_annot", 0), self._n_side_derived))
            print("[GerçekBeyin] koku: %d ORN (sol %d / sağ %d), %d PN, %d lateral horn"
                  % (int(orn_m.sum()), len(self.orn_L), len(self.orn_R),
                     len(self.pn_idx), len(self.lh_idx)))
            print("[GerçekBeyin] işitme: %d Johnston organı nöronu "
                  "(ses sol %d / sağ %d, hava akımı %d)"
                  % (len(self.jo_idx), len(self.jo_sound_L), len(self.jo_sound_R),
                     len(self.jo_wind_L) + len(self.jo_wind_R)))
            print("[GerçekBeyin] ocelli: %d OCG01 hücresi (sol %d / sağ %d) "
                  "— DNp20'nin girdisinin %%44'ü" % (len(self.ocg_idx),
                                                     len(self.ocg_L), len(self.ocg_R)))

    def _locate_motor_sides(self, verbose=True):
        """
        İnen nöronların sol/sağ kimliği.

        ÖNCEKİ HATA: dizinin ilk yarısı "sol", ikinci yarısı "sağ" sayılıyordu.
        DNp20 toplam 2 nörondur (1 sol, 1 sağ) ve dizideki sıraları bodyId'ye
        göredir — yani sol/sağ ataması YAZI TURA idi. Dönüş yönü rastgele ters
        çıkabiliyordu. Artık konektomun kendi somaSide alanından okunuyor.
        """
        self.motor_side = {}
        for role, ix in self.motor_idx.items():
            self.motor_side[role] = (ix[self.soma_side[ix] == 0],
                                     ix[self.soma_side[ix] == 1])
        if verbose:
            for role in ("turn", "steer2"):
                l, r = self.motor_side[role]
                print("    %-7s %-8s sol %d / sağ %d nöron"
                      % (role, MOTOR_TYPES[role], len(l), len(r)))

    def _locate_kc_mbon(self):
        """KC -> MBON sinapslarının CSR içindeki yerini bulur (plastisite için)."""
        self.kc_mbon_slots = None
        if len(self.kc_idx) == 0 or len(self.mbon_idx) == 0:
            return
        kc_set = np.zeros(self.N, dtype=bool)
        kc_set[self.kc_idx] = True
        rows, slots, kcs = [], [], []
        W = self.W
        for r in self.mbon_idx:
            lo, hi = W.indptr[r], W.indptr[r + 1]
            cols = W.indices[lo:hi]
            m = kc_set[cols]
            if m.any():
                pos = np.arange(lo, hi)[m]
                slots.append(pos)
                kcs.append(cols[m])
                rows.append(np.full(pos.shape, r))
        if slots:
            self.kc_mbon_slots = np.concatenate(slots)
            self.kc_mbon_pre = np.concatenate(kcs)
            self.kc_mbon_post = np.concatenate(rows)
            self.kc_mbon_w0 = self.W.data[self.kc_mbon_slots].copy()
            # KC indeksini yerel konuma çevir (trace için)
            lookup = np.full(self.N, -1, dtype=np.int64)
            lookup[self.kc_idx] = np.arange(len(self.kc_idx))
            self.kc_mbon_local = lookup[self.kc_mbon_pre]

    # ------------------------------------------------------------------
    def inject_vision(self, retina, cols, rows, drive=1.15, ocellus_l=None, ocellus_r=None):
        """
        Retina (cols*rows RGB) -> GERÇEK fotoreseptörlere akım.

        Işık fotoreseptörü DEPOLARİZE eder (pozitif akım). Fotoreseptör
        histaminerjiktir, yani hedefini İNHİBE eder — işaret çevrimi
        ölçülmüş nörotransmitterden gelir, bizden değil.
        """
        arr = np.asarray(retina, dtype=np.float32)
        if arr.ndim == 2 and arr.shape[1] == 3:
            r_, g_, b_ = arr[:, 0] / 255.0, arr[:, 1] / 255.0, arr[:, 2] / 255.0
        else:
            r_ = g_ = b_ = arr.reshape(-1) / 255.0
        lum = 0.30 * r_ + 0.59 * g_ + 0.11 * b_
        # Naka-Rushton fotoreseptör adaptasyonu
        lum = lum ** 1.4 / (lum ** 1.4 + 0.35 ** 1.4)
        chan = {"lum": lum,
                "uv": np.clip(b_ * 1.25 - 0.3 * r_, 0.0, 1.0),
                "blue": b_, "green": g_}

        self.I_ext[:] = self.tonic
        self.I_ext[self.graded_mask] += np.float32(GRADED_REST_DRIVE)
        for t, kind in self.layer_kind.items():
            smp = self._sampler(t, cols, rows)
            self.I_ext[self.layer_idx[t]] += self._sample(chan[kind], smp) * drive

        # --- OCELLI: üst ve yan ışık gradyanı (meşale / gökyüzü) ---
        # Java ışın izleyicisinden (CompoundEyeRaytracer) gelen gerçek blok ve gökyüzü
        # ışık gradyanı doğrudan OCG01 nöronlarına aktarılır.
        if len(self.ocg_idx):
            if ocellus_l is not None and ocellus_r is not None:
                gl = float(ocellus_l)
                gr = float(ocellus_r)
            else:
                top = max(1, rows // 3)
                uvg = (0.45 * lum + 0.55 * chan["uv"]).reshape(rows, cols)[:top]
                half = cols // 2
                gl = float(uvg[:, :half].mean())     # üst-SOL görüş alanı
                gr = float(uvg[:, half:].mean())     # üst-SAĞ görüş alanı
            self.I_ext[self.ocg_L] += np.float32(gl * OCELLI_GAIN * drive)
            self.I_ext[self.ocg_R] += np.float32(gr * OCELLI_GAIN * drive)
            self.ocelli_lr = (gl, gr)

    def inject_type(self, type_name, current):
        ix = self.idx_of_type.get(type_name)
        if ix is not None and len(ix):
            self.I_ext[ix] += current

    def inject_indices(self, idx, current):
        if len(idx):
            self.I_ext[idx] += current

    # ------------------------------------------------------------------
    def _lif_step(self):
        self.I_syn *= self._ds
        # Graded hücreler spike atmaz; salgıları membran potansiyeliyle
        # SÜREKLİ orantılıdır. Spike'la aynı vektörde taşınır.
        act = self.spikes
        if self._n_graded:
            gv = (self.V[self.graded_mask] - self.V_REST) * self._g_norm
            np.clip(gv, 0.0, 1.6, out=gv)
            act = self._act_buf
            act[:] = self.spikes
            act[self.graded_mask] = gv * GRADED_SCALE
        if act.any():
            self.I_syn += self.W.dot(act)

        I = self.I_syn + self.I_ext
        if self.noise > 0:
            off = int(self.rng.integers(0, self._noise_n - self.N))
            I = I + self._noise_pool[off:off + self.N] * self.noise

        target = self.V_REST + self.R_M * I
        ready = self.refrac <= 0.0
        self.V = np.where(ready,
                          target + (self.V - target) * self._dm,
                          self.V_RESET).astype(np.float32)
        self.refrac[~ready] -= self.dt

        fired = self.V >= self.V_THRESH
        fired &= self._spiking_mask         # graded hücreler spike atmaz
        self.spikes = fired.astype(np.float32)
        if fired.any():
            self.V[fired] = self.V_RESET
            self.refrac[fired] = self.T_REFRAC
            self.spike_count += self.spikes

    def run_frame(self):
        self.spike_count[:] = 0.0
        kc_acc = (np.zeros(len(self.kc_idx), dtype=np.float32)
                  if len(self.kc_idx) else None)
        for _ in range(self.substeps):
            self._lif_step()
            if kc_acc is not None:
                kc_acc += self.spikes[self.kc_idx]
        if kc_acc is not None:
            self.kc_trace = 0.90 * self.kc_trace + 0.10 * (kc_acc / self.substeps)

    # ------------------------------------------------------------------
    def set_tonic(self, level, floor=None):
        """
        Tonik uyarım = taban + level x (alt-grafikte eksik olan girdi oranı)

        TABAN, nöronun içsel uyarılabilirliğidir. ON yolunun çalışması için
        şart: L1 glutamaterjik (inhibitör) olduğundan Mi1 ışıkla SERBEST
        KALARAK ateşler (disinhibisyon). Bastırılacak bir taban aktivite
        yoksa disinhibisyon mekanizması hiç çalışmaz.
        """
        self.tonic0 = float(level)
        if floor is not None:
            self.tonic_floor = float(floor)
        # TABANIN KAPSAMI
        # Taban, ON yolunun çalışması için kondu: L1 glutamaterjik (inhibitör)
        # olduğundan Mi1 ışıkla SERBEST KALARAK ateşler; bastırılacak bir taban
        # aktivite yoksa disinhibisyon hiç çalışmaz. Bu gerekçe OPTİK LOB için
        # geçerlidir. Aynı tabanı 118 bin nöronun hepsine vermek, girdisi zaten
        # neredeyse tam olan hücrelerde (ör. DNa02 %2 eksik) gerçek sinaptik
        # sinyali bastırır. "optic" kapsamı tabanı optik loba sınırlar.
        # ÖLÇÜLDÜ (yan yana karşılaştırma): tabanı optik loba sınırlamak her
        # açıdan kötü çıktı. LC4 tamamen susuyor (6,97 -> 0,02 Hz), sinek zar
        # zor yürüyor (24,9 -> 8,6 Hz), duvar etkisi yarıya iniyor (2,09 ->
        # 1,17). Sebebi: LC4 gibi hücreler sinaptik girdiden eşiğe ulaşamıyor
        # -- konektom sinaptik GÜCÜ içermediği için. Varsayılan "all" kalır.
        floor = np.full(self.N, np.float32(self.tonic_floor), dtype=np.float32)
        if self.floor_scope == "optic":
            floor *= self._optic_mask
        self.tonic = (floor + self.missing_input * np.float32(level)).astype(np.float32)
        self.tonic *= self.tonic_scale
        self.tonic[self.graded_mask] = 0.0
        # Giant Fiber ölçülmüş değerini korur (calibrate_giant_fiber)
        _gf = getattr(self, "gf_tonic", None)
        if _gf is not None and len(self.motor_idx["escape"]):
            self.tonic[self.motor_idx["escape"]] = np.float32(_gf)

    def calibrate(self, target_hz=2.0, iters=18, verbose=True, lo=0.0, hi=1.4):
        """
        TEK bir skaler tonik seviyesi aranır: duyu girdisi yokken popülasyonun
        ortalama ateşleme hızı target_hz olacak şekilde.

        Nöron başına ayrı ayar YAPILMAZ — o, konektomun doğal heterojenliğini
        (özellikle Kenyon hücrelerinin seyrekliğini) silerdi. Tek parametre,
        tek varsayım; nöronlar arası fark tamamen ölçülmüş bağlantıdan gelir.
        """
        def probe(level, frames=3):
            self.set_tonic(level)
            self.V[:] = self.V_REST
            self.I_syn[:] = 0.0
            self.spikes[:] = 0.0
            tot = 0.0
            for _ in range(frames):
                self.I_ext[:] = self.tonic
                self.I_ext[self.graded_mask] += np.float32(GRADED_REST_DRIVE)
                self.spike_count[:] = 0.0
                for _ in range(self.substeps):
                    self._lif_step()
                tot += self.mean_rate
            return tot / frames

        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            r = probe(mid)
            if r < target_hz:
                lo = mid
            else:
                hi = mid
        level = 0.5 * (lo + hi)
        r = probe(level)
        self.set_tonic(level)
        self.calibrated = True
        if verbose:
            print("    tonik seviyesi %.4f -> taban %.2f Hz (hedef %.1f)"
                  % (level, r, target_hz))
        return level

    def calibrate_steering(self, cols=64, rows=24, locomotor=0.60,
                           warm=25, frames=45, verbose=True):
        """
        Simetrik uyaranda dönüş torku sıfır olmalıdır.

        Düz gri bir alan gösterip (sol ve sağ göze tamamen aynı girdi) kalan
        torku ölçer ve sabit sapma olarak kaydeder. Bu sapma konektomun
        eksik rekonstrüksiyonundan gelir, sineğin kararından değil.
        """
        self.steer_bias = 0.0
        grey = np.full((cols * rows, 3), 128.0, dtype=np.float32)
        acc = []
        for i in range(warm + frames):
            self.inject_vision(grey, cols, rows, drive=1.15)
            self.inject_indices(self.motor_idx["forward"], np.float32(locomotor))
            self.inject_indices(self.motor_idx["turn"], np.float32(locomotor * 0.45))
            self.inject_indices(self.motor_idx["steer2"], np.float32(locomotor * 0.45))
            self.run_frame()
            m = self.decode_motor()
            if i >= warm:
                acc.append(m["steering_torque"] / 1.8)
        self.steer_bias = float(np.mean(acc)) if acc else 0.0
        if verbose:
            print("[GerçekBeyin] dönüş sapması ölçüldü: %+.4f "
                  "(sol/sağ rekonstrüksiyon farkı) -> sıfırlandı" % self.steer_bias)
        return self.steer_bias

    # ------------------------------------------------------------------
    #  DÖNÜŞ İŞARETİNİN ÖLÇÜLMESİ
    # ------------------------------------------------------------------
    #  Konektom bize DNp20'nin sol ve sağ hücresinin kime bağlandığını
    #  söyler. "Sol DNp20 ateşlerse sinek hangi yöne döner" sorusunu
    #  SÖYLEMEZ — bu davranışsal bir olgudur ve ancak davranıştan bilinir.
    #
    #  Bu yüzden işareti literatürden tahmin etmek yerine, modelin ölçülmüş
    #  iki klasik sinek davranışını üretmesini şart koşuyoruz:
    #
    #    1. OPTOMOTOR  — sağa kayan desende sinek sağa döner
    #                    (Hassenstein & Reichardt 1956; Götz 1964)
    #    2. FOTOTAKSİ  — sinek aydınlığa doğru yürür
    #                    (Benzer 1967, karşı-akım deneyi)
    #
    #  Hangisi ölçülebilir bir etki verirse işaret ondan belirlenir; ikisi de
    #  gürültünün altında kalırsa işaret DEĞİŞTİRİLMEZ ve bu açıkça bildirilir.
    # ------------------------------------------------------------------
    def _turn_probe(self, make_frame, cols, rows, locomotor, warm, frames, reps):
        vals = []
        for _ in range(reps):
            self.V[:] = self.V_REST
            self.I_syn[:] = 0.0
            self.spikes[:] = 0.0
            self.motor_smooth = {}
            for i in range(warm):
                self.sense(make_frame(i), cols, rows, locomotor=locomotor)
            acc = []
            for i in range(warm, warm + frames):
                m = self.sense(make_frame(i), cols, rows, locomotor=locomotor)
                acc.append(m["steering_torque"] / 1.8)
            vals.append(float(np.mean(acc[6:])))
        return np.array(vals)

    @staticmethod
    def _effect(a, b):
        d = float(b.mean() - a.mean())
        p = float(np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)) if len(a) > 1 else 0.0
        return d, (abs(d) / p if p > 1e-9 else 0.0)

    def calibrate_turn_sign(self, cols=64, rows=24, locomotor=0.60,
                            warm=18, frames=26, reps=4, verbose=True):
        self.steer_sign = 1.0
        X = np.arange(cols, dtype=np.float32)[None, :] + np.zeros((rows, 1), np.float32)

        # --- 1. OPTOMOTOR: kayan çizgi deseni ---
        def grating(speed):
            def f(i):
                v = 0.5 + 0.45 * np.sin(2 * np.pi * (X - i * speed) / 11.0)
                return np.repeat((v * 255.0).reshape(-1, 1), 3, axis=1).astype(np.float32)
            return f

        # Sütun 0 SOL gözdür; faz artarken desen ekranda SAĞA kayar.
        om_r = self._turn_probe(grating(+2.2), cols, rows, locomotor, warm, frames, reps)
        om_l = self._turn_probe(grating(-2.2), cols, rows, locomotor, warm, frames, reps)
        om_d, om_e = self._effect(om_l, om_r)

        # --- 2. FOTOTAKSİ: bir taraf aydınlık, öbürü karanlık ---
        def split(bright_left):
            img = np.zeros((rows, cols, 3), dtype=np.float32)
            half = cols // 2
            img[:, :half] = 225.0 if bright_left else 35.0
            img[:, half:] = 35.0 if bright_left else 225.0
            flat = img.reshape(-1, 3)
            return lambda i: flat

        ph_l = self._turn_probe(split(True), cols, rows, locomotor, warm, frames, reps)
        ph_r = self._turn_probe(split(False), cols, rows, locomotor, warm, frames, reps)
        # aydınlık SAĞDA iken sinek SAĞA dönmeli -> (sağ - sol) pozitif olmalı
        ph_d, ph_e = self._effect(ph_l, ph_r)

        self.sign_evidence = {"optomotor_diff": om_d, "optomotor_effect": om_e,
                              "phototaxis_diff": ph_d, "phototaxis_effect": ph_e}

        src, diff, eff = None, 0.0, 0.0
        if om_e >= 1.2 and abs(om_d) > 0.008:
            src, diff, eff = "optomotor", om_d, om_e
        elif ph_e >= 1.2 and abs(ph_d) > 0.008:
            src, diff, eff = "fototaksi", ph_d, ph_e

        if src:
            self.steer_sign = 1.0 if diff > 0 else -1.0
            note = "%s ile belirlendi (etki %.1f) -> işaret %+.0f" % (src, eff, self.steer_sign)
        else:
            note = "iki ölçüm de gürültünün altında -> işaret DEĞİŞTİRİLMEDİ"

        if verbose:
            print("[GerçekBeyin] optomotor  sağa %+.4f sola %+.4f (fark %+.4f, etki %.1f)"
                  % (om_r.mean(), om_l.mean(), om_d, om_e))
            print("[GerçekBeyin] fototaksi  ışık sağda %+.4f solda %+.4f (fark %+.4f, etki %.1f)"
                  % (ph_r.mean(), ph_l.mean(), ph_d, ph_e))
            print("[GerçekBeyin] dönüş işareti: %s" % note)
        return self.steer_sign

    # ------------------------------------------------------------------
    def calibrate_all(self, target_hz=2.0, cache=True, verbose=True):
        """
        Üç kalibrasyonu sırayla yapar ve sonucu diske yazar.

            1. tonik seviye     — ağ dinlenme hızı
            2. dönüş sapması    — sol/sağ rekonstrüksiyon farkı
            3. dönüş işareti    — ölçülmüş sinek davranışından

        Sonuç önbelleğe alınır: bunlar ağın sabit özellikleridir, her
        çalıştırmada bir dakika harcamaya gerek yok. Konektom dosyası
        değişirse önbellek geçersiz olur.
        """
        import hashlib
        import json
        path = self.graph_path + ".calib.json"
        # Gövde tarafı vektörü de anahtara girer: dönüş sapması ve dönüş
        # işareti sol/sağ atamasına bağlıdır, atama değişince eski değerler
        # geçersizdir.
        _sid = getattr(self, "side_eff", self.soma_side)
        key = "v%d-%d-%d-%.4f-%.4f-%.4f-%.2f-%s-%d-%.3f" % (
            MODEL_VERSION, self.N, self.W.nnz, float(self.W.data[:4096].sum()),
            self.tonic_floor, self.noise, target_hz, self.floor_scope,
            int(np.sum(_sid.astype(np.int64) * np.arange(1, len(_sid) + 1)) % 10**9),
            STEER2_WEIGHT)
        key = hashlib.md5(key.encode()).hexdigest()[:16]

        if cache and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("key") == key:
                    self.set_tonic(d["tonic_level"])
                    self.calibrated = True
                    self.gf_tonic = float(d.get("gf_tonic", 0.0))
                    if len(self.motor_idx["escape"]):
                        self.tonic[self.motor_idx["escape"]] = np.float32(self.gf_tonic)
                    self.steer_bias = float(d["steer_bias"])
                    self.steer_sign = float(d["steer_sign"])
                    self.sign_evidence = d.get("evidence", {})
                    if verbose:
                        print("[GerçekBeyin] kalibrasyon önbellekten: tonik %.4f, "
                              "sapma %+.4f, işaret %+.0f"
                              % (d["tonic_level"], self.steer_bias, self.steer_sign))
                    return
            except Exception:
                pass

        self.calibrate(target_hz=target_hz, verbose=verbose)
        self.calibrate_giant_fiber(verbose=verbose)
        self.calibrate_steering(verbose=verbose)
        self.calibrate_turn_sign(verbose=verbose)
        if cache:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"key": key, "tonic_level": self.tonic0,
                               "gf_tonic": getattr(self, "gf_tonic", 0.0),
                               "steer_bias": self.steer_bias,
                               "steer_sign": self.steer_sign,
                               "evidence": self.sign_evidence}, f, indent=2)
            except Exception:
                pass

    def calibrate_giant_fiber(self, cols=64, rows=24, locomotor=0.60,
                              quiet_hz=0.4, verbose=True):
        """
        DNp01'in (Giant Fiber) tonik uyarımını ÖLÇEREK ayarlar.

        Giant Fiber dinlenmede ateşlemez — eşiği yüksektir, ancak güçlü ve
        çakışan looming girdisiyle tetiklenir (Card & Dickinson 2008). Tonik
        uyarımını sıfırlarsak sinek durup dururken zıplamaz ama looming'i de
        hiç duyamaz; yüksek verirsek sebepsiz zıplar.

        Doğru değer ölçülebilir: sabit bir sahnede DNp01'i hâlâ SESSİZ bırakan
        EN YÜKSEK tonik uyarım. Bu, onu sessiz tutarken duyarlılığını en üste
        çeker. İkili arama ile buluyoruz.
        """
        gf = self.motor_idx["escape"]
        if not len(gf):
            return 0.0
        flat = np.full((rows * cols, 3), 128.0, dtype=np.float32)

        def rest_rate(scale, warm=10, n=14):
            self.tonic[gf] = np.float32(scale)
            self.V[:] = self.V_REST
            self.I_syn[:] = 0.0
            self.spikes[:] = 0.0
            self.motor_smooth = {}
            for _ in range(warm):
                self.sense(flat, cols, rows, locomotor=locomotor)
            acc = []
            for _ in range(n):
                self.sense(flat, cols, rows, locomotor=locomotor)
                acc.append(self.rate(gf))
            return float(np.mean(acc))

        lo, hi = 0.0, float((self.V_THRESH - self.V_REST) / self.R_M)
        if rest_rate(hi) <= quiet_hz:
            best = hi
        else:
            best = 0.0
            for _ in range(10):
                mid = 0.5 * (lo + hi)
                if rest_rate(mid) <= quiet_hz:
                    best, lo = mid, mid
                else:
                    hi = mid
        # Güvenlik payı: gürültünün ara sıra eşiği aşmasına izin verme
        best *= 0.90
        self.gf_tonic = best
        self.tonic[gf] = np.float32(best)
        if verbose:
            print("[GerçekBeyin] Giant Fiber tonik uyarımı %.4f "
                  "(sessiz kaldığı en yüksek değer; dinlenme %.2f Hz)"
                  % (best, rest_rate(best)))
        self.tonic[gf] = np.float32(best)
        return best

    def _sided(self, tname):
        """Bir nöron tipinin sol/sağ indisleri (gövde tarafı konektomdan)."""
        ix = self.idx_of_type.get(tname, np.array([], dtype=int))
        if not len(ix):
            return np.array([], dtype=int), np.array([], dtype=int)
        side = self.soma_side[ix]
        return ix[side == 0], ix[side == 1]

    def _turn_to(self, want_right):
        """
        İstenen dünya dönüş yönüne göre sürülecek inen nöron (DN) grubunu seçer.
        steer_sign fototaksi kalibrasyonundan türetilir: tork = (sağ - sol) * steer_sign.
        Dönüş tarafı kalibre edilmiş katsayı işaretine göre belirlenir.

        want_right > 0  ->  dünyada SAĞA dönmek isteniyor.
        """
        l, r = self.motor_side["turn"]
        l2, r2 = self.motor_side["steer2"]
        return (r, r2) if (want_right > 0) == (self.steer_sign > 0) else (l, l2)

    def inject_loom(self, level, bearing):
        """
        YAKLAŞAN CİSİM -> looming dedektörü nöronlarına (LC4 / LPLC2).

        NEDEN DOĞRUDAN: ölçüldü (30 tur looming vs sabit sahne):
            LPLC2  Cohen d +0,82   — görüyor
            LC4    Cohen d -0,54   — TERS yönde, looming'de azalıyor
            DNp04  Cohen d +0,12   — girdisinin %57'si LC4 olduğu için
                                      bozuk sinyali miras alıyor
        Hata LC4'ün kendisinde değil, onu besleyen T4/T5 yön seçiciliğinde:
        konektom sinaptik GÜÇ içermediği için hareket algısı zayıf kalıyor
        (README'de "bilinen eksik" olarak duruyor).

        Eksik olan İŞLEM AŞAMASINI atlıyoruz: büyüme sinyalini doğrudan
        dedektöre veriyoruz. Işığı fotoreseptöre, kokuyu ORN'e, sesi
        Johnston organına basmakla aynı kategoride bir varsayım.
        KARAR hâlâ ağın: DNp04/DNp01/MDN ateşlerse kaçar, ateşlemezse kaçmaz.

        level   : 0..1 yakınlık/büyüme şiddeti
        bearing : radyan, + = SOL (cisim solda ise sol lobula sürülür)
        """
        if level <= 0.0:
            self.loom_lr = (0.0, 0.0)
            return
        b = float(np.clip(bearing / (np.pi / 2.0), -1.0, 1.0))
        gl = level * (0.55 + 0.45 * b)          # cisim solda -> sol göz
        gr = level * (0.55 - 0.45 * b)
        gl = max(0.0, gl); gr = max(0.0, gr)
        for ixs, amp in ((self.lc4_L, gl), (self.lc4_R, gr)):
            if len(ixs):
                self.inject_indices(ixs, np.float32(amp * LOOM_GAIN))
        for ixs, amp in ((self.lplc2_L, gl), (self.lplc2_R, gr)):
            if len(ixs):
                self.inject_indices(ixs, np.float32(amp * LOOM_GAIN * 0.8))
        self.loom_lr = (gl, gr)

    def rate(self, idx):
        """Ateşleme hızı (Hz)."""
        if len(idx) == 0:
            return 0.0
        return float(self.spike_count[idx].sum()) / len(idx) / (self.frame_ms / 1000.0)

    def rate_of_type(self, tname):
        return self.rate(self.idx_of_type.get(tname, np.array([], dtype=int)))

    def learn(self, reward, punish, lr=0.0009):
        """
        3-faktör plastisite: Δw = η · [DA(t) − DA_taban] · e_ij(t)
        Yalnızca GERÇEK KC->MBON sinapsları değişir; grafiğin geri kalanı sabittir.
        """
        if self.kc_mbon_slots is None:
            return 0.0
        da = float(reward) - 0.8 * float(punish)
        self.da_baseline = 0.98 * self.da_baseline + 0.02 * da
        rpe = da - self.da_baseline
        if abs(rpe) > 0.04:
            e = self.kc_trace[self.kc_mbon_local]
            self.W.data[self.kc_mbon_slots] += (lr * rpe) * e * np.sign(self.kc_mbon_w0)
            # ölçülmüş ağırlığın ±%60'ı sınır: konektom yapısı korunur
            lim = np.abs(self.kc_mbon_w0) * 1.6
            np.clip(self.W.data[self.kc_mbon_slots], -lim, lim,
                    out=self.W.data[self.kc_mbon_slots])
        return rpe

    def save_memory(self, filepath):
        """Mantar cisimciği öğrenilmiş KC->MBON sinaps ağırlıklarını diske kaydeder."""
        if self.kc_mbon_slots is None:
            return False
        try:
            weights = self.W.data[self.kc_mbon_slots].copy()
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            np.savez_compressed(filepath, kc_mbon_weights=weights, da_baseline=self.da_baseline)
            return True
        except Exception as e:
            print("[GerçekBeyin] Bellek kaydedilirken hata:", e)
            return False

    def load_memory(self, filepath):
        """Daha önce öğrenilmiş KC->MBON ağırlıklarını diskten yükler."""
        if self.kc_mbon_slots is None or not os.path.exists(filepath):
            return False
        try:
            data = np.load(filepath)
            if "kc_mbon_weights" in data:
                saved_w = data["kc_mbon_weights"]
                if len(saved_w) == len(self.kc_mbon_slots):
                    self.W.data[self.kc_mbon_slots] = saved_w
                    if "da_baseline" in data:
                        self.da_baseline = float(data["da_baseline"])
                    print("[GerçekBeyin] 💾 Bellek yüklendi: %s (%d sinaps)" % (filepath, len(saved_w)))
                    return True
        except Exception as e:
            print("[GerçekBeyin] Bellek yüklenirken hata:", e)
        return False

    def reset_memory(self, filepath=None):
        """Mantar cisimciği KC->MBON sinaps ağırlıklarını orijinal taban konektom değerine sıfırlar."""
        if self.kc_mbon_slots is not None and getattr(self, "kc_mbon_w0", None) is not None:
            self.W.data[self.kc_mbon_slots] = self.kc_mbon_w0.copy()
            self.da_baseline = 0.0
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print("[GerçekBeyin] 🗑️ Bellek dosyası silindi:", filepath)
                except Exception as e:
                    print("[GerçekBeyin] Bellek dosyası silinirken hata:", e)
            print("[GerçekBeyin] 🔄 Bellek sıfırlandı (taban konektom ağırlıklarına döndü).")
            return True
        return False

    # ------------------------------------------------------------------
    def sense(self, retina, cols, rows, drive=1.15,
              mechano=0.0, pain=0.0, reward=0.0, punish=0.0, odor=0.0,
              odor_l=None, odor_r=None, sound=0.0, sound_bearing=0.0,
              wind=0.0, hazard_bearing=None, obstacle=0.0, load=0.0,
              taste=0.0, loom=0.0, loom_bearing=0.0, locomotor=0.55,
              heat=0.0, ocellus_l=None, ocellus_r=None, cold=0.0,
              is_raining=False):
        """
        Tam duyusal kare: görüntü + mekanoreseptör + dopamin.

        MEKANORESEPTÖR ENJEKSİYONU (tehlikeli blok, çarpma, acı):
        Gerçek sinekte bacak mekanoreseptörleri ve nosiseptörler ventral sinir
        kordonu üzerinden inen nöronları etkiler. Alt-grafiğimizde VNC devresi
        yok, bu yüzden sinyali doğrudan o nöronların KENDİSİNE veriyoruz:
            MDN    <- geri çekilme (Bidaye ve ark. 2014: MDN geri yürütür)
            DNp09  <- kaçış lokomosyonu
            DNp01  <- acı/çarpma anında Giant Fiber sıçraması
        Bu, görüntüyü fotoreseptöre basmakla aynı kategoride bir varsayımdır.

        DOPAMİN: PAM (ödül) ve PPL1 (ceza) kümeleri gerçek nöronlardır ve
        mantar cisimciğine gerçek bağlantılarıyla projekte ederler.
        """
        self.inject_vision(retina, cols, rows, drive=drive,
                           ocellus_l=ocellus_l, ocellus_r=ocellus_r)

        # LOKOMOTOR DÜRTÜ (modelleme varsayımı)
        # Gerçek sinekte yürüme kararı, oktopaminerjik uyarılmışlık durumundan
        # ve modellemediğimiz üst düzey devrelerden gelir; sinek "sebepsiz"
        # yürür. Alt-grafikte bu yok, o yüzden DNpe017'ye sabit bir taban
        # dürtü veriyoruz. YÖN buradan gelmez — yönü görsel devre belirler.
        if locomotor > 0.0:
            # UYARILMIŞLIK, mantar cisimciğinin koku okumasından sürülüyor.
            # Bir önceki karenin değeri kullanılır (50 ms gecikme) — sinyal
            # ağın kendi çıktısı olduğu için aynı karede kullanılamaz.
            # Koku VAR -> +  (hızlan, düzleş) ; koku KAYBOLDU -> −  (yavaşla).
            _ar = float(self.odor_now) - max(float(self.odor_lost),
                                             float(self.odor_drop))
            _ar = float(np.clip(_ar, -1.0, 1.0))
            _fwd = locomotor * (1.0 + AROUSAL_FWD_GAIN * _ar)
            _trn = locomotor * 0.45 * (1.0 - AROUSAL_TURN_DROP * max(0.0, _ar))
            self.arousal = _ar
            self.inject_indices(self.motor_idx["forward"], np.float32(_fwd))
            self.inject_indices(self.motor_idx["turn"], np.float32(_trn))
            self.inject_indices(self.motor_idx["steer2"], np.float32(_trn))

            # ARAMA (CAST): koku AZALIYOR ya da kayboldu -> yavaşla + tara.
            # Koku yeniden artınca tarama söner ve surge devreye girer —
            # sineği kaynağa götüren şey dönüşün yönü değil, DURMA ölçütüdür.
            # ÖLÇÜLDÜ (arena, 20 deneme, eşleştirilmiş): sağa-sola SALINAN
            # sürüm işe yaramadı (−0,2 m); "koku artana kadar aynı yönde
            # dön" sürümü en yakın mesafeyi 7,2 -> 3,7 m'ye indirdi ve
            # varış 0/14'ten 3/14'e çıktı.
            _lost = max(getattr(self, "odor_lost", 0.0),
                        getattr(self, "odor_drop", 0.0))
            if _lost > 0.02:
                # Dönüş yönü bir KARAR değil: sinek kokunun yönünü bilmez
                # (ölçüldü — dönüş nöronlarının koku girdisi %0,000 ve
                # DNa02 ağırlığı 0,25'ten 3,0'a taranınca etki gürültüde
                # kaldı: d +0,30 / +0,17 / −0,10 / +0,20 / −0,12).
                # Bir tarafa dönülür ve koku ARTMAYA BAŞLAYANA KADAR o
                # tarafta kalınır; durduran şey yön bilgisi değil, kokunun
                # kendisidir. Bir sonraki arama ters tarafa başlar.
                if self.cast_side == 0.0:
                    self._cast_flip = -getattr(self, "_cast_flip", 1.0)
                    self.cast_side = self._cast_flip
                _amp = np.float32(_lost * CAST_GAIN)
                t1, t2 = self._turn_to(self.cast_side)
                self.inject_indices(t1, _amp)
                self.inject_indices(t2, _amp * 0.6)
                # tarayan sinek yavaşlar (Álvarez-Salvado 2018) ama durmaz
                self.inject_indices(self.motor_idx["forward"],
                                    np.float32(-_lost * locomotor * 0.20))
                self.cast_drive = float(_lost * self.cast_side)
            else:
                self.cast_side = 0.0          # koku arttı -> tarama bitti
                self.cast_drive = 0.0

        # MEKANO = acı veren / geçilemez durum -> geri yürüyüş (MDN)
        # ENGEL  = önümde bir şey var -> DÖNÜŞ. İkisi ayrı olmalı: gerçek sinek
        # duvara geldiğinde geri vitese takmaz, döner. Geri yürüyüş (moonwalk)
        # antenle sert temas ve nosiseptif durumlara aittir.
        if mechano > 0.0:
            self.inject_indices(self.motor_idx["backward"],
                                np.float32(mechano * MECH_MDN_GAIN))
            self.inject_indices(self.motor_idx["fast"], np.float32(mechano * 0.55))
            self.inject_indices(self.motor_idx["forward"], np.float32(-mechano * 0.85))
        if obstacle > 0.0:
            # Hafifçe yavaşlat; yön aşağıdaki dönüş bloğundan gelir.
            # Fazla bastırırsak sinek dönerken hiç ilerlemez ve köşede
            # yerinde fırıl fırıl döner — ölçüldü, 0.45 ile öyle oluyordu.
            self.inject_indices(self.motor_idx["forward"], np.float32(-obstacle * 0.18))
        if load > 0.0:
            # BACAK YÜK RESEPTÖRLERİ (kampaniform sensilla).
            # "İtiyorum ama ilerlemiyorum" — bu GÖRSEL değil proprioseptif bir
            # sinyaldir ve gerçek sinekte yürüme dürtüsünü keser. Log ölçümü:
            # duvara yaslanan sinek ileri itişi 0.94'te tutuyordu, yani duvara
            # tam güç bastırıyordu. Gerçek sinek bastırmayı bırakır.
            self.inject_indices(self.motor_idx["forward"], np.float32(-load * 1.05))
            self.inject_indices(self.motor_idx["backward"], np.float32(load * 0.30))
        if pain > 0.0:
            # Nosiseptif acı kaçış refleksi: Kafa konektomunda torasik VNC refleks
            # yayları bulunmadığından, acı uyarımı doğrudan kaçış (escape) ve geri çekilme
            # (backward) motor nöronlarına iletilir.
            self.inject_indices(self.motor_idx["escape"], np.float32(pain * 2.2))
            self.inject_indices(self.motor_idx["backward"], np.float32(pain * 1.5))

        # --- TEHLİKEDEN DÖNEREK KAÇMA (Nosiseptif Dönüş Manevrası) ---
        # Drosophila nosiseptif kaçış tepkisi dönüş manevrası içerir (Card & Dickinson 2008).
        # Engellerden ve darbelerden kaçış için dönüş nöronlarına asimetrik uyarı verilir.
        _avoid = max(float(mechano), float(obstacle), float(load) * 0.55,
                     float(loom) * 0.9)
        _is_loom = loom > 0.05
        if _is_loom:
            hazard_bearing = float(loom_bearing)
        if hazard_bearing is not None and _avoid > 0.0:
            if _is_loom:
                # Tehdit arkaya alınana kadar kaçış dönüşü sürer.
                # İstenen yönelim (tehdidin tersi) ile mevcut açısal hata hesaplanır:
                _e = math.atan2(math.sin(hazard_bearing + math.pi),
                                math.cos(hazard_bearing + math.pi))
                b = -_e / math.pi                     # + = sağa dön
                if abs(hazard_bearing) < 0.35 and self._esc_side != 0:
                    b = self._esc_side * abs(b)       # önde: seçilen yöne bağlı kal
                elif abs(b) > 0.15:
                    self._esc_side = 1 if b > 0 else -1
            else:
                b = float(np.clip(hazard_bearing / (np.pi / 2.0), -1.0, 1.0))
                self._esc_side = 0
            gain = TURN_AWAY_GAIN if mechano >= obstacle else OBSTACLE_TURN_GAIN
            amp = np.float32(_avoid * gain)
            t1, t2 = self._turn_to(+1.0 if b > 0 else -1.0)
            self.inject_indices(t1, amp * abs(b))
            self.inject_indices(t2, amp * 0.6 * abs(b))
            # Tehdit arkada kaldıkça kaçış sürati artırılır
            if _is_loom:
                self.inject_indices(self.motor_idx["forward"],
                                    np.float32(_avoid * (1.0 - abs(b)) * 1.10))
        elif not _is_loom:
            self._esc_side = 0
        # --- KOKU: gerçek ORN'lere, iki antene AYRI ---
        # Eskiden koku doğrudan "ileri yürü" nöronuna basılıyordu: sinek kokuyu
        # alıyor ama yönünü bilmiyordu, elmanın yanından geçip gidiyordu.
        # Artık koku gerçek koku reseptör nöronlarına giriyor; oradan gerçek
        # PN'lere, lateral horn'a ve mantar cisimciğine kendi kablolarıyla
        # yayılıyor. Yönelim iki anten arasındaki FARKTAN doğuyor — sinekte
        # olduğu gibi.
        if odor_l is None and odor_r is None and odor > 0.0:
            odor_l = odor_r = odor
        ol = float(odor_l or 0.0)
        orr = float(odor_r or 0.0)
        # UYUM (adaptasyon): reseptör sabit kokuya alışır, çıktısı konsantrasyon
        # DEĞİŞİMİNİ izler. Bu sayede "yaklaşıyorum" ile "uzaklaşıyorum" ayrı
        # sinyaller olur — sineğin kokuyu bulabilmesinin tek yolu bu.
        # Uyum seviyesi düşük-geçiren bir izdir; ondan geriye kalan FAZİK kısım
        # reseptöre gider. Tam çıkarma yapmıyoruz (K<1): gerçek ORN de sabit
        # kokuya sıfır tepki vermez, azalmış bir tonik tepki sürdürür.
        _a = self._orn_a
        self.orn_adapt_l = _a * self.orn_adapt_l + (1.0 - _a) * ol
        self.orn_adapt_r = _a * self.orn_adapt_r + (1.0 - _a) * orr
        # KAPANMA (OFF) TEPKİSİ: sıfırda kırpmıyoruz. Gerçek ORN'in kendiliğinden
        # bir taban aktivitesi vardır ve koku KESİLİNCE bu tabanın ALTINA iner
        # (Nagel & Wilson 2011, Şek. 2). Bu, "kokuyu kaybettim" sinyalidir ve
        # sineğin arama davranışının tetikleyicisidir: koku varken ileri atılır
        # (surge), koku kaybolunca yavaşlar ve dönmeye başlar (cast) —
        # Álvarez-Salvado ve ark. 2018. Biz max(0,...) ile kırptığımız sürece
        # sinek kokuyu kaybettiğini HİÇ öğrenemiyordu.
        pl = float(np.clip((ol - ORN_ADAPT_K * self.orn_adapt_l) * ORN_ADAPT_GAIN,
                           -ORN_OFF_LIMIT, 4.0))
        pr = float(np.clip((orr - ORN_ADAPT_K * self.orn_adapt_r) * ORN_ADAPT_GAIN,
                           -ORN_OFF_LIMIT, 4.0))
        self.odor_phasic = (pl, pr)
        if pl != 0.0:
            self.inject_indices(self.orn_L, np.float32(pl * ODOR_GAIN))
        if pr != 0.0:
            self.inject_indices(self.orn_R, np.float32(pr * ODOR_GAIN))

        # --- İŞİTME: gerçek Johnston organı nöronlarına ---
        # Ses basıncı iki antene de gelir; kaynağın yönü şiddet farkını yaratır.
        if sound > 0.0 and len(self.jo_sound_L):
            b = float(np.clip(sound_bearing / (np.pi / 2.0), -1.0, 1.0))
            gl = sound * (0.55 + 0.45 * b)      # + yön = sol
            gr = sound * (0.55 - 0.45 * b)
            self.inject_indices(self.jo_sound_L, np.float32(max(0.0, gl) * SOUND_GAIN))
            self.inject_indices(self.jo_sound_R, np.float32(max(0.0, gr) * SOUND_GAIN))
        # Hava akımı / kendi hareketi -> JO-C/E (statik sapma)
        if wind > 0.0 and len(self.jo_wind_L):
            self.inject_indices(self.jo_wind_L, np.float32(wind * WIND_GAIN))
            self.inject_indices(self.jo_wind_R, np.float32(wind * WIND_GAIN))

        # --- YAKLAŞAN CİSİM: looming dedektörlerine ---
        self.inject_loom(float(loom), float(loom_bearing))

        # --- TAT: ayak tat reseptörlerine (tarsal GRN) ---
        # Sinek yemeğin üstünde/elinde tutuyorsa ayağı şekeri tadar. Buradan
        # gerçek sinapslarla MN9'a (proboscis uzatma) gider ve hortum uzar.
        # Açlık bir KARAR değil, bir KAZANÇTIR: aç sinekte PER eşiği düşer
        # (Dethier 1976; Inagaki ve ark. 2012 dopaminerjik modülasyon).
        # Yani "yemeli mi" kararını biz vermiyoruz, ağ veriyor.
        if taste > 0.0 and len(self.grn_idx):
            self.inject_indices(self.grn_idx, np.float32(taste * TASTE_GAIN))

        # --- SICAKLIK VE SOĞUKLUK: termosensör projeksiyon nöronlarına ---
        # Gerçek sinek 31 °C üstünden ve aşırı soğuk/buzdan şiddetle kaçar (Hamada 2008, Gallio 2011).
        # Alt-grafikte sıcaklık/nem/soğukluk PN'leri var (VP1/VP2/VP3 hattı).
        if heat > 0.0 and len(self.thermo_idx):
            self.inject_indices(self.thermo_idx, np.float32(heat * HEAT_GAIN))
        if cold > 0.0 and len(self.thermo_idx):
            self.inject_indices(self.thermo_idx, np.float32(cold * HEAT_GAIN * 0.75))

        if cold > 0.35:
            punish = max(punish, float(cold) * 0.85)

        if reward > 0.0 and len(self.pam_idx):
            self.inject_indices(self.pam_idx, np.float32(reward * 1.8))
        if punish > 0.0 and len(self.ppl1_idx):
            self.inject_indices(self.ppl1_idx, np.float32(punish * 1.8))

        self.run_frame()
        rpe = self.learn(reward, punish)
        m = self.decode_motor()
        m["rpe"] = rpe

        # DOPAMİN TABANI
        # PAM ve PPL1 tonik olarak aktiftir (ölçüm: hiçbir şey olmazken
        # PPL1 3,16 Hz, PAM 3,29 Hz). Mutlak hız "sinek korkuyor" demek
        # DEĞİLDİR; anlam taşıyan şey tabandan sapmadır — learn() de zaten
        # rpe = da - da_baseline diye hesaplıyor. Göstergeler de aynı
        # büyüklüğü göstersin diye tabanları burada tutuyoruz (τ ≈ 5 s).
        pam_r = self.rate(self.pam_idx)
        ppl_r = self.rate(self.ppl1_idx)
        if self.pam_base is None:
            self.pam_base, self.ppl_base = pam_r, ppl_r
        self.pam_base = 0.995 * self.pam_base + 0.005 * pam_r
        self.ppl_base = 0.995 * self.ppl_base + 0.005 * ppl_r
        m["pam_rate"] = pam_r
        m["ppl_rate"] = ppl_r
        m["pam_dev"] = pam_r - self.pam_base      # + = beklenenden iyi
        m["ppl_dev"] = ppl_r - self.ppl_base      # + = beklenenden kötü
        # GÖSTERGE İÇİN YUMUŞATMA (~1 s).
        # PPL1 yalnızca 16 nörondur; bir karede tek spike 1,08 Hz demektir,
        # yani anlık hız çok kuantalı ve zıplıyor (ölçüm: sapma min -42,3
        # max +39,5). Çıplak gözle okunamaz. Öğrenme kuralı yumuşatılmamış
        # değeri kullanmaya devam ediyor; yalnızca EKRAN yumuşatılıyor.
        a = 0.93
        self.pam_dev_s = a * self.pam_dev_s + (1 - a) * m["pam_dev"]
        self.ppl_dev_s = a * self.ppl_dev_s + (1 - a) * m["ppl_dev"]
        m["pam_dev_s"] = self.pam_dev_s
        m["ppl_dev_s"] = self.ppl_dev_s

        # KAÇIŞ da tabandan ölçülür. DNp04 de tonik aktiftir: gerçek oyunda
        # 5144 kare boyunca tehlike yokken ortalama 4,40 Hz attı (DNp01 0,64).
        # Mutlak hız gösterilince "TEHLİKE" çubuğu hiçbir şey olmazken bile
        # %16-30 dolu duruyordu — PAM/PPL1'deki aynı hata.
        # KOKUYA YANIT VEREN İNEN NÖRON TOPLULUĞU (yalnızca gösterge)
        if len(self.dn_odor_idx):
            _dr = self.rate(self.dn_odor_idx)
            if self.dn_odor_base is None:
                self.dn_odor_base = _dr
            self.dn_odor_base = 0.997 * self.dn_odor_base + 0.003 * _dr
            _dv = _dr - self.dn_odor_base
            self.dn_odor_dev_s = 0.88 * self.dn_odor_dev_s + 0.12 * _dv
            m["dn_odor_rate"] = _dr
            m["dn_odor_dev"] = self.dn_odor_dev_s

        # MANTAR CİSİMCİĞİ: koku VARLIĞININ ölçülmüş okuması (bkz. KC_ODOR_*).
        # Taban izlemiyoruz — seyrek kod sayesinde koku yokken zaten susuyor.
        if len(self.kc_idx):
            _kr = self.rate(self.kc_idx)
            _now = float(np.clip((_kr - KC_ODOR_THR) / KC_ODOR_SPAN, 0.0, 1.0))
            self.odor_now = (AROUSAL_SMOOTH * self.odor_now
                             + (1.0 - AROUSAL_SMOOTH) * _now)
            # "Az önce koku vardı" tepe izi; ondan düşüş = kokuyu kaybetme.
            # Yalnızca koku ŞU AN zayıfsa kayıp sayılır: bulut içindeki
            # dalgalanma kayıp değildir (ölçüldü — dalgalanmayı kayıp sayınca
            # sinek bulutun içinde durmadan dönüyor ve elmayı kaçırıyordu).
            self.odor_peak = max(self.odor_now, self.odor_peak * CAST_PEAK_DECAY)
            _lost = self.odor_peak - self.odor_now
            self.odor_lost = float(_lost) if (
                _lost > CAST_MIN_LOST and self.odor_now < CAST_MAX_NOW) else 0.0
            # ZAMAN TÜREVİ (bant geçiren): + yaklaşıyor, − uzaklaşıyor
            self.odor_fast = (ODOR_FAST_A * self.odor_fast
                              + (1.0 - ODOR_FAST_A) * self.odor_now)
            self.odor_slow = (ODOR_SLOW_A * self.odor_slow
                              + (1.0 - ODOR_SLOW_A) * self.odor_now)
            self.odor_d = self.odor_fast - self.odor_slow
            # "az önce koku vardı" kapısı: koku hiç yokken tarama yapılmaz
            _gate = min(1.0, self.odor_peak / 0.15)
            self.odor_drop = float(np.clip(-self.odor_d * CAST_DERIV_GAIN,
                                           0.0, 1.0)) * _gate
            m["kc_rate"] = _kr
            m["odor_now"] = self.odor_now
            m["odor_d"] = self.odor_d
            m["odor_lost"] = max(self.odor_lost, self.odor_drop)
        m["arousal"] = getattr(self, "arousal", 0.0)
        m["cast"] = getattr(self, "cast_drive", 0.0)

        if len(self.thermo_idx):
            m["thermo_rate"] = self.rate(self.thermo_idx)
        # TEMİZLENME — sadece okuma, tabandan sapma
        if len(self.groom_idx):
            _gr = self.rate(self.groom_idx)
            if self.groom_base is None:
                self.groom_base = _gr
            self.groom_base = 0.995 * self.groom_base + 0.005 * _gr
            self.groom_dev_s = (0.92 * self.groom_dev_s
                                + 0.08 * (_gr - self.groom_base))
            m["groom_rate"] = _gr
            m["groom"] = max(0.0, self.groom_dev_s)

        esc_r = r_esc = m["rates"].get("escape", 0.0)
        loom_r = m.get("loom_rate", 0.0)
        if self.esc_base is None:
            self.esc_base, self.loom_base = esc_r, loom_r
        self.esc_base = 0.995 * self.esc_base + 0.005 * esc_r
        self.loom_base = 0.995 * self.loom_base + 0.005 * loom_r
        # ÖNCE YUMUŞAT, SONRA POZİTİFİNİ AL.
        # Tersini yapınca (önce max(0,...) sonra yumuşatma) gürültü hep
        # yukarı birikiyor ve çubuk tehlike yokken bile %20-40 dolu
        # görünüyordu. DNp04 iki nörondur, anlık hızı ±birkaç Hz zıplar.
        dev = (esc_r - self.esc_base) + 0.6 * (loom_r - self.loom_base)
        self.esc_dev_s = a * self.esc_dev_s + (1 - a) * dev
        m["esc_dev_s"] = max(0.0, self.esc_dev_s)
        return m

    def state_label(self, motor, hunger=0.0):
        """Tek cümlelik "şu an ne halde" özeti — hepsi gerçek nöronlardan.

        Bir sinek "mutlu" olmaz; ama ölçülebilir içsel durumları vardır ve
        her biri gerçek bir nöron kümesinden okunuyor. Sıra ÖNEM sırasıdır:
        kaçış her şeyi bastırır (gerçek sinekte de öyle).
        """
        r = motor.get("rates", {})
        loom = motor.get("loom_rate", 0.0)
        gf = r.get("escape", 0.0)
        c = lambda x: float(min(1.0, max(0.0, x)))
        if gf > 6.0:
            return "KAÇIŞ — Giant Fiber ateşledi, sıçrıyor", c(gf / 20.0)
        if loom > 14.0:
            return "TEHLİKE — üzerine bir şey geliyor (DNp04)", c((loom - 14.0) / 12.0)
        p = motor.get("ppl_dev_s", 0.0)
        if p > 1.2:
            return "KAÇINMA — ceza dopamini tabanın üstünde (PPL1)", c(p / 6.0)
        q = motor.get("pam_dev_s", 0.0)
        if q > 1.2:
            return "ÖDÜL — ödül dopamini tabanın üstünde (PAM)", c(q / 6.0)
        if r.get("backward", 0.0) > 9.0:
            return "GERİ ÇEKİLME — MDN sürüyor", c(r["backward"] / 30.0)
        # Koku uyarımı: DNc01/DNc02/DNb05/DNp29 tabanın üstünde. Bu, "sinek
        # yiyeceğin YERİNİ biliyor" demek DEĞİL — yön bu ağda kodlanmıyor
        # (ölçüldü, README). "Burada yiyecek kokusu var, hızlan ve düz git"
        # demek; gerçek sineğin kokuyu bulma yolu da budur.
        _ar = motor.get("arousal", 0.0)
        if _ar > 0.12:
            return "KOKU ALDI — yiyecek kokusu var, hızlanıyor", c(_ar)
        if motor.get("odor_lost", 0.0) > 0.25:
            return ("ARIYOR — kokuyu kaybetti, sağa sola tarıyor",
                    c(motor["odor_lost"]))
        if hunger > 0.55:
            return "AÇ — yiyecek arıyor", c(hunger)
        if r.get("forward", 0.0) > 14.0:
            return "SAKİN YÜRÜYÜŞ — tehlike yok", c(r["forward"] / 30.0)
        return "DURGUN — belirgin bir sürücü yok", 0.0

    def state_bars(self, motor, hunger=0.0):
        """Tüm içsel sürücüler 0..1 arası — hepsi TABANDAN SAPMA."""
        r = motor.get("rates", {})
        c = lambda x: float(min(1.0, max(0.0, x)))
        return {
            "KOKU": c(motor.get("arousal", 0.0)),
            "ARAMA": c(motor.get("odor_lost", 0.0)),
            "ÖDÜL": c(motor.get("pam_dev_s", 0.0) / 4.0),
            "KAÇINMA": c(motor.get("ppl_dev_s", 0.0) / 4.0),
            "TEHLİKE": c(motor.get("esc_dev_s", 0.0) / 6.0),
            "AÇLIK": c(hunger),
            "HAREKET": c(r.get("forward", 0.0) / 30.0),
        }

    def decode_motor(self):
        """
        Motor komutu, GERÇEK inen nöronların ateşleme hızından okunur.
        DNp20 iki nörondur (sol/sağ); farkları dönüşü verir.
        """
        raw = {role: self.rate(ix) for role, ix in self.motor_idx.items()}
        # Kas alçak-geçiren filtresi: tek nöronun kuantalı hızını sürekli
        # bir kuvvete çevirir (kasılma toplanması).
        a = self._motor_a
        for k, v in raw.items():
            self.motor_smooth[k] = a * self.motor_smooth.get(k, v) + (1.0 - a) * v
        r = dict(self.motor_smooth)
        self.last_rates = r
        self.motor_raw = raw

        # Sol/sağ ayrımı konektomun somaSide alanından gelir.
        tl, tr = self.motor_side["turn"]
        sl, sr = self.motor_side["steer2"]
        sides = {"tL": self.rate(tl), "tR": self.rate(tr),
                 "sL": self.rate(sl), "sR": self.rate(sr)}
        for k, v in sides.items():
            self.motor_smooth[k] = a * self.motor_smooth.get(k, v) + (1.0 - a) * v
        # DNa02 KATKISI DÜŞÜK TUTULUR.
        # Literatürde DNa02 bir dönüş nöronudur, ama konektom ölçümü şunu
        # söylüyor: DNa02'nin girdisinin yalnızca %2,6'sı görsel çıkış
        # nöronlarından gelir (DNp20'de bu oran %68,3). Yani DNa02 görsel
        # yönelimi değil, merkezi/navigasyonel dönüşü taşır. Görsel karara
        # eşit ağırlıkla katarsak sinyali seyreltir.
        _w = STEER2_WEIGHT
        l = self.motor_smooth["tL"] + _w * self.motor_smooth["sL"]
        rr = self.motor_smooth["tR"] + _w * self.motor_smooth["sR"]

        # YÖN SÖZLEŞMESİ
        # DNa02'nin tek taraflı uyarılması sineği AYNI tarafa döndürür
        # (ipsilateral; Rayshubskiy ve ark.). Yani sağ taraf daha çok
        # ateşliyorsa sinek sağa döner.
        # Bot tarafında: newYaw = yaw - tork, ve artan yaw sola dönüştür;
        # dolayısıyla POZİTİF tork = SAĞA dönüş. O halde tork = (sağ - sol).
        denom = max(2.0, l + rr)
        # steer_bias: MaleCNS'in sol ve sağ optik lobu EŞİT tamamlanmamıştır
        # (bizim alt-grafiğimizde sol 1.644, sağ 3.069 retinotopik sütun).
        # Bu, simetrik bir sahnede bile sabit bir dönüş torku üretir — sinek
        # boş odada sürekli bir tarafa kayar. Ölçüp çıkarıyoruz; teraziyi
        # tartmadan önce sıfırlamakla aynı şey. Sahneye bağlı fark KORUNUR,
        # yalnızca sabit ofset gider.
        steering = float(np.clip(((rr - l) / denom - self.steer_bias)
                                 * self.steer_sign * 1.8, -1.0, 1.0))
        thrust = float(np.clip(r["forward"] / 22.0, 0.0, 2.0))
        backing = r["backward"] > 15.0
        gf = r["escape"]
        # LOOMING KAÇIŞI: DNp04 + DNp11, girdilerinin %74 / %20'si LC4'ten.
        loom = r.get("loom", 0.0) + 0.5 * r.get("loom2", 0.0)
        if backing:
            thrust = -0.35
        return {
            "steering_torque": steering,
            "forward_thrust": thrust,
            "back": bool(backing),
            # LOOMING EŞİĞİ ÖLÇÜLDÜ: DNp04 mob yokken 4.81 Hz, mob varken
            # 20.37 Hz. Eşik 8.0 iken sinek 12 m uzaktaki mobu bile kaçış
            # sayıyordu (karelerin %20'si). 14.0 ikisinin arasında güvenli.
            "sprint": bool(r["fast"] > 10.0 or loom > 18.0),
            "jump": bool(gf > 6.0),
            "escape": bool(gf > 3.0 or loom > 14.0 or r["fast"] > 14.0),
            "loom_rate": loom,
            "rates": r,
            "DNp20_L": l, "DNp20_R": rr,
        }

    # ------------------------------------------------------------------
    def population_rates(self, names):
        return {n: self.rate_of_type(n) for n in names}

    @property
    def mean_rate(self):
        return float(self.spike_count.sum()) / self.N / (self.frame_ms / 1000.0)
