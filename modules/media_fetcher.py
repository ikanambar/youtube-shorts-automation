"""
Media Fetcher Module
====================
Hybrid media sourcing for video creation:

1. REAL VIDEO style  -> Smart per-sentence stock video from Pexels/Pixabay
2. ARTISTIC styles   -> AI image generation via Pollinations.ai
   (cinematic_ai, anime, cartoon, illustration, graphic_art, 3d_render,
    oil_painting, watercolor, custom)

Key feature: Uses Pollinations Text AI (FREE) to convert Indonesian narration
into accurate English search keywords / image prompts, so visuals truly match
what is being narrated.
"""
import os
import re
import random
import hashlib
import httpx
from pathlib import Path
from typing import List, Optional, Dict
from urllib.parse import quote
from config.settings import Config
from loguru import logger


# Visual styles that use AI image generation (everything except real_video)
AI_STYLES = {
    'cinematic_ai', 'anime', 'cartoon', 'illustration',
    'graphic_art', '3d_render', 'oil_painting', 'watercolor', 'custom'
}

# Style-specific prompt modifiers appended to every AI image prompt
STYLE_MODIFIERS = {
    'cinematic_ai': 'cinematic film still, dramatic lighting, movie scene, 8k, highly detailed, professional color grading, depth of field',
    'anime': 'anime style, studio ghibli inspired, vibrant colors, detailed anime illustration, cel shading, high quality anime art',
    'cartoon': 'cartoon style, pixar 3d animation style, colorful, playful, clean render, high quality',
    'illustration': 'digital illustration, detailed artwork, artstation trending, concept art, beautiful lighting, painterly',
    'graphic_art': 'bold graphic design, poster art, flat design, vector style, striking composition, modern aesthetic',
    '3d_render': '3d render, octane render, unreal engine, ultra realistic, volumetric lighting, 8k',
    'oil_painting': 'oil painting, classical fine art, textured brushstrokes, masterpiece, rich colors',
    'watercolor': 'watercolor painting, soft washes, artistic, delicate, hand painted, flowing colors',
    'custom': '',  # custom uses only the user's prompt
}


