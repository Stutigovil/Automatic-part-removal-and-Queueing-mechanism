

import os
import time
import serial
import threading
from flask import Flask, render_template, request, jsonify,Response,stream_with_context
from serial.tools import list_ports
from tqdm import tqdm
import cv2
from io import StringIO
import sys


COOL_DOWN_TIME = 300  #cooldown in seconds
PORT = "COM5" #printer's port
BAUDRATE = 115200
UPLOAD_FOLDER = "queue"
ARDUINO_PORT = "COM13" 
CHECK_INTERVAL=1 # Checking printer connection after this many seconds
file_counts={}
app = Flask(__name__)
print_queue = {}
current_print = None
printer_connected = False
printer_status_message = "Checking printer connection..."
queue_running = False
camera = cv2.VideoCapture(0)
Print_now_folder = "Print_now_files"  # folder for print-now files

if not os.path.exists(Print_now_folder):
    os.makedirs(Print_now_folder)  

def check_printer_connection():
    global printer_connected, printer_status_message

    # ports = [p.device for p in list_ports.comports()]
    # print(f"🔍 Detected Ports: {ports}")

    if PORT :
        try:
            ser = serial.Serial(PORT, BAUDRATE, timeout=2)
            time.sleep(2)
            ser.write(b"\r\n\r\n")  
            time.sleep(1)
            ser.reset_input_buffer()
            printer_connected = True
            printer_status_message = "✅ Printer is connected!"
            ser.close()
        except serial.SerialException as e:
            printer_connected = False
            printer_status_message = f"❌ Error: Could not connect to {PORT}. {e}"
    else:
        printer_connected = False
        printer_status_message = f"❌ Printer not found on {PORT}. Check connection."

check_printer_connection()


def periodic_printer_check():
    while True:
        check_printer_connection()
        time.sleep(CHECK_INTERVAL)


threading.Thread(target=periodic_printer_check, daemon=True).start()

def get_gcode_files():
    return sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(".gcode")])


# def send_gcode(filename):
#     global current_print

#     file_path = os.path.join(UPLOAD_FOLDER, filename)
#     if not os.path.exists(file_path):
#         print(f"❌ Error: '{filename}' not found.")
#         return

#     try:
#         ser = serial.Serial(PORT, BAUDRATE, timeout=2)
#         time.sleep(2)

#         with open(file_path, "r") as file:
#             codes = [line.strip() for line in file if line.strip() and not line.startswith(";")]

#         print(f"\n🚀 Sending {filename} to the printer...\n")
#         tqdm_bar = tqdm(codes, unit=" cmds", ncols=100)

#         for code in tqdm_bar:
#             ser.write((code + "\n").encode())  
#             while True:
#                 response = ser.readline().decode().strip()
#                 if response:
#                     print(f"< {response}")
#                 if response.lower().startswith("ok") or "error" in response.lower():
#                     break

#         print(f"✅ {filename} print completed!")
#         ser.write(("G1 Z180 ; \n").encode())
        
#         print_progress=100
#         time.sleep(COOL_DOWN_TIME) 
#         arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=2)
#         time.sleep(2)
#         arduino.write(("start").encode())

#         time.sleep(45)
#         arduino.close()
#         ser.close()
#     except Exception as e:
#         print(f"❌ Error while printing {filename}: {e}")

#     current_print = None  

# currentpriont,cooldown timer,removal display


def process_print_queue():
    global print_queue, current_print

    while print_queue:
        item = print_queue.pop(0)  # Get the first item in the queue
        file_name = item["file_name"]
        count = item["count"]

        for i in range(count):  # Print it 'count' times
            print(f"🖨️ Printing {file_name} (Attempt {i+1} of {count})")
            send_gcode(os.path.join(UPLOAD_FOLDER, file_name))  # Call send_gcode()

def send_gcode(file_path):
    global current_print
    current_print = os.path.basename(file_path)
    if not os.path.exists(file_path):
        print(f"❌ Error: '{file_path}' not found.")
        return

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=2)
        time.sleep(2)

        with open(file_path, "r") as file:
            codes = [line.strip() for line in file if line.strip() and not line.startswith(";")]

        print(f"\n🚀 Sending {os.path.basename(file_path)} to the printer...\n")
        
        for code in tqdm(codes, unit=" cmds", ncols=100):
            ser.write((code + "\n").encode())  
            while True:
                response = ser.readline().decode().strip()
                if response:
                    print(f"< {response}")
                if response.lower().startswith("ok") or "error" in response.lower():
                    break

        print(f"✅ {os.path.basename(file_path)} print completed!")
        ser.write(("G1 Z180 ; \n").encode())

        time.sleep(COOL_DOWN_TIME)
        arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=2)
        time.sleep(2)
        arduino.write(("start").encode())
        time.sleep(45)
        arduino.close()
        ser.close()

    except Exception as e:
        print(f"❌ Error while printing {os.path.basename(file_path)}: {e}")

    current_print = None  

