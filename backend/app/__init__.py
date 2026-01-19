from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import ee
import os

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    """Uygulama Factory"""
    app = Flask(__name__)
    
    # Ayarları yükle
    app.config.from_object('app.config.Config')
    
    # JWT Ayarı (Config dosyasına eklemeyi unuttuysak diye default değer)
    app.config.setdefault('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    
    # Eklentileri başlat
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    db.init_app(app)
    jwt.init_app(app)
    
    # GEE Başlat
    try:
        if app.config.get('GEE_PROJECT_ID'):
            ee.Initialize(project=app.config['GEE_PROJECT_ID'])
        else:
            ee.Initialize()
        print("✅ GEE Bağlantısı Başarılı")
    except Exception as e:
        print(f"⚠️ GEE Hatası: {e}")
    
    # Klasör kontrolü
    ml_dir = 'ml/models'
    if not os.path.exists(ml_dir):
        os.makedirs(ml_dir)

    from app import models

    # --- ROUTE'LARI KAYDET ---
    # Artık route'ları güvenle açabiliriz çünkü içlerini birazdan güncelleyeceğiz.
    
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    from app.routes.fields import fields_bp
    app.register_blueprint(fields_bp, url_prefix='/api')
    
    # Analiz rotasını şimdilik kapalı tutabilirsin veya açabilirsin
    # from app.routes.analysis import analysis_bp
    # app.register_blueprint(analysis_bp, url_prefix='/api')
    
    @app.route('/')
    def index():
        return {'status': 'running', 'version': '3.0'}
    
    return app