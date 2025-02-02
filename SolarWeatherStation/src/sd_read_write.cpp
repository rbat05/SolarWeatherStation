#include "sd_read_write.hpp"

bool sd_get_info() {
  // Check if the SD card is available
  // then, print out sd card info to serial
  int chipSelect = 5;
  pinMode(chipSelect, OUTPUT);

  if (SD.begin(chipSelect)) {
    Serial.println("SD card is available.");
  } else {
    Serial.println("SD card is not available.");
    return false;
  }

  uint8_t card_type = SD.cardType();
  if (card_type == CARD_NONE) {
    Serial.println("No SD card attached.");
    return false;
  }

  Serial.print("SD Card Type: ");
  if (card_type == CARD_MMC) {
    Serial.println("MMC");
  } else if (card_type == CARD_SD) {
    Serial.println("SDSC");
  } else if (card_type == CARD_SDHC) {
    Serial.println("SDHC");
  } else {
    Serial.println("UNKNOWN");
  }

  uint64_t card_size = SD.cardSize() / (1024 * 1024);
  Serial.printf("SD Card Size: %lluMB\n", card_size);
  Serial.println();
  Serial.printf("Total space: %lluMB\n", SD.totalBytes() / (1024 * 1024));
  Serial.printf("Used space: %lluMB\n", SD.usedBytes() / (1024 * 1024));
  return true;
}

// Write in .csv format, in file named "weather_data.csv"
// Line format: date_time, temperature, humidity, pressure, uv_index_int,
// uv_index_str, wind_speed, wind_direction
void sd_write_weather_data(WeatherData data) {
  // Check if the SD card is available
  // then, print out sd card info to serial
  // then, open the file "weather_data.csv"
  // then, create a formatted string out of struct
  // then, write the formatted string to serial
  // then, write the formatted string to the file on new line
  // then, close the file
  File myfile;

  int chipSelect = 5;
  pinMode(chipSelect, OUTPUT);

  bool card_mounted = sd_get_info();
  if (card_mounted) {
    Serial.println("Attempting to write to weather_data.csv, card mounted.");
    myfile = SD.open("/weather_data.csv", FILE_APPEND);

    if (myfile) {
      String formatted_data =
          data.date_time + "," + String(data.temperature) + "," +
          String(data.humidity) + "," + String(data.pressure) + "," +
          String(data.uv_index_int) + "," + data.uv_index_str + "," +
          String(data.wind_speed) + "," + data.wind_direction;
      Serial.println("Writing following data to weather_data.csv:");
      Serial.println(formatted_data);
      myfile.println(formatted_data);
      myfile.close();
    } else {
      Serial.println("Error writing to weather_data.csv, file failed to open.");
    }

  } else {
    Serial.println("Error writing to weather_data.csv, card failed to mount.");
  }
}

// Write in .csv format, in file named "diagnostics.csv"
// Line format: date_time, battery_voltage, battery_percentage, I2C address of
// BME280, I2C address of DS3231, analog reading of UV sensor, analog reading of
// hall effect sensors 1 - 5
void sd_write_diagnostics(Diagnostics data) {
  // Check if the SD card is available
  // then, print out sd card info to serial
  // then, open the file "diagnostics.csv"
  // then, create a formatted string out of struct
  // then, write the formatted string to serial
  // then, write the formatted string to the file on new line
  // then, close the file
  File myfile;

  int chipSelect = 5;
  pinMode(chipSelect, OUTPUT);

  bool card_mounted = sd_get_info();
  if (card_mounted) {
    Serial.println("Attempting to write to diagnostics.csv, card mounted.");
    myfile = SD.open("/diagnostics.csv", FILE_APPEND);

    if (myfile) {
      String formatted_data =
          data.date_time + "," + String(data.battery_voltage) + "," +
          String(data.battery_percentage) + ",0x" +
          String(data.bme280_address, HEX) + ",0x" +
          String(data.ds3231_address, HEX) + "," +
          String(data.uv_sensor_reading) + "," +
          String(data.north_49e_reading) + "," +
          String(data.south_49e_reading) + "," + String(data.east_49e_reading) +
          "," + String(data.west_49e_reading) + "," +
          String(data.tach_49e_reading);
      Serial.println("Writing following data to diagnostics.csv:");
      Serial.println(formatted_data);
      myfile.println(formatted_data);
      myfile.close();
    } else {
      Serial.println("Error writing to diagnostics.csv, file failed to open.");
    }

  } else {
    Serial.println("Error writing to diagnostics.csv, card failed to mount.");
  }
}