"""Animation: the 2026 hurricane season as it unfolded, Atlantic vs East Pacific.

A "now" line sweeps from 1 June to 30 November. Each storm appears as a bar spanning
its active period, coloured by the peak intensity it reached (Saffir-Simpson). Running
counters show how many storms in each basin reached hurricane strength.

Reads data/hurricane_2026.csv. Downburst Daan house style, English.

Usage: python render_hurricane_race.py [--preview-only]
"""
import csv
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from multiprocessing import get_context

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
DATA = os.path.join(ROOT, "data", "hurricane_2026.csv")
OUT = os.path.join(ROOT, "output")
FRAMES = os.environ.get("FRAMES_DIR", os.path.join(OUT, "_hur_frames"))

W, H = 1080, 1350
NAVY, GOLD, WHITE, GREY = "#173f51", "#f1c40f", "#ffffff", "#c3d0d8"
PANEL, RULE = "#1d4a5e", "#2c5468"
ATL, EPAC = "#2f97d0", "#e0604f"
HEADER_H, GOLDLINE_H, FOOTER_H = 190, 5, 100

F = lambda n, s: FontProperties(fname=os.path.join(ASSETS, "fonts", n + ".ttf"), size=s)
MONT_XB = lambda s: F("Montserrat-ExtraBold", s)
MONT_B = lambda s: F("Montserrat-Bold", s)
ROB_B = lambda s: F("Roboto-Bold", s)
ROB = lambda s: F("Roboto-Regular", s)
OUTLINE = [pe.withStroke(linewidth=3, foreground="#000000")]

# Saffir-Simpson track colours (the NHC/Wikipedia convention)
CAT_COLOR = {"TS": "#00faf4", "SS": "#00faf4", "C1": "#ffffcc", "C2": "#ffe775",
             "C3": "#ffc140", "C4": "#ff8f20", "C5": "#ff6060"}
HURR = {"C1", "C2", "C3", "C4", "C5"}

START, END = date(2026, 6, 1), date(2026, 11, 30)
SPAN = (END - START).days
FPS = 30
SWEEP_S = 11.0          # seconds for the sweep itself
HOLD_START, HOLD_END = 0.7, 3.0

# Atlantic's first hurricane: Isaias reached hurricane strength on 8 October
ISAIAS_HURR = date(2026, 10, 8)


def load():
    rows = list(csv.DictReader(open(DATA)))
    out = {}
    for b in ("atlantic", "epac"):
        s = [r for r in rows if r["basin"] == b]
        for r in s:
            r["d0"] = date.fromisoformat(r["start"])
            r["d1"] = date.fromisoformat(r["end"])
        out[b] = sorted(s, key=lambda r: r["d0"])
    return out


def px_axes(fig, top, h):
    a = fig.add_axes([0, 1 - (top + h) / H, 1, h / H])
    a.set_axis_off(); a.set_xlim(0, W); a.set_ylim(0, h)
    return a


# Geometry of the two storm panels
PLOT_X0, PLOT_X1 = 128, W - 34
ATL_TOP, ATL_ROW = 314, 25
EPAC_TOP, EPAC_ROW = 620, 23
TITLE_H, MONTH_H = 26, 20
MONTHS = [(date(2026, m, 1), n) for m, n in
          [(6, "JUN"), (7, "JUL"), (8, "AUG"), (9, "SEP"), (10, "OCT"), (11, "NOV")]]


def dx(d):
    """Date -> x pixel."""
    return PLOT_X0 + (d - START).days / SPAN * (PLOT_X1 - PLOT_X0)


def panel_h(rows, row_h):
    return TITLE_H + MONTH_H + len(rows) * row_h + 8


