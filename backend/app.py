from flask import Flask, request, jsonify, send_file  # Importa las funciones necesarias de Flask para crear la aplicación web.
import xml.etree.ElementTree as ET  # Importa el módulo para trabajar con XML.
from models import ListaSolicitudes, Autorizacion, SolicitudDTE  # Importa las clases personalizadas del módulo models.
import os  # Importa el módulo para interactuar con el sistema operativo.
import json  # Importa el módulo para trabajar con datos JSON.
from io import BytesIO  # Importa BytesIO para manejar flujos de datos en memoria.
from reportlab.lib.pagesizes import letter  # Importa el tamaño de página carta para generar PDFs.
from reportlab.pdfgen import canvas  # Importa canvas para generar PDFs.

app = Flask(__name__)  # Crea una instancia de la aplicación Flask.

# Inicializa las estructuras de datos necesarias.
lista_solicitudes = ListaSolicitudes()  # Lista para almacenar solicitudes.
autorizacion = Autorizacion()  # Objeto para manejar autorizaciones.

# Función para dar formato de indentación a un árbol XML.
def indent(elem, level=0):
    i = "\n" + level * "  "  # Define el nivel de indentación.
    if len(elem):  # Si el elemento tiene hijos.
        if not elem.text or not elem.text.strip():  # Si no tiene texto, agrega indentación.
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():  # Si no tiene texto de cola, agrega indentación.
            elem.tail = i
        for child in elem:  # Recorre los hijos y aplica recursivamente.
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():  # Ajusta la cola del último hijo.
            child.tail = i
    else:  # Si no tiene hijos.
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# Función para guardar datos en un archivo XML.
def save_to_xml():
    root = ET.Element("LISTAAUTORIZACIONES")  # Crea el elemento raíz del XML.
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes) | set(lista_solicitudes.facturas_recibidas_por_fecha.keys()))  # Obtiene las fechas únicas.
    for fecha in fechas:  # Itera sobre las fechas.
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas para la fecha.
        auth_elem = ET.SubElement(root, "AUTORIZACION")  # Crea un subelemento para la autorización.
        ET.SubElement(auth_elem, "FECHA").text = fecha  # Agrega la fecha.
        ET.SubElement(auth_elem, "FACTURAS_RECIBIDAS").text = str(stats["facturas_recibidas"])  # Agrega el número de facturas recibidas.
        errores_elem = ET.SubElement(auth_elem, "ERRORES")  # Crea un subelemento para errores.
        # Agrega detalles de errores.
        ET.SubElement(errores_elem, "NIT_EMISOR").text = str(stats["errores"]["NIT_EMISOR"])
        ET.SubElement(errores_elem, "NIT_RECEPTOR").text = str(stats["errores"]["NIT_RECEPTOR"])
        ET.SubElement(errores_elem, "IVA").text = str(stats["errores"]["IVA"])
        ET.SubElement(errores_elem, "TOTAL").text = str(stats["errores"]["TOTAL"])
        ET.SubElement(errores_elem, "REFERENCIA_DUPLICADA").text = str(stats["errores"]["REFERENCIA_DUPLICADA"])
        ET.SubElement(auth_elem, "FACTURAS_CORRECTAS").text = str(stats["facturas_correctas"])  # Agrega el número de facturas correctas.
        ET.SubElement(auth_elem, "CANTIDAD_EMISORES").text = str(stats["cantidad_emisores"])  # Agrega la cantidad de emisores.
        ET.SubElement(auth_elem, "CANTIDAD_RECEPTORES").text = str(stats["cantidad_receptores"])  # Agrega la cantidad de receptores.
        listado_elem = ET.SubElement(auth_elem, "LISTADO_AUTORIZACIONES")  # Crea un subelemento para el listado de autorizaciones.
        for aprobacion in stats["aprobaciones"]:  # Itera sobre las aprobaciones.
            aprob_elem = ET.SubElement(listado_elem, "APROBACION")  # Crea un subelemento para cada aprobación.
            dte_elem = ET.SubElement(aprob_elem, "DTE")  # Crea un subelemento para el DTE.
            nit_emisor_elem = ET.SubElement(dte_elem, "NIT_EMISOR")  # Agrega el NIT del emisor.
            nit_emisor_elem.set("ref", aprobacion["referencia"])  # Agrega el atributo de referencia.
            nit_emisor_elem.text = aprobacion["nit_emisor"]  # Agrega el texto del NIT emisor.
            # Agrega más detalles del DTE.
            ET.SubElement(dte_elem, "CODIGO_APROBACION").text = aprobacion["codigo_aprobacion"]
            ET.SubElement(dte_elem, "IVA").text = str(aprobacion["iva"])
            ET.SubElement(dte_elem, "VALOR").text = str(aprobacion["valor"])
            ET.SubElement(dte_elem, "TOTAL").text = str(aprobacion["iva"] + aprobacion["valor"])
        ET.SubElement(listado_elem, "TOTAL_APROBACIONES").text = str(stats["total_aprobaciones"])  # Agrega el total de aprobaciones.
    
    indent(root)  # Aplica indentación al XML.
    tree = ET.ElementTree(root)  # Crea el árbol XML.
    tree.write("autorizaciones.xml", encoding="utf-8", xml_declaration=True)  # Escribe el archivo XML.
    with open("autorizaciones.xml", "r", encoding="utf-8") as f:  # Lee el archivo XML.
        return f.read()  # Devuelve el contenido del archivo.

