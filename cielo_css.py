import unicodedata as uc
from urllib.parse import urljoin

import bs4
import requests

from api import normalize

root = "http://www.aemet.es/es/eltiempo/prediccion/municipios/ayuda"

r = requests.get(root)
soup = bs4.BeautifulSoup(r.content, "lxml")

with open("out/cielo.css", "w") as f:
    for img in soup.select("div.contenedor_iconos")[0].select("div.icono_ayuda img"):
        url = urljoin(root, img.attrs["src"])
        title = img.attrs["title"][9:]
        title = normalize(title)
        f.write('.icon.%s {background-image: url("%s");}\n' % (title, url))
