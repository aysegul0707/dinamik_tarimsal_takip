import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class Config:
    """
    Proje Konfigürasyonu
    Hem teknik ayarları hem de iş kurallarını (Business Logic) içerir.
    """
    
    # --- FLASK AYARLARI ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')
    DEBUG = True
    
    # --- VERİTABANI AYARLARI (SQLite) ---
    # Not: Flask-SQLAlchemy 'SQLALCHEMY_DATABASE_URI' değişkenine ihtiyaç duyar.
    # Bu kod, proje klasöründe 'tarim.db' dosyasını otomatik bulur/oluşturur.
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '..', 'tarim.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- GOOGLE EARTH ENGINE ---
    GEE_PROJECT_ID = os.getenv('GEE_PROJECT_ID')
    
    # --- SENTINEL-2 VE VERİ AYARLARI ---
    # Bulut Maskeleme: %30 üzeri bulutlu görüntüleri analizden çıkar
    CLOUD_THRESHOLD = 30
    
    # Baseline (Normal) Hesabı İçin Kullanılacak Yıllar
    # DÜZELTME: Sentinel-2 verileri 2017 öncesi kararsız olabilir. 
    # Son 5-6 yıl en sağlıklı aralıktır.
    BASELINE_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
    
    # Yıllık Nadas Tespiti
    # Bir yılın maksimum NDVI değeri 0.35'i geçmediyse, o yıl ekim yapılmamıştır.
    NADAS_YEARLY_MAX_THRESHOLD = 0.35
    
    # --- RİSK EŞİKLERİ (Z-Score - Standart Sapma) ---
    # warning: Kullanıcıya sarı uyarı göster
    # critical: Kullanıcıya kırmızı alarm göster
    Z_THRESHOLDS = {
        'ndvi': {'warning': 1.5, 'critical': 2.5}, # Bitki Sağlığı
        'ndmi': {'warning': 1.5, 'critical': 2.5}, # Su İçeriği
        'msi':  {'warning': 1.5, 'critical': 2.5}  # Nem Stresi
    }
    
    # --- ABONELİK LİMİTLERİ (Business Logic) ---
    SUBSCRIPTION_LIMITS = {
        'free': {
            'max_fields': 3,            # Maksimum tarla sayısı
            'report_frequency': 'weekly', # Rapor sıklığı
            'max_history_days': 90,     # Geçmişe dönük kaç gün görebilir
            'high_res_export': False    # Yüksek çözünürlüklü indirme
        },
        'premium': {
            'max_fields': 20,
            'report_frequency': 'daily',
            'max_history_days': 365,
            'high_res_export': True
        }
    }
    
    # --- EMAIL AYARLARI (İsteğe Bağlı) ---
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_USE_TLS = True