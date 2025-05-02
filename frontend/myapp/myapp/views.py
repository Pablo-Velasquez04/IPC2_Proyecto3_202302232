import io  # Importa el módulo para manejar flujos de entrada/salida.
from django.shortcuts import render, redirect  # Importa funciones para renderizar plantillas y redirigir.
from django.contrib import messages  # Importa para mostrar mensajes al usuario.
import requests  # Importa para realizar solicitudes HTTP.
from datetime import datetime  # Importa para manejar fechas y horas.
import json  # Importa para trabajar con datos en formato JSON.
from django.http import HttpResponse  # Importa para generar respuestas HTTP.
from reportlab.pdfgen import canvas  # Importa para generar archivos PDF.
from io import BytesIO  # Importa para manejar flujos de datos en memoria.
from reportlab.lib.pagesizes import letter  # Importa para definir el tamaño de página en PDF.

# Vista para cargar y procesar XML o archivos.
def upload(request):
    entrada = ""  # Variable para almacenar el contenido de entrada.
    salida = ""  # Variable para almacenar el contenido de salida.
    if request.method == 'POST':  # Verifica si la solicitud es POST.
        # Opción 1: Procesar XML desde el textarea.
        entrada = request.POST.get('entrada', '')  # Obtiene el contenido del textarea.
        if entrada:  # Si hay contenido en el textarea.
            try:
                # Envía el XML al backend para procesarlo.
                response = requests.post('http://127.0.0.1:5000/cargar', data={'xml': entrada})
                response.raise_for_status()  # Verifica si la solicitud fue exitosa.
                salida = response.text  # Obtiene la respuesta del backend.
                messages.success(request, 'XML procesado correctamente :D')  # Muestra mensaje de éxito.
            except requests.RequestException as e:  # Maneja errores de solicitud.
                messages.error(request, f'Error al procesar el XML: {str(e)}')  # Muestra mensaje de error.
                salida = f"Error al procesar el XML: {str(e)}"

        # Opción 2: Procesar archivo subido.
        else:
            xml_file = request.FILES.get('xml_file')  # Obtiene el archivo subido.
            if xml_file:  # Si se subió un archivo.
                try:
                    # Lee el contenido del archivo para mostrarlo en el textarea.
                    entrada = xml_file.read().decode('utf-8')
                    xml_file.seek(0)  # Reinicia el puntero del archivo.
                    files = {'xml_file': (xml_file.name, xml_file, 'text/xml')}  # Prepara el archivo para enviarlo.
                    response = requests.post('http://127.0.0.1:5000/cargar', files=files)  # Envía el archivo al backend.
                    response.raise_for_status()  # Verifica si la solicitud fue exitosa.
                    salida = response.text  # Obtiene la respuesta del backend.
                    messages.success(request, 'Archivo cargado correctamente :D')  # Muestra mensaje de éxito.
                except requests.RequestException as e:  # Maneja errores de solicitud.
                    messages.error(request, f'Error al cargar el archivo: {str(e)}')  # Muestra mensaje de error.
                    salida = f"Error al cargar el archivo: {str(e)}"
                except UnicodeDecodeError:  # Maneja errores de codificación.
                    messages.error(request, 'El archivo no está en formato UTF-8 válido.')  # Muestra mensaje de error.
                    salida = "El archivo no está en formato UTF-8 válido."
            else:
                # Si no se seleccionó archivo ni se ingresó XML.
                messages.error(request, 'No se seleccionó ningún archivo ni se ingresó XML.')
                salida = "No se seleccionó ningún archivo ni se ingresó XML."

    # Renderiza la plantilla 'upload.html' con las variables de entrada y salida.
    return render(request, 'upload.html', {'entrada': entrada, 'salida': salida})

# Vista para consultar datos del backend.
def consult(request):
    try:
        # Solicita datos al backend.
        response = requests.get('http://127.0.0.1:5000/consultar')
        response.raise_for_status()  # Verifica si la solicitud fue exitosa.
        data = response.json()  # Convierte la respuesta a JSON.
        autorizaciones = data.get('LISTAAUTORIZACIONES', [])  # Obtiene la lista de autorizaciones.
        print("Datos enviados a consult.html:", autorizaciones)  # Depuración.
        # Renderiza la plantilla 'consult.html' con las autorizaciones.
        return render(request, 'consult.html', {'autorizaciones': autorizaciones})
    except requests.RequestException as e:  # Maneja errores de solicitud.
        # Renderiza la plantilla con una lista vacía si hay error.
        return render(request, 'consult.html', {'autorizaciones': []})

