
# 3D Printer Web Interface

This project is a Flask-based web interface for monitoring and controlling a 3D printer. It allows users to upload G-code files, manage a print queue, monitor live printing progress, and view a real-time camera feed.

## Features
- **Printer Status Monitoring**: Checks and displays printer connection status.
- **File Upload & Print Queue**: Upload `.gcode` files and manage a print queue.
- **Real-time Print Progress**: Displays printing progress percentage.
- **Cooldown Timer**: Starts a countdown after print completion.
- **Live Camera Feed**: Streams real-time footage of the printing process.
- **Alerts & Notifications**: Displays alerts when printing and cooldown are complete.

## Installation
1. **Clone the repository**  
   ```bash
   git clone https://github.com/yourusername/3d-printer-interface.git
   cd 3d-printer-interface

## Create and activate a virtual environment

python -m venv venv
source venv/bin/activate  

 # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py

# Access the interface
Open a browser and go to:
 # http://127.0.0.1:5000/

# Dependencies
Python 3.x
Flask
OpenCV (for live camera feed)
pySerial (for printer communication)
tqdm (for print progress tracking)
pySerial Tools (for listing ports)

# Folder Structure


3d-printer-interface/
│── uploads/           # Directory for uploaded G-code files
│── Print_now_files/   # Temp folder for immediate prints
│── templates/         # HTML templates (index.html)
│── static/            # Static assets (CSS, JS)
│── app.py             # Main Flask application
│── requirements.txt   # List of dependencies
│── README.md          # Project documentation

# API Endpoints
/ → Web interface
/upload → Upload G-code file
/start_queue → Start the print queue
/print_now → Print file immediately
/video_feed → Live camera stream
/printer_status → Check printer connection
/current_print_status → Get current print progress

# Notes
Ensure your printer is connected and configured correctly.
Modify PORT and ARDUINO_PORT in app.py if needed.
For camera streaming, ensure OpenCV supports your webcam.
