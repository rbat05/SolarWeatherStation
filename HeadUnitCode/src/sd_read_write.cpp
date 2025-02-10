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
    // Serial.println(filename + " last line: ");

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
    // Serial.print("Found last line in " + filename + ": ");
    // Serial.println(LAST_LINE_READINGS);
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
    Serial.println("Write successful.");
  } else {
    Serial.println("Error writing to " + filename + ", file failed to open.");
  }
}

void sdUpdateWebpage(LatestReadings &latest_readings, String filename) {
  File myFile;
  SD.remove("index.html");
  myFile = SD.open("index.html", FILE_WRITE);
  if (myFile) {
    myFile.println("<!DOCTYPE html>");
    myFile.println("<html>");
    myFile.println("<head>");
    myFile.println("<title>ESP8266 Web Server</title>");
    myFile.println(
        "<meta name=\"viewport\" content=\"width=device-width, "
        "initial-scale=1\">");
    myFile.println(
        "<meta http-equiv=\"refresh\" content=\"200\">");  // Refresh every 200s
    myFile.println("<style>");
    myFile.println(
        "body { font-family: Arial, sans-serif; text-align: center; }");
    myFile.println("h1 { font-size: 2rem; }");
    myFile.println(".reading { font-size: 1.5rem; }");
    myFile.println(
        "table { width: 80%; margin: 20px auto; border-collapse: collapse; }");
    myFile.println(
        "th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }");
    myFile.println("th { background-color: #f2f2f2; }");
    myFile.println("</style>");
    myFile.println("</head>");
    myFile.println("<body>");
    myFile.println("<h1>Weather Station Live Readings</h1>");
    myFile.println(
        "<div class=\"reading\">Temperature: <span id=\"temperature\">" +
        String(latest_readings.temperature, 2) + "</span> &deg;C</div>");
    myFile.println("<div class=\"reading\">Humidity: <span id=\"humidity\">" +
                   String(latest_readings.humidity, 2) + "</span> %</div>");
    myFile.println("<div class=\"reading\">Pressure: <span id=\"pressure\">" +
                   String(latest_readings.pressure, 2) + "</span> hPa</div>");
    myFile.println(
        "<div class=\"reading\">Wind Speed: <span id=\"windSpeed\">" +
        String(latest_readings.windSpeed, 2) + "</span> km/h</div>");
    myFile.println(
        "<div class=\"reading\">Wind Direction: <span id=\"windDirection\">" +
        latest_readings.windDirection + "</span></div>");
    myFile.println(
        "<div class=\"reading\">Battery Percentage: <span "
        "id=\"batteryPercentage\">" +
        String(latest_readings.batteryPercentage, 2) + "</span> %</div>");
    myFile.println(
        "<div class=\"reading\">Last Update: <span id=\"lastUpdate\">" +
        latest_readings.dayDate + " " + latest_readings.time + "</span></div>");

    myFile.println("<br><br>");

    // Stats section with table
    myFile.println("<section class=\"dailyStats\">");
    myFile.println("<h2>Daily Statistics</h2>");
    myFile.println("<table>");
    myFile.println(
        "<tr><th>Metric</th><th>High</th><th>Low</th><th>Average</th></tr>");
    myFile.println(
        "<tr><td>Temperature (&deg;C)</td><td id=\"dailyHighTemp\">" +
        getDailyHigh(filename, "temperature") +
        "</td><td id=\"dailyLowTemp\">" + getDailyLow(filename, "temperature") +
        "</td><td id=\"dailyAvgTemp\">" +
        getDailyAverage(filename, "temperature") + "</td></tr>");
    myFile.println("<tr><td>Humidity (%)</td><td id=\"dailyHighHumidity\">" +
                   getDailyHigh(filename, "humidity") +
                   "</td><td id=\"dailyLowHumidity\">" +
                   getDailyLow(filename, "humidity") +
                   "</td><td id=\"dailyAvgHumidity\">" +
                   getDailyAverage(filename, "humidity") + "</td></tr>");
    myFile.println("<tr><td>Pressure (hPa)</td><td id=\"dailyHighPressure\">" +
                   getDailyHigh(filename, "pressure") +
                   "</td><td id=\"dailyLowPressure\">" +
                   getDailyLow(filename, "pressure") +
                   "</td><td id=\"dailyAvgPressure\">" +
                   getDailyAverage(filename, "pressure") + "</td></tr>");
    myFile.println("</table>");
    myFile.println("</section>");

    myFile.println("</body>");
    myFile.println("</html>");
    myFile.close();
    Serial.println("HTML file updated successfully.");
  } else {
    Serial.println("Error writing to index.html, file failed to open.");
  }
}

