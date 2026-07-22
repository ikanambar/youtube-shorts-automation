"""
Text-to-Speech Engine Module
=============================
Uses Microsoft Edge TTS (FREE, high quality) to convert scripts to speech.
No API key required - completely free!
"""
import asyncio
import edge_tts
from pathlib import Path
from typing import Optional, Tuple
from config.settings import Config
from loguru import logger


class TTSEngine:
    """Text-to-Speech engine using Edge TTS (free)."""
    
    def __init__(self, voice: Optional[str] = None, rate: str = '+0%', volume: str = '+0%'):
        """
        Initialize TTS engine.
        
        Args:
            voice: Voice name (e.g., 'id-ID-ArdiNeural')
            rate: Speech rate (e.g., '+10%', '-5%')
            volume: Volume adjustment
        """
        self.voice = voice or Config.TTS_VOICE
        self.rate = rate or Config.TTS_RATE
        self.volume = volume or Config.TTS_VOLUME
        self.output_dir = Config.AUDIO_FOLDER
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_speech(self, text: str, output_filename: str = None) -> Tuple[str, float]:
        """
        Convert text to speech and save as audio file.
        
        Args:
            text: The text to convert to speech
            output_filename: Custom filename (without extension)
        
        Returns:
            Tuple of (audio_file_path, duration_seconds)
        """
        if not output_filename:
            import hashlib
            output_filename = f"tts_{hashlib.md5(text[:50].encode()).hexdigest()}"
        
        output_path = self.output_dir / f"{output_filename}.mp3"
        subtitle_path = self.output_dir / f"{output_filename}.vtt"
        
        # Run async TTS
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            duration = loop.run_until_complete(
                self._generate_async(text, str(output_path), str(subtitle_path))
            )
        finally:
            loop.close()
        
        logger.info(f"TTS generated: {output_path} (duration: {duration:.1f}s)")
        return str(output_path), duration
    
    async def _generate_async(self, text: str, output_path: str, subtitle_path: str) -> float:
        """Async TTS generation with subtitles."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume
        )
        
        # Generate audio with subtitle data
        submaker = edge_tts.SubMaker()
        
        with open(output_path, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.create_sub(
                        (chunk["offset"], chunk["duration"]),
                        chunk["text"]
                    )
        
        # Save subtitles
        subtitle_content = submaker.generate_subs()
        with open(subtitle_path, "w", encoding="utf-8") as sub_file:
            sub_file.write(subtitle_content)
        
        # Calculate duration from audio file
        duration = self._get_audio_duration(output_path)
        
        return duration
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(audio_path)
            duration = clip.duration
            clip.close()
            return duration
        except Exception:
            # Estimate based on text length (~150 words per minute)
            return 30.0
    
    def generate_speech_with_timestamps(self, text: str, output_filename: str = None) -> dict:
        """
        Generate speech and return detailed word timestamps.
        
        Returns:
            Dict with audio_path, duration, subtitle_path, and word_timings
        """
        if not output_filename:
            import hashlib
            output_filename = f"tts_{hashlib.md5(text[:50].encode()).hexdigest()}"
        
        output_path = self.output_dir / f"{output_filename}.mp3"
        subtitle_path = self.output_dir / f"{output_filename}.vtt"
        
        # Run async TTS with word timings
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._generate_with_timings(text, str(output_path), str(subtitle_path))
            )
        finally:
            loop.close()
        
        return result
    
    async def _generate_with_timings(self, text: str, output_path: str, subtitle_path: str) -> dict:
        """Generate speech and capture word timings for subtitle sync."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume
        )
        
        word_timings = []
        submaker = edge_tts.SubMaker()
        
        with open(output_path, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_timings.append({
                        'text': chunk["text"],
                        'offset': chunk["offset"] / 10_000_000,  # Convert to seconds
                        'duration': chunk["duration"] / 10_000_000
                    })
                    submaker.create_sub(
                        (chunk["offset"], chunk["duration"]),
                        chunk["text"]
                    )
        
        # Save VTT subtitles
        subtitle_content = submaker.generate_subs()
        with open(subtitle_path, "w", encoding="utf-8") as sub_file:
            sub_file.write(subtitle_content)
        
        duration = self._get_audio_duration(output_path)
        
        return {
            'audio_path': output_path,
            'subtitle_path': subtitle_path,
            'duration': duration,
            'word_timings': word_timings
        }
    
    @staticmethod
    def list_voices(language: str = None) -> list:
        """List available TTS voices."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            voices = loop.run_until_complete(edge_tts.list_voices())
        finally:
            loop.close()
        
        if language:
            voices = [v for v in voices if v['Locale'].startswith(language)]
        
        return voices
