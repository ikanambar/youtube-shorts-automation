"""YouTube integration routes."""
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from database.models import db, ActivityLog
from config.settings import Config

youtube_bp = Blueprint('youtube', __name__)


@youtube_bp.route('/settings')
@login_required
def settings():
    """YouTube connection settings."""
    return render_template('youtube/settings.html')


@youtube_bp.route('/connect')
@login_required
def connect():
    """Start YouTube OAuth2 flow."""
    from modules.youtube_uploader import get_auth_url
    
    if not Config.YOUTUBE_CLIENT_ID or not Config.YOUTUBE_CLIENT_SECRET:
        flash('YouTube API credentials belum dikonfigurasi. Periksa file .env', 'danger')
        return redirect(url_for('youtube.settings'))
    
    auth_url = get_auth_url()
    return redirect(auth_url)


@youtube_bp.route('/callback')
@login_required
def callback():
    """Handle YouTube OAuth2 callback."""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        flash(f'Gagal menghubungkan YouTube: {error}', 'danger')
        return redirect(url_for('youtube.settings'))
    
    if not code:
        flash('Kode autorisasi tidak ditemukan.', 'danger')
        return redirect(url_for('youtube.settings'))
    
    from modules.youtube_uploader import exchange_code_for_tokens, get_channel_info
    
    try:
        tokens = exchange_code_for_tokens(code)
        
        # Save tokens
        current_user.youtube_access_token = tokens.get('access_token')
        current_user.youtube_refresh_token = tokens.get('refresh_token')
        current_user.youtube_connected = True
        
        # Get channel info
        channel_info = get_channel_info(tokens.get('access_token'))
        if channel_info:
            current_user.youtube_channel_name = channel_info.get('title')
            current_user.youtube_channel_id = channel_info.get('id')
        
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='YouTube Connected',
            details=f'Connected to channel: {current_user.youtube_channel_name}',
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'YouTube berhasil dihubungkan! Channel: {current_user.youtube_channel_name}', 'success')
    except Exception as e:
        flash(f'Gagal menghubungkan YouTube: {str(e)}', 'danger')
    
    return redirect(url_for('youtube.settings'))


@youtube_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect YouTube account."""
    current_user.youtube_access_token = None
    current_user.youtube_refresh_token = None
    current_user.youtube_token_expiry = None
    current_user.youtube_channel_name = None
    current_user.youtube_channel_id = None
    current_user.youtube_connected = False
    db.session.commit()
    
    flash('YouTube berhasil diputuskan.', 'info')
    return redirect(url_for('youtube.settings'))
