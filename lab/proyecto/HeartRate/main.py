import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import collections
from bluetooth_manager import BluetoothManager


class HeartRateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Device Health Monitor")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1e1e1e')
        
        # Variables de datos para Heart Rate
        self.current_bpm = 0
        self.connection_status = "Desconectado"
        self.device_status = "Esperando..."
        self.bpm_history = collections.deque(maxlen=50)  # Últimas 50 lecturas
        self.time_history = collections.deque(maxlen=50)
        
        # Variables de datos para Posture Monitor
        self.current_posture = {"x": 0, "y": 0}
        self.posture_status = "Esperando..."
        self.posture_history = collections.deque(maxlen=50)  # Últimas 50 lecturas
        self.posture_time_history = collections.deque(maxlen=50)
        self.posture_deviation = 0  # Desviación actual respecto al centro
        
        # Bluetooth manager
        self.bt_manager = BluetoothManager()
        self.bt_manager.set_callbacks(self.on_data_received, self.on_status_changed)
        
        # Configurar estilos
        self.setup_styles()
        
        # Crear interfaz
        self.create_interface()
        
        # Variables para los gráficos
        self.setup_plots()
        
        # Inicializar datos del gráfico
        self.start_time = time.time()
        
    def setup_styles(self):
        """Configurar estilos para una UI moderna"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores
        style.configure('Title.TLabel', 
                       font=('Arial', 24, 'bold'),
                       foreground='#ffffff',
                       background='#1e1e1e')
        
        style.configure('Subtitle.TLabel',
                       font=('Arial', 14),
                       foreground='#cccccc',
                       background='#1e1e1e')
        
        style.configure('BPM.TLabel',
                       font=('Arial', 48, 'bold'),
                       foreground='#ff4757',
                       background='#2d2d2d')
        
        style.configure('Status.TLabel',
                       font=('Arial', 12),
                       foreground='#70a1ff',
                       background='#1e1e1e')
        
        style.configure('Posture.TLabel',
                       font=('Arial', 36, 'bold'),
                       foreground='#00d2d3',
                       background='#2d2d2d')
        
        style.configure('Deviation.TLabel',
                       font=('Arial', 24, 'bold'),
                       foreground='#ff9ff3',
                       background='#2d2d2d')
        
    def create_interface(self):
        """Crear la interfaz de usuario"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(main_frame, text="❤️ Multi-Device Health Monitor", style='Title.TLabel')
        title_label.pack(pady=(0, 10))
        
        # Frame superior para información principal - dos columnas
        info_frame = tk.Frame(main_frame, bg='#1e1e1e')
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Frame izquierdo - Heart Rate
        heart_frame = tk.Frame(info_frame, bg='#2d2d2d', relief=tk.RAISED, bd=2)
        heart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # BPM Display
        bpm_frame = tk.Frame(heart_frame, bg='#2d2d2d')
        bpm_frame.pack(pady=20)
        
        ttk.Label(bpm_frame, text="Ritmo Cardíaco", style='Subtitle.TLabel').pack()
        self.bpm_label = ttk.Label(bpm_frame, text="-- BPM", style='BPM.TLabel')
        self.bpm_label.pack(pady=(5, 0))
        
        # Estado del dispositivo Heart Rate
        status_frame = tk.Frame(heart_frame, bg='#2d2d2d')
        status_frame.pack(pady=(0, 20))
        
        self.device_status_label = ttk.Label(status_frame, text="Estado: Esperando...", style='Status.TLabel')
        self.device_status_label.pack()
        
        # Frame derecho - Posture Monitor
        posture_frame = tk.Frame(info_frame, bg='#2d2d2d', relief=tk.RAISED, bd=2)
        posture_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Posture Display
        posture_display_frame = tk.Frame(posture_frame, bg='#2d2d2d')
        posture_display_frame.pack(pady=20)
        
        ttk.Label(posture_display_frame, text="Monitor de Postura", style='Subtitle.TLabel').pack()
        self.posture_label = ttk.Label(posture_display_frame, text="X: 0, Y: 0", style='Posture.TLabel')
        self.posture_label.pack(pady=(5, 0))
        
        self.deviation_label = ttk.Label(posture_display_frame, text="Desviación: 0°", style='Deviation.TLabel')
        self.deviation_label.pack(pady=(5, 0))
        
        # Estado del dispositivo Posture Monitor
        posture_status_frame = tk.Frame(posture_frame, bg='#2d2d2d')
        posture_status_frame.pack(pady=(0, 20))
        
        self.posture_status_label = ttk.Label(posture_status_frame, text="Estado: Esperando...", style='Status.TLabel')
        self.posture_status_label.pack()
        
        # Frame para controles
        control_frame = tk.Frame(main_frame, bg='#1e1e1e')
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Botones de control - Heart Rate
        button_frame1 = tk.Frame(control_frame, bg='#1e1e1e')
        button_frame1.pack(pady=(0, 10))
        
        ttk.Label(button_frame1, text="❤️ Heart Rate Controls:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        self.connect_btn = tk.Button(button_frame1, text="🔗 Conectar HR", 
                                   command=self.toggle_heart_rate_connection,
                                   bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                                   padx=15, pady=8, relief=tk.FLAT)
        self.connect_btn.pack(side=tk.LEFT, padx=(20, 10))
        
        self.ping_btn = tk.Button(button_frame1, text="📡 Ping", 
                                command=self.send_ping,
                                bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                                padx=15, pady=8, relief=tk.FLAT, state=tk.DISABLED)
        self.ping_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_btn = tk.Button(button_frame1, text="📊 Estado", 
                                  command=self.request_status,
                                  bg='#FF9800', fg='white', font=('Arial', 10, 'bold'),
                                  padx=15, pady=8, relief=tk.FLAT, state=tk.DISABLED)
        self.status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botones de control - Posture Monitor
        button_frame2 = tk.Frame(control_frame, bg='#1e1e1e')
        button_frame2.pack(pady=(0, 10))
        
        ttk.Label(button_frame2, text="🧍 Posture Monitor Controls:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        self.connect_posture_btn = tk.Button(button_frame2, text="� Conectar Postura", 
                                           command=self.toggle_posture_connection,
                                           bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                                           padx=15, pady=8, relief=tk.FLAT)
        self.connect_posture_btn.pack(side=tk.LEFT, padx=(20, 10))
        
        self.calibrate_btn = tk.Button(button_frame2, text="⚖️ Calibrar", 
                                     command=self.calibrate_posture,
                                     bg='#9C27B0', fg='white', font=('Arial', 10, 'bold'),
                                     padx=15, pady=8, relief=tk.FLAT, state=tk.DISABLED)
        self.calibrate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Estado de conexión
        connection_status_frame = tk.Frame(control_frame, bg='#1e1e1e')
        connection_status_frame.pack()
        
        self.hr_connection_label = ttk.Label(connection_status_frame, text="❤️ HR: 🔴 Desconectado", style='Status.TLabel')
        self.hr_connection_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.posture_connection_label = ttk.Label(connection_status_frame, text="🧍 Postura: 🔴 Desconectado", style='Status.TLabel')
        self.posture_connection_label.pack(side=tk.LEFT)
        
        # Frame para los gráficos
        self.plot_frame = tk.Frame(main_frame, bg='#1e1e1e')
        self.plot_frame.pack(fill=tk.BOTH, expand=True)
        
    def setup_plots(self):
        """Configurar los gráficos"""
        # Configurar matplotlib para tema oscuro
        plt.style.use('dark_background')
        
        # Crear figura con dos subplots
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 6), facecolor='#1e1e1e')
        
        # Configurar gráfico de BPM
        self.ax1.set_facecolor('#2d2d2d')
        self.ax1.set_title('Historial de Ritmo Cardíaco', color='white', fontsize=12, fontweight='bold')
        self.ax1.set_xlabel('Tiempo (s)', color='white')
        self.ax1.set_ylabel('BPM', color='white')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.tick_params(colors='white')
        
        # Línea del gráfico BPM
        self.line1, = self.ax1.plot([], [], color='#ff4757', linewidth=2, marker='o', markersize=3)
        
        # Configurar gráfico de Postura
        self.ax2.set_facecolor('#2d2d2d')
        self.ax2.set_title('Historial de Desviación de Postura', color='white', fontsize=12, fontweight='bold')
        self.ax2.set_xlabel('Tiempo (s)', color='white')
        self.ax2.set_ylabel('Desviación (°)', color='white')
        self.ax2.grid(True, alpha=0.3)
        self.ax2.tick_params(colors='white')
        
        # Línea del gráfico de Postura
        self.line2, = self.ax2.plot([], [], color='#00d2d3', linewidth=2, marker='o', markersize=3)
        
        # Ajustar espaciado entre subplots
        plt.tight_layout()
        
        # Canvas para tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configurar límites iniciales
        self.ax1.set_xlim(0, 50)
        self.ax1.set_ylim(50, 120)
        
        self.ax2.set_xlim(0, 50)
        self.ax2.set_ylim(-30, 30)
        
    def update_plot(self):
        """Actualizar los gráficos con nuevos datos"""
        # Actualizar gráfico de BPM
        if len(self.time_history) > 1:
            times = [t - self.start_time for t in self.time_history]
            self.line1.set_data(times, list(self.bpm_history))
            
            # Ajustar límites del eje X para BPM
            if times:
                self.ax1.set_xlim(max(0, times[-1] - 50), times[-1] + 5)
            
            # Ajustar límites del eje Y para BPM
            if self.bpm_history:
                min_bpm = min(self.bpm_history)
                max_bpm = max(self.bpm_history)
                margin = (max_bpm - min_bpm) * 0.1 or 10
                self.ax1.set_ylim(max(30, min_bpm - margin), min(200, max_bpm + margin))
        
        # Actualizar gráfico de Postura
        if len(self.posture_time_history) > 1:
            posture_times = [t - self.start_time for t in self.posture_time_history]
            self.line2.set_data(posture_times, list(self.posture_history))
            
            # Ajustar límites del eje X para Postura
            if posture_times:
                self.ax2.set_xlim(max(0, posture_times[-1] - 50), posture_times[-1] + 5)
            
            # Ajustar límites del eje Y para Postura
            if self.posture_history:
                min_dev = min(self.posture_history)
                max_dev = max(self.posture_history)
                margin = max(5, (max_dev - min_dev) * 0.1)
                self.ax2.set_ylim(min_dev - margin, max_dev + margin)
        
        self.canvas.draw()
        
    def toggle_heart_rate_connection(self):
        """Alternar conexión del Heart Rate Monitor"""
        if self.bt_manager.is_connected("HeartRate_Wearable"):
            self.disconnect_heart_rate()
        else:
            self.connect_heart_rate()
    
    def toggle_posture_connection(self):
        """Alternar conexión del Posture Monitor"""
        if self.bt_manager.is_connected("PostureMonitor"):
            self.disconnect_posture()
        else:
            self.connect_posture()
    
    def connect_heart_rate(self):
        """Conectar al Heart Rate Monitor en un hilo separado"""
        def connect_thread():
            self.root.after(0, lambda: self.connect_btn.config(text="⏳ Conectando...", state=tk.DISABLED))
            success = self.bt_manager.connect_device("HeartRate_Wearable")
            self.root.after(0, lambda: self.on_heart_rate_connection_result(success))
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def connect_posture(self):
        """Conectar al Posture Monitor en un hilo separado"""
        def connect_thread():
            self.root.after(0, lambda: self.connect_posture_btn.config(text="⏳ Conectando...", state=tk.DISABLED))
            success = self.bt_manager.connect_device("PostureMonitor")
            self.root.after(0, lambda: self.on_posture_connection_result(success))
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def disconnect_heart_rate(self):
        """Desconectar del Heart Rate Monitor"""
        self.bt_manager.disconnect_device("HeartRate_Wearable")
        self.on_heart_rate_connection_result(False)
    
    def disconnect_posture(self):
        """Desconectar del Posture Monitor"""
        self.bt_manager.disconnect_device("PostureMonitor")
        self.on_posture_connection_result(False)
    
    def on_heart_rate_connection_result(self, success):
        """Manejar resultado de conexión del Heart Rate"""
        if success:
            self.connect_btn.config(text="🔌 Desconectar HR", state=tk.NORMAL, bg='#f44336')
            self.ping_btn.config(state=tk.NORMAL)
            self.status_btn.config(state=tk.NORMAL)
            self.hr_connection_label.config(text="❤️ HR: 🟢 Conectado")
        else:
            self.connect_btn.config(text="🔗 Conectar HR", state=tk.NORMAL, bg='#4CAF50')
            self.ping_btn.config(state=tk.DISABLED)
            self.status_btn.config(state=tk.DISABLED)
            self.hr_connection_label.config(text="❤️ HR: 🔴 Desconectado")
    
    def on_posture_connection_result(self, success):
        """Manejar resultado de conexión del Posture Monitor"""
        if success:
            self.connect_posture_btn.config(text="🔌 Desconectar Postura", state=tk.NORMAL, bg='#f44336')
            self.calibrate_btn.config(state=tk.NORMAL)
            self.posture_connection_label.config(text="🧍 Postura: 🟢 Conectado")
        else:
            self.connect_posture_btn.config(text="🔗 Conectar Postura", state=tk.NORMAL, bg='#4CAF50')
            self.calibrate_btn.config(state=tk.DISABLED)
            self.posture_connection_label.config(text="🧍 Postura: 🔴 Desconectado")
    
    def calibrate_posture(self):
        """Calibrar el monitor de postura"""
        self.bt_manager.send_command("CALIBRATE", "PostureMonitor")
    
    def send_ping(self):
        """Enviar ping al dispositivo Heart Rate"""
        self.bt_manager.send_command("PING", "HeartRate_Wearable")
    
    def request_status(self):
        """Solicitar estado del dispositivo Heart Rate"""
        self.bt_manager.send_command("STATUS", "HeartRate_Wearable")
    
    def on_data_received(self, data):
        """Callback para datos recibidos"""
        self.root.after(0, lambda: self._process_data(data))
    
    def _process_data(self, data):
        """Procesar datos recibidos en el hilo principal"""
        try:
            # Check if data includes device name prefix
            if ":" in data and data.split(":", 1)[0] in ["HeartRate_Wearable", "PostureMonitor"]:
                device_name, message = data.split(":", 1)
            else:
                # Default to HeartRate for backward compatibility
                device_name = "HeartRate_Wearable"
                message = data
            
            if device_name == "HeartRate_Wearable":
                self._process_heart_rate_data(message)
            elif device_name == "PostureMonitor":
                self._process_posture_data(message)
                
        except Exception as e:
            print(f"Error procesando datos: {e}")
    
    def _process_heart_rate_data(self, data):
        """Procesar datos del Heart Rate Monitor"""
        if data.startswith("BPM:"):
            # Formato: BPM:valor_instantaneo:valor_promedio
            parts = data.split(":")
            if len(parts) >= 2:
                bpm = int(parts[1])
                self.current_bpm = bpm
                self.bpm_label.config(text=f"{bpm} BPM")
                
                # Agregar al historial
                current_time = time.time()
                self.bpm_history.append(bpm)
                self.time_history.append(current_time)
                
                # Actualizar gráfico
                self.update_plot()
                
                self.device_status = "Midiendo"
                self.device_status_label.config(text=f"Estado: {self.device_status}")
                
        elif data.startswith("STATUS:"):
            status = data.split(":", 1)[1]
            if status == "NO_FINGER":
                self.device_status = "Coloca el dedo en el sensor"
                self.bpm_label.config(text="-- BPM")
            elif status == "MEASURING":
                self.device_status = "Midiendo..."
            elif status == "SENSOR_REINIT":
                self.device_status = "Reinicializando sensor..."
            elif status == "SENSOR_OK":
                self.device_status = "Sensor OK"
            
            self.device_status_label.config(text=f"Estado: {self.device_status}")
            
        elif data == "READY":
            self.device_status = "Listo"
            self.device_status_label.config(text=f"Estado: {self.device_status}")
            
        elif data == "PONG":
            self.device_status = "Ping exitoso"
            self.device_status_label.config(text=f"Estado: {self.device_status}")
            
        elif data.startswith("ERROR:"):
            self.device_status = data
            self.device_status_label.config(text=f"Estado: {self.device_status}")
    
    def _process_posture_data(self, data):
        """Procesar datos del Posture Monitor"""
        if data.startswith("POSTURE:"):
            # Formato: POSTURE:x:y:deviation
            parts = data.split(":")
            if len(parts) >= 4:
                x = float(parts[1])
                y = float(parts[2])
                deviation = float(parts[3])
                
                self.current_posture = {"x": x, "y": y}
                self.posture_deviation = deviation
                
                # Actualizar labels
                self.posture_label.config(text=f"X: {x:.1f}, Y: {y:.1f}")
                self.deviation_label.config(text=f"Desviación: {deviation:.1f}°")
                
                # Agregar al historial
                current_time = time.time()
                self.posture_history.append(deviation)
                self.posture_time_history.append(current_time)
                
                # Actualizar gráfico
                self.update_plot()
                
                self.posture_status = "Monitoreando"
                self.posture_status_label.config(text=f"Estado: {self.posture_status}")
                
        elif data.startswith("POSTURE_STATUS:"):
            status = data.split(":", 1)[1]
            if status == "CALIBRATED":
                self.posture_status = "Calibrado - Monitoreando"
            elif status == "CALIBRATING":
                self.posture_status = "Calibrando..."
            elif status == "UNCALIBRATED":
                self.posture_status = "Sin calibrar"
            elif status == "SENSOR_ERROR":
                self.posture_status = "Error en sensor"
            
            self.posture_status_label.config(text=f"Estado: {self.posture_status}")
            
        elif data == "CALIBRATE_OK":
            self.posture_status = "Calibración completada"
            self.posture_status_label.config(text=f"Estado: {self.posture_status}")
            
        elif data.startswith("POSTURE_ERROR:"):
            self.posture_status = data
            self.posture_status_label.config(text=f"Estado: {self.posture_status}")
    
    def on_status_changed(self, status):
        """Callback para cambios de estado de conexión"""
        self.root.after(0, lambda: self._update_connection_status(status))
    
    def _update_connection_status(self, status):
        """Actualizar estado de conexión en el hilo principal"""
        self.connection_status = status
        
        if "Conectado" in status:
            self.connection_label.config(text="🟢 " + status)
        elif "Error" in status:
            self.connection_label.config(text="🔴 " + status)
        else:
            self.connection_label.config(text="🟡 " + status)
    
    def on_closing(self):
        """Manejar cierre de la aplicación"""
        if self.bt_manager.is_connected():
            self.bt_manager.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = HeartRateApp(root)
    print("application started", root)
    
    # Manejar cierre de ventana
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Centrar ventana
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()
    print("application closed")

if __name__ == "__main__":
    main()