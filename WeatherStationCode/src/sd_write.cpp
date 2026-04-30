#include "sd_write.hpp"

// Store up to 10 readings of max 128 characters each in deep sleep memory
RTC_DATA_ATTR char savedReadings[10][128];
RTC_DATA_ATTR int savedReadingsCount = 0;

bool sdGetInfo() {
  // Check if the SD card is available
  // then, print out sd card info to serial
  int chipSelect = 12;
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
  int chipSelect = 12;
  pinMode(chipSelect, OUTPUT);

  // Always format the data so we can at least send it via ESP-NOW if the SD
  // fails
  String formattedData =
      data.dateTime + "," + String(data.temperature) + "," +
      String(data.humidity) + "," + String(data.pressure) + "," +
      String(data.windSpeed) + "," + data.windDirection + "," +
      String(data.batteryVoltage) + "," + String(data.batteryPercentage);

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

      // Write any backlogged readings stored in memory first
      if (savedReadingsCount > 0) {
        Serial.printf("Writing %d saved backlogged readings...\n",
                      savedReadingsCount);
        for (int i = 0; i < savedReadingsCount; i++) {
          myFile.println(String(savedReadings[i]));
        }
        savedReadingsCount = 0;  // Reset counter
      }

      Serial.println("Writing following data to " + filename + ":");
      Serial.println(formattedData);
      myFile.println(formattedData);
      myFile.close();
      return formattedData;
    } else {
      Serial.println("Error writing to " + filename + ", file failed to open.");
    }

  } else {
    Serial.println("Error writing to " + filename + ", card failed to mount.");
  }

  // Fallback: If SD failed, store reading in RTC memory to survive Deep Sleep
  Serial.println("Storing reading in RTC memory for next boot.");
  if (savedReadingsCount < 10) {
    strncpy(savedReadings[savedReadingsCount], formattedData.c_str(), 127);
    savedReadings[savedReadingsCount][127] = '\0';  // Ensure null-termination
    savedReadingsCount++;
  } else {
    // Buffer is full: shift old readings out to make room for newest one
    for (int i = 1; i < 10; i++) {
      strncpy(savedReadings[i - 1], savedReadings[i], 128);
    }
    strncpy(savedReadings[9], formattedData.c_str(), 127);
    savedReadings[9][127] = '\0';
  }

  return formattedData;
}