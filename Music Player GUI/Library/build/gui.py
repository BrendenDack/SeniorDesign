from pathlib import Path

# from tkinter import *
# Explicit imports to satisfy Flake8
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\tpadmin\Desktop\Music Player GUI\Library\build\assets\frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


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
