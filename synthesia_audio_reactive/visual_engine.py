"""Pygame renderer and interaction layer for the simulator."""

from __future__ import annotations

import math
import time

import pygame

from audio_engine import AudioFeatures
from config import CONFIG
from effects import Effects
from particle_system import ParticleSystem
from utils import palette, star_field


class VisualEngine:
    modes = [
        "Particle Galaxy",
        "Neural Universe",
        "Audio Nebula",
        "Energy Tentacles",
        "Fractal Reactor",
    ]

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(CONFIG.title)
        self.fullscreen = CONFIG.fullscreen
        self.screen = self._create_screen()
        self.clock = pygame.time.Clock()
        self.width, self.height = self.screen.get_size()
        self.particles = ParticleSystem(self.width, self.height, CONFIG.particle_count)
        self.effects = Effects(self.width, self.height)
        self.stars = star_field(520, self.width, self.height)
        self.mode = 0
        self.show_lines = True
        self.show_shockwaves = True
        self.show_parallax = False
        self.show_wavelines = True
        self.parallax_alpha = 0.0
        self.wavelines_alpha = 1.0
        self.paused = False
        self.running = True
        self.requested_audio_source: str | None = None
        self.requested_capture_preset: str | None = None
        self.toggle_guitar_only_requested = False
        self.start_time = time.perf_counter()
        self.visual_time = 0.0
        self.visual_presence = 0.0
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cam_roll = 0.0
        self.cam_zoom = 1.0
        self.coaster_pos = 0.0
        self.beat_bump = 0.0
        self.font = pygame.font.SysFont("Segoe UI", 18)
        self.font_mid = pygame.font.SysFont("Segoe UI", 22)
        self.font_big = pygame.font.SysFont("Segoe UI", 34)

    def _create_screen(self) -> pygame.Surface:
        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF if self.fullscreen else pygame.DOUBLEBUF
        try:
            return pygame.display.set_mode((CONFIG.width, CONFIG.height), flags, vsync=1)
        except Exception:
            return pygame.display.set_mode((CONFIG.width, CONFIG.height), flags)

    def tick(self) -> float:
        return self.clock.tick(CONFIG.fps) / 1000.0

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_f:
            self.fullscreen = not self.fullscreen
            self.screen = self._create_screen()
        elif key == pygame.K_SPACE:
            self.particles.reset()
        elif key == pygame.K_TAB:
            self.mode = (self.mode + 1) % len(self.modes)
        elif key == pygame.K_l:
            self.show_lines = not self.show_lines
        elif key == pygame.K_b:
            self.show_shockwaves = not self.show_shockwaves
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key == pygame.K_m:
            self.requested_capture_preset = "mic"
        elif key == pygame.K_o:
            self.requested_capture_preset = "screen"
        elif key == pygame.K_g:
            self.requested_capture_preset = "guitar"
        elif key == pygame.K_c:
            self.requested_capture_preset = "cycle"
        elif pygame.K_1 <= key <= pygame.K_5:
            self.mode = key - pygame.K_1
        elif key == pygame.K_6:
            self.show_parallax = not self.show_parallax
        elif key == pygame.K_7:
            self.show_wavelines = not self.show_wavelines

    def update_and_draw(self, dt: float, audio: AudioFeatures, source_name: str = "audio", guitar_only: bool = False) -> None:
        primary, secondary, accent = palette(audio.centroid, audio.bass, audio.mid, audio.treble)
        source_allowed = audio.is_guitar or not guitar_only
        target_presence = audio.visual_envelope if source_allowed else 0.0
        
        # Frame-rate independent presence smoothing
        presence_factor = CONFIG.transition_attack if target_presence > self.visual_presence else CONFIG.transition_release
        presence_smoothing = max(0.001, min(0.999, presence_factor ** (60.0 * dt)))
        self.visual_presence = self.visual_presence * presence_smoothing + target_presence * (1.0 - presence_smoothing)
        active = source_allowed and self.visual_presence > 0.0008

        # Accumulate visual time based on music tempo and intensity
        if active and not self.paused:
            time_speed = 0.65 + audio.visual_intensity * 2.8 + (1.8 if audio.beat else 0.0)
            self.visual_time += dt * time_speed
        else:
            self.visual_time += dt * 0.28
        t = self.visual_time

        # Update roller coaster movement (coaster_pos)
        # Coaster speed increases with percussive visual_intensity and beat!
        if active and not self.paused:
            self.coaster_pos += dt * (1.8 + audio.visual_intensity * 4.5)
            # Beat bump vertically
            bump_target = (audio.beat * 55.0) if hasattr(audio, 'beat') else 0.0
            self.beat_bump = self.beat_bump * 0.80 + bump_target * 0.20
        else:
            self.beat_bump *= 0.90 # Decay when inactive

        # Coaster turns (tilt & horizontal sway) - influenced directly by stereo panning!
        panning_influence = getattr(audio, "panning", 0.0) * 0.85
        turn = math.sin(self.coaster_pos * 0.65) * 0.45 + math.sin(self.coaster_pos * 0.25) * 0.20 + panning_influence
        # Coaster ups and downs (slope)
        slope = math.cos(self.coaster_pos * 0.85) * 0.35 + math.cos(self.coaster_pos * 0.3) * 0.12

        # Target roller coaster offsets (large and highly visible!)
        if active:
            # Gating factor that goes to 0 when inactive, but stays high when active
            motion_gate = 0.35 + 0.65 * self.visual_presence
            
            # cam_x moves by up to 320px, treble adds high-frequency jitter
            target_cam_x = turn * (320.0 + audio.treble * 220.0) * motion_gate
            # cam_y moves by up to 240px, beat bump adds vertical hit, bass adds low-frequency bounce
            target_cam_y = (slope * 220.0 - self.beat_bump * 1.5 + audio.bass * 80.0) * motion_gate
            # cam_roll tilts by up to 0.65 radians (approx 37 degrees)
            target_cam_roll = -turn * (0.65 + audio.bass * 0.45) * motion_gate
            # cam_zoom ranges from ~0.75 to ~1.28
            target_cam_zoom = 1.0 + (slope * 0.25 + audio.visual_envelope * 0.18) * motion_gate
        else:
            target_cam_x = 0.0
            target_cam_y = 0.0
            target_cam_roll = 0.0
            target_cam_zoom = 1.0

        # Smooth camera movement
        cam_smooth = 0.88 ** (60.0 * dt)
        self.cam_x = self.cam_x * cam_smooth + target_cam_x * (1.0 - cam_smooth)
        self.cam_y = self.cam_y * cam_smooth + target_cam_y * (1.0 - cam_smooth)
        self.cam_roll = self.cam_roll * cam_smooth + target_cam_roll * (1.0 - cam_smooth)
        self.cam_zoom = self.cam_zoom * cam_smooth + target_cam_zoom * (1.0 - cam_smooth)

        if active and audio.beat and self.show_shockwaves:
            self.effects.trigger_shockwave()

        if active and not self.paused:
            self.particles.update(dt, audio, self.mode, t)
        self.effects.update(dt)
        self.effects.update_audio_motion(dt, audio, self.visual_presence)

        self._draw_background(audio, primary, secondary, t, self.visual_presence)

        if not active:
            self.effects.shockwaves.clear()
            self.effects.draw_idle_wave_field(self.screen, primary, secondary)
            self._draw_idle_monitor(audio, primary, secondary, t, source_name, guitar_only)
            self._draw_hud(audio, source_name, guitar_only)
            pygame.display.flip()
            return

        target_parallax = 1.0 if self.show_parallax else 0.0
        target_wavelines = 1.0 if self.show_wavelines else 0.0
        alpha_speed = min(1.0, 4.0 * dt)
        self.parallax_alpha += (target_parallax - self.parallax_alpha) * alpha_speed
        self.wavelines_alpha += (target_wavelines - self.wavelines_alpha) * alpha_speed

        signature = self._morph_signature_text(audio)
        
        # 4-tuple to drawers: (cam_x, cam_y, cam_roll, cam_zoom)
        camera_tuple = (self.cam_x, self.cam_y, self.cam_roll, self.cam_zoom)

        # Draw abstract wavelines in the background
        if self.wavelines_alpha > 0.01:
            self.effects.draw_abstract_line_field(self.screen, primary, secondary, accent, audio, t, self.visual_presence * self.wavelines_alpha, camera_offset=camera_tuple)

        # Mode-specific visual effects (Tentacles, Nebula, Fractal)
        # Drawn here so they appear BEHIND the parallax room when it's active
        if self.mode == 2:  # Audio Nebula
            self.effects.draw_nebula(self.screen, primary, secondary, audio, t, self.visual_presence, camera_offset=camera_tuple)
        elif self.mode == 3:  # Energy Tentacles
            self.effects.draw_tentacles(self.screen, accent, audio, t, self.visual_presence, camera_offset=camera_tuple)
        elif self.mode == 4:  # Fractal Reactor
            self.effects.draw_fractal_reactor(self.screen, accent, audio, t, self.visual_presence, camera_offset=camera_tuple)

        # Draw Parallax Room (Optical Depth Field) on top of the ornaments
        if self.parallax_alpha > 0.01:
            self.effects.draw_optical_depth_field(self.screen, primary, secondary, accent, audio, t, self.visual_presence * self.parallax_alpha)

        # Particles (foreground)
        self.particles.draw(self.screen, primary, secondary, audio, self.mode, t, self.visual_presence, camera_offset=camera_tuple)
        if self.show_lines:
            self.particles.draw_connections(self.screen, accent, audio, self.visual_presence, camera_offset=camera_tuple)

        self._draw_hud(audio, source_name, guitar_only, signature)
        pygame.display.flip()

    def _draw_background(self, audio: AudioFeatures, primary: pygame.Color, secondary: pygame.Color, t: float, presence: float) -> None:
        fade = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        fade_alpha = int(80 - min(1.0, presence) * (80 - CONFIG.trail_alpha))
        fade.fill((2, 4, 10, fade_alpha))
        self.screen.blit(fade, (0, 0))

        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        visible_stars = len(self.stars)
        target_fraction = min(1.0, presence * 0.55 + audio.richness * 0.25)
        
        # Deep background parallax shift (opposite to camera offset)
        dx = int(self.cam_x * (0.32 - 0.5) * 1.5)
        dy = int(self.cam_y * (0.32 - 0.5) * 1.5)
        
        # Roller coaster rotation & zoom for stars (depth = 0.32)
        theta = self.cam_roll * 0.32
        z = 1.0 + (self.cam_zoom - 1.0) * 0.32
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        cx, cy = self.width // 2, self.height // 2

        for idx, (x, y, b) in enumerate(self.stars):
            idx_fraction = idx / visible_stars
            star_fade = max(0.0, min(1.0, (target_fraction - idx_fraction) * 10.0))
            if star_fade <= 0.01:
                continue
            
            # Apply parallax shift
            px = x + dx - cx
            py = y + dy - cy
            # Apply roller coaster tilt and zoom
            rx = (px * cos_t - py * sin_t) * z
            ry = (px * sin_t + py * cos_t) * z
            final_x = int(cx + rx)
            final_y = int(cy + ry)

            if 0 <= final_x < self.width and 0 <= final_y < self.height:
                twinkle = int(b * (0.55 + 0.45 * math.sin(t * 1.4 + x * 0.01 + y * 0.02)))
                alpha = int(twinkle * (0.25 + audio.class_confidence * 0.75) * presence * star_fade)
                if alpha > 2:
                    pygame.draw.circle(bg, (92 + primary.r // 6, 84 + secondary.g // 7, 66 + primary.b // 10, alpha), (final_x, final_y), 1)
        self.screen.blit(bg, (0, 0), special_flags=pygame.BLEND_ADD)

    def _draw_spiral(self, primary: pygame.Color, secondary: pygame.Color, audio: AudioFeatures, t: float) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        center = (self.width // 2, self.height // 2)
        arms = 3
        for arm in range(arms):
            points = []
            for i in range(180):
                u = i / 179
                angle = arm / arms * math.tau + u * (7.5 + audio.mid * 4.5) + t * (0.14 + audio.bass * 0.2)
                radius = u * (160 + audio.rms * 520)
                x = center[0] + math.cos(angle) * radius
                y = center[1] + math.sin(angle) * radius * 0.58
                points.append((x, y))
            color = primary if arm % 2 == 0 else secondary
            pygame.draw.aalines(layer, (*color[:3], 34), False, points)
        self.screen.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def _morph_signature_text(self, audio: AudioFeatures) -> str:
        weights = [
            ("BASS", audio.shape_bass),
            ("PERC", audio.shape_percussive),
            ("BRIGHT", audio.shape_bright),
            ("VOCAL", audio.shape_vocal),
            ("TONAL", audio.shape_tonal),
            ("AMBIENT", audio.shape_ambient),
            ("DIST", audio.distortion_amount),
            ("NOISE", audio.noise_amount),
        ]
        top = [item for item in sorted(weights, key=lambda item: item[1], reverse=True)[:2] if item[1] > 0.02]
        if not top:
            return "MORPH SILENCE"
        return "MORPH " + " + ".join(f"{name} {weight:.2f}" for name, weight in top)

    def _audio_status(self, audio: AudioFeatures, guitar_only: bool = False) -> str:
        if audio.is_guitar:
            return "GUITAR CLEAR"
        if not audio.audio_received:
            return "NO AUDIO BUFFER"
        if audio.raw_input_level < 0.0005:
            return "INPUT TOO LOW"
        if guitar_only and audio.activity > 0.025:
            return "IGNORING NON-GUITAR / UNCLEAR SOUND"
        if not guitar_only and audio.visual_envelope > 0.003:
            return "AUDIO ACTIVE"
        if audio.visual_intensity <= 0.001:
            return "BELOW VISUAL THRESHOLD"
        return "WAITING FOR CLEAR SIGNAL"

    def _draw_hud(self, audio: AudioFeatures, source_name: str = "audio", guitar_only: bool = False, signature: str = "SILENCE") -> None:
        fps = self.clock.get_fps()
        status = self._audio_status(audio, guitar_only)
        lines = [
            f"{self.modes[self.mode]} | SRC {source_name} | {'GTR ONLY' if guitar_only else 'ALL AUDIO'} | {status} | {signature}",
            f"RAW {audio.raw_input_level:.5f}  ACT {audio.activity:.2f}  ENV {audio.visual_envelope:.2f}  VIS {audio.visual_intensity:.2f}  RICH {audio.richness:.2f}  DIV {audio.sound_diversity:.2f}  FPS {fps:04.1f}",
            f"CAM X {self.cam_x:+.1f}  Y {self.cam_y:+.1f}  ROLL {math.degrees(self.cam_roll):+.1f}°  ZOOM {self.cam_zoom:.2f}  PAN {getattr(audio, 'panning', 0.0):+.2f}",
            f"MORPH B{audio.shape_bass:.2f} P{audio.shape_percussive:.2f} H{audio.shape_bright:.2f} V{audio.shape_vocal:.2f} T{audio.shape_tonal:.2f} A{audio.shape_ambient:.2f}  {audio.pitch_freq:05.0f} Hz  NOTE {audio.note_name}  M mic-only  O screen-only  G guitar-only  C cycle",
        ]
        for index, line in enumerate(lines):
            image = self.font.render(line, True, (196, 218, 224))
            self.screen.blit(image, (18, 16 + index * 22))

    def _draw_meter(
        self,
        layer: pygame.Surface,
        label: str,
        value: float,
        rect: pygame.Rect,
        color: tuple[int, int, int],
    ) -> None:
        level = max(0.0, min(1.0, value))
        pygame.draw.rect(layer, (164, 156, 130, 44), rect, width=1, border_radius=4)
        fill = pygame.Rect(rect.x + 2, rect.y + 2, int((rect.width - 4) * level), rect.height - 4)
        if fill.width > 0:
            pygame.draw.rect(layer, (*color, 145), fill, border_radius=3)
        text = self.font.render(f"{label} {value:.3f}", True, (215, 208, 184))
        layer.blit(text, (rect.x, rect.y - 23))

    def _draw_idle_monitor(self, audio: AudioFeatures, primary: pygame.Color, secondary: pygame.Color, t: float, source_name: str, guitar_only: bool) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        status = self._audio_status(audio, guitar_only)
        meter_width = int(self.width * 0.42)
        meter_height = 14
        x = (self.width - meter_width) // 2
        y = self.height - 142
        raw_level = max(0.0, min(1.0, audio.raw_input_level / max(0.0001, CONFIG.visual_full_raw_level)))
        env_level = max(0.0, min(1.0, audio.visual_envelope))
        guitar_level = max(0.0, min(1.0, audio.guitar_confidence))

        pygame.draw.line(layer, (120, 110, 88, 26), (0, self.height // 2), (self.width, self.height // 2), 1)
        pygame.draw.line(layer, (120, 110, 88, 18), (self.width // 2, 0), (self.width // 2, self.height), 1)

        title = self.font_big.render(status, True, (232, 221, 190))
        subtitle = self.font_mid.render(
            f"{source_name} | {'guitar-only filter ON' if guitar_only else 'all-audio mode'} | M mic-only | O screen-only | G guitar-only | C cycle",
            True,
            (174, 184, 178),
        )
        self.screen.blit(title, title.get_rect(center=(self.width // 2, int(self.height * 0.43))))
        self.screen.blit(subtitle, subtitle.get_rect(center=(self.width // 2, int(self.height * 0.43) + 42)))

        self._draw_meter(layer, "RAW", raw_level, pygame.Rect(x, y, meter_width, meter_height), primary[:3])
        self._draw_meter(layer, "ENV", env_level, pygame.Rect(x, y + 38, meter_width, meter_height), secondary[:3])
        self._draw_meter(layer, "GTR", guitar_level, pygame.Rect(x, y + 76, meter_width, meter_height), (220, 190, 128))

        dots = 18 + int(raw_level * 36)
        center_y = self.height * 0.54
        for i in range(dots):
            u = i / max(1, dots - 1)
            px = int(self.width * (0.23 + u * 0.54))
            drift = math.sin(t * (0.55 + raw_level * 1.7) + i * 0.71) * (8 + 26 * raw_level)
            py = int(center_y + drift)
            alpha = int(28 + raw_level * 92)
            pygame.draw.circle(layer, (*primary[:3], alpha), (px, py), 1)

        self.screen.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def shutdown(self) -> None:
        pygame.quit()
