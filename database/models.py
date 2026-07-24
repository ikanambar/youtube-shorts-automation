"""Database models for YouTube Shorts Automation."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # YouTube OAuth tokens
    youtube_access_token = db.Column(db.Text, nullable=True)
    youtube_refresh_token = db.Column(db.Text, nullable=True)
    youtube_token_expiry = db.Column(db.DateTime, nullable=True)
    youtube_channel_name = db.Column(db.String(200), nullable=True)
    youtube_channel_id = db.Column(db.String(100), nullable=True)
    youtube_connected = db.Column(db.Boolean, default=False)
    
    # Relationships
    videos = db.relationship('Video', backref='creator', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='owner', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'


class Video(db.Model):
    """Video model to track generated videos."""
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Content
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    script = db.Column(db.Text, nullable=True)
    hashtags = db.Column(db.Text, nullable=True)  # JSON array
    niche = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(10), default='id')

    # Visual style: real_video, cinematic_ai, anime, cartoon, illustration,
    # graphic_art, 3d_render, oil_painting, watercolor, custom
    visual_style = db.Column(db.String(50), default='real_video')
    custom_prompt = db.Column(db.Text, nullable=True)  # User's custom visual instruction
    
    # Files
    video_path = db.Column(db.String(500), nullable=True)
    thumbnail_path = db.Column(db.String(500), nullable=True)
    audio_path = db.Column(db.String(500), nullable=True)
    
    # Video Settings
    duration = db.Column(db.Float, nullable=True)
    resolution = db.Column(db.String(20), default='1080x1920')
    voice = db.Column(db.String(100), nullable=True)
    music_track = db.Column(db.String(200), nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='draft')  # draft, generating, ready, uploading, uploaded, failed
    error_message = db.Column(db.Text, nullable=True)
    
    # YouTube
    youtube_video_id = db.Column(db.String(50), nullable=True)
    youtube_url = db.Column(db.String(200), nullable=True)
    upload_status = db.Column(db.String(20), default='pending')  # pending, scheduled, uploading, uploaded, failed
    uploaded_at = db.Column(db.DateTime, nullable=True)
    
    # Analytics
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Video {self.title}>'
    
    @property
    def status_badge(self):
        """Return Bootstrap badge class based on status."""
        badges = {
            'draft': 'secondary',
            'generating': 'info',
            'ready': 'success',
            'uploading': 'warning',
            'uploaded': 'primary',
            'failed': 'danger'
        }
        return badges.get(self.status, 'secondary')


class Schedule(db.Model):
    """Schedule model for automated content creation and upload."""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Schedule Settings
    name = db.Column(db.String(200), nullable=False)
    niche = db.Column(db.String(50), nullable=False)
    language = db.Column(db.String(10), default='id')
    voice = db.Column(db.String(100), nullable=True)
    
    # Frequency
    frequency = db.Column(db.String(20), default='daily')  # daily, twice_daily, weekly, custom
    custom_cron = db.Column(db.String(100), nullable=True)
    preferred_time = db.Column(db.Time, nullable=True)
    timezone = db.Column(db.String(50), default='Asia/Jakarta')
    
    # Content Settings
    auto_generate_script = db.Column(db.Boolean, default=True)
    script_template = db.Column(db.Text, nullable=True)
    include_music = db.Column(db.Boolean, default=True)
    include_subtitles = db.Column(db.Boolean, default=True)
    
    # Upload Settings
    auto_upload = db.Column(db.Boolean, default=True)
    visibility = db.Column(db.String(20), default='public')  # public, private, unlisted
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)
    total_videos_created = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Schedule {self.name}>'


class ContentTemplate(db.Model):
    """Pre-built content templates for different niches."""
    __tablename__ = 'content_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    niche = db.Column(db.String(50), nullable=False)
    language = db.Column(db.String(10), default='id')
    title_template = db.Column(db.String(200), nullable=False)
    script_template = db.Column(db.Text, nullable=False)
    search_keywords = db.Column(db.Text, nullable=True)  # For finding stock media
    is_active = db.Column(db.Boolean, default=True)
    times_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Template {self.title_template}>'


class ActivityLog(db.Model):
    """Activity log for tracking system events."""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='info')  # info, success, warning, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Log {self.action} at {self.created_at}>'
