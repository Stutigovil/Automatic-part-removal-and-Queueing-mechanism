import os
import time
import serial
import threading
from flask import Flask, render_template, request, jsonify,Response,redirect,url_for
from serial.tools import list_ports
from tqdm import tqdm
import cv2


COOL_DOWN_TIME = 300  #cooldown in seconds
PORT = "COM5" #printer's port
BAUDRATE = 115200
UPLOAD_FOLDER = "uploads"
ARDUINO_PORT = "COM13" 
CHECK_INTERVAL=1 # Checking printer connection after this many seconds
file_counts={}
app = Flask(__name__)
print_queue = {}
current_print = None
printer_connected = False
printer_status_message = "Checking printer connection..."
queue_running = False
current_print_progress = {"file": None, "progress": 0, "total": 0}  # Track printing progress

camera = cv2.VideoCapture(0)

Print_now_folder = "Print_now_files"  # folder for print-now files


if not os.path.exists(Print_now_folder):
    os.makedirs(Print_now_folder)
      
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def check_printer_connection():
    global printer_connected, printer_status_message

    ports = [p.device for p in list_ports.comports()]
    # print(f"🔍 Detected Ports: {ports}")

    if PORT in ports:
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

def periodic_printer_check():
    while True:
        check_printer_connection()
        time.sleep(CHECK_INTERVAL)

def get_gcode_files():
    return sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(".gcode")])

def process_print_queue():
    global print_queue, current_print

    while print_queue:
        item = print_queue.pop(0)  # Get the first item in the queue
        file_name = item["file_name"]
        count = item["count"]

        for i in range(count):  # Print it 'count' times
            print(f"🖨 Printing {file_name} (Attempt {i+1} of {count})")
            send_gcode(os.path.join(UPLOAD_FOLDER, file_name))  # Call send_gcode()

def send_gcode(file_path):
    global current_print, current_print_progress
    current_print = os.path.basename(file_path)
    if not os.path.exists(file_path):
        print(f"❌ Error: '{file_path}' not found.")
        return
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=2)
        time.sleep(2)
        with open(file_path, "r") as file:
            codes = [line.strip() for line in file if line.strip() and not line.startswith(";")]
        total_lines = len(codes)
        current_print_progress = {"file": current_print, "progress": 0, "total": total_lines}
        print(f"\n🚀 Sending {os.path.basename(file_path)} to the printer...\n")
        for i, code in enumerate(tqdm(codes, unit=" cmds", ncols=100)):
            ser.write((code + "\n").encode())
            while True:
                response = ser.readline().decode().strip()
                if response:
                    print(f"< {response}")
                if response.lower().startswith("ok") or "error" in response.lower():
                    break
            current_print_progress["progress"] = i + 1
        print(f"✅ {os.path.basename(file_path)} print completed!")
        ser.write(("G1 Z180 ; \n").encode())
        time.sleep(COOL_DOWN_TIME)
        arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=2)
        time.sleep(2)
        arduino.write("start".encode())
        time.sleep(45)
        arduino.close()
        ser.close()
    except Exception as e:
        print(f"❌ Error while printing {os.path.basename(file_path)}: {e}")
    current_print = None
    current_print_progress = {"file": None, "progress": 0, "total": 0}

def start_queue():
    global printer_connected, print_queue, current_print, queue_running

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
            print(f"🖨 Printing {file_name} (Attempt {i+1} of {count})")
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
            
# Flask

check_printer_connection()
threading.Thread(target=periodic_printer_check, daemon=True).start()

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
    
@app.route("/current_print_status")
def current_print_status():
    return jsonify(current_print_progress)

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

    return jsonify({"message": f"🖨 Printing {file.filename} now!"}), 200

@app.route("/start_printing")
def start_printing():
    threading.Thread(target=process_print_queue).start()  # Run in background
    return redirect(url_for("index"))

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


# Run Flask
if __name__ == "_main_":
    app.run(debug=True)