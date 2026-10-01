"""
================================================================================
 MaleCNS v1.0 — GERÇEK ERKEK MEYVE SİNEĞİ KONEKTOMU YÜKLEYİCİSİ
================================================================================

Veri kaynağı (resmî, hesapsız indirilebilir):
    https://male-cns.janelia.org/download/
    FlyEM / HHMI Janelia + University of Cambridge + MRC LMB + Google Research
    Lisans: CC BY 4.0

Bu dosya UYDURMA BAĞLANTI ÜRETMEZ. Grafiğin tamamı ölçülmüş elektron mikroskobu
rekonstrüksiyonundan gelir:
    * 211.577 anotasyonlu gövde, 166.700 nöron (superclass'ı olanlar)
    * 25.582.938 yönlü nöron-çifti bağlantısı
    * 124.177.617 sinaptik temas

MODELLEME VARSAYIMLARI (açıkça belirtilmeli — bunlar veriden gelmez):
    1. Nörotransmitter -> işaret eşlemesi:
         asetilkolin            -> +1 (uyarıcı)
         GABA                   -> -1 (inhibitör)
         glutamat               -> -1 (Drosophila'da GluCl kanalı inhibitördür)
         histamin               -> -1 (fotoreseptörler; inhibitör)
         dopamin/oktopamin/
         serotonin              ->  0 hızlı akım (modülatör olarak ayrı işlenir)
         belirsiz / yok         -> +1 (varsayılan; kaç nöronu etkilediği raporlanır)
    2. Sinaptik temas sayısı, sinaptik ağırlıkla doğru orantılı kabul edilir.
    3. Nöron dinamiği (LIF parametreleri) ölçümden değil, literatürden alınmıştır.

Konektom NE OLAN'ı söyler (kim kime bağlı), NASIL ÇALIŞTIĞINI söylemez.
"""

import os
import json
import numpy as np

try:
    import scipy.sparse as sp
except ImportError:                                     # pragma: no cover
    sp = None

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "connectome")

BASE_URL = ("https://storage.googleapis.com/flyem-male-cns/v1.0/"
            "connectome-data/flat-connectome")
FILES = {
    "annotations": "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    "weights": "connectome-weights-male-cns-v1.0-minconf-0.5.feather",
    "neurotransmitters": "body-neurotransmitters-male-cns-v1.0.feather",
}

# Nörotransmitter -> hızlı sinaptik akım işareti
NT_SIGN = {
    "acetylcholine": 1.0,
    "gaba": -1.0,
    "glutamate": -1.0,
    "histamine": -1.0,
    "dopamine": 0.0,        # modülatör — hızlı akım üretmez
    "octopamine": 0.0,
    "serotonin": 0.0,
    "unclear": 1.0,
    "": 1.0,
}


def _need(name):
    p = os.path.join(DATA_DIR, {"annotations": "annotations.feather",
                                "weights": "weights.feather",
                                "neurotransmitters": "neurotransmitters.feather"}[name])
    if not os.path.exists(p):
        raise FileNotFoundError(
            "%s bulunamadı.\nİndir:\n  curl -L -o %s %s/%s"
            % (p, p, BASE_URL, FILES[name]))
    return p


