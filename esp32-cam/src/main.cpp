#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include "esp_camera.h"
#include "camera_pins.h"

const char* ssid = "Familia-Munoz_2.4G"; 
const char* password = "AlyPa90*";

const char* ws_host = "guardian-ai-md9o.onrender.com"; 
const int ws_port = 443; 
const char* ws_path = "/api/v1/ws/stream";

WebSocketsClient webSocket;
bool isConnected = false;
unsigned long lastFrameTime = 0;
const int frameInterval = 200; // 5 FPS para estabilidad inicial en Render (200ms)

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("❌ WebSocket Desconectado");
            isConnected = false;
            break;
        case WStype_CONNECTED:
            Serial.println("✅ Conectado al Servidor en la Nube");
            isConnected = true;
            break;
        case WStype_TEXT:
            // Log de confirmación del servidor
            // Serial.printf("[WS]: %s\n", payload);
            break;
        case WStype_BIN:
            break;
        case WStype_ERROR:
            Serial.println("⚠️ Error en WebSocket");
            break;
        default:
            break;
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Configuración Cámara
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
    config.xclk_freq_hz = 10000000;
    config.pixel_format = PIXFORMAT_JPEG;

    if (psramFound()) {
        config.frame_size = FRAMESIZE_VGA;
        config.jpeg_quality = 12;
        config.fb_count = 2;
        config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
        config.frame_size = FRAMESIZE_QVGA;
        config.jpeg_quality = 15;
        config.fb_count = 1;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("❌ Error al iniciar cámara: 0x%x\n", err);
        return;
    }

    sensor_t * s = esp_camera_sensor_get();
    if (s) {
        s->set_vflip(s, 1);
        s->set_hmirror(s, 0);
    }

    // Wi-Fi
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Conectando a Wi-Fi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n🌐 Wi-Fi Conectado");

    // Configuración SSL WebSocket
    webSocket.setExtraHeaders("Origin: https://guardian-ai-md9o.onrender.com\r\n");
    webSocket.beginSSL(ws_host, ws_port, ws_path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000); // Intenta reconectar cada 5s, no de forma agresiva
    webSocket.enableHeartbeat(10000, 3000, 2); // Ping/Pong activo cada 10s
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        webSocket.loop();

        // Envío seguro de frames
        if (isConnected && (millis() - lastFrameTime >= frameInterval)) {
            camera_fb_t * fb = esp_camera_fb_get();
            if (fb) {
                // Solo enviar si el buffer del socket está listo para transmitir
                bool sent = webSocket.sendBIN(fb->buf, fb->len);
                if (!sent) {
                    Serial.println("⚠️ Frame no enviado (buffer lleno)");
                }
                // SIEMPRE liberar el buffer de la cámara para prevenir fugas de memoria
                esp_camera_fb_return(fb);
            }
            lastFrameTime = millis();
        }
    } else {
        isConnected = false;
        delay(500);
    }
}