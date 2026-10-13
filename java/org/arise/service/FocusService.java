package org.arise.service;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.util.Calendar;

/** Focus mode: sends you Home when you open a blocked app while focus is active. */
public class FocusService extends AccessibilityService {
    private long lastToast = 0;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent e) {
        if (e.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED || e.getPackageName() == null) return;
        String pkg = e.getPackageName().toString();
        if (pkg.equals(getPackageName())) return;
        try {
            JSONObject cfg = read();
            if (cfg == null) return;
            JSONObject f = cfg.optJSONObject("focus");
            if (f == null || !active(f)) return;
            JSONArray blocked = f.optJSONArray("blocked_packages");
            if (blocked == null) return;
            for (int i = 0; i < blocked.length(); i++) {
                if (pkg.equals(blocked.optString(i))) {
                    performGlobalAction(GLOBAL_ACTION_HOME);
                    long now = System.currentTimeMillis();
                    if (now - lastToast > 3000) {
                        lastToast = now;
                        Toast.makeText(this, "Arise Focus: stay on task", Toast.LENGTH_SHORT).show();
                    }
                    return;
                }
            }
        } catch (Exception ignored) {
        }
    }

    private boolean active(JSONObject f) {
        if (f.optLong("until_ms", 0) > System.currentTimeMillis()) return true;
        if (!f.optBoolean("enabled", false)) return false;
        JSONArray sc = f.optJSONArray("schedules");
        if (sc == null) return false;
        Calendar c = Calendar.getInstance();
        int cur = c.get(Calendar.HOUR_OF_DAY) * 60 + c.get(Calendar.MINUTE);
        for (int i = 0; i < sc.length(); i++) {
            JSONObject s = sc.optJSONObject(i);
            if (s == null) continue;
            int a = mins(s.optString("start", "00:00")), b = mins(s.optString("end", "00:00"));
            if (a <= b ? (cur >= a && cur < b) : (cur >= a || cur < b)) return true;
        }
        return false;
    }

    private int mins(String hhmm) {
        String[] p = hhmm.split(":");
        return Integer.parseInt(p[0]) * 60 + Integer.parseInt(p[1]);
    }

    private JSONObject read() {
        try {
            File file = new File(getFilesDir(), "arise_config.json");
            if (!file.exists()) return null;
            FileInputStream in = new FileInputStream(file);
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

    @Override
    public void onInterrupt() {
    }
}
