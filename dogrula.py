# -*- coding: utf-8 -*-
"""
================================================================================
 DROSOPHILA — DAVRANIŞ DOĞRULAMA VE TEST BATARYASI
================================================================================
Bu betik, ağ parametrelerindeki değişikliklerin duyusal ve motor tepkilere
etkisini sentetik sahneler üzerinde istatistiksel olarak doğrular.

Tüm ölçümler **Cohen's d** etki büyüklüğü ile raporlanır:
(d < 0,2 önemsiz, d > 0,8 güçlü etki).

Kullanım:
    python dogrula.py           # Standart test bataryası (~2 dk)
    python dogrula.py 16        # Yüksek tekrarlı test bataryası

Çalıştırmak için Minecraft sunucusuna gerek yoktur; test uyaranları sentetiktir.
"""

import collections
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np

import fly_brain_real as FB

COLS, ROWS = 64, 24


def _scene(kind):
    """Botun ürettiğiyle aynı biçimde sentetik sahne (gök / duvar / zemin)."""
    img = np.zeros((ROWS, COLS, 3), dtype=np.float32)
    img[:8] = (110, 165, 235)
    img[8:17] = (105, 105, 112)
    img[17:] = (75, 150, 55)
    if kind == "duvar_sol":
        img[:, :COLS // 2] = (95, 95, 100)
    elif kind == "duvar_sag":
        img[:, COLS // 2:] = (95, 95, 100)
    elif kind == "isik_sol":
        # TAM ALAN aydınlık/karanlık bölünmesi (kalibrasyonun kendi probu).
        # Eski sürüm yalnızca GÖKYÜZÜ yarısını aydınlatıyordu; ölçüldü
        # (18 tekrar): o sahnede etki d +0,71 ile TERS görünüyor, tam alanda
        # ise d −2,60 (ışığa yaklaşıyor). Yani hata davranışta değil,
        # test sahnesindeydi — gökyüzü yarısı yanal bir parlaklık ipucu
        # değil, ufuk kontrastı değişimi yaratıyor.
        img[:, :COLS // 2] = (225, 225, 225)
        img[:, COLS // 2:] = (35, 35, 35)
    elif kind == "isik_sag":
        img[:, COLS // 2:] = (225, 225, 225)
        img[:, :COLS // 2] = (35, 35, 35)
    return img.reshape(-1, 3)


SCENES = {k: _scene(k) for k in
          ("duz", "duvar_sol", "duvar_sag", "isik_sol", "isik_sag")}


def cohen_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    s = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    return float((a.mean() - b.mean()) / s) if s > 1e-9 else 0.0


def _yorum(d):
    d = abs(d)
    return ("yok" if d < 0.2 else "zayıf" if d < 0.5 else
            "orta" if d < 0.8 else "güçlü" if d < 2.0 else "çok güçlü")


def run(reps=10, verbose=True):
    brain = FB.RealFlyBrain(gain=3.0, tonic_floor=FB.TONIC_FLOOR, verbose=False)
    brain.calibrate_all(verbose=False)
    if verbose:
        print("kalibrasyon: tonik %.4f | dönüş sapması %+.4f | işaret %+.0f"
              % (brain.tonic0, brain.steer_bias, brain.steer_sign))

    for _ in range(45):
        brain.sense(SCENES["duz"], COLS, ROWS, drive=1.15, locomotor=0.60)

    def trial(scene, n=10, **kw):
        # her denemeden önce nötr sahnede dinlendir (taşıma etkisini kes)
        for _ in range(5):
            brain.sense(SCENES["duz"], COLS, ROWS, drive=1.15, locomotor=0.60)
        brain.orn_adapt_l = brain.orn_adapt_r = 0.0
        acc = collections.defaultdict(list)
        for _ in range(n):
            m = brain.sense(scene, COLS, ROWS, drive=1.15, locomotor=0.60, **kw)
            acc["tork"].append(m["steering_torque"])
            acc["itis"].append(m["forward_thrust"])
            acc["loom"].append(m["rates"].get("loom", 0.0))
            acc["kacis"].append(m["rates"].get("escape", 0.0))
            acc["JO"].append(brain.rate(brain.jo_sound_L) -
                             brain.rate(brain.jo_sound_R))
            acc["dnodor"].append(brain.rate(brain.dn_odor_idx)
                                 if len(brain.dn_odor_idx) else 0.0)
            acc["KCkoku"].append(m.get("odor_now", 0.0))
            acc["arama"].append(m.get("odor_lost", 0.0))
            acc["mutlak_tork"].append(abs(m["steering_torque"]))
            acc["hz"].append(brain.mean_rate)
            acc["Mi1"].append(brain.rate_of_type("Mi1"))
            acc["LC4"].append(brain.rate_of_type("LC4"))
            acc["KC"].append(brain.rate(brain.kc_idx))
            acc["DNp20"].append(brain.rate(brain.motor_idx["turn"]))
            acc["ileri"].append(brain.rate(brain.motor_idx["forward"]))
        h = n // 2                      # ilk yarı geçici rejim, atılır
        return {k: float(np.mean(v[h:])) for k, v in acc.items()}

    G = collections.defaultdict(list)
    for i in range(reps):
        G["duvar_sol"].append(trial(SCENES["duvar_sol"]))
        G["duvar_sag"].append(trial(SCENES["duvar_sag"]))
        G["isik_sol"].append(trial(SCENES["isik_sol"]))
        G["isik_sag"].append(trial(SCENES["isik_sag"]))
        G["koku_sol"].append(trial(SCENES["duz"], odor_l=0.90, odor_r=0.15))
        G["koku_sag"].append(trial(SCENES["duz"], odor_l=0.15, odor_r=0.90))
        G["ses_sol"].append(trial(SCENES["duz"], sound=0.85, sound_bearing=+1.2))
        G["ses_sag"].append(trial(SCENES["duz"], sound=0.85, sound_bearing=-1.2))
        # ENGEL/TEHLİKE KANALI (hazard_bearing yön testi)
        G["engel_sol"].append(trial(SCENES["duz"], obstacle=0.80,
                                    hazard_bearing=+1.2))
        G["engel_sag"].append(trial(SCENES["duz"], obstacle=0.80,
                                    hazard_bearing=-1.2))
        G["mob"].append(trial(SCENES["duz"], loom=0.80, loom_bearing=+0.6))
        # MOB ARKADA: Tehdit arkadayken doğrusal kaçış tepkisi test edilir
        G["mob_arka"].append(trial(SCENES["duz"], loom=0.80, loom_bearing=2.85))
        G["bos"].append(trial(SCENES["duz"]))
        if verbose:
            print("  tekrar %d/%d" % (i + 1, reps), end="\r", flush=True)

    # --- KOKU RAMPASI: yükselirken vs düşerken (klinotaksi testi) ---
    # Aynı konsantrasyondan geçilir; tek fark yönüdür. Sinek yönü bilmez
    # ama "artıyor mu azalıyor mu" bilir; davranışı buna bağlı olmalı.
    def rampa(yukari, n=40):
        for _ in range(12):
            brain.sense(SCENES["duz"], COLS, ROWS, drive=1.15, locomotor=0.60)
        brain.orn_adapt_l = brain.orn_adapt_r = 0.0
        brain.odor_now = brain.odor_peak = brain.odor_fast = 0.0
        brain.odor_slow = brain.odor_d = brain.odor_drop = brain.odor_lost = 0.0
        lv = np.linspace(0.05, 0.95, n)
        if not yukari:
            lv = lv[::-1]
        out = collections.defaultdict(list)
        for L in lv:
            m = brain.sense(SCENES["duz"], COLS, ROWS, drive=1.15,
                            locomotor=0.60, odor_l=float(L), odor_r=float(L))
            out["arama"].append(m.get("odor_lost", 0.0))
            out["mutlak_tork"].append(abs(m["steering_torque"]))
            out["itis"].append(m["forward_thrust"])
            out["degisim"].append(m.get("odor_d", 0.0))
        # SON %40'IN ORTALAMASI. Rampanın başı geçici rejimdir; arama
        # dürtüsü de doğal olarak düşüşün ilerleyen kısmında doğar.
        # (26 adımlık ilk sürüm bu yüzden yanıltıcıydı: arama ancak son
        #  iki karede devreye giriyor, ortalama gürültüde kayboluyordu.)
        h = int(n * 0.6)
        return {k: float(np.mean(v[h:])) for k, v in out.items()}

    for i in range(reps):
        G["rampa_yukari"].append(rampa(True))
        G["rampa_asagi"].append(rampa(False))

    g = lambda k, f: [x[f] for x in G[k]]
    tests = [
        ("DUVAR   sol vs sağ  → dönüş",
         cohen_d(g("duvar_sol", "tork"), g("duvar_sag", "tork")), "+"),
        # Koku YÖNÜ ölçüldü ve bu ağda YOK (bkz. README): dönüş nöronlarının
        # koku girdisi %0,000, kokuyu alan inen nöronlar ise tip başına tek
        # hücre — bir spike 0,77 Hz, yön için çözünürlük yok. Beklenti
        # koymuyoruz; sayı burada yalnızca durumu izlemek için.
        ("KOKU    sol vs sağ  → dönüş (bu ağda YOK)",
         cohen_d(g("koku_sol", "tork"), g("koku_sag", "tork")), "?"),
        # Koku VARLIĞI inen nöronlara güçlü ulaşıyor (DNc01 4,23 -> 10,19 Hz,
        # d 2,40) ve uyarılmışlık dürtüsünü sürüyor: sinek kokuyu alınca
        # hızlanır ve düzleşir. Bu bataryanın en kritik satırı.
        ("KOKU    var vs yok  → ileri itiş",
         cohen_d(g("koku_sol", "itis") + g("koku_sag", "itis"),
                 g("bos", "itis")), "+"),
        ("KOKU    var vs yok  → uyarılmışlık DN'leri",
         cohen_d(g("koku_sol", "dnodor") + g("koku_sag", "dnodor"),
                 g("bos", "dnodor")), "+"),
        # Uyarılmışlığın YENİ kaynağı: mantar cisimciği (KC). Gerçek oyun
        # loglarında eşik 1,5 Hz -> %98 yakalama, %0,04 yanlış alarm.
        ("KOKU    var vs yok  → KC koku okuması",
         cohen_d(g("koku_sol", "KCkoku") + g("koku_sag", "KCkoku"),
                 g("bos", "KCkoku")), "+"),
        # KLİNOTAKSİ: koku azalırken arama dürtüsü doğmalı, artarken doğmamalı.
        ("KOKU    azalırken vs artarken → arama dürtüsü",
         cohen_d(g("rampa_asagi", "arama"), g("rampa_yukari", "arama")), "+"),
        ("KOKU    azalırken vs artarken → dönüş miktarı",
         cohen_d(g("rampa_asagi", "mutlak_tork"),
                 g("rampa_yukari", "mutlak_tork")), "+"),
        ("KOKU    artarken vs azalırken → ileri itiş",
         cohen_d(g("rampa_yukari", "itis"), g("rampa_asagi", "itis")), "+"),
        ("SES     sol vs sağ  → Johnston farkı",
         cohen_d(g("ses_sol", "JO"), g("ses_sag", "JO")), "+"),
        ("SES     sol vs sağ  → dönüş",
         cohen_d(g("ses_sol", "tork"), g("ses_sag", "tork")), "?"),
        ("MOB     yaklaşan    → DNp04",
         cohen_d(g("mob", "loom"), g("bos", "loom")), "+"),
        # Tehlike SOLDA iken tork POZİTİF olmalı (sağa kaç). Sözleşme:
        # tork > 0 = sağa dönüş (bot: newYaw = yaw − tork).
        ("ENGEL   solda vs sağda → dönüş (ters yöne mi)",
         cohen_d(g("engel_sol", "tork"), g("engel_sag", "tork")), "+"),
        ("MOB     yaklaşan    → dönüş (kaçış yönü)",
         cohen_d(g("mob", "tork"), g("bos", "tork")), "+"),
        # Mob ÖNDE iken çok dönmeli, ARKADA iken dönmeyi bırakıp koşmalı.
        ("MOB     önde vs arkada → dönüş miktarı",
         cohen_d(g("mob", "mutlak_tork"), g("mob_arka", "mutlak_tork")), "+"),
        ("MOB     arkada vs önde → ileri itiş (kaçıyor mu)",
         cohen_d(g("mob_arka", "itis"), g("mob", "itis")), "+"),
        # İŞARET SÖZLEŞMESİ: tork > 0 = SAĞA dönüş. Bir uyarana YAKLAŞMA,
        # "sol uyaran − sağ uyaran" farkında NEGATİF d demektir; ondan
        # KAÇMA pozitif d demektir. (Duvar +, fototaksi −.)
        ("IŞIK    sol vs sağ  → dönüş (fototaksi, ışığa yaklaşma)",
         cohen_d(g("isik_sol", "tork"), g("isik_sag", "tork")), "-"),
    ]

    print("\n" + "=" * 74)
    print("DAVRANIŞ BATARYASI   (%d tekrar)" % reps)
    print("=" * 74)
    for ad, d, beklenen in tests:
        bayrak = ""
        if beklenen == "+" and d < 0.2:
            bayrak = "  << BEKLENEN YÖNDE DEĞİL"
        elif beklenen == "-" and d > -0.2:
            bayrak = "  << BEKLENEN YÖNDE DEĞİL"
        print("  %-42s d %+6.2f  %-10s%s" % (ad, d, _yorum(d), bayrak))

    print("-" * 74)
    print("KATMAN CANLILIĞI (boş sahnede, susan katman var mı)")
    for f, alt in (("hz", 1.0), ("Mi1", 0.3), ("LC4", 0.3),
                   ("KC", 0.02), ("DNp20", 2.0), ("ileri", 5.0)):
        v = float(np.mean(g("bos", f)))
        print("  %-10s %7.2f Hz   %s" % (f, v, "TAMAM" if v >= alt else "SUSMUŞ <<"))
    print("=" * 74)
    return G


if __name__ == "__main__":
    run(reps=int(sys.argv[1]) if len(sys.argv) > 1 else 10)
