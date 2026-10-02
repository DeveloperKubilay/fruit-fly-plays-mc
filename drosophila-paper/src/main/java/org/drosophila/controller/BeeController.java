package org.drosophila.controller;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.entity.Bee;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.util.Vector;
import org.drosophila.compat.Compat;
import org.drosophila.olfaction.OdorDiffusion;

import java.util.Collection;
import java.util.UUID;

/**
 * 3D Uçan Arı (Bee) Beden Yöneticisi ve Motor Uygulayıcısı.
 * Python beyninden gelen inen nöron motor komutlarını (DNp20 tork, DNpe017 itiş, DNp01 sıçrama/kalkış)
 * gerçek 3D böcek uçuş fiziğine çevirir.
 */
public class BeeController implements Listener {

    private final JavaPlugin plugin;
    private Bee beeEntity;
    private UUID beeUuid;
    private String displayName = "§eFruit Fly";
    private double speedMultiplier = 1.0;
    private boolean invulnerable = false;
    private boolean respawnScheduled = false;
    private boolean isBottled = false;

    // Metabolik Açlık & Enerji (Drosophila dNPF Modülasyonu)
    public static final double MAX_FOOD = 20.0;
    public static final double MIN_FOOD = 3.0; // Biyolojik taban: açlıktan ölmez, sadece arama dürtüsü tavan yapar
    private double foodLevel = MAX_FOOD;
    private int flowerSipCooldown = 0; // Çiçek nektarı yudumlama aralığı
    private int leafRestCooldown = 0;   // Ağaç yaprağında dinlenme aralığı
    private String lastMood = "neutral";
    private OdorDiffusion.OdorSample lastOdor = null;

    // Durum ve duyusal izler
    private boolean hurtLastFrame = false;
    private double lastHealth = 20.0;
    private int stuckTicks = 0;
    private Location lastPosCheck = null;
    private int particleTick = 0;

    public static class MotorCommand {
        public boolean forward = false;
        public boolean back = false;
        public float steering_torque = 0.0f;
        public float pitch = 0.0f;
        public boolean is_escaping = false;
        public boolean jump = false;
        public boolean sprint = false;
        public boolean eat = false;
        public float forward_thrust = 0.0f;
        public String mood = "neutral";
    }

    public BeeController(JavaPlugin plugin) {
        this.plugin = plugin;
        Bukkit.getPluginManager().registerEvents(this, plugin);
    }

    public void setDisplayName(String name) {
        this.displayName = name;
        if (beeEntity != null && beeEntity.isValid()) {
            beeEntity.setCustomName(name);
        }
    }

    public void setSpeedMultiplier(double mult) {
        this.speedMultiplier = mult;
    }

    public void setInvulnerable(boolean invulnerable) {
        this.invulnerable = invulnerable;
        if (beeEntity != null && beeEntity.isValid()) {
            beeEntity.setInvulnerable(invulnerable);
        }
    }

    public Bee getBee() {
        if (beeEntity != null) {
            if (beeEntity.isDead()) {
                beeEntity = null;
                beeUuid = null;
                return null;
            }
            if (!beeEntity.isValid()) {
                Location l = beeEntity.getLocation();
                if (l != null && l.getWorld() != null) {
                    l.getChunk().load();
                    l.getChunk().setForceLoaded(true);
                }
            }
            if (beeEntity.isValid()) {
                return beeEntity;
            }
        }
        return null;
    }