def draw_panel(fig, top, rows, row_h, title, color, now):
    """One basin: title line, month grid, storm bars drawn up to `now`."""
    h = panel_h(rows, row_h)
    a = px_axes(fig, top, h)
    a.text(30, h - TITLE_H / 2, title, fontproperties=MONT_B(22), color=color, va="center")
    y_top = h - TITLE_H - MONTH_H

    # month grid
    for d0, nm in MONTHS:
        x = dx(d0)
        a.plot([x, x], [4, y_top + MONTH_H - 4], color=RULE, lw=1, zorder=1)
        a.text(x + 5, y_top + MONTH_H / 2, nm, fontproperties=ROB_B(12), color=GREY,
               va="center", zorder=1)

    done = 0
    for i, r in enumerate(rows):
        y = y_top - 8 - i * row_h
        if r["d0"] > now:
            continue
        x0 = dx(r["d0"])
        x1 = dx(min(r["d1"], now))
        x1 = max(x1, x0 + 7)                       # korte stormen blijven zichtbaar
        col = CAT_COLOR[r["peak_category"]]
        is_h = r["peak_category"] in HURR
        a.add_patch(plt.Rectangle((x0, y - row_h * 0.30), x1 - x0, row_h * 0.58,
                                  color=col, zorder=3,
                                  linewidth=1.4 if is_h else 0,
                                  edgecolor="#ffffff" if is_h else "none"))
        a.text(x0 - 8, y, r["name"], fontproperties=ROB_B(12 if is_h else 11),
               color=WHITE if is_h else GREY, ha="right", va="center", zorder=4)
        if is_h:
            done += 1
    return done


def draw(t, path, D):
    """t in 0..1 over the season."""
    now = START + timedelta(days=round(t * SPAN))
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)

    # ---------------- header
    ax = px_axes(fig, 0, HEADER_H)
    ax.text(30, 130, "2026 HURRICANE SEASON", fontproperties=MONT_XB(40), color=GOLD, va="center")
    ax.text(32, 86, "Atlantic vs East Pacific, as it happened", fontproperties=ROB_B(24),
            color=WHITE, va="center")
    ax.text(32, 44, now.strftime("%d %B 2026").lstrip("0"), fontproperties=ROB_B(21),
            color=GREY, va="center")
    lax = fig.add_axes([1 - 180 / W, 1 - 160 / H, 165 / W, 125 / H]); lax.set_axis_off()
    lax.imshow(D["logo"])
    g = px_axes(fig, HEADER_H, GOLDLINE_H)
    g.add_patch(plt.Rectangle((0, 0), W, GOLDLINE_H, color=GOLD))

    # ---------------- counters
    c = px_axes(fig, 200, 104)
    c.add_patch(plt.Rectangle((48, 0), W - 96, 104, color=PANEL))
    c.text(W / 2, 84, "STORMS THAT REACHED HURRICANE STRENGTH", fontproperties=ROB_B(15),
           color=GREY, ha="center", va="center")
    c.plot([W / 2, W / 2], [12, 58], color=RULE, lw=1.5)

    n_atl = sum(1 for r in D["atlantic"] if r["peak_category"] in HURR and r["d0"] <= now)
    n_ep = sum(1 for r in D["epac"] if r["peak_category"] in HURR and r["d0"] <= now)
    for xf, lab, val, col in ((0.27, "ATLANTIC", n_atl, ATL), (0.73, "EAST PACIFIC", n_ep, EPAC)):
        c.text(W * xf - 56, 34, lab, fontproperties=MONT_B(19), color=col, ha="right", va="center")
        c.text(W * xf + 26, 34, str(val), fontproperties=MONT_XB(48), color=col,
               ha="center", va="center")

    # ---------------- panels
    draw_panel(fig, ATL_TOP, D["atlantic"], ATL_ROW, "ATLANTIC", ATL, now)
    draw_panel(fig, EPAC_TOP, D["epac"], EPAC_ROW, "EAST PACIFIC", EPAC, now)

    # ---------------- sweeping "now" line across both panels
    sweep_top = ATL_TOP + TITLE_H
    sweep_bot = EPAC_TOP + panel_h(D["epac"], EPAC_ROW) - 4
    sw = px_axes(fig, sweep_top, sweep_bot - sweep_top)
    x = dx(now)
    sw.plot([x, x], [0, sweep_bot - sweep_top], color=GOLD, lw=2.2, alpha=0.9, zorder=6)

    # Milestone: the Atlantic's first hurricane
    if now >= ISAIAS_HURR:
        xi = dx(ISAIAS_HURR)
        sw.plot([xi, xi], [0, sweep_bot - sweep_top], color=WHITE, lw=1.4,
                ls=(0, (4, 4)), alpha=0.75, zorder=5)

    # ---------------- caption under the panels
    cap = px_axes(fig, sweep_bot + 10, 40)
    if now >= ISAIAS_HURR:
        cap.text(W / 2, 20, "8 October: the Atlantic finally gets a hurricane — latest since 1905",
                 fontproperties=ROB_B(19), color=GOLD, ha="center", va="center")
    elif now >= date(2026, 9, 21):
        cap.text(W / 2, 20, "Four months in. The Atlantic still has no hurricane.",
                 fontproperties=ROB_B(19), color=GOLD, ha="center", va="center")

    lg = px_axes(fig, sweep_bot + 54, 36)
    labs = [("Tropical storm", "TS"), ("Cat 1-2", "C2"), ("Cat 3-4", "C4"), ("Cat 5", "C5")]
    widths = [30 + 34 + 7.4 * len(l) for l, _ in labs]
    lx = (W - sum(widths)) / 2
    for (lab, key), wd in zip(labs, widths):
        lg.add_patch(plt.Rectangle((lx, 12), 26, 11, color=CAT_COLOR[key]))
        lg.text(lx + 33, 18, lab, fontproperties=ROB_B(13), color=WHITE, va="center")
        lx += wd

    fax = fig.add_axes([0, 0, 1, FOOTER_H / H]); fax.set_axis_off()
    fax.imshow(D["footer"], aspect="auto")

    fig.savefig(path, dpi=100, facecolor=NAVY)
    plt.close(fig)


