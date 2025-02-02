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
  float wind_speed;
  String wind_direction;
  int uv_index_int;
  String uv_index_str;
  String date_time;
};

// Diagnostics Data
struct Diagnostics {
  uint8_t bme280_address;
  uint8_t ds3231_address;
  float uv_sensor_reading;
  float north_49e_reading;
  float south_49e_reading;
  float east_49e_reading;
  float west_49e_reading;
  float tach_49e_reading;
  float battery_voltage;
  float battery_percentage;
  String date_time;
};

bool sd_get_info();
void sd_write_weather_data(WeatherData data);
void sd_write_diagnostics(Diagnostics data);

#endif