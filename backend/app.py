from flask import Flask, request, Response
import xml.etree.ElementTree as ET
import os
import json
import re

app = Flask(__name__)

@app.route('/cargar', methods=['POST'])
def cargar():
    try:
        xml_file = request.files.get('xml_file')
        if not xml_file:
            return Response(json.dumps({"error": "No se proporcionó un archivo XML"}), status=400, mimetype='application/json')

        xml_content = xml_file.read().decode('utf-8')
        print("Contenido del XML:", xml_content)  # Depuración
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return Response(json.dumps({"error": f"Formato de XML inválido: {str(e)}"}), status=400, mimetype='application/json')

        first_dte = root.find("DTE")
        if first_dte is None:
            return Response(json.dumps({"error": "No se encontraron elementos DTE en el XML"}), status=400, mimetype='application/json')

        tiempo = first_dte.find("TIEMPO")
        if tiempo is None or not tiempo.text:
            return Response(json.dumps({"error": "El elemento TIEMPO no está presente o está vacío en el primer DTE"}), status=400, mimetype='application/json')

        match = re.search(r'\d{2}/\d{2}/\d{4}', tiempo.text)
        if not match:
            return Response(json.dumps({"error": "Formato de fecha inválido en TIEMPO"}), status=400, mimetype='application/json')
        fecha = match.group(0)

        existing_root = ET.Element("LISTAAUTORIZACIONES")

        facturas_recibidas = 0
        errores = {
            "NIT_EMISOR": 0,
            "NIT_RECEPTOR": 0,
            "IVA": 0,
            "TOTAL": 0,
            "REFERENCIA_DUPLICADA": 0
        }
        facturas_correctas = 0
        emisor_nits = set()
        receptor_nits = set()
        referencias = set()

        aprobaciones = []

        for dte in root.findall("DTE"):
            facturas_recibidas += 1
            nit_emisor = dte.find("NIT_EMISOR")
            nit_receptor = dte.find("NIT_RECEPTOR")
            valor_elem = dte.find("VALOR")
            iva_elem = dte.find("IVA")
            total_elem = dte.find("TOTAL")
            referencia = dte.find("REFERENCIA")

            # Verificar si todos los elementos existen
            if not all(elem is not None for elem in [nit_emisor, nit_receptor, valor_elem, iva_elem, total_elem, referencia]):
                continue

            nit_emisor_text = nit_emisor.text.strip() if nit_emisor.text else ""
            nit_receptor_text = nit_receptor.text.strip() if nit_receptor.text else ""
            try:
                valor = float(valor_elem.text.strip())
                iva = float(iva_elem.text.strip())
                total = float(total_elem.text.strip())
            except ValueError as e:
                print(f"Error al convertir valores: {e}")
                errores["TOTAL"] += 1
                continue
            referencia_text = referencia.text.strip() if referencia.text else ""

            error = False
            print(f"Validando DTE - Valor: {valor}, IVA: {iva}, Total: {total}")  # Depuración

            if not nit_emisor_text or not nit_emisor_text.isalnum():
                errores["NIT_EMISOR"] += 1
                error = True
            if not nit_receptor_text or not nit_receptor_text.isalnum():
                errores["NIT_RECEPTOR"] += 1
                error = True
            if iva <= 0:
                errores["IVA"] += 1
                error = True
            # Validación de TOTAL con redondeo explícito
            expected_total = round(valor + iva, 2)
            print(f"Expected Total: {expected_total}, Actual Total: {total}")  # Depuración
            if abs(total - expected_total) > 0.01:
                errores["TOTAL"] += 1
                error = True
                print(f"Error en TOTAL: Esperado {expected_total}, Obtenido {total}")
            if referencia_text in referencias:
                errores["REFERENCIA_DUPLICADA"] += 1
                error = True
            else:
                referencias.add(referencia_text)

            if not error:
                facturas_correctas += 1
                emisor_nits.add(nit_emisor_text)
                receptor_nits.add(nit_receptor_text)

                aprobacion = {
                    "NIT_EMISOR": {"ref": referencia_text, "value": nit_emisor_text},
                    "CODIGO_APROBACION": f"{fecha.replace('/', '')}{referencia_text.zfill(8)}",
                    "IVA": iva,
                    "VALOR": valor
                }
                aprobaciones.append(aprobacion)

        autorizacion = ET.SubElement(existing_root, "AUTORIZACION")
        fecha_elem = ET.SubElement(autorizacion, "FECHA")
        fecha_elem.text = fecha
        facturas_recibidas_elem = ET.SubElement(autorizacion, "FACTURAS_RECIBIDAS")
        facturas_recibidas_elem.text = str(facturas_recibidas)
        errores_elem = ET.SubElement(autorizacion, "ERRORES")
        for key, value in errores.items():
            error_elem = ET.SubElement(errores_elem, key)
            error_elem.text = str(value)
        facturas_correctas_elem = ET.SubElement(autorizacion, "FACTURAS_CORRECTAS")
        facturas_correctas_elem.text = str(facturas_correctas)
        cantidad_emisores_elem = ET.SubElement(autorizacion, "CANTIDAD_EMISORES")
        cantidad_emisores_elem.text = str(len(emisor_nits))
        cantidad_receptores_elem = ET.SubElement(autorizacion, "CANTIDAD_RECEPTORES")
        cantidad_receptores_elem.text = str(len(receptor_nits))

        listado_autorizaciones = ET.SubElement(autorizacion, "LISTADO_AUTORIZACIONES")
        aprobacion_elem = ET.SubElement(listado_autorizaciones, "APROBACION")
        for aprob in aprobaciones:
            dte_elem = ET.SubElement(aprobacion_elem, "DTE")
            nit_emisor_elem = ET.SubElement(dte_elem, "NIT_EMISOR")
            nit_emisor_elem.set("ref", aprob["NIT_EMISOR"]["ref"])
            nit_emisor_elem.text = aprob["NIT_EMISOR"]["value"]
            codigo_elem = ET.SubElement(dte_elem, "CODIGO_APROBACION")
            codigo_elem.text = aprob["CODIGO_APROBACION"]
            iva_elem = ET.SubElement(dte_elem, "IVA")
            iva_elem.text = str(aprob["IVA"])
            valor_elem = ET.SubElement(dte_elem, "VALOR")
            valor_elem.text = str(aprob["VALOR"])
        total_aprobaciones_elem = ET.SubElement(listado_autorizaciones, "TOTAL_APROBACIONES")
        total_aprobaciones_elem.text = str(len(aprobaciones))

        tree = ET.ElementTree(existing_root)
        tree.write("autorizaciones.xml", encoding="utf-8", xml_declaration=True)
        print("autorizaciones.xml generado con éxito")

        response = {
            "message": "Archivo procesado correctamente",
            "facturas_recibidas": facturas_recibidas,
            "facturas_correctas": facturas_correctas,
            "errores": errores
        }
        return Response(json.dumps(response), status=200, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": f"Error interno: {str(e)}"}), status=500, mimetype='application/json')
    






@app.route('/consultar', methods=['GET'])
def consultar():
    try:
        if not os.path.exists("autorizaciones.xml"):
            return Response(json.dumps({"LISTAAUTORIZACIONES": []}), status=200, mimetype='application/json')
        
        tree = ET.parse("autorizaciones.xml")
        root = tree.getroot()
        resultado = []
        
        for auth in root.findall("AUTORIZACION"):
            fecha = auth.find("FECHA").text if auth.find("FECHA") is not None else ""
            facturas_recibidas = int(auth.find("FACTURAS_RECIBIDAS").text) if auth.find("FACTURAS_RECIBIDAS") is not None else 0
            errores_elem = auth.find("ERRORES")
            errores = {
                "NIT_EMISOR": int(errores_elem.find("NIT_EMISOR").text) if errores_elem and errores_elem.find("NIT_EMISOR") is not None else 0,
                "NIT_RECEPTOR": int(errores_elem.find("NIT_RECEPTOR").text) if errores_elem and errores_elem.find("NIT_RECEPTOR") is not None else 0,
                "IVA": int(errores_elem.find("IVA").text) if errores_elem and errores_elem.find("IVA") is not None else 0,
                "TOTAL": int(errores_elem.find("TOTAL").text) if errores_elem and errores_elem.find("TOTAL") is not None else 0,
                "REFERENCIA_DUPLICADA": int(errores_elem.find("REFERENCIA_DUPLICADA").text) if errores_elem and errores_elem.find("REFERENCIA_DUPLICADA") is not None else 0
            } if errores_elem else {
                "NIT_EMISOR": 0,
                "NIT_RECEPTOR": 0,
                "IVA": 0,
                "TOTAL": 0,
                "REFERENCIA_DUPLICADA": 0
            }
            facturas_correctas = int(auth.find("FACTURAS_CORRECTAS").text) if auth.find("FACTURAS_CORRECTAS") is not None else 0
            cantidad_emisores = int(auth.find("CANTIDAD_EMISORES").text) if auth.find("CANTIDAD_EMISORES") is not None else 0
            cantidad_receptores = int(auth.find("CANTIDAD_RECEPTORES").text) if auth.find("CANTIDAD_RECEPTORES") is not None else 0

            listado_autorizaciones = auth.find("LISTADO_AUTORIZACIONES")
            aprobaciones = []
            total_aprobaciones = 0
            if listado_autorizaciones is not None:
                aprobacion_elem = listado_autorizaciones.find("APROBACION")
                if aprobacion_elem is not None:
                    aprobaciones = [
                        {
                            "NIT_EMISOR": {
                                "ref": dte.find("NIT_EMISOR").get("ref", ""),
                                "value": dte.find("NIT_EMISOR").text if dte.find("NIT_EMISOR") is not None and dte.find("NIT_EMISOR").text else ""
                            },
                            "CODIGO_APROBACION": dte.find("CODIGO_APROBACION").text if dte.find("CODIGO_APROBACION") is not None else "",
                            "IVA": float(dte.find("IVA").text) if dte.find("IVA") is not None else 0.0,
                            "VALOR": float(dte.find("VALOR").text) if dte.find("VALOR") is not None else 0.0
                        }
                        for dte in aprobacion_elem.findall("DTE")
                    ]
                total_aprobaciones = int(listado_autorizaciones.find("TOTAL_APROBACIONES").text) if listado_autorizaciones.find("TOTAL_APROBACIONES") is not None else 0

            autorizacion = {
                "FECHA": fecha,
                "FACTURAS_RECIBIDAS": facturas_recibidas,
                "ERRORES": errores,
                "FACTURAS_CORRECTAS": facturas_correctas,
                "CANTIDAD_EMISORES": cantidad_emisores,
                "CANTIDAD_RECEPTORES": cantidad_receptores,
                "LISTADO_AUTORIZACIONES": {
                    "APROBACION": aprobaciones,
                    "TOTAL_APROBACIONES": total_aprobaciones
                }
            }
            resultado.append(autorizacion)
        
        response = {"LISTAAUTORIZACIONES": resultado}
        print("Respuesta de /consultar:", response)  # Depuración
        return Response(
            json.dumps(response, ensure_ascii=False),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        print("Error en /consultar:", str(e))  # Depuración
        return Response(
            json.dumps({"error": f"Error consultando datos: {str(e)}"}),
            status=500,
            mimetype='application/json'
        )
    






@app.route('/reset', methods=['POST'])
def reset():
    try:
        if os.path.exists("autorizaciones.xml"):
            os.remove("autorizaciones.xml")
        return Response(json.dumps({"message": "Sistema reseteado"}), status=200, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True)