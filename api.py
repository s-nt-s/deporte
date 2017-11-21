import json
import os
import re
import ssl
import sys
import time
import unicodedata as uc
from datetime import datetime
from urllib.parse import urlencode, urljoin

import bs4
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

requests.packages.urllib3.disable_warnings()

CIPHERS = 'RSA+3DES:!aNULL:!eNULL:!MD5'


class DESAdapter(HTTPAdapter):

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).proxy_manager_for(*args, **kwargs)


class Session():

    def __init__(self, root=None, adapter=None):
        self.s = requests.Session()
        if adapter:
            self.s.mount('https://', adapter)
        self.s.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
              "Cache-Control": "no-cache",
              "Pragma": "no-cache",
              "Expires": "Thu, 01 Jan 1970 00:00:00 GMT",
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
           'Accept-Encoding': 'gzip, deflate',
           'DNT': '1',
           'Connection': 'keep-alive',
           'Upgrade-Insecure-Requests': '1',
        }
        self.cookies = None
        self.root = root
        if root:
            self.get(root)

    def get_soup(self):
        self.soup = bs4.BeautifulSoup(self.response.content, "lxml")
        return self.soup

    def get(self, url, **kwargs):
        if self.cookies:
            kwargs["cookies"] = self.cookies
        if self.root:
            url = urljoin(self.root, url)
        self.response = self.s.get(url, verify=False, **kwargs)
        return self.response

    def post(self, url, **kwargs):
        if self.cookies:
            kwargs["cookies"] = self.cookies
        if self.root:
            url = urljoin(self.root, url)
        self.response = self.s.post(url, verify=False, **kwargs)
        return self.response

    def get_link(self, reg):
        l = self.get_soup().find("a", attrs={"href": reg})
        return urljoin(self.response.url, l.attrs["href"])


class Portal(Session):

    def __init__(self, url, user=None, password=None, adapter=None):
        super().__init__(url, adapter=adapter)
        self.root = self.response.url
        if self.response and self.response.text:
            text = self.response.text.strip()
            if not text.startswith("<") and len(text) < 200:
                raise Exception(text)

        url, data = self.get_form(user=user, password=password)

        data["__EVENTTARGET"] = "ctl00$ContentSection$lnkEntrar"
        if not user or not password:
            data[
                "__EVENTTARGET"] = "ctl00$ContentSection$lnkEntrarSinIdentificar"

        self.post(url, data=data)

        error = self.get_soup().select("#ContentSection_uAlert_spnAlertDanger")
        if len(error) > 0:
            error = error[0].get_text()
            error = re.sub(r"\s*\n\s*", r"\n", error)
            error = error.strip()
            raise Exception(error)

        ops = self.get_soup().select("#ContentSection_hdnOperaciones")
        value = ops[0].attrs["value"]
        self.operaciones = json.loads(value)

    def get_form(self, user=None, password=None):
        form = self.get_soup().find("form")
        data = {}
        for h in form.select("input"):
            if h.attrs.get("name", None) != None:
                name = h.attrs["name"]
                if user and "identificador" in name.lower():
                    data[name] = user
                elif password and "contrasena" in name.lower():
                    data[name] = password
                elif "value" in h.attrs:
                    data[name] = h.attrs["value"]
        return form.attrs["action"], data

    def operacion(self, codigo):
        ops = [o for o in self.operaciones if o["CodOperacion"] == codigo][0]
        url, data = self.get_form()
        data["__EVENTTARGET"] = "Continuar"
        data["__EVENTARGUMENT"] = codigo + ";" + \
            ops["NomOperacion"].replace(" ", "+") + ";" + ops["Url"]

        self.post(url, data=data)

        ops = self.get_soup().select("#ContentSection_uCentro_hdnCentros")
        value = ops[0].attrs["value"]
        self.centros = json.loads(value)

    def centro(self, codigo):
        ops = [o for o in self.centros if o["CodCentro"] == codigo][0]
        url, data = self.get_form()
        data["__EVENTTARGET"] = "Continuar"
        data["__EVENTARGUMENT"] = str(codigo) + ";" + ops[
            "NomCentro"].replace(" ", "+")
        self.post(url, data=data)

        ops = self.get_soup().select("#ContentSection_hdnActividades")
        value = ops[0].attrs["value"]
        self.actividades = json.loads(value)

    def actividad(self, codigo):
        ops = [o for o in self.actividades if o["CodActividad"] == codigo][0]
        url, data = self.get_form()
        data["__EVENTTARGET"] = "Continuar"
        data["__EVENTARGUMENT"] = str(codigo)
        self.post(url, data=data)

    def fechas(self):
        libre = []
        url, data = self.get_form()
        data["__EVENTTARGET"] = "Continuar"
        for f in self.get_soup().select("#ContentSection_divListaFechas a"):
            fecha = f.attrs["href"].split("'")[3]
            fch = "-".join(reversed(fecha.split("/")))
            data["__EVENTARGUMENT"] = fecha
            self.post(url, data=data)
            for l in self.get_soup().select("td img"):
                if l.attrs.get("estado", None) == "Libre":
                    hora = l.attrs["onclick"].split("'")[5]
                    libre.append(fch + " " + hora)
        return sorted(libre)


def normalize(s):
    s = ''.join((c for c in uc.normalize('NFD', s) if uc.category(c) != 'Mn'))
    s = s.replace(" ", "_")
    return s
