/**
 * SizeComparator Frontend Application
 * Main application logic for the weight comparison interface
 */

class SizeComparatorApp {
    constructor() {
        this.api = new SizeComparatorAPI();
        this.comparisonCount = 0; // Initialize to 0
        this.initializeEventListeners();
        this.initializeCounter();
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
     * Initialize the comparison counter
     */
    initializeCounter() {
        this.loadGlobalCounter();
        // Refresh counter periodically
        setInterval(() => this.loadGlobalCounter(), 30000); // Every 30 seconds
    }

    /**
     * Load counter from API
     */
    async loadGlobalCounter() {
        try {
            const response = await fetch('/api/counter');
            if (response.ok) {
                const data = await response.json();
                this.comparisonCount = data.count || 0;
                this.updateCounterDisplay();
            }
        } catch (error) {
            console.error('Failed to load global counter:', error);
            // Just keep the current value if API fails
            this.updateCounterDisplay();
        }
    }

    /**
     * Save counter to localStorage (deprecated - kept for compatibility)
     */
    saveCounter() {
        // No longer using localStorage - backend handles persistence
    }

    /**
     * Update the counter display
     */
    updateCounterDisplay() {
        const counterElement = document.getElementById('counter');
        if (counterElement) {
            counterElement.textContent = this.comparisonCount.toLocaleString();
        }
    }

    /**
     * Increment the comparison counter
     */
    incrementCounter() {
        // Don't increment locally - just reload from server
        // The server already incremented when processing the comparison
        
        // Add animation
        const counterDisplay = document.querySelector('.counter-display');
        if (counterDisplay) {
            counterDisplay.classList.add('increment');
            setTimeout(() => {
                counterDisplay.classList.remove('increment');
            }, 500);
        }
        
        // Reload counter from server to get the real value
        this.loadGlobalCounter();
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
                fastBtn.textContent = 'Processing...';
                resultDiv.innerHTML = 'Processing...';
            } else {
                resultDiv.innerHTML = 'AI processing...';
            }
            
            resultDiv.style.display = 'block';
            resultDiv.className = 'loading';
        } else {
            fastBtn.disabled = false;
            fastBtn.textContent = 'Compare';
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
        
        // Increment counter for successful comparisons
        this.incrementCounter();
        
        // Get validation info
        let validationInfo = '';
        
        if (data.provider_used && data.provider_used.includes('fast_validated')) {
            validationInfo = '<br><strong>Validation:</strong> Fast optimized validation';
        } else if (data.provider_used && data.provider_used.includes('openai')) {
            validationInfo = '<br><strong>Mode:</strong> Single AI call';
        }
        
        // Parse provider info to show model/company
        let providerDisplay = 'Unknown';
        if (data.provider_used) {
            // Extract provider and model from strings like "fast_validated_rule_based_2_calls" or "xai_grok-2"
            if (data.provider_used.includes('xai')) {
                providerDisplay = 'X.AI (Grok-2)';
            } else if (data.provider_used.includes('openai')) {
                providerDisplay = 'OpenAI (GPT-4)';
            } else if (data.provider_used.includes('anthropic')) {
                providerDisplay = 'Anthropic (Claude)';
            } else if (data.provider_used.includes('fallback')) {
                providerDisplay = 'Fallback (Static Data)';
            }
        }
        
        resultDiv.className = 'success';
        resultDiv.innerHTML = `
            <h3>Result:</h3>
            <p style="font-size: 1.3em; margin: 15px 0; line-height: 1.4em;">${data.comparison_text}</p>
            <div class="meta">
                <strong>Weight:</strong> ${data.weight_processed}<br>
                <strong>Response Time:</strong> ${data.response_time_ms}ms<br>
                <strong>Provider:</strong> ${providerDisplay}
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