#include "espNOW_send.hpp"

#include <esp_wifi.h>

// Relay ESP8266 permanent MAC address
uint8_t receiverAddress[] = {0x2c, 0x3a, 0xe8, 0x08, 0xdb, 0x6a};

volatile bool espNowDeliverySuccess = false;
volatile bool espNowDeliveryComplete = false;
bool espNowInitialized = false;

// Remember the last successful channel across deep sleep
RTC_DATA_ATTR uint8_t currentEspNowChannel = 1;

// Callback function when data is sent
void onDataSent(const uint8_t* mac_addr, esp_now_send_status_t status) {
  // Serial.print("Last Packet Send Status: ");

  // Check if the packet was sent
  if (status == ESP_NOW_SEND_SUCCESS) {
    espNowDeliverySuccess = true;
  } else {
    espNowDeliverySuccess = false;
  }
  espNowDeliveryComplete = true;

  // Additional debugging output
  // Serial.print("Status value: ");
  // Serial.println(status);
}

// Send data via ESP-NOW
bool sendData(String data) {
  espNowDeliverySuccess = false;
  espNowDeliveryComplete = false;

  if (!espNowInitialized) {
    // Set device as a Wi-Fi Station
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) return false;

    // Register callback for sending data
    esp_now_register_send_cb(onDataSent);

    // Add receiver's MAC address
    esp_now_peer_info_t peerInfo;
    memset(&peerInfo, 0, sizeof(peerInfo));
    memcpy(peerInfo.peer_addr, receiverAddress, 6);
    peerInfo.channel = currentEspNowChannel;
    peerInfo.encrypt = false;

    // Try to add peer to ESP-NOW
    if (esp_now_add_peer(&peerInfo) != ESP_OK) return false;

    espNowInitialized = true;
  }

  // Convert data to uint8_t
  uint8_t send[data.length() + 1];
  data.getBytes(send, data.length() + 1);

  // Loop through Wi-Fi channels 1 to 11 to find the Relay
  for (int i = 0; i < 11; i++) {
    espNowDeliverySuccess = false;
    espNowDeliveryComplete = false;

    // Force ESP32 local radio to the current test channel
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(currentEspNowChannel, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);

    // Update the peer information to the current test channel
    esp_now_peer_info_t peerInfo;
    memset(&peerInfo, 0, sizeof(peerInfo));
    memcpy(peerInfo.peer_addr, receiverAddress, 6);
    peerInfo.channel = currentEspNowChannel;
    peerInfo.encrypt = false;
    esp_now_mod_peer(&peerInfo);

    // Send data
    if (esp_now_send(receiverAddress, send, sizeof(send)) == ESP_OK) {
      // Wait max 500ms for hardware ACK from receiver
      unsigned long startWait = millis();
      while (!espNowDeliveryComplete && millis() - startWait < 500) {
        delay(10);
      }

      if (espNowDeliverySuccess) {
        return true;  // Success! It will use this channel next time.
      }
    }

    // Transmission failed (no ACK), jump to the next channel
    currentEspNowChannel++;
    if (currentEspNowChannel > 11) {
      currentEspNowChannel = 1;
    }
  }

  return false;  // Failed on all 11 channels
}
