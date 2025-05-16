#!/usr/bin/env python3
import json
import sys
import tty
import termios
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy import signal
import pyaudio
import platform
import os
import time
from PIL import Image, ImageDraw, ImageFont

# Configuration
PROFILES_DIR = Path("user_profiles")
HRTF_PATH = Path("HRIRs/")
STEMS = ["bass", "vocals", "drums", "other"]
FS = 48000  # Match calibrateV2.py
DURATION = 1.5
SUPPRESS_ERRORS = True  # Match calibrateV2.py
SCREEN_HEIGHT = 320
SCREEN_WIDTH = 240
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
font_menu = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

def get_available_angles(hrtf_path: Path, subject: str) -> list:
    """Load available angles for a subject from HRIR files."""
    angles = []
    for file in hrtf_path.glob(f"Subject_{subject}_*_0.mat"):
        try:
            angle = int(file.stem.split('_')[-2])
            angles.append(angle)
        except ValueError:
            continue
    return sorted(angles)

def snap_to_nearest_angle(target: float, available_angles: list) -> float:
    """Snap target angle to the nearest available angle."""
    if not available_angles:
        return target
    return available_angles[np.argmin(np.abs(np.array(available_angles) - target))]

def generate_swept_sine(duration: float, fs: int) -> np.ndarray:
    """Generate a linear chirp for better audibility."""
    t = np.linspace(0, duration, int(duration * fs))
    return 0.05 * signal.chirp(t, f0=500, f1=4000, t1=duration, method='linear')

def play_audio(audio_data: np.ndarray, fs: int) -> bool:
    """
    Robust audio playback with OS-level stderr suppression.
    Uses device index 0 (expected: TX USB Audio, hw:2,0).
    """
    print(f"Initializing audio playback (SUPPRESS_ERRORS={SUPPRESS_ERRORS})...")
    sys.stdout.flush()

    p = None
    stream = None
    try:
        if SUPPRESS_ERRORS:
            stderr_fd = sys.stderr.fileno()
            stderr_save = os.dup(stderr_fd)
            devnull_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull_fd, stderr_fd)
            os.close(devnull_fd)

            p = pyaudio.PyAudio()
            device_index = 0
            dev_info = p.get_device_info_by_index(device_index)
            if dev_info['maxOutputChannels'] < 2 or dev_info['hostApi'] != 0:
                raise RuntimeError(f"Device at index {device_index} does not support stereo ALSA output")
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=int(fs),
                output=True,
                output_device_index=device_index
            )
            stream.write(audio_data.astype(np.float32).tobytes())
            stream.stop_stream()
            stream.close()
            stream = None
            p.terminate()
            p = None

            os.dup2(stderr_save, stderr_fd)
            os.close(stderr_save)
        else:
            p = pyaudio.PyAudio()
            device_index = 0
            dev_info = p.get_device_info_by_index(device_index)
            if dev_info['maxOutputChannels'] < 2 or dev_info['hostApi'] != 0:
                raise RuntimeError(f"Device at index {device_index} does not support stereo ALSA output")
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=int(fs),
                output=True,
                output_device_index=device_index
            )
            stream.write(audio_data.astype(np.float32).tobytes())
            stream.stop_stream()
            stream.close()
            stream = None
            p.terminate()
            p = None

        print(f"Selected audio device: {dev_info['name']} (Index: {device_index})")
        sys.stdout.flush()
        return True
    except Exception as e:
        print(f"Audio Error: {str(e)}")
        sys.stderr.flush()
        return False
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        if p is not None:
            p.terminate()
        sys.stdout.flush()
        sys.stderr.flush()

