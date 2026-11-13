"""Kaart: verwachte sneeuwval dinsdag 17 november per model (ECMWF / GFS / ICON).

Drie panelen naast elkaar met de opgetelde sneeuwval (water-equivalent) over
dinsdag 17 november, plus een staafdiagram per plaats. Downburst Daan-huisstijl.

De modellen zijn het oneens: dat is hier het verhaal, niet de hoeveelheid.

Gebruik: python plot_snow_models.py
"""
import csv
import os

import cartopy.io.shapereader as shpreader
import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.font_manager import FontProperties
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
GRID = os.environ.get("SNOW_GRID", os.path.join(ROOT, "data", "sneeuw"))
PTS_CSV = os.path.join(GRID, "pts.csv")
OUT = os.path.join(ROOT, "output", "sneeuw_17nov_modellen.png")

W, H = 1080, 1350
NAVY, GOLD, WHITE, GREY = "#173f51", "#f1c40f", "#ffffff", "#c3d0d8"
SEA, LAND, GRIDLN = "#101f2b", "#1d3443", "#2c5468"
HEADER_H, GOLDLINE_H, FOOTER_H = 190, 5, 100

F = lambda n, s: FontProperties(fname=os.path.join(ASSETS, "fonts", n + ".ttf"), size=s)
MONT_XB = lambda s: F("Montserrat-ExtraBold", s)
MONT_B = lambda s: F("Montserrat-Bold", s)
ROB_B = lambda s: F("Roboto-Bold", s)
ROB = lambda s: F("Roboto-Regular", s)
OUTLINE = [pe.withStroke(linewidth=3, foreground="#000000")]

# Modelkleuren — vast per model, gevalideerd tegen het navy oppervlak
MODELS = [("ecmwf_ifs025", "ECMWF", "#b88c00"),
          ("ncep_gfs013", "GFS", "#2f97d0"),
          ("dwd_icon", "ICON", "#e0604f")]

LON0, LON1, LAT0, LAT1 = 2.30, 7.40, 49.40, 53.70

# Sneeuwval (mm water-equivalent ≈ cm sneeuw bij 10:1), oplopend donkerder
SNOW_LEVELS = [0.3, 0.5, 1, 2, 3, 5, 7, 10, 15]
SNOW_COLORS = ["#eaf5fc", "#c5e4f5", "#93cdec", "#5fb0de", "#3a8aca",
               "#2a63ae", "#2f4396", "#4a2b8c", "#6b1f7a"]
SNOW_CMAP = LinearSegmentedColormap.from_list(
    "sneeuw", list(zip(np.linspace(0, 1, len(SNOW_COLORS)), SNOW_COLORS)), N=512)

# (naam, lon, lat, label tonen, dx, dy, ha)
CITIES = [("Antwerpen", 4.40, 51.22, True, -0.10, 0.07, "right"),
          ("Brussel", 4.35, 50.85, True, -0.10, -0.30, "right"),
          ("Eindhoven", 5.47, 51.44, True, 0.10, 0.06, "left"),
          ("Enschede", 6.89, 52.22, True, -0.10, 0.06, "right"),
          ("Zwolle", 6.09, 52.51, False, 0, 0, "left"),
          ("Oostende", 2.92, 51.23, False, 0, 0, "left"),
          ("Luik", 5.57, 50.63, False, 0, 0, "left"),
          ("Botrange", 6.09, 50.50, False, 0, 0, "left"),
          ("Amsterdam", 4.90, 52.37, False, 0, 0, "left")]
BAR_PTS = ["Antwerpen", "Eindhoven", "Enschede", "Zwolle", "Brussel", "Oostende", "Botrange"]


def snow_index(v):
    """mm water-equivalent -> 0..1 op de klasse-schaal (klassen even breed)."""
    n = len(SNOW_LEVELS)
    return np.interp(v, SNOW_LEVELS, np.arange(n) / (n - 1))


def map_lines():
    out = {}
    for key, cat, name in [("coast", "physical", "coastline"),
                           ("borders", "cultural", "admin_0_boundary_lines_land")]:
        segs = []
        for geom in shpreader.Reader(shpreader.natural_earth("10m", cat, name)).geometries():
            b = geom.bounds
            if b[2] < LON0 - 1 or b[0] > LON1 + 1 or b[3] < LAT0 - 1 or b[1] > LAT1 + 1:
                continue
            for g in getattr(geom, "geoms", [geom]):
                segs.append(np.asarray(g.coords))
        out[key] = segs
    land = []
    for geom in shpreader.Reader(shpreader.natural_earth("10m", "physical", "land")).geometries():
        b = geom.bounds
        if b[2] < LON0 - 1 or b[0] > LON1 + 1 or b[3] < LAT0 - 1 or b[1] > LAT1 + 1:
            continue
        for g in getattr(geom, "geoms", [geom]):
            land.append(np.asarray(g.exterior.coords))
    out["land"] = land
    return out


