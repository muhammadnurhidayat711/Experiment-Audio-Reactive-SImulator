"""Small pure-Python Perlin noise fallback.

The external ``noise`` package currently requires a C build on some Python
versions, including Python 3.14 on Windows. This module provides the pnoise2
function used by the simulator and shadows that package when running locally.
"""

from __future__ import annotations

import math

_PERM_BASE = [
    151, 160, 137, 91, 90, 15, 131, 13, 201, 95, 96, 53, 194, 233, 7, 225,
    140, 36, 103, 30, 69, 142, 8, 99, 37, 240, 21, 10, 23, 190, 6, 148,
    247, 120, 234, 75, 0, 26, 197, 62, 94, 252, 219, 203, 117, 35, 11, 32,
    57, 177, 33, 88, 237, 149, 56, 87, 174, 20, 125, 136, 171, 168, 68, 175,
    74, 165, 71, 134, 139, 48, 27, 166, 77, 146, 158, 231, 83, 111, 229, 122,
    60, 211, 133, 230, 220, 105, 92, 41, 55, 46, 245, 40, 244, 102, 143, 54,
    65, 25, 63, 161, 1, 216, 80, 73, 209, 76, 132, 187, 208, 89, 18, 169,
    200, 196, 135, 130, 116, 188, 159, 86, 164, 100, 109, 198, 173, 186, 3,
    64, 52, 217, 226, 250, 124, 123, 5, 202, 38, 147, 118, 126, 255, 82, 85,
    212, 207, 206, 59, 227, 47, 16, 58, 17, 182, 189, 28, 42, 223, 183, 170,
    213, 119, 248, 152, 2, 44, 154, 163, 70, 221, 153, 101, 155, 167, 43,
    172, 9, 129, 22, 39, 253, 19, 98, 108, 110, 79, 113, 224, 232, 178, 185,
    112, 104, 218, 246, 97, 228, 251, 34, 242, 193, 238, 210, 144, 12, 191,
    179, 162, 241, 81, 51, 145, 235, 249, 14, 239, 107, 49, 192, 214, 31,
    181, 199, 106, 157, 184, 84, 204, 176, 115, 121, 50, 45, 127, 4, 150,
    254, 138, 236, 205, 93, 222, 114, 67, 29, 24, 72, 243, 141, 128, 195,
    78, 66, 215, 61, 156, 180,
]
_PERM = _PERM_BASE * 2


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _grad(hash_value: int, x: float, y: float) -> float:
    h = hash_value & 7
    u = x if h < 4 else y
    v = y if h < 4 else x
    return ((u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v))


def _perlin2(x: float, y: float) -> float:
    xi = math.floor(x) & 255
    yi = math.floor(y) & 255
    xf = x - math.floor(x)
    yf = y - math.floor(y)
    u = _fade(xf)
    v = _fade(yf)

    aa = _PERM[_PERM[xi] + yi]
    ab = _PERM[_PERM[xi] + yi + 1]
    ba = _PERM[_PERM[xi + 1] + yi]
    bb = _PERM[_PERM[xi + 1] + yi + 1]

    x1 = _lerp(_grad(aa, xf, yf), _grad(ba, xf - 1.0, yf), u)
    x2 = _lerp(_grad(ab, xf, yf - 1.0), _grad(bb, xf - 1.0, yf - 1.0), u)
    return max(-1.0, min(1.0, _lerp(x1, x2, v)))


def pnoise2(
    x: float,
    y: float,
    octaves: int = 1,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    repeatx: int = 1024,
    repeaty: int = 1024,
    base: int = 0,
) -> float:
    """Return 2D fractal Perlin noise in approximately the -1..1 range."""

    del repeatx, repeaty
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amplitude = 0.0
    offset = base * 37.0

    for _ in range(max(1, octaves)):
        total += _perlin2(x * frequency + offset, y * frequency + offset) * amplitude
        max_amplitude += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return total / max_amplitude if max_amplitude else 0.0