def get_key() -> str:
    """Read a single key press without echoing."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def get_input(up=None, down=None, left=None, right=None, enter=None) -> str:
    """Read a single input from GPIO buttons."""
    time.sleep(0.2)
    if up and up.is_pressed:
        return 'w'
    if down and down.is_pressed:
        return 's'
    if right and right.is_pressed:
        return 'd'
    if left and left.is_pressed:
        return 'a'
    if enter and enter.is_pressed:
        return '\n'
    return ''

def select_profile(profiles_dir: Path, up=None, down=None, left=None, right=None, enter=None, lcd=None) -> tuple[Path, dict]:
    profiles = sorted(profiles_dir.glob("*.json"))
    if not profiles:
        default_profile = {
            "hrtf_subject": "003",
            "effective_radius": 8.5,
            "head_width": 15.2,
            "head_length": 19.0,
            "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
        }
        return None, default_profile

    selected_idx = 0

    # Setup for drawing
    HEIGHT, WIDTH = 240, 320
    font = ImageFont.load_default()
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        pass  # Fallback to default

    def draw_screen():
        image = Image.new("RGB", (WIDTH, HEIGHT), "WHITE")
        draw = ImageDraw.Draw(image)
        title = "Select a profile:"
        draw.text((10, 10), title, font=font, fill="BLACK")

        start_y = 40
        line_height = 20
        for i, profile in enumerate(profiles):
            y = start_y + i * line_height
            marker = ">" if i == selected_idx else " "
            text = f"{marker} {profile.name[:26]}"  # clip name if too long
            draw.text((10, y), text, font=font, fill="RED" if i == selected_idx else "BLACK")
        image = image.rotate(90, expand=True)
        lcd.ShowImage(image)

    while True:
        draw_screen()
        ch = get_input(up=up, down=down, right=right, left=left, enter=enter)

        if ch in ('\r', '\n'):
            try:
                with open(profiles[selected_idx], 'r') as f:
                    profile_data = json.load(f)
                if not all(k in profile_data for k in ['hrtf_subject', 'effective_radius']):
                    return None, {
                        "hrtf_subject": "003",
                        "effective_radius": 8.5,
                        "head_width": 15.2,
                        "head_length": 19.0,
                        "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
                    }
                return profiles[selected_idx], profile_data
            except json.JSONDecodeError:
                return None, {
                    "hrtf_subject": "003",
                    "effective_radius": 8.5,
                    "head_width": 15.2,
                    "head_length": 19.0,
                    "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
                }
        elif ch == 'w' and selected_idx > 0:
            selected_idx -= 1
        elif ch == 's' and selected_idx < len(profiles) - 1:
            selected_idx += 1


def select_stem(up=None, down=None, left=None, right=None, enter=None, lcd=None) -> str:
    selected_idx = 0
    HEIGHT, WIDTH = 240, 320
    font = font_menu  # Reuse existing

    def draw_screen():
        img = Image.new("RGB", (WIDTH, HEIGHT), "WHITE")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Select a stem to edit:", font=font, fill="BLACK")

        for i, stem in enumerate(STEMS):
            y = 40 + i * 30
            color = "RED" if i == selected_idx else "BLACK"
            marker = ">" if i == selected_idx else " "
            draw.text((10, y), f"{marker} {stem.capitalize()}", font=font, fill=color)

        img = img.rotate(90, expand=True)
        lcd.ShowImage(img)

    while True:
        draw_screen()
        ch = get_input(up=up, down=down, right=right, left=left, enter=enter)
        if ch in ('\r', '\n'):
            return STEMS[selected_idx]
        elif ch == 'w' and selected_idx > 0:
            selected_idx -= 1
        elif ch == 's' and selected_idx < len(STEMS) - 1:
            selected_idx += 1


def get_angle_input(current_angle: float, available_angles: list, subject: str, up=None, down=None, left=None, right=None, enter=None, lcd=None) -> float:
    angle = current_angle
    stimulus = generate_swept_sine(DURATION, FS)
    HEIGHT, WIDTH = 240, 320
    font = font_menu

    def draw_screen():
        img = Image.new("RGB", (WIDTH, HEIGHT), "WHITE")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Adjust Azimuth Angle", font=font, fill="BLACK")
        draw.text((10, 50), f"Current: {angle:.1f}°", font=font, fill="BLUE")
        draw.text((10, 80), f"Snapped: {snap_to_nearest_angle(angle, available_angles):.1f}°", font=font, fill="GREEN")
        draw.text((10, 120), "Up/Down: ±10°  Left/Right: ±1°", font=font, fill="BLACK")
        draw.text((10, 150), "Return: Preview", font=font, fill="BLACK")
        draw.text((10, 180), "Enter to Confirm", font=font, fill="BLACK")
        img = img.rotate(90, expand=True)
        lcd.ShowImage(img)

    while True:
        draw_screen()
        ch = get_input(up=up, down=down, right=right, left=left, enter=enter)
        if ch in ('\r', '\n'):
            return snap_to_nearest_angle(angle, available_angles)
        elif ch == 'w':
            angle += 10
        elif ch == 's':
            angle -= 10
        elif ch == 'd':
            angle += 1
        elif ch == 'a':
            angle -= 1
        elif ch == 'p':
            hrtf_file = HRTF_PATH / f"Subject_{subject}_{int(snap_to_nearest_angle(angle, available_angles))}_0.mat"
            try:
                data = loadmat(str(hrtf_file))
                if 'hrir_left' not in data or 'hrir_right' not in data:
                    raise KeyError("Missing hrir_left or hrir_right in HRIR file")
                spatial_audio = np.column_stack([
                    signal.lfilter(data['hrir_left'].flatten(), 1, stimulus),
                    signal.lfilter(data['hrir_right'].flatten(), 1, stimulus)
                ])
                play_audio(spatial_audio, FS)
            except Exception as e:
                img = Image.new("RGB", (WIDTH, HEIGHT), "WHITE")
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), f"Preview error: {str(e)}", font=font, fill="RED")
                img = img.rotate(90, expand=True)
                lcd.ShowImage(img)
                time.sleep(2)


def edit_profile(up=None, down=None, left=None, right=None, enter=None, lcd=None):
    """Main profile editing workflow."""
    img = Image.new("RGB", (SCREEN_HEIGHT, SCREEN_WIDTH), "WHITE")
    draw = ImageDraw.Draw(img)
    msg = "=== Edit HRTF Profile Stem Directions ==="
    print(msg)
    draw.text((SCREEN_HEIGHT/2, 5), msg, font=font_menu, fill="BLACK")
    lcd.ShowImage(img)
    time.sleep(1)
    lcd.clear()
    profile_path, profile_data = select_profile(PROFILES_DIR, up=up, down=down, right=right, left=left, enter=enter, lcd=lcd)
    
    # Initialize stem_directions if not present
    if "stem_directions" not in profile_data:
        profile_data["stem_directions"] = {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
    
    # Load available angles for the subject's HRIRs
    subject = profile_data["hrtf_subject"]
    available_angles = get_available_angles(HRTF_PATH, subject)
    if not available_angles:
        print(f"Warning: No HRIR files found for Subject_{subject} in {HRTF_PATH}. Angles will not be snapped.")
        available_angles = list(range(-180, 181))  # Fallback to all integers
    
    while True:
        stem = select_stem(up=up, down=down, right=right, left=left, enter=enter, lcd=lcd)
        current_angle = profile_data["stem_directions"].get(stem, 0)
        new_angle = get_angle_input(current_angle, available_angles, subject, up=up, down=down, right=right, left=left, enter=enter, lcd=lcd)
        profile_data["stem_directions"][stem] = new_angle
        
        print("\nCurrent stem directions:")
        for s in STEMS:
            angle = profile_data["stem_directions"].get(s, 0)
            snapped_angle = snap_to_nearest_angle(angle, available_angles)
            print(f"  {s.capitalize()}: {snapped_angle:.1f}°")
        
        print("\nPress Enter to save and exit, or any other key to edit another stem.")
        ch = get_input(up=up, down=down, right=right, left=left, enter=enter)
        if ch in ('\r', '\n'):
            break
    
    # Save updated profile
    if profile_path is None:
        user_id = input("Enter a new user ID for the profile: ").strip()
        profile_path = PROFILES_DIR / f"{user_id}.json"
        os.makedirs(PROFILES_DIR, exist_ok=True)
    
    try:
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        print(f"\nProfile updated and saved to {profile_path}")
        print("Use this profile in test.py to apply custom stem directions.")
        return "Profile Data Saved Successfully!"
    except Exception as e:
        print(f"Error saving profile: {str(e)}")

if __name__ == "__main__":
    edit_profile()