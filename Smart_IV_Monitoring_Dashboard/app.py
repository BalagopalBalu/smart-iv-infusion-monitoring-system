from __future__ import annotations

import csv
import io
import json
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import serial
from serial import SerialException
from flask import Flask, jsonify, render_template, request, Response

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EVENTS_PATH = BASE_DIR / "events.json"

DEFAULT_CONFIG = {
    "esp_port": "COM7",
    "uno_port": "COM4",
    "esp_baud": 115200,
    "uno_baud": 9600,
    "camera_url": "",
    "low_weight_limit_g": 150.0,
    "auto_connect": True
}

app = Flask(__name__)

def load_config():
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

config = load_config()
lock = threading.RLock()
stop_event = threading.Event()
esp_serial = None
uno_serial = None

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def load_events():
    if EVENTS_PATH.exists():
        try:
            data = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
            return deque(data[-1000:], maxlen=1000)
        except Exception:
            pass
    return deque(maxlen=1000)

events = load_events()
state = {
    "drop_count": 0,
    "weight_g": None,
    "weight_status": "WAITING FOR UNO TELEMETRY",
    "system_status": "DISCONNECTED",
    "esp_status": "Disconnected",
    "uno_status": "Disconnected",
    "last_drop_at": None,
    "last_update": now_iso(),
    "camera_url": config.get("camera_url", ""),
    "low_weight_limit_g": float(config.get("low_weight_limit_g", 150.0)),
    "latest_esp_line": "",
    "latest_uno_line": "",
    "error": "",
    "alerts": []
}
alert_ids = set()

def add_event(kind, message, value=None):
    event = {
        "time": now_iso(),
        "kind": kind,
        "message": message,
        "value": value
    }
    with lock:
        events.append(event)
        try:
            EVENTS_PATH.write_text(json.dumps(list(events), indent=2), encoding="utf-8")
        except Exception:
            pass
        if kind == "alert":
            state["alerts"].insert(0, event)
            del state["alerts"][50:]
        state["last_update"] = event["time"]

def parse_esp_line(line):
    match = re.search(r"IV:\s*DROP EVENT\s*\|\s*Count:\s*(\d+)", line, re.I)
    if match:
        count = int(match.group(1))
        with lock:
            previous = state["drop_count"]
            state["drop_count"] = max(previous, count)
            state["last_drop_at"] = now_iso()
            state["last_update"] = state["last_drop_at"]
        add_event("drop", f"IV drop detected — count {count}", count)
        return count
    # Optional alternative protocol if the camera firmware emits it.
    match = re.search(r"(?:DROP_COUNT|COUNT)\s*[:=]\s*(\d+)", line, re.I)
    if match:
        count = int(match.group(1))
        with lock:
            state["drop_count"] = count
            state["last_update"] = now_iso()
        return count
    return None

def parse_uno_line(line):
    # Supported telemetry format:
    # TELEMETRY:weight=123.4,status=NORMAL,count=12
    match = re.search(
        r"TELEMETRY:\s*weight\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*status\s*=\s*([A-Z_ -]+)(?:\s*,\s*count\s*=\s*(\d+))?",
        line, re.I
    )
    if match:
        weight = float(match.group(1))
        status = match.group(2).strip().upper()
        count = match.group(3)
        with lock:
            state["weight_g"] = round(weight, 1)
            state["weight_status"] = status
            if count is not None:
                state["drop_count"] = int(count)
            state["last_update"] = now_iso()
        if status in ("LOW", "LOW_WEIGHT", "ALERT", "EMPTY", "LOW WEIGHT"):
            add_event("alert", f"Low-weight alert — estimated {weight:.1f} g", weight)
        return

    # Also accept simple lines such as "Estimated Weight: 123.4 g"
    match = re.search(r"(?:estimated\s*)?weight\s*[:=]\s*(-?\d+(?:\.\d+)?)\s*g?", line, re.I)
    if match:
        weight = float(match.group(1))
        with lock:
            state["weight_g"] = round(weight, 1)
            limit = float(state["low_weight_limit_g"])
            status = "LOW WEIGHT" if weight < limit else "NORMAL"
            state["weight_status"] = status
            state["last_update"] = now_iso()
        if weight < float(state["low_weight_limit_g"]):
            add_event("alert", f"Low-weight threshold crossed — estimated {weight:.1f} g", weight)

