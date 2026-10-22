"""Animatie: baan van de lagedrukkern (L) van storm Austen boven de maximale windstoten (ICON-D2).

Huisstijl Downburst Daan, Nederlandstalig, 1080x1350 (4:5, sociale media).

Tussen de uurlijkse modelvelden wordt bewegingsgecompenseerd geïnterpoleerd: beide
velden worden langs de verplaatsing van de kern naar het tussentijdstip geschoven
en daarna gemengd. Zo glijden de windvelden en isobaren mee met de storm in plaats
van uit- en in te faden. De L volgt een kubische spline door de uurposities.

Gebruik: python render_animation.py [--preview-only]
"""
import csv
import glob
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from multiprocessing import Pool

import cartopy.io.shapereader as shpreader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter, map_coordinates

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "icon_d2")
TRACK = os.path.join(ROOT, "data", "track_austen.csv")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "output")
FRAMES = os.environ.get("FRAMES_DIR", os.path.join(OUT, "_frames"))

RUN_LABEL = "do 22/10 09 UTC"
START, END = "2026-10-23T0700", "2026-10-24T0000"
SUBSTEPS = 16          # tussenbeelden per modeluur
FPS = 30
HOLD_START, HOLD_END = 1.0, 2.5  # seconden stilstand
BE_TZ = timezone(timedelta(hours=2))  # CEST (zomertijd tot 25 okt 2026)

# Kaartuitsnede: België + oostelijk Kanaal (ICON-D2 reikt niet verder dan ~2°W)
LON0, LON1 = -2.6, 8.6
LAT0, LAT1 = 48.70, 54.08

# Huisstijl
W, H = 1080, 1350
NAVY = "#173f51"
NAVY_DARK = "#0e2d40"
PANEL = "#254e61"
GOLD = "#f1c40f"
WHITE = "#ffffff"
GREY = "#c3d0d8"
SEA = "#122230"
LAND = "#1d3443"
HEADER_H, GOLDLINE_H, MAP_H, STATS_H, FOOTER_H = 190, 5, 830, 225, 100

F = lambda name, size: FontProperties(fname=os.path.join(ASSETS, "fonts", name + ".ttf"), size=size)
MONT_XB = lambda s: F("Montserrat-ExtraBold", s)
MONT_B = lambda s: F("Montserrat-Bold", s)
ROB_B = lambda s: F("Roboto-Bold", s)
ROB = lambda s: F("Roboto-Regular", s)

OUTLINE = [pe.withStroke(linewidth=3, foreground="#000000")]

# Windstoten in km/u: kleurenschaal van Meteociel (ICON-D2 "Rafales de vent max").
# Elke klasse krijgt haar kleur in het midden; daartussen wordt vloeiend overgevloeid.
# De klassen zijn ongelijk breed (5 → 10 → 20 km/u), dus waarden worden eerst naar
# klasse-index omgezet, zodat elke klasse even breed is op de schaal, net als bij Meteociel.
GUST_BOUNDS = np.array(list(range(0, 90, 5)) + list(range(90, 160, 10)) + [160, 180, 200, 220, 240, 260], float)
GUST_COLORS = ["#ffffff", "#97e6ff", "#33ccff", "#0099ff", "#00ff99", "#33cc66", "#66cc33", "#66ff00",
               "#a4f22f", "#b7cf0e", "#d6f017", "#cc9900", "#ee9900", "#ff9966", "#cc9999", "#cc6633",
               "#cc3333", "#ff0d0d", "#c60000", "#800000", "#800050", "#a00077", "#cc00cc", "#ff00ff",
               "#ff40ff", "#ff80ff", "#ffa0ff", "#ffffff", "#e3e3e3", "#c6c6c6"]
N_CLASSES = len(GUST_COLORS)
assert len(GUST_BOUNDS) == N_CLASSES + 1
_pos = (np.arange(N_CLASSES) + 0.5) / N_CLASSES
GUST_CMAP = LinearSegmentedColormap.from_list(
    "meteociel_gusts", [(0.0, GUST_COLORS[0])] + list(zip(_pos, GUST_COLORS)) + [(1.0, GUST_COLORS[-1])], N=1024)


