import serial
import time
# Change ARDUINO_PORT based on your OS
# Linux/macOS: "/dev/ttyACM0" or "/dev/ttyUSB0"
# Windows: "COM13" (Check in Device Manager)
PRINTER_PORT = "COM5"
BAUD_RATE = 115200

# Initialize serial connection
printer = serial.Serial(PRINTER_PORT, BAUD_RATE, timeout=2)
time.sleep(2)
printer.write(("G1 Z180 ; \n").encode())

printer.close()
