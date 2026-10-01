package org.drosophila.vision;

import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.entity.Bee;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Item;
import org.bukkit.entity.Monster;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Vector;

import java.util.Arrays;

/**
 * Petek Göz Işın İzleyicisi (Compound Eye Raytracer).
 * Gerçek meyve sineğinde (Drosophila melanogaster) göz başına ~750, toplam ~1500 ommatidium bulunur.
 * 270° yatay x 108° dikey panoramayı 64 sütun x 24 satır = 1536 ommatidia HD ızgarasıyla tarar,
 * ardından 32x6 (192 ommatidia) beyin fotoreseptör retinasına uzaysal olarak havuzlar (spatial pooling).
 */
public class CompoundEyeRaytracer {

    public static final int COLS = 32;
    public static final int ROWS = 6;

    public static final int HD_COLS = 64;
    public static final int HD_ROWS = 24;

    public static final double H_FOV = Math.toRadians(270.0);
    public static final double V_MIN = Math.toRadians(-36.0);
    public static final double V_MAX = Math.toRadians(+72.0);
    public static final double MAX_RANGE = 16.0;

    private final double[] colAnglesHd = new double[HD_COLS];
    private final double[] rowAnglesHd = new double[HD_ROWS];
    private final double dPhiHd;

    public static class RaycastResult {
        public final int[] retinaHd = new int[HD_COLS * HD_ROWS * 3];  // 1536 ommatidium HD görseli
        public final int[] retinaRgb = new int[COLS * ROWS * 3];       // 192 ommatidium beyin retinası
        public final float[] depthBrain = new float[COLS * ROWS];      // 192 ommatidium 2D derinlik matrisi (metre)
        public final float[] distances = new float[COLS];              // 32 sütun ufuk mesafesi
        public float ocellusLeft = 0.0f;
        public float ocellusRight = 0.0f;
        public float threatDist = 99.0f;
        public float threatBearing = 0.0f;                             // + = SOL, - = SAĞ
        public String threatName = "";
        public float threatLoom = 0.0f;
        public float heat = 0.0f;                                      // 0.0 - 1.0 arası lav/ateş ısısı
        public float skyFactor = 1.0f;                                 // Gökyüzü ışık çarpanı
        public long timeOfDay = 0L;                                    // Dünya zamanı
        public float waterDist = 99.0f;                                // En yakın su mesafesi
        public float waterBearing = 0.0f;                              // Suyun açısı (+ = SOL, - = SAĞ)
        public boolean waterAhead = false;                             // Önünde su var mı?
        public boolean waterBelow = false;                             // Altında su var mı?
        public float humidity = 0.0f;                                  // Higroreseptör nem oranı (0.0 - 1.0)
        public float cold = 0.0f;                                      // Soğuk / Kar / Buz oranı (0.0 - 1.0)
        public boolean isRaining = false;                              // Yağmur / Fırtına altında mı?
        public float sunBearing = 0.0f;                                // Güneşin arıya göre açısı radyan (+ = SOL, - = SAĞ)
        public float sunElevation = 0.0f;                              // Güneş ufuk yüksekliği (-1.0 ile +1.0)
    }

    public CompoundEyeRaytracer() {
        dPhiHd = H_FOV / HD_COLS;
        for (int c = 0; c < HD_COLS; c++) {
            // Sütun 0 = EN SOL (+135°), Sütun 63 = EN SAĞ (-135°)
            colAnglesHd[c] = ((HD_COLS - 1) / 2.0 - c) * dPhiHd;
        }
        double dThetaHd = (V_MAX - V_MIN) / (HD_ROWS - 1);
        for (int r = 0; r < HD_ROWS; r++) {
            rowAnglesHd[r] = V_MAX - r * dThetaHd;
        }
    }

