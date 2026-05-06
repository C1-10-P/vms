#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// Function prototypes (avoid implicit declaration errors)
float calculateDistance(int rssi);
void publishDetection(String tagId, int rssi, float distance);
void publishHeartbeat();
void startBLEScan(int duration);

// BLE Scan object
BLEScan* pBLEScan;

// Callback class
class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
        String tagId = advertisedDevice.getAddress().toString().c_str();
        int rssi = advertisedDevice.getRSSI();

        // Calculate distance from RSSI
        float distance = calculateDistance(rssi);

        // Publish to MQTT
        publishDetection(tagId, rssi, distance);
    }
};

void setup() {
    Serial.begin(115200);

    BLEDevice::init("");
    pBLEScan = BLEDevice::getScan();
    pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
    pBLEScan->setActiveScan(true); // better results, more power usage
}

// Main loop
void loop() {
    startBLEScan(5);     // Scan for 5 seconds
    publishHeartbeat();  // Send status
    delay(60000);        // Run every 60 seconds
}

// Start BLE scan
void startBLEScan(int duration) {
    pBLEScan->start(duration, false);
    pBLEScan->clearResults();
}

// Example distance calculation (RSSI-based)
float calculateDistance(int rssi) {
    int txPower = -59; // typical BLE TX power
    if (rssi == 0) return -1.0;

    float ratio = (float)rssi / txPower;
    if (ratio < 1.0) {
        return pow(ratio, 10);
    } else {
        return (0.89976) * pow(ratio, 7.7095) + 0.111;
    }
}

// Stub MQTT publish (replace with your implementation)
void publishDetection(String tagId, int rssi, float distance) {
    Serial.printf("Device: %s | RSSI: %d | Distance: %.2f\n",
                  tagId.c_str(), rssi, distance);
}

// Stub heartbeat
void publishHeartbeat() {
    Serial.println("Heartbeat sent");
}