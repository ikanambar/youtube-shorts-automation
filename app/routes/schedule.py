"""Schedule management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from database.models import db, Schedule, ActivityLog
from config.settings import NICHES, TTS_VOICES, Config
from datetime import time as dt_time

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/')
@login_required
def index():
    """List all schedules."""
    schedules = Schedule.query.filter_by(user_id=current_user.id)\
        .order_by(Schedule.created_at.desc()).all()
    return render_template('schedule/index.html', schedules=schedules, niches=NICHES)


@schedule_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new schedule."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        niche = request.form.get('niche', 'motivational')
        frequency = request.form.get('frequency', 'daily')
        preferred_time = request.form.get('preferred_time', '09:00')
        voice = request.form.get('voice', Config.TTS_VOICE)
        language = request.form.get('language', 'id')
        auto_upload = request.form.get('auto_upload', 'on') == 'on'
        visibility = request.form.get('visibility', 'public')
        include_music = request.form.get('include_music', 'on') == 'on'
        include_subtitles = request.form.get('include_subtitles', 'on') == 'on'
        
        if not name:
            flash('Nama jadwal wajib diisi.', 'danger')
            return redirect(url_for('schedule.create'))
        
        # Parse time
        try:
            hour, minute = preferred_time.split(':')
            pref_time = dt_time(int(hour), int(minute))
        except (ValueError, TypeError):
            pref_time = dt_time(9, 0)
        
        schedule = Schedule(
            user_id=current_user.id,
            name=name,
            niche=niche,
            language=language,
            voice=voice,
            frequency=frequency,
            preferred_time=pref_time,
            auto_upload=auto_upload,
            visibility=visibility,
            include_music=include_music,
            include_subtitles=include_subtitles,
            is_active=True
        )
        db.session.add(schedule)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user.id,
            action='Schedule Created',
            details=f'Schedule "{name}" created ({frequency})',
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Jadwal berhasil dibuat!', 'success')
        return redirect(url_for('schedule.index'))
    
    return render_template('schedule/create.html', 
                         niches=NICHES, 
                         voices=TTS_VOICES,
                         default_voice=Config.TTS_VOICE)


@schedule_bp.route('/<int:schedule_id>/toggle', methods=['POST'])
@login_required
def toggle(schedule_id):
    """Toggle schedule active/inactive."""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    schedule.is_active = not schedule.is_active
    db.session.commit()
    
    status = 'diaktifkan' if schedule.is_active else 'dinonaktifkan'
    flash(f'Jadwal "{schedule.name}" {status}.', 'success')
    return redirect(url_for('schedule.index'))


@schedule_bp.route('/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete(schedule_id):
    """Delete a schedule."""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    name = schedule.name
    db.session.delete(schedule)
    db.session.commit()
    
    flash(f'Jadwal "{name}" berhasil dihapus.', 'success')
    return redirect(url_for('schedule.index'))


@schedule_bp.route('/<int:schedule_id>/run-now', methods=['POST'])
@login_required
def run_now(schedule_id):
    """Manually trigger a scheduled task."""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    
    from modules.scheduler import run_schedule_task
    try:
        run_schedule_task(schedule.id)
        flash(f'Jadwal "{schedule.name}" sedang dijalankan!', 'info')
    except Exception as e:
        flash(f'Gagal menjalankan jadwal: {str(e)}', 'danger')
    
    return redirect(url_for('schedule.index'))
