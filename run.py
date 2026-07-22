"""
YouTube Shorts Automation - Main Entry Point
============================================
Run this file to start the application.

Usage:
    python run.py
"""
import os
import sys
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", 
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add("logs/app.log", rotation="10 MB", retention="7 days", level="DEBUG")

from app import create_app
from config.settings import Config

# Create app
app = create_app()

# Initialize scheduler (only in main process, not reloader)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    try:
        from modules.scheduler import init_scheduler
        scheduler = init_scheduler(app)
        logger.info("Background scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler initialization failed: {e}")


def add_template_filters():
    """Add custom Jinja2 template filters."""
    import json
    
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object."""
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError):
            return []


add_template_filters()


if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    logger.info("=" * 50)
    logger.info("  YouTube Shorts Automation")
    logger.info("  Starting server on http://localhost:5000")
    logger.info("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG,
        use_reloader=Config.DEBUG
    )