// Line format:
// DAY DD/MM/YYYY - hh:mm:ss,TEMP,HUMI,PRES,WIND SPEED,WIND DIRECTION,BATT
// Mon 10/02/2025 - 13:38:57,30.46,37.74,1012.07,-1.00,NA,4.13,98.00

// Returns either TEMP, HUMI, or PRES from above line format
String trimLineForMetric(String line, String metric) {
  if (metric == "temperature") {
    return line.substring(line.indexOf(',') + 1,
                          line.indexOf(',', line.indexOf(',') + 5));
  } else if (metric == "humidity") {
    line = line.substring(line.indexOf(',') + 1);
    return line.substring(line.indexOf(',') + 1,
                          line.indexOf(',', line.indexOf(',') + 5));
  } else if (metric == "pressure") {
    line = line.substring(line.indexOf(',') + 1);
    line = line.substring(line.indexOf(',') + 1);
    return line.substring(line.indexOf(',') + 1,
                          line.indexOf(',', line.indexOf(',') + 5));
  } else {
    return "Invalid metric";
  }
}

// Returns Day Date and Time from above line format
String getTimestampForMetric(String line) {
  return line.substring(0, line.indexOf(','));
}

String getDailyHigh(String filename, String metric) {
  File myFile;
  myFile = SD.open(filename, FILE_READ);

  if (!myFile) {
    Serial.println("Error: Failed to open file '" + filename +
                   "' for reading.");
    return "Error: File open failed";
  }

  // If metric = temperature, get value after first comma
  // If metric = humidity, get value after second comma
  // If metric = pressure, get value after third comma
  // For a found high, store the return in a "Value @ Time" format
  String significantLine = "";
  float highValue = -1000.0;
  int lineCount = 0;

  myFile.readStringUntil('\n');  // Skip header

  while (myFile.available()) {
    String currentLine = myFile.readStringUntil('\n');
    if (currentLine.length() > 0 && currentLine.substring(0, 1) != "A") {
      lineCount++;
      float currentMetric = trimLineForMetric(currentLine, metric).toFloat();
      if (currentMetric > highValue) {
        highValue = currentMetric;
        significantLine = currentLine;
      }
    }
  }
  myFile.close();

  if (lineCount == 0) {
    Serial.println("Error: No data found in file '" + filename + "'.");
    return "No data";
  }

  return String(highValue) + " @ " + getTimestampForMetric(significantLine);
}

String getDailyLow(String filename, String metric) {
  File myFile;
  myFile = SD.open(filename, FILE_READ);

  if (!myFile) {
    Serial.println("Error: Failed to open file '" + filename +
                   "' for reading.");
    return "Error: File open failed";
  }
  // If metric = temperature, get value after first comma
  // If metric = humidity, get value after second comma
  // If metric = pressure, get value after third comma
  // For a found low, store the return in a "Value @ Time" format
  String significantLine = "";
  float lowValue = 9999.0;
  int lineCount = 0;

  myFile.readStringUntil('\n');  // Skip header

  while (myFile.available()) {
    String currentLine = myFile.readStringUntil('\n');
    if (currentLine.length() > 0 && currentLine.substring(0, 1) != "A") {
      lineCount++;
      float currentMetric = trimLineForMetric(currentLine, metric).toFloat();
      if (currentMetric < lowValue) {
        lowValue = currentMetric;
        significantLine = currentLine;
      }
    }
  }
  myFile.close();

  if (lineCount == 0) {
    Serial.println("Error: No data found in file '" + filename + "'.");
    return "No data";
  }

  return String(lowValue) + " @ " + getTimestampForMetric(significantLine);
}

String getDailyAverage(String filename, String metric) {
  File myFile;
  myFile = SD.open(filename, FILE_READ);

  if (!myFile) {
    Serial.println("Error: Failed to open file '" + filename +
                   "' for reading.");
    return "Error: File open failed";
  }

  // If metric = temperature, get value after first comma
  // If metric = humidity, get value after second comma
  // If metric = pressure, get value after third comma
  float rollingSum = 0.0;
  int lineCount = 0;

  myFile.readStringUntil('\n');  // Skip header

  while (myFile.available()) {
    String currentLine = myFile.readStringUntil('\n');
    if (currentLine.length() > 0 && currentLine.substring(0, 1) != "A") {
      float currentMetric = trimLineForMetric(currentLine, metric).toFloat();
      rollingSum += currentMetric;
      lineCount++;
    }
  }
  myFile.close();

  if (lineCount == 0) {
    Serial.println("Error: No data found in file '" + filename + "'.");
    return "No data";
  }

  return String(rollingSum / lineCount);
}
