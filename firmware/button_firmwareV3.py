#!/usr/bin/python
# -*- coding:utf-8 -*-

# Now refactored to use GPIO Zero !!

import sys
import time
import logging
from enum import Enum, auto
from functools import partial

try:
    from gpiozero import Button
except ModuleNotFoundError:
    logging.error("GPIO Zero not found. Please install it with 'pip install gpiozero'")
    sys.exit(1)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class Buttons:
    SELECT = 26
    BACK = 16
    UP = 4
    RIGHT = 22
    DOWN = 20
    LEFT = 21
    VOLUME_UP = 23
    VOLUME_DOWN = 24
    
    @classmethod
    def all_pins(cls):
        return [cls.SELECT, cls.BACK, cls.UP, cls.RIGHT, cls.DOWN, cls.LEFT, cls.VOLUME_UP, cls.VOLUME_DOWN]

class NavAction(Enum):
    SELECT = auto()
    BACK = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    
    @classmethod
    def from_pin(cls, pin):
        pin_to_action = {
            Buttons.SELECT: cls.SELECT,
            Buttons.BACK: cls.BACK,
            Buttons.UP: cls.UP,
            Buttons.DOWN: cls.DOWN,
            Buttons.LEFT: cls.LEFT,
            Buttons.RIGHT: cls.RIGHT,
            Buttons.VOLUME_UP: cls.VOLUME_UP,
            Buttons.VOLUME_DOWN: cls.VOLUME_DOWN
        }
        return pin_to_action.get(pin)

