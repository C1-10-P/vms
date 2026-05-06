// firmware/camera_node/camera_node.ino - QR Scanner Only
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"

// ============ Pin Definitions ============
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Status LED
#define STATUS_LED_PIN    4

// Button for manual trigger (optional)
#define BUTTON_PIN        13

// ============ WiFi Configuration ============
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ============ MQTT Configuration ============
const char* MQTT_BROKER = "192.168.1.100";
const int MQTT_PORT = 1883;
const char* MQTT_USER = "esp32_camera";
const char* MQTT_PASSWORD = "your_password";

// ============ Node Configuration ============
const char* NODE_UUID = "CAM-001";
const char* NODE_TYPE = "camera";

// ============ Global Variables ============
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastHeartbeat = 0;
bool isProcessing = false;

// ============ Setup ============
void setup() {
  Serial.begin(115200);
  Serial.println("\n\nVMS QR Scanner Node Starting...");
  
  // Initialize pins
  pinMode(STATUS_LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(STATUS_LED_PIN, LOW);
  
  // Initialize camera
  initCamera();
  
  // Connect to WiFi
  connectWiFi();
  
  // Setup MQTT
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(mqttCallback);
  connectMQTT();
  
  // Send startup status
  sendStatus("online", "QR Scanner ready");
  
  // Blink to indicate ready
  blinkLED(3);
  
  Serial.println("QR Scanner ready. Place QR code in front of camera.");
}

// ============ Camera Initialization ============
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 10;
  config.fb_count = 1;
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }
  Serial.println("Camera initialized");
}

// ============ QR Code Detection ============
String decodeQRCode() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return "";
  }
  
  // Here you would integrate a QR decoding library
  // For ESP32-CAM, you can use the quirc library
  // This is a placeholder - in production, implement actual QR decoding
  
  // Simulate QR detection for testing
  // In production, replace with actual QR decoding
  String simulatedData = simulateQRDetection();
  
  esp_camera_fb_return(fb);
  
  return simulatedData;
}

// Simulated QR detection for testing
// Replace with actual QR decoding in production
String simulateQRDetection() {
  // For testing, return a sample student ID
  // In production, use actual QR decoding library
  static int counter = 0;
  counter++;
  
  if (counter % 3 == 0) {
    return "ENE221-0108/2018|TIE4101";
  } else if (counter % 3 == 1) {
    return "ENE221-0100/2020|TIE4101";
  } else {
    return "{\"first_name\":\"John\",\"last_name\":\"Doe\",\"national_id\":\"12345678\",\"phone_number\":\"+254712345678\",\"purpose\":\"meeting\"}";
  }
}

// ============ Process Scans ============
void processAttendanceScan() {
  if (isProcessing) {
    Serial.println("Already processing, please wait...");
    return;
  }
  
  isProcessing = true;
  digitalWrite(STATUS_LED_PIN, HIGH);
  
  Serial.println("Scanning QR code for attendance...");
  
  String qrData = decodeQRCode();
  
  if (qrData.length() > 0) {
    Serial.print("QR Detected: ");
    Serial.println(qrData);
    
    // Create JSON payload
    StaticJsonDocument<512> doc;
    doc["node_uuid"] = NODE_UUID;
    doc["scan_type"] = "attendance";
    doc["qr_data"] = qrData;
    doc["timestamp"] = millis();
    
    char buffer[512];
    serializeJson(doc, buffer);
    
    // Publish to MQTT
    if (client.publish("jkuat/attendance/scan", buffer)) {
      Serial.println("Attendance data sent to server");
      blinkLED(2);  // Success - blink twice
    } else {
      Serial.println("Failed to send attendance data");
      blinkLED(5);  // Error - blink 5 times
    }
  } else {
    Serial.println("No QR code detected");
    blinkLED(1);  // No QR - blink once
  }
  
  digitalWrite(STATUS_LED_PIN, LOW);
  isProcessing = false;
}

