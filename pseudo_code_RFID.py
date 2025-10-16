def rfid_loop():
    global last_uid, rfid_alert_flag

    while continue_reading is True:
        (status, tag_type) = RFID_Request(IDLE_MODE)

        if status == OK:
            (status, uid) = RFID_SelectTag()

            if status == OK:
                uid_str = convert_uid_bytes_to_uppercase_hex_string(uid)
                print("Card detected UID: " + uid_str)

                with lcd_lock:
                    clear_lcd_display()

                    if uid_str == last_uid:
                        display_on_lcd("Goodbye")
                        log_event("RFID Scan OUT", uid_str)
                        last_uid = None
                    else:
                        display_on_lcd("Welcome")
                        log_event("RFID Scan IN", uid_str)
                        last_uid = uid_str

                turn_on_led(red_off=True, green_on=True, blue_off=True)
                wait(2)
                turn_off_all_leds()

                with rfid_lock:
                    rfid_alert_flag = True
