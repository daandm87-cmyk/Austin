"""Kaart: sneeuwdek op de grond op dinsdag 17 november, vier modellen van fijn naar grof.

Toont het werkelijke sneeuwdek (cm) in plaats van water-equivalent, plus een
puntdiagram van de laagste 2m-temperatuur per plaats. Dat laatste verklaart het
verschil: de modellen zitten tot 4 °C uit elkaar aan de grond.

Gebruik: python plot_snow_depth.py
"""
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
GRID = os.environ.get("SNOW_GRID2", os.path.join(ROOT, "data", "sneeuw2"))
OUT = os.path.join(ROOT, "output", "sneeuwdek_17nov_modellen.png")

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

# Van fijn naar grof. Kleuren gevalideerd tegen het navy oppervlak (CVD-waarschuwing
# afgedekt door de waardelabels in het puntdiagram).
MODELS = [("dwd_icon_eu", "ICON-EU", "6,5 km · run 13/11 01u", "#3aa86b"),
          ("ncep_gfs013", "GFS", "13 km · run 12/11 19u", "#2f97d0"),
          ("dwd_icon", "ICON", "13 km · run 13/11 01u", "#d45a9a"),
          ("ecmwf_ifs025", "ECMWF", "25 km · run 12/11 19u", "#b88c00")]

LON0, LON1, LAT0, LAT1 = 2.30, 7.40, 49.40, 53.70

# Sneeuwdek in cm
SD_LEVELS = [0.5, 1, 2, 3, 5, 8, 12, 20]
SD_COLORS = ["#dcecf8", "#a9d6f0", "#6fb8e4", "#3f8fcf", "#2a63ae", "#33409a", "#4a2b8c", "#6b1f7a"]
SD_CMAP = LinearSegmentedColormap.from_list(
    "sneeuwdek", list(zip(np.linspace(0, 1, len(SD_COLORS)), SD_COLORS)), N=512)

CITIES = [("Antwerpen", 4.40, 51.22, True, -0.10, 0.07, "right"),
          ("Brussel", 4.35, 50.85, True, -0.10, -0.30, "right"),
          ("Eindhoven", 5.47, 51.44, True, 0.10, 0.06, "left"),
          ("Enschede", 6.89, 52.22, True, -0.10, 0.06, "right"),
          ("Zwolle", 6.09, 52.51, False, 0, 0, "left"),
          ("Oostende", 2.92, 51.23, False, 0, 0, "left"),
          ("Botrange", 6.09, 50.50, False, 0, 0, "left")]
DOT_PTS = [("Oostende", 51.23, 2.92), ("Antwerpen", 51.22, 4.40), ("Brussel", 50.85, 4.35),
           ("Eindhoven", 51.44, 5.47), ("Enschede", 52.22, 6.89), ("Zwolle", 52.51, 6.09),
           ("Botrange", 50.50, 6.09)]


def sd_index(v):
    n = len(SD_LEVELS)
    return np.interp(v, SD_LEVELS, np.arange(n) / (n - 1))


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


