/**
 * SizeComparator Frontend Application
 * Main application logic for the weight comparison interface
 */

class SizeComparatorApp {
    constructor() {
        this.api = new SizeComparatorAPI();
        this.initializeEventListeners();
    }

    /**
     * Initialize event listeners for the interface
     */
    initializeEventListeners() {
        // Allow Enter key to submit
        const weightInput = document.getElementById('weight');
        if (weightInput) {
            weightInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.compareWeight('fast');
                }
            });
        }
    }

    /**
     * Set weight value in the input field (used by example buttons)
     * @param {string} weight - The weight value to set
     */
    setWeight(weight) {
        const weightInput = document.getElementById('weight');
        if (weightInput) {
            weightInput.value = weight;
        }
    }

    /**
     * Compare weight using the specified mode
     * @param {string} mode - Either 'fast' for fast validation or 'single' for single call
     */
    async compareWeight(mode) {
        console.log('compareWeight called with mode:', mode);
        const weight = document.getElementById('weight').value.trim();
        const style = document.getElementById('style').value;
        const resultDiv = document.getElementById('result');
        const fastBtn = document.getElementById('fastBtn');
        
        if (!weight) {
            alert('Please enter a weight!');
            return;
        }
        console.log('Weight:', weight, 'Style:', style);
        
        // Show loading state
        this.setLoadingState(true, mode);
        
        const startTime = Date.now();
        
        try {
            let data;
            
            if (mode === 'fast') {
                data = await this.api.compareWeightFast(weight, style);
            } else {
                data = await this.api.compareWeightSingle(weight, style);
            }
            
            const clientTime = Date.now() - startTime;
            this.showSuccessResult(data, mode, clientTime);
            
        } catch (error) {
            this.showErrorResult(error);
        } finally {
            this.setLoadingState(false, mode);
        }
    }

    /**
     * Set the loading state for buttons and result display
     * @param {boolean} isLoading - Whether the app is in loading state
     * @param {string} mode - The current mode ('fast' or 'single')
     */
    setLoadingState(isLoading, mode) {
        const resultDiv = document.getElementById('result');
        const fastBtn = document.getElementById('fastBtn');
        
        if (isLoading) {
            fastBtn.disabled = true;
            
            if (mode === 'fast') {
                fastBtn.textContent = 'Fast validating...';
                resultDiv.innerHTML = 'Smart validation in progress...<br>Making 2 calls + rule checking...';
            } else {
                resultDiv.innerHTML = 'AI processing...';
            }
            
            resultDiv.style.display = 'block';
            resultDiv.className = 'loading';
        } else {
            fastBtn.disabled = false;
            fastBtn.textContent = 'Fast Validated';
        }
    }

    /**
     * Display successful comparison result
     * @param {Object} data - The response data from the API
     * @param {string} mode - The comparison mode used
     * @param {number} clientTime - Time taken on client side
     */
    showSuccessResult(data, mode, clientTime) {
        const resultDiv = document.getElementById('result');
        
        // Get validation info
        let validationInfo = '';
        
        if (data.provider_used && data.provider_used.includes('fast_validated')) {
            validationInfo = '<br><strong>Validation:</strong> Fast optimized validation';
        } else if (data.provider_used && data.provider_used.includes('openai')) {
            validationInfo = '<br><strong>Mode:</strong> Single AI call';
        }
        
        resultDiv.className = 'success';
        resultDiv.innerHTML = `
            <h3>${mode === 'fast' ? 'Fast Validated' : 'Single Call'} Result:</h3>
            <p style="font-size: 1.3em; margin: 15px 0; line-height: 1.4em;">${data.comparison_text}</p>
            <div class="meta">
                <strong>Weight:</strong> ${data.weight_processed}<br>
                <strong>Server Time:</strong> ${data.response_time_ms}ms<br>
                <strong>Client Time:</strong> ${clientTime}ms<br>
                <strong>Provider:</strong> ${data.provider_used || 'Unknown'}
                ${validationInfo}
            </div>
        `;
    }

    /**
     * Display error result
     * @param {Error} error - The error that occurred
     */
    showErrorResult(error) {
        const resultDiv = document.getElementById('result');
        
        resultDiv.className = 'error';
        
        if (error instanceof APIError) {
            resultDiv.innerHTML = `
                <h3>Error:</h3>
                <p>${error.message}</p>
            `;
        } else {
            resultDiv.innerHTML = `
                <h3>Network Error:</h3>
                <p>Could not connect to the AI service. Please try again.</p>
                <p><strong>Error:</strong> ${error.message}</p>
            `;
        }
    }
}

// Global functions for backward compatibility with HTML onclick attributes
function setWeight(weight) {
    if (window.app) {
        window.app.setWeight(weight);
    }
}

function compareWeight(mode) {
    if (window.app) {
        window.app.compareWeight(mode);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SizeComparatorApp();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SizeComparatorApp;
}