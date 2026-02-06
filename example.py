from sense_hat import SenseHat
import time

# Initialize the Sense HAT
sense = SenseHat()

# Optional: Clear the LED matrix
sense.clear()

try:
    while True:
        # Read environmental sensors
        temp = sense.get_temperature()
        humidity = sense.get_humidity()
        pressure = sense.get_pressure()

        # Read orientation (IMU)
        orientation = sense.get_orientation()
        pitch = orientation['pitch']
        roll = orientation['roll']
        yaw = orientation['yaw']

        # Print data rounded to 2 decimal places
        print(f"Temp: {temp:.2f}C, Humidity: {humidity:.2f}%, Pressure: {pressure:.2f}mb")
        print(f"Pitch: {pitch:.2f}, Roll: {roll:.2f}, Yaw: {yaw:.2f}")
        print("-" * 20)

        # Wait 1 second before reading again
        time.sleep(1)

except KeyboardInterrupt:
    # Clear screen on exit
    sense.clear()