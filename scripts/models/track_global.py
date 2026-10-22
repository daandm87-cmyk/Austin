# Track storm Austen's low backwards/forwards in coarse-model MSLP fields.
import sys, glob, os, numpy as np
from scipy.ndimage import gaussian_filter, minimum_filter
d = sys.argv[1]; ref_t = sys.argv[2] if len(sys.argv) > 2 else "2026-10-23T0600"
ref = (50.4, -1.7)
fs = sorted(glob.glob(d + "/*.npz")); times = [os.path.basename(f)[:-4] for f in fs]
def hav(a, b, c, e):
    a, b, c, e = map(np.radians, (a, b, c, e))
    return 6371 * 2 * np.arcsin(np.sqrt(np.sin((c-a)/2)**2 + np.cos(a)*np.cos(c)*np.sin((e-b)/2)**2))
def minima(f):
    z = np.load(f); p, lat, lon = z["p"], z["lat"], z["lon"]
    res = abs(lat[1]-lat[0]); ps = gaussian_filter(p, 0.25/res)  # ~0.25° smoothing
    w = max(3, int(round(1.0/res)))
    mk = (ps == minimum_filter(ps, size=w))
    ii, jj = np.where(mk)
    return [(lat[i], lon[j], float(p[max(i-2,0):i+3, max(j-2,0):j+3].min())) for i, j in zip(ii, jj)]
k0 = times.index(ref_t) if ref_t in times else min(range(len(times)), key=lambda k: abs(int(times[k][8:10]+times[k][11:13]) - int(ref_t[8:10]+ref_t[11:13])))
track = {}
for step in (-1, 1):
    pos = ref; k = k0; maxd = 450
    while 0 <= k < len(times):
        c = [m for m in minima(fs[k]) if hav(pos[0], pos[1], m[0], m[1]) < maxd]
        if not c: break
        best = min(c, key=lambda m: (m[2] + 0.02 * hav(pos[0], pos[1], m[0], m[1])))
        track[times[k]] = best; pos = best[:2]; k += step
for t in sorted(track):
    la, lo, p = track[t]; print(t, f"{la:6.2f} {lo:7.2f} {p:7.1f}")
