#include "sd_read_write.hpp"

bool sdGetInfo() {
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

  uint8_t cardType = SD.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("No SD card attached.");
    return false;
  }

  Serial.print("SD Card Type: ");
  if (cardType == CARD_MMC) {
    Serial.println("MMC");
  } else if (cardType == CARD_SD) {
    Serial.println("SDSC");
  } else if (cardType == CARD_SDHC) {
    Serial.println("SDHC");
  } else {
    Serial.println("UNKNOWN");
  }

  uint64_t cardSize = SD.cardSize() / (1024 * 1024);
  Serial.printf("SD Card Size: %lluMB\n", cardSize);
  Serial.println();
  Serial.printf("Total space: %lluMB\n", SD.totalBytes() / (1024 * 1024));
  Serial.printf("Used space: %lluMB\n", SD.usedBytes() / (1024 * 1024));
  return true;
}

// Write in .csv format, in file named "weather_data.csv"
// Line format: dateTime, temperature, humidity, pressure, windSpeed,
// windDirection
// void sdWriteWeatherData(WeatherData data) {
//   // Check if the SD card is available
//   // then, print out sd card info to serial
//   // then, open the file "weather_data.csv"
//   // then, create a formatted string out of struct
//   // then, write the formatted string to serial
//   // then, write the formatted string to the file on new line
//   // then, close the file
//   File myFile;

//   int chipSelect = 5;
//   pinMode(chipSelect, OUTPUT);

//   bool cardMounted = sdGetInfo();
//   if (cardMounted) {
//     Serial.println("Attempting to write to weather_data.csv, card mounted.");
//     myFile = SD.open("/weather_data.csv", FILE_APPEND);

//     if (myFile) {
//       String formattedData =
//           data.dateTime + "," + String(data.temperature) + "," +
//           String(data.humidity) + "," + String(data.pressure) + "," +
//           String(data.uvIndexInt) + "," + data.uvIndexStr + "," +
//           String(data.windSpeed) + "," + data.windDirection;
//       Serial.println("Writing following data to weather_data.csv:");
//       Serial.println(formattedData);
//       myFile.println(formattedData);
//       myFile.close();
//     } else {
//       Serial.println("Error writing to weather_data.csv, file failed to
//       open.");
//     }

//   } else {
//     Serial.println("Error writing to weather_data.csv, card failed to
//     mount.");
//   }
// }

// Write in .csv format, in file named "diagnostics.csv"
// Line format: dateTime, batteryVoltage, batteryPercentage, I2C address of
// BME280, I2C address of DS3231, analog reading of UV sensor, analog reading of
// hall effect sensors 1 - 5
// void sdWriteDiagnostics(Diagnostics data) {
//   // Check if the SD card is available
//   // then, print out sd card info to serial
//   // then, open the file "diagnostics.csv"
//   // then, create a formatted string out of struct
//   // then, write the formatted string to serial
//   // then, write the formatted string to the file on new line
//   // then, close the file
//   File myFile;

//   int chipSelect = 5;
//   pinMode(chipSelect, OUTPUT);

//   bool cardMounted = sdGetInfo();
//   if (cardMounted) {
//     Serial.println("Attempting to write to diagnostics.csv, card mounted.");
//     myFile = SD.open("/diagnostics.csv", FILE_APPEND);

//     if (myFile) {
//       String formattedData =
//           data.dateTime + "," + String(data.batteryVoltage) + "," +
//           String(data.batteryPercentage) + ",0x" +
//           String(data.bme280Address, HEX) + ",0x" +
//           String(data.ds3231Address, HEX) + "," +
//           String(data.uvSensorReading) +
//           "," + String(data.north49eReading) + "," +
//           String(data.south49eReading) + "," + String(data.east49eReading) +
//           "," + String(data.west49eReading) + "," +
//           String(data.tach49eReading);
//       Serial.println("Writing following data to diagnostics.csv:");
//       Serial.println(formattedData);
//       myFile.println(formattedData);
//       myFile.close();
//     } else {
//       Serial.println("Error writing to diagnostics.csv, file failed to
//       open.");
//     }

//   } else {
//     Serial.println("Error writing to diagnostics.csv, card failed to
//     mount.");
//   }
// }

String sdWriteReadings(Readings data, String filename) {
  // Check if the SD card is available
  // then, print out sd card info to serial
  // then, open/create the file with todays date
  // then, create a formatted string out of struct
  // then, write the formatted string to serial
  // then, write the formatted string to the file on new line
  // then, close the file
  File myFile;

  int chipSelect = 5;
  pinMode(chipSelect, OUTPUT);

  bool cardMounted = sdGetInfo();
  if (cardMounted) {
    Serial.println("Attempting to write to " + filename + ", card mounted.");
    myFile = SD.open("/" + filename, FILE_APPEND);
    // If file is empty, write the header which is
    // DATE/TIME, TEMPERATURE, HUMIDITY, PRESSURE, WIND SPEED, WIND DIRECTION,
    // BATTERY VOLTAGE, BATTERY PERCENTAGE

    if (myFile) {
      if (myFile.size() == 0) {
        Serial.println("Writing header to " + filename + ":");
        myFile.println(
            "DATE/TIME, TEMPERATURE, HUMIDITY, PRESSURE, WIND SPEED, "
            "WIND DIRECTION, BATTERY VOLTAGE, BATTERY PERCENTAGE");
      }
      String formattedData =
          data.dateTime + "," + String(data.temperature) + "," +
          String(data.humidity) + "," + String(data.pressure) + "," +
          String(data.windSpeed) + "," + data.windDirection + "," +
          String(data.batteryVoltage) + "," + String(data.batteryPercentage);
      Serial.println("Writing following data to " + filename + ":");
      Serial.println(formattedData);
      myFile.println(formattedData);
      return formattedData;
      myFile.close();
    } else {
      Serial.println("Error writing to " + filename + ", file failed to open.");
      return "Aaa 01/01/2020 - 00:00:00,0.00,0.00,0.00,-1.00,NA,0.00,0.00";
    }

  } else {
    Serial.println("Error writing to " + filename + ", card failed to mount.");
    return "Aaa 01/01/2020 - 00:00:00,0.00,0.00,0.00,-1.00,NA,0.00,0.00";
  }
}