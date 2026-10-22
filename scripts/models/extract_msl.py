# Extract MSLP over the N-Atlantic / W-Europe box from any Open-Meteo spatial .om file
import sys, re, numpy as np, omfiles
src, dst = sys.argv[1], sys.argv[2]
r = omfiles.OmFileReader.from_path(src)
wkt = r.get_child_by_name("crs_wkt").read_scalar()
la0, lo0, la1, lo1 = map(float, re.search(r"BBOX\[([^\]]*)\]", wkt).group(1).split(","))
p = r.get_child_by_name("pressure_msl")[:]
ny, nx = p.shape
lat = np.linspace(la0, la1, ny); lon = np.linspace(lo0, lo1, nx)
ys = (lat >= 35) & (lat <= 65); xs = (lon >= -45) & (lon <= 20)
np.savez_compressed(dst, p=p[np.ix_(ys, xs)].astype(np.float32), lat=lat[ys], lon=lon[xs])
