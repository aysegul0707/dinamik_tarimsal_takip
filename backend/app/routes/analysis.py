"""Analiz endpoint'leri"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.services.gee_service import GEEService
from app.services.baseline_service import BaselineService

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/analyze', methods=['POST'])
def analyze():
    """Genel analiz"""
    data = request.get_json()
    
    if not data or 'coordinates' not in data:
        return jsonify({
            'success': False,
            'error': 'Koordinatlar gerekli'
        }), 400
    
    coordinates = data['coordinates']
    end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = data.get('start_date',
        (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
    
    try:
        # Zaman serisi çek
        df = GEEService.get_timeseries(coordinates, start_date, end_date)
        
        if df.empty:
            return jsonify({
                'success': False,
                'error': 'Bu tarih aralığında veri bulunamadı'
            }), 404
        
        # Kaliteli veri filtresi
        df_quality = df[df['clear_pixel_ratio'] > 0.5]
        
        # Özet
        summary = {
            'total_images': len(df),
            'quality_images': len(df_quality),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d')
            },
            'ndvi': {
                'mean': float(df_quality['ndvi_mean'].mean()),
                'min': float(df_quality['ndvi_mean'].min()),
                'max': float(df_quality['ndvi_mean'].max()),
                'current': float(df_quality.iloc[-1]['ndvi_mean']) if len(df_quality) > 0 else None
            },
            'ndmi': {
                'mean': float(df_quality['ndmi_mean'].mean()),
                'current': float(df_quality.iloc[-1]['ndmi_mean']) if len(df_quality) > 0 else None
            },
            'msi': {
                'mean': float(df_quality['msi_mean'].mean()),
                'current': float(df_quality.iloc[-1]['msi_mean']) if len(df_quality) > 0 else None
            }
        }
        
        # Trend
        trend = BaselineService.calculate_trend(df_quality)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'trend': trend,
            'timeseries': df_quality.to_dict('records')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/timeseries', methods=['POST'])
def get_timeseries():
    """Zaman serisi verisi"""
    data = request.get_json()
    
    coordinates = data.get('coordinates')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not all([coordinates, start_date, end_date]):
        return jsonify({
            'success': False,
            'error': 'coordinates, start_date ve end_date gerekli'
        }), 400
    
    try:
        df = GEEService.get_timeseries(coordinates, start_date, end_date)
        
        return jsonify({
            'success': True,
            'count': len(df),
            'data': df.to_dict('records')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/current', methods=['POST'])
def get_current():
    """Güncel durum"""
    data = request.get_json()
    coordinates = data.get('coordinates')
    
    if not coordinates:
        return jsonify({
            'success': False,
            'error': 'Koordinatlar gerekli'
        }), 400
    
    try:
        current = GEEService.get_current_status(coordinates)
        
        if current is None:
            return jsonify({
                'success': False,
                'error': 'Güncel veri bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': current
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500