STATIC = {}


def init():
    D = load()
    D["logo"] = np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA"))
    D["footer"] = np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA"))
    STATIC["D"] = D


def one(args):
    i, t = args
    p = os.path.join(FRAMES, "f%04d.png" % i)
    if not os.path.exists(p):
        draw(t, p, STATIC["D"])
    return i


def main():
    os.makedirs(OUT, exist_ok=True)
    init()
    if "--preview-only" in sys.argv:
        draw(float(os.environ.get("PREVIEW_T", 1.0)),
             os.path.join(OUT, "hurricane_2026_race_preview.png"), STATIC["D"])
        print(os.path.join(OUT, "hurricane_2026_race_preview.png"))
        return
    n = int(SWEEP_S * FPS)
    ts = [0.0] * int(HOLD_START * FPS) + list(np.linspace(0, 1, n)) + [1.0] * int(HOLD_END * FPS)
    os.makedirs(FRAMES, exist_ok=True)
    uniq = sorted(set(ts))
    with get_context("fork").Pool(os.cpu_count(), initializer=init) as pool:
        for k, _ in enumerate(pool.imap_unordered(one, list(enumerate(uniq))), 1):
            if k % 40 == 0:
                print("%d/%d frames" % (k, len(uniq)), flush=True)
    order = [uniq.index(x) for x in ts]
    lst = os.path.join(FRAMES, "list.txt")
    with open(lst, "w") as fh:
        for o in order:
            fh.write("file 'f%04d.png'\nduration %.6f\n" % (o, 1 / FPS))
    mp4 = os.path.join(OUT, "hurricane_2026_race.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-preset", "slow", "-movflags", "+faststart", mp4], check=True)
    shutil.rmtree(FRAMES, ignore_errors=True)
    print("done:", mp4)


if __name__ == "__main__":
    main()
