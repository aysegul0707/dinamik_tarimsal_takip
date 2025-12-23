/**
 * API İletişim Modülü
 * Backend ile tüm HTTP iletişimini yönetir
 */

const API = {
    BASE_URL: 'http://localhost:5000/api',
    
    /**
     * Genel HTTP istek fonksiyonu
     */
    async request(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        if (finalOptions.body && typeof finalOptions.body === 'object') {
            finalOptions.body = JSON.stringify(finalOptions.body);
        }
        
        try {
            const response = await fetch(url, finalOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Bir hata oluştu');
            }
            
            return data;
        } catch (error) {
            console.error('API Hatası:', error);
            throw error;
        }
    },
    
    /**
     * Tarla İşlemleri
     */
    fields: {
        async list() {
            return API.request('/fields');
        },
        
        async create(fieldData) {
            return API.request('/fields', {
                method: 'POST',
                body: fieldData
            });
        },
        
        async get(fieldId) {
            return API.request(`/fields/${fieldId}`);
        },
        
        async delete(fieldId) {
            return API.request(`/fields/${fieldId}`, {
                method: 'DELETE'
            });
        }
    },
    
    /**
     * Analiz İşlemleri
     */
    analysis: {
        async analyze(coordinates, startDate, endDate) {
            return API.request('/analyze', {
                method: 'POST',
                body: { coordinates, start_date: startDate, end_date: endDate }
            });
        },
        
        async getTimeseries(coordinates, startDate, endDate) {
            return API.request('/timeseries', {
                method: 'POST',
                body: { coordinates, start_date: startDate, end_date: endDate }
            });
        },
        
        async getCurrent(coordinates) {
            return API.request('/current', {
                method: 'POST',
                body: { coordinates }
            });
        }
    },
    
    /**
     * Risk İşlemleri
     */
    risk: {
        async calculateBaseline(coordinates, fieldId = null) {
            return API.request('/baseline', {
                method: 'POST',
                body: { coordinates, field_id: fieldId }
            });
        },
        
        async calculateRisk(coordinates, fieldId = null) {
            return API.request('/risk', {
                method: 'POST',
                body: { coordinates, field_id: fieldId }
            });
        }
    }
};

// Global erişim için
window.API = API;