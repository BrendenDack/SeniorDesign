# This is bascially the same code as the Music Player GUI folder except I merged them into one to test some things 
# Also have been modified to have a potentially working clock of each screen. Not too sure how well itll work with Tkinter

#Music Library 
from pathlib import Path

# from tkinter import *
# NEW !!!
import time
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\tpadmin\Desktop\Music Player GUI\Library\build\assets\frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# NEW !!!
# Function to update the clock
def update_time():
    current_time = time.strftime('%H:%M')  # Get current time in hours:minutes format
    canvas.delete("time_text")  # Delete old time text
    canvas.create_text(
        355.0,
        15.0,
        anchor="nw",
        text=current_time,
        fill="#000000",
        font=("Inter Bold", 32 * -1),
        tags="time_text"  # Add tag to identify this text object
    )
    canvas.after(1000, update_time)  # Call the function again after 1 second

# NEW !!!
# Start the clock update function 

window = Tk()

window.geometry("800x600")
window.configure(bg = "#FFFFFF")


canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 600,
    width = 800,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_1 clicked"),
    relief="flat"
)
button_1.place(
    x=7.0,
    y=252.0,
    width=783.0,
    height=136.0
)

canvas.create_text(
    355.0,
    15.0,
    anchor="nw",
    text="12:00",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    356.0,
    128.0,
    anchor="nw",
    text="HYBS",
    fill="#000000",
    font=("Inter Medium", 32 * -1)
)

canvas.create_text(
    356.0,
    485.0,
    anchor="nw",
    text="imase",
    fill="#515151",
    font=("Inter Medium", 32 * -1)
)

canvas.create_text(
    616.0,
    89.0,
    anchor="nw",
    text="Source \nSeparation\nAvailable",
    fill="#000000",
    font=("Inter SemiBold", 32 * -1)
)

canvas.create_text(
    610.0,
    446.0,
    anchor="nw",
    text="Source \nSeparation\nUnavailable",
    fill="#000000",
    font=("Inter SemiBold", 32 * -1)
)

canvas.create_text(
    65.0,
    128.0,
    anchor="nw",
    text="Tip Toe",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    65.0,
    485.0,
    anchor="nw",
    text="NIGHT DANCER",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    754.0,
    35.0,
    image=image_image_1
)

canvas.create_rectangle(
    -3.0,
    411.0000007674098,
    799.9993801116943,
    415.0,
    fill="#000000",
    outline="")

canvas.create_rectangle(
    -3.0,
    63.0,
    800.0,
    66.0,
    fill="#000000",
    outline="")

canvas.create_rectangle(
    -3.0,
    229.0000007674098,
    799.9993801116943,
    233.0,
    fill="#000000",
    outline="")

canvas.create_rectangle(
    20.0,
    12.0,
    65.0,
    57.0,
    fill="#FFFFFF",
    outline="")

canvas.create_rectangle(
    27.0,
    19.0,
    57.0,
    49.0,
    fill="#FFFFFF",
    outline="")

image_image_2 = PhotoImage(
    file=relative_to_assets("image_2.png"))
image_2 = canvas.create_image(
    41.0,
    34.0,
    image=image_image_2
)

image_image_3 = PhotoImage(
    file=relative_to_assets("image_3.png"))
image_3 = canvas.create_image(
    41.0,
    499.0,
    image=image_image_3
)

image_image_4 = PhotoImage(
    file=relative_to_assets("image_4.png"))
image_4 = canvas.create_image(
    41.0,
    147.0,
    image=image_image_4
)
window.resizable(False, False)
window.mainloop()

#Main Menu
from pathlib import Path

# from tkinter import *
# NEW !!!
import time
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\tpadmin\Desktop\Music Player GUI\Main Menu\build\assets\frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# NEW !!!
# Function to update the clock 
def update_time():
    current_time = time.strftime('%H:%M')  # Get current time in hours:minutes format
    canvas.delete("time_text")  # Delete old time text (using "time_text" tag)
    canvas.create_text(
        355.0,
        15.0,
        anchor="nw",
        text=current_time,
        fill="#000000",
        font=("Inter Bold", 32 * -1),
        tags="time_text"  # Add tag to identify this text object
    )
    canvas.after(1000, update_time)  # Call the function again after 1 second

# NEW !!!
# Start the clock update function 
update_time()

window = Tk()

window.geometry("800x600")
window.configure(bg = "#FFFFFF")


canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 600,
    width = 800,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_1 clicked"),
    relief="flat"
)
button_1.place(
    x=15.0,
    y=436.0,
    width=771.0,
    height=141.0
)

button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_2 clicked"),
    relief="flat"
)
button_2.place(
    x=15.0,
    y=252.0,
    width=771.0,
    height=144.0
)

button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_3 clicked"),
    relief="flat"
)
button_3.place(
    x=15.0,
    y=83.0,
    width=771.0,
    height=125.0
)

image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    400.0,
    215.0,
    image=image_image_1
)
window.resizable(False, False)
window.mainloop()

# Settings
# from tkinter import *
# NEW !!!
import time
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\tpadmin\Desktop\Music Player GUI\Settings\build\assets\frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# NEW !!!
# Function to update the clock 
def update_time():
    current_time = time.strftime('%H:%M')  # Get current time in hours:minutes-+ format
    canvas.delete("time_text")  # Delete old time text (using "time_text" tag)
    canvas.create_text(
        355.0,
        15.0,
        anchor="nw",
        text=current_time,
        fill="#000000",
        font=("Inter Bold", 32 * -1),
        tags="time_text"  # Add tag to identify this text object
    )
    canvas.after(1000, update_time)  # Call the function again after 1 second

# Start the clock update function 

window = Tk()

window.geometry("800x600")
window.configure(bg = "#FFFFFF")


canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 600,
    width = 800,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
canvas.create_text(
    355.0,
    15.0,
    anchor="nw",
    text="12:00",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    21.0,
    131.0,
    anchor="nw",
    text="Storage Space Avaliable",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    678.0,
    131.0,
    anchor="nw",
    text="10 GB",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    667.0,
    305.0,
    anchor="nw",
    text="5",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    21.0,
    304.0,
    anchor="nw",
    text="Volume",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    21.0,
    486.0,
    anchor="nw",
    text="Time Zone",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

canvas.create_text(
    603.0,
    480.0,
    anchor="nw",
    text="Cupertino",
    fill="#000000",
    font=("Inter Bold", 32 * -1)
)

image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    754.0,
    35.0,
    image=image_image_1
)

canvas.create_rectangle(
    -3.0,
    411.0000007674098,
    799.9993801116943,
    415.0,
    fill="#000000",
    outline="")

canvas.create_rectangle(
    -3.0,
    63.0,
    800.0,
    66.0,
    fill="#000000",
    outline="")

canvas.create_rectangle(
    -3.0,
    229.0000007674098,
    799.9993801116943,
    233.0,
    fill="#000000",
    outline="")

button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_1 clicked"),
    relief="flat"
)
button_1.place(
    x=586.0,
    y=300.0,
    width=48.0,
    height=48.0
)

button_image_2 = PhotoImage(
    file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("button_2 clicked"),
    relief="flat"
)
button_2.place(
    x=721.0,
    y=300.0,
    width=48.0,
    height=48.0
)

canvas.create_rectangle(
    20.0,
    12.0,
    65.0,
    57.0,
    fill="#FFFFFF",
    outline="")

image_image_2 = PhotoImage(
    file=relative_to_assets("image_2.png"))
image_2 = canvas.create_image(
    41.0,
    34.0,
    image=image_image_2
)
window.resizable(False, False)
window.mainloop()
