# -*- coding: utf-8 -*-
"""
================================================================================
 DROSOPHILA — SİNEĞİN ÇIKARDIĞI SES
================================================================================
Gerçek Drosophila melanogaster'ın sesi kanat vuruşudur:

    * Uçuş kanat vuruşu    ~200 Hz  (erkek ~220, dişi ~190; Gö̈pfert & Robert 2002)
      Duyduğumuz vızıltı bu temel frekans ve harmonikleridir.
    * Kalkış (kaçış)       Giant Fiber ateşleyince kanat ~5 ms içinde devreye
      girer ve frekans yukarı fırlar (Card & Dickinson 2008).
    * Kur şarkısı          darbe (pulse) ~250 Hz taşıyıcı, ~35 ms darbe arası;
      sinüs şarkı ~160 Hz. Tek kanatla yapılır (pIP10 inen nöronları).

Burada üretilen ses, motor nöronlarının o anki ateşleme hızından türetilir:
frekans ve genlik DNpe017 / DNp09 / DNp01 motor nöronlarının anlık çıktısıdır.

İKİNCİ KANAL — SİNEĞİN DUYDUĞU SES (Johnston Organı)
--------------------------------------------------
Johnston organı nöronlarının o anki ateşleme hızı stereo olarak seslendirilir.
Sol kulaklıkta sol anten (JO-L), sağda sağ anten (JO-R) hızı bulunur.
Ses solda olduğunda sol kanal daha yüksek frekans ve genlik üretir.
Taşıyıcı frekans, sineğin duyma bandının ortasıdır (~250 Hz; Johnston organı
en iyi 100–400 Hz aralığında yanıt verir, Göpfert & Robert 2002).

Kapatmak için: run_real.py --sessiz ya da pencerede S tuşu.
"""

import math
import numpy as np

SR = 22050          # örnekleme hızı
CHUNK_MS = 60       # her karede üretilen parça

# Gerçek ölçümlerden frekans aralığı
F_REST = 185.0      # dinlenme/yavaş kanat
F_FLIGHT = 205.0    # normal uçuş vızıltısı
F_ESCAPE = 245.0    # kalkış/kaçış — kanat frekansı yukarı fırlar

# Ses çıkış aygıtı. None = Windows'un VARSAYILAN aygıtı (normal durum).
# Bilgisayarda birden çok sanal aygıt varsa (ör. SteelSeries Sonar) ve ses
# yanlış yere gidiyorsa run_real.py --ses-aygit "Hoparlör" ile seçilebilir.
DEVICE = None

F_EAR = 250.0       # duyulan sesin taşıyıcısı (JO bandının ortası)
EAR_REF_HZ = 36.0   # JO'nun doygunluk hızı (ölçüldü: ses 1,0 -> 36,6 Hz)


