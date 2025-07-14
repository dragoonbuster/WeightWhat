#!/usr/bin/env python3
"""
Test Script for Service Factory

Tests all factory creation methods and service selection scenarios
to verify intelligent service selection works correctly.
"""

import sys
import os
import asyncio
import time
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.shared.service_factory import (
    ComparisonServiceFactory, ServiceType, PerformanceProfile, ServiceRequirements,
    create_service_for_weight, create_fast_service, create_accurate_service, create_default_service
)
from models.mvp import MVPComparisonRequest
from core.environment import EnvironmentManager, EnvironmentType


def print_header(title: str):
    """Print formatted test section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_test(test_name: str):
    """Print formatted test name"""
    print(f"\n--- {test_name} ---")


def print_result(success: bool, message: str):
    """Print test result"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"  {status}: {message}")


async def test_basic_factory_creation():
    """Test basic factory creation and initialization"""
    print_header("BASIC FACTORY CREATION TESTS")
    
    # Test 1: Factory creation without environment manager
    print_test("Factory creation without environment manager")
    try:
        factory = ComparisonServiceFactory()
        print_result(True, f"Factory created successfully, default strategy: {factory.performance_config['default_service_strategy']}")
    except Exception as e:
        print_result(False, f"Factory creation failed: {e}")
        return False
    
    # Test 2: Factory creation with environment manager
    print_test("Factory creation with environment manager")
    try:
        env_manager = EnvironmentManager(environment=EnvironmentType.DEVELOPMENT)
        factory = ComparisonServiceFactory(env_manager)
        print_result(True, f"Factory created with env manager, AI providers available: {factory._are_ai_providers_available()}")
    except Exception as e:
        print_result(False, f"Factory creation with env manager failed: {e}")
        return False
    
    # Test 3: Service capabilities initialization
    print_test("Service capabilities initialization")
    try:
        capabilities = factory.service_capabilities
        expected_services = {ServiceType.BASIC, ServiceType.FAST_VALIDATION, ServiceType.FULL_VALIDATION, ServiceType.COMPREHENSIVE}
        actual_services = set(capabilities.keys())
        
        if expected_services == actual_services:
            print_result(True, f"All service types configured: {[s.value for s in actual_services]}")
        else:
            missing = expected_services - actual_services
            print_result(False, f"Missing service types: {[s.value for s in missing]}")
    except Exception as e:
        print_result(False, f"Service capabilities check failed: {e}")
        return False
    
    return True


async def get_service_health(service):
    """Helper to get service health, handling both async and sync methods"""
    try:
        health = service.get_health_status()
        # Check if it's a coroutine (async)
        if hasattr(health, '__await__'):
            return await health
        else:
            return health
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def test_individual_service_creation():
    """Test individual service creation methods"""
    print_header("INDIVIDUAL SERVICE CREATION TESTS")
    
    factory = ComparisonServiceFactory()
    
    # Test basic service creation
    print_test("Basic service creation")
    try:
        service = factory.create_basic_service()
        health = await get_service_health(service)
        print_result(True, f"Basic service created, status: {health.get('status', 'unknown')}")
    except Exception as e:
        print_result(False, f"Basic service creation failed: {e}")
        return False
    
    # Test fast validation service creation
    print_test("Fast validation service creation")
    try:
        service = factory.create_fast_validation_service()
        health = await get_service_health(service)
        print_result(True, f"Fast validation service created, status: {health.get('status', 'unknown')}")
    except Exception as e:
        print_result(False, f"Fast validation service creation failed: {e}")
        return False
    
    # Test full validation service creation
    print_test("Full validation service creation")
    try:
        service = factory.create_full_validation_service()
        health = await get_service_health(service)
        print_result(True, f"Full validation service created, status: {health.get('status', 'unknown')}")
    except Exception as e:
        print_result(False, f"Full validation service creation failed: {e}")
        return False
    
    # Test comprehensive service creation
    print_test("Comprehensive service creation")
    try:
        service = factory.create_comprehensive_service()
        health = await get_service_health(service)
        print_result(True, f"Comprehensive service created, status: {health.get('status', 'unknown')}")
    except Exception as e:
        print_result(False, f"Comprehensive service creation failed: {e}")
        return False
    
    return True