    public Bee spawnBee(Location loc) {
        despawnBee();
        respawnScheduled = false;
        World w = loc.getWorld();
        if (w == null) return null;

        loc.getChunk().load();
        loc.getChunk().setForceLoaded(true);

        Bee bee = (Bee) w.spawnEntity(loc, EntityType.BEE);
        bee.setAI(false); // Minecraft'ın varsayılan AI'ını kapat, kontrol MaleCNS beyninde
        bee.setCustomName(displayName);
        bee.setCustomNameVisible(true);
        bee.setRemoveWhenFarAway(false);
        bee.setPersistent(true);
        bee.setCanPickupItems(true);
        bee.setInvulnerable(this.invulnerable);
        bee.addScoreboardTag("drosophila_fly");

        if (Compat.MAX_HEALTH != null) {
            AttributeInstance maxHealthAttr = bee.getAttribute(Compat.MAX_HEALTH);
            if (maxHealthAttr != null) {
                maxHealthAttr.setBaseValue(20.0);
            }
        }
        bee.setHealth(20.0);

        this.beeEntity = bee;
        this.beeUuid = bee.getUniqueId();
        this.lastHealth = 20.0;
        this.foodLevel = MAX_FOOD;
        this.lastPosCheck = loc.clone();

        w.playSound(loc, Sound.ENTITY_BEE_POLLINATE, 1.0f, 1.2f);
        Compat.spawnHappyParticle(w, loc.add(0, 0.5, 0), 8, 0.2, 0.2, 0.2, 0.02);

        plugin.getLogger().info("[Drosophila] " + displayName + " spawned at: " + loc.getBlockX() + ", "
                + loc.getBlockY() + ", " + loc.getBlockZ());
        return bee;
    }

    public void despawnBee() {
        if (beeEntity != null) {
            try {
                beeEntity.getLocation().getChunk().setForceLoaded(false);
            } catch (Exception ignored) {}
            if (beeEntity.isValid()) {
                beeEntity.remove();
            }
        }
        beeEntity = null;
        beeUuid = null;
    }

    public void bringToPlayer(Player p) {
        Bee bee = getBee();
        if (bee == null) {
            respawnDefault();
            bee = getBee();
        }
        if (bee != null && p != null) {
            Location target = p.getEyeLocation().add(p.getLocation().getDirection().multiply(1.5));
            Location safeLoc = findNearestFreeSpace(target);
            if (safeLoc == null) safeLoc = p.getLocation().add(0, 1.0, 0);

            safeLoc.getChunk().load();
            safeLoc.getChunk().setForceLoaded(true);
            bee.teleport(safeLoc);
            lastPosCheck = safeLoc.clone();
            p.getWorld().playSound(safeLoc, Sound.ENTITY_BEE_POLLINATE, 1.0f, 1.5f);
            Compat.spawnHappyParticle(p.getWorld(), safeLoc.clone().add(0, 0.4, 0), 10, 0.2, 0.2, 0.2, 0.05);
        }
    }

    private Location customSpawnLocation = null;

    public void setCustomSpawnLocation(Location loc) {
        this.customSpawnLocation = loc;
        if (loc != null && loc.getWorld() != null) {
            plugin.getConfig().set("bee.spawnpoint.world", loc.getWorld().getName());
            plugin.getConfig().set("bee.spawnpoint.x", loc.getX());
            plugin.getConfig().set("bee.spawnpoint.y", loc.getY());
            plugin.getConfig().set("bee.spawnpoint.z", loc.getZ());
            plugin.getConfig().set("bee.spawnpoint.yaw", (double) loc.getYaw());
            plugin.getConfig().set("bee.spawnpoint.pitch", (double) loc.getPitch());
            plugin.saveConfig();
        } else {
            plugin.getConfig().set("bee.spawnpoint", null);
            plugin.saveConfig();
        }
    }

    public Location getCustomSpawnLocation() {
        if (customSpawnLocation == null && plugin.getConfig().contains("bee.spawnpoint.world")) {
            String wName = plugin.getConfig().getString("bee.spawnpoint.world");
            World w = Bukkit.getWorld(wName);
            if (w != null) {
                double x = plugin.getConfig().getDouble("bee.spawnpoint.x");
                double y = plugin.getConfig().getDouble("bee.spawnpoint.y");
                double z = plugin.getConfig().getDouble("bee.spawnpoint.z");
                float yaw = (float) plugin.getConfig().getDouble("bee.spawnpoint.yaw", 0.0);
                float pitch = (float) plugin.getConfig().getDouble("bee.spawnpoint.pitch", 0.0);
                customSpawnLocation = new Location(w, x, y, z, yaw, pitch);
            }
        } else if (customSpawnLocation != null && customSpawnLocation.getWorld() == null) {
            String wName = plugin.getConfig().getString("bee.spawnpoint.world");
            if (wName != null) {
                customSpawnLocation.setWorld(Bukkit.getWorld(wName));
            }
        }
        return customSpawnLocation;
    }

