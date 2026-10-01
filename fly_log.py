# -*- coding: utf-8 -*-
"""
================================================================================
 DROSOPHILA — AYRINTILI KAYIT (LOG) SİSTEMİ
================================================================================
Bir sorun gördüğünde tek yapman gereken `logs/` klasöründeki en son dosyayı
göndermek. İçinde şunlar var:

    * Her karenin tam duyusal girdisi ve motor çıktısı (CSV satırı)
    * Her karenin gerçek nöron ateşleme hızları
    * Olay satırları (acı, tehlike, yemek, takılma, ölüm, bağlantı kopması)
    * Saniyede bir insan-okur özet
    * Çökme olursa tam hata izi

Dosya boyutu sınırlıdır; dolunca yenisi açılır, eski dosyalar silinmez.
"""

import datetime
import io
import os
import sys
import traceback

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
MAX_BYTES = 40 * 1024 * 1024        # dosya başına 40 MB
KEEP_FILES = 12                     # bundan fazlası birikirse en eskiyi sil

# Kare satırının sütunları — dosyanın başına da yazılır
FRAME_COLS = [
    "t", "fps", "atlanan", "beyin_ms", "isin_ms",
    # --- duyu ---
    "can", "aclik", "yon_derece", "x", "y", "z",
    "aci", "mekano", "engel", "yuk", "tehlike_yon", "tehlike_skor",
    "tehlikeli_blok", "su_onde", "suda", "duvar", "basamak", "takilma",
    "koku_sol", "koku_sag", "koku_mesafe", "koku_ad",
    "ses", "ses_yon", "ses_ad", "ruzgar",
    "ocellus_sol", "ocellus_sag",
    "odul", "ceza", "besin_sayisi",
    # --- nöron ---
    "R1-R6", "L1", "L2", "Mi1", "Mi9", "Tm3", "Tm9", "T4a", "T5a",
    "LC4", "LPLC2", "APL", "ORN", "PN", "LH", "JO", "OCG01",
    "LoVP", "KCg-d", "KC_Hz", "KC_sessiz_yuzde", "MBON", "PAM", "PPL1", "PAM_sapma", "PPL1_sapma", "RPE",
    # --- motor ---
    "DNp20_sol", "DNp20_sag", "DNpe017", "MDN", "DNp09", "DNp01",
    "DNp04", "DNp11", "MN9", "looming", "tehdit_m", "tat", "durum",
    "koku_fazik", "DN_koku", "uyarilma", "KC_koku", "koku_degisim", "arama",
    "kur", "pC1", "pIP10", "sarki", "sicak", "termo", "temizlenme", "gok",
    "tork", "itis", "ileri", "geri", "zipla", "kosu", "ye",
    "ag_hz",
]


def _ts():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


