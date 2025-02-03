#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <SD.h>
#include <SPI.h>
#include <Wire.h>

#include <iostream>

#include "RTClib.h"

#define SCREEN_WIDTH 128  // OLED display width, in pixels
#define SCREEN_HEIGHT 64  // OLED display height, in pixels
#define SSD1306_I2C_ADDRESS 0x3C

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
#define OLED_RESET -1  // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

RTC_DS3231 rtc;

char daysOfTheWeek[7][12] = {"Sunday",   "Monday", "Tuesday", "Wednesday",
                             "Thursday", "Friday", "Saturday"};

String get_day_date(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char day_date[33];
  sprintf(day_date, "%s %02d/%02d/%04d", daysOfTheWeek[now.dayOfTheWeek()],
          now.day(), now.month(), now.year());

  return String(day_date);
}

String get_time(RTC_DS3231 &rtc) {
  DateTime now = rtc.now();

  char time[15];
  sprintf(time, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(time);
}

String LAST_LINE;
float temperature;
float humidity;
float pressure;
int uv_index;
String uv_index_str;
float wind_speed;
String wind_direction;

void setup() {
  Serial.begin(115200);

  if (!display.begin(SSD1306_SWITCHCAPVCC,
                     SSD1306_I2C_ADDRESS)) {  // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for (;;);
  }

  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }

  // SD Card
  Serial.print("Initializing SD card...");

  if (!SD.begin(15)) {
    Serial.println("initialization failed!");
    return;
  }
  Serial.println("initialization done.");

  // open the file. note that only one file can be open at a time,
  // so you have to close this one before opening another.
  File myFile;
  myFile = SD.open("weather_data.csv", FILE_READ);
  if (myFile) {
    Serial.println("weather_data.csv last line: ");

    // read from the file until there's nothing else in it:
    LAST_LINE = "";
    while (myFile.available()) {
      String currentLine = myFile.readStringUntil('\n');
      if (currentLine.length() > 0) {
        LAST_LINE = currentLine;
      }
    }
    myFile.close();

    // Print the last line of the file
    Serial.println(LAST_LINE);
  } else {
    // if the file didn't open, print an error:
    Serial.println("weather_data.csv failed to open.");
  }

  // Extract data from the last line of the file
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  temperature = LAST_LINE.substring(0, LAST_LINE.indexOf(',')).toFloat();
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  humidity = LAST_LINE.substring(0, LAST_LINE.indexOf(',')).toFloat();
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  pressure = LAST_LINE.substring(0, LAST_LINE.indexOf(',')).toFloat();
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  uv_index = LAST_LINE.substring(0, LAST_LINE.indexOf(',')).toInt();
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  uv_index_str = LAST_LINE.substring(0, LAST_LINE.indexOf(','));
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  wind_speed = LAST_LINE.substring(0, LAST_LINE.indexOf(',')).toFloat();
  LAST_LINE = LAST_LINE.substring(LAST_LINE.indexOf(',') + 1);

  wind_direction = LAST_LINE;
}

void loop() {
  String day_date = get_day_date(rtc);
  String time = get_time(rtc);

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);

  display.setCursor(0, 0);
  display.println(day_date);

  display.setCursor(0, 8);
  display.println(time);

  display.setCursor(0, 16);
  display.print("Temp (");
  display.print((char)247);
  display.print("C): ");
  display.println(temperature);

  display.setCursor(0, 24);
  display.print("Humi (%): ");
  display.println(humidity);

  display.setCursor(0, 32);
  display.print("Pres (hPa): ");
  display.println(pressure);

  display.setCursor(0, 40);
  display.print("UVI: ");
  display.println(uv_index_str);

  display.setCursor(0, 48);
  display.print("Wind:  ");
  display.print(wind_speed);
  display.print(" km/h ");
  display.println(wind_direction);

  display.display();
  delay(1000);
}

// Saturday 01/02/2025 - 13:04:19,26.90,49.20,1015.14,0,OFF,15.00,NORTH