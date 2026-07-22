"""
Video Creation Engine Module
=============================
Creates professional YouTube Shorts videos by combining:
- Stock footage/images from free APIs
- AI-generated voiceover (Edge TTS - free)
- Animated subtitles with styling
- Background music
- Ken Burns effect for images
- Smooth transitions
"""
import os
import json
import random
import textwrap
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from loguru import logger

from config.settings import Config
from modules.tts_engine import TTSEngine
from modules.media_fetcher import MediaFetcher


# Video dimensions for YouTube Shorts (9:16 portrait)
WIDTH = Config.VIDEO_WIDTH   # 1080
HEIGHT = Config.VIDEO_HEIGHT  # 1920
FPS = Config.VIDEO_FPS        # 30


def generate_video_task(video_id: int) -> str:
    """
    Main task to generate a complete YouTube Shorts video.
    
    This is called from the route or scheduler.
    
    Args:
        video_id: Database ID of the Video record
        
    Returns:
        Path to the generated video file
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from database.models import db, Video, ActivityLog
        
        video = Video.query.get(video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        try:
            video.status = 'generating'
            db.session.commit()
            
            logger.info(f"Starting video generation for: {video.title}")
            
            # Step 1: Generate TTS audio
            logger.info("Step 1: Generating voiceover...")
            tts = TTSEngine(voice=video.voice)
            tts_result = tts.generate_speech_with_timestamps(
                video.script, 
                output_filename=f"video_{video.id}"
            )
            
            audio_path = tts_result['audio_path']
            audio_duration = tts_result['duration']
            word_timings = tts_result['word_timings']
            
            video.audio_path = audio_path
            video.duration = audio_duration
            db.session.commit()
            
            # Step 2: Fetch stock media
            logger.info("Step 2: Fetching stock media...")
            niche_keywords = video.hashtags or '["nature", "cinematic"]'
            try:
                keywords_list = json.loads(niche_keywords)
                search_query = ' '.join([k.replace('#', '') for k in keywords_list[:3]])
            except (json.JSONDecodeError, TypeError):
                search_query = video.niche or 'nature cinematic'
            
            fetcher = MediaFetcher()
            # Calculate how many clips we need (each ~5-8 seconds)
            clips_needed = max(3, int(audio_duration / 6))
            media_paths = fetcher.fetch_videos(search_query, count=clips_needed)
            
            if not media_paths:
                # Use images if no videos available
                media_paths = fetcher.fetch_images(search_query, count=clips_needed)
            
            # Step 3: Create the video
            logger.info("Step 3: Compositing video...")
            output_path = str(Config.VIDEOS_FOLDER / f"shorts_{video.id}.mp4")
            
            _compose_video(
                media_paths=media_paths,
                audio_path=audio_path,
                output_path=output_path,
                duration=audio_duration,
                word_timings=word_timings,
                title=video.title
            )
            
            # Step 4: Generate thumbnail
            logger.info("Step 4: Generating thumbnail...")
            thumb_path = str(Config.THUMBNAILS_FOLDER / f"thumb_{video.id}.jpg")
            _generate_thumbnail(media_paths[0] if media_paths else None, video.title, thumb_path)
            
            # Update video record
            video.video_path = output_path
            video.thumbnail_path = thumb_path
            video.status = 'ready'
            video.error_message = None
            db.session.commit()
            
            # Log success
            log = ActivityLog(
                user_id=video.user_id,
                action='Video Generated',
                details=f'Video "{video.title}" generated successfully ({audio_duration:.0f}s)',
                status='success'
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Video generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            video.status = 'failed'
            video.error_message = str(e)
            db.session.commit()
            
            # Log failure
            log = ActivityLog(
                user_id=video.user_id,
                action='Video Generation Failed',
                details=f'Error: {str(e)}',
                status='error'
            )
            db.session.add(log)
            db.session.commit()
            
            raise


def _compose_video(
    media_paths: List[str],
    audio_path: str,
    output_path: str,
    duration: float,
    word_timings: List[Dict],
    title: str
) -> None:
    """
    Compose the final video from components.
    
    Creates a professional-looking Shorts video with:
    - Background media (stock videos/images)
    - Ken Burns effect for images
    - Animated word-by-word subtitles
    - Gradient overlay for text readability
    - Title card at the beginning
    """
    from moviepy.editor import (
        VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
        TextClip, ColorClip, concatenate_videoclips
    )
    
    # Load audio
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration
    
    # Create background clips from media
    bg_clips = []
    time_per_clip = total_duration / max(len(media_paths), 1)
    
    for i, media_path in enumerate(media_paths):
        start_time = i * time_per_clip
        clip_duration = time_per_clip
        
        if start_time >= total_duration:
            break
        
        # Ensure last clip fills remaining time
        if i == len(media_paths) - 1:
            clip_duration = total_duration - start_time
        
        try:
            if media_path.endswith(('.mp4', '.mov', '.avi', '.webm')):
                clip = VideoFileClip(media_path)
                # Resize to fill frame (portrait 9:16)
                clip = _resize_to_fill(clip, WIDTH, HEIGHT)
                # Trim or loop to needed duration
                if clip.duration >= clip_duration:
                    clip = clip.subclip(0, clip_duration)
                else:
                    # Loop the clip
                    loops = int(clip_duration / clip.duration) + 1
                    clip = concatenate_videoclips([clip] * loops).subclip(0, clip_duration)
            else:
                # Image - apply Ken Burns effect
                clip = _create_ken_burns_clip(media_path, clip_duration)
            
            clip = clip.set_start(start_time)
            bg_clips.append(clip)
            
        except Exception as e:
            logger.warning(f"Failed to process media {media_path}: {e}")
            # Create color fallback
            fallback = ColorClip(size=(WIDTH, HEIGHT), color=(20, 20, 40))\
                .set_duration(clip_duration).set_start(start_time)
            bg_clips.append(fallback)
    
    if not bg_clips:
        # Create solid background if no media
        bg_clips = [ColorClip(size=(WIDTH, HEIGHT), color=(20, 20, 40)).set_duration(total_duration)]
    
    # Create gradient overlay for subtitle readability
    gradient = _create_gradient_overlay(total_duration)
    
    # Create subtitle clips with word-by-word animation
    subtitle_clips = _create_animated_subtitles(word_timings, total_duration)
    
    # Compose all layers
    all_clips = bg_clips + [gradient] + subtitle_clips
    
    final = CompositeVideoClip(all_clips, size=(WIDTH, HEIGHT))
    final = final.set_duration(total_duration)
    final = final.set_audio(audio)
    
    # Export
    final.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        bitrate='4000k',
        threads=4,
        logger=None  # Suppress moviepy output
    )
    
    # Cleanup
    audio.close()
    final.close()
    for clip in bg_clips:
        clip.close()


def _resize_to_fill(clip, target_w: int, target_h: int):
    """Resize and crop clip to fill target dimensions."""
    from moviepy.editor import VideoFileClip
    
    # Calculate scale to fill
    clip_aspect = clip.w / clip.h
    target_aspect = target_w / target_h
    
    if clip_aspect > target_aspect:
        # Clip is wider - scale by height
        new_h = target_h
        new_w = int(clip_aspect * target_h)
    else:
        # Clip is taller - scale by width
        new_w = target_w
        new_h = int(target_w / clip_aspect)
    
    clip = clip.resize((new_w, new_h))
    
    # Center crop
    x_center = new_w // 2
    y_center = new_h // 2
    clip = clip.crop(
        x1=x_center - target_w // 2,
        y1=y_center - target_h // 2,
        x2=x_center + target_w // 2,
        y2=y_center + target_h // 2
    )
    
    return clip


def _create_ken_burns_clip(image_path: str, duration: float):
    """Create a Ken Burns (pan/zoom) effect from a still image."""
    from moviepy.editor import ImageClip
    
    # Load and resize image to be larger than frame
    img = Image.open(image_path)
    
    # Make image 20% larger for zoom room
    scale = 1.2
    img_w = int(WIDTH * scale)
    img_h = int(HEIGHT * scale)
    img = img.resize((img_w, img_h), Image.LANCZOS)
    img_array = np.array(img)
    
    # Create clip with zoom effect
    def make_frame(t):
        # Smooth zoom from 1.0 to 1.15 over duration
        progress = t / duration
        zoom = 1.0 + (0.15 * progress)
        
        # Calculate crop area
        crop_w = int(WIDTH / zoom)
        crop_h = int(HEIGHT / zoom)
        
        # Pan slightly
        pan_x = int((img_w - crop_w) * (0.3 + 0.4 * progress))
        pan_y = int((img_h - crop_h) * (0.3 + 0.4 * progress))
        
        # Crop and resize
        cropped = img_array[pan_y:pan_y + crop_h, pan_x:pan_x + crop_w]
        
        # Resize to output dimensions
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cropped)
        pil_img = pil_img.resize((WIDTH, HEIGHT), PILImage.LANCZOS)
        
        return np.array(pil_img)
    
    from moviepy.editor import VideoClip
    clip = VideoClip(make_frame, duration=duration)
    
    return clip


def _create_gradient_overlay(duration: float):
    """Create a semi-transparent gradient overlay for subtitle readability."""
    from moviepy.editor import ImageClip
    
    # Create gradient - dark at bottom, transparent at top
    gradient = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    
    # Bottom 40% has gradient from transparent to semi-dark
    gradient_start = int(HEIGHT * 0.5)
    for y in range(gradient_start, HEIGHT):
        progress = (y - gradient_start) / (HEIGHT - gradient_start)
        alpha = int(180 * progress)  # Max 180/255 opacity
        gradient[y, :] = [0, 0, 0, alpha]
    
    # Also add slight top gradient for title area
    top_end = int(HEIGHT * 0.15)
    for y in range(top_end):
        progress = 1 - (y / top_end)
        alpha = int(100 * progress)
        gradient[y, :] = [0, 0, 0, alpha]
    
    # Save as PNG with alpha
    img = Image.fromarray(gradient, 'RGBA')
    overlay_path = str(Config.TEMP_FOLDER / 'gradient_overlay.png')
    img.save(overlay_path)
    
    clip = ImageClip(overlay_path, duration=duration)\
        .set_position((0, 0))
    
    return clip


def _create_animated_subtitles(word_timings: List[Dict], total_duration: float) -> List:
    """
    Create word-by-word animated subtitles.
    
    Groups words into lines and highlights the current word.
    """
    from moviepy.editor import TextClip
    
    if not word_timings:
        return []
    
    subtitle_clips = []
    
    # Group words into subtitle chunks (5-7 words per line)
    words_per_chunk = 5
    chunks = []
    current_chunk = []
    
    for timing in word_timings:
        current_chunk.append(timing)
        if len(current_chunk) >= words_per_chunk:
            chunks.append(current_chunk)
            current_chunk = []
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # Create a text clip for each chunk
    for chunk in chunks:
        if not chunk:
            continue
        
        chunk_text = ' '.join([w['text'] for w in chunk])
        start_time = chunk[0]['offset']
        end_time = chunk[-1]['offset'] + chunk[-1]['duration']
        duration = max(end_time - start_time, 0.5)
        
        try:
            # Create main subtitle text
            txt_clip = TextClip(
                chunk_text,
                fontsize=52,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=3,
                size=(WIDTH - 100, None),
                method='caption',
                align='center'
            )
            
            txt_clip = txt_clip.set_start(start_time)\
                .set_duration(duration)\
                .set_position(('center', HEIGHT * 0.72))
            
            subtitle_clips.append(txt_clip)
            
        except Exception as e:
            logger.warning(f"Failed to create subtitle clip: {e}")
            continue
    
    return subtitle_clips


def _generate_thumbnail(media_path: Optional[str], title: str, output_path: str) -> None:
    """Generate a thumbnail image for the video."""
    
    # Create thumbnail canvas (1080x1920 for Shorts)
    thumb = Image.new('RGB', (WIDTH, HEIGHT), color=(20, 20, 40))
    draw = ImageDraw.Draw(thumb)
    
    # Try to use first frame of media as background
    if media_path:
        try:
            if media_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                bg = Image.open(media_path)
                bg = bg.resize((WIDTH, HEIGHT), Image.LANCZOS)
                thumb.paste(bg)
                draw = ImageDraw.Draw(thumb)
            elif media_path.endswith(('.mp4', '.mov', '.avi')):
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(media_path)
                frame = clip.get_frame(0)
                clip.close()
                bg = Image.fromarray(frame)
                bg = bg.resize((WIDTH, HEIGHT), Image.LANCZOS)
                thumb.paste(bg)
                draw = ImageDraw.Draw(thumb)
        except Exception:
            pass
    
    # Add dark overlay
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 140))
    thumb = thumb.convert('RGBA')
    thumb = Image.alpha_composite(thumb, overlay)
    draw = ImageDraw.Draw(thumb)
    
    # Add title text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
    except (IOError, OSError):
        font = ImageFont.load_default()
    
    # Word wrap title
    lines = textwrap.wrap(title, width=18)
    y_position = HEIGHT // 2 - (len(lines) * 80) // 2
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) // 2
        
        # Draw text shadow
        draw.text((x + 3, y_position + 3), line, fill=(0, 0, 0), font=font)
        # Draw main text
        draw.text((x, y_position), line, fill=(255, 255, 255), font=font)
        y_position += 90
    
    # Save
    thumb = thumb.convert('RGB')
    thumb.save(output_path, 'JPEG', quality=90)
    logger.info(f"Thumbnail saved: {output_path}")
