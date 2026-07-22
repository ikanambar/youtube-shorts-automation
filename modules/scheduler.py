"""
Scheduler Module
=================
Automated content creation and upload scheduling.
Uses APScheduler for job management.
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


def init_scheduler(app):
    """
    Initialize the APScheduler with the Flask app.
    
    Sets up periodic jobs for:
    - Checking and running due schedules
    - Cleaning up old temporary files
    """
    from flask_apscheduler import APScheduler
    
    scheduler = APScheduler()
    
    # Configure scheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    app.config['JOBS'] = [
        {
            'id': 'check_schedules',
            'func': 'modules.scheduler:check_and_run_schedules',
            'trigger': 'interval',
            'minutes': 15,  # Check every 15 minutes
            'kwargs': {'app': app}
        },
        {
            'id': 'cleanup_temp',
            'func': 'modules.scheduler:cleanup_temp_files',
            'trigger': 'interval',
            'hours': 6,  # Every 6 hours
            'kwargs': {'app': app}
        }
    ]
    
    scheduler.init_app(app)
    scheduler.start()
    
    logger.info("Scheduler initialized and started")
    return scheduler


def check_and_run_schedules(app=None):
    """
    Check all active schedules and run any that are due.
    
    This is called periodically by APScheduler.
    """
    if not app:
        return
    
    with app.app_context():
        from database.models import db, Schedule
        
        now = datetime.utcnow()
        
        # Find active schedules that are due
        active_schedules = Schedule.query.filter_by(is_active=True).all()
        
        for schedule in active_schedules:
            if _is_schedule_due(schedule, now):
                try:
                    logger.info(f"Running schedule: {schedule.name}")
                    run_schedule_task(schedule.id)
                    
                    # Update last/next run
                    schedule.last_run = now
                    schedule.next_run = _calculate_next_run(schedule)
                    schedule.total_videos_created += 1
                    db.session.commit()
                    
                except Exception as e:
                    logger.error(f"Schedule {schedule.name} failed: {e}")


def run_schedule_task(schedule_id: int):
    """
    Execute a single schedule task: generate content + create video + optional upload.
    
    Args:
        schedule_id: Database ID of the Schedule
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from database.models import db, Schedule, Video, ActivityLog
        from modules.content_generator import generate_script
        from modules.video_engine import generate_video_task
        from modules.youtube_uploader import upload_video_task
        
        schedule = Schedule.query.get(schedule_id)
        if not schedule or not schedule.is_active:
            logger.warning(f"Schedule {schedule_id} not found or inactive")
            return
        
        user_id = schedule.user_id
        
        try:
            # Step 1: Generate content
            logger.info(f"[Schedule {schedule.name}] Generating content...")
            content = generate_script(
                niche=schedule.niche,
                language=schedule.language
            )
            
            # Step 2: Create video record
            video = Video(
                user_id=user_id,
                title=content['title'],
                script=content['script'],
                niche=schedule.niche,
                language=schedule.language,
                voice=schedule.voice,
                hashtags=json.dumps(content['hashtags']),
                description=f"{content['title']}\n\n{' '.join(content['hashtags'])}",
                status='draft'
            )
            db.session.add(video)
            db.session.commit()
            
            # Step 3: Generate video
            logger.info(f"[Schedule {schedule.name}] Generating video...")
            generate_video_task(video.id)
            
            # Step 4: Auto-upload if enabled
            if schedule.auto_upload:
                logger.info(f"[Schedule {schedule.name}] Uploading to YouTube...")
                try:
                    upload_video_task(video.id, user_id)
                except Exception as e:
                    logger.warning(f"Auto-upload failed: {e}")
                    # Video is still ready, just not uploaded
            
            # Log success
            log = ActivityLog(
                user_id=user_id,
                action='Scheduled Task Completed',
                details=f'Schedule "{schedule.name}" created video: {content["title"]}',
                status='success'
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"[Schedule {schedule.name}] Task completed successfully")
            
        except Exception as e:
            logger.error(f"[Schedule {schedule.name}] Task failed: {e}")
            
            log = ActivityLog(
                user_id=user_id,
                action='Scheduled Task Failed',
                details=f'Schedule "{schedule.name}" failed: {str(e)}',
                status='error'
            )
            db.session.add(log)
            db.session.commit()
            
            raise


def _is_schedule_due(schedule, now: datetime) -> bool:
    """Check if a schedule should run now."""
    
    # If never run, it's due
    if not schedule.last_run:
        return True
    
    last_run = schedule.last_run
    
    if schedule.frequency == 'daily':
        # Run once per day
        return (now - last_run) >= timedelta(hours=23)
    
    elif schedule.frequency == 'twice_daily':
        # Run every 12 hours
        return (now - last_run) >= timedelta(hours=11)
    
    elif schedule.frequency == 'weekly':
        # Run once per week
        return (now - last_run) >= timedelta(days=6, hours=23)
    
    elif schedule.frequency == 'every_3_days':
        return (now - last_run) >= timedelta(days=2, hours=23)
    
    elif schedule.frequency == 'hourly':
        # For testing
        return (now - last_run) >= timedelta(minutes=55)
    
    return False


def _calculate_next_run(schedule) -> datetime:
    """Calculate the next run time for a schedule."""
    now = datetime.utcnow()
    
    if schedule.frequency == 'daily':
        return now + timedelta(days=1)
    elif schedule.frequency == 'twice_daily':
        return now + timedelta(hours=12)
    elif schedule.frequency == 'weekly':
        return now + timedelta(weeks=1)
    elif schedule.frequency == 'every_3_days':
        return now + timedelta(days=3)
    elif schedule.frequency == 'hourly':
        return now + timedelta(hours=1)
    
    return now + timedelta(days=1)


def cleanup_temp_files(app=None):
    """Remove old temporary files to save disk space."""
    if not app:
        return
    
    with app.app_context():
        import shutil
        from config.settings import Config
        
        temp_dir = Config.TEMP_FOLDER
        if temp_dir.exists():
            # Remove files older than 24 hours
            now = datetime.now().timestamp()
            for f in temp_dir.iterdir():
                if f.is_file():
                    file_age = now - f.stat().st_mtime
                    if file_age > 86400:  # 24 hours
                        f.unlink()
                        logger.debug(f"Cleaned temp file: {f}")
        
        logger.info("Temp cleanup completed")
