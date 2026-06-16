"""Entry point for Synthesia Audio Reactive Simulator."""

from __future__ import annotations

from audio_engine import AudioEngine
from visual_engine import VisualEngine


def main() -> None:
    audio = AudioEngine()
    visual = VisualEngine()
    audio.start()

    try:
        while visual.running:
            dt = visual.tick()
            visual.handle_events()
            if visual.requested_capture_preset is not None:
                audio.apply_capture_preset(visual.requested_capture_preset)
                visual.requested_capture_preset = None
            if visual.requested_audio_source is not None:
                audio.set_source(visual.requested_audio_source)
                visual.requested_audio_source = None
            if visual.toggle_guitar_only_requested:
                audio.toggle_guitar_only()
                visual.toggle_guitar_only_requested = False
            features = audio.update(dt)
            visual.update_and_draw(dt, features, audio.audio_source, audio.guitar_only)
    finally:
        audio.stop()
        visual.shutdown()


if __name__ == "__main__":
    main()
