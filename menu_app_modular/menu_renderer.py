import curses
import sys
import logging
import subprocess
import time
from datetime import datetime
from menu_config import MENUS
from music_loader import load_music_files, CURRENT_PAGE, ALL_MUSIC_FILES
from action_handlers import FUNCTION_DICTIONARY

# Setup logging to file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='menu_renderer.log',
    filemode='w'
)

# Add parent directory to sys.path for external modules
sys.path.append("../")

try:
    from battery_monitor import get_battery_info
except ModuleNotFoundError:
    def get_battery_info():
        return ("Unknown", 0)  # Fallback: unknown status, 0%
    logging.warning("battery_monitor module not found. Battery info disabled.")

class MenuRenderer:
    def __init__(self):
        self.menu_stack = ["main"]
        self.current_index = 0
        self.selected_song = None
        self.initialized = 0  # Count cycles
        logging.info(f"MenuRenderer initialized, menu_stack={self.menu_stack}")
        time.sleep(0.5)  # Stabilize GPIO

    def handle_selection(self, stdscr, selected_option, h, w, current_menu_key):
        label = selected_option["label"]
        target = selected_option.get("target")
        action = selected_option.get("action")
        action_type = selected_option.get("action_type", "shell")
        logging.debug(f"handle_selection: menu_stack={self.menu_stack}, current_menu_key={current_menu_key}, selected_option={selected_option}")

        if target == "back":
            if len(self.menu_stack) > 1:
                self.menu_stack.pop()
                self.current_index = 0
                logging.info("Navigated back")
        elif target == "next_page":
            load_music_files(CURRENT_PAGE + 1)
            self.current_index = 0
            logging.info("Next page loaded")
        elif target == "prev_page":
            load_music_files(CURRENT_PAGE - 1)
            self.current_index = 0
            logging.info("Previous page loaded")
        elif target and target in MENUS:
            if selected_option.get("action_type") == "dynamic" and target == "submenu_songs":
                load_music_files(page=0)
            self.menu_stack.append(target)
            self.current_index = 0
            logging.info(f"Navigated to menu: {target}")
        elif current_menu_key == "submenu_songs" and label.lower() not in ["next page", "previous page", "back"]:
            self.selected_song = label
            self.menu_stack.append("submenu_song_options")
            self.current_index = 0
            logging.info(f"Selected song: {label}")
        elif action:
            if action_type == "shell":
                try:
                    result = subprocess.run(action, shell=True, text=True, capture_output=True)
                    output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
                except Exception as e:
                    output = f"Shell Error: {e}"
            elif action_type == "python":
                func = FUNCTION_DICTIONARY.get(action)
                if func:
                    try:
                        curses.endwin()
                        output = func()
                    except Exception as e:
                        output = f"Python Error: {e}"
                    finally:
                        stdscr = curses.initscr()
                        curses.noecho()
                        curses.cbreak()
                        stdscr.keypad(True)
                        stdscr.clear()
                        curses.doupdate()
                else:
                    output = f"Function '{action}' not found"
            else:
                output = f"Unknown action type: {action_type}"

            stdscr.clear()
            if output is None:
                output = "Finished Task"
            lines = str(output).split("\n")
            for i, line in enumerate(lines):
                y = max(0, min(h - 1, h // 2 - len(lines) // 2 + i))
                x = max(0, min(w - 1, w // 2 - len(line) // 2))
                try:
                    stdscr.addstr(y, x, line[:w - x])
                except curses.error:
                    pass
            stdscr.refresh()
            time.sleep(2)
            logging.info(f"Action executed: {action}")
        else:
            stdscr.clear()
            message = f"You selected: {label}"
            y = max(0, min(h - 1, h // 2))
            x = max(0, min(w - 1, w // 2 - len(message) // 2))
            try:
                stdscr.addstr(y, x, message[:w - x])
            except curses.error:
                pass
            stdscr.refresh()
            time.sleep(1)
            logging.info(f"Displayed selection: {label}")

    def draw_menu(self, stdscr, button_manager):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        logging.info("Starting draw_menu loop")

        # Clear keyboard buffer
        while stdscr.getch() != -1:
            pass

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            current_menu_key = self.menu_stack[-1]
            current_menu = MENUS[current_menu_key]
            title = current_menu["title"]
            logging.debug(f"draw_menu: menu_stack={self.menu_stack}, current_menu_key={current_menu_key}, title={title}, initialized={self.initialized}")

            now = datetime.now()
            time_str = now.strftime("%I:%M:%S %p")
            stdscr.addstr(0, w - len(time_str) - 1, time_str)
            battery = get_battery_info()
            battery_str = str(battery[0])
            stdscr.addstr(1, w - len(battery_str) - 1, battery_str)

            options = current_menu["options"]
            stdscr.addstr(1, w // 2 - len(title) // 2, title, curses.A_BOLD)

            for idx, option in enumerate(options):
                label = option["label"]
                x = w // 2 - len(label) // 2
                y = h // 2 - len(options) // 2 + idx
                if idx == self.current_index:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, label)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, label)

            stdscr.refresh()
            logging.debug("GUI refreshed")

            if self.initialized < 20:  # Skip inputs for ~1s (20 cycles at 0.05s)
                self.initialized += 1
                logging.info(f"Skipping input handling, cycle {self.initialized}")
                time.sleep(0.05)
                continue

            try:
                key = stdscr.getch()
                logging.debug(f"Key pressed: {key}")
            except Exception as e:
                key = -1
                logging.error(f"Error reading key: {e}")

            if key == curses.KEY_UP:
                self.current_index = (self.current_index - 1) % len(options)
                logging.info(f"Keyboard UP: current_index={self.current_index}")
            elif key == curses.KEY_DOWN:
                self.current_index = (self.current_index + 1) % len(options)
                logging.info(f"Keyboard DOWN: current_index={self.current_index}")
            elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
                selected_option = options[self.current_index]
                self.handle_selection(stdscr, selected_option, h, w, current_menu_key)
                logging.info("Keyboard ENTER: selection handled")
            elif key in [curses.KEY_BACKSPACE, 127]:
                FUNCTION_DICTIONARY["start_voice"]()
                logging.info("Keyboard BACKSPACE: start_voice triggered")

            logging.debug(f"Before handle_input: menu_stack={self.menu_stack}")
            self.current_index = button_manager.handle_input(self.current_index, options, current_menu_key, stdscr, h, w, self)
            logging.debug(f"After handle_input: menu_stack={self.menu_stack}")

            time.sleep(0.05)