package org.drosophila.auditory;

import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.*;

import java.util.Collection;

/**
 * Johnston Organı (İşitme & Rüzgâr / Hava Akımı) Duyusal Örnekleyicisi.
 * Gerçek meyve sineğinde antenin 2. segmentinde (pedisel) yer alan Johnston Organı:
 * - JO-A/B: Yüksek frekanslı ses titreşimlerini (yaklaşan avcı, kanat çırpışı, ayak sesleri).
 * - JO-C/E: Hava akımını, uçuş hızını ve rüzgâr sapmasını (statik anten bükülmesi) algılar.
 */
public class AuditoryWindSampler {

    public static class AuditorySample {
        public float soundLevel = 0.0f;       // 0.0 - 1.0 arası ses şiddeti
        public float soundBearing = 0.0f;     // Radyan cinsinden sesin geliş açısı (+ = SOL, - = SAĞ)
        public String soundName = "sessiz";   // En baskın ses kaynağı
        public float windLevel = 0.0f;        // 0.0 - 1.0 arası rüzgâr / hava hızı
    }

    private static final double MAX_HEARING_RANGE = 16.0;

    /**
     * Arının konumundan çevredeki sesleri ve hava akımını örnekler.
     */
    public AuditorySample sample(Bee bee) {
        AuditorySample sample = new AuditorySample();
        if (bee == null || !bee.isValid()) return sample;

        Location beeLoc = bee.getLocation();
        World world = beeLoc.getWorld();
        if (world == null) return sample;

        // 1. RÜZGÂR VE HAVA HIZI (JO-C / JO-E):
        // Arının anlık hız vektörünün büyüklüğü hava direncini oluşturur.
        org.bukkit.util.Vector vel = bee.getVelocity();
        double speed = (vel != null) ? vel.length() : 0.0;
        float wind = (float) Math.min(1.0, speed * 2.2);

        // Hava durumu etkisi (yağmur/fırtına hava akımını ve türbülansı artırır)
        if (world.hasStorm()) {
            wind = Math.min(1.0f, wind + 0.35f);
        }
        if (world.isThundering()) {
            wind = Math.min(1.0f, wind + 0.25f);
        }
        sample.windLevel = wind;

        // 2. İŞİTME (JO-A / JO-B):
        // 16 blok yarıçapındaki ses yayan varlıkları (canavarlar, koşan oyuncular, patlamalar, havai fişekler) tara
        Collection<Entity> nearby = world.getNearbyEntities(beeLoc, MAX_HEARING_RANGE, MAX_HEARING_RANGE, MAX_HEARING_RANGE,
                e -> (e instanceof Monster || e instanceof Player || e instanceof FireworkRocket || e instanceof TNTPrimed) && e != bee);

        double maxIntensity = 0.0;
        Entity loudestEntity = null;
        double loudestDist = MAX_HEARING_RANGE;

        for (Entity e : nearby) {
            double dist = beeLoc.distance(e.getLocation());
            if (dist > MAX_HEARING_RANGE) continue;

            double intensity = 1.0 - (dist / MAX_HEARING_RANGE);

            // Hareket/eylem faktörü: koşan veya saldıran varlık daha çok ses çıkarır
            if (e instanceof Player) {
                Player p = (Player) e;
                if (p.isSprinting()) intensity *= 1.4;
                else if (p.isSneaking()) intensity *= 0.25;
            } else if (e instanceof Monster) {
                // Creeper yaklaşması, zombi homurtusu vs.
                String typeName = e.getType().name().toLowerCase();
                if (typeName.contains("creeper")) intensity *= 1.3;
                else if (typeName.contains("zombie")) intensity *= 1.1;
            } else if (e instanceof TNTPrimed) {
                // TNT fünye/patlama tıslaması (yüksek tehdit)
                intensity *= 1.9;
            } else if (e instanceof FireworkRocket) {
                // Havai fişek roket ıslığı ve patlaması
                intensity *= 1.6;
            }

            if (intensity > maxIntensity) {
                maxIntensity = intensity;
                loudestEntity = e;
                loudestDist = dist;
            }
        }

        if (loudestEntity != null && maxIntensity > 0.05) {
            sample.soundLevel = (float) Math.min(1.0, maxIntensity);
            sample.soundName = loudestEntity.getType().name().toLowerCase();

            // Sesin yönünü hesapla (+ = SOL, - = SAĞ sözleşmesi)
            Location eLoc = loudestEntity.getLocation();
            double dx = eLoc.getX() - beeLoc.getX();
            double dz = eLoc.getZ() - beeLoc.getZ();

            // Dünyadaki açı (radyan)
            double angleToSource = Math.atan2(-dx, dz); // Minecraft X-Z açısı
            double beeYawRad = Math.toRadians(beeLoc.getYaw());

            // Açı farkı: kaynağın arının görüş çizgisine göre bağıl açısı
            double diff = angleToSource - beeYawRad;
            while (diff > Math.PI) diff -= 2 * Math.PI;
            while (diff < -Math.PI) diff += 2 * Math.PI;

            // Minecraft koordinatlarında SOL = +X, dolayısıyla bağıl açı:
            // diff > 0 olduğunda saat yönünün tersi (SOL)
            sample.soundBearing = (float) -diff;
        }

        return sample;
    }
}
