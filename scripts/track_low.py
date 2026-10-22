"""Volg de lagedrukkern van storm Austin uur per uur in de ICON-D2 MSLP-velden.

Vertrekt vanaf een referentietijdstip en zoekt vooruit en achteruit het minimum
van het (licht afgevlakte) drukveld binnen een zoekvenster rond de verwachte
positie. Het spoor stopt zodra de kern de rand van het ICON-D2 domein raakt.

Gebruik: python track_low.py <map met .npz> <uitvoer.csv>
"""
import csv
import glob
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

REF_TIME = "2026-10-23T1100"
REF_POS = (50.9, 1.2)  # boven het Kanaal, nabij Calais
SEARCH = 1.0  # halve vensterhoogte in graden (breedte x1.6)
EDGE_PX = 12  # kern binnen 12 roosterpunten (~25 km) van de domeinrand = onbetrouwbaar


def smooth(p):
    m = np.isnan(p)
    ps = gaussian_filter(np.where(m, np.nanmean(p), p), 4)
    ps[m] = np.nan
    return ps


def refine(sub, i, j):
    """Parabolische sub-roosterpuntverfijning van het minimum."""
    def vertex(a, b, c):
        den = a - 2 * b + c
        return 0.0 if den == 0 else 0.5 * (a - c) / den
    return i + vertex(*sub[i - 1:i + 2, j]), j + vertex(*sub[i, j - 1:j + 2])


def find_min(ps, lat, lon, la, lo):
    rows = np.where(np.abs(lat - la) < SEARCH)[0]
    cols = np.where(np.abs(lon - lo) < SEARCH * 1.6)[0]
    sub = ps[np.ix_(rows, cols)]
    if np.isnan(sub).all():
        return None
    i, j = np.unravel_index(np.nanargmin(sub), sub.shape)
    on_window_edge = i in (0, sub.shape[0] - 1) or j in (0, sub.shape[1] - 1)
    gi, gj = rows[i], cols[j]
    near_nan = np.isnan(ps[max(gi - EDGE_PX, 0):gi + EDGE_PX + 1, max(gj - EDGE_PX, 0):gj + EDGE_PX + 1]).any()
    near_domain_edge = gj + EDGE_PX >= ps.shape[1] or gi + EDGE_PX >= ps.shape[0]
    if on_window_edge or near_nan or near_domain_edge:
        return None
    fi, fj = refine(sub, i, j)
    return (np.interp(rows[0] + fi, np.arange(len(lat)), lat),
            np.interp(cols[0] + fj, np.arange(len(lon)), lon),
            float(sub[i, j]))


def main(src, dst):
    files = sorted(glob.glob(os.path.join(src, "*.npz")))
    times = [os.path.basename(f)[:-4] for f in files]
    d0 = np.load(files[0])
    lat, lon = d0["lat"], d0["lon"]
    raw = {t: np.load(f)["p"] for t, f in zip(times, files)}

    k0 = times.index(REF_TIME)
    track = {}
    for step in (-1, 1):
        la, lo = REF_POS
        prev = None
        k = k0
        while 0 <= k < len(times):
            hit = find_min(smooth(raw[times[k]]), lat, lon, la, lo)
            if hit is None:
                break
            hla, hlo, _ = hit
            # Kerndruk = echte (niet afgevlakte) minimumwaarde rond de kern
            win = raw[times[k]][np.ix_(np.abs(lat - hla) < 0.3, np.abs(lon - hlo) < 0.5)]
            track[times[k]] = (hla, hlo, float(np.nanmin(win)))
            dla, dlo = (hla - prev[0], hlo - prev[1]) if prev else (0.0, 0.0)
            prev = (hla, hlo)
            la, lo = hla + dla, hlo + dlo
            k += step

    with open(dst, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tijd_utc", "lat", "lon", "kerndruk_hpa"])
        for t in sorted(track):
            la, lo, p = track[t]
            w.writerow([t, f"{la:.3f}", f"{lo:.3f}", f"{p:.1f}"])
            print(t, f"{la:.3f}", f"{lo:.3f}", f"{p:.1f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
