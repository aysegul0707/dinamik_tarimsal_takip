"""Risk analizi endpoint'leri"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.services.gee_service import GEEService
from app.services.baseline_service import BaselineService
from app.services.ml_service import MLService

risk_bp = Blueprint('risk', __name__)

# Baseline cache (geçici, sonra DB'ye taşınacak)
baseline_cache = {}


@risk_bp.route('/baseline', methods=['POST'])
def calculate_baseline():
    """
    Tarla için baseline hesapla
    
    Request body:
    {
        "field_id": "1",
        "coordinates": [32.5, 37.9]
    }
    """
    data = request.get_json()
    
    field_id = data.get('field_id')
    coordinates = data.get('coordinates')
    
    if not coordinates:
        return jsonify({
            'success': False,
            'error': 'Koordinatlar gerekli'
        }), 400
    
    try:
        baseline = BaselineService.calculate_baseline(coordinates)
        
        if not baseline or not baseline['baseline']:
            return jsonify({
                'success': False,
                'error': 'Baseline hesaplanamadı, yeterli veri yok'
            }), 404
        
        # Cache'e kaydet
        if field_id:
            baseline_cache[field_id] = baseline
        
        return jsonify({
            'success': True,
            'baseline': baseline
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@risk_bp.route('/risk', methods=['POST'])
def calculate_risk():
    """
    Risk analizi yap
    
    Request body:
    {
        "field_id": "1",        (opsiyonel, cache'den baseline almak için)
        "coordinates": [32.5, 37.9]
    }
    """
    data = request.get_json()
    
    field_id = data.get('field_id')
    coordinates = data.get('coordinates')
    
    if not coordinates:
        return jsonify({
            'success': False,
            'error': 'Koordinatlar gerekli'
        }), 400
    
    try:
        # Güncel durum
        current = GEEService.get_current_status(coordinates)
        
        if current is None:
            return jsonify({
                'success': False,
                'error': 'Güncel veri bulunamadı'
            }), 404
        
        # Baseline (cache'den veya yeni hesapla)
        if field_id and field_id in baseline_cache:
            baseline = baseline_cache[field_id]
        else:
            baseline = BaselineService.calculate_baseline(coordinates)
            if field_id:
                baseline_cache[field_id] = baseline
        
        if not baseline or not baseline['baseline']:
            return jsonify({
                'success': False,
                'error': 'Baseline hesaplanamadı'
            }), 404
        
        # Son 4 haftanın verisi (trend için)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        timeseries = GEEService.get_timeseries(coordinates, start_date, end_date)
        
        # Risk hesapla
        risk = MLService.predict_risk(current, baseline, timeseries)
        
        return jsonify({
            'success': True,
            'current': current,
            'risk': risk
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500