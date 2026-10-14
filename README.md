# Smart IV Infusion Monitoring System

**An Arduino-Based Smart Healthcare Prototype with Camera-Assisted Drop Detection, Weight Monitoring, and a Python Dashboard**

[![Platform](https://img.shields.io/badge/Platform-Arduino%20UNO-00979D?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![Language](https://img.shields.io/badge/Language-C%2B%2B%20%7C%20Python-blue)](https://www.python.org/)
[![Camera](https://img.shields.io/badge/Camera-ESP32--CAM-orange)](https://github.com/espressif/esp32-camera)
[![Dashboard](https://img.shields.io/badge/Dashboard-Flask-black?logo=flask)](https://flask.palletsprojects.com/)

## Overview

The **Smart IV Infusion Monitoring System** is an educational hardware–software prototype designed to demonstrate automated observation of an intravenous (IV) fluid setup. It combines camera-assisted drop-event detection, bottle-weight measurement, embedded control, local alerts, and a web-based monitoring dashboard.

An ESP32-CAM captures the drip chamber and performs motion-based drop-event detection. A Python serial relay transfers the detected count to an Arduino UNO. Meanwhile, a load cell connected through an HX711 module measures the suspended bottle's weight. The Arduino processes the available readings, updates an I²C LCD, and activates an LED and buzzer when the configured low-weight threshold is crossed.

A Flask-based dashboard provides a centralized interface for viewing the available monitoring information and camera stream.

> **Project type:** Academic prototype  
> **Domain:** Embedded Systems · IoT · Smart Healthcare · Software Integration

## Key Features

- **Camera-assisted drop detection:** ESP32-CAM captures the drip chamber and detects potential drop events using motion analysis.
- **Bottle-weight monitoring:** Load cell and HX711 module provide weight measurements.
- **Embedded control:** Arduino UNO receives drop counts and manages local monitoring functions.
- **LCD display:** Presents available readings and system status.
- **Low-weight alert:** LED and buzzer provide local warnings based on a configured threshold.
- **Serial communication:** Python relays drop-count data from the ESP32-CAM to the Arduino UNO.
- **Web dashboard:** Flask application provides a browser-based monitoring interface.
- **Live camera stream:** Allows visual observation of the drip chamber through the dashboard.
- **Extensible architecture:** Provides a foundation for future data logging, trend analysis, and additional monitoring calculations.

## System Architecture

```text
             IV Drip Chamber
                    |
                    v
                ESP32-CAM
          Camera Stream and
          Drop-Event Detection
                    |
             Serial Interface
                    |
                    v
             Python Serial Relay
                    |
             USB Serial to UNO
                    |
                    v
               Arduino UNO <------ HX711 <------ Load Cell
                    |
             +------+------+
             |             |
             v             v
          I2C LCD       LED + Buzzer
       Readings/Status   Local Alert

        Laptop / Computer
        +----------------------+
        | Python Relay         |
        | Flask Web Dashboard  |
        | Live Stream and Data  |
        +----------------------+
```

## Hardware Components

| Component | Purpose |
|---|---|
| Arduino UNO | Main controller for monitoring and local alerts |
| ESP32-CAM | Camera streaming and drop-event detection |
| Load cell | Measures the suspended bottle's load |
| HX711 module | Interfaces the load cell with the Arduino |
| 16×2 I²C LCD | Displays monitoring information |
| LED | Visual low-weight warning |
| Buzzer | Audible low-weight warning |
| Laptop/PC | Runs the Python relay and dashboard |
| Jumper wires and breadboard | Circuit connections and prototyping |

## Software and Tools

- **Arduino IDE** — firmware development and uploading
- **Embedded C/C++** — Arduino and ESP32-CAM programming
- **Python** — serial communication and application logic
- **Flask** — web dashboard
- **PySerial** — serial-port communication
- **HTML, CSS, and JavaScript** — dashboard interface
- **HX711 and LCD libraries** — sensor and display interfacing

Refer to the source files and `requirements.txt` for the dependencies used by each component.

## Repository Structure

```text
smart-iv-infusion-monitoring-system/
│
├── arduino-uno/
│   ├── README.md
│   └── smart_iv_arduino.ino
│
├── esp32-cam/
│   ├── README.md
│   └── smart_iv_camera.ino
│
├── python-relay/
│   ├── README.md
│   └── iv_relay.py
│
├── Smart_IV_Monitoring_Dashboard/
│   ├── app.py
│   ├── templates/
│   ├── static/
│   ├── requirements.txt
│   └── config.json
│
└── README.md
```

*The filenames and dashboard folder shown above are examples; adjust this tree to match the files actually committed to the repository.*

## Getting Started

### 1. Download the project

Clone the repository or use GitHub's **Code → Download ZIP** option.

### 2. Set up the hardware

Connect the Arduino UNO, ESP32-CAM, load cell, HX711, LCD, LED, and buzzer according to the wiring documented in the corresponding source files.

### 3. Upload the firmware

- Open the Arduino UNO sketch in Arduino IDE and upload it to the UNO.
- Configure the ESP32-CAM board and network settings, then upload the camera firmware.
- Confirm that each board operates correctly before starting the Python software.

### 4. Install Python dependencies

Open a terminal in the dashboard project directory and run:

```bash
python -m pip install -r requirements.txt
```

### 5. Configure serial ports and camera URL

Check the COM port assigned to each board in Device Manager. Update the software configuration to match your computer and local network.

Close Arduino IDE Serial Monitor windows that are using the same COM ports before launching the Python applications.

### 6. Launch the dashboard

From the dashboard project directory, run:

```bash
python app.py
```

Open the local dashboard in your browser:

```text
http://127.0.0.1:5000
```

Keep the terminal running while using the dashboard. Stop the application with `Ctrl+C`.

**Note:** Follow the actual configuration and startup instructions included with the uploaded project files if they differ from these general steps.

## Testing and Validation

The prototype has been tested for the following functions during development:

- Drop-count detection and transfer to the Arduino UNO
- Bottle-weight measurement
- Low-weight alert activation
- Normal-weight indication
- Live camera-stream operation
- Recovery after restarting or reconnecting components

Performance depends on sensor calibration, camera placement, lighting, serial communication, and operating conditions. These development tests do not establish clinical accuracy or medical-device safety.

## Future Enhancements

Potential improvements include:

- More robust drop detection under different lighting and background conditions
- Calibrated, timestamp-based infusion-rate estimation
- Estimated remaining-fluid calculations using validated weight measurements
- Approximate time-to-completion estimation when a reliable rate is available
- Historical graphs and event logging
- Communication-failure indicators and configurable notifications
- Improved sensor calibration and systematic reliability testing

These are proposed enhancements unless explicitly implemented and validated in the current version.

## Contributors

**Balagopal M S**  
Electronics and Communication Engineering — Data Science

**Gokulakrishna G**  
Electronics and Communication Engineering

SRM Institute of Science and Technology, Ramapuram

**Course:** Microprocessor, Microcontroller and Interfacing Techniques — 21ECC301P

## Disclaimer

This project is developed for **academic learning, demonstration, and research purposes only**. It is not a certified medical device and has not been clinically validated. It must not be used to make clinical decisions or to monitor or control an actual patient's IV infusion.

## License

No license has been specified yet. If you intend to permit public reuse or modification, consider adding an appropriate open-source license after confirming the terms you want to use.
