# gee_test.py
import ee
import json

# 1. GEE'yi başlat (ilk seferde tarayıcı açılır, giriş yaparsınız)
ee.Authenticate()  # Sadece ilk seferde
ee.Initialize(project='agricultural-481909')  # Proje ID'nizi yazın

# 2. Tarla koordinatları
tarla_merkez = ee.Geometry.Point([38.709532, 38.978599])
tarla_sinir = tarla_merkez.buffer(250)

# 3. Sentinel-2 verisi çek
sentinel = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(tarla_sinir)
    .filterDate('2024-01-01', '2024-06-01')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .sort('CLOUDY_PIXEL_PERCENTAGE')
    .first())

# 4. NDVI hesapla
ndvi = sentinel.normalizedDifference(['B8', 'B4']).rename('NDVI')

# 5. Ortalama değeri al
stats = ndvi.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=tarla_sinir,
    scale=10,
    maxPixels=1e9
).getInfo()

print("=== PYTHON'DAN GEE SONUÇLARI ===")
print(f"Ortalama NDVI: {stats['NDVI']:.4f}")

# 6. Tarihsel veri çek (ML için)
def extract_ndvi(image):
    ndvi_img = image.normalizedDifference(['B8', 'B4'])
    mean_val = ndvi_img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tarla_sinir,
        scale=10
    ).get('nd')
    
    return ee.Feature(None, {
        'date': image.date().format('YYYY-MM-dd'),
        'ndvi': mean_val
    })

zaman_serisi = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(tarla_sinir)
    .filterDate('2023-01-01', '2025-11-20')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
    .map(extract_ndvi))

# Feature Collection'ı listeye çevir
sonuclar = zaman_serisi.getInfo()

print("\n=== ZAMAN SERİSİ VERİLERİ ===")
for feature in sonuclar['features'][:200]:  # İlk 200  kayıt
    props = feature['properties']
    if props['ndvi'] is not None:
        print(f"{props['date']}: NDVI = {props['ndvi']:.4f}")