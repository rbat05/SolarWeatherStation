#ifndef BME280_TEMP_HUMI_PRES_HPP
#define BME280_TEMP_HUMI_PRES_HPP
#include <Adafruit_BME280.h>  // Adafruit BME280 Library
#include <Adafruit_Sensor.h>  // Adafruit Unified Sensor
#include <Arduino.h>
#include <Wire.h>  // I2C communication

// Checks if the BME280 sensor is connected
void bme280_setup(Adafruit_BME280 &bme280);

// Returns readings from the BME280 sensor
float bme280_get_temperature(Adafruit_BME280 &bme280);
float bme280_get_humidity(Adafruit_BME280 &bme280);
float bme280_get_pressure(Adafruit_BME280 &bme280);

// Change sensor mode
void bme280_sleep_mode();
void bme280_forced_mode();

#endif