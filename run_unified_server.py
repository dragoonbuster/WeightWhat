#!/usr/bin/env python3
"""
Run the unified SizeComparator server directly
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    print("🚀 Starting SizeComparator Unified Server")
    print("=" * 50)
    
    try:
        # Import and create the application
        from core.environment import EnvironmentManager
        from api.unified_app import create_unified_app, ServiceMode
        
        # Create environment manager
        env_manager = EnvironmentManager()
        print(f"🌍 Environment: {env_manager.environment}")
        
        # Create the unified app
        app = create_unified_app(env_manager)
        print(f"📱 App created: {app.title} v{app.version}")
        
        # Show available service modes
        print(f"🎯 Available service modes:")
        for mode in ServiceMode:
            print(f"   • {mode.value}: {mode.name}")
        
        # Start the server
        print("\n🚀 Starting server...")
        print("🌐 Server will be available at:")
        print("   • Main API: http://localhost:8000/api/compare")
        print("   • Health check: http://localhost:8000/health")
        print("   • API status: http://localhost:8000/api/status")
        print("   • API docs: http://localhost:8000/docs")
        print("   • Demo data: http://localhost:8000/api/demo")
        
        print("\n📋 Example requests:")
        print("   • Basic mode: POST /api/compare?service_mode=basic")
        print("   • Fast validation: POST /api/compare?service_mode=fast_validation")
        print("   • Full validation: POST /api/compare?service_mode=full_validation")
        print("   • Comprehensive: POST /api/compare?service_mode=comprehensive")
        
        print("\n🔧 Legacy endpoints (backward compatibility):")
        print("   • POST /api/compare/single (maps to basic)")
        print("   • POST /api/compare/validated (maps to full_validation)")
        print("   • POST /api/compare/fast (maps to fast_validation)")
        
        # Import and start uvicorn
        import uvicorn
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)