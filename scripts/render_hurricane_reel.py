"""Facebook Reel (1080x1920): the 2026 hurricane season, Atlantic vs East Pacific.

Three segments in one clip, so it can go out as a single video post:
  A. Track race   - both basins on a map, tracks drawing in through the season
  B. Season race  - every storm as a bar, coloured by the peak intensity it reached
  C. Scorecard    - the final numbers, held at the end

Counters are exact: a storm is counted the moment its best track first reaches
Saffir-Simpson category 1.

Data: data/hurricane_2026.csv (season table) and data/hurricane_2026_tracks.csv
(NHC best-track points). Downburst Daan house style, English.

Usage: python render_hurricane_reel.py [--preview A|B|C]
"""
import csv
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from multiprocessing import get_context

import cartopy.io.shapereader as shpreader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "output")
FRAMES = os.environ.get("FRAMES_DIR", os.path.join(OUT, "_reel_frames"))

# ---- canvas and Facebook Reels safe zones -----------------------------------
W, H = 1080, 1920
SAFE_TOP = 150          # above this Facebook can overlay its own chrome
SAFE_BOT = 1455         # below this sit the caption, page name and action buttons
NAVY, GOLD, WHITE, GREY = "#173f51", "#f1c40f", "#ffffff", "#c3d0d8"
PANEL, RULE = "#1d4a5e", "#2c5468"
SEA, LAND, COAST = "#0c1a26", "#27485c", "#4d7f9a"
ATL, EPAC = "#2f97d0", "#e0604f"

F = lambda n, s: FontProperties(fname=os.path.join(ASSETS, "fonts", n + ".ttf"), size=s)
MONT_XB = lambda s: F("Montserrat-ExtraBold", s)
MONT_B = lambda s: F("Montserrat-Bold", s)
ROB_B = lambda s: F("Roboto-Bold", s)
ROB = lambda s: F("Roboto-Regular", s)

CAT_COLOR = {0: "#00faf4", 1: "#ffffcc", 2: "#ffe775", 3: "#ffc140", 4: "#ff8f20", 5: "#ff6060"}
TD_COLOR = "#5ebaff"

T0 = datetime(2026, 6, 1)
T1 = datetime(2026, 11, 30)
SPAN = (T1 - T0).total_seconds()
FPS = 30

# Segment lengths in seconds. Pacing rule: every segment gets a lead-in so the
# layout can be read before anything moves, a sweep, narrative pauses on the two
# moments that carry the story, and a hold long enough to read the finished state.
A_LEAD, A_SWEEP, A_HOLD = 1.2, 7.5, 3.8
B_LEAD, B_SWEEP, B_HOLD = 1.0, 10.0, 4.2
C_STAGES = [2.0, 2.5, 3.0, 3.5]          # hero / numbers / records / all
BEAT_SEP, BEAT_OCT = datetime(2026, 9, 21), datetime(2026, 10, 8, 12)
A_BEATS = {BEAT_OCT: 1.2}
B_BEATS = {BEAT_SEP: 1.2, BEAT_OCT: 1.6}

MAPS = {  # basin -> (lon0, lon1, lat0, lat1)
    "atlantic": (-102, -18, 9.5, 43),
    "epac": (-172, -84, 4.5, 37),
}


def px_axes(fig, top, h):
    a = fig.add_axes([0, 1 - (top + h) / H, 1, h / H])
    a.set_axis_off(); a.set_xlim(0, W); a.set_ylim(0, h)
    return a


# ----------------------------------------------------------------- data
def load():
    season = list(csv.DictReader(open(os.path.join(ROOT, "data", "hurricane_2026.csv"))))
    for r in season:
        r["d0"] = datetime.fromisoformat(r["start"])
        r["d1"] = datetime.fromisoformat(r["end"]) + timedelta(hours=18)

    tracks = {}
    for p in csv.DictReader(open(os.path.join(ROOT, "data", "hurricane_2026_tracks.csv"))):
        key = (p["basin"], p["name"])
        t = datetime.strptime(str(p["dtg"]), "%Y%m%d%H")
        tracks.setdefault(key, []).append(
            (t, float(p["lon"]), float(p["lat"]), int(p["ss"]), p["type"]))
    for v in tracks.values():
        v.sort()

    # exact moment each storm first reached hurricane strength
    hur_at = {}
    for key, v in tracks.items():
        for t, lo, la, ss, ty in v:
            if ss >= 1:
                hur_at[key] = t
                break
    return dict(season=season, tracks=tracks, hur_at=hur_at)


