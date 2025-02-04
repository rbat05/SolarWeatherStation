#include "sd_read.hpp"

String LAST_LINE_WEATHER_DATA;
String LAST_LINE_DIAGNOSTICS;

void sd_read_setup() {
  // SD Card
  Serial.print("Initializing SD card...");

  if (!SD.begin(15)) {
    Serial.println("Initialization failed!");
    return;
  }
  Serial.println("Initialization done. SD on pin 8.");
}

// No other way to do this, library does not support reverse reading nor seek
// functions
void sd_read_get_last_line() {
  File myFile;
  myFile = SD.open("weather_data.csv", FILE_READ);
  if (myFile) {
    Serial.println("weather_data.csv last line: ");

    // read from the file until there's nothing else in it:
    LAST_LINE_WEATHER_DATA = "";
    while (myFile.available()) {
      String currentLine = myFile.readStringUntil('\n');
      if (currentLine.length() > 0) {
        LAST_LINE_WEATHER_DATA = currentLine;
      }
    }
    myFile.close();

    // Print the last line of the file
    Serial.print("Found last line in weather_data.csv: ");
    Serial.println(LAST_LINE_WEATHER_DATA);
  } else {
    // if the file didn't open, print an error:
    Serial.println("weather_data.csv failed to open.");
  }

  myFile = SD.open("diagnostics.csv", FILE_READ);
  if (myFile) {
    Serial.println("diagnostics.csv last line: ");

    // read from the file until there's nothing else in it:
    LAST_LINE_DIAGNOSTICS = "";
    while (myFile.available()) {
      String currentLine = myFile.readStringUntil('\n');
      if (currentLine.length() > 0) {
        LAST_LINE_DIAGNOSTICS = currentLine;
      }
    }
    myFile.close();

    // Print the last line of the file
    Serial.print("Found last line in diagnostics.csv: ");
    Serial.println(LAST_LINE_DIAGNOSTICS);
  } else {
    // if the file didn't open, print an error:
    Serial.println("diagnostics.csv failed to open.");
  }
}

LatestReadings sd_read_get_latest_readings(LatestReadings &latest_readings) {
  // Weather Data
  latest_readings.day_date = LAST_LINE_WEATHER_DATA.substring(
      0, LAST_LINE_WEATHER_DATA.indexOf('-') - 1);
  latest_readings.time =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf('-') + 2,
                                       LAST_LINE_WEATHER_DATA.indexOf(','));

  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.temperature =
      LAST_LINE_WEATHER_DATA.substring(0, LAST_LINE_WEATHER_DATA.indexOf(','))
          .toFloat();
  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.humidity =
      LAST_LINE_WEATHER_DATA.substring(0, LAST_LINE_WEATHER_DATA.indexOf(','))
          .toFloat();
  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.pressure =
      LAST_LINE_WEATHER_DATA.substring(0, LAST_LINE_WEATHER_DATA.indexOf(','))
          .toFloat();
  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.uv_index =
      LAST_LINE_WEATHER_DATA.substring(0, LAST_LINE_WEATHER_DATA.indexOf(','))
          .toInt();
  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.uv_index_str =
      LAST_LINE_WEATHER_DATA.substring(0, LAST_LINE_WEATHER_DATA.indexOf(','));
  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.wind_speed =
      LAST_LINE_WEATHER_DATA.substring(0, LAST_LINE_WEATHER_DATA.indexOf(','))
          .toFloat();
  LAST_LINE_WEATHER_DATA =
      LAST_LINE_WEATHER_DATA.substring(LAST_LINE_WEATHER_DATA.indexOf(',') + 1);

  latest_readings.wind_direction = LAST_LINE_WEATHER_DATA;

  // Diagnostics
  // Skip the first two values
  LAST_LINE_DIAGNOSTICS =
      LAST_LINE_DIAGNOSTICS.substring(LAST_LINE_DIAGNOSTICS.indexOf(',') + 1);
  LAST_LINE_DIAGNOSTICS =
      LAST_LINE_DIAGNOSTICS.substring(LAST_LINE_DIAGNOSTICS.indexOf(',') + 1);

  // Extract the battery percentage value
  latest_readings.battery_percentage =
      LAST_LINE_DIAGNOSTICS.substring(0, LAST_LINE_DIAGNOSTICS.indexOf(','))
          .toFloat();

  return latest_readings;
}

// gonna fucking kms why this shit so ugly