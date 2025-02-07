#ifndef ESPNOW_SEND_HPP
#define ESPNOW_SEND_HPP

#include <WiFi.h>
#include <esp_now.h>

// Callback when data is sent
void onDataSent(const uint8_t *macAddr, esp_now_send_status_t status);
void sendData(String data);
#endif