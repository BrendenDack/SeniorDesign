import lgpio
import time
h = lgpio.gpiochip_open(0)

# GPIO Pin Definitions
SELECT_BUTTON = 26    # GPIO 26: Select
BACK_BUTTON = 16      # GPIO 16: Back
UP_BUTTON = 4        # GPIO 1: Up
RIGHT_BUTTON = 22    # GPIO 22: Right
DOWN_BUTTON = 20     # GPIO 20: Down
LEFT_BUTTON = 21     # GPIO 21: Left
VOLUME_UP = 23       # GPIO 23: Volume up
VOLUME_DOWN = 24     # GPIO 24: Volume down
button_list = [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, DOWN_BUTTON, 
               LEFT_BUTTON, RIGHT_BUTTON, VOLUME_DOWN, VOLUME_UP]
def setup_gpio():
    
    # Claim each button's gpio pin
    lgpio.gpio_claim_input(h, SELECT_BUTTON)
    lgpio.gpio_claim_input(h, BACK_BUTTON)
    lgpio.gpio_claim_input(h, UP_BUTTON)
    lgpio.gpio_claim_input(h, RIGHT_BUTTON)
    lgpio.gpio_claim_input(h, DOWN_BUTTON)
    lgpio.gpio_claim_input(h, LEFT_BUTTON)
    lgpio.gpio_claim_input(h, VOLUME_UP)
    lgpio.gpio_claim_input(h, VOLUME_DOWN)

    #lgpio.group_claim_input(h, button_list)

    # Set debounce timings for each button
    lgpio.gpio_set_debounce_micros(h, SELECT_BUTTON, 200)
    lgpio.gpio_set_debounce_micros(h, BACK_BUTTON, 200)
    lgpio.gpio_set_debounce_micros(h, UP_BUTTON, 200)
    lgpio.gpio_set_debounce_micros(h, RIGHT_BUTTON, 200)
    lgpio.gpio_set_debounce_micros(h, DOWN_BUTTON, 200)
    lgpio.gpio_set_debounce_micros(h, LEFT_BUTTON, 200)
    lgpio.gpio_set_debounce_micros(h, VOLUME_UP, 200)
    lgpio.gpio_set_debounce_micros(h, VOLUME_DOWN, 200)

values = [lgpio.gpio_read(h, pin) for pin in button_list]

print("Listening for button presses. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
        values = lgpio.gpio_read(h, SELECT_BUTTON)
        print(values)
        if (values[0] == 1):
            print("I'm Select!")
        if (values[1] == 1):
            print("I'm Back!")
        if (values[2] == 1):
            print("I'm Up!")
        if (values[3] == 1):
            print("I'm Right!")
        if (values[4] == 1):
            print("I'm Left!")
        if (values[5] == 1):
            print("I'm Down!")
        if (values[6] == 1):
            print("I'm Vol Up!")
        if (values[7] == 1):
            print("I'm Vol Down!")
except KeyboardInterrupt:
    print("Stopping...")

lgpio.gpiochip_close(h)