from flask import Flask
from flask_cors import CORS
import ee

import os

def create_app():
    """Flask uygulama factory"""
    # Frontend klasörünün yolunu bul
    base_dir = os.path.abspath(os.path.dirname(__file__))
    frontend_dir = os.path.join(base_dir, '..', '..', 'frontend')
    
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    app.config.from_object('app.config.Config')
    
    # CORS ayarları (frontend erişimi için)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Google Earth Engine başlat
    try:
        ee.Initialize(project=app.config['GEE_PROJECT_ID'])
        print("✅ Google Earth Engine bağlantısı başarılı")
    except Exception as e:
        print(f"⚠️ GEE bağlantı hatası: {e}")
        print("   ee.Authenticate() çalıştırmanız gerekebilir")
    
    # Blueprint'leri kaydet
    from app.routes.fields import fields_bp
    from app.routes.analysis import analysis_bp
    from app.routes.risk import risk_bp
    
    app.register_blueprint(fields_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(risk_bp, url_prefix='/api')
    
    # Ana sayfa
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    return app