class MaleCNS:
    """Gerçek MaleCNS konektomunu yükler ve istenen alt-grafiği çıkarır."""

    def __init__(self, data_dir=None):
        self.dir = data_dir or DATA_DIR
        self.ann = None          # pandas DataFrame: bodyId, type, superclass, ...
        self.nt = None           # bodyId -> consensus_nt
        self.edges = None        # (pre, post, weight) numpy dizileri

    # ---------------------------------------------------------------
    def load_annotations(self):
        import pyarrow.feather as ft
        cols = ["bodyId", "type", "superclass", "class", "subclass",
                "somaSide", "instance", "group"]
        t = ft.read_table(_need("annotations"))
        keep = [c for c in cols if c in t.column_names]
        self.ann = t.select(keep).to_pandas()
        self.ann["type"] = self.ann["type"].fillna("")
        self.ann["superclass"] = self.ann["superclass"].fillna("")
        return self.ann

    def load_neurotransmitters(self):
        import pyarrow.feather as ft
        t = ft.read_table(_need("neurotransmitters")).select(["body", "consensus_nt"])
        df = t.to_pandas()
        df = df.drop_duplicates(subset="body")
        df["consensus_nt"] = df["consensus_nt"].fillna("").str.lower()
        self.nt = dict(zip(df["body"].to_numpy(), df["consensus_nt"].to_numpy()))
        return self.nt

    def load_edges(self, bodies=None, min_weight=1, verbose=True):
        """
        connectome-weights: 151.856.684 yönlü nöron-çifti bağlantısı.
        Tamamını belleğe almak ~3 GB tutar; bu yüzden dosya bellek-eşlemeli açılır
        ve filtreleme pyarrow tarafında, numpy'a çevirmeden ÖNCE yapılır.
        """
        import pyarrow as pa
        import pyarrow.feather as ft
        import pyarrow.compute as pc

        t = ft.read_table(_need("weights"), memory_map=True)
        names = t.column_names
        pre = next((c for c in ("body_pre", "bodyId_pre", "pre", "source") if c in names), None)
        post = next((c for c in ("body_post", "bodyId_post", "post", "target") if c in names), None)
        wt = next((c for c in ("weight", "count", "synapses", "n") if c in names), None)
        if not (pre and post and wt):
            raise RuntimeError("Beklenmeyen şema. Sütunlar: %s" % names)
        if verbose:
            print("[MaleCNS] ham bağlantı satırı: %d" % t.num_rows)

        mask = pc.greater_equal(t[wt], min_weight)
        if bodies is not None:
            bs = pa.array(np.asarray(bodies, dtype=np.int64))
            mask = pc.and_(mask, pc.is_in(t[pre], value_set=bs))
            mask = pc.and_(mask, pc.is_in(t[post], value_set=bs))
        t = t.filter(mask)
        if verbose:
            print("[MaleCNS] filtre sonrası (ağırlık>=%d, seçim içi): %d" % (min_weight, t.num_rows))

        a = t[pre].to_numpy().astype(np.int64)
        b = t[post].to_numpy().astype(np.int64)
        w = t[wt].to_numpy().astype(np.float32)
        del t
        self.edges = (a, b, w)
        self.edge_columns = (pre, post, wt)
        return self.edges

    # ---------------------------------------------------------------
    def select(self, type_patterns=None, superclasses=None, extra_bodies=None):
        """
        İstenen hücre tiplerini seçer.
        type_patterns : regex listesi (örn. [r'^T4[abcd]$', r'^KC'])
        superclasses  : superclass listesi (örn. ['descending_neuron'])
        """
        if self.ann is None:
            self.load_annotations()
        df = self.ann
        mask = np.zeros(len(df), dtype=bool)
        if type_patterns:
            pat = "|".join("(%s)" % p for p in type_patterns)
            mask |= df["type"].str.match(pat, case=False, na=False).to_numpy()
        if superclasses:
            mask |= df["superclass"].isin(superclasses).to_numpy()
        if extra_bodies is not None and len(extra_bodies):
            mask |= df["bodyId"].isin(list(extra_bodies)).to_numpy()
        return df.loc[mask].copy()

    # ---------------------------------------------------------------
    def build(self, selection, min_weight=1, verbose=True):
        """
        Seçilen nöronlar için işaretli seyrek bağlantı matrisi kurar.
        Döner: dict(W=csr(post,pre), bodyIds, types, superclass, signs, stats)
        """
        if sp is None:
            raise RuntimeError("scipy gerekli:  pip install scipy")
        if self.nt is None:
            self.load_neurotransmitters()

        bodies = selection["bodyId"].to_numpy().astype(np.int64)
        order = np.argsort(bodies)
        bodies = bodies[order]
        if self.edges is None:
            self.load_edges(bodies=bodies, min_weight=min_weight, verbose=verbose)
        sel = selection.iloc[order].reset_index(drop=True)
        n = len(bodies)
        index = {int(b): i for i, b in enumerate(bodies)}

        a, b, w = self.edges
        # gövde kimliği -> yerel indeks (kenarlar yüklenirken zaten seçime filtrelendi)
        pre_i = np.searchsorted(bodies, a)
        post_i = np.searchsorted(bodies, b)
        ok = (bodies[np.clip(pre_i, 0, n - 1)] == a) & (bodies[np.clip(post_i, 0, n - 1)] == b)
        pre_i, post_i, ww = pre_i[ok], post_i[ok], w[ok]

        # Nörotransmitter işareti PRE nörondan gelir
        nts = np.array([self.nt.get(int(x), "") for x in bodies], dtype=object)
        signs = np.array([NT_SIGN.get(str(s).lower(), 1.0) for s in nts], dtype=np.float32)
        n_unknown = int(sum(1 for s in nts if str(s).lower() not in NT_SIGN or str(s) == ""))
        n_modul = int((signs == 0.0).sum())

        vals = ww * signs[pre_i]
        nz = vals != 0.0
        W = sp.csr_matrix((vals[nz], (post_i[nz], pre_i[nz])),
                          shape=(n, n), dtype=np.float32)
        W.sum_duplicates()

        stats = {
            "neurons": int(n),
            "edges": int(W.nnz),
            "synapses": float(np.abs(ww).sum()),
            "excitatory_neurons": int((signs > 0).sum()),
            "inhibitory_neurons": int((signs < 0).sum()),
            "modulatory_neurons": n_modul,
            "unknown_nt_neurons": n_unknown,
            "min_weight": int(min_weight),
        }
        if verbose:
            print("[MaleCNS] alt-grafik: %(neurons)d nöron, %(edges)d bağlantı, "
                  "%(synapses).0f sinaptik temas" % stats)
            print("[MaleCNS] uyarıcı %(excitatory_neurons)d | inhibitör %(inhibitory_neurons)d "
                  "| modülatör %(modulatory_neurons)d | NT bilinmeyen %(unknown_nt_neurons)d" % stats)

        return {
            "W": W,
            "bodyIds": bodies,
            "types": sel["type"].to_numpy(),
            "superclass": sel["superclass"].to_numpy(),
            "somaSide": (sel["somaSide"].fillna("").to_numpy()
                         if "somaSide" in sel else np.array([""] * n)),
            "nt": nts,
            "signs": signs,
            "stats": stats,
        }

    # ---------------------------------------------------------------
    @staticmethod
    def save(graph, path):
        sp.save_npz(path + ".W.npz", graph["W"])
        np.savez_compressed(
            path + ".meta.npz",
            bodyIds=graph["bodyIds"],
            types=graph["types"].astype("U48"),
            superclass=graph["superclass"].astype("U32"),
            somaSide=graph["somaSide"].astype("U8"),
            nt=graph["nt"].astype("U20"),
            signs=graph["signs"],
        )
        with open(path + ".stats.json", "w", encoding="utf-8") as f:
            json.dump(graph["stats"], f, indent=2)

    @staticmethod
    def load_cached(path):
        if not os.path.exists(path + ".W.npz"):
            return None
        W = sp.load_npz(path + ".W.npz")
        m = np.load(path + ".meta.npz", allow_pickle=False)
        with open(path + ".stats.json", encoding="utf-8") as f:
            stats = json.load(f)
        return {"W": W, "bodyIds": m["bodyIds"], "types": m["types"],
                "superclass": m["superclass"], "somaSide": m["somaSide"],
                "nt": m["nt"], "signs": m["signs"], "stats": stats}


