#include <Arduino.h>

#include <iostream>

#include "ds3231_live.hpp"
#include "espNOW_recieve.hpp"
#include "sd_read.hpp"
#include "ssd1306_display.hpp"
#include "webserver.hpp"

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
#define SCREEN_WIDTH 128  // OLED display width, in pixels
#define SCREEN_HEIGHT 64  // OLED display height, in pixels
#define OLED_RESET -1     // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

RTC_DS3231 rtc;

LatestReadings latest_readings;
TimeDifference timeDifference;

String LATEST_READING_UPDATE;

void onDataReceived(uint8_t *senderMac, uint8_t *incomingData, uint8_t len) {
  uint8_t recieved[len + 1];
  Serial.print("Received: ");
  for (int i = 0; i < len; i++) {
    Serial.print((char)incomingData[i]);
    recieved[i] = incomingData[i];
  }

  Serial.println();

  String recievedString = String((char *)recieved);
  sdWriteLatestReading(getFilename(rtc), recievedString);

  ssd1306DisplayClear(display);
}

void setup() {
  Serial.begin(115200);
  ssd1306DisplaySetup(display);
  setupDS3231(rtc);
  sdReadSetup();
  ssd1306DisplayClear(display);

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Print MAC address of the receiver
  Serial.print("Receiver MAC: ");
  for (int i = 0; i < 6; i++) {
    Serial.print(WiFi.macAddress()[i], HEX);
    if (i < 5) {
      Serial.print(":");
    }
  }

  Serial.println();
  // Initialize ESP-NOW
  if (esp_now_init() != 0) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register callback for receiving data
  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);
  esp_now_register_recv_cb(onDataReceived);
}

void loop() {
  String dayDate = getDayDate(rtc);
  String time = getTime(rtc);

  // Refreshes the time section of the display only (ie line 2 & line 8)
  int x, y;
  for (y = 7; y <= 14; y++) {
    for (x = 0; x < 127; x++) {
      display.drawPixel(x, y, BLACK);
    }
  }
  for (y = 55; y <= 63; y++) {
    for (x = 0; x < 127; x++) {
      display.drawPixel(x, y, BLACK);
    }
  }
  ssd1306DisplayLiveTime(display, dayDate, time);
  timeDifference =
      getTimeDifference(rtc, latest_readings.time, latest_readings.dayDate);

  // Get todays filename
  String filename = getFilename(rtc);

  sdReadGetLastLine(filename);
  sdReadGetLatestReadings(latest_readings);

  Serial.println("Setup complete.");
  Serial.println("Temperature: " + String(latest_readings.temperature));
  Serial.println("Humidity: " + String(latest_readings.humidity));
  Serial.println("Pressure: " + String(latest_readings.pressure));
  Serial.println("Wind Speed: " + String(latest_readings.windSpeed));
  Serial.println("Wind Direction: " + latest_readings.windDirection);
  Serial.println("Battery Percentage: " +
                 String(latest_readings.batteryPercentage));
  Serial.println("Day Date: " + latest_readings.dayDate);
  Serial.println("Time: " + latest_readings.time);
  Serial.println("Time Difference: " + String(timeDifference.hours) +
                 " hours " + String(timeDifference.minutes) + " minutes " +
                 String(timeDifference.seconds) + " seconds");

  ssd1306DisplayReadings(
      display, latest_readings.temperature, latest_readings.humidity,
      latest_readings.pressure, latest_readings.windSpeed,
      latest_readings.windDirection, latest_readings.batteryPercentage,
      timeDifference.hours, timeDifference.minutes, timeDifference.seconds);
  delay(700);
}