# Importa las bibliotecas necesarias para el funcionamiento del servidor y manejo de datos
from flask import Flask, request, jsonify, send_file  # Flask para crear la API
import xml.etree.ElementTree as ET  # Para manejar XML
from models import ListaSolicitudes, Autorizacion, SolicitudDTE  # Importa clases personalizadas
import os  # Para operaciones del sistema de archivos
import json  # Para manejar datos JSON
from io import BytesIO  # Para manejar flujos de datos en memoria
from reportlab.lib.pagesizes import letter  # Para definir el tamaño de página en ReportLab
from reportlab.pdfgen import canvas  # Para generar PDFs

# Inicializa la aplicación Flask
app = Flask(__name__)

# Instancia las clases personalizadas para manejar solicitudes y autorizaciones
lista_solicitudes = ListaSolicitudes()
autorizacion = Autorizacion()

# Función para dar formato de indentación a un árbol XML
def indent(elem, level=0):  # Define una función para aplicar indentación a un elemento XML
    i = "\n" + level * "  "  # Crea una cadena de nueva línea seguida de espacios según el nivel
    if len(elem):  # Verifica si el elemento tiene hijos
        if not elem.text or not elem.text.strip():  # Si el texto del elemento está vacío o solo tiene espacios
            elem.text = i + "  "  # Asigna la indentación al texto del elemento
        if not elem.tail or not elem.tail.strip():  # Si el texto de cierre (tail) está vacío o solo tiene espacios
            elem.tail = i  # Asigna la indentación al texto de cierre
        for child in elem:  # Itera sobre los hijos del elemento
            indent(child, level + 1)  # Llama recursivamente a la función para cada hijo, aumentando el nivel
        if not child.tail or not child.tail.strip():  # Si el texto de cierre del último hijo está vacío o solo tiene espacios
            child.tail = i  # Asigna la indentación al texto de cierre del último hijo
    else:  # Si el elemento no tiene hijos
        if level and (not elem.tail or not elem.tail.strip()):  # Si el nivel es mayor a 0 y el texto de cierre está vacío o solo tiene espacios
            elem.tail = i  # Asigna la indentación al texto de cierre

# Función para guardar las autorizaciones en un archivo XML
def save_to_xml():
    root = ET.Element("LISTAAUTORIZACIONES")  # Crea el elemento raíz del XML
    # Obtiene todas las fechas únicas de solicitudes y facturas recibidas
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes) | set(lista_solicitudes.facturas_recibidas_por_fecha.keys()))
    for fecha in fechas:
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas por fecha
        auth_elem = ET.SubElement(root, "AUTORIZACION")  # Crea un subelemento para cada autorización
        ET.SubElement(auth_elem, "FECHA").text = fecha  # Agrega la fecha
        ET.SubElement(auth_elem, "FACTURAS_RECIBIDAS").text = str(stats["facturas_recibidas"])  # Facturas recibidas
        errores_elem = ET.SubElement(auth_elem, "ERRORES")  # Subelemento para errores
        # Agrega detalles de errores
        ET.SubElement(errores_elem, "NIT_EMISOR").text = str(stats["errores"]["NIT_EMISOR"])
        ET.SubElement(errores_elem, "NIT_RECEPTOR").text = str(stats["errores"]["NIT_RECEPTOR"])
        ET.SubElement(errores_elem, "IVA").text = str(stats["errores"]["IVA"])
        ET.SubElement(errores_elem, "TOTAL").text = str(stats["errores"]["TOTAL"])
        ET.SubElement(errores_elem, "REFERENCIA_DUPLICADA").text = str(stats["errores"]["REFERENCIA_DUPLICADA"])
        ET.SubElement(auth_elem, "FACTURAS_CORRECTAS").text = str(stats["facturas_correctas"])  # Facturas correctas
        ET.SubElement(auth_elem, "CANTIDAD_EMISORES").text = str(stats["cantidad_emisores"])  # Cantidad de emisores
        ET.SubElement(auth_elem, "CANTIDAD_RECEPTORES").text = str(stats["cantidad_receptores"])  # Cantidad de receptores
        listado_elem = ET.SubElement(auth_elem, "LISTADO_AUTORIZACIONES")  # Listado de autorizaciones
        for aprobacion in stats["aprobaciones"]:
            aprob_elem = ET.SubElement(listado_elem, "APROBACION")  # Detalles de cada aprobación
            nit_emisor_elem = ET.SubElement(aprob_elem, "NIT_EMISOR")
            nit_emisor_elem.set("ref", aprobacion["referencia"])  # Referencia de la aprobación
            nit_emisor_elem.text = aprobacion["nit_emisor"]  # NIT del emisor
            ET.SubElement(aprob_elem, "CODIGO_APROBACION").text = aprobacion["codigo_aprobacion"]  # Código de aprobación
        ET.SubElement(listado_elem, "TOTAL_APROBACIONES").text = str(stats["total_aprobaciones"])  # Total de aprobaciones
    
    indent(root)  # Aplica formato al XML
    tree = ET.ElementTree(root)  # Crea el árbol XML
    tree.write("autorizaciones.xml", encoding="utf-8", xml_declaration=True)  # Guarda el archivo XML
    with open("autorizaciones.xml", "r", encoding="utf-8") as f:
        return f.read()  # Devuelve el contenido del archivo XML