class WingBeat:
    """Faz sürekli kanat vuruşu sentezleyici."""

    def __init__(self, enabled=True, volume=0.50):
        self.ok = False
        self.enabled = bool(enabled)
        self.volume = float(volume)
        self.phase = 0.0
        self.freq = F_REST
        self.amp = 0.0
        self.sr = SR
        self.nch = 2
        self._err = 0
        self.ch = None
        self.ear_ch = None
        self.ear_phase = 0.0
        self.ear_l = 0.0
        self.ear_r = 0.0
        if not self.enabled:
            return
        self._open()

    # ------------------------------------------------------------------
    def _open(self):
        """Ses kartını aç. Butonla sonradan açılabilsin diye ayrı durur."""
        if self.ok:
            return True
        try:
            import pygame
            # ÖNEMLİ: pygame.init() mikseri ZATEN açmış olabilir (köprü
            # pencereyi açarken çağırıyor) ve genelde 44100 Hz açar. Biz
            # 22050 Hz örnek üretirsek ses iki kat hızlı ve kopuk çalar —
            # ilk sürümde tam olarak bu oldu, kullanıcı "ses gelmedi" dedi.
            # Çözüm: mikseri ne bulursak ONUN hızında sentezlemek.
            # Hangi aygıtlar var — sorun olursa kullanıcı buradan seçsin.
            try:
                import pygame._sdl2.audio as _sdl2a
                _devs = list(_sdl2a.get_audio_device_names(False))
                print("[Ses] çıkış aygıtları: %s" % ", ".join(_devs))
                print("[Ses] kullanılan: %s"
                      % (DEVICE or "Windows VARSAYILAN aygıtı"))
            except Exception:
                _devs = []
            if DEVICE:
                # İstenen aygıtı açmak için mikseri sıfırdan kuruyoruz.
                try:
                    pygame.mixer.quit()
                except Exception:
                    pass
                _ad = next((d for d in _devs if DEVICE.lower() in d.lower()), DEVICE)
                pygame.mixer.init(frequency=44100, size=-16, channels=2,
                                  buffer=1024, devicename=_ad)
            info = pygame.mixer.get_init()
            # KANAL SAYISI ÖLÇÜLDÜ VE SORUN ÇIKARDI: bu makinede (SteelSeries
            # Sonar sanal aygıtı) pygame.init() mikseri 8 KANAL açıyor
            # -> get_init() = (44100, -16, 8). sndarray.make_sound, dizinin
            # sütun sayısının mikser kanal sayısına EŞİT olmasını ister;
            # 2 sütunlu stereo diziyi reddediyor ve ses hiç çıkmıyordu
            # (panelde "SES YOK (kart)"). Önce 2 kanala düşürmeyi deniyoruz,
            # olmazsa kaç kanal varsa o kadar sütunla yazıyoruz.
            if info and int(info[2]) != 2:
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init(frequency=int(info[0]), size=-16,
                                      channels=2, buffer=1024)
                    info = pygame.mixer.get_init()
                except Exception:
                    try:
                        pygame.mixer.init()
                    except Exception:
                        pass
                    info = pygame.mixer.get_init()
            if not info:
                pygame.mixer.init(frequency=SR, size=-16, channels=2,
                                  buffer=1024)
                info = pygame.mixer.get_init()
            if not info:
                raise RuntimeError("mikser açılmadı")
            self.pygame = pygame
            self.sr = int(info[0])
            self.nch = int(info[2])
            self.stereo = self.nch >= 2
            self.ch = pygame.mixer.Channel(0)
            self.ear_ch = pygame.mixer.Channel(1)
            self.ok = True
            print("[Ses] AÇIK — mikser %d Hz, %d kanal | kanal 0: kanat "
                  "vuruşu, kanal 1: sineğin duyduğu ses%s"
                  % (self.sr, self.nch,
                     "" if self.stereo else "  (mono kart: yön duyulmaz)"))
        except Exception as e:
            print("[Ses] ses açılamadı (%s: %s) — sessiz devam ediyor"
                  % (type(e).__name__, e))
            return False
        return True

    # ------------------------------------------------------------------
    def update(self, rates, jump=False, escaping=False):
        """
        Motor nöronlarının hızından bir parça ses üretir ve kuyruğa atar.

        rates: brain.decode_motor()["rates"] — DNpe017 (ileri), DNp09 (hızlı),
               DNp01 (Giant Fiber), MDN (geri).
        """
        if not self.ok or not self.enabled:
            return
        fwd = float(rates.get("forward", 0.0))
        fast = float(rates.get("fast", 0.0))
        gf = float(rates.get("escape", 0.0))
        loom = float(rates.get("loom", 0.0))

        # Uyarılmışlık: yürüme dürtüsü + kaçış bileşenleri
        drive = fwd / 30.0 + fast / 25.0 + gf / 25.0 + loom / 40.0
        drive = max(0.0, min(1.6, drive))

        # Kalkış anında frekans yukarı fırlar (Card & Dickinson 2008)
        if jump or escaping or gf > 6.0:
            f_t = F_ESCAPE
            a_t = 0.95
        else:
            f_t = F_REST + (F_FLIGHT - F_REST) * min(1.0, drive)
            a_t = 0.12 + 0.55 * min(1.0, drive)

        # Kanat kası anında değil, birkaç vuruşta hızlanır
        self.freq += (f_t - self.freq) * 0.25
        self.amp += (a_t - self.amp) * 0.30

        n = int(self.sr * CHUNK_MS / 1000)
        t = np.arange(n, dtype=np.float32) / self.sr
        ph = self.phase + 2.0 * math.pi * self.freq * t
        # Kanat vuruşu saf sinüs değildir; harmonikler vızıltıyı verir.
        w = (np.sin(ph)
             + 0.45 * np.sin(2.0 * ph)
             + 0.22 * np.sin(3.0 * ph)
             + 0.10 * np.sin(4.0 * ph))
        w *= self.amp * self.volume / 1.77
        self.phase = float((ph[-1] + 2.0 * math.pi * self.freq / self.sr)
                           % (2.0 * math.pi))

        self._play(self.ch, np.clip(w, -1.0, 1.0))

    # ------------------------------------------------------------------
    def _play(self, ch, mono, left=None, right=None):
        """Parçayı kuyruğa at. mono verilirse iki kanala da aynısı gider."""
        if ch is None:
            return
        try:
            nch = getattr(self, "nch", 1)
            if nch >= 2:
                l = mono if left is None else left
                r = mono if right is None else right
                cols = [l, r]
                # 5.1/7.1 gibi çok kanallı kartlarda kalan kanallar sessiz;
                # make_sound sütun sayısının kanal sayısına eşit olmasını ister.
                while len(cols) < nch:
                    cols.append(np.zeros_like(l))
                buf = np.stack(cols, axis=1)
            elif mono is not None:
                buf = mono
            else:
                # mono karta düştük: iki kulağı topla (yön bilgisi kaybolur)
                buf = (left + right) * 0.5
            buf = (np.clip(buf, -1.0, 1.0) * 32767.0).astype(np.int16)
            snd = self.pygame.sndarray.make_sound(np.ascontiguousarray(buf))
            if ch.get_queue() is None:
                ch.queue(snd)
            self._err = 0
        except Exception as e:
            # KENDİNİ TOPARLA. Eskiden tek bir hata ok=False yapıp sesi
            # KALICI olarak susturuyordu — kullanıcı "ses bir yerden sonra
            # kendi kendine gitti" dedi. Ses kartı uykuya dalabilir, başka
            # bir uygulama aygıtı ele alabilir, cihaz değişebilir. Artık
            # birkaç hatadan sonra mikser yeniden açılmayı deniyor.
            self._err = getattr(self, "_err", 0) + 1
            if self._err == 1:
                print("[Ses] hata: %s: %s — yeniden açmayı deneyecek"
                      % (type(e).__name__, e))
            if self._err >= 5:
                self._err = 0
                self.ok = False
                try:
                    self.pygame.mixer.quit()
                except Exception:
                    pass
                if not self._open():
                    self.enabled = False   # gerçekten yok; panelde görünür
                    print("[Ses] ses kartı geri gelmedi — kapatıldı "
                          "(SES butonuyla tekrar denenebilir)")

    # ------------------------------------------------------------------
    def hear(self, jo_left, jo_right):
        """
        SİNEĞİN DUYDUĞU SES — Johnston organı hızından, stereo.

        jo_left / jo_right: sol ve sağ antenin JO-A/JO-B nöronlarının Hz'i.
        Genlik bu hızlardan gelir; uydurma bir "ses efekti" değildir. İki
        kanal arasındaki fark, sineğin yön kestirmek için kullandığı
        farkın ta kendisidir.
        """
        if not self.ok or not self.enabled or self.ear_ch is None:
            return
        # Kulak da kas gibi anlık değil: birkaç karede yumuşar.
        self.ear_l += (min(1.0, jo_left / EAR_REF_HZ) - self.ear_l) * 0.35
        self.ear_r += (min(1.0, jo_right / EAR_REF_HZ) - self.ear_r) * 0.35
        if self.ear_l < 0.02 and self.ear_r < 0.02:
            return                      # sessizlik: kuyruğu boş bırak
        n = int(self.sr * CHUNK_MS / 1000)
        t = np.arange(n, dtype=np.float32) / self.sr
        ph = self.ear_phase + 2.0 * math.pi * F_EAR * t
        base = np.sin(ph) + 0.30 * np.sin(2.0 * ph)
        self.ear_phase = float((ph[-1] + 2.0 * math.pi * F_EAR / self.sr)
                               % (2.0 * math.pi))
        v = self.volume * 0.9 / 1.30
        self._play(self.ear_ch, None,
                   left=base * self.ear_l * v, right=base * self.ear_r * v)

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self._open()          # --sessiz ile başlatıldıysa şimdi açılır
        else:
            self.close()
        return self.enabled

    def close(self):
        for ch in (self.ch, self.ear_ch):
            try:
                if ch is not None:
                    ch.stop()
            except Exception:
                pass
