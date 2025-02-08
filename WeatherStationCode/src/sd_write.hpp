#ifndef SD_WRITE_HPP
#define SD_WRITE_HPP
#include <Arduino.h>
#include <SD.h>
#include <SPI.h>

// Struct to hold readings
struct Readings {
  String dateTime;
  float temperature;
  float humidity;
  float pressure;
  float windSpeed;
  String windDirection;
  float batteryVoltage;
  float batteryPercentage;
};

// Get SD card info
bool sdGetInfo();

// Write readings to SD card, each reading on a new line, each day in a new file
String sdWriteReadings(Readings data, String filename);

#endif