# Vista para generar un resumen de IVA por fecha.
def iva_summary(request):
    if request.method == 'POST':  # Verifica si la solicitud es POST.
        date = request.POST.get('date')  # Obtiene la fecha ingresada.
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')  # Convierte la fecha a objeto datetime.
            formatted_date = date_obj.strftime('%d/%m/%Y')  # Formatea la fecha.
            response = requests.get('http://127.0.0.1:5000/consultar')  # Solicita datos al backend.
            response.raise_for_status()  # Verifica si la solicitud fue exitosa.
            data = response.json()  # Convierte la respuesta a JSON.
            iva_data = []  # Lista para almacenar datos de IVA.
            for auth in data.get('LISTAAUTORIZACIONES', []):  # Itera sobre las autorizaciones.
                if auth['FECHA'] == formatted_date:  # Filtra por fecha.
                    for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']:  # Itera sobre aprobaciones.
                        nit = aprob['NIT_EMISOR']['value']  # Obtiene el NIT del emisor.
                        iva = float(aprob['IVA'])  # Convierte el IVA a float.
                        iva_data.append({'nit': nit, 'iva': iva})  # Agrega los datos a la lista.
            print("iva_data:", iva_data)  # Depuración.
            iva_data_json = json.dumps(iva_data)  # Convierte los datos a JSON.
            # Renderiza la plantilla con los datos de IVA.
            return render(request, 'iva_summary.html', {'date': date, 'iva_data_json': iva_data_json})
        except requests.RequestException as e:  # Maneja errores de solicitud.
            messages.error(request, f'Error al obtener datos: {str(e)}')  # Muestra mensaje de error.
    # Renderiza la plantilla vacía si no es POST.
    return render(request, 'iva_summary.html')

# Vista para generar un resumen de valores en un rango de fechas.
def range_summary(request):
    if request.method == 'POST':  # Verifica si la solicitud es POST.
        start_date = request.POST.get('start_date')  # Obtiene la fecha de inicio.
        end_date = request.POST.get('end_date')  # Obtiene la fecha de fin.
        value_type = request.POST.get('value_type', 'total')  # Obtiene el tipo de valor (total o sin IVA).
        try:
            response = requests.get('http://127.0.0.1:5000/consultar')  # Solicita datos al backend.
            response.raise_for_status()  # Verifica si la solicitud fue exitosa.
            data = response.json()  # Convierte la respuesta a JSON.
            start = datetime.strptime(start_date, '%Y-%m-%d')  # Convierte la fecha de inicio a objeto datetime.
            end = datetime.strptime(end_date, '%Y-%m-%d')  # Convierte la fecha de fin a objeto datetime.
            range_data = []  # Lista para almacenar datos del rango.
            for auth in data.get('LISTAAUTORIZACIONES', []):  # Itera sobre las autorizaciones.
                auth_date = datetime.strptime(auth['FECHA'], '%d/%m/%Y')  # Convierte la fecha de autorización.
                if start <= auth_date <= end:  # Filtra por rango de fechas.
                    total_value = sum(
                        aprob['VALOR'] + aprob['IVA']  # Suma el valor y el IVA.
                        for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']
                    )
                    value = total_value if value_type == 'total' else total_value - sum(
                        aprob['IVA'] for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']
                    )  # Calcula el valor según el tipo.
                    range_data.append({'date': auth['FECHA'], 'value': value})  # Agrega los datos a la lista.
            print("range_data:", range_data)  # Depuración.
            range_data_json = json.dumps(range_data)  # Convierte los datos a JSON.
            # Renderiza la plantilla con los datos del rango.
            return render(request, 'range_summary.html', {
                'start_date': start_date,
                'end_date': end_date,
                'value_type': value_type,
                'range_data_json': range_data_json
            })
        except requests.RequestException as e:  # Maneja errores de solicitud.
            messages.error(request, f'Error al obtener datos: {str(e)}')  # Muestra mensaje de error.
    # Renderiza la plantilla vacía si no es POST.
    return render(request, 'range_summary.html')

# Vista para mostrar la página de ayuda.
def help(request):
    return render(request, 'help.html')  # Renderiza la plantilla de ayuda.

