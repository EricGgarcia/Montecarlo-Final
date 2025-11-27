import time
import math
import random
import json
import socket
from conexion_rabbitmq import ConexionRabbitMQ

# Configuración
HOST = '172.26.167.190'
USER = 'Ale'
PASS = 'Ale'
CLIENTE_ID = str(random.randint(100, 999))

conejo = ConexionRabbitMQ(HOST, USER, PASS)
conejo.conectar()

# Variable global para guardar el modelo recibido
modelo_actual = None
escenarios_procesados = 0
tiempo_inicio = 0

def ejecutar_modelo(modelo, escenario):
    """Simula la ejecución de la función del modelo"""
    # simular una función matemática basada en el escenario
    val = escenario['valor']
    resultado = math.sqrt(val) * random.normalvariate(10, 2)
    return resultado

def callback_recibir_modelo(ch, method, properties, body):
    global modelo_actual, tiempo_inicio
    print(f" [!] Modelo RECIBIDO")
    modelo_actual = json.loads(body)
    tiempo_inicio = time.time()
    
    #Detenemos el consumo del modelo para pasar a consumir escenarios
    ch.stop_consuming()

def callback_procesar_escenario(ch, method, properties, body):
    global escenarios_procesados
    
    if modelo_actual is None:
        print("Error: No tengo modelo")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    escenario = json.loads(body)
    
    # 1 Ejecutar simulación
    resultado_valor = ejecutar_modelo(modelo_actual, escenario)
    
    # 2 Publicar resultado
    conejo.publicar_resultado({'valor': resultado_valor})
    
    # 3 Confirmar a RabbitMQ (ACK)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
    # 4 Actualizar estadísticas locales y enviar al Dashboard
    escenarios_procesados += 1
    tiempo_actual = time.time()
    duracion = tiempo_actual - tiempo_inicio
    velocidad = escenarios_procesados / duracion if duracion > 0 else 0
    
    # Enviar "latido" al dashboard cada 10 procesados para no saturar
    if escenarios_procesados % 10 == 0:
        conejo.publicar_estadistica('consumidor', {
            'consumidor_id': CLIENTE_ID,
            'escenarios_procesados': escenarios_procesados,
            'velocidad': velocidad,
            'timestamp': tiempo_actual
        })
        print(f"Proc: {escenarios_procesados} | Vel: {velocidad:.2f}/s")

print(f"--- CONSUMIDOR {CLIENTE_ID} INICIADO ---")

# FASE 1: Esperar el modelo 
conejo.recibir_modelo(callback_recibir_modelo)

# FASE 2: Una vez tenemos modelo, procesar escenarios
print(" [*] Modelo cargado. Iniciando procesamiento de escenarios...")
conejo.consumir_escenarios(callback_procesar_escenario)