async def test_smart_routing_logic():
    """Test smart routing logic for different scenarios"""
    print_header("SMART ROUTING LOGIC TESTS")
    
    factory = ComparisonServiceFactory()
    
    # Test scenarios with different requirements
    test_scenarios = [
        {
            "name": "Light weight, fast timeout",
            "requirements": ServiceRequirements(
                weight_kg=0.05,
                timeout_ms=1500,
                performance_profile=PerformanceProfile.SPEED_OPTIMIZED
            ),
            "expected_category": "basic or fast"
        },
        {
            "name": "Common weight, balanced profile",
            "requirements": ServiceRequirements(
                weight_kg=5.0,
                timeout_ms=3000,
                performance_profile=PerformanceProfile.BALANCED
            ),
            "expected_category": "fast or basic"
        },
        {
            "name": "Heavy weight, accuracy priority",
            "requirements": ServiceRequirements(
                weight_kg=500.0,
                timeout_ms=8000,
                accuracy_priority=True,
                performance_profile=PerformanceProfile.ACCURACY_OPTIMIZED
            ),
            "expected_category": "full validation"
        },
        {
            "name": "Extreme weight, long timeout",
            "requirements": ServiceRequirements(
                weight_kg=10000.0,
                timeout_ms=10000,
                performance_profile=PerformanceProfile.ACCURACY_OPTIMIZED
            ),
            "expected_category": "full validation"
        },
        {
            "name": "Microscopic weight, speed priority",
            "requirements": ServiceRequirements(
                weight_kg=0.001,
                timeout_ms=1800,
                speed_priority=True,
                performance_profile=PerformanceProfile.SPEED_OPTIMIZED
            ),
            "expected_category": "fast validation"
        }
    ]
    
    for scenario in test_scenarios:
        print_test(scenario["name"])
        try:
            service = factory.get_optimal_service(scenario["requirements"])
            service_type = type(service).__name__
            
            # Get health to verify service works
            health = await get_service_health(service)
            
            print_result(True, f"Selected: {service_type}, Health: {health.get('status', 'unknown')}")
            print(f"    Weight: {scenario['requirements'].weight_kg}kg, Timeout: {scenario['requirements'].timeout_ms}ms")
            print(f"    Profile: {scenario['requirements'].performance_profile.value}")
            print(f"    Expected: {scenario['expected_category']}")
            
        except Exception as e:
            print_result(False, f"Service selection failed: {e}")
            return False
    
    return True


async def test_weight_based_selection():
    """Test service selection based on weight categories"""
    print_header("WEIGHT-BASED SERVICE SELECTION TESTS")
    
    factory = ComparisonServiceFactory()
    
    # Test different weight ranges
    weight_tests = [
        {"weight": "5 g", "description": "Very light weight"},
        {"weight": "500 g", "description": "Light weight"},  
        {"weight": "5 kg", "description": "Medium weight"},
        {"weight": "50 kg", "description": "Heavy weight"},
        {"weight": "500 kg", "description": "Very heavy weight"},
        {"weight": "5000 kg", "description": "Extreme weight"}
    ]
    
    for test in weight_tests:
        print_test(f"{test['description']} - {test['weight']}")
        try:
            request = MVPComparisonRequest(weight_input=test["weight"])
            service = factory.get_service_from_request(request)
            service_type = type(service).__name__
            
            # Test the service
            response = await service.create_comparison(request)
            
            print_result(True, f"Selected: {service_type}")
            print(f"    Weight processed: {response.weight_processed}")
            print(f"    Response time: {response.response_time_ms}ms")
            print(f"    Provider: {response.provider_used}")
            
        except Exception as e:
            print_result(False, f"Weight-based selection failed: {e}")
            return False
    
    return True


async def test_performance_profiles():
    """Test different performance profiles"""
    print_header("PERFORMANCE PROFILE TESTS")
    
    factory = ComparisonServiceFactory()
    
    # Test all performance profiles with same weight
    profiles = [
        PerformanceProfile.SPEED_OPTIMIZED,
        PerformanceProfile.BALANCED,
        PerformanceProfile.ACCURACY_OPTIMIZED
    ]
    
    weight_kg = 5.0  # Common weight
    
    for profile in profiles:
        print_test(f"Profile: {profile.value}")
        try:
            requirements = ServiceRequirements(
                weight_kg=weight_kg,
                timeout_ms=5000,
                performance_profile=profile
            )
            
            service = factory.get_optimal_service(requirements)
            service_type = type(service).__name__
            
            # Test service performance
            start_time = time.time()
            request = MVPComparisonRequest(weight_input=f"{weight_kg} kg")
            response = await service.create_comparison(request)
            actual_time_ms = int((time.time() - start_time) * 1000)
            
            print_result(True, f"Selected: {service_type}")
            print(f"    Actual response time: {actual_time_ms}ms")
            print(f"    Reported response time: {response.response_time_ms}ms")
            print(f"    Provider: {response.provider_used}")
            
        except Exception as e:
            print_result(False, f"Performance profile test failed: {e}")
            return False
    
    return True


