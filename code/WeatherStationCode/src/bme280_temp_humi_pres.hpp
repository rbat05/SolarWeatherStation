#ifndef BME280_TEMP_HUMI_PRES_HPP
#define BME280_TEMP_HUMI_PRES_HPP
#include <Adafruit_BME280.h>  // Adafruit BME280 Library
#include <Adafruit_Sensor.h>  // Adafruit Unified Sensor
#include <Arduino.h>
#include <Wire.h>  // I2C communication

// Checks if the BME280 sensor is connected
void bme280Setup(Adafruit_BME280 &bme280);

// Returns readings from the BME280 sensor
float bme280GetTemperature(Adafruit_BME280 &bme280);
float bme280GetHumidity(Adafruit_BME280 &bme280);
float bme280GetPressure(Adafruit_BME280 &bme280);

// Change sensor mode
void bme280SleepMode();
void bme280ForcedMode();

#endif