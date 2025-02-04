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

void setup() {
  Serial.begin(115200);

  // SSD1306 Display
  ssd1306DisplaySetup(display);

  setupDS3231(rtc);

  sdReadSetup();
  sdReadGetLastLine();
  sdReadGetLatestReadings(latest_readings);

  Serial.println("Setup complete.");
  // Serial.println("Temperature: " + String(latest_readings.temperature));
  // Serial.println("Humidity: " + String(latest_readings.humidity));
  // Serial.println("Pressure: " + String(latest_readings.pressure));
  // Serial.println("UV Index: " + String(latest_readings.uvIndex));
  // Serial.println("UV Index Str: " + latest_readings.uvIndexStr);
  // Serial.println("Wind Speed: " + String(latest_readings.windSpeed));
  // Serial.println("Wind Direction: " + latest_readings.windDirection);
  // Serial.println("Battery Percentage: " +
  //                String(latest_readings.batteryPercentage));
  // Serial.println("Day Date: " + latest_readings.dayDate);
  // Serial.println("Time: " + latest_readings.time);
}

void loop() {
  // Display live time and latest weather data for 5 seconds
  ssd1306DisplayClear(display);

  for (int i = 0; i < 10; i++) {
    // ssd1306DisplayClear(display);
    String dayDate = getDayDate(rtc);
    String time = getTime(rtc);

    // Refreshes the time section of the display only (ie line 2)
    int x, y;
    for (y = 7; y <= 14; y++) {
      for (x = 0; x < 127; x++) {
        display.drawPixel(x, y, BLACK);
      }
    }

    ssd1306DisplayLiveTime(display, dayDate, time);
    ssd1306DisplayWeatherData(
        display, latest_readings.temperature, latest_readings.humidity,
        latest_readings.pressure, latest_readings.uvIndex,
        latest_readings.uvIndexStr, latest_readings.windSpeed,
        latest_readings.windDirection);
    delay(1000);
  }

  // Display diagnostic information for 3 seconds and then reset
  ssd1306DisplayDiagnostic(display, latest_readings.batteryPercentage,
                           latest_readings.dayDate, latest_readings.time);
  delay(3000);
}

// Saturday 01/02/2025 - 13:04:19,26.90,49.20,1015.14,0,OFF,15.00,NORTH