#include "bme280_temp_humi_pres.hpp"
#define SENSOR_ADDR 0x76

// Checks if the BME280 sensor is connected
// If connected, the program will continue
// If not, the program will be stuck in an infinite loop until the sensor is
// connected or ESP is reset
void bme280_setup(Adafruit_BME280 bme280) {
  bool status = bme280.begin(SENSOR_ADDR);

  if (status == true) {
    Serial.printf("BME280 sensor is connected @0x%X!\n", SENSOR_ADDR);
    return;
  } else {
    Serial.println("BME280 sensor is not connected, check wiring or reset.");
    while (1);
  }
}

// Returns the temperature in Celsius
int bme280_get_temperature(Adafruit_BME280 bme280) {
  return bme280.readTemperature();
}

// Returns the humidity in Percentage
int bme280_get_humidity(Adafruit_BME280 bme280) {
  return bme280.readHumidity();
}

// Returns the pressure in hPa
int bme280_get_pressure(Adafruit_BME280 bme280) {
  return bme280.readPressure();
}

// Changes the sensor mode to sleep mode
void bme280_sleep_mode() {
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write((uint8_t)0xF4);  // Selecting the control measurement register
  Wire.write((uint8_t)0b00000000);  // Setting the sensor mode to sleep mode
  Wire.endTransmission();
}

// Changes the sensor mode to normal mode
void bme280_normal_mode() {
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write((uint8_t)0xF4);  // Selecting the control measurement register
  Wire.write((uint8_t)0b00000011);  // Setting the sensor mode to normal mode
  Wire.endTransmission();
}