def map_geom():
    out = {}
    land = list(shpreader.Reader(shpreader.natural_earth("50m", "physical", "land")).geometries())
    coast = list(shpreader.Reader(shpreader.natural_earth("50m", "physical", "coastline")).geometries())
    for key, (lo0, lo1, la0, la1) in MAPS.items():
        polys, lines = [], []
        for geom in land:
            b = geom.bounds
            if b[2] < lo0 - 5 or b[0] > lo1 + 5 or b[3] < la0 - 5 or b[1] > la1 + 5:
                continue
            for g in getattr(geom, "geoms", [geom]):
                polys.append(np.asarray(g.exterior.coords))
        for geom in coast:
            b = geom.bounds
            if b[2] < lo0 - 5 or b[0] > lo1 + 5 or b[3] < la0 - 5 or b[1] > la1 + 5:
                continue
            for g in getattr(geom, "geoms", [geom]):
                lines.append(np.asarray(g.coords))
        out[key] = (polys, lines)
    return out


# ----------------------------------------------------------------- chrome
def header(fig, subtitle, stamp):
    a = px_axes(fig, SAFE_TOP, 180)
    a.text(34, 128, "2026 HURRICANE SEASON", fontproperties=MONT_XB(42), color=GOLD, va="center")
    a.text(36, 82, subtitle, fontproperties=ROB_B(25), color=WHITE, va="center")
    if stamp:
        a.text(36, 40, stamp, fontproperties=ROB_B(21), color=GREY, va="center")
    lax = fig.add_axes([1 - 176 / W, 1 - (SAFE_TOP + 128) / H, 158 / W, 118 / H])
    lax.set_axis_off(); lax.imshow(STATIC["logo"])
    g = px_axes(fig, SAFE_TOP + 180, 5)
    g.add_patch(plt.Rectangle((0, 0), W, 5, color=GOLD))


def footer(fig):
    fh = 84
    a = fig.add_axes([0, 1 - (SAFE_BOT + fh) / H, 1, fh / H])
    a.set_axis_off()
    a.imshow(STATIC["footer"], aspect="auto")


def counters(fig, top, n_atl, n_ep, label="STORMS THAT REACHED HURRICANE STRENGTH"):
    c = px_axes(fig, top, 112)
    c.add_patch(plt.Rectangle((40, 0), W - 80, 112, color=PANEL))
    c.text(W / 2, 90, label, fontproperties=ROB_B(16), color=GREY, ha="center", va="center")
    c.plot([W / 2, W / 2], [14, 64], color=RULE, lw=1.5)
    for xf, lab, val, col in ((0.27, "ATLANTIC", n_atl, ATL), (0.73, "EAST PACIFIC", n_ep, EPAC)):
        c.text(W * xf - 58, 38, lab, fontproperties=MONT_B(20), color=col, ha="right", va="center")
        c.text(W * xf + 28, 38, str(val), fontproperties=MONT_XB(50), color=col,
               ha="center", va="center")


def count_hurr(D, now):
    a = sum(1 for (b, n), t in D["hur_at"].items() if b == "atlantic" and t <= now)
    e = sum(1 for (b, n), t in D["hur_at"].items() if b == "epac" and t <= now)
    return a, e


# ----------------------------------------------------------------- segment A
def draw_tracks(fig, top, h, basin, D, now, title, color):
    lo0, lo1, la0, la1 = MAPS[basin]
    t = px_axes(fig, top, 30)
    t.text(34, 14, title, fontproperties=MONT_B(22), color=color, va="center")
    m = fig.add_axes([40 / W, 1 - (top + 30 + h) / H, 1000 / W, h / H], facecolor=SEA)
    m.set_xlim(lo0, lo1); m.set_ylim(la0, la1); m.set_axis_off()
    polys, lines = STATIC["geom"][basin]
    for poly in polys:
        m.fill(poly[:, 0], poly[:, 1], color=LAND, zorder=1, lw=0)
    for ln in lines:
        m.plot(ln[:, 0], ln[:, 1], color=COAST, lw=0.8, zorder=2)
    for (b, name), pts in D["tracks"].items():
        if b != basin:
            continue
        shown = [p for p in pts if p[0] <= now]
        if len(shown) < 2:
            continue
        for (ta, loa, laa, ssa, tya), (tb, lob, lab_, ssb, tyb) in zip(shown, shown[1:]):
            col = TD_COLOR if (ssb == 0 and tyb == "TD") else CAT_COLOR[ssb]
            m.plot([loa, lob], [laa, lab_], color=col, lw=3.2, zorder=3,
                   solid_capstyle="round")
        tl, lol, lal, ssl, tyl = shown[-1]
        if (now - tl).total_seconds() <= 6 * 3600:      # still running: head marker
            m.plot(lol, lal, "o", ms=7, mfc=CAT_COLOR[ssl] if ssl else "#ffffff",
                   mec="#ffffff", mew=1.4, zorder=5)
            m.text(lol, lal + (la1 - la0) * 0.03, name, fontproperties=ROB_B(13), color=WHITE,
                   ha="center", va="bottom", zorder=6)
    for sp in m.spines.values():
        sp.set_visible(True); sp.set_color(RULE); sp.set_linewidth(1.5)
    m.set_frame_on(True)


