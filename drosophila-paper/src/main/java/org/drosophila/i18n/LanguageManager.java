package org.drosophila.i18n;

import org.bukkit.ChatColor;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;
import org.drosophila.DrosophilaPlugin;

import java.io.File;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.List;

/**
 * Drosophila Çoklu Dil (i18n) Yöneticisi.
 * Varsayılan dil: İngilizce ("en").
 * Türkçe ("tr") ve sonradan languages/ klasörüne eklenebilecek tüm özel dilleri destekler.
 */
public class LanguageManager {

    private final DrosophilaPlugin plugin;
    private FileConfiguration langConfig;
    private FileConfiguration fallbackConfig;
    private String currentLang = "en";

    public LanguageManager(DrosophilaPlugin plugin) {
        this.plugin = plugin;
    }

    public void init(String langCode) {
        if (langCode == null || langCode.trim().isEmpty()) {
            langCode = "en";
        }
        this.currentLang = langCode.trim().toLowerCase();

        // 1. languages klasörünü hazırla ve gömülü dilleri çıkar
        File langFolder = new File(plugin.getDataFolder(), "languages");
        if (!langFolder.exists()) {
            langFolder.mkdirs();
        }

        saveDefaultLangResource("messages_en.yml");
        saveDefaultLangResource("messages_tr.yml");

        // 2. Fallback (İngilizce) yükle
        InputStream fallbackStream = plugin.getResource("languages/messages_en.yml");
        if (fallbackStream != null) {
            this.fallbackConfig = YamlConfiguration.loadConfiguration(new InputStreamReader(fallbackStream, StandardCharsets.UTF_8));
        }

        // 3. Hedef dil dosyasını yükle
        File langFile = new File(langFolder, "messages_" + this.currentLang + ".yml");
        if (langFile.exists()) {
            this.langConfig = YamlConfiguration.loadConfiguration(langFile);
            plugin.getLogger().info("[Drosophila] Language loaded: " + this.currentLang + " (" + langFile.getName() + ")");
        } else {
            plugin.getLogger().warning("[Drosophila] Language file not found: " + langFile.getName() + ", falling back to 'en' (English).");
            File defaultFile = new File(langFolder, "messages_en.yml");
            if (defaultFile.exists()) {
                this.langConfig = YamlConfiguration.loadConfiguration(defaultFile);
            } else {
                this.langConfig = this.fallbackConfig;
            }
        }
    }

    private void saveDefaultLangResource(String fileName) {
        File out = new File(new File(plugin.getDataFolder(), "languages"), fileName);
        if (!out.exists()) {
            try {
                plugin.saveResource("languages/" + fileName, false);
            } catch (Exception e) {
                plugin.getLogger().warning("[Drosophila] Could not extract language resource (" + fileName + "): " + e.getMessage());
            }
        }
    }

    public String get(String key) {
        String msg = null;
        if (langConfig != null) {
            msg = langConfig.getString(key);
        }
        if (msg == null && fallbackConfig != null) {
            msg = fallbackConfig.getString(key);
        }
        if (msg == null) {
            return "§c[Missing lang key: " + key + "]";
        }
        return ChatColor.translateAlternateColorCodes('&', msg);
    }

    public String get(String key, Object... args) {
        String template = get(key);
        if (args == null || args.length == 0) {
            return template;
        }
        for (int i = 0; i < args.length; i++) {
            String val = args[i] != null ? args[i].toString() : "";
            template = template.replace("{" + i + "}", val);
        }
        return template;
    }

    public List<String> getList(String key) {
        List<String> list = null;
        if (langConfig != null) {
            list = langConfig.getStringList(key);
        }
        if ((list == null || list.isEmpty()) && fallbackConfig != null) {
            list = fallbackConfig.getStringList(key);
        }
        if (list == null || list.isEmpty()) {
            List<String> empty = new ArrayList<>();
            empty.add("§c[Missing lang key: " + key + "]");
            return empty;
        }
        List<String> res = new ArrayList<>();
        for (String s : list) {
            res.add(ChatColor.translateAlternateColorCodes('&', s));
        }
        return res;
    }

    public String getCurrentLang() {
        return currentLang;
    }
}
