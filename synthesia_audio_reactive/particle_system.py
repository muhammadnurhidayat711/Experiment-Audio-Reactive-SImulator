"""High-volume NumPy particle simulation with audio-reactive flow fields."""

from __future__ import annotations

import math
import random

import numpy as np
import pygame
from noise import pnoise2

from config import CONFIG
from utils import clamp, random_points, smoothstep


class ParticleSystem:
    def __init__(self, width: int, height: int, count: int) -> None:
        self.width = width
        self.height = height
        self.count = count
        self.center = np.array([width * 0.5, height * 0.5], dtype=np.float32)
        self.positions = random_points(count, width, height)
        self.previous_positions = self.positions.copy()
        self.velocities = np.random.normal(0, 1, (count, 2)).astype(np.float32)
        self.force_memory = np.zeros((count, 2), dtype=np.float32)
        self.life = np.random.uniform(0.35, 1.0, count).astype(np.float32)
        self.size = np.random.uniform(0.75, 1.75, count).astype(np.float32)
        self.draw_order = np.random.permutation(count)
        self.seed = random.random() * 1000.0

    def reset(self) -> None:
        self.positions = random_points(self.count, self.width, self.height)
        self.previous_positions = self.positions.copy()
        self.velocities = np.random.normal(0, 1, (self.count, 2)).astype(np.float32)
        self.force_memory.fill(0.0)
        self.life = np.random.uniform(0.35, 1.0, self.count).astype(np.float32)
        self.draw_order = np.random.permutation(self.count)

    def update(self, dt: float, audio, mode: int, t: float) -> None:
        px = self.positions[:, 0]
        py = self.positions[:, 1]
        dx = px - self.center[0]
        dy = py - self.center[1]
        dist = np.sqrt(dx * dx + dy * dy) + 1e-5
        nx = dx / dist
        ny = dy / dist
        tangent = np.stack((-ny, nx), axis=1)
        radial = np.stack((nx, ny), axis=1)

        flow = self._flow_vectors(t, audio)
        self.previous_positions[:] = self.positions
        env = audio.visual_envelope
        speed = CONFIG.particle_speed * (0.10 + env * 0.82 + audio.richness * 0.28 + audio.sound_diversity * 0.22)

        if mode == 0:
            acceleration = tangent * (0.34 + audio.mid * 0.9) + flow * 1.1 - radial * (0.08 + audio.bass * 0.22)
        elif mode == 1:
            acceleration = flow * (1.25 + audio.treble * 0.9) + radial * np.sin(dist[:, None] * 0.009 + t * 0.65) * 0.22
        elif mode == 2:
            acceleration = flow * 1.45 + tangent * (audio.mid * 0.42 + 0.12) + radial * math.sin(t * 0.45) * 0.14
        elif mode == 3:
            pulse = np.sin(dist[:, None] * 0.014 - t * 1.6)
            acceleration = radial * pulse * (0.45 + audio.bass * 0.9) + flow * 0.95
        else:
            fold = np.sin((px[:, None] * py[:, None]) * 0.000003 + t * 0.42)
            acceleration = (tangent * fold * 0.45 + flow * 1.0 + radial * np.cos(dist[:, None] * 0.01 + t * 0.55) * 0.18) * (0.65 + audio.mid * 0.35)

        bass_motion = radial * np.sin(dist[:, None] * 0.018 - t * 2.2) * (0.32 + audio.bass * 0.95)
        # Removed np.sign to make the burst wave completely smooth instead of jumping
        burst = np.sin(dist[:, None] * 0.031 + t * 6.0)
        percussive_motion = radial * burst * (0.22 + audio.spectral_flux * 1.1)
        bright_motion = np.stack((np.sin(py * 0.018 + t * 1.9), np.cos(px * 0.017 - t * 1.4)), axis=1).astype(np.float32) * (0.18 + audio.air * 0.78)
        vocal_motion = np.stack((np.sin(py * 0.006 + t * 0.55), np.sin(px * 0.006 - t * 0.45)), axis=1).astype(np.float32) * (0.2 + audio.presence * 0.62)
        ambient_motion = flow * (0.36 + audio.spectral_spread * 0.44)
        tonal_motion = tangent * (0.18 + audio.note_confidence * 0.5)
        acceleration += (
            bass_motion * audio.shape_bass
            + percussive_motion * audio.shape_percussive
            + bright_motion * audio.shape_bright
            + vocal_motion * audio.shape_vocal
            + ambient_motion * audio.shape_ambient
            + tonal_motion * audio.shape_tonal
        )
        distortion = getattr(audio, "distortion_amount", 0.0)
        noise = getattr(audio, "noise_amount", 0.0)
        if distortion > 0.01:
            fold_motion = np.stack(
                (
                    # Removed np.sign to keep particle folding motion perfectly smooth
                    np.sin(py * 0.035 + t * 4.8),
                    np.sin(px * 0.018 - t * 3.4),
                ),
                axis=1,
            ).astype(np.float32)
            acceleration += fold_motion * distortion * (0.18 + audio.visual_envelope * 0.42)
        if noise > 0.02:
            grain_motion = np.stack(
                (
                    np.sin(px * 0.071 + py * 0.013 + t * 13.0),
                    np.cos(py * 0.067 - px * 0.011 - t * 11.0),
                ),
                axis=1,
            ).astype(np.float32)
            acceleration += grain_motion * noise * 0.16
        acceleration *= 1.0 - audio.shape_ambient * 0.18

        morph_force = self._morph_vectors(dist, audio, t)
        acceleration = acceleration * (0.78 + audio.visual_envelope * 0.12) + morph_force * (0.22 + audio.class_confidence * 0.42)

        if audio.pitch_class >= 0:
            note_mode = audio.pitch_class % 4
            note_strength = 0.18 + audio.note_confidence * 0.55
            if note_mode == 0:
                note_force = radial * np.sin(dist[:, None] * 0.011 - t * 0.9)
            elif note_mode == 1:
                note_force = np.stack((np.sin(py * 0.009 + t * 0.65), np.cos(px * 0.004)), axis=1)
            elif note_mode == 2:
                note_force = np.stack((np.cos(py * 0.004), np.sin(px * 0.009 - t * 0.65)), axis=1)
            else:
                note_force = tangent * (0.45 + np.sin(dist[:, None] * 0.008 + t * 0.55) * 0.22)
            acceleration += note_force.astype(np.float32) * note_strength

        # Force incredibly smooth, fluid gliding movement for particles
        force_smoothing = min(0.995, 0.96 + audio.sound_diversity * 0.01)
        velocity_damping = min(0.995, 0.98 + audio.sound_diversity * 0.005)
        
        # Scale smoothing/damping coefficients exponentially by dt
        force_smoothing_coeff = max(0.001, min(0.999, force_smoothing ** (60.0 * dt)))
        velocity_damping_coeff = max(0.001, min(0.999, velocity_damping ** (60.0 * dt)))
        
        self.force_memory = self.force_memory * force_smoothing_coeff + acceleration.astype(np.float32) * (1.0 - force_smoothing_coeff)
        self.velocities = self.velocities * velocity_damping_coeff + self.force_memory * speed * dt
        velocity_length = np.linalg.norm(self.velocities, axis=1, keepdims=True) + 1e-6
        max_velocity = 1.0 + env * 4.7 + audio.sound_diversity * 1.2
        self.velocities *= np.minimum(1.0, max_velocity / velocity_length)
        self.positions += self.velocities * (60.0 * dt)
        self.life -= dt * (0.028 + audio.treble * 0.035)
        self._wrap_and_respawn(audio)

    def _morph_vectors(self, dist: np.ndarray, audio, t: float) -> np.ndarray:
        ids = np.arange(self.count, dtype=np.float32)
        u = ids / max(1, self.count - 1)
        turn = u * math.tau * (1.0 + audio.richness * 0.9)
        center = self.center
        morph = smoothstep(0.001, 0.38, audio.visual_envelope) * (0.35 + audio.class_confidence * 0.65)
        if morph <= 0.001:
            return np.zeros((self.count, 2), dtype=np.float32)

        radius = 95 + audio.bass * 360 + np.sin(turn * 4.0 + t * 2.1) * (18 + audio.bass * 30)
        bass_target = np.stack(
            (center[0] + np.cos(turn) * radius, center[1] + np.sin(turn) * radius * (0.58 + audio.spectral_spread * 0.18)),
            axis=1,
        )

        spokes_count = 12
        spoke_angle = np.floor(u * spokes_count) / spokes_count * math.tau
        jitter = np.sin(ids * 12.989 + t * 9.0) * 0.18
        radius = 70 + (u % (1.0 / spokes_count)) * spokes_count * (260 + audio.presence * 260)
        percussive_target = np.stack((center[0] + np.cos(spoke_angle + jitter) * radius, center[1] + np.sin(spoke_angle + jitter) * radius), axis=1)

        radius = 70 + u * (420 + audio.air * 380)
        angle = turn * 2.7 + np.sin(u * math.tau * 5.0 + t * 1.8) * 0.35
        bright_target = np.stack((center[0] + np.cos(angle) * radius, center[1] + np.sin(angle) * radius), axis=1)

        x_span = (u - 0.5) * (520 + audio.presence * 360)
        wave = np.sin(u * math.tau * (2.0 + audio.note_confidence) + t * 1.1) * (75 + audio.mid * 130)
        vocal_target = np.stack((center[0] + x_span, center[1] + wave), axis=1)

        turns = 1.3 + max(0, audio.pitch_class) * 0.08 + audio.note_confidence * 0.7
        radius = 40 + u * (280 + audio.body * 260)
        angle = turn * turns + t * 0.35
        tonal_target = np.stack((center[0] + np.cos(angle) * radius, center[1] + np.sin(angle) * radius * (0.72 + audio.mid * 0.2)), axis=1)

        radius = 80 + np.sqrt(u) * (360 + audio.spectral_spread * 300)
        angle = turn * 1.618 + np.sin(t * 0.25 + u * 9.0) * 0.45
        ambient_target = np.stack((center[0] + np.cos(angle) * radius, center[1] + np.sin(angle) * radius), axis=1)

        fallback_weight = max(0.0, 1.0 - (
            audio.shape_bass
            + audio.shape_percussive
            + audio.shape_bright
            + audio.shape_vocal
            + audio.shape_tonal
            + audio.shape_ambient
        ))
        target = (
            bass_target * audio.shape_bass
            + percussive_target * audio.shape_percussive
            + bright_target * audio.shape_bright
            + vocal_target * audio.shape_vocal
            + tonal_target * audio.shape_tonal
            + ambient_target * (audio.shape_ambient + fallback_weight)
        ).astype(np.float32)
        delta = target - self.positions
        length = np.linalg.norm(delta, axis=1, keepdims=True) + 1e-6
        force = delta / length * np.minimum(1.0, length / (130.0 + dist[:, None] * 0.08))
        return force.astype(np.float32) * morph

    def _flow_vectors(self, t: float, audio) -> np.ndarray:
        step = max(1, self.count // 2200)
        angles = np.empty(self.count, dtype=np.float32)
        scale = CONFIG.flow_scale * (0.75 + audio.centroid * 0.75)
        z = self.seed + t * CONFIG.flow_speed * (1.0 + audio.mid)
        sampled = range(0, self.count, step)
        for i in sampled:
            n = pnoise2(
                self.positions[i, 0] * scale + z,
                self.positions[i, 1] * scale - z,
                octaves=3,
                persistence=0.55,
                lacunarity=2.0,
            )
            angles[i : i + step] = n * math.tau * 2.0 + audio.bass * math.pi
        return np.stack((np.cos(angles), np.sin(angles)), axis=1).astype(np.float32)

    def _wrap_and_respawn(self, audio) -> None:
        margin = 80
        dead = (
            (self.positions[:, 0] < -margin)
            | (self.positions[:, 0] > self.width + margin)
            | (self.positions[:, 1] < -margin)
            | (self.positions[:, 1] > self.height + margin)
            | (self.life <= 0.0)
        )
        if not np.any(dead):
            return
        n = int(np.sum(dead))
        angle = np.random.uniform(0, math.tau, n)
        radius = np.random.uniform(18, 160 + audio.bass * 380, n)
        self.positions[dead, 0] = self.center[0] + np.cos(angle) * radius
        self.positions[dead, 1] = self.center[1] + np.sin(angle) * radius
        self.previous_positions[dead] = self.positions[dead]
        self.velocities[dead] = np.random.normal(0, 0.25, (n, 2))
        self.force_memory[dead] = 0.0
        self.life[dead] = np.random.uniform(0.55, 1.0, n)

    def draw(self, surface: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, mode: int, t: float = 0.0, presence: float | None = None, camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        presence = audio.visual_envelope if presence is None else presence
        visible_fraction = self._visible_fraction(audio, presence)
        indices = self.draw_order
        render_positions = self._distorted_positions(self.positions[indices], audio, t)
        render_previous = self._distorted_positions(self.previous_positions[indices], audio, t - 0.035)
        render_positions, depth = self._depth_projected_positions(render_positions, audio, t, camera_offset)
        render_previous, _ = self._depth_projected_positions(render_previous, audio, t - 0.035, camera_offset)
        points = render_positions.astype(np.int32)
        previous = render_previous.astype(np.int32)
        life = self.life[indices]
        env = max(audio.visual_envelope, presence)
        sizes = self.size[indices] * (0.42 + env * 0.78 + audio.richness * CONFIG.richness_particle_size + audio.sound_diversity * 0.28) * (0.72 + depth * 1.05)
        mix = np.clip((self.positions[indices, 0] / self.width + audio.centroid) * 0.5, 0, 1)

        for idx, (x, y) in enumerate(points):
            idx_fraction = idx / self.count
            p_fade = max(0.0, min(1.0, (visible_fraction - idx_fraction) * 10.0))
            if p_fade <= 0.01:
                continue
            if 0 <= x < self.width and 0 <= y < self.height:
                px, py = previous[idx]
                m = float(mix[idx])
                color = (
                    int(primary.r * (1 - m) + secondary.r * m),
                    int(primary.g * (1 - m) + secondary.g * m),
                    int(primary.b * (1 - m) + secondary.b * m),
                    int((8 + life[idx] * (76 + audio.richness * 68)) * max(0.05, presence) * (0.62 + float(depth[idx]) * 0.78) * p_fade),
                )
                line_color = (color[0], color[1], color[2], max(10, color[3] - 26))
                pygame.draw.aaline(layer, line_color, (int(px), int(py)), (int(x), int(y)))
                pygame.draw.circle(layer, color, (int(x), int(y)), max(1, int(sizes[idx])))

        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def _depth_projected_positions(self, positions: np.ndarray, audio, t: float, camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> tuple[np.ndarray, np.ndarray]:
        if positions.size == 0:
            return positions, np.zeros(0, dtype=np.float32)
        centered = positions - self.center
        radius = np.linalg.norm(centered, axis=1)
        angle = np.arctan2(centered[:, 1], centered[:, 0])
        wave_depth = (
            np.sin(angle * 2.0 + t * 0.55 + audio.centroid * 2.4)
            + np.sin(radius * 0.006 - t * 0.42 + audio.bass * 1.6) * 0.65
            + np.cos((positions[:, 0] - positions[:, 1]) * 0.004 + t * 0.32) * audio.sound_diversity
        )
        depth = np.clip((wave_depth + 1.95) / 3.90, 0.0, 1.0).astype(np.float32)
        strength = max(0.0, min(1.0, audio.visual_envelope * CONFIG.optical_depth_strength))
        scale = 1.0 + (depth[:, None] - 0.5) * (0.18 + strength * 0.30)
        parallax = np.stack(
            (
                np.sin(angle + t * 0.18) * (depth - 0.5),
                np.cos(angle * 0.7 - t * 0.16) * (depth - 0.5),
            ),
            axis=1,
        ).astype(np.float32)
        projected = self.center + centered * scale + parallax * (18.0 + strength * 46.0)
        
        # Apply translation parallax
        projected[:, 0] -= camera_offset[0] * (depth * 0.7 + 0.15)
        projected[:, 1] -= camera_offset[1] * (depth * 0.7 + 0.15)
        
        # Apply roller coaster rotation & zoom
        cam_roll = camera_offset[2]
        cam_zoom = camera_offset[3]
        if abs(cam_roll) > 0.001 or abs(cam_zoom - 1.0) > 0.001:
            centered_proj = projected - self.center
            theta = cam_roll * (depth * 0.8 + 0.2)
            z = 1.0 + (cam_zoom - 1.0) * (depth * 0.8 + 0.2)
            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            rx = (centered_proj[:, 0] * cos_t - centered_proj[:, 1] * sin_t) * z
            ry = (centered_proj[:, 0] * sin_t + centered_proj[:, 1] * cos_t) * z
            projected[:, 0] = self.center[0] + rx
            projected[:, 1] = self.center[1] + ry
            
        return projected.astype(np.float32), depth

    def _visible_fraction(self, audio, presence: float | None = None) -> float:
        presence = audio.visual_envelope if presence is None else presence
        growth = smoothstep(CONFIG.particle_visibility_attack, CONFIG.particle_visibility_full, presence)
        richness_growth = smoothstep(0.55, 1.0, audio.richness) * 0.12
        diversity_growth = smoothstep(0.30, 0.85, audio.sound_diversity) * 0.16
        bass_growth = smoothstep(0.55, 1.0, audio.bass) * smoothstep(0.20, 0.90, presence) * 0.08
        return min(0.22, CONFIG.min_particle_visibility + (1.0 - CONFIG.min_particle_visibility) * min(1.0, growth + richness_growth + diversity_growth + bass_growth))

    def _distorted_positions(self, positions: np.ndarray, audio, t: float) -> np.ndarray:
        distortion_amount = getattr(audio, "distortion_amount", 0.0)
        noise_amount = getattr(audio, "noise_amount", 0.0)
        if audio.sound_class in {"silence", "ambient"} and not audio.is_guitar and distortion_amount <= 0.02 and noise_amount <= 0.02:
            return positions
        strength = CONFIG.distortion_strength * (
            0.25
            + audio.guitar_confidence * 0.45
            + audio.spectral_flux * 0.35
            + audio.richness * CONFIG.richness_distortion_boost
            + audio.class_confidence * 0.25
            + distortion_amount * 0.85
            + noise_amount * 0.26
        ) * max(0.15, audio.visual_envelope)
        frequency = CONFIG.distortion_frequency * (0.72 + audio.note_confidence + audio.class_confidence * 0.35 + distortion_amount * 1.35 + noise_amount * 0.45)
        phase = t * CONFIG.distortion_speed * (0.7 + audio.class_confidence * 0.6) + max(0, audio.pitch_class) * 0.37
        x = positions[:, 0]
        y = positions[:, 1]
        dx = np.sin(y * frequency + phase) * strength + np.sin((x + y) * frequency * 0.45 - phase) * strength * 0.35
        dy = np.cos(x * frequency * 0.82 - phase * 1.17) * strength * 0.72 + np.cos((x - y) * frequency * 0.38 + phase) * strength * 0.28
        if distortion_amount > 0.01:
            dx += np.sign(np.sin(y * frequency * 2.7 + phase * 1.8)) * strength * distortion_amount * 0.45
        if noise_amount > 0.02:
            dx += np.sin((x * 0.41 + y * 0.17) + phase * 12.0) * strength * noise_amount * 0.18
            dy += np.cos((y * 0.39 - x * 0.13) - phase * 10.0) * strength * noise_amount * 0.18
        warped = positions.copy()
        warped[:, 0] += dx
        warped[:, 1] += dy
        return warped

    def draw_connections(self, surface: pygame.Surface, color: pygame.Color, audio, presence: float | None = None, camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        presence = audio.visual_envelope if presence is None else presence
        if presence <= 0.001:
            return

        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        env = max(0.0, min(1.0, presence))
        line_energy = smoothstep(0.001, 0.22, env)
        max_subset_size = 120
        chosen = self.draw_order[:max_subset_size]
        base_subset = self.positions[chosen]
        subset = self._distorted_positions(base_subset, audio, audio.pitch_class * 0.13 + audio.centroid)
        subset, depth = self._depth_projected_positions(subset, audio, audio.pitch_class * 0.13 + audio.centroid, camera_offset)
        velocities = self.velocities[chosen]
        speed = np.linalg.norm(velocities, axis=1) + 1e-6
        directions = velocities / speed[:, None]
        cell = CONFIG.line_distance * (0.82 + audio.mid * 0.55)
        buckets: dict[tuple[int, int], list[int]] = {}
        for i, p in enumerate(subset):
            key = (int(p[0] // cell), int(p[1] // cell))
            buckets.setdefault(key, []).append(i)

        target_fraction = (24 + line_energy * 62 + audio.richness * 64 + audio.sound_diversity * 92) / max_subset_size
        max_dist_sq = cell * cell * (0.72 + audio.mid * 0.45 + audio.note_confidence * 0.18)
        for key, indices in buckets.items():
            neighbor_indices = []
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    neighbor_indices.extend(buckets.get((key[0] + ox, key[1] + oy), []))
            for i in indices:
                p = subset[i]
                for j in neighbor_indices:
                    if j <= i:
                        continue
                    q = subset[j]
                    d = float(np.sum((p - q) ** 2))
                    if d < max_dist_sq:
                        alignment = abs(float(np.dot(directions[i], directions[j])))
                        if alignment < 0.18 and audio.richness < 0.35:
                            continue
                        closeness = 1.0 - d / max_dist_sq
                        idx_i = i / max_subset_size
                        idx_j = j / max_subset_size
                        max_idx = max(idx_i, idx_j)
                        line_fade = max(0.0, min(1.0, (target_fraction - max_idx) * 10.0))
                        if line_fade <= 0.01:
                            continue
                        alpha = int(
                            (closeness**1.8)
                            * (20 + audio.presence * 28 + audio.richness * 38 + audio.sound_diversity * 42)
                            * (0.18 + line_energy * 0.92)
                            * (0.55 + alignment * 0.45)
                            * line_fade
                        )
                        if alpha <= 3:
                            continue
                        bend = math.sin((p[0] + q[1]) * 0.006 + audio.pitch_class * 0.7) * (2.0 + audio.note_confidence * 7.0)
                        mid = (p + q) * 0.5
                        delta = q - p
                        length = math.sqrt(d) + 1e-6
                        normal = np.array([-delta[1] / length, delta[0] / length], dtype=np.float32)
                        control = mid + normal * bend
                        line_color = (*color[:3], alpha)
                        pygame.draw.aaline(layer, line_color, (float(p[0]), float(p[1])), (float(control[0]), float(control[1])))
                        pygame.draw.aaline(layer, line_color, (float(control[0]), float(control[1])), (float(q[0]), float(q[1])))
                        if alpha > 18:
                            pygame.draw.circle(layer, (*color[:3], alpha // 3), (int(control[0]), int(control[1])), 1)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