class ButtonFirmware:
    _instance = None
    
    @classmethod
    def get_instance(cls, menu_items=None, selected_index=0, callback=None):
        if cls._instance is None:
            if menu_items is None:
                raise ValueError("First call to get_instance must include menu_items")
            cls._instance = cls(menu_items, selected_index, callback)
        elif menu_items is not None:
            cls._instance.update_menu(menu_items, selected_index, callback)
        return cls._instance
    
    def __init__(self, menu_items, selected_index=0, callback=None):
        if not menu_items or not isinstance(menu_items, list):
            logging.error("Menu items must be a non-empty list")
            raise ValueError("Menu items must be a non-empty list")
        if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(menu_items):
            logging.error("Invalid selected_index: %d", selected_index)
            raise ValueError(f"selected_index must be between 0 and {len(menu_items) - 1}")
        
        self.menu_items = menu_items
        self.selected_index = selected_index
        self.callback = callback or self.default_callback
        self.is_active = False
        self.button_objects = {}  # Store GPIO Zero Button objects
        self.setup_gpio()
        logging.debug("ButtonFirmware initialized with %d menu items", len(menu_items))

    def setup_gpio(self):
        logging.debug("Setting up GPIO pins using GPIO Zero")
        try:
            # Clear any existing button objects
            for button in self.button_objects.values():
                button.close()
            self.button_objects = {}

            # Create button objects - note: we use pull_up=False since hardware has external pull-down resistors
            # GPIO Zero defaults to active_state=None which auto-detects based on pull resistors
            for pin in Buttons.all_pins():
                # The bounce_time parameter can be adjusted later for better debouncing
                # Default here is 200ms to match the previous bouncetime value
                self.button_objects[pin] = Button(pin, pull_up=False, bounce_time=0.2)
                logging.debug(f"Created Button object for pin {pin}")
        except Exception as e:
            logging.error("Failed to setup GPIO: %s", e)
            raise

    def default_callback(self, index, action, bf):
        item_name = self.menu_items[index].get("text") or self.menu_items[index].get("name", f"Item {index}")
        logging.debug("Default callback: index=%d, action=%s, item=%s", index, action, item_name)

    def update_menu(self, menu_items, selected_index=0, callback=None):
        if not menu_items or not isinstance(menu_items, list):
            logging.error("Menu items must be a non-empty list")
            raise ValueError("Menu items must be a non-empty list")
        if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(menu_items):
            logging.error("Invalid selected_index: %d", selected_index)
            selected_index = 0
            
        self.menu_items = menu_items
        self.selected_index = selected_index
        if callback:
            self.callback = callback
            logging.debug("Updated menu with %d items and new callback", len(menu_items))

    def button_pressed_handler(self, pin):
        """Handler called when a button is pressed"""
        action = NavAction.from_pin(pin)
        if not action:
            logging.warning("Unexpected pin: %d", pin)
            return
            
        prev_index = self.selected_index
        
        if action == NavAction.UP:
            logging.debug("Up Button (GPIO %d) pressed", Buttons.UP)
            self.selected_index = max(0, self.selected_index - 1)
        elif action == NavAction.DOWN:
            logging.debug("Down Button (GPIO %d) pressed", Buttons.DOWN)
            self.selected_index = min(len(self.menu_items) - 1, self.selected_index + 1)
        
        item_name = self.menu_items[self.selected_index].get("text") or self.menu_items[self.selected_index].get("name", f"Item {self.selected_index}")
        if action == NavAction.SELECT:
            logging.info("Select Button pressed - Selected: %s", item_name)
        elif action == NavAction.BACK:
            logging.info("Back Button pressed")
        elif action == NavAction.RIGHT:
            logging.debug("Right Button pressed")
        elif action == NavAction.LEFT:
            logging.debug("Left Button pressed")
        elif action == NavAction.VOLUME_UP:
            logging.debug("Volume Up Button pressed")
        elif action == NavAction.VOLUME_DOWN:
            logging.debug("Volume Down Button pressed")

        try:
            self.callback(self.selected_index, pin, self)
        except Exception as e:
            logging.error("Callback failed: %s", e)

    def start(self):
        if self.is_active:
            logging.debug("Button firmware already active")
            return
            
        logging.debug("Starting button firmware")
        try:
            # Add event handlers to all buttons
            for pin, button in self.button_objects.items():
                # Remove any existing handlers
                button.when_pressed = None
                # Add new handler
                button.when_pressed = partial(self.button_pressed_handler, pin)
                logging.debug(f"Added event handler for pin {pin}")
            
            self.is_active = True
            logging.info("Button navigation active")
        except Exception as e:
            logging.error("Failed to add event handlers: %s", e)
            raise

    def cleanup(self):
        if not self.is_active:
            logging.debug("Button firmware not active")
            return
            
        logging.debug("Cleaning up button event handlers")
        try:
            # Remove event handlers and close button objects
            for pin, button in self.button_objects.items():
                button.when_pressed = None
                button.close()
                logging.debug(f"Removed event handler for pin {pin}")
            
            self.button_objects = {}
            self.is_active = False
            logging.info("Button event handlers cleanup complete")
        except Exception as e:
            logging.warning("Button cleanup failed: %s", e)

def setup_button_firmware(menu_items, selected_index=0, callback=None):
    try:
        bf = ButtonFirmware.get_instance(menu_items, selected_index, callback)
        logging.debug("setup_button_firmware: ButtonFirmware instance created or updated")
        return bf
    except Exception as e:
        logging.error("Failed to setup button firmware: %s", e)
        raise

if __name__ == "__main__":
    MENU_ITEMS = [
        {"text": "Item 1", "x": 10, "y": 10},
        {"text": "Item 2", "x": 10, "y": 20},
        {"text": "Item 3", "x": 10, "y": 30},
    ]
    def test_callback(index, channel, bf):
        item_name = MENU_ITEMS[index].get("text", f"Item {index}")
        logging.info("Test callback: Selected index %d - %s, channel %d", index, item_name, channel)
        if channel == Buttons.BACK:
            logging.info("Back button pressed, would return to previous menu")

    try:
        bf = setup_button_firmware(MENU_ITEMS, callback=test_callback)
        bf.start()
        print("Button firmware active. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bf.cleanup()
        logging.info("Exiting test mode")