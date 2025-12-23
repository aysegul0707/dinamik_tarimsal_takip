"""
Makine Öğrenmesi Servisi
Risk sınıflandırması ve tahmin
"""
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from app.services.baseline_service import BaselineService


class MLService:
    """Risk tahmin servisi"""
    
    MODEL_PATH = 'ml/model.pkl'
    SCALER_PATH = 'ml/scaler.pkl'
    
    # Risk seviyeleri
    RISK_LABELS = {0: 'Düşük', 1: 'Orta', 2: 'Yüksek'}
    
    @staticmethod
    def prepare_features(current_data, baseline, timeseries_df):
        """
        ML modeli için özellik vektörü hazırla
        
        Args:
            current_data: Güncel ölçüm dict
            baseline: Baseline dict
            timeseries_df: Son birkaç haftanın verisi
            
        Returns:
            np.array: Özellik vektörü
        """
        current_week = datetime.now().isocalendar().week
        
        # Baseline DataFrame
        baseline_df = pd.DataFrame(baseline['baseline'])
        
        # Z-skorları hesapla
        z_ndvi = BaselineService.calculate_zscore(
            current_data['ndvi_mean'], 
            current_week, 
            baseline_df, 
            'ndvi'
        ) or 0
        
        z_ndmi = BaselineService.calculate_zscore(
            current_data['ndmi_mean'], 
            current_week, 
            baseline_df, 
            'ndmi'
        ) or 0
        
        # Trend analizi
        trend = BaselineService.calculate_trend(timeseries_df)
        
        # Mevsimsel encoding (sin/cos)
        week_sin = np.sin(2 * np.pi * current_week / 52)
        week_cos = np.cos(2 * np.pi * current_week / 52)
        
        # Sapma yüzdesi
        week_baseline = baseline_df[baseline_df['week'] == current_week]
        if not week_baseline.empty:
            expected_ndvi = week_baseline['ndvi_mu'].values[0]
            deviation_pct = (expected_ndvi - current_data['ndvi_mean']) / expected_ndvi * 100
        else:
            deviation_pct = 0
        
        # Özellik vektörü
        features = np.array([
            current_data['ndvi_mean'],      # Güncel NDVI
            current_data['ndmi_mean'],      # Güncel NDMI
            z_ndvi,                         # NDVI Z-skoru
            z_ndmi,                         # NDMI Z-skoru
            abs(z_ndvi),                    # Mutlak Z-skoru
            deviation_pct,                  # Sapma yüzdesi
            trend['slope'],                 # Trend eğimi
            week_sin,                       # Mevsim (sin)
            week_cos,                       # Mevsim (cos)
            current_data.get('clear_pixel_ratio', 0.8)  # Veri kalitesi
        ])
        
        return features.reshape(1, -1)
    
    @staticmethod
    def calculate_rule_based_risk(current_data, baseline, timeseries_df):
        """
        Kural bazlı risk skoru hesapla (ML yoksa veya karşılaştırma için)
        
        Returns:
            dict: score (0-100), level (Düşük/Orta/Yüksek), factors
        """
        current_week = datetime.now().isocalendar().week
        baseline_df = pd.DataFrame(baseline['baseline'])
        
        score = 0
        factors = []
        
        ndvi = current_data['ndvi_mean']
        ndmi = current_data['ndmi_mean']
        
        # 1. Mutlak NDVI kontrolü
        if ndvi < 0.20:
            score += 40
            factors.append(f"Kritik düşük NDVI ({ndvi:.2f})")
        elif ndvi < 0.30:
            score += 25
            factors.append(f"Düşük NDVI ({ndvi:.2f})")
        
        # 2. Z-skoru kontrolü
        z_ndvi = BaselineService.calculate_zscore(
            ndvi, current_week, baseline_df, 'ndvi'
        )
        
        if z_ndvi is not None:
            if abs(z_ndvi) > 3:
                score += 30
                factors.append(f"Şiddetli sapma (Z={z_ndvi:.2f})")
            elif abs(z_ndvi) > 2:
                score += 20
                factors.append(f"Belirgin sapma (Z={z_ndvi:.2f})")
            elif abs(z_ndvi) > 1.5:
                score += 10
                factors.append(f"Hafif sapma (Z={z_ndvi:.2f})")
        
        # 3. Trend kontrolü
        trend = BaselineService.calculate_trend(timeseries_df)
        
        if trend['direction'] == 'decreasing':
            if trend['slope'] < -0.05:
                score += 25
                factors.append("Hızlı düşüş trendi")
            else:
                score += 15
                factors.append("Düşüş trendi")
        
        # 4. NDMI kontrolü (su stresi)
        if ndmi < -0.2:
            score += 15
            factors.append(f"Su stresi belirtisi (NDMI={ndmi:.2f})")
        
        # Skoru sınırla
        score = min(score, 100)
        
        # Seviye belirle
        if score < 30:
            level = 'Düşük'
        elif score < 60:
            level = 'Orta'
        else:
            level = 'Yüksek'
        
        return {
            'score': score,
            'level': level,
            'factors': factors,
            'z_score': z_ndvi,
            'trend': trend
        }
    
    @staticmethod
    def load_model():
        """Eğitilmiş modeli yükle"""
        if os.path.exists(MLService.MODEL_PATH):
            with open(MLService.MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            with open(MLService.SCALER_PATH, 'rb') as f:
                scaler = pickle.load(f)
            return model, scaler
        return None, None
    
    @staticmethod
    def predict_risk(current_data, baseline, timeseries_df):
        """
        Risk tahmini yap
        ML modeli varsa kullan, yoksa kural bazlı
        
        Returns:
            dict: Tam risk analizi sonucu
        """
        # Kural bazlı hesaplama (her zaman yap)
        rule_based = MLService.calculate_rule_based_risk(
            current_data, baseline, timeseries_df
        )
        
        # ML modeli dene
        model, scaler = MLService.load_model()
        
        ml_prediction = None
        if model is not None:
            try:
                features = MLService.prepare_features(
                    current_data, baseline, timeseries_df
                )
                features_scaled = scaler.transform(features)
                
                prediction = model.predict(features_scaled)[0]
                probabilities = model.predict_proba(features_scaled)[0]
                
                ml_prediction = {
                    'class': int(prediction),
                    'level': MLService.RISK_LABELS[prediction],
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
            'timestamp': datetime.now().isoformat()
        }