# Ruta para cargar datos desde un archivo XML.
@app.route('/cargar', methods=['POST'])
def cargar():
    xml_data = None  # Inicializa la variable para los datos XML.
    try:
        if 'xml' in request.form:  # Si el XML está en el formulario.
            xml_data = request.form['xml']
        elif 'xml_file' in request.files:  # Si el XML está en un archivo.
            xml_file = request.files['xml_file']
            xml_data = xml_file.read().decode('utf-8')  # Lee y decodifica el archivo.
        else:
            return jsonify({"error": "No se proporcionó XML ni archivo"}), 400  # Devuelve un error si no hay XML.

        root = ET.fromstring(xml_data)  # Parsea el XML.
        for dte in root.findall('.//DTE'):  # Busca todos los elementos DTE.
            # Extrae los datos del DTE.
            tiempo = dte.find('TIEMPO').text if dte.find('TIEMPO') is not None else ""
            referencia = dte.find('REFERENCIA').text if dte.find('REFERENCIA') is not None else ""
            nit_emisor = dte.find('NIT_EMISOR').text if dte.find('NIT_EMISOR') is not None else ""
            nit_receptor = dte.find('NIT_RECEPTOR').text if dte.find('NIT_RECEPTOR') is not None else ""
            valor = dte.find('VALOR').text if dte.find('VALOR') is not None else "0.00"
            iva = dte.find('IVA').text if dte.find('IVA') is not None else "0.00"
            total = dte.find('TOTAL').text if dte.find('TOTAL') is not None else "0.00"
            
            solicitud = SolicitudDTE(tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total)  # Crea una solicitud DTE.
            if solicitud.fecha:  # Si la fecha es válida.
                result, message = lista_solicitudes.agregar(solicitud, autorizacion)  # Agrega la solicitud a la lista.
                print(f"Resultado de agregar: {result}, Mensaje: {message}")  # Imprime el resultado.
            else:
                print(f"Solicitud ignorada por fecha inválida: {tiempo}")  # Imprime un mensaje si la fecha es inválida.

        autorizaciones_content = save_to_xml()  # Guarda las autorizaciones en un archivo XML.
        return autorizaciones_content, 200, {'Content-Type': 'text/xml'}  # Devuelve el contenido del XML.

    except ET.ParseError:  # Maneja errores de parseo del XML.
        return jsonify({"error": "Error al parsear el XML"}), 400
    except Exception as e:  # Maneja otros errores.
        return jsonify({"error": str(e)}), 500

