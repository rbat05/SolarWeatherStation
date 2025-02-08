#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <espnow.h>

#include <iostream>

#include "ds3231_live.hpp"
#include "sd_read_write.hpp"
#include "ssd1306_display.hpp"
#include "webserver.hpp"

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
#define SCREEN_WIDTH 128  // OLED display width, in pixels
#define SCREEN_HEIGHT 64  // OLED display height, in pixels
#define OLED_RESET -1     // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Declaration for an RTC DS3231 object
RTC_DS3231 rtc;

// Declaration for a LatestReadings object, holds the latest readings
LatestReadings latest_readings;

// Declaration for a TimeDifference object, holds the time difference between
// the latest reading and the current time
TimeDifference timeDifference;

// String to hold the latest reading update, recieved through ESPNOW
String LATEST_READING_UPDATE;

// Callback function that will be executed when data is received
void onDataReceived(uint8_t *senderMac, uint8_t *incomingData, uint8_t len) {
  // Write the incoming data to the uint8_t array
  uint8_t recieved[len + 1];
  Serial.print("Received: ");
  for (int i = 0; i < len; i++) {
    Serial.print((char)incomingData[i]);
    recieved[i] = incomingData[i];
  }

  Serial.println();

  // Convert the uint8_t array to a String
  String recievedString = String((char *)recieved);
  // Write the latest reading to the SD card
  sdWriteLatestReading(getFilename(rtc), recievedString);
  // Clear the display
  ssd1306DisplayClear(display);
}

void setup() {
  Serial.begin(115200);

  // Peripherals setup
  ssd1306DisplaySetup(display);
  setupDS3231(rtc);
  sdReadSetup();

  // Clear the display
  ssd1306DisplayClear(display);

  // ESPNOW setup
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
  // Get the current day date and time
  String dayDate = getDayDate(rtc);
  String time = getTime(rtc);

  // Refreshes line 2 & line 8 only
  int x, y;
  for (y = 7; y <= 14; y++) {
    for (x = 0; x < 127; x++) {
      display.drawPixel(x, y, BLACK);
    }
  }
  for (y = 56; y <= 63; y++) {
    for (x = 0; x < 127; x++) {
      display.drawPixel(x, y, BLACK);
    }
  }

  // Get the time difference between the latest reading and the current time
  timeDifference =
      getTimeDifference(rtc, latest_readings.time, latest_readings.dayDate);

  // Display the live time and the time difference between now and the last
  // reading
  ssd1306DisplayLiveTime(display, dayDate, time, timeDifference.hours,
                         timeDifference.minutes, timeDifference.seconds);

  // Get todays filename
  String filename = getFilename(rtc);

  // Get the latest readings from the SD card, store into latest_readings struct
  sdReadGetLastLine(filename);
  sdReadGetLatestReadings(latest_readings);

  // Serial.println("Setup complete.");
  // Serial.println("Temperature: " + String(latest_readings.temperature));
  // Serial.println("Humidity: " + String(latest_readings.humidity));
  // Serial.println("Pressure: " + String(latest_readings.pressure));
  // Serial.println("Wind Speed: " + String(latest_readings.windSpeed));
  // Serial.println("Wind Direction: " + latest_readings.windDirection);
  // Serial.println("Battery Percentage: " +
  //                String(latest_readings.batteryPercentage));
  // Serial.println("Day Date: " + latest_readings.dayDate);
  // Serial.println("Time: " + latest_readings.time);
  // Serial.println("Time Difference: " + String(timeDifference.hours) +
  //                " hours " + String(timeDifference.minutes) + " minutes " +
  //                String(timeDifference.seconds) + " seconds");

  // Display the latest readings on the OLED display
  ssd1306DisplayReadings(
      display, latest_readings.temperature, latest_readings.humidity,
      latest_readings.pressure, latest_readings.windSpeed,
      latest_readings.windDirection, latest_readings.batteryPercentage);
}