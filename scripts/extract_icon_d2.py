"""Knip MSLP en max. windstoten uit één Open-Meteo ICON-D2 .om-bestand (focusgebied België/Kanaal).

Gebruik: python extract_icon_d2.py <bron.om> <doel.npz>
"""
import sys

import numpy as np
import omfiles

# Regulier lat/lon-rooster van ICON-D2 zoals Open-Meteo het publiceert (0.02°)
LAT = 43.18 + 0.02 * np.arange(746)
LON = -3.94 + 0.02 * np.arange(1215)
YS = slice(np.searchsorted(LAT, 47.0), np.searchsorted(LAT, 55.0))
XS = slice(0, np.searchsorted(LON, 10.0))


def main(src, dst):
    r = omfiles.OmFileReader.from_path(src)
    names = {r.get_child_by_index(i).name for i in range(r.num_children)}
    p = r.get_child_by_name("pressure_msl")[:][YS, XS]
    # Analyse-tijdstip (+0 u) heeft nog geen uurmaximum van de windstoten
    if "wind_gusts_10m" in names:
        g = r.get_child_by_name("wind_gusts_10m")[:][YS, XS]
    else:
        g = np.full(p.shape, np.nan, np.float32)
    np.savez_compressed(dst, p=p, g=g, lat=LAT[YS], lon=LON[XS])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
