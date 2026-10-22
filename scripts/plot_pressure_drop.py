"""Grafiek: kerndrukverloop van storm Austen per model (bomcycloon-check), Downburst Daan-huisstijl.

Leest data/drukverloop_modellen.csv (globale modellen, run wo 21/10 12 UTC; analyses van
latere runs) en data/track_austen.csv (ICON-D2, run do 22/10 09 UTC).

Gebruik: python plot_pressure_drop.py
"""
import csv
import os
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "output", "storm_austen_drukverloop_modellen.png")
BE_TZ = timezone(timedelta(hours=2))

W, H = 1080, 1350
NAVY, GOLD, WHITE, GREY, GRID = "#173f51", "#f1c40f", "#ffffff", "#c3d0d8", "#2c5468"
HEADER_H, FOOTER_H = 190, 100

F = lambda name, size: FontProperties(fname=os.path.join(ASSETS, "fonts", name + ".ttf"), size=size)
MONT_XB = lambda s: F("Montserrat-ExtraBold", s)
MONT_B = lambda s: F("Montserrat-Bold", s)
ROB_B = lambda s: F("Roboto-Bold", s)
ROB = lambda s: F("Roboto-Regular", s)

# Gevalideerd categorisch palet (donker oppervlak #173f51), vaste volgorde
MODELS = [
    ("ECMWF IFS", "#b88c00"),
    ("GFS", "#2f97d0"),
    ("UKMO", "#e0604f"),
    ("ICON", "#9a7ce0"),
    ("ICON-D2", "#3aa86b"),
]
RUN = "2026_10_21_1200Z"


def t_be(s):
    return datetime.strptime(s, "%Y-%m-%dT%H%M").replace(tzinfo=timezone.utc).astimezone(BE_TZ).replace(tzinfo=None)


def load():
    series, analyses = {}, []
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "drukverloop_modellen.csv"))))
    for r in rows:
        if r["run"] == RUN:
            series.setdefault(r["model"], []).append((t_be(r["tijd_utc"]), float(r["kerndruk_hpa"])))
    # Analyses (t+0) van opeenvolgende ECMWF-runs
    first = {}
    for r in rows:
        if r["model"] == "ECMWF IFS":
            first.setdefault(r["run"], (t_be(r["tijd_utc"]), float(r["kerndruk_hpa"])))
    analyses = sorted(first.values())
    d2 = [(t_be(r["tijd_utc"]), float(r["kerndruk_hpa"]))
          for r in csv.DictReader(open(os.path.join(ROOT, "data", "track_austen.csv")))
          if r["tijd_utc"] <= "2026-10-24T0000"]
    series["ICON-D2"] = d2
    return series, analyses


def max_drop(pts):
    best = None
    d = dict(pts)
    for t, p in pts:
        t2 = t + timedelta(hours=24)
        if t2 in d and (best is None or p - d[t2] > best[0]):
            best = (p - d[t2], t, t2, p, d[t2])
    return best


