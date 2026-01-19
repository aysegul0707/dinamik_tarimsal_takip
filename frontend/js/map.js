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
        console.log('🗺️ Harita başlatılıyor...');
        
        // Harita konteynerini kontrol et
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {
            console.error('❌ Harita konteyneri bulunamadı!');
            return;
        }
        
        try {
            // Harita oluştur (Türkiye merkezli)
            this.map = L.map('map', {
                center: [39.0, 35.0],
                zoom: 6,
                zoomControl: false
            });

            // Zoom kontrolünü sağ alta ekle
            L.control.zoom({
                position: 'bottomright'
            }).addTo(this.map);
            
            // === HARITA KATMANLARI ===
            
            // OpenStreetMap - Ana katman (her zaman çalışır)
            const osmLayer = L.tileLayer(
                'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }
            );
            
            // Esri Uydu Görüntüsü - Yüksek kaliteli uydu
            const esriSatellite = L.tileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                {
                    attribution: '© Esri',
                    maxZoom: 19
                }
            );
            
            // Esri Hibrit (Uydu + Etiketler)
            const esriHybrid = L.layerGroup([
                L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                    maxZoom: 19
                }),
                L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
                    maxZoom: 19
                })
            ]);
            
            // CartoDB Positron - Şık minimal harita
            const cartoLight = L.tileLayer(
                'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                {
                    attribution: '© CartoDB',
                    maxZoom: 19
                }
            );
            
            // Varsayılan olarak Esri Uydu ekle
            esriSatellite.addTo(this.map);
            
            // Katman kontrolü
            const baseMaps = {
                "🛰️ Uydu Görüntüsü": esriSatellite,
                "🗺️ Uydu + Etiketler": esriHybrid,
                "🗺️ Sokak Haritası": osmLayer,
                "✨ Modern Harita": cartoLight
            };
            
            L.control.layers(baseMaps, null, { 
                position: 'bottomright',
                collapsed: true
            }).addTo(this.map);
            
            // === ÇİZİM KATMANI ===
            this.drawnItems = new L.FeatureGroup();
            this.map.addLayer(this.drawnItems);
            
            // Çizim kontrolleri - Sadece poligon (ortada konumlandırılacak)
            this.drawControl = new L.Control.Draw({
                position: 'topleft',
                edit: {
                    featureGroup: this.drawnItems,
                    remove: true
                },
                draw: {
                    polygon: {
                        allowIntersection: false,
                        showArea: true,
                        shapeOptions: {
                            color: '#10B981',
                            weight: 3,
                            fillOpacity: 0.25,
                            fillColor: '#10B981'
                        },
                        metric: true,
                        feet: false
                    },
                    rectangle: false,
                    polyline: false,
                    circle: false,
                    marker: false,
                    circlemarker: false
                }
            });
            
            // Event listeners
            this.setupEventListeners();
            
            // Harita tıklama
            this.map.on('click', (e) => this.onMapClick(e));
            
            // Harita boyutunu güncelle (gecikmeli)
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
            
            console.log('✅ Harita başarıyla başlatıldı!');
            
        } catch (error) {
            console.error('❌ Harita başlatma hatası:', error);
        }
    },
    
    /**
     * Event listener'ları kur
     */
    setupEventListeners() {
        // DMS Input (Koordinat Yapıştırma)
        const inputDms = document.getElementById('input-dms');
        if (inputDms) {
            inputDms.addEventListener('input', (e) => {
                const val = e.target.value;
                const coords = this.parseDMS(val);
                
                if (coords) {
                    document.getElementById('input-lat').value = coords.lat.toFixed(6);
                    document.getElementById('input-lng').value = coords.lng.toFixed(6);
                    
                    // Otomatik git
                    this.goToCoordinates(coords.lat, coords.lng);
                }
            });
        }
        
        // DMS Arama Butonu
        const btnSearchDms = document.getElementById('btn-search-dms');
        if (btnSearchDms) {
            btnSearchDms.addEventListener('click', () => {
                const val = document.getElementById('input-dms').value;
                const coords = this.parseDMS(val);
                if (coords) {
                    this.goToCoordinates(coords.lat, coords.lng);
                }
            });
        }

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

        // Tarla Çiz butonu
        const btnDraw = document.getElementById('btn-draw');
        if (btnDraw) {
            btnDraw.addEventListener('click', () => {
                this.enableDrawMode();
            });
        }

        // Temizle butonu
        const btnClear = document.getElementById('btn-clear');
        if (btnClear) {
            btnClear.addEventListener('click', () => {
                this.clearAll();
            });
        }

        // Çizim tamamlandığında
        this.map.on('draw:created', (e) => {
            const layer = e.layer;
            this.drawnItems.addLayer(layer);
            
            if (e.layerType === 'polygon' || e.layerType === 'rectangle') {
                // Polygon koordinatlarını al
                const latlngs = layer.getLatLngs()[0];
                this.selectedCoordinates = latlngs.map(ll => [ll.lng, ll.lat]);
                this.selectedCoordinates.push(this.selectedCoordinates[0]); // Polygon'u kapat
                this.currentPolygon = layer;
            } else if (e.layerType === 'marker') {
                const latlng = layer.getLatLng();
                this.selectedCoordinates = [latlng.lng, latlng.lat];
                this.currentMarker = layer;
            }
            
            this.updateCoordinatesDisplay();
            this.enableAnalyzeButton();
            
            // Draw modunu kapat
            this.map.removeControl(this.drawControl);
        });

        // Çizim düzenlendiğinde
        this.map.on('draw:edited', (e) => {
            const layers = e.layers;
            layers.eachLayer((layer) => {
                if (layer instanceof L.Polygon) {
                    const latlngs = layer.getLatLngs()[0];
                    this.selectedCoordinates = latlngs.map(ll => [ll.lng, ll.lat]);
                    this.selectedCoordinates.push(this.selectedCoordinates[0]);
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
    },
    
    /**
     * DMS (Derece Dakika Saniye) formatını parse et
     * Örn: 37°55'34.5"N 29°56'33.1"E
     */
    parseDMS(dmsStr) {
        if (!dmsStr) return null;
        
        // Temizle
        dmsStr = dmsStr.trim();
        
        // Regex: Derece, Dakika, Saniye, Yön (N/S/E/W)
        const dmsRegex = /(\d+)[°]\s*(\d+)[′']\s*(\d+(?:\.\d+)?)[″"]\s*([NSEW])/gi;
        
        const matches = [...dmsStr.matchAll(dmsRegex)];
        
        if (matches.length >= 2) {
            const coords = {};
            
            matches.forEach(match => {
                const deg = parseFloat(match[1]);
                const min = parseFloat(match[2]);
                const sec = parseFloat(match[3]);
                const hemi = match[4].toUpperCase();
                
                let decimal = deg + min/60 + sec/3600;
                
                if (hemi === 'S' || hemi === 'W') {
                    decimal = -decimal;
                }
                
                if (hemi === 'N' || hemi === 'S') {
                    coords.lat = decimal;
                } else {
                    coords.lng = decimal;
                }
            });
            
            if (coords.lat !== undefined && coords.lng !== undefined) {
                return coords;
            }
        }
        
        return null;
    },

    /**
     * Belirtilen koordinata git
     */
    goToCoordinates(lat, lng) {
        // Haritayı oraya odakla
        this.map.flyTo([lat, lng], 15, {
            duration: 1.5
        });
        
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
        if (!this.drawControl._map) {
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
        
        // Draw kontrolünü kaldır
        if (this.drawControl._map) {
            this.map.removeControl(this.drawControl);
        }
    },
    
    /**
     * Koordinat gösterimini güncelle
     */
    updateCoordinatesDisplay() {
        const display = document.getElementById('coords-text');
        
        if (!this.selectedCoordinates) {
            display.textContent = '📍 Haritada bir nokta seçin veya tarla çizin';
            return;
        }
        
        if (Array.isArray(this.selectedCoordinates[0])) {
            // Polygon
            const pointCount = this.selectedCoordinates.length - 1;
            display.textContent = `📐 Polygon seçildi (${pointCount} köşe)`;
        } else {
            // Nokta
            const [lng, lat] = this.selectedCoordinates;
            display.textContent = `📍 Seçilen Konum: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        }
    },
    
    /**
     * Analiz butonunu etkinleştir
     */
    enableAnalyzeButton() {
        const btn = document.getElementById('btn-analyze');
        if (btn) {
            btn.disabled = false;
        }
    },
    
    /**
     * Analiz butonunu devre dışı bırak
     */
    disableAnalyzeButton() {
        const btn = document.getElementById('btn-analyze');
        if (btn) {
            btn.disabled = true;
        }
    },
    
    /**
     * Seçili koordinatları döndür
     */
    getSelectedCoordinates() {
        return this.selectedCoordinates;
    }
};

// Global erişim
window.MapModule = MapModule;
