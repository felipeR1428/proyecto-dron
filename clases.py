# clases.py

import logging
import threading
import time
import queue

# Configuración del log
logging.basicConfig(
    filename='registro_dron.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

class RegistroEventos:
    def __init__(self):
        self.eventos = []
        self.lock = threading.Lock()  # Para manejar acceso concurrente
    
    def agregar_evento(self, mensaje):
        with self.lock:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            entrada = f"[{timestamp}] {mensaje}"
            self.eventos.append(entrada)
            logging.info(entrada)

class Drone:
    def __init__(self, registro_eventos, queue_commands, queue_updates, queue_commands_simulacion, queue_updates_simulacion):
        self.registro_eventos = registro_eventos
        self.queue_commands = queue_commands            # Cola para recibir comandos de la interfaz y máquina de estados
        self.queue_updates = queue_updates              # Cola para enviar actualizaciones a la interfaz y máquina de estados
        self.queue_commands_simulacion = queue_commands_simulacion   # Cola para enviar comandos a la simulación
        self.queue_updates_simulacion = queue_updates_simulacion     # Cola para recibir actualizaciones de la simulación

        self.localizacion_emergencia = None
        self.bateria = 100      # Porcentaje de batería
        self.velocidad = 0      # Velocidad en km/h
        self.altitud = 0        # Altitud en metros

        # Coordenadas iniciales en el Hospital Universitario San Ignacio en Bogotá
        self.home_lat = 4.627925
        self.home_lon = -74.064692
        self.posicion_actual = [self.home_lat, self.home_lon]

        self.thread_activo = True

        # Iniciar hilos para manejar comandos y actualizaciones
        threading.Thread(target=self.escuchar_comandos_externos, daemon=True).start()
        threading.Thread(target=self.recibir_actualizaciones_simulacion, daemon=True).start()
        threading.Thread(target=self.actualizar_estado_drone, daemon=True).start()

    def simulation_to_coord(self, x, y):
        lon = x / 10000 + self.home_lon
        lat = y / 10000 + self.home_lat
        return (lat, lon)

    def escuchar_comandos_externos(self):
        """Escucha comandos de la interfaz de usuario o máquina de estados."""
        while self.thread_activo:
            try:
                comando = self.queue_commands.get(timeout=1)
                if comando:
                    tipo_comando = comando.get('tipo')
                    self.registro_eventos.agregar_evento(f"Comando recibido: {tipo_comando}")
                    if tipo_comando == 'recepcion_comando_arranque_vuelo':
                        ubicacion = comando.get('ubicacion')
                        self.recibir_comando_arranque_vuelo(ubicacion)
                    elif tipo_comando == 'cambio_localizacion_emergencia':
                        nueva_ubicacion = comando.get('nueva_ubicacion')
                        self.cambiar_localizacion_emergencia(nueva_ubicacion)
                    elif tipo_comando == 'despegar':
                        self.despegar()
                    elif tipo_comando == 'aterrizar':
                        self.aterrizar()
                    elif tipo_comando == 'iniciar_asistencia':
                        self.iniciar_asistencia()
                    elif tipo_comando == 'regresar_base':
                        self.regresar_base()
                    elif tipo_comando == 'vuelo_libre':
                        activar = comando.get('activar', True)
                        self.enviar_comando_simulacion({'tipo': 'vuelo_libre', 'activar': activar})
                        estado = "activado" if activar else "desactivado"
                        self.registro_eventos.agregar_evento(f"Vuelo libre {estado}.")
                    # Manejar otros comandos según sea necesario
            except queue.Empty:
                continue  # No hay comandos, continuar esperando

    def recibir_comando_arranque_vuelo(self, ubicacion):
        """Inicia el vuelo hacia la emergencia."""
        self.localizacion_emergencia = ubicacion
        self.registro_eventos.agregar_evento(f"Iniciando vuelo hacia la emergencia en {ubicacion}.")
        self.log_estado(f"Iniciando vuelo hacia la emergencia en {ubicacion}.")
        self.velocidad = 60
        self.altitud = 100
        # Enviar comando a la simulación para iniciar el vuelo con la ubicación de emergencia
        self.enviar_comando_simulacion({'tipo': 'recibir_comando_arranque', 'ubicacion': ubicacion})
        # Enviar actualización a la interfaz de usuario
        self.enviar_actualizacion_ui()

    def despegar(self):
        """Simula el despegue del dron."""
        self.registro_eventos.agregar_evento("Iniciando secuencia de despegue.")
        self.log_estado("Secuencia de despegue iniciada.")
        # Simular aumento de altitud hasta alcanzar altitud de vuelo
        for altura in range(0, 101, 20):
            time.sleep(0.5)
            self.altitud = altura
            self.registro_eventos.agregar_evento(f"Despegando... Altitud actual: {self.altitud} m.")
            self.enviar_actualizacion_ui()
        self.registro_eventos.agregar_evento("Despegue completado.")
        self.log_estado("Despegue completado.")
        # Enviar evento de despegue completado
        self.queue_updates.put({'type': 'evento', 'data': 'despegue_completado'})

    def aterrizar(self):
        """Simula el aterrizaje del dron."""
        self.registro_eventos.agregar_evento("Iniciando secuencia de aterrizaje.")
        self.log_estado("Secuencia de aterrizaje iniciada.")
        # Simular descenso de altitud hasta alcanzar el suelo
        for altura in range(self.altitud, -1, -20):
            time.sleep(0.5)
            self.altitud = altura
            self.registro_eventos.agregar_evento(f"Aterrizando... Altitud actual: {self.altitud} m.")
            self.enviar_actualizacion_ui()
        self.registro_eventos.agregar_evento("Aterrizaje completado.")
        self.log_estado("Aterrizaje completado.")
        # Enviar evento de aterrizaje completado
        self.queue_updates.put({'type': 'evento', 'data': 'aterrizaje_completado'})

    def iniciar_asistencia(self):
        """Simula la asistencia al paciente."""
        self.registro_eventos.agregar_evento("Iniciando asistencia al paciente con el DEA.")
        self.log_estado("Asistiendo al paciente.")
        # Simular tiempo de asistencia
        time.sleep(5)
        self.registro_eventos.agregar_evento("Asistencia al paciente completada.")
        self.log_estado("Asistencia completada.")
        # Enviar evento de asistencia completada
        self.queue_updates.put({'type': 'evento', 'data': 'asistencia_completada'})

    def regresar_base(self):
        """Inicia el regreso del dron a la base."""
        self.registro_eventos.agregar_evento("Iniciando regreso a la base.")
        self.log_estado("Regresando a la base.")
        # Enviar comando a la simulación para regresar a la base
        self.enviar_comando_simulacion({'tipo': 'regresar_base'})
        # Actualizar estado
        self.velocidad = 60
        self.enviar_actualizacion_ui()

    def cambiar_localizacion_emergencia(self, nueva_ubicacion):
        """Actualiza la ubicación de la emergencia."""
        self.registro_eventos.agregar_evento(f"Cambio de localización de emergencia a {nueva_ubicacion}.")
        self.log_estado(f"Cambiando rumbo hacia nueva ubicación: {nueva_ubicacion}.")
        self.localizacion_emergencia = nueva_ubicacion
        # Enviar actualización a la interfaz de usuario
        self.enviar_actualizacion_ui()
        # Enviar comando a la simulación si es necesario
        self.enviar_comando_simulacion({
            'tipo': 'cambio_localizacion_emergencia',
            'nueva_ubicacion': nueva_ubicacion
        })

    def enviar_comando_simulacion(self, comando):
        """Envía un comando a la simulación a través de la cola."""
        if self.queue_commands_simulacion:
            self.queue_commands_simulacion.put(comando)
            self.log_estado(f"Comando enviado a la simulación: {comando}")
            self.registro_eventos.agregar_evento(f"Comando enviado a la simulación: {comando}")

    def recibir_actualizaciones_simulacion(self):
        """Recibe actualizaciones de la simulación."""
        while self.thread_activo:
            try:
                update = self.queue_updates_simulacion.get(timeout=1)
                if update:
                    tipo_update = update.get('type')
                    if tipo_update == 'posicion_actualizada':
                        data = update.get('data')
                        x_sim, y_sim = data['posicion']
                        # Convertir coordenadas de simulación a coordenadas reales
                        self.posicion_actual = self.simulation_to_coord(x_sim, y_sim)
                        self.registro_eventos.agregar_evento(f"Posición actualizada: {self.posicion_actual}")
                        # Enviar actualización a la interfaz de usuario
                        self.enviar_actualizacion_ui()
                    elif tipo_update == 'evento':
                        mensaje = update.get('data')
                        self.registro_eventos.agregar_evento(f"Evento de simulación: {mensaje}")
                        self.log_estado(f"Evento recibido de la simulación: {mensaje}")
                        # Enviar evento a la máquina de estados
                        self.queue_updates.put({'type': 'evento', 'data': mensaje})
            except queue.Empty:
                continue  # No hay actualizaciones, continuar esperando

    def actualizar_estado_drone(self):
        """Actualiza periódicamente el estado del dron."""
        while self.thread_activo:
            time.sleep(1)
            if self.velocidad > 0:
                self.bateria -= 1
                self.registro_eventos.agregar_evento(f"Batería actual: {self.bateria}%")
                if self.bateria <= 0:
                    self.bateria = 0
                    self.velocidad = 0
                    self.registro_eventos.agregar_evento("Batería agotada. Dron aterrizando de emergencia.")
                    self.log_estado("Batería agotada. Aterrizaje de emergencia.")
                    # Enviar comando a la simulación para detener el dron
                    self.enviar_comando_simulacion({'tipo': 'detener_dron'})
                    # Enviar evento de batería baja
                    self.queue_updates.put({'type': 'evento', 'data': 'aviso_bateria_baja'})
                # Enviar actualización de estado a la interfaz de usuario
                self.enviar_actualizacion_ui()
            else:
                time.sleep(1)  # Si el dron está en tierra, esperar un poco más para ahorrar recursos

    def enviar_actualizacion_ui(self):
        """Envía una actualización del estado actual del dron a la interfaz de usuario."""
        self.queue_updates.put({
            'type': 'estado_dron',
            'data': {
                'estado': 'En vuelo' if self.velocidad > 0 else 'En tierra',
                'bateria': self.bateria,
                'velocidad': self.velocidad,
                'altitud': self.altitud,
                'posicion_actual': self.posicion_actual
            }
        })
        self.registro_eventos.agregar_evento("Estado del dron actualizado.")

    def log_estado(self, mensaje):
        """Registra un mensaje en el log y en la consola."""
        print(f"Drone: {mensaje}")
        logging.info(f"Drone: {mensaje}")
