#!/usr/bin/env python3
# HOMEe: button-triggered env logger for Raspberry Pi (UTC logging + full band messages)
# GPIO: BTN=18, DHT11=24, LEDs RED=5 ORANGE=6 YELLOW=13 GREEN=16 BLUE=19 PURPLE=26
 
from gpiozero import LED, Button
from signal import pause
from time import sleep, time, strftime, gmtime
import requests, pigpio, pigpio_dht, csv, os, subprocess, traceback
 
# ── Config ─────────────────────────────────────────────────────────────
SERVER   = "http://127.0.0.1:5000/submit"
LOG_FILE = "/home/raspberry01/homee/homee_readings.csv"
DROPBOX_UPLOADER = [
    "/bin/bash",
    "/home/raspberry01/homee/Dropbox-Uploader/dropbox_uploader.sh",
    "upload", LOG_FILE, "homee_readings.csv", "/",
]
BTN = Button(18, pull_up=True, bounce_time=0.15)
DHT_PIN = 24
 
# ── LEDs ───────────────────────────────────────────────────────────────
LEDS = {
    "RED": LED(5), "ORANGE": LED(6), "YELLOW": LED(13),
    "GREEN": LED(16), "BLUE": LED(19), "PURPLE": LED(26),
}
TEMP_GROUP = {"RED","GREEN","BLUE"}
HUM_GROUP  = {"ORANGE","YELLOW","PURPLE"}
 
def _group_off(group):
    for n in group: LEDS[n].off()
 
def _apply_led(color, mode):
    grp = TEMP_GROUP if color in TEMP_GROUP else HUM_GROUP
    _group_off(grp)
    led = LEDS[color]
    if   mode == "solid":  led.on()
    elif mode == "flash1": led.blink(on_time=0.5, off_time=0.5, background=True)
    elif mode == "flash5": led.blink(on_time=2.5, off_time=2.5, background=True)
    elif mode == "off":    led.off()
    else: raise ValueError(mode)
 
# ── Bands (from your table) ────────────────────────────────────────────
def classify_temp(c):
    if c >= 29:        return ("RED","flash1","TEMP IS TOO HOT!")
    if 27 <= c <= 28:  return ("RED","flash5","Temp is too hot")
    if 24 <= c <= 26:  return ("RED","solid","Temp is getting high")
    if 19 <= c <= 23:  return ("GREEN","solid","Ideal temp")
    if 0  <= c <= 18:  return ("BLUE","flash5","TEMP is too cold")
    return ("BLUE","flash1","TEMP IS TOO COLD!")
 
def classify_humidity(rh):
    if rh >= 70:       return ("ORANGE","flash5","HUM IS TOO HIGH!")
    if 60 <= rh <= 69: return ("ORANGE","solid","Humidity getting high")
    if 41 <= rh <= 59: return ("YELLOW","solid","Ideal humidity")
    if 31 <= rh <= 40: return ("PURPLE","solid","Humidity getting low")
    return ("PURPLE","flash5","HUM IS TOO LOW!")
 
# ── Sensor (signature: DHT11(gpio, pi=pi)) ─────────────────────────────
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not running. Start with: sudo pigpiod")
 
sensor = pigpio_dht.DHT11(DHT_PIN, pi=pi)
 
def _read_dht11(max_tries=5, retry_delay=0.8):
    """Handles dict/tuple outputs; returns (temp_c, humidity)."""
    last_err = None
    for _ in range(max_tries):
        try:
            r = sensor.read()
            if isinstance(r, dict):
                if r.get("valid", True):
                    c = r.get("temp_c") or r.get("temperature")
                    h = r.get("humidity")
                    if c is not None and h is not None:
                        return float(c), float(h)
            elif isinstance(r, tuple):
                nums = [v for v in r if isinstance(v, (int, float))]
                if len(nums) >= 2:
                    a, b = float(nums[-2]), float(nums[-1])
                    if 0 <= a <= 80 and 0 <= b <= 100: return a, b
                    if 0 <= b <= 80 and 0 <= a <= 100: return b, a
        except Exception as e:
            last_err = e
        sleep(retry_delay)
    raise RuntimeError(f"DHT11 read failed: {last_err}")
 
# ── CSV (UTC + messages) ───────────────────────────────────────────────
def log_to_csv(ts, temp, rh, t_color, t_mode, t_msg, h_color, h_mode, h_msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow([
                "timestamp","datetime_utc","temperature_C","humidity_pct",
                "temp_color","temp_mode","temp_message",
                "hum_color","hum_mode","hum_message"
            ])
        w.writerow([
            ts, strftime("%Y-%m-%dT%H:%M:%SZ", gmtime()),
            round(temp,1), round(rh,1),
            t_color, t_mode, t_msg,
            h_color, h_mode, h_msg
        ])
 
# ── Button handler ─────────────────────────────────────────────────────
def on_press():
    print("\nButton pressed → Reading sensor...")
    try:
        c, rh = _read_dht11()
        t_color, t_mode, t_msg = classify_temp(c)
        h_color, h_mode, h_msg = classify_humidity(rh)
 
        _apply_led(t_color, t_mode)
        _apply_led(h_color, h_mode)
 
        ts = int(time())  # epoch seconds (UTC by definition)
        log_to_csv(ts, c, rh, t_color, t_mode, t_msg, h_color, h_mode, h_msg)
        print(f"Logged UTC: {strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())} | "
              f"{c:.1f}°C, {rh:.1f}% → {t_color}/{h_color}")
 
        # POST
        try:
            payload = {
                "timestamp": ts, "temp_c": round(c,1), "humidity": round(rh,1),
                "temp_band":{"color":t_color,"mode":t_mode,"message":t_msg},
                "hum_band":{"color":h_color,"mode":h_mode,"message":h_msg},
                "datetime_utc": strftime("%Y-%m-%dT%H:%M:%SZ", gmtime()),
            }
            r = requests.post(SERVER, json=payload, timeout=5)
            print(f"POST {SERVER} -> {r.status_code}")
        except Exception as e:
            print(f"[HTTP] Failed to POST: {e}")
 
        # Dropbox upload
        try:
            subprocess.run(DROPBOX_UPLOADER, check=False)
        except Exception as e:
            print(f"[Dropbox] Upload failed: {e}")
 
    except Exception as e:
        print("Measurement failed:", e)
        traceback.print_exc()
        LEDS["RED"].blink(on_time=0.2, off_time=0.2, background=True)
        LEDS["PURPLE"].blink(on_time=0.2, off_time=0.2, background=True)
        sleep(2); LEDS["RED"].off(); LEDS["PURPLE"].off()
 
# ── Main ───────────────────────────────────────────────────────────────
def main():
    print("HOMEe ready. Press the button to measure, log (UTC), send, and upload.")
    BTN.when_pressed = on_press
    try: pause()
    finally:
        for led in LEDS.values(): led.off()
        pi.stop()
 
if __name__ == "__main__":
    main()
