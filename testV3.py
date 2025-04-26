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

def select_profile(profiles_dir: Path) -> dict:
    """Prompt user to select a valid profile from user_profiles using WASD."""
    profiles = sorted(profiles_dir.glob("*.json"))
    if not profiles:
        print("No profiles found in user_profiles/. Using default HRTF (Subject_003).")
        return {
            "hrtf_subject": "003",
            "effective_radius": 8.5,
            "head_width": 15.2,
            "head_length": 19.0,
            "stem_directions": {"bass": -80, "drums": 80, "other": -45, "vocals": 15}
        }

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
                required_fields = ['hrtf_subject', 'effective_radius']
                if not all(k in profile_data for k in required_fields):
                    print(f"Invalid profile {profiles[selected_idx].name}: Missing required fields.")
                    return {
                        "hrtf_subject": "003",
                        "effective_radius": 8.5,
                        "head_width": 15.2,
                        "head_length": 19.0,
                        "stem_directions": {"bass": -80, "drums": 80, "other": -45, "vocals": 15}
                    }
                # Validate stem_directions
                if 'stem_directions' not in profile_data or not isinstance(profile_data['stem_directions'], dict):
                    print(f"Warning: 'stem_directions' missing or invalid in {profiles[selected_idx].name}. Using defaults.")
                    profile_data['stem_directions'] = {"bass": -80, "drums": 80, "other": -45, "vocals": 15}
                elif not all(stem in profile_data['stem_directions'] for stem in ['bass', 'drums', 'other', 'vocals']):
                    print(f"Warning: 'stem_directions' incomplete in {profiles[selected_idx].name}. Using defaults for missing stems.")
                    defaults = {"bass": -80, "drums": 80, "other": -45, "vocals": 15}
                    for stem in ['bass', 'drums', 'other', 'vocals']:
                        profile_data['stem_directions'].setdefault(stem, defaults[stem])
                
                print(f"\nSelected profile: {profiles[selected_idx].name}")
                print(f"  HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
                print(f"  Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
                print(f"  Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
                print(f"  Effective Radius: {profile_data['effective_radius']:.2f} cm")
                print("  Stem Directions:")
                for stem, angle in profile_data['stem_directions'].items():
                    print(f"    {stem.capitalize()}: {angle}°")
                return profile_data
            except json.JSONDecodeError:
                print(f"Error: {profiles[selected_idx].name} is not a valid JSON file.")
                return {
                    "hrtf_subject": "003",
                    "effective_radius": 8.5,
                    "head_width": 15.2,
                    "head_length": 19.0,
                    "stem_directions": {"bass": -80, "drums": 80, "other": -45, "vocals": 15}
                }
        elif ch.lower() == 'w' and selected_idx > 0:
            selected_idx -= 1
        elif ch.lower() == 's' and selected_idx < len(profiles) - 1:
            selected_idx += 1

def HRTF(az, n, profile: dict):
    subject = profile.get("hrtf_subject", "003")
    effective_radius = profile.get("effective_radius", 8.5)
    hrtf_path = Path(f"/home/advented/HRIRs/Subject_{subject}_{az}_0.mat")
    try:
        data = loadmat(str(hrtf_path))
        hrir_left = data['hrir_left'].flatten()
        hrir_right = data['hrir_right'].flatten()
    except FileNotFoundError:
        print(f"Error: HRTF file {hrtf_path} not found. Using default Subject_003.")
        hrtf_path = Path(f"/home/advented/HRIRs/Subject_003_{az}_0.mat")
        try:
            data = loadmat(str(hrtf_path))
            hrir_left = data['hrir_left'].flatten()
            hrir_right = data['hrir_right'].flatten()
        except FileNotFoundError:
            print(f"Error: Default HRTF file {hrtf_path} not found. Using zero HRIR.")
            hrir_left = np.zeros(512)
            hrir_right = np.zeros(512)
    
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

fs, data = read_wav_file("/home/advented/audioProductV1/projectCode/Original.wav", 44100)

from openunmix import predict
# Load umxl model explicitly for higher-quality source separation
# change argument to umxhq ,for higher quality  
#change argument to umxl for faster separation
# Note: testing them..they seem to sound the same though hq just has less bleed and some better quality just not the best - can notice this the most in vocals
separator = torch.hub.load('sigsep/open-unmix-pytorch', 'umxhq', device=device)
estimates = predict.separate(
    audio=torch.as_tensor(data).float(),
    rate=fs,
    device=device,
    separator=separator
)
for target, estimate in estimates.items():
    print(target)
    audio = estimate.detach().cpu().numpy()[0]
    display(Audio(audio, rate=fs))

original_fs = 44100
duration = 0.2
estimates_numpy = {}
for target, estimate in estimates.items():
    estimates_numpy[target] = torch.squeeze(estimate).detach().cpu().numpy().T

profiles_dir = Path("/home/advented/audioProductV1/projectCode/SeniorDesign/user_profiles")
profile = select_profile(profiles_dir)

start = Time.perf_counter()
# Use stem_directions angles from profile
stem_directions = profile['stem_directions']
modified_bass = HRTF(stem_directions['bass'], Stereo_to_mono(estimates_numpy['bass']), profile)
modified_drums = HRTF(stem_directions['drums'], Stereo_to_mono(estimates_numpy['drums']), profile)
modified_other = HRTF(stem_directions['other'], Stereo_to_mono(estimates_numpy['other']), profile)
modified_vocals = HRTF(stem_directions['vocals'], Stereo_to_mono(estimates_numpy['vocals']), profile)
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