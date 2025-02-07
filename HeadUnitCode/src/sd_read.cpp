#include "sd_read.hpp"

// String LAST_LINE_READINGS;
// String LAST_LINE_DIAGNOSTICS;
String LAST_LINE_READINGS;

void sdReadSetup() {
  // SD Card
  Serial.print("Initializing SD card...");
  // DO NOT CHANGE 15->8, BREAKS FOR NO REASON
  if (!SD.begin(15)) {
    Serial.println("Initialization failed!");
    return;
  }
  Serial.println("Initialization done. SD on pin 8.");
}

// No other way to do this, library does not support reverse reading nor seek
// functions
void sdReadGetLastLine(String filename) {
  File myFile;
  myFile = SD.open(filename, FILE_READ);
  if (myFile) {
    Serial.println(filename + " last line: ");

    // read from the file until there's nothing else in it:
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

LatestReadings sdReadGetLatestReadings(LatestReadings &latest_readings) {
  // Weather Data
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

// gonna fucking kms why this shit so ugly