"""
Pytest configuration and shared fixtures for SizeComparator tests.

This file provides common test fixtures and configuration for all test modules.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.environment import EnvironmentManager, EnvironmentType
from src.models.mvp import MVPComparisonRequest, MVPComparisonResponse
from src.services.shared.service_factory import ComparisonServiceFactory, ServiceRequirements, PerformanceProfile


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_manager():
    """Mock environment manager for testing"""
    mock = Mock(spec=EnvironmentManager)
    mock.environment = EnvironmentType.DEVELOPMENT
    mock.get_variable.return_value = None
    return mock


@pytest.fixture
def test_env_manager():
    """Real environment manager configured for testing"""
    return EnvironmentManager(environment=EnvironmentType.DEVELOPMENT)


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    return Mock()


@pytest.fixture
def sample_mvp_request():
    """Sample MVP comparison request for testing"""
    return MVPComparisonRequest(
        weight_input="5 kg",
        style="default",
        provider="auto"
    )


@pytest.fixture
def sample_mvp_requests():
    """Multiple sample MVP requests for testing"""
    return [
        MVPComparisonRequest(weight_input="5 kg", style="default"),
        MVPComparisonRequest(weight_input="10 pounds", style="creative"),
        MVPComparisonRequest(weight_input="100 grams", style="technical"),
        MVPComparisonRequest(weight_input="2.5 tons", style="default"),
        MVPComparisonRequest(weight_input="1 ounce", style="creative")
    ]


@pytest.fixture
def sample_service_requirements():
    """Sample service requirements for testing"""
    return ServiceRequirements(
        weight_kg=5.0,
        timeout_ms=3000,
        performance_profile=PerformanceProfile.BALANCED
    )


@pytest.fixture
def mock_service_factory():
    """Mock service factory for testing"""
    factory = Mock(spec=ComparisonServiceFactory)
    factory.get_service_health_status.return_value = {
        "factory_status": "healthy",
        "services": {},
        "availability": {},
        "ai_providers_available": False
    }
    return factory


@pytest.fixture
def test_service_factory(test_env_manager):
    """Real service factory for integration tests"""
    return ComparisonServiceFactory(test_env_manager)


@pytest.fixture
def mock_ai_provider_keys():
    """Mock AI provider API keys for testing"""
    return {
        "SIZECOMPARATOR_OPENAI_API_KEY": "test-openai-key",
        "SIZECOMPARATOR_ANTHROPIC_API_KEY": "test-anthropic-key",
        "SIZECOMPARATOR_XAI_API_KEY": "test-xai-key"
    }


@pytest.fixture
def mock_comparison_response():
    """Mock comparison response for testing"""
    return MVPComparisonResponse(
        comparison_text="Test comparison result",
        weight_processed="5.0 kg",
        provider_used="test_provider",
        response_time_ms=150,
        cached=False
    )


@pytest.fixture
def disable_ai_providers(monkeypatch):
    """Disable AI providers for testing fallback behavior"""
    monkeypatch.delenv("SIZECOMPARATOR_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SIZECOMPARATOR_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SIZECOMPARATOR_XAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def enable_ai_providers(monkeypatch, mock_ai_provider_keys):
    """Enable AI providers for testing AI functionality"""
    for key, value in mock_ai_provider_keys.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary configuration file for testing"""
    config_content = """
# Test configuration
services:
  comparison:
    timeout_ms: 5000
    enable_caching: true
    
providers:
  openai:
    model: gpt-4
    temperature: 0.3
  anthropic:
    model: claude-3-sonnet-20240229
    temperature: 0.2
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file


# Performance test fixtures
@pytest.fixture
def performance_test_weights():
    """Weight inputs for performance testing"""
    return [
        "1 g",      # Very light
        "100 g",    # Light
        "5 kg",     # Medium
        "50 kg",    # Heavy
        "1000 kg",  # Very heavy
        "10 tons"   # Extreme
    ]


@pytest.fixture
def timeout_test_scenarios():
    """Timeout scenarios for testing"""
    return [
        {"timeout_ms": 1000, "expected_service": "basic"},
        {"timeout_ms": 2000, "expected_service": "fast_validation"},
        {"timeout_ms": 5000, "expected_service": "full_validation"},
        {"timeout_ms": 10000, "expected_service": "comprehensive"}
    ]


# Integration test fixtures
@pytest.fixture
def integration_test_enabled():
    """Check if integration tests should run"""
    return os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"


@pytest.fixture
def real_ai_api_key():
    """Real AI API key for integration tests"""
    return (
        os.getenv("SIZECOMPARATOR_OPENAI_API_KEY") or
        os.getenv("SIZECOMPARATOR_ANTHROPIC_API_KEY") or
        os.getenv("SIZECOMPARATOR_XAI_API_KEY")
    )


# Skip markers for conditional tests
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require real API keys)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take several seconds)"
    )
    config.addinivalue_line(
        "markers", "ai_required: marks tests that require AI providers"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests that measure performance"
    )


def pytest_runtest_setup(item):
    """Setup for individual test items"""
    # Skip integration tests if not enabled
    if item.get_closest_marker("integration"):
        if not os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true":
            pytest.skip("Integration tests not enabled")
    
    # Skip AI tests if no API keys available
    if item.get_closest_marker("ai_required"):
        if not any([
            os.getenv("SIZECOMPARATOR_OPENAI_API_KEY"),
            os.getenv("SIZECOMPARATOR_ANTHROPIC_API_KEY"),
            os.getenv("SIZECOMPARATOR_XAI_API_KEY")
        ]):
            pytest.skip("AI providers not configured")