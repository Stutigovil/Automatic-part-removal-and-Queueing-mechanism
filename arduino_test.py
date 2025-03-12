import serial
import time
# Change ARDUINO_PORT based on your OS
# Linux/macOS: "/dev/ttyACM0" or "/dev/ttyUSB0"
# Windows: "COM13" (Check in Device Manager)
ARDUINO_PORT = "COM13"
BAUD_RATE = 9600

# Initialize serial connection
arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
time.sleep(2)
arduino.write("start".encode())







# arduino.close()
