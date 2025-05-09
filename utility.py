import numpy as np
from scipy.io import loadmat, wavfile
from scipy.signal import lfilter, resample
import torch
from openunmix import predict
from IPython.display import Audio, display # type: ignore
from battery_monitor import get_battery_info, is_charging
from calibrateUserProfile import apply_hrtf
from pydub import AudioSegment
import os
import pickle
import json
from pathlib import Path

PROFILES_DIR = Path("user_profiles")
global volume
volume = 1

# Read WAV file and return data and sampling rate
def read_wav_file(filename, fs=16000):
    fs, data = wavfile.read(filename)
    return fs, data

def convert_to_wav(input_file_path):
    file_name, ext = os.path.splitext(input_file_path)
    ext = ext.lower()

    # Load audio with pydub
    try:
        audio = AudioSegment.from_file(input_file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load audio file: {e}")

    wav_file_path = f"{file_name}.wav"

    # Export to WAV format if not already a WAV
    if ext != ".wav":
        audio.export(wav_file_path, format="wav")
    else:
        wav_file_path = input_file_path  # already WAV

    return wav_file_path

# Set Volume
def set_volume(vol):
    global volume
    volume = vol

# Get Volume
def get_volume():
    global volume
    return volume

# Apply HRTF Function to input signal n, with azimuth(angle) az
def Apply_HRTF(az, n):
    data = loadmat(f'HRIRs/Subject_003_{az}_0.mat')
    hrir_left = data['hrir_left'].flatten()
    hrir_right = data['hrir_right'].flatten()
    
    # Resample HRIRs from 44.1 kHz to 16 kHz
    #hrir_left_resampled = resample(hrir_left, int(len(hrir_left) * fs / original_fs))
    #hrir_right_resampled = resample(hrir_right, int(len(hrir_right) * fs / original_fs))
    
    # Generate white noise
    #n = generate_white_noise(duration, fs)
    
    y_left = lfilter(hrir_left, 1, n) # Left
    y_right = lfilter(hrir_right, 1, n) # Right
    y = np.column_stack((y_left, y_right)).astype(np.float32)
    return y

# Take Stereo input signal and convert to mono signal
def Stereo_to_mono(signal):
    # x = np.linalg.norm(np.abs(signal)) # get magnitude of absolute value of signal
    left = signal[:,0]
    right = signal[:, 1]
    x = left + right
    peak = np.max(np.abs(x))
    return 0.5 * (x/peak) # return mono signal

# Separate sources from input signal given file name (Will add more options later)
def separate_sources(file_name):
    # Set up Torch
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    # Load the audio file with pydub (supports most formats)
    audio = AudioSegment.from_file(file_name)
    audio = audio.normalize()

    # Ensure it's stereo
    if audio.channels != 2:
        audio = audio.set_channels(2)

    # Convert to 44100Hz and 16-bit samples
    audio = audio.set_frame_rate(16000).set_sample_width(2)

    # Get raw data as NumPy array
    samples = np.array(audio.get_array_of_samples()).reshape((-1, 2))
    samples = samples.astype(np.float32) / 32768.0  # normalize 16-bit PCM

    # Separate sources
    estimates = predict.separate(
        torch.as_tensor(samples).float(),
        rate=16000,
        device=device
    )

    for target, estimate in estimates.items():
        print(target)
        audio_out = estimate.detach().cpu().numpy()[0]
        display(Audio(audio_out, rate=16000))

    # Convert to dictionary of NumPy arrays
    estimates_numpy = {}
    for target, estimate in estimates.items():
        estimates_numpy[target] = torch.squeeze(estimate).detach().cpu().numpy().T

    return estimates_numpy

# Sum the signals of the modified stems
def summed_signal(modified_vocals, modified_bass, modified_other, modified_drums):
    global volume
    if (volume == 0):
        volume = 1e-10
    summed_song = (modified_vocals + modified_bass + modified_other + modified_drums)/(1/volume)
    return summed_song

# Apply HRTF to the separated sources
def spacial_stems(estimates_numpy):
    azim = [-80, -65, -55, -45, -40, -35, -30, -25, -20, -15, -10, -5]
    azim = azim + [0] + [-a for a in reversed(azim)]
    modified_bass = Apply_HRTF(azim[0], Stereo_to_mono(estimates_numpy['bass']))
    modified_drums = Apply_HRTF(azim[24], Stereo_to_mono(estimates_numpy['drums']))
    modified_other = Apply_HRTF(azim[6], Stereo_to_mono(estimates_numpy['other']))
    modified_vocals = Apply_HRTF(azim[18], Stereo_to_mono(estimates_numpy['vocals']))

    return modified_bass, modified_drums, modified_other, modified_vocals

# Perform Full Suite of Spacial Audio Separation
def Spacial_Audio_Separation(file_name):
    estimates_numpy = separate_sources(file_name)
    modified_bass, modified_drums, modified_other, modified_vocals = spacial_stems(estimates_numpy)
    summed_song = summed_signal(modified_vocals, modified_bass, modified_other, modified_drums)
    return summed_song

def run_spatial_audio(file_name):
    print("Starting process")
    only_file_name = os.path.relpath(file_name, "Music")
    print(file_name)
    name_only, ext = os.path.splitext(only_file_name)
    print(name_only)
    output_filepath = "Spatial/" + name_only + ".pkl"
    print(output_filepath)
    if os.path.exists(output_filepath):
        print("attempting to load pickle file")
        with open(output_filepath, 'rb') as f:
            estimates_numpy = pickle.load(f)
    else:
        print("No pickle file: Starting Seperation")
        
        estimates_numpy = separate_sources(file_name)

        print("Trying to save pickle file")
        # Save stems to pickle file
        with open(f'Spatial/{name_only}.pkl', 'wb') as f:
            pickle.dump(estimates_numpy, f)

    return "Song successfully converted."

def apply_bulk_hrtf(estimates_numpy, Loaded_Profile):
    
    try:
        with open(f"{PROFILES_DIR}/{Loaded_Profile}", 'r') as f:
            profile_data = json.load(f)
        if not all(k in profile_data for k in ['hrtf_subject', 'effective_radius']):
            print(f"Invalid profile: {Loaded_Profile} Missing required fields.")
            return None, {
                "hrtf_subject": "003",
                "effective_radius": 8.5,
                "head_width": 15.2,
                "head_length": 19.0,
                "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
            }
        print(f"\nSelected profile: {Loaded_Profile}")
        print(f"  HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
        print(f"  Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
        print(f"  Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
        print(f"  Effective Radius: {profile_data['effective_radius']:.2f} cm")
    except json.JSONDecodeError:
        print(f"Error: {Loaded_Profile} is not a valid JSON file.")
        return None, {
            "hrtf_subject": "003",
            "effective_radius": 8.5,
            "head_width": 15.2,
            "head_length": 19.0,
            "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
        }

    if "stem_directions" not in profile_data:
        profile_data["stem_directions"] = {"bass": 0, "vocals": 0, "drums": 0, "other": 0}

    angles = profile_data["stem_directions"]
    test_subject = profile_data['hrtf_subject']
    print("Create Stems dict")
    spacial_stems = {'vocals' : 0, 'drums' : 0, 'bass' : 0, 'other' : 0}
    print("Vocals")
    spacial_stems['vocals'] = apply_hrtf(estimates_numpy['vocals'], angles['vocals'], test_subject)
    print("drums")
    spacial_stems['drums'] = apply_hrtf(estimates_numpy['drums'], angles['drums'], test_subject)
    print("bass")
    spacial_stems['bass'] = apply_hrtf(estimates_numpy['bass'], angles['bass'], test_subject)
    print("other")
    spacial_stems['other'] = apply_hrtf(estimates_numpy['other'], angles['other'], test_subject)
    print("Finished HRTFS")
    
    return spacial_stems
