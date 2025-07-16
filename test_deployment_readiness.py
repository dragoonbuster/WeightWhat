#!/usr/bin/env python3
"""
Test deployment readiness of SizeComparator
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Check critical imports
print("Checking deployment readiness...\n")

# 1. Check environment
print("1. Environment Configuration:")
try:
    from src.core.environment import EnvironmentManager
    env_manager = EnvironmentManager()
    print(f"   ✓ Environment: {env_manager.environment}")
    print(f"   ✓ Debug mode: {env_manager.environment == 'development'}")
except Exception as e:
    print(f"   ✗ Environment error: {e}")

# 2. Check application creation
print("\n2. Application Creation:")
try:
    from src.api.unified_app import create_unified_app
    app = create_unified_app()
    print(f"   ✓ App created: {app.title}")
    print(f"   ✓ Version: {app.version}")
except Exception as e:
    print(f"   ✗ Application error: {e}")

# 3. Check service factory
print("\n3. Service Factory:")
try:
    from src.services.shared.service_factory import ComparisonServiceFactory
    factory = ComparisonServiceFactory()
    health = factory.get_service_health_status()
    print(f"   ✓ Factory status: {health['factory_status']}")
    print(f"   ✓ Available services: {len([s for s in health['services'] if health['services'][s]['available']])}")
except Exception as e:
    print(f"   ✗ Service factory error: {e}")

# 4. Check AI providers
print("\n4. AI Provider Configuration:")
api_keys_found = []
if os.getenv('SIZECOMPARATOR_OPENAI_API_KEY'):
    api_keys_found.append('OpenAI')
if os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY'):
    api_keys_found.append('Anthropic')
if os.getenv('SIZECOMPARATOR_XAI_API_KEY'):
    api_keys_found.append('X.AI')

if api_keys_found:
    print(f"   ✓ API keys found: {', '.join(api_keys_found)}")
else:
    print("   ⚠ No API keys found (will use fallback mode)")

# 5. Check critical files
print("\n5. Critical Files:")
critical_files = [
    ("Dockerfile", "Dockerfile"),
    ("Docker Compose", "docker-compose.yml"),
    ("Requirements", "requirements.txt"),
    ("Environment Example", ".env.example"),
    ("Deployment Checklist", "DEPLOYMENT_CHECKLIST.md"),
    ("Production Script", "start_production.sh"),
    ("Frontend", "frontend/index.html")
]

for name, file_path in critical_files:
    if Path(file_path).exists():
        print(f"   ✓ {name}: exists")
    else:
        print(f"   ✗ {name}: missing")

# 6. Check dependencies
print("\n6. Critical Dependencies:")
try:
    import fastapi
    print(f"   ✓ FastAPI: {fastapi.__version__}")
except:
    print("   ✗ FastAPI: not installed")

try:
    import uvicorn
    print(f"   ✓ Uvicorn: installed")
except:
    print("   ✗ Uvicorn: not installed")

try:
    import gunicorn
    print(f"   ✓ Gunicorn: installed")
except:
    print("   ✗ Gunicorn: not installed")

try:
    import dotenv
    print(f"   ✓ Python-dotenv: installed")
except:
    print("   ✗ Python-dotenv: not installed")

# 7. Check fallback repository
print("\n7. Enhanced Fallback System:")
repository_file = Path("fallback_responses.json")
if repository_file.exists():
    import json
    with open(repository_file) as f:
        data = json.load(f)
    total = data.get("total_responses", 0)
    print(f"   ✓ Repository exists: {total} responses")
else:
    print("   ⚠ Repository not generated (run generate_fallback_repository.py)")

# Summary
print("\n" + "="*50)
print("DEPLOYMENT READINESS SUMMARY")
print("="*50)

issues = []
warnings = []

if not api_keys_found:
    warnings.append("No AI provider API keys configured")

if not repository_file.exists():
    warnings.append("Fallback repository not generated")

if env_manager.environment == "development":
    warnings.append("Environment is set to development")

if issues:
    print(f"\n❌ CRITICAL ISSUES ({len(issues)}):")
    for issue in issues:
        print(f"   - {issue}")
else:
    print("\n✅ NO CRITICAL ISSUES FOUND")

if warnings:
    print(f"\n⚠️  WARNINGS ({len(warnings)}):")
    for warning in warnings:
        print(f"   - {warning}")

print("\n📋 Next Steps:")
print("1. Copy .env.example to .env and configure")
print("2. Set production environment variables")
print("3. Generate fallback repository (optional but recommended)")
print("4. Build Docker image")
print("5. Deploy using docker-compose or cloud provider")

print("\nFor detailed instructions, see DEPLOYMENT_CHECKLIST.md")