#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "BluetoothSerial.h"

MAX30105 particleSensor;
BluetoothSerial SerialBT;

// Variables para envío de datos por Bluetooth
unsigned long lastBluetoothSend = 0;
const unsigned long BLUETOOTH_INTERVAL = 1000; // Enviar datos cada segundo
float lastValidBPM = 0; // Última lectura válida de BPM

// Variables para manejo de errores I2C
const int IR_THRESHOLD = 2000; // Umbral para detectar dedo en el sensor (igual que base.ino)
unsigned long lastI2CError = 0;
unsigned long lastSensorCheck = 0;
const unsigned long SENSOR_CHECK_INTERVAL = 300; // Verificar sensor cada 30 segundos (menos frecuente)
bool sensorOK = true;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Paso 1: Serial iniciado");

  Wire.begin(21, 22);
  Serial.println("Paso 2: I2C iniciado");

  SerialBT.begin("HeartRate_Wearable");
  Serial.println("Paso 3: Bluetooth iniciado");

  Serial.println("Paso 4: Iniciando sensor...");
  if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD)) {
    Serial.println("Paso 5: Sensor no encontrado");
    return;
  }

  Serial.println("Paso 6: Sensor encontrado");
  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeIR(0x0A);
  Serial.println("Paso 7: Sensor configurado");
}


void loop() {
  long irValue = particleSensor.getIR();

  if (irValue < IR_THRESHOLD) { // Usar el mismo threshold que base.ino (20000)
    //Serial.println("Coloca el dedo en el sensor...");
    //Serial.println(irValue);
    
    // Enviar estado por Bluetooth cada cierto tiempo
    if (millis() - lastBluetoothSend > BLUETOOTH_INTERVAL) {
      SerialBT.println("STATUS:NO_FINGER");
      lastBluetoothSend = millis();
    }
    
    delay(1000);
    return;
  }

  if (particleSensor.available()) {
    uint32_t ir = particleSensor.getIR();

    bool beatDetected = checkForBeat(ir);

    if (beatDetected) {
      static uint32_t lastBeat = 0;
      uint32_t now = millis();
      uint32_t delta = now - lastBeat;
      lastBeat = now;

      float bpm = 60000.0 / (float)delta;
      // bpm > 30 && 
      if (bpm < 200) {
        Serial.print("Latido detectado! BPM: ");
        Serial.println(bpm);
        
        // Guardar última lectura válida para Bluetooth
        lastValidBPM = bpm;
      }
    }

    particleSensor.nextSample(); // Siguiente muestra
  }

  // Enviar datos por Bluetooth periódicamente
  if (millis() - lastBluetoothSend > BLUETOOTH_INTERVAL) {
    if (irValue > IR_THRESHOLD) { // Solo si hay dedo en el sensor
      if (lastValidBPM > 0) {
        // Formato: BPM:valor_instantaneo:valor_promedio
        String data = "BPM:" + String((int)lastValidBPM) + ":" + String((int)lastValidBPM);
        SerialBT.println(data);
        
        Serial.println("Enviado por Bluetooth: " + data);
      } else {
        SerialBT.println("STATUS:MEASURING");
      }
    }
    lastBluetoothSend = millis();
  }

  // Verificar comandos recibidos por Bluetooth
  if (SerialBT.available()) {
    String receivedData = SerialBT.readString();
    receivedData.trim();
    
    if (receivedData == "PING") {
      SerialBT.println("PONG");
    } else if (receivedData == "STATUS") {
      if (irValue > IR_THRESHOLD) {
        SerialBT.println("STATUS:MEASURING");
      } else {
        SerialBT.println("STATUS:NO_FINGER");
      }
    } else if (receivedData == "RESET_SENSOR") {
      sensorOK = reinitializeSensor();
    }
  }

  // Verificar estado del sensor periódicamente (solo si hay problemas persistentes)
  if (millis() - lastSensorCheck > SENSOR_CHECK_INTERVAL) {
    if (!checkSensorConnection()) {
      Serial.println("Sensor desconectado, intentando reconectar...");
      sensorOK = reinitializeSensor();
    } else {
      sensorOK = true;
    }
    lastSensorCheck = millis();
  }
}

// Función para verificar si el sensor está respondiendo
bool checkSensorConnection() {
  Wire.beginTransmission(0x57); // Dirección I2C del MAX30102
  byte error = Wire.endTransmission();
  return (error == 0);
}

// Función para reinicializar el sensor
bool reinitializeSensor() {
  Serial.println("Intentando reinicializar sensor...");
  SerialBT.println("STATUS:SENSOR_REINIT");
  
  delay(100); // Pequeña pausa
  
  if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD)) {
    Serial.println("Error: No se pudo reinicializar el sensor");
    SerialBT.println("ERROR: Sensor reinit failed");
    return false;
  }
  
  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeIR(0x0A);
  
  Serial.println("Sensor reinicializado correctamente");
  SerialBT.println("STATUS:SENSOR_OK");
  lastI2CError = millis();
  
  return true;
}