    public boolean isBottled() {
        return isBottled;
    }

    public void setBottled(boolean bottled) {
        this.isBottled = bottled;
    }

    public void scheduleRespawn() {
        if (respawnScheduled || isBottled) return;
        if (!plugin.getConfig().getBoolean("bee.auto-spawn", true)) return;
        respawnScheduled = true;
        plugin.getLogger().info("[Drosophila] " + displayName + " will respawn in 2 seconds...");
        Bukkit.getScheduler().runTaskLater(plugin, this::respawnDefault, 40L);
    }

    public void respawnDefault() {
        respawnScheduled = false;
        Location spawnLoc = null;
        Location custom = getCustomSpawnLocation();
        if (custom != null && custom.getWorld() != null) {
            spawnLoc = custom.clone();
        } else {
            World w = Bukkit.getWorlds().get(0);
            spawnLoc = w.getSpawnLocation().add(0, 1.5, 0);
        }
        Location safe = findNearestFreeSpace(spawnLoc);
        spawnBee(safe != null ? safe : spawnLoc);
    }

    /**
     * Python beyninden gelen motor komutlarını 3D uçuş fiziğine uygular.
     */
    public void applyMotor(MotorCommand cmd) {
        applyMotor(cmd, null);
    }

    public void applyMotor(MotorCommand cmd, OdorDiffusion.OdorSample odor) {
        if (cmd != null && cmd.mood != null) {
            this.lastMood = cmd.mood;
        }
        if (odor != null) {
            this.lastOdor = odor;
        }
        if (beeEntity == null || !beeEntity.isValid() || cmd == null) return;

        Location loc = beeEntity.getLocation();
        float currentYaw = loc.getYaw();
        float currentPitch = loc.getPitch();

        // 1. DÖNÜŞ (DNp20 sol/sağ farkı torku):
        // steering_torque > 0 = SAĞA dönüş (+yaw), < 0 = SOLA dönüş (-yaw)
        float turnScale = cmd.is_escaping ? 8.5f : 4.5f;
        float smoothTurn = cmd.steering_torque * turnScale;
        float newYaw = currentYaw + smoothTurn;

        // 2. EĞİM (Pitch - Yukarı / Aşağı bakış)
        float targetPitch = currentPitch * 0.7f + (cmd.pitch * 35.0f) * 0.3f;
        targetPitch = Math.max(-60.0f, Math.min(60.0f, targetPitch));

        beeEntity.setRotation(newYaw, targetPitch);

        // Metabolik enerji harcaması (Uçuş maliyeti):
        // Havada süzülürken saniyede ~0.04 tokluk harcanır (20 tickte bir 0.04), kaçarken/sprintte 0.08
        // MIN_FOOD (3.0) altına inmez; sinek açlıktan ölmez, sadece yemek arama/dNPF duyarlılığı tavan yapar.
        double burnPerTick = (cmd.sprint || cmd.is_escaping) ? 0.004 : 0.002;
        this.foodLevel = Math.max(MIN_FOOD, this.foodLevel - burnPerTick);

        if (flowerSipCooldown > 0) {
            flowerSipCooldown--;
        }
        if (leafRestCooldown > 0) {
            leafRestCooldown--;
        }

        if (!loc.getChunk().isForceLoaded()) {
            loc.getChunk().load();
            loc.getChunk().setForceLoaded(true);
        }

        Vector moveVec = new Vector(0, 0, 0);

        // Doğal meyve sineği uçuş hızı: saniyede ~1.5 - 2.0 blok (20 Hz pakette 0.09)
        double baseSpeed = 0.09 * speedMultiplier;
        if (odor != null && odor.closestDist <= 5.0f) {
            baseSpeed *= 0.55; // Besine yaklaşırken iniş yavaşlaması (landing deceleration)
        } else if (odor != null && odor.closestDist <= 2.2f) {
            baseSpeed *= 0.35; // Konma ve beslenme yavaşlaması
        }
        if (cmd.sprint || cmd.is_escaping) baseSpeed *= 1.55;

        // 3. 3D UÇUŞ VEKTÖRÜ (Bakış doğrultusuyla birebir hizalı):
        Location lookLoc = loc.clone();
        lookLoc.setYaw(newYaw);
        lookLoc.setPitch(targetPitch);
        Vector fwdDir = lookLoc.getDirection();

        double thrust = Math.max(cmd.forward ? 0.35 : 0.0, cmd.forward_thrust);
        if (cmd.back) {
            // MDN geri çekilme
            Vector backDir = fwdDir.clone().setY(0).normalize().multiply(-baseSpeed * 0.55);
            moveVec.add(backDir);
        } else if (thrust > 0.05) {
            Vector flightDir = fwdDir.clone();
            flightDir.setY(flightDir.getY() * 0.85); // 3D dinamik uçuş ve süzülme
            if (flightDir.lengthSquared() > 0.001) flightDir.normalize();
            moveVec.add(flightDir.multiply(baseSpeed * Math.min(2.0, (0.7 + 0.6 * thrust))));
        }

        // 4. İRTİFA VE SÜZÜLME KONTROLÜ (Doğal Böcek Uçuşu & Besine Alçalış):
        World w = loc.getWorld();
        double distToGround = getDistanceToGround(loc);
        int terrainY = (w != null) ? w.getHighestBlockYAt(loc) : 64;
        double heightAboveTerrain = loc.getY() - terrainY;

        double liftY = 0.0;
        Block curBlock = loc.getBlock();
        Block blockAhead = loc.clone().add(fwdDir.clone().multiply(0.8)).getBlock();
        Block blockBelow = loc.clone().subtract(0, 0.8, 0).getBlock();

        boolean trackingFoodBelow = (odor != null && odor.closestDist <= 12.0f && odor.foodDeltaY < -0.15f);
        boolean trackingFoodAbove = (odor != null && odor.closestDist <= 12.0f && odor.foodDeltaY > 0.20f);

        if (curBlock.isLiquid() || blockBelow.isLiquid()) {
            // Su içinde veya hemen üstünde: acil yukarı yüksel! Kanatlar ıslanmasın!
            liftY += 0.32;
            beeEntity.setRemainingAir(beeEntity.getMaximumAir());
            hurtLastFrame = true; // Suyu tehlike/acı hissetsin
            Compat.spawnSplashParticle(loc.getWorld(), loc.clone().add(0, 0.2, 0), 4, 0.1, 0.1, 0.1, 0.05);
        } else if (blockAhead.isLiquid()) {
            // Tam önü su: dalışı engelle, yukarı kaç
            liftY += 0.22;
        } else if (heightAboveTerrain > 12.0) {
            // Biyolojik İrtifa Limiti: Ağaç ve arazi seviyesinin 12 bloktan fazla üstüne çıktıysa
            // yerçekimi ve hava akımı ile doğal olarak aşağı ekosisteme/zemine süzülür
            double excess = heightAboveTerrain - 12.0;
            liftY -= Math.min(0.35, 0.06 + excess * 0.03);
        } else if (cmd.jump && heightAboveTerrain <= 10.0) {
            // Giant Fiber sıçraması / Ani havalanma (yalnızca yer seviyesinde tehlikeden kaçarken)
            liftY += 0.30;
            loc.getWorld().playSound(loc, Sound.ENTITY_BEE_LOOP, 0.8f, 1.8f);
        } else if (trackingFoodBelow) {
            // Besin arının altında: yerdeki yiyeceğe doğru biyolojik süzülüş ve konma
            double targetY = (odor.foodLoc != null) ? (odor.foodLoc.getY() + 0.35) : (loc.getY() + odor.foodDeltaY + 0.35);
            double diffY = targetY - loc.getY();
            liftY += Math.max(-0.25, Math.min(0.15, diffY * 0.22));
        } else if (trackingFoodAbove) {
            // Besin/yaprak arının üstünde: ağaç tepesine ve yukarıdaki kaynağa doğru tırmanış
            double targetY = (odor.foodLoc != null) ? (odor.foodLoc.getY() + 0.35) : (loc.getY() + odor.foodDeltaY + 0.35);
            double diffY = targetY - loc.getY();
            liftY += Math.min(0.28, Math.max(0.06, diffY * 0.25));
        } else if (distToGround < 1.1 && cmd.pitch <= 0.15 && (odor == null || odor.closestDist > 3.0f)) {
            // Yere çok yakınsa hafif zemin etkisiyle yukarı süzül (ancak yemeğe yaklaşmıyorsa)
            liftY += 0.07;
        } else if (distToGround < 0.20) {
            // Yere tamamen temas ettiyse hafif yüksel (sıkışmayı önle)
            liftY += 0.04;
        } else {
            // Havada asılı kalma (küçük doğal kanat dalgalanması)
            liftY += Math.sin(System.currentTimeMillis() * 0.008) * 0.015;
        }

        moveVec.setY(moveVec.getY() + liftY);

        // 5. 3D EKSEN BAZLI ÇARPIŞMA VE DUVAR KAYMASI (WALL-SLIDING):
        double curX = loc.getX();
        double curY = loc.getY();
        double curZ = loc.getZ();

        double dx = moveVec.getX();
        double dy = moveVec.getY();
        double dz = moveVec.getZ();

        // X ekseni çarpışma testi ve duvar kayması
        if (dx != 0 && isBoxColliding(w, curX + dx, curY, curZ)) {
            dx = 0;
        }
        // Y ekseni çarpışma testi (tavan / zemin)
        if (dy != 0 && isBoxColliding(w, curX + dx, curY + dy, curZ)) {
            dy = 0;
        }
        // Z ekseni çarpışma testi ve duvar kayması
        if (dz != 0 && isBoxColliding(w, curX + dx, curY + dy, curZ + dz)) {
            dz = 0;
        }

        Location nextLoc = new Location(w, curX + dx, curY + dy, curZ + dz, newYaw, targetPitch);

        // Eğer arı bir şekilde katı blok içinde kalmışsa hemen açık alana yönlendir
        if (isBoxColliding(w, nextLoc.getX(), nextLoc.getY(), nextLoc.getZ())) {
            nextLoc = findNearestFreeSpace(nextLoc);
            nextLoc.setYaw(newYaw);
            nextLoc.setPitch(targetPitch);
        }

        beeEntity.teleport(nextLoc);

        // Yerdeki elma veya yiyecekleri otomatik alma ve yeme
        checkAndConsumeFood(beeEntity.getLocation());

        // Beslenme efekti
        if (cmd.eat) {
            loc.getWorld().spawnParticle(Particle.HEART, loc.clone().add(0, 0.35, 0), 3, 0.15, 0.15, 0.15, 0.02);
            beeEntity.setHasNectar(true);
        }

        // Biyolojik Ruh Hali / Duygu Parçacıkları (Dopamin PAM/PPL1 & Kaçış/Tehdit)
        particleTick++;
        if (particleTick % 7 == 0 && w != null) {
            if ("eating".equalsIgnoreCase(cmd.mood)) {
                w.spawnParticle(Particle.HEART, loc.clone().add(0, 0.35, 0), 4, 0.15, 0.15, 0.15, 0.03);
            } else if ("happy".equalsIgnoreCase(cmd.mood)) {
                w.spawnParticle(Particle.HEART, loc.clone().add(0, 0.35, 0), 2, 0.15, 0.15, 0.15, 0.02);
            } else if ("sad".equalsIgnoreCase(cmd.mood)) {
                w.spawnParticle(Particle.FALLING_OBSIDIAN_TEAR, loc.clone().add(0, 0.3, 0), 2, 0.1, 0.1, 0.1, 0.02);
            } else if ("scared".equalsIgnoreCase(cmd.mood)) {
                w.spawnParticle(Particle.SQUID_INK, loc.clone().add(0, 0.3, 0), 2, 0.1, 0.1, 0.1, 0.03);
            }
        }

        // Takılma (stuck) ve Köşeden Kaçış Kontrolü:
        if (lastPosCheck != null) {
            double distMoved = loc.distance(lastPosCheck);
            // Sadece ileri gitmek isterken ilerleyemiyorsa stuck say; geri çekilirken (cmd.back) stuck sayma!
            if (distMoved < 0.04 && cmd.forward && !cmd.back) {
                stuckTicks++;
                // 30 tick (~1.5 sn) boyunca köşeye/duvara takılı kaldıysa:
                // Biyolojik kaçış sekkadi (saccade): Sinek köşeden açık yöne doğru 135° keskin dönüş yapar
                if (stuckTicks > 30) {
                    float escapeTurn = (Math.random() > 0.5 ? +135.0f : -135.0f);
                    Location turnLoc = loc.clone();
                    turnLoc.setYaw(turnLoc.getYaw() + escapeTurn);
                    turnLoc.setPitch(0.0f);
                    beeEntity.teleport(turnLoc);
                    stuckTicks = 0;
                }
            } else if (distMoved > 0.06 || cmd.back) {
                stuckTicks = Math.max(0, stuckTicks - 3);
            }
        }
        lastPosCheck = loc.clone();
    }

