# interfaz_usuario.py

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkintermapview import TkinterMapView
import csv
import os
import threading
import queue
from datetime import datetime
from clases import Drone, RegistroEventos

class InterfazUsuario(tk.Tk):
    def __init__(self, queue_to_drone, queue_from_drone, registro_eventos):
        super().__init__()
        self.title("Centro de Control de Operaciones - Dron DEA")
        self.geometry("1400x900")

        # Colas para comunicarse con el dron
        self.queue_to_drone = queue_to_drone
        self.queue_from_drone = queue_from_drone

        # Referencia al registro de eventos
        self.registro_eventos = registro_eventos

        # Variables de la interfaz
        self.selected_location = tk.StringVar()
        self.drone_status = tk.StringVar(value=(
            "Estado del Dron:\n"
            "  Estado Actual: En tierra\n"
            "  Batería: 100%\n"
            "  Velocidad: 0 km/h\n"
            "  Altitud: 0 m\n"
            "  Posición: (4.627925, -74.064692)"
        ))
        self.estado_maquina = tk.StringVar(value="Estado de la Máquina de Estados: en_tierra")
        self.emergencias_registradas = []

        # Variables para manejar los casos de emergencia
        self.casos_emergencia = []
        self.indice_caso_actual = 0
        self.cargar_emergencias_desde_archivo()

        # Creamos un Lock para manejar el acceso a la interfaz desde hilos
        self.lock = threading.Lock()

        # Crear las secciones de la interfaz
        self.crear_seccion_superior()
        self.crear_seccion_izquierda()
        self.crear_seccion_central()
        self.crear_seccion_derecha()

        # Iniciar el hilo para recibir actualizaciones
        self.actualizaciones_thread = threading.Thread(target=self.recibir_actualizaciones, daemon=True)
        self.actualizaciones_thread.start()

        # Iniciar el ciclo principal de la interfaz
        self.after(1000, self.actualizar_interfaz)

    def crear_seccion_superior(self):
        self.frame_superior = tk.Frame(self, bg="darkblue", height=50)
        self.frame_superior.pack(side=tk.TOP, fill=tk.X)

        self.lbl_titulo = tk.Label(
            self.frame_superior,
            text="Centro de Control de Operaciones - Dron DEA",
            bg="darkblue",
            fg="white",
            font=("Helvetica", 18, "bold"),
        )
        self.lbl_titulo.pack(pady=10)

    def crear_seccion_izquierda(self):
        self.frame_izquierdo = tk.Frame(self, width=300, bg="lightgrey")
        self.frame_izquierdo.pack(side=tk.LEFT, fill=tk.Y)

        # Botón: Recibir llamada
        self.btn_llamada = tk.Button(
            self.frame_izquierdo,
            text="Recibir Llamada",
            bg="green",
            fg="white",
            font=("Helvetica", 12),
            command=self.recibir_llamada,
        )
        self.btn_llamada.pack(pady=10, fill=tk.X)

        # Botón: Crear emergencia
        self.btn_crear_emergencia = tk.Button(
            self.frame_izquierdo,
            text="Crear Emergencia",
            bg="orange",
            fg="black",
            font=("Helvetica", 12),
            command=self.mostrar_formulario_emergencia,
        )
        self.btn_crear_emergencia.pack(pady=10, fill=tk.X)

        # Botón: Enviar dron
        self.btn_enviar_dron = tk.Button(
            self.frame_izquierdo,
            text="Enviar Dron",
            bg="red",
            fg="white",
            font=("Helvetica", 12),
            command=self.enviar_dron,
        )
        self.btn_enviar_dron.pack(pady=10, fill=tk.X)

        # Etiqueta: Estado del Dron
        self.lbl_estado_dron = tk.Label(
            self.frame_izquierdo,
            textvariable=self.drone_status,
            bg="lightgrey",
            fg="black",
            font=("Helvetica", 12),
            justify="left",
            anchor='w'
        )
        self.lbl_estado_dron.pack(pady=10, fill=tk.X)

        # Etiqueta: Estado de la Máquina de Estados
        self.lbl_estado_maquina = tk.Label(
            self.frame_izquierdo,
            textvariable=self.estado_maquina,
            bg="lightgrey",
            fg="black",
            font=("Helvetica", 12),
            justify="left",
            anchor='w'
        )
        self.lbl_estado_maquina.pack(pady=10, fill=tk.X)

    def crear_seccion_central(self):
        self.frame_central = tk.Frame(self, bg="white")
        self.frame_central.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Mapa interactivo
        self.map_widget = TkinterMapView(self.frame_central, width=800, height=600)
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        self.map_widget.set_position(4.627925, -74.064692)  # Coordenadas iniciales
        self.map_widget.set_zoom(15)

        # Marcador del dron
        self.drone_marker = self.map_widget.set_marker(4.627925, -74.064692, text="Dron")

    def crear_seccion_derecha(self):
        self.frame_derecho = tk.Frame(self, width=300, bg="lightgrey")
        self.frame_derecho.pack(side=tk.RIGHT, fill=tk.Y)

        # Registro de eventos
        self.lbl_registro = tk.Label(
            self.frame_derecho,
            text="Registro de Eventos",
            bg="lightgrey",
            fg="black",
            font=("Helvetica", 14, "bold"),
        )
        self.lbl_registro.pack(pady=10)

        self.txt_registro = scrolledtext.ScrolledText(
            self.frame_derecho,
            width=40,
            height=30,
            font=("Helvetica", 10),
        )
        self.txt_registro.pack(pady=10)

    def recibir_llamada(self):
        if self.indice_caso_actual < len(self.casos_emergencia):
            emergencia = self.casos_emergencia[self.indice_caso_actual]
            self.indice_caso_actual += 1
            self.emergencias_registradas.append(emergencia)
            registro = (
                f"LLAMADA: {emergencia['usuario']} reporta una emergencia de tipo "
                f"'{emergencia['situacion']}' en {emergencia['ubicacion']}."
            )
            self.agregar_a_registro(registro, origen="LLAMADA")
            self.registro_eventos.agregar_evento(registro)
            # Agregar marcador en el mapa
            try:
                lat, lon = map(float, emergencia['ubicacion'].split(","))
                self.map_widget.set_marker(lat, lon, text="Emergencia")
            except ValueError:
                messagebox.showerror("Error", "La ubicación debe estar en formato 'latitud, longitud'.")
        else:
            messagebox.showinfo("Información", "No hay más emergencias en la cola.")

    def enviar_dron(self):
        if self.emergencias_registradas:
            emergencia = self.emergencias_registradas.pop(0)
            ubicacion = emergencia['ubicacion']
            registro = f"Dron enviado a la emergencia en {ubicacion}."
            self.agregar_a_registro(registro, origen="DRON")
            self.registro_eventos.agregar_evento(registro)
            # Enviar comando al dron
            comando = {
                'tipo': 'recepcion_comando_arranque_vuelo',
                'ubicacion': ubicacion
            }
            self.queue_to_drone.put(comando)
        else:
            messagebox.showwarning("Advertencia", "No hay emergencias registradas para enviar el dron.")

    def mostrar_formulario_emergencia(self):
        FormularioEmergencia(self)

    def agregar_a_registro(self, mensaje, origen="SISTEMA"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entrada = f"[{timestamp}] [{origen}] {mensaje}\n"
        self.txt_registro.insert(tk.END, entrada)
        self.txt_registro.see(tk.END)
        # Registrar en RegistroEventos
        self.registro_eventos.agregar_evento(entrada)

    def actualizar_posicion_mapa(self, posicion):
        lat, lon = posicion
        if self.drone_marker:
            self.drone_marker.set_position(lat, lon)
        else:
            self.drone_marker = self.map_widget.set_marker(lat, lon, text="Dron")

    def recibir_actualizaciones(self):
        """Hilo para recibir actualizaciones del dron y de la máquina de estados."""
        while True:
            try:
                update = self.queue_from_drone.get(timeout=1)  # Esperar hasta 1 segundo
                if update:
                    if update.get('type') == 'estado_dron':
                        # Actualizar estado interno
                        estado = update.get('data')
                        # Construir el texto con toda la información
                        estado_texto = (
                            "Estado del Dron:\n"
                            f"  Estado Actual: {estado['estado']}\n"
                            f"  Batería: {estado['bateria']}%\n"
                            f"  Velocidad: {estado['velocidad']} km/h\n"
                            f"  Altitud: {estado['altitud']} m\n"
                            f"  Posición: {estado['posicion_actual']}"
                        )
                        with self.lock:
                            self.drone_status.set(estado_texto)
                        # Actualizar marcador en el mapa
                        self.actualizar_posicion_mapa(estado['posicion_actual'])
                    elif update.get('type') == 'estado_maquina':
                        estado_maquina = update.get('data')
                        with self.lock:
                            self.estado_maquina.set(f"Estado de la Máquina de Estados: {estado_maquina}")
                    elif update.get('type') == 'evento':
                        mensaje = update.get('data')
                        self.agregar_a_registro(mensaje, origen="DRON")
                        self.registro_eventos.agregar_evento(mensaje)
            except queue.Empty:
                continue  # No hay actualizaciones, continuar esperando

    def actualizar_interfaz(self):
        # Actualizar interfaz si es necesario
        self.after(1000, self.actualizar_interfaz)

    def cargar_emergencias_desde_archivo(self):
        if os.path.exists("emergencias.txt"):
            with open("emergencias.txt", "r") as archivo:
                reader = csv.DictReader(archivo)
                self.casos_emergencia = list(reader)

class FormularioEmergencia(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Registrar Nueva Emergencia")
        self.geometry("400x300")
        self.parent = parent

        tk.Label(self, text="Usuario:", font=("Helvetica", 12)).pack(pady=5)
        self.entry_usuario = tk.Entry(self)
        self.entry_usuario.pack(fill="x", padx=10, pady=5)

        tk.Label(self, text="Situación:", font=("Helvetica", 12)).pack(pady=5)
        self.combo_situacion = ttk.Combobox(
            self,
            values=["Paro Cardíaco", "Accidente", "Incendio", "Otro"],
            state="readonly",
        )
        self.combo_situacion.pack(fill="x", padx=10, pady=5)

        tk.Label(self, text="Ubicación (Lat, Lon):", font=("Helvetica", 12)).pack(pady=5)
        self.entry_ubicacion = tk.Entry(self, textvariable=self.parent.selected_location)
        self.entry_ubicacion.pack(fill="x", padx=10, pady=5)

        btn_seleccionar_mapa = tk.Button(self, text="Seleccionar en Mapa", command=self.seleccionar_en_mapa)
        btn_seleccionar_mapa.pack(pady=5)

        tk.Button(self, text="Guardar Emergencia", command=self.guardar_emergencia).pack(pady=10)

    def seleccionar_en_mapa(self):
        messagebox.showinfo("Seleccionar en Mapa", "Seleccione una ubicación haciendo clic en el mapa.")

    def guardar_emergencia(self):
        usuario = self.entry_usuario.get()
        situacion = self.combo_situacion.get()
        ubicacion = self.entry_ubicacion.get()
        if not usuario or not situacion or not ubicacion:
            messagebox.showwarning(
                "Advertencia", "Todos los campos son obligatorios."
            )
            return
        emergencia = {
            'usuario': usuario,
            'situacion': situacion,
            'ubicacion': ubicacion
        }
        self.parent.emergencias_registradas.append(emergencia)
        registro = (
            f"{usuario} reportó una emergencia de tipo '{situacion}' en {ubicacion}."
        )
        self.parent.agregar_a_registro(registro, origen="INTERFAZ")
        self.parent.registro_eventos.agregar_evento(registro)
        self.destroy()

        # Agregar marcador de la emergencia en el mapa
        try:
            lat, lon = map(float, ubicacion.split(","))
            self.parent.map_widget.set_marker(lat, lon, text="Emergencia")
        except ValueError:
            messagebox.showerror("Error", "La ubicación debe estar en formato 'latitud, longitud'.")
