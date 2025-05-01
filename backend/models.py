import re
from datetime import datetime

class SolicitudDTE:
    def __init__(self, tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total):
        self.tiempo = tiempo or ""
        self.referencia = referencia or ""
        self.nit_emisor = nit_emisor or ""
        self.nit_receptor = nit_receptor or ""
        self.valor_str = valor or "0.00"
        self.iva_str = iva or "0.00"
        self.total_str = total or "0.00"
        try:
            self.valor = float(self.valor_str)
            self.iva = float(self.iva_str)
            self.total = float(self.total_str)
        except ValueError:
            self.valor = 0.0
            self.iva = 0.0
            self.total = 0.0
        self.fecha = self._extraer_fecha()

    def _extraer_fecha(self):
        if not self.tiempo:
            return None
        match = re.match(r'.*?(\d{2}/\d{2}/\d{4})', self.tiempo)
        return match.group(1) if match else None

    def es_valida(self, validador_nit):
        if not self.fecha:
            return False, "Fecha inválida"
        if not validador_nit.validar(self.nit_emisor):
            return False, "NIT emisor inválido"
        if not validador_nit.validar(self.nit_receptor):
            return False, "NIT receptor inválido"
        if not (0 <= len(self.referencia) <= 40):
            return False, "Referencia inválida"
        if not re.match(r'^\d+\.\d{2}$', self.valor_str) or self.valor <= 0:
            return False, "Valor inválido"
        if not re.match(r'^\d+\.\d{2}$', self.iva_str):
            return False, "IVA inválido"
        if not re.match(r'^\d+\.\d{2}$', self.total_str):
            return False, "Total inválido"
        expected_iva = round(self.valor * 0.12, 2)
        if abs(self.iva - expected_iva) > 0.01:
            return False, "IVA mal calculado"
        if abs(self.total - (self.valor + self.iva)) > 0.01:
            return False, "Total mal calculado"
        return True, ""

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
        self.solicitudes = []
        self.referencias_por_fecha = {}
        self.errores_por_fecha = {}  # Cambiado: errores por fecha
        self.facturas_recibidas_por_fecha = {}  # Cambiado: facturas recibidas por fecha
        self.facturas_correctas_por_fecha = {}  # Cambiado: facturas correctas por fecha
        self.emisores_por_fecha = {}  # Cambiado: emisores por fecha
        self.receptores_por_fecha = {}  # Cambiado: receptores por fecha

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

    def agregar(self, solicitud, autorizacion):
        fecha = solicitud.fecha
        self.inicializar_fecha(fecha)
        self.facturas_recibidas_por_fecha[fecha] += 1

        if solicitud.referencia in self.referencias_por_fecha[fecha]:
            self.errores_por_fecha[fecha]["REFERENCIA_DUPLICADA"] += 1
            return False, "Referencia duplicada"
        
        es_valida, mensaje = solicitud.es_valida(ValidadorNIT())
        if not es_valida:
            if "NIT emisor" in mensaje:
                self.errores_por_fecha[fecha]["NIT_EMISOR"] += 1
            elif "NIT receptor" in mensaje:
                self.errores_por_fecha[fecha]["NIT_RECEPTOR"] += 1
            elif "IVA" in mensaje:
                self.errores_por_fecha[fecha]["IVA"] += 1
            elif "Total" in mensaje:
                self.errores_por_fecha[fecha]["TOTAL"] += 1
            return False, mensaje
        
        self.referencias_por_fecha[fecha].add(solicitud.referencia)
        self.solicitudes.append({
            "solicitud": solicitud,
            "codigo_aprobacion": autorizacion.generar(fecha)
        })
        self.facturas_correctas_por_fecha[fecha] += 1
        self.emisores_por_fecha[fecha].add(solicitud.nit_emisor)
        self.receptores_por_fecha[fecha].add(solicitud.nit_receptor)
        return True, ""

    def estadisticas(self, fecha):
        self.inicializar_fecha(fecha)
        return {
            "fecha": fecha,
            "facturas_recibidas": self.facturas_recibidas_por_fecha[fecha],
            "errores": self.errores_por_fecha[fecha].copy(),
            "facturas_correctas": self.facturas_correctas_por_fecha[fecha],
            "cantidad_emisores": len(self.emisores_por_fecha[fecha]),
            "cantidad_receptores": len(self.receptores_por_fecha[fecha]),
            "aprobaciones": [
                {
                    "nit_emisor": s["solicitud"].nit_emisor,
                    "referencia": s["solicitud"].referencia,
                    "codigo_aprobacion": s["codigo_aprobacion"]
                } for s in self.solicitudes if s["solicitud"].fecha == fecha
            ],
            "total_aprobaciones": len([s for s in self.solicitudes if s["solicitud"].fecha == fecha])
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