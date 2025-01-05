#include <Arduino.h>  // Built-in library

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

void setup() {
  Serial.begin(115200);
  Serial.println("Hello World");
}

void loop() {}
