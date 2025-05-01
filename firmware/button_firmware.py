#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import time
import logging
import traceback
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# GPIO Pin Definitions
SELECT_BUTTON = 13   # GPIO 13: Select
BACK_BUTTON = 6      # GPIO 6: Back
UP_BUTTON = 4        # GPIO 4: Up
RIGHT_BUTTON = 22    # GPIO 22: Right
DOWN_BUTTON = 20     # GPIO 20: Down
LEFT_BUTTON = 21     # GPIO 21: Left
VOLUME_UP = 23       # GPIO 23: Volume Up
VOLUME_DOWN = 24     # GPIO 24: Volume Down

class ButtonFirmware:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ButtonFirmware, cls).__new__(cls)
        return cls._instance

    def __init__(self, menu_items, selected_index=0, callback=None):
        if not hasattr(self, '_initialized'):
            if not menu_items or not isinstance(menu_items, list):
                logging.error("Menu items must be a non-empty list")
                raise ValueError("Menu items must be a non-empty list")
            if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(menu_items):
                logging.error("Invalid selected_index: %d", selected_index)
                raise ValueError(f"selected_index must be between 0 and {len(menu_items) - 1}")
            self.menu_items = menu_items
            self.selected_index = selected_index
            self.callback = callback or self.default_callback
            self.active = False
            self.setup_gpio()
            self._initialized = True
            logging.debug("ButtonFirmware initialized with %d menu items", len(menu_items))

    def setup_gpio(self):
        logging.debug("Setting up GPIO pins")
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        except Exception as e:
            logging.error("Failed to setup GPIO: %s\n%s", e, traceback.format_exc())
            raise

    def default_callback(self, index, channel):
        item_name = self.menu_items[index].get("text") or self.menu_items[index].get("name", f"Item {index}")
        logging.debug("Default callback: index=%d, channel=%d, item=%s", index, channel, item_name)

    def button_callback(self, channel):
        if not self.active:
            return
        prev_index = self.selected_index
        item_name = self.menu_items[self.selected_index].get("text") or self.menu_items[self.selected_index].get("name", f"Item {self.selected_index}")

        try:
            if channel == UP_BUTTON:
                logging.debug("Up Button (GPIO %d) pressed", UP_BUTTON)
                self.selected_index = max(0, self.selected_index - 1)
            elif channel == DOWN_BUTTON:
                logging.debug("Down Button (GPIO %d) pressed", DOWN_BUTTON)
                self.selected_index = min(len(self.menu_items) - 1, self.selected_index + 1)
            elif channel == SELECT_BUTTON:
                logging.info("Select Button (GPIO %d) pressed - Selected: %s", SELECT_BUTTON, item_name)
            elif channel == BACK_BUTTON:
                logging.info("Back Button (GPIO %d) pressed", BACK_BUTTON)
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

            self.callback(self.selected_index, channel)
        except Exception as e:
            logging.error("Button callback failed: %s\n%s", e, traceback.format_exc())

    def start(self):
        if self.active:
            logging.warning("ButtonFirmware already active")
            return
        logging.debug("Starting button firmware")
        try:
            for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
                try:
                    GPIO.remove_event_detect(pin)  # Clear existing events
                    GPIO.add_event_detect(pin, GPIO.RISING, callback=self.button_callback, bouncetime=300)
                    logging.debug("Added event detection for pin %d", pin)
                except Exception as e:
                    logging.error("Failed to add event detection for pin %d: %s\n%s", pin, e, traceback.format_exc())
                    raise
            self.active = True
            logging.info("Button navigation active")
        except Exception as e:
            logging.error("Failed to start button firmware: %s\n%s", e, traceback.format_exc())
            self.active = False
            raise

    def stop(self):
        if not self.active:
            return
        logging.debug("Stopping button firmware")
        try:
            for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
                GPIO.remove_event_detect(pin)
            self.active = False
            logging.info("Button navigation stopped")
        except Exception as e:
            logging.warning("Stop button firmware failed: %s\n%s", e, traceback.format_exc())

    def cleanup(self):
        logging.debug("Cleaning up GPIO")
        try:
            self.stop()
            logging.info("GPIO cleanup complete")
        except Exception as e:
            logging.warning("GPIO cleanup failed: %s\n%s", e, traceback.format_exc())

    def update_menu(self, menu_items, selected_index=0, callback=None):
        if not menu_items or not isinstance(menu_items, list):
            logging.error("Menu items must be a non-empty list")
            raise ValueError("Menu items must be a non-empty list")
        if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(menu_items):
            logging.error("Invalid selected_index: %d", selected_index)
            raise ValueError(f"selected_index must be between 0 and {len(menu_items) - 1}")
        self.menu_items = menu_items
        self.selected_index = selected_index
        self.callback = callback or self.default_callback
        self.active = True
        logging.debug("Updated ButtonFirmware with %d menu items", len(menu_items))

def setup_button_firmware(menu_items, selected_index=0, callback=None):
    try:
        bf = ButtonFirmware(menu_items, selected_index, callback)
        logging.debug("setup_button_firmware: ButtonFirmware instance created or updated")
        return bf
    except Exception as e:
        logging.error("Failed to setup button firmware: %s\n%s", e, traceback.format_exc())
        raise

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