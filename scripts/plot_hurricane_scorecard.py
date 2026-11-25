"""Scorecard: 2026 hurricane season, Atlantic vs Eastern Pacific. Downburst Daan house style.

Reads data/hurricane_2026.csv (per-storm, verified against the NHC/Wikipedia season
tables) and renders a 1080x1350 card in English.

Usage: python plot_hurricane_scorecard.py
"""
import csv
import os
from collections import Counter

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
OUT = os.path.join(ROOT, "output", "hurricane_2026_scorecard.png")

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

MAJOR = {"C3", "C4", "C5"}
HURR = {"C1", "C2", "C3", "C4", "C5"}


def load():
    rows = list(csv.DictReader(open(DATA)))
    out = {}
    for b in ("atlantic", "epac"):
        s = [r for r in rows if r["basin"] == b]
        out[b] = dict(named=len(s),
                      hurr=sum(r["peak_category"] in HURR for r in s),
                      major=sum(r["peak_category"] in MAJOR for r in s),
                      storms=s)
    return out


def fy(top, h):
    return 1 - (top + h) / H, h / H


def px_axes(fig, top, h):
    """As met pixelcoordinaten: (0,0) linksonder, (W,h) rechtsboven."""
    a = fig.add_axes([0, 1 - (top + h) / H, 1, h / H])
    a.set_axis_off(); a.set_xlim(0, W); a.set_ylim(0, h)
    return a


def main():
    d = load()
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=NAVY)

    # ---------------- header
    ax = px_axes(fig, 0, HEADER_H)
    ax.text(30, 128, "2026 HURRICANE SEASON", fontproperties=MONT_XB(40), color=GOLD, va="center")
    ax.text(32, 82, "A tale of two oceans", fontproperties=ROB_B(27), color=WHITE, va="center")
    ax.text(32, 38, "Season ends November 30  \u00b7  storm data via NHC",
            fontproperties=ROB_B(17), color=GREY, va="center")
    lax = fig.add_axes([1 - 180 / W, 1 - 160 / H, 165 / W, 125 / H]); lax.set_axis_off()
    lax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "logo_downburst_daan.png")).convert("RGBA")))
    g = px_axes(fig, HEADER_H, GOLDLINE_H)
    g.add_patch(plt.Rectangle((0, 0), W, GOLDLINE_H, color=GOLD))

    # ---------------- hero
    hero_top, hero_h = 209, 196
    hero = px_axes(fig, hero_top, hero_h)
    hero.add_patch(plt.Rectangle((48, 0), W - 96, hero_h, color=PANEL))
    hero.text(W / 2, hero_h - 42, "The Atlantic's first hurricane arrived on OCTOBER 8",
              fontproperties=ROB_B(23), color=WHITE, ha="center", va="center")
    hero.text(W / 2, hero_h - 103, "LATEST ON RECORD SINCE 1905",
              fontproperties=MONT_XB(38), color=GOLD, ha="center", va="center")
    hero.text(W / 2, 36, "Only 1907 and 1914 went an entire season without one",
              fontproperties=ROB(17), color=GREY, ha="center", va="center")

    # ---------------- head-to-head
    hd_top = hero_top + hero_h + 22
    hd = px_axes(fig, hd_top, 50)
    hd.text(W * 0.27, 20, "ATLANTIC", fontproperties=MONT_B(26), color=ATL, ha="center", va="center")
    hd.text(W * 0.73, 20, "EAST PACIFIC", fontproperties=MONT_B(26), color=EPAC, ha="center", va="center")

    rows = [("NAMED STORMS", "named"), ("HURRICANES", "hurr"), ("MAJOR HURRICANES", "major")]
    row_top, row_h = hd_top + 50, 116
    for i, (label, key) in enumerate(rows):
        r = px_axes(fig, row_top + i * row_h, row_h - 10)
        rh = row_h - 10
        r.add_patch(plt.Rectangle((48, 0), W - 96, rh, color=PANEL))
        r.text(W / 2, rh - 24, label, fontproperties=ROB_B(16), color=GREY, ha="center", va="center")
        r.plot([W / 2, W / 2], [14, rh - 44], color=RULE, lw=1.5)
        r.text(W * 0.27, 36, str(d["atlantic"][key]), fontproperties=MONT_XB(50), color=ATL,
               ha="center", va="center")
        r.text(W * 0.73, 36, str(d["epac"][key]), fontproperties=MONT_XB(50), color=EPAC,
               ha="center", va="center")

    # ---------------- Pacific records
    rec_top = row_top + len(rows) * row_h + 16
    rec_h = 290
    rec = px_axes(fig, rec_top, rec_h)
    rec.text(W / 2, rec_h - 18, "PACIFIC RECORDS (FULL BASIN)", fontproperties=MONT_B(19),
             color=GOLD, ha="center", va="center")
    items = [("Highest accumulated cyclone energy ever measured", "beats 2018"),
             ("11 major hurricanes", "ties 2015 for the most"),
             ("3 Category 5 hurricanes", "ties the all-time record"),
             ("Polo bottomed out at 892 mb", "2nd-most intense Pacific hurricane on record")]
    for i, (a, b) in enumerate(items):
        yy = rec_h - 72 - i * 62
        rec.plot([92], [yy + 4], marker="o", ms=8, color=EPAC)
        rec.text(118, yy + 11, a, fontproperties=ROB_B(18), color=WHITE, va="center")
        rec.text(118, yy - 13, b, fontproperties=ROB(14), color=GREY, va="center")

    # ---------------- note
    nt = px_axes(fig, rec_top + rec_h + 10, 80)
    nt.text(W / 2, 54, "El Ni\u00f1o loaded the Atlantic with wind shear and took it away from the Pacific.",
            fontproperties=ROB_B(16), color=GOLD, ha="center", va="center")
    nt.text(W / 2, 20, "East Pacific counts exclude the 5 storms named in the Central Pacific basin.",
            fontproperties=ROB(13), color=GREY, ha="center", va="center")

    fax = fig.add_axes([0, 0, 1, FOOTER_H / H]); fax.set_axis_off()
    fax.imshow(np.asarray(Image.open(os.path.join(ASSETS, "footer_socials.png")).convert("RGBA")),
               aspect="auto")

    fig.savefig(OUT, dpi=100, facecolor=NAVY)
    print(OUT)
    print("atlantic", d["atlantic"]["named"], d["atlantic"]["hurr"], d["atlantic"]["major"])
    print("epac    ", d["epac"]["named"], d["epac"]["hurr"], d["epac"]["major"])


if __name__ == "__main__":
    main()
