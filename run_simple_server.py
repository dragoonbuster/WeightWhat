#!/usr/bin/env python3
"""
Run the simplified SizeComparator server.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"Loaded environment from {env_path}")

# Check for API keys
api_keys_found = []
if os.getenv('SIZECOMPARATOR_OPENAI_API_KEY'):
    api_keys_found.append('OpenAI')
if os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY'):
    api_keys_found.append('Anthropic')
if os.getenv('SIZECOMPARATOR_XAI_API_KEY'):
    api_keys_found.append('X.AI')

if api_keys_found:
    print(f"Found API keys for: {', '.join(api_keys_found)}")
else:
    print("WARNING: No AI provider API keys found!")
    print("The application will use fallback responses only.")

if __name__ == "__main__":
    print("Starting SizeComparator Simplified Server")
    print("=" * 50)
    
    # Import app
    from src.api.simple_app import app
    
    # Determine port
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    print(f"Server will be available at:")
    print(f"  • Frontend: http://localhost:{port}")
    print(f"  • API: http://localhost:{port}/api/compare")
    print(f"  • Counter: http://localhost:{port}/api/counter")
    print(f"  • Docs: http://localhost:{port}/docs")
    
    # Run server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")