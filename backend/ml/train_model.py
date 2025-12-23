"""
Random Forest Model Eğitim Scripti
Baseline verilerinden otomatik etiketler oluşturur ve model eğitir
"""
import os
import sys
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

# Parent dizini ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Örnek veri oluşturma (gerçek projede GEE'den gelecek)
def generate_sample_data(n_samples=1000):
    """
    Eğitim için örnek veri oluştur
    Gerçek projede bu veriler GEE'den çekilecek
    """
    np.random.seed(42)
    
    data = []
    
    for i in range(n_samples):
        # Hafta (1-52)
        week = np.random.randint(1, 53)
        
        # Mevsimsel NDVI (sinüzoidal pattern)
        base_ndvi = 0.4 + 0.3 * np.sin(2 * np.pi * week / 52)
        
        # Rastgele varyasyon
        ndvi = base_ndvi + np.random.normal(0, 0.1)
        ndvi = np.clip(ndvi, 0, 1)
        
        # NDMI (NDVI ile korelasyonlu)
        ndmi = ndvi * 0.5 - 0.3 + np.random.normal(0, 0.05)
        ndmi = np.clip(ndmi, -0.5, 0.5)
        
        # Baseline değerleri (3 yıllık ortalama simülasyonu)
        ndvi_mu = 0.4 + 0.3 * np.sin(2 * np.pi * week / 52)
        ndvi_sigma = 0.08 + np.random.uniform(0, 0.04)
        
        # Z-skoru
        z_score = (ndvi - ndvi_mu) / ndvi_sigma
        
        # Trend (son 3 hafta simülasyonu)
        trend_slope = np.random.normal(0, 0.03)
        
        # Sapma yüzdesi
        deviation_pct = (ndvi_mu - ndvi) / ndvi_mu * 100 if ndvi_mu > 0 else 0
        
        # Mevsimsel encoding
        week_sin = np.sin(2 * np.pi * week / 52)
        week_cos = np.cos(2 * np.pi * week / 52)
        
        # Veri kalitesi
        clear_ratio = np.random.uniform(0.5, 1.0)
        
        # OTOMATİK ETİKETLEME
        # Z-skoru bazlı (rapordaki gibi)
        abs_z = abs(z_score)
        if abs_z < 1.5:
            label = 0  # Düşük risk
        elif abs_z < 2.5:
            label = 1  # Orta risk
        else:
            label = 2  # Yüksek risk
        
        # Ek kontroller ile etiket düzeltme
        if ndvi < 0.2 and week in range(15, 40):  # Büyüme mevsiminde çok düşük
            label = max(label, 2)
        if trend_slope < -0.05:  # Güçlü düşüş trendi
            label = max(label, 1)
        
        data.append({
            'ndvi': ndvi,
            'ndmi': ndmi,
            'z_ndvi': z_score,
            'z_ndmi': z_score * 0.8,  # Basitleştirme
            'abs_z': abs_z,
            'deviation_pct': deviation_pct,
            'trend_slope': trend_slope,
            'week_sin': week_sin,
            'week_cos': week_cos,
            'clear_ratio': clear_ratio,
            'label': label
        })
    
    return pd.DataFrame(data)


def train_model():
    """Model eğit ve kaydet"""
    print("="*60)
    print("RANDOM FOREST MODEL EĞİTİMİ")
    print("="*60)
    
    # 1. Veri oluştur/yükle
    print("\n📊 Veri hazırlanıyor...")
    df = generate_sample_data(n_samples=2000)
    
    print(f"   Toplam örnek: {len(df)}")
    print(f"   Sınıf dağılımı:")
    print(f"     - Düşük (0): {(df['label']==0).sum()}")
    print(f"     - Orta (1):  {(df['label']==1).sum()}")
    print(f"     - Yüksek (2): {(df['label']==2).sum()}")
    
    # 2. Feature ve label ayır
    feature_cols = ['ndvi', 'ndmi', 'z_ndvi', 'z_ndmi', 'abs_z', 
                    'deviation_pct', 'trend_slope', 'week_sin', 
                    'week_cos', 'clear_ratio']
    
    X = df[feature_cols].values
    y = df['label'].values
    
    # 3. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    print(f"\n   Eğitim seti: {len(X_train)}")
    print(f"   Test seti: {len(X_test)}")
    
    # 4. Ölçeklendirme
    print("\n⚖️ Özellikler ölçeklendiriliyor...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 5. Model eğitimi
    print("\n🌲 Random Forest eğitiliyor...")
    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    model.fit(X_train_scaled, y_train)
    
    # 6. Cross-validation
    print("\n📈 Cross-validation yapılıyor...")
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='f1_macro')
    print(f"   CV F1-scores: {cv_scores}")
    print(f"   Ortalama CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    # 7. Test seti değerlendirmesi
    print("\n🎯 Test seti değerlendirmesi:")
    y_pred = model.predict(X_test_scaled)
    
    print("\n" + classification_report(y_test, y_pred, 
          target_names=['Düşük', 'Orta', 'Yüksek']))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # 8. Feature importance
    print("\n📊 Özellik önemleri:")
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for _, row in importances.iterrows():
        bar = '█' * int(row['importance'] * 50)
        print(f"   {row['feature']:15} {bar} {row['importance']:.3f}")
    
    # 9. Model kaydet
    print("\n💾 Model kaydediliyor...")
    
    model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
    scaler_path = os.path.join(os.path.dirname(__file__), 'scaler.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"   ✅ Model kaydedildi: {model_path}")
    print(f"   ✅ Scaler kaydedildi: {scaler_path}")
    
    # 10. Test tahmini
    print("\n🔮 Örnek tahminler:")
    sample_indices = np.random.choice(len(X_test), 5, replace=False)
    
    for idx in sample_indices:
        pred = model.predict(X_test_scaled[idx:idx+1])[0]
        prob = model.predict_proba(X_test_scaled[idx:idx+1])[0]
        actual = y_test[idx]
        
        labels = ['Düşük', 'Orta', 'Yüksek']
        print(f"   Gerçek: {labels[actual]:7} | Tahmin: {labels[pred]:7} | "
              f"Olasılıklar: D:{prob[0]:.2f} O:{prob[1]:.2f} Y:{prob[2]:.2f}")
    
    print("\n" + "="*60)
    print("EĞİTİM TAMAMLANDI!")
    print("="*60)
    
    return model, scaler


if __name__ == '__main__':
    train_model()