def seg_a(fig, frac, D):
    now = T0 + timedelta(seconds=frac * SPAN)
    header(fig, "Every storm track, as it happened", now.strftime("%d %B 2026").lstrip("0"))
    na, ne = count_hurr(D, now)
    counters(fig, 352, na, ne)
    draw_tracks(fig, 486, 418, "atlantic", D, now, "ATLANTIC", ATL)
    draw_tracks(fig, 952, 374, "epac", D, now, "EAST PACIFIC", EPAC)
    legend(fig, 1366)
    footer(fig)


def legend(fig, top):
    lg = px_axes(fig, top, 34)
    labs = [("Trop. storm", 0), ("Cat 1-2", 2), ("Cat 3-4", 4), ("Cat 5", 5)]
    widths = [28 + 30 + 7.2 * len(l) for l, _ in labs]
    lx = (W - sum(widths)) / 2
    for (lab, k), wd in zip(labs, widths):
        lg.add_patch(plt.Rectangle((lx, 10), 24, 10, color=CAT_COLOR[k]))
        lg.text(lx + 30, 15, lab, fontproperties=ROB_B(13), color=WHITE, va="center")
        lx += wd


# ----------------------------------------------------------------- segment B
PLOT_X0, PLOT_X1 = 128, W - 36
MONTHS = [(datetime(2026, m, 1), n) for m, n in
          [(6, "JUN"), (7, "JUL"), (8, "AUG"), (9, "SEP"), (10, "OCT"), (11, "NOV")]]
TITLE_H, MONTH_H = 26, 20


def dx(d):
    return PLOT_X0 + (d - T0).total_seconds() / SPAN * (PLOT_X1 - PLOT_X0)


def bars(fig, top, rows, row_h, title, color, now):
    h = TITLE_H + MONTH_H + len(rows) * row_h + 8
    a = px_axes(fig, top, h)
    a.text(30, h - TITLE_H / 2, title, fontproperties=MONT_B(22), color=color, va="center")
    y_top = h - TITLE_H - MONTH_H
    for d0, nm in MONTHS:
        x = dx(d0)
        a.plot([x, x], [4, y_top + MONTH_H - 4], color=RULE, lw=1, zorder=1)
        a.text(x + 5, y_top + MONTH_H / 2, nm, fontproperties=ROB_B(12), color=GREY,
               va="center", zorder=1)
    for i, r in enumerate(rows):
        if r["d0"] > now:
            continue
        y = y_top - 8 - i * row_h
        x0, x1 = dx(r["d0"]), max(dx(min(r["d1"], now)), dx(r["d0"]) + 7)
        cat = r["peak_category"]
        col = CAT_COLOR[0] if cat in ("TS", "SS") else CAT_COLOR[int(cat[1])]
        is_h = cat.startswith("C")
        a.add_patch(plt.Rectangle((x0, y - row_h * 0.30), x1 - x0, row_h * 0.58, color=col,
                                  zorder=3, linewidth=1.3 if is_h else 0,
                                  edgecolor="#ffffff" if is_h else "none"))
        a.text(x0 - 8, y, r["name"], fontproperties=ROB_B(12 if is_h else 11),
               color=WHITE if is_h else GREY, ha="right", va="center", zorder=4)
    return h


