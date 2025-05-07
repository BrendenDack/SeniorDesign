# button_manager.py
from gpiozero import Button
from gpiozero.exc import GPIOZeroError
from action_handlers import FUNCTION_DICTIONARY

class ButtonManager:
    def __init__(self):
        self.buttons = {}
        self.pressed_states = {}
        try:
            self.buttons = {
                "select": Button(26, pull_up=True, bounce_time=0.1),
                "back": Button(16, pull_up=True, bounce_time=0.1),
                "up": Button(4, pull_up=True, bounce_time=0.1),
                "right": Button(22, pull_up=True, bounce_time=0.1),
                "down": Button(20, pull_up=True, bounce_time=0.1),
                "left": Button(21, pull_up=True, bounce_time=0.1),
                "volume_up": Button(23, pull_up=True, bounce_time=0.1),
                "volume_down": Button(24, pull_up=True, bounce_time=0.1),
            }
            self.pressed_states = {key: False for key in self.buttons}
        except GPIOZeroError:
            self.buttons = {key: None for key in ["select", "back", "up", "right", "down", "left", "volume_up", "volume_down"]}
            print("Buttons init Failed. Could not claim Buttons.")
            time.sleep(3)

    def handle_input(self, current_index, options, current_menu_key, stdscr, h, w, menu_renderer):
        if self.buttons["up"] and self.buttons["up"].is_pressed and not self.pressed_states["up"]:
            current_index = (current_index - 1) % len(options)
            self.pressed_states["up"] = True
        elif self.buttons["up"] and not self.buttons["up"].is_pressed:
            self.pressed_states["up"] = False

        if self.buttons["down"] and self.buttons["down"].is_pressed and not self.pressed_states["down"]:
            current_index = (current_index + 1) % len(options)
            self.pressed_states["down"] = True
        elif self.buttons["down"] and not self.buttons["down"].is_pressed:
            self.pressed_states["down"] = False

        if self.buttons["select"] and self.buttons["select"].is_pressed and not self.pressed_states["select"]:
            selected_option = options[current_index]
            menu_renderer.handle_selection(stdscr, selected_option, h, w, current_menu_key)
            self.pressed_states["select"] = True
        elif self.buttons["select"] and not self.buttons["select"].is_pressed:
            self.pressed_states["select"] = False

        if self.buttons["back"] and self.buttons["back"].is_pressed and not self.pressed_states["back"]:
            FUNCTION_DICTIONARY["start_voice"]()
            self.pressed_states["back"] = True
        elif self.buttons["back"] and not self.buttons["back"].is_pressed:
            self.pressed_states["back"] = False

        return current_index