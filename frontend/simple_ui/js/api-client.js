/**
 * API Client for SizeComparator Backend
 * Handles communication with the FastAPI backend
 */

class SizeComparatorAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    /**
     * Make a comparison request using fast validation
     * @param {string} weightInput - The weight input string
     * @param {string} style - The comparison style (default, creative, technical)
     * @returns {Promise<Object>} The comparison response
     */
    async compareWeightFast(weightInput, style = 'default') {
        return this._makeRequest('/api/compare/fast', {
            weight_input: weightInput,
            style: style
        });
    }

    /**
     * Make a comparison request using single AI call
     * @param {string} weightInput - The weight input string
     * @param {string} style - The comparison style (default, creative, technical)
     * @returns {Promise<Object>} The comparison response
     */
    async compareWeightSingle(weightInput, style = 'default') {
        return this._makeRequest('/api/compare/single', {
            weight_input: weightInput,
            style: style
        });
    }

    /**
     * Get health status of the API
     * @returns {Promise<Object>} Health status response
     */
    async getHealthStatus() {
        const response = await fetch(`${this.baseUrl}/health`);
        return response.json();
    }

    /**
     * Get performance optimization information
     * @returns {Promise<Object>} Performance info response
     */
    async getPerformanceInfo() {
        const response = await fetch(`${this.baseUrl}/api/performance`);
        return response.json();
    }

    /**
     * Internal method to make POST requests
     * @private
     */
    async _makeRequest(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const responseData = await response.json();
        
        if (!response.ok) {
            throw new APIError(responseData, response.status);
        }
        
        return responseData;
    }
}

/**
 * Custom error class for API errors
 */
class APIError extends Error {
    constructor(responseData, status) {
        super(responseData.error || responseData.detail || 'API Error');
        this.name = 'APIError';
        this.status = status;
        this.data = responseData;
    }
}

// Export for module use or global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SizeComparatorAPI, APIError };
} else {
    window.SizeComparatorAPI = SizeComparatorAPI;
    window.APIError = APIError;
}