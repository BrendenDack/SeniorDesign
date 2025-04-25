import torch
import torchaudio
import numpy as np
from scipy.io import loadmat, wavfile
from scipy.signal import lfilter, resample
import os
from IPython.display import Audio, display
from pydub import AudioSegment
import time as Time
import matplotlib.pyplot as plt
import librosa
from pathlib import Path
import json
import sys
import tty
import termios

def generate_white_noise(duration, fs):
    return np.random.normal(0, 0.5, int(duration * fs))

def read_wav_file(filename, fs=44100):
    data, fs = librosa.load(str(filename), sr=fs)
    return fs, data

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

def select_profile(profiles_dir: Path) -> dict:
    """Prompt user to select a valid profile from user_profiles using WASD."""
    profiles = sorted(profiles_dir.glob("*.json"))
    if not profiles:
        print("No profiles found in user_profiles/. Using default HRTF (Subject_003).")
        return {"hrtf_subject": "003", "effective_radius": 8.5, "head_width": 15.2, "head_length": 19.0, "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}}

    print("\nSelect a user profile (w/s to navigate, Enter to select):")
    selected_idx = 0
    while True:
        for i, profile in enumerate(profiles):
            marker = ">" if i == selected_idx else " "
            print(f"{marker} {profile.name}")
        sys.stdout.flush()
        
        ch = get_key()
        if ch in ('\r', '\n'):
            try:
                with open(profiles[selected_idx], 'r') as f:
                    profile_data = json.load(f)
                if not all(k in profile_data for k in ['hrtf_subject', 'effective_radius']):
                    print(f"Invalid profile {profiles[selected_idx].name}: Missing required fields.")
                    return {"hrtf_subject": "003", "effective_radius": 8.5, "head_width": 15.2, "head_length": 19.0, "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}}
                print(f"\nSelected profile: {profiles[selected_idx].name}")
                print(f"  HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
                print(f"  Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
                print(f"  Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
                print(f"  Effective Radius: {profile_data['effective_radius']:.2f} cm")
                return profile_data
            except json.JSONDecodeError:
                print(f"Error: {profiles[selected_idx].name} is not a valid JSON file.")
                return {"hrtf_subject": "003", "effective_radius": 8.5, "head_width": 15.2, "head_length": 19.0, "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}}
        elif ch.lower() == 'w' and selected_idx > 0:
            selected_idx -= 1
        elif ch.lower() == 's' and selected_idx < len(profiles) - 1:
            selected_idx += 1

def HRTF(az, n, profile: dict, available_angles: list):
    subject = profile.get("hrtf_subject", "003")
    effective_radius = profile.get("effective_radius", 8.5)
    az = int(snap_to_nearest_angle(az, available_angles))  # Snap to valid angle
    hrtf_path = Path(f"/home/advented/HRIRs/Subject_{subject}_{az}_0.mat")
    try:
        data = loadmat(str(hrtf_path))
        if 'hrir_left' not in data or 'hrir_right' not in data:
            raise KeyError("Missing hrir_left or hrir_right in HRIR file")
        hrir_left = data['hrir_left'].flatten()
        hrir_right = data['hrir_right'].flatten()
    except (FileNotFoundError, KeyError) as e:
        print(f"Error: HRTF file {hrtf_path} not found or invalid ({str(e)}). Using default Subject_003_0.")
        hrtf_path = Path(f"/home/advented/HRIRs/Subject_003_0_0.mat")
        data = loadmat(str(hrtf_path))
        hrir_left = data['hrir_left'].flatten()
        hrir_right = data['hrir_right'].flatten()
        az = 0
    
    scale = effective_radius / 8.5
    hrir_left_len = len(hrir_left)
    new_len = int(hrir_left_len * scale)
    hrir_left = resample(hrir_left, new_len) if scale != 1 else hrir_left
    hrir_right = resample(hrir_right, new_len) if scale != 1 else hrir_right
    
    y_left = lfilter(hrir_left, 1, n)
    y_right = lfilter(hrir_right, 1, n)
    y = np.column_stack((y_left, y_right)).astype(np.float32)
    return y

def plot_signal(x, fn, title='Original Signal'):
    plt.figure(figsize=(10, 4))
    plt.plot(x, color='blue')
    plt.title(title)
    plt.xlabel('Sample Index')
    plt.ylabel('Amplitude')
    plt.grid(True)
    plt.savefig(fn)
    print('Plot saved')

def Stereo_to_mono(signal):
    left = signal[:, 0]
    right = signal[:, 1]
    x = left + right
    peak = np.max(np.abs(x))
    return 0.5 * (x / peak)

start_program = Time.perf_counter()
use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")

fs, data = read_wav_file("Original.wav", 44100)

from openunmix import predict
estimates = predict.separate(
    torch.as_tensor(data).float(),
    rate=fs,
    device=device
)
for target, estimate in estimates.items():
    print(target)
    audio = estimate.detach().cpu().numpy()[0]
    display(Audio(audio, rate=fs))

estimates_numpy = {}
for target, estimate in estimates.items():
    estimates_numpy[target] = torch.squeeze(estimate).detach().cpu().numpy().T

profiles_dir = Path("/home/advented/audioProductV1/projectCode/SeniorDesign/user_profiles")
profile = select_profile(profiles_dir)

# Validate stem_directions
stems = ["bass", "vocals", "drums", "other"]
if "stem_directions" not in profile or not all(s in profile["stem_directions"] for s in stems):
    print("Warning: Invalid or missing stem_directions in profile. Using defaults (0°).")
    profile["stem_directions"] = {s: 0 for s in stems}
else:
    # Ensure stem_directions are numeric
    for s in stems:
        try:
            profile["stem_directions"][s] = float(profile["stem_directions"][s])
        except (TypeError, ValueError):
            print(f"Warning: Invalid angle for {s} ({profile['stem_directions'][s]}). Using 0°.")
            profile["stem_directions"][s] = 0

# Load available angles for the subject
hrtf_path = Path("/home/advented/HRIRs/")
subject = profile.get("hrtf_subject", "003")
available_angles = get_available_angles(hrtf_path, subject)
if not available_angles:
    print(f"Warning: No HRIR files found for Subject_{subject}. Using default angles.")
    available_angles = [0]

# Snap stem directions and check for large errors
stem_angles = {}
for s in stems:
    target_angle = profile["stem_directions"][s]
    snapped_angle = snap_to_nearest_angle(target_angle, available_angles)
    if abs(target_angle - snapped_angle) > 10:
        print(f"Warning: Large snapping error for {s}: {target_angle}° → {snapped_angle}°. Consider adjusting in editProfiles.py.")
    stem_angles[s] = snapped_angle

# Print applied angles
print("\nApplying stem directions:")
for s in stems:
    print(f"  {s.capitalize()}: {stem_angles[s]:.1f}°")

start = Time.perf_counter()
modified_bass = HRTF(stem_angles["bass"], Stereo_to_mono(estimates_numpy["bass"]), profile, available_angles)
modified_drums = HRTF(stem_angles["drums"], Stereo_to_mono(estimates_numpy["drums"]), profile, available_angles)
modified_other = HRTF(stem_angles["other"], Stereo_to_mono(estimates_numpy["other"]), profile, available_angles)
modified_vocals = HRTF(stem_angles["vocals"], Stereo_to_mono(estimates_numpy["vocals"]), profile, available_angles)
end = Time.perf_counter()

Total_time = end - start
print("HRTF time taken: " + str(Total_time))

sample_rate = 44100
wavfile.write('vocals.wav', sample_rate, modified_vocals)
wavfile.write('other.wav', sample_rate, modified_other)
wavfile.write('drums.wav', sample_rate, modified_drums)
wavfile.write('bass.wav', sample_rate, modified_bass)

summed_song = (modified_vocals + modified_bass + modified_other + modified_drums) / 4
wavfile.write('combined.wav', sample_rate, summed_song)

wavfile.write('test.wav', sample_rate, 2 * Stereo_to_mono(estimates_numpy['vocals']))

end_program = Time.perf_counter()
Total_time = end_program - start_program
print("Total time taken for program: " + str(Total_time))