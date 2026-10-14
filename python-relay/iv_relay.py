
import re
import time
import serial

ESP_PORT = "COM7"
UNO_PORT = "COM4"

esp = None
uno = None

try:
    # Open ESP32-CAM serial with DTR/RTS disabled before opening.
    esp = serial.Serial()
    esp.port = ESP_PORT
    esp.baudrate = 115200
    esp.timeout = 1
    esp.dtr = False
    esp.rts = False
    esp.open()

    # Open Arduino UNO serial.
    uno = serial.Serial(UNO_PORT, 9600, timeout=1)

    time.sleep(2)

    print("Smart IV relay started.")
    print("Waiting for IV drop events...")
    print("Press Ctrl+C to stop.")

    while True:
        raw = esp.readline()

        if not raw:
            continue

        line = raw.decode("utf-8", errors="ignore").strip()

        if line:
            print("ESP32:", line)

        match = re.search(
            r"IV:\s*DROP EVENT\s*\|\s*Count:\s*(\d+)",
            line
        )

        if match:
            count = int(match.group(1))
            message = f"COUNT:{count}\n"

            uno.write(message.encode("ascii"))
            print("Sent to UNO:", message.strip())

except KeyboardInterrupt:
    print("\nRelay stopped.")

except serial.SerialException as error:
    print("Serial port error:", error)
    print("Check COM ports and close Serial Monitor windows.")

finally:
    if esp is not None and esp.is_open:
        esp.close()

    if uno is not None and uno.is_open:
        uno.close()

    print("Serial ports closed.")
