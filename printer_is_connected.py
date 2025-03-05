import serial.tools.list_ports

def check_printer_connection():
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print(" No devices found. Please check your USB connection.")
        return False
    
    for port in ports:
        if "CH340" in port.description or "FT232R" in port.description:
            print(f" Printer is connected on {port.device} ({port.description})")
            return True
    
    print(" No 3D printer detected. Try reconnecting.")
    return False

# Run the function
check_printer_connection()
