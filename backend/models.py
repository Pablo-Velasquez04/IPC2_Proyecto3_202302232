import re
from datetime import datetime

class SolicitudDTE:
    def __init__(self, tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total):
        self.tiempo = tiempo or ""
        self.referencia = referencia or ""
        self.nit_emisor = nit_emisor or ""
        self.nit_receptor = nit_receptor or ""
        # Almacenar valores originales como strings
        self.valor_str = valor or "0.00"
        self.iva_str = iva or "0.00"
        self.total_str = total or "0.00"
        # Convertir a float para cálculos
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
        if not validador_nit.validar(self.nit_emisor) or not validador_nit.validar(self.nit_receptor):
            return False, "NIT inválido"
        if not (0 <= len(self.referencia) <= 40):
            return False, "Referencia inválida"
        # Validar formato de los valores originales
        if not re.match(r'^\d+\.\d{2}$', self.valor_str) or self.valor <= 0:
            return False, "Valor inválido"
        if not re.match(r'^\d+\.\d{2}$', self.iva_str):
            return False, "IVA inválido"
        if not re.match(r'^\d+\.\d{2}$', self.total_str):
            return False, "Total inválido"
        # Validar cálculos
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

    def agregar(self, solicitud):
        fecha = solicitud.fecha
        if fecha not in self.referencias_por_fecha:
            self.referencias_por_fecha[fecha] = set()
        if solicitud.referencia in self.referencias_por_fecha[fecha]:
            return False, "Referencia duplicada"
        self.referencias_por_fecha[fecha].add(solicitud.referencia)
        self.solicitudes.append(solicitud)
        return True, ""

class Autorizacion:
    def __init__(self):
        self.correlativos = {}

    def generar(self, fecha):
        if fecha not in self.correlativos:
            self.correlativos[fecha] = 0
        self.correlativos[fecha] += 1
        return f"{fecha.replace('/', '')}{self.correlativos[fecha]:08d}"