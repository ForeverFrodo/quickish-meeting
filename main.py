import enum
import os
import time
import tkinter as tk
from typing import Callable

import RPi.GPIO as GPIO
from PIL import Image, ImageSequence, ImageTk  # pip install pillow

# TODO:
# - Change background for burn mode
#   - if time, get animation going
# - Display numbers for people and money selection
# - Center the words on selection screen
# - On Burn screen, put clock on top left corner
# - On Burn screen, make sure everything is visible
# - Make it run on startup

# fix broken environment variable
if os.environ.get("DISPLAY", "") == "":
    print("no display found. Using :0.0")
    os.environ.__setitem__("DISPLAY", ":0.0")

# GPIO setup
GPIO.setmode(GPIO.BCM)
INCREMENT_PIN: int = 1
DECREMENT_PIN: int = 2
MODE_PIN: int = 0
AUX_PIN: int = 3
DEFAULT_NUM_PEOPLE: int = 2
DEFAULT_HOURLY_WAGE: int = 50  # dollars per hour

GPIO.setup(INCREMENT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DECREMENT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(MODE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(AUX_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# Clock mode is implemented as follows:
#   0 -> simple clock display
#   1 -> select number of people
#   2 -> select hourly wage
#   3 -> display money burned
class ClockMode(enum.Enum):
    CLOCK = 0
    SEL_PEEPS = 1
    SEL_WAGE = 2
    BURN = 3


class AnimatedGIF:
    def __init__(
        self,
        canvas: tk.Canvas,
        gif_path: str,
        get_width: Callable[[None], int],
        get_height: Callable[[None], int],
    ) -> None:
        self.canvas: tk.Canvas = canvas
        self.get_width: Callable[[None], int] = get_width
        self.get_height: Callable[[None], int] = get_height
        self.update_coords()
        self.gif_path: str = gif_path
        self.sequence: list[ImageTk.PhotoImage] = []
        self.load_frames()
        self.index: int = 0
        self.image_item: int = self.canvas.create_image(
            self.x, self.y, anchor="center", image=self.sequence[0]
        )
        self.running: bool = False
        self.canvas.itemconfigure(self.image_item, state="hidden")

    def update_coords(self) -> None:
        """Gets the center coordinate and saves it to self.x and self.y"""
        self.x: int = int(self.get_width() / 2)
        self.y: int = int(self.get_height() / 2)

    def load_frames(self) -> None:
        self.image = Image.open(self.gif_path)
        for frame in ImageSequence.Iterator(self.image):
            self.sequence.append(ImageTk.PhotoImage(frame))

    def update_frame(self) -> None:
        if self.running:
            frame = self.sequence[self.index]
            self.canvas.itemconfig(self.image_item, image=frame)
            self.index = (self.index + 1) % len(self.sequence)
            self.canvas.after(
                100, self.update_frame
            )  # Adjust the delay to control the speed

    def start_animation(self) -> None:
        self.running = True
        self.canvas.itemconfigure(self.image_item, state="normal")
        self.update_frame()

    def stop_animation(self) -> None:
        self.running = False
        self.canvas.itemconfigure(self.image_item, state="hidden")


clockMode: ClockMode = ClockMode.CLOCK

numPeople = DEFAULT_NUM_PEOPLE
hourlyWage = DEFAULT_HOURLY_WAGE
meetingStartTime = 0

app: tk.Tk = tk.Tk()
width: int = app.winfo_screenwidth()
height: int = app.winfo_screenheight()
app.config(cursor="none")
app.attributes("-fullscreen", True)
app.overrideredirect(True)
app.title("Money Burner")
# app.wm_attributes("-alpha", "black")

backgrounds: dict[ClockMode, ImageTk.PhotoImage] = {
    ClockMode.CLOCK: ImageTk.PhotoImage(
        (Image.open("./clock.jpg")).resize((width, height), Image.LANCZOS)
    ),
    ClockMode.SEL_PEEPS: ImageTk.PhotoImage(
        (Image.open("./selections.jpg")).resize((width, height), Image.LANCZOS)
    ),
    ClockMode.SEL_WAGE: ImageTk.PhotoImage(
        (Image.open("./selections.jpg")).resize((width, height), Image.LANCZOS)
    ),
    ClockMode.BURN: ImageTk.PhotoImage(
        (Image.open("./burn.jpg")).resize((width, height), Image.LANCZOS)
    ),
}

canvas: tk.Canvas = tk.Canvas(app, width=width, height=height)
canvas.pack(fill="both", expand=True)


background_label: int = canvas.create_image(
    width / 2,
    height / 2,
    anchor="center",
    image=backgrounds[clockMode],
)
canvas.image = backgrounds[
    clockMode
]  # Keep a reference to avoid garbage collection

animated_gif: AnimatedGIF = AnimatedGIF(
    canvas,
    "./fire_overlayed.gif",
    app.winfo_screenwidth,
    app.winfo_screenheight,
)


def update_background() -> None:
    new_photo = backgrounds[clockMode]
    if new_photo != canvas.image:
        canvas.itemconfig(background_label, image=new_photo)
        canvas.image = new_photo  # Keep a reference to avoid garbage collection


def update_time(repeat: bool = True) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    if clockMode is ClockMode.BURN:
        elapsed_time = time.time() - meetingStartTime
        total_cost = numPeople * hourlyWage * (elapsed_time / 3600)
        canvas.itemconfigure(
            "money",
            text=f"${total_cost:.2f}"
        )
        current_time = time.strftime("%H:%M:%S")
        canvas.itemconfigure(
            "time",
            text=current_time
        )
    elif clockMode is ClockMode.CLOCK:
        current_time = time.strftime("%H:%M:%S")
        canvas.itemconfigure(
            "time",
            text=current_time
        )
    elif clockMode is ClockMode.SEL_PEEPS:
        canvas.itemconfigure("num", text=str(numPeople))
    else:
        canvas.itemconfigure("num", text=str(numPeople))
        canvas.itemconfigure("wage", text="$" + str(hourlyWage))
    if repeat:
        canvas.after(1000, update_time)


def increment_value(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Increment")
    if clockMode == ClockMode.SEL_PEEPS:
        numPeople += 1
        update_time(repeat=False)
    elif clockMode == ClockMode.SEL_WAGE:
        hourlyWage += 5
        update_time(repeat=False)
    update_time(False)


def decrement_value(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Decrement")
    if clockMode == ClockMode.SEL_PEEPS and numPeople > 0:
        numPeople -= 1
        update_time(repeat=False)
    elif clockMode == ClockMode.SEL_WAGE and hourlyWage > 0:
        hourlyWage -= 5
        update_time(repeat=False)
    update_time(False)


def next_event(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Next")
    if clockMode == ClockMode.CLOCK:

        animated_gif.stop_animation()
        clockMode = ClockMode.SEL_PEEPS
        update_background()

        canvas.itemconfigure("Mode", text="People in Meeting", font=("Courier", 26, "normal"))
        canvas.coords("Mode", width / 1.95, height / 16)
        canvas.itemconfigure("time", text="")
        canvas.coords("time", 0, 0)
        canvas.itemconfigure("money", text="")
        canvas.coords("money", 0, 0)
        canvas.itemconfigure("num", text="")
        canvas.coords("num", width / 1.95, height / 3.6)
        canvas.itemconfigure("wage", text="")
        canvas.coords("wage", width / 1.95, height / 2.25)

    elif clockMode == ClockMode.SEL_PEEPS:
        animated_gif.stop_animation()
        clockMode = ClockMode.SEL_WAGE
        update_background()

        canvas.itemconfigure("Mode", text="Cost per Person ($)", font=("Courier", 26, "normal"))
        canvas.coords("Mode", width / 1.95, height / 16)
        canvas.itemconfigure("time", text="")
        canvas.coords("time", 0, 0)
        canvas.itemconfigure("money", text="")
        canvas.coords("money", 0, 0)
        canvas.itemconfigure("num", text="")
        canvas.coords("num", width / 1.95, height / 3.6)
        canvas.itemconfigure("wage", text="")
        canvas.coords("wage", width / 1.95, height / 2.25)

    elif clockMode == ClockMode.SEL_WAGE:
        animated_gif.start_animation()
        clockMode = ClockMode.BURN
        update_background()

        canvas.itemconfigure("Mode", text="", font=("Courier", 35, "bold"))
        canvas.coords("Mode", width / 2, height / 4)
        canvas.itemconfigure("time", text="", font=("Courier", 40, "bold"), fill="black")
        canvas.coords("time", width / 4.7, height / 8.2)
        canvas.itemconfigure("money", text="", font=("Courier", 140, "bold"), fill="black")
        canvas.coords("money", width / 2, height / 2)
        canvas.itemconfigure("num", text="")
        canvas.coords("num", 0, 0)
        canvas.itemconfigure("wage", text="")
        canvas.coords("wage", 0, 0)

        meetingStartTime = time.time()
    else:
        animated_gif.stop_animation()
        clockMode = ClockMode.CLOCK
        update_background()

        canvas.itemconfigure("Mode", text="")
        canvas.coords("Mode", 0, 0)
        canvas.itemconfigure("time", font=("Courier", 100, "bold"), fill="white")
        canvas.coords("time", width / 2, height / 2)
        canvas.itemconfigure("money", text="")
        canvas.coords("money", 0, 0)
        canvas.itemconfigure("num", text="")
        canvas.coords("num", 0, 0)
        canvas.itemconfigure("wage", text="")
        canvas.coords("wage", 0, 0)

    print(clockMode)
    update_time(False)
    
canvas.create_text(
    width / 2,
    height / 16,
    text="",
    font=("Courier", 26),
    fill="white",
    tags="Mode",
)

canvas.create_text(
    width / 2,
    height / 2,
    text="",
    font=("Courier", 100, "bold"),
    fill="white",
    tags="time",
)

canvas.create_text(
    width / 2,
    height / 2,
    text="",
    font=("Courier", 80),
    fill="white",
    tags="money",
)

canvas.create_text(
    width / 2,
    height / 4,
    text="",
    font=("Courier", 26, "bold"),
    fill="black",
    tags="num",
)

canvas.create_text(
    width / 2,
    height / 2.5,
    text="",
    font=("Courier", 26, "bold"),
    fill="black",
    tags="wage",
)

secret_message = ImageTk.PhotoImage(
        Image.open("./message.png").resize((width, int(height/1.5)), Image.LANCZOS)
    )
secret_item = canvas.create_image(
            width / 2, height / 2, anchor="center", image=secret_message, state="hidden"
        )

def display_secret_message(channel: int) -> None:
    if GPIO.input(AUX_PIN):
        canvas.itemconfigure(secret_item, state="hidden")
    else:
        canvas.itemconfigure(secret_item, state="normal")

update_time()

GPIO.add_event_detect(
    INCREMENT_PIN, GPIO.FALLING, callback=increment_value, bouncetime=300
)
GPIO.add_event_detect(
    DECREMENT_PIN, GPIO.FALLING, callback=decrement_value, bouncetime=300
)
GPIO.add_event_detect(
    MODE_PIN, GPIO.FALLING, callback=next_event, bouncetime=300
)
GPIO.add_event_detect(
    AUX_PIN, GPIO.BOTH, callback=display_secret_message, bouncetime=300
)

app.mainloop()

GPIO.cleanup()
