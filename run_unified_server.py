#!/usr/bin/env python3
"""
Run the unified SizeComparator server directly
"""

import sys
import os
from pathlib import Path

# Load .env file for API keys and configuration
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f" Loaded environment from {env_path}")
else:
    print("️  Warning: No .env file found. Creating from template...")
    template_path = Path(__file__).parent / '.env.example'
    if template_path.exists():
        import shutil
        shutil.copy(template_path, env_path)
        print(f" Created .env from template. Please edit {env_path} to add your API keys.")

# Check for API keys
api_keys_found = []
if os.getenv('SIZECOMPARATOR_OPENAI_API_KEY'):
    api_keys_found.append('OpenAI')
if os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY'):
    api_keys_found.append('Anthropic')
if os.getenv('SIZECOMPARATOR_XAI_API_KEY'):
    api_keys_found.append('X.AI')

if api_keys_found:
    print(f" Found API keys for: {', '.join(api_keys_found)}")
else:
    print("️  WARNING: No AI provider API keys found!")
    print("   The application will use fallback responses instead of AI-generated ones.")
    print("   To enable AI responses, add at least one API key to your .env file:")
    print("   - SIZECOMPARATOR_OPENAI_API_KEY")
    print("   - SIZECOMPARATOR_ANTHROPIC_API_KEY")
    print("   - SIZECOMPARATOR_XAI_API_KEY")

# Add project root to Python path to ensure proper imports
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Set PYTHONPATH environment variable as well
os.environ['PYTHONPATH'] = str(project_root)

if __name__ == "__main__":
    print(" Starting SizeComparator Unified Server")
    print("=" * 50)
    
    try:
        # Now we can import from src directly
        from src.core.environment import EnvironmentManager
        from src.api.unified_app import create_unified_app, ServiceMode
        
        # Create environment manager
        env_manager = EnvironmentManager()
        print(f" Environment: {env_manager.environment}")
        
        # Create the unified app
        app = create_unified_app(env_manager)
        print(f" App created: {app.title} v{app.version}")
        
        # Show available service modes
        print(f" Available service modes:")
        for mode in ServiceMode:
            print(f"   • {mode.value}: {mode.name}")
        
        # Start the server
        # Determine port
        import sys
        port = 8001 if len(sys.argv) > 1 and sys.argv[1] == "--port-8001" else 8000
        
        print("\n Starting server...")
        print(f" Server will be available at:")
        print(f"   • Main API: http://localhost:{port}/api/compare")
        print(f"   • Health check: http://localhost:{port}/health")
        print(f"   • API status: http://localhost:{port}/api/status")
        print(f"   • API docs: http://localhost:{port}/docs")
        print(f"   • Demo data: http://localhost:{port}/api/demo")
        
        print("\n Example requests:")
        print("   • Basic mode: POST /api/compare?service_mode=basic")
        print("   • Fast validation: POST /api/compare?service_mode=fast_validation")
        print("   • Full validation: POST /api/compare?service_mode=full_validation")
        print("   • Comprehensive: POST /api/compare?service_mode=comprehensive")
        
        print("\n Legacy endpoints (backward compatibility):")
        print("   • POST /api/compare/single (maps to basic)")
        print("   • POST /api/compare/validated (maps to full_validation)")
        print("   • POST /api/compare/fast (maps to fast_validation)")
        
        # Import and start uvicorn
        import uvicorn
        
        # Run the server (port already determined above)
        port = 8001 if len(sys.argv) > 1 and sys.argv[1] == "--port-8001" else 8000
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n️ Server stopped by user")
    except Exception as e:
        print(f"\n Server failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)