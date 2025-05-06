#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import time
import logging
import threading
from stt import start_voice_recognition
try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    logging.error("RPi.GPIO not found. Please install it with 'pip install RPi.GPIO'")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# GPIO Pin Definitions
SELECT_BUTTON = 26   # GPIO 13: Select
BACK_BUTTON = 16      # GPIO 6: Back
UP_BUTTON = 4        # GPIO 4: Up
RIGHT_BUTTON = 22    # GPIO 22: Right
DOWN_BUTTON = 20     # GPIO 20: Down
LEFT_BUTTON = 21     # GPIO 21: Left
VOLUME_UP = 23       # GPIO 23: Volume Up
VOLUME_DOWN = 24     # GPIO 24: Volume Down

class ButtonFirmware:
    def __init__(self, menu_items, selected_index=0, callback=None):
        """Initialize button firmware with menu items and optional custom callback."""
        if not menu_items or not isinstance(menu_items, list):
            logging.error("Menu items must be a non-empty list")
            raise ValueError("Menu items must be a non-empty list")
        if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(menu_items):
            logging.error("Invalid selected_index: %d", selected_index)
            raise ValueError(f"selected_index must be between 0 and {len(menu_items) - 1}")
        self.menu_items = menu_items
        self.selected_index = selected_index
        self.callback = callback or self.default_callback
        self.setup_gpio()
        logging.debug("ButtonFirmware initialized with %d menu items", len(menu_items))

    def setup_gpio(self):
        """Setup GPIO pins with pull-down resistors."""
        logging.debug("Setting up GPIO pins")
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
                print(f"{pin} is causing error")
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        except Exception as e:
            logging.error("Failed to setup GPIO: %s", e)
            raise

    def default_callback(self, index, channel):
        """Default callback for logging button actions."""
        item_name = self.menu_items[index].get("text") or self.menu_items[index].get("name", f"Item {index}")
        logging.debug("Default callback: index=%d, channel=%d, item=%s", index, channel, item_name)

    def button_callback(self, channel):
        """Handle button presses and update selected index."""
        prev_index = self.selected_index
        item_name = self.menu_items[self.selected_index].get("text") or self.menu_items[self.selected_index].get("name", f"Item {self.selected_index}")

        if channel == UP_BUTTON:
            logging.debug("Up Button (GPIO %d) pressed", UP_BUTTON)
            self.selected_index = max(0, self.selected_index - 1)
        elif channel == DOWN_BUTTON:
            logging.debug("Down Button (GPIO %d) pressed", DOWN_BUTTON)
            self.selected_index = min(len(self.menu_items) - 1, self.selected_index + 1)
        elif channel == SELECT_BUTTON:
            logging.info("Select Button (GPIO %d) pressed - Selected: %s", SELECT_BUTTON, item_name)
        elif channel == BACK_BUTTON:
            logging.info("Back Button (GPIO %d) pressed - Triggering Voice Recognition", BACK_BUTTON)
            #Run the voice recognition in a seperate thread
            #recognition_thread = threading.Thread(target=start_voice_recognition)
            #recognition_thread.daemon=True # Daemonize the thread to allow it to exit with the main program
            #recognition_thread.start() # Start the recognition process
            print("I'm working I promise")
        elif channel == RIGHT_BUTTON:
            logging.debug("Right Button (GPIO %d) pressed", RIGHT_BUTTON)
        elif channel == LEFT_BUTTON:
            logging.debug("Left Button (GPIO %d) pressed", LEFT_BUTTON)
        elif channel == VOLUME_UP:
            logging.debug("Volume Up Button (GPIO %d) pressed", VOLUME_UP)
        elif channel == VOLUME_DOWN:
            logging.debug("Volume Down Button (GPIO %d) pressed", VOLUME_DOWN)
        else:
            logging.warning("Unexpected channel: %d", channel)

        # Always call the callback to allow volume or other actions
        try:
            self.callback(self.selected_index, channel)
        except Exception as e:
            logging.error("Callback failed: %s", e)

    def start(self):
        """Add event detection for buttons."""
        logging.debug("Starting button firmware")
        try:
            for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
                GPIO.add_event_detect(pin, GPIO.RISING, callback=self.button_callback, bouncetime=200)
                logging.debug("Added event detection for pin %d", pin)
            logging.info("Button navigation active")
        except Exception as e:
            logging.error("Failed to add event detection: %s", e)
            raise

    def cleanup(self):
        """Clean up GPIO settings."""
        logging.debug("Cleaning up GPIO")
        try:
            for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
                GPIO.remove_event_detect(pin)
            GPIO.cleanup()
            logging.info("GPIO cleanup complete")
        except Exception as e:
            logging.warning("GPIO cleanup failed: %s", e)

def setup_button_firmware(menu_items, selected_index=0, callback=None):
    """Initialize and return a ButtonFirmware instance for button polling."""
    try:
        bf = ButtonFirmware(menu_items, selected_index, callback)
        logging.debug("setup_button_firmware: ButtonFirmware instance created")
        return bf
    except Exception as e:
        logging.error("Failed to setup button firmware: %s", e)
        raise

# Example usage (for testing standalone)
if __name__ == "__main__":
    MENU_ITEMS = [
        {"text": "Item 1", "x": 10, "y": 10},
        {"text": "Item 2", "x": 10, "y": 20},
        {"text": "Item 3", "x": 10, "y": 30},
    ]
    def test_callback(index, channel):
        item_name = MENU_ITEMS[index].get("text", f"Item {index}")
        logging.info("Test callback: Selected index %d - %s, channel %d", index, item_name, channel)

    try:
        bf = setup_button_firmware(MENU_ITEMS, callback=test_callback)
        bf.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bf.cleanup()
        logging.info("Exiting test mode")