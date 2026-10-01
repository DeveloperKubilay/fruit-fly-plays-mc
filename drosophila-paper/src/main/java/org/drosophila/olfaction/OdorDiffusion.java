package org.drosophila.olfaction;

import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.entity.Bee;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Item;
import org.bukkit.inventory.ItemStack;
import org.bukkit.util.Vector;

import java.util.Collection;

/**
 * 3D Koku Yayılımı, Anten Örneklemesi ve Biyolojik Tokluk Kapısı (Odor Diffusion & Satiety Gating).
 *
 * Gerçek Drosophila Melanogaster Koku Hiyerarşisi:
 * 1. Yerdeki Meyveler / Besinler (Elma, kavun, fermente meyveler):
 *    - 16 blok menzil, %100 Çekim Gücü (En yüksek öncelik)
 * 2. Ağaç Yaprakları (*_LEAVES):
 *    - 5.0 blok dar koku menzili, %38 Çekim Gücü (~%40)
 *    - Sinek yaprağın içine hapsolmasın diye reseptör adaptasyonu (yakında koku sönümü)
 *    - Tokluk >= 15.0 olduğunda yaprak kokusu tamamen sıfırlanır, sinek açık göğe uçar!
 * 3. Çiçekler / Nektar:
 *    - 4.0 blok dar menzil, %15 zayıf çekim
 *    - Yalnızca sinek açsa (foodLevel < 12.0) algılanır; tok sinek çiçekle ilgilenmez.
 */
public class OdorDiffusion {

    public static final double ODOR_RANGE = 16.0;
    public static final double ANT_FWD = 0.35;   // Antenlerin baştan öne mesafesi
    public static final double ANT_SIDE = 0.20;  // İki anten arası yarı mesafe

    public static class OdorSample {
        public float odorLeft = 0.0f;
        public float odorRight = 0.0f;
        public float foodOdorLeft = 0.0f;
        public float foodOdorRight = 0.0f;
        public float flowerOdorLeft = 0.0f;
        public float flowerOdorRight = 0.0f;
        public float leafOdorLeft = 0.0f;
        public float leafOdorRight = 0.0f;
        public float peerDist = 99.0f;           // En yakın diğer arı mesafesi
        public float peerBearing = 0.0f;         // Diğer arının yön açısı
        public float closestDist = 99.0f;
        public String foodName = "";
        public float pathLength = -1.0f;
        public float taste = 0.0f;               // Ayak ve hortum tat duyusu (0.0 nötr, +1 tatlı/şeker, -1 acı/zehir)
        public float foodDeltaY = 0.0f;          // En yakın besinin arıya göre dikey farkı (+ üstte, - altta)
        public Location foodLoc = null;          // En yakın besin konumu
    }

    public OdorSample sample(Bee bee) {
        return sample(bee, 10.0);
    }

