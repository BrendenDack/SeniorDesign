import utility
import time as Time

start = Time.perf_counter()
summed_song = utility.separate_sources("Music/01 Fix My Eyes.mp3")
end = Time.perf_counter()
print(f"Time taken: {end-start} seconds")