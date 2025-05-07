import curses
import time
from button_manager import ButtonManager
from menu_renderer import MenuRenderer

def main():
    try:
        # Initialize button manager for GPIO input
        button_manager = ButtonManager()
        
        # Initialize menu renderer for UI and navigation
        menu_renderer = MenuRenderer()
        
        # Run the menu loop with curses
        #curses is implicit doesnt need stdscr.. look more into it 
        curses.wrapper(lambda stdscr: menu_renderer.draw_menu(stdscr, button_manager))
    except KeyboardInterrupt:
        print("Exiting via KeyboardInterrupt")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":#
    main()