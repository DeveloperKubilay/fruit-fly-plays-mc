package org.drosophila.item;

import org.bukkit.*;
import org.bukkit.entity.Bee;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.drosophila.DrosophilaPlugin;
import org.drosophila.controller.BeeController;
import org.drosophila.network.BrainServer;

/**
 * Şişede Sinek ("Fly in a Bottle") Yöneticisi.
 * Oyuncu boş bir cam şişeyle sineğe sağ tıkladığında sineği güvenle şişeye alır;
 * Python beynine uyku/dondurma sinyali gönderir (0 CPU).
 * Şişe yere sağ tıklandığında sinek uyanır ve yaşamaya devam eder.
 */
public class BottleManager implements Listener {

    private final DrosophilaPlugin plugin;
    private final BeeController beeController;
    private final BrainServer brainServer;
    private final NamespacedKey bottleKey;

    public BottleManager(DrosophilaPlugin plugin, BeeController beeController, BrainServer brainServer) {
        this.plugin = plugin;
        this.beeController = beeController;
        this.brainServer = brainServer;
        this.bottleKey = new NamespacedKey(plugin, "bottled_fly");
        Bukkit.getPluginManager().registerEvents(this, plugin);
    }

    public ItemStack createBottledFlyItem(String flyName) {
        ItemStack item = new ItemStack(Material.POTION);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(plugin.getLanguageManager().get("bottle.item_name", flyName));
            meta.setLore(plugin.getLanguageManager().getList("bottle.lore"));
            meta.getPersistentDataContainer().set(bottleKey, PersistentDataType.STRING, flyName != null ? flyName : "fly");
            item.setItemMeta(meta);
        }
        return item;
    }

    public boolean isBottledFly(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return false;
        ItemMeta meta = item.getItemMeta();
        if (meta == null) return false;
        if (meta.getPersistentDataContainer().has(bottleKey, PersistentDataType.STRING)) {
            return true;
        }
        // Geriye dönük uyumluluk: eski isim kontrolü
        return meta.hasDisplayName() && (
                meta.getDisplayName().contains("Bottled Fruit Fly") ||
                meta.getDisplayName().contains("Şişede Meyve Sineği")
        );
    }

    @EventHandler
    public void onCapture(PlayerInteractEntityEvent event) {
        if (event.getHand() != EquipmentSlot.HAND) return;
        if (!(event.getRightClicked() instanceof Bee)) return;

        Bee bee = (Bee) event.getRightClicked();
        if (beeController.getBee() == null || !bee.getUniqueId().equals(beeController.getBee().getUniqueId())) {
            return;
        }

        Player player = event.getPlayer();
        ItemStack hand = player.getInventory().getItemInMainHand();

        if (hand.getType() == Material.GLASS_BOTTLE) {
            event.setCancelled(true);

            // Şişeleme işlemi
            beeController.setBottled(true);
            Location loc = bee.getLocation();
            beeController.despawnBee();

            // Efekt ve ses
            loc.getWorld().playSound(loc, Sound.ITEM_BOTTLE_FILL, 1.0f, 1.2f);
            loc.getWorld().spawnParticle(Particle.HAPPY_VILLAGER, loc.clone().add(0, 0.4, 0), 10, 0.2, 0.2, 0.2, 0.05);

            // Eşyayı al ve şişeli sineği ver
            if (hand.getAmount() > 1) {
                hand.setAmount(hand.getAmount() - 1);
            } else {
                player.getInventory().setItemInMainHand(new ItemStack(Material.AIR));
            }

            ItemStack bottled = createBottledFlyItem(brainServer.getFlyId());
            if (player.getInventory().firstEmpty() == -1) {
                player.getWorld().dropItemNaturally(player.getLocation(), bottled);
            } else {
                player.getInventory().addItem(bottled);
            }

            // Python beynine dondurma sinyali
            brainServer.sendBottleCommand(true);

            player.sendMessage(plugin.getLanguageManager().get("bottle.captured"));
            plugin.getLogger().info("[Drosophila] Fly captured into bottle, simulation put to sleep.");
        }
    }

    @EventHandler
    public void onRelease(PlayerInteractEvent event) {
        if (event.getHand() != EquipmentSlot.HAND) return;
        if (event.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        if (event.getClickedBlock() == null) return;

        Player player = event.getPlayer();
        ItemStack hand = player.getInventory().getItemInMainHand();

        if (isBottledFly(hand)) {
            event.setCancelled(true);

            Location spawnLoc = event.getClickedBlock().getLocation()
                    .add(event.getBlockFace().getDirection())
                    .add(0.5, 0.2, 0.5);

            beeController.setBottled(false);
            Bee released = beeController.spawnBee(spawnLoc);

            if (released != null) {
                spawnLoc.getWorld().playSound(spawnLoc, Sound.ITEM_BOTTLE_EMPTY, 1.0f, 1.2f);
                spawnLoc.getWorld().playSound(spawnLoc, Sound.ENTITY_BEE_POLLINATE, 1.0f, 1.4f);
                spawnLoc.getWorld().spawnParticle(Particle.HAPPY_VILLAGER, spawnLoc.clone().add(0, 0.4, 0), 12, 0.2, 0.2, 0.2, 0.05);

                // Şişeli eşyayı eksilt, boş şişe ver
                if (hand.getAmount() > 1) {
                    hand.setAmount(hand.getAmount() - 1);
                } else {
                    player.getInventory().setItemInMainHand(new ItemStack(Material.AIR));
                }
                player.getInventory().addItem(new ItemStack(Material.GLASS_BOTTLE));

                // Python beynine uyandırma sinyali
                brainServer.sendBottleCommand(false);

                player.sendMessage(plugin.getLanguageManager().get("bottle.released"));
                plugin.getLogger().info("[Drosophila] Fly released from bottle, simulation resumed.");
            }
        }
    }
}
