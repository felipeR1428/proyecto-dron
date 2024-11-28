# interfaz_eventos.py

import tkinter as tk
from tkinter import messagebox

class InterfazEventos(tk.Toplevel):
    def __init__(self, queue_to_drone, registro_eventos):
        super().__init__()
        self.title("Centro de Control de Operaciones - Dron DEA")
        self.geometry("600x800")
        self.queue_to_drone = queue_to_drone
        self.registro_eventos = registro_eventos

        # Lista de eventos posibles de la máquina de estados
        self.eventos = [
            'cambio_localizacion_emergencia',
            'recepcion_comando_descarga_electrica',
            'deteccion_signos_vitales_paciente',
            'deteccion_lugar_ocupado_aterrizar',
            'recepcion_comando_arranque_vuelo',
            'aviso_bateria_baja',
            'falla_motor_detectada',
            'motor_recuperado',
            'aterrizaje_forzoso',
            'regresar_base',
            'reanudar_navegacion',
            'detener_operaciones',
            'resetear_parametros',
            'vuelo_libre',
            'deteccion_obstaculo_fijo',
            'deteccion_obstaculo_movil',
            'perdida_senal_gps',
            'deteccion_alta_turbulencia',
            'deteccion_lugar_libre_aterrizaje',
            'ocupacion_lugar_aterrizaje',
        ]

        self.colores_botones = [
            'red', 'green', 'blue', 'orange', 'purple', 'brown',
            'pink', 'gray', 'cyan', 'magenta', 'yellow', 'lime', 'teal', 'navy', 'maroon', 'olive', 'silver', 'gold'
        ]

        self.crear_interfaz()

    def crear_interfaz(self):
        # Encabezado similar al de la interfaz de usuario
        self.frame_superior = tk.Frame(self, bg="darkblue", height=50)
        self.frame_superior.pack(side=tk.TOP, fill=tk.X)

        self.lbl_titulo = tk.Label(
            self.frame_superior,
            text="Centro de Control de Operaciones - Dron DEA",
            bg="darkblue",
            fg="white",
            font=("Helvetica", 16, "bold"),
        )
        self.lbl_titulo.pack(pady=10)

        tk.Label(
            self,
            text="Eventos de la Máquina de Estados",
            font=("Helvetica", 14, "bold")
        ).pack(pady=10)

        # Crear un frame para los botones
        frame_botones = tk.Frame(self)
        frame_botones.pack(pady=10, fill=tk.BOTH, expand=True)

        # Crear un canvas con scrollbar si es necesario
        canvas = tk.Canvas(frame_botones)
        scrollbar = tk.Scrollbar(frame_botones, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scroll_frame = tk.Frame(canvas)

        # Vincular el scroll
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Distribuir los botones en dos columnas
        for idx, evento in enumerate(self.eventos):
            color_boton = self.colores_botones[idx % len(self.colores_botones)]
            btn_evento = tk.Button(
                scroll_frame,
                text=evento.replace('_', ' ').capitalize(),
                width=25,
                height=2,
                bg=color_boton,
                fg="white",
                command=lambda e=evento: self.enviar_evento(e)
            )
            row = idx // 2  # Número de fila
            col = idx % 2   # Columna (0 o 1)
            btn_evento.grid(row=row, column=col, padx=10, pady=5)

        # Ajustar las columnas para que ocupen el mismo espacio
        scroll_frame.columnconfigure(0, weight=1)
        scroll_frame.columnconfigure(1, weight=1)

    def enviar_evento(self, evento):
        # Enviar el evento al dron
        comando = {
            'tipo': evento
        }
        self.queue_to_drone.put(comando)
        mensaje = f"Evento '{evento}' enviado al dron."
        self.registro_eventos.agregar_evento(mensaje)
        messagebox.showinfo("Evento Enviado", mensaje)
