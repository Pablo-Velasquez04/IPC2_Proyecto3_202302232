import re  # Importa el módulo de expresiones regulares para trabajar con patrones de texto.
from datetime import datetime  # Importa la clase datetime para trabajar con fechas y horas.

# Define una clase para representar una solicitud de DTE (Documento Tributario Electrónico).
class SolicitudDTE:
    def __init__(self, tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total):
        # Inicializa los atributos de la solicitud con valores proporcionados o predeterminados.
        self.tiempo = tiempo or ""  # Tiempo en formato de texto.
        self.referencia = referencia or ""  # Referencia única de la solicitud.
        self.nit_emisor = nit_emisor or ""  # NIT del emisor.
        self.nit_receptor = nit_receptor or ""  # NIT del receptor.
        self.valor_str = valor or "0.00"  # Valor en formato de texto.
        self.iva_str = iva or "0.00"  # IVA en formato de texto.
        self.total_str = total or "0.00"  # Total en formato de texto.
        try:
            # Convierte los valores de texto a números flotantes.
            self.valor = float(self.valor_str)
            self.iva = float(self.iva_str)
            self.total = float(self.total_str)
        except ValueError:
            # Si ocurre un error en la conversión, asigna valores predeterminados.
            self.valor = 0.0
            self.iva = 0.0
            self.total = 0.0
        # Extrae la fecha del atributo `tiempo`.
        self.fecha = self._extraer_fecha()

    # Método privado para extraer la fecha del atributo `tiempo`.
    def _extraer_fecha(self):
        if not self.tiempo:  # Si no hay tiempo, retorna None.
            return None
        # Busca un patrón de fecha en el formato DD/MM/YYYY.
        match = re.match(r'.*?(\d{2}/\d{2}/\d{4})', self.tiempo)
        return match.group(1) if match else None  # Retorna la fecha encontrada o None.

    # Valida la solicitud utilizando un validador de NIT.
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
        # Valida el formato y el valor del atributo `valor`.
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
        expected_total = round(self.valor + expected_iva, 2)
        print(f"Expected Total: {expected_total}, Actual: {self.total}")
        if abs(self.total - expected_total) > 0.01:
            errores.append("Total mal calculado")
        print(f"Errores detectados: {errores}")
        return len(errores) == 0, errores  # Retorna si es válida y la lista de errores.

# Clase para validar NITs (Número de Identificación Tributaria).
class ValidadorNIT:
    def validar(self, nit):
        # Verifica si el NIT tiene un formato válido.
        if not nit or not re.match(r'^\d{1,20}[0-9K]$', nit):
            return False
        digits = nit[:-1]  # Obtiene los dígitos del NIT (sin el verificador).
        verificador = nit[-1]  # Obtiene el dígito verificador.
        # Calcula el total según el algoritmo de validación del NIT.
        total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(digits)))
        mod = total % 11  # Calcula el módulo 11.
        expected = 11 - mod  # Calcula el valor esperado.
        if expected == 11:
            expected = 0
        elif expected == 10:
            return verificador == 'K'  # Si es 10, el verificador debe ser 'K'.
        return verificador == str(expected)  # Compara con el valor esperado.

