#ifndef ESPNOW_RECIEVE_HPP
#define ESPNOW_RECIEVE_HPP

#include <ESP8266WiFi.h>
#include <espnow.h>

void onDataReceived(uint8_t *senderMac, uint8_t *incomingData, uint8_t len);
void setupEspNOW();

#endif