class FlyLogger:
    def __init__(self, label="Drosophila_Fly", enabled=True):
        self.enabled = enabled
        self.f = None
        self.path = None
        self.n = 0
        self.bytes = 0
        self.label = label
        self._last_summary = 0.0
        self._prev = {}
        if enabled:
            self._open()

    # ------------------------------------------------------------------
    def _open(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self._prune()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(LOG_DIR, "drosophila_%s_%s.log" % (self.label, stamp))
        self.f = io.open(self.path, "w", encoding="utf-8", newline="\n")
        self.bytes = 0
        self.f.write("# Drosophila — MaleCNS v1.0 gerçek konektom kaydı\n")
        self.f.write("# başlangıç: %s\n"
                     % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.f.write("# python: %s\n" % sys.version.split()[0])
        self.f.write("#\n# KARE satırlarının sütunları:\n# %s\n#\n"
                     % " | ".join(FRAME_COLS))
        self.f.flush()

    def _prune(self):
        try:
            fs = sorted(
                (os.path.join(LOG_DIR, x) for x in os.listdir(LOG_DIR)
                 if x.startswith("drosophila_") and x.endswith(".log")),
                key=os.path.getmtime)
            for p in fs[:max(0, len(fs) - KEEP_FILES + 1)]:
                os.remove(p)
        except Exception:
            pass

    def _w(self, line):
        if not self.f:
            return
        try:
            self.f.write(line)
            self.bytes += len(line)
            if self.bytes > MAX_BYTES:
                self.f.close()
                self._open()
        except Exception:
            self.f = None            # kayıt yazılamıyorsa simülasyonu durdurma

    # ------------------------------------------------------------------
    def header(self, brain, extra=None):
        """Beyin kurulduktan sonra bir kez: ağın ve kalibrasyonun künyesi."""
        if not self.enabled:
            return
        ev = getattr(brain, "sign_evidence", {}) or {}
        L = [
            "=" * 78,
            "AĞ: %d nöron | %d bağlantı | %d alt-adım x %.2f ms"
            % (brain.N, brain.W.nnz, brain.substeps, brain.dt),
            "retinotopik giriş: %d sütun (sol %d / sağ %d)"
            % (len(brain.col_index), int((brain.col_side == 0).sum()),
               int((brain.col_side == 1).sum())),
            "koku: %d ORN (sol %d/sağ %d) | %d PN | %d lateral horn"
            % (len(brain.orn_L) + len(brain.orn_R), len(brain.orn_L),
               len(brain.orn_R), len(brain.pn_idx), len(brain.lh_idx)),
            "işitme: %d Johnston organı | ocelli: %d OCG01 (sol %d/sağ %d)"
            % (len(brain.jo_idx), len(brain.ocg_idx),
               len(brain.ocg_L), len(brain.ocg_R)),
            "mantar cisimciği: %d Kenyon hücresi | %d MBON | %d PAM | %d PPL1"
            % (len(brain.kc_idx), len(brain.mbon_idx),
               len(brain.pam_idx), len(brain.ppl1_idx)),
            "KALİBRASYON: tonik %.5f | GF tonik %.4f | dönüş sapması %+.4f | "
            "dönüş işareti %+.0f"
            % (brain.tonic0, getattr(brain, "gf_tonic", 0.0),
               brain.steer_bias, brain.steer_sign),
            "  işaret kanıtı: fototaksi etki %.2f (fark %+.4f) | "
            "optomotor etki %.2f (fark %+.4f)"
            % (ev.get("phototaxis_effect", 0.0), ev.get("phototaxis_diff", 0.0),
               ev.get("optomotor_effect", 0.0), ev.get("optomotor_diff", 0.0)),
        ]
        for k, v in (extra or {}).items():
            L.append("%s: %s" % (k, v))
        L.append("=" * 78)
        self._w("\n".join("# " + x for x in L) + "\n")
        if self.f:
            self.f.flush()

    def event(self, kind, msg, dedupe=True):
        """
        Dikkat çeken bir şey olduğunda tek satır.

        dedupe: aynı olay arka arkaya sürüyorsa yalnızca başlangıcı yazılır,
        bitince kaç kare sürdüğü not düşülür. (Acı 60 kare sürünce log
        60 satır dolmasın.)
        """
        if not self.enabled:
            return
        if dedupe:
            if self._prev.get(kind) == msg:
                self._prev[kind + "#"] = self._prev.get(kind + "#", 1) + 1
                return
            n = self._prev.get(kind + "#", 0)
            if n > 1:
                self._w("OLAY  %s  %-10s (%d kare daha sürdü)\n" % (_ts(), kind, n))
            self._prev[kind] = msg
            self._prev[kind + "#"] = 1
        self._w("OLAY  %s  %-10s %s\n" % (_ts(), kind, msg))
        if self.f:
            self.f.flush()

    def event_clear(self, kind):
        """Olay bitti; bir sonraki başlangıç yeniden yazılsın."""
        if not self.enabled or kind not in self._prev:
            return
        n = self._prev.pop(kind + "#", 0)
        self._prev.pop(kind, None)
        if n > 1:
            self._w("OLAY  %s  %-10s bitti (%d kare sürdü)\n" % (_ts(), kind, n))

    def error(self, exc):
        if not self.enabled:
            return
        self._w("HATA  %s\n%s\n" % (_ts(), traceback.format_exc()))
        if self.f:
            self.f.flush()

    # ------------------------------------------------------------------
    def frame(self, vals):
        """Her kare: FRAME_COLS sırasına göre tek satır."""
        if not self.enabled:
            return
        self.n += 1
        out = []
        for c in FRAME_COLS:
            v = vals.get(c, "")
            if isinstance(v, bool):
                out.append("1" if v else "0")
            elif isinstance(v, float):
                out.append("%.3f" % v)
            elif v is None:
                out.append("")
            else:
                out.append(str(v))
        self._w("KARE " + ";".join(out) + "\n")
        if self.n % 40 == 0 and self.f:
            self.f.flush()

    def summary(self, t, vals):
        """Saniyede bir insan-okur özet — logu gözle taramak için."""
        if not self.enabled or t - self._last_summary < 1.0:
            return
        self._last_summary = t
        def f(k, d=1):
            v = vals.get(k, 0.0)
            try:
                return ("%." + str(d) + "f") % float(v)
            except (TypeError, ValueError):
                return str(v)

        self._w(
            "ÖZET  %s  can %s/20 açlık %s | DNp20 %s/%s ileri %s MDN %s GF %s | "
            "tork %s itiş %s %s%s%s%s| KC sessiz %%%s | mekano %s engel %s yük %s acı %s | "
            "koku %s/%s ses %s | ocellus %s/%s | %s ms\n"
            % (_ts(), f("can", 0), f("aclik", 0),
               f("DNp20_sol"), f("DNp20_sag"), f("DNpe017"), f("MDN"), f("DNp01"),
               f("tork", 2), f("itis", 2),
               "İLERİ " if vals.get("ileri") else "",
               "GERİ " if vals.get("geri") else "",
               "ZIPLA " if vals.get("zipla") else "",
               "KOŞU " if vals.get("kosu") else "",
               f("KC_sessiz_yuzde", 0), f("mekano", 2), f("engel", 2), f("yuk", 2), f("aci", 0),
               f("koku_sol", 2), f("koku_sag", 2), f("ses", 2),
               f("ocellus_sol", 2), f("ocellus_sag", 2), f("beyin_ms")))
        if self.f:
            self.f.flush()

    def close(self):
        try:
            if self.f:
                self.f.write("# bitiş: %s  (%d kare)\n"
                             % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                self.n))
                self.f.close()
        except Exception:
            pass
        self.f = None
