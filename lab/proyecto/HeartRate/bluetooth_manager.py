import serial
import threading
import time
import queue
import subprocess
from typing import Optional, Callable


class BluetoothManager:
    def __init__(self):
        self.serial_port_path = "/dev/rfcomm0"
        self.baud_rate = 115200
        self.serial_conn: Optional[serial.Serial] = None
        self.device_name = "HeartRate_Wearable"
        self.device_address: Optional[str] = None
        self.data_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self.running = False
        self.receive_thread = None

    def set_callbacks(self, data_callback: Callable, status_callback: Callable):
        self.data_callback = data_callback
        self.status_callback = status_callback

    def find_device_address(self) -> Optional[str]:
        import bluetooth
        print("Buscando dispositivos...")
        devices = bluetooth.discover_devices(duration=8, lookup_names=True)
        for addr, name in devices:
            print(f"Encontrado: {name} ({addr})")
            if name and self.device_name.lower() in name.lower():
                return addr
        return None

    def bind_rfcomm(self) -> bool:
        try:
            subprocess.run(["sudo", "rfcomm", "release", "0"], capture_output=True)
            subprocess.run(["sudo", "rfcomm", "bind", "0", self.device_address, "1"], capture_output=True, check=True)
            time.sleep(2)  # Esperar qu1e se cree el dispositivo
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al enlazar rfcomm: {e}")
            return False

    def connect(self) -> bool:
        self.device_address = self.find_device_address()
        if not self.device_address:
            print("Dispositivo no encontrado")
            return False

        if not self.bind_rfcomm():
            print("No se pudo enlazar rfcomm")
            return False

        try:
            self.serial_conn = serial.Serial(self.serial_port_path, self.baud_rate, timeout=1)
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_data, daemon=True)
            self.receive_thread.start()
            if self.status_callback:
                self.status_callback("Conectado")
            print("Conexión establecida")
            return True
        except Exception as e:
            print(f"Error abriendo puerto serial: {e}")
            return False

    def disconnect(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        subprocess.run(["sudo", "rfcomm", "release", "0"], capture_output=True)
        if self.status_callback:
            self.status_callback("Desconectado")
        print("Conexión cerrada")

    def _receive_data(self):
        while self.running:
            try:
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode().strip()
                    if line:
                        print(f"Datos recibidos: {line}")
                        if self.data_callback:
                            self.data_callback(line)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error recibiendo datos: {e}")
                self.running = False
                break

    def send_command(self, command: str) -> bool:
        if not self.serial_conn or not self.serial_conn.is_open:
            print("Puerto serial no está abierto")
            return False
        try:
            if not command.endswith("\n"):
                command += "\n"
            self.serial_conn.write(command.encode())
            print(f"Comando enviado: {command.strip()}")
            return True
        except Exception as e:
            print(f"Error enviando comando: {e}")
            return False

    def is_connected(self) -> bool:
        return self.serial_conn and self.serial_conn.is_open
