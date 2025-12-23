"""Tarla yönetimi endpoint'leri"""
from flask import Blueprint, request, jsonify

fields_bp = Blueprint('fields', __name__)

# Geçici in-memory depolama (sonra PostgreSQL'e taşınacak)
fields_db = {}


@fields_bp.route('/fields', methods=['GET'])
def list_fields():
    """Tüm tarlaları listele"""
    return jsonify({
        'success': True,
        'fields': list(fields_db.values())
    })


@fields_bp.route('/fields', methods=['POST'])
def create_field():
    """Yeni tarla ekle"""
    data = request.get_json()
    
    if not data or 'coordinates' not in data:
        return jsonify({
            'success': False,
            'error': 'Koordinatlar gerekli'
        }), 400
    
    field_id = str(len(fields_db) + 1)
    
    field = {
        'id': field_id,
        'name': data.get('name', f'Tarla {field_id}'),
        'coordinates': data['coordinates'],
        'created_at': data.get('created_at'),
        'baseline_calculated': False
    }
    
    fields_db[field_id] = field
    
    return jsonify({
        'success': True,
        'field': field
    }), 201


@fields_bp.route('/fields/<field_id>', methods=['GET'])
def get_field(field_id):
    """Tarla detayı"""
    if field_id not in fields_db:
        return jsonify({
            'success': False,
            'error': 'Tarla bulunamadı'
        }), 404
    
    return jsonify({
        'success': True,
        'field': fields_db[field_id]
    })


@fields_bp.route('/fields/<field_id>', methods=['DELETE'])
def delete_field(field_id):
    """Tarla sil"""
    if field_id not in fields_db:
        return jsonify({
            'success': False,
            'error': 'Tarla bulunamadı'
        }), 404
    
    del fields_db[field_id]
    
    return jsonify({
        'success': True,
        'message': 'Tarla silindi'
    })