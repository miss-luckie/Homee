#!/usr/bin/env python3
import time
from datetime import datetime
import pigpio
import pigpio_dht
from gpiozero import LED

# ---- LED pins (BCM) ----
RED     = LED(5)     # temp hot
ORANGE  = LED(6)     # humidity high
YELLOW  = LED(13)    # humidity normal
GREEN   = LED(16)    # temp normal
BLUE    = LED(19)    # temp cold
PURPLE  = LED(26)    # humidity low

# DHT11 on GPIO24
DHT_PIN = 24
pi = pigpio.pi()
sensor = pigpio_dht.DHT11(DHT_PIN)

BLINK_ON, BLINK_OFF = 3.0, 3.0

def all_off(*leds):
    for led in leds:
        led.off()   # cancels any prior blink, too

# ---- Band rules (your spec) ----
# Temp (°C): b:0–18 | a:19–23 | z:24–26 | y:27–28 | x:29–100
# Hum  (%):  b:0–30 | a:31–40 | z:41–59 | y:60–69 | x:70–100
def temp_band_msg(t):
    if t is None: return "?", "Temperature reading unavailable."
    if 29 <= t <= 100: return "x", "Temperature is TOO HOT!"
    if 27 <= t <= 28:  return "y", "Temperature is TOO HOT! (RED)"
    if 24 <= t <= 26:  return "z", "Temperature is getting hot (RED)"
    if 19 <= t <= 23:  return "a", "Temperature is in normal range (GREEN)"
    if 0  <= t <= 18:  return "b", "Temperature is TOO COLD! (BLUE)"
    return "?", "Temperature out of expected range."

def humid_band_msg(h):
    if h is None: return "?", "Humidity reading unavailable."
    if 70 <= h <= 100: return "x", "Humidity is TOO HIGH! (ORANGE)"
    if 60 <= h <= 69:  return "y", "Humidity is getting high (ORANGE)"
    if 41 <= h <= 59:  return "z", "Humidity is in normal range (YELLOW)"
    if 31 <= h <= 40:  return "a", "Humidity is getting low (PURPLE)"
    if 0  <= h <= 30:  return "b", "Humidity is TOO LOW! (PURPLE)"
    return "?", "Humidity out of expected range."

_last_tb = None
_last_hb = None

def apply_temp(tb):
    global _last_tb
    if tb == _last_tb: return
    _last_tb = tb
    all_off(RED, GREEN, BLUE)
    if tb == "x": RED.blink(on_time=BLINK_ON, off_time=BLINK_OFF, background=True)
    elif tb == "y": RED.on()
    elif tb == "z": RED.on()
    elif tb == "a": GREEN.on()
    elif tb == "b": BLUE.blink(on_time=BLINK_ON, off_time=BLINK_OFF, background=True)

def apply_hum(hb):
    global _last_hb
    if hb == _last_hb: return
    _last_hb = hb
    all_off(ORANGE, YELLOW, PURPLE)
    if hb == "x": ORANGE.blink(on_time=BLINK_ON, off_time=BLINK_OFF, background=True)
    elif hb == "y": ORANGE.on()
    elif hb == "z": YELLOW.on()
    elif hb == "a": PURPLE.on()
    elif hb == "b": PURPLE.blink(on_time=BLINK_ON, off_time=BLINK_OFF, background=True)

print("H.O.M.E.E bands → LEDs. Ctrl+C to stop.")
try:
    while True:
        result = sensor.read()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if result["valid"]:
            t = result["temp_c"]; h = result["humidity"]
            tb, t_msg = temp_band_msg(t)
            hb, h_msg = humid_band_msg(h)
            print(f"[{ts}] Temp {t:.1f}°C | Hum {h:.1f}%")
            print("  •", t_msg)
            print("  •", h_msg)
            apply_temp(tb)
            apply_hum(hb)
        else:
            print(f"[{ts}] DHT11 read failed, retrying...")
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    all_off(RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE)
