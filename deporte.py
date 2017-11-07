from api import Portal, DESAdapter
import os
from jinja2 import Environment, FileSystemLoader

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def in_range(fch):
    f, hm = fch.split(" ")
    h, m  = hm.split(":")
    tm = int(h) + (int(m)/100)
    return tm >= 15.5

def get_paul():
    userpass = open(".userpass").read().strip()
    user, password = userpass.split(" ")
    p = Portal("https://gestiona.madrid.org/cronosweb", user=user, password=password)
    p.operacion('01010000')
    p.centro(4)
    p.actividad(7)
    libre = [f for f in p.fechas() if in_range(f)]
    return libre

def get_mina():
    p = Portal(
        "https://deportesweb.madrid.es/deportesWeb/Login", adapter=DESAdapter())
    p.operacion('01010000')
    p.centro(17)
    p.actividad(64)
    libre = [f for f in p.fechas() if in_range(f)]
    return libre

paul = get_paul()
mina = get_mina()

j2_env = Environment(loader=FileSystemLoader("."), trim_blocks=True)
out = j2_env.get_template('template.html')
html = out.render(paul=paul, mina=mina)
print (html)
with open("out.html", "wb") as fh:
    fh.write(bytes(html, 'UTF-8'))

