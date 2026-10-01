package org.drosophila.network;

import org.drosophila.auditory.AuditoryWindSampler.AuditorySample;
import org.drosophila.controller.BeeController;
import org.drosophila.controller.BeeController.MotorCommand;
import org.drosophila.olfaction.OdorDiffusion.OdorSample;
import org.drosophila.vision.CompoundEyeRaytracer.RaycastResult;
import org.java_websocket.WebSocket;
import org.java_websocket.handshake.ClientHandshake;
import org.java_websocket.server.WebSocketServer;

import java.net.InetSocketAddress;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.logging.Logger;

/**
 * Paper sunucusu üzerinde 0.0.0.0:port adresinde çalışan WebSocket Sunucusu.
 * Python beyni (run_real.py) bu sunucuya bağlanır.
 * Duyu çerçevelerini Python'a iletir, inen nöron motor komutlarını alır.
 */
public class BrainServer extends WebSocketServer {

    private final BeeController controller;
    private final Logger logger;
    private final AtomicReference<WebSocket> activeConn = new AtomicReference<>(null);
    private final AtomicBoolean sending = new AtomicBoolean(false);
    private volatile MotorCommand lastCommand = new MotorCommand();

    private String flyId = "Fly_1";
    private String authToken = "drosophila_secret_token_123";

    public BrainServer(int port, BeeController controller, Logger logger) {
        super(new InetSocketAddress("0.0.0.0", port));
        this.controller = controller;
        this.logger = logger;
        setReuseAddr(true);
        setTcpNoDelay(true);
    }

    public void setAuthToken(String token) {
        this.authToken = (token != null) ? token : "";
    }

    public String getAuthToken() {
        return authToken;
    }

    public void setFlyId(String id) {
        this.flyId = (id != null && !id.isEmpty()) ? id : "Fly_1";
    }

    public String getFlyId() {
        return flyId;
    }

    public boolean isConnected() {
        WebSocket conn = activeConn.get();
        return conn != null && conn.isOpen();
    }

    public MotorCommand getLastCommand() {
        return lastCommand;
    }

    @Override
    public void onStart() {
        logger.info("[Drosophila-Paper] WebSocket server started on 0.0.0.0:" + getPort());
        logger.info("[Drosophila-Paper] Waiting for Python brain (run_real.py)...");
    }

    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        String descriptor = handshake.getResourceDescriptor();
        String remote = conn.getRemoteSocketAddress() != null ? conn.getRemoteSocketAddress().toString() : "client";

        // Query parametresinde token kontrolü (?token=...)
        if (authToken != null && !authToken.isEmpty()) {
            if (descriptor != null && descriptor.contains("token=")) {
                String tokenParam = extractParam(descriptor, "token");
                if (!authToken.equals(tokenParam)) {
                    logger.warning("[Drosophila-Paper] Unauthorized connection attempt from " + remote + " (invalid token)!");
                    conn.close(1008, "Invalid auth token");
                    return;
                }
            }
        }

        WebSocket old = activeConn.getAndSet(conn);
        if (old != null && old.isOpen() && !old.equals(conn)) {
            try {
                old.close(1001, "New connection replacing old");
            } catch (Exception ignored) {}
        }

