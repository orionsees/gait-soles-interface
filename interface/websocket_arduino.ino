#include <Arduino.h>
#include <WiFi.h>
#include <WiFiMulti.h>
#include <WiFiClientSecure.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

WiFiMulti WiFiMulti;
WebSocketsClient webSocket;

#define USE_SERIAL Serial

// WiFi credentials
const char* ssid = "Redmi Note 10S";
const char* password = "012345678";

// WebSocket server details
const char* websocket_server = "gait-soles-interface.onrender.com";
const int websocket_port = 443;
const char* websocket_path = "/ws";

unsigned long lastMessageTime = 0;
const long messageInterval = 5; // Send a message every 5 seconds

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            USE_SERIAL.printf("[WSc] Disconnected!\n");
            break;
        case WStype_CONNECTED:
            {
                USE_SERIAL.printf("[WSc] Connected to url: %s\n", payload);
                
                // Register as a sensor client
                StaticJsonDocument<200> registerDoc;
                registerDoc["type"] = "register";
                registerDoc["role"] = "sensor";
                
                String registerMsg;
                serializeJson(registerDoc, registerMsg);
                webSocket.sendTXT(registerMsg);
                USE_SERIAL.println("Registered as sensor client");
            }
            break;
        case WStype_TEXT:
            USE_SERIAL.printf("[WSc] Received text: %s\n", payload);
            break;
        case WStype_BIN:
            USE_SERIAL.printf("[WSc] Received binary length: %u\n", length);
            break;
        case WStype_ERROR:         
        case WStype_FRAGMENT_TEXT_START:
        case WStype_FRAGMENT_BIN_START:
        case WStype_FRAGMENT:
        case WStype_FRAGMENT_FIN:
            break;
    }
}

void setup() {
    USE_SERIAL.begin(115200);
    USE_SERIAL.setDebugOutput(true);

    USE_SERIAL.println();
    USE_SERIAL.println("ESP32 WebSocket Client");
    USE_SERIAL.println();

    for(uint8_t t = 4; t > 0; t--) {
        USE_SERIAL.printf("[SETUP] BOOT WAIT %d...\n", t);
        USE_SERIAL.flush();
        delay(1000);
    }

    WiFiMulti.addAP(ssid, password);

    // Wait for WiFi connection
    USE_SERIAL.println("Connecting to WiFi...");
    while(WiFiMulti.run() != WL_CONNECTED) {
        delay(100);
    }
    USE_SERIAL.println("WiFi connected");

    // Connect to WebSocket server
    webSocket.beginSSL(websocket_server, websocket_port, websocket_path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
    
    USE_SERIAL.println("WebSocket connection established");
}

void loop() {
    webSocket.loop();

    // Send a test message every few seconds
    unsigned long currentMillis = millis();
    if (currentMillis - lastMessageTime >= messageInterval) {
        lastMessageTime = currentMillis;
        
        // Create JSON message compatible with the server format
        StaticJsonDocument<200> sensorDoc;
        sensorDoc["type"] = "sensor";
        sensorDoc["message"] = "Hello World from ESP32";
        sensorDoc["value"] = random(100); // Random test value
        
        String sensorMsg;
        serializeJson(sensorDoc, sensorMsg);
        
        webSocket.sendTXT(sensorMsg);
        USE_SERIAL.println("Sent: " + sensorMsg);
    }
}
