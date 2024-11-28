# simulacion.py

from vpython import *
import multiprocessing
import queue
import time

def iniciar_simulacion(queue_commands, queue_updates):
    """
    Inicia la simulación 3D del dron utilizando VPython.
    Escucha comandos desde la cola para iniciar misiones hacia ubicaciones específicas.
    Envía actualizaciones de estado a la interfaz de usuario y a la máquina de estados.
    """
    # Configuración de la escena
    scene = canvas(title='Simulación del Dron en 3D', width=1000, height=800)
    scene.background = vector(0.8, 0.9, 1)  # Cielo azul claro
    scene.range = 50
    scene.forward = vector(-1, -1, -1)  # Orientación inicial de la cámara

    # Variables globales
    vuelo_libre = False
    keys_pressed = set()

    # Coordenadas del hospital (posición inicial del dron)
    home_lat = 4.627925
    home_lon = -74.064692

    # Crear el dron estilizado
    def crear_dron():
        # Cuerpo principal
        cuerpo = box(
            pos=vector(0, 0, 5),
            size=vector(2.5, 1.2, 0.5),
            color=color.gray(0.2)
        )

        # Indicador LED en la parte superior
        led = box(
            pos=cuerpo.pos + vector(0, 0.6, 0),
            size=vector(0.5, 0.2, 0.05),
            color=color.blue
        )

        # Cámara en la parte frontal
        camara_cuerpo = box(
            pos=cuerpo.pos + vector(0, -0.6, -0.3),
            size=vector(0.7, 0.5, 0.5),
            color=color.black
        )
        lente = sphere(
            pos=camara_cuerpo.pos + vector(0, 0, 0.3),
            radius=0.1,
            color=color.red
        )

        # Brazos del dron
        brazo_longitud = 3.5
        brazo_grosor = 0.2
        brazos = []
        posiciones_brazos = [
            vector(brazo_longitud, 0, 0),
            vector(-brazo_longitud, 0, 0),
            vector(0, brazo_longitud, 0),
            vector(0, -brazo_longitud, 0),
        ]
        for pos in posiciones_brazos:
            brazo = box(
                pos=cuerpo.pos + pos / 2,
                size=vector(brazo_longitud, brazo_grosor, 0.1),
                color=color.gray(0.3)
            )
            brazos.append(brazo)

        # Rotores y hélices
        rotor_radius = 0.6
        rotors = []
        helices = []
        for brazo_pos in posiciones_brazos:
            rotor = cylinder(
                pos=cuerpo.pos + brazo_pos,
                axis=vector(0, 0, 0.2),
                radius=rotor_radius,
                color=color.black
            )
            helice = box(
                pos=rotor.pos + vector(0, 0, 0.1),
                size=vector(1.5, 0.1, 0.02),
                color=color.gray(0.7),
            )
            rotors.append(rotor)
            helices.append(helice)

        return cuerpo, brazos, rotors, helices, led, camara_cuerpo, lente

    # Función para convertir coordenadas geográficas a coordenadas de simulación
    def coord_to_simulation(lat, lon):
        # Simple mapping, ajustar escala según sea necesario
        x = (lon - home_lon) * 10000  # Escala en X
        y = (lat - home_lat) * 10000   # Escala en Y
        return vector(x, y, 5)  # Mantener Z en 5

    # Crear el dron
    cuerpo, brazos, rotors, helices, led, camara_cuerpo, lente = crear_dron()

    drone_target_position = None
    animation_in_progress = False
    direction_arrow = None
    destination_marker = None
    emergency_point = None

    # Ajustes de la cámara
    camera_offset = vector(0, -20, 10)
    scene.camera.pos = cuerpo.pos + camera_offset
    scene.camera.axis = cuerpo.pos - scene.camera.pos

    # Variable para rotar las hélices
    helice_angle = 0

    # Variables para el control del dron
    detener_dron = False
    regreso = False

    # Manejo de teclas
    def keydown(evt):
        key = evt.key
        keys_pressed.add(key)

    def keyup(evt):
        key = evt.key
        keys_pressed.discard(key)

    scene.bind('keydown', keydown)
    scene.bind('keyup', keyup)

    # Función para actualizar las partes del dron según la posición del cuerpo
    def actualizar_partes_dron():
        # Actualizar posiciones de brazos, rotores y hélices
        posiciones_brazos = [
            vector(3.5, 0, 0),
            vector(-3.5, 0, 0),
            vector(0, 3.5, 0),
            vector(0, -3.5, 0),
        ]
        for brazo, offset in zip(brazos, posiciones_brazos):
            brazo.pos = cuerpo.pos + offset / 2

        for rotor, helice, offset in zip(rotors, helices, posiciones_brazos):
            rotor.pos = cuerpo.pos + offset
            helice.pos = rotor.pos + vector(0, 0, 0.1)
            # La rotación de las hélices ya se maneja en el bucle principal

        # Actualizar posición del LED
        led.pos = cuerpo.pos + vector(0, 0.6, 0)

        # Actualizar posición de la cámara y lente
        camara_cuerpo.pos = cuerpo.pos + vector(0, -0.6, -0.3)
        lente.pos = camara_cuerpo.pos + vector(0, 0, 0.3)

    while True:
        rate(60)  # 60 fps

        # Rotar las hélices para simular movimiento continuo
        helice_angle += 0.2
        for helice in helices:
            helice.rotate(angle=0.2, axis=vector(0, 0, 1), origin=helice.pos)

        # Escuchar comandos de la cola
        try:
            message = queue_commands.get_nowait()
            comando = message.get('tipo')
            if comando == 'recibir_comando_arranque':
                # Iniciar misión hacia la localización de emergencia
                ubicacion = message.get('ubicacion')
                if ubicacion:
                    try:
                        lat_str, lon_str = ubicacion.split(',')
                        lat = float(lat_str.strip())
                        lon = float(lon_str.strip())
                        # Convertir a coordenadas de simulación
                        drone_target_position = coord_to_simulation(lat, lon)
                        # Crear punto de emergencia
                        if emergency_point:
                            emergency_point.visible = False  # Ocultar anterior si existe
                        emergency_point = cylinder(
                            pos=drone_target_position,
                            axis=vector(0, 0, 2),
                            radius=1,
                            color=color.red
                        )
                        animation_in_progress = True
                        queue_updates.put({
                            'type': 'evento',
                            'data': f"Dron despegando hacia {ubicacion}"
                        })
                        print(f"Dron despegando hacia {ubicacion}")
                        # Crear marcador y flecha de dirección
                        if direction_arrow:
                            direction_arrow.visible = False
                        direction_arrow = arrow(
                            pos=cuerpo.pos,
                            axis=drone_target_position - cuerpo.pos,
                            shaftwidth=0.2,
                            color=color.yellow
                        )
                    except ValueError:
                        queue_updates.put({
                            'type': 'evento',
                            'data': "Error en la ubicación proporcionada."
                        })
                else:
                    # Ubicación no proporcionada
                    queue_updates.put({
                        'type': 'evento',
                        'data': "No se proporcionó ubicación para la emergencia."
                    })
            elif comando == 'vuelo_libre':
                activar = message.get('activar', True)
                vuelo_libre = activar
                if vuelo_libre:
                    queue_updates.put({
                        'type': 'evento',
                        'data': "Vuelo libre activado."
                    })
                else:
                    queue_updates.put({
                        'type': 'evento',
                        'data': "Vuelo libre desactivado."
                    })
            elif comando == 'detener_dron':
                detener_dron = True
                animation_in_progress = False
                queue_updates.put({
                    'type': 'evento',
                    'data': "Dron detenido por comando de emergencia."
                })
            elif comando == 'reiniciar_dron':
                # Reiniciar dron a posición inicial
                cuerpo.pos = vector(0, 0, 5)
                detener_dron = False
                animation_in_progress = False
                # Actualizar posiciones de partes del dron
                actualizar_partes_dron()
            # Puedes manejar más comandos si es necesario
        except queue.Empty:
            pass  # No hay comandos, continuar

        if detener_dron:
            continue  # Si el dron está detenido, saltamos la animación

        # Control manual del dron en modo vuelo libre
        if vuelo_libre:
            move_step = 0.5  # Ajustar velocidad de movimiento
            if 'w' in keys_pressed:
                cuerpo.pos.y += move_step
            if 's' in keys_pressed:
                cuerpo.pos.y -= move_step
            if 'a' in keys_pressed:
                cuerpo.pos.x -= move_step
            if 'd' in keys_pressed:
                cuerpo.pos.x += move_step
            if 'q' in keys_pressed:
                cuerpo.pos.z += move_step
            if 'e' in keys_pressed:
                cuerpo.pos.z -= move_step

            # Actualizar posiciones de partes del dron
            actualizar_partes_dron()

            # Actualizar la posición de la cámara para seguir al dron
            scene.camera.pos = cuerpo.pos + camera_offset
            scene.camera.axis = cuerpo.pos - scene.camera.pos

            # Enviar actualización de posición al dron
            queue_updates.put({
                'type': 'posicion_actualizada',
                'data': {
                    'posicion': (cuerpo.pos.x, cuerpo.pos.y)
                }
            })
            continue  # Saltar el resto del bucle para evitar conflictos

        # Animar el dron hacia la posición objetivo
        if animation_in_progress and drone_target_position:
            direction = drone_target_position - cuerpo.pos
            if direction.mag > 0.5:
                step = direction.norm() * 0.2  # Velocidad de movimiento ajustable
                cuerpo.pos += step

                # Actualizar posiciones de partes del dron
                actualizar_partes_dron()

                # Actualizar dirección de flecha
                if direction_arrow:
                    direction_arrow.pos = cuerpo.pos
                    direction_arrow.axis = drone_target_position - cuerpo.pos

                # Actualizar la posición de la cámara para seguir al dron
                scene.camera.pos = cuerpo.pos + camera_offset
                scene.camera.axis = cuerpo.pos - scene.camera.pos

                # Enviar actualización de posición al dron
                queue_updates.put({
                    'type': 'posicion_actualizada',
                    'data': {
                        'posicion': (cuerpo.pos.x, cuerpo.pos.y)
                    }
                })
            else:
                animation_in_progress = False
                queue_updates.put({
                    'type': 'evento',
                    'data': "Dron llegó al destino"
                })
                if direction_arrow:
                    direction_arrow.visible = False
                if destination_marker:
                    destination_marker.visible = False

                if not regreso:
                    # Simular asistencia
                    queue_updates.put({
                        'type': 'evento',
                        'data': "Dron asistiendo con el DEA."
                    })
                    time.sleep(5)  # Tiempo de asistencia
                    queue_updates.put({
                        'type': 'evento',
                        'data': "Asistencia completada, dron regresando a base."
                    })

                    # Regresar a base
                    drone_target_position = vector(0, 0, 5)  # Regresar a la posición inicial
                    animation_in_progress = True
                    destination_marker = sphere(
                        pos=drone_target_position,
                        radius=0.5,
                        color=color.green
                    )
                    direction_arrow = arrow(
                        pos=cuerpo.pos,
                        axis=drone_target_position - cuerpo.pos,
                        shaftwidth=0.2,
                        color=color.yellow
                    )
                    regreso = True
                else:
                    # Dron ha regresado a la base
                    queue_updates.put({
                        'type': 'evento',
                        'data': "Dron regresó a la base y está en espera."
                    })
                    regreso = False  # Reiniciar para la próxima misión
        else:
            # Enviar actualización de posición al dron en reposo
            queue_updates.put({
                'type': 'posicion_actualizada',
                'data': {
                    'posicion': (cuerpo.pos.x, cuerpo.pos.y)
                }
            })
