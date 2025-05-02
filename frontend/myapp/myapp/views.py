# frontend/myapp/myapp/views.py
import io
from django.shortcuts import render, redirect
from django.contrib import messages
import requests
from datetime import datetime
import json
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import letter

# Removed unused import 'tkinter.tix'

def upload(request):
    if request.method == 'POST':
        xml_file = request.FILES.get('xml_file')
        if xml_file:
            try:
                files = {'xml_file': (xml_file.name, xml_file, 'text/xml')}
                response = requests.post('http://127.0.0.1:5000/cargar', files=files)
                response.raise_for_status()
                response_data = response.json()
                if 'error' in response_data:
                    messages.error(request, f"Error: {response_data['error']}")
                else:
                    messages.success(request, 'Archivo cargado correctamente.')
                return render(request, 'upload.html', {'response': response_data})
            except requests.RequestException as e:
                messages.error(request, f'Error al cargar el archivo: {str(e)}')
        else:
            messages.error(request, 'No se seleccionó ningún archivo.')
    return render(request, 'upload.html')

def consult(request):
    try:
        response = requests.get('http://127.0.0.1:5000/consultar')
        response.raise_for_status()
        data = response.json()
        autorizaciones = data.get('LISTAAUTORIZACIONES', [])
        print("Datos enviados a consult.html:", autorizaciones)  # Depuración
        return render(request, 'consult.html', {'autorizaciones': autorizaciones})
    except requests.RequestException as e:
        return render(request, 'consult.html', {'autorizaciones': []})

def iva_summary(request):
    if request.method == 'POST':
        date = request.POST.get('date')  # Formato YYYY-MM-DD
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
            response = requests.get('http://127.0.0.1:5000/consultar')
            response.raise_for_status()
            data = response.json()
            iva_data = []
            for auth in data.get('LISTAAUTORIZACIONES', []):
                if auth['FECHA'] == formatted_date:
                    for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']:
                        nit = aprob['NIT_EMISOR']['value']
                        iva = float(aprob['IVA'])  # Asegurarse de que sea float
                        iva_data.append({'nit': nit, 'iva': iva})
            print("iva_data:", iva_data)  # Depuración
            # Convertir iva_data a JSON válido
            iva_data_json = json.dumps(iva_data)
            return render(request, 'iva_summary.html', {'date': date, 'iva_data_json': iva_data_json})
        except requests.RequestException as e:
            messages.error(request, f'Error al obtener datos: {str(e)}')
    return render(request, 'iva_summary.html')

def range_summary(request):
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        value_type = request.POST.get('value_type', 'total')
        try:
            response = requests.get('http://127.0.0.1:5000/consultar')
            response.raise_for_status()
            data = response.json()
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            range_data = []
            for auth in data.get('LISTAAUTORIZACIONES', []):
                auth_date = datetime.strptime(auth['FECHA'], '%d/%m/%Y')
                if start <= auth_date <= end:
                    total_value = sum(
                        aprob['VALOR'] + aprob['IVA']
                        for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']
                    )
                    value = total_value if value_type == 'total' else total_value - sum(
                        aprob['IVA'] for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']
                    )
                    range_data.append({'date': auth['FECHA'], 'value': value})
            print("range_data:", range_data)  # Depuración
            # Convertir range_data a JSON válido
            range_data_json = json.dumps(range_data)
            return render(request, 'range_summary.html', {
                'start_date': start_date,
                'end_date': end_date,
                'value_type': value_type,
                'range_data_json': range_data_json
            })
        except requests.RequestException as e:
            messages.error(request, f'Error al obtener datos: {str(e)}')
    return render(request, 'range_summary.html')

def help(request):
    return render(request, 'help.html')

def send(request):
    try:
        response = requests.get('http://127.0.0.1:5000/consultar')
        response.raise_for_status()
        data = response.json()
        print("Datos recibidos de /consultar:", data)  # Depuración

        autorizaciones = data.get('LISTAAUTORIZACIONES', [])
        if not autorizaciones:
            messages.error(request, "No hay datos para generar el reporte.")
            return render(request, 'upload.html')

        # Generar PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.drawString(100, 750, "Reporte de Autorizaciones")
        y = 700
        for auth in autorizaciones:
            p.drawString(100, y, f"Fecha: {auth['FECHA']}")
            p.drawString(100, y - 20, f"Facturas Recibidas: {auth['FACTURAS_RECIBIDAS']}")
            p.drawString(100, y - 40, f"Facturas Correctas: {auth['FACTURAS_CORRECTAS']}")
            y -= 60
            if auth['LISTADO_AUTORIZACIONES']['APROBACION']:
                p.drawString(100, y, "Aprobaciones:")
                y -= 20
                for aprob in auth['LISTADO_AUTORIZACIONES']['APROBACION']:
                    p.drawString(120, y, f"NIT Emisor: {aprob['NIT_EMISOR']['value']} (Referencia: {aprob['NIT_EMISOR']['ref']})")
                    p.drawString(120, y - 20, f"Código Aprobación: {aprob['CODIGO_APROBACION']}")
                    p.drawString(120, y - 40, f"IVA: {aprob['IVA']}")
                    p.drawString(120, y - 60, f"Valor: {aprob['VALOR']}")
                    y -= 80
                    if y < 100:
                        p.showPage()
                        y = 750
            else:
                p.drawString(100, y, "No hay aprobaciones.")
                y -= 20
            if y < 100:
                p.showPage()
                y = 750
        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_autorizaciones.pdf"'
        return response
    except requests.RequestException as e:
        messages.error(request, f"Error al generar el reporte: {str(e)}")
        return render(request, 'upload.html')

def reset(request):
    try:
        response = requests.post('http://127.0.0.1:5000/reset')
        response.raise_for_status()
        messages.success(request, 'Sistema reseteado correctamente.')
    except requests.RequestException as e:
        messages.error(request, f'Error al resetear: {str(e)}')
    return redirect('upload')