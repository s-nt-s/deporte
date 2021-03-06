#!/usr/bin/env python3

import calendar
import locale
import os
from datetime import datetime

import requests
from jinja2 import Environment, FileSystemLoader

import holidays
from api import DESAdapter, Portal, normalize
from crontab import CronTab
from weather import WeatherMadrid

import urllib3
urllib3.disable_warnings()

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

locale.setlocale(locale.LC_TIME, "es_ES.utf8")

H_MIN_F = 10.0
H_MIN_L = 15.3
H_MAX = 20.0

W_MIN = 2
W_MAX = 5

week = list(calendar.day_name)
now = datetime.now()
holi = holidays.ES(prov="MAD", years=now.year)
weather = WeatherMadrid()
out_file = "out/index.html"


def get_user_passwd(var, f):
    if var in os.environ:
        userpass = os.environ[var]
    else:
        userpass = open(f).read().strip()
    return userpass.split(" ")


def in_range(fch):
    dt = datetime.strptime(fch, '%Y-%m-%d %H:%M')
    if dt < now:
        return False
    h, m = fch.split(" ")[1].split(":")
    tm = int(h) + (int(m) / 100)
    if tm > H_MAX:
        return False
    w = dt.isoweekday()
    if w in (6, 7) or dt in holi:
        return tm >= H_MIN_F
    return tm >= H_MIN_L


def to_hh_mm(time):
    hours = int(time)
    minutes = (time * 100) % 100
    return "%02d:%02d" % (hours, minutes)


def get_paul():
    user, password = get_user_passwd("MADRID_ORG", ".ig_madrid.org")
    p = Portal("https://gestiona.madrid.org/cronosweb",
               user=user, password=password)
    p.operacion('01010000')
    p.centro(4)
    p.actividad(7)
    free = [f for f in p.fechas() if in_range(f)]
    return free


def get_mina():
    p = Portal(
        "https://deportesweb.madrid.es/deportesWeb/Login")  # , adapter=DESAdapter())
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


def get_class(w_day_hour):
    cls = ""
    if w_day_hour:
        if w_day_hour.get("prob_precipitacion", 0) >= 70:
            cls += " heavy_rain"
        elif w_day_hour.get("prob_precipitacion", 0) >= 50:
            cls += " soft_rain"

        if w_day_hour.get("viento", 0) > 15:
            cls += " wind"

        if w_day_hour.get("sens_termica", 0) >= 30:
            cls += " hot"
        elif w_day_hour.get("sens_termica", 0) <= 16:
            cls += " cold"
        if w_day_hour.get("estado_cielo_des", None):
            cls += " " + normalize(w_day_hour["estado_cielo_des"])
    if len(cls) > 1:
        cls = "weather " + cls
    return cls.strip()


def get_week_day(d):
    dt = datetime.strptime(d, '%Y-%m-%d')
    return dt.strftime("%A").title()


def to_pm(hm, short=False):
    h, m = hm.split(":")
    h = int(h)
    pm = h > 12
    if pm:
        h = h - 12
    rs = str(h)
    if not short or m != "00":
        rs += ":" + m
    if pm:
        return rs + " pm"
    return rs


def build_times(free, set_weather=False):
    splt = [f.split(" ") for f in free]
    days = sorted(set([f[0] for f in splt]))
    times = []
    for d in days:
        hours = [f[1] for f in splt if f[0] == d]
        hours_salas = []
        max_width = 0
        for h in sorted(set(hours)):
            w_day_hour = weather.day_hour(d, h) if set_weather else None
            hm = to_pm(h)
            width = len(hm.split(":")[0])
            hours_salas.append({
                "hour": hm,
                "weather": w_day_hour,
                "rooms": hours.count(h),
                "class": get_class(w_day_hour),
                "cielo": w_day_hour.get("estado_cielo_des", None) if w_day_hour else None,
                "width": width
            })
            max_width = max(width, max_width)
        times.append({
            "day": d,
            "hours": hours_salas,
            "caption": get_week_day(d),
            "max_width": max_width
        })
    return times


def get_cron():
    try:
        cron = CronTab(user=True)
        comments = []
        next_run = None
        for job in cron.find_command(abspath):
            if job.is_enabled() and job.is_valid():
                comments.append(job.comment.lower())
                schedule = job.schedule(date_from=datetime.now())
                dt = schedule.get_next()
                if next_run is None or next_run > dt:
                    next_run = dt
        summary = ", ".join(comments[:-1])
        if len(comments) > 1:
            summary += " y " + comments[-1]
        r = {
            "summary": summary,
            "next": next_run
        }
        return r
    except:
        return None

paul = get_paul()
mina = get_mina()

j2_env = Environment(loader=FileSystemLoader("templates"), trim_blocks=True)
out = j2_env.get_template('index.html')

html = out.render(data={
    "now": now,
    "mina": build_times(mina, set_weather=True),
    "paul": build_times(paul, set_weather=False),
    "h_min_l": to_pm(to_hh_mm(H_MIN_L), short=True),
    "h_min_f": to_pm(to_hh_mm(H_MIN_F), short=True),
    "h_max": to_pm(to_hh_mm(H_MAX), short=True),
    "w_min": week[W_MIN],
    "w_max": week[W_MAX],
    "cron": get_cron()
})
with open(out_file, "wb") as fh:
    fh.write(bytes(html, 'UTF-8'))