# Ruta para consultar las autorizaciones.
@app.route('/consultar', methods=['GET'])
def consultar():
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes) | set(lista_solicitudes.facturas_recibidas_por_fecha.keys()))  # Obtiene las fechas únicas.
    result = {"LISTAAUTORIZACIONES": []}  # Inicializa el resultado.
    for fecha in fechas:  # Itera sobre las fechas.
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas para la fecha.
        autorizacion_data = {  # Crea un diccionario con los datos de la autorización.
            "FECHA": fecha,
            "FACTURAS_RECIBIDAS": stats["facturas_recibidas"],
            "ERRORES": stats["errores"],
            "FACTURAS_CORRECTAS": stats["facturas_correctas"],
            "CANTIDAD_EMISORES": stats["cantidad_emisores"],
            "CANTIDAD_RECEPTORES": stats["cantidad_receptores"],
            "LISTADO_AUTORIZACIONES": {
                "APROBACION": [
                    {
                        "NIT_EMISOR": {"ref": a["referencia"], "value": a["nit_emisor"]},
                        "CODIGO_APROBACION": a["codigo_aprobacion"],
                        "IVA": a["iva"],
                        "VALOR": a["valor"],
                        "TOTAL": a["iva"] + a["valor"]
                    }
                    for a in stats["aprobaciones"]
                ],
                "TOTAL_APROBACIONES": stats["total_aprobaciones"]
            }
        }
        result["LISTAAUTORIZACIONES"].append(autorizacion_data)  # Agrega los datos al resultado.
    return jsonify(result)  # Devuelve el resultado en formato JSON.

# Ruta para obtener un resumen del IVA.
@app.route('/iva_summary', methods=['GET'])
def iva_summary_api():
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))  # Obtiene las fechas únicas.
    iva_data = {}  # Inicializa el diccionario para los datos del IVA.
    for fecha in fechas:  # Itera sobre las fechas.
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas para la fecha.
        for aprob in stats["aprobaciones"]:  # Itera sobre las aprobaciones.
            nit = aprob["nit_emisor"]  # Obtiene el NIT del emisor.
            iva = float(aprob["iva"])  # Obtiene el IVA.
            if fecha not in iva_data:  # Si la fecha no está en el diccionario, la agrega.
                iva_data[fecha] = {}
            iva_data[fecha][nit] = iva_data[fecha].get(nit, 0) + iva  # Suma el IVA al NIT correspondiente.
    return jsonify(iva_data)  # Devuelve los datos del IVA en formato JSON.

# Ruta para obtener un resumen de un rango de fechas.
@app.route('/range_summary', methods=['POST'])
def range_summary_api():
    data = request.get_json()  # Obtiene los datos del cuerpo de la solicitud.
    start_date = data.get('start_date')  # Obtiene la fecha de inicio.
    end_date = data.get('end_date')  # Obtiene la fecha de fin.
    value_type = data.get('value_type', 'total')  # Obtiene el tipo de valor (total o sin IVA).
    result = []  # Inicializa el resultado.
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))  # Obtiene las fechas únicas.
    for fecha in fechas:  # Itera sobre las fechas.
        if start_date <= fecha <= end_date:  # Si la fecha está en el rango.
            stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas para la fecha.
            total_value = sum(a["valor"] + a["iva"] for a in stats["aprobaciones"])  # Calcula el valor total.
            value = total_value if value_type == 'total' else total_value - sum(a["iva"] for a in stats["aprobaciones"])  # Calcula el valor según el tipo.
            result.append({"date": fecha, "value": value})  # Agrega el resultado.
    return jsonify(result)  # Devuelve el resultado en formato JSON.