    public boolean isBoxColliding(World w, double x, double y, double z) {
        if (w == null) return false;
        double r = 0.28;
        double minY = y + 0.05;
        double maxY = y + 0.55;

        int minBx = (int) Math.floor(x - r);
        int maxBx = (int) Math.floor(x + r);
        int minBy = (int) Math.floor(minY);
        int maxBy = (int) Math.floor(maxY);
        int minBz = (int) Math.floor(z - r);
        int maxBz = (int) Math.floor(z + r);

        for (int bx = minBx; bx <= maxBx; bx++) {
            for (int by = minBy; by <= maxBy; by++) {
                for (int bz = minBz; bz <= maxBz; bz++) {
                    Block b = w.getBlockAt(bx, by, bz);
                    if (b.getType().isSolid()) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    public Location findNearestFreeSpace(Location loc) {
        World w = loc.getWorld();
        if (w == null) return loc;
        if (!isBoxColliding(w, loc.getX(), loc.getY(), loc.getZ())) {
            return loc;
        }
        double[][] offsets = {
            {0, 0.6, 0}, {0, 1.0, 0}, {0, 1.5, 0}, {0, -0.6, 0},
            {0.5, 0, 0}, {-0.5, 0, 0},
            {0, 0, 0.5}, {0, 0, -0.5},
            {0.5, 0.5, 0}, {-0.5, 0.5, 0},
            {0.5, 1.0, 0}, {-0.5, 1.0, 0},
            {0, 0.5, 0.5}, {0, 0.5, -0.5},
            {0, 1.0, 0.5}, {0, 1.0, -0.5}
        };
        for (double[] off : offsets) {
            double nx = loc.getX() + off[0];
            double ny = loc.getY() + off[1];
            double nz = loc.getZ() + off[2];
            if (!isBoxColliding(w, nx, ny, nz)) {
                return new Location(w, nx, ny, nz, loc.getYaw(), loc.getPitch());
            }
        }
        return loc;
    }

    private double getDistanceToGround(Location loc) {
        World w = loc.getWorld();
        if (w == null) return 2.0;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();

        for (int y = by; y >= Math.max(w.getMinHeight(), by - 8); y--) {
            Block b = w.getBlockAt(bx, y, bz);
            if (b.getType().isSolid() || b.isLiquid()) {
                return (loc.getY() - (y + 1.0));
            }
        }
        return 8.0;
    }

    public boolean wasHurt() {
        boolean h = hurtLastFrame;
        hurtLastFrame = false;
        return h;
    }

    public double getHealth() {
        if (beeEntity != null && beeEntity.isValid()) {
            return beeEntity.getHealth();
        }
        return 20.0;
    }

    public int getStuckTicks() {
        return stuckTicks;
    }

    public void healBee(double amount) {
        if (beeEntity == null || !beeEntity.isValid()) return;
        double maxHealth = 20.0;
        if (Compat.MAX_HEALTH != null) {
            AttributeInstance attr = beeEntity.getAttribute(Compat.MAX_HEALTH);
            if (attr != null) {
                maxHealth = attr.getValue();
            }
        }
        double current = beeEntity.getHealth();
        beeEntity.setHealth(Math.min(maxHealth, Math.max(0.0, current + amount)));
    }

    @EventHandler
    public void onDamage(EntityDamageEvent event) {
        if (beeEntity != null && event.getEntity().getUniqueId().equals(beeUuid)) {
            EntityDamageEvent.DamageCause cause = event.getCause();

            // Minecraft motorunun fiziksel boğulma, sıkışma, tavan veya duvar içi hasarlarını iptal et
            if (cause == EntityDamageEvent.DamageCause.SUFFOCATION
                    || cause == EntityDamageEvent.DamageCause.DROWNING
                    || cause == EntityDamageEvent.DamageCause.FALL
                    || cause == EntityDamageEvent.DamageCause.CRAMMING
                    || cause == EntityDamageEvent.DamageCause.FLY_INTO_WALL) {
                event.setCancelled(true);

                if (cause == EntityDamageEvent.DamageCause.SUFFOCATION || cause == EntityDamageEvent.DamageCause.DROWNING) {
                    Location free = findNearestFreeSpace(beeEntity.getLocation());
                    if (free != null) {
                        if (cause == EntityDamageEvent.DamageCause.DROWNING) {
                            free.setY(free.getY() + 0.6);
                        }
                        beeEntity.teleport(free);
                    }
                    beeEntity.setRemainingAir(beeEntity.getMaximumAir());
                }
                return;
            }

            // Biyolojik hasarlar (Ateş, lav, oyuncu/canavar saldırısı):
            hurtLastFrame = true;
            Location l = beeEntity.getLocation();
            l.getWorld().playSound(l, Sound.ENTITY_BEE_HURT, 1.0f, 1.2f);
            l.getWorld().spawnParticle(Particle.DAMAGE_INDICATOR, l, 5, 0.1, 0.1, 0.1, 0.05);
        }
    }

    @EventHandler
    public void onDeath(EntityDeathEvent event) {
        if (beeEntity != null && event.getEntity().getUniqueId().equals(beeUuid)) {
            beeEntity = null;
            beeUuid = null;
            scheduleRespawn();
        }
    }

    private void checkAndConsumeFood(Location loc) {
        if (beeEntity == null || !beeEntity.isValid()) return;
        World w = beeEntity.getWorld();
        if (w == null) return;

        // 1. YERDEKİ MEYVELER VE BESİNLER (Elma, karpuz vs. - Tam Tokluk & Can Yenilenmesi)
        Collection<Entity> nearby = beeEntity.getNearbyEntities(2.5, 2.5, 2.5);
        for (Entity e : nearby) {
            if (e instanceof Item) {
                Item item = (Item) e;
                ItemStack stack = item.getItemStack();
                if (OdorDiffusion.isAttractiveFood(stack.getType())) {
                    plugin.getLogger().info("[Drosophila] " + displayName + " consumed food: " + stack.getType().name() + " (Health +4, Full Food)");
                    w.playSound(loc, Sound.ENTITY_GENERIC_EAT, 1.0f, 1.2f);
                    w.playSound(loc, Sound.ENTITY_PLAYER_BURP, 0.8f, 1.3f);
                    w.spawnParticle(Particle.HEART, loc.clone().add(0, 0.4, 0), 8, 0.25, 0.25, 0.25, 0.05);

                    healBee(4.0);
                    this.foodLevel = MAX_FOOD; // Yemeği yedi, karnı tamamen doydu (20.0)
                    beeEntity.setHasNectar(true);

                    if (stack.getAmount() > 1) {
                        stack.setAmount(stack.getAmount() - 1);
                        item.setItemStack(stack);
                    } else {
                        item.remove();
                    }
                    return; // Elma yendiyse yaprak veya çiçek kontrolüne gerek yok
                }
            }
        }

        // 2. AĞAÇ YAPRAKLARINDA DİNLENME (Leaf Resting & Canopy Micro-Foraging):
        // Sinek ağaç yapraklarına konduğunda dinlenir ve küçük bir tokluk desteği alır.
        // Tokluk 15.0'e ulaştığında tokluk kapısı devreye girer ve sinek ağaçtan açık havaya uçar.
        if (leafRestCooldown <= 0 && foodLevel < 15.0) {
            int bx = loc.getBlockX();
            int by = loc.getBlockY();
            int bz = loc.getBlockZ();
            boolean foundLeaf = false;
            leafLoop:
            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dz = -1; dz <= 1; dz++) {
                        Material mat = w.getBlockAt(bx + dx, by + dy, bz + dz).getType();
                        if (OdorDiffusion.isLeafBlock(mat)) {
                            foundLeaf = true;
                            break leafLoop;
                        }
                    }
                }
            }
            if (foundLeaf) {
                leafRestCooldown = 80; // 4 saniyede bir hafif dinlenme
                this.foodLevel = Math.min(16.0, this.foodLevel + 0.6); // Hafif tokluk desteği
                healBee(0.5);
                Compat.spawnHappyParticle(w, loc.clone().add(0, 0.2, 0), 2, 0.15, 0.15, 0.15, 0.02);
            }
        }

        // 3. ÇİÇEK NEKTARI (Sadece çok açken acil hayatta kalma yudumu: foodLevel < 10.0):
        // Drosophila meyve sineğidir; karnını çiçekle tıka basa doyuramaz, sadece hayatta kalma yudumu alır.
        if (flowerSipCooldown <= 0 && foodLevel < 10.0) {
            boolean foundFlower = false;
            int bx = loc.getBlockX();
            int by = loc.getBlockY();
            int bz = loc.getBlockZ();
            flowerLoop:
            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 0; dy++) {
                    for (int dz = -1; dz <= 1; dz++) {
                        Material mat = w.getBlockAt(bx + dx, by + dy, bz + dz).getType();
                        if (OdorDiffusion.isFlowerOrNectar(mat)) {
                            foundFlower = true;
                            break flowerLoop;
                        }
                    }
                }
            }
            if (foundFlower) {
                flowerSipCooldown = 80; // 4 saniyede bir küçük yudum
                this.foodLevel = Math.min(12.0, this.foodLevel + 0.8); // Sadece hayatta kalma seviyesine kadar
                healBee(0.5);
                beeEntity.setHasNectar(true);
                w.playSound(loc, Sound.ENTITY_BEE_POLLINATE, 0.5f, 1.6f);
                Compat.spawnHappyParticle(w, loc.clone().add(0, 0.25, 0), 2, 0.15, 0.15, 0.15, 0.03);
            }
        }
    }

    public double getFoodLevel() {
        return foodLevel;
    }

    public void setFoodLevel(double level) {
        this.foodLevel = Math.max(MIN_FOOD, Math.min(MAX_FOOD, level));
    }

    public String getLastMood() {
        return lastMood != null ? lastMood : "neutral";
    }

    public OdorDiffusion.OdorSample getLastOdor() {
        return lastOdor;
    }

    public boolean isObstacleAhead() {
        if (beeEntity == null || !beeEntity.isValid()) return false;
        Location l = beeEntity.getEyeLocation();
        Vector dir = l.getDirection().clone().setY(0);
        if (dir.lengthSquared() < 0.001) return false;
        dir.normalize().multiply(0.85);
        Block b = l.clone().add(dir).getBlock();
        return b.getType().isSolid();
    }
}
