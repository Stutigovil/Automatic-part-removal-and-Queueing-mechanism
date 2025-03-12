
import os
import time
import serial
import threading
import cv2
from flask import Flask, render_template, request, jsonify,Response,stream_with_context
from serial.tools import list_ports
from tqdm import tqdm


cooldown_time = 180
PORT = "COM5"
ARDUINO_PORT = "COM13" #arduino's port
BAUDRATE = 115200
UPLOAD_FOLDER = "uploads"
camera = cv2.VideoCapture(0)
print_progress=0

app = Flask(__name__)
print_queue = {} 
current_print = None
printer_connected = False
printer_status_message = "Checking printer connection..."
queue_running = False

def check_printer_connection():
    global printer_connected, printer_status_message

    ports = [p.device for p in list_ports.comports()]
    print(f"🔍 Detected Ports: {ports}")

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

check_printer_connection()

def get_gcode_files():
    return sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(".gcode")])


def send_gcode(filename):
    global current_print,print_progress

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        print(f"❌ Error: '{filename}' not found.")
        return

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=2)
        time.sleep(2)

        with open(file_path, "r") as file:
            codes = [line.strip() for line in file if line.strip() and not line.startswith(";")]

        total_commands=len(codes)
        print_progress=0
        print(f"\n🚀 Sending {filename} to the printer...\n")
        tqdm_bar = tqdm(codes, unit=" cmds", ncols=100)

        for code in tqdm_bar:
            ser.write((code + "\n").encode())  
            while True:
                response = ser.readline().decode().strip()
                if response:
                    print(f"< {response}")
                if response.lower().startswith("ok") or "error" in response.lower():
                    break
            print_progress=int(((index+1)/total_commands)*100)
        print(f"✅ {filename} print completed!")
        ser.write(("G1 Z180 ; \n").encode())
        ser.close()
        print_progress=100
        time.sleep(cooldown_time) 
        arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=2)
        time.sleep(2)
        arduino.serial.write(("start").encode())
        time.sleep(20)
        arduino.close()
    except Exception as e:
        print(f"❌ Error while printing {filename}: {e}")

    current_print = None  
    print_progress=0


def start_queue():
    global current_print, queue_running

    if not printer_connected:
        print("❌ Printer not connected. Cannot start queue.")
        return

    if not print_queue:
        print("❌ No files in queue.")
        return

    queue_running = True

    while queue_running and printer_connected and print_queue:
        filename, count = print_queue.popitem()
        for _ in range(count):
            print(f"🖨️ Printing: {filename}")
            send_gcode(filename)
            time.sleep(1)

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
@app.route("/print_progress")
def print_progress_Status():
    return jsonify({"progress":print_progress})

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
    data = request.get_json()
    filename = data.get("filename")

    if not printer_connected:
        return jsonify({"message": "❌ Printer not connected. Please check the connection."}), 400

    if not filename:
        return jsonify({"message": "❌ No file selected."}), 400

    threading.Thread(target=send_gcode, args=(filename,), daemon=True).start()
    return jsonify({"message": f"🖨️ Printing {filename} now!"}), 200


@app.route("/adjust_count", methods=["POST"])
def adjust_count():
    data = request.get_json()
    filename = data.get("filename")
    delta = data.get("delta")

    if filename in print_queue:
        print_queue[filename] = max(1, print_queue[filename] + delta)
        return jsonify({"message": "✅ Count updated!", "count": print_queue[filename]}), 200

    return jsonify({"message": "❌ File not found in queue."}), 400


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
# def start_queueing_mechanism():
#     print("✅ 3D Printing Queue Mechanism Started!")
    # Your existing queuing logic goes here

# if __name__ == "__main__":
#     start_queueing_mechanism()

# Run Flask
# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    app.run(debug=True, port=5001)  # Use a different port (5001)
