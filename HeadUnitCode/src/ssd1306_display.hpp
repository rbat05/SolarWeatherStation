#ifndef SSD1306_DISPLAY_HPP
#define SSD1306_DISPLAY_HPP

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

void ssd1306_display_setup(Adafruit_SSD1306 &display);
void ssd1306_display_clear(Adafruit_SSD1306 &display);
void ssd1306_display_live_time(Adafruit_SSD1306 &display, String day_date,
                               String time);
void ssd1306_display_weather_data(
    Adafruit_SSD1306 &display, float latest_temperature, float latest_humidity,
    float latest_pressure, int latest_uv_index, String latest_uv_index_str,
    float latest_wind_speed, String latest_wind_direction);
void ssd1306_display_diagnostic(Adafruit_SSD1306 &display,
                                float latest_battery_percentage,
                                String latest_reading_day_date,
                                String latest_reading_time);

#endif