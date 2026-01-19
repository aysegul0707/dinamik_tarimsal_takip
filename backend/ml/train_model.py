"""Random Forest Model Eğitim Scripti - Multi-metric"""
import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_sample_data(n_samples=2000):
    """Örnek eğitim verisi oluştur"""
    np.random.seed(42)
    
    data = []
    
    for i in range(n_samples):
        week = np.random.randint(1, 53)
        
        # Mevsimsel NDVI
        base_ndvi = 0.4 + 0.3 * np.sin(2 * np.pi * week / 52)
        ndvi = base_ndvi + np.random.normal(0, 0.1)
        ndvi = np.clip(ndvi, 0, 1)
        
        # NDMI (NDVI ile korelasyonlu)
        ndmi = ndvi * 0.5 - 0.3 + np.random.normal(0, 0.05)
        ndmi = np.clip(ndmi, -0.5, 0.5)
        
        # MSI (ters korelasyon)
        msi = 1.5 - ndvi * 0.5 + np.random.normal(0, 0.1)
        msi = np.clip(msi, 0.5, 2.5)
        
        # Baseline değerleri
        ndvi_mu = 0.4 + 0.3 * np.sin(2 * np.pi * week / 52)
        ndvi_sigma = 0.08
        
        # Z-skorları
        z_ndvi = (ndvi - ndvi_mu) / ndvi_sigma
        z_ndmi = np.random.normal(0, 1.2)
        z_msi = np.random.normal(0, 1.1)
        
        # Trend
        trend_slope = np.random.normal(0, 0.03)
        
        # Mevsimsel encoding
        week_sin = np.sin(2 * np.pi * week / 52)
        week_cos = np.cos(2 * np.pi * week / 52)
        
        # Veri kalitesi
        clear_ratio = np.random.uniform(0.5, 1.0)
        
        # Otomatik etiketleme
        abs_z_ndvi = abs(z_ndvi)
        abs_z_ndmi = abs(z_ndmi)
        
        if (15 <= week <= 35 and ndvi < 0.20) or abs_z_ndvi > 3.0 or abs_z_ndmi > 3.0:
            label = 2  # Yüksek
        elif abs_z_ndvi < 1.0 and abs_z_ndmi < 1.0:
            label = 0  # Düşük
        else:
            label = 1  # Orta
        
        # Ek düzeltmeler
        if ndvi < 0.2 and 15 <= week <= 35:
            label = max(label, 2)
        if trend_slope < -0.05:
            label = max(label, 1)
        
        data.append({
            'ndvi': ndvi,
            'ndmi': ndmi,
            'msi': msi,
            'z_ndvi': z_ndvi,
            'z_ndmi': z_ndmi,
            'z_msi': z_msi,
            'abs_z_ndvi': abs_z_ndvi,
            'abs_z_ndmi': abs_z_ndmi,
            'abs_z_msi': abs(z_msi),
            'trend_slope': trend_slope,
            'week_sin': week_sin,
            'week_cos': week_cos,
            'clear_ratio': clear_ratio,
            'label': label
        })
    
    return pd.DataFrame(data)


def train_model():
    """Genel model eğit"""
    print("=" * 60)
    print("RANDOM FOREST MODEL EĞİTİMİ (MULTI-METRIC)")
    print("=" * 60)
    
    # Veri oluştur
    print("\n📊 Veri hazırlanıyor...")
    df = generate_sample_data(n_samples=3000)
    
    print(f"   Toplam örnek: {len(df)}")
    print(f"   Sınıf dağılımı:")
    print(f"     - Düşük (0): {(df['label']==0).sum()}")
    print(f"     - Orta (1):  {(df['label']==1).sum()}")
    print(f"     - Yüksek (2): {(df['label']==2).sum()}")
    
    # Features
    feature_cols = ['ndvi', 'ndmi', 'msi', 'z_ndvi', 'z_ndmi', 'z_msi',
                    'abs_z_ndvi', 'abs_z_ndmi', 'abs_z_msi', 'trend_slope',
                    'week_sin', 'week_cos', 'clear_ratio']
    
    X = df[feature_cols].values
    y = df['label'].values
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    print(f"\n   Eğitim: {len(X_train)}, Test: {len(X_test)}")
    
    # Ölçeklendirme
    print("\n⚖️ Özellikler ölçeklendiriliyor...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Model eğitimi
    print("\n🌲 Random Forest eğitiliyor...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Cross-validation
    print("\n📈 Cross-validation...")
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='f1_macro')
    print(f"   CV F1-scores: {cv_scores}")
    print(f"   Ortalama: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    # Test
    print("\n🎯 Test seti:")
    y_pred = model.predict(X_test_scaled)
    
    print("\n" + classification_report(y_test, y_pred, 
          target_names=['Düşük', 'Orta', 'Yüksek']))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Feature importance
    print("\n📊 Özellik önemleri:")
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for _, row in importances.iterrows():
        bar = '█' * int(row['importance'] * 50)
        print(f"   {row['feature']:15} {bar} {row['importance']:.3f}")
    
    # Kaydet
    print("\n💾 Model kaydediliyor...")
    
    os.makedirs('ml/models', exist_ok=True)
    
    with open('ml/models/general_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    with open('ml/models/general_scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    print("   ✅ ml/models/general_model.pkl")
    print("   ✅ ml/models/general_scaler.pkl")
    
    print("\n" + "=" * 60)
    print("EĞİTİM TAMAMLANDI!")
    print("=" * 60)


if __name__ == '__main__':
    train_model()