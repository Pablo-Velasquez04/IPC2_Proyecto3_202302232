import re  # Importa el módulo de expresiones regulares para trabajar con patrones de texto.
from datetime import datetime  # Importa la clase datetime para trabajar con fechas y horas.

# Clase que representa una solicitud de DTE (Documento Tributario Electrónico).
class SolicitudDTE:
    def __init__(self, tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total):
        # Inicializa los atributos de la solicitud con valores proporcionados o valores predeterminados.
        self.tiempo = tiempo or ""  # Tiempo de la solicitud.
        self.referencia = referencia or ""  # Referencia única de la solicitud.
        self.nit_emisor = nit_emisor or ""  # NIT del emisor.
        self.nit_receptor = nit_receptor or ""  # NIT del receptor.
        self.valor_str = valor or "0.00"  # Valor de la solicitud como cadena.
        self.iva_str = iva or "0.00"  # IVA de la solicitud como cadena.
        self.total_str = total or "0.00"  # Total de la solicitud como cadena.
        try:
            # Convierte los valores de cadena a flotantes.
            self.valor = float(self.valor_str)
            self.iva = float(self.iva_str)
            self.total = float(self.total_str)
        except ValueError:
            # Si ocurre un error en la conversión, asigna valores predeterminados.
            self.valor = 0.0
            self.iva = 0.0
            self.total = 0.0
        self.fecha = self._extraer_fecha()  # Extrae la fecha del atributo `tiempo`.

    # Método privado para extraer la fecha del atributo `tiempo`.
    def _extraer_fecha(self):
        if not self.tiempo:  # Si no hay tiempo, retorna None.
            return None
        # Busca un patrón de fecha en formato DD/MM/YYYY en el atributo `tiempo`.
        match = re.match(r'.*?(\d{2}/\d{2}/\d{4})', self.tiempo)
        return match.group(1) if match else None  # Retorna la fecha encontrada o None.

    # Método para validar la solicitud utilizando un validador de NIT.
    def es_valida(self, validador_nit):
        errores = []  # Lista para almacenar errores de validación.
        print(f"Validando DTE - Referencia: {self.referencia}, Fecha: {self.fecha}")
        if not self.fecha:  # Verifica si la fecha es válida.
            errores.append("Fecha inválida")
        if not validador_nit.validar(self.nit_emisor):  # Valida el NIT del emisor.
            errores.append("NIT emisor inválido")
        if not validador_nit.validar(self.nit_receptor):  # Valida el NIT del receptor.
            errores.append("NIT receptor inválido")
        if not (0 <= len(self.referencia) <= 40):  # Verifica la longitud de la referencia.
            errores.append("Referencia inválida")
        # Valida el formato y valor del atributo `valor`.
        if not re.match(r'^\d+\.\d{2}$', self.valor_str) or self.valor <= 0:
            errores.append("Valor inválido")
        # Valida el formato del atributo `iva`.
        if not re.match(r'^\d+\.\d{2}$', self.iva_str):
            errores.append("IVA inválido")
        # Valida el formato del atributo `total`.
        if not re.match(r'^\d+\.\d{2}$', self.total_str):
            errores.append("Total inválido")
        # Calcula el IVA esperado y lo compara con el proporcionado.
        expected_iva = round(self.valor * 0.12, 2)
        print(f"Expected IVA: {expected_iva}, Actual: {self.iva}")
        if abs(self.iva - expected_iva) > 0.01:
            errores.append("IVA mal calculado")
        # Calcula el total esperado y lo compara con el proporcionado.
        expected_total = round(self.valor + self.iva, 2)
        print(f"Expected Total: {expected_total}, Actual: {self.total}")
        if abs(self.total - expected_total) > 0.01:
            errores.append("Total mal calculado")
        print(f"Errores detectados: {errores}")
        return len(errores) == 0, errores  # Retorna si es válida y la lista de errores.

# Clase para validar NITs.
class ValidadorNIT:
    def validar(self, nit):
        if not nit:  # Si el NIT está vacío, retorna False.
            return False
        # Conjunto de NITs válidos.
        valid_nits = {'637672K', '672681K', '326445', '5750814', '7378106'}
        return nit in valid_nits  # Verifica si el NIT está en el conjunto.