# Ruta para cargar datos desde un archivo XML
@app.route('/cargar', methods=['POST'])  # Define una ruta para cargar datos desde un archivo XML usando el método POST
def cargar():
    xml_data = None  # Inicializa la variable para almacenar los datos XML
    try:
        # Verifica si el XML se envió como texto o archivo
        if 'xml' in request.form:  # Si el XML se envió como texto en el formulario
            xml_data = request.form['xml']  # Obtiene el contenido del XML
        elif 'xml_file' in request.files:  # Si el XML se envió como archivo
            xml_file = request.files['xml_file']  # Obtiene el archivo enviado
            xml_data = xml_file.read().decode('utf-8')  # Lee y decodifica el contenido del archivo
        else:  # Si no se proporcionó ni texto ni archivo
            return jsonify({"error": "No se proporcionó XML ni archivo"}), 400  # Devuelve un error

        root = ET.fromstring(xml_data)  # Parsea el contenido del XML y obtiene el elemento raíz
        for dte in root.findall('.//DTE'):  # Itera sobre cada elemento DTE en el XML
            # Extrae los datos del DTE
            tiempo = dte.find('TIEMPO').text if dte.find('TIEMPO') is not None else ""  # Obtiene el tiempo o un valor vacío
            referencia = dte.find('REFERENCIA').text if dte.find('REFERENCIA') is not None else ""  # Obtiene la referencia o un valor vacío
            nit_emisor = dte.find('NIT_EMISOR').text if dte.find('NIT_EMISOR') is not None else ""  # Obtiene el NIT del emisor o un valor vacío
            nit_receptor = dte.find('NIT_RECEPTOR').text if dte.find('NIT_RECEPTOR') is not None else ""  # Obtiene el NIT del receptor o un valor vacío
            valor = dte.find('VALOR').text if dte.find('VALOR') is not None else "0.00"  # Obtiene el valor o un valor predeterminado
            iva = dte.find('IVA').text if dte.find('IVA') is not None else "0.00"  # Obtiene el IVA o un valor predeterminado
            total = dte.find('TOTAL').text if dte.find('TOTAL') is not None else "0.00"  # Obtiene el total o un valor predeterminado
            
            # Crea una solicitud DTE con los datos extraídos
            solicitud = SolicitudDTE(tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total)  # Instancia una solicitud DTE
            if solicitud.fecha:  # Verifica si la fecha de la solicitud es válida
                result, message = lista_solicitudes.agregar(solicitud, autorizacion)  # Intenta agregar la solicitud a la lista
                print(f"Resultado de agregar: {result}, Mensaje: {message}")  # Imprime el resultado y mensaje
            else:  # Si la fecha no es válida
                print(f"Solicitud ignorada por fecha inválida: {tiempo}")  # Imprime un mensaje indicando que se ignoró la solicitud

        autorizaciones_content = save_to_xml()  # Guarda las autorizaciones en un archivo XML y obtiene su contenido
        return autorizaciones_content, 200, {'Content-Type': 'text/xml'}  # Devuelve el contenido del XML con un código 200

    except ET.ParseError:  # Si ocurre un error al parsear el XML
        return jsonify({"error": "Error al parsear el XML"}), 400  # Devuelve un error con código 400
    except Exception as e:  # Si ocurre cualquier otro error
        return jsonify({"error": str(e)}), 500  # Devuelve el error con código 500

