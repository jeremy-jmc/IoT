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
        self.root.title("Heart Rate Monitor")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')
        
        # Variables de datos
        self.current_bpm = 0
        self.connection_status = "Desconectado"
        self.device_status = "Esperando..."
        self.bpm_history = collections.deque(maxlen=50)  # Últimas 50 lecturas
        self.time_history = collections.deque(maxlen=50)
        
        # Bluetooth manager
        self.bt_manager = BluetoothManager()
        self.bt_manager.set_callbacks(self.on_data_received, self.on_status_changed)
        
        # Configurar estilos
        self.setup_styles()
        
        # Crear interfaz
        self.create_interface()
        
        # Variables para el gráfico
        self.setup_plot()
        
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
        
        style.configure('Modern.TButton',
                       font=('Arial', 12, 'bold'),
                       foreground='#ffffff')
        
    def create_interface(self):
        """Crear la interfaz de usuario"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(main_frame, text="❤️ Monitor de Ritmo Cardíaco", style='Title.TLabel')
        title_label.pack(pady=(0, 10))
        
        # Frame superior para información principal
        info_frame = tk.Frame(main_frame, bg='#2d2d2d', relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # BPM Display
        bpm_frame = tk.Frame(info_frame, bg='#2d2d2d')
        bpm_frame.pack(pady=20)
        
        ttk.Label(bpm_frame, text="Ritmo Cardíaco", style='Subtitle.TLabel').pack()
        self.bpm_label = ttk.Label(bpm_frame, text="-- BPM", style='BPM.TLabel')
        self.bpm_label.pack(pady=(5, 0))
        
        # Estado del dispositivo
        status_frame = tk.Frame(info_frame, bg='#2d2d2d')
        status_frame.pack(pady=(0, 20))
        
        self.device_status_label = ttk.Label(status_frame, text="Estado: Esperando...", style='Status.TLabel')
        self.device_status_label.pack()
        
        # Frame para controles
        control_frame = tk.Frame(main_frame, bg='#1e1e1e')
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Botones de control
        button_frame = tk.Frame(control_frame, bg='#1e1e1e')
        button_frame.pack()
        
        self.connect_btn = tk.Button(button_frame, text="🔗 Conectar", 
                                   command=self.toggle_connection,
                                   bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
                                   padx=20, pady=10, relief=tk.FLAT)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.ping_btn = tk.Button(button_frame, text="📡 Ping", 
                                command=self.send_ping,
                                bg='#2196F3', fg='white', font=('Arial', 12, 'bold'),
                                padx=20, pady=10, relief=tk.FLAT, state=tk.DISABLED)
        self.ping_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_btn = tk.Button(button_frame, text="📊 Estado", 
                                  command=self.request_status,
                                  bg='#FF9800', fg='white', font=('Arial', 12, 'bold'),
                                  padx=20, pady=10, relief=tk.FLAT, state=tk.DISABLED)
        self.status_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.reset_btn = tk.Button(button_frame, text="🔄 Reset Sensor", 
                                 command=self.reset_sensor,
                                 bg='#f44336', fg='white', font=('Arial', 12, 'bold'),
                                 padx=20, pady=10, relief=tk.FLAT, state=tk.DISABLED)
        self.reset_btn.pack(side=tk.LEFT)
        
        # Estado de conexión
        self.connection_label = ttk.Label(control_frame, text="🔴 Desconectado", style='Status.TLabel')
        self.connection_label.pack(pady=(10, 0))
        
        # Frame para el gráfico
        self.plot_frame = tk.Frame(main_frame, bg='#1e1e1e')
        self.plot_frame.pack(fill=tk.BOTH, expand=True)
        
    def setup_plot(self):
        """Configurar el gráfico de ritmo cardíaco"""
        # Configurar matplotlib para tema oscuro
        plt.style.use('dark_background')
        
        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor='#1e1e1e')
        self.ax.set_facecolor('#2d2d2d')
        self.ax.set_title('Historial de Ritmo Cardíaco', color='white', fontsize=14, fontweight='bold')
        self.ax.set_xlabel('Tiempo (s)', color='white')
        self.ax.set_ylabel('BPM', color='white')
        self.ax.grid(True, alpha=0.3)
        self.ax.tick_params(colors='white')
        
        # Línea del gráfico
        self.line, = self.ax.plot([], [], color='#ff4757', linewidth=2, marker='o', markersize=4)
        
        # Canvas para tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configurar límites iniciales
        self.ax.set_xlim(0, 50)
        self.ax.set_ylim(50, 120)
        
    def update_plot(self):
        """Actualizar el gráfico con nuevos datos"""
        if len(self.time_history) > 1:
            # Convertir tiempo a segundos relativos
            times = [t - self.start_time for t in self.time_history]
            
            self.line.set_data(times, list(self.bpm_history))
            
            # Ajustar límites del eje X
            if times:
                self.ax.set_xlim(max(0, times[-1] - 50), times[-1] + 5)
            
            # Ajustar límites del eje Y
            if self.bpm_history:
                min_bpm = min(self.bpm_history)
                max_bpm = max(self.bpm_history)
                margin = (max_bpm - min_bpm) * 0.1 or 10
                self.ax.set_ylim(max(30, min_bpm - margin), min(200, max_bpm + margin))
        
        self.canvas.draw()
        
    def toggle_connection(self):
        """Alternar conexión Bluetooth"""
        if self.bt_manager.is_connected():
            self.disconnect_device()
        else:
            self.connect_device()
    
    def connect_device(self):
        """Conectar al dispositivo en un hilo separado"""
        def connect_thread():
            # Disable all control buttons during connection
            self.root.after(0, lambda: self.set_buttons_state(False))
            
            success = self.bt_manager.connect()
            self.root.after(0, lambda: self.on_connection_result(success))
        
        self.connect_btn.config(text="⏳ Conectando...", state=tk.DISABLED)
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def set_buttons_state(self, connected: bool):
        """Configurar estado de los botones según la conexión"""
        if connected:
            self.connect_btn.config(text="🔌 Desconectar", state=tk.NORMAL, bg='#f44336')
            self.ping_btn.config(state=tk.NORMAL)
            self.status_btn.config(state=tk.NORMAL)
            self.reset_btn.config(state=tk.NORMAL)
        else:
            self.connect_btn.config(text="🔗 Conectar", state=tk.NORMAL, bg='#4CAF50')
            self.ping_btn.config(state=tk.DISABLED)
            self.status_btn.config(state=tk.DISABLED)
            self.reset_btn.config(state=tk.DISABLED)
    
    def disconnect_device(self):
        """Desconectar del dispositivo"""
        self.bt_manager.disconnect()
        self.on_connection_result(False)
    
    def on_connection_result(self, success):
        """Manejar resultado de conexión"""
        if success:
            self.set_buttons_state(True)
            self.connection_label.config(text="🟢 Conectado")
        else:
            self.set_buttons_state(False)
            self.connection_label.config(text="🔴 Desconectado")
    
    def send_ping(self):
        """Enviar ping al dispositivo"""
        self.bt_manager.send_command("PING")
    
    def request_status(self):
        """Solicitar estado del dispositivo"""
        self.bt_manager.send_command("STATUS")
    
    def reset_sensor(self):
        """Resetear el sensor"""
        self.bt_manager.send_command("RESET_SENSOR")
    
    def on_data_received(self, data):
        """Callback para datos recibidos"""
        self.root.after(0, lambda: self._process_data(data))
    
    def _process_data(self, data):
        """Procesar datos recibidos en el hilo principal"""
        try:
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
                
        except Exception as e:
            print(f"Error procesando datos: {e}")
    
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