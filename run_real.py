"""
================================================================================
  🪰 DROSOPHILA — GERÇEK MaleCNS v1.0 KONEKTOM ÇALIŞTIRICISI
================================================================================

Kullanım:
    python run_real.py                     -> Yerel Minecraft sunucusuna bağlanır (ws://localhost:8765)
    python run_real.py 192.168.1.50        -> Başka makinedeki sunucuya bağlanır (ws://192.168.1.50:8765)
    python run_real.py 192.168.1.50:8766   -> Özel host ve port
    python run_real.py 8766                -> Özel port (localhost:8766)
    python run_real.py --server            -> Sunucu modu (eski ters bağlantı modu)
    python run_real.py --sessiz            -> Kanat vuruşu / işitme sesi kapalı
    python run_real.py --ses-aygit "..."   -> Belirli bir ses aygıtına çıkış ver

Minecraft Paper / Spigot sunucusundaki DrosophilaBee eklentisi 0.0.0.0:8765 üzerinde
WebSocket sunucusunu açar; bu script istemci olarak Minecraft'a bağlanır.
Konektom dosyaları eksikse indirme komutlarını gösterir.
"""

import asyncio
import os
import signal
import sys

# Konsol kod sayfası UTF-8 değilse Windows'ta emoji hatalarını önle
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Headless / Sunucu ortamında X11 veya ses aygıtı yoksa pygame'in çökmesini engelle
if "DISPLAY" not in os.environ and os.name != "nt":
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
if "--sessiz" in sys.argv:
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

HERE = os.path.dirname(os.path.abspath(__file__))
NEEDED = {
    "connectome/weights.feather":
        "connectome-weights-male-cns-v1.0-minconf-0.5.feather",
    "connectome/annotations.feather":
        "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    "connectome/neurotransmitters.feather":
        "body-neurotransmitters-male-cns-v1.0.feather",
}
BASE = ("https://storage.googleapis.com/flyem-male-cns/v1.0/"
        "connectome-data/flat-connectome")


def check_data():
    graph = os.path.join(HERE, "connectome", "malecns_behavior.W.npz")
    annot_path = os.path.join(HERE, "connectome", "annotations.feather")
    if os.path.exists(graph):
        if not os.path.exists(annot_path):
            print("[run_real] annotations.feather eksik, indiriliyor (14 MB)...")
            try:
                import urllib.request
                os.makedirs(os.path.join(HERE, "connectome"), exist_ok=True)
                url = "%s/%s" % (BASE, "body-annotations-male-cns-v1.0-minconf-0.5.feather")
                urllib.request.urlretrieve(url, annot_path)
                print("[run_real] annotations.feather başarıyla indirildi.")
            except Exception as e:
                print("[run_real] Otomatik indirme hatası: %s" % e)
                print("Lütfen şu komutu çalıştırın:\n  curl -L -o connectome/annotations.feather %s/body-annotations-male-cns-v1.0-minconf-0.5.feather" % BASE)
                return False
        return True

    missing = [(p, f) for p, f in NEEDED.items()
               if not os.path.exists(os.path.join(HERE, p))]
    if missing:
        print("=" * 72)
        print("  KONEKTOM VERİSİ EKSİK — MaleCNS v1.0 (CC BY 4.0, hesap gerekmez)")
        print("=" * 72)
        for p, f in missing:
            print("  curl -L -o %s %s/%s" % (p, BASE, f))
        print()
        print("  Toplam ~1,1 GB. Sonra:  python connectome_loader.py")
        print("=" * 72)
        return False
    print("[run_real] Alt-grafik kuruluyor (ilk çalıştırmada birkaç dakika)...")
    import connectome_loader
    connectome_loader.build_behavior_graph()
    return True


def main():
    ws_host = "localhost"
    ws_port = 8765
    as_server = False

    for a in sys.argv[1:]:
        if a in ("--server", "--sunucu"):
            as_server = True
        elif a.startswith("--"):
            continue
        elif ":" in a:
            parts = a.split(":", 1)
            ws_host = parts[0]
            if parts[1].isdigit():
                ws_port = int(parts[1])
        elif a.isdigit() and len(a) >= 4:
            ws_port = int(a)
        elif "." in a or a == "localhost":
            ws_host = a

    print("=" * 72)
    print("  🪰 DROSOPHILA — GERÇEK MaleCNS v1.0 KONEKTOMU")
    if as_server:
        print("  🌐 WebSocket Sunucusu: 0.0.0.0:%d (DrosophilaBee bekleniyor)" % ws_port)
    else:
        print("  🌐 Hedef Minecraft Sunucusu: ws://%s:%d" % (ws_host, ws_port))
    print("=" * 72)

    if not check_data():
        sys.exit(1)

    _done = {"v": False}

    def cleanup(*_):
        if _done["v"]:
            return
        _done["v"] = True
        print("\n[ÇIKIŞ] Kapatılıyor...")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("[1/1] 🧠 Gerçek konektom beyni başlatılıyor...")
    import minecraft_real_bridge

    # Ses ayarları
    if "--sessiz" in sys.argv:
        minecraft_real_bridge.SOUND_ON = False
    if "--ses-aygit" in sys.argv:
        import fly_sound
        _i = sys.argv.index("--ses-aygit")
        if _i + 1 < len(sys.argv):
            fly_sound.DEVICE = sys.argv[_i + 1]

    debug_mode = ("--debug" in sys.argv or "--log" in sys.argv)
    if debug_mode:
        print("  🐞 Hata Ayıklama (Debug) ve Ayrıntılı Log Modu AÇIK")

    try:
        asyncio.run(minecraft_real_bridge.bridge_loop(
            ws_host=ws_host, ws_port=ws_port, label="DrosophilaBee", as_server=as_server,
            logging=debug_mode, debug=debug_mode
        ))
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        import traceback
        traceback.print_exc()
        cleanup()
    finally:
        cleanup()


if __name__ == "__main__":
    main()
