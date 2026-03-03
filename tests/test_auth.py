"""Authentication tests."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from provisioning.auth.service import AuthService, JWT_SECRET
from provisioning.auth.schemas import (
    UserCreate,
    UserUpdate,
    APIKeyCreate,
    LoginRequest,
    TokenPayload,
)


# =============================================================================
# Password Hashing Tests
# =============================================================================

def test_password_hashing():
    """Test password hash and verify."""
    password = "secure-password-123"
    hash1 = AuthService.hash_password(password)
    hash2 = AuthService.hash_password(password)
    
    # Different hashes (bcrypt salting)
    assert hash1 != hash2
    
    # Both verify correctly
    assert AuthService.verify_password(password, hash1)
    assert AuthService.verify_password(password, hash2)
    
    # Wrong password fails
    assert not AuthService.verify_password("wrong-password", hash1)


def test_api_key_hashing():
    """Test API key hashing (SHA-256, deterministic)."""
    key = "cg_test-key-12345"
    hash1 = AuthService.hash_api_key(key)
    hash2 = AuthService.hash_api_key(key)
    
    # Same hash (SHA-256 is deterministic)
    assert hash1 == hash2
    
    # Different key = different hash
    hash3 = AuthService.hash_api_key("cg_different-key")
    assert hash1 != hash3


# =============================================================================
# JWT Token Tests
# =============================================================================

def test_create_and_decode_token():
    """Test JWT token creation and decoding."""
    # Mock user
    user = MagicMock()
    user.id = "user-123"
    user.email = "test@example.com"
    user.is_admin = False
    user.tenant_id = "tenant-456"
    
    # Create mock service (no DB needed for token ops)
    service = AuthService(None)
    
    # Create token
    token, expires_in = service.create_access_token(user)
    
    assert token
    assert expires_in > 0
    
    # Decode token
    payload = AuthService.decode_token(token)
    
    assert payload is not None
    assert payload.sub == "user-123"
    assert payload.email == "test@example.com"
    assert payload.is_admin is False
    assert payload.tenant_id == "tenant-456"
    assert payload.exp > datetime.utcnow().timestamp()


def test_expired_token():
    """Test that expired tokens fail validation."""
    user = MagicMock()
    user.id = "user-123"
    user.email = "test@example.com"
    user.is_admin = False
    user.tenant_id = None
    
    service = AuthService(None)
    
    # Create token with very short expiry
    token, _ = service.create_access_token(user, expires_delta=timedelta(seconds=-1))
    
    # Should fail to decode
    payload = AuthService.decode_token(token)
    assert payload is None


def test_invalid_token():
    """Test that invalid tokens fail validation."""
    payload = AuthService.decode_token("invalid-token")
    assert payload is None
    
    payload = AuthService.decode_token("")
    assert payload is None


# =============================================================================
# User Management Tests
# =============================================================================

@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_user(mock_session):
    """Test user creation."""
    service = AuthService(mock_session)
    
    request = UserCreate(
        email="new@example.com",
        name="New User",
        password="secure123",
        is_admin=False,
    )
    
    # Mock add to capture the user
    created_user = None
    def capture_user(user):
        nonlocal created_user
        created_user = user
    mock_session.add = capture_user
    
    await service.create_user(request)
    
    assert created_user is not None
    assert created_user.email == "new@example.com"
    assert created_user.name == "New User"
    assert created_user.is_admin is False
    # Password should be hashed
    assert created_user.password_hash != "secure123"
    assert AuthService.verify_password("secure123", created_user.password_hash)


@pytest.mark.asyncio
async def test_authenticate_success(mock_session):
    """Test successful authentication."""
    # Create a mock user
    password = "correct-password"
    password_hash = AuthService.hash_password(password)
    
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.email = "user@example.com"
    mock_user.password_hash = password_hash
    mock_user.is_active = True
    mock_user.locked_until = None
    mock_user.failed_attempts = 0
    
    # Mock the query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.authenticate("user@example.com", password)
    
    assert result is mock_user
    assert mock_user.failed_attempts == 0
    assert mock_user.last_login is not None


@pytest.mark.asyncio
async def test_authenticate_wrong_password(mock_session):
    """Test failed authentication increments failed_attempts."""
    password_hash = AuthService.hash_password("correct-password")
    
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.is_active = True
    mock_user.locked_until = None
    mock_user.failed_attempts = 0
    mock_user.password_hash = password_hash
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.authenticate("user@example.com", "wrong-password")
    
    assert result is None
    assert mock_user.failed_attempts == 1


@pytest.mark.asyncio
async def test_authenticate_locked_account(mock_session):
    """Test that locked accounts cannot authenticate."""
    mock_user = MagicMock()
    mock_user.is_active = True
    mock_user.locked_until = datetime.utcnow() + timedelta(minutes=10)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.authenticate("user@example.com", "any-password")
    
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_inactive_account(mock_session):
    """Test that inactive accounts cannot authenticate."""
    mock_user = MagicMock()
    mock_user.is_active = False
    mock_user.locked_until = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.authenticate("user@example.com", "any-password")
    
    assert result is None


# =============================================================================
# API Key Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_api_key(mock_session):
    """Test API key creation returns raw key only once."""
    service = AuthService(mock_session)
    
    request = APIKeyCreate(
        name="Test Key",
        description="For testing",
    )
    
    created_key = None
    def capture_key(key):
        nonlocal created_key
        created_key = key
    mock_session.add = capture_key
    
    api_key, raw_key = await service.create_api_key("user-123", request)
    
    # Raw key returned
    assert raw_key.startswith("cg_")
    assert len(raw_key) > 20
    
    # Model has hash, not raw key
    assert created_key.key_hash != raw_key
    assert created_key.key_prefix == raw_key[:10]
    assert created_key.name == "Test Key"
    assert created_key.user_id == "user-123"


@pytest.mark.asyncio
async def test_create_api_key_with_expiry(mock_session):
    """Test API key with expiration."""
    service = AuthService(mock_session)
    
    request = APIKeyCreate(
        name="Expiring Key",
        expires_in_days=30,
    )
    
    created_key = None
    def capture_key(key):
        nonlocal created_key
        created_key = key
    mock_session.add = capture_key
    
    await service.create_api_key("user-123", request)
    
    assert created_key.expires_at is not None
    # Should expire in ~30 days
    delta = created_key.expires_at - datetime.utcnow()
    assert 29 <= delta.days <= 30


@pytest.mark.asyncio
async def test_validate_api_key_success(mock_session):
    """Test successful API key validation."""
    raw_key = "cg_test-key-for-validation"
    key_hash = AuthService.hash_api_key(raw_key)
    
    mock_api_key = MagicMock()
    mock_api_key.key_hash = key_hash
    mock_api_key.is_active = True
    mock_api_key.expires_at = None
    mock_api_key.user_id = "user-123"
    mock_api_key.last_used_at = None
    mock_api_key.use_count = 0
    
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.is_active = True
    
    # First call returns API key, second returns user
    call_count = [0]
    def mock_execute(query):
        result = MagicMock()
        if call_count[0] == 0:
            result.scalar_one_or_none = MagicMock(return_value=mock_api_key)
        else:
            result.scalar_one_or_none = MagicMock(return_value=mock_user)
        call_count[0] += 1
        return result
    
    mock_session.execute = AsyncMock(side_effect=mock_execute)
    
    service = AuthService(mock_session)
    result = await service.validate_api_key(raw_key)
    
    assert result is not None
    api_key, user = result
    assert api_key is mock_api_key
    assert user is mock_user
    # Usage tracking updated
    assert mock_api_key.use_count == 1
    assert mock_api_key.last_used_at is not None


@pytest.mark.asyncio
async def test_validate_expired_api_key(mock_session):
    """Test that expired API keys fail validation."""
    raw_key = "cg_expired-key"
    key_hash = AuthService.hash_api_key(raw_key)
    
    mock_api_key = MagicMock()
    mock_api_key.key_hash = key_hash
    mock_api_key.is_active = True
    mock_api_key.expires_at = datetime.utcnow() - timedelta(days=1)  # Expired
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_api_key)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.validate_api_key(raw_key)
    
    assert result is None


@pytest.mark.asyncio
async def test_validate_revoked_api_key(mock_session):
    """Test that revoked API keys fail validation."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.validate_api_key("cg_revoked-key")
    
    assert result is None


