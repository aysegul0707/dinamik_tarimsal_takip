/**
 * Harita Modülü
 * Leaflet harita işlemlerini yönetir
 */

const MapModule = {
    map: null,
    drawnItems: null,
    drawControl: null,
    currentMarker: null,
    currentPolygon: null,
    selectedCoordinates: null,
    
    /**
     * Haritayı başlat
     */
    init() {
        // Harita oluştur (Türkiye merkezli)
        this.map = L.map('map').setView([39.0, 35.0], 6);
        
        // Uydu görüntüsü katmanı
        const satelliteLayer = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: 'Esri World Imagery',
                maxZoom: 19
            }
        );
        
        // OpenStreetMap katmanı
        const osmLayer = L.tileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }
        );
        
        // Varsayılan olarak uydu görüntüsü
        satelliteLayer.addTo(this.map);
        
        // Katman kontrolü
        const baseMaps = {
            "🛰️ Uydu": satelliteLayer,
            "🗺️ Harita": osmLayer
        };
        L.control.layers(baseMaps).addTo(this.map);
        
        // Çizim katmanı
        this.drawnItems = new L.FeatureGroup();
        this.map.addLayer(this.drawnItems);
        
        // Çizim kontrolleri
        this.drawControl = new L.Control.Draw({
            edit: {
                featureGroup: this.drawnItems
            },
            draw: {
                polygon: {
                    allowIntersection: false,
                    showArea: true,
                    shapeOptions: {
                        color: '#2e7d32',
                        fillOpacity: 0.3
                    }
                },
                rectangle: {
                    shapeOptions: {
                        color: '#2e7d32',
                        fillOpacity: 0.3
                    }
                },
                polyline: false,
                circle: false,
                marker: true,
                circlemarker: false
            }
        });
        
        // Event listeners
        this.setupEventListeners();
        
        // Harita tıklama
        this.map.on('click', (e) => this.onMapClick(e));
        
        console.log('✅ Harita başlatıldı');
    },
    
    /**
     * Event listener'ları kur
     */
    setupEventListeners() {
        // Koordinata git butonu
        const btnGoto = document.getElementById('btn-goto');
        if (btnGoto) {
            btnGoto.addEventListener('click', () => {
                const lat = parseFloat(document.getElementById('input-lat').value);
                const lng = parseFloat(document.getElementById('input-lng').value);
                
                if (!isNaN(lat) && !isNaN(lng)) {
                    this.goToCoordinates(lat, lng);
                } else {
                    alert('Lütfen geçerli koordinat giriniz!');
                }
            });
        }

        // Çizim tamamlandığında
        this.map.on('draw:created', (e) => {
            const layer = e.layer;
            this.drawnItems.addLayer(layer);
            
            // Koordinatları al
            if (e.layerType === 'marker') {
                const latlng = layer.getLatLng();
                this.selectedCoordinates = [latlng.lng, latlng.lat];
                this.currentMarker = layer;
            } else {
                // Polygon veya rectangle
                const coords = layer.getLatLngs()[0].map(ll => [ll.lng, ll.lat]);
                // Polygon'u kapat
                coords.push(coords[0]);
                this.selectedCoordinates = coords;
                this.currentPolygon = layer;
            }
            
            this.updateCoordinatesDisplay();
            this.enableAnalyzeButton();
        });
        
        // Çizim düzenlendiğinde
        this.map.on('draw:edited', (e) => {
            const layers = e.layers;
            layers.eachLayer((layer) => {
                if (layer instanceof L.Marker) {
                    const latlng = layer.getLatLng();
                    this.selectedCoordinates = [latlng.lng, latlng.lat];
                } else {
                    const coords = layer.getLatLngs()[0].map(ll => [ll.lng, ll.lat]);
                    coords.push(coords[0]);
                    this.selectedCoordinates = coords;
                }
            });
            this.updateCoordinatesDisplay();
        });
        
        // Çizim silindiğinde
        this.map.on('draw:deleted', () => {
            this.selectedCoordinates = null;
            this.updateCoordinatesDisplay();
            this.disableAnalyzeButton();
        });
        
        // Buton event'leri
        document.getElementById('btn-draw').addEventListener('click', () => {
            this.enableDrawMode();
        });
        
        document.getElementById('btn-clear').addEventListener('click', () => {
            this.clearAll();
        });
    },
    
    /**
     * Belirtilen koordinata git
     */
    goToCoordinates(lat, lng) {
        // Haritayı oraya odakla
        this.map.flyTo([lat, lng], 15);
        
        // Varsa eski çizimleri temizle
        this.clearAll();
        
        // İşaretçi ekle
        const marker = L.marker([lat, lng], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: '📍',
                iconSize: [30, 30],
                iconAnchor: [15, 30]
            })
        }).addTo(this.drawnItems);
        
        marker.bindPopup(`<b>Konum:</b><br>${lat.toFixed(5)}, ${lng.toFixed(5)}`).openPopup();
        
        // Seçili durumu güncelle
        this.currentMarker = marker;
        this.selectedCoordinates = [lng, lat];
        this.updateCoordinatesDisplay();
        this.enableAnalyzeButton();
    },

    /**
     * Harita tıklaması
     */
    onMapClick(e) {
        // Eğer çizim modu aktif değilse, nokta ekle
        if (!this.map.pm || !this.map.pm.globalDrawModeEnabled()) {
            this.clearAll();
            
            const marker = L.marker(e.latlng, {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: '📍',
                    iconSize: [30, 30],
                    iconAnchor: [15, 30]
                })
            }).addTo(this.drawnItems);
            
            this.currentMarker = marker;
            this.selectedCoordinates = [e.latlng.lng, e.latlng.lat];
            
            this.updateCoordinatesDisplay();
            this.enableAnalyzeButton();
        }
    },
    
    /**
     * Çizim modunu etkinleştir
     */
    enableDrawMode() {
        this.map.addControl(this.drawControl);
    },
    
    /**
     * Tüm çizimleri temizle
     */
    clearAll() {
        this.drawnItems.clearLayers();
        this.selectedCoordinates = null;
        this.currentMarker = null;
        this.currentPolygon = null;
        this.updateCoordinatesDisplay();
        this.disableAnalyzeButton();
    },
    
    /**
     * Koordinat gösterimini güncelle
     */
    updateCoordinatesDisplay() {
        const display = document.getElementById('coords-text');
        
        if (!this.selectedCoordinates) {
            display.textContent = 'Haritada bir nokta seçin veya tarla çizin';
            return;
        }
        
        if (Array.isArray(this.selectedCoordinates[0])) {
            // Polygon
            const pointCount = this.selectedCoordinates.length - 1;
            display.textContent = `📐 Polygon seçildi (${pointCount} köşe)`;
        } else {
            // Nokta
            const [lng, lat] = this.selectedCoordinates;
            display.textContent = `📍 Nokta: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        }
    },
    
    /**
     * Analiz butonunu etkinleştir
     */
    enableAnalyzeButton() {
        const btn = document.getElementById('btn-analyze');
        btn.disabled = false;
    },
    
    /**
     * Analiz butonunu devre dışı bırak
     */
    disableAnalyzeButton() {
        const btn = document.getElementById('btn-analyze');
        btn.disabled = true;
    },
    
    /**
     * Seçili koordinatları getir
     */
    getSelectedCoordinates() {
        return this.selectedCoordinates;
    },
    
    /**
     * Koordinata zoom yap
     */
    zoomToCoordinates(coordinates) {
        if (Array.isArray(coordinates[0])) {
            // Polygon
            const bounds = L.latLngBounds(
                coordinates.map(c => [c[1], c[0]])
            );
            this.map.fitBounds(bounds, { padding: [50, 50] });
        } else {
            // Nokta
            this.map.setView([coordinates[1], coordinates[0]], 14);
        }
    },
    
    /**
     * NDVI ısı haritası ekle (ileri seviye)
     */
    addHeatmapLayer(geojsonData) {
        // İleride NDVI değerlerine göre renklendirme
        // Şimdilik boş
    }
};

// Global erişim
window.MapModule = MapModule;