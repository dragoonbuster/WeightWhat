"""
Fast Validated AI MVP - <2 second response time with smart validation
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.mvp import MVPComparisonRequest, MVPComparisonResponse, MVPErrorResponse
from services.fast_validation_service import FastValidationService
from services.ai_mvp_comparison import AIEnhancedMVPService
from services.mvp_comparison import MVPComparisonError

# Create FastAPI app
app = FastAPI(
    title="SizeComparator Fast Validated AI",
    description="AI-powered weight comparison with <2 second validation",
    version="0.4.0"
)

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
fast_validation_service = FastValidationService()
single_service = AIEnhancedMVPService()

@app.on_event("startup")
async def startup_event():
    """Startup initialization"""
    print("⚡ Starting Fast Validated AI SizeComparator")
    health = fast_validation_service.get_health_status()
    print(f"📊 AI Providers: {health['ai_providers']['available_count']} available")
    print(f"🧠 Mode: {health['validation_mode']}")
    print(f"⏱️  Target: {health['target_response_time']}")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    await fast_validation_service.cleanup()
    await single_service.cleanup()

@app.get("/", response_class=HTMLResponse)
async def serve_demo_page():
    """Serve fast validation demo page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SizeComparator Fast Validated AI</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                max-width: 900px; 
                margin: 0 auto; 
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }
            h1 { 
                text-align: center; 
                color: white;
                margin-bottom: 20px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .subtitle {
                text-align: center;
                font-size: 1.2em;
                margin-bottom: 30px;
                opacity: 0.9;
            }
            .speed-badge {
                display: inline-block;
                background: linear-gradient(45deg, #ff6b6b, #feca57);
                padding: 12px 24px;
                border-radius: 30px;
                font-weight: bold;
                margin: 10px;
                font-size: 1.1em;
                text-shadow: none;
                color: white;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            .method-badge {
                display: inline-block;
                background: linear-gradient(45deg, #4ecdc4, #44a08d);
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                margin: 0 5px;
                font-size: 0.9em;
                text-shadow: none;
                color: white;
            }
            .input-group {
                margin: 20px 0;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                font-size: 1.1em;
            }
            input, select, button {
                width: 100%;
                padding: 15px;
                margin: 5px 0;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                box-sizing: border-box;
            }
            input, select {
                background: rgba(255,255,255,0.9);
                color: #333;
            }
            button {
                background: linear-gradient(45deg, #4CAF50, #45a049);
                color: white;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s;
                border: none;
                font-size: 18px;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            }
            button:disabled {
                background: #cccccc;
                cursor: not-allowed;
                transform: none;
            }
            #result {
                margin-top: 20px;
                padding: 20px;
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                min-height: 50px;
                display: none;
                border-left: 5px solid #4CAF50;
            }
            .loading {
                text-align: center;
                color: #ffd700;
                animation: pulse 2s infinite;
            }
            .error {
                color: #ff6b6b;
                background: rgba(255,0,0,0.1);
                border-left-color: #ff6b6b;
            }
            .success {
                color: #51cf66;
            }
            .meta {
                font-size: 0.9em;
                opacity: 0.8;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid rgba(255,255,255,0.2);
            }
            .fast-indicator {
                background: rgba(0,255,0,0.1);
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #4CAF50;
            }
            .examples {
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .example-item {
                display: inline-block;
                background: rgba(255,255,255,0.1);
                padding: 5px 10px;
                margin: 3px;
                border-radius: 15px;
                cursor: pointer;
                transition: background 0.3s;
                font-size: 0.9em;
            }
            .example-item:hover {
                background: rgba(255,255,255,0.3);
            }
            .comparison-buttons {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin: 20px 0;
            }
            .comparison-buttons button {
                padding: 10px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ Fast Validated AI</h1>
            <div class="subtitle">
                <div class="speed-badge">⚡ &lt;2 Second Response Time</div>
                <br>
                <span class="method-badge">🚀 Smart Validation</span>
                <span class="method-badge">🎯 Rule-Based Filtering</span>
                <span class="method-badge">⚡ Fast AI Selection</span>
                <br><br>
                Optimized accuracy with lightning speed!
            </div>
            
            <div class="fast-indicator">
                <strong>⚡ Fast Validation Strategy:</strong><br>
                • <strong>Common weights (1-100kg):</strong> 2 parallel calls + rule validation<br>
                • <strong>Extreme weights:</strong> 3 calls + quick AI validation<br>
                • <strong>Auto-fallback:</strong> Single call if needed for speed
            </div>
            
            <div class="examples">
                <strong>💡 Try these examples:</strong><br>
                <span class="example-item" onclick="setWeight('75 kg')">75 kg</span>
                <span class="example-item" onclick="setWeight('25 pounds')">25 pounds</span>
                <span class="example-item" onclick="setWeight('500 grams')">500 grams</span>
                <span class="example-item" onclick="setWeight('0.5 tons')">0.5 tons</span>
                <span class="example-item" onclick="setWeight('50 kg')">50 kg</span>
            </div>
            
            <div class="input-group">
                <label for="weight">Weight Input:</label>
                <input type="text" id="weight" placeholder="e.g., 75 kg, 25 pounds, 500 grams" />
            </div>
            
            <div class="input-group">
                <label for="style">Comparison Style:</label>
                <select id="style">
                    <option value="default">🎯 Default - Quick & accurate</option>
                    <option value="creative">🎨 Creative - More detailed</option>
                    <option value="technical">⚗️ Technical - Precise</option>
                </select>
            </div>
            
            <div class="comparison-buttons">
                <button onclick="compareWeight('fast')" id="fastBtn">⚡ Fast Validated (&lt;2s)</button>
                <button onclick="compareWeight('single')" id="singleBtn">🚀 Single Call (&lt;3s)</button>
            </div>
            
            <div id="result"></div>
        </div>

        <script>
            function setWeight(weight) {
                document.getElementById('weight').value = weight;
            }

            async function compareWeight(mode) {
                const weight = document.getElementById('weight').value.trim();
                const style = document.getElementById('style').value;
                const resultDiv = document.getElementById('result');
                const fastBtn = document.getElementById('fastBtn');
                const singleBtn = document.getElementById('singleBtn');
                
                if (!weight) {
                    alert('Please enter a weight!');
                    return;
                }
                
                // Show loading state
                fastBtn.disabled = true;
                singleBtn.disabled = true;
                
                if (mode === 'fast') {
                    fastBtn.textContent = '⚡ Fast validating...';
                    resultDiv.innerHTML = '⚡ Smart validation in progress...<br>🧠 Making 2 calls + rule checking...';
                } else {
                    singleBtn.textContent = '🚀 AI thinking...';
                    resultDiv.innerHTML = '🧠 Single AI call in progress...';
                }
                
                resultDiv.style.display = 'block';
                resultDiv.className = 'loading';
                
                const startTime = Date.now();
                
                try {
                    const endpoint = mode === 'fast' ? '/api/compare/fast' : '/api/compare/single';
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            weight_input: weight,
                            style: style
                        })
                    });
                    
                    const data = await response.json();
                    const clientTime = Date.now() - startTime;
                    
                    if (response.ok) {
                        // Success
                        resultDiv.className = 'success';
                        
                        // Get provider emoji
                        let providerEmoji = '⚡';
                        let validationInfo = '';
                        
                        if (data.provider_used.includes('fast_validated')) {
                            providerEmoji = '⚡';
                            validationInfo = '<br><strong>⚡ Validation:</strong> Fast optimized validation';
                        } else if (data.provider_used.includes('openai')) {
                            providerEmoji = '🧠';
                            validationInfo = '<br><strong>🚀 Mode:</strong> Single AI call';
                        }
                        
                        resultDiv.innerHTML = `
                            <h3>📏 ${mode === 'fast' ? 'Fast Validated' : 'Single Call'} Result:</h3>
                            <p style="font-size: 1.3em; margin: 15px 0; line-height: 1.4em;">${data.comparison_text}</p>
                            <div class="meta">
                                <strong>📊 Weight:</strong> ${data.weight_processed}<br>
                                <strong>⚡ Server Time:</strong> ${data.response_time_ms}ms<br>
                                <strong>🌐 Client Time:</strong> ${clientTime}ms<br>
                                <strong>🤖 Provider:</strong> ${providerEmoji} ${data.provider_used}
                                ${validationInfo}
                            </div>
                        `;
                    } else {
                        // Error
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `
                            <h3>❌ Error:</h3>
                            <p>${data.error || data.detail}</p>
                        `;
                    }
                } catch (error) {
                    // Network error
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `
                        <h3>❌ Network Error:</h3>
                        <p>Could not connect to the AI service. Please try again.</p>
                        <p><strong>Error:</strong> ${error.message}</p>
                    `;
                }
                
                // Reset buttons
                fastBtn.disabled = false;
                singleBtn.disabled = false;
                fastBtn.textContent = '⚡ Fast Validated (<2s)';
                singleBtn.textContent = '🚀 Single Call (<3s)';
            }
            
            // Allow Enter key to submit
            document.getElementById('weight').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    compareWeight('fast');
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/api/compare/fast", response_model=MVPComparisonResponse)
async def compare_weight_fast(request: MVPComparisonRequest):
    """Fast validated AI endpoint - <2 second target"""
    try:
        result = await fast_validation_service.create_fast_validated_comparison(request)
        return result
    except MVPComparisonError as e:
        raise HTTPException(status_code=400, detail=e.to_response().dict())
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": f"Internal server error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "request_id": "unknown"
            }
        )

