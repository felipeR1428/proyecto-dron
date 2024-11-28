# main.py

import threading
import multiprocessing
import queue
from clases import Drone, RegistroEventos
from interfaz_usuario import InterfazUsuario
from interfaz_eventos import InterfazEventos
from simulacion import iniciar_simulacion
from maquina_estados import MaquinaEstados  # Importar la máquina de estados

def main():
    # Crear colas para comunicación
    queue_to_drone = queue.Queue()
    queue_from_drone = queue.Queue()
    queue_to_simulacion = multiprocessing.Queue()
    queue_from_simulacion = multiprocessing.Queue()

    # Crear instancia del registro de eventos
    registro_eventos = RegistroEventos()

    # Crear instancia de la máquina de estados
    maquina_estados = MaquinaEstados(
        registro_eventos,
        queue_from_drone,
        queue_to_drone
    )

    # Crear instancia del dron
    drone = Drone(
        registro_eventos,
        queue_to_drone,
        queue_from_drone,
        queue_to_simulacion,    # Cola para enviar comandos a la simulación
        queue_from_simulacion   # Cola para recibir actualizaciones de la simulación
    )

    # Iniciar hilo para recibir actualizaciones del dron en la máquina de estados
    threading.Thread(target=maquina_estados.recibir_actualizaciones_dron, daemon=True).start()

    # Iniciar la simulación en un proceso separado
    proceso_simulacion = multiprocessing.Process(
        target=iniciar_simulacion,
        args=(queue_to_simulacion, queue_from_simulacion)
    )
    proceso_simulacion.start()

    # Crear e iniciar la interfaz de usuario
    app = InterfazUsuario(queue_to_drone, queue_from_drone, registro_eventos)

    # Crear e iniciar la interfaz de eventos
    interfaz_eventos = InterfazEventos(queue_to_drone, registro_eventos)
    interfaz_eventos.protocol("WM_DELETE_WINDOW", interfaz_eventos.destroy)

    try:
        app.mainloop()
    finally:
        # Al cerrar la interfaz, terminamos el proceso de simulación
        proceso_simulacion.terminate()
        proceso_simulacion.join()

if __name__ == "__main__":
    main()
