import calendar
import json
import locale
import os
from datetime import date, datetime

from jinja2 import Environment, FileSystemLoader

from api import DESAdapter, Portal
import holidays

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

locale.setlocale(locale.LC_TIME, "es_ES.utf8")

H_MIN = 15.3
H_MAX = 20.0

W_MIN = 1
W_MAX = 4

week = list(calendar.day_name)
now = datetime.now()
holi = holidays.ES(prov="MAD", years=now.year)


def in_range(fch):
    dt = datetime.strptime(fch, '%Y-%m-%d %H:%M')
    if dt < now:
        return False
    if dt in holi:
        return True
    w = dt.weekday()
    if w in (5, 6):
        return True
    #if w < W_MIN or w > W_MAX:
    #    return False
    h, m = fch.split(" ")[1].split(":")
    tm = int(h) + (int(m) / 100)
    return tm >= H_MIN and tm <= H_MAX


def to_hh_mm(time):
    hours = int(time)
    minutes = (time * 100) % 100
    return "%02d:%02d" % (hours, minutes)


def get_paul():
    userpass = open(".userpass").read().strip()
    user, password = userpass.split(" ")
    p = Portal("https://gestiona.madrid.org/cronosweb",
               user=user, password=password)
    p.operacion('01010000')
    p.centro(4)
    p.actividad(7)
    free = [f for f in p.fechas() if in_range(f)]
    return free


def get_mina():
    p = Portal(
        "https://deportesweb.madrid.es/deportesWeb/Login", adapter=DESAdapter())
    p.operacion('01010000')
    p.centro(17)
    p.actividad(64)
    free = [f for f in p.fechas() if in_range(f)]
    return free


def get_mina_squash():
    p = Portal(
        "https://deportesweb.madrid.es/deportesWeb/Login", adapter=DESAdapter())
    p.operacion('01010000')
    p.centro(17)
    p.actividad(73)
    free = [f for f in p.fechas() if in_range(f)]
    return free


def get_week_day(d):
    dt = datetime.strptime(d, '%Y-%m-%d')
    return dt.strftime("%A").title()


def to_pm(hm, short=False):
    h, m = hm.split(":")
    h = int(h)
    if h < 13:
        return hm
    h = h - 12
    if short and m == "00":
        return str(h) + " pm"
    return "%s:%s pm" % (h, m)


def build_times(free):
    splt = [f.split(" ") for f in free]
    days = sorted(set([f[0] for f in splt]))
    times = []
    for d in days:
        hours = [to_pm(f[1]) for f in splt if f[0] == d]
        hours_salas = []
        for h in sorted(set(hours)):
            salas = hours.count(h)
            if salas > 1:
                h = h + (" (%s salas)" % salas)
            hours_salas.append(h)
        times.append({
            "day": d,
            "hours": hours_salas,
            "caption": get_week_day(d)
        })
    return times

paul = get_paul()
mina = get_mina()

j2_env = Environment(loader=FileSystemLoader("templates"), trim_blocks=True)
out = j2_env.get_template('index.html')
html = out.render(data={
    "now": now.strftime("%A %d a las %H:%M").replace(" 0", " "),
    "mina": build_times(mina),
    "paul": build_times(paul),
    "h_min": to_pm(to_hh_mm(H_MIN), short=True),
    "h_max": to_pm(to_hh_mm(H_MAX), short=True),
    "w_min": week[W_MIN],
    "w_max": week[W_MAX]
})
with open("out/index.html", "wb") as fh:
    fh.write(bytes(html, 'UTF-8'))
