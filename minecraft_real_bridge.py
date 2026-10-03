"""
================================================================================
 MINECRAFT <-> GERÇEK MEYVE SİNEĞİ BEYNİ KÖPRÜSÜ
================================================================================
Bu köprü, Minecraft botunu MaleCNS v1.0 konektomuna bağlar.

    118.820 gerçek nöron | 5.058.421 gerçek bağlantı | 50.972.620 sinaptik temas
    FlyEM / HHMI Janelia + Cambridge + MRC LMB + Google Research  (CC BY 4.0)

Duyular gerçek duyu nöronlarına girer:
    görme   -> R1-R6 / R7 / R8 fotoreseptörleri (histaminerjik)
    koku    -> 2.635 ORN, sol ve sağ anten AYRI
    işitme  -> Johnston organı (JO-A/JO-B ses, JO-C/JO-E hava akımı)

Elle yazılmış "şu olursa şunu yap" davranış kuralı YOKTUR. Motor komutları
gerçek inen nöronların ateşleme hızından okunur:

    DNp20    -> sağa/sola dönüş (bilateral fark)
    DNpe017  -> ileri yürüyüş
    MDN      -> geri yürüyüş
    DNp09    -> hızlı kaçış
    DNp01    -> Giant Fiber sıçraması

Çalıştır:   python run_real.py
"""

import asyncio
import json
import math
import os
import sys
import time

# Konsol kod sayfası UTF-8 değilse (Windows'ta sık) tek bir emoji
# UnicodeEncodeError atıp bütün köprüyü düşürüyordu. Yazdıramadığı
# karakteri atlasın, simülasyon devam etsin.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import pygame
import websockets

import fly_brain_real
from fly_brain_real import RealFlyBrain
from fly_log import FlyLogger
from fly_sound import WingBeat

# ---------------------------------------------------------------- pencere
pygame.init()
pygame.font.init()
# Petek gözün 32 sütunluk yatay tarama dizisinin açıları (CompoundEyeRaytracer.java):
# FOV_H = 270°, colAng[c] = FOV_H/2 - c/(cols-1)*FOV_H). Sütun 0 EN SOL (+135°),
# sütun 31 EN SAĞ (-135°). Kaçış yönü bu profilden çıkarılır.
# Ses kanalları:
#   Kanal 0 — Sineğin kanat vuruş sesi (DNpe017/DNp09/DNp01 motor nöronlarından)
#   Kanal 1 — Sineğin duyduğu ortam sesi (Johnston organı sol/sağ stereo farkı)
# Kapatmak için: run_real.py --sessiz ya da pencerede S tuşu
SOUND_ON = True
IS_HEADLESS = (os.environ.get("SDL_VIDEODRIVER") == "dummy")
SCAN_ANG = np.linspace(np.pi * 0.75, -np.pi * 0.75, 32).astype(np.float32)

WIN_W, WIN_H = 1060, 780
CANVAS_W, CANVAS_H = WIN_W, WIN_H
canvas = pygame.Surface((CANVAS_W, CANVAS_H))

# Ekran çözünürlüğünü algıla ve pencereyi görev çubuğuna taşmayacak boyutta başlat
_disp_info = pygame.display.Info()
_avail_w = max(640, min(WIN_W, _disp_info.current_w - 40)) if _disp_info.current_w > 0 else WIN_W
_avail_h = max(480, min(WIN_H, _disp_info.current_h - 90)) if _disp_info.current_h > 0 else WIN_H
_init_scale = min(_avail_w / WIN_W, _avail_h / WIN_H, 1.0)
_init_w = int(WIN_W * _init_scale)
_init_h = int(WIN_H * _init_scale)

screen = pygame.display.set_mode((_init_w, _init_h), pygame.RESIZABLE)
pygame.display.set_caption("Drosophila — MaleCNS v1.0 Gerçek Konektom")
clock = pygame.time.Clock()

F_TITLE = pygame.font.SysFont("segoeui,arial", 19, bold=True)
F_LBL = pygame.font.SysFont("segoeui,arial", 13, bold=True)
F_BIG = pygame.font.SysFont("segoeui,arial", 21, bold=True)
F_S = pygame.font.SysFont("segoeui,arial", 11)
F_M = pygame.font.SysFont("consolas,couriernew", 13)
F_MS = pygame.font.SysFont("consolas,couriernew", 11)

BG = (13, 16, 22)
PANEL = (22, 28, 37)
ACC = (0, 220, 190)
TXT = (228, 233, 242)
MUTE = (132, 147, 168)
ALERT = (255, 70, 90)
GREEN = (55, 225, 125)

# Dashboard'da izlenecek gerçek hücre tipleri (görme -> karar -> hareket)
WATCH_EN = [
    ("R1-R6", "photoreceptor"), ("L1", "lamina ON"), ("L2", "lamina OFF"),
    ("Mi1", "medulla ON"), ("Mi9", "medulla delay"), ("Tm3", "medulla ON"),
    ("Tm9", "medulla OFF"), ("T4a", "motion ON"), ("T5a", "motion OFF"),
    ("LPLC2", "looming"), ("LC4", "looming"), ("APL", "MB inhibition"),
]
WATCH_TR = [
    ("R1-R6", "fotoreseptör"), ("L1", "lamina ON"), ("L2", "lamina OFF"),
    ("Mi1", "medulla ON"), ("Mi9", "medulla gecikme"), ("Tm3", "medulla ON"),
    ("Tm9", "medulla OFF"), ("T4a", "hareket ON"), ("T5a", "hareket OFF"),
    ("LPLC2", "looming"), ("LC4", "looming"), ("APL", "MB inhibisyon"),
]
WATCH = WATCH_EN

_fps = []


def fps_tick():
    """Kare basi BIR KEZ cagrilir: zaman damgasini kaydeder."""
    _fps.append(pygame.time.get_ticks() / 1000.0)
    while len(_fps) > 40:
        _fps.pop(0)


def fps_now():
    """Saf okuyucu.

    Eskiden bu fonksiyonun kendisi zaman damgasi ekliyordu ve kare basina
    iki yerden cagriliyordu (cizim + kayit): ornekleme hizi gercegin iki
    kati cikiyor, ekran 37.5 FPS derken gercek hiz 18.3 oluyordu.
    """
    if len(_fps) < 2:
        return 0.0
    d = _fps[-1] - _fps[0]
    return (len(_fps) - 1) / d if d > 1e-6 else 0.0


def retina_surface(retina, cols, rows):
    """
    Ekranda gördüğün görüntü, beyne giren görüntünün BİREBİR aynısıdır.

    Burada kontrast germe, parlaklık düzeltmesi, yumuşatma YOKTUR. Ommatidium
    başına hangi RGB üçlüsü hesaplandıysa, fotoreseptörlere de o giriyor,
    ekrana da o basılıyor. Büyütme en-yakın-komşu ile yapılır: aradaki
    pikselleri uydurmak faset sayısını çoğaltmış gibi gösterirdi.
    """
    a = np.asarray(retina, dtype=np.float32)
    if a.size != cols * rows * 3:
        return None
    a = np.clip(a.reshape(rows, cols, 3), 0, 255)
    return pygame.surfarray.make_surface(np.transpose(a, (1, 0, 2)).astype(np.uint8))


# SES BUTONU — tıklanabilir. Fare olayı ana döngüde bu dikdörtgenle
# karşılaştırılır; S tuşu da aynı işi yapar.
SES_BTN = pygame.Rect(460, 5, 120, 24)
NEURAL_BTN = pygame.Rect(588, 5, 170, 24)


