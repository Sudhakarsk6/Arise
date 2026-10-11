package org.arise.service;

import android.app.Notification;
import android.app.RemoteInput;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Watches incoming chat notifications. If you have not opened/dismissed the
 * notification after N minutes, it sends the auto-reply through the
 * notification's own "Reply" action. Settings come from arise_config.json
 * (written by the Python app).
 */
public class AriseListener extends NotificationListenerService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Map<String, Runnable> pending = new HashMap<>();
    private final Map<String, Long> lastReply = new HashMap<>();

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try {
            handle(sbn);
        } catch (Exception e) {
            log("listener error: " + e);
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // You opened, replied to or dismissed it -> cancel the pending auto-reply.
        Runnable r = pending.remove(sbn.getKey());
        if (r != null) {
            handler.removeCallbacks(r);
            log("cancelled auto-reply (you handled it): " + sbn.getPackageName());
        }
    }

    private void handle(final StatusBarNotification sbn) throws Exception {
        final String pkg = sbn.getPackageName();
        if (pkg.equals(getPackageName())) return;

        JSONObject cfg = readConfig();
        if (cfg == null) return;
        JSONObject ar = cfg.optJSONObject("autoreply");
        if (ar == null || !ar.optBoolean("enabled", false)) return;

        JSONArray pk = ar.optJSONArray("packages");
        boolean pkgOk = false;
        if (pk != null) for (int i = 0; i < pk.length(); i++) if (pkg.equals(pk.optString(i))) pkgOk = true;
        if (!pkgOk) return;

        Notification n = sbn.getNotification();
        if ((n.flags & Notification.FLAG_GROUP_SUMMARY) != 0 || n.actions == null) return;
        Bundle ex = n.extras;
        if (ex.getBoolean(Notification.EXTRA_IS_GROUP_CONVERSATION, false)) return; // skip group chats

        Notification.Action found = null;
        for (Notification.Action a : n.actions) {
            if (a.getRemoteInputs() != null && a.getRemoteInputs().length > 0 && a.actionIntent != null) {
                found = a;
                break;
            }
        }
        if (found == null) return;
        final Notification.Action action = found;

        CharSequence t = ex.getCharSequence(Notification.EXTRA_TITLE);
        final String sender = t == null ? "unknown" : t.toString();

        JSONArray only = ar.optJSONArray("only_contacts");
        if (only != null && only.length() > 0) {
            boolean match = false;
            for (int i = 0; i < only.length(); i++)
                if (sender.toLowerCase(Locale.ROOT).contains(only.optString(i).toLowerCase(Locale.ROOT))) match = true;
            if (!match) return;
        }

        final String ck = pkg + "|" + sender.toLowerCase(Locale.ROOT);
        long cooldown = ar.optLong("cooldown_minutes", 60) * 60000L;
        Long last = lastReply.get(ck);
        if (last != null && System.currentTimeMillis() - last < cooldown) return;

        final String key = sbn.getKey();
        if (pending.containsKey(key)) return; // timer already running for this chat

        final String message = ar.optString("message", "I'll reply soon. (Auto-reply from Arise)");
        long delay = ar.optLong("delay_minutes", 10) * 60000L;

        Runnable r = new Runnable() {
            @Override
            public void run() {
                pending.remove(key);
                try {
                    RemoteInput[] ris = action.getRemoteInputs();
                    Intent intent = new Intent();
                    Bundle b = new Bundle();
                    for (RemoteInput ri : ris) b.putCharSequence(ri.getResultKey(), message);
                    RemoteInput.addResultsToIntent(ris, intent, b);
                    action.actionIntent.send(AriseListener.this, 0, intent);
                    lastReply.put(ck, System.currentTimeMillis());
                    log("auto-replied to " + sender + " (" + pkg + ")");
                } catch (Exception e) {
                    log("auto-reply failed for " + sender + ": " + e);
                }
            }
        };
        pending.put(key, r);
        handler.postDelayed(r, delay);
        log("timer started for " + sender + " (" + pkg + ")");
    }

    private JSONObject readConfig() {
        try {
            File f = new File(getFilesDir(), "arise_config.json");
            if (!f.exists()) return null;
            FileInputStream in = new FileInputStream(f);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int r;
            while ((r = in.read(buf)) > 0) out.write(buf, 0, r);
            in.close();
            return new JSONObject(out.toString("UTF-8"));
        } catch (Exception e) {
            return null;
        }
    }

    private void log(String msg) {
        try {
            String ts = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss ", Locale.US).format(new Date());
            FileOutputStream o = new FileOutputStream(new File(getFilesDir(), "arise_log.txt"), true);
            o.write((ts + msg + "\n").getBytes("UTF-8"));
            o.close();
        } catch (Exception ignored) {
        }
    }
}
