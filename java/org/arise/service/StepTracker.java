package org.arise.service;

import android.content.Context;
import android.content.SharedPreferences;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Locale;

/** Counts steps with the hardware step-counter and keeps a per-day history. */
public class StepTracker implements SensorEventListener {
    private static StepTracker inst;
    private final SharedPreferences sp;
    private final SensorManager sm;
    private int today = 0;

    private StepTracker(Context c) {
        sp = c.getSharedPreferences("arise_steps", Context.MODE_PRIVATE);
        sm = (SensorManager) c.getSystemService(Context.SENSOR_SERVICE);
        if (day(0).equals(sp.getString("day", ""))) today = sp.getInt("d_" + day(0), 0);
    }

    public static synchronized void start(Context c) {
        if (inst == null) inst = new StepTracker(c.getApplicationContext());
        inst.register();
    }

    public static synchronized int todaySteps() {
        return inst == null ? 0 : inst.today;
    }

    /** "2026-10-11:5432,2026-10-10:8011,..." newest first. */
    public static synchronized String history(int days) {
        if (inst == null) return "";
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < days; i++) {
            String d = day(-i);
            int v = i == 0 ? inst.today : inst.sp.getInt("d_" + d, 0);
            if (b.length() > 0) b.append(',');
            b.append(d).append(':').append(v);
        }
        return b.toString();
    }

    private void register() {
        sm.unregisterListener(this);
        Sensor s = sm.getDefaultSensor(Sensor.TYPE_STEP_COUNTER);
        if (s != null) sm.registerListener(this, s, SensorManager.SENSOR_DELAY_NORMAL);
    }

    @Override
    public synchronized void onSensorChanged(SensorEvent e) {
        long total = (long) e.values[0];
        String d = day(0);
        long base = sp.getLong("base", -1), last = sp.getLong("last", -1), offset = sp.getLong("offset", 0);
        if (!d.equals(sp.getString("day", "")) || base < 0) {   // new day (or first run)
            base = total;
            offset = 0;
        } else if (total < last) {                              // phone rebooted: counter restarted
            offset = offset + (last - base);
            base = 0;
        }
        today = (int) (offset + total - base);
        sp.edit().putString("day", d).putLong("base", base).putLong("last", total)
                .putLong("offset", offset).putInt("d_" + d, today).apply();
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    private static String day(int offset) {
        Calendar c = Calendar.getInstance();
        c.add(Calendar.DAY_OF_YEAR, offset);
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(c.getTime());
    }
}
