from app.api.auth import create_password_reset_token, verify_password_reset_token
from app.services.email import send_password_reset_email

def test_password_reset_token_creation_and_verification():
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = create_password_reset_token(user_id)
    assert token is not None
    assert isinstance(token, str)

    extracted_user_id = verify_password_reset_token(token)
    assert extracted_user_id == user_id

def test_invalid_password_reset_token():
    assert verify_password_reset_token("invalid.token.string") is None

def test_send_password_reset_email_logging():
    # Test that logging fallback works when SMTP is unconfigured
    result = send_password_reset_email("test@example.com", "fake-token-123")
    assert result is True

if __name__ == "__main__":
    test_password_reset_token_creation_and_verification()
    test_invalid_password_reset_token()
    test_send_password_reset_email_logging()
    print("All password reset unit tests passed successfully!")
