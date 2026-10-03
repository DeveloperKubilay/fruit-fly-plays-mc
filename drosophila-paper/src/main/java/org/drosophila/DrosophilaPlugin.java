package org.drosophila;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Bee;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.util.Vector;
import org.drosophila.auditory.AuditoryWindSampler;
import org.drosophila.auditory.AuditoryWindSampler.AuditorySample;
import org.drosophila.controller.BeeController;
import org.drosophila.i18n.LanguageManager;
import org.drosophila.network.BrainServer;
import org.drosophila.olfaction.OdorDiffusion;
import org.drosophila.olfaction.OdorDiffusion.OdorSample;
import org.drosophila.vision.CompoundEyeRaytracer;
import org.drosophila.vision.CompoundEyeRaytracer.RaycastResult;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Locale;

/**
 * DrosophilaAna Eklenti Sınıfı.
 * MaleCNS v1.0 Biyolojik Konektomunu Minecraft'ta 3D uçan bir Meyve Sineği olarak simüle eder.
 */
public class DrosophilaPlugin extends JavaPlugin implements CommandExecutor, TabCompleter {

    private BeeController beeController;
    private CompoundEyeRaytracer raytracer;
    private OdorDiffusion odorDiffusion;
    private AuditoryWindSampler auditorySampler;
    private BrainServer brainServer;
    private org.drosophila.item.BottleManager bottleManager;
    private LanguageManager languageManager;

    private BukkitTask tickTask;

    public LanguageManager getLanguageManager() {
        return languageManager;
    }

    @Override
    public void onEnable() {
        saveDefaultConfig();

        // 1. Çoklu Dil Yöneticisini Başlat (config: 'language', varsayılan: 'en')
        this.languageManager = new LanguageManager(this);
        String lang = getConfig().getString("language", "en");
        this.languageManager.init(lang);

        this.raytracer = new CompoundEyeRaytracer();
        this.odorDiffusion = new OdorDiffusion();
        this.auditorySampler = new AuditoryWindSampler();
        this.beeController = new BeeController(this);

        loadConfiguration();

        int port = getConfig().getInt("brain.port", 8765);
        this.brainServer = new BrainServer(port, beeController, getLogger());
        this.brainServer.setAuthToken(getConfig().getString("brain.auth-token", "drosophila_secret_token_123"));
        this.brainServer.setLanguage(this.languageManager.getCurrentLang());
        this.brainServer.start();

        this.bottleManager = new org.drosophila.item.BottleManager(this, beeController, brainServer);

        String[] cmdList = {"fruitfly"};
        for (String c : cmdList) {
            org.bukkit.command.PluginCommand pc = getCommand(c);
            if (pc != null) {
                pc.setExecutor(this);
                pc.setTabCompleter(this);
            }
        }

        // Ana Tick Döngüsü: Her Minecraft tick'inde (20 Hz = 50 ms) çalışır
        this.tickTask = Bukkit.getScheduler().runTaskTimer(this, this::onTick, 20L, 1L);

        // Sunucu açıldığında sineği otomatik oluştur (bee.auto-spawn ayarı)
        boolean autoSpawn = getConfig().getBoolean("bee.auto-spawn", true);
        if (autoSpawn) {
            Bukkit.getScheduler().runTaskLater(this, () -> {
                if (beeController.getBee() == null) {
                    beeController.respawnDefault();
                }
            }, 30L);
        }

        getLogger().info("=================================================");
        getLogger().info("🪰 FruitFly (MaleCNS v1.0) enabled!");
        getLogger().info("Language: " + languageManager.getCurrentLang());
        getLogger().info("Commands: /fruitfly tp | /fruitfly come | /fruitfly status");
        getLogger().info("=================================================");
    }

    @Override
    public void onDisable() {
        if (tickTask != null) {
            tickTask.cancel();
        }
        if (brainServer != null) {
            try {
                brainServer.stop(1000);
            } catch (InterruptedException e) {
                getLogger().warning("BrainServer interrupted while stopping: " + e.getMessage());
            }
        }
        if (beeController != null) {
            beeController.despawnBee();
        }
        getLogger().info("FruitFly plugin disabled.");
    }