def seg_b(fig, frac, D):
    now = T0 + timedelta(seconds=frac * SPAN)
    header(fig, "Atlantic vs East Pacific, week by week",
           now.strftime("%d %B 2026").lstrip("0"))
    na, ne = count_hurr(D, now)
    counters(fig, 352, na, ne)
    atl = [r for r in D["season"] if r["basin"] == "atlantic"]
    ep = [r for r in D["season"] if r["basin"] == "epac"]
    t_atl, t_ep = 486, 486 + (TITLE_H + MONTH_H + 10 * 25 + 8) + 18
    bars(fig, t_atl, atl, 25, "ATLANTIC", ATL, now)
    hb = bars(fig, t_ep, ep, 23, "EAST PACIFIC", EPAC, now)

    sw = px_axes(fig, t_atl + TITLE_H, t_ep + hb - 6 - (t_atl + TITLE_H))
    x = dx(now)
    sw.plot([x, x], [0, sw.get_ylim()[1]], color=GOLD, lw=2.2, alpha=0.9, zorder=6)
    iso = D["hur_at"].get(("atlantic", "Isaias"))
    if iso and now >= iso:
        xi = dx(iso)
        sw.plot([xi, xi], [0, sw.get_ylim()[1]], color=WHITE, lw=1.4, ls=(0, (4, 4)),
                alpha=0.75, zorder=5)

    cap = px_axes(fig, t_ep + hb + 6, 40)
    if iso and now >= iso:
        cap.text(W / 2, 20, "8 October: the Atlantic finally gets a hurricane — latest since 1905",
                 fontproperties=ROB_B(19), color=GOLD, ha="center", va="center")
    elif now >= datetime(2026, 9, 21):
        cap.text(W / 2, 20, "Four months in. The Atlantic still has no hurricane.",
                 fontproperties=ROB_B(19), color=GOLD, ha="center", va="center")
    legend(fig, t_ep + hb + 52)
    footer(fig)


# ----------------------------------------------------------------- segment C
def seg_c(fig, frac, D):
    """frac encodes the reveal stage: 0 hero, 1 +numbers, 2 +records, 3 +note."""
    stage = int(round(frac * (len(C_STAGES) - 1)))
    header(fig, "A tale of two oceans", "Season ends November 30")
    atl = [r for r in D["season"] if r["basin"] == "atlantic"]
    ep = [r for r in D["season"] if r["basin"] == "epac"]
    HU = lambda rs: sum(1 for r in rs if r["peak_category"].startswith("C"))
    MJ = lambda rs: sum(1 for r in rs if r["peak_category"] in ("C3", "C4", "C5"))

    hero = px_axes(fig, 368, 196)
    hero.add_patch(plt.Rectangle((40, 0), W - 80, 196, color=PANEL))
    hero.text(W / 2, 150, "The Atlantic's first hurricane arrived on OCTOBER 8",
              fontproperties=ROB_B(22), color=WHITE, ha="center", va="center")
    hero.text(W / 2, 92, "LATEST ON RECORD SINCE 1905", fontproperties=MONT_XB(37),
              color=GOLD, ha="center", va="center")
    hero.text(W / 2, 36, "Only 1907 and 1914 went a whole season without one",
              fontproperties=ROB(17), color=GREY, ha="center", va="center")

    if stage < 1:
        footer(fig)
        return
    hd = px_axes(fig, 590, 50)
    hd.text(W * 0.27, 20, "ATLANTIC", fontproperties=MONT_B(25), color=ATL, ha="center", va="center")
    hd.text(W * 0.73, 20, "EAST PACIFIC", fontproperties=MONT_B(25), color=EPAC, ha="center", va="center")
    rows = [("NAMED STORMS", len(atl), len(ep)), ("HURRICANES", HU(atl), HU(ep)),
            ("MAJOR HURRICANES", MJ(atl), MJ(ep))]
    for i, (lab, a, e) in enumerate(rows):
        r = px_axes(fig, 640 + i * 116, 106)
        r.add_patch(plt.Rectangle((40, 0), W - 80, 106, color=PANEL))
        r.text(W / 2, 82, lab, fontproperties=ROB_B(16), color=GREY, ha="center", va="center")
        r.plot([W / 2, W / 2], [14, 62], color=RULE, lw=1.5)
        r.text(W * 0.27, 36, str(a), fontproperties=MONT_XB(48), color=ATL, ha="center", va="center")
        r.text(W * 0.73, 36, str(e), fontproperties=MONT_XB(48), color=EPAC, ha="center", va="center")

    if stage < 2:
        footer(fig)
        return
    rec = px_axes(fig, 1000, 300)
    rec.text(W / 2, 282, "PACIFIC RECORDS (FULL BASIN)", fontproperties=MONT_B(19),
             color=GOLD, ha="center", va="center")
    items = [("Highest cyclone energy ever measured", "beats 2018"),
             ("11 major hurricanes", "ties 2015 for the most"),
             ("3 Category 5 hurricanes", "ties the all-time record"),
             ("Polo bottomed out at 892 mb", "2nd-most intense Pacific hurricane on record")]
    for i, (a, b) in enumerate(items):
        yy = 224 - i * 60
        rec.plot([96], [yy + 4], marker="o", ms=8, color=EPAC)
        rec.text(122, yy + 11, a, fontproperties=ROB_B(18), color=WHITE, va="center")
        rec.text(122, yy - 13, b, fontproperties=ROB(14), color=GREY, va="center")

    if stage < 3:
        footer(fig)
        return
    nt = px_axes(fig, 1310, 60)
    nt.text(W / 2, 40, "El Niño: shear floods the Atlantic, and drains out of the Pacific.",
            fontproperties=ROB_B(16), color=GOLD, ha="center", va="center")
    nt.text(W / 2, 12, "East Pacific counts exclude the 5 Central Pacific storms.",
            fontproperties=ROB(13), color=GREY, ha="center", va="center")
    footer(fig)