def start_queue():
    global print_queue, current_print, queue_running,printer_connected

    if not printer_connected:
        print("❌ Printer not connected. Cannot start queue.")
        return

    if not print_queue:
        print("❌ No files in queue.")
        return

    queue_running = True

    while queue_running and printer_connected and print_queue:
        item = print_queue.pop(0)  # Get the first item in the queue
        file_name = item["file_name"]
        count = item["count"]

        for i in range(count):  # Print it 'count' times
            print(f"🖨️ Printing {file_name} (Attempt {i+1} of {count})")
            send_gcode(os.path.join(UPLOAD_FOLDER, file_name))  # Call send_gcode()

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
# LOG_FILE = "printer_logs.txt"  # Log file to store print statements

# Redirect print output to a file
# class Logger(object):
#     def __init__(self, filename=LOG_FILE):
#         self.terminal = sys.stdout
#         self.log = open(filename, "w", encoding="utf-8", buffering=1)  # ✅ Fix: Use utf-8 encoding


#     def write(self, message):
#         self.terminal.write(message)
#         self.log.write(message)

#     def flush(self):
#         self.terminal.flush()
#         self.log.flush()

# sys.stdout = Logger()  # Redirect stdout

# Flask
@app.route("/")
def index():
    return render_template(
        "index.html",
        printer_connected=printer_connected,
        printer_status_message=printer_status_message,
        current_print=current_print,
        files=get_gcode_files(),
        print_queue=print_queue,
    )


@app.route("/printer_status")
def printer_status():
    return jsonify({
        "printer_connected": printer_connected,
        "printer_status_message": printer_status_message
    })

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file selected"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename.endswith(".gcode"):
        return jsonify({"message": "Invalid file type. Please upload a .gcode file"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    if file.filename not in print_queue:
        print_queue[file.filename] = 1

    return jsonify({"message": "File uploaded successfully"}), 200

# @app.route("/logs")
# def get_logs():
#     """Serve the log file content as JSON."""
#     try:
#         with open(LOG_FILE, "r") as f:
#             logs = f.readlines()
#         return jsonify({"logs": logs})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route("/print_now", methods=["POST"])
def print_now():
    if "file" not in request.files:
        return jsonify({"message": "❌ No file selected."}), 400

    file = request.files["file"]
    
    if file.filename == "" or not file.filename.endswith(".gcode"):
        return jsonify({"message": "❌ Invalid file type. Please upload a .gcode file."}), 400

    file_path = os.path.join(Print_now_folder, file.filename)  # Save file in temp folder
    file.save(file_path)  # Save the uploaded file

    # Start the printing process
    threading.Thread(target=send_gcode, args=(file_path,), daemon=True).start()

    return jsonify({"message": f"🖨️ Printing {file.filename} now!"}), 200

@app.route("/start_printing")
def start_printing():
    threading.Thread(target=process_print_queue).start()  # Run in background
    return redirect(url_for("index"))

# @app.route('/adjust_count', methods=['POST'])
# def adjust_count():
#     data = request.get_json()
    
#     print("Received Data:", data)  # Debugging Line
    
#     if not data:
#         return jsonify({"error": "Invalid JSON data"}), 400

#     filename = data.get("file_name")
#     action = data.get("action")

#     if not filename or action not in ["increase", "decrease"]:
#         return jsonify({"error": "Invalid input"}), 400

#     # Initialize file count if not exists
#     if filename not in file_counts:
#         file_counts[filename] = 0

#     # Adjust the count
#     if action == "increase":
#         file_counts[filename] += 1
#     elif action == "decrease" and file_counts[filename] > 0:
#         file_counts[filename] -= 1

#     # Print the updated count
#     print(f"File: {filename}, Count: {file_counts[filename]}")

#     return jsonify({"file_name": filename, "count": file_counts[filename]})







@app.route("/clear_queue", methods=["POST"])
def clear_queue():
    """Clear the print queue."""
    global print_queue
    print_queue = {}  
    return jsonify({"message": "Queue cleared successfully"}), 200

@app.route("/start_queue", methods=["POST"])
def start_queue_route():
    """Start processing the queue."""
    global queue_running

    if not printer_connected:
        return jsonify({"message": "Printer not connected. Please check connection."}), 400

    if not print_queue:
        return jsonify({"message": "No files in queue to print."}), 400

    if not queue_running:
        queue_thread = threading.Thread(target=start_queue, daemon=True)
        queue_thread.start()
        return jsonify({"message": "Queue started printing!"}), 200

    return jsonify({"message": "Queue is already running."}), 400

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Run Flask
if __name__ == "__main__":
    app.run(debug=True)

