"""
YouTube Upload Module
======================
Handles YouTube OAuth2 authentication and video upload.
Uses YouTube Data API v3 (FREE - quota based).
"""
import os
import json
import httpx
from datetime import datetime
from typing import Dict, Optional
from config.settings import Config
from loguru import logger


# OAuth2 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"


def get_auth_url() -> str:
    """
    Generate OAuth2 authorization URL for YouTube.
    
    Returns:
        Authorization URL to redirect user to
    """
    params = {
        'client_id': Config.YOUTUBE_CLIENT_ID,
        'redirect_uri': Config.YOUTUBE_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(Config.YOUTUBE_SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true'
    }
    
    query_string = '&'.join(f'{k}={v}' for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query_string}"


def exchange_code_for_tokens(code: str) -> Dict:
    """
    Exchange authorization code for access/refresh tokens.
    
    Args:
        code: Authorization code from OAuth callback
        
    Returns:
        Dict with access_token, refresh_token, etc.
    """
    data = {
        'code': code,
        'client_id': Config.YOUTUBE_CLIENT_ID,
        'client_secret': Config.YOUTUBE_CLIENT_SECRET,
        'redirect_uri': Config.YOUTUBE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    with httpx.Client(timeout=30) as client:
        response = client.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


def refresh_access_token(refresh_token: str) -> Dict:
    """
    Refresh an expired access token.
    
    Args:
        refresh_token: The refresh token
        
    Returns:
        Dict with new access_token
    """
    data = {
        'refresh_token': refresh_token,
        'client_id': Config.YOUTUBE_CLIENT_ID,
        'client_secret': Config.YOUTUBE_CLIENT_SECRET,
        'grant_type': 'refresh_token'
    }
    
    with httpx.Client(timeout=30) as client:
        response = client.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


def get_channel_info(access_token: str) -> Optional[Dict]:
    """
    Get YouTube channel information.
    
    Args:
        access_token: Valid YouTube access token
        
    Returns:
        Dict with channel id and title, or None
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'part': 'snippet',
        'mine': 'true'
    }
    
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{YOUTUBE_API_URL}/channels",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        data = response.json()
    
    items = data.get('items', [])
    if items:
        channel = items[0]
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'thumbnail': channel['snippet'].get('thumbnails', {}).get('default', {}).get('url')
        }
    
    return None


def upload_video_task(video_id: int, user_id: int) -> str:
    """
    Upload a video to YouTube.
    
    Args:
        video_id: Database ID of the Video record
        user_id: Database ID of the User
        
    Returns:
        YouTube video ID
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from database.models import db, Video, User, ActivityLog
        
        video = Video.query.get(video_id)
        user = User.query.get(user_id)
        
        if not video or not user:
            raise ValueError("Video or user not found")
        
        if not user.youtube_connected or not user.youtube_refresh_token:
            raise ValueError("YouTube not connected")
        
        if not video.video_path or not os.path.exists(video.video_path):
            raise ValueError("Video file not found")
        
        try:
            # Refresh token
            tokens = refresh_access_token(user.youtube_refresh_token)
            access_token = tokens.get('access_token')
            
            if not access_token:
                raise ValueError("Failed to refresh access token")
            
            # Update stored token
            user.youtube_access_token = access_token
            db.session.commit()
            
            # Prepare video metadata
            hashtags = []
            try:
                hashtags = json.loads(video.hashtags) if video.hashtags else []
            except (json.JSONDecodeError, TypeError):
                pass
            
            description = video.description or ''
            if hashtags:
                description += '\n\n' + ' '.join(hashtags)
            
            # Add #Shorts tag
            if '#shorts' not in description.lower():
                description += '\n#Shorts'
            
            metadata = {
                'snippet': {
                    'title': video.title[:100],  # YouTube title limit
                    'description': description[:5000],  # YouTube description limit
                    'tags': [h.replace('#', '') for h in hashtags],
                    'categoryId': '22',  # People & Blogs
                    'defaultLanguage': video.language or 'id'
                },
                'status': {
                    'privacyStatus': 'public',  # public, private, or unlisted
                    'selfDeclaredMadeForKids': False,
                    'embeddable': True
                }
            }
            
            # Upload video
            youtube_video_id = _upload_to_youtube(
                access_token=access_token,
                video_path=video.video_path,
                metadata=metadata
            )
            
            # Update video record
            video.youtube_video_id = youtube_video_id
            video.youtube_url = f"https://youtube.com/shorts/{youtube_video_id}"
            video.upload_status = 'uploaded'
            video.status = 'uploaded'
            video.uploaded_at = datetime.utcnow()
            db.session.commit()
            
            # Upload thumbnail if available
            if video.thumbnail_path and os.path.exists(video.thumbnail_path):
                try:
                    _upload_thumbnail(access_token, youtube_video_id, video.thumbnail_path)
                except Exception as e:
                    logger.warning(f"Thumbnail upload failed: {e}")
            
            # Log success
            log = ActivityLog(
                user_id=user_id,
                action='Video Uploaded',
                details=f'"{video.title}" uploaded to YouTube: {video.youtube_url}',
                status='success'
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Video uploaded: {video.youtube_url}")
            return youtube_video_id
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            video.upload_status = 'failed'
            video.error_message = f"Upload error: {str(e)}"
            db.session.commit()
            
            log = ActivityLog(
                user_id=user_id,
                action='Upload Failed',
                details=str(e),
                status='error'
            )
            db.session.add(log)
            db.session.commit()
            
            raise


def _upload_to_youtube(access_token: str, video_path: str, metadata: Dict) -> str:
    """
    Perform the actual video upload to YouTube using resumable upload.
    
    Args:
        access_token: Valid access token
        video_path: Path to the video file
        metadata: Video metadata dict
        
    Returns:
        YouTube video ID
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Type': 'video/mp4',
        'X-Upload-Content-Length': str(os.path.getsize(video_path))
    }
    
    params = {
        'uploadType': 'resumable',
        'part': 'snippet,status'
    }
    
    # Step 1: Initiate resumable upload
    with httpx.Client(timeout=60) as client:
        response = client.post(
            YOUTUBE_UPLOAD_URL,
            headers=headers,
            params=params,
            content=json.dumps(metadata)
        )
        response.raise_for_status()
    
    upload_url = response.headers.get('Location')
    if not upload_url:
        raise ValueError("No upload URL received from YouTube")
    
    # Step 2: Upload the video file
    file_size = os.path.getsize(video_path)
    
    with open(video_path, 'rb') as video_file:
        upload_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size)
        }
        
        with httpx.Client(timeout=600) as client:  # 10 minute timeout for upload
            response = client.put(
                upload_url,
                headers=upload_headers,
                content=video_file.read()
            )
            response.raise_for_status()
    
    result = response.json()
    video_id = result.get('id')
    
    if not video_id:
        raise ValueError(f"Upload response missing video ID: {result}")
    
    return video_id


def _upload_thumbnail(access_token: str, video_id: str, thumbnail_path: str) -> None:
    """Upload a custom thumbnail for a YouTube video."""
    url = f"{YOUTUBE_API_URL}/thumbnails/set"
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    params = {'videoId': video_id}
    
    with open(thumbnail_path, 'rb') as f:
        files = {'media_body': ('thumbnail.jpg', f, 'image/jpeg')}
        with httpx.Client(timeout=60) as client:
            response = client.post(
                url,
                headers=headers,
                params=params,
                files={'file': ('thumbnail.jpg', f, 'image/jpeg')}
            )
            # Thumbnail upload may fail for unverified accounts - that's OK
            if response.status_code != 200:
                logger.warning(f"Thumbnail upload returned {response.status_code}")