# Ruta para obtener datos para un gráfico.
@app.route('/graph_data', methods=['GET'])
def graph_data():
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))  # Obtiene las fechas únicas.
    graph_data = {"labels": fechas, "data": []}  # Inicializa los datos del gráfico.
    for fecha in fechas:  # Itera sobre las fechas.
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas para la fecha.
        total = sum(a["valor"] + a["iva"] for a in stats["aprobaciones"])  # Calcula el total.
        graph_data["data"].append(total)  # Agrega el total a los datos.
    return jsonify(graph_data)  # Devuelve los datos del gráfico en formato JSON.

# Ruta para generar un reporte en PDF.
@app.route('/pdf_report', methods=['GET'])
def pdf_report():
    buffer = BytesIO()  # Crea un buffer en memoria.
    p = canvas.Canvas(buffer, pagesize=letter)  # Crea un objeto canvas para el PDF.
    p.drawString(100, 750, "Reporte de Autorizaciones")  # Escribe el título del reporte.
    y = 700  # Define la posición inicial en el eje Y.
    fechas = sorted(set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes))  # Obtiene las fechas únicas.
    for fecha in fechas:  # Itera sobre las fechas.
        stats = lista_solicitudes.estadisticas(fecha)  # Obtiene estadísticas para la fecha.
        p.drawString(100, y, f"Fecha: {fecha}")  # Escribe la fecha.
        p.drawString(100, y - 20, f"Facturas Recibidas: {stats['facturas_recibidas']}")  # Escribe las facturas recibidas.
        p.drawString(100, y - 40, f"Facturas Correctas: {stats['facturas_correctas']}")  # Escribe las facturas correctas.
        y -= 60  # Ajusta la posición en el eje Y.
        if stats["aprobaciones"]:  # Si hay aprobaciones.
            p.drawString(100, y, "Aprobaciones:")  # Escribe el título de aprobaciones.
            y -= 20
            for aprob in stats["aprobaciones"]:  # Itera sobre las aprobaciones.
                p.drawString(120, y, f"NIT Emisor: {aprob['nit_emisor']} (Ref: {aprob['referencia']})")  # Escribe el NIT del emisor.
                p.drawString(120, y - 20, f"Código: {aprob['codigo_aprobacion']}")  # Escribe el código de aprobación.
                p.drawString(120, y - 40, f"IVA: {aprob['iva']}")  # Escribe el IVA.
                p.drawString(120, y - 60, f"Valor: {aprob['valor']}")  # Escribe el valor.
                y -= 80  # Ajusta la posición en el eje Y.
                if y < 100:  # Si la posición es muy baja, crea una nueva página.
                    p.showPage()
                    y = 750
        else:  # Si no hay aprobaciones.
            p.drawString(100, y, "No hay aprobaciones.")  # Escribe que no hay aprobaciones.
            y -= 20
        if y < 100:  # Si la posición es muy baja, crea una nueva página.
            p.showPage()
            y = 750
    p.showPage()  # Finaliza la página.
    p.save()  # Guarda el PDF.
    buffer.seek(0)  # Regresa al inicio del buffer.
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='reporte.pdf')  # Devuelve el PDF como archivo descargable.

# Ruta para reiniciar el sistema.
@app.route('/reset', methods=['POST'])
def reset():
    global lista_solicitudes, autorizacion  # Declara las variables globales.
    lista_solicitudes = ListaSolicitudes()  # Reinicia la lista de solicitudes.
    autorizacion = Autorizacion()  # Reinicia las autorizaciones.
    if os.path.exists("autorizaciones.xml"):  # Si existe el archivo XML.
        os.remove("autorizaciones.xml")  # Lo elimina.
    return jsonify({"message": "Sistema reseteado correctamente"}), 200  # Devuelve un mensaje de éxito.

if __name__ == '__main__':  # Punto de entrada principal.
    app.run(debug=True, port=5000)  # Inicia la aplicación Flask en modo debug y en el puerto 5000.