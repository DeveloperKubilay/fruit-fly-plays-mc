package org.drosophila.compat;

import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;

/**
 * Minecraft sürüm farklılıklarını (1.20 - 1.21 / 26.1+) köprüleyen uyumluluk katmanı.
 * Spigot/Paper sürümleri arasında adı değişen Attribute ve Particle enumlarını
 * çalışma zamanında (runtime) güvenli biçimde çözer.
 */
public final class Compat {

    private Compat() {}

    public static final Attribute MAX_HEALTH = resolveAttribute("MAX_HEALTH", "GENERIC_MAX_HEALTH");
    public static final Particle HAPPY_VILLAGER = resolveParticle("HAPPY_VILLAGER", "VILLAGER_HAPPY");
    public static final Particle SPLASH = resolveParticle("SPLASH", "WATER_SPLASH");

    private static Attribute resolveAttribute(String... names) {
        for (String name : names) {
            try {
                return Attribute.valueOf(name);
            } catch (Exception ignored) {}
        }
        return null;
    }

    private static Particle resolveParticle(String... names) {
        for (String name : names) {
            try {
                return Particle.valueOf(name);
            } catch (Exception ignored) {}
        }
        return null;
    }

    public static void spawnHappyParticle(World w, Location loc, int count, double ox, double oy, double oz, double speed) {
        if (w != null && loc != null && HAPPY_VILLAGER != null) {
            w.spawnParticle(HAPPY_VILLAGER, loc, count, ox, oy, oz, speed);
        }
    }

    public static void spawnSplashParticle(World w, Location loc, int count, double ox, double oy, double oz, double speed) {
        if (w != null && loc != null && SPLASH != null) {
            w.spawnParticle(SPLASH, loc, count, ox, oy, oz, speed);
        }
    }
}