    /**
     * Arının anlık konumundan 64x24 = 1536 ommatidium HD petek göz ışınlarını tarar.
     */
    public RaycastResult trace(Bee bee) {
        RaycastResult res = new RaycastResult();
        Arrays.fill(res.distances, (float) MAX_RANGE);
        Arrays.fill(res.depthBrain, (float) MAX_RANGE);
        float[] depthHd = new float[HD_COLS * HD_ROWS];
        Arrays.fill(depthHd, (float) MAX_RANGE);

        Location eyeLoc = bee.getEyeLocation();
        World world = eyeLoc.getWorld();
        if (world == null) return res;

        res.skyFactor = eyeLoc.getBlock().getLightFromSky() / 15.0f;
        res.timeOfDay = world.getTime();

        double beeYawRad = Math.toRadians(eyeLoc.getYaw());

        double sumLightL = 0.0, sumLightR = 0.0;
        float maxLightL = 0.0f, maxLightR = 0.0f;
        int countL = 0, countR = 0;

        // 1. 64x24 = 1536 HD OMMATIDIUM IŞIN İZLEME
        for (int r = 0; r < HD_ROWS; r++) {
            double pitch = rowAnglesHd[r];
            double cp = Math.cos(pitch);
            double sp = Math.sin(pitch);
            double hexShift = (r % 2 == 1) ? (dPhiHd * 0.5) : 0.0;

            for (int c = 0; c < HD_COLS; c++) {
                double rayYaw = beeYawRad - colAnglesHd[c] - hexShift;
                double dx = -Math.sin(rayYaw) * cp;
                double dy = sp;
                double dz = Math.cos(rayYaw) * cp;
                Vector dir = new Vector(dx, dy, dz).normalize();

                RayTraceResult hit = world.rayTrace(eyeLoc, dir, MAX_RANGE,
                        FluidCollisionMode.ALWAYS, true, 0.35,
                        entity -> entity != bee);

                double dist = MAX_RANGE;
                int[] rgb;
                float brightness = 0.5f;

                if (hit != null) {
                    if (hit.getHitPosition() != null) {
                        dist = eyeLoc.distance(hit.getHitPosition().toLocation(world));
                    }

                    if (hit.getHitEntity() != null) {
                        Entity ent = hit.getHitEntity();
                        rgb = getEntityColor(ent);

                        if (ent instanceof Monster) {
                            if (dist < res.threatDist) {
                                res.threatDist = (float) dist;
                                res.threatName = ent.getType().name().toLowerCase();
                                res.threatBearing = (float) colAnglesHd[c];
                                if (dist < 12.0) {
                                    res.threatLoom = (float) Math.pow((12.0 - dist) / 10.0, 1.6);
                                }
                            }
                        }
                    } else if (hit.getHitBlock() != null) {
                        Block b = hit.getHitBlock();
                        Material bMat = b.getType();

                        // Su tespiti (Hygro / Su tehlikesi):
                        if (bMat == Material.WATER) {
                            if (dist < res.waterDist) {
                                res.waterDist = (float) dist;
                                res.waterBearing = (float) colAnglesHd[c];
                            }
                            if (dist < 5.0 && Math.abs(colAnglesHd[c]) < 0.45) {
                                res.waterAhead = true;
                            }
                            if (dist < 3.5 && pitch < -0.1) {
                                res.waterBelow = true;
                            }
                        }

                        int[] base = getBlockColor(bMat);
                        if (isEmissive(bMat)) {
                            // Işık yayan blok (meşale, fener, ateş vb.): karanlıkta parıldayan doğrudan ışık kaynağı
                            rgb = base;
                            brightness = 1.0f;
                        } else {
                            BlockFace face = hit.getHitBlockFace() != null ? hit.getHitBlockFace() : BlockFace.UP;
                            Block lightBlock = b.getRelative(face);

                            int skyL = lightBlock.getLightFromSky();
                            int blkL = lightBlock.getLightFromBlocks();
                            float rawLight = Math.max(skyL * res.skyFactor, blkL) / 15.0f;
                            // Biyolojik ışık kontrastı: Meşale ve karanlık arasında keskin fototaksi farkı
                            float light = Math.max(0.06f, rawLight);
                            float distFade = Math.max(0.25f, 1.0f - (float) (dist / 22.0));
                            float factor = light * distFade;

                            rgb = new int[]{
                                    Math.min(255, (int) (base[0] * factor)),
                                    Math.min(255, (int) (base[1] * factor)),
                                    Math.min(255, (int) (base[2] * factor))
                            };
                            brightness = factor;
                        }
                    } else {
                        rgb = getSkyColor(res.skyFactor);
                        brightness = Math.max(0.08f, res.skyFactor);
                    }
                } else {
                    rgb = getSkyColor(res.skyFactor);
                    brightness = Math.max(0.08f, res.skyFactor);
                }

                int hdIdx = (r * HD_COLS + c) * 3;
                res.retinaHd[hdIdx] = rgb[0];
                res.retinaHd[hdIdx + 1] = rgb[1];
                res.retinaHd[hdIdx + 2] = rgb[2];
                depthHd[r * HD_COLS + c] = (float) dist;

                // Ufuk hizası mesafe şeridi (göz hizası: pitch -10° ile +15° arası)
                if (pitch >= Math.toRadians(-10.0) && pitch <= Math.toRadians(+15.0)) {
                    int brainCol = c / (HD_COLS / COLS);
                    if (dist < res.distances[brainCol]) {
                        res.distances[brainCol] = (float) dist;
                    }
                }

                // Ocelli ve Hemisferik Işık Ölçümü (Zemin seviyesindeki meşalelerden gökyüzüne kadar: pitch >= -20°)
                if (pitch >= Math.toRadians(-20.0)) {
                    if (c < HD_COLS / 2) {
                        sumLightL += brightness;
                        if (brightness > maxLightL) maxLightL = brightness;
                        countL++;
                    } else {
                        sumLightR += brightness;
                        if (brightness > maxLightR) maxLightR = brightness;
                        countR++;
                    }
                }
            }
        }

        // 2. 1536 HD OMMATIDIA -> 192 BEYİN RETİNASINA UZAYSAL HAVUZLAMA (Spatial Pooling)
        int cRatio = HD_COLS / COLS; // 2
        int rRatio = HD_ROWS / ROWS; // 4
        for (int br = 0; br < ROWS; br++) {
            for (int bc = 0; bc < COLS; bc++) {
                int sumR = 0, sumG = 0, sumB = 0;
                float sumDepth = 0.0f;
                int count = 0;
                for (int dr = 0; dr < rRatio; dr++) {
                    int hr = br * rRatio + dr;
                    for (int dc = 0; dc < cRatio; dc++) {
                        int hc = bc * cRatio + dc;
                        int idx = (hr * HD_COLS + hc) * 3;
                        sumR += res.retinaHd[idx];
                        sumG += res.retinaHd[idx + 1];
                        sumB += res.retinaHd[idx + 2];
                        sumDepth += depthHd[hr * HD_COLS + hc];
                        count++;
                    }
                }
                int bIdx = (br * COLS + bc) * 3;
                res.retinaRgb[bIdx] = sumR / count;
                res.retinaRgb[bIdx + 1] = sumG / count;
                res.retinaRgb[bIdx + 2] = sumB / count;
                res.depthBrain[br * COLS + bc] = sumDepth / count;
            }
        }

        // Ocelli (Tepe ve yan ışık gradyanı):
        Vector dir = eyeLoc.getDirection();
        Vector rightVec = dir.clone().crossProduct(new Vector(0, 1, 0));
        if (rightVec.lengthSquared() > 0.001) {
            rightVec.normalize();
        } else {
            rightVec = new Vector(1, 0, 0);
        }
        Location leftSample = eyeLoc.clone().subtract(rightVec.clone().multiply(2.0));
        Location rightSample = eyeLoc.clone().add(rightVec.clone().multiply(2.0));
        float leftBlockLight = leftSample.getBlock().getLightFromBlocks() / 15.0f;
        float rightBlockLight = rightSample.getBlock().getLightFromBlocks() / 15.0f;

        float ocelliBaseL = (countL > 0) ? (float) (sumLightL / countL) : 0.06f;
        float ocelliBaseR = (countR > 0) ? (float) (sumLightR / countR) : 0.06f;

        // Biyolojik Ocelli Entegrasyonu:
        // Ortalama ortam ışığı (%30) + Görüş alanındaki en parlak ışık kaynağı/meşale (%50) + Yan blok ışık gradyanı (%20)
        res.ocellusLeft = Math.min(1.0f, Math.max(0.0f, (ocelliBaseL * 0.30f) + (maxLightL * 0.50f) + (leftBlockLight * 0.20f)));
        res.ocellusRight = Math.min(1.0f, Math.max(0.0f, (ocelliBaseR * 0.30f) + (maxLightR * 0.50f) + (rightBlockLight * 0.20f)));

        // 3. TERMO-DUYU (Sıcaklık / Lav & Ateş Taraması):
        res.heat = sampleHeat(eyeLoc);

        // 4. HİGRO-DUYU (Nem ve Su Yakınlığı):
        res.humidity = sampleHumidity(eyeLoc);

        // 5. TERMO-DUYU (Soğukluk / Buz & Kar Taraması):
        res.cold = sampleCold(eyeLoc);

        // 6. YAĞMUR / FIRTINA ETKİSİ:
        res.isRaining = world.hasStorm() && (world.getHighestBlockYAt(eyeLoc) <= eyeLoc.getBlockY());

        // 7. GÖKYÜZÜ PUSULASI (Dorsal Rim Area & Güneş Yönü):
        double sunAngle = ((res.timeOfDay % 24000L) / 24000.0) * 2.0 * Math.PI - (Math.PI / 2.0);
        res.sunElevation = (float) Math.sin(sunAngle);
        double sunWorldYaw = (res.timeOfDay >= 0 && res.timeOfDay <= 12000) ? (Math.PI / 2.0) : (-Math.PI / 2.0);
        double diff = sunWorldYaw - beeYawRad;
        while (diff > Math.PI) diff -= 2 * Math.PI;
        while (diff < -Math.PI) diff += 2 * Math.PI;
        res.sunBearing = (float) diff;

        // Altındaki blok su mu denetimi
        Block under1 = eyeLoc.clone().subtract(0, 0.7, 0).getBlock();
        Block under2 = eyeLoc.clone().subtract(0, 1.7, 0).getBlock();
        if (under1.getType() == Material.WATER || under2.getType() == Material.WATER) {
            res.waterBelow = true;
        }

        return res;
    }

