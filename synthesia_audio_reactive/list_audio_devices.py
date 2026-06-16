"""List available audio input devices for sounddevice."""

from __future__ import annotations

import sounddevice as sd

try:
    import soundcard as sc
except Exception:
    sc = None


def main() -> None:
    print("Input devices:")
    for index, device in enumerate(sd.query_devices()):
        channels = int(device.get("max_input_channels", 0))
        if channels > 0:
            default_marker = " (default)" if sd.default.device[0] == index else ""
            print(f"{index}: {device['name']} - {channels} channel(s){default_marker}")

    print("\nOutput devices for system_audio loopback:")
    for index, device in enumerate(sd.query_devices()):
        channels = int(device.get("max_output_channels", 0))
        if channels > 0:
            default_marker = " (default)" if sd.default.device[1] == index else ""
            print(f"{index}: {device['name']} - {channels} channel(s){default_marker}")

    print("\nSoundcard loopback devices for screen-only mode:")
    if sc is None:
        print("soundcard is not installed")
    else:
        try:
            default_speaker = sc.default_speaker()
            print(f"default speaker: {default_speaker.name}")
            for index, microphone in enumerate(sc.all_microphones(include_loopback=True)):
                marker = " (selected automatically)" if default_speaker.name.lower() in microphone.name.lower() else ""
                print(f"{index}: {microphone.name}{marker}")
        except Exception as exc:
            print(f"could not list soundcard loopback devices: {exc}")


if __name__ == "__main__":
    main()
