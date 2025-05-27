import pytest
from veo_custom_video_app.backend.auth.auth import get_password_hash, verify_password

# --- Tests for get_password_hash ---

def test_get_password_hash_returns_string():
    """Test that get_password_hash returns a non-empty string."""
    hashed_password = get_password_hash("plainpassword123")
    assert isinstance(hashed_password, str)
    assert len(hashed_password) > 0

def test_get_password_hash_different_for_same_password():
    """
    Test that hashing the same password twice yields different results
    due to bcrypt's salting mechanism.
    """
    hashed1 = get_password_hash("samesamepassword")
    hashed2 = get_password_hash("samesamepassword")
    assert hashed1 != hashed2

# --- Tests for verify_password ---

def test_verify_password_correct():
    """Test that verify_password returns True for a correct password."""
    plain_password = "correctpassword"
    hashed_password = get_password_hash(plain_password)
    assert verify_password(plain_password, hashed_password) is True

def test_verify_password_incorrect():
    """Test that verify_password returns False for an incorrect password."""
    plain_password = "correctpassword"
    hashed_password = get_password_hash(plain_password)
    assert verify_password("incorrectPa$$word", hashed_password) is False

def test_verify_password_empty_input():
    """
    Test verify_password behavior with empty inputs.
    Passlib's verify typically raises an error for malformed or empty hash strings.
    """
    # Check behavior with empty plain password against a valid hash
    hashed_password = get_password_hash("somepassword")
    assert verify_password("", hashed_password) is False
    
    # Passlib's verify raises ValueError (or a subclass like passlib.exc.MalformedHashError)
    # for malformed/empty hashes. We'll catch broadly with Exception or more specific if known.
    # passlib.exc.MissingHashError is raised if hash is None or empty string
    from passlib.exc import MissingHashError, MalformedHashError

    with pytest.raises((MissingHashError, MalformedHashError, ValueError)):
        verify_password("anypassword", "") # Empty hash string

    with pytest.raises((MissingHashError, MalformedHashError, ValueError)):
        verify_password("", "") # Empty plain password and empty hash string

def test_verify_password_with_non_bcrypt_hash():
    """
    Test verify_password with a hash string that is not a valid bcrypt hash.
    Passlib's context.verify should return False if the hash isn't recognized
    by any verifier in the context (our context only has bcrypt).
    """
    plain_password = "testpassword"
    not_a_bcrypt_hash = "this_is_definitely_not_a_bcrypt_hash_string"
    # Depending on the exact format and passlib version, this might return False
    # or raise MalformedHashError if it loosely resembles a known scheme but is invalid.
    # If it's completely unrecognized, it should return False.
    try:
        assert verify_password(plain_password, not_a_bcrypt_hash) is False
    except Exception as e:
        # If it raises an error for being malformed beyond just not matching,
        # that's also acceptable as it's not a valid hash for the context.
        print(f"Note: verify_password raised {type(e).__name__} for non-bcrypt hash, which is also acceptable.")
        assert isinstance(e, (MalformedHashError, ValueError))

def test_verify_password_with_different_bcrypt_hash_same_password():
    """
    Test that verify_password still works even if two hashes for the same password
    are different (due to different salts), as long as the password matches.
    """
    plain_password = "saltypassword"
    hashed1 = get_password_hash(plain_password)
    hashed2 = get_password_hash(plain_password) # This will be different from hashed1
    
    assert hashed1 != hashed2 # Confirm hashes are different
    assert verify_password(plain_password, hashed1) is True
    assert verify_password(plain_password, hashed2) is True


# --- Tests for create_access_token ---
from datetime import timedelta, datetime, timezone 
from jose import jwt, JWTError 
from veo_custom_video_app.backend.auth.auth import (
    create_access_token, 
    SECRET_KEY, 
    ALGORITHM, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)

def test_create_access_token_returns_string():
    token = create_access_token(data={"sub": "testuser@example.com"})
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_access_token_payload_default_expiry():
    user_email = "testuser@example.com"
    token = create_access_token(data={"sub": user_email})
    
    # Decode the token to verify its contents
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == user_email
    assert "exp" in payload
    
    # Check that the expiration time is approximately correct
    expected_exp_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    actual_exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) # Ensure timezone aware for comparison
    
    # Allow a small delta for the time taken to generate the token
    assert abs((expected_exp_time - actual_exp_time).total_seconds()) < 5 # 5 seconds tolerance

def test_create_access_token_payload_custom_expiry():
    user_email = "anotheruser@example.com"
    custom_delta = timedelta(hours=1)
    token = create_access_token(data={"sub": user_email}, expires_delta=custom_delta)
    
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == user_email
    assert "exp" in payload
    
    expected_exp_time = datetime.now(timezone.utc) + custom_delta
    actual_exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    
    assert abs((expected_exp_time - actual_exp_time).total_seconds()) < 5

