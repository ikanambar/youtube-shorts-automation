"""
Internet Video Fetcher
======================
Searches and downloads REAL video clips from across the internet (YouTube)
using yt-dlp, matching the custom prompt + narration per scene.

This gives access to a HUGE variety of footage - far beyond stock libraries:
- Real human videos
- Movie / film clips
- Real events and moments
- Anime clips
- Documentaries, sports, nature, etc.

The custom prompt is the primary driver: video is built around what you type.

------------------------------------------------------------------------
COPYRIGHT NOTICE
------------------------------------------------------------------------
Clips downloaded from the internet may be copyrighted. Publishing them
(e.g. on YouTube Shorts) can trigger copyright claims or strikes. Use clips
you have the right to use, keep them short/transformative, and take
responsibility for what you upload.
------------------------------------------------------------------------
"""
import os
import re
import glob
import random
import hashlib
from pathlib import Path
from typing import List, Optional
from config.settings import Config
from loguru import logger

try:
    import yt_dlp
    from yt_dlp.utils import download_range_func
    YT_DLP_AVAILABLE = True
except Exception as _e:  # pragma: no cover
    YT_DLP_AVAILABLE = False


class InternetVideoFetcher:
    """Search + download real video clips from YouTube via yt-dlp."""

    # How many seconds to grab from each source video
    CLIP_SECONDS = 9
    # Search this many candidates per scene
    SEARCH_RESULTS = 10

    def __init__(self):
        self.temp_dir = Config.TEMP_FOLDER
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # Reuse MediaFetcher for text-AI query building + stock fallback
        from modules.media_fetcher import MediaFetcher
        self._media = MediaFetcher()

    # ==========================================================
    # MAIN ENTRY POINT
    # ==========================================================

    def fetch_clips_for_script(
        self,
        script: str,
        custom_prompt: str = '',
        niche: str = 'facts',
        count: int = 5
    ) -> List[str]:
        """
        Fetch real video clips matching each scene of the narration.

        Args:
            script: Full narration text
            custom_prompt: User's theme/subject that drives the visuals
            niche: Content niche (hint for fallback keywords)
            count: Number of clips wanted

        Returns:
            List of local video file paths
        """
        segments = self._media._split_script_into_segments(script, count)
        logger.info(f"Internet video: {len(segments)} scenes | prompt='{custom_prompt[:40]}'")

        if not YT_DLP_AVAILABLE:
            logger.warning("yt-dlp not installed - falling back to stock video")
            return self._media._fetch_smart_stock_videos(segments, niche)

        base_theme = (custom_prompt or '').strip()
        clips: List[str] = []
        used_ids = set()

        for i, seg in enumerate(segments):
            query = self._build_query(seg, base_theme, niche)
            logger.info(f"Scene {i+1} search query: '{query}'")

            clip = self._search_and_download(query, i, used_ids)

            if not clip:
                # Fallback: stock video for this scene
                logger.warning(f"Scene {i+1}: no internet clip, trying stock video")
                kw = self._media._narration_to_keywords(seg, niche)
                clip = self._media._search_one_stock_video(kw, used_ids)

            if clip:
                clips.append(clip)

        # Absolute fallback if nothing worked
        if not clips:
            logger.warning("Internet video found nothing, using stock footage")
            clips = self._media._fetch_smart_stock_videos(segments, niche)

        return clips

    # ==========================================================
    # QUERY BUILDING (prompt + narration -> search query)
    # ==========================================================

    def _build_query(self, segment: str, base_theme: str, niche: str) -> str:
        """Build a concise English YouTube search query for a scene."""
        instruction = (
            "Give a short YouTube video search query (max 6 English words) to find "
            "real footage that visually illustrates this narration"
            + (f", themed around: {base_theme}" if base_theme else "")
            + ". Return ONLY the search query, no quotes, no explanation. "
            "Narration: " + segment
        )
        q = self._media._pollinations_text(instruction)

        if q:
            q = re.sub(r'["\n\r]', ' ', q).strip()
            words = q.split()
            if 0 < len(words) <= 12:
                query = ' '.join(words[:8])
            else:
                query = ' '.join(words[:6])
            return query

        # Fallback: local keyword extraction + theme
        kw = self._media._narration_to_keywords(segment, niche)
        return (base_theme + ' ' + kw).strip() if base_theme else kw

    # ==========================================================
    # SEARCH + DOWNLOAD (yt-dlp)
    # ==========================================================

    def _search_and_download(self, query: str, index: int, used_ids: set) -> Optional[str]:
        """Search YouTube and download a short section of a matching video."""
        stem = f"yt_clip_{index}_{hashlib.md5(query.encode()).hexdigest()[:8]}"

        # Reuse if already downloaded
        existing = glob.glob(str(self.temp_dir / f"{stem}.*"))
        for f in existing:
            if os.path.getsize(f) > 10000 and not f.endswith('.part'):
                return f

        try:
            # 1) Search for candidates (metadata only)
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'noplaylist': True,
                'default_search': 'ytsearch',
                'extract_flat': False,
            }
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{self.SEARCH_RESULTS}:{query}", download=False)

            entries = [e for e in (info.get('entries', []) if info else []) if e]

            # 2) Pick a suitable candidate (reasonable duration, not used yet)
            chosen = self._pick_candidate(entries, used_ids)
            if not chosen:
                return None

            used_ids.add(chosen.get('id'))
            duration = chosen.get('duration') or 60

            # 3) Pick a section (skip intros, avoid the very end)
            start, end = self._pick_section(duration)

            # 4) Download just that section
            out_tmpl = str(self.temp_dir / f"{stem}.%(ext)s")
            dl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                # video-only mp4 preferred (no audio needed, smaller); fallback to best
                'format': 'bv*[height<=1280][ext=mp4]/bv*[ext=mp4]/b[ext=mp4]/b',
                'outtmpl': out_tmpl,
                'download_ranges': download_range_func(None, [(start, end)]),
                'force_keyframes_at_cuts': True,
                'overwrites': True,
                'retries': 2,
                'fragment_retries': 2,
            }
            url = chosen.get('webpage_url') or chosen.get('url') or chosen.get('id')

            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                ydl.download([url])

            # 5) Find the produced file
            produced = glob.glob(str(self.temp_dir / f"{stem}.*"))
            for f in produced:
                if os.path.getsize(f) > 10000 and not f.endswith('.part'):
                    logger.info(f"Downloaded internet clip: {f}")
                    return f

        except Exception as e:
            logger.warning(f"yt-dlp failed for '{query}': {e}")

        return None

    def _pick_candidate(self, entries: list, used_ids: set) -> Optional[dict]:
        """Choose a good candidate video: reasonable length, not already used."""
        # First pass: prefer 20s - 20min videos
        for e in entries:
            vid = e.get('id')
            dur = e.get('duration') or 0
            if vid in used_ids:
                continue
            if dur and (dur < 20 or dur > 1200):
                continue
            return e

        # Second pass: relax duration limits
        for e in entries:
            if e.get('id') not in used_ids:
                return e

        return None

    def _pick_section(self, duration: float) -> tuple:
        """Choose a start/end section within the video."""
        seg = self.CLIP_SECONDS
        if not duration or duration <= seg + 2:
            return (0, min(seg, max(duration or seg, 1)))

        # Skip the first ~15% (intros), leave room before the end
        earliest = max(duration * 0.15, 3)
        latest = max(duration - seg - 1, earliest)
        start = random.uniform(earliest, latest) if latest > earliest else earliest
        return (round(start, 1), round(start + seg, 1))
