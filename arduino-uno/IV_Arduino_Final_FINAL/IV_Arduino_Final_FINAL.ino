
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "HX711.h"

#define DT_PIN 3
#define SCK_PIN 2
#define LED_PIN 8
#define BUZZER_PIN 9

LiquidCrystal_I2C lcd(0x27, 16, 2);
HX711 scale;

const float CALIBRATION_FACTOR = -392.4;
const float EMPTY_BOTTLE_BASELINE = 655177.0;
const float LOW_WEIGHT_LIMIT = 100.0;

unsigned long previousLCDUpdate = 0;
unsigned long previousAlarm = 0;

float estimatedWeight = 0.0;
bool lowLevel = false;

unsigned long dropCount = 0;
char serialBuffer[32];
byte bufferIndex = 0;

void readDropCount() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        serialBuffer[bufferIndex] = '\0';

        if (strncmp(serialBuffer, "COUNT:", 6) == 0) {
          dropCount = strtoul(serialBuffer + 6, NULL, 10);
        }

        bufferIndex = 0;
      }
    } else if (bufferIndex < sizeof(serialBuffer) - 1) {
      serialBuffer[bufferIndex++] = c;
    } else {
      bufferIndex = 0;
    }
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  noTone(BUZZER_PIN);

  lcd.init();
  lcd.backlight();
  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print("SMART IV SYSTEM");
  lcd.setCursor(0, 1);
  lcd.print("Starting...");
  delay(1500);

  scale.begin(DT_PIN, SCK_PIN);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Load Cell Ready");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  delay(1000);

  lcd.clear();
}

void loop() {
  readDropCount();

  if (!scale.is_ready()) {
    delay(10);
    return;
  }

  long rawReading = scale.read();

  estimatedWeight =
      (rawReading - EMPTY_BOTTLE_BASELINE) / CALIBRATION_FACTOR;

  if (estimatedWeight < 0) {
    estimatedWeight = 0;
  }

  lowLevel = (estimatedWeight <= LOW_WEIGHT_LIMIT);

  unsigned long now = millis();

  if (now - previousLCDUpdate >= 500) {
    previousLCDUpdate = now;

    lcd.setCursor(0, 0);
    lcd.print("Weight:         ");
    lcd.setCursor(8, 0);
    lcd.print(estimatedWeight, 1);
    lcd.print("g "); 
    lcd.setCursor(0, 1);

    if (lowLevel) {
        lcd.print("LOW LEVEL ALERT ");
    } else if (dropCount > 0) {
        lcd.print("IV Rate: Normal ");
    } else {
        lcd.print("Waiting for drop");
    }
  }

  if (lowLevel) {
    digitalWrite(LED_PIN, HIGH);

    if (now - previousAlarm >= 2000) {
      previousAlarm = now;
      tone(BUZZER_PIN, 1000, 300);
    }
  } else {
    digitalWrite(LED_PIN, LOW);
    noTone(BUZZER_PIN);
  }
}
