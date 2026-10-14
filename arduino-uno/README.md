# Arduino UNO Firmware

This folder contains the main controller firmware for the Smart IV Infusion Monitoring System.

## Responsibilities
- Receive the drop count from the Python serial relay.
- Read bottle weight through the HX711 load-cell module.
- Display monitoring information on the I2C LCD.
- Activate the LED and buzzer when the configured low-weight threshold is reached.

## Hardware Connections
- HX711 DT: Digital pin 3
- HX711 SCK: Digital pin 2
- LED: Digital pin 8
- Buzzer: Digital pin 9
- LCD: I2C interface

See the main project README for setup instructions.

**Note:** Upload the tested Arduino sketch in this folder before considering this component complete.
