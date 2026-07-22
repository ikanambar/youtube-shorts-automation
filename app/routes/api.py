"""API routes for AJAX operations."""
import json
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database.models import db, Video, ContentTemplate
from config.settings import NICHES

api_bp = Blueprint('api', __name__)


@api_bp.route('/generate-script', methods=['POST'])
@login_required
def generate_script():
    """Generate a script using AI or templates."""
    data = request.get_json()
    niche = data.get('niche', 'motivational')
    topic = data.get('topic', '')
    language = data.get('language', 'id')
    
    from modules.content_generator import generate_script
    
    try:
        result = generate_script(niche=niche, topic=topic, language=language)
        return jsonify({
            'success': True,
            'title': result['title'],
            'script': result['script'],
            'hashtags': result['hashtags']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/video-status/<int:video_id>')
@login_required
def video_status(video_id):
    """Get current video generation/upload status."""
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    return jsonify({
        'id': video.id,
        'status': video.status,
        'upload_status': video.upload_status,
        'video_path': video.video_path,
        'youtube_url': video.youtube_url,
        'error_message': video.error_message
    })


@api_bp.route('/templates/<niche>')
@login_required
def get_templates(niche):
    """Get content templates for a specific niche."""
    templates = ContentTemplate.query.filter_by(niche=niche, is_active=True).all()
    return jsonify({
        'templates': [
            {
                'id': t.id,
                'title_template': t.title_template,
                'script_template': t.script_template,
            }
            for t in templates
        ]
    })


@api_bp.route('/stats')
@login_required
def stats():
    """Get dashboard statistics."""
    from sqlalchemy import func
    
    total_videos = Video.query.filter_by(user_id=current_user.id).count()
    uploaded = Video.query.filter_by(user_id=current_user.id, status='uploaded').count()
    total_views = db.session.query(func.sum(Video.views))\
        .filter_by(user_id=current_user.id).scalar() or 0
    
    return jsonify({
        'total_videos': total_videos,
        'uploaded': uploaded,
        'total_views': total_views,
        'youtube_connected': current_user.youtube_connected
    })


@api_bp.route('/niches')
@login_required
def get_niches():
    """Get available niches."""
    return jsonify(NICHES)
