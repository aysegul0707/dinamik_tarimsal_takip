"""Baseline Hesaplama Servisi - Multi-metric + Yıllık Nadas Tespiti"""
import pandas as pd
import numpy as np
from flask import current_app
from app.services.gee_service import GEEService


class BaselineService:
    """Baseline hesaplama ve yönetimi"""
    
    @staticmethod
    def detect_nadas_years(df):
        """
        Yıllık maksimum NDVI kontrolü ile nadas yılları tespit et
        """
        threshold = current_app.config['NADAS_YEARLY_MAX_THRESHOLD']
        
        # Yıllık maksimum NDVI
        yearly_max = df.groupby(df['date'].dt.year)['ndvi_mean'].max()
        
        # Nadas yıllar: max NDVI < eşik
        nadas_years = yearly_max[yearly_max < threshold].index.tolist()
        valid_years = yearly_max[yearly_max >= threshold].index.tolist()
        
        return {
            'nadas_years': nadas_years,
            'valid_years': valid_years,
            'yearly_max': yearly_max.to_dict()
        }
    
    @staticmethod
    def calculate_baseline(coordinates):
        """
        Haftalık baseline hesapla (NDVI + NDMI + MSI)
        """
        # Çok yıllık veri çek
        df = GEEService.get_baseline_data(coordinates)
        
        if df.empty:
            return None
        
        # Kalite filtresi
        df = df[df['clear_pixel_ratio'] > 0.5].copy()
        
        if df.empty:
            return None
        
        # Nadas tespiti
        nadas_info = BaselineService.detect_nadas_years(df)
        
        print(f"✅ Geçerli yıllar: {nadas_info['valid_years']}")
        print(f"❌ Nadas yıllar: {nadas_info['nadas_years']}")
        
        # Sadece geçerli yılları tut
        if nadas_info['valid_years']:
            df = df[df['date'].dt.year.isin(nadas_info['valid_years'])].copy()
        else:
            print("⚠️ Tüm yıllar nadas olarak tespit edildi!")
            return None
        
        if df.empty:
            return None
        
        # Hafta numarası ekle
        df['week'] = df['date'].dt.isocalendar().week
        
        # Haftalık istatistikler
        baseline = df.groupby('week').agg({
            'ndvi_mean': ['mean', 'std', 'count'],
            'ndmi_mean': ['mean', 'std'],
            'msi_mean': ['mean', 'std']
        }).reset_index()
        
        # Sütun isimlerini düzelt
        baseline.columns = [
            'week',
            'ndvi_mu', 'ndvi_sigma', 'sample_count',
            'ndmi_mu', 'ndmi_sigma',
            'msi_mu', 'msi_sigma'
        ]
        
        # NaN sigma değerlerini doldur
        baseline['ndvi_sigma'] = baseline['ndvi_sigma'].fillna(0.05).clip(lower=0.03)
        baseline['ndmi_sigma'] = baseline['ndmi_sigma'].fillna(0.05).clip(lower=0.03)
        baseline['msi_sigma'] = baseline['msi_sigma'].fillna(0.1).clip(lower=0.05)
        
        # Sonuç
        return {
            'baseline': baseline.to_dict('records'),
            'nadas_info': nadas_info,
            'total_samples': len(df),
            'years_used': nadas_info['valid_years']
        }
    
    @staticmethod
    def calculate_zscore(current_value, week, baseline_df, metric='ndvi'):
        """Z-skoru hesapla"""
        week_baseline = baseline_df[baseline_df['week'] == week]
        
        if week_baseline.empty:
            return None
        
        mu = week_baseline[f'{metric}_mu'].values[0]
        sigma = week_baseline[f'{metric}_sigma'].values[0]
        
        if sigma == 0 or pd.isna(sigma):
            return None
        
        return (current_value - mu) / sigma
    
    @staticmethod
    def calculate_trend(df, window=3):
        """Trend eğimi hesapla"""
        if len(df) < window:
            return {'slope': 0, 'direction': 'insufficient_data'}
        
        recent = df.tail(window).copy()
        x = np.arange(len(recent))
        y = recent['ndvi_mean'].values
        
        slope = np.polyfit(x, y, 1)[0]
        
        if slope < -0.03:
            direction = 'decreasing'
        elif slope > 0.03:
            direction = 'increasing'
        else:
            direction = 'stable'
        
        return {'slope': float(slope), 'direction': direction}