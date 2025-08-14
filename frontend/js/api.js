// API Configuration and Utilities
class API {
    constructor() {
        this.baseURL = 'http://localhost:8000/api/v1';
        this.setupInterceptors();
    }

    setupInterceptors() {
        // Add request interceptor for authentication
        this.addRequestInterceptor((config) => {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers = config.headers || {};
                config.headers['Authorization'] = `Bearer ${token}`;
            }
            return config;
        });

        // Add response interceptor for token refresh
        this.addResponseInterceptor(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;
                
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    
                    try {
                        const refreshToken = localStorage.getItem('refresh_token');
                        if (refreshToken) {
                            const response = await this.refreshToken(refreshToken);
                            localStorage.setItem('access_token', response.access_token);
                            
                            // Retry the original request
                            originalRequest.headers['Authorization'] = `Bearer ${response.access_token}`;
                            return this.request(originalRequest);
                        }
                    } catch (refreshError) {
                        // Refresh failed, redirect to login
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        window.location.reload();
                    }
                }
                
                return Promise.reject(error);
            }
        );
    }

    async request(config) {
        try {
            const response = await fetch(`${this.baseURL}${config.url}`, {
                method: config.method || 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...config.headers
                },
                body: config.data ? JSON.stringify(config.data) : undefined
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    async refreshToken(refreshToken) {
        const response = await fetch(`${this.baseURL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
            throw new Error('Token refresh failed');
        }

        return await response.json();
    }

    addRequestInterceptor(interceptor) {
        this.requestInterceptor = interceptor;
    }

    addResponseInterceptor(successInterceptor, errorInterceptor) {
        this.responseSuccessInterceptor = successInterceptor;
        this.responseErrorInterceptor = errorInterceptor;
    }
}

// Create API instance
const api = new API();

// Authentication API
const authAPI = {
    async login(credentials) {
        return api.request({
            url: '/auth/login',
            method: 'POST',
            data: credentials
        });
    },

    async register(userData) {
        return api.request({
            url: '/auth/register',
            method: 'POST',
            data: userData
        });
    },

    async getCurrentUser() {
        return api.request({
            url: '/auth/me'
        });
    },

    async refreshToken(refreshToken) {
        return api.request({
            url: '/auth/refresh',
            method: 'POST',
            data: { refresh_token: refreshToken }
        });
    },

    async changePassword(passwordData) {
        return api.request({
            url: '/auth/change-password',
            method: 'POST',
            data: passwordData
        });
    },

    async logout() {
        return api.request({
            url: '/auth/logout',
            method: 'POST'
        });
    }
};

// Users API
const usersAPI = {
    async getUsers(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return api.request({
            url: `/users?${queryString}`
        });
    },

    async getUser(userId) {
        return api.request({
            url: `/users/${userId}`
        });
    },

    async createUser(userData) {
        return api.request({
            url: '/users',
            method: 'POST',
            data: userData
        });
    },

    async updateUser(userId, userData) {
        return api.request({
            url: `/users/${userId}`,
            method: 'PUT',
            data: userData
        });
    },

    async deleteUser(userId) {
        return api.request({
            url: `/users/${userId}`,
            method: 'DELETE'
        });
    },

    async activateUser(userId) {
        return api.request({
            url: `/users/${userId}/activate`,
            method: 'POST'
        });
    },

    async deactivateUser(userId) {
        return api.request({
            url: `/users/${userId}/deactivate`,
            method: 'POST'
        });
    },

    async getUserStats() {
        return api.request({
            url: '/users/stats'
        });
    }
};

// Scraping API
const scrapingAPI = {
    async getJobs(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return api.request({
            url: `/scraping/jobs?${queryString}`
        });
    },

    async getJob(jobId) {
        return api.request({
            url: `/scraping/jobs/${jobId}`
        });
    },

    async createJob(jobData) {
        return api.request({
            url: '/scraping/jobs',
            method: 'POST',
            data: jobData
        });
    },

    async updateJob(jobId, jobData) {
        return api.request({
            url: `/scraping/jobs/${jobId}`,
            method: 'PUT',
            data: jobData
        });
    },

    async deleteJob(jobId) {
        return api.request({
            url: `/scraping/jobs/${jobId}`,
            method: 'DELETE'
        });
    },

    async startJob(jobId) {
        return api.request({
            url: `/scraping/jobs/${jobId}/start`,
            method: 'POST'
        });
    },

    async cancelJob(jobId) {
        return api.request({
            url: `/scraping/jobs/${jobId}/cancel`,
            method: 'POST'
        });
    },

    async retryJob(jobId) {
        return api.request({
            url: `/scraping/jobs/${jobId}/retry`,
            method: 'POST'
        });
    },

    async scrapeImmediate(scrapingData) {
        return api.request({
            url: '/scraping/immediate',
            method: 'POST',
            data: scrapingData
        });
    },

    async getScrapingStats() {
        return api.request({
            url: '/scraping/stats'
        });
    }
};

// Validation API
const validationAPI = {
    async validateCard(cardData) {
        return api.request({
            url: '/validation/validate',
            method: 'POST',
            data: cardData
        });
    },

    async batchValidate(cardsData) {
        return api.request({
            url: '/validation/batch',
            method: 'POST',
            data: cardsData
        });
    },

    async getValidationHistory(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return api.request({
            url: `/validation/history?${queryString}`
        });
    },

    async getValidationResult(resultId) {
        return api.request({
            url: `/validation/results/${resultId}`
        });
    },

    async deleteValidationResult(resultId) {
        return api.request({
            url: `/validation/results/${resultId}`,
            method: 'DELETE'
        });
    },

    async getValidationStats() {
        return api.request({
            url: '/validation/stats'
        });
    }
};

// Cards API
const cardsAPI = {
    async getCards(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return api.request({
            url: `/cards?${queryString}`
        });
    },

    async getCard(cardId) {
        return api.request({
            url: `/cards/${cardId}`
        });
    },

    async createCard(cardData) {
        return api.request({
            url: '/cards',
            method: 'POST',
            data: cardData
        });
    },

    async updateCard(cardId, cardData) {
        return api.request({
            url: `/cards/${cardId}`,
            method: 'PUT',
            data: cardData
        });
    },

    async deleteCard(cardId) {
        return api.request({
            url: `/cards/${cardId}`,
            method: 'DELETE'
        });
    },

    async validateCard(cardId, validationData = {}) {
        return api.request({
            url: `/cards/${cardId}/validate`,
            method: 'POST',
            data: validationData
        });
    },

    async getCardStats() {
        return api.request({
            url: '/cards/stats'
        });
    }
};

// Jobs API (General)
const jobsAPI = {
    async getJobs(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return api.request({
            url: `/jobs?${queryString}`
        });
    },

    async getJob(jobId) {
        return api.request({
            url: `/jobs/${jobId}`
        });
    },

    async updateJob(jobId, jobData) {
        return api.request({
            url: `/jobs/${jobId}`,
            method: 'PUT',
            data: jobData
        });
    },

    async deleteJob(jobId) {
        return api.request({
            url: `/jobs/${jobId}`,
            method: 'DELETE'
        });
    },

    async pauseJob(jobId) {
        return api.request({
            url: `/jobs/${jobId}/pause`,
            method: 'POST'
        });
    },

    async resumeJob(jobId) {
        return api.request({
            url: `/jobs/${jobId}/resume`,
            method: 'POST'
        });
    },

    async retryJob(jobId) {
        return api.request({
            url: `/jobs/${jobId}/retry`,
            method: 'POST'
        });
    },

    async getJobStats() {
        return api.request({
            url: '/jobs/stats'
        });
    }
};

// Export APIs for global use
window.authAPI = authAPI;
window.usersAPI = usersAPI;
window.scrapingAPI = scrapingAPI;
window.validationAPI = validationAPI;
window.cardsAPI = cardsAPI;
window.jobsAPI = jobsAPI;