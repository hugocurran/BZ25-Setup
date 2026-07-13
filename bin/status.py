#!/usr/bin/python3
from gpiozero import LED
from signal import pause

led = LED(17)

# Blink with 1 second on, 1 second off
led.blink(on_time=1, off_time=1)

# Keep the script running
pause()

