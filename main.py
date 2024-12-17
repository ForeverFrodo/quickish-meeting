import tkinter as tk
import time
import RPi.GPIO as GPIO

# GPIO setup
GPIO.setmode(GPIO.BOARD)
INCREMENT_PIN = 28
DECREMENT_PIN = 3
MODE_PIN = 27

GPIO.setup(INCREMENT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(DECREMENT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(MODE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def update_time():
    if mode_var.get() == "Clock":
        current_time = time.strftime("%H:%M:%S")
        clock_label.config(text=current_time)
    clock_label.after(1000, update_time)

def increment_value(channel):
    global value
    value += 1
    display_value()

def decrement_value(channel):
    global value
    if value > 0:
        value -= 1
    display_value()

def display_value():
    clock_label.config(text=str(value))

def switch_mode(channel):
    global people, cost_per_person, start_time, running
    current_mode = mode_var.get()
    if current_mode == "Clock":
        mode_var.set("Set People")
        value_label.config(text="People in Meeting")
        value = 0
        display_value()
    elif current_mode == "Set People":
        mode_var.set("Set Cost")
        people = value
        value_label.config(text="Cost per Person ($)")
        value = 0
        display_value()
    elif current_mode == "Set Cost":
        mode_var.set("Running")
        cost_per_person = value
        value_label.config(text="Meeting Cost ($)")
        value = 0
        running = True
        start_time = time.time()
        update_meeting_cost()
    else:
        mode_var.set("Clock")
        running = False
        update_time()

def update_meeting_cost():
    global running, value
    if running:
        elapsed_time = time.time() - start_time
        total_cost = people * cost_per_person * (elapsed_time / 3600)
        clock_label.config(text=f"${total_cost:.2f}")
        clock_label.after(1000, update_meeting_cost)

app = tk.Tk()
app.attributes('-fullscreen', True)
app.title("Money Burner")

mode_var = tk.StringVar(value="Clock")
value = 0
people = 0
cost_per_person = 0
running = False
start_time = 0

value_label = tk.Label(app, text="", font=("Arial", 24))
value_label.pack()

clock_label = tk.Label(app, font=("Arial", 48), bg="black", fg="white")
clock_label.pack(fill="both", expand=1)

update_time()

GPIO.add_event_detect(INCREMENT_PIN, GPIO.FALLING, callback=increment_value, bouncetime=300)
GPIO.add_event_detect(DECREMENT_PIN, GPIO.FALLING, callback=decrement_value, bouncetime=300)
GPIO.add_event_detect(MODE_PIN, GPIO.FALLING, callback=switch_mode, bouncetime=300)

app.mainloop()

GPIO.cleanup()
