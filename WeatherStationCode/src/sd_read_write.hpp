#ifndef SD_READ_WRITE_HPP
#define SD_READ_WRITE_HPP
#include <Arduino.h>
#include <SD.h>
#include <SPI.h>

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

bool sdGetInfo();
String sdWriteReadings(Readings data, String filename);

#endif