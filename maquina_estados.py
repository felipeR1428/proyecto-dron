# maquina_estados.py

import threading
import queue
import time
import logging

class MaquinaEstados:
    def __init__(self, registro_eventos, queue_from_drone, queue_to_drone):
        self.registro_eventos = registro_eventos
        self.queue_from_drone = queue_from_drone  # Cola para recibir actualizaciones del dron
        self.queue_to_drone = queue_to_drone      # Cola para enviar comandos al dron

        # Definir los estados posibles
        self.estados = [
            'en_tierra',
            'despegando',
            'en_ruta',
            'en_emergencia',
            'asistiendo_paciente',
            'regresando_base',
            'aterrizando',
            'en_mantenimiento',
            'en_dea'
        ]

        # Estado inicial
        self.estado_actual = 'en_tierra'

        # Eventos
        self.eventos = queue.Queue()

        # Iniciar hilo para procesar eventos
        threading.Thread(target=self.procesar_eventos, daemon=True).start()

    def procesar_eventos(self):
        while True:
            try:
                evento = self.eventos.get(timeout=1)
                self.gestionar_evento(evento)
            except queue.Empty:
                continue  # No hay eventos, continuar esperando

    def gestionar_evento(self, evento):
        # Loggear el evento recibido
        self.registro_eventos.agregar_evento(f"Evento recibido: {evento}")
        logging.info(f"MaquinaEstados: Evento recibido: {evento}")

        # Guardar el estado anterior
        estado_anterior = self.estado_actual

        # Implementar la lógica de la máquina de estados
        if evento == 'recepcion_comando_arranque_vuelo':
            if self.estado_actual == 'en_tierra':
                self.cambiar_estado('despegando')
                self.enviar_comando_dron({'tipo': 'despegar'})
            elif self.estado_actual == 'en_dea':
                self.registro_eventos.agregar_evento("No se puede iniciar vuelo. Dron en estado DEA.")
            else:
                self.registro_eventos.agregar_evento("Comando de arranque ignorado. Dron no está en tierra.")
        elif evento == 'despegue_completado':
            if self.estado_actual == 'despegando':
                self.cambiar_estado('en_ruta')
                self.registro_eventos.agregar_evento("Dron en ruta hacia la emergencia.")
        elif evento == 'cambio_localizacion_emergencia':
            if self.estado_actual in ['en_ruta', 'en_emergencia']:
                self.enviar_comando_dron({'tipo': 'cambio_localizacion_emergencia'})
                self.registro_eventos.agregar_evento("Cambiando localización de la emergencia.")
        elif evento == 'llegada_destino':
            if self.estado_actual == 'en_ruta':
                self.cambiar_estado('en_emergencia')
                self.registro_eventos.agregar_evento("Dron llegó al destino y está en emergencia.")
                self.enviar_comando_dron({'tipo': 'iniciar_asistencia'})
        elif evento == 'deteccion_signos_vitales_paciente':
            if self.estado_actual == 'en_emergencia':
                self.cambiar_estado('en_dea')
                self.registro_eventos.agregar_evento("Signos vitales detectados. Preparando DEA.")
        elif evento == 'recepcion_comando_descarga_electrica':
            if self.estado_actual == 'en_dea':
                self.registro_eventos.agregar_evento("Descarga eléctrica administrada.")
        elif evento == 'asistencia_completada':
            if self.estado_actual == 'en_dea':
                self.cambiar_estado('regresando_base')
                self.enviar_comando_dron({'tipo': 'regresar_base'})
        elif evento == 'aviso_bateria_baja':
            self.cambiar_estado('en_mantenimiento')
            self.registro_eventos.agregar_evento("Batería baja. Dron en mantenimiento.")
        elif evento == 'falla_motor_detectada':
            self.cambiar_estado('en_mantenimiento')
            self.registro_eventos.agregar_evento("Falla en motor detectada. Dron en mantenimiento.")
        elif evento == 'motor_recuperado':
            if self.estado_actual == 'en_mantenimiento':
                self.cambiar_estado('en_tierra')
                self.registro_eventos.agregar_evento("Motor recuperado. Dron listo.")
        elif evento == 'regreso_base':
            if self.estado_actual == 'regresando_base':
                self.cambiar_estado('aterrizando')
                self.enviar_comando_dron({'tipo': 'aterrizar'})
        elif evento == 'aterrizaje_completado':
            if self.estado_actual == 'aterrizando':
                self.cambiar_estado('en_tierra')
                self.registro_eventos.agregar_evento("Dron aterrizó y está en tierra.")
        else:
            self.registro_eventos.agregar_evento(f"Evento no manejado en el estado actual: {evento}")

        # Actualizar estado del dron
        if estado_anterior != self.estado_actual:
            self.enviar_actualizacion_estado()

    def cambiar_estado(self, nuevo_estado):
        # Llamar al método on_exit del estado actual
        self.on_exit(self.estado_actual)
        self.estado_actual = nuevo_estado
        # Llamar al método on_enter del nuevo estado
        self.on_enter(self.estado_actual)
        self.registro_eventos.agregar_evento(f"Transición de estado: {self.estado_actual}")

    def on_enter(self, estado):
        # Acciones al entrar a un estado
        self.registro_eventos.agregar_evento(f"Entrando en estado: {estado}")
        logging.info(f"MaquinaEstados: Entrando en estado {estado}")

    def on_exit(self, estado):
        # Acciones al salir de un estado
        self.registro_eventos.agregar_evento(f"Saliendo del estado: {estado}")
        logging.info(f"MaquinaEstados: Saliendo del estado {estado}")

    def enviar_comando_dron(self, comando):
        """Envía un comando al dron a través de la cola."""
        self.queue_to_drone.put(comando)
        logging.info(f"MaquinaEstados: Comando enviado al dron: {comando}")
        self.registro_eventos.agregar_evento(f"Comando enviado al dron: {comando}")

    def recibir_actualizaciones_dron(self):
        """Recibe actualizaciones del dron y genera eventos según sea necesario."""
        while True:
            try:
                update = self.queue_from_drone.get(timeout=1)
                if update:
                    tipo_update = update.get('type')
                    if tipo_update == 'evento':
                        mensaje = update.get('data')
                        # Mapear el mensaje a un evento
                        evento = self.mapear_mensaje_a_evento(mensaje)
                        if evento:
                            self.registro_eventos.agregar_evento(f"Evento mapeado: {evento}")
                            self.eventos.put(evento)
            except queue.Empty:
                continue  # No hay actualizaciones, continuar esperando

    def mapear_mensaje_a_evento(self, mensaje):
        """Mapea un mensaje recibido a un evento de la máquina de estados."""
        if "Dron despegando hacia" in mensaje:
            return 'despegue_completado'
        elif "Dron llegó al destino" in mensaje:
            return 'llegada_destino'
        elif "Dron asistiendo con el DEA." in mensaje:
            return 'deteccion_signos_vitales_paciente'
        elif "Descarga eléctrica administrada" in mensaje:
            return 'recepcion_comando_descarga_electrica'
        elif "Asistencia completada" in mensaje:
            return 'asistencia_completada'
        elif "Dron regresó a la base" in mensaje:
            return 'regreso_base'
        elif "Dron aterrizó" in mensaje:
            return 'aterrizaje_completado'
        elif "Batería baja" in mensaje:
            return 'aviso_bateria_baja'
        elif "Falla en motor detectada" in mensaje:
            return 'falla_motor_detectada'
        elif "Motor recuperado" in mensaje:
            return 'motor_recuperado'
        # Agregar más mapeos según los mensajes que se envían desde el dron
        return None

    def enviar_actualizacion_estado(self):
        """Envía una actualización del estado actual a la interfaz de usuario o registro."""
        mensaje = f"Estado del dron actualizado: {self.estado_actual}"
        self.registro_eventos.agregar_evento(mensaje)
        logging.info(f"MaquinaEstados: {mensaje}")
        # Enviar actualización a la interfaz de usuario
        self.queue_to_drone.put({
            'type': 'estado_maquina',
            'data': self.estado_actual
        })
