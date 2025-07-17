import serial
import threading
import time
import queue
import subprocess
from typing import Optional, Callable, Dict


class BluetoothDevice:
    def __init__(self, name: str, rfcomm_port: int, data_callback: Callable, status_callback: Callable):
        self.name = name
        self.rfcomm_port = rfcomm_port
        self.serial_port_path = f"/dev/rfcomm{rfcomm_port}"
        self.baud_rate = 115200
        self.serial_conn: Optional[serial.Serial] = None
        self.device_address: Optional[str] = None
        self.data_callback = data_callback
        self.status_callback = status_callback
        self.running = False
        self.receive_thread = None


class BluetoothManager:
    def __init__(self):
        self.devices: Dict[str, BluetoothDevice] = {}
        self.device_configs = {
            "HeartRate_Wearable": {"rfcomm_port": 0},
            "PostureMonitor": {"rfcomm_port": 1}
        }

    def set_callbacks(self, data_callback: Callable, status_callback: Callable):
        self.data_callback = data_callback
        self.status_callback = status_callback

    def add_device(self, device_name: str) -> bool:
        """Add a device to be managed"""
        if device_name not in self.device_configs:
            print(f"Unknown device: {device_name}")
            return False
        
        if device_name in self.devices:
            print(f"Device {device_name} already added")
            return True
        
        config = self.device_configs[device_name]
        device = BluetoothDevice(
            device_name, 
            config["rfcomm_port"], 
            self.data_callback, 
            self.status_callback
        )
        self.devices[device_name] = device
        return True

    def find_device_address(self, device_name: str) -> Optional[str]:
        import bluetooth
        print(f"Buscando {device_name}...")
        devices = bluetooth.discover_devices(duration=8, lookup_names=True)
        for addr, name in devices:
            print(f"Encontrado: {name} ({addr})")
            if name and device_name.lower() in name.lower():
                return addr
        return None

    def bind_rfcomm(self, device: BluetoothDevice) -> bool:
        try:
            subprocess.run(["sudo", "rfcomm", "release", str(device.rfcomm_port)], capture_output=True)
            subprocess.run(["sudo", "rfcomm", "bind", str(device.rfcomm_port), device.device_address, "1"], capture_output=True, check=True)
            time.sleep(2)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al enlazar rfcomm{device.rfcomm_port}: {e}")
            return False

    def connect_device(self, device_name: str) -> bool:
        """Connect to a specific device"""
        if device_name not in self.devices:
            if not self.add_device(device_name):
                return False
        
        device = self.devices[device_name]
        
        if device.serial_conn and device.serial_conn.is_open:
            print(f"{device_name} ya está conectado")
            return True
        
        device.device_address = self.find_device_address(device_name)
        if not device.device_address:
            print(f"Dispositivo {device_name} no encontrado")
            return False

        if not self.bind_rfcomm(device):
            print(f"No se pudo enlazar rfcomm para {device_name}")
            return False

        try:
            device.serial_conn = serial.Serial(device.serial_port_path, device.baud_rate, timeout=1)
            device.running = True
            device.receive_thread = threading.Thread(target=self._receive_data, args=(device,), daemon=True)
            device.receive_thread.start()
            if self.status_callback:
                self.status_callback(f"{device_name} Conectado")
            print(f"Conexión establecida con {device_name}")
            return True
        except Exception as e:
            print(f"Error abriendo puerto serial para {device_name}: {e}")
            return False

    def disconnect_device(self, device_name: str):
        """Disconnect a specific device"""
        if device_name not in self.devices:
            return
        
        device = self.devices[device_name]
        device.running = False
        if device.serial_conn and device.serial_conn.is_open:
            device.serial_conn.close()
        subprocess.run(["sudo", "rfcomm", "release", str(device.rfcomm_port)], capture_output=True)
        if self.status_callback:
            self.status_callback(f"{device_name} Desconectado")
        print(f"Conexión cerrada con {device_name}")

    def connect(self) -> bool:
        """Connect to HeartRate device (for backward compatibility)"""
        return self.connect_device("HeartRate_Wearable")

    def disconnect(self):
        """Disconnect all devices"""
        for device_name in list(self.devices.keys()):
            self.disconnect_device(device_name)

    def _receive_data(self, device: BluetoothDevice):
        """Receive data from a specific device"""
        while device.running:
            try:
                if device.serial_conn.in_waiting:
                    line = device.serial_conn.readline().decode().strip()
                    if line:
                        print(f"Datos recibidos de {device.name}: {line}")
                        if self.data_callback:
                            # Add device name to the data
                            self.data_callback(f"{device.name}:{line}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error recibiendo datos de {device.name}: {e}")
                device.running = False
                break

    def send_command(self, command: str, device_name: str = "HeartRate_Wearable") -> bool:
        """Send command to a specific device"""
        if device_name not in self.devices:
            print(f"Dispositivo {device_name} no está conectado")
            return False
        
        device = self.devices[device_name]
        if not device.serial_conn or not device.serial_conn.is_open:
            print(f"Puerto serial de {device_name} no está abierto")
            return False
        try:
            if not command.endswith("\n"):
                command += "\n"
            device.serial_conn.write(command.encode())
            print(f"Comando enviado a {device_name}: {command.strip()}")
            return True
        except Exception as e:
            print(f"Error enviando comando a {device_name}: {e}")
            return False

    def is_connected(self, device_name: str = "HeartRate_Wearable") -> bool:
        """Check if a specific device is connected"""
        if device_name not in self.devices:
            return False
        device = self.devices[device_name]
        return device.serial_conn and device.serial_conn.is_open

    def get_connected_devices(self) -> list:
        """Get list of connected devices"""
        connected = []
        for device_name, device in self.devices.items():
            if device.serial_conn and device.serial_conn.is_open:
                connected.append(device_name)
        return connected
