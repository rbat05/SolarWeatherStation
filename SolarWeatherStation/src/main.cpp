#include <Arduino.h>  // Built-in library
#include <Wire.h>
#include <string.h>

#include <iostream>  // Built-in library

#include "49e_wind_speed_dir.hpp"
#include "bme280_temp_humi_pres.hpp"
#include "ds3231_rtc.hpp"
#include "s12sd_uv.hpp"
#include "sd_read_write.hpp"

// BME280 - Connected via I2C, G22 = SCL, G21 = SDA
Adafruit_BME280 bme280;

// S12SD - Connected via Analog, G36 = UV
const int UV_PIN = 36;

// DS3231 - Connected via I2C, G22 = SCL, G21 = SDA
RTC_DS3231 rtc;

// Battery Pin - Connected via Analog, G25 = Battery
const int BATTERY_PIN = 25;

void setup() { Serial.begin(115200); }

void loop() {
  // int uv_index_value = get_uv_index_value(UV_PIN);
  // std::string uv_index = get_uv_index(uv_index_value);
  // Serial.print("UV Index: ");
  // Serial.print(uv_index.c_str());
  // Serial.print(" (");
  // Serial.print(uv_index_value);
  // Serial.print(")");

  // Serial.print("Analog Read: ");
  // Serial.println(analogRead(UV_PIN));
  delay(1000);
}
