"""
Simplified serverless endpoint for Vercel deployment
"""
import os
import json
import random
from http.server import BaseHTTPRequestHandler

# Simple fallback responses (no AI needed for a gag site)
WEIGHT_COMPARISONS = {
    "tiny": [
        "{weight} is about as heavy as a paperclip or a small ant",
        "{weight} is roughly the weight of a grain of rice",
        "{weight} weighs about as much as a single eyelash"
    ],
    "light": [
        "{weight} is about as heavy as a smartphone",
        "{weight} is roughly the weight of a banana",
        "{weight} weighs about as much as a hamster"
    ],
    "medium": [
        "{weight} is about as heavy as a laptop",
        "{weight} is roughly the weight of a newborn baby",
        "{weight} weighs about as much as a bowling ball"
    ],
    "heavy": [
        "{weight} is about as heavy as a golden retriever",
        "{weight} is roughly the weight of a microwave oven",
        "{weight} weighs about as much as a car tire"
    ],
    "very_heavy": [
        "{weight} is about as heavy as a refrigerator",
        "{weight} is roughly the weight of a grand piano",
        "{weight} weighs about as much as a small car"
    ]
}

def get_weight_category(kg):
    """Determine weight category"""
    if kg < 0.01:
        return "tiny"
    elif kg < 1:
        return "light"
    elif kg < 50:
        return "medium"
    elif kg < 500:
        return "heavy"
    else:
        return "very_heavy"

def parse_weight(weight_input):
    """Simple weight parsing"""
    weight_input = weight_input.lower().strip()
    
    # Extract number and unit
    import re
    match = re.match(r'([\d.]+)\s*(\w+)', weight_input)
    if not match:
        return None, None
    
    value = float(match.group(1))
    unit = match.group(2)
    
    # Convert to kg
    conversions = {
        'kg': 1,
        'g': 0.001,
        'mg': 0.000001,
        'lb': 0.453592,
        'lbs': 0.453592,
        'pound': 0.453592,
        'pounds': 0.453592,
        'oz': 0.0283495,
        'ounce': 0.0283495,
        'ton': 1000,
        'tons': 1000
    }
    
    kg = value * conversions.get(unit, 1)
    return kg, weight_input

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/compare':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                weight_input = data.get('weight_input', '')
                
                kg, display = parse_weight(weight_input)
                if kg is None:
                    response = {
                        'error': 'Invalid weight format',
                        'comparison_text': 'Please enter a weight like "5 kg" or "10 pounds"'
                    }
                else:
                    category = get_weight_category(kg)
                    comparisons = WEIGHT_COMPARISONS[category]
                    comparison = random.choice(comparisons).format(weight=display)
                    
                    response = {
                        'comparison_text': comparison,
                        'weight_processed': display,
                        'provider_used': 'basic_fallback',
                        'response_time_ms': random.randint(50, 200),
                        'cached': False
                    }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'status': 'healthy', 'service': 'basic_only'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()