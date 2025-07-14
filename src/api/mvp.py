"""
MVP FastAPI Application for SizeComparator Demo
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.mvp import MVPComparisonRequest, MVPComparisonResponse, MVPErrorResponse
from services.mvp_comparison import MVPComparisonService, MVPComparisonError

# Create FastAPI app
app = FastAPI(
    title="SizeComparator MVP",
    description="Simple weight comparison demo using AI",
    version="0.1.0"
)

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MVP demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
comparison_service = MVPComparisonService()

@app.get("/", response_class=HTMLResponse)
async def serve_demo_page():
    """Serve simple demo HTML page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SizeComparator MVP Demo</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
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
            }
            h1 { 
                text-align: center; 
                color: white;
                margin-bottom: 30px;
                font-size: 2.5em;
            }
            .input-group {
                margin: 20px 0;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }
            input, select, button {
                width: 100%;
                padding: 12px;
                margin: 5px 0;
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }
            button {
                background: #4CAF50;
                color: white;
                cursor: pointer;
                font-weight: bold;
                transition: background 0.3s;
            }
            button:hover {
                background: #45a049;
            }
            button:disabled {
                background: #cccccc;
                cursor: not-allowed;
            }
            #result {
                margin-top: 20px;
                padding: 20px;
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                min-height: 50px;
                display: none;
            }
            .loading {
                text-align: center;
                color: #ffd700;
            }
            .error {
                color: #ff6b6b;
                background: rgba(255,0,0,0.1);
            }
            .success {
                color: #51cf66;
            }
            .meta {
                font-size: 0.9em;
                opacity: 0.8;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 SizeComparator MVP</h1>
            <p style="text-align: center; font-size: 1.2em; margin-bottom: 30px;">
                Enter any weight and discover what it compares to!
            </p>
            
            <div class="input-group">
                <label for="weight">Weight Input:</label>
                <input type="text" id="weight" placeholder="e.g., 5 kg, 10 pounds, 100 grams" />
            </div>
            
            <div class="input-group">
                <label for="style">Comparison Style:</label>
                <select id="style">
                    <option value="default">Default</option>
                    <option value="creative">Creative</option>
                    <option value="technical">Technical</option>
                </select>
            </div>
            
            <button onclick="compareWeight()" id="compareBtn">Compare Weight</button>
            
            <div id="result"></div>
        </div>

        <script>
            async function compareWeight() {
                const weight = document.getElementById('weight').value.trim();
                const style = document.getElementById('style').value;
                const resultDiv = document.getElementById('result');
                const btn = document.getElementById('compareBtn');
                
                if (!weight) {
                    alert('Please enter a weight!');
                    return;
                }
                
                // Show loading state
                btn.disabled = true;
                btn.textContent = 'Comparing...';
                resultDiv.style.display = 'block';
                resultDiv.className = 'loading';
                resultDiv.innerHTML = '🔄 Processing your weight comparison...';
                
                try {
                    const response = await fetch('/api/compare', {
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
                        resultDiv.innerHTML = `
                            <h3>📏 Comparison Result:</h3>
                            <p style="font-size: 1.2em; margin: 15px 0;">${data.comparison_text}</p>
                            <div class="meta">
                                <strong>Processed:</strong> ${data.weight_processed}<br>
                                <strong>Response Time:</strong> ${data.response_time_ms}ms<br>
                                <strong>Provider:</strong> ${data.provider_used}<br>
                                <strong>Request ID:</strong> ${data.request_id}
                            </div>
                        `;
                    } else {
                        // Error
                        resultDiv.className = 'error';
                        resultDiv.innerHTML = `
                            <h3>❌ Error:</h3>
                            <p>${data.error}</p>
                            ${data.suggestions ? '<p><strong>Suggestions:</strong><br>' + data.suggestions.join('<br>') + '</p>' : ''}
                        `;
                    }
                } catch (error) {
                    // Network error
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `
                        <h3>❌ Network Error:</h3>
                        <p>Could not connect to the server. Please try again.</p>
                        <p><strong>Error:</strong> ${error.message}</p>
                    `;
                }
                
                // Reset button
                btn.disabled = false;
                btn.textContent = 'Compare Weight';
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

@app.post("/api/compare", response_model=MVPComparisonResponse)
async def compare_weight(request: MVPComparisonRequest):
    """MVP endpoint for weight comparison"""
    try:
        result = await comparison_service.create_comparison(request)
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
    """Simple health check"""
    return comparison_service.get_health_status()

@app.get("/api/demo")
async def demo_data():
    """Demo endpoint showing example requests"""
    return {
        "examples": [
            {"weight_input": "5 kg", "description": "5 kilograms"},
            {"weight_input": "10 pounds", "description": "10 pounds"},
            {"weight_input": "100 grams", "description": "100 grams"},
            {"weight_input": "2.5 tons", "description": "2.5 metric tons"},
            {"weight_input": "1 ounce", "description": "1 ounce"}
        ],
        "supported_units": ["kg", "lbs", "grams", "ounces", "tons", "pounds"],
        "available_styles": ["default", "creative", "technical"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)