def load_points():
    """Opgetelde sneeuwval per plaats en model voor 17 nov (uit pts.csv)."""
    acc = {}
    for r in csv.DictReader(open(PTS_CSV)):
        if not r["stamp"].startswith("2026-11-17"):
            continue
        v = r["swe_mm"]
        if v in ("", None):
            continue
        acc[(r["model"], r["punt"])] = acc.get((r["model"], r["punt"]), 0.0) + float(v)
    return acc


def fy(top_px, h_px):
    return 1 - (top_px + h_px) / H, h_px / H


def main():
    L = map_lines()
    pts = load_points()
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)

    # ---------- header
    y, hh = fy(0, HEADER_H)
    ax = fig.add_axes([0, y, 1, hh]); ax.set_axis_off()
    ax.text(0.028, 0.72, "EERSTE SNEEUW?", fontproperties=MONT_XB(60), color=GOLD,
            va="center", transform=ax.transAxes)
    ax.text(0.030, 0.42, "Dinsdag 17 november — de modellen zijn het oneens",
            fontproperties=ROB_B(25), color=WHITE, va="center", transform=ax.transAxes)
    ax.text(0.030, 0.17, "Sneeuwval over de hele dag  |  runs van do 12/11, 19:00 Belgische tijd",
            fontproperties=ROB_B(18), color=GREY, va="center", transform=ax.transAxes)
    lax = fig.add_axes([1 - 180 / W, 1 - 160 / H, 165 / W, 125 / H]); lax.set_axis_off()
    lax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA")))
    y, hh = fy(HEADER_H, GOLDLINE_H)
    g = fig.add_axes([0, y, 1, hh]); g.set_axis_off()
    g.add_patch(plt.Rectangle((0, 0), 1, 1, color=GOLD, transform=g.transAxes))

    # ---------- drie kaartpanelen
    top = HEADER_H + GOLDLINE_H + 8
    pw, gap = 338, 18
    ph = int(pw / 0.7383)   # hoekgetrouw op 51,5°N
    x0 = (W - (3 * pw + 2 * gap)) / 2
    for k, (mid, label, col) in enumerate(MODELS):
        d = np.load(os.path.join(GRID, f"acc_{mid}.npz"))
        swe, lat, lon = d["swe"], d["lat"], d["lon"]
        px = x0 + k * (pw + gap)
        t = fig.add_axes([px / W, 0, pw / W, 1]); t.set_axis_off()
        t.text(0.5, 1 - (top + 17) / H, label, fontproperties=MONT_B(24), color=col,
               ha="center", va="center", transform=t.transAxes)
        m = fig.add_axes([px / W, 1 - (top + 38 + ph) / H, pw / W, ph / H], facecolor=SEA)
        m.set_xlim(LON0, LON1); m.set_ylim(LAT0, LAT1); m.set_axis_off()
        for poly in L["land"]:
            m.fill(poly[:, 0], poly[:, 1], color=LAND, zorder=1, lw=0)
        ext = [lon[0], lon[-1], lat[0], lat[-1]]
        masked = np.ma.masked_array(snow_index(swe), swe < SNOW_LEVELS[0])
        m.imshow(masked, origin="lower", extent=ext, cmap=SNOW_CMAP, vmin=0, vmax=1,
                 interpolation="bilinear", zorder=2, aspect="auto")
        for seg in L["coast"]:
            m.plot(seg[:, 0], seg[:, 1], color="#8fa6b4", lw=0.7, zorder=4)
        for seg in L["borders"]:
            m.plot(seg[:, 0], seg[:, 1], color="#dce7ee", lw=1.0, zorder=4, alpha=0.9)
        for nm, clo, cla, show, dx, dy, ha in CITIES:
            m.plot(clo, cla, "o", ms=3.5, color=WHITE, mec="#000000", mew=0.7, zorder=6)
            if show:
                m.text(clo + dx, cla + dy, nm, fontproperties=ROB_B(11), color=WHITE, ha=ha,
                       va="bottom", zorder=6, path_effects=OUTLINE, clip_on=True)
        mx = float(np.nanmax(swe))
        m.text(0.5, 0.015, ("max %.1f mm" % mx) if mx >= 0.3 else "geen sneeuwval",
               transform=m.transAxes, fontproperties=ROB_B(14), color=WHITE, ha="center",
               va="bottom", zorder=9,
               bbox=dict(boxstyle="square,pad=0.22", fc="#000000", ec="none", alpha=0.72))
        for sp in ("left", "right", "top", "bottom"):
            m.spines[sp].set_visible(True); m.spines[sp].set_color(col); m.spines[sp].set_linewidth(2)
        m.set_frame_on(True)

    # ---------- kleurenbalk
    maps_bottom = top + 38 + ph
    cb_y, cb_h = maps_bottom + 50, 17
    c = fig.add_axes([0.08, 1 - (cb_y + cb_h) / H, 0.84, cb_h / H])
    c.imshow(np.linspace(0, 1, 512)[None, :], cmap=SNOW_CMAP, vmin=0, vmax=1, aspect="auto",
             extent=[0, 1, 0, 1])
    c.set_xlim(0, 1); c.set_ylim(0, 1); c.set_xticks([]); c.set_yticks([])
    for sp in c.spines.values():
        sp.set_visible(False)
    for v in SNOW_LEVELS:
        xv = float(snow_index(v))
        c.plot([xv, xv], [0, 1], color="#ffffff", lw=0.8, alpha=0.55, zorder=3)
        c.annotate("%g" % v, xy=(xv, 0), xytext=(0, -7), textcoords="offset points",
                   fontproperties=ROB_B(13), color=WHITE, ha="center", va="top",
                   annotation_clip=False)
    c.annotate("SNEEUWVAL IN MM WATER  (≈ cm sneeuw bij 10:1)", xy=(0.5, 1.0),
               xycoords="axes fraction", xytext=(0, 12), textcoords="offset points",
               fontproperties=MONT_B(16), color=GOLD, ha="center", va="bottom",
               annotation_clip=False)

    # ---------- staafdiagram per plaats
    bar_top = cb_y + cb_h + 135
    bar_h = 218
    b = fig.add_axes([0.095, 1 - (bar_top + bar_h) / H, 0.85, bar_h / H], facecolor=NAVY)
    for sp in b.spines.values():
        sp.set_visible(False)
    b.grid(axis="y", color=GRIDLN, lw=1)
    b.set_axisbelow(True)
    nm_ = len(MODELS)
    xs = np.arange(len(BAR_PTS))
    wdt = 0.26
    for k, (mid, label, col) in enumerate(MODELS):
        vals = [pts.get((mid, p), 0.0) for p in BAR_PTS]
        off = (k - (nm_ - 1) / 2) * wdt
        bars = b.bar(xs + off, vals, wdt * 0.92, color=col, label=label, zorder=3,
                     edgecolor=NAVY, linewidth=2)
        for xv, v in zip(xs + off, vals):
            if v >= 0.3:
                b.text(xv, v + 0.18, "%.1f" % v, fontproperties=ROB_B(12), color=WHITE,
                       ha="center", va="bottom", zorder=4)
    b.set_xticks(xs)
    b.set_xticklabels(BAR_PTS, fontproperties=ROB_B(14))
    b.tick_params(colors=GREY, length=0, labelsize=13)
    for lb in b.get_yticklabels():
        lb.set_fontproperties(ROB_B(13))
    b.set_ylabel("mm water", fontproperties=ROB_B(14), color=GREY)
    b.set_ylim(0, 9.5)
    b.text(0.0, 1.26, "Opgetelde sneeuwval per plaats — dinsdag 17 november",
           transform=b.transAxes, fontproperties=MONT_B(17), color=WHITE, va="bottom")
    leg = b.legend(loc="upper left", bbox_to_anchor=(0.0, 1.20), ncol=3, frameon=False,
                   prop=ROB_B(15), handlelength=1.4, columnspacing=1.8)
    for t_ in leg.get_texts():
        t_.set_color(WHITE)

    # ---------- bronregel
    note_top = bar_top + bar_h + 38          # onder de plaatsnamen van het staafdiagram
    note = fig.add_axes([0, 1 - (note_top + 58) / H, 1, 58 / H]); note.set_axis_off()
    note.text(0.5, 0.62, "ICON geeft nul sneeuw: dat model is 3 tot 5 °C warmer aan de grond.",
              fontproperties=ROB_B(16), color=GOLD, ha="center", va="center", transform=note.transAxes)
    note.text(0.5, 0.18, "Bron: ECMWF IFS 0,25° · NCEP GFS 0,13° · DWD ICON globaal, via Open-Meteo  |  "
              "Natural Earth", fontproperties=ROB(13), color=GREY, ha="center", va="center",
              transform=note.transAxes)

    fax = fig.add_axes([0, 0, 1, FOOTER_H / H]); fax.set_axis_off()
    fax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA")),
               aspect="auto")

    fig.savefig(OUT, dpi=100, facecolor=NAVY)
    print(OUT)


if __name__ == "__main__":
    main()
