#include <Arduino.h>
#include <ArduinoOTA.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <espnow.h>
#include <user_interface.h>

#include "config.hpp"

volatile bool dataReceived = false;
String incomingDataString = "";

// Health Server & Buffer Variables
ESP8266WebServer server(80);
const int MAX_BUFFER_SIZE = 100;
String offlineBuffer[MAX_BUFFER_SIZE];
int bufferCount = 0;

unsigned long packetsReceived = 0;
int lastHttpResponse = 0;
unsigned long lastPostAttempt = 0;
const unsigned long POST_RETRY_INTERVAL = 5000;

// --- UPDATE WITH YOUR RASPBERRY PI IP ---
const char* serverName = "http://192.168.1.100:5000/api/weather";

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><title>Relay Health</title>";
  html +=
      "<meta name=\"viewport\" content=\"width=device-width, "
      "initial-scale=1\">";
  html +=
      "<style>body{font-family:Arial; margin:2rem; background-color:#121212; "
      "color:#ffffff;}";
  html +=
      ".stat{font-size:1.2rem; margin-bottom:10px; padding:10px; "
      "background:#1e1e1e; border-radius:5px;}</style></head><body>";
  html += "<h1>Weather Station Relay Health OTA TEST</h1>";

  unsigned long uptimeSeconds = millis() / 1000;
  int days = uptimeSeconds / 86400;
  int hours = (uptimeSeconds % 86400) / 3600;
  int mins = (uptimeSeconds % 3600) / 60;
  int secs = uptimeSeconds % 60;

  html += "<div class=\"stat\"><b>Uptime:</b> " + String(days) + "d " +
          String(hours) + "h " + String(mins) + "m " + String(secs) + "s</div>";
  html += "<div class=\"stat\"><b>WiFi RSSI:</b> " + String(WiFi.RSSI()) +
          " dBm</div>";
  html += "<div class=\"stat\"><b>WiFi Channel:</b> " + String(WiFi.channel()) +
          "</div>";
  html += "<div class=\"stat\"><b>ESP-NOW Packets Received:</b> " +
          String(packetsReceived) + "</div>";
  html += "<div class=\"stat\"><b>Latest ESP-NOW Packet:</b> " +
          (incomingDataString == "" ? "None" : incomingDataString) + "</div>";
  html += "<div class=\"stat\"><b>Last HTTP Response Code:</b> " +
          String(lastHttpResponse) + "</div>";
  html += "<div class=\"stat\"><b>Offline Buffer Status:</b> " +
          String(bufferCount) + " / " + String(MAX_BUFFER_SIZE) + "</div>";

  html += "</body></html>";
  server.send(200, "text/html", html);
}

// Callback function that will be executed when data is received
void onDataReceived(uint8_t* senderMac, uint8_t* incomingData, uint8_t len) {
  // Write the incoming data to the uint8_t array
  uint8_t recieved[len + 1];

  Serial.print("Received: ");

  for (int i = 0; i < len; i++) {
    Serial.print((char)incomingData[i]);
    recieved[i] = incomingData[i];
  }

  recieved[len] = '\0';

  // Convert the uint8_t array to a String
  incomingDataString = String((char*)recieved);
  dataReceived = true;
}

void setup() {
  Serial.begin(115200);
  Serial.println("\nStarting Relay...");

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to Wi-Fi...");
  }

  Serial.print("Station IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Wi-Fi Channel: ");
  Serial.println(WiFi.channel());

  // Print MAC address of the receiver
  Serial.print("Receiver MAC: ");
  Serial.println(WiFi.macAddress());

  // Initialize ESP-NOW
  if (esp_now_init() != 0) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Setup OTA
  ArduinoOTA.setHostname("Relay");
  ArduinoOTA.onStart([]() { Serial.println("\nStarting OTA update..."); });
  ArduinoOTA.onEnd([]() { Serial.println("\nOTA Update Complete!"); });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
    if (error == OTA_AUTH_ERROR)
      Serial.println("Auth Failed");
    else if (error == OTA_BEGIN_ERROR)
      Serial.println("Begin Failed");
    else if (error == OTA_CONNECT_ERROR)
      Serial.println("Connect Failed");
    else if (error == OTA_RECEIVE_ERROR)
      Serial.println("Receive Failed");
    else if (error == OTA_END_ERROR)
      Serial.println("End Failed");
  });
  ArduinoOTA.begin();

  // Setup Health Web Server
  server.on("/", handleRoot);
  server.begin();

  // Register callback for receiving data
  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);  // ESPNOW OLD
  esp_now_register_recv_cb(onDataReceived);

  Serial.println("Setup complete. Waiting for data...");
}

void loop() {
  // Handle OTA updates
  ArduinoOTA.handle();

  // Listen for incoming HTTP requests to the health dashboard
  server.handleClient();

  if (dataReceived == true) {
    packetsReceived++;

    // Store reading in the buffer
    if (bufferCount < MAX_BUFFER_SIZE) {
      offlineBuffer[bufferCount++] = incomingDataString;
    } else {
      // Buffer full: shift everything left (drop oldest) to make room for
      // newest
      for (int i = 1; i < MAX_BUFFER_SIZE; i++) {
        offlineBuffer[i - 1] = offlineBuffer[i];
      }
      offlineBuffer[MAX_BUFFER_SIZE - 1] = incomingDataString;
    }

    dataReceived = false;
    Serial.flush();
  }

  // If we have buffered data, try to send it (rate-limited to avoid spamming a
  // dead server)
  if (bufferCount > 0 && (millis() - lastPostAttempt > POST_RETRY_INTERVAL)) {
    if (WiFi.status() == WL_CONNECTED) {
      lastPostAttempt = millis();
      WiFiClient client;
      HTTPClient http;

      http.begin(client, serverName);
      http.addHeader("Content-Type", "text/plain");

      int httpResponseCode = http.POST(offlineBuffer[0]);
      lastHttpResponse = httpResponseCode;

      if (httpResponseCode > 0) {
        Serial.print("HTTP POST Success, Code: ");
        Serial.println(httpResponseCode);

        // Successfully reached server, remove from buffer
        for (int i = 1; i < bufferCount; i++) {
          offlineBuffer[i - 1] = offlineBuffer[i];
        }
        bufferCount--;

        // If success code, immediately trigger next loop to blast remaining
        // backlog
        if (httpResponseCode == 200) lastPostAttempt = 0;
      } else {
        Serial.print("HTTP POST Error: ");
        Serial.println(httpResponseCode);
      }
      http.end();
    } else {
      // If WiFi is disconnected, silently wait and try again later
    }
  }
}