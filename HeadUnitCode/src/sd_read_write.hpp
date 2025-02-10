#ifndef SD_READ_WRITE_HPP
#define SD_READ_WRITE_HPP

#include <FS.h>
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
void sdUpdateWebpage(LatestReadings &latest_readings, String filename);

String trimLineForMetric(String line, String metric);
String getTimestampForMetric(String line);

// Pass the metric as a string, e.g. "temperature", "humidity", "pressure"
// Returns the daily high, low, and average for the metric
String getDailyHigh(String filename, String metric);
String getDailyLow(String filename, String metric);
String getDailyAverage(String filename, String metric);

// Need to pass in date range
String getWeeklyHigh(String metric);
String getWeeklyLow(String metric);
String getWeeklyAverage(String metric);

String getMonthlyHigh(String metric);
String getMonthlyLow(String metric);
String getMonthlyAverage(String metric);

#endif