from models import SolicitudDTE, ValidadorNIT, ListaSolicitudes

validador = ValidadorNIT()
solicitud = SolicitudDTE("Guatemala, 15/01/2025 15:25", "A1990", "737810K", "123456K", "100.00", "12.00", "112.00")
lista = ListaSolicitudes()

# Probar validación
es_valida, mensaje = solicitud.es_valida(validador)
print(f"Solicitud válida: {es_valida}, Mensaje: {mensaje}")

# Probar referencia única
ok, msg = lista.agregar(solicitud)
print(f"Agregada: {ok}, Mensaje: {msg}")