    private float sampleHumidity(Location loc) {
        World w = loc.getWorld();
        if (w == null) return 0.0f;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();
        double minWaterDist = 99.0;
        int r = 4;
        for (int x = bx - r; x <= bx + r; x++) {
            for (int y = Math.max(w.getMinHeight(), by - 3); y <= Math.min(w.getMaxHeight(), by + 2); y++) {
                for (int z = bz - r; z <= bz + r; z++) {
                    if (w.getBlockAt(x, y, z).getType() == Material.WATER) {
                        double d = loc.distance(new Location(w, x + 0.5, y + 0.5, z + 0.5));
                        if (d < minWaterDist) {
                            minWaterDist = d;
                        }
                    }
                }
            }
        }
        if (minWaterDist < 4.0) {
            return (float) Math.max(0.0, 1.0 - (minWaterDist / 4.0));
        }
        return 0.0f;
    }

    private float sampleCold(Location loc) {
        World w = loc.getWorld();
        if (w == null) return 0.0f;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();
        double minColdDist = 99.0;

        int r = 4;
        for (int x = bx - r; x <= bx + r; x++) {
            for (int y = Math.max(w.getMinHeight(), by - 2); y <= Math.min(w.getMaxHeight(), by + 2); y++) {
                for (int z = bz - r; z <= bz + r; z++) {
                    Material mat = w.getBlockAt(x, y, z).getType();
                    if (mat == Material.SNOW || mat == Material.SNOW_BLOCK || mat == Material.POWDER_SNOW
                            || mat == Material.ICE || mat == Material.PACKED_ICE || mat == Material.BLUE_ICE
                            || mat == Material.FROSTED_ICE) {
                        double d = loc.distance(new Location(w, x + 0.5, y + 0.5, z + 0.5));
                        if (d < minColdDist) {
                            minColdDist = d;
                        }
                    }
                }
            }
        }

        if (minColdDist < 5.0) {
            return (float) Math.max(0.0, 1.0 - (minColdDist / 5.0));
        }
        return 0.0f;
    }

