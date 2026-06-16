"""Configuration for Synthesia Audio Reactive Simulator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    title: str = "Synthesia Audio Reactive Simulator"
    width: int = 1920
    height: int = 1080
    fps: int = 60
    fullscreen: bool = False
    particle_count: int = 2200
    sample_rate: int = 44100
    block_size: int = 1024
    fft_size: int = 2048
    audio_source: str = "microphone"  # "microphone" or "system_audio"
    guitar_only: bool = False
    input_device: int | None = None
    output_device: int | None = None
    mic_gain: float = 95.0
    audio_smoothing: float = 0.70
    silence_threshold: float = 0.014
    visual_min_raw_level: float = 0.0009
    visual_full_raw_level: float = 0.045
    visual_envelope_attack: float = 0.28
    visual_envelope_release: float = 0.88
    guitar_confidence_threshold: float = 0.075
    guitar_note_confidence_threshold: float = 0.025
    guitar_harmonicity_threshold: float = 0.14
    guitar_required_frames: int = 1
    guitar_body_threshold: float = 0.007
    guitar_max_spread: float = 0.92
    guitar_air_reject: float = 0.88
    guitar_min_frequency: float = 70.0
    guitar_max_frequency: float = 1400.0
    visual_attack: float = 0.28
    visual_release: float = 0.88
    transition_attack: float = 0.38
    transition_release: float = 0.945
    morph_force_smoothing: float = 0.975
    morph_velocity_damping: float = 0.995
    detail_transition_layers: int = 3
    beat_cooldown: float = 0.18
    bass_range: tuple[int, int] = (20, 160)
    mid_range: tuple[int, int] = (160, 2500)
    treble_range: tuple[int, int] = (2500, 12000)
    flow_scale: float = 0.0018
    flow_speed: float = 0.075
    particle_speed: float = 2.15
    distortion_strength: float = 18.0
    distortion_frequency: float = 0.012
    distortion_speed: float = 1.15
    distortion_visual_gain: float = 1.25
    noise_visual_gain: float = 1.10
    noise_dot_count: int = 180
    noise_scratch_count: int = 28
    optical_depth_strength: float = 0.82
    optical_layer_count: int = 11
    optical_chromatic_shift: float = 3.0
    parallax_room_speed: float = 0.18
    parallax_room_smooth: float = 0.94
    parallax_room_depth: float = 0.92
    richness_line_boost: int = 55
    richness_particle_size: float = 0.45
    richness_distortion_boost: float = 0.7
    min_particle_visibility: float = 0.0015
    particle_visibility_attack: float = 0.52
    particle_visibility_full: float = 1.05
    trail_alpha: int = 30
    line_distance: float = 68.0
    max_lines: int = 82


CONFIG = AppConfig()
