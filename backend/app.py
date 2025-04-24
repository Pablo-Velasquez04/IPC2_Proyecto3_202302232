from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET
from models import SolicitudDTE, ValidadorNIT, ListaSolicitudes

app = Flask(__name__)
lista_solicitudes = ListaSolicitudes()
validador_nit = ValidadorNIT()

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'file' not in request.files:
        return jsonify({"error": "No se proporcionó archivo"}), 400
    file = request.files['file']
    if not file.filename.endswith('.xml'):
        return jsonify({"error": "El archivo debe ser XML"}), 400

    try:
        # Leer XML
        tree = ET.parse(file)
        root = tree.getroot()
        resultados = []
        # Set temporal para rastrear referencias procesadas en este archivo
        referencias_procesadas = {}

        # Procesar cada DTE
        for dte in root.findall('.//DTE'):
            try:
                tiempo = dte.find('TIEMPO').text
                referencia = dte.find('REFERENCIA').text
                nit_emisor = dte.find('NIT_EMISOR').text
                nit_receptor = dte.find('NIT_RECEPTOR').text
                valor = dte.find('VALOR').text
                iva = dte.find('IVA').text
                total = dte.find('TOTAL').text

                # Crear solicitud
                try:
                    solicitud = SolicitudDTE(tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total)
                except ValueError as e:
                    resultados.append({"referencia": referencia, "error": str(e)})
                    continue
                
                # Validar formato
                if not solicitud.fecha:
                    resultados.append({"referencia": referencia, "error": "Fecha inválida"})
                    continue
                
                # Verificar duplicados en el archivo
                if solicitud.fecha not in referencias_procesadas:
                    referencias_procesadas[solicitud.fecha] = set()
                if referencia in referencias_procesadas[solicitud.fecha]:
                    resultados.append({"referencia": referencia, "error": "Referencia duplicada"})
                    continue
                referencias_procesadas[solicitud.fecha].add(referencia)
                
                # Validar datos
                es_valida, mensaje = solicitud.es_valida(validador_nit)
                if not es_valida:
                    resultados.append({"referencia": referencia, "error": mensaje})
                    continue
                
                # Verificar referencia única contra solicitudes previas
                ok, msg = lista_solicitudes.agregar(solicitud)
                if not ok:
                    resultados.append({"referencia": referencia, "error": msg})
                    continue
                
                resultados.append({"referencia": referencia, "estado": "Procesada correctamente"})
                
            except Exception as e:
                resultados.append({"referencia": referencia or "Desconocida", "error": f"Error en DTE: {str(e)}"})
        
        return jsonify({
            "resultados": resultados,
            "total_procesadas": len(resultados),
            "total_errores": len([r for r in resultados if "error" in r])
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Error procesando XML: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True)