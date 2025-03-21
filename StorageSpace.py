import os

# Links:
# https://www.geeksforgeeks.org/os-module-python-examples/ 
# https://www.geeksforgeeks.org/python-os-statvfs-method/ 
# https://www.geeksforgeeks.org/get-file-size-in-bytes-kb-mb-and-gb-using-python/ 

def get_storage_info(music_folder):
    # Get total storage space 
    # os.statvfs(): Retrieves info about the file system in the given path
    # f_blocks: Represents the size of fs in f_frsize units
    # f_frsize: Represents the fragment size
    total_space = os.statvfs(music_folder).f_blocks * os.statvfs(music_folder).f_frsize
    
    # Get available storage space
    # f_bavail: Represents the number of free blocks for unprivileged users
    free_space = os.statvfs(music_folder).f_bavail * os.statvfs(music_folder).f_frsize
    
    # Get used storage space by subtracting free space from total space
    used_space = total_space - free_space
    
    return total_space, used_space, free_space

# Conversion to kilobytes, megabytes, and gigabytes
# idk what is going on here tbh 
file_size_kb = used_space / 1024
file_size_mb = file_size_kb / 1024
file_size_gb = file_size_mb / 1024

def display_storage_info(music_folder):
    total_space, used_space, free_space = get_storage_info(music_folder)
    print(f"Total Storage: {file_size_gb(total_space)}")
    print(f"Used Storage: {file_size_gb(used_space)}")
    print(f"Free Storage: {file_size_gb(free_space)}")

# Set the path to music folder
# Leaving path to music player blank for now until we have some sort of music directory
music_folder_path = ""  
display_storage_info(music_folder_path)
