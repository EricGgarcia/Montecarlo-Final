import re
import numpy as np
import json
import math # Agregado para permitir funciones como math.sqrt, math.log, etc.

class ModeloMontecarlo:
    """Representa un modelo de simulación Montecarlo"""
    
    def __init__(self):
        self.funcion = None
        self.variables = {}
        self.num_simulaciones = 0
        
    def cargar_desde_archivo(self, ruta_archivo):
        """Carga el modelo desde un archivo de texto"""
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Parsear la función
        match_funcion = re.search(r'funcion:\s*(.+)', contenido)
        if match_funcion:
            self.funcion = match_funcion.group(1).strip()
        
        # Parsear las variables
        seccion_variables = re.search(r'variables:(.*?)(?=simulaciones:|$)', contenido, re.DOTALL)
        if seccion_variables:
            lineas_variables = seccion_variables.group(1).strip().split('\n')
            for linea in lineas_variables:
                linea = linea.strip()
                if ':' in linea:
                    nombre, distribucion = linea.split(':', 1)
                    self.variables[nombre.strip()] = distribucion.strip()
        
        # Parsear número de simulaciones
        match_sims = re.search(r'simulaciones:\s*(\d+)', contenido)
        if match_sims:
            self.num_simulaciones = int(match_sims.group(1))
    
    def generar_escenario(self):
        """Genera un escenario con valores aleatorios para cada variable"""
        escenario = {}
        
        for nombre_var, dist_str in self.variables.items():
            valor = self._generar_valor(dist_str)
            escenario[nombre_var] = valor
        
        return escenario
    
    def _generar_valor(self, dist_str):
        """Genera un valor aleatorio según la distribución especificada"""
        dist_str = dist_str.lower()
        
        # Distribución constante
        if 'constante' in dist_str:
            match = re.search(r'constante\(([^)]+)\)', dist_str)
            if match:
                return float(match.group(1))
        
        # Distribución normal
        elif 'normal' in dist_str:
            match = re.search(r'normal\(media=([^,]+),\s*std=([^)]+)\)', dist_str)
            if match:
                media = float(match.group(1))
                std = float(match.group(2))
                return np.random.normal(media, std)
        
        # Distribución uniforme
        elif 'uniforme' in dist_str:
            match = re.search(r'uniforme\(([^,]+),\s*([^)]+)\)', dist_str)
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                return np.random.uniform(min_val, max_val)
        
        return 0.0
    
    def ejecutar(self, escenario):
        """Ejecuta el modelo con un escenario específico"""
        # Crear un contexto seguro con las variables del escenario
        contexto = escenario.copy()
        
        # Agregar librería math al contexto por si la fórmula la usa 
        contexto['math'] = math 
        contexto['__builtins__'] = {}
        
        try:
            # Limpiamos la fórmula. Si viene "retorno = a * b",  se queda solo con " a * b"
            formula_limpia = self.funcion
            if "=" in formula_limpia:
                formula_limpia = formula_limpia.split("=")[1].strip()
            
            # Evaluamos solo la parte matemática derecha
            resultado = eval(formula_limpia, {"__builtins__": {}}, contexto)
            return float(resultado)
            
        except Exception as e:
            # Imprimir la fórmula que falló para ayudar a depurar
            print(f"Error al ejecutar modelo: {e}")
            print(f"Fórmula intentada: {self.funcion}")
            print(f"Variables: {escenario}")
            return None
    
    def to_json(self):
        """Serializa el modelo a JSON para enviarlo por RabbitMQ"""
        return json.dumps({
            'funcion': self.funcion,
            'variables': self.variables,
            'num_simulaciones': self.num_simulaciones
        })
    
    @classmethod
    def from_json(cls, json_str):
        """Crea un modelo desde JSON"""
        if isinstance(json_str, dict):
            datos = json_str
        else:
            datos = json.loads(json_str)
            
        modelo = cls()
        modelo.funcion = datos['funcion']
        modelo.variables = datos['variables']
        modelo.num_simulaciones = datos['num_simulaciones']
        return modelo