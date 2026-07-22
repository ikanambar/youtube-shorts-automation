"""Main routes - Dashboard and home."""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from database.models import db, Video, Schedule, ActivityLog
from sqlalchemy import func
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page / redirect to dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with statistics and recent activity."""
    # Statistics
    total_videos = Video.query.filter_by(user_id=current_user.id).count()
    uploaded_videos = Video.query.filter_by(user_id=current_user.id, status='uploaded').count()
    pending_videos = Video.query.filter_by(user_id=current_user.id, status='ready').count()
    active_schedules = Schedule.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    # Total views across all videos
    total_views = db.session.query(func.sum(Video.views)).filter_by(user_id=current_user.id).scalar() or 0
    
    # Recent videos
    recent_videos = Video.query.filter_by(user_id=current_user.id)\
        .order_by(Video.created_at.desc()).limit(5).all()
    
    # Recent activity
    recent_activity = ActivityLog.query.filter_by(user_id=current_user.id)\
        .order_by(ActivityLog.created_at.desc()).limit(10).all()
    
    # Videos created this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_videos = Video.query.filter(
        Video.user_id == current_user.id,
        Video.created_at >= week_ago
    ).count()
    
    stats = {
        'total_videos': total_videos,
        'uploaded_videos': uploaded_videos,
        'pending_videos': pending_videos,
        'active_schedules': active_schedules,
        'total_views': total_views,
        'weekly_videos': weekly_videos,
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_videos=recent_videos,
                         recent_activity=recent_activity)
