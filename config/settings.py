"""Application settings and configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/database/app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # YouTube API
    YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID', '')
    YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET', '')
    YOUTUBE_REDIRECT_URI = os.getenv('YOUTUBE_REDIRECT_URI', 'http://localhost:5000/auth/youtube/callback')
    YOUTUBE_SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.force-ssl'
    ]
    
    # Media APIs
    PEXELS_API_KEY = os.getenv('PEXELS_API_KEY', '')
    PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY', '')
    
    # OpenAI (Optional)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # TTS Settings
    TTS_VOICE = os.getenv('TTS_VOICE', 'id-ID-ArdiNeural')
    TTS_RATE = os.getenv('TTS_RATE', '+0%')
    TTS_VOLUME = os.getenv('TTS_VOLUME', '+0%')
    
    # Video Settings
    VIDEO_WIDTH = int(os.getenv('VIDEO_WIDTH', 1080))
    VIDEO_HEIGHT = int(os.getenv('VIDEO_HEIGHT', 1920))
    VIDEO_FPS = int(os.getenv('VIDEO_FPS', 30))
    VIDEO_DURATION_MIN = int(os.getenv('VIDEO_DURATION_MIN', 15))
    VIDEO_DURATION_MAX = int(os.getenv('VIDEO_DURATION_MAX', 60))
    
    # Paths
    UPLOAD_FOLDER = BASE_DIR / os.getenv('UPLOAD_FOLDER', 'uploads')
    VIDEOS_FOLDER = UPLOAD_FOLDER / 'videos'
    THUMBNAILS_FOLDER = UPLOAD_FOLDER / 'thumbnails'
    AUDIO_FOLDER = UPLOAD_FOLDER / 'audio'
    TEMP_FOLDER = BASE_DIR / 'temp'
    STATIC_FOLDER = BASE_DIR / 'app' / 'static'
    MUSIC_FOLDER = STATIC_FOLDER / 'music'
    
    # Scheduler
    MAX_SCHEDULED_VIDEOS = int(os.getenv('MAX_SCHEDULED_VIDEOS', 50))
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', '')
    
    @classmethod
    def init_dirs(cls):
        """Create necessary directories."""
        dirs = [
            cls.UPLOAD_FOLDER,
            cls.VIDEOS_FOLDER, 
            cls.THUMBNAILS_FOLDER,
            cls.AUDIO_FOLDER,
            cls.TEMP_FOLDER,
            cls.MUSIC_FOLDER,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


# Video niches/categories available
NICHES = {
    'motivational': {
        'name': 'Motivasi & Inspirasi',
        'hashtags': ['#motivasi', '#inspirasi', '#sukses', '#semangat', '#shorts'],
        'music_mood': 'inspiring'
    },
    'facts': {
        'name': 'Fakta Menarik',
        'hashtags': ['#fakta', '#faktamenarik', '#tahukahkamu', '#edukasi', '#shorts'],
        'music_mood': 'curious'
    },
    'tech': {
        'name': 'Teknologi & Tips',
        'hashtags': ['#teknologi', '#tips', '#tutorial', '#tech', '#shorts'],
        'music_mood': 'modern'
    },
    'nature': {
        'name': 'Alam & Sains',
        'hashtags': ['#alam', '#sains', '#nature', '#science', '#shorts'],
        'music_mood': 'calm'
    },
    'history': {
        'name': 'Sejarah & Budaya',
        'hashtags': ['#sejarah', '#history', '#budaya', '#culture', '#shorts'],
        'music_mood': 'epic'
    },
    'health': {
        'name': 'Kesehatan & Fitness',
        'hashtags': ['#kesehatan', '#health', '#fitness', '#tips', '#shorts'],
        'music_mood': 'energetic'
    },
    'finance': {
        'name': 'Keuangan & Bisnis',
        'hashtags': ['#keuangan', '#bisnis', '#investasi', '#financial', '#shorts'],
        'music_mood': 'professional'
    },
    'psychology': {
        'name': 'Psikologi & Self-Improvement',
        'hashtags': ['#psikologi', '#selfimprovement', '#mindset', '#growth', '#shorts'],
        'music_mood': 'thoughtful'
    }
}

# Available TTS Voices
TTS_VOICES = {
    'id-ID-ArdiNeural': 'Indonesian - Ardi (Male)',
    'id-ID-GadisNeural': 'Indonesian - Gadis (Female)',
    'en-US-ChristopherNeural': 'English - Christopher (Male)',
    'en-US-JennyNeural': 'English - Jenny (Female)',
    'en-US-GuyNeural': 'English - Guy (Male)',
    'en-GB-SoniaNeural': 'English UK - Sonia (Female)',
    'ja-JP-KeitaNeural': 'Japanese - Keita (Male)',
    'ko-KR-InJoonNeural': 'Korean - InJoon (Male)',
}
