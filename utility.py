import numpy as np
import librosa
from scipy.io import loadmat, wavfile
from scipy.signal import lfilter, resample
import torch
from openunmix import predict
from IPython.display import Audio, display # type: ignore
from battery_monitor import get_battery_info, is_charging

global volume
volume = 1

# Read WAV file and return data and sampling rate
def read_wav_file(filename, fs=16000):
    fs, data = wavfile.read(filename)
    return fs, data

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

    #set up Torch
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    fs, data = read_wav_file(filename=file_name, fs=44100)

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