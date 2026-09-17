#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include "esp_camera.h"
#include "camera_pins.h"

const char* ssid = "Alfred"; 
const char* password = "12345678";

const char* ws_host = "172.20.10.2"; // IPv4 actual del PC en la red Wi-Fi
const int ws_port = 10000; 
const char* ws_path = "/api/v1/ws/stream";

WebSocketsClient webSocket;
bool isConnected = false;
unsigned long lastFrameTime = 0;
const int frameInterval = 40; // Ajustado a ~25 FPS para mayor estabilidad TCP

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("❌ WebSocket Local Desconectado");
            isConnected = false;
            break;
        case WStype_CONNECTED:
            Serial.println("✅ Conectado al Backend Local (PC)");
            isConnected = true;
            break;
        case WStype_ERROR:
            Serial.printf("⚠️ Error en comunicación WebSocket: %s\n", payload ? (char*)payload : "Desconocido");
            break;
        default:
            break;
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

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
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    if (psramFound()) {
        Serial.println("🧠 PSRAM Detectada. Usando VGA (640x480).");
        config.frame_size = FRAMESIZE_VGA;
        config.jpeg_quality = 12; 
        config.fb_count = 2;
        config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
        Serial.println("⚠️ PSRAM NO Detectada. Usando QVGA (320x240).");
        config.frame_size = FRAMESIZE_QVGA;
        config.jpeg_quality = 12;
        config.fb_count = 1;
        config.grab_mode = CAMERA_GRAB_LATEST;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("❌ Error al inicializar cámara: 0x%x\n", err);
        return;
    }

    sensor_t * s = esp_camera_sensor_get();
    if (s) {
        s->set_vflip(s, 1);
        s->set_hmirror(s, 0);
    }

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Conectando a Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n🌐 Wi-Fi Conectado. IP ESP32: " + WiFi.localIP().toString());

    // Configuración del WebSocket
    webSocket.begin(ws_host, ws_port, ws_path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(2000);
    // Mantiene viva la conexión omitiendo timeouts de red local
    webSocket.enableHeartbeat(1500, 3000, 2); 
}

void loop() {
    webSocket.loop();

    if (WiFi.status() != WL_CONNECTED) {
        isConnected = false;
        return;
    }

    if (isConnected && (millis() - lastFrameTime >= frameInterval)) {
        camera_fb_t * fb = esp_camera_fb_get();
        if (fb) {
            bool sent = webSocket.sendBIN(fb->buf, fb->len);
            if (!sent) {
                Serial.println("⚠️ Error al enviar frame por WS (Buffer lleno)");
            }
            esp_camera_fb_return(fb);
            lastFrameTime = millis();
        }
    }
}