#include "ssd1306_display.hpp"
#define SSD1306_I2C_ADDRESS 0x3C  // Default I2C address for the OLED display

void ssd1306DisplaySetup(Adafruit_SSD1306 &display) {
  if (!display.begin(SSD1306_SWITCHCAPVCC,
                     SSD1306_I2C_ADDRESS)) {  // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for (;;);
  }
}

void ssd1306DisplayClear(Adafruit_SSD1306 &display) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);

  display.display();
}

void ssd1306DisplayLiveTime(Adafruit_SSD1306 &display, String dayDate,
                            String time) {
  display.setCursor(0, 0);
  display.println(dayDate);

  display.setCursor(0, 8);
  display.println(time);

  display.display();
}

// Format
// Live Day Date
// Live Time
// Latest Temperature
// Latest Humidity
// Latest Pressure
// Latest Wind Speed & Direction
// Latest Battery Percentage
// Time difference between latest reading and current time

void ssd1306DisplayReadings(Adafruit_SSD1306 &display, float latest_temperature,
                            float latest_humidity, float latest_pressure,
                            float latest_wind_speed,
                            String latest_wind_direction,
                            float latest_battery_percentage, int hours,
                            int minutes, int seconds) {
  display.setCursor(0, 16);
  display.print("Temp(");
  display.print((char)247);
  display.print("C): ");
  display.println(latest_temperature);

  display.setCursor(0, 24);
  display.print("Humi(%): ");
  display.println(latest_humidity);

  display.setCursor(0, 32);
  display.print("Pres(hPa): ");
  display.println(latest_pressure);

  display.setCursor(0, 40);
  display.print("Wind: ");
  display.print(latest_wind_speed);
  display.print(" km/h ");
  display.println(latest_wind_direction);

  display.setCursor(0, 48);
  display.print("Battery: ");
  display.print(latest_battery_percentage);
  display.println("%");

  display.setCursor(0, 56);

  // Only display most significant time difference
  if (hours > 0) {
    display.print(hours);
    display.print("h ago...");
  } else if (minutes > 0) {
    display.print(minutes);
    display.print("m ago...");
  } else {
    display.print(seconds);
    display.println("Just Now...");
  }

  display.display();
}