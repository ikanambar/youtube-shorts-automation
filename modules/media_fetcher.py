"""
Media Fetcher Module
====================
Fetches AI-generated images from Pollinations.ai that match narration per-sentence.
Falls back to Pexels/Pixabay stock footage if AI generation fails.

Strategy:
1. Split script into sentences
2. Generate AI image prompts per sentence (cinematic, matching content)
3. Download AI-generated images from Pollinations.ai (FREE, no API key)
4. Fallback: stock footage from Pexels/Pixabay
"""
import os
import re
import random
import hashlib
import time
import httpx
from pathlib import Path
from typing import List, Optional, Dict
from urllib.parse import quote
from config.settings import Config
from loguru import logger


class MediaFetcher:
    """Fetches AI-generated or stock media for video creation."""

    # Pollinations.ai - FREE, no API key needed
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"

    # Visual style suffix for consistent cinematic look
    STYLE_SUFFIX = ", cinematic lighting, high quality, 4k, professional photography, dramatic atmosphere"

    # Niche-specific visual themes
    NICHE_THEMES = {
        'motivational': 'epic sunrise, mountain peak, golden light, inspirational',
        'facts': 'scientific visualization, educational, detailed, stunning',
        'tech': 'futuristic technology, neon glow, digital, modern',
        'nature': 'beautiful nature, national geographic style, vivid colors',
        'history': 'historical painting style, dramatic, ancient, epic',
        'health': 'healthy lifestyle, fitness, wellness, bright clean',
        'finance': 'luxury, business, wealth, professional, modern office',
        'psychology': 'abstract mind, brain visualization, ethereal, thoughtful',
    }

    def __init__(self):
        self.pexels_key = Config.PEXELS_API_KEY
        self.pixabay_key = Config.PIXABAY_API_KEY
        self.temp_dir = Config.TEMP_FOLDER
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def fetch_ai_images_for_script(self, script: str, niche: str = 'facts', count: int = 5) -> List[str]:
        """
        Generate AI images that match the narration per-sentence.

        This is the PRIMARY method - generates images that perfectly match
        what is being narrated in each part of the video.

        Args:
            script: The full narration script
            niche: Content niche for visual style hints
            count: Number of images needed

        Returns:
            List of local file paths to AI-generated images
        """
        # Split script into meaningful segments
        segments = self._split_script_into_segments(script, count)
        logger.info(f"Split script into {len(segments)} segments for AI image generation")

        image_paths = []
        niche_theme = self.NICHE_THEMES.get(niche, 'cinematic, dramatic, professional')

        for i, segment in enumerate(segments):
            try:
                # Create a visual prompt from the narration segment
                visual_prompt = self._create_visual_prompt(segment, niche_theme)
                logger.info(f"Segment {i+1}: '{segment[:50]}...' -> Prompt: '{visual_prompt[:80]}...'")

                # Generate AI image
                path = self._generate_pollinations_image(visual_prompt, i)
                if path:
                    image_paths.append(path)
                else:
                    logger.warning(f"AI generation failed for segment {i+1}, trying fallback")
                    # Fallback: try stock image with extracted keywords
                    keywords = self._extract_keywords(segment)
                    fallback_paths = self._fetch_stock_images(keywords, 1)
                    if fallback_paths:
                        image_paths.extend(fallback_paths)

            except Exception as e:
                logger.warning(f"Failed to generate image for segment {i+1}: {e}")
                continue

        # If we got nothing, final fallback
        if not image_paths:
            logger.warning("All AI generation failed, falling back to stock footage")
            keywords = self._extract_keywords(script)
            image_paths = self._fetch_stock_images(keywords, count)

        return image_paths

    def fetch_videos(self, keywords: str, count: int = 5, orientation: str = 'portrait') -> List[str]:
        """Legacy method - fetch stock videos. Kept for backward compatibility."""
        video_paths = []

        if self.pexels_key:
            try:
                paths = self._fetch_pexels_videos(keywords, count, orientation)
                video_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pexels video fetch failed: {e}")

        if len(video_paths) < count and self.pixabay_key:
            try:
                remaining = count - len(video_paths)
                paths = self._fetch_pixabay_videos(keywords, remaining)
                video_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pixabay video fetch failed: {e}")

        if not video_paths:
            image_paths = self.fetch_images(keywords, count)
            return image_paths

        return video_paths

    def fetch_images(self, keywords: str, count: int = 5) -> List[str]:
        """Legacy method - fetch stock images."""
        return self._fetch_stock_images(keywords, count)

    # ==========================================
    # AI IMAGE GENERATION (Pollinations.ai)
    # ==========================================

    def _generate_pollinations_image(self, prompt: str, index: int) -> Optional[str]:
        """
        Generate an AI image using Pollinations.ai (FREE, no API key).

        Args:
            prompt: Visual description for image generation
            index: Image index for unique filename

        Returns:
            Local file path or None if failed
        """
        # Create unique filename based on prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        file_path = self.temp_dir / f"ai_img_{index}_{prompt_hash}.jpg"

        # Skip if already generated
        if file_path.exists() and file_path.stat().st_size > 1000:
            return str(file_path)

        # Build URL - portrait orientation for YouTube Shorts (1080x1920)
        encoded_prompt = quote(prompt)
        url = self.POLLINATIONS_URL.format(
            prompt=encoded_prompt,
            width=1080,
            height=1920,
            seed=random.randint(1, 999999)
        )

        try:
            logger.info(f"Generating AI image {index+1}...")
            with httpx.Client(timeout=120, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()

                # Verify we got an image (not an error page)
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type or len(response.content) > 10000:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"AI image generated: {file_path} ({len(response.content)} bytes)")
                    return str(file_path)
                else:
                    logger.warning(f"Pollinations returned non-image response")
                    return None

        except Exception as e:
            logger.warning(f"Pollinations image generation failed: {e}")
            return None

    def _split_script_into_segments(self, script: str, target_count: int) -> List[str]:
        """
        Split a script into meaningful segments for image generation.
        Each segment represents a visual scene.
        """
        # Split by sentences
        sentences = re.split(r'[.!?]+', script)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

        if not sentences:
            return [script]

        # If we have more sentences than needed, group them
        if len(sentences) <= target_count:
            return sentences

        # Group sentences into target_count segments
        segments = []
        sentences_per_segment = max(1, len(sentences) // target_count)

        for i in range(0, len(sentences), sentences_per_segment):
            segment = '. '.join(sentences[i:i + sentences_per_segment])
            segments.append(segment)
            if len(segments) >= target_count:
                break

        return segments[:target_count]

    def _create_visual_prompt(self, text_segment: str, niche_theme: str) -> str:
        """
        Convert a narration text segment into a visual prompt for AI image generation.

        Strategy:
        - Extract the key visual concept from the text
        - Add cinematic style modifiers
        - Add niche-specific theme
        """
        # Remove filler words and create visual description
        # Take the core concept from the segment
        clean_text = text_segment.strip()

        # Limit prompt length (Pollinations works best with concise prompts)
        if len(clean_text) > 150:
            clean_text = clean_text[:150]

        # Build the visual prompt
        prompt = f"A stunning visual representation of: {clean_text}. Style: {niche_theme}{self.STYLE_SUFFIX}"

        return prompt

    def _extract_keywords(self, text: str) -> str:
        """Extract search keywords from text for stock footage fallback."""
        # Remove common words
        stop_words = {'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'dengan', 'ini', 'itu',
                      'adalah', 'pada', 'tidak', 'akan', 'juga', 'sudah', 'bisa', 'lebih',
                      'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                      'should', 'may', 'might', 'can', 'shall', 'of', 'in', 'to', 'for',
                      'with', 'on', 'at', 'by', 'from', 'that', 'this', 'it', 'its'}

        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]

        # Take top 5 most likely visual keywords
        return ' '.join(keywords[:5]) if keywords else 'cinematic nature'

    # ==========================================
    # STOCK FOOTAGE FALLBACK (Pexels + Pixabay)
    # ==========================================

    def _fetch_stock_images(self, keywords: str, count: int) -> List[str]:
        """Fetch stock images as fallback."""
        image_paths = []

        if self.pexels_key:
            try:
                paths = self._fetch_pexels_images(keywords, count)
                image_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pexels image fetch failed: {e}")

        if len(image_paths) < count and self.pixabay_key:
            try:
                remaining = count - len(image_paths)
                paths = self._fetch_pixabay_images(keywords, remaining)
                image_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pixabay image fetch failed: {e}")

        return image_paths

    def _fetch_pexels_videos(self, keywords: str, count: int, orientation: str) -> List[str]:
        """Fetch videos from Pexels API."""
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": keywords,
            "per_page": count,
            "orientation": orientation,
            "size": "medium"
        }

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        paths = []
        for video in data.get('videos', [])[:count]:
            video_files = video.get('video_files', [])

            selected = None
            for vf in video_files:
                if vf.get('height', 0) >= 720 and vf.get('width', 0) <= vf.get('height', 0):
                    selected = vf
                    break

            if not selected and video_files:
                selected = video_files[0]

            if selected:
                video_url = selected['link']
                file_path = self.temp_dir / f"pexels_video_{video['id']}.mp4"

                if not file_path.exists():
                    self._download_file(video_url, file_path)

                paths.append(str(file_path))

        return paths

    def _fetch_pexels_images(self, keywords: str, count: int) -> List[str]:
        """Fetch images from Pexels API."""
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": self.pexels_key}
        params = {
            "query": keywords,
            "per_page": count,
            "orientation": "portrait",
            "size": "medium"
        }

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        paths = []
        for photo in data.get('photos', [])[:count]:
            img_url = photo['src'].get('portrait') or photo['src'].get('large')
            file_path = self.temp_dir / f"pexels_img_{photo['id']}.jpg"

            if not file_path.exists():
                self._download_file(img_url, file_path)

            paths.append(str(file_path))

        return paths

    def _fetch_pixabay_videos(self, keywords: str, count: int) -> List[str]:
        """Fetch videos from Pixabay API."""
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": self.pixabay_key,
            "q": keywords,
            "per_page": count,
            "safesearch": "true",
            "video_type": "film"
        }

        with httpx.Client(timeout=30) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        paths = []
        for hit in data.get('hits', [])[:count]:
            videos = hit.get('videos', {})
            medium = videos.get('medium', {})
            video_url = medium.get('url', '')

            if not video_url:
                small = videos.get('small', {})
                video_url = small.get('url', '')

            if video_url:
                file_path = self.temp_dir / f"pixabay_video_{hit['id']}.mp4"

                if not file_path.exists():
                    self._download_file(video_url, file_path)

                paths.append(str(file_path))

        return paths

    def _fetch_pixabay_images(self, keywords: str, count: int) -> List[str]:
        """Fetch images from Pixabay API."""
        url = "https://pixabay.com/api/"
        params = {
            "key": self.pixabay_key,
            "q": keywords,
            "per_page": count,
            "safesearch": "true",
            "image_type": "photo",
            "orientation": "vertical"
        }

        with httpx.Client(timeout=30) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        paths = []
        for hit in data.get('hits', [])[:count]:
            img_url = hit.get('largeImageURL', hit.get('webformatURL'))

            if img_url:
                file_path = self.temp_dir / f"pixabay_img_{hit['id']}.jpg"

                if not file_path.exists():
                    self._download_file(img_url, file_path)

                paths.append(str(file_path))

        return paths

    def _download_file(self, url: str, path: Path) -> None:
        """Download a file from URL to local path."""
        logger.info(f"Downloading: {url}")
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            with open(path, 'wb') as f:
                f.write(response.content)

        logger.info(f"Downloaded to: {path}")

    def cleanup_temp(self) -> None:
        """Remove all temporary files."""
        if self.temp_dir.exists():
            for f in self.temp_dir.iterdir():
                if f.is_file():
                    f.unlink()
            logger.info("Temp directory cleaned")
