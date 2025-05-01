from django.shortcuts import render
import requests
from django.http import HttpResponse
from django.contrib import messages
import json
from datetime import datetime

def upload(request):
    if request.method == 'POST':
        xml_file = request.FILES.get('xml_file')
        if not xml_file or not xml_file.name.endswith('.xml'):
            messages.error(request, 'Por favor, suba un archivo XML válido.')
            return render(request, 'upload.html')
        try:
            response = requests.post('http://127.0.0.1:5000/procesar', files={'file': xml_file})
            response.raise_for_status()
            messages.success(request, 'Archivo procesado correctamente.')
            return render(request, 'upload.html', {'response': response.json()})
        except requests.RequestException as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
            return render(request, 'upload.html')
    return render(request, 'upload.html')

def consult(request):
    try:
        response = requests.get('http://127.0.0.1:5000/consultar')
        response.raise_for_status()
        data = response.json()
        return render(request, 'consult.html', {'data': json.dumps(data, indent=2)})
    except requests.RequestException as e:
        messages.error(request, f'Error al consultar datos: {str(e)}')
        return render(request, 'consult.html')

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
    return HttpResponse("Botón Enviar: Implementar en Fase 4")

def reset(request):
    return HttpResponse("Botón Reset: Implementar en Fase 4")