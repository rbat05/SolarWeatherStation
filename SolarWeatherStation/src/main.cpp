#include <Arduino.h>  // Built-in library
#include <Wire.h>
#include <string.h>

#include <iostream>  // Built-in library

#include "49e_wind_speed_dir.hpp"
#include "bme280_temp_humi_pres.hpp"
#include "ds3231_rtc.hpp"
#include "s12sd_uv.hpp"
#include "sd_read_write.hpp"
#include "utilities.hpp"

// BME280 - Connected via I2C, G22 = SCL, G21 = SDA
Adafruit_BME280 bme280;

// S12SD - Connected via Analog, G36 = UV
const int UV_PIN = 36;

// DS3231 - Connected via I2C, G22 = SCL, G21 = SDA
RTC_DS3231 rtc;

// Battery Pin - Connected via Analog, G25 = Battery
const int BATTERY_PIN = 25;

// 49E - Connected via Analog, G39 = North, G34 = South, G35 = East, G32 = West
// WIND DIRECTION
const int PIN_49E_NORTH = 39;
const int PIN_49E_SOUTH = 34;
const int PIN_49E_EAST = 35;
const int PIN_49E_WEST = 32;

// 49E - Connected via Analog, G33 = Tachometer
// WIND SPEED
const int PIN_49E_TACH = 33;

void setup() {
  Serial.begin(115200);
  WeatherData data1;
  Diagnostics data2;

  delay(1000);

  data1.temperature = 25.0;
  data1.humidity = 50.0;
  data1.pressure = 1013.25;
  data1.wind_speed = 10.0;
  data1.wind_direction = "NW";
  data1.uv_index = 8;
  data1.date_time = "Tonday 18/01/2025 - 17:10:45";

  data2.bme280_address = 0x76;
  data2.ds3231_address = 0x68;
  data2.uv_sensor_reading = 1.124;
  data2.north_49e_reading = 1750.45;
  data2.south_49e_reading = 1750.65;
  data2.east_49e_reading = 1254.67;
  data2.west_49e_reading = 1255.55;
  data2.tach_49e_reading = 10;
  data2.battery_voltage = 3.7;
  data2.battery_percentage = 50.0;
  data2.date_time = "Tonday 18/01/2025 - 17:10:45";

  sd_write_weather_data(data1);
  sd_write_diagnostics(data2);
}

void loop() {}