# ---------------------------------------------------------------------------
#  Sinek davranışı için gerekli devrenin hücre tipleri
#  (hepsi gerçek MaleCNS tip adları — uydurma yok)
# ---------------------------------------------------------------------------
BEHAVIOR_CIRCUIT = [
    # --- Görsel giriş ---
    r"^R[1-8]",                     # fotoreseptörler (histaminerjik)
    r"^L[1-5]$",                    # lamina monopolar hücreleri
    r"^Mi\d",                       # medulla intrinsic
    r"^Tm\d", r"^TmY\d",            # transmedullary
    r"^T[1-5][a-d]?$",              # T4/T5 yön-seçici hareket dedektörleri
    r"^C[23]$", r"^Dm\d", r"^Pm\d",
    # --- Lobula çıkış (görsel özellik dedektörleri) ---
    r"^LC\d+", r"^LPLC\d+", r"^LPC\d+", r"^LT\d+",
    # --- Mantar cisimciği (öğrenme) ---
    r"^KC", r"^MBON", r"^PAM\d", r"^PPL1", r"^APL$", r"^DPM$",
    # --- Merkezi kompleks (pusula / yön) ---
    #   EPG + PEN + PEG + Delta7 : Halka çekici (ring attractor) pusula devresi.
    #   MeTu -> TuBu -> ER : Görsel yön ipuçlarının pusula nöronlarına (ring neurons) aktarım yolu.
    #   PFN : Hız ve yön sinyallerini hDelta vektör hafızasına taşıyan yol integrasyonu nöronları.
    r"^EPG", r"^PEN", r"^PEG", r"^Delta7", r"^ER\d", r"^PFL", r"^FC\d", r"^hDelta",
    r"^MeTu", r"^TuBu", r"^PFN", r"^PFR", r"^PFG",
    # --- Antennal lob (koku) ---
    #   ORN  : koku reseptör nöronu (anten) — 53 gerçek glomerül tipi
    #   *PN  : projeksiyon nöronu (DL4_adPN, VA1v_adPN, VP2_l2PN ...)
    #   LH   : lateral horn — DOĞUŞTAN gelen koku->davranış yolu.
    #          Sinek elmaya öğrenmeden gider; o karar burada verilir.
    r"^ORN", r".*PN$", r"^lPN", r"^mPN", r"^DA\d", r"^VA\d", r"^LH",
    # --- Johnston organı (İŞİTME) ve anten mekanoreseptörleri ---
    #   JO-A / JO-B : ses ve kanat vuruşu titreşimi (Kamikouchi ve ark. 2009)
    #   JO-C / JO-E : yerçekimi ve hava akımı (statik anten sapması)
    #   AMMC        : antennal mechanosensory and motor center (ilk aktarma)
    #   WED         : wedge — işitsel/mekanosensör aktarma, inen nöronlara gider
    r"^JO-", r"^AMMC", r"^WED",
]


