#include "ssd1306_display.hpp"
#define SSD1306_I2C_ADDRESS 0x3C  // Default I2C address for the OLED display

// Setup the SSD1306 display
void ssd1306DisplaySetup(Adafruit_SSD1306 &display) {
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;);  // Don't proceed, loop forever
  }
}

// Clear the SSD1306 display
void ssd1306DisplayClear(Adafruit_SSD1306 &display) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  Serial.println("Display Cleared.");
  delay(1000);
  display.display();
  Serial.println("Display Clearer");
}

// Format
// Line 1: Live Day Date
// Line 2: Live Time
// Line 8: Time difference between latest reading and current time
// Display the live time and the time difference between now and the last
// reading
void ssd1306DisplayLiveTime(Adafruit_SSD1306 &display, String dayDate,
                            String time, int hours, int minutes, int seconds) {
  display.setCursor(0, 0);
  display.println(dayDate);

  display.setCursor(0, 8);
  display.println(time);

  // Only display most significant time difference
  display.setCursor(0, 56);
  if (hours > 0) {
    display.print(hours);
    display.println("h ago...");
  } else if (minutes > 0) {
    display.print(minutes);
    display.println("m ago...");
  } else if (seconds > 0) {
    display.println("Just Now...");
  }

  display.display();
}

// Format
// Line 3: Latest Temperature
// Line 4: Latest Humidity
// Line 5: Latest Pressure
// Line 6: Latest Wind Speed & Direction
// Line 7: Latest Battery Percentage
// Display the latest readings on the OLED display
void ssd1306DisplayReadings(Adafruit_SSD1306 &display, float latest_temperature,
                            float latest_humidity, float latest_pressure,
                            float latest_wind_speed,
                            String latest_wind_direction,
                            float latest_battery_percentage) {
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

  display.display();
}