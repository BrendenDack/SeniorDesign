# action_handlers.py
import os
import subprocess
import sys

# Add parent directory to sys.path for external modules
sys.path.append("../")

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

FUNCTION_DICTIONARY = {
    "default_function": clear_console,
    "start_voice": start_voice_recognition,
    "play_song": lambda: subprocess.run(f'ffplay -nodisp -autoexit "Music/{selected_song}"', shell=True),
    "run_calibration": run_calibration,
    "apply_spatial_audio": lambda: run_spatial_audio(f"Music/{selected_song}"),
}