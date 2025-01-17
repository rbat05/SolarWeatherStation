#ifndef SD_READ_WRITE_HPP
#define SD_READ_WRITE_HPP
#include <Arduino.h>
struct WeatherData {
  float temperature;
  float humidity;
  float pressure;
  float wind_speed;
  float wind_direction;
  float uv_index;
  float battery_voltage;
  float battery_percentage;
  String date_time;
};

void sd_write(WeatherData data);

#endif