#include "ssd1306_display.hpp"
#define SSD1306_I2C_ADDRESS 0x3C  // Default I2C address for the OLED display

void ssd1306_display_setup(Adafruit_SSD1306 &display) {
  if (!display.begin(SSD1306_SWITCHCAPVCC,
                     SSD1306_I2C_ADDRESS)) {  // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for (;;);
  }
}

void ssd1306_display_clear(Adafruit_SSD1306 &display) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);

  display.display();
}

void ssd1306_display_live_time(Adafruit_SSD1306 &display, String day_date,
                               String time) {
  display.setCursor(0, 0);
  display.println(day_date);

  display.setCursor(0, 8);
  display.println(time);

  display.display();
}

void ssd1306_display_weather_data(
    Adafruit_SSD1306 &display, float latest_temperature, float latest_humidity,
    float latest_pressure, int latest_uv_index, String latest_uv_index_str,
    float latest_wind_speed, String latest_wind_direction) {
  display.setCursor(0, 16);
  display.print("Temp (");
  display.print((char)247);
  display.print("C): ");
  display.println(latest_temperature);

  display.setCursor(0, 24);
  display.print("Humi (%): ");
  display.println(latest_humidity);

  display.setCursor(0, 32);
  display.print("Pres (hPa): ");
  display.println(latest_pressure);

  display.setCursor(0, 40);
  display.print("UVI: ");
  display.println(latest_uv_index_str);

  display.setCursor(0, 48);
  display.print("Wind:  ");
  display.print(latest_wind_speed);
  display.print(" km/h ");
  display.println(latest_wind_direction);

  display.display();
}

void ssd1306_display_diagnostic(Adafruit_SSD1306 &display,
                                float latest_battery_percentage,
                                String latest_reading_day_date,
                                String latest_reading_time) {
  ssd1306_display_clear(display);

  display.setCursor(0, 0);
  display.println("Latest reading from: ");
  display.println(latest_reading_day_date);
  display.setCursor(0, 16);
  display.println(latest_reading_time);

  display.setCursor(0, 24);
  display.print("Battery: ");
  display.print(latest_battery_percentage);
  display.println("%");

  display.display();
}