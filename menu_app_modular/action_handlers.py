# action_handlers.py
import os
import time
import subprocess
import sys
import threading

# Add parent directory to sys.path for external modules
sys.path.append("../")

# Global variables for voice recognition
recognition_running = False
recognition_thread = None

try:
    from stt import start_voice_recognition
except (ModuleNotFoundError, Exception) as e:
    def start_voice_recognition():
        print(f"Voice recognition unavailable: {str(e)}. Check if 'vosk-model-small-en-us-0.15' is in ~/SeniorDesignCode/github_code/SeniorDesign/")
    print(f"Warning: Failed to load 'stt' module or Vosk model: {str(e)}. Voice recognition disabled. Ensure 'vosk-model-small-en-us-0.15' is in ../")

try:
    from calibrateUserProfile import run_calibration
except ModuleNotFoundError:
    def run_calibration():
        print("Calibration unavailable: 'calibrateUserProfile' module not found")
    print("Warning: 'calibrateUserProfile' module not found. Calibration disabled.")

try:
    from utility import run_spatial_audio
except ModuleNotFoundError:
    def run_spatial_audio(*args, **kwargs):
        print("Spatial audio unavailable: 'utility' module not found")
    print("Warning: 'utility' module not found. Spatial audio disabled.")

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def start_voice():
    global recognition_running, recognition_thread
    if recognition_running:
        print("Voice recognition already running, ignoring press")
        return
    def recognition_wrapper():
        global recognition_running
        recognition_running = True
        try:
            start_voice_recognition()
        except Exception as e:
            print(f"Voice recognition error: {e}")
        finally:
            recognition_running = False
            print("Voice recognition ended")
    recognition_thread = threading.Thread(target=recognition_wrapper)
    recognition_thread.daemon = True
    recognition_thread.start()

FUNCTION_DICTIONARY = {
    "default_function": clear_console,
    "start_voice": start_voice,
    "play_song": lambda: subprocess.run(f'ffplay -nodisp -autoexit "Music/{selected_song}"', shell=True) if selected_song else print("No song selected"),
    "run_calibration": run_calibration,
    "apply_spatial_audio": lambda: run_spatial_audio(f"Music/{selected_song}") if selected_song else print("No song selected"),
}