def gust_index(v):
    """km/u -> positie 0..1 op de klasse-schaal."""
    return np.interp(v, GUST_BOUNDS, np.arange(N_CLASSES + 1)) / N_CLASSES


CITIES = [  # (naam, lon, lat, label-dx, label-dy, ha)
    ("Brussel", 4.35, 50.85, 0.08, 0.05, "left"),
    ("Antwerpen", 4.40, 51.22, 0.08, 0.05, "left"),
    ("Gent", 3.72, 51.05, 0.06, -0.17, "left"),
    ("Brugge", 3.22, 51.21, 0.0, -0.21, "center"),
    ("Oostende", 2.92, 51.23, -0.06, 0.07, "right"),
    ("Luik", 5.57, 50.63, 0.08, 0.05, "left"),
    ("Namen", 4.87, 50.47, 0.08, -0.13, "left"),
    ("Hasselt", 5.34, 50.93, 0.08, 0.05, "left"),
    ("Aarlen", 5.82, 49.68, 0.08, 0.05, "left"),
    ("Rijsel", 3.06, 50.63, -0.08, -0.13, "right"),
    ("Duinkerke", 2.38, 51.03, 0.0, -0.21, "center"),
    ("Calais", 1.86, 50.95, -0.08, -0.13, "right"),
    ("Dover", 1.31, 51.13, -0.08, 0.05, "right"),
    ("Londen", -0.13, 51.51, 0.08, 0.05, "left"),
    ("Brighton", -0.14, 50.82, -0.08, 0.05, "right"),
    ("Le Havre", 0.11, 49.49, 0.08, -0.13, "left"),
    ("Parijs", 2.35, 48.86, 0.08, 0.05, "left"),
    ("Amiens", 2.30, 49.89, 0.08, 0.05, "left"),
    ("Rotterdam", 4.48, 51.92, 0.08, 0.05, "left"),
    ("Amsterdam", 4.90, 52.37, 0.08, 0.05, "left"),
    ("Eindhoven", 5.47, 51.44, 0.08, 0.05, "left"),
    ("Keulen", 6.96, 50.94, 0.08, 0.05, "left"),
    ("Luxemburg", 6.13, 49.61, 0.08, -0.13, "left"),
]
REF_PLACES = [c for c in CITIES if c[0] in
              ("Brussel", "Antwerpen", "Gent", "Brugge", "Oostende", "Duinkerke", "Calais", "Dover",
               "Londen", "Brighton", "Le Havre", "Rotterdam", "Eindhoven", "Amsterdam", "Keulen", "Rijsel")]
BELGIAN = {"Brussel", "Antwerpen", "Gent", "Brugge", "Oostende", "Zeebrugge", "Knokke-Heist", "De Panne",
           "Nieuwpoort", "Hasselt", "Luik", "Genk", "Turnhout", "Kortrijk", "Ieper"}
REF_PLACES += [("Zeebrugge", 3.20, 51.33), ("Knokke-Heist", 3.29, 51.35), ("De Panne", 2.59, 51.10),
               ("Nieuwpoort", 2.75, 51.13), ("Genk", 5.50, 50.97), ("Turnhout", 4.94, 51.32),
               ("Kortrijk", 3.26, 50.83), ("Ieper", 2.89, 50.85), ("Middelburg", 3.61, 51.50), ("Vlissingen", 3.57, 51.44),
               ("Breda", 4.78, 51.59), ("Nijmegen", 5.86, 51.84), ("Arnhem", 5.90, 51.98),
               ("Apeldoorn", 5.97, 52.21), ("Enschede", 6.89, 52.22), ("Zwolle", 6.09, 52.51),
               ("Portsmouth", -1.09, 50.80), ("Eastbourne", 0.28, 50.77), ("Folkestone", 1.18, 51.08),
               ("Boulogne-sur-Mer", 1.61, 50.73), ("Dieppe", 1.08, 49.92), ("Den Haag", 4.30, 52.08),
               ("Lingen", 7.32, 52.52), ("Oldenburg", 8.21, 53.14)]