def test_create_access_token_additional_claims():
    user_email = "claimuser@example.com"
    additional_data = {"user_id": 123, "role": "tester"}
    token_data = {"sub": user_email, **additional_data} # Combine subject with other claims
    
    token = create_access_token(data=token_data)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == user_email
    assert payload["user_id"] == 123
    assert payload["role"] == "tester"
    assert "exp" in payload
    
def test_create_access_token_empty_data():
    # Technically, create_access_token({"sub": ""}) is valid for encoding,
    # but the 'sub' claim should ideally not be empty.
    # The function itself doesn't validate the content of 'data' beyond it being a dict.
    token = create_access_token(data={}) # No 'sub'
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "sub" not in payload # Or it might be None if data.get("sub") was used internally and data was {}
                               # Current create_access_token copies data, so if no "sub", it's not in payload.
    assert "exp" in payload

# --- Tests for get_current_user and get_current_active_user ---
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
# pytest is already imported at the top

# JWTError, SECRET_KEY, ALGORITHM are already imported from jose & auth.auth for create_access_token tests
from veo_custom_video_app.backend.auth.auth import get_current_user, get_current_active_user
from veo_custom_video_app.backend.app.models import User as UserModel

@pytest.mark.asyncio
async def test_get_current_user_valid_token_active_user():
    mock_db_session = MagicMock()
    test_user_email = "test@example.com"
    
    # Mock the user object that the DB query would return
    mock_user_instance = UserModel(id=1, email=test_user_email, hashed_password="fakehash", is_active=True)
    mock_db_session.query(UserModel).filter().first.return_value = mock_user_instance
    
    # Valid token payload
    token_payload = {"sub": test_user_email}
    # A dummy token string; its content doesn't matter as jwt.decode is mocked
    dummy_token_str = "valid.dummy.token" 

    with patch('veo_custom_video_app.backend.auth.auth.jwt.decode', return_value=token_payload) as mock_jwt_decode:
        user = await get_current_user(token=dummy_token_str, db=mock_db_session)
        
        mock_jwt_decode.assert_called_once_with(dummy_token_str, SECRET_KEY, algorithms=[ALGORITHM])
        mock_db_session.query(UserModel).filter(UserModel.email == test_user_email).first.assert_called_once()
        assert user == mock_user_instance
        assert user.email == test_user_email

@pytest.mark.asyncio
async def test_get_current_user_invalid_token_jwt_error():
    mock_db_session = MagicMock() # Not strictly needed as error should raise before DB call
    dummy_token_str = "invalid.dummy.token"

    with patch('veo_custom_video_app.backend.auth.auth.jwt.decode', side_effect=JWTError("Invalid token")) as mock_jwt_decode:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=dummy_token_str, db=mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail
        mock_jwt_decode.assert_called_once_with(dummy_token_str, SECRET_KEY, algorithms=[ALGORITHM])

@pytest.mark.asyncio
async def test_get_current_user_token_missing_sub_claim():
    mock_db_session = MagicMock()
    token_payload_no_sub = {"foo": "bar"} # No 'sub' claim
    dummy_token_str = "dummy.token.no.sub"

    with patch('veo_custom_video_app.backend.auth.auth.jwt.decode', return_value=token_payload_no_sub):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=dummy_token_str, db=mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_current_user_user_not_found_in_db():
    mock_db_session = MagicMock()
    test_user_email = "notfound@example.com"
    
    # Mock DB query to return None (user not found)
    mock_db_session.query(UserModel).filter().first.return_value = None
    
    token_payload = {"sub": test_user_email}
    dummy_token_str = "dummy.token.user.not.found"

    with patch('veo_custom_video_app.backend.auth.auth.jwt.decode', return_value=token_payload):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=dummy_token_str, db=mock_db_session)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail 
        mock_db_session.query(UserModel).filter(UserModel.email == test_user_email).first.assert_called_once()

# Tests for get_current_active_user (which depends on get_current_user)

@pytest.mark.asyncio
async def test_get_current_active_user_inactive_user():
    # Mock the user object that get_current_user would return
    mock_inactive_user = UserModel(id=2, email="inactive@example.com", hashed_password="hash", is_active=False)
    
    with pytest.raises(HTTPException) as exc_info:
        # Directly pass the mocked user to the function we are unit testing
        await get_current_active_user(current_user=mock_inactive_user) 
        
    assert exc_info.value.status_code == 400 
    assert "Inactive user" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_current_active_user_active_user():
    mock_active_user = UserModel(id=1, email="active@example.com", hashed_password="hash", is_active=True)
    
    user = await get_current_active_user(current_user=mock_active_user)
    assert user == mock_active_user