def main():
    series, analyses = load()
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)

    # header
    ax = fig.add_axes([0, 1 - HEADER_H / H, 1, HEADER_H / H]); ax.set_axis_off()
    ax.text(0.028, 0.70, "STORM AUSTEN", fontproperties=MONT_XB(64), color=GOLD, va="center", transform=ax.transAxes)
    ax.text(0.030, 0.39, "Bomcycloon? Kerndruk per model", fontproperties=ROB_B(27), color=WHITE,
            va="center", transform=ax.transAxes)
    ax.text(0.030, 0.15, "Runs: globaal wo 21/10 14u  |  ICON-D2 do 22/10 11u (Belgische tijd)",
            fontproperties=ROB_B(18), color=GREY, va="center", transform=ax.transAxes)
    lax = fig.add_axes([1 - 180 / W, 1 - 160 / H, 165 / W, 125 / H]); lax.set_axis_off()
    lax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA")))
    gax = fig.add_axes([0, 1 - (HEADER_H + 5) / H, 1, 5 / H]); gax.set_axis_off()
    gax.add_patch(plt.Rectangle((0, 0), 1, 1, color=GOLD, transform=gax.transAxes))

    # kerncijfer
    ec = max_drop(series["ECMWF IFS"])
    drops = [max_drop(series[m])[0] for m, _ in MODELS[:4]]
    k = fig.add_axes([0, 1 - (HEADER_H + 5 + 150) / H, 1, 150 / H]); k.set_axis_off()
    k.text(0.05, 0.62, f"−{min(drops):.0f} tot −{max(drops):.0f} hPa", fontproperties=MONT_XB(46), color=GOLD,
           va="center", transform=k.transAxes)
    k.text(0.05, 0.22, "in 24 uur boven de Atlantische Oceaan  ·  bomgrens op 48°N: −20,5 hPa",
           fontproperties=ROB_B(19), color=WHITE, va="center", transform=k.transAxes)

    # grafiek
    top = HEADER_H + 5 + 150
    a = fig.add_axes([0.105, (FOOTER_H + 120) / H, 0.80, (H - top - FOOTER_H - 145) / H], facecolor=NAVY)
    for sp in a.spines.values():
        sp.set_visible(False)
    a.grid(axis="y", color=GRID, lw=1)
    a.tick_params(colors=GREY, length=0, labelsize=14)
    for lbl in a.get_xticklabels() + a.get_yticklabels():
        lbl.set_fontproperties(ROB_B(14))

    # bomvenster (ECMWF) + bomgrens-helling
    _, t0, t1, p0, p1 = ec
    a.axvspan(t0, t1, color=GOLD, alpha=0.10, lw=0, zorder=0)
    a.text(t0 + (t1 - t0) / 2, 1012.2, "24 uur explosieve verdieping", fontproperties=ROB_B(15), color=GOLD,
           ha="center", va="bottom")
    a.plot([t0, t1], [p0, p0 - 20.5], color=WHITE, lw=2, ls=(0, (5, 4)), alpha=0.8, zorder=2)
    a.text(t1 + timedelta(hours=1), p0 - 20.5, "bomgrens\n−20,5 hPa/24 u", fontproperties=ROB_B(14),
           color=WHITE, va="center", ha="left", alpha=0.9)

    for name, col in MODELS:
        pts = series[name]
        x, y = zip(*pts)
        a.plot(x, y, color=col, lw=3, zorder=4, solid_capstyle="round",
               path_effects=[pe.withStroke(linewidth=5, foreground=NAVY)])
        a.plot(x, y, "o", ms=5, color=col, zorder=4)
    tx, ty = zip(*analyses)
    a.plot(tx, ty, "D", ms=10, color=WHITE, mec=NAVY, mew=2, zorder=6, label="ECMWF-analyse")

    # dieptepunt-annotatie
    pm = min(min(p for _, p in s) for s in series.values())
    a.axhline(pm, color=GREY, lw=1, ls=":", zorder=1)
    a.text(datetime(2026, 10, 21, 14), pm - 0.4, f"dieptepunt ± {pm:.0f} hPa (do-avond, ten ZW van Cornwall)",
           fontproperties=ROB_B(14), color=GREY, va="top")

    a.set_ylim(970, 1013)
    a.set_yticks(range(975, 1011, 5))
    a.set_xlim(datetime(2026, 10, 21, 13, 30), datetime(2026, 10, 24, 6))
    a.set_ylabel("Kerndruk (hPa)", fontproperties=ROB_B(16), color=GREY)
    a.xaxis.set_major_locator(mdates.HourLocator(byhour=[2, 14]))
    days = ["ma", "di", "wo", "do", "vr", "za", "zo"]
    a.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: (lambda d: f"{days[d.weekday()]} {d:%H}u")(mdates.num2date(v))))

    # legende (analyse-markers + bron)
    lg = fig.add_axes([0, (FOOTER_H + 8) / H, 1, 70 / H]); lg.set_axis_off()
    x = 0.05
    for name, col in MODELS:
        lg.plot([x, x + 0.03], [0.72, 0.72], color=col, lw=5, transform=lg.transAxes, solid_capstyle="round")
        t = lg.text(x + 0.04, 0.72, name, fontproperties=ROB_B(16), color=WHITE, va="center", transform=lg.transAxes)
        x += 0.07 + 0.0125 * len(name)
    lg.plot([0.05 + 0.015], [0.2], "D", ms=10, color=WHITE, mec=NAVY, mew=2, transform=lg.transAxes)
    lg.text(0.09, 0.2, "ECMWF-analyse (startpunt latere runs)", fontproperties=ROB_B(15), color=WHITE,
            va="center", transform=lg.transAxes)
    lg.text(0.97, 0.2, "Bron: ECMWF, NCEP, UKMO, DWD via Open-Meteo", fontproperties=ROB(14), color=GREY,
            va="center", ha="right", transform=lg.transAxes)

    fax = fig.add_axes([0, 0, 1, FOOTER_H / H]); fax.set_axis_off()
    fax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA")), aspect="auto")

    fig.savefig(OUT, dpi=100, facecolor=NAVY)
    print(OUT)


if __name__ == "__main__":
    main()