# =============================================================================
# Password Change Tests
# =============================================================================

@pytest.mark.asyncio
async def test_change_password_success(mock_session):
    """Test successful password change."""
    old_password = "old-password"
    new_password = "new-password"
    old_hash = AuthService.hash_password(old_password)
    
    mock_user = MagicMock()
    mock_user.password_hash = old_hash
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.change_password("user-123", old_password, new_password)
    
    assert result is True
    # Password hash should be updated
    assert mock_user.password_hash != old_hash
    assert AuthService.verify_password(new_password, mock_user.password_hash)


@pytest.mark.asyncio
async def test_change_password_wrong_current(mock_session):
    """Test password change with wrong current password."""
    mock_user = MagicMock()
    mock_user.password_hash = AuthService.hash_password("actual-password")
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_session.execute.return_value = mock_result
    
    service = AuthService(mock_session)
    result = await service.change_password("user-123", "wrong-password", "new-password")
    
    assert result is False


# =============================================================================
# Summary
# =============================================================================

"""
Test coverage:
- Password hashing (bcrypt): hash, verify, uniqueness
- API key hashing (SHA-256): deterministic hash
- JWT tokens: create, decode, expiry, invalid
- User authentication: success, wrong password, locked, inactive
- API keys: create, expiry, validate, revoked
- Password change: success, wrong current password

Total: 15 tests
"""
