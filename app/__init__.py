"""Flask application factory."""
from flask import Flask
from flask_login import LoginManager
from config.settings import Config
from database.models import db, User

login_manager = LoginManager()


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu.'
    login_manager.login_message_category = 'warning'
    
    # Create directories
    Config.init_dirs()
    
    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.videos import videos_bp
    from app.routes.schedule import schedule_bp
    from app.routes.youtube import youtube_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(videos_bp, url_prefix='/videos')
    app.register_blueprint(schedule_bp, url_prefix='/schedule')
    app.register_blueprint(youtube_bp, url_prefix='/youtube')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register custom Jinja2 filters
    import json as _json
    
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return _json.loads(value) if value else []
        except (_json.JSONDecodeError, TypeError):
            return []
    
    # Create database tables
    with app.app_context():
        db.create_all()
        _seed_templates()
    
    return app


def _seed_templates():
    """Seed initial content templates if empty."""
    from database.models import ContentTemplate
    
    if ContentTemplate.query.count() == 0:
        templates = [
            # Motivational
            ContentTemplate(
                niche='motivational',
                language='id',
                title_template='💪 {topic} - Motivasi Hari Ini',
                script_template='Tahukah kamu? {fact}. Ingat, {motivation}. Jangan pernah menyerah, karena {closing}.',
                search_keywords='motivation, success, sunrise, achievement'
            ),
            ContentTemplate(
                niche='motivational',
                language='id',
                title_template='🔥 Kata-Kata Bijak: {topic}',
                script_template='{quote}. Pesan dari kata-kata ini adalah {meaning}. Mulai hari ini, {action}.',
                search_keywords='inspiration, wisdom, light, path'
            ),
            # Facts
            ContentTemplate(
                niche='facts',
                language='id',
                title_template='🤯 Fakta Mengejutkan: {topic}',
                script_template='Fakta mengejutkan! {fact_1}. Tidak hanya itu, {fact_2}. Yang lebih menarik lagi, {fact_3}.',
                search_keywords='amazing, science, world, discovery'
            ),
            ContentTemplate(
                niche='facts',
                language='id',
                title_template='❓ Tahukah Kamu: {topic}',
                script_template='Tahukah kamu bahwa {fact}? Ini terjadi karena {explanation}. Menarik bukan?',
                search_keywords='knowledge, education, learning, curious'
            ),
            # Technology
            ContentTemplate(
                niche='tech',
                language='id',
                title_template='💻 Tips Tech: {topic}',
                script_template='Tips teknologi hari ini! {intro}. Caranya mudah, {steps}. Dengan tips ini, {benefit}.',
                search_keywords='technology, computer, smartphone, digital'
            ),
            # Nature
            ContentTemplate(
                niche='nature',
                language='id',
                title_template='🌍 Keajaiban Alam: {topic}',
                script_template='Alam selalu memukau kita. {intro}. Fakta menariknya, {fact}. Sungguh menakjubkan!',
                search_keywords='nature, ocean, mountain, forest, animals'
            ),
            # Health
            ContentTemplate(
                niche='health',
                language='id',
                title_template='🏃 Tips Sehat: {topic}',
                script_template='Mau hidup lebih sehat? {tip}. Menurut penelitian, {research}. Mulai dari sekarang, {action}.',
                search_keywords='health, fitness, exercise, food, wellness'
            ),
            # Finance
            ContentTemplate(
                niche='finance',
                language='id',
                title_template='💰 Tips Keuangan: {topic}',
                script_template='Tips keuangan yang wajib kamu tahu! {tip}. Banyak orang tidak sadar bahwa {insight}. Mulai {action} dari sekarang.',
                search_keywords='money, finance, business, investment, savings'
            ),
        ]
        
        for t in templates:
            db.session.add(t)
        db.session.commit()