    private int[] getSkyColor(float skyFactor) {
        float f = Math.max(0.2f, skyFactor);
        return new int[]{
                Math.min(255, (int) (140 * f + 25)),
                Math.min(255, (int) (180 * f + 35)),
                Math.min(255, (int) (240 * f + 45))
        };
    }

    private float sampleHeat(Location loc) {
        World w = loc.getWorld();
        if (w == null) return 0.0f;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();
        double minHeatDist = 99.0;

        int r = 5;
        for (int x = bx - r; x <= bx + r; x++) {
            for (int y = Math.max(w.getMinHeight(), by - 3); y <= Math.min(w.getMaxHeight(), by + 3); y++) {
                for (int z = bz - r; z <= bz + r; z++) {
                    Material mat = w.getBlockAt(x, y, z).getType();
                    if (mat == Material.LAVA || mat == Material.FIRE || mat == Material.SOUL_FIRE
                            || mat == Material.CAMPFIRE || mat == Material.SOUL_CAMPFIRE
                            || mat == Material.MAGMA_BLOCK) {
                        double d = loc.distance(new Location(w, x + 0.5, y + 0.5, z + 0.5));
                        if (d < minHeatDist) {
                            minHeatDist = d;
                        }
                    }
                }
            }
        }

        if (minHeatDist < 6.0) {
            return (float) Math.max(0.0, 1.0 - (minHeatDist / 6.0));
        }
        return 0.0f;
    }

