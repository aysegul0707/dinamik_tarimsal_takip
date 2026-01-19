from flask import Blueprint, request, jsonify
from app.models.user import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Yeni kullanıcı kaydı"""
    data = request.get_json()
    
    # 1. Veri Kontrolü
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({'error': 'Eksik bilgi: username, email ve password zorunludur'}), 400
        
    # 2. Kullanıcı Zaten Var mı?
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Bu kullanıcı adı alınmış'}), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Bu email zaten kayıtlı'}), 400
    
    # 3. Yeni Kullanıcı Oluştur (SQLAlchemy ile)
    try:
        new_user = User(
            username=data['username'],
            email=data['email'],
            subscription_type='free' # Varsayılan ücretsiz
        )
        new_user.password = data['password'] # Setter metodu şifreyi otomatik hashler
        new_user.save() # Veritabanına kaydet
        
        return jsonify({'message': 'Kayıt başarılı! Giriş yapabilirsiniz.'}), 201
    except Exception as e:
        return jsonify({'error': f'Kayıt sırasında hata oluştu: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Giriş yap ve Token al"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Kullanıcı adı ve şifre gerekli'}), 400
    
    # Veritabanında kullanıcıyı bul
    user = User.query.filter_by(username=data.get('username')).first()
    
    # Kullanıcı yoksa veya şifre yanlışsa
    if not user or not user.check_password(data.get('password')):
        return jsonify({'error': 'Geçersiz kullanıcı adı veya şifre'}), 401
        
    # Başarılı ise Token oluştur (7 gün geçerli)
    token = create_access_token(identity=user.id, expires_delta=timedelta(days=7))
    
    return jsonify({
        'message': 'Giriş başarılı',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.subscription_type
        }
    })

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Token sahibinin bilgilerini getir (Profil Sayfası İçin)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'subscription': user.subscription_type,
        'created_at': user.created_at.isoformat()
    })