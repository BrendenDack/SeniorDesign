# menu_renderer.py
import curses
import sys
from datetime import datetime
from menu_config import MENUS
from music_loader import load_music_files, CURRENT_PAGE, ALL_MUSIC_FILES
from action_handlers import FUNCTION_DICTIONARY
import subprocess
import time

# Add parent directory to sys.path for external modules
sys.path.append("../")

try:
    from battery_monitor import get_battery_info
except ModuleNotFoundError:
    def get_battery_info():
        return ("Unknown", 0)  # Fallback: unknown status, 0%
    print("Warning: 'battery_monitor' module not found. Battery info disabled.")

class MenuRenderer:
    def __init__(self):
        self.menu_stack = ["main"]
        self.current_index = 0
        self.selected_song = None

    def handle_selection(self, stdscr, selected_option, h, w, current_menu_key):
        label = selected_option["label"]
        target = selected_option.get("target")
        action = selected_option.get("action")
        action_type = selected_option.get("action_type", "shell")

        if target == "back":
            if len(self.menu_stack) > 1:
                self.menu_stack.pop()
                self.current_index = 0
        elif target == "next_page":
            load_music_files(CURRENT_PAGE + 1)
            self.current_index = 0
        elif target == "prev_page":
            load_music_files(CURRENT_PAGE - 1)
            self.current_index = 0
        elif target and target in MENUS:
            if selected_option.get("action_type") == "dynamic" and target == "submenu_songs":
                load_music_files(page=0)
            self.menu_stack.append(target)
            self.current_index = 0
        elif current_menu_key == "submenu_songs" and label.lower() not in ["next page", "previous page", "back"]:
            self.selected_song = label
            self.menu_stack.append("submenu_song_options")
            self.current_index = 0
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

    def draw_menu(self, stdscr, button_manager):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            now = datetime.now()
            time_str = now.strftime("%I:%M:%S %p")
            stdscr.addstr(0, w - len(time_str) - 1, time_str)
            battery = get_battery_info()
            battery_str = f"{battery[1]}% {battery[0]}"
            stdscr.addstr(1, w - len(battery_str) - 1, battery_str)

            current_menu_key = self.menu_stack[-1]
            current_menu = MENUS[current_menu_key]
            options = current_menu["options"]
            title = current_menu["title"]

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

            try:
                key = stdscr.getch()
            except Exception:
                key = -1

            if key == curses.KEY_UP:
                self.current_index = (self.current_index - 1) % len(options)
            elif key == curses.KEY_DOWN:
                self.current_index = (self.current_index + 1) % len(options)
            elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
                selected_option = options[self.current_index]
                self.handle_selection(stdscr, selected_option, h, w, current_menu_key)
            elif key in [curses.KEY_BACKSPACE, 127]:
                FUNCTION_DICTIONARY["start_voice"]()

            self.current_index = button_manager.handle_input(self.current_index, options, current_menu_key, stdscr, h, w, self)

            time.sleep(0.05)