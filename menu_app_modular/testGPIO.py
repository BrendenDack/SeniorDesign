import time
from button_manager import ButtonManager

def main():
    manager = ButtonManager()
    
    print("Press a button to test...")
    
    while True:
        for key, button in manager.buttons.items():
            if button and button.is_pressed:
                print(f"Button pressed: {key}")
                time.sleep(0.5)  # Avoid rapid multiple detections

if __name__ == "__main__":
    main()
