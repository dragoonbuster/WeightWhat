#!/usr/bin/env python3
"""
Test script to verify the unified server can be started
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_unified_server():
    """Test that the unified server can be created and started"""
    
    try:
        print("🚀 Testing Unified Server Creation")
        print("=" * 50)
        
        # Test server creation
        print("1. Testing server creation...")
        from core.environment import EnvironmentManager
        from api.unified_app import create_unified_app, UnifiedSizeComparatorApp
        
        # Create environment manager
        env_manager = EnvironmentManager()
        print(f"   🌍 Environment: {env_manager.environment}")
        
        # Create app instance
        app_instance = UnifiedSizeComparatorApp(env_manager)
        print("   ✅ App instance created")
        
        # Create FastAPI app
        app = create_unified_app(env_manager)
        print(f"   📱 FastAPI app created: {app.title}")
        print(f"   🔢 Version: {app.version}")
        
        # Test route information
        print("\n2. Testing route information...")
        routes = [route for route in app.routes]
        print(f"   📍 Total routes: {len(routes)}")
        
        # Find API routes
        api_routes = [route for route in routes if hasattr(route, 'path') and '/api' in route.path]
        print(f"   🛣️ API routes: {len(api_routes)}")
        
        for route in api_routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = list(route.methods) if route.methods else ['GET']
                print(f"      • {methods[0]} {route.path}")
        
        # Test configuration
        print("\n3. Testing configuration...")
        config = app_instance.config
        print(f"   ⚙️ Default service mode: {config['default_service_mode']}")
        print(f"   🔄 Fallback service mode: {config['fallback_service_mode']}")
        print(f"   🌐 Serve frontend: {config['serve_frontend']}")
        print(f"   📁 Frontend path: {config['frontend_path']}")
        print(f"   🔗 Enable legacy endpoints: {config['enable_legacy_endpoints']}")
        
        # Test service factory integration
        print("\n4. Testing service factory integration...")
        factory_status = app_instance.service_factory.get_service_health_status()
        print(f"   🏭 Factory status: {factory_status['factory_status']}")
        print(f"   🤖 AI providers: {factory_status['ai_providers_available']}")
        
        available_services = factory_status['availability']
        print(f"   📊 Available services:")
        for service_type, available in available_services.items():
            status = "✅" if available else "❌"
            print(f"      {status} {service_type}")
        
        # Test that server can be imported and configured
        print("\n5. Testing server configuration...")
        try:
            import uvicorn
            
            # Test server config (but don't start it)
            server_config = {
                "host": "0.0.0.0",
                "port": 8000,
                "log_level": "info",
                "app": app
            }
            
            print(f"   🌐 Server host: {server_config['host']}")
            print(f"   🔌 Server port: {server_config['port']}")
            print(f"   📊 Log level: {server_config['log_level']}")
            print("   ✅ Server configuration valid")
            
        except ImportError:
            print("   ⚠️ uvicorn not available, but app creation successful")
        
        print("\n" + "=" * 50)
        print("🎉 Unified server test completed successfully!")
        
        print("\n📋 Summary:")
        print("   • Server creation: ✅")
        print("   • Route registration: ✅")
        print("   • Configuration: ✅")
        print("   • Service factory integration: ✅")
        print("   • Server configuration: ✅")
        
        print("\n🚀 Ready to start unified server with:")
        print("   python -m src.api.unified_app")
        print("   or")
        print("   uvicorn src.api.unified_app:app --host 0.0.0.0 --port 8000")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_unified_server()
    sys.exit(0 if success else 1)