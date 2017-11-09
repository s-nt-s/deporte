#!/usr/bin/env python3

import calendar
import json
import locale
import os
import xml.etree.ElementTree as etree
from datetime import date, datetime
from ftplib import FTP

import requests
from jinja2 import Environment, FileSystemLoader

import holidays
from crontab import CronTab

from api import DESAdapter, Portal
from weather import WeatherMadrid

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

locale.setlocale(locale.LC_TIME, "es_ES.utf8")

H_MIN = 15.3
H_MAX = 20.0

W_MIN = 2
W_MAX = 5

week = list(calendar.day_name)
now = datetime.now()
holi = holidays.ES(prov="MAD", years=now.year)
weather = WeatherMadrid()
out_file = "out/index.html"


def in_range(fch):
    dt = datetime.strptime(fch, '%Y-%m-%d %H:%M')
    if dt < now:
        return False
    if dt in holi:
        return True
    w = dt.isoweekday()
    if w in (6, 7):
        return True
    # if w < W_MIN or w > W_MAX:
    #    return False
    h, m = fch.split(" ")[1].split(":")
    tm = int(h) + (int(m) / 100)
    return tm >= H_MIN and tm <= H_MAX


def to_hh_mm(time):
    hours = int(time)
    minutes = (time * 100) % 100
    return "%02d:%02d" % (hours, minutes)


def get_paul():
    userpass = open(".ig_madrid.org").read().strip()
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


def get_class(w_day_hour):
    cls = ""
    if w_day_hour:
        return ""
        if w_day_hour.get("prob_precipitacion", 0) > 50:
            cls += " heavy_rain"
        elif w_day_hour.get("prob_precipitacion", 0) > 5:
            cls += " soft_rain"

        if w_day_hour.get("viento", 0) > 20:
            cls += " heavy_wind"
        elif w_day_hour.get("viento", 0) > 5:
            cls += " soft_wind"

        if w_day_hour.get("sens_termica", 0) > 30:
            cls += " heavy_hot"
        elif w_day_hour.get("sens_termica", 0) < 20:
            cls += " heavy_cold"
    if len(cls) > 1:
        cls = "weather " + cls
    return cls.strip()


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


def build_times(free, set_weather=False):
    splt = [f.split(" ") for f in free]
    days = sorted(set([f[0] for f in splt]))
    times = []
    for d in days:
        hours = [f[1] for f in splt if f[0] == d]
        hours_salas = []
        for h in sorted(set(hours)):
            w_day_hour = weather.day_hour(d, h) if set_weather else None
            hours_salas.append({
                "hour": to_pm(h),
                "weather": w_day_hour,
                "rooms": hours.count(h),
                "class": get_class(w_day_hour)
            })
        times.append({
            "day": d,
            "hours": hours_salas,
            "caption": get_week_day(d)
        })
    return times

def get_cron():
    cron = CronTab(user=True)
    comments = []
    next_run = None
    for job in cron.find_command(abspath):
        if job.is_enabled() and job.is_valid():
            comments.append(job.comment.lower())
            schedule = job.schedule(date_from=datetime.now())
            dt = schedule.get_next()
            if next_run is None or next_run>dt:
                next_run = dt
    summary = ", ".join(comments[:-1])
    if len(comments)>1:
        summary += " y "+comments[-1]
    r = {
        "summary": summary,
        "next": next_run.strftime("%A %d a las %H:%M").replace(" 0", " ") if next_run else None
    }
    return r

paul = get_paul()
mina = get_mina()

j2_env = Environment(loader=FileSystemLoader("templates"), trim_blocks=True)
out = j2_env.get_template('index.html')
html = out.render(data={
    "now": now.strftime("%A %d a las %H:%M").replace(" 0", " "),
    "mina": build_times(mina, set_weather=True),
    "paul": build_times(paul, set_weather=False),
    "h_min": to_pm(to_hh_mm(H_MIN), short=True),
    "h_max": to_pm(to_hh_mm(H_MAX), short=True),
    "w_min": week[W_MIN],
    "w_max": week[W_MAX],
    "cron": get_cron()
})
with open(out_file, "wb") as fh:
    fh.write(bytes(html, 'UTF-8'))


ftp_con = open(".ig_ftp").read().strip()
host, user, passwd, path = ftp_con.split(" ")
ftp = FTP(host)
ftp.login(user=user, passwd=passwd)
ftp.cwd(path)
with open(out_file, 'rb') as fh:
    ftp.storbinary('STOR ' + os.path.basename(out_file), fh)
ftp.quit()
