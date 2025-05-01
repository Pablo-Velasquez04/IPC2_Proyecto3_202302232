import os
import xml.etree.ElementTree as ET

# Obtiene la ruta del archivo XML relativo al script actual
ruta_archivo = os.path.join(os.path.dirname(__file__), 'test.xml')

tree = ET.parse(ruta_archivo)
root = tree.getroot()

lista = []
for dte in root.iter('DTE'):
    tiempo = dte.find('TIEMPO')
    lista.append(tiempo.text)

print(lista)
