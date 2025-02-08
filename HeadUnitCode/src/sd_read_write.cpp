#include "sd_read_write.hpp"

String LAST_LINE_READINGS;

// Setup SD card
void sdReadSetup() {
  Serial.print("Initializing SD card...");
  // DO NOT CHANGE 15->8, BREAKS FOR NO REASON
  if (!SD.begin(15)) {
    Serial.println("Initialization failed!");
    return;
  }
  Serial.println("Initialization done. SD on pin 8.");
}

// Get last line of the file, max length of file is 289 lines (60s * 60m * 24h /
// updated every 300s) + header
void sdReadGetLastLine(String filename) {
  File myFile;
  myFile = SD.open(filename, FILE_READ);
  if (myFile) {
    Serial.println(filename + " last line: ");

    // Read from the file until there's nothing else in it:
    LAST_LINE_READINGS = "";
    while (myFile.available()) {
      String currentLine = myFile.readStringUntil('\n');
      if (currentLine.length() > 0) {
        LAST_LINE_READINGS = currentLine;
      }
    }
    myFile.close();

    // Print the last line of the file
    Serial.print("Found last line in " + filename + ": ");
    Serial.println(LAST_LINE_READINGS);
  } else {
    // if the file didn't open, print an error:
    Serial.println(filename + " failed to open.");
  }
}

// Extract the latest readings from the last line of the file into a struct
// variables
LatestReadings sdReadGetLatestReadings(LatestReadings &latest_readings) {
  latest_readings.dayDate =
      LAST_LINE_READINGS.substring(0, LAST_LINE_READINGS.indexOf('-') - 1);
  latest_readings.time = LAST_LINE_READINGS.substring(
      LAST_LINE_READINGS.indexOf('-') + 2, LAST_LINE_READINGS.indexOf(','));

  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);

  latest_readings.temperature =
      LAST_LINE_READINGS.substring(0, LAST_LINE_READINGS.indexOf(','))
          .toFloat();
  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);

  latest_readings.humidity =
      LAST_LINE_READINGS.substring(0, LAST_LINE_READINGS.indexOf(','))
          .toFloat();
  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);

  latest_readings.pressure =
      LAST_LINE_READINGS.substring(0, LAST_LINE_READINGS.indexOf(','))
          .toFloat();
  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);

  latest_readings.windSpeed =
      LAST_LINE_READINGS.substring(0, LAST_LINE_READINGS.indexOf(','))
          .toFloat();
  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);

  latest_readings.windDirection =
      LAST_LINE_READINGS.substring(0, LAST_LINE_READINGS.indexOf(','));
  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);

  LAST_LINE_READINGS =
      LAST_LINE_READINGS.substring(LAST_LINE_READINGS.indexOf(',') + 1);
  latest_readings.batteryPercentage = LAST_LINE_READINGS.toFloat();

  return latest_readings;
}

// Write the latest readings to the file, recieves through ESPNOW
void sdWriteLatestReading(String filename, String data) {
  File myFile;
  myFile = SD.open(filename, FILE_WRITE);
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
    Serial.println("Writing following data to " + filename + ":");
    Serial.println(data);
    myFile.println(data);
    myFile.close();
  } else {
    Serial.println("Error writing to " + filename + ", file failed to open.");
  }
}