def draw_button(rect, text, on):
    col = (35, 120, 85) if on else (70, 52, 58)
    edge = (60, 220, 160) if on else (150, 90, 100)
    pygame.draw.rect(canvas, col, rect, border_radius=6)
    pygame.draw.rect(canvas, edge, rect, 1, border_radius=6)
    t = F_LBL.render(text, True, (235, 245, 240))
    canvas.blit(t, (rect.x + (rect.w - t.get_width()) // 2,
                    rect.y + (rect.h - t.get_height()) // 2))


def draw_neural_overlay(brain, motor, extra, lang="en"):
    """SPACE veya TAB ile açılan tam kapsamlı MaleCNS v1.0 Nöral Aktivite Haritası."""
    ov_rect = pygame.Rect(14, 34, CANVAS_W - 28, CANVAS_H - 42)
    overlay = pygame.Surface((ov_rect.width, ov_rect.height))
    overlay.fill((16, 20, 28))
    pygame.draw.rect(overlay, (42, 52, 68), (0, 0, ov_rect.width, ov_rect.height), 2, border_radius=10)

    is_tr = (lang == "tr")

    if is_tr:
        title = F_TITLE.render("🧠 BİYOLOJİK KONEKTOM NÖRAL AKTİVİTE HARİTASI (MaleCNS v1.0)", True, ACC)
        sub_text = ("[TAB veya SPACE ile kapat]  |  118.820 Nöron  |  4.037.761 Sinaps  |  Ortalama Aktivite: %.2f Hz"
                    % brain.mean_rate)
    else:
        title = F_TITLE.render("🧠 BIOLOGICAL CONNECTOME NEURAL ACTIVITY MAP (MaleCNS v1.0)", True, ACC)
        sub_text = ("[Press TAB or SPACE to close]  |  118,820 Neurons  |  4,037,761 Synapses  |  Mean Activity: %.2f Hz"
                    % brain.mean_rate)
    overlay.blit(title, (18, 12))
    sub = F_MS.render(sub_text, True, (160, 200, 220))
    overlay.blit(sub, (18, 36))

    col_w = (ov_rect.width - 50) // 4
    col_y = 62
    col_h = 470

    # 1. GÖRSEL LOBLAR / OPTIC LOBES
    c1 = pygame.Rect(10, col_y, col_w, col_h)
    pygame.draw.rect(overlay, PANEL, c1, border_radius=8)
    p1_title = "1. GÖRSEL LOBLAR (Optic)" if is_tr else "1. OPTIC LOBES (Vision)"
    overlay.blit(F_LBL.render(p1_title, True, (255, 220, 90)), (c1.x + 12, c1.y + 8))
    if is_tr:
        optic_types = [
            ("R1-R6", "Fotoreseptör", 40.0),
            ("L1", "Lamina ON", 35.0),
            ("L2", "Lamina OFF", 35.0),
            ("Mi1", "Medulla ON", 30.0),
            ("Mi9", "Medulla gecikme", 30.0),
            ("Tm3", "Medulla ON", 30.0),
            ("Tm9", "Medulla OFF", 30.0),
            ("T4a", "Hareket ON", 40.0),
            ("T5a", "Hareket OFF", 40.0),
            ("LC4", "Looming tehdit", 30.0),
            ("LPLC2", "Genişleyen cisim", 30.0),
        ]
    else:
        optic_types = [
            ("R1-R6", "Photoreceptor", 40.0),
            ("L1", "Lamina ON", 35.0),
            ("L2", "Lamina OFF", 35.0),
            ("Mi1", "Medulla ON", 30.0),
            ("Mi9", "Medulla delay", 30.0),
            ("Tm3", "Medulla ON", 30.0),
            ("Tm9", "Medulla OFF", 30.0),
            ("T4a", "Motion ON", 40.0),
            ("T5a", "Motion OFF", 40.0),
            ("LC4", "Looming threat", 30.0),
            ("LPLC2", "Expanding obj", 30.0),
        ]
    cy = c1.y + 32
    for tname, desc, max_hz in optic_types:
        r = brain.rate_of_type(tname)
        overlay.blit(F_MS.render("%-6s %-13s" % (tname, desc), True, MUTE), (c1.x + 10, cy))
        pygame.draw.rect(overlay, (35, 42, 54), (c1.x + 10, cy + 14, col_w - 70, 6), border_radius=2)
        pygame.draw.rect(overlay, (80, 190, 255), (c1.x + 10, cy + 14, int((col_w - 70) * min(1.0, r / max_hz)), 6), border_radius=2)
        overlay.blit(F_MS.render("%4.1f" % r, True, TXT), (c1.x + col_w - 52, cy + 10))
        cy += 38

    # 2. MANTAR CİSİMCİĞİ / MUSHROOM BODY
    c2 = pygame.Rect(20 + col_w, col_y, col_w, col_h)
    pygame.draw.rect(overlay, PANEL, c2, border_radius=8)
    p2_title = "2. ÖĞRENME (Mushroom Body)" if is_tr else "2. LEARNING (Mushroom Body)"
    overlay.blit(F_LBL.render(p2_title, True, (255, 215, 0)), (c2.x + 12, c2.y + 8))
    kc_len = len(brain.kc_idx)
    kc_spikes = brain.spike_count[brain.kc_idx] if kc_len else np.array([])
    kc_silent = 100.0 * float((kc_spikes == 0).mean()) if len(kc_spikes) else 0.0
    cy2 = c2.y + 32
    if is_tr:
        mb_items = [
            ("Kenyon (KC)", "%d hücre" % kc_len, brain.rate(brain.kc_idx), 20.0, (180, 140, 255)),
            ("KC Sessiz", "%%%.0f seyrek" % kc_silent, kc_silent, 100.0, GREEN if kc_silent > 80 else (255, 180, 60)),
            ("MBON", "%d hücre" % len(brain.mbon_idx), brain.rate(brain.mbon_idx), 35.0, (255, 200, 100)),
            ("PAM Ödül", "dopamin", brain.rate(brain.pam_idx), 25.0, GREEN),
            ("PPL1 Ceza", "dopamin", brain.rate(brain.ppl1_idx), 25.0, ALERT),
            ("APL", "GABA inhib.", brain.rate_of_type("APL"), 25.0, (200, 120, 255)),
            ("DPA", "plastisite", abs(motor.get("rpe", 0.0)) * 20.0, 20.0, GREEN if motor.get("rpe", 0.0) >= 0 else ALERT),
        ]
    else:
        mb_items = [
            ("Kenyon (KC)", "%d cells" % kc_len, brain.rate(brain.kc_idx), 20.0, (180, 140, 255)),
            ("KC Silent", "%%%.0f sparse" % kc_silent, kc_silent, 100.0, GREEN if kc_silent > 80 else (255, 180, 60)),
            ("MBON", "%d cells" % len(brain.mbon_idx), brain.rate(brain.mbon_idx), 35.0, (255, 200, 100)),
            ("PAM Reward", "dopamine", brain.rate(brain.pam_idx), 25.0, GREEN),
            ("PPL1 Punish", "dopamine", brain.rate(brain.ppl1_idx), 25.0, ALERT),
            ("APL", "GABA inhib.", brain.rate_of_type("APL"), 25.0, (200, 120, 255)),
            ("DPA", "plasticity", abs(motor.get("rpe", 0.0)) * 20.0, 20.0, GREEN if motor.get("rpe", 0.0) >= 0 else ALERT),
        ]
    for name, desc, val, max_v, col in mb_items:
        overlay.blit(F_MS.render("%-11s %-11s" % (name, desc), True, MUTE), (c2.x + 10, cy2))
        pygame.draw.rect(overlay, (35, 42, 54), (c2.x + 10, cy2 + 14, col_w - 70, 6), border_radius=2)
        pygame.draw.rect(overlay, col, (c2.x + 10, cy2 + 14, int((col_w - 70) * min(1.0, val / max_v)), 6), border_radius=2)
        overlay.blit(F_MS.render("%4.1f" % val, True, TXT), (c2.x + col_w - 52, cy2 + 10))
        cy2 += 55

    # 3. İNEN MOTOR NÖRONLAR / DESCENDING NEURONS
    c3 = pygame.Rect(30 + col_w * 2, col_y, col_w, col_h)
    pygame.draw.rect(overlay, PANEL, c3, border_radius=8)
    p3_title = "3. MOTOR ÇIKTILAR (Descending)" if is_tr else "3. MOTOR OUTPUTS (Descending)"
    overlay.blit(F_LBL.render(p3_title, True, ACC), (c3.x + 12, c3.y + 8))
    rates = motor.get("rates", {})
    cy3 = c3.y + 32
    if is_tr:
        dn_items = [
            ("DNp20 Sol", "görsel tork L", motor.get("DNp20_L", 0.0), 40.0, (120, 200, 255)),
            ("DNp20 Sağ", "görsel tork R", motor.get("DNp20_R", 0.0), 40.0, (120, 200, 255)),
            ("DNa02", "merkezi yönelim", brain.rate_of_type("DNa02"), 30.0, (140, 220, 180)),
            ("DNpe017", "ileri yürüyüş", rates.get("forward", 0.0), 40.0, GREEN),
            ("MDN", "geri çekilme", rates.get("backward", 0.0), 30.0, (255, 180, 60)),
            ("DNp09", "hızlı kaçış", rates.get("fast", 0.0), 35.0, (255, 150, 200)),
            ("DNp01", "Giant Fiber", rates.get("escape", 0.0), 25.0, ALERT),
            ("MN9", "hortum/proboscis", rates.get("feed", 0.0), 30.0, (255, 230, 140)),
        ]
    else:
        dn_items = [
            ("DNp20 Left", "visual torque L", motor.get("DNp20_L", 0.0), 40.0, (120, 200, 255)),
            ("DNp20 Right", "visual torque R", motor.get("DNp20_R", 0.0), 40.0, (120, 200, 255)),
            ("DNa02", "steering drive", brain.rate_of_type("DNa02"), 30.0, (140, 220, 180)),
            ("DNpe017", "forward walk", rates.get("forward", 0.0), 40.0, GREEN),
            ("MDN", "backward crawl", rates.get("backward", 0.0), 30.0, (255, 180, 60)),
            ("DNp09", "fast escape", rates.get("fast", 0.0), 35.0, (255, 150, 200)),
            ("DNp01", "Giant Fiber", rates.get("escape", 0.0), 25.0, ALERT),
            ("MN9", "proboscis feed", rates.get("feed", 0.0), 30.0, (255, 230, 140)),
        ]
    for name, desc, val, max_v, col in dn_items:
        overlay.blit(F_MS.render("%-9s %-13s" % (name, desc), True, MUTE), (c3.x + 10, cy3))
        pygame.draw.rect(overlay, (35, 42, 54), (c3.x + 10, cy3 + 14, col_w - 70, 6), border_radius=2)
        pygame.draw.rect(overlay, col, (c3.x + 10, cy3 + 14, int((col_w - 70) * min(1.0, val / max_v)), 6), border_radius=2)
        overlay.blit(F_MS.render("%4.1f" % val, True, TXT), (c3.x + col_w - 52, cy3 + 10))
        cy3 += 50

    # 4. DUYU VE ÇEVRE / SENSORY & ENVIRONMENT
    c4 = pygame.Rect(40 + col_w * 3, col_y, col_w, col_h)
    pygame.draw.rect(overlay, PANEL, c4, border_radius=8)
    p4_title = "4. DUYU VE ÇEVRE (Sensory)" if is_tr else "4. SENSES & ENVIRONMENT (Sensory)"
    overlay.blit(F_LBL.render(p4_title, True, (180, 255, 150)), (c4.x + 12, c4.y + 8))
    jo_r = brain.rate(brain.jo_idx) if len(brain.jo_idx) else 0.0
    cy4 = c4.y + 32
    if is_tr:
        sens_items = [
            ("ORN Sol", "sol anten koku", brain.rate(brain.orn_L) if len(brain.orn_L) else 0.0, 35.0, (150, 245, 130)),
            ("ORN Sağ", "sağ anten koku", brain.rate(brain.orn_R) if len(brain.orn_R) else 0.0, 35.0, (150, 245, 130)),
            ("PN", "anten lobu proj.", brain.rate(brain.pn_idx) if len(brain.pn_idx) else 0.0, 35.0, (180, 240, 160)),
            ("LH", "lateral horn", brain.rate(brain.lh_idx) if len(brain.lh_idx) else 0.0, 35.0, (200, 220, 140)),
            ("Johnston", "işitme+rüzgâr", jo_r, 35.0, (255, 210, 120)),
            ("OCG01 Sol", "sol ocellus", brain.rate(brain.ocg_L) if len(brain.ocg_L) else 0.0, 35.0, (255, 235, 140)),
            ("OCG01 Sağ", "sağ ocellus", brain.rate(brain.ocg_R) if len(brain.ocg_R) else 0.0, 35.0, (255, 235, 140)),
            ("GRN Tat", "şeker nektar", brain.rate(brain.grn_idx) if len(brain.grn_idx) else 0.0, 30.0, (255, 180, 120)),
        ]
    else:
        sens_items = [
            ("ORN Left", "L antenna odor", brain.rate(brain.orn_L) if len(brain.orn_L) else 0.0, 35.0, (150, 245, 130)),
            ("ORN Right", "R antenna odor", brain.rate(brain.orn_R) if len(brain.orn_R) else 0.0, 35.0, (150, 245, 130)),
            ("PN", "ant. lobe proj.", brain.rate(brain.pn_idx) if len(brain.pn_idx) else 0.0, 35.0, (180, 240, 160)),
            ("LH", "lateral horn", brain.rate(brain.lh_idx) if len(brain.lh_idx) else 0.0, 35.0, (200, 220, 140)),
            ("Johnston", "hearing+wind", jo_r, 35.0, (255, 210, 120)),
            ("OCG01 Left", "left ocellus", brain.rate(brain.ocg_L) if len(brain.ocg_L) else 0.0, 35.0, (255, 235, 140)),
            ("OCG01 Right", "right ocellus", brain.rate(brain.ocg_R) if len(brain.ocg_R) else 0.0, 35.0, (255, 235, 140)),
            ("GRN Taste", "sugar nectar", brain.rate(brain.grn_idx) if len(brain.grn_idx) else 0.0, 30.0, (255, 180, 120)),
        ]
    for name, desc, val, max_v, col in sens_items:
        overlay.blit(F_MS.render("%-9s %-13s" % (name, desc), True, MUTE), (c4.x + 10, cy4))
        pygame.draw.rect(overlay, (35, 42, 54), (c4.x + 10, cy4 + 14, col_w - 70, 6), border_radius=2)
        pygame.draw.rect(overlay, col, (c4.x + 10, cy4 + 14, int((col_w - 70) * min(1.0, val / max_v)), 6), border_radius=2)
        overlay.blit(F_MS.render("%4.1f" % val, True, TXT), (c4.x + col_w - 52, cy4 + 10))
        cy4 += 50

    # Alt Alan: Canlı Kenyon Hücresi & Nöral Spike Matrisi
    mat_y = col_y + col_h + 10
    mat_w = ov_rect.width - 20
    mat_h = ov_rect.height - mat_y - 10
    if mat_h > 20:
        pygame.draw.rect(overlay, (22, 28, 37), (10, mat_y, mat_w, mat_h), border_radius=6)
        mat_title = ("CANLI NÖRAL SPİKE MATRİSİ — Kenyon Hücreleri & İnen Nöronların Anlık Ateşlemeleri:"
                     if is_tr else
                     "LIVE NEURAL SPIKE MATRIX — Kenyon Cells & Descending Neurons Real-Time Spikes:")
        overlay.blit(F_S.render(mat_title, True, MUTE), (20, mat_y + 4))
        n_show = min(400, len(kc_spikes))
        if n_show > 0:
            bw = (mat_w - 20) / float(n_show)
            for i in range(n_show):
                spk = float(kc_spikes[i])
                if spk > 0:
                    h = min(mat_h - 22, int(spk * 6 + 4))
                    col = (int(100 + 155 * min(1.0, spk / 3.0)), int(180 + 75 * min(1.0, spk / 3.0)), 255)
                    pygame.draw.rect(overlay, col, (20 + int(i * bw), mat_y + mat_h - 4 - h, max(1, int(bw)), h))

    canvas.blit(overlay, (ov_rect.x, ov_rect.y))


def bar(x, y, w, h, frac, col, bgc=(38, 44, 56)):
    pygame.draw.rect(canvas, bgc, (x, y, w, h), border_radius=3)
    pygame.draw.rect(canvas, col, (x, y, int(w * max(0.0, min(1.0, frac))), h),
                     border_radius=3)


def render(brain, motor, retina, cols, rows, distances, health, food,
           heading, cast_ms, extra, senses, lang="en"):
    if IS_HEADLESS:
        return
    canvas.fill(BG)
    f = fps_now()
    is_tr = (lang == "tr")

    hdr_title = "DROSOPHILA  |  MaleCNS v1.0 GERÇEK KONEKTOM" if is_tr else "DROSOPHILA  |  MaleCNS v1.0 REAL CONNECTOME"
    canvas.blit(F_TITLE.render(hdr_title, True, ACC), (18, 7))
    if is_tr:
        hdr = ("%.1f FPS   %d nöron  %d bağlantı   beyin %.0f ms   ışın %s"
               % (f, brain.N, brain.W.nnz, extra.get("brain_ms", 0.0),
                  ("%.0f ms" % cast_ms) if cast_ms else "-"))
    else:
        hdr = ("%.1f FPS   %d neurons  %d synapses   brain %.0f ms   raycast %s"
               % (f, brain.N, brain.W.nnz, extra.get("brain_ms", 0.0),
                  ("%.0f ms" % cast_ms) if cast_ms else "-"))
    sh = F_MS.render(hdr, True, MUTE if f > 8 else ALERT)
    canvas.blit(sh, (CANVAS_W - 18 - sh.get_width(), 10))
    _ses = extra.get("ses")
    if _ses is None:
        draw_button(SES_BTN, "SES YOK (kart)" if is_tr else "NO AUDIO (device)", False)
    else:
        if is_tr:
            draw_button(SES_BTN, "SES: AÇIK" if _ses else "SES: kapalı", bool(_ses))
        else:
            draw_button(SES_BTN, "AUDIO: ON" if _ses else "AUDIO: off", bool(_ses))

    _ov = extra.get("show_overlay", False)
    if is_tr:
        draw_button(NEURAL_BTN, "HARİTA: AÇIK [TAB]" if _ov else "BEYİN HARİTASI [TAB]", bool(_ov))
    else:
        draw_button(NEURAL_BTN, "MAP: ON [TAB]" if _ov else "BRAIN MAP [TAB]", bool(_ov))

    # ---------------- PANEL 1: retina ----------------
    p1 = pygame.Rect(14, 32, CANVAS_W - 28, 204)
    pygame.draw.rect(canvas, PANEL, p1, border_radius=10)
    p1_desc = (
        "1. PETEK GÖZ — %d ommatidium (gerçek sinek ~1500) — ekrandaki görüntü fotoreseptörlere giren görüntünün AYNISI"
        if is_tr else
        "1. COMPOUND EYE — %d ommatidia (real fly ~1500) — scene matches photoreceptor inputs"
    ) % (cols * rows)
    canvas.blit(F_LBL.render(p1_desc, True, (255, 220, 90)), (p1.x + 12, p1.y + 5))
    ix, iy, iw, ih = 24, 52, CANVAS_W - 48, 126
    s = retina_surface(retina, cols, rows) if retina is not None else None
    if s is not None:
        canvas.blit(pygame.transform.scale(s, (iw, ih)), (ix, iy))
    else:
        pygame.draw.rect(canvas, (28, 33, 42), (ix, iy, iw, ih))
    pygame.draw.rect(canvas, (58, 68, 84), (ix, iy, iw, ih), 1)
    pygame.draw.line(canvas, (255, 255, 255), (ix + iw // 2, iy),
                     (ix + iw // 2, iy + ih), 1)
    canvas.blit(F_S.render("<< SOL GÖZ" if is_tr else "<< LEFT EYE", True, (0, 210, 235)), (ix + 6, iy + ih + 2))
    r_lbl = F_S.render("SAĞ GÖZ >>" if is_tr else "RIGHT EYE >>", True, (255, 175, 45))
    canvas.blit(r_lbl, (ix + iw - r_lbl.get_width() - 6, iy + ih + 2))
    if distances is not None and len(distances) == 32:
        cw = iw / 32.0
        for c in range(32):
            d = float(distances[c])
            v = float(np.clip(1.0 - (d - 1.0) / 14.0, 0.0, 1.0))
            pygame.draw.rect(canvas, (int(40 + 215 * v), int(200 * (1 - v) + 40), 40),
                             (ix + int(c * cw), iy + ih + 15, int(cw) - 1, 9))
        dist_text = (
            "MESAFE ŞERİDİ: kırmızı = yakın (çarpmak üzere), yeşil = açık yol   |   en yakın %.1f m"
            if is_tr else
            "DISTANCE STRIP: red = close (collision risk), green = open path   |   closest %.1f m"
        ) % float(np.min(distances))
        canvas.blit(F_S.render(dist_text, True, (150, 160, 178)), (ix + 2, iy + ih + 26))

    # ---------------- PANEL 2: görsel yol ----------------
    p2 = pygame.Rect(14, 242, 620, 196)
    pygame.draw.rect(canvas, PANEL, p2, border_radius=10)
    p2_desc = ("2. GÖRSEL YOL — gerçek hücre tiplerinin ateşleme hızı"
               if is_tr else
               "2. VISUAL PATHWAY — biological firing rates of cell types")
    canvas.blit(F_LBL.render(p2_desc, True, TXT), (p2.x + 12, p2.y + 6))
    y = p2.y + 24
    watch_list = WATCH_TR if is_tr else WATCH_EN
    for tname, human in watch_list:
        r = brain.rate_of_type(tname)
        canvas.blit(F_MS.render("%-7s %-16s" % (tname, human), True, MUTE), (p2.x + 14, y))
        bar(p2.x + 195, y + 2, 300, 8, r / 40.0,
            (120, 200, 255) if r < 30 else (255, 180, 60))
        canvas.blit(F_MS.render("%5.1f Hz" % r, True, TXT), (p2.x + 505, y))
        y += 14

    # ---------------- PANEL 3: mantar cisimciği ----------------
    p3 = pygame.Rect(644, 242, CANVAS_W - 658, 196)
    pygame.draw.rect(canvas, PANEL, p3, border_radius=10)
    p3_desc = "3. MANTAR CİSİMCİĞİ (öğrenme)" if is_tr else "3. MUSHROOM BODY (learning)"
    canvas.blit(F_LBL.render(p3_desc, True, (255, 215, 0)), (p3.x + 12, p3.y + 6))
    kc = brain.spike_count[brain.kc_idx]
    silent = 100.0 * float((kc == 0).mean()) if len(kc) else 0.0
    kc_cell_str = ("Kenyon hücresi: %d" if is_tr else "Kenyon cells: %d") % len(brain.kc_idx)
    canvas.blit(F_M.render(kc_cell_str, True, TXT), (p3.x + 14, p3.y + 24))
    silent_str = ("sessiz: %%%.0f  (gerçek sinek %%90+)" if is_tr else "silent: %%%.0f  (real fly 90%%+)") % silent
    canvas.blit(F_M.render(silent_str, True,
                           GREEN if silent > 80 else (255, 180, 60)), (p3.x + 14, p3.y + 40))
    canvas.blit(F_M.render("KC   %5.2f Hz" % brain.rate(brain.kc_idx), True, TXT),
                (p3.x + 14, p3.y + 58))
    mbon_str = ("MBON %5.2f Hz  (%d hücre)" if is_tr else "MBON %5.2f Hz  (%d cells)") % (
        brain.rate(brain.mbon_idx), len(brain.mbon_idx))
    canvas.blit(F_M.render(mbon_str, True, TXT), (p3.x + 14, p3.y + 74))
    pam_str = ("PAM  %5.2f Hz  ödül" if is_tr else "PAM  %5.2f Hz  reward") % brain.rate(brain.pam_idx)
    canvas.blit(F_M.render(pam_str, True, GREEN), (p3.x + 14, p3.y + 92))
    ppl_str = ("PPL1 %5.2f Hz  ceza" if is_tr else "PPL1 %5.2f Hz  punish") % brain.rate(brain.ppl1_idx)
    canvas.blit(F_M.render(ppl_str, True, ALERT), (p3.x + 14, p3.y + 108))
    rpe = motor.get("rpe", 0.0)
    rpe_str = ("dopamin hata sinyali %+.3f" if is_tr else "dopamine error signal %+.3f") % rpe
    canvas.blit(F_M.render(rpe_str, True,
                           GREEN if rpe > 0 else (MUTE if abs(rpe) < .02 else ALERT)),
                (p3.x + 14, p3.y + 126))
    # KC aktivite şeridi
    n = min(300, len(kc))
    if n:
        bw = (p3.width - 30) / float(n)
        base = p3.y + 184
        act = kc[:n]
        mx = max(1.0, float(act.max()))
        for i in range(n):
            a = float(act[i]) / mx
            if a > 0:
                h = int(2 + a * 22)
                pygame.draw.rect(canvas, (int(90 + 165 * a), int(70 + 140 * a), 255),
                                 (p3.x + 15 + int(i * bw), base - h, max(1, int(bw)), h))
        pygame.draw.line(canvas, (58, 68, 84), (p3.x + 15, base), (p3.right - 15, base), 1)

    # ---------------- PANEL 4: inen nöronlar ----------------
    p4 = pygame.Rect(14, 444, CANVAS_W - 28, 114)
    pygame.draw.rect(canvas, PANEL, p4, border_radius=10)
    p4_desc = (
        "4. İNEN NÖRONLAR — motor komutu BURADAN okunuyor (kural yok, spike var)   | DNp20 girdisinin %68'i görsel, %44'ü ocelli"
        if is_tr else
        "4. DESCENDING NEURONS — motor decoded from spikes directly   | DNp20 input: 68% visual, 44% ocelli"
    )
    canvas.blit(F_LBL.render(p4_desc, True, TXT), (p4.x + 12, p4.y + 5))
    rates = motor["rates"]
    if is_tr:
        cols4 = [("DNp20 sol", motor["DNp20_L"], (120, 200, 255)),
                 ("DNp20 sağ", motor["DNp20_R"], (120, 200, 255)),
                 ("DNpe017 ileri", rates["forward"], GREEN),
                 ("MDN geri", rates["backward"], (255, 180, 60)),
                 ("DNp09 hızlı", rates["fast"], (255, 150, 200)),
                 ("DNp01 Giant Fiber", rates["escape"], ALERT)]
    else:
        cols4 = [("DNp20 left", motor["DNp20_L"], (120, 200, 255)),
                 ("DNp20 right", motor["DNp20_R"], (120, 200, 255)),
                 ("DNpe017 fwd", rates["forward"], GREEN),
                 ("MDN back", rates["backward"], (255, 180, 60)),
                 ("DNp09 fast", rates["fast"], (255, 150, 200)),
                 ("DNp01 Giant Fiber", rates["escape"], ALERT)]
    x = p4.x + 16
    for name, val, col in cols4:
        canvas.blit(F_MS.render(name, True, MUTE), (x, p4.y + 23))
        pygame.draw.rect(canvas, (38, 44, 56), (x, p4.y + 37, 150, 9), border_radius=3)
        pygame.draw.rect(canvas, col, (x, p4.y + 37, int(150 * min(1.0, val / 40.0)), 9),
                         border_radius=3)
        canvas.blit(F_M.render("%5.1f Hz" % val, True, TXT), (x, p4.y + 49))
        x += 172
    if is_tr:
        motor_str = ("MOTOR:  tork %+.3f   itiş %+.2f   geri %s   koşu %s   zıpla %s"
                     % (motor["steering_torque"], motor["forward_thrust"],
                        motor["back"], motor["sprint"], motor["jump"]))
        stats_str = ("Can %.0f/20   Tokluk %.0f/20   yön %.0f°   ortalama ağ aktivitesi %.2f Hz"
                     % (health, food, math.degrees(heading) % 360, brain.mean_rate))
    else:
        motor_str = ("MOTOR:  torque %+.3f   thrust %+.2f   back %s   sprint %s   jump %s"
                     % (motor["steering_torque"], motor["forward_thrust"],
                        motor["back"], motor["sprint"], motor["jump"]))
        stats_str = ("Health %.0f/20   Food %.0f/20   heading %.0f°   mean network activity %.2f Hz"
                     % (health, food, math.degrees(heading) % 360, brain.mean_rate))
    canvas.blit(F_M.render(motor_str, True, ACC), (p4.x + 16, p4.y + 67))
    canvas.blit(F_MS.render(stats_str, True, MUTE), (p4.x + 16, p4.y + 88))

    # ---------------- PANEL 5: ANTENLER (koku + işitme) ----------------
    p5a = pygame.Rect(14, 564, CANVAS_W - 28, 92)
    pygame.draw.rect(canvas, PANEL, p5a, border_radius=10)
    p5a_desc = (
        "5. ANTENLER + OCELLI — koku ORN'lere, ses Johnston organına, ışık OCG01'e giriyor"
        if is_tr else
        "5. ANTENNAE + OCELLI — odor to ORNs, sound to Johnston's organ, light to OCG01"
    )
    canvas.blit(F_LBL.render(p5a_desc, True, (180, 255, 150)), (p5a.x + 12, p5a.y + 5))

    ol, orr = senses.get("odor_l", 0.0), senses.get("odor_r", 0.0)
    snd, sname = senses.get("sound", 0.0), senses.get("sound_name", "")
    wind = senses.get("wind", 0.0)

    canvas.blit(F_MS.render("koku SOL anten" if is_tr else "odor LEFT antenna", True, MUTE), (p5a.x + 16, p5a.y + 23))
    bar(p5a.x + 130, p5a.y + 25, 140, 8, ol, (150, 245, 130))
    canvas.blit(F_MS.render("koku SAĞ anten" if is_tr else "odor RIGHT antenna", True, MUTE), (p5a.x + 16, p5a.y + 38))
    bar(p5a.x + 130, p5a.y + 40, 140, 8, orr, (150, 245, 130))
    _od = motor.get("odor_d", 0.0)
    _opath = senses.get("odor_path", -1.0)
    if is_tr:
        path_str = ("kokunun HAVADAN yolu: %s | kuş uçuşu %.1f m"
                    % (("%.1f m" % _opath) if _opath >= 0 else "ULAŞMIYOR (duvar arkasında)",
                       senses.get("food_dist", 99.0)))
        diff_str = ("anten farkı %+.2f | zaman değişimi %+.3f -> %s"
                    % (ol - orr, _od,
                       "YAKLAŞIYOR" if _od > 0.01 else
                       "UZAKLAŞIYOR — arıyor" if _od < -0.01 else "sabit"))
    else:
        path_str = ("odor AIR PATH: %s | direct dist %.1f m"
                    % (("%.1f m" % _opath) if _opath >= 0 else "BLOCKED (behind wall)",
                       senses.get("food_dist", 99.0)))
        diff_str = ("antenna delta %+.2f | temporal delta %+.3f -> %s"
                    % (ol - orr, _od,
                       "APPROACHING" if _od > 0.01 else
                       "RECEDING — searching" if _od < -0.01 else "stable"))
    canvas.blit(F_MS.render(path_str, True, GREEN if _opath >= 0 else MUTE), (p5a.x + 16, p5a.y + 54))
    canvas.blit(F_MS.render(diff_str, True, GREEN if _od > 0.01 else (ALERT if _od < -0.01 else MUTE)),
                (p5a.x + 16, p5a.y + 70))

    canvas.blit(F_MS.render("ORN  %5.2f Hz   PN %5.2f Hz   lateral horn %5.2f Hz"
                            % (brain.rate(np.concatenate([brain.orn_L, brain.orn_R]))
                               if len(brain.orn_L) + len(brain.orn_R) else 0.0,
                               brain.rate(brain.pn_idx), brain.rate(brain.lh_idx)),
                            True, TXT), (p5a.x + 330, p5a.y + 23))
    jo_desc = ("Johnston organı %5.2f Hz   (%d nöron)" if is_tr else "Johnston organ %5.2f Hz   (%d neurons)") % (
        brain.rate(brain.jo_idx), len(brain.jo_idx))
    canvas.blit(F_MS.render(jo_desc, True, TXT), (p5a.x + 330, p5a.y + 38))
    snd_desc = ("ses %.2f  %-22s hava akımı %.2f" if is_tr else "sound %.2f  %-22s wind flow %.2f") % (
        snd, sname[:22], wind)
    canvas.blit(F_MS.render(snd_desc, True, (255, 210, 120) if snd > 0.05 else MUTE),
                (p5a.x + 330, p5a.y + 54))

    # OCELLI
    _sky = senses.get("sky", 1.0)
    if is_tr:
        _gun = "GÜNDÜZ" if _sky > 0.7 else ("GECE" if _sky < 0.35 else "alacakaranlık")
        _gun_note = "  ocelli doygun" if _sky > 0.7 else "  ışık yönü okunur"
        oc_light_str = "ocellus ışığı  sol %.2f  sağ %.2f"
    else:
        _gun = "DAY" if _sky > 0.7 else ("NIGHT" if _sky < 0.35 else "twilight")
        _gun_note = "  ocelli saturated" if _sky > 0.7 else "  light bearing active"
        oc_light_str = "ocellus light  L %.2f  R %.2f"
    canvas.blit(F_MS.render("%s (%.2f)%s" % (_gun, _sky, _gun_note), True,
                (255, 235, 140) if _sky > 0.7 else (140, 170, 255)),
                (p5a.x + 690, p5a.y + 5))
    gl, gr = getattr(brain, "ocelli_lr", (0.0, 0.0))
    canvas.blit(F_MS.render(oc_light_str % (gl, gr), True, (255, 235, 140)), (p5a.x + 690, p5a.y + 23))
    canvas.blit(F_MS.render("OCG01  %s %5.2f Hz  %s %5.2f Hz" % (
        ("sol", brain.rate(brain.ocg_L), "sağ", brain.rate(brain.ocg_R)) if is_tr else
        ("L", brain.rate(brain.ocg_L), "R", brain.rate(brain.ocg_R))),
        True, TXT), (p5a.x + 690, p5a.y + 38))

    # TEHLİKE / SU / SICAKLIK / ENVANTER
    _inv = senses.get("inv_empty", -1)
    if _inv == 0:
        canvas.blit(F_LBL.render("ENVANTER DOLU!" if is_tr else "INVENTORY FULL!", True, ALERT), (p5a.x + 330, p5a.y + 5))
    elif _inv > 0 and senses.get("food_dist", 99.0) < 16.0:
        inv_str = ("yerde yemek %.1f m (boş %d)" if is_tr else "food on ground %.1f m (empty %d)") % (
            senses["food_dist"], _inv)
        canvas.blit(F_MS.render(inv_str, True, (150, 245, 130)), (p5a.x + 330, p5a.y + 5))

    _cr, _cp = senses.get("chat_reward", 0.0), senses.get("chat_punish", 0.0)
    if _cr > 0.02 or _cp > 0.02:
        if is_tr:
            chat_lbl = "SOHBET: %s" % ("ÖDÜL" if _cr > _cp else "CEZA")
        else:
            chat_lbl = "CHAT: %s" % ("REWARD" if _cr > _cp else "PUNISH")
        canvas.blit(F_LBL.render(chat_lbl, True, GREEN if _cr > _cp else ALERT), (p5a.x + 200, p5a.y + 5))

    _w_ahead = senses.get("water_ahead", False)
    _w_below = senses.get("water_below", False)
    _w_dist = float(senses.get("water_dist", 99.0))
    _hum = float(senses.get("humidity", 0.0))
    _heat = senses.get("heat", 0.0)
    _cold = senses.get("cold", 0.0)
    _rain = senses.get("is_raining", False)
    if _w_ahead or _w_below or _w_dist < 6.0:
        w_tag = ("[ALT]" if _w_below else "[ÖN]") if is_tr else ("[BELOW]" if _w_below else "[AHEAD]")
        w_title = "SU TEHLİKESİ: %.1f m %s" if is_tr else "WATER HAZARD: %.1f m %s"
        canvas.blit(F_LBL.render(w_title % (_w_dist, w_tag), True, (45, 175, 255)), (p5a.x + 480, p5a.y + 70))
    elif _heat > 0.02:
        canvas.blit(F_LBL.render(("SICAK %.2f" if is_tr else "HEAT %.2f") % _heat, True, (255, 140, 60)), (p5a.x + 480, p5a.y + 70))
    elif _cold > 0.05 or _rain:
        canvas.blit(F_LBL.render("SOĞUK / YAĞMUR" if is_tr else "COLD / RAIN", True, (140, 215, 255)), (p5a.x + 480, p5a.y + 70))

    hb = senses.get("hazard_bearing")
    if hb is not None and max(senses.get("mech", 0.0), senses.get("obst", 0.0)) > 0.0:
        if is_tr:
            side = "SOL" if hb > 0.05 else ("SAĞ" if hb < -0.05 else "TAM ÖN")
            hz_str = "tehlike: %s -> ters yön" % side
        else:
            side = "LEFT" if hb > 0.05 else ("RIGHT" if hb < -0.05 else "FRONT")
            hz_str = "hazard: %s -> reverse turn" % side
        canvas.blit(F_MS.render(hz_str, True, ALERT), (p5a.x + 690, p5a.y + 54))

    # ---------------- PANEL 6: İÇSEL DURUM ----------------
    p6 = pygame.Rect(14, 662, CANVAS_W - 28, 48)
    pygame.draw.rect(canvas, PANEL, p6, border_radius=10)
    p6_desc = (
        "6. İÇSEL DURUM — gerçek dopamin nöronlarından (uydurma değil)"
        if is_tr else
        "6. INTERNAL STATE — decoded from dopamine neurons (MaleCNS connectome)"
    )
    canvas.blit(F_LBL.render(p6_desc, True, (255, 170, 210)), (p6.x + 12, p6.y + 4))

    pam_v = motor.get("pam_dev_s", 0.0)
    ppl_v = motor.get("ppl_dev_s", 0.0)
    esc_v = motor.get("esc_dev_s", 0.0)
    mb_v = motor.get("rpe", 0.0)
    hunger = float(np.clip((20.0 - food) / 20.0, 0.0, 1.0))

    if is_tr:
        drives = [
            ("İŞTAH / ÖDÜL", min(1.0, max(0.0, pam_v) / 3.0), (90, 230, 140), "PAM sapma"),
            ("KAÇINMA / CEZA", min(1.0, max(0.0, ppl_v) / 3.0), (255, 150, 90), "PPL1 sapma"),
            ("TEHLİKE / KAÇIŞ", min(1.0, esc_v / 6.0), (255, 80, 95), "DNp01+04"),
            ("AÇLIK", hunger, (150, 190, 255), "besin"),
            ("KOKU UYARIMI", min(1.0, max(0.0, motor.get("arousal", 0.0))),
             (255, 215, 120), "KC %.1f Hz" % motor.get("kc_rate", 0.0)),
            ("ARAMA (kayıp)", min(1.0, max(0.0, motor.get("odor_lost", 0.0))),
             (200, 160, 255), "koku düşüyor"),
            ("ÖĞRENME SİNYALİ", min(1.0, abs(mb_v) * 8.0),
             GREEN if mb_v >= 0 else ALERT, "dopamin hatası"),
        ]
    else:
        drives = [
            ("APPETITE / REWARD", min(1.0, max(0.0, pam_v) / 3.0), (90, 230, 140), "PAM dev"),
            ("AVERSION / PUNISH", min(1.0, max(0.0, ppl_v) / 3.0), (255, 150, 90), "PPL1 dev"),
            ("DANGER / ESCAPE", min(1.0, esc_v / 6.0), (255, 80, 95), "DNp01+04"),
            ("HUNGER", hunger, (150, 190, 255), "nutrients"),
            ("ODOR AROUSAL", min(1.0, max(0.0, motor.get("arousal", 0.0))),
             (255, 215, 120), "KC %.1f Hz" % motor.get("kc_rate", 0.0)),
            ("SEARCH (lost)", min(1.0, max(0.0, motor.get("odor_lost", 0.0))),
             (200, 160, 255), "odor falling"),
            ("LEARNING SIGNAL", min(1.0, abs(mb_v) * 8.0),
             GREEN if mb_v >= 0 else ALERT, "dopamine error"),
        ]
    bx = p6.x + 16
    bw = (p6.width - 44) // len(drives)
    for name, frac, col, src in drives:
        canvas.blit(F_MS.render(name, True, MUTE), (bx, p6.y + 17))
        bar(bx, p6.y + 28, bw - 20, 7, frac, col)
        canvas.blit(F_MS.render(src, True, (92, 104, 122)), (bx, p6.y + 36))
        bx += bw

    # ---------------- PANEL 7: davranış ----------------
    p5 = pygame.Rect(14, 716, CANVAS_W - 28, 58)
    pygame.draw.rect(canvas, PANEL, p5, border_radius=10)
    gf = rates["escape"]
    ev = getattr(brain, "sign_evidence", {}) or {}
    if is_tr:
        if gf > 6:
            st, sc = "GIANT FIBER — acil sıçrama", ALERT
        elif rates["backward"] > 9:
            st, sc = "MDN — geri yürüyor", (255, 180, 60)
        elif rates["fast"] > 10:
            st, sc = "DNp09 — hızlı kaçış", (255, 150, 200)
        elif rates["forward"] > 12:
            st, sc = "DNpe017 — ileri yürüyor", GREEN
        elif abs(motor["steering_torque"]) > 0.25:
            st, sc = "DNp20 — dönüyor", (120, 200, 255)
        else:
            st, sc = "düşük aktivite — bekliyor", MUTE
        sub_p5 = ("Bu satır bir kuraldan değil, hangi inen nöronun ateşlediğinden geliyor. "
                  "Veri: MaleCNS v1.0 (Janelia/Cambridge/MRC LMB/Google) CC BY 4.0")
        sign_p5 = ("dönüş işareti %+.0f (fototaksi: %.1f, optomotor: %.1f) | duyu: LIF + graded | motor: DNp20/DNpe017"
                   % (getattr(brain, "steer_sign", 1.0),
                      ev.get("phototaxis_effect", 0.0),
                      ev.get("optomotor_effect", 0.0)))
    else:
        if gf > 6:
            st, sc = "GIANT FIBER — emergency jump", ALERT
        elif rates["backward"] > 9:
            st, sc = "MDN — backward crawling", (255, 180, 60)
        elif rates["fast"] > 10:
            st, sc = "DNp09 — fast sprint", (255, 150, 200)
        elif rates["forward"] > 12:
            st, sc = "DNpe017 — walking forward", GREEN
        elif abs(motor["steering_torque"]) > 0.25:
            st, sc = "DNp20 — steering", (120, 200, 255)
        else:
            st, sc = "low activity — hovering/idle", MUTE
        sub_p5 = ("Behavior decoded directly from descending neuron spikes (no hardcoded rules). "
                  "Data: MaleCNS v1.0 (Janelia/Cambridge/MRC LMB/Google) CC BY 4.0")
        sign_p5 = ("steering sign %+.0f (phototaxis: %.1f, optomotor: %.1f) | senses: LIF + graded | motor: DNp20/DNpe017"
                   % (getattr(brain, "steer_sign", 1.0),
                      ev.get("phototaxis_effect", 0.0),
                      ev.get("optomotor_effect", 0.0)))

    canvas.blit(F_BIG.render(st, True, sc), (p5.x + 16, p5.y + 4))
    canvas.blit(F_S.render(sub_p5, True, MUTE), (p5.x + 16, p5.y + 29))
    canvas.blit(F_MS.render(sign_p5, True, (140, 185, 165)), (p5.x + 16, p5.y + 42))

    if _ov:
        draw_neural_overlay(brain, motor, extra, lang=lang)

    cur_size = screen.get_size()
    if cur_size == (CANVAS_W, CANVAS_H):
        screen.blit(canvas, (0, 0))
    else:
        scaled = pygame.transform.smoothscale(canvas, cur_size)
        screen.blit(scaled, (0, 0))
    pygame.display.flip()


# ============================================================================
async def bridge_loop(ws_host="localhost", ws_port=8765, label="Drosophila_Fly",
                      gain=3.0, tonic_floor=None, target_hz=2.0, logging=False,
                      as_server=False, debug=False):
    global screen
    print("=" * 70)
    print("  GERÇEK KONEKTOM YÜKLENİYOR (MaleCNS v1.0)")
    print("=" * 70)
    if tonic_floor is None:
        tonic_floor = fly_brain_real.TONIC_FLOOR
    brain = RealFlyBrain(gain=gain, tonic_floor=tonic_floor, verbose=True)
    print("  kalibrasyon (tonik + dönüş sapması + dönüş işareti)...")
    brain.calibrate_all(target_hz=target_hz, verbose=True)

    log = FlyLogger(label=label, enabled=logging)
    if log.enabled:
        log.header(brain, {"gain": gain, "tonic_floor": tonic_floor,
                           "locomotor": 0.60, "ws_port": ws_port})
        print("  📝 ayrıntılı kayıt: %s" % log.path)
        print("     (sorun olursa bu dosyayı gönder)")
    print("=" * 70)

    mem_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    mem_file = os.path.join(mem_dir, "memory_%s.npz" % label)
    if os.path.exists(mem_file):
        brain.load_memory(mem_file)

    pygame.display.set_caption("🪰 %s — MaleCNS v1.0 Gerçek Konektom" % label)
    prev_health = 20.0
    prev_food_items = 0
    adapt_o = 0.0        # engel sinyali uyum izi (fazik mekanoduyu)
    adapt_m = 0.0        # nosiseptif uyum izi
    stale_total = 0      # yetişemeyip atılan eski kare sayısı
    wing = WingBeat(enabled=SOUND_ON)   # kanat vuruşu sesi (S tuşu açar/kapatır)
    esc_dir = 0          # kilitlenmiş kaçış dönüş yönü (+1 sol / -1 sağ)
    esc_t = 0.0          # kilidin kurulduğu an
    ESC_MAX_S = 3.5      # bu kadar sürdüyse ve hâlâ kapalıysa ters tarafı dene
    last_mem_save = 0.0
    prev_retina_floor = None
    loaded_fly_id = label
    is_bottled = False
    AUTH_TOKEN = (
        os.environ.get("FLY_AUTH_TOKEN")
        or os.environ.get("MINECRAFT_PASSWORD")
        or os.environ.get("PASSWORD")
        or os.environ.get("AUTH_TOKEN")
        or ""
    ).strip()
    uri = f"ws://{ws_host}:{ws_port}?token={AUTH_TOKEN}" if AUTH_TOKEN else f"ws://{ws_host}:{ws_port}"
    current_lang = "en"
    lang_synced = False

    if IS_HEADLESS:
        print("[RealBrain] 🖥️ Headless Terminal Mode (--no-gui) active."
              if current_lang != "tr" else "[GerçekBeyin] 🖥️ Sadece Terminal Modu (--no-gui) devrede.")

    if as_server:
        print("[RealBrain] 🌐 WebSocket Server listening: 0.0.0.0:%d" % ws_port
              if current_lang != "tr" else "[GerçekBeyin] 🌐 WebSocket Sunucusu dinliyor: 0.0.0.0:%d" % ws_port)
        print("              FruitFly plugin will connect to this address."
              if current_lang != "tr" else "              Minecraft Paper/Spigot sunucusundaki FruitFly eklentisi buraya bağlanacak.")
        if not IS_HEADLESS:
            screen.fill(BG)
            msg = "Waiting for FruitFly plugin (0.0.0.0:%d)..." % ws_port if current_lang != "tr" else "FruitFly eklentisi bekleniyor (0.0.0.0:%d)..." % ws_port
            t = F_LBL.render(msg, True, ALERT)
            screen.blit(t, (screen.get_width() // 2 - t.get_width() // 2, screen.get_height() // 2))
            pygame.display.flip()

        incoming_queue = asyncio.Queue()
        active_ws = None

        async def _client_handler(ws):
            nonlocal active_ws
            if active_ws is not None:
                try:
                    await active_ws.close(1001, "New connection replacing old")
                except Exception:
                    pass
            active_ws = ws
            await incoming_queue.put(ws)
            await ws.wait_closed()

        server = await websockets.serve(_client_handler, "0.0.0.0", ws_port, max_size=2 ** 24, ping_interval=5, ping_timeout=3)
    else:
        if not IS_HEADLESS:
            screen.fill(BG)
            msg = f"Waiting for Minecraft server ({ws_host}:{ws_port})..." if current_lang != "tr" else f"Minecraft sunucusu bekleniyor ({ws_host}:{ws_port})..."
            t = F_LBL.render(msg, True, ALERT)
            screen.blit(t, (screen.get_width() // 2 - t.get_width() // 2, screen.get_height() // 2))
            pygame.display.flip()

    waiting_logged = False
    while True:
        try:
            if as_server:
                ws = await incoming_queue.get()
                remote_ip = str(getattr(ws, 'remote_address', None) or 'client')
                print("[RealBrain] ✅ FruitFly plugin connected: %s" % remote_ip
                      if current_lang != "tr" else "[GerçekBeyin] ✅ FruitFly eklentisi bağlandı: %s" % remote_ip)
                log.event("BAĞLANTI", "fruitfly connected: %s" % remote_ip)
            else:
                if not waiting_logged:
                    print(f"[RealBrain] ⏳ Waiting for Minecraft Server: ws://{ws_host}:{ws_port}"
                          if current_lang != "tr" else f"[GerçekBeyin] ⏳ Minecraft Paper Sunucusu bekleniyor: ws://{ws_host}:{ws_port}")
                    waiting_logged = True
                ws = await websockets.connect(uri, max_size=2 ** 24)
                print(f"[RealBrain] ✅ Connected to Minecraft Server: {ws_host}:{ws_port}"
                      if current_lang != "tr" else f"[GerçekBeyin] ✅ Minecraft Paper Sunucusuna bağlandı: {ws_host}:{ws_port}")
                waiting_logged = False
                log.event("BAĞLANTI", f"sunucuya bağlandı: {ws_host}:{ws_port}")

            async with ws:
                last_log = 0.0

                # --- HER ZAMAN EN YENİ KARE ---
                # Ayrı bir okuyucu görev soketi sürekli boşaltır ve yalnızca
                # EN SON kareyi saklar. Beyin hangi hızda çalışırsa çalışsın
                # daima en taze görüntüyü görür.
                #
                # Eskiden bu iş ana döngüde şöyle yapılıyordu:
                #     await asyncio.wait_for(ws.recv(), timeout=0.0)
                # ve HİÇ ÇALIŞMIYORDU: timeout<=0 olunca wait_for coroutine'i
                # bir kez bile çalıştırmadan iptal edip TimeoutError atıyor.
                # Ölçüldü (kuyrukta 10 kare): timeout=0.0 ile atılan 0, işlenen
                # kare EN ESKİSİ. Bot 20 Hz gönderirken beyin 18 Hz işliyor,
                # yani saniyede ~2 kare kuyruğa ekleniyordu ve hiç atılmıyordu.
                # Bir dakika sonra sinek ~2 saniye geriden geliyordu.
                newest = {"raw": None, "seq": 0}
                fresh = asyncio.Event()

                async def _reader():
                    try:
                        while True:
                            newest["raw"] = await ws.recv()
                            newest["seq"] += 1
                            fresh.set()
                    finally:
                        fresh.set()      # okuyucu ölürse ana döngü uyansın

                reader = asyncio.create_task(_reader())
                last_seq = 0
                show_neural_overlay = False
                while True:
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT or (
                                ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                            wing.close()
                            pygame.quit()
                            sys.exit()
                        elif ev.type == pygame.VIDEORESIZE:
                            screen = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
                        _win_w, _win_h = screen.get_size()
                        _mx = ev.pos[0] * (CANVAS_W / max(1, _win_w)) if hasattr(ev, 'pos') else 0
                        _my = ev.pos[1] * (CANVAS_H / max(1, _win_h)) if hasattr(ev, 'pos') else 0
                        _tikla = (ev.type == pygame.MOUSEBUTTONDOWN
                                  and ev.button == 1
                                  and SES_BTN.collidepoint((_mx, _my)))
                        if _tikla or (ev.type == pygame.KEYDOWN
                                      and ev.key == pygame.K_s):
                            is_on = wing.toggle()
                            print("[Audio] wing + ear %s" % ("ON" if is_on else "off")
                                  if current_lang != "tr" else "[Ses] kanat + kulak %s" % ("AÇIK" if is_on else "kapalı"))

                        _tikla_neural = (ev.type == pygame.MOUSEBUTTONDOWN
                                         and ev.button == 1
                                         and NEURAL_BTN.collidepoint((_mx, _my)))
                        if _tikla_neural or (ev.type == pygame.KEYDOWN
                                             and ev.key in (pygame.K_TAB, pygame.K_SPACE)):
                            show_neural_overlay = not show_neural_overlay
                            print("[Neural Map] %s" % ("ON" if show_neural_overlay else "off")
                                  if current_lang != "tr" else "[Nöral Harita] %s" % ("AÇIK" if show_neural_overlay else "kapalı"))

                    # Yeni kare bekle. Okuyucu görev bu arada soketi
                    # boşaltmaya devam ediyor; biz uyandığımızda elimizde
                    # daima EN SON kare oluyor, aradakiler atılmış sayılıyor.
                    while newest["seq"] == last_seq:
                        if reader.done():
                            await reader          # gerçek hatayı yükseltir
                            raise ConnectionError("bot bağlantısı kapandı")
                        fresh.clear()
                        if newest["seq"] != last_seq:
                            break
                        await fresh.wait()
                    # DİKKAT: 'dropped' adı aşağıda koku mesafesi için de
                    # kullanılıyor; sayaç ayrı isimde olmalı.
                    stale_now = newest["seq"] - last_seq - 1
                    last_seq = newest["seq"]
                    raw = newest["raw"]
                    stale_total += stale_now
                    fps_tick()
                    tnow = pygame.time.get_ticks() / 1000.0
                    data = json.loads(raw)
                    if not lang_synced:
                        if data.get("lang") == "tr":
                            current_lang = "tr"
                        lang_synced = True

                    # --- AUTH TOKEN GÜVENLİK DOĞRULAMASI ---
                    client_token = data.get("auth_token")
                    if AUTH_TOKEN and client_token and client_token != AUTH_TOKEN:
                        print("[RealBrain] ⚠️ Unauthorized auth token — connection rejected."
                              if current_lang != "tr" else "[GerçekBeyin] ⚠️ Yetkisiz token — bağlantı reddedildi.")
                        await ws.close(1008, "Invalid auth token")
                        break

                    # --- ŞİŞE / DİNLENME (BOTTLE / UNBOTTLE) KOMUTLARI ---
                    cmd = data.get("command")
                    if cmd == "bottle" or data.get("bottled") is True:
                        _target_id = str(data.get("fly_id") or label)
                        is_bottled = True
                        print("[RealBrain] 🍾 '%s' bottled! Simulation paused (0 CPU)." % _target_id
                              if current_lang != "tr" else "[GerçekBeyin] 🍾 '%s' şişeye alındı! Simülasyon donduruldu (0 CPU)." % _target_id)
                        log.event("ŞİŞELENDİ", "%s bottled" % _target_id)
                        continue
                    elif cmd == "unbottle":
                        _target_id = str(data.get("fly_id") or label)
                        is_bottled = False
                        print("[RealBrain] 🐝 '%s' unbottled! MaleCNS brain awakened." % _target_id
                              if current_lang != "tr" else "[GerçekBeyin] 🐝 '%s' şişeden salındı! MaleCNS beyni uyandı." % _target_id)
                        log.event("SALINDI", "%s unbottled" % _target_id)
                        continue

                    if is_bottled:
                        await asyncio.sleep(0.08)
                        continue

                    # --- AKILLI DİNLENME (Smart Sleep - 4 Güvenlik Kuralı) ---
                    is_sleeping = bool(data.get("is_sleeping", False))
                    if is_sleeping:
                        await ws.send(json.dumps({
                            "forward": False, "back": False,
                            "steering_torque": 0.0, "pitch": 0.0,
                            "jump": False, "sprint": False, "is_sleeping": True
                        }))
                        await asyncio.sleep(0.08)
                        continue

                    # --- HAFIZA SIFIRLAMA KOMUTU ---
                    if data.get("command") == "reset_memory" or data.get("reset_memory") is True:
                        _target_id = str(data.get("fly_id") or label)
                        _target_mem = os.path.join(mem_dir, "memory_%s.npz" % _target_id)
                        brain.reset_memory(_target_mem)
                        print("[RealBrain] 🔄 '%s' brain memory reset (reverted to baseline connectome)." % _target_id
                              if current_lang != "tr" else "[GerçekBeyin] 🔄 '%s' sineğinin hafızası sıfırlandı (taban konektoma döndü)." % _target_id)
                        log.event("SIFIRLANDI", "hafıza sıfırlandı: %s" % _target_id)
                        if "distances" not in data:
                            await ws.send(json.dumps({"status": "ok", "action": "memory_reset"}))
                            continue

                    current_fly_id = str(data.get("fly_id") or label)
                    mem_file = os.path.join(mem_dir, "memory_%s.npz" % current_fly_id)
                    if current_fly_id != loaded_fly_id:
                        loaded_fly_id = current_fly_id
                        if os.path.exists(mem_file):
                            brain.load_memory(mem_file)

                    hd = data.get("retina_hd")
                    cols = int(data.get("hd_cols") or 32)
                    rows = int(data.get("hd_rows") or 6)
                    if hd is None:
                        hd = data.get("retina")
                        cols, rows = 32, 6
                    distances = np.array(data.get("distances", [16.0] * 32),
                                         dtype=np.float32)
                    health = float(data.get("health", 20.0))
                    food = float(data.get("food", 20.0))
                    heading = float(data.get("heading", 0.0))

                    # --- mekanoreseptör / nosiseptör sinyalleri ---
                    hurt = bool(data.get("hurt", False))
                    dmg = max(0.0, prev_health - health)
                    prev_health = health
                    # Nosiseptif darbe uyarımı (Babcock et al. 2009)
                    pain = 1.0 if (hurt or dmg > 0.1) else 0.0
                    # İKİ AYRI SİNYAL
                    #   mech  -> MDN, GERİ yürüyüş. Yalnızca acı veren veya
                    #            gerçekten geçilemez durumlar.
                    #   obst  -> yalnızca DÖNÜŞ. "Önümde bir şey var" demek
                    #            geri vitese takmak değildir; gerçek sinek de
                    #            duvara gelince döner, geri geri gitmez.
                    # (Eskiden duvar da mech'e yazılıyordu ve sinek köyde
                    #  sürekli geri gidiyordu.)
                    # SU VE HİGRO-RESEPSİYON (Nem ve Su Algısı)
                    water_ahead = bool(data.get("water_ahead", False))
                    water_below = bool(data.get("water_below", False))
                    water_dist = float(data.get("water_dist", 99.0))
                    water_bearing = float(data.get("water_bearing", 0.0))
                    humidity = float(data.get("humidity", 0.0))

                    mech = 0.0
                    obst = 0.0
                    if data.get("hazard_ahead"):
                        mech = max(mech, 1.0)     # kaktüs/ateş/lav: acı
                    if data.get("in_water") or water_below:
                        mech = max(mech, 0.85)    # suya düştü/altı su: acil yüzeye/havaya fırla
                    if water_ahead or water_dist < 4.5:
                        obst = max(obst, 0.85)    # su önde: dön, suya dalma!
                    if humidity > 0.65:
                        obst = max(obst, 0.60)
                    if data.get("wall_ahead"):
                        obst = max(obst, 0.90)    # tırmanılamaz duvar: dön
                    stuck = int(data.get("stuck_ticks", 0))

                    # YÜK: "ileri itiyorum ama yer değiştirmiyorum".
                    # ÖNEMLİ — bu sinyal ARTIK engel (dönüş) kanalına girmiyor.
                    # Eskiden giriyordu ve şu döngüyü kuruyordu:
                    #     dönüyor -> ilerleyemiyor -> takılma artıyor ->
                    #     engel artıyor -> daha çok dönüyor
                    # yani sinek köşede fırıl fırıl dönüyordu. Yük artık
                    # yalnızca YÜRÜME DÜRTÜSÜNÜ keser; dönüş yönünü göz verir.
                    load = min(1.0, max(0.0, (stuck - 3) / 13.0))
                    if bool(data.get("wall_ahead")):
                        obst = max(obst, 0.80)
                    if stuck > 18:
                        # çok uzun süre kıpırdayamıyor: geri çekilmeyi dene
                        mech = max(mech, min(0.9, (stuck - 18) / 12.0))

                    # --- MEKANODUYU UYUMU (fazik yanıt) ---
                    # Gerçek mekanoreseptörler FAZİKTİR: temas anında güçlü
                    # ateşler, temas sürerse yanıt söner. Bu olmadan şöyle bir
                    # döngü kuruluyordu:
                    #     dönüyor -> ilerleyemiyor -> stuck artıyor ->
                    #     engel sinyali artıyor -> daha çok dönüyor
                    # yani sinek yerinde fırıl fırıl dönüyordu. Uyum, duvara
                    # yaslanan sineğin sonsuza kadar "duvar!" sinyali almasını
                    # engeller; bir süre sonra kendi yürüme dürtüsü baskın olur.
                    obst_raw, mech_raw = obst, mech
                    adapt_o = 0.94 * adapt_o + 0.06 * obst_raw
                    adapt_m = 0.985 * adapt_m + 0.015 * mech_raw   # acı yavaş uyum
                    # ENGEL ARTIK BÜYÜK ÖLÇÜDE TONİK.
                    # Ölçüm (4143 kare): duvara yaslandıktan 1 sn sonra engel
                    # 0.50 -> 0.18'e sönüyordu; dönüş dürtüsü tam ihtiyaç
                    # anında kayboluyor, sinek duvara yapışıp kalıyordu. Oysa
                    # 1-3 m öndeki duvar GÖRSEL bir uyarandır (ışın izleme =
                    # göz), mekanik temas değil; görme uyumla sıfıra inmez.
                    # Uyum katsayısı 0.80 -> 0.25. Fırıl fırıl dönme döngüsü
                    # zaten takılmayı engel kanalından ayırarak kırıldı.
                    obst = float(max(0.0, obst_raw - 0.25 * adapt_o))
                    mech = float(max(0.0, mech_raw - 0.45 * adapt_m))

                    # ---------------- KAÇIŞ YÖNÜ ----------------
                    # ÖLÇÜM (1595 kare, 235554 logu): sinek 87 saniyede NET
                    # 0.1 blok yer değiştirdi, karelerin %56'sı tek bir blokta
                    # geçti, dönüş verimi %1 — sola döndüğü kadar sağa dönüyor.
                    # Sebep: kaçış yönü neredeyse eşit iki sayının ikili
                    # karşılaştırmasıydı (sol yarının en yakın bloğu vs sağ
                    # yarınınki). Düz duvara dik bakarken bu iki sayı eşittir;
                    # işaret yazı-tura oluyor ve kilit dolunca yarısında ters
                    # tarafı seçiyordu. Üstelik sonuç hep ±0.6/±0.7 idi:
                    # dünyanın ne kadar asimetrik olduğu bilgisi atılıyordu.
                    #
                    # Artık AÇIK YÖN, 32 sütunluk mesafe profilinin tamamından
                    # ağırlıklı ortalamayla çıkarılıyor (büyüklüğü de var) ve
                    # seçilen yön DUVAR GERÇEKTEN TEMİZLENENE kadar korunuyor.
                    # Düz duvara dik bakan bir sineğin elinde asimetri bilgisi
                    # YOKTUR; yapması gereken bir tarafa bağlanıp duvarı
                    # geçene kadar sürdürmektir.
                    free = 0.0
                    if len(distances) == 32:
                        op = np.clip(distances / 8.0, 0.0, 1.0) ** 2
                        w = op * np.cos(SCAN_ANG * 0.5)   # arka yarıküre az çeksin
                        den = float(w.sum())
                        if den > 1e-6:
                            free = float((w * SCAN_ANG).sum() / den)

                    blocked = max(mech, obst, load)
                    if esc_dir != 0 and blocked < 0.10:
                        esc_dir = 0                      # duvar geçildi
                    elif blocked > 0.25:
                        if esc_dir == 0:
                            # Bot gerçek bir tehlike bloğu (lav/ateş/kaktüs/su)
                            # gördüyse yönü ondan gelir; yoksa açık taraftan.
                            hzb = data.get("hazard_bearing")
                            hzs = float(data.get("hazard_score", 0.0) or 0.0)
                            if (water_ahead or water_dist < 5.0) and abs(water_bearing) > 1e-4:
                                esc_dir = -1 if water_bearing > 0 else 1
                            elif hzs > 0.05 and hzb and abs(float(hzb)) > 1e-6:
                                esc_dir = -1 if float(hzb) > 0 else 1
                            else:
                                esc_dir = 1 if free >= 0.0 else -1   # +1 = sola kaç
                            esc_t = time.monotonic()
                        elif (time.monotonic() - esc_t) > ESC_MAX_S:
                            esc_dir = -esc_dir           # uzun sürdü, ters tarafı dene
                            esc_t = time.monotonic()

                    if esc_dir != 0:
                        mag = 0.40 + 0.60 * min(1.0, abs(free) / (math.pi / 3.0))
                        hazard_bearing = -esc_dir * (math.pi / 2.0) * mag
                    else:
                        hazard_bearing = None

                    # --- İŞİTME (Johnston organı) ---
                    sound = float(np.clip(data.get("sound_level", 0.0), 0.0, 1.0))
                    sound_bearing = float(data.get("sound_bearing", 0.0))
                    wind = float(np.clip(data.get("wind", 0.0), 0.0, 1.0))

                    # --- YAKLAŞAN TEHDİT (LC4/LPLC2 Looming Dedektörleri) ---
                    # Tehdit mesafesi ve yönü doğrudan MaleCNS optik lobundaki
                    # looming nöronlarına (LC4/LPLC2) aktarılır. Bkz. inject_loom().
                    td = float(data.get("threat_dist", 99.0))
                    loom = 0.0
                    loom_bearing = float(data.get("threat_bearing", 0.0) or 0.0)
                    if td < 12.0:
                        # yakınlık arttıkça büyüme sinyali artar (1/mesafe)
                        loom = float(np.clip((12.0 - td) / 10.0, 0.0, 1.0)) ** 1.6
                    # YÖN İŞARETİ:
                    # Minecraft ve petek gözde:
                    #   * ileri yön (-sin yaw, -cos yaw); yaw büyüdükçe SOLA döner.
                    #   * sol yarı daha darsa hazardBearing > 0 yazılır -> POZİTİF = SOL.
                    #   * koku da aynı formülle hesaplanır ve bearing > 0 iken odorLeft'e yazılır.
                    # Yani beyin ve eklenti sözleşmesi: "+ = SOL", tork > 0 = SAĞA dönüş.
                    loom_bearing = float(loom_bearing)

                    # --- TAT (ayak tat reseptörleri) ---
                    # Sinek yemeğin üstündeyse / elinde tutuyorsa ayağı şekeri
                    # tadar. Açlık burada bir KARAR değil, reseptör KAZANCIDIR:
                    # aç sinekte PER eşiği düşer (Dethier 1976). Karar ağın.
                    _hunger = float(np.clip((20.0 - food) / 20.0, 0.0, 1.0))
                    taste = float(data.get("taste", 0.0))
                    if int(data.get("food_count", 0)) > 0:
                        taste = max(taste, 0.30 + 0.70 * _hunger)      # envanterde yemek var
                    if float(data.get("dropped_food_dist", 99.0)) < 1.4:
                        taste = max(taste, 0.45 + 0.55 * _hunger)   # üstünde duruyor
                    if data.get("is_eating"):
                        taste = max(taste, 0.5)            # ağzında, devam etsin

                    # --- dopamin ---
                    food_items = int(data.get("food_count", 0))
                    got = food_items > prev_food_items
                    prev_food_items = food_items
                    hunger = float(np.clip((20.0 - food) / 12.0, 0.15, 1.0))
                    reward = (0.9 * hunger) if got else 0.0
                    if taste > 0.4:
                        reward = max(reward, 0.85 * hunger) # Tatlı nektar / şeker ödülü (PAM)
                    punish = 1.0 if pain > 0 else 0.0
                    if taste < -0.1:
                        punish = max(punish, 0.95)          # Zehirli/acı tat cezası (PPL1)
                    heat_val = float(data.get("heat", 0.0) or 0.0)
                    if heat_val > 0.05:
                        punish = max(punish, heat_val * 0.7) # Aşırı sıcaklık cezası (PPL1)
                    if water_below or data.get("in_water") or humidity > 0.8:
                        punish = max(punish, 0.80)          # Suda boğulma / ıslanma tehlikesi cezası (PPL1)
                    # SOHBETTEN KOŞULLAMA — deneycinin şekeri/şoku.
                    # Gerçek sinek deneyinde de ödül/ceza dışarıdan verilir;
                    # biz yalnızca pekiştireci veriyoruz, ne öğreneceğine
                    # ağ karar veriyor (KC->MBON plastisitesi zaten çalışıyor).
                    _cr = float(data.get("chat_reward", 0.0) or 0.0)
                    _cp = float(data.get("chat_punish", 0.0) or 0.0)
                    if _cr > 0.02:
                        reward = max(reward, 0.9 * _cr)
                    if _cp > 0.02:
                        punish = max(punish, 1.0 * _cp)
                    # --- KOKU (Antenal Koku Reseptörleri) ---
                    # Sol ve sağ anten koku konsantrasyonu bağımsız olarak okunur.
                    dropped = float(data.get("dropped_food_dist", 99.0))
                    odor_l = float(np.clip(data.get("odor_left", 0.0), 0.0, 1.0))
                    odor_r = float(np.clip(data.get("odor_right", 0.0), 0.0, 1.0))
                    odor = max(odor_l, odor_r)

                    # --- SICAKLIK, SOĞUKLUK, OCELLI VE GÖKYÜZÜ PUSULASI ---
                    heat = float(np.clip(data.get("heat", 0.0) or 0.0, 0.0, 1.0))
                    cold = float(np.clip(data.get("cold", 0.0) or 0.0, 0.0, 1.0))
                    is_raining = bool(data.get("is_raining", False))
                    ocellus_l = float(data.get("ocellus_left", 0.0) or 0.0)
                    ocellus_r = float(data.get("ocellus_right", 0.0) or 0.0)
                    sun_b = float(data.get("sun_bearing", 0.0) or 0.0)
                    sun_el = float(data.get("sun_elevation", 0.0) or 0.0)
                    peer_d = float(data.get("peer_dist", 99.0) or 99.0)
                    peer_b = float(data.get("peer_bearing", 0.0) or 0.0)

                    # Biyolojik Optik Akış (Optic Flow) ile Yer Sürati Regülasyonu (David 1982, Fry 2009)
                    ground_speed_mod = 1.0
                    if hd is not None and len(hd) >= cols * 2:
                        try:
                            cur_floor = np.array(hd[-cols * 2:], dtype=np.float32)
                            if prev_retina_floor is not None and prev_retina_floor.shape == cur_floor.shape:
                                flow = float(np.mean(np.abs(cur_floor - prev_retina_floor))) / 255.0
                                if flow > 0.35:
                                    ground_speed_mod = 0.85
                                elif flow < 0.06:
                                    ground_speed_mod = 1.15
                            prev_retina_floor = cur_floor
                        except Exception:
                            pass

                    cast_ms_v = data.get("cast_ms")
                    t0 = time.perf_counter()
                    motor = brain.sense(hd, cols, rows, drive=1.15,
                                        mechano=mech, pain=pain,
                                        reward=reward, punish=punish,
                                        odor_l=odor_l, odor_r=odor_r,
                                        sound=sound, sound_bearing=sound_bearing,
                                        wind=wind, hazard_bearing=hazard_bearing,
                                        load=load, taste=taste,
                                        loom=loom, loom_bearing=loom_bearing,
                                        obstacle=obst, locomotor=0.60,
                                        heat=heat, ocellus_l=ocellus_l, ocellus_r=ocellus_r,
                                        cold=cold, is_raining=is_raining)
                    brain_ms = (time.perf_counter() - t0) * 1000.0

                    # Periyodik Mantar Cisimciği Bellek Kaydı (her 25 saniyede bir)
                    if tnow - last_mem_save > 25.0:
                        last_mem_save = tnow
                        brain.save_memory(mem_file)

                    render(brain, motor, hd, cols, rows, distances, health, food,
                           heading, data.get("cast_ms"),
                           {"brain_ms": brain_ms,
                            "show_overlay": show_neural_overlay,
                            "ses": (True if (wing.enabled and wing.ok)
                                    else (None if wing.enabled else False))},
                           {"odor_l": odor_l, "odor_r": odor_r, "sound": sound,
                            "sound_name": str(data.get("sound_name") or ""),
                            "wind": wind, "mech": mech, "obst": obst,
                            "hazard_bearing": hazard_bearing,
                            "inv_empty": int(data.get("inv_empty", -1)),
                            "food_dist": dropped,
                            "odor_path": float(data.get("odor_path", -1.0)),
                            "sky": float(data.get("sky_factor", 1.0)),
                            "gun_saati": int(data.get("time_of_day", 0)),
                            "chat_reward": _cr, "chat_punish": _cp,
                            "heat": heat,
                            "cold": cold,
                            "is_raining": is_raining,
                            "ocellus_l": ocellus_l,
                            "ocellus_r": ocellus_r,
                            "water_ahead": water_ahead, "water_below": water_below,
                            "water_dist": water_dist, "humidity": humidity},
                           lang=current_lang)

                    # Kanat vuruşu sesi
                    wing.update(motor["rates"], jump=motor["jump"],
                                escaping=motor["escape"])
                    wing.hear(brain.rate(brain.jo_sound_L),
                              brain.rate(brain.jo_sound_R))

                    # İleri itişe yer hızı modülasyonu ve akran sosyal mesafesi
                    thrust_val = motor["forward_thrust"] * ground_speed_mod
                    if peer_d < 2.5:
                        thrust_val *= 0.65  # Akran sineğe çok yaklaşınca yavaşla / sosyal mesafe
                    if dropped < 5.0:
                        thrust_val *= 0.55  # Besine yaklaşırken iniş yavaşlaması (landing deceleration)
                    if dropped < 2.2:
                        thrust_val *= 0.35  # Besine temas mesafesinde konma ve yeme
                    cmd_forward = bool(thrust_val > 0.25 and not motor["back"])
                    # YEME: BEDEN REFLEKSİ (beyinden okunamıyor — ölçüldü).
                    cmd_eat = bool(_hunger > 0.40 and food_items > 0
                                   and not data.get("is_eating"))

                    # DİNAMİK 3D PITCH (Böcek Dikey Bakış ve İrtifa Eğimi)
                    tnow = pygame.time.get_ticks() / 1000.0
                    cmd_pitch = 0.0
                    if water_below or water_ahead or data.get("in_water"):
                        # Sudan kaçış: yukarı tırmanış
                        cmd_pitch = -0.42
                    elif motor["escape"] or td < 8.0:
                        # Gerçek canavardan kaçış: yukarı tırmanış
                        cmd_pitch = -0.38
                    elif dropped < 8.0 and dropped > 0.3:
                        # Yiyecek / yaprak / çiçek kaynağına odaklanma
                        food_dy = float(data.get("food_delta_y", -1.0))
                        if food_dy > 0.4:
                            # Ağaç yaprağı / yüksekteki besin: yukarı tırmanış
                            cmd_pitch = -0.32
                        else:
                            # Yerdeki yiyeceğe/çiçeğe odaklanma: aşağı süzülüş
                            cmd_pitch = 0.34
                    elif obst > 0.6:
                        # Önünde yüksek duvar var: hafif yukarı
                        cmd_pitch = -0.20
                    else:
                        # Doğal süzülme salınımı
                        cmd_pitch = 0.06 * math.sin(tnow * 1.6)

                    # Canavardan korkma / kaçma refleksi:
                    is_mob_threat = bool(td < 8.0 or motor["escape"])
                    is_jump_needed = bool(motor["jump"] or water_below or td < 5.0 or data.get("in_water"))
                    is_sprint_needed = bool(motor["sprint"] or td < 8.0 or water_ahead)

                    # Ruh hali / duygu belirleme (Minecraft partikül efektleri için)
                    pam_dev = motor.get("pam_dev_s", 0.0)
                    ppl_dev = motor.get("ppl_dev_s", 0.0)
                    if cmd_eat or (data.get("food_count", 0) > 0 and dropped < 1.8):
                        mood_str = "eating"
                    elif is_mob_threat or motor["escape"] or pain > 0:
                        mood_str = "scared"
                    elif ppl_dev > 0.7 or punish > 0.35:
                        mood_str = "sad"
                    elif pam_dev > 0.6 or reward > 0.20:
                        mood_str = "happy"
                    else:
                        mood_str = "neutral"

                    await ws.send(json.dumps({
                        "forward": cmd_forward,
                        "back": bool(motor["back"]),
                        "steering_torque": float(motor["steering_torque"]),
                        "forward_thrust": float(thrust_val),
                        "pitch": float(cmd_pitch),
                        "is_escaping": is_mob_threat,
                        "jump": is_jump_needed,
                        "sprint": is_sprint_needed,
                        "eat": cmd_eat,
                        "mood": mood_str,
                        "shore_turn": 0.0,
                    }))

                    # ---------------- AYRINTILI KAYIT ----------------
                    tnow = pygame.time.get_ticks() / 1000.0
                    if log.enabled:
                        if td < 12.0:
                            log.event("MOB", "%s %.1f m, yön %+.2f -> looming %.2f, "
                                      "DNp04 %.1f Hz, kaçış %s"
                                      % (str(data.get("threat_name") or "?")[:14], td,
                                         loom_bearing, loom,
                                         motor["rates"].get("loom", 0.0),
                                         "EVET" if motor["escape"] else "hayır"))
                        else:
                            log.event_clear("MOB")
                        if pain > 0:
                            log.event("ACI", "can %.0f/20 (hasar %.1f)" % (health, dmg))
                        else:
                            log.event_clear("ACI")
                        if data.get("hazard_ahead"):
                            log.event("TEHLİKE", "önde zararlı blok, yön %s"
                                      % ("%.2f" % hazard_bearing
                                         if hazard_bearing is not None else "?"))
                        else:
                            log.event_clear("TEHLİKE")
                        if motor["back"]:
                            log.event("GERİ", "MDN %.1f Hz (mekano %.2f engel %.2f)"
                                      % (motor["rates"]["backward"], mech, obst))
                        else:
                            log.event_clear("GERİ")
                        if got:
                            log.event("YEMEK", "envantere besin geldi (%d)" % food_items,
                                      dedupe=False)
                        if stuck > 8:
                            log.event("TAKILDI", "stuck=%d engel %.2f mekano %.2f"
                                      % (stuck, obst, mech))
                        else:
                            log.event_clear("TAKILDI")
                        r_ = motor["rates"]
                        kcv = brain.spike_count[brain.kc_idx]
                        gl_, gr_ = getattr(brain, "ocelli_lr", (0.0, 0.0))
                        row = {
                            "t": "%.2f" % tnow, "fps": "%.1f" % fps_now(),
                            "atlanan": stale_now,
                            "beyin_ms": "%.1f" % brain_ms,
                            "isin_ms": data.get("cast_ms"),
                            "can": health, "aclik": food,
                            "yon_derece": "%.1f" % (math.degrees(heading) % 360),
                            "x": "%.1f" % float(data.get("pos_x", 0.0)),
                            "y": "%.1f" % float(data.get("pos_y", 0.0)),
                            "z": "%.1f" % float(data.get("pos_z", 0.0)),
                            "aci": pain, "mekano": mech, "engel": obst, "yuk": load,
                            "tehlike_yon": ("%.2f" % hazard_bearing)
                                           if hazard_bearing is not None else "",
                            "tehlike_skor": data.get("hazard_score", 0.0),
                            "tehlikeli_blok": bool(data.get("hazard_ahead")),
                            "su_onde": bool(data.get("water_ahead")),
                            "suda": bool(data.get("in_water")),
                            "duvar": bool(data.get("wall_ahead")),
                            "basamak": bool(data.get("step_up_ahead")),
                            "takilma": stuck,
                            "koku_sol": odor_l, "koku_sag": odor_r,
                            "koku_fazik": "%.3f" % sum(
                                getattr(brain, "odor_phasic", (0.0, 0.0))),
                            "DN_koku": "%.2f" % motor.get("dn_odor_rate", 0.0),
                            "uyarilma": "%.3f" % motor.get("arousal", 0.0),
                            "KC_koku": "%.3f" % motor.get("odor_now", 0.0),
                            "koku_degisim": "%.4f" % motor.get("odor_d", 0.0),
                            "arama": "%.3f" % motor.get("odor_lost", 0.0),
                            "sicak": "%.2f" % heat,
                            "termo": "%.2f" % motor.get("thermo_rate", 0.0),
                            "temizlenme": "%.2f" % motor.get("groom", 0.0),
                            "gok": "%.2f" % float(data.get("sky_factor", 1.0)),
                            "koku_mesafe": "%.1f" % dropped,
                            "koku_yol": "%.1f" % float(data.get("odor_path", -1.0)),
                            "koku_ad": data.get("dropped_food_name") or "",
                            "ses": sound, "ses_yon": sound_bearing,
                            "ses_ad": str(data.get("sound_name") or "")[:24],
                            "ruzgar": wind,
                            "ocellus_sol": float(gl_), "ocellus_sag": float(gr_),
                            "odul": reward, "ceza": punish, "besin_sayisi": food_items,
                            "LoVP": brain.rate(getattr(brain, "lovp_idx", [])),
                            "KCg-d": brain.rate(getattr(brain, "kcd_idx", [])),
                            "KC_Hz": brain.rate(brain.kc_idx),
                            "KC_sessiz_yuzde": 100.0 * float((kcv == 0).mean()),
                            "MBON": brain.rate(brain.mbon_idx),
                            "PAM": brain.rate(brain.pam_idx),
                            "PAM_sapma": motor.get("pam_dev", 0.0),
                            "PPL1_sapma": motor.get("ppl_dev", 0.0),
                            "PPL1": brain.rate(brain.ppl1_idx),
                            "RPE": motor.get("rpe", 0.0),
                            "ORN": brain.rate(np.concatenate([brain.orn_L, brain.orn_R]))
                                   if len(brain.orn_L) + len(brain.orn_R) else 0.0,
                            "PN": brain.rate(brain.pn_idx),
                            "LH": brain.rate(brain.lh_idx),
                            "JO": brain.rate(brain.jo_idx),
                            "OCG01": brain.rate(brain.ocg_idx),
                            "DNp20_sol": motor["DNp20_L"], "DNp20_sag": motor["DNp20_R"],
                            "DNpe017": r_["forward"], "MDN": r_["backward"],
                            "DNp09": r_["fast"], "DNp01": r_["escape"],
                            "DNp04": r_.get("loom", 0.0),
                            "DNp11": r_.get("loom2", 0.0),
                            "MN9": r_.get("feed", 0.0),
                            "looming": loom, "tehdit_m": td, "tat": taste,
                            "tehdit_buyume": "%.2f" % float(data.get("threat_growth", 0.0) or 0.0),
                            "durum": brain.state_label(motor, _hunger)[0],
                            "tork": motor["steering_torque"],
                            "itis": motor["forward_thrust"],
                            "ileri": bool(cmd_forward), "geri": bool(motor["back"]),
                            "zipla": bool(motor["jump"]), "kosu": bool(motor["sprint"]),
                            "ye": bool(cmd_eat), "ag_hz": brain.mean_rate,
                        }
                        for tname in ("R1-R6", "L1", "L2", "Mi1", "Mi9", "Tm3",
                                      "Tm9", "T4a", "T5a", "LC4", "LPLC2", "APL"):
                            row[tname] = brain.rate_of_type(tname)
                        log.frame(row)
                        log.summary(tnow, row)

                    now = tnow
                    if (now - last_log > 2.5):
                        last_log = now
                        r = motor["rates"]
                        kcq = brain.spike_count[brain.kc_idx]
                        pam = brain.rate(brain.pam_idx)
                        ppl = brain.rate(brain.ppl1_idx)
                        mbo = brain.rate(brain.mbon_idx)
                        gl2, gr2 = getattr(brain, "ocelli_lr", (0.0, 0.0))
                        is_tr = (current_lang == "tr")
                        yn = (lambda x: "EVET" if x else "hayır") if is_tr else (lambda x: "YES" if x else "no")
                        if is_tr:
                            cmd = ("GERİ" if motor["back"] else
                                   ("İLERİ" if cmd_forward else "DUR"))
                            if motor["jump"]:
                                cmd += "+ZIPLA"
                            if motor["sprint"]:
                                cmd += " +KOŞU"
                        else:
                            cmd = ("BACK" if motor["back"] else
                                   ("FWD" if cmd_forward else "STOP"))
                            if motor["jump"]:
                                cmd += "+JUMP"
                            if motor["sprint"]:
                                cmd += " +SPRINT"

                        print("\n" + "─" * 78)
                        if is_tr:
                            print("🪰 %-16s t=%6.1fs  %4.1f FPS  beyin %2.0f ms  ışın %s"
                                  % (label, now, fps_now(), brain_ms,
                                     ("%.0f ms" % cast_ms_v) if cast_ms_v else "-"))
                            print("GÖRME   R1-R6 %5.1f  L1 %5.1f  L2 %5.1f  Mi1 %5.1f  "
                                  "Mi9 %5.1f  Tm3 %5.1f  Tm9 %5.1f"
                                  % (brain.rate_of_type("R1-R6"), brain.rate_of_type("L1"),
                                     brain.rate_of_type("L2"), brain.rate_of_type("Mi1"),
                                     brain.rate_of_type("Mi9"), brain.rate_of_type("Tm3"),
                                     brain.rate_of_type("Tm9")))
                            print("        T4a %5.1f  T5a %5.1f  LC4 %5.1f  LPLC2 %5.1f  "
                                  "APL %5.1f     (Hz)"
                                  % (brain.rate_of_type("T4a"), brain.rate_of_type("T5a"),
                                     brain.rate_of_type("LC4"), brain.rate_of_type("LPLC2"),
                                     brain.rate_of_type("APL")))
                            print("OCELLI  ışık sol %.2f sağ %.2f   OCG01 sol %5.1f sağ %5.1f Hz"
                                  % (gl2, gr2, brain.rate(brain.ocg_L), brain.rate(brain.ocg_R)))
                            _ph = getattr(brain, "odor_phasic", (0.0, 0.0))
                            _phs = sum(_ph)
                            print("KOKU    anten sol %.2f sağ %.2f  (%s %.1f m)   "
                                  "ORN %4.1f  PN %4.1f  LH %4.1f Hz"
                                  % (odor_l, odor_r,
                                     data.get("dropped_food_name") or "yok", dropped,
                                     brain.rate(np.concatenate([brain.orn_L, brain.orn_R]))
                                     if len(brain.orn_L) + len(brain.orn_R) else 0.0,
                                     brain.rate(brain.pn_idx), brain.rate(brain.lh_idx)))
                            print("        fazik sol %+.2f sağ %+.2f  ->  %s"
                                  % (_ph[0], _ph[1],
                                     "YAKLAŞIYOR" if _phs > 0.08 else
                                     "UZAKLAŞIYOR" if _phs < -0.08 else "sabit/koku yok"))
                            _aro = motor.get("arousal", 0.0)
                            print("        Kenyon %5.2f Hz -> koku %.2f | değişim "
                                  "%+.3f | arama %.2f  ->  uyarılmışlık %+.2f  %s"
                                  % (motor.get("kc_rate", 0.0),
                                     motor.get("odor_now", 0.0),
                                     motor.get("odor_d", 0.0),
                                     motor.get("odor_lost", 0.0), _aro,
                                     "HIZLAN+DÜZLEŞ" if _aro > 0.12 else
                                     "YAVAŞLA+TARA" if _aro < -0.12 else "normal"))
                        else:
                            print("🪰 %-16s t=%6.1fs  %4.1f FPS  brain %2.0f ms  ray %s"
                                  % (label, now, fps_now(), brain_ms,
                                     ("%.0f ms" % cast_ms_v) if cast_ms_v else "-"))
                            print("VISION  R1-R6 %5.1f  L1 %5.1f  L2 %5.1f  Mi1 %5.1f  "
                                  "Mi9 %5.1f  Tm3 %5.1f  Tm9 %5.1f"
                                  % (brain.rate_of_type("R1-R6"), brain.rate_of_type("L1"),
                                     brain.rate_of_type("L2"), brain.rate_of_type("Mi1"),
                                     brain.rate_of_type("Mi9"), brain.rate_of_type("Tm3"),
                                     brain.rate_of_type("Tm9")))
                            print("        T4a %5.1f  T5a %5.1f  LC4 %5.1f  LPLC2 %5.1f  "
                                  "APL %5.1f     (Hz)"
                                  % (brain.rate_of_type("T4a"), brain.rate_of_type("T5a"),
                                     brain.rate_of_type("LC4"), brain.rate_of_type("LPLC2"),
                                     brain.rate_of_type("APL")))
                            print("OCELLI  light L %.2f R %.2f   OCG01 L %5.1f R %5.1f Hz"
                                  % (gl2, gr2, brain.rate(brain.ocg_L), brain.rate(brain.ocg_R)))
                            _ph = getattr(brain, "odor_phasic", (0.0, 0.0))
                            _phs = sum(_ph)
                            print("ODOR    antenna L %.2f R %.2f  (%s %.1f m)   "
                                  "ORN %4.1f  PN %4.1f  LH %4.1f Hz"
                                  % (odor_l, odor_r,
                                     data.get("dropped_food_name") or "none", dropped,
                                     brain.rate(np.concatenate([brain.orn_L, brain.orn_R]))
                                     if len(brain.orn_L) + len(brain.orn_R) else 0.0,
                                     brain.rate(brain.pn_idx), brain.rate(brain.lh_idx)))
                            print("        phasic L %+.2f R %+.2f  ->  %s"
                                  % (_ph[0], _ph[1],
                                     "APPROACHING" if _phs > 0.08 else
                                     "LEAVING" if _phs < -0.08 else "steady/no odor"))
                            _aro = motor.get("arousal", 0.0)
                            print("        Kenyon %5.2f Hz -> odor %.2f | change "
                                  "%+.3f | search %.2f  ->  arousal %+.2f  %s"
                                  % (motor.get("kc_rate", 0.0),
                                     motor.get("odor_now", 0.0),
                                     motor.get("odor_d", 0.0),
                                     motor.get("odor_lost", 0.0), _aro,
                                     "SPEEDUP+SURGE" if _aro > 0.12 else
                                     "SLOWDOWN+CAST" if _aro < -0.12 else "normal"))
                        # ENVANTER DOLUYSA yerdeki yemek ALINAMAZ. Sinek
                        # elmanın tam üstünden geçse bile hiçbir şey olmaz;
                        # bu beynin değil, oyunun kuralı.
                        # SOHBET PEKİŞTİRECİ: ödül tek başına bir şey
                        # öğretmez. Sinekte öğrenme, o anda ateşleyen Kenyon
                        # hücrelerinin izine (eligibility trace) yazılır —
                        # KC sessizse yazılacak bir ipucu yoktur. Bunu
                        # yazdırıyoruz ki kullanıcı ne zaman ödül vereceğini
                        # bilsin: koku/sahne varken ver.
                        if is_tr:
                            if _cr > 0.02 or _cp > 0.02:
                                _kcv = brain.rate(brain.kc_idx)
                                print("SOHBET  %s (%.2f)  KC %.2f Hz -> %s   RPE %+.3f"
                                      % ("ÖDÜL/PAM" if _cr > _cp else "CEZA/PPL1",
                                         max(_cr, _cp), _kcv,
                                         "ipucu var, ÖĞRENİYOR" if _kcv > 1.2
                                         else "KC sessiz — yazacak ipucu yok",
                                         motor.get("rpe", 0.0)))
                            _inv = int(data.get("inv_empty", -1))
                            if _inv == 0:
                                print("        >> ENVANTER DOLU (boş slot 0) — sinek "
                                      "yemeği ALAMAZ, üstünden geçse bile. "
                                      "Envanteri boşalt!")
                            elif _inv > 0 and dropped < 3.0:
                                print("        yerdeki yemek %.1f m — alması için "
                                      "~1 m'ye girmeli (boş slot %d)" % (dropped, _inv))
                            if heat > 0.02:
                                print("SICAKLIK %.2f -> termo PN %.1f Hz"
                                      % (heat, motor.get("thermo_rate", 0.0)))
                            print("MOB     tehdit %s  looming %.2f  ->  DNp04 %5.1f  "
                                  "DNp11 %4.1f  DNp01 %4.1f Hz"
                                  % (("%.1f m" % td) if td < 90 else "yok", loom,
                                     motor["rates"].get("loom", 0.0),
                                     motor["rates"].get("loom2", 0.0),
                                     motor["rates"].get("escape", 0.0)))
                            print("İŞİTME  \"%s\"  şiddet %.2f  yön %+.2f  ->  Johnston "
                                  "organı %4.1f Hz  (rüzgâr %.2f)"
                                  % (str(data.get("sound_name") or "sessiz")[:28],
                                     sound, sound_bearing,
                                     brain.rate(brain.jo_idx), wind))
                            print("BAĞLAM  görsel yol: LoVP %4.1f Hz -> KCg-d %4.1f Hz "
                                  "(yer hafızası buradan geçer)"
                                  % (brain.rate(getattr(brain, "lovp_idx", [])),
                                     brain.rate(getattr(brain, "kcd_idx", []))))
                            print("ÖĞRENME KC %4.1f Hz sessiz %%%2.0f | MBON %4.1f | "
                                  "PAM %4.1f | PPL1 %4.1f | hata sinyali %+.3f"
                                  % (brain.rate(brain.kc_idx),
                                     100 * float((kcq == 0).mean()), mbo, pam, ppl,
                                     motor.get("rpe", 0.0)))
                            _lbl, _sev = brain.state_label(motor, _hunger, lang="tr")
                            _bars = brain.state_bars(motor, _hunger, lang="tr")
                            print("► DURUM  %s   [şiddet %%%.0f]" % (_lbl, 100 * _sev))
                            print("         " + "  ".join(
                                "%s %s %%%.0f" % (k, "█" * int(v * 8) + "·" * (8 - int(v * 8)),
                                                  100 * v) for k, v in _bars.items()))
                            print("        iştah %+.2f  kaçınma %+.2f  kaçış %.2f  |  "
                                  "can %.0f/20  açlık %.0f/20  besin %d"
                                  % (motor.get("pam_dev_s", 0.0), motor.get("ppl_dev_s", 0.0),
                                     min(1.0, r["escape"] / 20.0),
                                     health, food, food_items))
                            print("MOTOR   DNp20 sol %5.1f sağ %5.1f | DNpe017 %5.1f | "
                                  "MDN %5.1f | DNp09 %5.1f | DNp01 %5.1f"
                                  % (motor["DNp20_L"], motor["DNp20_R"], r["forward"],
                                     r["backward"], r["fast"], r["escape"]))
                            print("        tork %+.3f  itiş %+.2f   ->  %s" % (
                                  motor["steering_torque"], motor["forward_thrust"], cmd))
                            print("ÇEVRE   duvar:%s tehlike:%s su:%s suda:%s "
                                  "basamak:%s takılma:%d"
                                  % (yn(data.get("wall_ahead")),
                                     yn(data.get("hazard_ahead")), yn(data.get("water_ahead")),
                                     yn(data.get("in_water")), yn(data.get("step_up_ahead")),
                                     stuck))
                            print("        mekano %.2f (ham %.2f) engel %.2f (ham %.2f) "
                                  "yük %.2f  acı %.0f"
                                  % (mech, mech_raw, obst, obst_raw, load, pain))
                            print("        kaçış yönü %s  (kilit %s)"
                                  % (("%+.2f" % hazard_bearing)
                                     if hazard_bearing is not None else "yok",
                                     {0: "serbest", 1: "SOL", -1: "SAĞ"}[esc_dir]))
                            print("        konum %.0f/%.0f/%.0f  yön %.0f°  ağ %.2f Hz  "
                                  "| atlanan eski kare: %d (bu karede %d)"
                                  % (float(data.get("pos_x", 0)), float(data.get("pos_y", 0)),
                                     float(data.get("pos_z", 0)),
                                     math.degrees(heading) % 360, brain.mean_rate,
                                     stale_total, stale_now))
                        else:
                            if _cr > 0.02 or _cp > 0.02:
                                _kcv = brain.rate(brain.kc_idx)
                                print("CHAT    %s (%.2f)  KC %.2f Hz -> %s   RPE %+.3f"
                                      % ("REWARD/PAM" if _cr > _cp else "PUNISH/PPL1",
                                         max(_cr, _cp), _kcv,
                                         "cue present, LEARNING" if _kcv > 1.2
                                         else "KC silent — no cue to write",
                                         motor.get("rpe", 0.0)))
                            _inv = int(data.get("inv_empty", -1))
                            if _inv == 0:
                                print("        >> INVENTORY FULL (0 empty slots) — fly "
                                      "CANNOT pick up food even when walking over it. "
                                      "Empty inventory!")
                            elif _inv > 0 and dropped < 3.0:
                                print("        dropped food %.1f m — needs to be "
                                      "<1 m to pick up (empty slots %d)" % (dropped, _inv))
                            if heat > 0.02:
                                print("THERMO   %.2f -> thermo PN %.1f Hz"
                                      % (heat, motor.get("thermo_rate", 0.0)))
                            print("MOB     threat %s  looming %.2f  ->  DNp04 %5.1f  "
                                  "DNp11 %4.1f  DNp01 %4.1f Hz"
                                  % (("%.1f m" % td) if td < 90 else "none", loom,
                                     motor["rates"].get("loom", 0.0),
                                     motor["rates"].get("loom2", 0.0),
                                     motor["rates"].get("escape", 0.0)))
                            print("HEARING \"%s\"  volume %.2f  bearing %+.2f  ->  Johnston's "
                                  "organ %4.1f Hz  (wind %.2f)"
                                  % (str(data.get("sound_name") or "silent")[:28],
                                     sound, sound_bearing,
                                     brain.rate(brain.jo_idx), wind))
                            print("CONTEXT visual path: LoVP %4.1f Hz -> KCg-d %4.1f Hz "
                                  "(place memory passes here)"
                                  % (brain.rate(getattr(brain, "lovp_idx", [])),
                                     brain.rate(getattr(brain, "kcd_idx", []))))
                            print("LEARN   KC %4.1f Hz silent %2.0f%% | MBON %4.1f | "
                                  "PAM %4.1f | PPL1 %4.1f | error signal %+.3f"
                                  % (brain.rate(brain.kc_idx),
                                     100 * float((kcq == 0).mean()), mbo, pam, ppl,
                                     motor.get("rpe", 0.0)))
                            _lbl, _sev = brain.state_label(motor, _hunger, lang="en")
                            _bars = brain.state_bars(motor, _hunger, lang="en")
                            print("► STATE  %s   [intensity %%%.0f]" % (_lbl, 100 * _sev))
                            print("         " + "  ".join(
                                "%s %s %%%.0f" % (k, "█" * int(v * 8) + "·" * (8 - int(v * 8)),
                                                  100 * v) for k, v in _bars.items()))
                            print("        appetite %+.2f  aversion %+.2f  escape %.2f  |  "
                                  "health %.0f/20  hunger %.0f/20  food %d"
                                  % (motor.get("pam_dev_s", 0.0), motor.get("ppl_dev_s", 0.0),
                                     min(1.0, r["escape"] / 20.0),
                                     health, food, food_items))
                            print("MOTOR   DNp20 L %5.1f R %5.1f | DNpe017 %5.1f | "
                                  "MDN %5.1f | DNp09 %5.1f | DNp01 %5.1f"
                                  % (motor["DNp20_L"], motor["DNp20_R"], r["forward"],
                                     r["backward"], r["fast"], r["escape"]))
                            print("        torque %+.3f  thrust %+.2f   ->  %s" % (
                                  motor["steering_torque"], motor["forward_thrust"], cmd))
                            print("ENV     wall:%s hazard:%s water:%s in_water:%s "
                                  "step:%s stuck:%d"
                                  % (yn(data.get("wall_ahead")),
                                     yn(data.get("hazard_ahead")), yn(data.get("water_ahead")),
                                     yn(data.get("in_water")), yn(data.get("step_up_ahead")),
                                     stuck))
                            print("        mechano %.2f (raw %.2f) obst %.2f (raw %.2f) "
                                  "load %.2f  pain %.0f"
                                  % (mech, mech_raw, obst, obst_raw, load, pain))
                            print("        escape dir %s  (lock %s)"
                                  % (("%+.2f" % hazard_bearing)
                                     if hazard_bearing is not None else "none",
                                     {0: "free", 1: "LEFT", -1: "RIGHT"}[esc_dir]))
                            print("        pos %.0f/%.0f/%.0f  heading %.0f°  net %.2f Hz  "
                                  "| dropped stale frames: %d (this frame %d)"
                                  % (float(data.get("pos_x", 0)), float(data.get("pos_y", 0)),
                                     float(data.get("pos_z", 0)),
                                     math.degrees(heading) % 360, brain.mean_rate,
                                     stale_total, stale_now))
                        print("─" * 78)

        except Exception as _e:
            waiting_logged = False
            try:
                reader.cancel()
            except (NameError, RuntimeError):
                pass
            if not as_server and isinstance(_e, (ConnectionRefusedError, OSError, websockets.exceptions.WebSocketException)):
                pass
            else:
                if debug:
                    import traceback
                    traceback.print_exc()

            log.event("KOPTU", "bağlantı kesildi: %s" % type(_e).__name__)
            if not IS_HEADLESS:
                screen.fill(BG)
                msg = f"Minecraft sunucusu bekleniyor ({ws_host}:{ws_port})..." if not as_server else f"FruitFly eklentisi bekleniyor (0.0.0.0:{ws_port})..."
                t = F_LBL.render(msg, True, ALERT)
                screen.blit(t, (screen.get_width() // 2 - t.get_width() // 2, screen.get_height() // 2))
                pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(bridge_loop())
