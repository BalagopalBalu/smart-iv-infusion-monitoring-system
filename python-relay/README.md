# Python Serial Relay

This component connects the ESP32-CAM drop-count output to the Arduino UNO.

## Responsibilities
- Read serial messages from the ESP32-CAM.
- Extract the detected drop count.
- Forward the count to the Arduino UNO.
- Handle serial-port communication and recovery.

## Setup
Install the required Python dependencies, configure the correct COM ports, and close conflicting serial-monitor applications before running the relay.

Upload the tested Python relay script into this folder.
