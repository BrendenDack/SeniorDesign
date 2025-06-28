# button_manager.py
import logging
import time
from gpiozero import Button
from gpiozero.exc import GPIOZeroError
from action_handlers import FUNCTION_DICTIONARY
import time

# Setup logging to file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='button_manager.log',
    filemode='w'
)

class ButtonManager:
    def __init__(self):
        self.buttons = {}
        self.pressed_states = {}
        try:
            self.buttons = {
                "select": Button(26, pull_up=False, bounce_time=0.4),
                "back": Button(16, pull_up=False, bounce_time=0.4),
                "up": Button(4, pull_up=False, bounce_time=0.4),
                "right": Button(22, pull_up=False, bounce_time=0.4),
                "down": Button(20, pull_up=False, bounce_time=0.4),
                "left": Button(21, pull_up=False, bounce_time=0.4),
                "volume_up": Button(23, pull_up=False, bounce_time=0.4),
                "volume_down": Button(24, pull_up=False, bounce_time=0.4),
            }
            self.pressed_states = {key: False for key in self.buttons}
            logging.info("GPIO buttons initialized successfully")
            # Check initial states
            time.sleep(1)  # Wait for stabilization
            
            for key, button in self.buttons.items():
                logging.debug(f"Initial state of {key}: is_pressed={button.is_pressed}")
                if button.is_pressed:
                    logging.warning(f"Button {key} is pressed at startup")
        except GPIOZeroError as e:
            logging.error(f"GPIO initialization failed: {e}")
            self.buttons = {key: None for key in ["select", "back", "up", "right", "down", "left", "volume_up", "volume_down"]}
            print("Buttons init Failed. Could not claim Buttons.")
            time.sleep(3)

    def handle_input(self, current_index, options, current_menu_key, stdscr, h, w, menu_renderer):
        logging.debug(f"handle_input called: current_index={current_index}, current_menu_key={current_menu_key}")
        for key, button in self.buttons.items():
            if button:
                logging.debug(f"Button {key}: is_pressed={button.is_pressed}, state={self.pressed_states[key]}")

        # UP button
        if self.buttons["up"] and self.buttons["up"].is_pressed and not self.pressed_states["up"]:
            logging.debug("UP button pressed")
            current_index = (current_index - 1) % len(options)
            self.pressed_states["up"] = True
        elif self.buttons["up"] and not self.buttons["up"].is_pressed and self.pressed_states["up"]:
            logging.debug("UP button released")
            self.pressed_states["up"] = False

        # DOWN button
        if self.buttons["down"] and self.buttons["down"].is_pressed and not self.pressed_states["down"]:
            logging.debug("DOWN button pressed")
            current_index = (current_index + 1) % len(options)
            self.pressed_states["down"] = True
        elif self.buttons["down"] and not self.buttons["down"].is_pressed and self.pressed_states["down"]:
            logging.debug("DOWN button released")
            self.pressed_states["down"] = False

        # SELECT button
        if self.buttons["select"] and self.buttons["select"].is_pressed and not self.pressed_states["select"]:
            logging.debug("SELECT button pressed")
            selected_option = options[current_index]
            menu_renderer.handle_selection(stdscr, selected_option, h, w, current_menu_key)
            self.pressed_states["select"] = True
        elif self.buttons["select"] and not self.buttons["select"].is_pressed and self.pressed_states["select"]:
            logging.debug("SELECT button released")
            self.pressed_states["select"] = False

        # BACK button
        if self.buttons["back"] and self.buttons["back"].is_pressed and not self.pressed_states["back"]:
            logging.debug("BACK button pressed")
            FUNCTION_DICTIONARY["start_voice"]()
            self.pressed_states["back"] = True
        elif self.buttons["back"] and not self.buttons["back"].is_pressed and self.pressed_states["back"]:
            logging.debug("BACK button released")
            self.pressed_states["back"] = False

        logging.debug(f"handle_input returning: current_index={current_index}")
        return current_index