# Vista para generar y descargar un reporte en PDF.
def send(request):
    try:
        response = requests.get('http://127.0.0.1:5000/consultar')  # Solicita datos al backend.
        response.raise_for_status()  # Verifica si la solicitud fue exitosa.
        data = response.json()  # Convierte la respuesta a JSON.
        print("Datos recibidos de /consultar:", data)  # Depuración.

        autorizaciones = data.get('LISTAAUTORIZACIONES', [])  # Obtiene la lista de autorizaciones.
        if not autorizaciones:  # Si no hay autorizaciones.
            messages.error(request, "No hay datos para generar el reporte.")  # Muestra mensaje de error.
            return render(request, 'upload.html')  # Renderiza la plantilla de carga.

        # Genera el PDF.
        buffer = io.BytesIO()  # Crea un buffer en memoria.
        p = canvas.Canvas(buffer, pagesize=letter)  # Crea un objeto canvas para el PDF.
        p.drawString(100, 750, "Reporte de Autorizaciones")  # Escribe el título en el PDF.
        y = 700  # Coordenada Y inicial.
        for auth in autorizaciones:  # Itera sobre las autorizaciones.
            p.drawString(100, y, f"Fecha: {auth['FECHA']}")  # Escribe la fecha.
            p.drawString(100, y - 20, f"Facturas Recibidas: {auth['FACTURAS_RECIBIDAS']}")  # Escribe las facturas recibidas.
            p.drawString(100, y - 40, f"Facturas Correctas: {auth['FACTURAS_CORRECTAS']}")  # Escribe las facturas correctas.
            y -= 60  # Ajusta la coordenada Y.
            if auth['LISTADO_AUTORIZACIONES']['APROBACION']:  # Si hay aprobaciones.
                p.drawString(100, y, "Aprobaciones:")  # Escribe el título de aprobaciones.
                y -= 20
                for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']:  # Itera sobre las aprobaciones.
                    p.drawString(120, y, f"NIT Emisor: {aprob['NIT_EMISOR']['value']} (Referencia: {aprob['NIT_EMISOR']['ref']})")  # Escribe el NIT del emisor.
                    p.drawString(120, y - 20, f"Código Aprobación: {aprob['CODIGO_APROBACION']}")  # Escribe el código de aprobación.
                    p.drawString(120, y - 40, f"IVA: {aprob['IVA']}")  # Escribe el IVA.
                    p.drawString(120, y - 60, f"Valor: {aprob['VALOR']}")  # Escribe el valor.
                    y -= 80  # Ajusta la coordenada Y.
                    if y < 100:  # Si se alcanza el final de la página.
                        p.showPage()  # Crea una nueva página.
                        y = 750  # Reinicia la coordenada Y.
            else:
                p.drawString(100, y, "No hay aprobaciones.")  # Escribe que no hay aprobaciones.
                y -= 20
            if y < 100:  # Si se alcanza el final de la página.
                p.showPage()  # Crea una nueva página.
                y = 750  # Reinicia la coordenada Y.
        p.showPage()  # Finaliza la página actual.
        p.save()  # Guarda el PDF.

        buffer.seek(0)  # Reinicia el puntero del buffer.
        response = HttpResponse(buffer, content_type='application/pdf')  # Crea una respuesta HTTP con el PDF.
        response['Content-Disposition'] = 'attachment; filename="reporte_autorizaciones.pdf"'  # Define el nombre del archivo.
        return response  # Devuelve el PDF como respuesta.
    except requests.RequestException as e:  # Maneja errores de solicitud.
        messages.error(request, f"Error al generar el reporte: {str(e)}")  # Muestra mensaje de error.
        return render(request, 'upload.html')  # Renderiza la plantilla de carga.

# Vista para resetear el sistema.
def reset(request):
    try:
        response = requests.post('http://127.0.0.1:5000/reset')  # Envía una solicitud para resetear el backend.
        response.raise_for_status()  # Verifica si la solicitud fue exitosa.
        messages.success(request, 'Sistema reseteado correctamente :D')  # Muestra mensaje de éxito.
    except requests.RequestException as e:  # Maneja errores de solicitud.
        messages.error(request, f'Error al resetear: {str(e)}')  # Muestra mensaje de error.
    return redirect('upload')  # Redirige a la vista de carga.