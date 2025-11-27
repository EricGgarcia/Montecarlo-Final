import pika
import json

class ConexionRabbitMQ:
    def __init__(self, host, usuario, password):
        self.host = host
        self.credentials = pika.PlainCredentials(usuario, password)
        self.connection = None
        self.channel = None

    def conectar(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host, credentials=self.credentials))
        self.channel = self.connection.channel()
        
        # Cola de ESCENARIOS (Work Queue - Reparte trabajo)
        self.channel.queue_declare(queue='cola_escenarios', durable=True)
        
        #  Cola de RESULTADOS (Work Queue - Recibe respuestas)
        self.channel.queue_declare(queue='cola_resultados', durable=True)
        
        # Exchange de MODELO (Fanout - "Micrófono" para todos)
        self.channel.exchange_declare(exchange='exchange_modelo', exchange_type='fanout')
        
        # Exchange de ESTADÍSTICAS (Fanout - Para el dashboard)
        self.channel.exchange_declare(exchange='exchange_stats', exchange_type='fanout')

    def publicar_modelo(self, modelo):
        """Publica el modelo a TODOS los consumidores conectados"""
        mensaje = json.dumps(modelo)
        # Se envía al exchange, no a una cola específica
        self.channel.basic_publish(
            exchange='exchange_modelo', # Nombre del micrófono
            routing_key='',             # No importa la ruta en fanout
            body=mensaje
        )
        print(" [x] Modelo publicado a todos los consumidores (Fanout)")

    def publicar_escenario(self, escenario):
        """Publica una tarea individual a la cola de trabajo"""
        mensaje = json.dumps(escenario)
        self.channel.basic_publish(
            exchange='',
            routing_key='cola_escenarios',
            body=mensaje,
            properties=pika.BasicProperties(delivery_mode=2) # Persistente
        )

    def recibir_modelo(self, callback_modelo):
        """
        Crea una cola temporal exclusiva para este consumidor
        y la conecta al 'micrófono' del modelo.
        """
        # Crear cola temporal con nombre aleatorio
        result = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        
        # Conectar esa cola al exchange del modelo
        self.channel.queue_bind(exchange='exchange_modelo', queue=queue_name)
        
        print(' * Esperando modelo...')
        
        # Consumir UNA sola vez
        self.channel.basic_consume(
            queue=queue_name, 
            on_message_callback=callback_modelo, 
            auto_ack=True
        )
        self.channel.start_consuming()

    def consumir_escenarios(self, callback_escenario):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='cola_escenarios', on_message_callback=callback_escenario)
        print(' * Esperando escenarios...')
        self.channel.start_consuming()

    def publicar_resultado(self, resultado):
        self.channel.basic_publish(
            exchange='',
            routing_key='cola_resultados',
            body=json.dumps(resultado)
        )

    # --- Métodos para el Dashboard ---
    def publicar_estadistica(self, tipo, datos):
        datos['tipo'] = tipo
        self.channel.basic_publish(
            exchange='exchange_stats',
            routing_key='',
            body=json.dumps(datos)
        )

    def consumir_estadisticas(self, callback):
        result = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(exchange='exchange_stats', queue=queue_name)
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    def consumir_resultados(self, callback):
        # El dashboard también lee resultados para el histograma
        self.channel.basic_consume(queue='cola_resultados', on_message_callback=callback, auto_ack=True)

    def iniciar_consumo(self):
        self.channel.start_consuming()