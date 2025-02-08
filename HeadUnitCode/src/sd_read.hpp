#ifndef SD_READ_HPP
#define SD_READ_HPP

#include <SD.h>
#include <SPI.h>
#include <Wire.h>

#define SD_CS_PIN 8

struct LatestReadings {
  String dayDate;
  String time;
  float temperature;
  float humidity;
  float pressure;
  float windSpeed;
  String windDirection;
  float batteryPercentage;
};

void sdReadSetup();
void sdReadGetLastLine(String filename);
LatestReadings sdReadGetLatestReadings(LatestReadings &latest_readings);
void sdWriteLatestReading(String filename, String data);

#endif