# Ruta para consultar las estadísticas de las autorizaciones
@app.route('/consultar', methods=['GET'])  # Define una ruta para consultar estadísticas, accesible mediante el método GET
def consultar():
    # Obtiene todas las fechas únicas de solicitudes y facturas recibidas
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes) | set(lista_solicitudes.facturas_recibidas_por_fecha.keys()))
    result = {"LISTAAUTORIZACIONES": []}  # Inicializa el resultado como un diccionario con una lista vacía

    for fecha in fechas:  # Itera sobre cada fecha única
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene las estadísticas correspondientes a la fecha
        # Crea un diccionario con los datos de la autorización para la fecha actual
        autorizacion_data = {
            "FECHA": fecha,  # Fecha de las estadísticas
            "FACTURAS_RECIBIDAS": stats["facturas_recibidas"],  # Número de facturas recibidas
            "ERRORES": stats["errores"],  # Detalles de los errores encontrados
            "FACTURAS_CORRECTAS": stats["facturas_correctas"],  # Número de facturas correctas
            "CANTIDAD_EMISORES": stats["cantidad_emisores"],  # Cantidad de emisores únicos
            "CANTIDAD_RECEPTORES": stats["cantidad_receptores"],  # Cantidad de receptores únicos
            "LISTADO_AUTORIZACIONES": {  # Detalles de las autorizaciones
                "APROBACION": [  # Lista de aprobaciones
                    {
                        "NIT_EMISOR": {"ref": a["referencia"], "value": a["nit_emisor"]},  # NIT del emisor con su referencia
                        "CODIGO_APROBACION": a["codigo_aprobacion"],  # Código de aprobación
                        "IVA": a["iva"],  # IVA de la aprobación
                        "VALOR": a["valor"],  # Valor de la aprobación
                        "TOTAL": a["iva"] + a["valor"]  # Total (IVA + Valor)
                    }
                    for a in stats["aprobaciones"]  # Itera sobre cada aprobación en las estadísticas
                ],
                "TOTAL_APROBACIONES": stats["total_aprobaciones"]  # Total de aprobaciones para la fecha
            }
        }
        result["LISTAAUTORIZACIONES"].append(autorizacion_data)  # Agrega los datos de la autorización al resultado

    return jsonify(result)  # Devuelve el resultado como una respuesta JSON

# Ruta para obtener un resumen del IVA por fecha y emisor
@app.route('/iva_summary', methods=['GET'])  # Define una ruta para obtener un resumen del IVA, accesible mediante el método GET
def iva_summary_api():
    # Obtiene todas las fechas únicas de solicitudes
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))
    iva_data = {}  # Inicializa un diccionario para almacenar los datos del IVA

    for fecha in fechas:  # Itera sobre cada fecha única
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene las estadísticas correspondientes a la fecha
        for aprob in stats["aprobaciones"]:  # Itera sobre cada aprobación en las estadísticas
            nit = aprob["nit_emisor"]  # Obtiene el NIT del emisor
            iva = float(aprob["iva"])  # Convierte el IVA de la aprobación a un valor flotante
            if fecha not in iva_data:  # Si la fecha no está en el diccionario de datos del IVA
                iva_data[fecha] = {}  # Inicializa un subdiccionario para la fecha
            # Suma el IVA al NIT correspondiente en la fecha actual
            iva_data[fecha][nit] = iva_data[fecha].get(nit, 0) + iva

    return jsonify(iva_data)  # Devuelve los datos del IVA como una respuesta JSON

# Ruta para obtener un resumen de valores en un rango de fechas
@app.route('/range_summary', methods=['POST'])  # Define una ruta para obtener un resumen de valores en un rango de fechas, accesible mediante el método POST
def range_summary_api():
    data = request.get_json()  # Obtiene los datos enviados en formato JSON en la solicitud
    start_date = data.get('start_date')  # Extrae la fecha de inicio del rango
    end_date = data.get('end_date')  # Extrae la fecha de fin del rango
    value_type = data.get('value_type', 'total')  # Extrae el tipo de valor a calcular ('total' por defecto)
    result = []  # Inicializa una lista para almacenar los resultados
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))  # Obtiene todas las fechas únicas de las solicitudes, ordenadas
    for fecha in fechas:  # Itera sobre cada fecha única
        if start_date <= fecha <= end_date:  # Verifica si la fecha está dentro del rango especificado
            stats = lista_solicitudes.estadisticas(fecha)  # Obtiene las estadísticas correspondientes a la fecha
            total_value = sum(a["valor"] + a["iva"] for a in stats["aprobaciones"])  # Calcula el valor total (valor + IVA) de las aprobaciones
            # Calcula el valor según el tipo especificado ('total' o sin IVA)
            value = total_value if value_type == 'total' else total_value - sum(a["iva"] for a in stats["aprobaciones"])
            result.append({"date": fecha, "value": value})  # Agrega el resultado (fecha y valor) a la lista
    return jsonify(result)  # Devuelve los resultados como una respuesta JSON

