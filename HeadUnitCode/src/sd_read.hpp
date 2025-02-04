#ifndef SD_READ_HPP
#define SD_READ_HPP

#include <SD.h>
#include <SPI.h>
#include <Wire.h>

#define SD_CS_PIN 8

struct LatestReadings {
  String day_date;
  String time;
  float temperature;
  float humidity;
  float pressure;
  int uv_index;
  String uv_index_str;
  float wind_speed;
  String wind_direction;
  float battery_percentage;
};

void sd_read_setup();
void sd_read_get_last_line();
LatestReadings sd_read_get_latest_readings(LatestReadings &latest_readings);

#endif