DAYS = ["ma", "di", "wo", "do", "vr", "za", "zo"]
DAYS_LONG = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
COMPASS = ["N", "NNO", "NO", "ONO", "O", "OZO", "ZO", "ZZO", "Z", "ZZW", "ZW", "WZW", "W", "WNW", "NW", "NNW"]


def parse_t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H%M").replace(tzinfo=timezone.utc)


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def bearing(lat1, lon1, lat2, lon2):
    p1, p2, dl = np.radians(lat1), np.radians(lat2), np.radians(lon2 - lon1)
    x = np.sin(dl) * np.cos(p2)
    y = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360


def compass(deg):
    return COMPASS[int((deg + 11.25) // 22.5) % 16]


def describe_position(la, lo):
    dist = lambda c: haversine(la, lo, c[2], c[1])
    places = [(n, x, y) for n, x, y, *_ in REF_PLACES]
    name, plo, pla = min(places, key=dist)
    # Belgische referentie verkiezen zolang de kern in de buurt is
    be = min((c for c in places if c[0] in BELGIAN), key=dist)
    if dist(be) < 35:
        name, plo, pla = be
    d = haversine(pla, plo, la, lo)
    if d < 12:
        return f"boven {name}"
    return f"{d:.0f} km {compass(bearing(pla, plo, la, lo))} van {name}"


# ----------------------------------------------------------------------------- data
def load():
    files = sorted(glob.glob(os.path.join(DATA, "*.npz")))
    times = [os.path.basename(f)[:-4] for f in files]
    i0, i1 = times.index(START), times.index(END)
    sel = list(zip(times, files))[i0:i1 + 1]
    d0 = np.load(sel[0][1])
    lat, lon = d0["lat"], d0["lon"]
    ys = np.where((lat >= LAT0 - 0.3) & (lat <= LAT1 + 0.3))[0]
    xs = np.where((lon >= LON0 - 0.3) & (lon <= LON1 + 0.3))[0]
    crop = np.ix_(ys, xs)
    P, G = [], []
    for _, f in sel:
        d = np.load(f)
        P.append(d["p"][crop])
        G.append(d["g"][crop] * 3.6)  # m/s -> km/u
    P, G = np.array(P), np.array(G)
    mask = np.isnan(P).any(axis=0) | np.isnan(G).any(axis=0)
    pfill = np.where(np.isnan(P), np.nanmean(P), P)
    P = np.array([gaussian_filter(p, 3) for p in pfill])  # gladde isobaren
    G = np.where(np.isnan(G), 0.0, G)

    rows = list(csv.DictReader(open(TRACK)))
    tr = {r["tijd_utc"]: (float(r["lat"]), float(r["lon"]), float(r["kerndruk_hpa"])) for r in rows}
    hrs = [t for t, _ in sel]
    tlat = np.array([tr[t][0] for t in hrs])
    tlon = np.array([tr[t][1] for t in hrs])
    tp = np.array([tr[t][2] for t in hrs])
    return dict(times=[parse_t(t) for t in hrs], lat=lat[ys], lon=lon[xs], P=P, G=G, mask=mask,
                tlat=tlat, tlon=tlon, tp=tp)


def belgium_mask(lat, lon):
    rec = next(r for r in shpreader.Reader(shpreader.natural_earth("10m", "cultural", "admin_0_countries")).records()
               if r.attributes["ADMIN"] == "Belgium")
    LO, LA = np.meshgrid(lon, lat)
    pts = np.column_stack([LO.ravel(), LA.ravel()])
    m = np.zeros(len(pts), bool)
    geoms = getattr(rec.geometry, "geoms", [rec.geometry])
    for g in geoms:
        m |= Path(np.asarray(g.exterior.coords)).contains_points(pts)
    return m.reshape(LO.shape)


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


# ----------------------------------------------------------------------- interpolatie
class Interp:
    def __init__(self, D):
        self.D = D
        n = len(D["times"])
        self.n = n
        self.hours = np.arange(n, dtype=float)
        self.slat = CubicSpline(self.hours, D["tlat"])
        self.slon = CubicSpline(self.hours, D["tlon"])
        self.sp = CubicSpline(self.hours, D["tp"])
        lat, lon = D["lat"], D["lon"]
        self.LA, self.LO = np.meshgrid(lat, lon, indexing="ij")
        self.dy = lat[1] - lat[0]
        self.dx = lon[1] - lon[0]
        self.II, self.JJ = np.meshgrid(np.arange(len(lat)), np.arange(len(lon)), indexing="ij")

    def pos(self, h):
        return float(self.slat(h)), float(self.slon(h)), float(self.sp(h))

    def fields(self, h):
        D = self.D
        k = min(int(np.floor(h)), self.n - 2)
        t = h - k
        if t < 1e-6:
            return D["P"][k], D["G"][k]
        if t > 1 - 1e-6:
            return D["P"][k + 1], D["G"][k + 1]
        dlat = D["tlat"][k + 1] - D["tlat"][k]
        dlon = D["tlon"][k + 1] - D["tlon"][k]
        # Verplaatsing volgt de kern, afnemend met afstand tot de kern (sigma ~ 3°)
        cl = 0.5 * (D["tlat"][k] + D["tlat"][k + 1])
        co = 0.5 * (D["tlon"][k] + D["tlon"][k + 1])
        r2 = (self.LA - cl) ** 2 + ((self.LO - co) * np.cos(np.radians(cl))) ** 2
        w = np.exp(-r2 / (2 * 3.0 ** 2))
        di, dj = w * dlat / self.dy, w * dlon / self.dx
        c0 = [self.II - t * di, self.JJ - t * dj]
        c1 = [self.II + (1 - t) * di, self.JJ + (1 - t) * dj]
        out = []
        for F in (D["P"], D["G"]):
            a = map_coordinates(F[k], c0, order=1, mode="nearest")
            b = map_coordinates(F[k + 1], c1, order=1, mode="nearest")
            out.append((1 - t) * a + t * b)
        return out


# ---------------------------------------------------------------------------- tekenen
STATIC = {}


def init_worker():
    D = load()
    STATIC["D"] = D
    STATIC["I"] = Interp(D)
    STATIC["lines"] = map_lines()
    STATIC["be"] = belgium_mask(D["lat"], D["lon"])
    STATIC["logo"] = np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA"))
    STATIC["footer"] = np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA"))


def fit_text(fig, ax, x, y, txt, font, size, max_px, **kw):
    """Tekst die krimpt tot ze binnen max_px pixels breed past."""
    t = ax.text(x, y, txt, fontproperties=font(size), **kw)
    width = t.get_window_extent(fig.canvas.get_renderer()).width
    if width > max_px:
        t.set_fontproperties(font(size * max_px / width))
    return t


def fy(px_from_top, h):
    """Figuurfractie voor een strook die px_from_top onder de bovenrand begint."""
    return 1 - (px_from_top + h) / H, h / H


def draw(h, path):
    D, I, L = STATIC["D"], STATIC["I"], STATIC["lines"]
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)

    # ---------------- header
    y, hh = fy(0, HEADER_H)
    ax = fig.add_axes([0, y, 1, hh]); ax.set_axis_off()
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color=NAVY, transform=ax.transAxes))
    ax.text(0.028, 0.70, "STORM AUSTEN", fontproperties=MONT_XB(64), color=GOLD, va="center",
            transform=ax.transAxes)
    ax.text(0.030, 0.39, "Baan van de lagedrukkern  |  Max. windstoten", fontproperties=ROB_B(27),
            color=WHITE, va="center", transform=ax.transAxes)
    t_utc = D["times"][0] + timedelta(hours=h)
    t_be = t_utc.astimezone(BE_TZ)
    ax.text(0.030, 0.15, f"{DAYS_LONG[t_be.weekday()].capitalize()} {t_be.day} oktober 2026  |  "
            f"ICON-D2 (DWD), run {RUN_LABEL}", fontproperties=ROB_B(20), color=GREY, va="center",
            transform=ax.transAxes)
    lax = fig.add_axes([1 - 180 / W, 1 - 160 / H, 165 / W, 125 / H]); lax.set_axis_off()
    lax.imshow(STATIC["logo"])
    y, hh = fy(HEADER_H, GOLDLINE_H)
    gax = fig.add_axes([0, y, 1, hh]); gax.set_axis_off()
    gax.add_patch(plt.Rectangle((0, 0), 1, 1, color=GOLD, transform=gax.transAxes))

    # ---------------- kaart
    y, hh = fy(HEADER_H + GOLDLINE_H, MAP_H)
    m = fig.add_axes([0, y, 1, hh], facecolor=SEA)
    m.set_xlim(LON0, LON1); m.set_ylim(LAT0, LAT1); m.set_axis_off()
    for poly in L["land"]:
        m.fill(poly[:, 0], poly[:, 1], color=LAND, zorder=1, lw=0)

    P, G = I.fields(h)
    lat, lon = D["lat"], D["lon"]
    ext = [lon[0] - 0.01, lon[-1] + 0.01, lat[0] - 0.01, lat[-1] + 0.01]
    Gm = np.ma.masked_array(gust_index(G), D["mask"])
    m.imshow(Gm, origin="lower", extent=ext, cmap=GUST_CMAP, vmin=0, vmax=1,
             interpolation="bilinear", zorder=2, aspect="auto")
    # Buiten het ICON-D2 domein
    out = np.ma.masked_array(np.ones_like(G), ~D["mask"])
    m.imshow(out, origin="lower", extent=ext, cmap=LinearSegmentedColormap.from_list("o", ["#0b1720", "#0b1720"]),
             alpha=0.82, interpolation="nearest", zorder=3, aspect="auto")
    m.text(-2.55, 48.78, "buiten\nICON-D2-\ndomein", fontproperties=ROB_B(14), color="#6f8796", zorder=4,
           va="bottom", ha="left", linespacing=1.1)

    for seg in L["coast"]:
        m.plot(seg[:, 0], seg[:, 1], color="#9fb4c1", lw=0.8, zorder=4)
    for seg in L["borders"]:
        m.plot(seg[:, 0], seg[:, 1], color="#c9d6de", lw=1.1, zorder=4, alpha=0.85)

    # Isobaren (elke 4 hPa)
    Pm = np.ma.masked_array(P, D["mask"])
    lv = np.arange(960, 1040, 4)
    m.contour(lon, lat, Pm, levels=lv, colors=WHITE, linewidths=0.9, alpha=0.55, zorder=5)

    for name, x, yy, dx, dy, ha in CITIES:
        m.plot(x, yy, "o", ms=5, color=WHITE, mec="#000000", mew=0.8, zorder=6)
        m.text(x + dx, yy + dy, name, fontproperties=ROB_B(16), color=WHITE, ha=ha, va="bottom",
               path_effects=OUTLINE, zorder=6)

    # Baan: afgelegd (goud) en verwacht (gestippeld)
    hh_all = np.linspace(0, I.n - 1, 600)
    past = hh_all[hh_all <= h]
    fut = hh_all[hh_all >= h]
    glow = [pe.withStroke(linewidth=7, foreground="#000000", alpha=0.6)]
    if len(fut) > 1:
        m.plot(I.slon(fut), I.slat(fut), color=WHITE, lw=2.2, ls=(0, (4, 4)), alpha=0.75, zorder=7)
    if len(past) > 1:
        m.plot(np.r_[I.slon(past), I.pos(h)[1]], np.r_[I.slat(past), I.pos(h)[0]], color=GOLD, lw=3.6,
               zorder=8, path_effects=glow, solid_capstyle="round")
    la, lo, pc = I.pos(h)
    for k in range(I.n):
        if k > h + 1e-6:
            continue
        m.plot(D["tlon"][k], D["tlat"][k], "o", ms=7, color=GOLD, mec="#000000", mew=1.2, zorder=9)
        # uurlabels verbergen zodra de L erover schuift
        if k % 3 == 0 and haversine(la, lo, D["tlat"][k], D["tlon"][k]) > 45:
            tl = (D["times"][k]).astimezone(BE_TZ)
            m.text(D["tlon"][k] + 0.05, D["tlat"][k] - 0.2, f"{tl:%H}u", fontproperties=ROB_B(14),
                   color=GOLD, path_effects=OUTLINE, zorder=9, ha="left")

    # Hoogste windstoot in België
    be = STATIC["be"] & ~D["mask"]
    Gb = np.where(be, G, -1)
    bi, bj = np.unravel_index(np.argmax(Gb), Gb.shape)
    gmax_be = G[bi, bj]

    # De L
    m.text(lo, la, "L", fontproperties=MONT_XB(64), color="#e5262b", ha="center", va="center", zorder=12,
           path_effects=[pe.withStroke(linewidth=13, foreground="#000000", alpha=0.55),
                         pe.withStroke(linewidth=8, foreground=WHITE),
                         pe.SimplePatchShadow(offset=(2, -2), alpha=0.6), pe.Normal()])
    m.text(lo, la - 0.36, f"{pc:.0f} hPa", fontproperties=ROB_B(19), color=WHITE, ha="center", va="top",
           zorder=12, path_effects=[pe.withStroke(linewidth=4, foreground="#000000")])

    # Tijdlabel (zoals 'VALID' in de waarschuwingskaarten)
    m.text(0.012, 0.985, f" GELDIG: {DAYS[t_be.weekday()].upper()} {t_be.day} OKT {t_be:%H:%M} ",
           transform=m.transAxes, fontproperties=ROB_B(21), color=WHITE, va="top", ha="left",
           bbox=dict(boxstyle="square,pad=0.25", fc="#000000", ec="none"), zorder=20)
    m.text(0.014, 0.925, f" Belgische tijd  |  {t_utc:%H:%M} UTC ", transform=m.transAxes,
           fontproperties=ROB(15), color=GREY, va="top", ha="left",
           bbox=dict(boxstyle="square,pad=0.2", fc="#000000", ec="none", alpha=0.75), zorder=20)
    m.text(0.988, 0.012, "Bron: DWD ICON-D2 via Open-Meteo  |  Natural Earth", transform=m.transAxes,
           fontproperties=ROB(13), color=GREY, ha="right", va="bottom", zorder=20,
           path_effects=OUTLINE)

    # ---------------- statistiekenpaneel
    y, hh = fy(HEADER_H + GOLDLINE_H + MAP_H, STATS_H)
    s = fig.add_axes([0, y, 1, hh]); s.set_axis_off(); s.set_xlim(0, W); s.set_ylim(0, STATS_H)
    s.add_patch(plt.Rectangle((0, 0), W, STATS_H, color=NAVY))
    s.add_patch(plt.Rectangle((0, STATS_H - 3), W, 3, color=GOLD))
    # kleurenschaal
    s.text(W / 2, STATS_H - 26, "MAXIMALE WINDSTOTEN (km/u)", fontproperties=MONT_B(19), color=GOLD,
           ha="center", va="center")
    cb_x0, cb_x1, cb_y, cb_h = 40, W - 40, STATS_H - 64, 16
    grad = np.linspace(0, 1, 1024)[None, :]
    s.imshow(grad, extent=[cb_x0, cb_x1, cb_y, cb_y + cb_h], cmap=GUST_CMAP, vmin=0, vmax=1,
             aspect="auto", zorder=2)
    for v in GUST_BOUNDS[:-1]:
        xv = cb_x0 + float(gust_index(v)) * (cb_x1 - cb_x0)
        s.plot([xv, xv], [cb_y - 4, cb_y], color=WHITE, lw=1.0)
        s.text(xv, cb_y - 7, f"{v:.0f}", fontproperties=ROB_B(12), color=WHITE, ha="center", va="top")

    # drie kolommen
    k = min(int(np.floor(h)), I.n - 2)
    dp3 = I.pos(min(h + 1.5, I.n - 1))[2] - I.pos(max(h - 1.5, 0))[2]
    trend = "verdiept" if dp3 < -0.3 else ("vult op" if dp3 > 0.3 else "stabiel")
    dla = float(I.slat(h, 1)); dlo = float(I.slon(h, 1))
    speed = haversine(la, lo, la + dla, lo + dlo)
    heading = compass(bearing(la, lo, la + dla, lo + dlo))
    cols = [
        ("Kerndruk", f"{pc:.0f} hPa", GOLD, trend.upper(), GREY),
        ("Max. windstoot België", f"{gmax_be:.0f} km/u", WHITE, "AFGELOPEN UUR", GREY),
        ("Positie kern", describe_position(la, lo), WHITE, f"{speed:.0f} KM/U RICHTING {heading}", GREY),
    ]
    cw = W / 3
    for i, (title, val, vc, sub, sc) in enumerate(cols):
        cx = cw * (i + 0.5)
        if i:
            s.plot([cw * i, cw * i], [14, 112], color="#3d6476", lw=1.2)
        s.text(cx, 100, title, fontproperties=ROB_B(19), color=WHITE, ha="center", va="center")
        if i < 2:
            s.text(cx, 62, val, fontproperties=MONT_XB(38), color=vc, ha="center", va="center")
        else:
            fit_text(fig, s, cx, 62, val, MONT_B, 26, cw - 30, color=vc, ha="center", va="center")
        s.text(cx, 24, sub, fontproperties=ROB_B(15), color=sc, ha="center", va="center")

    # ---------------- footer
    y, hh = fy(H - FOOTER_H, FOOTER_H)
    fax = fig.add_axes([0, y, 1, hh]); fax.set_axis_off()
    fax.imshow(STATIC["footer"], aspect="auto")

    fig.savefig(path, dpi=100, facecolor=NAVY)
    plt.close(fig)


