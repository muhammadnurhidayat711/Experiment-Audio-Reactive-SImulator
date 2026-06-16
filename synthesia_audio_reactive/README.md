# Synthesia Audio Reactive Simulator

Synthesia Audio Reactive Simulator adalah visualizer audio-reactive real-time berbasis Python. Project ini memakai microphone input, FFT analysis, RMS volume, bass/mid/treble bands, spectral flux, centroid, beat detection, Perlin noise flow field, 5000+ particles, glow, shockwave, neural lines, spiral galaxy, dan beberapa mode visual abstrak.

Visualnya dirancang sebagai generative digital art, bukan spectrum bar biasa.
Gaya visual default memakai warna dinamis audio-reactive dengan animasi morph yang cair antar bentuk suara.

## Fitur

- Realtime microphone input dengan `sounddevice`
- FFT spectrum dan RMS volume
- Analisis bass, mid, treble
- Beat detection berbasis bass energy dan spectral flux
- Spectral flux dan frequency centroid
- Audio smoothing
- Visual activity gate: partikel dan objek muncul hanya ketika mic menangkap suara
- Pitch-aware guitar mapping: setiap note class gitar menghasilkan bentuk dan gerak partikel berbeda
- Cosmic background dan motion trails
- Flow field berbasis Perlin Noise
- 7000 particles default
- Neural connection lines
- Energy orb di tengah layar
- Shockwave saat beat terdeteksi
- Spiral galaxy effect
- Glow effect dan additive blending
- Color shifting berdasarkan frekuensi
- Distortion warp halus pada dot, trail, koneksi, dan garis note
- Richness response: visual makin padat saat suara gitar makin ramai/kompleks
- Fullscreen support

## Guitar Shape Mapping

Simulator membaca pitch dominan gitar dengan pendekatan chroma, jadi harmonik gitar ikut dihitung ke note class seperti C, C#, D, E, F, G, A, dan B. Setiap note class memilih keluarga bentuk natural dan variasi parameter yang berbeda:

- Leaf
- Wave
- Branch
- Stem
- Petal
- Seed

HUD akan menampilkan signature yang sedang terbaca, misalnya `A WIDE WAVE`, `C# SOFT WAVE`, atau `G TALL LEAF`, beserta pitch frequency dan confidence. Partikel juga berubah gerak berdasarkan note class, sehingga tangga nada yang berbeda terasa lebih berbeda secara visual.

## Mode Visual

1. Particle Galaxy
2. Neural Universe
3. Audio Nebula
4. Energy Tentacles
5. Fractal Reactor

## Kontrol

- `ESC` = Exit
- `F` = Toggle fullscreen
- `SPACE` = Reset particles
- `TAB` = Next mode
- `1-5` = Select mode
- `L` = Toggle neural lines
- `B` = Toggle shockwave
- `P` = Pause
- `M` = Mic only: menangkap semua suara dari microphone
- `O` = Screen only: menangkap suara layar/system audio saja
- `G` = Guitar only: menangkap gitar dari microphone dengan filter gitar aktif
- `C` = Cycle capture preset: mic only -> screen only -> guitar only

## Instalasi

Pastikan Python 3.10+ sudah terpasang.

```bash
cd synthesia_audio_reactive
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Pada macOS/Linux:

```bash
cd synthesia_audio_reactive
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Catatan Audio

Jika microphone tidak tersedia atau izin microphone belum diberikan, visual akan diam dan menunggu input suara mic. Untuk input real-time, pastikan:

- Microphone aktif di sistem operasi
- Aplikasi terminal/Python memiliki izin microphone
- Driver audio berjalan normal

Jika visual terlalu sensitif atau kurang sensitif terhadap mic, ubah `silence_threshold` di `config.py`. Nilai lebih kecil membuat visual lebih mudah muncul, nilai lebih besar membuat visual hanya muncul pada suara yang lebih keras. Default saat ini dibuat cukup sensitif untuk gitar akustik/mic ruangan.

Visual juga memiliki guitar clarity gate. Jika suara keras tetapi bukan gitar atau nadanya tidak jelas, visual akan tetap diam. Atur ini di `config.py`:

