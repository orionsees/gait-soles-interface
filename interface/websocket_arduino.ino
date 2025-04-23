#include <Arduino.h>                // Core Arduino definitions
#include <WiFi.h>                   // Wi-Fi support for ESP32
#include <WiFiMulti.h>              // Manage multiple Wi-Fi networks
#include <WiFiClientSecure.h>       // Secure (SSL/TLS) TCP client
#include <WebSocketsClient.h>       // WebSocket client library
#include <ArduinoJson.h>            // JSON serialization/deserialization

WiFiMulti WiFiMulti;                // WiFiMulti instance
WebSocketsClient webSocket;         // WebSocket client instance

#define USE_SERIAL Serial           // Serial port for debug output

// WiFi credentials
const char* ssid     = "Redmi Note 10S";
const char* password = "012345678";

// WebSocket server details (WSS)
const char* websocket_server = "gait-soles-interface.onrender.com";
const int   websocket_port   = 443;
const char* websocket_path   = "/ws";

// FSR sensor analog pins
const int fsrPins[]   = {25, 26, , 34, 35};
const int numSensors  = sizeof(fsrPins) / sizeof(fsrPins[0]);

// Timing
unsigned long lastMessageTime   = 0;
const long     messageInterval  = 1;  // milliseconds

// WebSocket event handler
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      USE_SERIAL.println("[WSc] Disconnected!");
      break;
    case WStype_CONNECTED:
      USE_SERIAL.printf("[WSc] Connected to url: %s\n", payload);
      {
        // Send registration JSON: { "type": "register", "role": "sensor" }
        StaticJsonDocument<200> doc;
        doc["type"] = "register";
        doc["role"] = "sensor";
        String msg;
        serializeJson(doc, msg);
        webSocket.sendTXT(msg);
        USE_SERIAL.println("Registered as sensor client");
      }
      break;
    case WStype_TEXT:
      USE_SERIAL.printf("[WSc] Received text: %s\n", payload);
      break;
    default:
      break;
  }
}

void setup() {
  USE_SERIAL.begin(115200);
  USE_SERIAL.setDebugOutput(true);

  // Initialize FSR pins as inputs
  for (int i = 0; i < numSensors; i++) {
    pinMode(fsrPins[i], INPUT);
  }

  // Add Wi-Fi access point(s)
  WiFiMulti.addAP(ssid, password);

  // Wait for Wi-Fi connection
  USE_SERIAL.println("Connecting to WiFi…");
  while (WiFiMulti.run() != WL_CONNECTED) {
    delay(100);
  }
  USE_SERIAL.println("WiFi connected");

  // Begin secure WebSocket connection
  webSocket.beginSSL(websocket_server, websocket_port, websocket_path);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
  USE_SERIAL.println("WebSocket client setup complete");
}

void loop() {
  webSocket.loop();  // Maintain WebSocket connection

  unsigned long currentMillis = millis();
  if (currentMillis - lastMessageTime >= messageInterval) {
    lastMessageTime = currentMillis;

    // Build JSON message
    StaticJsonDocument<400> sensorDoc;
    sensorDoc["type"] = "sensor";
    JsonObject data = sensorDoc.createNestedObject("data");

    // Read and clamp FSR sensor values
    for (int i = 0; i < numSensors; i++) {
      int raw = analogRead(fsrPins[i]);                     // Read ADC (0–4095) :contentReference[oaicite:4]{index=4}
      int value = (raw > 0 ? raw : 0);                       // Clamp floating/noisy readings to zero
      data[String("fsr") + fsrPins[i]] = value;
    }

    // Add timestamp
    sensorDoc["timestamp"] = currentMillis;

    // Serialize and send over WebSocket
    String sensorMsg;
    serializeJson(sensorDoc, sensorMsg);
    webSocket.sendTXT(sensorMsg);
    USE_SERIAL.println("Sent: " + sensorMsg);
  }
}