# Ruta para obtener datos para gráficos
@app.route('/graph_data', methods=['GET'])  # Define una ruta en la aplicación Flask para la URL '/graph_data' que acepta solicitudes GET.
def graph_data():  # Define la función que se ejecutará cuando se acceda a la ruta '/graph_data'.
    # Obtiene una lista de fechas únicas de las solicitudes en 'lista_solicitudes.solicitudes' y las ordena.
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))
    
    # Inicializa un diccionario para almacenar los datos del gráfico.
    # 'labels' contendrá las fechas y 'data' será una lista vacía que se llenará más adelante.
    graph_data = {"labels": fechas, "data": []}
    
    # Itera sobre cada fecha en la lista de fechas ordenadas.
    for fecha in fechas:
        # Obtiene las estadísticas para la fecha actual llamando al método 'estadisticas' de 'lista_solicitudes'.
        stats = lista_solicitudes.estadisticas(fecha)
        
        # Calcula el total sumando el valor y el IVA de cada aprobación en las estadísticas.
        total = sum(a["valor"] + a["iva"] for a in stats["aprobaciones"])
        
        # Agrega el total calculado a la lista 'data' en el diccionario 'graph_data'.
        graph_data["data"].append(total)
    
    # Devuelve el diccionario 'graph_data' como una respuesta JSON.
    return jsonify(graph_data)

# Ruta para generar un reporte en PDF
@app.route('/pdf_report', methods=['GET'])  # Define una ruta para generar un reporte en PDF, accesible mediante el método GET
def pdf_report():  # Define la función que se ejecutará cuando se acceda a la ruta '/pdf_report'
    buffer = BytesIO()  # Crea un buffer en memoria para almacenar el contenido del PDF
    p = canvas.Canvas(buffer, pagesize=letter)  # Inicializa un lienzo para el PDF con tamaño de página carta
    p.drawString(100, 750, "Reporte de Autorizaciones")  # Escribe el título del reporte en el PDF
    y = 700  # Define la posición vertical inicial para el contenido del PDF
    # Obtiene una lista de fechas únicas de las solicitudes y las ordena
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))
    for fecha in fechas:  # Itera sobre cada fecha única
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene las estadísticas correspondientes a la fecha
        p.drawString(100, y, f"Fecha: {fecha}")  # Escribe la fecha en el PDF
        p.drawString(100, y - 20, f"Facturas Recibidas: {stats['facturas_recibidas']}")  # Escribe el número de facturas recibidas
        p.drawString(100, y - 40, f"Facturas Correctas: {stats['facturas_correctas']}")  # Escribe el número de facturas correctas
        y -= 60  # Reduce la posición vertical para el siguiente contenido
        if stats["aprobaciones"]:  # Verifica si hay aprobaciones en las estadísticas
            p.drawString(100, y, "Aprobaciones:")  # Escribe el encabezado de aprobaciones
            y -= 20  # Reduce la posición vertical
            for aprob in stats["aprobaciones"]:  # Itera sobre cada aprobación
                # Escribe los detalles de la aprobación en el PDF
                p.drawString(120, y, f"NIT Emisor: {aprob['nit_emisor']} (Ref: {aprob['referencia']})")
                p.drawString(120, y - 20, f"Código: {aprob['codigo_aprobacion']}")
                p.drawString(120, y - 40, f"IVA: {aprob['iva']}")
                p.drawString(120, y - 60, f"Valor: {aprob['valor']}")
                y -= 80  # Reduce la posición vertical para la siguiente aprobación
                if y < 100:  # Verifica si la posición vertical es demasiado baja para continuar en la misma página
                    p.showPage()  # Crea una nueva página en el PDF
                    y = 750  # Restablece la posición vertical inicial
        else:  # Si no hay aprobaciones
            p.drawString(100, y, "No hay aprobaciones.")  # Escribe un mensaje indicando que no hay aprobaciones
            y -= 20  # Reduce la posición vertical
        if y < 100:  # Verifica si la posición vertical es demasiado baja para continuar en la misma página
            p.showPage()  # Crea una nueva página en el PDF
            y = 750  # Restablece la posición vertical inicial
    p.showPage()  # Finaliza la última página del PDF
    p.save()  # Guarda el contenido del PDF en el buffer
    buffer.seek(0)  # Restablece el puntero del buffer al inicio
    # Devuelve el archivo PDF generado como respuesta, con el nombre 'reporte.pdf'
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='reporte.pdf')

# Ruta para reiniciar el sistema
@app.route('/reset', methods=['POST'])
def reset():
    global lista_solicitudes, autorizacion
    lista_solicitudes = ListaSolicitudes()  # Reinicia la lista de solicitudes
    autorizacion = Autorizacion()  # Reinicia las autorizaciones
    if os.path.exists("autorizaciones.xml"):  # Elimina el archivo XML si existe
        os.remove("autorizaciones.xml")
    return jsonify({"message": "Sistema reseteado correctamente"}), 200

# Punto de entrada principal para ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Ejecuta el servidor en modo debug en el puerto 5000