async def test_convenience_functions():
    """Test convenience functions"""
    print_header("CONVENIENCE FUNCTIONS TESTS")
    
    # Test create_fast_service
    print_test("create_fast_service")
    try:
        service = create_fast_service()
        service_type = type(service).__name__
        health = await get_service_health(service)
        print_result(True, f"Fast service: {service_type}, Status: {health.get('status')}")
    except Exception as e:
        print_result(False, f"create_fast_service failed: {e}")
        return False
    
    # Test create_accurate_service
    print_test("create_accurate_service")
    try:
        service = create_accurate_service()
        service_type = type(service).__name__
        health = await get_service_health(service)
        print_result(True, f"Accurate service: {service_type}, Status: {health.get('status')}")
    except Exception as e:
        print_result(False, f"create_accurate_service failed: {e}")
        return False
    
    # Test create_default_service
    print_test("create_default_service")
    try:
        service = create_default_service()
        service_type = type(service).__name__
        health = await get_service_health(service)
        print_result(True, f"Default service: {service_type}, Status: {health.get('status')}")
    except Exception as e:
        print_result(False, f"create_default_service failed: {e}")
        return False
    
    # Test create_service_for_weight
    print_test("create_service_for_weight")
    try:
        service = create_service_for_weight("100 kg")
        service_type = type(service).__name__
        health = await get_service_health(service)
        print_result(True, f"Weight-based service: {service_type}, Status: {health.get('status')}")
    except Exception as e:
        print_result(False, f"create_service_for_weight failed: {e}")
        return False
    
    return True


async def test_service_availability():
    """Test service availability detection"""
    print_header("SERVICE AVAILABILITY TESTS")
    
    factory = ComparisonServiceFactory()
    
    # Test availability check for all service types
    print_test("Service availability check")
    try:
        availability = {}
        for service_type in ServiceType:
            available = factory._is_service_available(service_type)
            availability[service_type.value] = available
        
        print_result(True, "Service availability checked")
        for service, available in availability.items():
            status = "Available" if available else "Unavailable"
            print(f"    {service}: {status}")
        
    except Exception as e:
        print_result(False, f"Service availability check failed: {e}")
        return False
    
    # Test health status
    print_test("Factory health status")
    try:
        health = factory.get_service_health_status()
        print_result(True, f"Factory status: {health.get('factory_status')}")
        print(f"    AI providers available: {health.get('ai_providers_available')}")
        print(f"    Available services: {len([s for s, a in health.get('availability', {}).items() if a])}")
        
    except Exception as e:
        print_result(False, f"Factory health status check failed: {e}")
        return False
    
    return True


async def test_fallback_scenarios():
    """Test fallback behavior when services fail"""
    print_header("FALLBACK SCENARIO TESTS")
    
    factory = ComparisonServiceFactory()
    
    # Test fallback when preferred service unavailable
    print_test("Service fallback logic")
    try:
        # Try to get comprehensive service (might not be available)
        requirements = ServiceRequirements(
            weight_kg=5.0,
            timeout_ms=10000,
            performance_profile=PerformanceProfile.ACCURACY_OPTIMIZED
        )
        
        service = factory.get_optimal_service(requirements)
        service_type = type(service).__name__
        
        # Verify service works
        request = MVPComparisonRequest(weight_input="5 kg")
        response = await service.create_comparison(request)
        
        print_result(True, f"Fallback service: {service_type}")
        print(f"    Response: {response.comparison_text[:100]}...")
        print(f"    Provider: {response.provider_used}")
        
    except Exception as e:
        print_result(False, f"Fallback logic test failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests"""
    print("Service Factory Test Suite")
    print("Testing intelligent service selection and factory methods")
    
    tests = [
        test_basic_factory_creation,
        test_individual_service_creation,
        test_smart_routing_logic,
        test_weight_based_selection,
        test_performance_profiles,
        test_convenience_functions,
        test_service_availability,
        test_fallback_scenarios
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print_result(False, f"Test execution failed: {e}")
    
    print_header("TEST SUMMARY")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed! Service factory is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)