"""ETRS-TM35FIN (EPSG:3067) -> WGS84 (lat, lon). Inverse transverse Mercator, Krueger series (GRS80)."""
from math import asin, atan, cosh, cos, degrees, radians, sin, sinh

_A = 6378137.0
_F = 1 / 298.257222101
_K0 = 0.9996
_LON0 = radians(27.0)
_FE = 500000.0


def tm35fin_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    n = _F / (2 - _F)
    A = _A / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    b = [n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96 - n ** 4 / 360,
         n ** 2 / 48 + n ** 3 / 15 - 437 * n ** 4 / 1440,
         17 * n ** 3 / 480 - 37 * n ** 4 / 840,
         4397 * n ** 4 / 161280]
    d = [2 * n - 2 * n ** 2 / 3 - 2 * n ** 3 + 116 * n ** 4 / 45,
         7 * n ** 2 / 3 - 8 * n ** 3 / 5 - 227 * n ** 4 / 45,
         56 * n ** 3 / 15 - 136 * n ** 4 / 35,
         4279 * n ** 4 / 630]
    xi0 = northing / (_K0 * A)
    eta0 = (easting - _FE) / (_K0 * A)
    xi = xi0 - sum(b[j] * sin(2 * (j + 1) * xi0) * cosh(2 * (j + 1) * eta0) for j in range(4))
    eta = eta0 - sum(b[j] * cos(2 * (j + 1) * xi0) * sinh(2 * (j + 1) * eta0) for j in range(4))
    chi = asin(sin(xi) / cosh(eta))
    lat = chi + sum(d[j] * sin(2 * (j + 1) * chi) for j in range(4))
    lon = _LON0 + atan(sinh(eta) / cos(xi))
    return degrees(lat), degrees(lon)