    private int[] getEntityColor(Entity ent) {
        if (ent instanceof Item) {
            ItemStack stack = ((Item) ent).getItemStack();
            String name = stack.getType().name().toLowerCase();
            if (name.contains("apple")) return new int[]{215, 45, 40};
            if (name.contains("flower") || name.contains("dandelion")) return new int[]{255, 235, 50};
            if (name.contains("bread") || name.contains("wheat")) return new int[]{220, 190, 90};
            return new int[]{240, 210, 120};
        }
        String t = ent.getType().name().toLowerCase();
        if (t.contains("creeper")) return new int[]{90, 200, 90};
        if (t.contains("zombie") || t.contains("husk")) return new int[]{70, 140, 100};
        if (t.contains("drowned")) return new int[]{45, 125, 115};
        if (t.contains("skeleton") || t.contains("stray")) return new int[]{210, 210, 200};
        if (t.contains("spider")) return new int[]{50, 40, 45};
        if (t.contains("phantom")) return new int[]{55, 70, 110};
        if (t.contains("enderman")) return new int[]{30, 25, 35};
        if (t.contains("witch")) return new int[]{75, 50, 85};
        if (t.contains("slime")) return new int[]{110, 210, 90};
        if (t.contains("player")) return new int[]{190, 160, 130};
        return new int[]{180, 180, 180};
    }

