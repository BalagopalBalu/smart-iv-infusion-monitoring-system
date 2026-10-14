# Smart IV Monitoring Dashboard

A laptop-only Flask dashboard for the existing Smart IV prototype:
- ESP32-CAM serial drop-event detection at 115200 baud
- forwards `COUNT:<count>\n` to Arduino UNO at 9600 baud
- camera stream embedded directly in the browser
- drop activity chart, optional weight trend, alert/event history, CSV export
- local-only web server at `http://127.0.0.1:5000`

## Important: avoid opening the same COM ports twice

This app combines the Python serial relay and the dashboard backend so that only one process owns COM7 and COM4.

1. Back up your current working `iv_relay.py` and Arduino UNO sketch.
2. Stop the old relay (`Ctrl+C`) before starting this app.
3. Close Serial Monitor windows for COM7 and COM4 in Arduino IDE.
4. Start this dashboard. Do not run the old relay at the same time.
5. The app uses the same event pattern and forwarding message as your working relay:
   - ESP32-CAM: `IV: DROP EVENT | Count: 9`
   - Arduino UNO: `COUNT:9\n`
6. The ESP serial connection sets DTR and RTS to `False` before opening to reduce unintended ESP32-CAM resets.

## Install and run (Windows)

Open Command Prompt in this folder and run:

```bat
python -m pip install -r requirements.txt
python app.py
```

Or double-click `run_dashboard.bat`.

Then open **http://127.0.0.1:5000** in the laptop browser. The server binds to `127.0.0.1`, not the LAN, so it is not exposed to other devices on Wi-Fi.

If `pip` or Flask fails under your Python 3.15 preview installation, install a stable supported Python release (Python 3.12 or 3.13) and run the commands using that interpreter. Keep your existing Python installation if it is needed for the current relay.

## Camera stream

Open the CameraWebServer page and use the actual stream URL configured by your sketch. In many ESP32-CAM CameraWebServer examples, the stream URL is similar to:

`http://ESP32-CAM-IP:81/stream`

Replace `ESP32-CAM-IP` with the camera's actual IP address. Save it under **Connection settings**. The dashboard displays the stream directly in the browser; it does not proxy or restart the camera. If the camera uses a different URL, use that URL instead.

## Weight telemetry caveat

The dashboard does **not** change the UNO firmware automatically. Your current working UNO code can continue to display weight and alerts on the LCD, and the drop-count relay can still work. For live weight charts and web weight alerts, the UNO must also send a telemetry line over its existing USB serial connection.

The dashboard understands this line format at 9600 baud:

```text
TELEMETRY:weight=123.4,status=NORMAL,count=9
```

Example low-weight line:

```text
TELEMETRY:weight=92.0,status=LOW_WEIGHT,count=9
```

Add telemetry output to your *existing* UNO sketch after it has calculated the current estimated weight and status. Use your sketch's actual variable names, and print at a slow rate (about once per second). For example, adapt the following lines inside your existing `loop()` after the weight/status values are updated:

```cpp
Serial.print("TELEMETRY:weight=");
Serial.print(estimatedWeight, 1);  // replace with your actual weight variable
Serial.print(",status=");
Serial.print(lowWeight ? "LOW_WEIGHT" : "NORMAL"); // replace with your actual alert condition
Serial.print(",count=");
Serial.println(dropCount); // replace with your actual received count variable
```

Do **not** paste this blindly if your variable names differ. Do not remove the current `COUNT:` receiver, HX711 handling, LCD code, LED or buzzer logic. Back up the working sketch first. If you share your current UNO sketch, the exact telemetry insertion can be made without guessing names.

If your existing sketch already prints a line like `Estimated Weight: 123.4 g`, the dashboard can attempt to read that too, but the explicit `TELEMETRY:` format is preferred. Do not use Arduino Serial Monitor while the dashboard is connected.

## Dashboard notes

- The CSV button exports the event history saved by the app.
- History is stored in `events.json` in this folder.
- Reset display changes the dashboard count only; it does not reset the ESP32-CAM's own counter.
- Changing serial port settings requires restarting `app.py`.
- A blank weight card means no weight telemetry has been received yet; it does not mean the hardware is disconnected.
- The dashboard is for a student prototype and is not a clinically validated infusion controller.
