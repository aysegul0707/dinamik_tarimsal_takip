"""Makine Öğrenmesi Servisi - Risk analizi ve tahmin"""
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from flask import current_app
from app.services.baseline_service import BaselineService


class MLService:
    """Risk tahmin ve analiz servisi"""
    
    MODEL_DIR = 'ml/models'
    
    @staticmethod
    def calculate_rule_based_risk(current_data, baseline_df, timeseries_df):
        """
        Kural bazlı risk analizi (NDVI + NDMI + MSI)
        """
        current_week = datetime.now().isocalendar().week
        thresholds = current_app.config['Z_THRESHOLDS']
        
        score = 0
        alerts = []
        
        # Güncel değerler
        ndvi = current_data.get('ndvi_mean', 0)
        ndmi = current_data.get('ndmi_mean', 0)
        msi = current_data.get('msi_mean', 1)
        
        # Z-skorları hesapla
        z_scores = {}
        for metric in ['ndvi', 'ndmi', 'msi']:
            z = BaselineService.calculate_zscore(
                current_data.get(f'{metric}_mean', 0),
                current_week,
                baseline_df,
                metric
            )
            z_scores[metric] = z if z is not None else 0
        
        # === KONTROL 1: Mutlak Değer Kontrolü ===
        
        # Büyüme mevsiminde kritik düşük NDVI
        if 15 <= current_week <= 35:  # Nisan-Eylül
            if ndvi < 0.20:
                score += 50
                alerts.append({
                    'type': 'critical',
                    'metric': 'NDVI',
                    'message': f'Bitki sağlığı kritik düşük ({ndvi:.2f}). Büyüme mevsiminde bu değer normalin çok altında.'
                })
            elif ndvi < 0.30:
                score += 30
                alerts.append({
                    'type': 'warning',
                    'metric': 'NDVI',
                    'message': f'Bitki sağlığı düşük ({ndvi:.2f}). İzlemeye devam edin.'
                })
        
        # === KONTROL 2: Z-Skoru Anomali Kontrolü ===
        
        # NDVI anomali
        z_ndvi = abs(z_scores['ndvi'])
        if z_ndvi >= thresholds['ndvi']['critical']:
            score += 30
            alerts.append({
                'type': 'critical',
                'metric': 'NDVI',
                'message': f'NDVI değeri normalden {z_ndvi:.1f} standart sapma uzakta.'
            })
        elif z_ndvi >= thresholds['ndvi']['warning']:
            score += 15
            alerts.append({
                'type': 'warning',
                'metric': 'NDVI',
                'message': f'NDVI değerinde sapma tespit edildi (Z={z_scores["ndvi"]:.2f}).'
            })
        
        # NDMI anomali (su stresi)
        z_ndmi = abs(z_scores['ndmi'])
        if z_ndmi >= thresholds['ndmi']['critical']:
            score += 35
            alerts.append({
                'type': 'critical',
                'metric': 'NDMI',
                'message': f'Ciddi su stresi tespit edildi! Acil sulama gerekli (NDMI: {ndmi:.2f}).'
            })
        elif z_ndmi >= thresholds['ndmi']['warning']:
            score += 20
            alerts.append({
                'type': 'warning',
                'metric': 'NDMI',
                'message': f'Su stresi başlangıcı. 2-3 gün içinde sulama planlayın (NDMI: {ndmi:.2f}).'
            })
        
        # MSI anomali (kuraklık riski)
        # MSI (Moisture Stress Index) arttıkça stres artar.
        # Bu yüzden sadece POZİTİF yöndeki (yukarı) sapmalar risktir.
        # abs() kullanmıyoruz!
        
        z_msi = z_scores['msi'] # Mutlak değer ALMA
        
        # Kritik Eşik (Örn: Normalden 2.5 kat daha stresli)
        if z_msi >= thresholds['msi']['critical']:
            score += 25
            alerts.append({
                'type': 'warning',
                'metric': 'MSI',
                'message': f'Nem stresi çok yüksek (Z={z_msi:.2f}). Kuraklık riski artıyor.'
            })
        # Uyarı Eşiği (Örn: Normalden 1.5 kat daha stresli)
        elif z_msi >= thresholds['msi']['warning']:
            score += 10
            alerts.append({
                'type': 'info',
                'metric': 'MSI',
                'message': f'Nem stresi normalin üzerinde (Z={z_msi:.2f}). Takip edilmeli.'
            })

        # === KONTROL 3: Trend Analizi ===
        
        trend = BaselineService.calculate_trend(timeseries_df)
        
        if trend['direction'] == 'decreasing':
            if trend['slope'] < -0.05:
                score += 25
                alerts.append({
                    'type': 'warning',
                    'metric': 'Trend',
                    'message': 'Hızlı düşüş trendi tespit edildi. Son 3 haftadır bitki sağlığı kötüleşiyor.'
                })
            else:
                score += 10
                alerts.append({
                    'type': 'info',
                    'metric': 'Trend',
                    'message': 'Hafif düşüş trendi gözleniyor. İzlemeye devam edin.'
                })
        
        # Skoru sınırla
        score = min(score, 100)
        
        # Risk seviyesi belirle
        if score < 30:
            level = 'Düşük'
            level_code = 0
        elif score < 60:
            level = 'Orta'
            level_code = 1
        else:
            level = 'Yüksek'
            level_code = 2
        
        return {
            'score': score,
            'level': level,
            'level_code': level_code,
            'alerts': alerts,
            'z_scores': z_scores,
            'trend': trend
        }
    
    @staticmethod
    def auto_label(current_data, baseline_df, week):
        """
        Otomatik etiketleme (RF eğitimi için)
        Sadece kesin durumları etiketle
        """
        ndvi = current_data.get('ndvi_mean', 0)
        ndmi = current_data.get('ndmi_mean', 0)
        
        # Z-skorları
        z_ndvi = BaselineService.calculate_zscore(ndvi, week, baseline_df, 'ndvi')
        z_ndmi = BaselineService.calculate_zscore(ndmi, week, baseline_df, 'ndmi')
        
        if z_ndvi is None or z_ndmi is None:
            return None
        
        z_ndvi_abs = abs(z_ndvi)
        z_ndmi_abs = abs(z_ndmi)
        
        # === YÜKSEK RİSK (Kesin durumlar) ===
        
        # Büyüme mevsiminde bitki yok
        if 15 <= week <= 35 and ndvi < 0.20:
            return 2
        
        # Çok güçlü sapma
        if z_ndvi_abs > 3.0 or z_ndmi_abs > 3.0:
            return 2
        
        # Su stresi + düşük NDVI kombinasyonu
        if z_ndmi_abs > 2.0 and z_ndvi_abs > 2.0:
            return 2
        
        # === DÜŞÜK RİSK (Kesin normal) ===
        
        # Her şey normale yakın
        if z_ndvi_abs < 1.0 and z_ndmi_abs < 1.0:
            return 0
        
        # Büyüme mevsiminde sağlıklı
        if 15 <= week <= 35 and ndvi > 0.50:
            return 0
        
        # === ORTA RİSK (Geri kalanlar) ===
        return 1
    
    @staticmethod
    def prepare_features(current_data, baseline_df, timeseries_df, week):
        """ML için özellik vektörü hazırla"""
        # Z-skorları
        z_ndvi = BaselineService.calculate_zscore(
            current_data.get('ndvi_mean', 0), week, baseline_df, 'ndvi'
        ) or 0
        
        z_ndmi = BaselineService.calculate_zscore(
            current_data.get('ndmi_mean', 0), week, baseline_df, 'ndmi'
        ) or 0
        
        z_msi = BaselineService.calculate_zscore(
            current_data.get('msi_mean', 1), week, baseline_df, 'msi'
        ) or 0
        
        # Trend
        trend = BaselineService.calculate_trend(timeseries_df)
        
        # Mevsimsel encoding
        week_sin = np.sin(2 * np.pi * week / 52)
        week_cos = np.cos(2 * np.pi * week / 52)
        
        # Feature vektörü
        features = np.array([
            current_data.get('ndvi_mean', 0),
            current_data.get('ndmi_mean', 0),
            current_data.get('msi_mean', 1),
            z_ndvi,
            z_ndmi,
            z_msi,
            abs(z_ndvi),
            abs(z_ndmi),
            abs(z_msi),
            trend['slope'],
            week_sin,
            week_cos,
            current_data.get('clear_pixel_ratio', 0.8)
        ])
        
        return features.reshape(1, -1)
    
    @staticmethod
    def load_model(field_id):
        """Tarla-spesifik modeli yükle"""
        model_path = os.path.join(MLService.MODEL_DIR, f'field_{field_id}_model.pkl')
        scaler_path = os.path.join(MLService.MODEL_DIR, f'field_{field_id}_scaler.pkl')
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)
            return model, scaler
        
        return None, None
    
    @staticmethod
    def predict_risk(current_data, baseline_df, timeseries_df, field_id=None):
        """
        Tam risk analizi
        """
        current_week = datetime.now().isocalendar().week
        
        # Kural bazlı analiz (her zaman)
        rule_based = MLService.calculate_rule_based_risk(
            current_data, baseline_df, timeseries_df
        )
        
        # ML tahmin (model varsa)
        ml_prediction = None
        if field_id:
            model, scaler = MLService.load_model(field_id)
            
            if model and scaler:
                try:
                    features = MLService.prepare_features(
                        current_data, baseline_df, timeseries_df, current_week
                    )
                    features_scaled = scaler.transform(features)
                    
                    prediction = model.predict(features_scaled)[0]
                    probabilities = model.predict_proba(features_scaled)[0]
                    
                    ml_prediction = {
                        'class': int(prediction),
                        'level': ['Düşük', 'Orta', 'Yüksek'][prediction],
                        'probabilities': {
                            'Düşük': float(probabilities[0]),
                            'Orta': float(probabilities[1]),
                            'Yüksek': float(probabilities[2])
                        }
                    }
                except Exception as e:
                    print(f"ML tahmin hatası: {e}")
        
        return {
            'rule_based': rule_based,
            'ml_prediction': ml_prediction,
            'final_level': ml_prediction['level'] if ml_prediction else rule_based['level'],
            'final_score': rule_based['score'],
            'timestamp': datetime.now().isoformat()
        }