    public OdorSample sample(Bee bee, double foodLevel) {
        OdorSample res = new OdorSample();
        Location beeLoc = bee.getLocation();
        World world = beeLoc.getWorld();
        if (world == null) return res;

        Location headPos = bee.getEyeLocation();
        Vector fwd = beeLoc.getDirection().setY(0).normalize();
        if (fwd.lengthSquared() < 0.001) fwd = new Vector(0, 0, 1);
        Vector right = new Vector(-fwd.getZ(), 0, fwd.getX()).normalize();
        Vector left = new Vector(fwd.getZ(), 0, -fwd.getX()).normalize();

        Location antLeft = headPos.clone().add(fwd.clone().multiply(ANT_FWD)).add(left.clone().multiply(ANT_SIDE));
        Location antRight = headPos.clone().add(fwd.clone().multiply(ANT_FWD)).add(right.clone().multiply(ANT_SIDE));

        // Biyolojik Doygunluk Kapısı (Satiety Gating - dNPF / DILP Nöropeptit Modülasyonu):
        // Tokluk 20.0 = Tam tok, 3.0 = Aşırı aç
        // Tok sinekte koku hassasiyeti sönümlenir; çiçek ve yaprak kokusu tamamen kapanır!
        double hungerFactor;
        if (foodLevel >= 17.0) {
            hungerFactor = 0.06; // Tamamen tok: koku ilgisi %94 sönümlenir, sinek açık alanda serbest uçar
        } else if (foodLevel >= 14.0) {
            hungerFactor = 0.35; // Az aç: sadece çok güçlü fermente kokuları fark eder
        } else {
            hungerFactor = Math.min(1.0, (20.0 - foodLevel) / 10.0); // 0.6 - 1.0 tam duyu keskinliği
        }

        Location bestSourceLoc = null;
        double bestSalience = 0.0;
        double bestDist = 99.0;
        String sourceName = "";
        String sourceType = ""; // "fruit", "food", "leaf", "flower"
        double sourceMaxRange = ODOR_RANGE;
        float sourceBaseWeight = 1.0f;

        // 1. YERDEKİ BESİNLER (Elma, karpuz, fermente meyveler vs. - 16 blok menzil, %100 Çekim)
        // Drosophila melanogaster için en yüksek çekim her zaman çürüyen/fermente meyvelerdir!
        Collection<Entity> nearby = bee.getNearbyEntities(ODOR_RANGE, ODOR_RANGE, ODOR_RANGE);
        for (Entity e : nearby) {
            if (e instanceof Item) {
                Item item = (Item) e;
                ItemStack stack = item.getItemStack();
                Material mat = stack.getType();
                if (isAttractiveFood(mat)) {
                    double d = beeLoc.distance(item.getLocation());
                    if (d <= ODOR_RANGE) {
                        boolean isFruit = isFruitFood(mat);
                        float baseWeight = isFruit ? 1.0f : 0.70f;
                        // Mesafe azaldıkça çekim artar:
                        double salience = baseWeight * ((ODOR_RANGE - d) / ODOR_RANGE);
                        if (foodLevel >= 17.0) {
                            salience *= 0.25; // Tok sinek yemeği sadece burnunun dibindeyse fark eder
                        }
                        if (salience > bestSalience) {
                            bestSalience = salience;
                            bestDist = d;
                            bestSourceLoc = item.getLocation();
                            sourceName = mat.name().toLowerCase();
                            sourceType = isFruit ? "fruit" : "food";
                            sourceMaxRange = ODOR_RANGE;
                            sourceBaseWeight = baseWeight;
                        }
                    }
                }
            }
        }

        // 2. AĞAÇ YAPRAKLARI (Maksimum 5.0 blok dar menzil, %38 çekim)
        // Sinek tokken (foodLevel >= 15.0) yapraklara ASLA yönelmez, böylece ağaç tacında kilitlenip kalmaz!
        if (foodLevel < 15.0) {
            int bx = beeLoc.getBlockX();
            int by = beeLoc.getBlockY();
            int bz = beeLoc.getBlockZ();
            int lr = 4; // Yatay 4 blok yarıçap

            for (int x = bx - lr; x <= bx + lr; x++) {
                for (int z = bz - lr; z <= bz + lr; z++) {
                    for (int y = Math.max(world.getMinHeight(), by - 2); y <= Math.min(world.getMaxHeight(), by + 3); y++) {
                        Block b = world.getBlockAt(x, y, z);
                        Material mat = b.getType();
                        if (isLeafBlock(mat)) {
                            Location lLoc = b.getLocation().add(0.5, 0.5, 0.5);
                            double d = beeLoc.distance(lLoc);
                            if (d <= 5.0) {
                                float leafWeight = 0.38f; // ~%38-40 hafif doğal çekim
                                // Yaprak İçi Reseptör Adaptasyonu (Sensory Adaptation):
                                // Sinek yaprağa çok yakınken (d < 1.4) koku itkisi %70 sönümlenir.
                                // Bu sayede sinek kafasını yaprak bloklarına gömüp hapsolmaz, kenardan süzülür!
                                if (d < 1.4) {
                                    leafWeight *= 0.30f;
                                }
                                double salience = leafWeight * ((5.0 - d) / 5.0);
                                salience *= hungerFactor;
                                if (salience > bestSalience) {
                                    bestSalience = salience;
                                    bestDist = d;
                                    bestSourceLoc = lLoc;
                                    sourceName = mat.name().toLowerCase();
                                    sourceType = "leaf";
                                    sourceMaxRange = 5.0;
                                    sourceBaseWeight = leafWeight;
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. DÜNYADAKİ ÇİÇEKLER VE KOVANLAR (Yalnızca sinek açsa: foodLevel < 12.0, 4.0 blok dar menzil, %15 zayıf çekim)
        // Drosophila bir bal arısı değildir; çiçeklere sadece acil hayatta kalma durumunda çok az ilgi duyar.
        // Doymuş bir sinek çiçekleri tamamen görmezden gelir!
        if (foodLevel < 12.0) {
            int bx = beeLoc.getBlockX();
            int by = beeLoc.getBlockY();
            int bz = beeLoc.getBlockZ();
            int fr = 3; // 3-4 blok dar yarıçap

            for (int x = bx - fr; x <= bx + fr; x++) {
                for (int z = bz - fr; z <= bz + fr; z++) {
                    for (int y = Math.max(world.getMinHeight(), by - 2); y <= Math.min(world.getMaxHeight(), by + 2); y++) {
                        Block b = world.getBlockAt(x, y, z);
                        Material mat = b.getType();
                        if (isFlowerOrNectar(mat)) {
                            Location fLoc = b.getLocation().add(0.5, 0.5, 0.5);
                            double d = beeLoc.distance(fLoc);
                            if (d <= 4.0) {
                                float flowerWeight = 0.15f; // Sadece %15 ikincil çekim
                                double salience = flowerWeight * ((4.0 - d) / 4.0);
                                salience *= hungerFactor;
                                if (salience > bestSalience) {
                                    bestSalience = salience;
                                    bestDist = d;
                                    bestSourceLoc = fLoc;
                                    sourceName = mat.name().toLowerCase();
                                    sourceType = "flower";
                                    sourceMaxRange = 4.0;
                                    sourceBaseWeight = flowerWeight;
                                }
                            }
                        }
                    }
                }
            }
        }

        if (bestSourceLoc != null && bestSalience > 0.001) {
            res.closestDist = (float) bestDist;
            res.foodName = sourceName;
            res.foodDeltaY = (float) (bestSourceLoc.getY() - beeLoc.getY());
            res.foodLoc = bestSourceLoc.clone();

            double dL = antLeft.distance(bestSourceLoc);
            double dR = antRight.distance(bestSourceLoc);

            float concL = (float) Math.max(0.0, (sourceMaxRange - dL) / sourceMaxRange) * sourceBaseWeight;
            float concR = (float) Math.max(0.0, (sourceMaxRange - dR) / sourceMaxRange) * sourceBaseWeight;

            // Duvar engeli kontrolü (Yaprak blokları kokuyu tamamen kesmez, taş/toprak duvarlar keser)
            if (isBlockedByWall(headPos, bestSourceLoc)) {
                concL *= 0.35f;
                concR *= 0.35f;
                res.pathLength = (float) (bestDist * 1.8);
            } else {
                res.pathLength = (float) bestDist;
            }

            // Açlık / Doygunluk faktörü modülasyonu
            concL = (float) (concL * hungerFactor);
            concR = (float) (concR * hungerFactor);

            res.odorLeft = Math.min(1.0f, Math.max(0.0f, concL));
            res.odorRight = Math.min(1.0f, Math.max(0.0f, concR));

            if ("flower".equals(sourceType)) {
                res.flowerOdorLeft = res.odorLeft;
                res.flowerOdorRight = res.odorRight;
            } else if ("leaf".equals(sourceType)) {
                res.leafOdorLeft = res.odorLeft;
                res.leafOdorRight = res.odorRight;
                res.foodOdorLeft = res.odorLeft * 0.5f;
                res.foodOdorRight = res.odorRight * 0.5f;
            } else {
                res.foodOdorLeft = res.odorLeft;
                res.foodOdorRight = res.odorRight;
            }

            // 4. TAT DUYUSU (Tarsal GRN & PER - Çiçeğe, yaprağa veya meyveye doğrudan temas)
            if (bestDist < 1.4) {
                if ("leaf".equals(sourceType)) {
                    res.taste = 0.25f; // Yaprakta taze bitki dokunuşu / hafif tat
                } else if ("flower".equals(sourceType)) {
                    res.taste = 0.50f; // Çiçek nektarı tadı
                } else {
                    if (sourceName.contains("wither") || sourceName.contains("cactus") || sourceName.contains("poison") || sourceName.contains("rotten")) {
                        res.taste = -1.0f; // Acı / zehir (PPL1 dopamin kaçınma)
                    } else {
                        res.taste = 0.95f; // Tatlı meyve şekeri (PAM dopamin ödül!)
                        if (!bee.hasNectar()) {
                            bee.setHasNectar(true);
                        }
                    }
                }
            }
        }

        // 5. DİĞER ARILAR (Sosyal Alan & Akran Mesafesi):
        Collection<Entity> peerBees = world.getNearbyEntities(beeLoc, 12.0, 8.0, 12.0,
                e -> (e instanceof Bee && e != bee));
        double minPeerDist = 99.0;
        Entity closestPeer = null;
        for (Entity pb : peerBees) {
            double d = beeLoc.distance(pb.getLocation());
            if (d < minPeerDist) {
                minPeerDist = d;
                closestPeer = pb;
            }
        }
        if (closestPeer != null) {
            res.peerDist = (float) minPeerDist;
            Vector toPeer = closestPeer.getLocation().toVector().subtract(beeLoc.toVector()).setY(0);
            if (toPeer.lengthSquared() > 0.001) {
                toPeer.normalize();
                Vector dir = beeLoc.getDirection().setY(0).normalize();
                double angle = Math.atan2(dir.getX() * toPeer.getZ() - dir.getZ() * toPeer.getX(),
                                          dir.getX() * toPeer.getX() + dir.getZ() * toPeer.getZ());
                res.peerBearing = (float) angle;
            }
        }

        return res;
    }

    public static boolean isFruitFood(Material mat) {
        if (mat == null) return false;
        String n = mat.name().toLowerCase();
        return n.contains("apple") || n.contains("melon") || n.contains("sweet_berr")
                || n.contains("glow_berr") || n.contains("honey") || n.contains("sugar")
                || n.contains("cookie") || n.contains("pie") || n.contains("cake")
                || n.contains("fermented");
    }

    public static boolean isAttractiveFood(Material mat) {
        if (mat == null) return false;
        String n = mat.name().toLowerCase();
        return mat.isEdible() || isFruitFood(mat) || n.contains("bread") || n.contains("wheat")
                || n.contains("carrot") || n.contains("potato") || n.contains("beef")
                || n.contains("pork") || n.contains("mutton") || n.contains("chicken");
    }

    public static boolean isLeafBlock(Material mat) {
        if (mat == null) return false;
        String n = mat.name().toLowerCase();
        return n.endsWith("_leaves") || n.contains("leaves") || n.contains("azalea_leaves");
    }

    public static boolean isFlower(Material mat) {
        if (mat == null) return false;
        String n = mat.name().toLowerCase();
        return n.contains("flower") || n.contains("poppy") || n.contains("dandelion")
                || n.contains("orchid") || n.contains("allium") || n.contains("bluet")
                || n.contains("tulip") || n.contains("daisy") || n.contains("cornflower")
                || n.contains("lily_of_the_valley") || n.contains("rose") || n.contains("sunflower")
                || n.contains("lilac") || n.contains("peony") || n.contains("blossom");
    }

    public static boolean isFlowerOrNectar(Material mat) {
        if (mat == null) return false;
        String n = mat.name().toLowerCase();
        return n.contains("dandelion") || n.contains("poppy") || n.contains("orchid")
                || n.contains("allium") || n.contains("bluet") || n.contains("tulip")
                || n.contains("daisy") || n.contains("cornflower") || n.contains("lily")
                || n.contains("rose") || n.contains("sunflower") || n.contains("lilac")
                || n.contains("peony") || n.contains("blossom") || n.contains("torchflower")
                || n.contains("pitcher") || n.contains("azalea") || n.contains("hive")
                || n.contains("nest") || n.contains("honey");
    }

    private boolean isBlockedByWall(Location from, Location to) {
        World w = from.getWorld();
        if (w == null) return false;
        Location target = to.clone().add(0, 0.35, 0);
        Vector dir = target.toVector().subtract(from.toVector());
        double dist = dir.length();
        if (dist < 1.0) return false;
        dir.normalize();

        for (double d = 0.5; d < dist - 0.6; d += 0.8) {
            Location p = from.clone().add(dir.clone().multiply(d));
            Block b = p.getBlock();
            // Yaprak blokları kokunun yayılmasını tamamen engellemez (doğal gözenekli yapı),
            // sadece sert katı bloklar (taş, toprak, tahta vs.) kokuyu keser.
            if (b.getType().isSolid() && !isLeafBlock(b.getType())) {
                return true;
            }
        }
        return false;
    }
}
