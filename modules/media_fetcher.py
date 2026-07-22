"""
Media Fetcher Module
====================
Fetches free stock videos and images from Pexels and Pixabay APIs.
All media is royalty-free and suitable for commercial use.
"""
import os
import random
import httpx
from pathlib import Path
from typing import List, Optional, Dict
from config.settings import Config
from loguru import logger


class MediaFetcher:
    """Fetches free stock media from various APIs."""
    
    def __init__(self):
        self.pexels_key = Config.PEXELS_API_KEY
        self.pixabay_key = Config.PIXABAY_API_KEY
        self.temp_dir = Config.TEMP_FOLDER
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_videos(self, keywords: str, count: int = 5, orientation: str = 'portrait') -> List[str]:
        """
        Fetch stock videos matching keywords.
        
        Args:
            keywords: Search keywords
            count: Number of videos to fetch
            orientation: portrait (for Shorts) or landscape
        
        Returns:
            List of local file paths to downloaded videos
        """
        video_paths = []
        
        # Try Pexels first
        if self.pexels_key:
            try:
                paths = self._fetch_pexels_videos(keywords, count, orientation)
                video_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pexels video fetch failed: {e}")
        
        # Supplement with Pixabay if needed
        if len(video_paths) < count and self.pixabay_key:
            try:
                remaining = count - len(video_paths)
                paths = self._fetch_pixabay_videos(keywords, remaining)
                video_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pixabay video fetch failed: {e}")
        
        # If no API keys, try to fetch free images instead
        if not video_paths:
            logger.info("No stock videos found, fetching images instead")
            image_paths = self.fetch_images(keywords, count)
            return image_paths
        
        return video_paths
    
    def fetch_images(self, keywords: str, count: int = 5) -> List[str]:
        """
        Fetch stock images matching keywords.
        
        Args:
            keywords: Search keywords
            count: Number of images to fetch
            
        Returns:
            List of local file paths to downloaded images
        """
        image_paths = []
        
        # Try Pexels
        if self.pexels_key:
            try:
                paths = self._fetch_pexels_images(keywords, count)
                image_paths.extend(paths)
            except Exception as e:
                logger.warning(f"Pexels image fetch failed: {e}")
        
        # Supplement with Pixabay
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
            # Get the best quality video file (SD for speed)
            video_files = video.get('video_files', [])
            
            # Prefer HD portrait videos
            selected = None
            for vf in video_files:
                if vf.get('height', 0) >= 720 and vf.get('width', 0) <= vf.get('height', 0):
                    selected = vf
                    break
            
            if not selected and video_files:
                # Fallback to first available
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
            # Get portrait/large size
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
            # Prefer medium quality
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
        import shutil
        if self.temp_dir.exists():
            for f in self.temp_dir.iterdir():
                if f.is_file():
                    f.unlink()
            logger.info("Temp directory cleaned")
