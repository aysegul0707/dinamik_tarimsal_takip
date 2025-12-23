import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Uygulama konfigürasyonu"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # GEE
    GEE_PROJECT_ID = os.getenv('GEE_PROJECT_ID')
    
    # Veritabanı (şimdilik opsiyonel - kullanmıyoruz)
    DATABASE_URL = os.getenv('DATABASE_URL', None)
    
    # Sentinel-2 ayarları
    CLOUD_THRESHOLD = 30  # Maksimum bulut yüzdesi (biraz artırdım)
    BASELINE_YEARS = ['2021', '2022', '2023']
    
    # Nadas tespiti için eşik
    NADAS_NDVI_THRESHOLD = 0.15
    NADAS_CONSECUTIVE_WEEKS = 8