# Clase para manejar una lista de solicitudes de DTE.
class ListaSolicitudes:
    def __init__(self):
        self.solicitudes = []  # Lista de solicitudes procesadas.
        self.referencias_por_fecha = {}  # Referencias únicas por fecha.
        self.errores_por_fecha = {}  # Errores agrupados por fecha.
        self.facturas_recibidas_por_fecha = {}  # Cantidad de facturas recibidas por fecha.
        self.facturas_correctas_por_fecha = {}  # Cantidad de facturas correctas por fecha.
        self.emisores_por_fecha = {}  # Conjunto de emisores únicos por fecha.
        self.receptores_por_fecha = {}  # Conjunto de receptores únicos por fecha.

    # Método para inicializar estructuras de datos para una fecha específica.
    def inicializar_fecha(self, fecha):
        if fecha not in self.referencias_por_fecha:
            self.referencias_por_fecha[fecha] = set()  # Inicializa referencias únicas.
            self.errores_por_fecha[fecha] = {  # Inicializa contadores de errores.
                "NIT_EMISOR": 0,
                "NIT_RECEPTOR": 0,
                "IVA": 0,
                "TOTAL": 0,
                "REFERENCIA_DUPLICADA": 0
            }
            self.facturas_recibidas_por_fecha[fecha] = 0  # Inicializa contador de facturas recibidas.
            self.facturas_correctas_por_fecha[fecha] = 0  # Inicializa contador de facturas correctas.
            self.emisores_por_fecha[fecha] = set()  # Inicializa emisores únicos.
            self.receptores_por_fecha[fecha] = set()  # Inicializa receptores únicos.

    # Método para agregar una solicitud a la lista.
    def agregar(self, solicitud, autorizacion):
        fecha = solicitud.fecha  # Obtiene la fecha de la solicitud.
        if not fecha:  # Si la fecha es inválida, retorna un error.
            return False, "Fecha inválida"
        self.inicializar_fecha(fecha)  # Inicializa estructuras para la fecha si no existen.
        self.facturas_recibidas_por_fecha[fecha] += 1  # Incrementa el contador de facturas recibidas para la fecha.
        print(f"Procesando DTE - Referencia: {solicitud.referencia}, Fecha: {fecha}")  # Imprime información de la solicitud.

        # Verifica si la referencia ya existe para la fecha.
        duplicada = solicitud.referencia in self.referencias_por_fecha[fecha]  # Comprueba si la referencia ya fue procesada.
        self.referencias_por_fecha[fecha].add(solicitud.referencia)  # Agrega la referencia a las procesadas para la fecha.
        if duplicada:  # Si la referencia ya existe, registra un error.
            self.errores_por_fecha[fecha]["REFERENCIA_DUPLICADA"] += 1  # Incrementa el contador de referencias duplicadas.
            print(f"Detectada duplicación: {solicitud.referencia}")  # Imprime un mensaje indicando la duplicación.

        # Valida la solicitud.
        es_valida, errores = solicitud.es_valida(ValidadorNIT())  # Valida la solicitud utilizando el validador de NIT.
        print(f"Validación resultado: {es_valida}, Errores: {errores}")  # Imprime el resultado de la validación.

        # Procesa los errores detectados durante la validación.
        for error in errores:  # Itera sobre los errores encontrados.
            if "NIT emisor" in error:  # Si el error está relacionado con el NIT del emisor.
                self.errores_por_fecha[fecha]["NIT_EMISOR"] += 1  # Incrementa el contador de errores de NIT del emisor.
            elif "NIT receptor" in error:  # Si el error está relacionado con el NIT del receptor.
                self.errores_por_fecha[fecha]["NIT_RECEPTOR"] += 1  # Incrementa el contador de errores de NIT del receptor.
            elif "IVA" in error:  # Si el error está relacionado con el IVA.
                self.errores_por_fecha[fecha]["IVA"] += 1  # Incrementa el contador de errores de IVA.
            elif "Total" in error:  # Si el error está relacionado con el total.
                self.errores_por_fecha[fecha]["TOTAL"] += 1  # Incrementa el contador de errores de total.

        # Si la solicitud es duplicada o inválida, retorna un error.
        if duplicada or not es_valida:  # Comprueba si la solicitud es duplicada o tiene errores.
            return False, "Referencia duplicada" if duplicada else (errores[0] if errores else "Error desconocido")  # Retorna el error correspondiente.

        # Agrega la solicitud a la lista de solicitudes procesadas.
        self.solicitudes.append({
            "solicitud": solicitud,  # Agrega la solicitud.
            "codigo_aprobacion": autorizacion.generar(fecha)  # Genera y agrega un código de aprobación único.
        })
        self.facturas_correctas_por_fecha[fecha] += 1  # Incrementa el contador de facturas correctas para la fecha.
        self.emisores_por_fecha[fecha].add(solicitud.nit_emisor)  # Agrega el NIT del emisor a la lista de emisores únicos.
        self.receptores_por_fecha[fecha].add(solicitud.nit_receptor)  # Agrega el NIT del receptor a la lista de receptores únicos.
        return True, "Procesada correctamente"  # Retorna éxito indicando que la solicitud fue procesada correctamente.

    # Método para obtener estadísticas de las solicitudes por fecha.
    def estadisticas(self, fecha):
        # Inicializa las estructuras de datos para la fecha si no existen.
        self.inicializar_fecha(fecha)
        
        # Filtra las solicitudes aprobadas para la fecha especificada.
        aprobaciones = [
            {
                "referencia": s["solicitud"].referencia,  # Obtiene la referencia de la solicitud.
                "nit_emisor": s["solicitud"].nit_emisor,  # Obtiene el NIT del emisor de la solicitud.
                "iva": s["solicitud"].iva,  # Obtiene el IVA de la solicitud.
                "valor": s["solicitud"].valor,  # Obtiene el valor de la solicitud.
                "codigo_aprobacion": s["codigo_aprobacion"]  # Obtiene el código de aprobación generado.
            }
            for s in self.solicitudes if s["solicitud"].fecha == fecha  # Filtra las solicitudes por la fecha especificada.
        ]
        
        # Retorna un diccionario con estadísticas relacionadas con la fecha.
        return {
            "facturas_recibidas": self.facturas_recibidas_por_fecha[fecha],  # Cantidad de facturas recibidas en la fecha.
            "errores": self.errores_por_fecha[fecha].copy(),  # Copia de los errores registrados para la fecha.
            "facturas_correctas": self.facturas_correctas_por_fecha[fecha],  # Cantidad de facturas correctas en la fecha.
            "cantidad_emisores": len(self.emisores_por_fecha[fecha]),  # Número de emisores únicos en la fecha.
            "cantidad_receptores": len(self.receptores_por_fecha[fecha]),  # Número de receptores únicos en la fecha.
            "aprobaciones": aprobaciones,  # Lista de aprobaciones para la fecha.
            "total_aprobaciones": len(aprobaciones)  # Total de aprobaciones realizadas en la fecha.
        }

# Clase para generar códigos de autorización.
class Autorizacion:
    def __init__(self):
        self.correlativos = {}  # Diccionario para almacenar correlativos por fecha.

    # Método para generar un código de autorización único por fecha.
    def generar(self, fecha):
        if fecha not in self.correlativos:
            self.correlativos[fecha] = 0  # Inicializa el correlativo para la fecha.
        self.correlativos[fecha] += 1  # Incrementa el correlativo.
        fecha_parts = fecha.split('/')  # Divide la fecha en partes (DD/MM/YYYY).
        yyyy = fecha_parts[2]  # Año.
        mm = fecha_parts[1]  # Mes.
        dd = fecha_parts[0]  # Día.
        correlativo = f"{self.correlativos[fecha]:07d}"  # Formatea el correlativo con ceros a la izquierda.
        return f"{yyyy}{mm}{dd}{correlativo}"  # Retorna el código de autorización.