void processVisitorScan() {
  if (isProcessing) {
    Serial.println("Already processing, please wait...");
    return;
  }
  
  isProcessing = true;
  digitalWrite(STATUS_LED_PIN, HIGH);
  
  Serial.println("Scanning QR code for visitor...");
  
  String qrData = decodeQRCode();
  
  if (qrData.length() > 0) {
    Serial.print("QR Detected: ");
    Serial.println(qrData);
    
    // Create JSON payload
    StaticJsonDocument<512> doc;
    doc["node_uuid"] = NODE_UUID;
    doc["scan_type"] = "visitor";
    doc["qr_data"] = qrData;
    doc["timestamp"] = millis();
    
    char buffer[512];
    serializeJson(doc, buffer);
    
    // Publish to MQTT
    if (client.publish("jkuat/visitor/scan", buffer)) {
      Serial.println("Visitor data sent to server");
      blinkLED(2);
    } else {
      Serial.println("Failed to send visitor data");
      blinkLED(5);
    }
  } else {
    Serial.println("No QR code detected");
    blinkLED(1);
  }
  
  digitalWrite(STATUS_LED_PIN, LOW);
  isProcessing = false;
}

// ============ Network Functions ============
void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi connection failed");
  }
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    
    if (client.connect(NODE_UUID, MQTT_USER, MQTT_PASSWORD)) {
      Serial.println("✅ connected");
      
      // Subscribe to commands
      char cmdTopic[64];
      snprintf(cmdTopic, 64, "jkuat/system/commands/%s", NODE_UUID);
      client.subscribe(cmdTopic);
      
      sendStatus("online", "Connected to MQTT");
      
    } else {
      Serial.print("❌ failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

// ============ MQTT Callback ============
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("📨 Command: ");
  Serial.println(topic);
  
  String message = String((char*)payload).substring(0, length);
  
  if (strcmp(topic, "jkuat/attendance/trigger") == 0) {
    processAttendanceScan();
  }
  else if (strcmp(topic, "jkuat/visitor/trigger") == 0) {
    processVisitorScan();
  }
  else if (strstr(topic, "jkuat/system/commands/") != NULL) {
    // Parse JSON command
    StaticJsonDocument<256> doc;
    deserializeJson(doc, payload, length);
    
    const char* command = doc["command"];
    
    if (strcmp(command, "reboot") == 0) {
      Serial.println("Rebooting...");
      ESP.restart();
    }
    else if (strcmp(command, "scan_attendance") == 0) {
      processAttendanceScan();
    }
    else if (strcmp(command, "scan_visitor") == 0) {
      processVisitorScan();
    }
  }
}

// ============ Status Functions ============
void sendStatus(const char* status, const char* message) {
  StaticJsonDocument<256> doc;
  doc["node_uuid"] = NODE_UUID;
  doc["status"] = status;
  doc["message"] = message;
  doc["version"] = "1.0.0";
  doc["uptime"] = millis() / 1000;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["rssi"] = WiFi.RSSI();
  doc["timestamp"] = millis();
  
  char buffer[256];
  serializeJson(doc, buffer);
  
  char statusTopic[64];
  snprintf(statusTopic, 64, "jkuat/system/status/%s", NODE_UUID);
  client.publish(statusTopic, buffer);
}

void sendHeartbeat() {
  StaticJsonDocument<128> doc;
  doc["node_uuid"] = NODE_UUID;
  doc["uptime"] = millis() / 1000;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["rssi"] = WiFi.RSSI();
  doc["timestamp"] = millis();
  
  char buffer[128];
  serializeJson(doc, buffer);
  
  char heartbeatTopic[64];
  snprintf(heartbeatTopic, 64, "jkuat/system/heartbeat/%s", NODE_UUID);
  client.publish(heartbeatTopic, buffer);
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(100);
    digitalWrite(STATUS_LED_PIN, LOW);
    delay(100);
  }
}

// ============ Main Loop ============
void loop() {
  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();
  
  // Check button for manual trigger
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(BUTTON_PIN) == LOW) {
      Serial.println("Button pressed!");
      processAttendanceScan();
      while (digitalRead(BUTTON_PIN) == LOW) {
        delay(10);
      }
    }
  }
  
  // Send heartbeat every 60 seconds
  if (millis() - lastHeartbeat > 60000) {
    sendHeartbeat();
    lastHeartbeat = millis();
  }
}