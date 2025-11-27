import time
import random
from conexion_rabbitmq import ConexionRabbitMQ

# Configuración
HOST = '172.26.167.190' ##
USER = 'Ale' ##Ale guest
PASS = 'Ale' ##Ale guest

conejo = ConexionRabbitMQ(HOST, USER, PASS)
conejo.conectar()

# 1. Definir el Modelo
modelo = {
    "nombre": "Simulacion_Financiera_2025",
    "tipo": "Montecarlo",
    "parametros": {"media": 10, "desviacion": 2}
}

# 2. Publicar Modelo
print("--- PUBLICANDO MODELO ---")
conejo.publicar_modelo(modelo)
print("Espere 2 segundos para asegurar propagación...")
time.sleep(2) 

# 3. Generar y Publicar Escenarios
TOTAL_ESCENARIOS = 10000
start_time = time.time()

print(f"--- GENERANDO {TOTAL_ESCENARIOS} ESCENARIOS ---")

for i in range(TOTAL_ESCENARIOS):
    # Crear un escenario único
    escenario = {
        "id": i,
        "valor": random.randint(100, 5000) # Variable aleatoria de entrada
    }
    
    conejo.publicar_escenario(escenario)
    
    # Reportar al dashboard cada 500 generados
    if i % 500 == 0:
        elapsed = time.time() - start_time
        velocidad = (i + 1) / elapsed if elapsed > 0 else 0
        conejo.publicar_estadistica('productor', {
            'escenarios_generados': i + 1,
            'total': TOTAL_ESCENARIOS,
            'porcentaje': ((i + 1) / TOTAL_ESCENARIOS) * 100,
            'velocidad': velocidad,
            'completado': False
        })
        print(f"Generado: {i} ({velocidad:.0f}/s)")

# Reporte final
conejo.publicar_estadistica('productor', {
    'escenarios_generados': TOTAL_ESCENARIOS,
    'total': TOTAL_ESCENARIOS,
    'porcentaje': 100,
    'velocidad': TOTAL_ESCENARIOS / (time.time() - start_time),
    'completado': True
})
print("--- CARGA COMPLETA ---")