@app.post("/api/compare/single", response_model=MVPComparisonResponse)
async def compare_weight_single(request: MVPComparisonRequest):
    """Single AI call endpoint"""
    try:
        result = await single_service.create_comparison(request)
        return result
    except MVPComparisonError as e:
        raise HTTPException(status_code=400, detail=e.to_response().dict())
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": f"Internal server error: {str(e)}",
                "error_code": "INTERNAL_ERROR", 
                "request_id": "unknown"
            }
        )

@app.get("/health")
async def health_check():
    """Health check with performance info"""
    return fast_validation_service.get_health_status()

@app.get("/api/performance")
async def get_performance_info():
    """Get performance optimization info"""
    return {
        "optimization_strategy": "smart_validation",
        "target_response_time": "< 2 seconds",
        "validation_methods": {
            "common_weights": "2 parallel calls + rule validation",
            "extreme_weights": "3 calls + quick AI validation",
            "fallback": "single call for speed"
        },
        "rule_validation": "Weight magnitude checks, object reasonableness, number validation",
        "ai_validation": "Quick selection prompt with 2s timeout"
    }

if __name__ == "__main__":
    import uvicorn
    print("⚡ Starting Fast Validated AI SizeComparator...")
    print("🎯 Target: <2 second response time")
    print("🧠 Strategy: Smart validation with rule-based filtering")
    print("💡 Configure: OPENAI_API_KEY environment variable")
    uvicorn.run(app, host="0.0.0.0", port=8004)