```python
guitar_confidence_threshold = 0.10
guitar_note_confidence_threshold = 0.035
guitar_harmonicity_threshold = 0.18
guitar_required_frames = 1
guitar_body_threshold = 0.012
guitar_max_spread = 0.92
guitar_air_reject = 0.88
guitar_min_frequency = 70.0
guitar_max_frequency = 1400.0
```

Naikkan `guitar_confidence_threshold` agar hanya gitar yang sangat jelas memicu visual. Turunkan sedikit jika gitar terlalu sering diabaikan. `HARM` di HUD menunjukkan seberapa jelas getaran nada/time-domain pitch terdeteksi.

Jika status HUD menampilkan `NO AUDIO BUFFER` atau `INPUT TOO LOW`, cek device input:

```bash
python list_audio_devices.py
```

Lalu set index device di `config.py`:

```python
input_device = 1
mic_gain = 95.0
```

Naikkan `mic_gain` jika `RAW` bergerak tetapi `ACT` tetap kecil. Untuk mic yang jauh dari gitar, coba `mic_gain = 110.0`.

## Menangkap Suara Sistem/Layar

Di Windows, tekan `O` untuk screen only. Mode ini hanya boleh menangkap suara layar/system audio, bukan mic. Jika system loopback tidak tersedia di build `sounddevice`/PortAudio yang sedang dipakai, HUD akan menampilkan `NO AUDIO BUFFER`.

Lihat daftar device:

```bash
python list_audio_devices.py
```

Default lewat config:

```python
audio_source = "system_audio"
guitar_only = False
output_device = None
```

`output_device = None` memakai output default Windows. Jika ingin memilih device tertentu, isi dengan index output dari `list_audio_devices.py`.

Untuk kembali ke mic only:

```python
audio_source = "microphone"
guitar_only = False
```

Jika ingin guitar only dari mic:

```python
audio_source = "microphone"
guitar_only = True
```

Jika `O` tetap `NO AUDIO BUFFER`, gunakan salah satu solusi berikut:

- Aktifkan `Stereo Mix` di Windows Recording Devices jika driver menyediakan.
- Pakai virtual audio cable seperti VB-Cable, lalu pilih device itu sebagai `input_device`.
- Putar musik ke output yang sama dengan `output_device` yang dipilih.

## Performa

Default target adalah 1920x1080 pada 60 FPS dengan 7000 particles. Jika perangkat kurang kuat, ubah nilai berikut di `config.py`:

```python
particle_count = 5000
trail_alpha = 32
max_lines = 250
```

Nilai `particle_count` lebih tinggi akan membuat visual lebih padat, tetapi lebih berat karena Pygame menggambar partikel satu per satu.

## Struktur

```text
synthesia_audio_reactive/
|-- main.py
|-- config.py
|-- audio_engine.py
|-- visual_engine.py
|-- particle_system.py
|-- effects.py
|-- utils.py
|-- noise.py
|-- requirements.txt
`-- README.md
```

## Troubleshooting

Jika instalasi `sounddevice` bermasalah, install PortAudio sesuai sistem operasi Anda. Di Windows biasanya wheel PyPI sudah cukup. Di Linux, Anda mungkin perlu:

```bash
sudo apt install portaudio19-dev
```

Jika FPS rendah, matikan line rendering dengan tombol `L`, kurangi `particle_count`, atau jalankan dalam resolusi lebih kecil dengan mengubah `width` dan `height` di `config.py`.

Distorsi visual bisa diatur di `config.py`:

```python
distortion_strength = 18.0
distortion_frequency = 0.012
distortion_speed = 1.15
richness_line_boost = 90
richness_particle_size = 0.45
richness_distortion_boost = 0.7
visual_min_raw_level = 0.018
visual_full_raw_level = 0.20
visual_envelope_attack = 0.22
visual_envelope_release = 0.86
min_particle_visibility = 0.003
particle_visibility_attack = 0.38
particle_visibility_full = 0.92
```

Jika memakai Python 3.14 di Windows, dependency memakai `pygame-ce` karena paket ini menyediakan kompatibilitas lebih baru tetapi tetap digunakan lewat `import pygame`. Perlin noise disediakan oleh modul lokal `noise.py`, sehingga tidak perlu build package `noise` dengan Visual C++ Build Tools.