    private void loadConfiguration() {
        if (beeController != null) {
            String customName = getConfig().getString("bee.display-name", "");
            if (customName != null && !customName.trim().isEmpty()) {
                beeController.setDisplayName(org.bukkit.ChatColor.translateAlternateColorCodes('&', customName));
            } else {
                beeController.setDisplayName(languageManager.get("entity.name"));
            }
            beeController.setSpeedMultiplier(getConfig().getDouble("bee.speed-multiplier", 1.0));
            beeController.setInvulnerable(getConfig().getBoolean("bee.invulnerable", false));
            if (getConfig().contains("bee.spawnpoint.world")) {
                String wName = getConfig().getString("bee.spawnpoint.world");
                World w = Bukkit.getWorld(wName);
                if (w != null) {
                    double x = getConfig().getDouble("bee.spawnpoint.x");
                    double y = getConfig().getDouble("bee.spawnpoint.y");
                    double z = getConfig().getDouble("bee.spawnpoint.z");
                    float yaw = (float) getConfig().getDouble("bee.spawnpoint.yaw", 0.0);
                    float pitch = (float) getConfig().getDouble("bee.spawnpoint.pitch", 0.0);
                    beeController.setCustomSpawnLocation(new Location(w, x, y, z, yaw, pitch));
                }
            }
        }
    }

    private int tickCount = 0;

