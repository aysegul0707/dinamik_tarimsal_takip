"""Google Earth Engine Servis Katmanı - HATA DÜZELTİLDİ"""
import ee
import pandas as pd
from datetime import datetime, timedelta
from flask import current_app


class GEEService:
    """GEE veri işlemleri"""
    
    @staticmethod
    def _get_geometry(coordinates):
        """Koordinatlardan geometri oluştur"""
        if len(coordinates) == 2 and isinstance(coordinates[0], (int, float)):
            return ee.Geometry.Point(coordinates).buffer(250)
        else:
            return ee.Geometry.Polygon([coordinates])
    
    @staticmethod
    def _apply_cloud_mask(image):
        """Çift katmanlı bulut maskesi"""
        qa60 = image.select('QA60')
        cloud_mask = qa60.bitwiseAnd(1 << 10).eq(0)
        cirrus_mask = qa60.bitwiseAnd(1 << 11).eq(0)
        
        scl = image.select('SCL')
        vegetation_soil = scl.eq(4).Or(scl.eq(5))
        
        final_mask = cloud_mask.And(cirrus_mask).And(vegetation_soil)
        
        return image.updateMask(final_mask)
    
    @staticmethod
    def _calculate_indices(image):
        """NDVI, NDMI, MSI hesapla"""
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        ndmi = image.normalizedDifference(['B8', 'B11']).rename('NDMI')
        msi = image.select('B11').divide(image.select('B8')).rename('MSI')
        
        return image.addBands([ndvi, ndmi, msi])
    
    @staticmethod
    def get_timeseries(coordinates, start_date, end_date):
        """Zaman serisi verisi çek - HATA DÜZELTİLDİ"""
        geometry = GEEService._get_geometry(coordinates)
        cloud_threshold = current_app.config['CLOUD_THRESHOLD']
        
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold)))
        
        def extract_stats(image):
            masked = GEEService._apply_cloud_mask(image)
            with_indices = GEEService._calculate_indices(masked)
            
            # HER METRİK İÇİN AYRI AYRI HESAPLAMA
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
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ),
                geometry=geometry,
                scale=10,
                maxPixels=1e9
            )
            
            # MSI istatistikleri
            msi_stats = with_indices.select('MSI').reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ),
                geometry=geometry,
                scale=10,
                maxPixels=1e9
            )
            
            # Temiz piksel oranı
            scl = image.select('SCL')
            clear_ratio = scl.eq(4).Or(scl.eq(5)).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=20
            ).get('SCL')
            
            # GEE'nin döndürdüğü key isimleri: NDVI_mean, NDVI_stdDev
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'timestamp': image.date().millis(),
                'ndvi_mean': ndvi_stats.get('NDVI_mean'),
                'ndvi_std': ndvi_stats.get('NDVI_stdDev'),
                'ndmi_mean': ndmi_stats.get('NDMI_mean'),
                'ndmi_std': ndmi_stats.get('NDMI_stdDev'),
                'msi_mean': msi_stats.get('MSI_mean'),
                'msi_std': msi_stats.get('MSI_stdDev'),
                'clear_pixel_ratio': clear_ratio,
                'cloud_percentage': image.get('CLOUDY_PIXEL_PERCENTAGE')
            })
        
        features = collection.map(extract_stats)
        result = features.getInfo()
        
        if not result['features']:
            return pd.DataFrame()
        
        df = pd.DataFrame([f['properties'] for f in result['features']])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        numeric_cols = ['ndvi_mean', 'ndvi_std', 'ndmi_mean', 'ndmi_std',
                       'msi_mean', 'msi_std', 'clear_pixel_ratio', 'cloud_percentage']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    @staticmethod
    def get_current_status(coordinates, days_back=30):
        """Güncel durum"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        df = GEEService.get_timeseries(coordinates, start_date, end_date)
        
        if df.empty:
            return None
        
        df_clean = df[df['clear_pixel_ratio'] > 0.5]
        
        if df_clean.empty:
            best = df.loc[df['cloud_percentage'].idxmin()]
        else:
            best = df_clean.loc[df_clean['clear_pixel_ratio'].idxmax()]
        
        return best.to_dict()
    
    @staticmethod
    def get_baseline_data(coordinates, years=None):
        """Baseline için çok yıllık veri"""
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