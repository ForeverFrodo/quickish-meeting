import enum
import os
import time
import tkinter as tk

from typing import Callable

import RPi.GPIO as GPIO
from PIL import Image, ImageSequence, ImageTk  # pip install pillow

# fix broken environment variable
if os.environ.get("DISPLAY", "") == "":
    print("no display found. Using :0.0")
    os.environ.__setitem__("DISPLAY", ":0.0")

# GPIO setup
GPIO.setmode(GPIO.BCM)
INCREMENT_PIN: int = 0
DECREMENT_PIN: int = 1
MODE_PIN: int = 2
AUX_PIN: int = 3
DEFAULT_NUM_PEOPLE: int = 2
DEFAULT_HOURLY_WAGE: int = 40  # dollars per hour

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
app.attributes("-fullscreen", True)
app.title("Money Burner")
#app.wm_attributes("-transparentcolor", "black")

backgrounds: dict[ClockMode, ImageTk.PhotoImage] = {
    ClockMode.CLOCK: ImageTk.PhotoImage((Image.open("./clock.jpg")).resize((width, height), Image.LANCZOS)),
    ClockMode.SEL_PEEPS: ImageTk.PhotoImage((Image.open("./selections.jpg")).resize((width, height), Image.LANCZOS)),
    ClockMode.SEL_WAGE: ImageTk.PhotoImage((Image.open("./selections.jpg")).resize((width, height), Image.LANCZOS)),
    ClockMode.BURN: ImageTk.PhotoImage((Image.open("./burn.jpg")).resize((width, height), Image.LANCZOS)),
}

canvas: tk.Canvas = tk.Canvas(app, width=width, height=height)
canvas.pack(fill="both", expand=True)

animated_gif: AnimatedGIF = AnimatedGIF(
    canvas, "./fire.gif", app.winfo_screenwidth, app.winfo_screenheight
)

background_label: int = canvas.create_image(
    int(width / 2),
    int(height / 2),
    anchor="center",
    image=backgrounds[clockMode],
)
canvas.image = backgrounds[
    clockMode
]  # Keep a reference to avoid garbage collection

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
        clock_label.config(text=f"${total_cost:.2f}")
    else:
        current_time = time.strftime("%H:%M:%S")
        clock_label.config(text=current_time)
    if repeat:
        clock_label.after(1000, update_time)


def increment_value(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Increment")
    if clockMode == ClockMode.SEL_PEEPS:
        numPeople += 1
        display_value()
    elif clockMode == ClockMode.SEL_WAGE:
        hourlyWage += 1
        display_value()
    update_time(False)


def decrement_value(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Decrement")
    if clockMode == ClockMode.SEL_PEEPS and numPeople > 0:
        numPeople -= 1
        display_value()
    elif clockMode == ClockMode.SEL_WAGE and hourlyWage > 0:
        hourlyWage -= 1
        display_value()
    update_time(False)


def display_value() -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    if clockMode == ClockMode.SEL_PEEPS:
        clock_label.config(text=str(numPeople))
    elif clockMode == ClockMode.SEL_WAGE:
        clock_label.config(text=str(hourlyWage))


def next_event(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Next")
    if clockMode == ClockMode.CLOCK:
        animated_gif.stop_animation()
        clockMode = ClockMode.SEL_PEEPS
        update_background()
        value_label.config(text="People in Meeting")
    elif clockMode == ClockMode.SEL_PEEPS:
        animated_gif.stop_animation()
        clockMode = ClockMode.SEL_WAGE
        update_background()
        value_label.config(text="Cost per Person ($)")
    elif clockMode == ClockMode.SEL_WAGE:
        animated_gif.start_animation()
        clockMode = ClockMode.BURN
        update_background()
        value_label.config(text="Meeting Cost ($)")
        meetingStartTime = time.time()
    else:
        animated_gif.stop_animation()
        clockMode = ClockMode.CLOCK
        update_background()
        value_label.config(text="Waiting for Meeting")
    print(clockMode)
    update_time(False)


def exit_clock(channel: int) -> None:
    print("Exiting")
    global app
    app.quit()
    quit()


value_label: tk.Label = tk.Label(
    app, text="Waiting for Meeting", font=("Courier", 24)
)
value_label.pack()

clock_label: tk.Label = tk.Label(
    app, font=("Courier", 48), bg="black", fg="white"
)
clock_label.pack(fill="both", expand=1)

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
    AUX_PIN, GPIO.FALLING, callback=exit_clock, bouncetime=300
)

app.mainloop()

GPIO.cleanup()