    public static int[] getBlockColor(Material mat) {
        if (mat == null) return new int[]{120, 120, 120};
        String name = mat.name();

        // 1. Işık Yayan ve Sıcak Bloklar
        if (name.contains("TORCH") || name.contains("LANTERN") || name.contains("GLOWSTONE")
                || name.contains("SHROOMLIGHT") || name.contains("SEA_LANTERN") || name.contains("FROGLIGHT")) {
            return new int[]{255, 235, 150};
        }
        if (name.contains("LAVA") || name.contains("FIRE") || name.contains("MAGMA")) {
            return new int[]{255, 95, 15};
        }
        if (name.contains("CAMPFIRE")) {
            return new int[]{235, 125, 40};
        }

        // 2. Cevher ve Kıymetli Bloklar (Elmas, Altın, Zümrüt vb.)
        if (name.contains("DIAMOND")) return new int[]{95, 235, 230};
        if (name.contains("GOLD")) return new int[]{250, 215, 45};
        if (name.contains("EMERALD")) return new int[]{50, 220, 100};
        if (name.contains("LAPIS")) return new int[]{30, 75, 185};
        if (name.contains("REDSTONE")) return new int[]{235, 35, 30};
        if (name.contains("IRON")) return new int[]{210, 210, 215};
        if (name.contains("COPPER")) return new int[]{195, 110, 80};
        if (name.contains("NETHERITE")) return new int[]{75, 65, 70};
        if (name.contains("COAL")) return new int[]{35, 35, 35};
        if (name.contains("QUARTZ")) return new int[]{235, 230, 225};
        if (name.contains("AMETHYST")) return new int[]{160, 95, 210};

        // 3. Tehlikeli / Zehirli Bitkiler
        if (name.contains("CACTUS")) return new int[]{35, 155, 45};
        if (name.contains("WITHER_ROSE")) return new int[]{35, 28, 40};
        if (name.contains("SWEET_BERRY")) return new int[]{170, 30, 55};
        if (name.contains("POWDER_SNOW")) return new int[]{235, 245, 255};

        // 4. Sıvılar
        if (name.contains("WATER")) return new int[]{35, 90, 210};

        // 5. Taşlar ve Mineraller
        if (name.contains("MOSSY")) return new int[]{85, 125, 65};
        if (name.contains("COBBLESTONE")) return new int[]{105, 105, 105};
        if (name.contains("STONE_BRICK")) return new int[]{115, 115, 115};
        if (name.contains("DEEPSLATE")) return new int[]{70, 70, 75};
        if (name.contains("TUFF")) return new int[]{90, 90, 85};
        if (name.contains("ANDESITE")) return new int[]{130, 130, 130};
        if (name.contains("DIORITE")) return new int[]{190, 190, 190};
        if (name.contains("GRANITE")) return new int[]{150, 105, 90};
        if (name.contains("OBSIDIAN")) return new int[]{35, 25, 55};
        if (name.contains("BASALT") || name.contains("BLACKSTONE")) return new int[]{50, 50, 55};
        if (name.contains("NETHERRACK") || name.contains("CRIMSON_NYLIUM")) return new int[]{125, 45, 45};
        if (name.contains("END_STONE")) return new int[]{225, 230, 175};
        if (name.contains("PURPUR")) return new int[]{170, 125, 170};
        if (name.contains("PRISMARINE")) return new int[]{90, 160, 145};
        if (name.contains("STONE")) return new int[]{125, 125, 125};

        // 6. Zemin & Arazi
        if (name.contains("GRASS_BLOCK") || name.contains("MOSS_BLOCK")) return new int[]{95, 155, 60};
        if (name.contains("DIRT") || name.contains("FARMLAND") || name.contains("PODZOL") || name.contains("PATH")) return new int[]{135, 95, 65};
        if (name.contains("MUD") || name.contains("SOUL_SOIL")) return new int[]{65, 50, 45};
        if (name.contains("SOUL_SAND")) return new int[]{85, 65, 55};
        if (name.contains("SANDSTONE")) return new int[]{215, 205, 155};
        if (name.contains("SAND")) return new int[]{220, 210, 160};
        if (name.contains("GRAVEL")) return new int[]{130, 125, 125};
        if (name.contains("CLAY")) return new int[]{160, 165, 175};
        if (name.contains("SNOW")) return new int[]{240, 245, 255};
        if (name.contains("ICE")) return new int[]{145, 185, 240};

        // 7. Bitkiler, Yapraklar ve Çiçekler
        if (name.contains("DANDELION") || name.contains("SUNFLOWER")) return new int[]{255, 235, 40};
        if (name.contains("POPPY") || name.contains("ROSE")) return new int[]{230, 40, 40};
        if (name.contains("ORCHID")) return new int[]{45, 165, 240};
        if (name.contains("ALLIUM") || name.contains("LILAC")) return new int[]{185, 115, 230};
        if (name.contains("TULIP")) return new int[]{240, 90, 80};
        if (name.contains("CORNFLOWER")) return new int[]{65, 105, 225};
        if (name.contains("AZALEA")) return new int[]{110, 150, 70};
        if (name.contains("LEAVES")) return new int[]{60, 135, 45};
        if (name.contains("GRASS") || name.contains("FERN") || name.contains("VINE")) return new int[]{75, 140, 50};
        if (name.contains("LILY")) return new int[]{40, 110, 45};

        // 8. Ağaç ve Tahta Türleri
        if (name.contains("CHERRY")) return new int[]{225, 180, 180};
        if (name.contains("BAMBOO")) return new int[]{190, 160, 70};
        if (name.contains("MANGROVE")) return new int[]{115, 50, 45};
        if (name.contains("WARPED")) return new int[]{45, 130, 125};
        if (name.contains("CRIMSON")) return new int[]{125, 40, 60};
        if (name.contains("DARK_OAK")) return new int[]{65, 45, 25};
        if (name.contains("ACACIA")) return new int[]{170, 95, 55};
        if (name.contains("JUNGLE")) return new int[]{160, 115, 80};
        if (name.contains("BIRCH")) return new int[]{195, 180, 130};
        if (name.contains("SPRUCE")) return new int[]{110, 80, 50};
        if (name.contains("OAK") || name.contains("WOOD") || name.contains("LOG") || name.contains("PLANKS")) return new int[]{155, 125, 80};

        // 9. 16 Renk Grubu (Yün, Beton, Terakota, Halı, Boyalı Cam vb.)
        if (name.contains("WHITE")) return new int[]{235, 235, 235};
        if (name.contains("ORANGE")) return new int[]{240, 115, 30};
        if (name.contains("MAGENTA")) return new int[]{190, 65, 175};
        if (name.contains("LIGHT_BLUE")) return new int[]{95, 170, 225};
        if (name.contains("YELLOW")) return new int[]{245, 215, 50};
        if (name.contains("LIME")) return new int[]{115, 195, 35};
        if (name.contains("PINK")) return new int[]{240, 140, 165};
        if (name.contains("GRAY")) return new int[]{75, 80, 85};
        if (name.contains("LIGHT_GRAY")) return new int[]{150, 150, 150};
        if (name.contains("CYAN")) return new int[]{40, 140, 150};
        if (name.contains("PURPLE")) return new int[]{120, 50, 165};
        if (name.contains("BLUE")) return new int[]{50, 70, 175};
        if (name.contains("BROWN")) return new int[]{115, 75, 45};
        if (name.contains("GREEN")) return new int[]{85, 125, 40};
        if (name.contains("RED")) return new int[]{185, 45, 40};
        if (name.contains("BLACK")) return new int[]{30, 30, 35};

        // 10. Cam
        if (name.contains("GLASS")) return new int[]{200, 225, 235};

        // Fallback: Malzemenin hash kodundan tutarlı renk
        int h = Math.abs(mat.name().hashCode());
        return new int[]{
                80 + (h % 120),
                80 + ((h / 120) % 120),
                80 + ((h / 14400) % 120)
        };
    }

    public static boolean isEmissive(Material mat) {
        if (mat == null) return false;
        String name = mat.name();
        return name.contains("TORCH") || name.contains("LANTERN") || name.contains("GLOWSTONE")
                || name.contains("SHROOMLIGHT") || name.contains("SEA_LANTERN") || name.contains("FROGLIGHT")
                || name.contains("LAVA") || name.contains("FIRE") || name.contains("CAMPFIRE");
    }
}
