"""Uygulama başlatıcı"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 TARIMSAL KURAKLIK TAKİP SİSTEMİ")
    print("=" * 60)
    print("📍 http://localhost:5000")
    print("📖 API Dokümantasyonu: http://localhost:5000/health")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)