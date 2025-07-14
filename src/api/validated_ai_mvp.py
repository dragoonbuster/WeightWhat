"""
Validated AI MVP - Enhanced accuracy through AI consensus validation
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
from services.ai_validation_service import AIValidationService
from services.mvp_comparison import MVPComparisonError

# Create FastAPI app
app = FastAPI(
    title="SizeComparator Validated AI MVP",
    description="AI-powered weight comparison with accuracy validation through consensus",
    version="0.3.0"
)

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MVP demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize validation service
validation_service = AIValidationService()

@app.on_event("startup")
async def startup_event():
    """Startup initialization"""
    print("🚀 Starting Validated AI SizeComparator MVP")
    health = validation_service.get_health_status()
    print(f"📊 AI Providers: {health['ai_providers']['available_count']} available")
    print(f"🧠 Mode: {health['primary_mode']}")
    print(f"✅ Validation: {'ENABLED' if health['validation_enabled'] else 'DISABLED'}")
    print(f"🔄 Parallel calls: {health['parallel_calls']}")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    await validation_service.cleanup()

@app.get("/", response_class=HTMLResponse)
async def serve_demo_page():
    """Serve enhanced demo HTML page with validation info"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SizeComparator Validated AI MVP</title>
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
            .validation-badge {
                display: inline-block;
                background: linear-gradient(45deg, #ff6b6b, #feca57);
                padding: 10px 20px;
                border-radius: 25px;
                font-weight: bold;
                margin: 10px;
                font-size: 1em;
                text-shadow: none;
                color: white;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            .ai-badge {
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
            .provider-badge {
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                margin-left: 5px;
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
            .accuracy-info {
                background: rgba(0,255,0,0.1);
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #4CAF50;
            }
            .toggle-group {
                display: flex;
                gap: 10px;
                align-items: center;
                margin: 10px 0;
            }
            .toggle-group label {
                margin-bottom: 0;
                font-size: 1em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 SizeComparator Validated AI</h1>
            <div class="subtitle">
                <div class="validation-badge">✅ AI VALIDATION ENABLED</div>
                <br>
                <span class="ai-badge">🧠 3x Parallel Calls</span>
                <span class="ai-badge">🔍 Accuracy Validation</span>
                <span class="ai-badge">🎯 Best Response Selection</span>
                <br><br>
                Enhanced accuracy through AI consensus and validation!
            </div>
            
            <div class="accuracy-info">
                <strong>🎯 How Validation Works:</strong><br>
                1️⃣ Makes 3 parallel AI calls for your weight<br>
                2️⃣ AI validator checks all responses for accuracy<br>
                3️⃣ Discards obviously wrong comparisons<br>
                4️⃣ Returns the best validated comparison
            </div>
            
            <div class="examples">
                <strong>💡 Try these examples:</strong><br>
                <span class="example-item" onclick="setWeight('5 kg')">5 kg</span>
                <span class="example-item" onclick="setWeight('10 pounds')">10 pounds</span>
                <span class="example-item" onclick="setWeight('50 grams')">50 grams</span>
                <span class="example-item" onclick="setWeight('2.5 tons')">2.5 tons</span>
                <span class="example-item" onclick="setWeight('1 ounce')">1 ounce</span>
                <span class="example-item" onclick="setWeight('100 kg')">100 kg</span>
            </div>
            
            <div class="input-group">
                <label for="weight">Weight Input:</label>
                <input type="text" id="weight" placeholder="e.g., 5 kg, 10 pounds, 100 grams" />
            </div>
            
            <div class="input-group">
                <label for="style">AI Comparison Style:</label>
                <select id="style">
                    <option value="default">🎯 Default - Everyday objects</option>
                    <option value="creative">🎨 Creative - Imaginative & fun</option>
                    <option value="technical">⚗️ Technical - Scientific & precise</option>
                </select>
            </div>
            
            <div class="toggle-group">
                <input type="checkbox" id="validation" checked />
                <label for="validation">Enable AI Validation (3x calls + validation)</label>
            </div>
            
            <button onclick="compareWeight()" id="compareBtn">🚀 Generate Validated AI Comparison</button>
            
            <div id="result"></div>
        </div>

        <script>
            function setWeight(weight) {
                document.getElementById('weight').value = weight;
            }

            async function compareWeight() {
                const weight = document.getElementById('weight').value.trim();
                const style = document.getElementById('style').value;
                const validation = document.getElementById('validation').checked;
                const resultDiv = document.getElementById('result');
                const btn = document.getElementById('compareBtn');
                
                if (!weight) {
                    alert('Please enter a weight!');
                    return;
                }
                
                // Show loading state
                btn.disabled = true;
                if (validation) {
                    btn.textContent = '🤖 AI is generating 3 responses + validation...';
                    resultDiv.innerHTML = '🧠 Making 3 parallel AI calls...<br>🔍 Then validating for accuracy...';
                } else {
                    btn.textContent = '🤖 AI is thinking...';
                    resultDiv.innerHTML = '🧠 AI is generating your comparison...';
                }
                resultDiv.style.display = 'block';
                resultDiv.className = 'loading';
                
                try {
                    const endpoint = validation ? '/api/compare/validated' : '/api/compare/single';
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
                    
                    if (response.ok) {
                        // Success
                        resultDiv.className = 'success';
                        
                        // Get provider emoji
                        let providerEmoji = '🤖';
                        if (data.provider_used.includes('validated_consensus')) providerEmoji = '✅';
                        else if (data.provider_used.includes('openai')) providerEmoji = '🧠';
                        else if (data.provider_used.includes('anthropic')) providerEmoji = '🎭';
                        else if (data.provider_used.includes('fallback')) providerEmoji = '🔧';
                        
                        resultDiv.innerHTML = `
                            <h3>📏 ${validation ? 'Validated ' : ''}AI Comparison Result:</h3>
                            <p style="font-size: 1.3em; margin: 15px 0; line-height: 1.4em;">${data.comparison_text}</p>
                            <div class="meta">
                                <strong>📊 Processed Weight:</strong> ${data.weight_processed}<br>
                                <strong>⚡ Response Time:</strong> ${data.response_time_ms}ms<br>
                                <strong>🤖 Provider:</strong> ${providerEmoji} ${data.provider_used}<span class="provider-badge">${data.cached ? 'CACHED' : 'FRESH'}</span><br>
                                <strong>🔍 Request ID:</strong> ${data.request_id}
                                ${validation ? '<br><strong>✅ Accuracy:</strong> Validated through AI consensus' : ''}
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
                
                // Reset button
                btn.disabled = false;
                btn.textContent = '🚀 Generate Validated AI Comparison';
            }
            
            // Allow Enter key to submit
            document.getElementById('weight').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    compareWeight();
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/api/compare/validated", response_model=MVPComparisonResponse)
async def compare_weight_validated(request: MVPComparisonRequest):
    """Validated AI endpoint with consensus checking"""
    try:
        result = await validation_service.create_validated_comparison(request)
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
    """Single AI call endpoint (for comparison)"""
    try:
        result = await validation_service.base_service.create_comparison(request)
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
    """Enhanced health check with validation status"""
    return validation_service.get_health_status()

@app.get("/api/config")
async def get_config():
    """Get current validation configuration"""
    health = validation_service.get_health_status()
    return {
        "validation_enabled": health["validation_enabled"],
        "parallel_calls": health["parallel_calls"],
        "validation_mode": health["validation_mode"],
        "ai_providers": health["ai_providers"]
    }

@app.post("/api/config/validation")
async def toggle_validation(enabled: bool = Query(..., description="Enable/disable validation")):
    """Toggle validation mode"""
    validation_service.validation_enabled = enabled
    return {
        "validation_enabled": enabled,
        "message": f"Validation {'enabled' if enabled else 'disabled'}"
    }

if __name__ == "__main__":
    import uvicorn
    print("✅ Starting Validated AI SizeComparator MVP...")
    print("🎯 Features:")
    print("   • 3x parallel AI calls for consensus")
    print("   • AI validation for accuracy checking")  
    print("   • Automatic discard of wrong responses")
    print("   • Best response selection")
    print("💡 Configure: OPENAI_API_KEY environment variable")
    uvicorn.run(app, host="0.0.0.0", port=8003)