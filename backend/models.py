import re
from datetime import datetime

class SolicitudDTE:
    def __init__(self, tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total):
        # Validar y parsear fecha
        match = re.search(r'\d{2}/\d{2}/\d{4}', tiempo)
        if not match:
            raise ValueError("Formato de fecha inválido")
        self.fecha = match.group(0)  # Formato DD/MM/YYYY
        self.referencia = referencia
        self.nit_emisor = nit_emisor
        self.nit_receptor = nit_receptor
        self.valor = float(valor)  # Guardar como float
        self.iva = float(iva)      # Guardar como float
        self.total = float(total)

    def validar(self, validador):
        # Validar NITs
        if not validador.validar(self.nit_emisor):
            return False, "NIT emisor inválido"
        if not validador.validar(self.nit_receptor):
            return False, "NIT receptor inválido"
        # Validar IVA
        expected_iva = round(self.valor * 0.12, 2)
        if abs(self.iva - expected_iva) > 0.01:
            return False, "IVA mal calculado"
        # Validar Total
        expected_total = round(self.valor + self.iva, 2)
        if abs(self.total - expected_total) > 0.01:
            return False, "Total mal calculado"
        return True, "Solicitud válida"

class ValidadorNIT:
    def validar(self, nit):
        if not nit or not re.match(r'^\d{1,20}[0-9K]$', nit):
            return False
        digits = nit[:-1]
        verificador = nit[-1]
        total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(digits)))
        mod = total % 11
        expected = 11 - mod
        if expected == 11:
            expected = 0
        elif expected == 10:
            return verificador == 'K'
        return verificador == str(expected)

class ListaSolicitudes:
    def __init__(self):
        self.solicitudes = []  # Lista de solicitudes aprobadas: {'solicitud': SolicitudDTE, 'codigo': str}
        self.referencias_por_fecha = {}  # Diccionario: fecha -> set de referencias
        self.facturas_recibidas_por_fecha = {}  # Diccionario: fecha -> int
        self.errores_por_fecha = {}  # Diccionario: fecha -> {tipo_error: int}

    def inicializar_fecha(self, fecha):
        if fecha not in self.referencias_por_fecha:
            self.referencias_por_fecha[fecha] = set()
            self.facturas_recibidas_por_fecha[fecha] = 0
            self.errores_por_fecha[fecha] = {
                "NIT_EMISOR": 0,
                "NIT_RECEPTOR": 0,
                "IVA": 0,
                "TOTAL": 0,
                "REFERENCIA_DUPLICADA": 0
            }

    def agregar(self, solicitud, autorizacion):
        self.inicializar_fecha(solicitud.fecha)
        # Verificar referencia única
        if solicitud.referencia in self.referencias_por_fecha[solicitud.fecha]:
            self.facturas_recibidas_por_fecha[solicitud.fecha] += 1
            self.errores_por_fecha[solicitud.fecha]["REFERENCIA_DUPLICADA"] += 1
            return False, "Referencia duplicada"
        # Validar solicitud
        ok, msg = solicitud.validar(ValidadorNIT())
        self.facturas_recibidas_por_fecha[solicitud.fecha] += 1
        if not ok:
            error_key = {
                "NIT emisor inválido": "NIT_EMISOR",
                "NIT receptor inválido": "NIT_RECEPTOR",
                "IVA mal calculado": "IVA",
                "Total mal calculado": "TOTAL"
            }.get(msg, "TOTAL")
            self.errores_por_fecha[solicitud.fecha][error_key] += 1
            return False, msg
        # Generar autorización
        codigo = autorizacion.generar(solicitud.fecha)
        self.solicitudes.append({'solicitud': solicitud, 'codigo': codigo})
        self.referencias_por_fecha[solicitud.fecha].add(solicitud.referencia)
        return True, "Procesada correctamente"

    def estadisticas(self, fecha):
        self.inicializar_fecha(fecha)
        facturas_correctas = sum(1 for s in self.solicitudes if s['solicitud'].fecha == fecha)
        emisores = set(s['solicitud'].nit_emisor for s in self.solicitudes if s['solicitud'].fecha == fecha)
        receptores = set(s['solicitud'].nit_receptor for s in self.solicitudes if s['solicitud'].fecha == fecha)
        aprobaciones = [
            {
                'referencia': s['solicitud'].referencia,
                'nit_emisor': s['solicitud'].nit_emisor,
                'iva': s['solicitud'].iva,  # Usar el valor almacenado en SolicitudDTE
                'valor': s['solicitud'].valor,  # Usar el valor almacenado en SolicitudDTE
                'codigo_aprobacion': s['codigo']
            }
            for s in self.solicitudes if s['solicitud'].fecha == fecha
        ]
        return {
            'facturas_recibidas': self.facturas_recibidas_por_fecha[fecha],
            'errores': self.errores_por_fecha[fecha],
            'facturas_correctas': facturas_correctas,
            'cantidad_emisores': len(emisores),
            'cantidad_receptores': len(receptores),
            'aprobaciones': aprobaciones,
            'total_aprobaciones': len(aprobaciones)
        }

class Autorizacion:
    def __init__(self):
        self.correlativos = {}

    def generar(self, fecha):
        if fecha not in self.correlativos:
            self.correlativos[fecha] = 0
        self.correlativos[fecha] += 1
        fecha_parts = fecha.split('/')
        yyyy = fecha_parts[2]
        mm = fecha_parts[1]
        dd = fecha_parts[0]
        correlativo = f"{self.correlativos[fecha]:08d}"
        return f"{yyyy}{mm}{dd}{correlativo}"