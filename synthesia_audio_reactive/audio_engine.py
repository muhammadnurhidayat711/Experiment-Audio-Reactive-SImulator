"""Realtime microphone capture and audio feature extraction."""

from __future__ import annotations

import queue
import threading
import time
from ctypes import oledll
from dataclasses import dataclass, field

import numpy as np
import sounddevice as sd

try:
    import soundcard as sc
except Exception:
    sc = None

from config import CONFIG
from utils import clamp, smoothstep


@dataclass
class AudioFeatures:
    raw_input_level: float = 0.0
    audio_received: bool = False
    rms: float = 0.0
    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0
    string_low: float = 0.0
    body: float = 0.0
    presence: float = 0.0
    air: float = 0.0
    dominant_freq: float = 0.0
    pitch_freq: float = 0.0
    pitch_class: int = -1
    note_name: str = "--"
    note_confidence: float = 0.0
    harmonicity: float = 0.0
    guitar_confidence: float = 0.0
    is_guitar: bool = False
    sound_class: str = "silence"
    class_confidence: float = 0.0
    shape_bass: float = 0.0
    shape_percussive: float = 0.0
    shape_bright: float = 0.0
    shape_vocal: float = 0.0
    shape_tonal: float = 0.0
    shape_ambient: float = 0.0
    sound_diversity: float = 0.0
    distortion_amount: float = 0.0
    noise_amount: float = 0.0
    spectral_spread: float = 0.0
    richness: float = 0.0
    visual_intensity: float = 0.0
    visual_envelope: float = 0.0
    activity: float = 0.0
    beat: bool = False
    spectral_flux: float = 0.0
    centroid: float = 0.0
    panning: float = 0.0
    spectrum: np.ndarray = field(default_factory=lambda: np.zeros(CONFIG.fft_size // 2 + 1, dtype=np.float32))


class AudioEngine:
    """Captures microphone input and exposes smoothed reactive features."""

    def __init__(self) -> None:
        self.sample_rate = CONFIG.sample_rate
        self.block_size = CONFIG.block_size
        self.fft_size = CONFIG.fft_size
        self.queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=8)
        self.stream: sd.InputStream | None = None
        self.capture_thread: threading.Thread | None = None
        self.capture_running = False
        self.window = np.zeros(self.fft_size, dtype=np.float32)
        self.buffer = np.zeros(self.fft_size, dtype=np.float32)
        self.freqs = np.zeros(self.fft_size // 2 + 1, dtype=np.float32)
        self.prev_spectrum = np.zeros(self.fft_size // 2 + 1, dtype=np.float32)
        self._configure_sample_rate(self.sample_rate)
        self.features = AudioFeatures()
        self.energy_history: list[float] = [0.0] * 43
        self.last_beat_time = 0.0
        self.last_audio_time = 0.0
        self.guitar_frame_count = 0
        self.visual_envelope = 0.0
        self.panning = 0.0
        self.enabled = False
        self.audio_source = CONFIG.audio_source
        self.guitar_only = CONFIG.guitar_only
        self.allow_microphone_fallback = True
        self.device_name = "No input device"

    def start(self) -> None:
        try:
            self._open_selected_source()
        except Exception as exc:
            self.enabled = False
            print(f"Audio source [{self.audio_source}] unavailable. Visuals will stay idle until audio input is available: {exc}")
            if self.audio_source == "system_audio" and self.allow_microphone_fallback:
                print("Falling back to microphone. Install/enable a loopback input for system audio capture.")
                self.audio_source = "microphone"
                self._reset_runtime_state()
                try:
                    self._open_selected_source()
                except Exception as fallback_exc:
                    self.enabled = False
                    print(f"Microphone fallback unavailable: {fallback_exc}")

    def _open_selected_source(self) -> None:
        if self.audio_source == "system_audio":
            self._open_soundcard_loopback()
            return

        device, channels, extra_settings, query_kind = self._select_audio_source()
        self._use_device_sample_rate(device, query_kind)
        self.stream = sd.InputStream(
            device=device,
            channels=channels,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            callback=self._callback,
            extra_settings=extra_settings,
        )
        self.stream.start()
        self.enabled = True
        info = sd.query_devices(device, query_kind)
        self.device_name = str(info.get("name", f"Audio {device}"))
        print(f"Audio source [{self.audio_source}]: {self.device_name}")

    def _open_soundcard_loopback(self) -> None:
        if sc is None:
            raise RuntimeError(
                "The optional 'soundcard' package is not installed. Run: python -m pip install soundcard"
            )

        speaker = sc.default_speaker()
        microphones = sc.all_microphones(include_loopback=True)
        if not microphones:
            raise RuntimeError("No loopback devices were found by soundcard.")

        speaker_name = str(getattr(speaker, "name", "")).lower()
        loopback = None
        for microphone in microphones:
            name = str(getattr(microphone, "name", "")).lower()
            if speaker_name and speaker_name in name:
                loopback = microphone
                break
        if loopback is None:
            for microphone in microphones:
                name = str(getattr(microphone, "name", "")).lower()
                if "loopback" in name or "stereo mix" in name or "what u hear" in name:
                    loopback = microphone
                    break
        if loopback is None:
            loopback = microphones[0]

        self._configure_sample_rate(48000)
        self.capture_running = True
        self.capture_thread = threading.Thread(target=self._soundcard_loopback_worker, args=(loopback,), daemon=True)
        self.capture_thread.start()
        self.enabled = True
        self.device_name = f"{getattr(loopback, 'name', 'System audio')} (soundcard loopback)"
        print(f"Audio source [{self.audio_source}]: {self.device_name}")

    def _soundcard_loopback_worker(self, loopback) -> None:
        com_initialized = False
        try:
            try:
                oledll.ole32.CoInitialize(None)
                com_initialized = True
            except Exception:
                pass
            with loopback.recorder(samplerate=self.sample_rate, channels=2, blocksize=self.block_size) as recorder:
                while self.capture_running:
                    data = recorder.record(numframes=self.block_size)
                    if data is None or len(data) == 0:
                        continue
                    data_arr = np.asarray(data, dtype=np.float32)
                    mono = np.mean(data_arr, axis=1).astype(np.float32, copy=True)
                    panning = 0.0
                    if data_arr.ndim >= 2 and data_arr.shape[1] >= 2:
                        left_rms = float(np.sqrt(np.mean(data_arr[:, 0] ** 2)))
                        right_rms = float(np.sqrt(np.mean(data_arr[:, 1] ** 2)))
                        denom = left_rms + right_rms
                        if denom > 1e-6:
                            panning = (right_rms - left_rms) / denom
                    try:
                        self.queue.put_nowait((mono, panning))
                    except queue.Full:
                        pass
        except Exception as exc:
            self.enabled = False
            self.capture_running = False
            print(f"System audio loopback stopped: {exc}")
        finally:
            if com_initialized:
                try:
                    oledll.ole32.CoUninitialize()
                except Exception:
                    pass

    def _configure_sample_rate(self, sample_rate: int) -> None:
        self.sample_rate = int(sample_rate)
        self.window = np.hanning(self.fft_size).astype(np.float32)
        self.buffer = np.zeros(self.fft_size, dtype=np.float32)
        self.freqs = np.fft.rfftfreq(self.fft_size, 1.0 / self.sample_rate)
        self.prev_spectrum = np.zeros(self.fft_size // 2 + 1, dtype=np.float32)

    def _use_device_sample_rate(self, device: int | None, query_kind: str) -> None:
        try:
            info = sd.query_devices(device, query_kind)
            device_rate = int(round(float(info.get("default_samplerate", self.sample_rate))))
        except Exception:
            device_rate = CONFIG.sample_rate
        if device_rate > 0 and device_rate != self.sample_rate:
            self._configure_sample_rate(device_rate)

    def _select_audio_source(self) -> tuple[int | None, int, object | None, str]:
        if self.audio_source == "system_audio":
            return self._select_loopback_device()
        return self._select_input_device(), 1, None, "input"

    def set_source(self, audio_source: str, fallback_to_microphone: bool = True) -> None:
        if audio_source not in {"microphone", "system_audio"}:
            return
        self.allow_microphone_fallback = fallback_to_microphone
        if audio_source == self.audio_source and self.enabled:
            return
        self.stop()
        self.audio_source = audio_source
        self._reset_runtime_state()
        self.start()

    def set_guitar_only(self, enabled: bool) -> None:
        self.guitar_only = enabled
        self.visual_envelope = 0.0
        self.features.visual_envelope = 0.0

    def apply_capture_preset(self, preset: str) -> None:
        if preset == "mic":
            self.set_guitar_only(False)
            self.set_source("microphone")
        elif preset == "screen":
            self.set_guitar_only(False)
            self.set_source("system_audio", fallback_to_microphone=False)
        elif preset == "guitar":
            self.set_guitar_only(True)
            self.set_source("microphone")
        elif preset == "cycle":
            if self.audio_source == "microphone" and not self.guitar_only:
                self.apply_capture_preset("screen")
            elif self.audio_source == "system_audio":
                self.apply_capture_preset("guitar")
            else:
                self.apply_capture_preset("mic")

    def toggle_guitar_only(self) -> None:
        self.set_guitar_only(not self.guitar_only)

    def _reset_runtime_state(self) -> None:
        while not self.queue.empty():
            self.queue.get_nowait()
        self.buffer.fill(0.0)
        self.prev_spectrum.fill(0.0)
        self.features = AudioFeatures()
        self.last_audio_time = 0.0
        self.guitar_frame_count = 0
        self.visual_envelope = 0.0

    def _select_loopback_device(self) -> tuple[int | None, int, object | None, str]:
        device = self._select_output_device()
        channels = 2
        try:
            info = sd.query_devices(device, "output")
            channels = max(1, min(2, int(info.get("max_output_channels", 2))))
        except Exception:
            pass

        try:
            return device, channels, sd.WasapiSettings(loopback=True), "output"
        except (AttributeError, TypeError) as exc:
            raise RuntimeError(
                "System audio capture requires a sounddevice/PortAudio build with WASAPI loopback support. "
                "Use microphone mode, Stereo Mix, or a virtual cable input if loopback is not available."
            ) from exc

    def _select_input_device(self) -> int | None:
        if CONFIG.input_device is not None:
            return CONFIG.input_device
        try:
            default_input = sd.default.device[0]
            if default_input is not None and default_input >= 0:
                return int(default_input)
        except Exception:
            pass

        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if int(device.get("max_input_channels", 0)) > 0:
                return index
        return None

    def _select_output_device(self) -> int | None:
        if CONFIG.output_device is not None:
            return CONFIG.output_device
        try:
            default_output = sd.default.device[1]
            if default_output is not None and default_output >= 0:
                return int(default_output)
        except Exception:
            pass

        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if int(device.get("max_output_channels", 0)) > 0:
                return index
        return None

    def stop(self) -> None:
        self.capture_running = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.capture_thread is not None:
            self.capture_thread.join(timeout=1.0)
            self.capture_thread = None

    def _callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
        del frames, time_info, status
        mono = np.mean(indata, axis=1).astype(np.float32, copy=True)
        panning = 0.0
        if indata.ndim >= 2 and indata.shape[1] >= 2:
            left_rms = float(np.sqrt(np.mean(indata[:, 0] ** 2)))
            right_rms = float(np.sqrt(np.mean(indata[:, 1] ** 2)))
            denom = left_rms + right_rms
            if denom > 1e-6:
                panning = (right_rms - left_rms) / denom
        try:
            self.queue.put_nowait((mono, panning))
        except queue.Full:
            pass

    def update(self, dt: float = 0.0167) -> AudioFeatures:
        received = False
        latest_panning = 0.0
        while not self.queue.empty():
            item = self.queue.get_nowait()
            if isinstance(item, tuple):
                chunk, chunk_panning = item
                latest_panning = chunk_panning
            else:
                chunk = item
                latest_panning = 0.0
            length = min(len(chunk), self.fft_size)
            self.buffer = np.roll(self.buffer, -length)
            self.buffer[-length:] = chunk[-length:]
            received = True
            self.last_audio_time = time.perf_counter()

        if not self.enabled:
            return self._silence_features(dt)
        if not received and time.perf_counter() - self.last_audio_time > 0.25:
            return self._silence_features(dt)

        signal = self.buffer * self.window
        spectrum = np.abs(np.fft.rfft(signal)).astype(np.float32)
        spectrum /= np.max(spectrum) + 1e-6

        raw_input_level = float(np.sqrt(np.mean(self.buffer * self.buffer)))
        rms = raw_input_level * CONFIG.mic_gain
        min_level = CONFIG.visual_min_raw_level
        full_level = CONFIG.visual_full_raw_level
        intensity_curve = 0.55
        if self.audio_source == "system_audio":
            min_level = max(min_level, 0.004)
            full_level = max(full_level, 0.34)
            intensity_curve = 0.68
        base_visual_intensity = smoothstep(min_level, full_level, raw_input_level)
        visual_intensity = base_visual_intensity ** intensity_curve
        bass = self._band_energy(spectrum, CONFIG.bass_range)
        mid = self._band_energy(spectrum, CONFIG.mid_range)
        treble = self._band_energy(spectrum, CONFIG.treble_range)
        string_low = self._band_energy(spectrum, (70, 250))
        body = self._band_energy(spectrum, (250, 900))
        presence = self._band_energy(spectrum, (900, 3500))
        air = self._band_energy(spectrum, (3500, 9000))
        flux = float(np.sum(np.maximum(0.0, spectrum - self.prev_spectrum)) / len(spectrum) * 18.0)
        centroid = float(np.sum(self.freqs * spectrum) / (np.sum(spectrum) + 1e-6) / (self.sample_rate * 0.5))
        dominant_freq = self._dominant_frequency(spectrum)
        pitch_freq, pitch_class, note_name, note_confidence = self._pitch_features(spectrum)
        time_pitch_freq, harmonicity = self._time_pitch_features(self.buffer)
        if harmonicity > note_confidence and time_pitch_freq > 0.0:
            pitch_freq = time_pitch_freq
            pitch_class, note_name = self._note_from_frequency(time_pitch_freq)
            note_confidence = max(note_confidence, harmonicity)
        spread = self._spectral_spread(spectrum, centroid)
        flatness = self._spectral_flatness(spectrum)
        activity = smoothstep(CONFIG.silence_threshold, CONFIG.silence_threshold * 2.15, rms)
        richness = self._audio_richness(visual_intensity, body, presence, air, spread, flux)
        distortion_amount = self._distortion_amount(activity, string_low, body, presence, air, spread, flux, note_confidence, harmonicity, flatness)
        noise_amount = self._noise_amount(activity, spread, flux, note_confidence, harmonicity, flatness)
        guitar_confidence = self._guitar_confidence(
            activity=activity,
            note_confidence=note_confidence,
            harmonicity=harmonicity,
            pitch_freq=pitch_freq,
            string_low=string_low,
            body=body,
            presence=presence,
            air=air,
            spread=spread,
            flux=flux,
        )
        raw_is_guitar = guitar_confidence >= CONFIG.guitar_confidence_threshold
        self.guitar_frame_count = self.guitar_frame_count + 1 if raw_is_guitar else 0
        is_guitar = self.guitar_frame_count >= CONFIG.guitar_required_frames
        sound_class, class_confidence, shape_weights = self._sound_class(
            is_guitar=is_guitar,
            guitar_confidence=guitar_confidence,
            activity=activity,
            bass=bass,
            mid=mid,
            treble=treble,
            string_low=string_low,
            body=body,
            presence=presence,
            air=air,
            spread=spread,
            flux=flux,
            note_confidence=note_confidence,
            harmonicity=harmonicity,
            centroid=centroid,
            distortion_amount=distortion_amount,
            noise_amount=noise_amount,
        )

        beat = activity > 0.12 and self._detect_beat(bass, flux)
        self.prev_spectrum = spectrum
        self._smooth(
            AudioFeatures(
                rms=clamp(rms),
                raw_input_level=raw_input_level,
                audio_received=True,
                bass=bass,
                mid=mid,
                treble=treble,
                string_low=string_low,
                body=body,
                presence=presence,
                air=air,
                dominant_freq=dominant_freq,
                pitch_freq=pitch_freq,
                pitch_class=pitch_class,
                note_name=note_name,
                note_confidence=note_confidence,
                harmonicity=harmonicity,
                guitar_confidence=guitar_confidence,
                is_guitar=is_guitar,
                sound_class=sound_class,
                class_confidence=class_confidence,
                shape_bass=shape_weights["bass"],
                shape_percussive=shape_weights["percussive"],
                shape_bright=shape_weights["bright"],
                shape_vocal=shape_weights["vocal"],
                shape_tonal=shape_weights["tonal"],
                shape_ambient=shape_weights["ambient"],
                sound_diversity=self._sound_diversity(shape_weights),
                distortion_amount=distortion_amount,
                noise_amount=noise_amount,
                spectral_spread=spread,
                richness=richness,
                visual_intensity=visual_intensity,
                activity=activity,
                beat=beat,
                spectral_flux=clamp(flux),
                centroid=clamp(centroid),
                panning=latest_panning,
                spectrum=spectrum,
            ),
            dt
        )
        return self.features

    def _band_energy(self, spectrum: np.ndarray, band: tuple[int, int]) -> float:
        mask = (self.freqs >= band[0]) & (self.freqs < band[1])
        if not np.any(mask):
            return 0.0
        value = float(np.mean(spectrum[mask]) * 4.2)
        return clamp(value)

    def _dominant_frequency(self, spectrum: np.ndarray) -> float:
        mask = (self.freqs >= 70) & (self.freqs <= 5000)
        if not np.any(mask):
            return 0.0
        local = spectrum[mask]
        if local.size == 0:
            return 0.0
        return float(self.freqs[mask][int(np.argmax(local))])

    def _pitch_features(self, spectrum: np.ndarray) -> tuple[float, int, str, float]:
        note_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        mask = (self.freqs >= CONFIG.guitar_min_frequency) & (self.freqs <= CONFIG.guitar_max_frequency)
        if not np.any(mask):
            return 0.0, -1, "--", 0.0

        local = spectrum[mask]
        local_freqs = self.freqs[mask]
        if local.size == 0:
            return 0.0, -1, "--", 0.0

        useful = local > max(float(np.mean(local)) * 1.15, 0.018)
        if not np.any(useful):
            return 0.0, -1, "--", 0.0

        useful_freqs = local_freqs[useful]
        useful_energy = local[useful]
        midi_values = np.rint(69 + 12 * np.log2(useful_freqs / 440.0)).astype(np.int32)
        pitch_classes = midi_values % 12
        weights = useful_energy / np.sqrt(useful_freqs / 110.0)

        chroma = np.zeros(12, dtype=np.float32)
        np.add.at(chroma, pitch_classes, weights)
        pitch_class = int(np.argmax(chroma))
        total = float(np.sum(chroma) + 1e-6)
        confidence = float((chroma[pitch_class] - np.mean(chroma)) / total * 3.2)

        same_note = pitch_classes == pitch_class
        freq = float(useful_freqs[same_note][int(np.argmax(weights[same_note]))]) if np.any(same_note) else 0.0
        return freq, pitch_class, note_names[pitch_class], clamp(confidence)

    def _time_pitch_features(self, signal: np.ndarray) -> tuple[float, float]:
        centered = signal.astype(np.float32) - float(np.mean(signal))
        energy = float(np.dot(centered, centered))
        if energy < 1e-7:
            return 0.0, 0.0

        min_lag = max(1, int(self.sample_rate / CONFIG.guitar_max_frequency))
        max_lag = min(len(centered) - 2, int(self.sample_rate / CONFIG.guitar_min_frequency))
        if max_lag <= min_lag:
            return 0.0, 0.0

        corr = np.correlate(centered, centered, mode="full")[len(centered) - 1 :]
        segment = corr[min_lag:max_lag]
        if segment.size == 0:
            return 0.0, 0.0
        lag = int(np.argmax(segment) + min_lag)
        harmonicity = float(corr[lag] / (corr[0] + 1e-6))
        if harmonicity <= 0.0:
            return 0.0, 0.0
        return float(self.sample_rate / lag), clamp(harmonicity)

    def _note_from_frequency(self, freq: float) -> tuple[int, str]:
        note_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        midi = int(round(69 + 12 * np.log2(freq / 440.0)))
        pitch_class = midi % 12
        return pitch_class, note_names[pitch_class]

    def _guitar_confidence(
        self,
        activity: float,
        note_confidence: float,
        harmonicity: float,
        pitch_freq: float,
        string_low: float,
        body: float,
        presence: float,
        air: float,
        spread: float,
        flux: float,
    ) -> float:
        in_guitar_range = CONFIG.guitar_min_frequency <= pitch_freq <= CONFIG.guitar_max_frequency
        if not in_guitar_range or note_confidence < CONFIG.guitar_note_confidence_threshold or activity < 0.025:
            return 0.0

        body_energy = string_low + body + presence * 0.35
        if body_energy < CONFIG.guitar_body_threshold:
            return 0.0
        if spread > CONFIG.guitar_max_spread or air > CONFIG.guitar_air_reject:
            return 0.0

        harmonic_score = smoothstep(CONFIG.guitar_harmonicity_threshold, 0.52, harmonicity)
        tonal_score = smoothstep(CONFIG.guitar_note_confidence_threshold, 0.28, note_confidence)
        body_score = smoothstep(CONFIG.guitar_body_threshold, 0.24, body_energy)
        clarity_score = 1.0 - smoothstep(0.58, CONFIG.guitar_max_spread, spread)
        transient_score = 1.0 - smoothstep(0.72, 1.0, flux)
        air_penalty = 1.0 - smoothstep(0.42, CONFIG.guitar_air_reject, air)
        score = harmonic_score * 0.38 + tonal_score * 0.27 + body_score * 0.22 + clarity_score * 0.08 + transient_score * 0.05
        return clamp(activity * score * max(0.25, air_penalty))

    def _sound_class(
        self,
        is_guitar: bool,
        guitar_confidence: float,
        activity: float,
        bass: float,
        mid: float,
        treble: float,
        string_low: float,
        body: float,
        presence: float,
        air: float,
        spread: float,
        flux: float,
        note_confidence: float,
        harmonicity: float,
        centroid: float,
        distortion_amount: float,
        noise_amount: float,
    ) -> tuple[str, float, dict[str, float]]:
        empty_weights = {
            "bass": 0.0,
            "percussive": 0.0,
            "bright": 0.0,
            "vocal": 0.0,
            "tonal": 0.0,
            "ambient": 0.0,
        }
        if activity < 0.02:
            return "silence", 0.0, empty_weights

        low_mass = clamp(bass * 0.55 + string_low * 0.45)
        mid_mass = clamp(body * 0.45 + presence * 0.55)
        high_mass = clamp(treble * 0.35 + air * 0.65)
        total_mass = low_mass + mid_mass + high_mass + 1e-6
        low_ratio = low_mass / total_mass
        mid_ratio = mid_mass / total_mass
        high_ratio = high_mass / total_mass
        tonal = clamp(note_confidence * 0.55 + harmonicity * 0.45)
        transient = clamp(flux * 0.8 + spread * 0.35)

        scores = {
            "bass": (low_mass * 0.42 + low_ratio * 0.58) * (0.72 + activity * 0.28) * (1.0 - high_ratio * 0.28),
            "percussive": (transient * 0.55 + smoothstep(0.035, 0.18, flux) * 0.45) * (0.55 + activity * 0.45) * (1.0 - tonal * 0.25),
            "bright": (high_mass * 0.45 + high_ratio * 0.55) * (0.48 + spread * 0.38 + centroid * 0.14),
            "vocal": (mid_mass * 0.42 + mid_ratio * 0.58) * (0.42 + tonal * 0.34 + activity * 0.24) * (1.0 - low_ratio * 0.16),
            "tonal": tonal * (0.55 + mid_mass * 0.35 + body * 0.10),
            "ambient": clamp((spread * 0.38 + mid_ratio * 0.28 + high_ratio * 0.22) * (1.0 - flux * 0.28)),
        }
        if is_guitar:
            scores["tonal"] = max(scores["tonal"], guitar_confidence * 0.92)

        powered = {name: max(0.0, value) ** 1.35 for name, value in scores.items()}
        total = sum(powered.values()) + 1e-6
        weights = {name: clamp(value / total) for name, value in powered.items()}
        sound_class = max(scores, key=scores.get)
        if is_guitar and guitar_confidence > 0.42 and weights["tonal"] > max(weights["bass"], weights["percussive"]) * 1.18:
            sound_class = "guitar"
        if distortion_amount > 0.22 and distortion_amount > noise_amount * 1.25:
            sound_class = "distortion"
        if noise_amount > 0.24 and noise_amount > distortion_amount * 1.15:
            sound_class = "noise"
        if sound_class == "guitar":
            confidence = guitar_confidence
        elif sound_class == "distortion":
            confidence = distortion_amount
        elif sound_class == "noise":
            confidence = noise_amount
        else:
            confidence = scores[sound_class]
        confidence = clamp(confidence)
        if confidence < 0.08:
            return "texture", confidence, weights
        return sound_class, confidence, weights

    def _spectral_flatness(self, spectrum: np.ndarray) -> float:
        useful = spectrum[(self.freqs >= 80) & (self.freqs <= 12000)]
        if useful.size == 0:
            return 0.0
        useful = np.maximum(useful.astype(np.float32), 1e-7)
        geometric = float(np.exp(np.mean(np.log(useful))))
        arithmetic = float(np.mean(useful) + 1e-7)
        return clamp(geometric / arithmetic)

    def _distortion_amount(
        self,
        activity: float,
        string_low: float,
        body: float,
        presence: float,
        air: float,
        spread: float,
        flux: float,
        note_confidence: float,
        harmonicity: float,
        flatness: float,
    ) -> float:
        harmonic_body = clamp(string_low * 0.22 + body * 0.42 + presence * 0.42 + air * 0.18)
        roughness = clamp(spread * 0.44 + flux * 0.34 + presence * 0.26 + air * 0.18)
        tonal_anchor = clamp(note_confidence * 0.45 + harmonicity * 0.35 + body * 0.20)
        noise_reject = 1.0 - smoothstep(0.42, 0.86, flatness)
        raw = activity * (harmonic_body * 0.42 + roughness * 0.38 + tonal_anchor * 0.20) * noise_reject
        return smoothstep(0.055, 0.42, raw)

    def _noise_amount(
        self,
        activity: float,
        spread: float,
        flux: float,
        note_confidence: float,
        harmonicity: float,
        flatness: float,
    ) -> float:
        tonal_reject = 1.0 - smoothstep(0.06, 0.34, note_confidence * 0.55 + harmonicity * 0.45)
        broad_band = smoothstep(0.20, 0.78, spread) * 0.46 + smoothstep(0.20, 0.72, flatness) * 0.54
        motion = 0.70 + smoothstep(0.06, 0.42, flux) * 0.30
        return smoothstep(0.075, 0.62, activity * broad_band * tonal_reject * motion)

    def _sound_diversity(self, weights: dict[str, float]) -> float:
        active = [max(0.0, value) for value in weights.values()]
        total = sum(active) + 1e-6
        normalized = [value / total for value in active if value > 1e-5]
        if len(normalized) <= 1:
            return 0.0
        entropy = -sum(value * np.log(value) for value in normalized)
        return clamp(float(entropy / np.log(len(active))))

    def _audio_richness(self, visual_intensity: float, body: float, presence: float, air: float, spread: float, flux: float) -> float:
        harmonic_mass = clamp(body * 0.55 + presence * 0.32 + air * 0.18)
        motion = clamp(flux * 0.75 + spread * 0.45)
        texture = clamp(harmonic_mass * 0.55 + motion * 0.20)
        raw = visual_intensity * (0.62 + texture * 0.38)
        return smoothstep(0.28, 0.94, raw)

    def _spectral_spread(self, spectrum: np.ndarray, centroid: float) -> float:
        total = float(np.sum(spectrum) + 1e-6)
        centroid_hz = centroid * (self.sample_rate * 0.5)
        variance = float(np.sum(((self.freqs - centroid_hz) ** 2) * spectrum) / total)
        return clamp((variance ** 0.5) / (self.sample_rate * 0.5))

    def _detect_beat(self, bass: float, flux: float) -> bool:
        now = time.perf_counter()
        self.energy_history.append(bass)
        self.energy_history = self.energy_history[-43:]
        avg = float(np.mean(self.energy_history))
        variance = float(np.var(self.energy_history))
        threshold = avg * (1.35 + variance * 2.0) + 0.08
        is_beat = bass > threshold and flux > 0.08 and now - self.last_beat_time > CONFIG.beat_cooldown
        if is_beat:
            self.last_beat_time = now
        return is_beat

    def _smooth(self, raw: AudioFeatures, dt: float = 0.0167) -> None:
        s = clamp(CONFIG.audio_smoothing ** (60.0 * dt), 0.001, 0.999)
        self.features.rms = self.features.rms * s + raw.rms * (1.0 - s)
        self.features.raw_input_level = self.features.raw_input_level * s + raw.raw_input_level * (1.0 - s)
        self.features.audio_received = raw.audio_received
        self.features.bass = self.features.bass * s + raw.bass * (1.0 - s)
        self.features.mid = self.features.mid * s + raw.mid * (1.0 - s)
        self.features.treble = self.features.treble * s + raw.treble * (1.0 - s)
        self.features.string_low = self.features.string_low * s + raw.string_low * (1.0 - s)
        self.features.body = self.features.body * s + raw.body * (1.0 - s)
        self.features.presence = self.features.presence * s + raw.presence * (1.0 - s)
        self.features.air = self.features.air * s + raw.air * (1.0 - s)
        self.features.dominant_freq = self.features.dominant_freq * s + raw.dominant_freq * (1.0 - s)
        self.features.pitch_freq = self.features.pitch_freq * s + raw.pitch_freq * (1.0 - s)
        if raw.is_guitar or raw.sound_class in {"tonal", "vocal"}:
            self.features.pitch_class = raw.pitch_class
            self.features.note_name = raw.note_name
        else:
            self.features.pitch_class = -1
            self.features.note_name = "--"
            self.features.pitch_freq = 0.0
        self.features.note_confidence = self.features.note_confidence * s + raw.note_confidence * (1.0 - s)
        self.features.harmonicity = self.features.harmonicity * s + raw.harmonicity * (1.0 - s)
        self.features.guitar_confidence = self.features.guitar_confidence * s + raw.guitar_confidence * (1.0 - s)
        self.features.is_guitar = raw.is_guitar
        self.features.sound_class = raw.sound_class
        self.features.class_confidence = self.features.class_confidence * s + raw.class_confidence * (1.0 - s)
        
        shape_smoothing = clamp(0.88 ** (60.0 * dt), 0.001, 0.999)
        self.features.shape_bass = self.features.shape_bass * shape_smoothing + raw.shape_bass * (1.0 - shape_smoothing)
        self.features.shape_percussive = self.features.shape_percussive * shape_smoothing + raw.shape_percussive * (1.0 - shape_smoothing)
        self.features.shape_bright = self.features.shape_bright * shape_smoothing + raw.shape_bright * (1.0 - shape_smoothing)
        self.features.shape_vocal = self.features.shape_vocal * shape_smoothing + raw.shape_vocal * (1.0 - shape_smoothing)
        self.features.shape_tonal = self.features.shape_tonal * shape_smoothing + raw.shape_tonal * (1.0 - shape_smoothing)
        self.features.shape_ambient = self.features.shape_ambient * shape_smoothing + raw.shape_ambient * (1.0 - shape_smoothing)
        self.features.sound_diversity = self.features.sound_diversity * shape_smoothing + raw.sound_diversity * (1.0 - shape_smoothing)
        
        distortion_smoothing = clamp(0.88 ** (60.0 * dt), 0.001, 0.999)
        self.features.distortion_amount = self.features.distortion_amount * distortion_smoothing + raw.distortion_amount * (1.0 - distortion_smoothing)
        
        noise_smoothing = clamp(0.90 ** (60.0 * dt), 0.001, 0.999)
        self.features.noise_amount = self.features.noise_amount * noise_smoothing + raw.noise_amount * (1.0 - noise_smoothing)
        
        self.features.spectral_spread = self.features.spectral_spread * s + raw.spectral_spread * (1.0 - s)
        self.features.richness = self.features.richness * s + raw.richness * (1.0 - s)
        self.features.visual_intensity = self.features.visual_intensity * s + raw.visual_intensity * (1.0 - s)
        
        target_envelope = raw.visual_intensity if (raw.is_guitar or not self.guitar_only) else 0.0
        envelope_factor = CONFIG.visual_envelope_attack if target_envelope > self.visual_envelope else CONFIG.visual_envelope_release
        envelope_smoothing = clamp(envelope_factor ** (60.0 * dt), 0.001, 0.999)
        self.visual_envelope = self.visual_envelope * envelope_smoothing + target_envelope * (1.0 - envelope_smoothing)
        self.features.visual_envelope = self.visual_envelope
        
        activity_factor = CONFIG.visual_attack if raw.activity > self.features.activity else CONFIG.visual_release
        activity_smoothing = clamp(activity_factor ** (60.0 * dt), 0.001, 0.999)
        self.features.activity = self.features.activity * activity_smoothing + raw.activity * (1.0 - activity_smoothing)
        
        self.features.spectral_flux = self.features.spectral_flux * s + raw.spectral_flux * (1.0 - s)
        self.features.centroid = self.features.centroid * s + raw.centroid * (1.0 - s)
        
        panning_s = clamp(0.82 ** (60.0 * dt), 0.001, 0.999)
        self.features.panning = self.features.panning * panning_s + raw.panning * (1.0 - panning_s)
        
        self.features.beat = raw.beat
        self.features.spectrum = raw.spectrum

    def _silence_features(self, dt: float = 0.0167) -> AudioFeatures:
        self._smooth(AudioFeatures(), dt)
        self.features.beat = False
        self.features.is_guitar = False
        self.features.audio_received = False
        envelope_s_dt = clamp(CONFIG.visual_envelope_release ** (60.0 * dt), 0.001, 0.999)
        self.visual_envelope *= envelope_s_dt
        self.features.visual_envelope = self.visual_envelope
        self.guitar_frame_count = 0
        return self.features