def serial_worker():
    global esp_serial, uno_serial
    while not stop_event.is_set():
        if not config.get("auto_connect", True):
            time.sleep(1)
            continue
        try:
            if esp_serial is None or not esp_serial.is_open:
                # Disable DTR/RTS to reduce unintended ESP32-CAM resets.
                candidate = serial.Serial()
                candidate.port = str(config["esp_port"])
                candidate.baudrate = int(config["esp_baud"])
                candidate.timeout = 1
                candidate.dtr = False
                candidate.rts = False
                candidate.open()
                esp_serial = candidate
                with lock:
                    state["esp_status"] = f"Connected · {config['esp_port']}"
                    state["error"] = ""
                add_event("system", f"ESP32-CAM serial connected on {config['esp_port']}")
            if uno_serial is None or not uno_serial.is_open:
                uno_serial = serial.Serial(
                    str(config["uno_port"]), int(config["uno_baud"]), timeout=0.25
                )
                time.sleep(2)
                with lock:
                    state["uno_status"] = f"Connected · {config['uno_port']}"
                    state["error"] = ""
                add_event("system", f"Arduino UNO connected on {config['uno_port']}")

            # Read camera serial. Same event matching and COUNT forwarding as the existing relay.
            raw = esp_serial.readline()
            if raw:
                line = raw.decode("utf-8", errors="ignore").strip()
                if line:
                    with lock:
                        state["latest_esp_line"] = line
                    count = parse_esp_line(line)
                    if count is not None and uno_serial and uno_serial.is_open:
                        uno_serial.write(f"COUNT:{count}\n".encode("ascii"))
                        add_event("relay", f"Forwarded COUNT:{count} to Arduino UNO", count)

            # Read optional UNO telemetry. This is full-duplex and does not prevent COUNT writes.
            if uno_serial and uno_serial.is_open and uno_serial.in_waiting:
                raw_uno = uno_serial.readline()
                if raw_uno:
                    line_uno = raw_uno.decode("utf-8", errors="ignore").strip()
                    if line_uno:
                        with lock:
                            state["latest_uno_line"] = line_uno
                        parse_uno_line(line_uno)

            with lock:
                if state["esp_status"].startswith("Connected") and state["uno_status"].startswith("Connected"):
                    state["system_status"] = "RUNNING"
                else:
                    state["system_status"] = "PARTIAL CONNECTION"
                state["last_update"] = now_iso()

        except (SerialException, OSError, ValueError) as exc:
            with lock:
                state["system_status"] = "CONNECTION ERROR"
                state["error"] = str(exc)
                if esp_serial is None or not getattr(esp_serial, "is_open", False):
                    state["esp_status"] = "Disconnected"
                if uno_serial is None or not getattr(uno_serial, "is_open", False):
                    state["uno_status"] = "Disconnected"
            for port_name in ("esp_serial", "uno_serial"):
                ser = globals().get(port_name)
                try:
                    if ser and ser.is_open:
                        ser.close()
                except Exception:
                    pass
                globals()[port_name] = None
            time.sleep(2)
        except Exception as exc:
            with lock:
                state["error"] = f"Unexpected error: {exc}"
            time.sleep(1)

def get_snapshot():
    with lock:
        result = dict(state)
        result["alerts"] = list(state["alerts"])
        result["event_count"] = len(events)
        return result

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/state")
def api_state():
    return jsonify(get_snapshot())

@app.get("/api/events")
def api_events():
    with lock:
        return jsonify(list(events)[::-1])

@app.post("/api/config")
def api_config():
    global config
    incoming = request.get_json(silent=True) or {}
    allowed = ("esp_port", "uno_port", "camera_url", "low_weight_limit_g")
    updated = dict(config)
    for key in allowed:
        if key in incoming:
            updated[key] = incoming[key]
    try:
        updated["low_weight_limit_g"] = max(0.0, float(updated["low_weight_limit_g"]))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Weight threshold must be a number."}), 400
    updated["esp_port"] = str(updated["esp_port"]).strip()
    updated["uno_port"] = str(updated["uno_port"]).strip()
    updated["camera_url"] = str(updated["camera_url"]).strip()
    config = updated
    with lock:
        state["camera_url"] = config["camera_url"]
        state["low_weight_limit_g"] = config["low_weight_limit_g"]
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "config": config})

@app.post("/api/reset-count")
def api_reset_count():
    # Dashboard-only reset; it does not reset the ESP32-CAM's internal counter.
    with lock:
        state["drop_count"] = 0
    add_event("system", "Dashboard drop-count display reset (camera counter unchanged)")
    return jsonify({"ok": True})

@app.post("/api/clear-history")
def api_clear_history():
    with lock:
        events.clear()
        state["alerts"] = []
        EVENTS_PATH.write_text("[]", encoding="utf-8")
    add_event("system", "Event history cleared from dashboard")
    return jsonify({"ok": True})

@app.get("/api/export.csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "type", "message", "value"])
    with lock:
        snapshot = list(events)
    for item in snapshot:
        writer.writerow([item.get("time"), item.get("kind"), item.get("message"), item.get("value", "")])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=smart_iv_event_history.csv"}
    )

def start_worker():
    thread = threading.Thread(target=serial_worker, daemon=True, name="serial-worker")
    thread.start()

if __name__ == "__main__":
    if config.get("auto_connect", True):
        start_worker()
    # Bind only to localhost: laptop-only access.
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
