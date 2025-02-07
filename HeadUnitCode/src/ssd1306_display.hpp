#ifndef SSD1306_DISPLAY_HPP
#define SSD1306_DISPLAY_HPP

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

void ssd1306DisplaySetup(Adafruit_SSD1306 &display);
void ssd1306DisplayClear(Adafruit_SSD1306 &display);
void ssd1306DisplayLiveTime(Adafruit_SSD1306 &display, String dayDate,
                            String time);
void ssd1306DisplayReadings(Adafruit_SSD1306 &display, float latest_temperature,
                            float latest_humidity, float latest_pressure,
                            float latest_wind_speed,
                            String latest_wind_direction,
                            float latest_battery_percentage, int hours,
                            int minutes, int seconds);

#endif