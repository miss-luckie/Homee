# START PROGRAM

# Init Flask web server and motion detector hardware
# Start background thread running motion_detection_loop()

# WEB ROUTES:
# "/" → Serve dashboard webpage (motion_control.html)
# "/api/status" → Send live status (motion, distance, lights)
# "/api/toggle_light" → Toggle room light ON/OFF, return result
# "/api/motion_log" → Return motion log as JSON
# "/api/clear_log" → Delete log file, confirm success
# "/api/export_log" → Convert log JSON → CSV, let user download


def background_thread():
    while True:
        # Read filtered distance
        read_filtered_distance()
        # Detect motion changes
        detect_motion_changes()
        # Update LEDs, lights, and logs
        update_leds_lights_logs()
        # Wait briefly
        wait_briefly()


# ON STARTUP:
# Load old log → calibrate baseline → start Flask at http://localhost:5000


# ON EXIT:
# Stop threads, turn off LEDs/lights, save logs, clean up

# END PROGRAM
