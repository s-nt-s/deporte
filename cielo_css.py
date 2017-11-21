import os
import unicodedata as uc
from ftplib import FTP
from urllib.parse import urljoin

import bs4
import requests

from api import normalize

root = "http://www.aemet.es/es/eltiempo/prediccion/municipios/ayuda"
out_file = "out/cielo.css"

r = requests.get(root)
soup = bs4.BeautifulSoup(r.content, "lxml")

with open(out_file, "w") as f:
    for img in soup.select("div.contenedor_iconos")[0].select("div.icono_ayuda img"):
        url = urljoin(root, img.attrs["src"])
        title = img.find_next_sibling("p").get_text()
        title = normalize(title)
        f.write('.%s .cielo {background-image: url("%s");}\n' % (title, url))


ftp_con = open(".ig_ftp").read().strip()
host, user, passwd, path = ftp_con.split(" ")
ftp = FTP(host)
ftp.login(user=user, passwd=passwd)
ftp.cwd(path)
with open(out_file, 'rb') as fh:
    ftp.storbinary('STOR ' + os.path.basename(out_file), fh)
ftp.quit()