def render_one(args):
    idx, h = args
    path = os.path.join(FRAMES, f"f{idx:04d}.png")
    if not os.path.exists(path):  # hervatten na onderbreking
        draw(h, path)
    return idx


def main():
    preview_only = "--preview-only" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    init_worker()
    n = STATIC["I"].n
    # Preview: kern aan de Belgische kust (15 UTC)
    draw(float(os.environ.get("PREVIEW_H", 8.0)), os.path.join(OUT, "storm_austen_icon_d2_preview.png"))
    if preview_only:
        return
    hs = [0.0] * int(HOLD_START * FPS) + list(np.linspace(0, n - 1, (n - 1) * SUBSTEPS + 1)) \
        + [float(n - 1)] * int(HOLD_END * FPS)
    os.makedirs(FRAMES, exist_ok=True)
    # Stilstaande beelden maar één keer renderen
    uniq = sorted(set(hs))
    with Pool(os.cpu_count(), initializer=init_worker) as pool:
        for i, _ in enumerate(pool.imap_unordered(render_one, list(enumerate(uniq))), 1):
            if i % 25 == 0:
                print(f"{i}/{len(uniq)} beelden", flush=True)
    order = [uniq.index(x) for x in hs]
    lst = os.path.join(FRAMES, "list.txt")
    with open(lst, "w") as fh:
        for o in order:
            fh.write(f"file 'f{o:04d}.png'\nduration {1 / FPS:.6f}\n")
    mp4 = os.path.join(OUT, "storm_austen_icon_d2.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-preset", "slow", "-movflags", "+faststart", mp4], check=True)
    gif = os.path.join(OUT, "storm_austen_icon_d2.gif")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf",
                    "fps=12,scale=540:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];"
                    "[b][p]paletteuse=dither=sierra2_4a", gif], check=True)
    shutil.rmtree(FRAMES)
    print("Klaar:", mp4, gif)


if __name__ == "__main__":
    main()
