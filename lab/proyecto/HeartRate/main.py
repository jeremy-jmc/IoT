import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import collections
from bluetooth_manager import *

class HeartRateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Device Health Monitor")
        self.root.geometry("1600x1000")  # Ventana aún más grande para gráficos grandes
        self.root.configure(bg='#1e1e1e')
        
        # Variables de datos para Heart Rate
        self.current_bpm = 0
        self.connection_status = "Desconectado"
        self.device_status = "Esperando..."
        self.bpm_history = collections.deque(maxlen=50)  # Últimas 50 lecturas
        self.time_history = collections.deque(maxlen=50)
        
        # Variables de datos para Posture Monitor
        self.current_ax = 0  # Valor AX actual (desviación de postura)
        self.posture_status = "Esperando..."
        self.ax_history = collections.deque(maxlen=300)  # Últimas 300 lecturas AX (5 minutos)
        self.ax_time_history = collections.deque(maxlen=300)
        
        # Métricas calculadas de postura
        self.avg_deviation = 0  # Desviación promedio
        self.max_deviation = 0  # Desviación máxima
        self.posture_stability = 0  # Estabilidad de postura (varianza inversa)
        self.poor_posture_time = 0  # Tiempo con mala postura (en segundos)
        self.poor_posture_percentage = 0  # Porcentaje de tiempo con mala postura
        self.posture_threshold = 5  # Umbral para considerar mala postura (grados)
        self.good_posture_streak = 0  # Racha actual de buena postura (segundos)
        self.poor_posture_episodes = 0  # Número de episodios de mala postura
        
        # Historial para analíticas de postura (últimos 5 minutos)
        self.poor_posture_trend = collections.deque(maxlen=60)  # Porcentaje de mala postura por minuto
        self.trend_time_history = collections.deque(maxlen=60)
        
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
        
        # Inicializar tendencia con un punto inicial
        self.poor_posture_trend.append(0)
        self.trend_time_history.append(self.start_time)
        
    def setup_styles(self):
        """Configurar estilos para una UI moderna"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores
        style.configure('Title.TLabel', 
                       font=('Arial', 18, 'bold'),
                       foreground='#ffffff',
                       background='#1e1e1e')
        
        style.configure('Subtitle.TLabel',
                       font=('Arial', 12),
                       foreground='#cccccc',
                       background='#1e1e1e')
        
        style.configure('BPM.TLabel',
                       font=('Arial', 32, 'bold'),
                       foreground='#ff4757',
                       background='#2d2d2d')
        
        style.configure('Status.TLabel',
                       font=('Arial', 10),
                       foreground='#70a1ff',
                       background='#1e1e1e')
        
        style.configure('Posture.TLabel',
                       font=('Arial', 24, 'bold'),
                       foreground='#00d2d3',
                       background='#2d2d2d')
        
        style.configure('Deviation.TLabel',
                       font=('Arial', 24, 'bold'),
                       foreground='#ff9ff3',
                       background='#2d2d2d')
        
        style.configure('Analytics.TLabel',
                       font=('Arial', 16, 'bold'),
                       foreground='#feca57',
                       background='#2d2d2d')
        
        style.configure('Warning.TLabel',
                       font=('Arial', 12, 'bold'),
                       foreground='#ff6b6b',
                       background='#2d2d2d')
        
        style.configure('Good.TLabel',
                       font=('Arial', 12, 'bold'),
                       foreground='#4ecdc4',
                       background='#2d2d2d')
        
    def create_interface(self):
        """Crear la interfaz de usuario"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Título
        title_label = ttk.Label(main_frame, text="❤️ Multi-Device Health Monitor", style='Title.TLabel')
        title_label.pack(pady=(0, 5))
        
        # Frame superior para información principal - dos columnas (más compacto)
        info_frame = tk.Frame(main_frame, bg='#1e1e1e')
        info_frame.pack(fill=tk.X, pady=(0, 8))  # Menos padding vertical
        
        # Frame izquierdo - Heart Rate
        heart_frame = tk.Frame(info_frame, bg='#2d2d2d', relief=tk.RAISED, bd=1)
        heart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        
        # BPM Display
        bpm_frame = tk.Frame(heart_frame, bg='#2d2d2d')
        bpm_frame.pack(pady=8)  # Menos padding
        
        ttk.Label(bpm_frame, text="Ritmo Cardíaco", style='Subtitle.TLabel').pack()
        self.bpm_label = ttk.Label(bpm_frame, text="-- BPM", style='BPM.TLabel')
        self.bpm_label.pack(pady=(2, 0))  # Menos padding
        
        # Estado del dispositivo Heart Rate
        status_frame = tk.Frame(heart_frame, bg='#2d2d2d')
        status_frame.pack(pady=(0, 5))  # Menos padding
        
        self.device_status_label = ttk.Label(status_frame, text="Estado: Esperando...", style='Status.TLabel')
        self.device_status_label.pack()
        
        # Frame derecho - Posture Monitor
        posture_frame = tk.Frame(info_frame, bg='#2d2d2d', relief=tk.RAISED, bd=1)
        posture_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Posture Display
        posture_display_frame = tk.Frame(posture_frame, bg='#2d2d2d')
        posture_display_frame.pack(pady=8)  # Menos padding
        
        ttk.Label(posture_display_frame, text="Monitor de Postura", style='Subtitle.TLabel').pack()
        self.posture_label = ttk.Label(posture_display_frame, text="AX: 0°", style='Posture.TLabel')
        self.posture_label.pack(pady=(2, 0))  # Menos padding
        
        # Métricas de postura
        metrics_frame = tk.Frame(posture_display_frame, bg='#2d2d2d')
        metrics_frame.pack(pady=(5, 0))
        
        # Primera fila de métricas
        metrics_row1 = tk.Frame(metrics_frame, bg='#2d2d2d')
        metrics_row1.pack(fill=tk.X, pady=(0, 3))
        
        self.avg_deviation_label = ttk.Label(metrics_row1, text="Promedio: 0°", style='Status.TLabel')
        self.avg_deviation_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stability_label = ttk.Label(metrics_row1, text="Estabilidad: 0%", style='Status.TLabel')
        self.stability_label.pack(side=tk.LEFT)
        
        # Segunda fila - Poor Posture Analytics
        metrics_row2 = tk.Frame(metrics_frame, bg='#2d2d2d')
        metrics_row2.pack(fill=tk.X, pady=(0, 3))
        
        self.poor_posture_label = ttk.Label(metrics_row2, text="Mala postura: 0s", style='Warning.TLabel')
        self.poor_posture_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.posture_percentage_label = ttk.Label(metrics_row2, text="0% tiempo", style='Analytics.TLabel')
        self.posture_percentage_label.pack(side=tk.LEFT)
        
        # Tercera fila - Streaks y episodios
        metrics_row3 = tk.Frame(metrics_frame, bg='#2d2d2d')
        metrics_row3.pack(fill=tk.X)
        
        self.good_streak_label = ttk.Label(metrics_row3, text="Buena postura: 0s", style='Good.TLabel')
        self.good_streak_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.episodes_label = ttk.Label(metrics_row3, text="Episodios: 0", style='Status.TLabel')
        self.episodes_label.pack(side=tk.LEFT)
        
        # Estado del dispositivo Posture
        posture_status_frame = tk.Frame(posture_frame, bg='#2d2d2d')
        posture_status_frame.pack(pady=(0, 5))  # Menos padding
        
        self.posture_device_status_label = ttk.Label(posture_status_frame, text="Estado: Esperando...", style='Status.TLabel')
        self.posture_device_status_label.pack()
        
        # Frame para controles
        control_frame = tk.Frame(main_frame, bg='#1e1e1e')
        control_frame.pack(fill=tk.X, pady=(0, 8))  # Menos padding
        
        # Botones de control - Heart Rate
        button_frame1 = tk.Frame(control_frame, bg='#1e1e1e')
        button_frame1.pack(pady=(0, 5))
        
        ttk.Label(button_frame1, text="❤️ Heart Rate Controls:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        self.connect_btn = tk.Button(button_frame1, text="🔗 Conectar HR", 
                                   command=self.toggle_heart_rate_connection,
                                   bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'),
                                   padx=10, pady=5, relief=tk.FLAT)
        self.connect_btn.pack(side=tk.LEFT, padx=(15, 8))
        
        self.ping_btn = tk.Button(button_frame1, text="📡 Ping", 
                                command=self.send_ping,
                                bg='#2196F3', fg='white', font=('Arial', 9, 'bold'),
                                padx=10, pady=5, relief=tk.FLAT, state=tk.DISABLED)
        self.ping_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.status_btn = tk.Button(button_frame1, text="📊 Estado", 
                                  command=self.request_status,
                                  bg='#FF9800', fg='white', font=('Arial', 9, 'bold'),
                                  padx=10, pady=5, relief=tk.FLAT, state=tk.DISABLED)
        self.status_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Botones de control - Posture Monitor
        button_frame2 = tk.Frame(control_frame, bg='#1e1e1e')
        button_frame2.pack(pady=(0, 5))
        
        ttk.Label(button_frame2, text="🧍 Posture Monitor Controls:", style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        self.connect_posture_btn = tk.Button(button_frame2, text="🔗 Conectar Postura", 
                                           command=self.toggle_posture_connection,
                                           bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'),
                                           padx=10, pady=5, relief=tk.FLAT)
        self.connect_posture_btn.pack(side=tk.LEFT, padx=(15, 8))
        
        self.calibrate_btn = tk.Button(button_frame2, text="⚖️ Calibrar", 
                                     command=self.calibrate_posture,
                                     bg='#9C27B0', fg='white', font=('Arial', 9, 'bold'),
                                     padx=10, pady=5, relief=tk.FLAT, state=tk.DISABLED)
        self.calibrate_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Estado de conexión
        connection_status_frame = tk.Frame(control_frame, bg='#1e1e1e')
        connection_status_frame.pack()
        
        self.hr_connection_label = ttk.Label(connection_status_frame, text="❤️ HR: 🔴 Desconectado", style='Status.TLabel')
        self.hr_connection_label.pack(side=tk.LEFT, padx=(0, 15))
        
        self.posture_connection_label = ttk.Label(connection_status_frame, text="🧍 Postura: 🔴 Desconectado", style='Status.TLabel')
        self.posture_connection_label.pack(side=tk.LEFT)
        
        # Frame para los gráficos
        self.plot_frame = tk.Frame(main_frame, bg='#1e1e1e')
        self.plot_frame.pack(fill=tk.BOTH, expand=True)
        
    def setup_plots(self):
        """Configurar los gráficos"""
        # Configurar matplotlib para tema oscuro
        plt.style.use('dark_background')
        
        # Crear figura con layout responsivo - tamaño más grande
        self.fig = plt.figure(figsize=(18, 12), facecolor='#1e1e1e')
        
        # Crear grid layout: Heart Rate arriba izquierda, Postura arriba derecha, Analytics abajo (span completo)
        # Aumentar hspace para evitar superposición entre los gráficos
        gs = self.fig.add_gridspec(2, 2, hspace=0.5, wspace=0.2, 
                                   height_ratios=[1.3, 1], width_ratios=[1, 1])
        
        # Configurar gráfico de BPM (arriba izquierda)
        self.ax1 = self.fig.add_subplot(gs[0, 0])
        self.ax1.set_facecolor('#2d2d2d')
        self.ax1.set_title('📈 Ritmo Cardíaco', color='white', fontsize=14, fontweight='bold', pad=5)
        self.ax1.set_xlabel('Tiempo (s)', color='white', fontsize=11, labelpad=5)
        self.ax1.set_ylabel('BPM', color='white', fontsize=11, labelpad=5)
        self.ax1.grid(True, alpha=0.3, linewidth=0.5)
        self.ax1.tick_params(colors='white', labelsize=10)
        
        # Línea del gráfico BPM
        self.line1, = self.ax1.plot([], [], color='#ff4757', linewidth=2.5, marker='o', markersize=3)
        
        # Configurar gráfico de Postura (arriba derecha)
        self.ax2 = self.fig.add_subplot(gs[0, 1])
        self.ax2.set_facecolor('#2d2d2d')
        self.ax2.set_title('🧍 Desviación de Postura', color='white', fontsize=14, fontweight='bold', pad=5)
        self.ax2.set_xlabel('Tiempo (s)', color='white', fontsize=11, labelpad=5)
        self.ax2.set_ylabel('Ángulo (°)', color='white', fontsize=11, labelpad=5)
        self.ax2.grid(True, alpha=0.3, linewidth=0.5)
        self.ax2.tick_params(colors='white', labelsize=10)
        
        # Línea del gráfico de Postura
        self.line2, = self.ax2.plot([], [], color='#00d2d3', linewidth=2.5, marker='o', markersize=3)
        
        # Líneas de referencia para postura
        self.ax2.axhline(y=0, color='green', linestyle='--', alpha=0.7, linewidth=2, label='Postura ideal')
        self.ax2.axhline(y=self.posture_threshold, color='red', linestyle='--', alpha=0.6, linewidth=1.5, label=f'Umbral ±{self.posture_threshold}°')
        self.ax2.axhline(y=-self.posture_threshold, color='red', linestyle='--', alpha=0.6, linewidth=1.5)
        self.ax2.legend(loc='upper right', fontsize=8, framealpha=0.7)
        
        # Configurar gráfico de Poor Posture Analytics (abajo, span completo)
        self.ax3 = self.fig.add_subplot(gs[1, :])
        self.ax3.set_facecolor('#2d2d2d')
        self.ax3.set_title('📊 Análisis de Mala Postura - Tendencia Temporal', color='white', fontsize=14, fontweight='bold', pad=10)
        self.ax3.set_xlabel('Tiempo (minutos)', color='white', fontsize=11, labelpad=5)
        self.ax3.set_ylabel('% Mala Postura', color='white', fontsize=11, labelpad=5)
        self.ax3.grid(True, alpha=0.3, linewidth=0.5)
        self.ax3.tick_params(colors='white', labelsize=10)
        
        # Línea del gráfico de tendencia de mala postura con área sombreada
        self.line3, = self.ax3.plot([], [], color='#feca57', linewidth=3, marker='s', markersize=4, label='% Mala Postura')
        
        # Líneas de referencia con mejor estilo
        self.ax3.axhline(y=20, color='orange', linestyle='--', alpha=0.8, linewidth=2.5, label='⚠️ Umbral de alerta (20%)')
        self.ax3.axhline(y=50, color='red', linestyle='--', alpha=0.8, linewidth=2.5, label='🚨 Crítico (50%)')
        self.ax3.axhline(y=10, color='green', linestyle='--', alpha=0.6, linewidth=2, label='✅ Bueno (<10%)')
        self.ax3.legend(loc='upper left', fontsize=9, framealpha=0.7)
        
        # Ajustar espaciado y márgenes con más espacio
        plt.tight_layout(pad=4.0)
        
        # Canvas para tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configurar límites iniciales
        self.ax1.set_xlim(0, 50)
        self.ax1.set_ylim(50, 120)
        
        self.ax2.set_xlim(0, 50)
        self.ax2.set_ylim(-45, 45)  # Rango más amplio para desviación de postura
        
        self.ax3.set_xlim(0, 60)  # 60 minutos
        self.ax3.set_ylim(0, 80)  # 0-80% de mala postura para dar más espacio
        
        # Inicializar área sombreada inicial
        self.filled_areas = []
        
    def update_plot(self):
        """Actualizar los gráficos con nuevos datos"""
        # Actualizar gráfico de BPM
        if len(self.time_history) > 1:
            times = [t - self.start_time for t in self.time_history]
            self.line1.set_data(times, list(self.bpm_history))
            
            # Ajustar límites del eje X para BPM con mejor margen
            if times:
                self.ax1.set_xlim(max(0, times[-1] - 30), times[-1] + 3)
            
            # Ajustar límites del eje Y para BPM con mejor escalado
            if self.bpm_history:
                min_bpm = min(self.bpm_history)
                max_bpm = max(self.bpm_history)
                margin = max(10, (max_bpm - min_bpm) * 0.15)
                self.ax1.set_ylim(max(40, min_bpm - margin), min(180, max_bpm + margin))
        
        # Actualizar gráfico de Postura (AX)
        if len(self.ax_time_history) > 1:
            ax_times = [t - self.start_time for t in self.ax_time_history]
            self.line2.set_data(ax_times, list(self.ax_history))
            
            # Ajustar límites del eje X para Postura con mejor margen
            if ax_times:
                self.ax2.set_xlim(max(0, ax_times[-1] - 30), ax_times[-1] + 3)
            
            # Ajustar límites del eje Y para Postura con escalado inteligente
            if self.ax_history:
                min_ax = min(self.ax_history)
                max_ax = max(self.ax_history)
                margin = max(3, (max_ax - min_ax) * 0.2)
                y_min = min(min_ax - margin, -self.posture_threshold - 5)
                y_max = max(max_ax + margin, self.posture_threshold + 5)
                self.ax2.set_ylim(y_min, y_max)
        
        # Actualizar gráfico de Poor Posture Analytics con área sombreada
        if len(self.trend_time_history) > 0:
            trend_times = [(t - self.start_time) / 60 for t in self.trend_time_history]  # Convertir a minutos
            trend_values = list(self.poor_posture_trend)
            
            self.line3.set_data(trend_times, trend_values)
            
            # Limpiar áreas sombreadas anteriores
            for collection in self.ax3.collections:
                collection.remove()
            
            # Agregar área sombreada debajo de la línea
            if len(trend_times) > 1:
                self.ax3.fill_between(trend_times, 0, trend_values, alpha=0.3, color='#feca57', label='Área de mala postura')
                
                # Agregar área sombreada para zonas críticas
                critical_values = [max(0, min(v, 100)) for v in trend_values]
                warning_mask = [v >= 20 for v in critical_values]
                critical_mask = [v >= 50 for v in critical_values]
                
                if any(warning_mask):
                    warning_fill = [v if warning_mask[i] else 0 for i, v in enumerate(critical_values)]
                    self.ax3.fill_between(trend_times, 0, warning_fill, alpha=0.2, color='orange')
                    
                if any(critical_mask):
                    critical_fill = [v if critical_mask[i] else 0 for i, v in enumerate(critical_values)]
                    self.ax3.fill_between(trend_times, 0, critical_fill, alpha=0.3, color='red')
            
            # Ajustar límites del eje X para Analytics con mejor vista
            if trend_times:
                self.ax3.set_xlim(max(0, trend_times[-1] - 45), trend_times[-1] + 3)
            
            # Ajustar límites del eje Y para Analytics dinámicamente
            if self.poor_posture_trend:
                max_percentage = max(self.poor_posture_trend)
                self.ax3.set_ylim(0, max(60, max_percentage + 15))
        
        # Redraw con mejor performance
        self.canvas.draw_idle()
        
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
        if data.startswith("AX:"):
            # Formato: AX:valor_desviacion
            parts = data.split(":")
            if len(parts) >= 2:
                try:
                    ax_value = float(parts[1])
                    self._update_posture_display(ax_value)
                except ValueError:
                    print(f"Error parseando valor AX: {parts[1]}")
    
        # Nueva lógica para manejar valores numéricos directos
        elif self._is_numeric(data):
            try:
                ax_value = float(data)
                self._update_posture_display(ax_value)
            except ValueError:
                print(f"Error parseando valor numérico: {data}")
                
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
            
            self.posture_device_status_label.config(text=f"Estado: {self.posture_status}")
            
        elif data == "CALIBRATE_OK":
            self.posture_status = "Calibración completada"
            self.posture_device_status_label.config(text=f"Estado: {self.posture_status}")
            
        elif data.startswith("ERROR:"):
            self.posture_status = data
            self.posture_device_status_label.config(text=f"Estado: {self.posture_status}")
    
    def _is_numeric(self, value):
        """Verificar si un string es numérico"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def _update_posture_display(self, ax_value):
        """Actualizar la visualización de postura con un nuevo valor AX"""
        # Multiplicar por 100 el valor recibido del PostureMonitor
        ax_value = ax_value * 100
        
        self.current_ax = ax_value
        
        # Actualizar label principal
        self.posture_label.config(text=f"AX: {ax_value:.1f}°")
        
        # Agregar al historial
        current_time = time.time()
        self.ax_history.append(ax_value)
        self.ax_time_history.append(current_time)
        
        # Calcular métricas de postura
        self._calculate_posture_metrics()
        
        # Actualizar labels de métricas
        self._update_posture_metrics_labels()
        
        # Actualizar gráfico
        self.update_plot()
        
        self.posture_status = "Monitoreando"
        self.posture_device_status_label.config(text=f"Estado: {self.posture_status}")
    
    def _calculate_posture_metrics(self):
        """Calcular métricas de postura basadas en el historial de AX"""
        if len(self.ax_history) == 0:
            return
        
        # Desviación promedio
        self.avg_deviation = sum(abs(ax) for ax in self.ax_history) / len(self.ax_history)
        
        # Desviación máxima
        self.max_deviation = max(abs(ax) for ax in self.ax_history)
        
        # Estabilidad de postura (basada en la varianza inversa)
        if len(self.ax_history) > 1:
            variance = sum((ax - sum(self.ax_history)/len(self.ax_history))**2 for ax in self.ax_history) / len(self.ax_history)
            self.posture_stability = max(0, 100 - (variance / 10) * 100)  # Escala de 0-100%
        else:
            self.posture_stability = 100
        
        # Tiempo con mala postura (últimos 60 segundos)
        current_time = time.time()
        poor_posture_count = 0
        total_samples_60s = 0
        
        for i, ax_time in enumerate(self.ax_time_history):
            if current_time - ax_time <= 60:  # Últimos 60 segundos
                total_samples_60s += 1
                if abs(self.ax_history[i]) > self.posture_threshold:
                    poor_posture_count += 1
        
        # Tiempo con mala postura (estimando ~1 muestra por segundo)
        self.poor_posture_time = poor_posture_count
        
        # Porcentaje de tiempo con mala postura
        if total_samples_60s > 0:
            self.poor_posture_percentage = (poor_posture_count / total_samples_60s) * 100
        else:
            self.poor_posture_percentage = 0
            
        # Calcular racha de buena postura (últimas N muestras consecutivas)
        consecutive_good = 0
        for i in range(len(self.ax_history) - 1, -1, -1):
            if abs(self.ax_history[i]) <= self.posture_threshold:
                consecutive_good += 1
            else:
                break
        self.good_posture_streak = consecutive_good
        
        # Contar episodios de mala postura (cambios de buena a mala postura)
        episodes = 0
        in_poor_posture = False
        for ax_value in self.ax_history:
            is_poor = abs(ax_value) > self.posture_threshold
            if is_poor and not in_poor_posture:
                episodes += 1
                in_poor_posture = True
            elif not is_poor:
                in_poor_posture = False
        self.poor_posture_episodes = episodes
        
        # Actualizar tendencia por minuto (cada 30 muestras para mayor responsividad)
        if len(self.ax_history) % 30 == 0 and len(self.ax_history) > 30:
            self._update_minute_trend()
    
    def _update_minute_trend(self):
        """Actualizar la tendencia de mala postura por minuto"""
        if len(self.ax_history) < 30:
            return
            
        # Tomar las últimas 30-60 muestras (último período)
        sample_size = min(60, len(self.ax_history))
        last_samples = list(self.ax_history)[-sample_size:]
        poor_count = sum(1 for ax in last_samples if abs(ax) > self.posture_threshold)
        percentage = (poor_count / sample_size) * 100
        
        # Agregar al historial de tendencias
        self.poor_posture_trend.append(percentage)
        self.trend_time_history.append(time.time())
    
    def _update_posture_metrics_labels(self):
        """Actualizar las etiquetas de métricas de postura"""
        self.avg_deviation_label.config(text=f"Promedio: {self.avg_deviation:.1f}°")
        self.stability_label.config(text=f"Estabilidad: {self.posture_stability:.1f}%")
        
        # Color coding para el porcentaje de mala postura
        if self.poor_posture_percentage <= 10:
            percentage_color = 'Good.TLabel'
        elif self.poor_posture_percentage <= 30:
            percentage_color = 'Analytics.TLabel'
        else:
            percentage_color = 'Warning.TLabel'
            
        self.poor_posture_label.config(text=f"Mala postura: {self.poor_posture_time}s")
        self.posture_percentage_label.config(text=f"{self.poor_posture_percentage:.1f}% tiempo", style=percentage_color)
        self.good_streak_label.config(text=f"Buena postura: {self.good_posture_streak}s")
        self.episodes_label.config(text=f"Episodios: {self.poor_posture_episodes}")
    
    def on_status_changed(self, status):
        """Callback para cambios de estado de conexión"""
        self.root.after(0, lambda: self._update_connection_status(status))
    
    def _update_connection_status(self, status):
        """Actualizar estado de conexión en el hilo principal"""
        self.connection_status = status
        
        # Update the appropriate connection label based on device type
        if "HeartRate_Wearable" in status:
            if "Conectado" in status:
                self.hr_connection_label.config(text="❤️ HR: 🟢 Conectado")
            elif "Error" in status:
                self.hr_connection_label.config(text="❤️ HR: 🔴 Error")
            else:
                self.hr_connection_label.config(text="❤️ HR: 🟡 " + status)
        elif "PostureMonitor" in status:
            if "Conectado" in status:
                self.posture_connection_label.config(text="🧍 Postura: 🟢 Conectado")
            elif "Error" in status:
                self.posture_connection_label.config(text="🧍 Postura: 🔴 Error")
            else:
                self.posture_connection_label.config(text="🧍 Postura: 🟡 " + status)
    
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
