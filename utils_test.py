import utility
import time as Time
import soundfile as sf
from calibrateUserProfile import apply_hrtf

start = Time.perf_counter()
stems = utility.separate_sources("Music/skydance_audio_title.mp3")
end = Time.perf_counter()
print(f"Time taken Separate: {end-start} seconds")

start = Time.perf_counter()
hrtf_stems = apply_hrtf(stems["vocals"], 0, "003")
sf.write(f"Spatial/hrtf_vocal_output.wav", stems['vocals'], samplerate=44100)
hrtf_stems = apply_hrtf(stems["bass"], 0, "003")
sf.write(f"Spatial/hrtf_bass_output.wav", stems['bass'], samplerate=44100)
hrtf_stems = apply_hrtf(stems["drums"], 0, "003")
sf.write(f"Spatial/hrtf_drums_output.wav", stems['drums'], samplerate=44100)
hrtf_stems = apply_hrtf(stems["other"], 0, "003")
sf.write(f"Spatial/hrtf_other_output.wav", stems['other'], samplerate=44100)
end = Time.perf_counter()

print(f"Time taken Apply_HRTF: {end-start} seconds")