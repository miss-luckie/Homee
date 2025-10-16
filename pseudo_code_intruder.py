def ultrasonic_loop():
    while continue_reading is True:
        # SEND 10-microsecond trigger pulse to TRIG pin
        send_trigger_pulse(duration_microseconds=10)

        # WAIT for echo start and echo end signals
        start, end = wait_for_echo_signals()

        # CALCULATE duration = end - start
        duration = end - start

        # CALCULATE distance = duration * 17150  // convert to cm
        distance = duration * 17150

        if distance > 2 and distance < 10:
            print("🚨 Intruder Detected!")

            with lcd_lock:
                clear_lcd_display()
                display_on_lcd("Intruder Detected!")

            log_event("Intruder Detected", "placeholder ID")

            flash_end_time = current_time + 5
            while current_time < flash_end_time:
                turn_on_led("red")
                wait(0.2)
                turn_off_led()
                wait(0.2)

            with lcd_lock:
                clear_lcd_display()

        wait(1)
