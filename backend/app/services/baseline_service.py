"""
Baseline Hesaplama Servisi
Her tarla için haftalık μ (ortalama) ve σ (standart sapma) hesaplar
Nadas dönemlerini tespit eder ve es geçer
"""
import pandas as pd
import numpy as np
from flask import current_app
from app.services.gee_service import GEEService


class BaselineService:
    """Baseline hesaplama ve yönetimi"""
    
    @staticmethod
    def detect_nadas_periods(df):
        """
        Nadas dönemlerini tespit et
        Ardışık düşük NDVI değerlerine bak
        
        Returns:
            List[tuple]: [(başlangıç_hafta, bitiş_hafta), ...]
        """
        threshold = current_app.config['NADAS_NDVI_THRESHOLD']
        min_consecutive = current_app.config['NADAS_CONSECUTIVE_WEEKS']
        
        df = df.copy()
        df['week'] = df['date'].dt.isocalendar().week
        df['year'] = df['date'].dt.year
        
        # Haftalık ortalamaları al
        weekly = df.groupby(['year', 'week'])['ndvi_mean'].mean().reset_index()
        
        nadas_periods = []
        
        for year in weekly['year'].unique():
            year_data = weekly[weekly['year'] == year].sort_values('week')
            
            # Düşük NDVI dönemlerini bul
            low_ndvi = year_data['ndvi_mean'] < threshold
            
            # Ardışık düşük dönemleri grupla
            groups = (low_ndvi != low_ndvi.shift()).cumsum()
            
            for group_id in groups[low_ndvi].unique():
                group_weeks = year_data[groups == group_id]['week'].values
                
                if len(group_weeks) >= min_consecutive:
                    nadas_periods.append({
                        'year': year,
                        'start_week': int(group_weeks.min()),
                        'end_week': int(group_weeks.max()),
                        'duration_weeks': len(group_weeks)
                    })
        
        return nadas_periods
    
    @staticmethod
    def calculate_baseline(coordinates, exclude_nadas=True):
        """
        Haftalık baseline hesapla
        
        Args:
            coordinates: Tarla koordinatları
            exclude_nadas: Nadas dönemlerini hariç tut
            
        Returns:
            DataFrame: hafta, ndvi_mu, ndvi_sigma, ndmi_mu, ndmi_sigma, sample_count
        """
        # Çok yıllık veri çek
        df = GEEService.get_baseline_data(coordinates)
        
        if df.empty:
            return pd.DataFrame()
        
        # Kalite filtresi: Temiz piksel oranı > %50
        df = df[df['clear_pixel_ratio'] > 0.5].copy()
        
        if df.empty:
            return pd.DataFrame()
        
        # Hafta numarası ekle
        df['week'] = df['date'].dt.isocalendar().week
        
        # Nadas dönemlerini tespit et
        nadas_periods = []
        if exclude_nadas:
            nadas_periods = BaselineService.detect_nadas_periods(df)
            
            # Nadas dönemlerini çıkar
            for period in nadas_periods:
                mask = (
                    (df['date'].dt.year == period['year']) &
                    (df['week'] >= period['start_week']) &
                    (df['week'] <= period['end_week'])
                )
                df = df[~mask]
        
        if df.empty:
            return pd.DataFrame()
        
        # Haftalık istatistikler hesapla
        baseline = df.groupby('week').agg({
            'ndvi_mean': ['mean', 'std', 'count'],
            'ndmi_mean': ['mean', 'std']
        }).reset_index()
        
        # Sütun isimlerini düzelt
        baseline.columns = [
            'week', 
            'ndvi_mu', 'ndvi_sigma', 'sample_count',
            'ndmi_mu', 'ndmi_sigma'
        ]
        
        # NaN sigma değerlerini küçük bir değerle doldur (tek örnek varsa)
        baseline['ndvi_sigma'] = baseline['ndvi_sigma'].fillna(0.05)
        baseline['ndmi_sigma'] = baseline['ndmi_sigma'].fillna(0.05)
        
        # Minimum sigma değeri (çok düşükse Z-skoru patlar)
        baseline['ndvi_sigma'] = baseline['ndvi_sigma'].clip(lower=0.03)
        baseline['ndmi_sigma'] = baseline['ndmi_sigma'].clip(lower=0.03)
        
        # Nadas bilgisini ekle
        baseline_dict = {
            'baseline': baseline.to_dict('records'),
            'nadas_periods': nadas_periods,
            'total_samples': len(df),
            'years_used': df['date'].dt.year.unique().tolist()
        }
        
        return baseline_dict
    
    @staticmethod
    def calculate_zscore(current_value, week, baseline_df, index_type='ndvi'):
        """
        Z-skoru hesapla
        
        Args:
            current_value: Güncel değer
            week: Hafta numarası (1-52)
            baseline_df: Baseline DataFrame
            index_type: 'ndvi' veya 'ndmi'
            
        Returns:
            float: Z-skoru veya None
        """
        week_baseline = baseline_df[baseline_df['week'] == week]
        
        if week_baseline.empty:
            return None
        
        mu = week_baseline[f'{index_type}_mu'].values[0]
        sigma = week_baseline[f'{index_type}_sigma'].values[0]
        
        if sigma == 0 or pd.isna(sigma):
            return None
        
        z_score = (current_value - mu) / sigma
        
        return z_score
    
    @staticmethod
    def calculate_trend(df, window=3):
        """
        Son N ölçümün trend eğimini hesapla
        
        Args:
            df: Zaman serisi DataFrame (date, ndvi_mean sütunları)
            window: Kaç ölçüm kullanılacak
            
        Returns:
            dict: slope, direction, confidence
        """
        if len(df) < window:
            return {
                'slope': 0,
                'direction': 'insufficient_data',
                'confidence': 0
            }
        
        recent = df.tail(window).copy()
        
        # Basit lineer regresyon
        x = np.arange(len(recent))
        y = recent['ndvi_mean'].values
        
        # Eğim hesapla
        slope = np.polyfit(x, y, 1)[0]
        
        # Yön belirle
        if slope < -0.03:
            direction = 'decreasing'
        elif slope > 0.03:
            direction = 'increasing'
        else:
            direction = 'stable'
        
        # Güven (R²)
        correlation = np.corrcoef(x, y)[0, 1]
        confidence = correlation ** 2 if not np.isnan(correlation) else 0
        
        return {
            'slope': float(slope),
            'direction': direction,
            'confidence': float(confidence)
        }