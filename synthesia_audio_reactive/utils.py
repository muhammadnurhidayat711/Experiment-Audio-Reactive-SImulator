"""Small math and color helpers used by visual modules."""

from __future__ import annotations

import math
import random
from typing import Iterable

import numpy as np
import pygame


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge0 == edge1:
        return 0.0
    x = clamp((x - edge0) / (edge1 - edge0))
    return x * x * (3.0 - 2.0 * x)


def hsv_color(h: float, s: float = 0.85, v: float = 1.0) -> pygame.Color:
    color = pygame.Color(0)
    color.hsva = ((h % 360.0), clamp(s) * 100.0, clamp(v) * 100.0, 100.0)
    return color


def avoid_blue_hue(hue: float) -> float:
    """Keep the palette away from cyan/blue halo ranges."""
    hue = hue % 360.0
    if 175.0 <= hue <= 255.0:
        return 35.0 + (hue - 175.0) / 80.0 * 95.0
    return hue


def palette(freq_centroid: float, bass: float, mid: float, treble: float) -> tuple[pygame.Color, pygame.Color, pygame.Color]:
    hue = avoid_blue_hue(32.0 + freq_centroid * 118.0 + treble * 38.0)
    secondary_hue = avoid_blue_hue(hue + 44.0 + bass * 32.0)
    accent_hue = avoid_blue_hue(hue + 128.0)
    primary = hsv_color(hue, 0.58, 0.84 + treble * 0.08)
    secondary = hsv_color(secondary_hue, 0.52, 0.78 + mid * 0.13)
    accent = hsv_color(accent_hue, 0.64, 0.88)
    return primary, secondary, accent


def draw_glow_circle(
    surface: pygame.Surface,
    position: tuple[int, int],
    radius: int,
    color: pygame.Color | tuple[int, int, int],
    layers: int = 6,
    alpha: int = 120,
) -> None:
    if radius <= 0:
        return
    glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = (radius * 2, radius * 2)
    rgb = color[:3] if hasattr(color, "__getitem__") else color
    for i in range(layers, 0, -1):
        r = int(radius * (0.6 + i / layers * 1.6))
        a = int(alpha * (i / layers) ** 2 / layers)
        pygame.draw.circle(glow, (*rgb, a), center, r)
    pygame.draw.circle(glow, (*rgb, min(255, alpha + 70)), center, radius)
    surface.blit(glow, (position[0] - center[0], position[1] - center[1]), special_flags=pygame.BLEND_ADD)


def random_points(count: int, width: int, height: int) -> np.ndarray:
    points = np.empty((count, 2), dtype=np.float32)
    points[:, 0] = np.random.uniform(0, width, count)
    points[:, 1] = np.random.uniform(0, height, count)
    return points


def star_field(count: int, width: int, height: int) -> list[tuple[int, int, int]]:
    return [(random.randrange(width), random.randrange(height), random.randrange(30, 160)) for _ in range(count)]


def rotate_points(points: np.ndarray, center: np.ndarray, angle: float) -> np.ndarray:
    s = math.sin(angle)
    c = math.cos(angle)
    translated = points - center
    rotated = np.empty_like(points)
    rotated[:, 0] = translated[:, 0] * c - translated[:, 1] * s
    rotated[:, 1] = translated[:, 0] * s + translated[:, 1] * c
    return rotated + center