    private void onTick() {
        tickCount++;

        // 1. Sinek Beden ve Duyu Döngüsü
        if (beeController.isBottled()) {
            return; // Sinek şişede dinleniyor (0 CPU)
        }
        Bee bee = beeController.getBee();
        if (bee == null || !bee.isValid()) {
            boolean autoSpawn = getConfig().getBoolean("bee.auto-spawn", true);
            if (autoSpawn) {
                beeController.scheduleRespawn();
            }
            return;
        }

        // A. Çoklu Duyu Toplama (Petek Göz, Koku, İşitme/Rüzgâr, Termo, Tat)
        RaycastResult vision = raytracer.trace(bee);
        OdorSample odor = odorDiffusion.sample(bee, beeController.getFoodLevel());
        AuditorySample auditory = auditorySampler.sample(bee);

        double health = beeController.getHealth();
        double heading = bee.getLocation().getYaw();
        boolean hurt = beeController.wasHurt();
        int stuck = beeController.getStuckTicks();
        boolean blocked = beeController.isObstacleAhead();

        // B. Akıllı Dinlenme (Smart Sleep) Kontrolü
        boolean smartSleepEnabled = getConfig().getBoolean("brain.smart-sleep.enabled", false);
        double maxPlayerDist = getConfig().getDouble("brain.smart-sleep.player-distance", 48.0);
        boolean isSleeping = false;
        if (smartSleepEnabled) {
            boolean playerNearby = false;
            for (Player p : bee.getWorld().getPlayers()) {
                if (p.getLocation().distanceSquared(bee.getLocation()) <= maxPlayerDist * maxPlayerDist) {
                    playerNearby = true;
                    break;
                }
            }
            // 4 Güvenlik Kuralı: Oyuncu 48m yakındaysa, tehdit/canavar varsa, ses varsa veya can azsa ASLA UYUMAZ
            if (!playerNearby && auditory.soundLevel < 0.05f && vision.threatDist > 16.0 && health >= 19.0) {
                isSleeping = true;
            }
        }

        // C. Python Beynine Duyu Çerçevesini Gönder
        brainServer.sendSensoryData(vision, odor, auditory, health, heading, hurt, stuck, blocked, isSleeping);

        // D. Python'dan Gelen Motor Komutunu Uygula
        beeController.applyMotor(brainServer.getLastCommand(), odor);
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String cmdName = label.toLowerCase();

        // Yetki kontrolü (OP veya drosophila.admin izni)
        if (!sender.hasPermission("drosophila.admin") && !sender.isOp()) {
            sender.sendMessage(languageManager.get("commands.no_permission"));
            return true;
        }

        if (args.length == 0 || args[0].equalsIgnoreCase("help")) {
            sender.sendMessage(languageManager.get("commands.help.header"));
            sender.sendMessage(languageManager.get("commands.help.tp", cmdName));
            sender.sendMessage(languageManager.get("commands.help.come", cmdName));
            sender.sendMessage(languageManager.get("commands.help.feed", cmdName));
            sender.sendMessage(languageManager.get("commands.help.hungry", cmdName));
            sender.sendMessage(languageManager.get("commands.help.food", cmdName));
            sender.sendMessage(languageManager.get("commands.help.spawnpoint", cmdName));
            sender.sendMessage(languageManager.get("commands.help.home", cmdName));
            sender.sendMessage(languageManager.get("commands.help.status", cmdName));
            sender.sendMessage(languageManager.get("commands.help.clear", cmdName));
            sender.sendMessage(languageManager.get("commands.help.reload", cmdName));
            return true;
        }

        String sub = args[0].toLowerCase();

        if (sub.equals("reload")) {
            reloadConfig();
            String newLang = getConfig().getString("language", "en");
            languageManager.init(newLang);
            if (brainServer != null) {
                brainServer.setAuthToken(getConfig().getString("brain.auth-token", "drosophila_secret_token_123"));
                brainServer.setLanguage(languageManager.getCurrentLang());
            }
            loadConfiguration();
            sender.sendMessage(languageManager.get("commands.reload.success"));
            return true;
        }

        if (sub.equals("hungry") || sub.equals("starve") || sub.equals("aciktir")) {
            beeController.setFoodLevel(BeeController.MIN_FOOD);
            Bee b = beeController.getBee();
            if (b != null) {
                b.getWorld().spawnParticle(org.bukkit.Particle.FALLING_OBSIDIAN_TEAR, b.getLocation().add(0, 0.35, 0), 6, 0.1, 0.1, 0.1, 0.02);
            }
            sender.sendMessage(languageManager.get("commands.hungry.success"));
            return true;
        }

        if (sub.equals("food") || sub.equals("hunger") || sub.equals("tokluk")) {
            if (args.length > 1) {
                try {
                    double val = Double.parseDouble(args[1]);
                    beeController.setFoodLevel(val);
                    sender.sendMessage(languageManager.get("commands.food.set", String.format(Locale.US, "%.1f", beeController.getFoodLevel())));
                } catch (NumberFormatException e) {
                    sender.sendMessage(languageManager.get("commands.food.invalid", cmdName));
                }
            } else {
                double f = beeController.getFoodLevel();
                String state = (f >= 15.0) ? languageManager.get("status.satiety.satiated")
                        : (f >= 8.0) ? languageManager.get("status.satiety.normal")
                        : languageManager.get("status.satiety.hungry");
                sender.sendMessage(languageManager.get("commands.food.status", String.format(Locale.US, "%.1f", f), state));
            }
            return true;
        }

        if (sub.equals("feed") || sub.equals("drop") || sub.equals("apple") || sub.equals("elma")) {
            if (args.length > 1 && (args[1].equalsIgnoreCase("full") || args[1].equalsIgnoreCase("now") || args[1].equalsIgnoreCase("doyur"))) {
                beeController.setFoodLevel(BeeController.MAX_FOOD);
                beeController.healBee(6.0);
                Bee b = beeController.getBee();
                if (b != null) {
                    b.getWorld().spawnParticle(org.bukkit.Particle.HEART, b.getLocation().add(0, 0.4, 0), 10, 0.25, 0.25, 0.25, 0.05);
                    b.getWorld().playSound(b.getLocation(), org.bukkit.Sound.ENTITY_GENERIC_EAT, 1.0f, 1.2f);
                }
                sender.sendMessage(languageManager.get("commands.feed.instantly_fed"));
                return true;
            }
            Bee b = beeController.getBee();
            if (b == null) {
                sender.sendMessage(languageManager.get("commands.fly_not_found"));
                return true;
            }
            Location bl = b.getLocation();
            Vector fwd = bl.getDirection().setY(0).normalize();
            if (fwd.lengthSquared() < 0.001) fwd = new Vector(0, 0, 1);
            Location dropLoc = bl.clone().add(fwd.multiply(2.5));
            int highestY = dropLoc.getWorld().getHighestBlockYAt(dropLoc);
            dropLoc.setY(highestY + 0.5);
            Item item = dropLoc.getWorld().dropItem(dropLoc, new org.bukkit.inventory.ItemStack(Material.APPLE));
            item.setVelocity(new Vector(0, 0.1, 0));
            sender.sendMessage(languageManager.get("commands.feed.apple_dropped", dropLoc.getBlockX(), dropLoc.getBlockY(), dropLoc.getBlockZ()));
            return true;
        }

        if (sub.equals("clear") || sub.equals("reset") || sub.equals("sifirla")) {
            boolean ok = brainServer.sendResetCommand(brainServer.getFlyId());
            if (ok) {
                sender.sendMessage(languageManager.get("commands.clear.success"));
            } else {
                sender.sendMessage(languageManager.get("commands.clear.not_connected"));
            }
            return true;
        }

        if (sub.equals("tp")) {
            Bee b = beeController.getBee();
            if (b == null) {
                beeController.respawnDefault();
                b = beeController.getBee();
            }
            if (sender instanceof Player) {
                if (b != null) {
                    ((Player) sender).teleport(b.getLocation());
                    sender.sendMessage(languageManager.get("commands.tp.success"));
                } else {
                    sender.sendMessage(languageManager.get("commands.fly_spawning"));
                }
            } else {
                if (b != null) {
                    Location l = b.getLocation();
                    sender.sendMessage(languageManager.get("commands.tp.console_loc", l.getBlockX(), l.getBlockY(), l.getBlockZ()));
                } else {
                    sender.sendMessage(languageManager.get("status.spawning"));
                }
            }
            return true;
        }

        if (sub.equals("come") || sub.equals("bring") || sub.equals("cagir")) {
            if (!(sender instanceof Player)) {
                sender.sendMessage(languageManager.get("commands.player_only"));
                return true;
            }
            Player p = (Player) sender;
            beeController.bringToPlayer(p);
            p.sendMessage(languageManager.get("commands.come.success"));
            return true;
        }

        if (sub.equals("spawnpoint") || sub.equals("setspawn")) {
            if (!(sender instanceof Player)) {
                sender.sendMessage(languageManager.get("commands.player_only"));
                return true;
            }
            Player p = (Player) sender;
            if (args.length > 1 && (args[1].equalsIgnoreCase("clear") || args[1].equalsIgnoreCase("remove") || args[1].equalsIgnoreCase("reset"))) {
                beeController.setCustomSpawnLocation(null);
                p.sendMessage(languageManager.get("commands.spawnpoint.reset"));
                return true;
            }
            Location loc = p.getLocation().add(0, 1.0, 0);
            beeController.setCustomSpawnLocation(loc);
            p.sendMessage(languageManager.get("commands.spawnpoint.set", loc.getBlockX(), loc.getBlockY(), loc.getBlockZ()));
            return true;
        }

        if (sub.equals("home") || sub.equals("ev")) {
            Location home = beeController.getCustomSpawnLocation();
            if (home == null) home = Bukkit.getWorlds().get(0).getSpawnLocation().add(0, 1.5, 0);
            Bee b = beeController.getBee();
            if (b != null) {
                b.teleport(home);
                sender.sendMessage(languageManager.get("commands.home.sent"));
            } else {
                beeController.respawnDefault();
                sender.sendMessage(languageManager.get("commands.home.spawned"));
            }
            return true;
        }

        if (sub.equals("status") || sub.equals("durum") || sub.equals("info")) {
            Bee b = beeController.getBee();
            sender.sendMessage(languageManager.get("status.header"));

            // 1. Brain & Connection
            boolean connected = brainServer.isConnected();
            sender.sendMessage(connected ? languageManager.get("status.brain_connected") : languageManager.get("status.brain_disconnected"));

            if (b != null && b.isValid()) {
                Location l = b.getLocation();

                // 2. Mood
                String mood = beeController.getLastMood();
                String moodKey = "status.mood." + (mood != null ? mood.toLowerCase() : "neutral");
                String moodStr = languageManager.get(moodKey);
                sender.sendMessage(languageManager.get("status.mood_title") + moodStr);

                // 3. Health & Satiety
                double health = b.getHealth();
                double food = beeController.getFoodLevel();
                String hungerState = (food >= 15.0) ? languageManager.get("status.satiety.satiated")
                        : (food >= 8.0) ? languageManager.get("status.satiety.normal")
                        : languageManager.get("status.satiety.hungry");
                sender.sendMessage(languageManager.get("status.stats_line",
                        String.format(Locale.US, "%.1f", health),
                        String.format(Locale.US, "%.1f", food),
                        hungerState));

                // 4. Location & Heading
                float yaw = (l.getYaw() % 360 + 360) % 360;
                sender.sendMessage(languageManager.get("status.location",
                        l.getBlockX(), l.getBlockY(), l.getBlockZ(),
                        String.format(Locale.US, "%.0f", yaw),
                        String.format(Locale.US, "%.0f", l.getPitch())));

                // 5. Environmental Odor
                OdorDiffusion.OdorSample odor = beeController.getLastOdor();
                if (odor != null && odor.foodName != null && !odor.foodName.isEmpty() && odor.closestDist < 16.0) {
                    sender.sendMessage(languageManager.get("status.odor_source",
                            odor.foodName,
                            String.format(Locale.US, "%.1f", odor.closestDist),
                            String.format(Locale.US, "%.2f", odor.odorLeft),
                            String.format(Locale.US, "%.2f", odor.odorRight)));
                } else {
                    sender.sendMessage(languageManager.get("status.odor_none"));
                }

                // 6. Surroundings scan
                Collection<Entity> nearbyEntities = l.getWorld().getNearbyEntities(l, 12.0, 6.0, 12.0);
                int itemCount = 0;
                int playerCount = 0;
                Entity closestThreat = null;
                double minThreatDist = 99.0;

                for (Entity e : nearbyEntities) {
                    if (e.equals(b)) continue;
                    if (e instanceof Item) {
                        itemCount++;
                    } else if (e instanceof Player) {
                        playerCount++;
                    } else if (e instanceof org.bukkit.entity.Monster) {
                        double d = l.distance(e.getLocation());
                        if (d < minThreatDist) {
                            minThreatDist = d;
                            closestThreat = e;
                        }
                    }
                }
                String threatText = (closestThreat != null)
                        ? languageManager.get("status.threat.detected", closestThreat.getType().name(), String.format(Locale.US, "%.1f", minThreatDist))
                        : languageManager.get("status.threat.none");
                sender.sendMessage(languageManager.get("status.scan", itemCount, playerCount, threatText));

                // 7. Spawnpoint / Home
                Location home = beeController.getCustomSpawnLocation();
                if (home != null) {
                    sender.sendMessage(languageManager.get("status.home_set", home.getBlockX(), home.getBlockY(), home.getBlockZ()));
                } else {
                    sender.sendMessage(languageManager.get("status.home_none"));
                }
            } else {
                sender.sendMessage(languageManager.get("status.spawning"));
            }
            sender.sendMessage(languageManager.get("status.footer"));
            return true;
        }

        sender.sendMessage(languageManager.get("commands.unknown", cmdName));
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        List<String> list = new ArrayList<>();
        if (args.length == 1) {
            List<String> subcommands = Arrays.asList(
                    "tp", "come", "feed", "hungry", "food", "clear", "spawnpoint", "home", "status", "reload", "help"
            );
            String input = args[0].toLowerCase();
            for (String sub : subcommands) {
                if (sub.startsWith(input)) {
                    list.add(sub);
                }
            }
            return list;
        } else if (args.length == 2) {
            String sub = args[0].toLowerCase();
            String input = args[1].toLowerCase();
            if (sub.equals("feed")) {
                if ("full".startsWith(input)) list.add("full");
            } else if (sub.equals("food")) {
                list.add("3");
                list.add("10");
                list.add("20");
            } else if (sub.equals("spawnpoint") || sub.equals("setspawn")) {
                if ("clear".startsWith(input)) list.add("clear");
            }
            return list;
        }
        return list;
    }
}
