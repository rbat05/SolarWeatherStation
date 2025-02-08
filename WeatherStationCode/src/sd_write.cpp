#include "sd_write.hpp"

bool sdGetInfo() {
  // Check if the SD card is available
  // then, print out sd card info to serial
  int chipSelect = 5;
  pinMode(chipSelect, OUTPUT);

  // Check if the card is available
  if (SD.begin(chipSelect)) {
    Serial.println("SD card is available.");
  } else {
    Serial.println("SD card is not available.");
    return false;
  }

  // Print out card info
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