        logger.info("[Drosophila-Paper] Python brain connected: " + remote + " (MaleCNS v1.0 active)");
    }

    @Override
    public void onClose(WebSocket conn, int code, String reason, boolean remote) {
        if (activeConn.compareAndSet(conn, null)) {
            logger.warning("[Drosophila-Paper] Python brain disconnected (" + reason + ").");
        }
    }

    @Override
    public void onError(WebSocket conn, Exception ex) {
        if (ex != null) {
            logger.warning("[Drosophila-Paper] WebSocket error: " + ex.getMessage());
        }
    }

    @Override
    public void onMessage(WebSocket conn, String message) {
        if (message == null || message.isEmpty()) return;

        // Token doğrulama (mesaj gövdesinde geldiyse)
        if (authToken != null && !authToken.isEmpty() && message.contains("\"auth_token\"")) {
            String token = extractString(message, "\"auth_token\":\"", "\"");
            if (token != null && !token.equals(authToken)) {
                logger.warning("[Drosophila-Paper] Invalid auth_token in message! Closing connection.");
                conn.close(1008, "Invalid auth token");
                activeConn.compareAndSet(conn, null);
                return;
            }
        }

        parseMotorCommand(message);
    }

    public void sendSensoryData(RaycastResult vision, OdorSample odor, AuditorySample auditory, double health,
                                double heading, boolean hurt, int stuckTicks, boolean blockedByObstacle) {
        sendSensoryData(vision, odor, auditory, health, heading, hurt, stuckTicks, blockedByObstacle, false);
    }

    public void sendSensoryData(RaycastResult vision, OdorSample odor, AuditorySample auditory, double health,
                                double heading, boolean hurt, int stuckTicks, boolean blockedByObstacle, boolean isSleeping) {
        WebSocket conn = activeConn.get();
        if (conn == null || !conn.isOpen()) return;

        // Yüksek performanslı JSON üretici (64x24 HD faset + 32x6 beyin retinası)
        StringBuilder sb = new StringBuilder(24576);
        sb.append("{");
        sb.append("\"auth_token\":\"").append(authToken).append("\",");
        sb.append("\"fly_id\":\"").append(flyId).append("\",");
        sb.append("\"is_sleeping\":").append(isSleeping).append(",");
        sb.append("\"hd_cols\":64,\"hd_rows\":24,");
        sb.append("\"heading\":").append(String.format(java.util.Locale.US, "%.2f", heading)).append(",");
        sb.append("\"health\":").append(String.format(java.util.Locale.US, "%.1f", health)).append(",");
        sb.append("\"food\":").append(String.format(java.util.Locale.US, "%.2f", controller.getFoodLevel())).append(",");
        sb.append("\"hurt\":").append(hurt).append(",");
        sb.append("\"stuck_ticks\":").append(stuckTicks).append(",");
        sb.append("\"wall_ahead\":").append(blockedByObstacle).append(",");

        // Johnston Organı (İşitme ve Rüzgâr / Hava Akımı):
        if (auditory != null) {
            sb.append("\"sound_level\":").append(String.format(java.util.Locale.US, "%.4f", auditory.soundLevel)).append(",");
            sb.append("\"sound_bearing\":").append(String.format(java.util.Locale.US, "%.4f", auditory.soundBearing)).append(",");
            sb.append("\"sound_name\":\"").append(auditory.soundName).append("\",");
            sb.append("\"wind\":").append(String.format(java.util.Locale.US, "%.4f", auditory.windLevel)).append(",");
        }

        // Koku ve Tat Duyusu:
        sb.append("\"odor_left\":").append(String.format(java.util.Locale.US, "%.4f", odor.odorLeft)).append(",");
        sb.append("\"odor_right\":").append(String.format(java.util.Locale.US, "%.4f", odor.odorRight)).append(",");
        sb.append("\"food_odor_left\":").append(String.format(java.util.Locale.US, "%.4f", odor.foodOdorLeft)).append(",");
        sb.append("\"food_odor_right\":").append(String.format(java.util.Locale.US, "%.4f", odor.foodOdorRight)).append(",");
        sb.append("\"flower_odor_left\":").append(String.format(java.util.Locale.US, "%.4f", odor.flowerOdorLeft)).append(",");
        sb.append("\"flower_odor_right\":").append(String.format(java.util.Locale.US, "%.4f", odor.flowerOdorRight)).append(",");
        sb.append("\"leaf_odor_left\":").append(String.format(java.util.Locale.US, "%.4f", odor.leafOdorLeft)).append(",");
        sb.append("\"leaf_odor_right\":").append(String.format(java.util.Locale.US, "%.4f", odor.leafOdorRight)).append(",");
        sb.append("\"peer_dist\":").append(String.format(java.util.Locale.US, "%.2f", odor.peerDist)).append(",");
        sb.append("\"peer_bearing\":").append(String.format(java.util.Locale.US, "%.4f", odor.peerBearing)).append(",");
        sb.append("\"dropped_food_dist\":").append(String.format(java.util.Locale.US, "%.2f", odor.closestDist)).append(",");
        sb.append("\"food_count\":").append(odor.closestDist < 1.4 ? 1 : 0).append(",");
        sb.append("\"taste\":").append(String.format(java.util.Locale.US, "%.4f", odor.taste)).append(",");

        // Ocelli, Gökyüzü Işığı, Dünya Saati ve Termo-Duyu (Sıcaklık):
        sb.append("\"ocellus_left\":").append(String.format(java.util.Locale.US, "%.4f", vision.ocellusLeft)).append(",");
        sb.append("\"ocellus_right\":").append(String.format(java.util.Locale.US, "%.4f", vision.ocellusRight)).append(",");
        sb.append("\"heat\":").append(String.format(java.util.Locale.US, "%.4f", vision.heat)).append(",");
        sb.append("\"sky_factor\":").append(String.format(java.util.Locale.US, "%.4f", vision.skyFactor)).append(",");
        sb.append("\"time_of_day\":").append(vision.timeOfDay).append(",");
        sb.append("\"sun_bearing\":").append(String.format(java.util.Locale.US, "%.4f", vision.sunBearing)).append(",");
        sb.append("\"sun_elevation\":").append(String.format(java.util.Locale.US, "%.4f", vision.sunElevation)).append(",");

        // Tehdit (Looming Canavar/Oyuncu):
        sb.append("\"threat_dist\":").append(String.format(java.util.Locale.US, "%.2f", vision.threatDist)).append(",");
        sb.append("\"threat_bearing\":").append(String.format(java.util.Locale.US, "%.4f", vision.threatBearing)).append(",");
        sb.append("\"threat_name\":\"").append(vision.threatName).append("\",");

        // Su, Nem ve Soğukluk / Yağmur Algısı:
        sb.append("\"water_dist\":").append(String.format(java.util.Locale.US, "%.2f", vision.waterDist)).append(",");
        sb.append("\"water_bearing\":").append(String.format(java.util.Locale.US, "%.4f", vision.waterBearing)).append(",");
        sb.append("\"water_ahead\":").append(vision.waterAhead).append(",");
        sb.append("\"water_below\":").append(vision.waterBelow).append(",");
        sb.append("\"humidity\":").append(String.format(java.util.Locale.US, "%.4f", vision.humidity)).append(",");
        sb.append("\"cold\":").append(String.format(java.util.Locale.US, "%.4f", vision.cold)).append(",");
        sb.append("\"is_raining\":").append(vision.isRaining).append(",");

        // 2D Derinlik Matrisi (32x6 = 192 ommatidia uzaysal derinlik)
        sb.append("\"depth\":[");
        for (int i = 0; i < vision.depthBrain.length; i++) {
            if (i > 0) sb.append(",");
            sb.append(String.format(java.util.Locale.US, "%.2f", vision.depthBrain[i]));
        }
        sb.append("],");

        // Mesafe dizisi (32 ufuk sütunu)
        sb.append("\"distances\":[");
        for (int i = 0; i < vision.distances.length; i++) {
            if (i > 0) sb.append(",");
            sb.append(String.format(java.util.Locale.US, "%.2f", vision.distances[i]));
        }
        sb.append("],");

        // HD Petek Göz Renkleri (64x24 = 1536 ommatidium)
        sb.append("\"retina_hd\":[");
        for (int i = 0; i < vision.retinaHd.length; i += 3) {
            if (i > 0) sb.append(",");
            sb.append("[").append(vision.retinaHd[i]).append(",")
              .append(vision.retinaHd[i + 1]).append(",")
              .append(vision.retinaHd[i + 2]).append("]");
        }
        sb.append("],");

        // Beyin Fotoreseptör Retinası (32x6 = 192 ommatidium)
        sb.append("\"retina\":[");
        for (int i = 0; i < vision.retinaRgb.length; i += 3) {
            if (i > 0) sb.append(",");
            sb.append("[").append(vision.retinaRgb[i]).append(",")
              .append(vision.retinaRgb[i + 1]).append(",")
              .append(vision.retinaRgb[i + 2]).append("]");
        }
        sb.append("]");

        sb.append("}");

        try {
            conn.send(sb.toString());
        } catch (Exception e) {
            logger.warning("[Drosophila-Paper] Data transmission error: " + e.getMessage());
        }
    }

    public void sendBottleCommand(boolean bottled) {
        WebSocket conn = activeConn.get();
        if (conn == null || !conn.isOpen()) return;
        String json = "{\"command\":\"" + (bottled ? "bottle" : "unbottle") + "\",\"fly_id\":\"" + flyId + "\",\"bottled\":" + bottled + ",\"auth_token\":\"" + authToken + "\"}";
        try {
            conn.send(json);
        } catch (Exception ignored) {}
    }

    public boolean sendResetCommand(String targetFlyId) {
        WebSocket conn = activeConn.get();
        if (conn == null || !conn.isOpen()) return false;
        String id = (targetFlyId != null && !targetFlyId.isEmpty()) ? targetFlyId : this.flyId;
        String json = "{\"command\":\"reset_memory\",\"fly_id\":\"" + id + "\"}";
        try {
            conn.send(json);
            logger.info("[Drosophila-Paper] Memory reset command sent to Python brain (" + id + ").");
            return true;
        } catch (Exception e) {
            logger.warning("[Drosophila-Paper] Failed to send memory reset command: " + e.getMessage());
            return false;
        }
    }

    private void parseMotorCommand(String json) {
        MotorCommand cmd = new MotorCommand();
        cmd.forward = json.contains("\"forward\": true") || json.contains("\"forward\":true");
        cmd.back = json.contains("\"back\": true") || json.contains("\"back\":true");
        cmd.is_escaping = json.contains("\"is_escaping\": true") || json.contains("\"is_escaping\":true");
        cmd.jump = json.contains("\"jump\": true") || json.contains("\"jump\":true");
        cmd.sprint = json.contains("\"sprint\": true") || json.contains("\"sprint\":true");
        cmd.eat = json.contains("\"eat\": true") || json.contains("\"eat\":true");

        // Sayısal değerler
        cmd.steering_torque = extractFloat(json, "\"steering_torque\":", 0.0f);
        cmd.forward_thrust = extractFloat(json, "\"forward_thrust\":", 0.0f);
        cmd.pitch = extractFloat(json, "\"pitch\":", 0.0f);

        // Ruh hali / duygu
        if (json.contains("\"mood\":\"happy\"") || json.contains("\"mood\": \"happy\"")) {
            cmd.mood = "happy";
        } else if (json.contains("\"mood\":\"sad\"") || json.contains("\"mood\": \"sad\"")) {
            cmd.mood = "sad";
        } else if (json.contains("\"mood\":\"scared\"") || json.contains("\"mood\": \"scared\"")) {
            cmd.mood = "scared";
        } else if (json.contains("\"mood\":\"eating\"") || json.contains("\"mood\": \"eating\"")) {
            cmd.mood = "eating";
        } else {
            cmd.mood = "neutral";
        }

        this.lastCommand = cmd;
    }

    private float extractFloat(String json, String key, float def) {
        int idx = json.indexOf(key);
        if (idx == -1) return def;
        int start = idx + key.length();
        int end = json.indexOf(",", start);
        if (end == -1) end = json.indexOf("}", start);
        if (end == -1) return def;
        try {
            return Float.parseFloat(json.substring(start, end).trim());
        } catch (Exception e) {
            return def;
        }
    }

    private String extractString(String json, String prefix, String suffix) {
        int idx = json.indexOf(prefix);
        if (idx == -1) return null;
        int start = idx + prefix.length();
        int end = json.indexOf(suffix, start);
        if (end == -1) return null;
        return json.substring(start, end);
    }

    private String extractParam(String query, String param) {
        int idx = query.indexOf(param + "=");
        if (idx == -1) return null;
        int start = idx + param.length() + 1;
        int end = query.indexOf("&", start);
        if (end == -1) end = query.length();
        return query.substring(start, end);
    }
}
