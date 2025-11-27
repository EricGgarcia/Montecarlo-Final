from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import json
import threading
import numpy as np
from conexion_rabbitmq import ConexionRabbitMQ

app = Flask(__name__)
app.config['SECRET_KEY'] = 'montecarlo_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# configuración de rabbitmq
HOST_RABBITMQ = '172.26.167.190' ##
USUARIO = 'Ale' ##Ale guest
PASSWORD = 'Ale' ##Ale guest

# lock para manejar concurrencia entre hilos
lock = threading.Lock()

# variables globales
estadisticas_productor = {
    'escenarios_generados': 0,
    'total': 0,
    'porcentaje': 0,
    'velocidad': 0,
    'completado': False
}

estadisticas_consumidores = {}
resultados = []
estadisticas_resultados = {
    'total': 0,
    'promedio': 0,
    'std': 0,
    'min': 0,
    'max': 0,
    'percentil_50': 0
}

class DashboardListener:
    """escucha las colas de rabbitmq y actualiza el dashboard"""
    
    def __init__(self):
        self.conexion = ConexionRabbitMQ(HOST_RABBITMQ, USUARIO, PASSWORD)
        
    def procesar_estadisticas(self, ch, method, properties, body):
        global estadisticas_productor, estadisticas_consumidores
        
        try:
            datos = json.loads(body.decode('utf-8'))
            
            with lock: # bloqueamos para escribir seguro
                if datos['tipo'] == 'productor':
                    estadisticas_productor = {
                        'escenarios_generados': datos.get('escenarios_generados', 0),
                        'total': datos.get('total', 0),
                        'porcentaje': datos.get('porcentaje', 0),
                        'velocidad': datos.get('velocidad', 0),
                        'completado': datos.get('completado', False)
                    }
                    socketio.emit('update_productor', estadisticas_productor)
                    
                elif datos['tipo'] == 'consumidor':
                    consumidor_id = datos.get('consumidor_id', 'unknown')
                    estadisticas_consumidores[consumidor_id] = {
                        'escenarios_procesados': datos.get('escenarios_procesados', 0),
                        'velocidad': datos.get('velocidad', 0),
                        'timestamp': datos.get('timestamp', 0)
                    }
                    socketio.emit('update_consumidores', estadisticas_consumidores)
                
        except Exception as e:
            print(f"error procesando estadísticas: {e}")
    
    def procesar_resultados(self, ch, method, properties, body):
        global resultados, estadisticas_resultados
        
        try:
            resultado = json.loads(body.decode('utf-8'))
            valor = resultado['valor']
            
            with lock:
                resultados.append(valor)
                current_len = len(resultados)
                
                # calcular estadísticas cada 100 resultados para no saturar
                if current_len % 100 == 0:
                    arr = np.array(resultados)
                    estadisticas_resultados = {
                        'total': current_len,
                        'promedio': float(np.mean(arr)),
                        'std': float(np.std(arr)),
                        'min': float(np.min(arr)),
                        'max': float(np.max(arr)),
                        'percentil_50': float(np.percentile(arr, 50))
                    }
                    
                    # calcular histograma
                    muestra = arr if current_len < 50000 else arr[-50000:]
                    hist, bin_edges = np.histogram(muestra, bins=30)
                    
                    histograma = {
                        'valores': hist.tolist(),
                        'bins': bin_edges.tolist()
                    }
                    
                    socketio.emit('update_resultados', {
                        'estadisticas': estadisticas_resultados,
                        'histograma': histograma
                    })
                
        except Exception as e:
            print(f"error procesando resultado: {e}")
    
    def iniciar(self):
        def escuchar():
            try:
                print("dashboard conectando a rabbitmq...")
                self.conexion.conectar()
                print("dashboard conectado a rabbitmq")
                
                self.conexion.consumir_estadisticas(self.procesar_estadisticas)
                self.conexion.consumir_resultados(self.procesar_resultados)
                
                print("dashboard escuchando colas...")
                self.conexion.iniciar_consumo()
                
            except Exception as e:
                print(f"error en listener: {e}")
        
        thread = threading.Thread(target=escuchar, daemon=True)
        thread.start()

@app.route('/')
def index():
    return render_template('dashboard.html')

@socketio.on('connect')
def handle_connect():
    print("cliente web conectado")
    with lock:
        emit('update_productor', estadisticas_productor)
        emit('update_consumidores', estadisticas_consumidores)
        emit('update_resultados', {
            'estadisticas': estadisticas_resultados,
            'histograma': {'valores': [], 'bins': []}
        })

if __name__ == '__main__':
    print("-" * 60)
    print("DASHBOARD MONTECARLO DISTRIBUIDO")
    print("-" * 60)
    
    listener = DashboardListener()
    listener.iniciar()
    
    print("\nAbra en navegador: http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