def dn_upstream_bodies(min_contacts=25, min_weight=3, verbose=True):
    """
    İnen nöronlara (motor çıkışı) doğrudan girdi veren nöronları bulur.

    Neden gerekli: DNp20 tam konektomda 4.806 sinaptik temas alır, ama görsel
    alt-grafiğimizde yalnızca 222'sini alıyordu — girdisinin %95'i eksikti.
    Aç kalan motor nöronu görüntüye değil gürültüye tepki verir. Bu fonksiyon
    eksik halkayı (merkezi beyin ara nöronları) kapatır.
    """
    import pyarrow as pa
    import pyarrow.feather as ft
    import pyarrow.compute as pc

    ann = ft.read_table(_need("annotations")).select(["bodyId", "superclass"]).to_pandas()
    ann["superclass"] = ann["superclass"].fillna("")
    dn = ann.loc[ann["superclass"] == "descending_neuron", "bodyId"].to_numpy().astype(np.int64)

    t = ft.read_table(_need("weights"), memory_map=True)
    t = t.filter(pc.greater_equal(t["weight"], min_weight))
    t = t.filter(pc.is_in(t["body_post"], value_set=pa.array(dn)))
    pre = t["body_pre"].to_numpy().astype(np.int64)
    w = t["weight"].to_numpy().astype(np.float64)
    del t
    order = np.argsort(pre, kind="stable")
    pre, w = pre[order], w[order]
    u, st = np.unique(pre, return_index=True)
    tot = np.add.reduceat(w, st)
    sel = u[tot >= min_contacts]
    if verbose:
        print("[MaleCNS] inen nöronları >=%d temasla besleyen: %d nöron"
              % (min_contacts, len(sel)))
    return sel


