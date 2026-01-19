"""Risk analizi endpoint'leri"""
from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import pandas as pd
from app.services.gee_service import GEEService
from app.services.baseline_service import BaselineService
from app.services.ml_service import MLService
from app.models import Field, Baseline, RiskLog
import json

risk_bp = Blueprint('risk', __name__)


@risk_bp.route('/baseline/calculate', methods=['POST'])
def calculate_baseline():
    """Baseline hesapla ve kaydet"""
    data = request.get_json()
    
    field_id = data.get('field_id')
    coordinates = data.get('coordinates')
    
    if not coordinates:
        return jsonify({
            'success': False,
            'error': 'Koordinatlar gerekli'
        }), 400
    
    try:
        # Baseline hesapla
        baseline = BaselineService.calculate_baseline(coordinates)
        
        if not baseline or not baseline['baseline']:
            return jsonify({
                'success': False,
                'error': 'Baseline hesaplanamadı, yeterli veri yok'
            }), 404
        
        # Veritabanına kaydet
        if field_id:
            # Tarla durumunu güncelle
            Field.update_status(field_id, 'baseline_ready')
            
            # Baseline'ı kaydet
            for row in baseline['baseline']:
                row['years_used'] = baseline['years_used']
            
            Baseline.save_bulk(field_id, baseline['baseline'])
        
        return jsonify({
            'success': True,
            'baseline': baseline
        })
        
    except Exception as e:
        # Hata durumunda tarla durumunu güncelle
        if field_id:
            Field.update_status(field_id, 'error')
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@risk_bp.route('/baseline/<int:field_id>', methods=['GET'])
def get_baseline(field_id):
    """Tarlanın baseline'ını getir"""
    try:
        baseline_rows = Baseline.get_by_field(field_id)
        
        if not baseline_rows:
            return jsonify({
                'success': False,
                'error': 'Baseline bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'baseline': baseline_rows
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@risk_bp.route('/risk', methods=['POST'])
def calculate_risk():
    """Risk analizi yap"""
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
        
        # Baseline al
        if field_id:
            baseline_rows = Baseline.get_by_field(field_id)
            if baseline_rows:
                baseline_df = pd.DataFrame(baseline_rows)
            else:
                # Baseline yoksa hesapla
                baseline_result = BaselineService.calculate_baseline(coordinates)
                if not baseline_result:
                    return jsonify({
                        'success': False,
                        'error': 'Baseline hesaplanamadı'
                    }), 404
                baseline_df = pd.DataFrame(baseline_result['baseline'])
        else:
            # Field ID yoksa anlık hesapla
            baseline_result = BaselineService.calculate_baseline(coordinates)
            if not baseline_result:
                return jsonify({
                    'success': False,
                    'error': 'Baseline hesaplanamadı'
                }), 404
            baseline_df = pd.DataFrame(baseline_result['baseline'])
        
        # Son 30 günün verisi (trend için)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        timeseries = GEEService.get_timeseries(coordinates, start_date, end_date)
        
        # Risk hesapla
        risk = MLService.predict_risk(current, baseline_df, timeseries, field_id)
        
        # Veritabanına kaydet
        if field_id:
            log_data = {
                'date': current['date'],
                'ndvi': current.get('ndvi_mean'),
                'ndmi': current.get('ndmi_mean'),
                'msi': current.get('msi_mean'),
                'z_ndvi': risk['rule_based']['z_scores'].get('ndvi'),
                'z_ndmi': risk['rule_based']['z_scores'].get('ndmi'),
                'z_msi': risk['rule_based']['z_scores'].get('msi'),
                'risk_score': risk['final_score'],
                'risk_level': risk['final_level'],
                'alerts': risk['rule_based']['alerts']
            }
            RiskLog.create(field_id, log_data)
        
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


@risk_bp.route('/risk/history/<int:field_id>', methods=['GET'])
def get_risk_history(field_id):
    """Risk geçmişi"""
    try:
        logs = RiskLog.get_by_field(field_id, limit=30)
        
        # Alerts'i parse et
        for log in logs:
            if log.get('alerts'):
                log['alerts'] = json.loads(log['alerts'])
        
        return jsonify({
            'success': True,
            'history': logs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500