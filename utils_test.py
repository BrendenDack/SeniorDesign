import utility
import time as Time

start = Time.perf_counter()
summed_song = utility.Spacial_Audio_Separation('Original.wav')
end = Time.perf_counter()
print(f"Time taken: {end-start} seconds")