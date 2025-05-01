#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import logging
import threading
from stt import start_voice_recognition

try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    print("Error: RPi.GPIO not found. Please install it with 'pip install RPi.GPIO'")
    sys.exit(1)

# GPIO Pin Definitions
SELECT_BUTTON = 26    # GPIO 26: Select
BACK_BUTTON = 16      # GPIO 16: Back
UP_BUTTON = 4        # GPIO 1: Up
RIGHT_BUTTON = 22    # GPIO 22: Right
DOWN_BUTTON = 20     # GPIO 20: Down
LEFT_BUTTON = 21     # GPIO 21: Left
VOLUME_UP = 23       # GPIO 23: Volume up
VOLUME_DOWN = 24     # GPIO 24: Volume down

class ButtonFirmware:
    def __init__(self, menu_items, selected_index=0, callback=None):
        """Initialize button firmware with menu items and optional custom callback."""
        self.menu_items = menu_items
        self.selected_index = selected_index
        self.callback = callback  # Custom callback function provided by the GUI
        self.setup_gpio()

    def setup_gpio(self):
        """Setup GPIO pins with pull-down resistors."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        GPIO.setup(SELECT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(BACK_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(UP_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(RIGHT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(DOWN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(LEFT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(VOLUME_UP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(VOLUME_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def button_callback(self, channel):
        """Handle button presses and update selected index."""
        prev_index = self.selected_index
        
        if channel == UP_BUTTON:
            print("Up Button (GPIO 1) pressed")
        elif channel == DOWN_BUTTON:
            print("Down Button (GPIO 20) pressed")
        elif channel == SELECT_BUTTON:
            print(f"Select Button (GPIO 5) pressed")
        elif channel == BACK_BUTTON:
            print("Back Button (GPIO 6) pressed - Returning to previous state")
            #Run the voice recognition in a seperate thread
            recognition_thread = threading.Thread(target=start_voice_recognition)
            recognition_thread.daemon=True # Daemonize the thread to allow it to exit with the main program
            recognition_thread.start() # Start the recognition process
        elif channel == RIGHT_BUTTON:
            print(f"Right Button (GPIO 22) pressed - Selected: {self.menu_items[self.selected_index]['text']}")
        elif channel == LEFT_BUTTON:
            print("Left Button (GPIO 21) pressed - No action defined yet")
        elif channel == VOLUME_DOWN:
            print("Left Button (GPIO 24) pressed - No action defined yet")
        elif channel == VOLUME_UP:
            print("Left Button (GPIO 23) pressed - No action defined yet")
        else:
            print(f"Unexpected channel: {channel}")
        
        # Call the custom callback if provided and index changed
        if self.callback and prev_index != self.selected_index:
            self.callback(self.selected_index)

    def start(self):
        """Add event detection for buttons."""
        GPIO.add_event_detect(SELECT_BUTTON, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(BACK_BUTTON, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(UP_BUTTON, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(RIGHT_BUTTON, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(DOWN_BUTTON, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(LEFT_BUTTON, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(VOLUME_UP, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        GPIO.add_event_detect(VOLUME_DOWN, GPIO.RISING, callback=self.button_callback, bouncetime=200)
        print("Button navigation active.")

    def cleanup(self):
        """Clean up GPIO settings."""
        GPIO.cleanup()
        logging.info("GPIO cleanup complete.")

# Example usage (for testing standalone):
if __name__ == "__main__":
    MENU_ITEMS = [
        {"text": "Item 1", "x": 10, "y": 10},
        {"text": "Item 2", "x": 10, "y": 20},
        {"text": "Item 3", "x": 10, "y": 30},
    ]
    def test_callback(index):
        print(f"Test callback: Selected index {index} - {MENU_ITEMS[index]['text']}")
    
    bf = ButtonFirmware(MENU_ITEMS, callback=test_callback)
    bf.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        bf.cleanup()