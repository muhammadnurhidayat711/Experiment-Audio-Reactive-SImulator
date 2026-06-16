"""Visual effects: shockwaves, nebula fields, fractal strokes, and glows."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
import pygame
from noise import pnoise2

from config import CONFIG
from utils import draw_glow_circle


@dataclass
class Shockwave:
    x: float
    y: float
    radius: float = 20.0
    alpha: float = 220.0
    speed: float = 1500.0

    def update(self, dt: float) -> bool:
        self.radius += self.speed * dt
        self.alpha -= 360.0 * dt
        return self.alpha > 0 and self.radius < max(CONFIG.width, CONFIG.height) * 1.2

    def draw(self, surface: pygame.Surface, color: pygame.Color) -> None:
        if self.alpha <= 0:
            return
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*color[:3], int(self.alpha)), (int(self.x), int(self.y)), int(self.radius), 3)
        pygame.draw.circle(layer, (*color[:3], int(self.alpha * 0.25)), (int(self.x), int(self.y)), int(self.radius * 0.86), 1)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)


class Effects:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.center = (width // 2, height // 2)
        self.shockwaves: list[Shockwave] = []
        self.wave_phase = 0.0
        self.flow_phase = 0.0
        self.left_drift = 0.0
        self.left_drift_px = 0.0
        self.flow_energy = 0.0
        self.flow_centroid = 0.0
        self.line_bass = 0.0
        self.line_percussive = 0.0
        self.line_bright = 0.0
        self.line_vocal = 0.0
        self.line_tonal = 0.0
        self.line_ambient = 0.0
        self.line_richness = 0.0
        self.line_flux = 0.0
        self.line_presence = 0.0
        self.line_diversity = 0.0
        self.line_distortion = 0.0
        self.line_noise = 0.0
        self.depth_energy = 0.0
        self.depth_rotation = 0.0
        self.room_travel = 0.0
        self.room_breath = 0.0
        self.room_focus = 0.0
        self.nebula_points = np.random.rand(180, 3).astype(np.float32)
        self.nebula_points[:, 0] *= width
        self.nebula_points[:, 1] *= height
        self.nebula_points[:, 2] = np.random.uniform(20, 150, len(self.nebula_points))

    def trigger_shockwave(self) -> None:
        jitter_x = random.uniform(-50, 50)
        jitter_y = random.uniform(-50, 50)
        self.shockwaves.append(Shockwave(self.center[0] + jitter_x, self.center[1] + jitter_y))

    def update(self, dt: float) -> None:
        self.shockwaves = [wave for wave in self.shockwaves if wave.update(dt)]

    def update_audio_motion(self, dt: float, audio, presence: float) -> None:
        target_energy = max(0.0, min(1.0, presence * 0.72 + audio.richness * 0.22 + audio.spectral_flux * 0.16))
        
        s_flow_energy = max(0.001, min(0.999, 0.92 ** (60.0 * dt)))
        self.flow_energy = self.flow_energy * s_flow_energy + target_energy * (1.0 - s_flow_energy)
        
        s_flow_centroid = max(0.001, min(0.999, 0.94 ** (60.0 * dt)))
        self.flow_centroid = self.flow_centroid * s_flow_centroid + audio.centroid * (1.0 - s_flow_centroid)
        
        s_line_bass = max(0.001, min(0.999, 0.955 ** (60.0 * dt)))
        self.line_bass = self.line_bass * s_line_bass + audio.shape_bass * (1.0 - s_line_bass)
        
        s_line_percussive = max(0.001, min(0.999, 0.965 ** (60.0 * dt)))
        self.line_percussive = self.line_percussive * s_line_percussive + audio.shape_percussive * (1.0 - s_line_percussive)
        
        s_line_bright = max(0.001, min(0.999, 0.96 ** (60.0 * dt)))
        self.line_bright = self.line_bright * s_line_bright + audio.shape_bright * (1.0 - s_line_bright)
        
        s_line_vocal = max(0.001, min(0.999, 0.955 ** (60.0 * dt)))
        self.line_vocal = self.line_vocal * s_line_vocal + audio.shape_vocal * (1.0 - s_line_vocal)
        
        s_line_tonal = max(0.001, min(0.999, 0.955 ** (60.0 * dt)))
        self.line_tonal = self.line_tonal * s_line_tonal + audio.shape_tonal * (1.0 - s_line_tonal)
        
        s_line_ambient = max(0.001, min(0.999, 0.965 ** (60.0 * dt)))
        self.line_ambient = self.line_ambient * s_line_ambient + audio.shape_ambient * (1.0 - s_line_ambient)
        
        s_line_richness = max(0.001, min(0.999, 0.95 ** (60.0 * dt)))
        self.line_richness = self.line_richness * s_line_richness + audio.richness * (1.0 - s_line_richness)
        
        s_line_flux = max(0.001, min(0.999, 0.965 ** (60.0 * dt)))
        self.line_flux = self.line_flux * s_line_flux + audio.spectral_flux * (1.0 - s_line_flux)
        
        s_line_presence = max(0.001, min(0.999, 0.94 ** (60.0 * dt)))
        self.line_presence = self.line_presence * s_line_presence + presence * (1.0 - s_line_presence)
        
        diversity = getattr(audio, "sound_diversity", 0.0)
        s_line_diversity = max(0.001, min(0.999, 0.955 ** (60.0 * dt)))
        self.line_diversity = self.line_diversity * s_line_diversity + diversity * (1.0 - s_line_diversity)
        
        s_line_distortion = max(0.001, min(0.999, 0.86 ** (60.0 * dt)))
        self.line_distortion = self.line_distortion * s_line_distortion + getattr(audio, "distortion_amount", 0.0) * (1.0 - s_line_distortion)
        
        s_line_noise = max(0.001, min(0.999, 0.90 ** (60.0 * dt)))
        self.line_noise = self.line_noise * s_line_noise + getattr(audio, "noise_amount", 0.0) * (1.0 - s_line_noise)
        
        depth_target = min(1.0, presence * 0.54 + audio.richness * 0.28 + audio.sound_diversity * 0.18 + self.line_distortion * 0.16)
        room_smooth = max(0.001, min(0.999, CONFIG.parallax_room_smooth ** (60.0 * dt)))
        self.depth_energy = self.depth_energy * room_smooth + depth_target * (1.0 - room_smooth)
        
        s_room_breath = max(0.001, min(0.999, 0.965 ** (60.0 * dt)))
        self.room_breath = self.room_breath * s_room_breath + (audio.bass * 0.42 + audio.mid * 0.32 + audio.richness * 0.26) * (1.0 - s_room_breath)
        
        s_room_focus = max(0.001, min(0.999, 0.955 ** (60.0 * dt)))
        self.room_focus = self.room_focus * s_room_focus + (audio.centroid * 0.55 + audio.sound_diversity * 0.45) * (1.0 - s_room_focus)
        
        beat_impulse = 1.0 if (hasattr(audio, 'beat') and audio.beat) else 0.0
        self.depth_rotation += dt * (0.02 + self.depth_energy * 0.06 + self.line_tonal * 0.025 + self.line_bright * 0.018 + beat_impulse * 0.05)
        self.room_travel += dt * (CONFIG.parallax_room_speed * 0.45 + self.depth_energy * 0.15 + self.room_breath * 0.08 + beat_impulse * 0.22)
        self.wave_phase += dt * (0.30 + self.flow_energy * 1.2 + self.line_bright * 0.45 + self.line_percussive * 0.32 + diversity * 0.15 + beat_impulse * 0.8)
        self.flow_phase += dt * (0.16 + self.flow_energy * 0.88 + self.flow_centroid * 0.32 + diversity * 0.12 + beat_impulse * 0.5)
        self.left_drift += dt * (0.024 + self.flow_energy * 0.12 + self.line_bass * 0.04 + diversity * 0.04 + self.line_distortion * 0.03 + beat_impulse * 0.1)
        self.left_drift_px += dt * (18.0 + self.flow_energy * 120.0 + self.line_bass * 35.0 + diversity * 40.0 + self.line_distortion * 45.0 + beat_impulse * 80.0)

    def draw_shockwaves(self, surface: pygame.Surface, color: pygame.Color) -> None:
        for wave in self.shockwaves:
            wave.draw(surface, color)

    def draw_optical_depth_field(
        self,
        surface: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        t: float,
        presence: float,
    ) -> None:
        amount = min(1.0, max(presence, self.depth_energy) * CONFIG.optical_depth_strength)
        if amount <= 0.006:
            return

        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        cx, cy = self.center
        layer_count = max(5, CONFIG.optical_layer_count)
        center_shift_x = math.sin(self.depth_rotation * 0.63) * self.width * 0.018 * amount
        center_shift_y = math.cos(self.depth_rotation * 0.51) * self.height * 0.014 * amount
        room_depth = CONFIG.parallax_room_depth

        for depth_index in range(layer_count):
            phase_depth = (depth_index / layer_count + self.room_travel) % 1.0
            near = phase_depth
            z = 1.0 - near
            perspective = 1.0 / (0.22 + z * 1.42)
            room_scale = (0.20 + near**1.85 * 1.18) * (0.92 + self.room_breath * 0.26)
            half_w = self.width * room_scale * (0.35 + self.room_focus * 0.08)
            half_h = self.height * room_scale * (0.20 + audio.mid * 0.06 + self.room_breath * 0.04)
            phase = self.depth_rotation + depth_index * 0.47
            warp = 12.0 + amount * 34.0 + audio.spectral_spread * 26.0
            frame = self._room_frame_points(
                cx + center_shift_x * near,
                cy + center_shift_y * near,
                half_w * perspective * room_depth,
                half_h * perspective * room_depth,
                phase,
                warp * (0.35 + near * 0.95),
                depth_index,
            )

            parallax = near * near * (12.0 + amount * 46.0)
            chroma = CONFIG.optical_chromatic_shift * amount * near
            shadow = [(x - chroma - parallax * 0.08, y + chroma * 0.55) for x, y in frame]
            highlight = [(x + chroma * 0.75, y - chroma * 0.45 - parallax * 0.04) for x, y in frame]
            fade = (1.0 - near * 0.50) * (0.45 + phase_depth * 0.55)
            alpha = int((10 + amount * 46 + audio.class_confidence * 14) * fade)
            if alpha <= 2:
                continue
            color = (primary, secondary, accent)[depth_index % 3]
            pygame.draw.aalines(layer, (18, 10, 34, max(2, alpha // 3)), True, shadow)
            pygame.draw.aalines(layer, (*color[:3], alpha), True, frame)
            if amount > 0.08:
                pygame.draw.aalines(layer, (*accent[:3], max(2, alpha // 5)), True, highlight)

        self._draw_room_parallax_dust(layer, primary, secondary, accent, t, amount, audio)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def _room_frame_points(
        self,
        cx: float,
        cy: float,
        half_w: float,
        half_h: float,
        phase: float,
        warp: float,
        seed: int,
    ) -> list[tuple[float, float]]:
        points = []
        side_steps = 22
        corners = (
            (-1.0, -1.0),
            (1.0, -1.0),
            (1.0, 1.0),
            (-1.0, 1.0),
        )
        for side in range(4):
            x1, y1 = corners[side]
            x2, y2 = corners[(side + 1) % 4]
            for i in range(side_steps):
                u = i / side_steps
                bx = x1 + (x2 - x1) * u
                by = y1 + (y2 - y1) * u
                edge_bias = math.sin(u * math.pi)
                curve = math.sin(u * math.tau + phase + side * 0.9) * warp * edge_bias
                noise = pnoise2(seed * 0.13 + side * 0.31 + u * 1.7, self.flow_phase * 0.035 + phase * 0.08, octaves=2) * warp * 0.55
                if side in (0, 2):
                    px = cx + bx * half_w
                    py = cy + by * half_h + curve + noise
                else:
                    px = cx + bx * half_w + curve * 0.72 + noise * 0.72
                    py = cy + by * half_h
                pinch = 1.0 + math.sin(phase * 0.7 + side) * 0.018
                points.append((cx + (px - cx) * pinch, cy + (py - cy) / max(0.82, pinch)))
        return points

    def _draw_depth_dust(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        t: float,
        amount: float,
        audio,
    ) -> None:
        max_count = 150
        cx, cy = self.center
        for i in range(max_count):
            activation_threshold = (i / max_count)
            current_level = (amount * 0.7 + audio.sound_diversity * 0.3)
            particle_fade = max(0.0, min(1.0, (current_level - activation_threshold) * 5.0))
            if particle_fade <= 0.01:
                continue
            seed = i * 4.917
            z = ((math.sin(seed + t * (0.18 + amount * 0.16)) + 1.0) * 0.5) ** 1.7
            angle = seed * 2.399963 + self.depth_rotation * (0.3 + z * 0.8)
            radius = (80 + z * min(self.width, self.height) * 0.72) * (0.75 + audio.bass * 0.28)
            warp = pnoise2(math.cos(angle) * 0.8 + t * 0.04, math.sin(angle) * 0.8 + seed, octaves=2)
            x = cx + math.cos(angle + warp * 0.35) * radius
            y = cy + math.sin(angle - warp * 0.28) * radius * (0.54 + z * 0.30)
            size = max(1, int((1 + z * 3.5 + amount * 1.5) * (0.7 + 0.3 * particle_fade)))
            alpha = int((8 + z * 58) * amount * particle_fade)
            color = (primary, secondary, accent)[i % 3]
            if alpha > 2:
                pygame.draw.circle(layer, (*color[:3], alpha), (int(x), int(y)), size)

    def _draw_room_parallax_dust(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        t: float,
        amount: float,
        audio,
    ) -> None:
        max_count = 180
        cx, cy = self.center
        for i in range(max_count):
            activation_threshold = (i / max_count)
            current_level = (amount * 0.6 + audio.sound_diversity * 0.4)
            particle_fade = max(0.0, min(1.0, (current_level - activation_threshold) * 5.0))
            if particle_fade <= 0.01:
                continue
            seed = i * 7.137
            lane = ((math.sin(seed * 1.43) * 43758.5453) % 1.0)
            z = (lane + self.room_travel * (0.38 + amount * 0.45) + math.sin(seed) * 0.013) % 1.0
            near = z**2.15
            angle = seed * 2.399963 + math.sin(self.depth_rotation + seed) * 0.12
            base_radius = 42 + near * min(self.width, self.height) * (0.82 + audio.bass * 0.18)
            drift = pnoise2(seed * 0.09, self.flow_phase * 0.05 + z, octaves=2) * (22 + near * 42)
            x = cx + math.cos(angle) * (base_radius + drift) + math.sin(t * 0.11 + seed) * near * 24
            y = cy + math.sin(angle) * (base_radius * (0.54 + near * 0.24) + drift * 0.5)
            size = max(1, int((1 + near * 4.6 + amount * 1.4) * (0.7 + 0.3 * particle_fade)))
            alpha = int((6 + near * 74) * amount * (0.45 + 0.55 * z) * particle_fade)
            if alpha <= 2:
                continue
            color = (primary, secondary, accent)[i % 3]
            pygame.draw.circle(layer, (*color[:3], alpha), (int(x), int(y)), size)
            if near > 0.72 and amount > 0.18:
                tail = 4 + near * 18
                self._draw_organic_stroke(
                    layer,
                    (*color[:3], int(alpha // 3 * particle_fade)),
                    (x - math.cos(angle) * tail, y - math.sin(angle) * tail * 0.55),
                    (x, y),
                    (2.0 + near * 4.0) * (0.7 + 0.3 * particle_fade),
                    seed + t * 0.7,
                    5,
                )

    def draw_energy_orb(self, surface: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        bass = audio.bass
        radius = int(38 + audio.rms * 72 + bass * 42)
        draw_glow_circle(surface, self.center, radius, color, layers=5, alpha=int(42 + bass * 70))
        ring_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for i in range(2):
            angle = t * (1.2 + i * 0.27)
            rx = int(radius * (1.55 + i * 0.16))
            ry = int(radius * (0.72 + i * 0.11))
            local = pygame.Surface((rx * 2 + 8, ry * 2 + 8), pygame.SRCALPHA)
            rect = pygame.Rect(4, 4, rx * 2, ry * 2)
            pygame.draw.ellipse(local, (*color[:3], 50 - i * 7), rect, 2)
            rotated = pygame.transform.rotate(local, math.degrees(math.sin(angle) * 16.0 + i * 24.0))
            ring_layer.blit(rotated, rotated.get_rect(center=self.center))
        surface.blit(ring_layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_audio_signature(
        self,
        surface: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        t: float,
        presence: float | None = None,
    ) -> str:
        presence = audio.visual_envelope if presence is None else presence
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._draw_morph_contour(layer, primary, secondary, audio, t, presence)
        self._draw_transition_details(layer, primary, secondary, accent, audio, t, presence)

        weights = [
            ("bass", audio.shape_bass),
            ("percussive", audio.shape_percussive),
            ("bright", audio.shape_bright),
            ("vocal", audio.shape_vocal),
            ("tonal", audio.shape_tonal),
            ("ambient", audio.shape_ambient),
        ]
        if max(weight for _, weight in weights) < 0.04:
            weights = [(audio.sound_class, max(0.12, audio.class_confidence))]

        for family, weight in weights:
            if weight <= 0.035:
                continue
            temp = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            if family == "bass":
                self._draw_resonant_rings(temp, primary, audio, t)
                self._draw_low_pulse(temp, primary, secondary, audio, t)
            elif family == "percussive":
                self._draw_pick_shards(temp, accent, audio, t)
                self._draw_transient_ticks(temp, primary, audio, t)
            elif family == "bright":
                self._draw_harmonic_sparks(temp, primary, secondary, audio, t)
                self._draw_bright_threads(temp, accent, audio, t)
            elif family == "vocal":
                self._draw_rosette(temp, secondary, audio, t)
                self._draw_mid_ribbons(temp, primary, audio, t)
            elif family == "tonal":
                self.draw_guitar_signature(temp, primary, secondary, accent, audio, t)
            else:
                self._draw_texture_field(temp, primary, secondary, audio, t)
            temp.set_alpha(int((58 + min(1.0, weight) * 172) * max(0.08, presence)))
            layer.blit(temp, (0, 0), special_flags=pygame.BLEND_ADD)

        top = sorted(weights, key=lambda item: item[1], reverse=True)[:2]
        signature = "MORPH " + " + ".join(f"{name.upper()} {weight:.2f}" for name, weight in top if weight > 0.02)

        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
        return signature

    def draw_abstract_line_field(
        self,
        surface: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        t: float,
        presence: float,
        camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0),
    ) -> None:
        if presence <= 0.003:
            return

        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        diversity = getattr(audio, "sound_diversity", 0.0)
        
        # Dynamic circular wavelines (Structured and Dynamic)
        bands = min(15, max(4, int(8 + self.line_richness * 10 + diversity * 6)))
        base_alpha = int(75 * presence * min(1.0, self.line_presence * 2.5))
        if base_alpha <= 2:
            return

        cx_center, cy_center = self.width // 2, self.height // 2

        # Draw concentric circular wavebands
        for band in range(bands):
            u_band = band / max(1, bands - 1)
            points = []
            
            # Dynamic radius per band
            base_radius = self.height * (0.08 + u_band * 0.35 + self.line_ambient * 0.05)
            phase = self.wave_phase * (0.82 + self.line_bright * 0.28 + self.line_percussive * 0.18) + band * 1.37
            
            amplitude = (
                20
                + self.line_bass * 45
                + self.line_vocal * 25
                + self.line_bright * 15
                + self.line_flux * 20
                + diversity * 15
            ) * 0.6
            
            # Dynamic spikes based on percussive
            spikes = int(6 + self.line_percussive * 18 + audio.bass * 6 + band % 3)
            
            # 3D Depth parallax offsets for this band
            band_depth = 0.15 + band * 0.08
            dx = -camera_offset[0] * (band_depth * 1.5)
            dy = -camera_offset[1] * (band_depth * 1.5)
            
            theta = camera_offset[2] * (band_depth * 0.8 + 0.2)
            z = 1.0 + (camera_offset[3] - 1.0) * (band_depth * 0.8 + 0.2)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            
            steps = 180
            for i in range(steps + 1):  # +1 to close the loop
                u = i / steps
                angle = u * math.tau
                
                # Dynamic audio deformation
                deformation = math.sin(angle * spikes + phase) * amplitude
                n = pnoise2(math.cos(angle) * 1.2 + band * 0.2 + self.flow_phase * 0.1, 
                            math.sin(angle) * 1.2 - self.flow_phase * 0.08, octaves=2) * (12 + self.line_ambient * 20)
                
                radius = base_radius + deformation + n
                
                # Rotate alternating bands in opposite directions
                rot_dir = 1 if band % 2 == 0 else -1
                x = cx_center + math.cos(angle + t * 0.15 * rot_dir) * radius
                y = cy_center + math.sin(angle + t * 0.15 * rot_dir) * radius
                
                # Apply parallax
                px = x + dx - cx_center
                py = y + dy - cy_center
                
                # Apply coaster rotation & zoom
                rx = (px * cos_t - py * sin_t) * z
                ry = (px * sin_t + py * cos_t) * z
                points.append((cx_center + rx, cy_center + ry))

            color = (primary, secondary, accent)[band % 3]
            band_gate = max(0.0, min(1.0, (self.line_richness + diversity + self.line_percussive + self.line_bright) * 0.55 + 0.45 - band * 0.05))
            alpha = max(2, int(base_alpha * (0.4 + u_band * 0.4) * band_gate))
            
            if alpha > 2:
                pygame.draw.aalines(layer, (*color[:3], alpha), True, points[:-1])
                
            # Add dynamic sparks on the rings for high energy
            if self.line_bright > 0.03 or self.line_percussive > 0.06:
                skip = 8
                for point in points[band % skip :: skip]:
                    spark_alpha = int(alpha * (0.40 + self.line_bright * 1.5 + self.line_percussive * 0.8))
                    if spark_alpha > 5:
                        pygame.draw.circle(layer, (*accent[:3], min(150, spark_alpha)), (int(point[0]), int(point[1])), 1)

        self._draw_shape_echoes(layer, primary, secondary, accent, audio, t, presence)
        self._draw_sound_flow_object(layer, primary, secondary, accent, audio, presence)
        self._draw_subtle_leaves(layer, primary, secondary, audio, presence)
        self._draw_distortion_overlay(layer, primary, secondary, accent, t, presence)
        self._draw_noise_overlay(layer, primary, secondary, t, presence)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def _warp_line_point(self, x: float, y: float, sample: float, band: int) -> tuple[float, float]:
        strength = 2.0 + self.line_bass * 4.0 + self.line_vocal * 3.0 + self.line_bright * 2.0 + self.line_diversity * 3.0
        phase = self.flow_phase * (0.35 + self.line_bright * 0.12) + band * 0.73
        slow = math.sin(sample * math.tau * (1.1 + self.line_tonal * 0.5) + phase)
        fine = math.sin(sample * math.tau * (2.0 + self.line_ambient * 0.5) - phase * 0.5)
        return (
            x + slow * strength * 0.35 + fine * strength * 0.15,
            y + math.cos(sample * math.tau * (1.0 + self.line_vocal * 0.4) - phase) * strength * 0.25,
        )

    def _draw_organic_stroke(
        self,
        layer: pygame.Surface,
        color: tuple[int, int, int, int],
        start: tuple[float, float],
        end: tuple[float, float],
        wobble: float,
        phase: float,
        steps: int = 9,
    ) -> None:
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) + 1e-6
        nx = -dy / length
        ny = dx / length
        points = []
        for i in range(max(4, steps)):
            u = i / max(1, steps - 1)
            taper = math.sin(u * math.pi)
            curl = math.sin(u * math.tau * 1.35 + phase) * wobble * taper
            drift = math.sin(u * math.tau * 0.55 - phase * 0.7) * wobble * 0.35 * taper
            px = x1 + dx * u + nx * curl + dx / length * drift
            py = y1 + dy * u + ny * curl + dy / length * drift
            points.append((px, py))
        pygame.draw.aalines(layer, color, False, points)

    def _draw_distortion_overlay(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        t: float,
        presence: float,
    ) -> None:
        amount = min(1.0, self.line_distortion * CONFIG.distortion_visual_gain * max(0.0, presence) * 0.22)
        if amount <= 0.018:
            return

        band_count = 22
        for band in range(band_count):
            band_fade = max(0.0, min(1.0, amount * 2.0 - (band / band_count) * 1.5))
            if band_fade <= 0.01:
                continue
            seed = band * 19.173
            y = self.height * ((math.sin(seed * 1.7) + 1.0) * 0.5)
            y += math.sin(t * 1.8 + seed) * 34.0 * amount
            width = self.width * (0.12 + 0.22 * ((math.sin(seed) + 1.0) * 0.5))
            x = (self.width * ((math.sin(seed * 2.31 + t * 0.13) + 1.0) * 0.5)) - width * 0.5
            offset = math.sin(t * (7.0 + amount * 8.0) + seed) * (18.0 + amount * 74.0)
            color = (primary, secondary, accent)[band % 3]
            alpha = int((10 + amount * 72) * (0.35 + 0.65 * ((math.sin(seed * 3.0) + 1.0) * 0.5)) * band_fade)
            if alpha <= 3:
                continue
            self._draw_organic_stroke(
                layer,
                (*color[:3], alpha),
                (x + offset, y),
                (x + width + offset, y + math.sin(seed) * 12 * amount),
                (8.0 + amount * 28.0) * (0.7 + 0.3 * band_fade),
                t * 2.1 + seed,
                12,
            )
            if amount > 0.22 and band % 3 == 0:
                self._draw_organic_stroke(
                    layer,
                    (*accent[:3], (alpha // 2)),
                    (x - offset * 0.4, y + 5),
                    (x + width * 0.55 - offset * 0.4, y + 5 + math.sin(seed + t) * 6 * amount),
                    (5.0 + amount * 20.0) * (0.7 + 0.3 * band_fade),
                    t * 2.7 - seed,
                    9,
                )

    def _draw_noise_overlay(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        t: float,
        presence: float,
    ) -> None:
        amount = min(1.0, self.line_noise * CONFIG.noise_visual_gain * max(0.0, presence) * 0.22)
        if amount <= 0.018:
            return

        max_dots = CONFIG.noise_dot_count
        for i in range(max_dots):
            dot_fade = max(0.0, min(1.0, amount * 2.0 - (i / max_dots) * 1.5))
            if dot_fade <= 0.01:
                continue
            seed = i * 12.9898 + int(t * 24.0) * 78.233
            x = int(((math.sin(seed) * 43758.5453) % 1.0) * self.width)
            y = int(((math.sin(seed * 1.317) * 24634.6345) % 1.0) * self.height)
            color = primary if i % 2 else secondary
            alpha = int((10 + amount * 76 * ((math.sin(seed * 0.71) + 1.0) * 0.5)) * dot_fade)
            pygame.draw.circle(layer, (*color[:3], alpha), (x, y), 1)

        max_scratches = CONFIG.noise_scratch_count
        for i in range(max_scratches):
            scratch_fade = max(0.0, min(1.0, amount * 2.0 - (i / max_scratches) * 1.5))
            if scratch_fade <= 0.01:
                continue
            seed = i * 9.271 + int(t * 18.0) * 17.13
            x = ((math.sin(seed) * 15342.13) % 1.0) * self.width
            y = ((math.sin(seed * 1.91) * 54123.31) % 1.0) * self.height
            length = (8 + amount * 48 * ((math.sin(seed * 0.33) + 1.0) * 0.5)) * (0.6 + 0.4 * scratch_fade)
            angle = math.sin(seed * 0.77) * 0.8
            color = secondary if i % 2 else primary
            alpha = int((8 + amount * 52) * scratch_fade)
            self._draw_organic_stroke(
                layer,
                (*color[:3], alpha),
                (x, y),
                (x + math.cos(angle) * length, y + math.sin(angle) * length),
                (2.5 + amount * 9.0) * (0.6 + 0.4 * scratch_fade),
                seed + t * 3.0,
                5,
            )

    def draw_idle_wave_field(
        self,
        surface: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
    ) -> None:
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        spacing = 16.0
        margin = 96.0
        steps = int((self.width + margin * 2) / spacing) + 3
        world_start = math.floor((self.left_drift_px - margin) / spacing) * spacing
        for band in range(4):
            points = []
            y_base = self.height * (0.24 + band * 0.17)
            phase = self.wave_phase * 0.72 + band * 1.31
            for i in range(steps):
                world_x = world_start + i * spacing
                x = world_x - self.left_drift_px
                sample = world_x / max(1.0, self.width)
                n = pnoise2(sample * 1.7 + band * 0.23 + self.flow_phase * 0.04, self.flow_phase * 0.035, octaves=2)
                y = y_base + math.sin(sample * math.tau * 1.35 + phase) * 18 + n * 26
                points.append((x, y))
            color = primary if band % 2 == 0 else secondary
            pygame.draw.aalines(layer, (*color[:3], 10 + band * 2), False, points)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def _draw_sound_flow_object(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        presence: float,
    ) -> None:
        if presence <= 0.01:
            return

        diversity = getattr(audio, "sound_diversity", 0.0)
        stream_count = 6
        base_y = self.height * (0.52 + (self.line_bass - self.line_bright) * 0.12)
        travel = self.flow_phase * (0.62 + self.line_percussive * 0.42 + self.line_bright * 0.34)
        for stream in range(stream_count):
            stream_fade = max(0.0, min(1.0, (self.line_richness * 0.5 + self.line_vocal * 0.3 + diversity * 0.2) * 2.5 - (stream - 2) * 0.5)) if stream >= 2 else 1.0
            if stream_fade <= 0.01:
                continue
            points = []
            offset = (stream - (stream_count - 1) / 2) * (22 + self.line_vocal * 30)
            phase = travel + stream * 0.73
            for i in range(118):
                u = i / 117
                x = self.width * (0.08 + u * 0.84)
                long_wave = math.sin(u * math.tau * (1.0 + self.line_tonal * 1.2) + phase) * (34 + self.line_bass * 30)
                fine_wave = math.sin(u * math.tau * (2.4 + self.line_bright * 3.8) - phase * 1.05) * (6 + self.line_bright * 16)
                ribbon_wave = math.sin(u * math.tau * 2.0 + self.flow_phase * 0.72 + stream) * self.line_vocal * 48
                noise = pnoise2(u * 1.8 + stream, self.flow_phase * 0.08, octaves=2) * (16 + self.line_ambient * 42)
                y = base_y + offset + long_wave + fine_wave + ribbon_wave + noise
                x += math.sin(u * math.tau + phase) * self.line_ambient * 24
                points.append(self._warp_point(x, y, audio, self.flow_phase + stream * 0.07, 0.45 + self.flow_energy))

            color = (primary, secondary, accent)[stream % 3]
            alpha = int((22 + self.flow_energy * 64 + audio.class_confidence * 18 + diversity * 26) * presence * (1.0 - stream * 0.08) * stream_fade)
            if alpha > 3:
                pygame.draw.aalines(layer, (*color[:3], alpha), False, points)

            head_u = (self.flow_phase * (0.08 + self.line_percussive * 0.06) + stream * 0.23) % 1.0
            head_index = max(0, min(len(points) - 1, int(head_u * (len(points) - 1))))
            hx, hy = points[head_index]
            head_radius = int((2 + presence * 4 + audio.shape_bass * 4 + audio.shape_percussive * 3) * (0.7 + 0.3 * stream_fade))
            pygame.draw.circle(layer, (*accent[:3], min(180, alpha + 38)), (int(hx), int(hy)), max(1, head_radius))

            tail_step = 9 if audio.shape_bright > 0.08 else 14
            for point in points[stream % tail_step :: tail_step]:
                dot_alpha = int(alpha * (0.22 + audio.shape_bright * 0.8 + audio.shape_percussive * 0.45))
                if dot_alpha > 3:
                    pygame.draw.circle(layer, (*color[:3], min(110, dot_alpha)), (int(point[0]), int(point[1])), 1)

    def _draw_subtle_leaves(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        audio,
        presence: float,
    ) -> None:
        leaf_strength = max(audio.shape_vocal, audio.shape_tonal, audio.shape_ambient * 0.65) * presence
        if leaf_strength <= 0.018:
            return

        leaf_count = 15
        for leaf in range(leaf_count):
            leaf_fade = max(0.0, min(1.0, leaf_strength * 2.5 - (leaf / leaf_count) * 2.0))
            if leaf_fade <= 0.01:
                continue
            seed = leaf * 1.618
            drift = self.flow_phase * (0.13 + audio.shape_ambient * 0.08)
            lane = (leaf + 0.5) / max(1, leaf_count)
            x = self.width * (0.12 + ((lane + drift) % 0.76))
            y = self.height * (0.28 + 0.46 * ((math.sin(seed + self.flow_phase * 0.22) + 1.0) * 0.5))
            angle = math.sin(seed + self.flow_phase * 0.31) * 0.75 + audio.centroid * 0.35
            length = (18 + leaf_strength * 38 + audio.shape_vocal * 18) * (0.7 + 0.3 * leaf_fade)
            width = (5 + leaf_strength * 13) * (0.7 + 0.3 * leaf_fade)
            color = primary if leaf % 2 else secondary
            alpha = int((8 + leaf_strength * 38) * (0.55 + 0.45 * math.sin(seed + self.flow_phase) ** 2) * leaf_fade)
            if alpha <= 2:
                continue

            points_left = []
            points_right = []
            for i in range(12):
                u = i / 11
                vein = math.sin(u * math.pi)
                bend = math.sin(u * math.pi * 1.4 + self.flow_phase * 0.45 + seed) * 3.5 * leaf_strength
                forward = (u - 0.5) * length
                side = vein * width
                ca = math.cos(angle)
                sa = math.sin(angle)
                cx = x + ca * forward - sa * bend
                cy = y + sa * forward + ca * bend
                points_left.append((cx - sa * side, cy + ca * side))
                points_right.append((cx + sa * side, cy - ca * side))

            pygame.draw.aalines(layer, (*color[:3], alpha), False, points_left)
            pygame.draw.aalines(layer, (*color[:3], alpha), False, points_right)
            if alpha > 10:
                midline = [((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5) for a, b in zip(points_left, points_right)]
                pygame.draw.aalines(layer, (*color[:3], alpha // 2), False, midline)

    def _draw_shape_echoes(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        t: float,
        presence: float,
    ) -> None:
        echo_count = 45
        radius = 120 + audio.shape_bass * 210 + audio.shape_tonal * 150 + audio.shape_ambient * 260
        for i in range(echo_count):
            u = i / max(1, echo_count - 1)
            # fade based on index: higher index echoes appear only at higher richness/percussive
            echo_fade = max(0.0, min(1.0, (audio.shape_percussive * 0.4 + audio.shape_bright * 0.3 + audio.richness * 0.3) * 2.5 - (1.0 - u) * 1.5))
            if u > 0.2 and echo_fade <= 0.01:
                continue
            angle = i * 2.399963 + t * (0.08 + audio.shape_bright * 0.28)
            local_radius = radius * (0.22 + math.sqrt(u) * 0.92)
            wobble = math.sin(t * 0.9 + i * 0.61) * (18 + audio.shape_vocal * 55)
            x = self.center[0] + math.cos(angle) * (local_radius + wobble)
            y = self.center[1] + math.sin(angle) * (local_radius * (0.62 + audio.shape_ambient * 0.22))
            color = primary if i % 3 == 0 else secondary if i % 3 == 1 else accent
            alpha = int((10 + audio.richness * 54 + audio.shape_percussive * 34) * presence * (0.45 + u * 0.55) * (echo_fade if u > 0.2 else 1.0))
            if alpha > 3:
                if audio.shape_bass > max(audio.shape_bright, audio.shape_percussive):
                    rect = pygame.Rect(0, 0, int(12 + audio.shape_bass * 44), int(5 + audio.shape_bass * 16))
                    rect.center = (int(x), int(y))
                    pygame.draw.ellipse(layer, (*color[:3], alpha), rect, 1)
                elif audio.shape_percussive > 0.08:
                    length = 8 + audio.shape_percussive * 42
                    x2 = x + math.cos(angle) * length
                    y2 = y + math.sin(angle) * length
                    self._draw_organic_stroke(layer, (*color[:3], alpha), (x, y), (x2, y2), 3.0 + audio.shape_percussive * 9.0, t + i * 0.37, 5)
                else:
                    pygame.draw.circle(layer, (*color[:3], alpha), (int(x), int(y)), 1 + int(audio.shape_vocal * 2))

    def _draw_morph_contour(self, layer: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, t: float, presence: float | None = None) -> None:
        intensity = audio.visual_envelope if presence is None else presence
        if intensity <= 0.002:
            return
        points = []
        count = 144
        class_phase = (
            audio.shape_bass * 0.0
            + audio.shape_percussive * 0.9
            + audio.shape_bright * 1.8
            + audio.shape_vocal * 2.7
            + audio.shape_tonal * 1.3
            + audio.shape_ambient * 3.6
        )
        lobes_val = 3.0 + (audio.shape_percussive * 5.0 + audio.shape_bright * 7.0 + audio.shape_vocal * 3.0 + audio.richness * 3.0)
        lobes_a = int(lobes_val)
        lobes_b = lobes_a + 1
        frac = lobes_val - lobes_a
        base_radius = 95 + intensity * 170 + audio.class_confidence * 90
        for i in range(count):
            u = i / count
            angle = u * math.tau
            n = pnoise2(math.cos(angle) * 0.8 + t * 0.12 + class_phase, math.sin(angle) * 0.8 - t * 0.10, octaves=3)
            wave_a = math.sin(angle * lobes_a + t * (0.7 + audio.spectral_flux) + class_phase)
            wave_b = math.sin(angle * lobes_b + t * (0.7 + audio.spectral_flux) + class_phase)
            wave = wave_a * (1.0 - frac) + wave_b * frac
            radius = base_radius + n * (42 + audio.spectral_spread * 80) + wave * (14 + audio.class_confidence * 40)
            radius += abs(math.sin(angle * 9.0 + t * 4.5)) * audio.spectral_flux * 120 * audio.shape_percussive
            radius *= 1.0 + (math.sin(angle * 2.0 + t) * 0.18 * audio.shape_vocal)
            radius += math.sin(angle * 13.0 - t * 2.2) * audio.air * 42 * audio.shape_bright
            radius += math.sin(angle * 3.0 + t * 1.2) * audio.bass * 36 * audio.shape_bass
            x = self.center[0] + math.cos(angle) * radius
            y = self.center[1] + math.sin(angle) * radius * (0.62 + audio.mid * 0.22 + audio.spectral_spread * 0.1)
            points.append(self._warp_point(x, y, audio, t, 1.6))

        color = primary if audio.centroid < 0.55 else secondary
        alpha = int((14 + audio.class_confidence * 54 + audio.richness * 26) * max(0.2, intensity))
        pygame.draw.aalines(layer, (*color[:3], alpha), True, points)
        if alpha > 18:
            pygame.draw.aalines(layer, (*secondary[:3], alpha // 2), True, points[::2])

    def _draw_transition_details(
        self,
        layer: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        t: float,
        presence: float,
    ) -> None:
        if presence <= 0.004:
            return
        weights = (
            audio.shape_bass,
            audio.shape_percussive,
            audio.shape_bright,
            audio.shape_vocal,
            audio.shape_tonal,
            audio.shape_ambient,
        )
        complexity = min(1.0, sum(w * w for w in weights) + audio.richness * 0.45 + audio.spectral_flux * 0.5)
        layers = max(1, CONFIG.detail_transition_layers)
        for band in range(layers):
            points = []
            count = 56 + band * 18
            phase = t * (0.18 + band * 0.05) + band * 1.71
            radius_base = 120 + band * 54 + audio.centroid * 260 + presence * 115
            for i in range(count):
                u = i / max(1, count - 1)
                angle = u * math.tau
                braid = (
                    math.sin(angle * (2.0 + audio.shape_vocal * 3.0) + phase) * (18 + audio.shape_vocal * 42)
                    + math.sin(angle * (5.0 + audio.shape_percussive * 8.0) - t * 1.6) * audio.shape_percussive * 55
                    + math.cos(angle * (7.0 + audio.shape_bright * 8.0) + t * 2.1) * audio.shape_bright * 46
                )
                radius = radius_base + braid + math.sin(angle * 3.0 - t) * audio.shape_bass * 38
                x = self.center[0] + math.cos(angle) * radius
                y = self.center[1] + math.sin(angle) * radius * (0.52 + audio.shape_tonal * 0.18 + audio.shape_ambient * 0.16)
                points.append(self._warp_point(x, y, audio, t + band * 0.11, 0.85 + complexity))
            color = (primary, secondary, accent)[band % 3]
            alpha = int((8 + complexity * 34) * presence * (1.0 - band * 0.18))
            if alpha > 2:
                pygame.draw.aalines(layer, (*color[:3], alpha), True, points)

    def draw_guitar_signature(
        self,
        surface: pygame.Surface,
        primary: pygame.Color,
        secondary: pygame.Color,
        accent: pygame.Color,
        audio,
        t: float,
    ) -> str:
        pitch_class = audio.pitch_class if audio.pitch_class >= 0 else 0
        note = audio.note_name if audio.note_name != "--" else "NO NOTE"
        families = (
            "NORTH LEAF",
            "SOFT WAVE",
            "THIN BRANCH",
            "LOW STEM",
            "OPEN PETAL",
            "QUIET SEED",
            "TALL LEAF",
            "WIDE WAVE",
            "BROKEN BRANCH",
            "FINE STEM",
            "NARROW PETAL",
            "SCATTER SEED",
        )
        family = families[pitch_class]
        signature = f"{note} {family}"
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        echo_count = 1 + int(audio.richness * audio.visual_envelope * 2.2)
        for echo in range(echo_count):
            echo_time = t - echo * 0.18
            if "LEAF" in family:
                self._draw_note_leaf(layer, primary, audio, pitch_class, echo_time)
            elif "WAVE" in family:
                self._draw_note_wave(layer, secondary, audio, pitch_class, echo_time)
            elif "BRANCH" in family:
                self._draw_note_branch(layer, accent, audio, pitch_class, echo_time)
            elif "STEM" in family:
                self._draw_note_stem(layer, primary, audio, pitch_class, echo_time)
            elif "PETAL" in family:
                self._draw_note_petal(layer, secondary, audio, pitch_class, echo_time)
            else:
                self._draw_note_seed(layer, primary, secondary, audio, pitch_class, echo_time)

        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
        return signature

    def _draw_low_pulse(self, layer: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, t: float) -> None:
        intensity = audio.visual_envelope
        rings = 3 + int(audio.bass * 5)
        for i in range(rings):
            u = i / max(1, rings - 1)
            radius = int(75 + u * (190 + audio.bass * 260) + math.sin(t * 2.2 + i) * 12)
            rect = pygame.Rect(0, 0, int(radius * 2.2), int(radius * (0.58 + audio.spectral_spread * 0.22)))
            rect.center = self.center
            color = primary if i % 2 else secondary
            alpha = int((18 + audio.bass * 88) * intensity * (1.0 - u * 0.35))
            pygame.draw.ellipse(layer, (*color[:3], alpha), rect, 2)

    def _draw_transient_ticks(self, layer: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        count = int(16 + audio.spectral_flux * 90 + audio.activity * 28)
        radius = 80 + audio.presence * 160
        for i in range(max(10, count)):
            angle = i / max(10, count) * math.tau + math.sin(t * 7.0 + i) * 0.04
            length = 18 + audio.spectral_flux * 95 + (i % 4) * 7
            start = radius + (i % 5) * 9
            x1 = self.center[0] + math.cos(angle) * start
            y1 = self.center[1] + math.sin(angle) * start
            x2 = self.center[0] + math.cos(angle) * (start + length)
            y2 = self.center[1] + math.sin(angle) * (start + length)
            alpha = int((22 + audio.spectral_flux * 125) * max(0.2, audio.visual_envelope))
            self._draw_organic_stroke(layer, (*color[:3], alpha), (x1, y1), (x2, y2), 3.0 + audio.spectral_flux * 12.0, t * 2.0 + i, 5)

    def _draw_bright_threads(self, layer: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        strands = 5 + int(audio.air * 8)
        for strand in range(strands):
            points = []
            base = strand / max(1, strands) * math.tau + t * (0.08 + audio.centroid * 0.12)
            for i in range(58):
                u = i / 57
                radius = 110 + u * (260 + audio.air * 420)
                angle = base + math.sin(u * math.tau * 2.0 + t * 1.2 + strand) * (0.15 + audio.air * 0.25)
                points.append((self.center[0] + math.cos(angle) * radius, self.center[1] + math.sin(angle) * radius))
            pygame.draw.aalines(layer, (*color[:3], int(12 + audio.air * 70)), False, points)

    def _draw_mid_ribbons(self, layer: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        ribbons = 3 + int(audio.body * 5)
        for ribbon in range(ribbons):
            points = []
            base = ribbon / max(1, ribbons) * math.tau + t * 0.07
            for i in range(72):
                u = i / 71
                radius = 75 + u * (210 + audio.mid * 220)
                wave = math.sin(u * math.tau * (1.2 + audio.note_confidence) + t * 1.1 + ribbon) * (18 + audio.presence * 48)
                angle = base + wave * 0.004 + (u - 0.5) * 0.42
                points.append((self.center[0] + math.cos(angle) * radius, self.center[1] + math.sin(angle) * radius * 0.82))
            pygame.draw.aalines(layer, (*color[:3], int(18 + audio.body * 74)), False, points)

    def _draw_texture_field(self, layer: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, t: float) -> None:
        count = 36 + int(audio.richness * 90 + audio.spectral_spread * 50)
        radius = 130 + audio.centroid * 520
        for i in range(max(24, count)):
            n = pnoise2(i * 0.07 + t * 0.08, audio.centroid * 1.7 - t * 0.05, octaves=2)
            angle = i * 2.399963 + n * 0.7
            distance = radius * (0.22 + ((i * 37) % 100) / 100.0 * 0.88)
            x = int(self.center[0] + math.cos(angle) * distance)
            y = int(self.center[1] + math.sin(angle) * distance)
            color = primary if n > 0 else secondary
            alpha = int((10 + abs(n) * 55 + audio.richness * 46) * max(0.18, audio.visual_envelope))
            pygame.draw.circle(layer, (*color[:3], alpha), (x, y), 1 + int(audio.spectral_spread * 3))

    def _note_angle(self, pitch_class: int, t: float, speed: float = 0.08) -> float:
        return pitch_class / 12.0 * math.tau + t * speed

    def _warp_point(self, x: float, y: float, audio, t: float, amount: float = 1.0) -> tuple[float, float]:
        strength = CONFIG.distortion_strength * 0.32 * amount * (0.2 + audio.guitar_confidence) * max(0.12, audio.visual_envelope)
        freq = CONFIG.distortion_frequency * (0.65 + audio.note_confidence)
        phase = t * CONFIG.distortion_speed + max(0, audio.pitch_class) * 0.37
        return (
            x + math.sin(y * freq + phase) * strength,
            y + math.cos(x * freq * 0.82 - phase * 1.17) * strength * 0.72,
        )

    def _draw_note_leaf(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        angle = self._note_angle(pitch_class, t, 0.025)
        intensity = audio.visual_envelope
        length = 115 + pitch_class * 8 + intensity * 155 + audio.note_confidence * 45
        width = 18 + (pitch_class % 5) * 5 + audio.body * 32 * intensity
        alpha = int(18 + intensity * 58)
        for side in (-1, 1):
            points = []
            for i in range(34):
                u = i / 33
                vein = math.sin(u * math.pi)
                bend = side * vein * width
                forward = (u - 0.08) * length
                x = math.cos(angle) * forward + math.cos(angle + math.pi / 2) * bend
                y = math.sin(angle) * forward + math.sin(angle + math.pi / 2) * bend
                points.append(self._warp_point(self.center[0] + x, self.center[1] + y, audio, t))
            pygame.draw.aalines(layer, (*color[:3], alpha), False, points)
        end = self._warp_point(self.center[0] + math.cos(angle) * length * 0.9, self.center[1] + math.sin(angle) * length * 0.9, audio, t)
        pygame.draw.aaline(layer, (*color[:3], alpha + 12), self.center, end)

    def _draw_note_wave(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        angle = self._note_angle(pitch_class, t, 0.022)
        intensity = audio.visual_envelope
        length = 185 + pitch_class * 10 + intensity * 180
        amplitude = 8 + (pitch_class % 6) * 3 + audio.note_confidence * 42
        alpha = int(16 + intensity * 62)
        strand_count = 2 + pitch_class % 4
        for strand in range(strand_count):
            points = []
            offset = (strand - (strand_count - 1) / 2) * (12 + pitch_class % 3 * 6)
            for i in range(72):
                u = i / 71
                forward = (u - 0.5) * length
                sway = math.sin(u * math.tau * (1.1 + pitch_class % 4 * 0.25) + t * 0.9) * amplitude + offset
                x = math.cos(angle) * forward + math.cos(angle + math.pi / 2) * sway
                y = math.sin(angle) * forward + math.sin(angle + math.pi / 2) * sway
                points.append(self._warp_point(self.center[0] + x, self.center[1] + y, audio, t))
            pygame.draw.aalines(layer, (*color[:3], max(12, alpha - strand * 7)), False, points)

    def _draw_note_ripple(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        angle = self._note_angle(pitch_class, t, 0.03)
        squash = 0.42 + (pitch_class % 4) * 0.12
        for i in range(4):
            radius = int(80 + i * 55 + audio.activity * 150 + audio.note_confidence * 70)
            rect = pygame.Rect(0, 0, radius * 2, int(radius * (0.7 + squash)))
            rect.center = (
                int(self.center[0] + math.cos(angle) * i * 10),
                int(self.center[1] + math.sin(angle) * i * 10),
            )
            pygame.draw.ellipse(layer, (*color[:3], int(34 + audio.activity * 74 - i * 8)), rect, 1)

    def _draw_note_branch(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        base = self._note_angle(pitch_class, t, 0.026)
        branch_count = 2 + pitch_class % 5
        for branch in range(branch_count):
            angle = base + (branch - branch_count / 2) * (0.12 + (pitch_class % 4) * 0.045)
            points = []
            intensity = audio.visual_envelope
            length = 95 + pitch_class * 9 + audio.presence * 95 * intensity
            for i in range(22):
                u = i / 21
                sway = math.sin(t * 0.9 + pitch_class + u * 3.0) * 13 * u
                x = math.cos(angle) * length * u + math.cos(angle + math.pi / 2) * sway
                y = math.sin(angle) * length * u + math.sin(angle + math.pi / 2) * sway
                points.append(self._warp_point(self.center[0] + x, self.center[1] + y, audio, t))
            pygame.draw.aalines(layer, (*color[:3], int(10 + audio.visual_envelope * 58)), False, points)

    def _draw_note_spiral(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        direction = -1 if pitch_class % 2 else 1
        points = []
        turns = 1.2 + (pitch_class % 5) * 0.18
        for i in range(120):
            u = i / 119
            angle = direction * u * math.tau * turns + self._note_angle(pitch_class, t, 0.06)
            radius = u * (95 + audio.activity * 260)
            points.append((self.center[0] + math.cos(angle) * radius, self.center[1] + math.sin(angle) * radius))
        pygame.draw.aalines(layer, (*color[:3], int(55 + audio.activity * 85)), False, points)

    def _draw_note_stem(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        angle = self._note_angle(pitch_class, t, 0.02)
        stems = 2 + pitch_class % 3
        for stem in range(stems):
            points = []
            side = (stem - (stems - 1) / 2) * (10 + pitch_class % 5 * 4)
            intensity = audio.visual_envelope
            length = 115 + pitch_class * 11 + intensity * 185
            for i in range(34):
                u = i / 33
                bend = math.sin(t * 0.75 + u * 3.0 + stem) * 16 * u
                x = math.cos(angle) * length * u + math.cos(angle + math.pi / 2) * (side + bend)
                y = math.sin(angle) * length * u + math.sin(angle + math.pi / 2) * (side + bend)
                points.append(self._warp_point(self.center[0] + x, self.center[1] + y, audio, t))
            pygame.draw.aalines(layer, (*color[:3], int(10 + audio.visual_envelope * 62)), False, points)

    def _draw_note_petal(self, layer: pygame.Surface, color: pygame.Color, audio, pitch_class: int, t: float) -> None:
        petals = 2 + pitch_class % 5
        for petal in range(petals):
            angle = petal / petals * math.tau + self._note_angle(pitch_class, t, 0.018)
            points = []
            for i in range(26):
                u = i / 25
                intensity = audio.visual_envelope
                radius = (18 + pitch_class % 4 * 7 + intensity * 95) * math.sin(u * math.pi)
                forward = u * (76 + pitch_class * 7 + audio.body * 65 * intensity)
                x = math.cos(angle) * forward + math.cos(angle + math.pi / 2) * radius
                y = math.sin(angle) * forward + math.sin(angle + math.pi / 2) * radius
                points.append(self._warp_point(self.center[0] + x, self.center[1] + y, audio, t))
            pygame.draw.aalines(layer, (*color[:3], int((10 + audio.body * 52) * max(0.15, audio.visual_envelope))), False, points)

    def _draw_note_seed(self, layer: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, pitch_class: int, t: float) -> None:
        count = 6 + pitch_class * 2
        radius = 48 + pitch_class * 9 + audio.visual_envelope * 170
        angle_offset = self._note_angle(pitch_class, t, 0.018)
        for i in range(count):
            u = i / max(1, count - 1)
            angle = angle_offset + i * 2.399963
            distance = radius * math.sqrt(u) * (0.78 + 0.22 * math.sin(t * 0.7 + i))
            x = int(self.center[0] + math.cos(angle) * distance)
            y = int(self.center[1] + math.sin(angle) * distance)
            color = primary if i % 2 else secondary
            pygame.draw.circle(layer, (*color[:3], int((10 + audio.air * 60) * max(0.18, audio.visual_envelope))), (x, y), 1)

    def _draw_resonant_rings(self, layer: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        freq_scale = max(0.0, min(1.0, (audio.dominant_freq - 70.0) / 360.0))
        wobble = 1.0 + audio.spectral_spread * 1.4
        for i in range(7):
            radius = int(85 + i * 44 + audio.string_low * 180 + freq_scale * 90)
            rect = pygame.Rect(0, 0, int(radius * 2.35), int(radius * (0.72 + wobble * 0.12)))
            rect.center = self.center
            alpha = int((88 - i * 9) * audio.activity)
            pygame.draw.ellipse(layer, (*color[:3], alpha), rect, max(1, 3 - i // 3))
            offset = int(math.sin(t * 4.0 + i) * 18 * audio.string_low)
            pygame.draw.ellipse(layer, (*color[:3], alpha // 3), rect.move(offset, -offset // 2), 1)

    def _draw_rosette(self, layer: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        petals = int(6 + audio.body * 10 + audio.spectral_spread * 8)
        inner = 60 + audio.rms * 90
        outer = 210 + audio.body * 260
        for petal in range(max(5, petals)):
            angle = petal / max(5, petals) * math.tau + t * (0.18 + audio.body * 0.2)
            points = []
            for i in range(18):
                u = i / 17
                wave = math.sin(u * math.pi)
                bend = math.sin(t * 1.8 + petal) * 0.22
                radius = inner + wave * outer
                a = angle + (u - 0.5) * (0.26 + audio.mid * 0.22) + bend * wave
                points.append((self.center[0] + math.cos(a) * radius, self.center[1] + math.sin(a) * radius))
            pygame.draw.aalines(layer, (*color[:3], int(42 + audio.body * 90)), False, points)

    def _draw_pick_shards(self, layer: pygame.Surface, color: pygame.Color, audio, t: float) -> None:
        shard_count = int(18 + audio.presence * 42 + audio.spectral_flux * 55)
        for i in range(max(12, shard_count)):
            angle = i / max(12, shard_count) * math.tau + math.sin(t * 8.0 + i) * 0.08
            length = 120 + audio.presence * 420 + (i % 5) * 18
            start = 45 + audio.rms * 55
            x1 = self.center[0] + math.cos(angle) * start
            y1 = self.center[1] + math.sin(angle) * start
            x2 = self.center[0] + math.cos(angle) * length
            y2 = self.center[1] + math.sin(angle) * length
            alpha = int(38 + audio.spectral_flux * 150)
            self._draw_organic_stroke(layer, (*color[:3], alpha), (x1, y1), (x2, y2), 7.0 + audio.presence * 28.0, t * 2.6 + i * 0.41, 8)

    def _draw_harmonic_sparks(self, layer: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, t: float) -> None:
        sparks = int(45 + audio.air * 120 + audio.treble * 85)
        radius = 170 + audio.centroid * 650
        for i in range(max(25, sparks)):
            phase = i * 12.989 + t * 2.3
            angle = (math.sin(phase) * 43758.5453) % math.tau
            distance = radius * (0.35 + ((math.sin(phase * 1.7) + 1.0) * 0.5) * 0.85)
            x = int(self.center[0] + math.cos(angle) * distance)
            y = int(self.center[1] + math.sin(angle) * distance)
            color = primary if i % 2 else secondary
            size = 1 + int(audio.air * 4)
            pygame.draw.circle(layer, (*color[:3], int(45 + audio.air * 130)), (x, y), size)

    def draw_nebula(self, surface: pygame.Surface, primary: pygame.Color, secondary: pygame.Color, audio, t: float, presence: float, camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dx = int(-camera_offset[0] * 0.45)
        dy = int(-camera_offset[1] * 0.45)
        
        # Coaster rotation & zoom for Nebula
        theta = camera_offset[2] * (0.45 * 0.8 + 0.2)
        z = 1.0 + (camera_offset[3] - 1.0) * (0.45 * 0.8 + 0.2)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        cx, cy = self.width // 2, self.height // 2

        for x, y, r in self.nebula_points:
            n = pnoise2(x * 0.0015 + t * 0.05, y * 0.0015 - t * 0.04, octaves=3)
            px = int(x + n * 48 * (1 + audio.mid)) + dx - cx
            py = int(y + n * 32 * (1 + audio.treble)) + dy - cy
            
            # Apply coaster rotation & zoom
            rx = (px * cos_t - py * sin_t) * z
            ry = (px * sin_t + py * cos_t) * z
            
            final_x = int(cx + rx)
            final_y = int(cy + ry)
            
            if 0 <= final_x < self.width and 0 <= final_y < self.height:
                alpha = int((6 + 34 * abs(n) + audio.rms * 24) * presence)
                color = primary if n > 0 else secondary
                pygame.draw.circle(layer, (*color[:3], alpha), (final_x, final_y), int(r * (0.8 + audio.bass * 0.8) * (0.7 + 0.3 * presence)))
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_tentacles(self, surface: pygame.Surface, color: pygame.Color, audio, t: float, presence: float, camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dx = -camera_offset[0] * 0.65
        dy = -camera_offset[1] * 0.65
        
        # Coaster rotation & zoom for Tentacles
        theta = camera_offset[2] * (0.55 * 0.8 + 0.2)
        z = 1.0 + (camera_offset[3] - 1.0) * (0.55 * 0.8 + 0.2)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        cx, cy = self.width // 2, self.height // 2
        
        # 1. Base Energy Tentacles (Wild, flowing, and spread out)
        arms_base = 24  # Increased slightly to fill the space
        for arm in range(arms_base):
            points = []
            base = arm / arms_base * math.tau + t * 0.15
            length = (220 + audio.mid * 380 + audio.bass * 200) * presence
            
            # Spread the roots of the tentacles across the screen smoothly
            drift_x = math.sin(t * 0.12 + arm * 2.1) * self.width * 0.35
            drift_y = math.cos(t * 0.14 + arm * 1.7) * self.height * 0.35
            start_x = cx + drift_x
            start_y = cy + drift_y
            
            for i in range(25):
                u = i / 24
                wave = math.sin(t * 3.0 + u * 8.0 + arm) * (25 + audio.treble * 50)
                angle = base + u * 1.5 * math.sin(t * 0.7 + arm) + wave * 0.005
                radius = length * u
                x = start_x + math.cos(angle) * radius + dx
                y = start_y + math.sin(angle) * radius + dy
                
                # Apply coaster camera transform around absolute center
                rx = ((x - cx) * cos_t - (y - cy) * sin_t) * z
                ry = ((x - cx) * sin_t + (y - cy) * cos_t) * z
                points.append((cx + rx, cy + ry))
            width = max(1, int((1 + audio.rms * 3) * presence))
            pygame.draw.lines(layer, (*color[:3], int(45 * presence)), False, points, width)

        # 2. Smooth Cannabis Leaf Ornaments (3 leaves spreading dynamically)
        leaf_configs = [
            (cx + math.sin(t * 0.15) * self.width * 0.25, cy + math.cos(t * 0.11) * self.height * 0.22, t * 0.05),
            (cx + math.sin(t * 0.12 + 2.0) * self.width * 0.30, cy + math.cos(t * 0.16 + 2.0) * self.height * 0.26, -t * 0.04 + 1.0),
            (cx + math.sin(t * 0.17 + 4.0) * self.width * 0.22, cy + math.cos(t * 0.13 + 4.0) * self.height * 0.30, t * 0.06 + 2.0),
        ]
        
        arms_leaf = 65  # Very dense, nicely optimized for 3 leaves
        for leaf_x, leaf_y, leaf_rot in leaf_configs:
            for arm in range(arms_leaf):
                arm_angle = arm / arms_leaf * math.tau
                
                # Mathematical Cannabis Leaf Polar Formula
                r_val = (1 - math.sin(arm_angle)) * (1 + 0.9 * math.cos(8 * arm_angle)) * (1 + 0.1 * math.cos(24 * arm_angle))
                leaf_factor = r_val / 4.18  # Normalize to approx 0.0 - 1.0 range
                
                # Smooth breathing effect based on audio envelope
                breathe = 0.9 + 0.1 * math.sin(t * 2.0) + audio.visual_envelope * 0.15
                
                points = []
                # Base angle includes individual leaf rotation
                base_angle = arm_angle + leaf_rot + math.sin(t * 0.4) * 0.15
                length = (190 + audio.mid * 160 + audio.bass * 220) * presence * leaf_factor * breathe
                
                for i in range(25):
                    u = i / 24
                    # Smooth organic curving along the fingers
                    sway = math.sin(t * 1.2 + arm_angle * 3.0) * 0.08
                    angle = base_angle + u * sway
                    
                    radius = length * u
                    x = leaf_x + math.cos(angle) * radius + dx
                    y = leaf_y + math.sin(angle) * radius + dy
                    
                    # Apply coaster camera transform around absolute center
                    rx = ((x - cx) * cos_t - (y - cy) * sin_t) * z
                    ry = ((x - cx) * sin_t + (y - cy) * cos_t) * z
                    points.append((cx + rx, cy + ry))
                
                # Glowing bright lines for the ornament
                width = max(1, int((1.5 + audio.bass * 3) * presence * (0.5 + 0.5 * u)))
                leaf_color = (min(255, color[0] + 20), min(255, color[1] + 60), min(255, color[2] + 20))
                pygame.draw.lines(layer, (*leaf_color, int(180 * presence)), False, points, width)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_fractal_reactor(self, surface: pygame.Surface, color: pygame.Color, audio, t: float, presence: float, camera_offset: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dx = -camera_offset[0] * 0.80
        dy = -camera_offset[1] * 0.80
        
        # Coaster rotation & zoom for Fractal Reactor
        theta = camera_offset[2] * (0.60 * 0.8 + 0.2)
        z = 1.0 + (camera_offset[3] - 1.0) * (0.60 * 0.8 + 0.2)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        cx, cy = self.width // 2, self.height // 2

        fractal_nodes = [
            (cx + math.sin(t * 0.12) * self.width * 0.35, cy + math.cos(t * 0.14) * self.height * 0.35, t * 0.18),
            (cx + math.sin(t * 0.15 + 2.0) * self.width * 0.30, cy + math.cos(t * 0.11 + 2.0) * self.height * 0.30, -t * 0.15),
            (cx + math.sin(t * 0.09 + 4.0) * self.width * 0.35, cy + math.cos(t * 0.17 + 4.0) * self.height * 0.30, t * 0.20),
            (cx + math.sin(t * 0.19 + 6.0) * self.width * 0.25, cy + math.cos(t * 0.13 + 6.0) * self.height * 0.25, -t * 0.22),
            (cx, cy, t * 0.1) # Center node
        ]

        branches = 8  # Reduced slightly per node
        depth = 6
        for node_x, node_y, base_rot in fractal_nodes:
            for i in range(branches):
                angle = i / branches * math.tau + base_rot
                length = (65 + audio.bass * 100) * presence
                self._branch(layer, node_x + dx, node_y + dy, angle, length, depth, color, audio, presence, cos_t, sin_t, z, cx, cy)
        surface.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def _branch(self, layer, x, y, angle, length, depth, color, audio, presence, cos_t=1.0, sin_t=0.0, z=1.0, cx=0.0, cy=0.0) -> None:
        if depth <= 0 or length < 4:
            return
        x2 = x + math.cos(angle) * length
        y2 = y + math.sin(angle) * length
        alpha = int((18 + depth * 24) * presence)
        
        # Apply coaster rotation & zoom
        px1 = (x - cx) * cos_t - (y - cy) * sin_t
        py1 = (x - cx) * sin_t + (y - cy) * cos_t
        tx1 = cx + px1 * z
        ty1 = cy + py1 * z

        px2 = (x2 - cx) * cos_t - (y2 - cy) * sin_t
        py2 = (x2 - cx) * sin_t + (y2 - cy) * cos_t
        tx2 = cx + px2 * z
        ty2 = cy + py2 * z

        pygame.draw.line(layer, (*color[:3], alpha), (tx1, ty1), (tx2, ty2), max(1, depth // 2))
        spread = 0.34 + audio.treble * 0.52
        next_len = length * (0.58 + audio.mid * 0.08)
        self._branch(layer, x2, y2, angle + spread, next_len, depth - 1, color, audio, presence, cos_t, sin_t, z, cx, cy)
        self._branch(layer, x2, y2, angle - spread, next_len, depth - 1, color, audio, presence, cos_t, sin_t, z, cx, cy)