def save_missing_input(graph, cache, min_weight=3, verbose=True):
    """
    Her nöron için: tam konektomda aldigi girdinin yuzde kaci alt-grafikte YOK.

    Tonik uyarim bu orana gore olceklenir. Optik lob neredeyse tamdir (Mi1 %5
    eksik), inen nöronlar ise tum beyinden girdi alir (DNp20 %95 eksik). Sabit
    tonik uyarim verirsek Kenyon hucrelerinin seyrekligi bozulur; bu dosya
    olmadan model dogru calismaz.
    """
    import pyarrow as pa
    import pyarrow.feather as ft
    import pyarrow.compute as pc

    bodies = graph["bodyIds"].astype(np.int64)
    t = ft.read_table(_need("weights"), memory_map=True)
    t = t.filter(pc.greater_equal(t["weight"], min_weight))
    t = t.filter(pc.is_in(t["body_post"], value_set=pa.array(bodies)))
    post = t["body_post"].to_numpy().astype(np.int64)
    w = t["weight"].to_numpy().astype(np.float64)
    del t

    full_in = np.zeros(len(bodies), dtype=np.float64)
    ix = np.searchsorted(bodies, post)
    np.add.at(full_in, ix, w)

    sub_in = np.asarray(abs(graph["W"]).sum(axis=1)).ravel().astype(np.float64)
    denom = np.maximum(full_in, 1.0)
    missing = np.clip(1.0 - sub_in / denom, 0.0, 1.0).astype(np.float32)
    np.savez_compressed(cache + ".inputs.npz",
                        missing=missing, full_in=full_in.astype(np.float32))
    if verbose:
        print("[MaleCNS] eksik girdi orani: ortalama %%%.0f  (medyan %%%.0f)"
              % (100 * missing.mean(), 100 * np.median(missing)))
    return missing


def build_behavior_graph(min_weight=3, cache="connectome/malecns_behavior",
                         dn_upstream=25, verbose=True):
    """
    Görme -> öğrenme -> hareket zincirinin GERÇEK konektom alt-grafiğini kurar.
    İnen nöronların TAMAMI dahil edilir (motor çıkışı oradan okunacak).
    """
    cached = MaleCNS.load_cached(cache)
    if cached is not None:
        if verbose:
            print("[MaleCNS] önbellekten yüklendi: %(neurons)d nöron, %(edges)d bağlantı"
                  % cached["stats"])
        if not os.path.exists(cache + ".inputs.npz"):
            save_missing_input(cached, cache, min_weight=min_weight, verbose=verbose)
        return cached

    mc = MaleCNS()
    mc.load_annotations()
    extra = dn_upstream_bodies(min_contacts=dn_upstream, min_weight=min_weight,
                               verbose=verbose) if dn_upstream else None
    sel = mc.select(type_patterns=BEHAVIOR_CIRCUIT,
                    superclasses=["descending_neuron"],
                    extra_bodies=extra)
    if verbose:
        print("[MaleCNS] seçilen nöron: %d" % len(sel))
    g = mc.build(sel, min_weight=min_weight, verbose=verbose)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    MaleCNS.save(g, cache)
    save_missing_input(g, cache, min_weight=min_weight, verbose=verbose)
    return g


if __name__ == "__main__":
    g = build_behavior_graph()
    print(json.dumps(g["stats"], indent=2))
