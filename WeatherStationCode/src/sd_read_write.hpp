#ifndef SD_READ_WRITE_HPP
#define SD_READ_WRITE_HPP
#include <Arduino.h>
#include <SD.h>
#include <SPI.h>

// Weather Data
struct WeatherData {
  float temperature;
  float humidity;
  float pressure;
  float windSpeed;
  String windDirection;
  int uvIndexInt;
  String uvIndexStr;
  String dateTime;
};

// Diagnostics Data
struct Diagnostics {
  uint8_t bme280Address;
  uint8_t ds3231Address;
  float uvSensorReading;
  float north49eReading;
  float south49eReading;
  float east49eReading;
  float west49eReading;
  float tach49eReading;
  float batteryVoltage;
  float batteryPercentage;
  String dateTime;
};

bool sdGetInfo();
void sdWriteWeatherData(WeatherData data);
void sdWriteDiagnostics(Diagnostics data);

#endif