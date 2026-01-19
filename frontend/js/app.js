/**
 * Ana Uygulama Modülü
 * Tüm modülleri koordine eder
 */

const App = {
    currentFieldId: null,
    isLoading: false,
    
    /**
     * Uygulamayı başlat
     */
    init() {
        console.log('🚀 Uygulama başlatılıyor...');
        
        // Haritayı başlat
        MapModule.init();
        
        // Boş grafik göster
        ChartsModule.showEmptyChart();
        
        // Event listeners
        this.setupEventListeners();
        
        console.log('✅ Uygulama hazır');
    },
    
    /**
     * Event listener'ları kur
     */
    setupEventListeners() {
        // Analiz butonu
        document.getElementById('btn-analyze').addEventListener('click', () => {
            this.runAnalysis();
        });
    },
    
    /**
     * Loading göster/gizle
     */
    showLoading(show = true) {
        const overlay = document.getElementById('loading');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
        this.isLoading = show;
    },
    
    /**
     * Ana analiz fonksiyonu
     */
    async runAnalysis() {
        const coordinates = MapModule.getSelectedCoordinates();
        
        if (!coordinates) {
            alert('Lütfen önce haritada bir tarla seçin!');
            return;
        }
        
        this.showLoading(true);
        
        try {
            // 1. Risk analizi yap
            console.log('📊 Risk analizi yapılıyor...');
            const riskResult = await API.risk.calculateRisk(coordinates);
            
            if (riskResult.success) {
                this.updateRiskDisplay(riskResult.risk);
                this.updateCurrentValues(riskResult.current);
            }
            
            // 2. Zaman serisi verisi al
            console.log('📈 Zaman serisi alınıyor...');
            const endDate = new Date().toISOString().split('T')[0];
            const startDate = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)
                .toISOString().split('T')[0];
            
            const analysisResult = await API.analysis.analyze(
                coordinates, startDate, endDate
            );
            
            if (analysisResult.success && analysisResult.timeseries.length > 0) {
                ChartsModule.updateTimeseriesChart(analysisResult.timeseries);
            }
            
            console.log('✅ Analiz tamamlandı');
            
        } catch (error) {
            console.error('❌ Analiz hatası:', error);
            alert(`Analiz sırasında hata oluştu: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    },
    
    /**
     * Risk gösterimini güncelle
     */
    updateRiskDisplay(riskData) {
        const levelElement = document.getElementById('risk-level');
        const scoreElement = document.getElementById('risk-score');
        const factorsElement = document.getElementById('risk-factors');
        const riskCircle = document.getElementById('risk-indicator');
        
        // Final level (ML varsa ML, yoksa rule-based)
        const level = riskData.final_level;
        const ruleBased = riskData.rule_based;
        
        // Level gösterimi
        levelElement.textContent = level;
        
        // Risk circle renklendirmesi
        riskCircle.className = 'risk-circle';
        if (level === 'Düşük') {
            riskCircle.classList.add('low');
        } else if (level === 'Orta') {
            riskCircle.classList.add('medium');
        } else {
            riskCircle.classList.add('high');
        }
        
        // Skor gösterimi
        scoreElement.textContent = `Risk Skoru: ${ruleBased.score}/100`;
        
        // Faktörler
        if (ruleBased.factors && ruleBased.factors.length > 0) {
            factorsElement.innerHTML = `
                <ul>
                    ${ruleBased.factors.map(f => `<li>${f}</li>`).join('')}
                </ul>
            `;
        } else {
            factorsElement.innerHTML = '<p style="color: #27ae60; text-align: center;">✓ Herhangi bir risk faktörü tespit edilmedi</p>';
        }
        
        // Z-skoru ve trend bilgisi
        if (ruleBased.z_score !== null) {
            const zInfo = document.createElement('p');
            zInfo.style.cssText = 'font-size: 0.8rem; color: #64748b; margin-top: 0.5rem; text-align: center;';
            zInfo.textContent = `Z-skoru: ${ruleBased.z_score.toFixed(2)} | Trend: ${ruleBased.trend.direction}`;
            factorsElement.appendChild(zInfo);
        }
    },
    
    /**
     * Güncel değerleri güncelle
     */
    updateCurrentValues(currentData) {
        // NDVI
        const ndviElement = document.getElementById('current-ndvi');
        if (currentData.ndvi_mean !== null && currentData.ndvi_mean !== undefined) {
            ndviElement.textContent = currentData.ndvi_mean.toFixed(3);
            
            // Renk kodlaması
            if (currentData.ndvi_mean < 0.2) {
                ndviElement.style.color = '#c62828';
            } else if (currentData.ndvi_mean < 0.4) {
                ndviElement.style.color = '#f9a825';
            } else {
                ndviElement.style.color = '#2e7d32';
            }
        } else {
            ndviElement.textContent = '-';
        }
        
        // NDMI
        const ndmiElement = document.getElementById('current-ndmi');
        if (currentData.ndmi_mean !== null && currentData.ndmi_mean !== undefined) {
            ndmiElement.textContent = currentData.ndmi_mean.toFixed(3);
        } else {
            ndmiElement.textContent = '-';
        }
        
        // Tarih
        const dateElement = document.getElementById('current-date');
        if (currentData.date) {
            const date = new Date(currentData.date);
            dateElement.textContent = date.toLocaleDateString('tr-TR');
        } else {
            dateElement.textContent = '-';
        }
    },
    
    /**
     * Hata göster
     */
    showError(message) {
        // Basit alert, ileride toast notification yapılabilir
        alert(message);
    },
    
    /**
     * Başarı mesajı göster
     */
    showSuccess(message) {
        console.log('✅', message);
    }
};

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Global erişim
window.App = App;