# ----------------------------------------------------------------- driver
STATIC = {}
SEGMENTS = {"A": seg_a, "B": seg_b, "C": seg_c}


def init():
    STATIC["D"] = load()
    STATIC["geom"] = map_geom()
    STATIC["logo"] = np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA"))
    STATIC["footer"] = np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA"))


def render(seg, frac, path):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)
    SEGMENTS[seg](fig, frac, STATIC["D"])
    fig.savefig(path, dpi=100, facecolor=NAVY)
    plt.close(fig)


def one(args):
    i, seg, frac = args
    p = os.path.join(FRAMES, "f%04d.png" % i)
    if not os.path.exists(p):
        render(seg, frac, p)
    return i


def _frac_of(d):
    return (d - T0).total_seconds() / SPAN


def _sweep(seg, lead, length, hold, beats):
    """Lead-in, sweep with a pause on each beat date, then a hold on the end state."""
    seq = [(seg, 0.0)] * int(lead * FPS)
    fr = list(np.linspace(0, 1, int(length * FPS)))
    marks = sorted((_frac_of(d), n) for d, n in beats.items())
    mi = 0
    for t in fr:
        seq.append((seg, t))
        if mi < len(marks) and t >= marks[mi][0]:
            seq += [(seg, t)] * int(marks[mi][1] * FPS)   # pause on the cached frame
            mi += 1
    seq += [(seg, 1.0)] * int(hold * FPS)
    return seq


def plan():
    """(segment, frac) per output frame, in order."""
    seq = _sweep("A", A_LEAD, A_SWEEP, A_HOLD, A_BEATS)
    seq += _sweep("B", B_LEAD, B_SWEEP, B_HOLD, B_BEATS)
    n = len(C_STAGES) - 1
    for i, secs in enumerate(C_STAGES):
        seq += [("C", i / n)] * int(secs * FPS)
    return seq


def main():
    os.makedirs(OUT, exist_ok=True)
    init()
    if "--preview" in sys.argv:
        seg = sys.argv[sys.argv.index("--preview") + 1]
        fr = float(os.environ.get("PREVIEW_T", 1.0))
        p = os.path.join(OUT, "reel_preview_%s.png" % seg)
        render(seg, fr, p)
        print(p)
        return
    seq = plan()
    uniq = sorted(set(seq), key=lambda x: ("ABC".index(x[0]), x[1]))
    idx = {k: i for i, k in enumerate(uniq)}
    os.makedirs(FRAMES, exist_ok=True)
    with get_context("fork").Pool(os.cpu_count(), initializer=init) as pool:
        for k, _ in enumerate(pool.imap_unordered(
                one, [(idx[u], u[0], u[1]) for u in uniq]), 1):
            if k % 50 == 0:
                print("%d/%d frames" % (k, len(uniq)), flush=True)
    lst = os.path.join(FRAMES, "list.txt")
    with open(lst, "w") as fh:
        for s in seq:
            fh.write("file 'f%04d.png'\nduration %.6f\n" % (idx[s], 1 / FPS))
    mp4 = os.path.join(OUT, "hurricane_2026_reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                    "-preset", "slow", "-movflags", "+faststart", mp4], check=True)
    shutil.rmtree(FRAMES, ignore_errors=True)
    print("done:", mp4, "frames:", len(seq), "duration: %.1fs" % (len(seq) / FPS))


if __name__ == "__main__":
    main()
