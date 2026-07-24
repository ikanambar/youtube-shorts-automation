"""Video management routes."""
import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, abort
from flask_login import login_required, current_user
from database.models import db, Video, ActivityLog, ContentTemplate
from config.settings import Config, NICHES, TTS_VOICES

videos_bp = Blueprint('videos', __name__)


@videos_bp.route('/<int:video_id>/stream')
@login_required
def stream(video_id):
    """Stream the video file."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    if not video.video_path or not os.path.exists(video.video_path):
        abort(404)
    return send_file(video.video_path, mimetype='video/mp4')


@videos_bp.route('/<int:video_id>/thumbnail')
@login_required
def thumbnail(video_id):
    """Serve the video thumbnail."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    if not video.thumbnail_path or not os.path.exists(video.thumbnail_path):
        abort(404)
    return send_file(video.thumbnail_path, mimetype='image/jpeg')


@videos_bp.route('/')
@login_required
def index():
    """List all videos."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    niche_filter = request.args.get('niche', 'all')
    
    query = Video.query.filter_by(user_id=current_user.id)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if niche_filter != 'all':
        query = query.filter_by(niche=niche_filter)
    
    videos = query.order_by(Video.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    
    return render_template('videos/index.html', 
                         videos=videos, 
                         niches=NICHES,
                         status_filter=status_filter,
                         niche_filter=niche_filter)


@videos_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new video."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        niche = request.form.get('niche', 'motivational')
        script = request.form.get('script', '').strip()
        voice = request.form.get('voice', Config.TTS_VOICE)
        include_music = request.form.get('include_music', 'on') == 'on'
        include_subtitles = request.form.get('include_subtitles', 'on') == 'on'
        language = request.form.get('language', 'id')
        visual_style = request.form.get('visual_style', 'real_video')
        custom_prompt = request.form.get('custom_prompt', '').strip()
        
        if not title:
            flash('Judul video wajib diisi.', 'danger')
            return redirect(url_for('videos.create'))
        
        if not script:
            flash('Script video wajib diisi.', 'danger')
            return redirect(url_for('videos.create'))
        
        # Get hashtags for niche
        niche_data = NICHES.get(niche, NICHES['motivational'])
        hashtags = json.dumps(niche_data['hashtags'])
        
        # Create video record
        video = Video(
            user_id=current_user.id,
            title=title,
            script=script,
            niche=niche,
            language=language,
            voice=voice,
            hashtags=hashtags,
            visual_style=visual_style,
            custom_prompt=custom_prompt,
            description=f"{title}\n\n{' '.join(niche_data['hashtags'])}",
            status='draft'
        )
        db.session.add(video)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='Video Created',
            details=f'Video "{title}" created as draft',
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Video berhasil dibuat! Klik "Generate" untuk membuat video.', 'success')
        return redirect(url_for('videos.detail', video_id=video.id))
    
    return render_template('videos/create.html', 
                         niches=NICHES, 
                         voices=TTS_VOICES,
                         default_voice=Config.TTS_VOICE)


@videos_bp.route('/<int:video_id>')
@login_required
def detail(video_id):
    """Video detail page."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    return render_template('videos/detail.html', video=video)


@videos_bp.route('/<int:video_id>/generate', methods=['POST'])
@login_required
def generate(video_id):
    """Start video generation process."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    
    if video.status not in ('draft', 'failed'):
        flash('Video sudah dalam proses atau selesai.', 'warning')
        return redirect(url_for('videos.detail', video_id=video.id))
    
    # Update status
    video.status = 'generating'
    db.session.commit()
    
    # Trigger async generation
    from modules.video_engine import generate_video_task
    try:
        generate_video_task(video.id)
        flash('Video sedang diproses! Tunggu beberapa menit.', 'info')
    except Exception as e:
        video.status = 'failed'
        video.error_message = str(e)
        db.session.commit()
        flash(f'Gagal membuat video: {str(e)}', 'danger')
    
    return redirect(url_for('videos.detail', video_id=video.id))


@videos_bp.route('/<int:video_id>/delete', methods=['POST'])
@login_required
def delete(video_id):
    """Delete a video."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    
    # Delete associated files
    import os
    for path in [video.video_path, video.thumbnail_path, video.audio_path]:
        if path and os.path.exists(path):
            os.remove(path)
    
    title = video.title
    db.session.delete(video)
    db.session.commit()
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action='Video Deleted',
        details=f'Video "{title}" deleted',
        status='info'
    )
    db.session.add(log)
    db.session.commit()
    
    flash('Video berhasil dihapus.', 'success')
    return redirect(url_for('videos.index'))


@videos_bp.route('/<int:video_id>/upload', methods=['POST'])
@login_required
def upload_to_youtube(video_id):
    """Upload video to YouTube."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    
    if not current_user.youtube_connected:
        flash('Hubungkan akun YouTube terlebih dahulu di Settings.', 'warning')
        return redirect(url_for('youtube.settings'))
    
    if video.status != 'ready':
        flash('Video belum siap untuk diupload.', 'warning')
        return redirect(url_for('videos.detail', video_id=video.id))
    
    # Trigger upload
    from modules.youtube_uploader import upload_video_task
    try:
        video.upload_status = 'uploading'
        db.session.commit()
        
        upload_video_task(video.id, current_user.id)
        flash('Video sedang diupload ke YouTube!', 'info')
    except Exception as e:
        video.upload_status = 'failed'
        video.error_message = str(e)
        db.session.commit()
        flash(f'Gagal upload: {str(e)}', 'danger')
    
    return redirect(url_for('videos.detail', video_id=video.id))
