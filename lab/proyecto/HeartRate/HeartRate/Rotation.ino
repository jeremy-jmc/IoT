#include <Wire.h>
#include <MPU6050.h>
#include <BluetoothSerial.h>   // 1️⃣  Librería BT

MPU6050 mpu;
BluetoothSerial SerialBT;      // 1️⃣  Instancia BT

const int  FILTER_SIZE   = 10;
float      ax_buffer[FILTER_SIZE] = {0};
int        buffer_index  = 0;

float ax;
float ax_offset          = 0;

const float umbralAX     = 0.15;   // Sensibilidad de inclinación
unsigned long tiempo_fuera_de_rango = 0;
bool  postura_incorrecta = false;

// ---------- Calibración ----------
void calibrarReferencia() {
  Serial.println("Calibrando... mantén postura correcta");
  long sum_ax = 0;

  for (int i = 0; i < 1000; i++) {
    int16_t ax_raw, ay_raw, az_raw;
    mpu.getAcceleration(&ax_raw, &ay_raw, &az_raw);
    sum_ax += ax_raw;
    delay(5);
  }

  ax_offset = (sum_ax / 1000.0) / 16384.0;
  Serial.print("AX calibrado en: "); Serial.println(ax_offset, 3);
  Serial.println("Referencia establecida.");
}

// ---------- SETUP ----------
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);          // SDA, SCL  (pines por defecto en muchos ESP32)

  Serial.println("Iniciando sensor...");
  mpu.initialize();
  if (mpu.testConnection()) {
    Serial.println("MPU6050 conectado correctamente.");
  } else {
    Serial.println("Error al conectar el MPU6050.");
    while (1);
  }

  // 2️⃣  Arrancamos Bluetooth con el nombre que aparecerá al emparejar
  if (!SerialBT.begin("PostureMonitor")) {  // true = BT habilitado
    Serial.println("Error al iniciar Bluetooth Serial");
    while (1);
  }
  Serial.println("Bluetooth listo. Busca el dispositivo 'PostureMonitor'.");

  delay(1000);
  calibrarReferencia();
}

// ---------- LOOP ----------
void loop() {
  int16_t ax_raw, ay_raw, az_raw;
  mpu.getAcceleration(&ax_raw, &ay_raw, &az_raw);

  // Convertir a g y aplicar offset
  float ax_new = ax_raw / 16384.0 - ax_offset;

  // Buffer circular
  ax_buffer[buffer_index] = ax_new;
  buffer_index = (buffer_index + 1) % FILTER_SIZE;

  // Promedio filtrado
  ax = 0;
  for (int i = 0; i < FILTER_SIZE; i++) {
    ax += ax_buffer[i];
  }
  ax /= FILTER_SIZE;

  // 3️⃣  Enviar el valor filtrado por USB y Bluetooth
  Serial.print("AX filtrado: "); Serial.println(ax, 3);
  SerialBT.println(ax, 3);    // envía "x.xxx\n"

  // Detección de postura
  if (abs(ax) > umbralAX) {
    if (tiempo_fuera_de_rango == 0) {
      tiempo_fuera_de_rango = millis();
    } else if (millis() - tiempo_fuera_de_rango >= 3000) {
      postura_incorrecta = true;
    }
  } else {
    tiempo_fuera_de_rango = 0;
    postura_incorrecta    = false;
  }

  if (postura_incorrecta) {
    Serial.println("⚠ Postura incorrecta (>3 s).");
    SerialBT.println("ALERTA_POSTURA");
  }

  delay(500);
}