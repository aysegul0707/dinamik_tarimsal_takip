"""
Google Earth Engine Servis Katmanı
Sentinel-2 verilerini çeker ve işler
"""
import ee
import pandas as pd
from datetime import datetime, timedelta
from flask import current_app


class GEEService:
    """GEE ile Sentinel-2 veri işlemleri"""
    
    @staticmethod
    def _get_geometry(coordinates):
        """
        Koordinatlardan GEE geometrisi oluştur
        
        Args:
            coordinates: [lon, lat] veya [[lon1,lat1], [lon2,lat2], ...] (polygon)
        """
        if len(coordinates) == 2 and isinstance(coordinates[0], (int, float)):
            # Nokta koordinatı - 250m buffer ekle
            return ee.Geometry.Point(coordinates).buffer(250)
        else:
            # Polygon
            return ee.Geometry.Polygon([coordinates])
    
    @staticmethod
    def _apply_cloud_mask(image):
        """
        SCL bandı ile bulut maskeleme
        Sadece vegetation (4) ve bare soil (5) pikselleri tut
        """
        scl = image.select('SCL')
        clear_pixels = scl.eq(4).Or(scl.eq(5))
        return image.updateMask(clear_pixels)
    
    @staticmethod
    def _calculate_indices(image):
        """NDVI ve NDMI hesapla"""
        # NDVI = (NIR - RED) / (NIR + RED)
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # NDMI = (NIR - SWIR) / (NIR + SWIR) - Bitki su stresi için
        ndmi = image.normalizedDifference(['B8', 'B11']).rename('NDMI')
        
        return image.addBands([ndvi, ndmi])
    
    @staticmethod
    def get_timeseries(coordinates, start_date, end_date):
        """
        Belirli koordinatlar için zaman serisi verisi çek
        
        Returns:
            DataFrame: tarih, ndvi_mean, ndmi_mean, temiz_piksel_orani
        """
        geometry = GEEService._get_geometry(coordinates)
        cloud_threshold = current_app.config['CLOUD_THRESHOLD']
        
        # Sentinel-2 koleksiyonu
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold)))
        
        def extract_stats(image):
            """Her görüntüden istatistik çıkar"""
            # Bulut maskesi uygula
            masked = GEEService._apply_cloud_mask(image)
            
            # İndeksler hesapla
            with_indices = GEEService._calculate_indices(masked)
            
            # NDVI istatistikleri
            ndvi_stats = with_indices.select('NDVI').reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ),
                geometry=geometry,
                scale=10,
                maxPixels=1e9
            )
            
            # NDMI istatistikleri
            ndmi_stats = with_indices.select('NDMI').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=20,
                maxPixels=1e9
            )
            
            # Temiz piksel oranı
            scl = image.select('SCL')
            clear_ratio = scl.eq(4).Or(scl.eq(5)).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=20
            ).get('SCL')
            
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'timestamp': image.date().millis(),
                'ndvi_mean': ndvi_stats.get('NDVI_mean'),
                'ndvi_std': ndvi_stats.get('NDVI_stdDev'),
                'ndmi_mean': ndmi_stats.get('NDMI_mean'),
                'clear_pixel_ratio': clear_ratio,
                'cloud_percentage': image.get('CLOUDY_PIXEL_PERCENTAGE')
            })
        
        # Verileri çek
        features = collection.map(extract_stats)
        result = features.getInfo()
        
        if not result['features']:
            return pd.DataFrame()
        
        # DataFrame'e çevir
        df = pd.DataFrame([f['properties'] for f in result['features']])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Sayısal dönüşümler
        numeric_cols = ['ndvi_mean', 'ndvi_std', 'ndmi_mean', 
                       'clear_pixel_ratio', 'cloud_percentage']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    @staticmethod
    def get_current_status(coordinates):
        """
        Güncel durumu getir (son 30 gün içindeki en temiz görüntü)
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        df = GEEService.get_timeseries(coordinates, start_date, end_date)
        
        if df.empty:
            return None
        
        # En yüksek temiz piksel oranlı görüntüyü seç
        df_clean = df[df['clear_pixel_ratio'] > 0.5]
        
        if df_clean.empty:
            # Temiz görüntü yoksa en az bulutluyu al
            best = df.loc[df['cloud_percentage'].idxmin()]
        else:
            best = df_clean.loc[df_clean['clear_pixel_ratio'].idxmax()]
        
        return best.to_dict()
    
    @staticmethod
    def get_baseline_data(coordinates, years=None):
        """
        Baseline hesaplama için çok yıllık veri çek
        
        Args:
            coordinates: Tarla koordinatları
            years: Yıl listesi, varsayılan ['2021', '2022', '2023']
        """
        if years is None:
            years = current_app.config['BASELINE_YEARS']
        
        all_data = []
        
        for year in years:
            start_date = f'{year}-01-01'
            end_date = f'{year}-12-31'
            
            df = GEEService.get_timeseries(coordinates, start_date, end_date)
            
            if not df.empty:
                df['year'] = int(year)
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)