# Clase para manejar una lista de solicitudes de DTE.
class ListaSolicitudes:
    def __init__(self):
        self.solicitudes = []  # Lista de solicitudes procesadas.
        self.referencias_por_fecha = {}  # Referencias únicas por fecha.
        self.errores_por_fecha = {}  # Errores agrupados por fecha.
        self.facturas_recibidas_por_fecha = {}  # Cantidad de facturas recibidas por fecha.
        self.facturas_correctas_por_fecha = {}  # Cantidad de facturas correctas por fecha.
        self.emisores_por_fecha = {}  # Emisores únicos por fecha.
        self.receptores_por_fecha = {}  # Receptores únicos por fecha.

    # Inicializa los datos para una fecha específica.
    def inicializar_fecha(self, fecha):
        if fecha not in self.referencias_por_fecha:
            self.referencias_por_fecha[fecha] = set()
            self.errores_por_fecha[fecha] = {
                "NIT_EMISOR": 0,
                "NIT_RECEPTOR": 0,
                "IVA": 0,
                "TOTAL": 0,
                "REFERENCIA_DUPLICADA": 0
            }
            self.facturas_recibidas_por_fecha[fecha] = 0
            self.facturas_correctas_por_fecha[fecha] = 0
            self.emisores_por_fecha[fecha] = set()
            self.receptores_por_fecha[fecha] = set()

    # Agrega una solicitud a la lista y la procesa.
    def agregar(self, solicitud, autorizacion):
        fecha = solicitud.fecha  # Obtiene la fecha de la solicitud.
        self.inicializar_fecha(fecha)  # Inicializa los datos para la fecha.
        self.facturas_recibidas_por_fecha[fecha] += 1  # Incrementa el contador de facturas recibidas.
        print(f"Procesando DTE - Referencia: {solicitud.referencia}, Fecha: {fecha}")

        # Valida la solicitud.
        es_valida, errores = solicitud.es_valida(ValidadorNIT())
        print(f"Validación resultado: {es_valida}, Errores: {errores}")
        for error in errores:
            if "NIT emisor" in error:
                self.errores_por_fecha[fecha]["NIT_EMISOR"] += 1
            elif "NIT receptor" in error:
                self.errores_por_fecha[fecha]["NIT_RECEPTOR"] += 1
            elif "IVA" in error:
                self.errores_por_fecha[fecha]["IVA"] += 1
            elif "Total" in error:
                self.errores_por_fecha[fecha]["TOTAL"] += 1

        # Verifica si la referencia ya existe (duplicada).
        duplicada = solicitud.referencia in self.referencias_por_fecha[fecha]
        if duplicada:
            self.errores_por_fecha[fecha]["REFERENCIA_DUPLICADA"] += 1
            print(f"Detectada duplicación: {solicitud.referencia}")

        # Agrega la referencia a la lista de referencias por fecha.
        self.referencias_por_fecha[fecha].add(solicitud.referencia)

        if duplicada:
            return False, "Referencia duplicada"  # Retorna error si es duplicada.
        if not es_valida:
            return False, errores[0] if errores else "Error desconocido"  # Retorna el primer error.

        # Si es válida, agrega la solicitud a la lista de solicitudes procesadas.
        self.solicitudes.append({
            "solicitud": solicitud,
            "codigo_aprobacion": autorizacion.generar(fecha)  # Genera un código de aprobación.
        })
        self.facturas_correctas_por_fecha[fecha] += 1  # Incrementa el contador de facturas correctas.
        self.emisores_por_fecha[fecha].add(solicitud.nit_emisor)  # Agrega el emisor a la lista.
        self.receptores_por_fecha[fecha].add(solicitud.nit_receptor)  # Agrega el receptor a la lista.
        return True, "Procesada correctamente"  # Retorna éxito.

    # Genera estadísticas para una fecha específica.
    def estadisticas(self, fecha):
        self.inicializar_fecha(fecha)  # Asegura que los datos para la fecha estén inicializados.
        aprobaciones = [
            {
                "referencia": s["solicitud"].referencia,
                "nit_emisor": s["solicitud"].nit_emisor,
                "iva": s["solicitud"].iva,
                "valor": s["solicitud"].valor,
                "codigo_aprobacion": s["codigo_aprobacion"]
            }
            for s in self.solicitudes if s["solicitud"].fecha == fecha
        ]
        return {
            "facturas_recibidas": self.facturas_recibidas_por_fecha[fecha],
            "errores": self.errores_por_fecha[fecha].copy(),
            "facturas_correctas": self.facturas_correctas_por_fecha[fecha],
            "cantidad_emisores": len(self.emisores_por_fecha[fecha]),
            "cantidad_receptores": len(self.receptores_por_fecha[fecha]),
            "aprobaciones": aprobaciones,
            "total_aprobaciones": len(aprobaciones)
        }

# Clase para generar códigos de autorización.
class Autorizacion:
    def __init__(self):
        self.correlativos = {}  # Diccionario para almacenar correlativos por fecha.

    # Genera un código de autorización único para una fecha.
    def generar(self, fecha):
        if fecha not in self.correlativos:
            self.correlativos[fecha] = 0  # Inicializa el correlativo si no existe.
        self.correlativos[fecha] += 1  # Incrementa el correlativo.
        fecha_parts = fecha.split('/')  # Divide la fecha en partes (DD/MM/YYYY).
        yyyy = fecha_parts[2]  # Año.
        mm = fecha_parts[1]  # Mes.
        dd = fecha_parts[0]  # Día.
        correlativo = f"{self.correlativos[fecha]:08d}"  # Formatea el correlativo con ceros a la izquierda.
        return f"{yyyy}{mm}{dd}{correlativo}"  # Retorna el código de autorización.