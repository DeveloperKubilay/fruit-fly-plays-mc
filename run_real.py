"""
================================================================================
  🪰 DROSOPHILA — GERÇEK MaleCNS v1.0 KONEKTOM ÇALIŞTIRICISI
================================================================================

Kullanım:
    python run_real.py                     -> Yerel Minecraft sunucusuna bağlanır (ws://localhost:8765)
    python run_real.py 1.2.3.4             -> Uzak makinedeki sunucuya bağlanır (ws://1.2.3.4:8765)
    python run_real.py 1.2.3.4:8766        -> Özel host ve port
    python run_real.py 8766                -> Özel port (localhost:8766)
    python run_real.py --server            -> Sunucu modu (eski ters bağlantı modu)
    python run_real.py --sessiz            -> Kanat vuruşu / işitme sesi kapalı
    python run_real.py --ses-aygit "..."   -> Belirli bir ses aygıtına çıkış ver

Ortam Değişkenleri (.env veya export / set):
    MINECRAFT_HOST=1.2.3.4                 -> Hedef sunucu IP / domain (varsayılan: localhost)
    MINECRAFT_PORT=8765                    -> Hedef port (varsayılan: 8765)

Minecraft Paper / Spigot sunucusundaki DrosophilaBee eklentisi 0.0.0.0:8765 üzerinde
WebSocket sunucusunu açar; bu script istemci olarak Minecraft'a bağlanır.
Konektom dosyaları eksikse indirme komutlarını gösterir.
"""

import asyncio
import json
import os
import signal
import sys

# Konsol kod sayfası UTF-8 değilse Windows'ta emoji hatalarını önle
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Headless / Sunucu ortamında X11 veya ses aygıtı yoksa veya --no-gui istenmişse dummy video/audio driver ayarla
if any(a in sys.argv for a in ("--no-gui", "--nogui", "--headless")):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
elif "DISPLAY" not in os.environ and os.name != "nt":
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


def load_config():
    """Varsa config.json veya .env dosyasından bağlantı ve güvenlik ayarlarını yükler."""
    cfg_file = os.path.join(HERE, "config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "minecraft_host" in data and data["minecraft_host"]:
                        os.environ.setdefault("MINECRAFT_HOST", str(data["minecraft_host"]))
                    if "minecraft_port" in data and data["minecraft_port"]:
                        os.environ.setdefault("MINECRAFT_PORT", str(data["minecraft_port"]))
                    token_val = data.get("auth_token") or data.get("password") or data.get("token")
                    if token_val:
                        os.environ.setdefault("FLY_AUTH_TOKEN", str(token_val))
                        os.environ.setdefault("MINECRAFT_PASSWORD", str(token_val))
        except Exception:
            pass

    env_file = os.path.join(HERE, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ.setdefault(k, v)
                        if k in ("MINECRAFT_PASSWORD", "PASSWORD", "AUTH_TOKEN", "FLY_PASSWORD"):
                            os.environ.setdefault("FLY_AUTH_TOKEN", v)
                        elif k == "FLY_AUTH_TOKEN":
                            os.environ.setdefault("MINECRAFT_PASSWORD", v)
        except Exception:
            pass


def main():
    load_config()

    # Varsayılan: localhost:8765 (modüler ortam değişkenleri: MINECRAFT_HOST, TARGET, SERVER_HOST)
    ws_host = (
        os.environ.get("MINECRAFT_HOST")
        or os.environ.get("TARGET")
        or os.environ.get("SERVER_HOST")
        or "localhost"
    )
    ws_port = 8765

    env_port = os.environ.get("MINECRAFT_PORT") or os.environ.get("SERVER_PORT")
    if env_port and str(env_port).isdigit():
        ws_port = int(env_port)

    # MINECRAFT_HOST içinde IP:Port varsa ayrıştır (Örn: 1.2.3.4:8765)
    if ":" in ws_host:
        parts = ws_host.split(":", 1)
        ws_host = parts[0]
        if parts[1].isdigit():
            ws_port = int(parts[1])

    auth_token = (
        os.environ.get("FLY_AUTH_TOKEN")
        or os.environ.get("MINECRAFT_PASSWORD")
        or os.environ.get("PASSWORD")
        or os.environ.get("AUTH_TOKEN")
        or os.environ.get("FLY_PASSWORD")
        or ""
    )

    as_server = False
    no_gui = any(a in sys.argv for a in ("--no-gui", "--nogui", "--headless"))

    i = 1
    positional = []
    while i < len(sys.argv):
        a = sys.argv[i]
        if a in ("--server", "--sunucu"):
            as_server = True
        elif a in ("--token", "--password", "-p"):
            if i + 1 < len(sys.argv):
                auth_token = sys.argv[i + 1]
                i += 1
        elif a.startswith("--token="):
            auth_token = a.split("=", 1)[1]
        elif a.startswith("--password="):
            auth_token = a.split("=", 1)[1]
        elif a in ("--no-gui", "--nogui", "--headless", "--sessiz"):
            pass
        elif a == "--ses-aygit":
            if i + 1 < len(sys.argv):
                i += 1
        elif not a.startswith("--"):
            positional.append(a)
        i += 1

    if len(positional) >= 1:
        arg_host = positional[0]
        if ":" in arg_host:
            parts = arg_host.split(":", 1)
            ws_host = parts[0]
            if parts[1].isdigit():
                ws_port = int(parts[1])
        elif arg_host.isdigit() and len(arg_host) >= 4:
            ws_port = int(arg_host)
        else:
            ws_host = arg_host

    if len(positional) >= 2:
        auth_token = positional[1]

    if auth_token:
        os.environ["FLY_AUTH_TOKEN"] = auth_token
        os.environ["MINECRAFT_PASSWORD"] = auth_token

    print("=" * 72)
    print("  🪰 DROSOPHILA — GERÇEK MaleCNS v1.0 KONEKTOMU")
    if as_server:
        print("  🌐 WebSocket Sunucusu: 0.0.0.0:%d (DrosophilaBee bekleniyor)" % ws_port)
    else:
        print("  🌐 Hedef Minecraft Sunucusu: ws://%s:%d" % (ws_host, ws_port))
    if no_gui:
        print("  🖥️ Arayüz Modu: Sadece Terminal Modu (--no-gui)")
    if auth_token:
        masked = auth_token[:2] + "*" * max(1, len(auth_token) - 4) + auth_token[-2:] if len(auth_token) > 4 else "***"
        print("  🔑 Güvenlik Şifresi: %s" % masked)
    else:
        print("  ⚠️ Güvenlik Şifresi: Belirtilmedi")
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
