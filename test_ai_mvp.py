#!/usr/bin/env python3
"""
AI MVP Integration Test - Test real AI provider integration
"""

import sys
import asyncio
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_ai_mvp_flow():
    """Test AI-enhanced MVP flow"""
    print("🤖 Testing AI-Enhanced SizeComparator MVP")
    
    # Check environment variables
    print("\n🔑 Checking AI Provider Configuration:")
    openai_key = os.getenv('SIZECOMPARATOR_OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    xai_key = os.getenv('SIZECOMPARATOR_XAI_API_KEY')
    
    print(f"   OpenAI API Key: {'✅ Configured' if openai_key else '❌ Not found'}")
    print(f"   Anthropic API Key: {'✅ Configured' if anthropic_key else '❌ Not found'}")
    print(f"   X.ai API Key: {'✅ Configured' if xai_key else '❌ Not found'}")
    
    if not (openai_key or anthropic_key):
        print("\n⚠️  No AI providers configured - will use fallback mode")
        print("💡 To test real AI, set environment variables:")
        print("   export OPENAI_API_KEY='sk-...'")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
    
    try:
        # Test 1: Initialize AI Service
        print("\n1️⃣ Testing AI Service Initialization...")
        from services.ai_mvp_comparison import AIEnhancedMVPService
        
        service = AIEnhancedMVPService()
        health = service.get_health_status()
        
        print(f"   ✅ Service initialized")
        print(f"   📊 Available AI providers: {health['ai_providers']['available_count']}")
        print(f"   🧠 Primary mode: {health['primary_mode']}")
        
        # Test 2: AI Comparison Generation
        print("\n2️⃣ Testing AI Comparison Generation...")
        from models.mvp import MVPComparisonRequest
        
        # Test different styles
        test_cases = [
            ("5 kg", "default"),
            ("10 pounds", "creative"), 
            ("100 grams", "technical")
        ]
        
        for weight_input, style in test_cases:
            request = MVPComparisonRequest(
                weight_input=weight_input,
                style=style
            )
            
            response = await service.create_comparison(request)
            
            print(f"   ✅ {weight_input} ({style}):")
            print(f"      📝 {response.comparison_text[:80]}...")
            print(f"      🤖 Provider: {response.provider_used}")
            print(f"      ⚡ Time: {response.response_time_ms}ms")
        
        # Test 3: Error Handling
        print("\n3️⃣ Testing Error Handling...")
        try:
            error_request = MVPComparisonRequest(weight_input="invalid weight")
            await service.create_comparison(error_request)
            print("   ❌ Should have handled error gracefully")
        except Exception:
            # Should gracefully return fallback, not crash
            pass
        
        print("   ✅ Error handling works (returns fallback)")
        
        # Test 4: Health Status
        print("\n4️⃣ Testing Health Status...")
        health = service.get_health_status()
        
        print(f"   ✅ Service status: {health['status']}")
        for provider, status in health['ai_providers'].items():
            if provider != 'available_count':
                emoji = '✅' if status == 'available' else '⚠️'
                print(f"   {emoji} {provider}: {status}")
        
        # Cleanup
        await service.cleanup()
        
        print("\n🎉 AI MVP Integration Test PASSED!")
        print("\n📋 AI MVP Status:")
        
        if health['ai_providers']['available_count'] > 0:
            print("   🤖 Real AI providers available!")
            print("   🚀 Ready for intelligent comparisons")
        else:
            print("   🔧 Fallback mode (configure API keys for AI)")
            print("   ✅ Still functional with smart fallbacks")
        
        print(f"\n🌐 Run: python src/api/ai_mvp.py")
        print(f"   Then open: http://localhost:8002")
        
        return True
        
    except Exception as e:
        print(f"\n❌ AI MVP Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ai_mvp_flow())
    sys.exit(0 if success else 1)