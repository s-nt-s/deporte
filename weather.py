import xml.etree.ElementTree as etree

import requests


class Weather():

    def __init__(self, url):
        response = requests.get(url)
        self.tree = etree.fromstring(response.content)

    def day_hour(self, day, hour):
        if isinstance(hour, str):
            hour = int(hour.split(":")[0])
        data = {}
        periodos = {'estado_cielo'}
        for t in self.tree.findall('.//prediccion/dia[@fecha="' + day + '"]/*'):
            if not t.text:
                continue
            periodo_ok = False
            if "periodo" in t.attrib:
                periodos.add(t.tag)
                hour1, hour2 = t.attrib["periodo"].split("-")
                if hour >= int(hour1) or hour < int(hour2):
                    periodo_ok = True
                    periodos.remove(t.tag)
            elif t.tag in periodos:
                periodo_ok = True
            if periodo_ok:
                data[t.tag] = t.text
                if t.tag == "viento":
                    data[t.tag] = t.find("velocidad").text
                if "descripcion" in t.attrib:
                    data[t.tag + "_des"] = t.attrib["descripcion"]
                continue
            for d in t.findall("dato"):
                if "hora" in d.attrib:
                    hour1 = d.attrib["hora"]
                    if hour >= int(hour1):
                        data[t.tag] = d.text
        for key, value in data.items():
            if value.isdigit():
                data[key] = int(value)

        return data


class WeatherMadrid(Weather):

    def __init__(self):
        super().__init__(
            "http://www.aemet.es/xml/municipios/localidad_28079.xml")
