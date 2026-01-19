from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.field import Field
from app.models.user import User
import json

fields_bp = Blueprint('fields', __name__)

@fields_bp.route('/fields', methods=['GET'])
@jwt_required()
def list_fields():
    """Giriş yapan kullanıcının tarlalarını listele"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Kullanıcının tarlalarını çek (SQLAlchemy Dynamic Relationship)
    fields = user.fields.all()
    
    results = []
    for f in fields:
        results.append({
            'id': f.id,
            'name': f.name,
            'location': f.location_name,
            'coordinates': json.loads(f.coordinates), # String'i tekrar JSON yap
            'crop_type': f.crop_type,
            'created_at': f.created_at.isoformat(),
            'model_ready': f.ml_model.is_ready if f.ml_model else False
        })
        
    return jsonify({'success': True, 'fields': results})

@fields_bp.route('/fields', methods=['POST'])
@jwt_required()
def create_field():
    """Yeni tarla kaydet (GeoJSON) - Limit Kontrollü"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # --- ABONELİK LİMİT KONTROLÜ ---
    limits = current_app.config['SUBSCRIPTION_LIMITS'].get(user.subscription_type, current_app.config['SUBSCRIPTION_LIMITS']['free'])
    current_field_count = user.fields.count()
    
    if current_field_count >= limits['max_fields']:
        return jsonify({
            'error': f'Tarla limitine ulaştınız ({limits["max_fields"]} adet). Daha fazlası için Premium\'a geçin.',
            'upgrade_required': True
        }), 403
    # ---------------------------------

    data = request.get_json()
    
    if not data or 'name' not in data or 'coordinates' not in data:
        return jsonify({'error': 'Eksik veri: İsim ve koordinatlar şart'}), 400
        
    try:
        # Koordinatları String olarak saklıyoruz
        coords_str = json.dumps(data['coordinates'])
        
        new_field = Field(
            name=data['name'],
            location_name=data.get('location', 'Bilinmiyor'),
            coordinates=coords_str,
            crop_type=data.get('crop_type'),
            user_id=user_id
        )
        new_field.save()
        
        return jsonify({
            'message': 'Tarla başarıyla kaydedildi', 
            'id': new_field.id,
            'limit_status': f"{current_field_count + 1}/{limits['max_fields']}"
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Kayıt hatası: {str(e)}'}), 500

@fields_bp.route('/fields/<int:field_id>', methods=['DELETE'])
@jwt_required()
def delete_field(field_id):
    """Tarla sil"""
    user_id = get_jwt_identity()
    field = Field.query.get_or_404(field_id)
    
    # Başkasının tarlasını silemezsin
    if field.user_id != user_id:
        return jsonify({'error': 'Yetkisiz işlem'}), 403
        
    field.delete()
    return jsonify({'message': 'Tarla silindi'})