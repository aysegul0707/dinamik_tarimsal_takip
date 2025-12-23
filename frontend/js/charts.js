/**
 * Grafik Modülü
 * Chart.js ile grafik işlemlerini yönetir
 */

const ChartsModule = {
    timeseriesChart: null,
    
    /**
     * Zaman serisi grafiğini oluştur veya güncelle
     */
    updateTimeseriesChart(data) {
        const ctx = document.getElementById('timeseries-chart').getContext('2d');
        
        // Tarihleri ve değerleri ayır
        const labels = data.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' });
        });
        
        const ndviValues = data.map(d => d.ndvi_mean);
        const ndmiValues = data.map(d => d.ndmi_mean);
        
        // Eğer grafik varsa güncelle, yoksa oluştur
        if (this.timeseriesChart) {
            this.timeseriesChart.data.labels = labels;
            this.timeseriesChart.data.datasets[0].data = ndviValues;
            this.timeseriesChart.data.datasets[1].data = ndmiValues;
            this.timeseriesChart.update();
            return;
        }
        
        // Yeni grafik oluştur
        this.timeseriesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'NDVI',
                        data: ndviValues,
                        borderColor: '#2e7d32',
                        backgroundColor: 'rgba(46, 125, 50, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'NDMI',
                        data: ndmiValues,
                        borderColor: '#1976d2',
                        backgroundColor: 'rgba(25, 118, 210, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw?.toFixed(3) || 'N/A'}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Tarih'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Değer'
                        },
                        min: -0.5,
                        max: 1,
                        ticks: {
                            stepSize: 0.25
                        }
                    }
                }
            }
        });
    },
    
    /**
     * Baseline karşılaştırma grafiği
     */
    createBaselineComparisonChart(currentData, baselineData) {
        // İleride baseline ile karşılaştırma grafiği
        // Şimdilik boş
    },
    
    /**
     * Grafikleri temizle
     */
    clearCharts() {
        if (this.timeseriesChart) {
            this.timeseriesChart.destroy();
            this.timeseriesChart = null;
        }
    },
    
    /**
     * Boş grafik göster
     */
    showEmptyChart() {
        const ctx = document.getElementById('timeseries-chart').getContext('2d');
        
        if (this.timeseriesChart) {
            this.timeseriesChart.destroy();
        }
        
        this.timeseriesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [''],
                datasets: [{
                    label: 'Veri yok',
                    data: [],
                    borderColor: '#ccc'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Analiz için tarla seçin',
                        color: '#999'
                    }
                }
            }
        });
    }
};

// Global erişim
window.ChartsModule = ChartsModule;