class MediaFetcher:
    """Fetches AI-generated or stock media for video creation."""

    POLLINATIONS_IMG_URL = "https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model=flux&nologo=true&enhance=true&seed={seed}"
    POLLINATIONS_TEXT_URL = "https://text.pollinations.ai/{prompt}"

    def __init__(self):
        self.pexels_key = Config.PEXELS_API_KEY
        self.pixabay_key = Config.PIXABAY_API_KEY
        self.temp_dir = Config.TEMP_FOLDER
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ==========================================================
    # MAIN ENTRY POINT - Router
    # ==========================================================

    def fetch_media_for_script(
        self,
        script: str,
        niche: str = 'facts',
        visual_style: str = 'real_video',
        custom_prompt: str = '',
        count: int = 5
    ) -> List[str]:
        """
        Fetch media matching the narration, using the chosen visual style.

        Args:
            script: Full narration script
            niche: Content niche (for keyword hints)
            visual_style: real_video | cinematic_ai | anime | cartoon |
                          illustration | graphic_art | 3d_render |
                          oil_painting | watercolor | custom
            custom_prompt: Extra user instruction for AI visuals
            count: Number of media segments needed

        Returns:
            List of local file paths (videos or images)
        """
        logger.info(f"Fetching media | style={visual_style} | niche={niche} | count={count}")

        segments = self._split_script_into_segments(script, count)
        logger.info(f"Split narration into {len(segments)} scenes")

        if visual_style in AI_STYLES:
            return self._fetch_ai_images(segments, visual_style, custom_prompt, niche)
        else:
            # real_video (default)
            return self._fetch_smart_stock_videos(segments, niche)

    # ==========================================================
    # SMART STOCK VIDEO (real_video) - per-sentence matching
    # ==========================================================

    def _fetch_smart_stock_videos(self, segments: List[str], niche: str) -> List[str]:
        """Find a matching stock VIDEO for each narration segment."""
        paths = []
        used_ids = set()

        for i, segment in enumerate(segments):
            # Convert narration -> English search keywords via Pollinations Text AI
            keywords = self._narration_to_keywords(segment, niche)
            logger.info(f"Scene {i+1}: '{segment[:40]}...' -> keywords: '{keywords}'")

            found = self._search_one_stock_video(keywords, used_ids)
            if not found:
                # Retry with simpler/broader keyword
                broad = keywords.split()[0] if keywords else (niche or 'cinematic')
                found = self._search_one_stock_video(broad, used_ids)

            if found:
                paths.append(found)
            else:
                # Fallback to an image for this scene
                img = self._search_one_stock_image(keywords, used_ids)
                if img:
                    paths.append(img)

        # Absolute fallback if nothing matched at all
        if not paths:
            logger.warning("Smart matching found nothing, using generic stock")
            paths = self._search_stock_images_bulk(niche or 'cinematic nature', len(segments))

        return paths

    def _search_one_stock_video(self, keywords: str, used_ids: set) -> Optional[str]:
        """Search Pexels then Pixabay for a single portrait video."""
        # Pexels
        if self.pexels_key:
            try:
                url = "https://api.pexels.com/videos/search"
                headers = {"Authorization": self.pexels_key}
                params = {"query": keywords, "per_page": 8,
                          "orientation": "portrait", "size": "medium"}
                with httpx.Client(timeout=30) as client:
                    r = client.get(url, headers=headers, params=params)
                    r.raise_for_status()
                    data = r.json()

                for video in data.get('videos', []):
                    if video['id'] in used_ids:
                        continue
                    vf = self._pick_portrait_file(video.get('video_files', []))
                    if vf:
                        fp = self.temp_dir / f"pexels_video_{video['id']}.mp4"
                        if not fp.exists():
                            self._download_file(vf['link'], fp)
                        used_ids.add(video['id'])
                        return str(fp)
            except Exception as e:
                logger.warning(f"Pexels video search failed: {e}")

        # Pixabay
        if self.pixabay_key:
            try:
                url = "https://pixabay.com/api/videos/"
                params = {"key": self.pixabay_key, "q": keywords,
                          "per_page": 8, "safesearch": "true"}
                with httpx.Client(timeout=30) as client:
                    r = client.get(url, params=params)
                    r.raise_for_status()
                    data = r.json()

                for hit in data.get('hits', []):
                    if hit['id'] in used_ids:
                        continue
                    videos = hit.get('videos', {})
                    v = videos.get('medium', {}) or videos.get('small', {})
                    if v.get('url'):
                        fp = self.temp_dir / f"pixabay_video_{hit['id']}.mp4"
                        if not fp.exists():
                            self._download_file(v['url'], fp)
                        used_ids.add(hit['id'])
                        return str(fp)
            except Exception as e:
                logger.warning(f"Pixabay video search failed: {e}")

        return None

    def _pick_portrait_file(self, video_files: List[Dict]) -> Optional[Dict]:
        """Choose a portrait HD video file, else first available."""
        for vf in video_files:
            h = vf.get('height', 0)
            w = vf.get('width', 0)
            if h >= 720 and w <= h:
                return vf
        return video_files[0] if video_files else None

    # ==========================================================
    # AI IMAGE GENERATION (artistic styles)
    # ==========================================================

    def _fetch_ai_images(self, segments: List[str], style: str,
                         custom_prompt: str, niche: str) -> List[str]:
        """Generate an AI image per narration segment in the chosen style."""
        paths = []
        style_mod = STYLE_MODIFIERS.get(style, '')

        for i, segment in enumerate(segments):
            # Turn narration into a concise English visual description
            visual_desc = self._narration_to_visual_description(segment, niche)

            # Compose the final image prompt
            parts = [visual_desc]
            if custom_prompt:
                parts.append(custom_prompt)
            if style_mod:
                parts.append(style_mod)
            prompt = ", ".join([p for p in parts if p])

            logger.info(f"Scene {i+1} [{style}] prompt: '{prompt[:90]}...'")

            path = self._generate_pollinations_image(prompt, i)
            if path:
                paths.append(path)

        # Fallback to stock images if AI failed entirely
        if not paths:
            logger.warning("AI generation failed, falling back to stock images")
            paths = self._search_stock_images_bulk(niche or 'cinematic', len(segments))

        return paths

    def _generate_pollinations_image(self, prompt: str, index: int) -> Optional[str]:
        """Generate a single AI image via Pollinations.ai (FREE)."""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        file_path = self.temp_dir / f"ai_img_{index}_{prompt_hash}.jpg"

        if file_path.exists() and file_path.stat().st_size > 5000:
            return str(file_path)

        url = self.POLLINATIONS_IMG_URL.format(
            prompt=quote(prompt),
            width=1080,
            height=1920,
            seed=random.randint(1, 999999)
        )

        # Try twice in case of transient errors
        for attempt in range(2):
            try:
                logger.info(f"Generating AI image {index+1} (attempt {attempt+1})...")
                with httpx.Client(timeout=150, follow_redirects=True) as client:
                    r = client.get(url)
                    r.raise_for_status()
                    ctype = r.headers.get('content-type', '')
                    if 'image' in ctype or len(r.content) > 10000:
                        with open(file_path, 'wb') as f:
                            f.write(r.content)
                        logger.info(f"AI image saved: {file_path} ({len(r.content)} bytes)")
                        return str(file_path)
            except Exception as e:
                logger.warning(f"Pollinations image attempt {attempt+1} failed: {e}")

        return None

    # ==========================================================
    # POLLINATIONS TEXT AI - narration -> keywords/description
    # ==========================================================

    def _narration_to_keywords(self, segment: str, niche: str) -> str:
        """Convert a narration sentence into 2-3 English stock-video keywords."""
        instruction = (
            "Convert this sentence into exactly 3 simple English keywords for "
            "searching stock footage. Return ONLY the keywords separated by spaces, "
            "no punctuation, no explanation. Sentence: " + segment
        )
        result = self._pollinations_text(instruction)
        if result:
            # Clean up: keep words only, max 4
            words = re.findall(r'[a-zA-Z]+', result)
            words = [w for w in words if len(w) > 2][:4]
            if words:
                return ' '.join(words)
        # Fallback: local keyword extraction
        return self._extract_keywords_local(segment, niche)

    def _narration_to_visual_description(self, segment: str, niche: str) -> str:
        """Convert a narration sentence into a short English visual scene description."""
        instruction = (
            "Describe a single vivid visual scene (in English, max 15 words) that "
            "would illustrate this narration. Return ONLY the description, no quotes. "
            "Narration: " + segment
        )
        result = self._pollinations_text(instruction)
        if result:
            desc = result.strip().strip('"').replace('\n', ' ')
            if 5 < len(desc) < 200:
                return desc
        # Fallback
        return self._extract_keywords_local(segment, niche)

    def _pollinations_text(self, prompt: str) -> Optional[str]:
        """Call Pollinations Text AI (FREE). Returns generated text or None."""
        try:
            url = self.POLLINATIONS_TEXT_URL.format(prompt=quote(prompt))
            with httpx.Client(timeout=45, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                text = r.text.strip()
                if text and len(text) < 500:
                    return text
        except Exception as e:
            logger.warning(f"Pollinations text failed: {e}")
        return None

    def _extract_keywords_local(self, text: str, niche: str) -> str:
        """Local fallback keyword extraction (no network)."""
        stop_words = {
            'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'dengan', 'ini', 'itu',
            'adalah', 'pada', 'tidak', 'akan', 'juga', 'sudah', 'bisa', 'lebih',
            'kamu', 'kita', 'saya', 'karena', 'atau', 'tapi', 'saat', 'setiap',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'to', 'of', 'in',
            'for', 'with', 'on', 'at', 'by', 'from', 'that', 'this', 'it',
        }
        niche_hint = {
            'motivational': 'success motivation sunrise',
            'facts': 'science discovery abstract',
            'tech': 'technology digital futuristic',
            'nature': 'nature landscape wildlife',
            'history': 'ancient history monument',
            'health': 'fitness healthy wellness',
            'finance': 'money business finance',
            'psychology': 'brain mind thinking',
        }.get(niche, 'cinematic')

        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words][:3]
        return ' '.join(keywords) if keywords else niche_hint

    # ==========================================================
    # SCRIPT SEGMENTATION
    # ==========================================================

    def _split_script_into_segments(self, script: str, target_count: int) -> List[str]:
        """Split script into scene segments (one visual per segment)."""
        sentences = re.split(r'[.!?]+', script)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 8]

        if not sentences:
            return [script] if script.strip() else ['cinematic scene']

        if len(sentences) <= target_count:
            return sentences

        # Group evenly into target_count segments
        segments = []
        per = max(1, len(sentences) // target_count)
        for i in range(0, len(sentences), per):
            segments.append('. '.join(sentences[i:i + per]))
            if len(segments) >= target_count:
                break
        return segments[:target_count]

    # ==========================================================
    # STOCK IMAGE HELPERS (fallback)
    # ==========================================================

    def _search_one_stock_image(self, keywords: str, used_ids: set) -> Optional[str]:
        """Search a single portrait stock image."""
        if self.pexels_key:
            try:
                url = "https://api.pexels.com/v1/search"
                headers = {"Authorization": self.pexels_key}
                params = {"query": keywords, "per_page": 8,
                          "orientation": "portrait", "size": "medium"}
                with httpx.Client(timeout=30) as client:
                    r = client.get(url, headers=headers, params=params)
                    r.raise_for_status()
                    data = r.json()
                for photo in data.get('photos', []):
                    if photo['id'] in used_ids:
                        continue
                    img_url = photo['src'].get('portrait') or photo['src'].get('large')
                    fp = self.temp_dir / f"pexels_img_{photo['id']}.jpg"
                    if not fp.exists():
                        self._download_file(img_url, fp)
                    used_ids.add(photo['id'])
                    return str(fp)
            except Exception as e:
                logger.warning(f"Pexels image search failed: {e}")
        return None

    def _search_stock_images_bulk(self, keywords: str, count: int) -> List[str]:
        """Fetch several stock images at once (last-resort fallback)."""
        paths = []
        used = set()
        for _ in range(count):
            img = self._search_one_stock_image(keywords, used)
            if img:
                paths.append(img)
            else:
                break
        return paths

    # ==========================================================
    # LEGACY METHODS (backward compatibility)
    # ==========================================================

    def fetch_videos(self, keywords: str, count: int = 5, orientation: str = 'portrait') -> List[str]:
        """Legacy: bulk stock video search by keyword."""
        segments = [keywords] * count
        return self._fetch_smart_stock_videos(segments, 'facts')

    def fetch_images(self, keywords: str, count: int = 5) -> List[str]:
        """Legacy: bulk stock image search by keyword."""
        return self._search_stock_images_bulk(keywords, count)

    def fetch_ai_images_for_script(self, script: str, niche: str = 'facts', count: int = 5) -> List[str]:
        """Legacy: AI image generation (cinematic style)."""
        segments = self._split_script_into_segments(script, count)
        return self._fetch_ai_images(segments, 'cinematic_ai', '', niche)

    # ==========================================================
    # UTILITIES
    # ==========================================================

    def _download_file(self, url: str, path: Path) -> None:
        """Download a file from URL to local path."""
        logger.info(f"Downloading: {url}")
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            with open(path, 'wb') as f:
                f.write(r.content)

    def cleanup_temp(self) -> None:
        """Remove all temporary files."""
        if self.temp_dir.exists():
            for f in self.temp_dir.iterdir():
                if f.is_file():
                    f.unlink()
            logger.info("Temp directory cleaned")
