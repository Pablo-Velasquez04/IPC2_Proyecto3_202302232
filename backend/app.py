from flask import Flask, request, Response
import xml.etree.ElementTree as ET
import os
from collections import OrderedDict
import json
from models import SolicitudDTE, ValidadorNIT, ListaSolicitudes, Autorizacion

app = Flask(__name__)
validador_nit = ValidadorNIT()
lista_solicitudes = ListaSolicitudes()  # Persistente para Fase 2
autorizacion = Autorizacion()

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'file' not in request.files:
        return Response(json.dumps({"error": "No se proporcionó archivo"}), status=400, mimetype='application/json')
    file = request.files['file']
    if not file.filename.endswith('.xml'):
        return Response(json.dumps({"error": "El archivo debe ser XML"}), status=400, mimetype='application/json')

    try:
        # Leer XML
        tree = ET.parse(file)
        root = tree.getroot()
        resultados = []
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
                    lista_solicitudes.inicializar_fecha(solicitud.fecha)
                    lista_solicitudes.facturas_recibidas_por_fecha[solicitud.fecha] += 1
                    lista_solicitudes.errores_por_fecha[solicitud.fecha]["REFERENCIA_DUPLICADA"] += 1
                    continue
                referencias_procesadas[solicitud.fecha].add(referencia)
                
                # Procesar solicitud
                ok, msg = lista_solicitudes.agregar(solicitud, autorizacion)
                if not ok:
                    resultados.append({"referencia": referencia, "error": msg})
                    continue
                
                resultados.append({"referencia": referencia, "estado": "Procesada correctamente"})
                
            except Exception as e:
                resultados.append({"referencia": referencia or "Desconocida", "error": f"Error en DTE: {str(e)}"})
        
        # Generar autorizaciones.xml
        generar_autorizaciones_xml(lista_solicitudes)

        response = {
            "resultados": resultados,
            "total_procesadas": len(resultados),
            "total_errores": len([r for r in resultados if "error" in r])
        }
        return Response(json.dumps(response, ensure_ascii=False), status=200, mimetype='application/json')
    
    except Exception as e:
        return Response(json.dumps({"error": f"Error procesando XML: {str(e)}"}), status=400, mimetype='application/json')

def generar_autorizaciones_xml(lista_solicitudes):
    root = ET.Element("LISTAAUTORIZACIONES")
    
    # Agrupar estadísticas por fecha
    fechas = set(s["solicitud"].fecha for s in lista_solicitudes.solicitudes) | \
             set(lista_solicitudes.referencias_por_fecha.keys())
    for fecha in sorted(fechas):
        stats = lista_solicitudes.estadisticas(fecha)
        autorizacion = ET.SubElement(root, "AUTORIZACION")
        
        ET.SubElement(autorizacion, "FECHA").text = fecha
        ET.SubElement(autorizacion, "FACTURAS_RECIBIDAS").text = str(stats["facturas_recibidas"])
        
        errores = ET.SubElement(autorizacion, "ERRORES")
        ET.SubElement(errores, "NIT_EMISOR").text = str(stats["errores"]["NIT_EMISOR"])
        ET.SubElement(errores, "NIT_RECEPTOR").text = str(stats["errores"]["NIT_RECEPTOR"])
        ET.SubElement(errores, "IVA").text = str(stats["errores"]["IVA"])
        ET.SubElement(errores, "TOTAL").text = str(stats["errores"]["TOTAL"])
        ET.SubElement(errores, "REFERENCIA_DUPLICADA").text = str(stats["errores"]["REFERENCIA_DUPLICADA"])
        
        ET.SubElement(autorizacion, "FACTURAS_CORRECTAS").text = str(stats["facturas_correctas"])
        ET.SubElement(autorizacion, "CANTIDAD_EMISORES").text = str(stats["cantidad_emisores"])
        ET.SubElement(autorizacion, "CANTIDAD_RECEPTORES").text = str(stats["cantidad_receptores"])
        
        listado = ET.SubElement(autorizacion, "LISTADO_AUTORIZACIONES")
        for aprobacion in stats["aprobaciones"]:
            aprob = ET.SubElement(listado, "APROBACION")
            nit_emisor = ET.SubElement(aprob, "NIT_EMISOR")
            nit_emisor.set("ref", aprobacion["referencia"])
            nit_emisor.text = aprobacion["nit_emisor"]
            ET.SubElement(aprob, "CODIGO_APROBACION").text = aprobacion["codigo_aprobacion"]
        
        ET.SubElement(listado, "TOTAL_APROBACIONES").text = str(stats["total_aprobaciones"])
    
    # Guardar archivo
    tree = ET.ElementTree(root)
    tree.write("autorizaciones.xml", encoding="utf-8", xml_declaration=True)

