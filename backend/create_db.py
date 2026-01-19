from app import create_app, db

# DEĞİŞİKLİK BURADA:
# 'from app.models import User' YERİNE
# Doğrudan dosyanın kendisinden çağırıyoruz:
from app.models.user import User
from app.models.field import Field
from app.models.analysis import AnalysisResult, FieldModel

app = create_app()

with app.app_context():
    print("⏳ Veritabanı tabloları oluşturuluyor...")
    db.create_all()
    
    # Admin kontrolü
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@tarim.com', subscription_type='premium')
            admin.password = 'admin123'
            admin.save()
            print("👤 Admin oluşturuldu: admin / admin123")
    except Exception as e:
        print(f"⚠️ Admin oluşturulurken hata (önemli değil): {e}")
    
    print("✅ İŞLEM TAMAM! 'tarim.db' dosyası hazır.")