import enum
import os
import time
import tkinter as tk

import RPi.GPIO as GPIO

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
class ClockMode(enum):
    SIMPLE_CLOCK_DISPLAY = 0
    SELECT_NUM_PEOPLE = 1
    SELECT_HOURLY_WAGE = 2
    DISPLAY_BURNING_MONEY = 3


clockMode: ClockMode = ClockMode.SIMPLE_CLOCK_DISPLAY

numPeople = DEFAULT_NUM_PEOPLE
hourlyWage = DEFAULT_HOURLY_WAGE
meetingStartTime = 0

app: tk.Tk = tk.Tk()
app.attributes("-fullscreen", True)
app.title("Money Burner")


def update_time(repeat: bool = True) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    if clockMode is ClockMode.DISPLAY_BURNING_MONEY:
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
    if clockMode == ClockMode.SELECT_NUM_PEOPLE:
        numPeople += 1
        display_value()
    elif clockMode == ClockMode.SELECT_HOURLY_WAGE:
        hourlyWage += 1
        display_value()
    update_time(False)


def decrement_value(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Decrement")
    if clockMode == ClockMode.SELECT_NUM_PEOPLE and numPeople > 0:
        numPeople -= 1
        display_value()
    elif clockMode == ClockMode.SELECT_HOURLY_WAGE and hourlyWage > 0:
        hourlyWage -= 1
        display_value()
    update_time(False)


def display_value() -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    if clockMode == ClockMode.SELECT_NUM_PEOPLE:
        clock_label.config(text=str(numPeople))
    elif clockMode == ClockMode.SELECT_HOURLY_WAGE:
        clock_label.config(text=str(hourlyWage))


def next_event(channel: int) -> None:
    global clockMode, numPeople, hourlyWage, meetingStartTime
    print("Next")
    if clockMode == ClockMode.SIMPLE_CLOCK_DISPLAY:
        clockMode = 1
        value_label.config(text="People in Meeting")
    elif clockMode == ClockMode.SELECT_NUM_PEOPLE:
        clockMode = ClockMode.SELECT_HOURLY_WAGE
        value_label.config(text="Cost per Person ($)")
    elif clockMode == ClockMode.SELECT_HOURLY_WAGE:
        clockMode = ClockMode.DISPLAY_BURNING_MONEY
        value_label.config(text="Meeting Cost ($)")
        meetingStartTime = time.time()
    else:
        clockMode = ClockMode.SIMPLE_CLOCK_DISPLAY
        value_label.config(text="Waiting for Meeting")
    print(clockMode)
    update_time(False)


def exit_clock(channel: int) -> None:
    print("Exiting")
    global app
    app.quit()
    quit()


value_label: tk.Label = tk.Label(
    app, text="Waiting for Meeting", font=("Arial", 24)
)
value_label.pack()

clock_label: tk.Label = tk.Label(
    app, font=("Arial", 48), bg="black", fg="white"
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