def main():
    L = map_lines()
    data = {m: np.load(os.path.join(GRID, f"acc2_{m}.npz")) for m, *_ in MODELS}
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)

    # ---------- header
    ax = fig.add_axes([0, 1 - HEADER_H / H, 1, HEADER_H / H]); ax.set_axis_off()
    ax.text(0.028, 0.73, "SNEEUW DINSDAG?", fontproperties=MONT_XB(55), color=GOLD,
            va="center", transform=ax.transAxes)
    ax.text(0.030, 0.44, "Sneeuwdek op de grond — dinsdag 17 november",
            fontproperties=ROB_B(25), color=WHITE, va="center", transform=ax.transAxes)
    ax.text(0.030, 0.18, "Vier modellen, van fijn naar grof  |  alleen GFS legt sneeuw neer",
            fontproperties=ROB_B(18), color=GREY, va="center", transform=ax.transAxes)
    lax = fig.add_axes([1 - 180 / W, 1 - 160 / H, 165 / W, 125 / H]); lax.set_axis_off()
    lax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA")))
    g = fig.add_axes([0, 1 - (HEADER_H + GOLDLINE_H) / H, 1, GOLDLINE_H / H]); g.set_axis_off()
    g.add_patch(plt.Rectangle((0, 0), 1, 1, color=GOLD, transform=g.transAxes))

    # ---------- vier kaartpanelen
    top = HEADER_H + GOLDLINE_H + 8
    pw, gap = 258, 10
    ph = int(pw / 0.7383)
    x0 = (W - (4 * pw + 3 * gap)) / 2
    for k, (mid, label, sub, col) in enumerate(MODELS):
        d = data[mid]
        sd, lat, lon = d["sd"], d["lat"], d["lon"]
        px = x0 + k * (pw + gap)
        t = fig.add_axes([px / W, 0, pw / W, 1]); t.set_axis_off()
        t.text(0.5, 1 - (top + 16) / H, label, fontproperties=MONT_B(22), color=col,
               ha="center", va="center", transform=t.transAxes)
        t.text(0.5, 1 - (top + 36) / H, sub, fontproperties=ROB(12), color=GREY,
               ha="center", va="center", transform=t.transAxes)
        m = fig.add_axes([px / W, 1 - (top + 48 + ph) / H, pw / W, ph / H], facecolor=SEA)
        m.set_xlim(LON0, LON1); m.set_ylim(LAT0, LAT1); m.set_axis_off()
        for poly in L["land"]:
            m.fill(poly[:, 0], poly[:, 1], color=LAND, zorder=1, lw=0)
        ext = [lon[0], lon[-1], lat[0], lat[-1]]
        masked = np.ma.masked_array(sd_index(sd), sd < SD_LEVELS[0])
        m.imshow(masked, origin="lower", extent=ext, cmap=SD_CMAP, vmin=0, vmax=1,
                 interpolation="nearest", zorder=2, aspect="auto")
        for seg in L["coast"]:
            m.plot(seg[:, 0], seg[:, 1], color="#8fa6b4", lw=0.6, zorder=4)
        for seg in L["borders"]:
            m.plot(seg[:, 0], seg[:, 1], color="#dce7ee", lw=0.9, zorder=4, alpha=0.9)
        for nm, clo, cla, show, dx, dy, ha in CITIES:
            m.plot(clo, cla, "o", ms=2.8, color=WHITE, mec="#000000", mew=0.6, zorder=6)
        mx = float(np.nanmax(sd))
        m.text(0.5, 0.022, ("max %.0f cm" % mx) if mx >= 0.5 else "geen sneeuw",
               transform=m.transAxes, fontproperties=ROB_B(14), color=WHITE, ha="center",
               va="bottom", zorder=9,
               bbox=dict(boxstyle="square,pad=0.22", fc="#000000", ec="none", alpha=0.75))
        for sp in ("left", "right", "top", "bottom"):
            m.spines[sp].set_visible(True); m.spines[sp].set_color(col); m.spines[sp].set_linewidth(2)
        m.set_frame_on(True)

    # ---------- kleurenbalk sneeuwdek
    maps_bottom = top + 48 + ph
    cb_y, cb_h = maps_bottom + 50, 16
    c = fig.add_axes([0.16, 1 - (cb_y + cb_h) / H, 0.68, cb_h / H])
    c.imshow(np.linspace(0, 1, 512)[None, :], cmap=SD_CMAP, vmin=0, vmax=1, aspect="auto",
             extent=[0, 1, 0, 1])
    c.set_xlim(0, 1); c.set_ylim(0, 1); c.set_xticks([]); c.set_yticks([])
    for sp in c.spines.values():
        sp.set_visible(False)
    for v in SD_LEVELS:
        xv = float(sd_index(v))
        c.plot([xv, xv], [0, 1], color=WHITE, lw=0.8, alpha=0.55, zorder=3)
        c.annotate("%g" % v, xy=(xv, 0), xytext=(0, -7), textcoords="offset points",
                   fontproperties=ROB_B(13), color=WHITE, ha="center", va="top",
                   annotation_clip=False)
    c.annotate("SNEEUWDEK IN CM", xy=(0.5, 1.0), xycoords="axes fraction",
               xytext=(0, 12), textcoords="offset points", fontproperties=MONT_B(16),
               color=GOLD, ha="center", va="bottom", annotation_clip=False)

    # ---------- puntdiagram laagste temperatuur
    dp_top = cb_y + cb_h + 138
    dp_h = 310
    b = fig.add_axes([0.20, 1 - (dp_top + dp_h) / H, 0.74, dp_h / H], facecolor=NAVY)
    for sp in b.spines.values():
        sp.set_visible(False)
    b.grid(axis="x", color=GRIDLN, lw=1)
    b.set_axisbelow(True)
    ys = np.arange(len(DOT_PTS))[::-1]
    for yi, (nm, pla, plo) in zip(ys, DOT_PTS):
        vals = []
        for mid, label, sub, col in MODELS:
            d = data[mid]
            i = int(np.argmin(abs(d["lat"] - pla))); j = int(np.argmin(abs(d["lon"] - plo)))
            vals.append((float(d["tmin"][i, j]), col))
        lo_, hi_ = min(v for v, _ in vals), max(v for v, _ in vals)
        b.plot([lo_, hi_], [yi, yi], color="#43708a", lw=2.5, zorder=2, solid_capstyle="round")
        for v, col in vals:
            b.plot(v, yi, "o", ms=11, color=col, mec=NAVY, mew=1.8, zorder=4)
        b.text(hi_ + 0.22, yi, "%.1f°" % hi_, fontproperties=ROB_B(12), color=GREY,
               va="center", ha="left", zorder=4)
        b.text(lo_ - 0.22, yi, "%.1f°" % lo_, fontproperties=ROB_B(12), color=GREY,
               va="center", ha="right", zorder=4)
    b.axvline(0, color=WHITE, lw=1.6, ls=(0, (4, 3)), alpha=0.8, zorder=3)
    b.text(0, len(DOT_PTS) - 0.45, " vriespunt", fontproperties=ROB_B(13), color=WHITE,
           ha="left", va="center")
    b.set_yticks(ys)
    b.set_yticklabels([n for n, _, _ in DOT_PTS], fontproperties=ROB_B(14))
    b.set_ylim(-0.7, len(DOT_PTS) - 0.1)
    b.set_xlim(-2.2, 7.6)
    b.tick_params(colors=GREY, length=0, labelsize=13)
    for lb in b.get_xticklabels():
        lb.set_fontproperties(ROB_B(13))
    b.set_xlabel("laagste 2m-temperatuur op dinsdag (°C)", fontproperties=ROB_B(14), color=GREY)
    b.text(0.0, 1.22, "Waarom de modellen verschillen: de temperatuur aan de grond",
           transform=b.transAxes, fontproperties=MONT_B(17), color=WHITE, va="bottom")
    handles = [plt.Line2D([], [], marker="o", ls="", ms=11, color=col, mec=NAVY, mew=1.8, label=lb)
               for _, lb, _, col in MODELS]
    leg = b.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.11), ncol=4,
                   frameon=False, prop=ROB_B(14), handletextpad=0.3, columnspacing=1.3)
    for t_ in leg.get_texts():
        t_.set_color(WHITE)

    # ---------- bronregel
    note_top = dp_top + dp_h + 50
    note = fig.add_axes([0, 1 - (note_top + 58) / H, 1, 58 / H]); note.set_axis_off()
    note.text(0.5, 0.66, "ICON-EU is het fijnste model dat zover komt — en houdt het op regen.",
              fontproperties=ROB_B(16), color=GOLD, ha="center", va="center", transform=note.transAxes)
    note.text(0.5, 0.20, "Sneeuwdek = wat het model op de grond laat liggen.  Bron: DWD, NCEP, "
              "ECMWF via Open-Meteo  |  Natural Earth",
              fontproperties=ROB(13), color=GREY, ha="center", va="center", transform=note.transAxes)

    fax = fig.add_axes([0, 0, 1, FOOTER_H / H]); fax.set_axis_off()
    fax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA")),
               aspect="auto")

    fig.savefig(OUT, dpi=100, facecolor=NAVY)
    print(OUT)


if __name__ == "__main__":
    main()
