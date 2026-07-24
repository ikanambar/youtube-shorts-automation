"""TTS Engine using Google TTS (gTTS) - FREE and stable."""
import os
from pathlib import Path
from typing import Optional, Tuple
from gtts import gTTS
from config.settings import Config
from loguru import logger


class TTSEngine:
    VOICE_MAP = {
        'id-ID-ArdiNeural': 'id',
        'id-ID-GadisNeural': 'id',
        'en-US-ChristopherNeural': 'en',
        'en-US-JennyNeural': 'en',
        'en-US-GuyNeural': 'en',
        'en-GB-SoniaNeural': 'en',
        'ja-JP-KeitaNeural': 'ja',
        'ko-KR-InJoonNeural': 'ko',
    }

    def __init__(self, voice=None, rate='+0%', volume='+0%'):
        self.voice = voice or Config.TTS_VOICE
        self.rate = rate or Config.TTS_RATE
        self.volume = volume or Config.TTS_VOLUME
        self.lang = self.VOICE_MAP.get(self.voice, 'id')
        self.output_dir = Config.AUDIO_FOLDER
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_speech(self, text, output_filename=None):
        if not output_filename:
            import hashlib
            output_filename = "tts_" + hashlib.md5(text[:50].encode()).hexdigest()
        output_path = self.output_dir / (output_filename + ".mp3")
        subtitle_path = self.output_dir / (output_filename + ".vtt")
        tts = gTTS(text=text, lang=self.lang, slow=False)
        tts.save(str(output_path))
        duration = self._get_audio_duration(str(output_path))
        self._generate_subtitles(text, duration, str(subtitle_path))
        logger.info("TTS generated: {} (duration: {:.1f}s)".format(output_path, duration))
        return str(output_path), duration

    def generate_speech_with_timestamps(self, text, output_filename=None):
        if not output_filename:
            import hashlib
            output_filename = "tts_" + hashlib.md5(text[:50].encode()).hexdigest()
        output_path = self.output_dir / (output_filename + ".mp3")
        subtitle_path = self.output_dir / (output_filename + ".vtt")
        tts = gTTS(text=text, lang=self.lang, slow=False)
        tts.save(str(output_path))
        duration = self._get_audio_duration(str(output_path))
        words = text.split()
        word_duration = duration / len(words) if words else 0
        word_timings = []
        for i, word in enumerate(words):
            word_timings.append({
                'text': word,
                'offset': i * word_duration,
                'duration': word_duration
            })
        self._generate_subtitles(text, duration, str(subtitle_path))
        return {
            'audio_path': str(output_path),
            'subtitle_path': str(subtitle_path),
            'duration': duration,
            'word_timings': word_timings
        }

    def _get_audio_duration(self, audio_path):
        try:
            from moviepy import AudioFileClip
            clip = AudioFileClip(audio_path)
            duration = clip.duration
            clip.close()
            return duration
        except Exception:
            return 30.0

    def _generate_subtitles(self, text, duration, subtitle_path):
        temp = text
        for sep in ['. ', '! ', '? ']:
            temp = temp.replace(sep, sep[0] + '|')
        parts = temp.split('|')
        sentences = [s.strip() for s in parts if s.strip()]
        time_per = duration / len(sentences) if sentences else duration
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for i, sent in enumerate(sentences):
                start = i * time_per
                end = (i + 1) * time_per
                f.write(self._fmt(start) + " --> " + self._fmt(end) + "\n")
                f.write(sent + "\n\n")

    def _fmt(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return "{:02d}:{:02d}:{:02d}.{:03d}".format(h, m, s, ms)

    @staticmethod
    def list_voices(language=None):
        voices = [
            {'ShortName': 'id-ID-ArdiNeural', 'Locale': 'id-ID', 'Gender': 'Male'},
            {'ShortName': 'id-ID-GadisNeural', 'Locale': 'id-ID', 'Gender': 'Female'},
            {'ShortName': 'en-US-ChristopherNeural', 'Locale': 'en-US', 'Gender': 'Male'},
            {'ShortName': 'en-US-JennyNeural', 'Locale': 'en-US', 'Gender': 'Female'},
            {'ShortName': 'en-US-GuyNeural', 'Locale': 'en-US', 'Gender': 'Male'},
            {'ShortName': 'en-GB-SoniaNeural', 'Locale': 'en-GB', 'Gender': 'Female'},
            {'ShortName': 'ja-JP-KeitaNeural', 'Locale': 'ja-JP', 'Gender': 'Male'},
            {'ShortName': 'ko-KR-InJoonNeural', 'Locale': 'ko-KR', 'Gender': 'Male'},
        ]
        if language:
            voices = [v for v in voices if v['Locale'].startswith(language)]
        return voices
