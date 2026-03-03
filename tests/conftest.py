"""
Pytest configuration and shared fixtures for ClawGeeks Platform tests.
"""

import os
import pytest

# Set test environment variables before any imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-integration-tests")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
os.environ.setdefault("COOLIFY_API_URL", "http://localhost:3000")
os.environ.setdefault("COOLIFY_API_KEY", "fake-coolify-key")


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
