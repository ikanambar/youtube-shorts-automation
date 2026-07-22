# 🎬 YouTube Shorts Automation

Sistem web otomatis untuk membuat dan mengupload video YouTube Shorts dengan AI. **100% gratis** menggunakan tools open-source dan free-tier API.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Fitur

- 🤖 **Auto Script Generator** - Generate script viral untuk 8+ niche (motivasi, fakta, tech, kesehatan, keuangan, dll)
- 🎙️ **AI Voiceover Gratis** - Text-to-Speech berkualitas tinggi via Microsoft Edge TTS (Indonesia & English)
- 🎞️ **Video Creator Engine** - Otomatis gabungkan stock footage + voiceover + subtitle animasi + Ken Burns effect
- 📤 **Auto Upload YouTube** - Upload langsung ke channel via YouTube Data API v3
- 📅 **Scheduler** - Jadwalkan pembuatan & upload otomatis (harian, mingguan, custom)
- 📊 **Dashboard Analytics** - Pantau performa video dan aktivitas

## 💰 Biaya

| Komponen | Layanan | Biaya |
|----------|---------|-------|
| Voiceover AI | Microsoft Edge TTS | **GRATIS** (tanpa API key) |
| Stock Video/Gambar | Pexels + Pixabay | **GRATIS** (free API key) |
| Upload YouTube | YouTube Data API v3 | **GRATIS** (quota harian) |
| Script Generator | Template built-in | **GRATIS** |
| Hosting | Railway/Render free tier | **GRATIS** |

> Opsional: OpenAI API untuk script AI yang lebih dinamis (berbayar, tapi tidak wajib)

## 🚀 Instalasi

### 1. Prasyarat
- Python 3.9+
- FFmpeg (untuk video processing)

```bash
# Install FFmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg
# macOS:
brew install ffmpeg
# Windows: download dari https://ffmpeg.org
```

### 2. Clone & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### 3. Konfigurasi API Keys (Gratis)

Edit file `.env`:

#### Pexels API (Gratis)
1. Daftar di https://www.pexels.com/api/
2. Copy API key ke `PEXELS_API_KEY`

#### Pixabay API (Gratis)
1. Daftar di https://pixabay.com/api/docs/
2. Copy API key ke `PIXABAY_API_KEY`

#### YouTube Data API v3 (Gratis)
1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru
3. Aktifkan **YouTube Data API v3**
4. Buat **OAuth 2.0 Client ID** (tipe: Web application)
5. Tambahkan redirect URI: `http://localhost:5000/youtube/callback`
6. Copy Client ID & Secret ke `.env`

### 4. Jalankan

```bash
python run.py
```

Buka http://localhost:5000

## 📖 Cara Pakai

1. **Daftar/Login** ke aplikasi
2. **Hubungkan YouTube** di menu YouTube Settings
3. **Buat Video**:
   - Pilih niche → Generate Script otomatis → Buat Video
4. **Auto-Upload**: Klik "Upload ke YouTube" atau aktifkan di scheduler
5. **Otomatisasi Penuh**: Buat Jadwal → sistem generate & upload video otomatis!

## 🏗️ Arsitektur

```
youtube-shorts-automation/
├── run.py                  # Entry point
├── config/
│   └── settings.py         # Konfigurasi aplikasi
├── database/
│   └── models.py           # Model database (User, Video, Schedule)
├── modules/
│   ├── content_generator.py   # Generate script & konten
│   ├── tts_engine.py          # Text-to-Speech (Edge TTS)
│   ├── media_fetcher.py       # Fetch stock media (Pexels/Pixabay)
│   ├── video_engine.py        # Compositing video
│   ├── youtube_uploader.py    # Upload ke YouTube
│   └── scheduler.py           # Automasi terjadwal
└── app/
    ├── routes/             # Flask routes
    ├── templates/          # HTML templates
    └── static/             # CSS, JS, assets
```

## ⚙️ Teknologi

- **Backend**: Flask, SQLAlchemy, APScheduler
- **Video**: MoviePy, Pillow, NumPy
- **TTS**: edge-tts (Microsoft Edge Text-to-Speech)
- **APIs**: YouTube Data API v3, Pexels, Pixabay
- **Frontend**: Bootstrap 5.3, vanilla JS

## ⚠️ Catatan Penting

- **YouTube Quota**: API upload memiliki quota harian (~6 upload/hari default). Bisa request penambahan quota di Google Cloud Console.
- **Copyright**: Semua stock media dari Pexels/Pixabay bebas royalti untuk penggunaan komersial.
- **Konten**: Selalu review konten yang dihasilkan sebelum upload untuk memastikan kualitas.

## 📝 Lisensi

MIT License - Bebas digunakan dan dimodifikasi.
