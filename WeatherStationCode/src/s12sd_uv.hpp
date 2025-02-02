#ifndef S12SD_UV_HPP
#define S12SD_UV_HPP
#include <Arduino.h>
#include <string.h>

// Gets the UV index value (0-12) based on the sensor value.
int get_uv_index_value(int uv_pin);
// Gets the UV index (LOW-EXTREME) based on the sensor value.
String get_uv_index(int uv_index_value);

#endif