@app.route('/consultar', methods=['GET'])
def consultar():
    try:
        if not os.path.exists("autorizaciones.xml"):
            return Response(json.dumps({"error": "No hay datos disponibles"}), status=404, mimetype='application/json')
        
        tree = ET.parse("autorizaciones.xml")
        root = tree.getroot()
        resultado = []
        
        for auth in root.findall(".//AUTORIZACION"):
            # Usar OrderedDict para controlar el orden de los campos
            autorizacion = OrderedDict([
                ("FECHA", auth.find("FECHA").text),
                ("FACTURAS_RECIBIDAS", int(auth.find("FACTURAS_RECIBIDAS").text)),
                ("ERRORES", OrderedDict([
                    ("NIT_EMISOR", int(auth.find("ERRORES/NIT_EMISOR").text)),
                    ("NIT_RECEPTOR", int(auth.find("ERRORES/NIT_RECEPTOR").text)),
                    ("IVA", int(auth.find("ERRORES/IVA").text)),
                    ("TOTAL", int(auth.find("ERRORES/TOTAL").text)),
                    ("REFERENCIA_DUPLICADA", int(auth.find("ERRORES/REFERENCIA_DUPLICADA").text))
                ])),
                ("FACTURAS_CORRECTAS", int(auth.find("FACTURAS_CORRECTAS").text)),
                ("CANTIDAD_EMISORES", int(auth.find("CANTIDAD_EMISORES").text)),
                ("CANTIDAD_RECEPTORES", int(auth.find("CANTIDAD_RECEPTORES").text)),
                ("LISTADO_AUTORIZACIONES", OrderedDict([
                    ("APROBACION", [
                        OrderedDict([
                            ("NIT_EMISOR", OrderedDict([
                                ("ref", aprob.find("NIT_EMISOR").get("ref")),
                                ("value", aprob.find("NIT_EMISOR").text)
                            ])),
                            ("CODIGO_APROBACION", aprob.find("CODIGO_APROBACION").text)
                        ])
                        for aprob in auth.findall(".//APROBACION")
                    ]),
                    ("TOTAL_APROBACIONES", int(auth.find("LISTADO_AUTORIZACIONES/TOTAL_APROBACIONES").text))
                ]))
            ])
            print("Autorizacion antes de serializar:", autorizacion)  # Depuración
            resultado.append(autorizacion)
        
        response = {"LISTAAUTORIZACIONES": resultado}
        print("Respuesta antes de serializar:", response)  # Depuración
        return Response(
            json.dumps(response, ensure_ascii=False),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        return Response(
            json.dumps({"error": f"Error consultando datos: {str(e)}"}),
            status=500,
            mimetype='application/json'
        )

@app.route('/reset', methods=['POST'])
def reset():
    try:
        global lista_solicitudes, autorizacion
        lista_solicitudes = ListaSolicitudes()
        autorizacion = Autorizacion()
        if os.path.exists("autorizaciones.xml"):
            os.remove("autorizaciones.xml")
        return Response(
            json.dumps({"mensaje": "Sistema reiniciado correctamente"}),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({"error": f"Error al reiniciar: {str(e)}"}),
            status=500,
            mimetype='application/json'
        )

if __name__ == '__main__':
    app.run(debug=True)