# START PROGRAM

# Setup distance sensor (trigger=4, echo=17)
# Setup LEDs: red, green, yellow
# Setup RGB room light and control button
# Use pigpio factory for accurate readings

# Create MotionDetector:
# - Take 50 samples for baseline (no one in front)
# - Use moving median filter for noise
# - Motion threshold = 15 cm
# - Room light stays on 5 sec after motion stops

# Button toggles light system ON/OFF

# Background thread checks every second:
# If light is ON and no motion for 5 sec → turn off light


def main_loop():
    while True:
        # Get filtered distance reading in cm
        distance = get_filtered_distance_cm()

        # Compare with baseline distance
        change = abs(distance - baseline_distance)

        if change > threshold:
            if not motion_active:
                # If motion just started:
                start_motion_block_timer()
                turn_on_led("red")
                turn_off_led("green")
                if light_system_enabled:
                    turn_on_room_light()
                log_motion_start()
            else:
                # Count as continued motion
                update_last_motion_time()
        else:
            if motion_active:
                # If motion was ongoing:
                end_motion_block()
                save_to_log_file()
                turn_on_led("green")
                turn_off_led("red")

        print_current_status(distance, change, motion_state, light_status)
        wait(0.3)


def handle_ctrl_c():
    stop_background_thread()
    end_motion_block_if_active()
    turn_off_all_leds_and_lights()
    exit_program()
