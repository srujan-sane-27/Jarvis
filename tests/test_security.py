from src.security.auth import SecurityManager


def test_phrase_normalization():
    sec = SecurityManager()
    assert sec._normalize_phrase("Omega-Protocol-9") == "omega protocol 9"
    assert sec._normalize_phrase("omega protocol nine") == "omega protocol 9"
    assert sec._normalize_phrase("Authorization Code: Omega Protocol 9!") == "authorization code omega protocol 9"


def test_passcode_verification():
    sec = SecurityManager()
    sec.settings.JARVIS_SECRET_CODE = "omega-protocol-9"
    
    # Incorrect attempts
    success, msg = sec.verify_passcode("open sesame")
    assert not success
    assert "Authorization failed" in msg

    # Correct unlock
    success, msg = sec.verify_passcode("authorization code omega protocol 9")
    assert success
    assert sec.is_session_active()

    # Lock system
    sec.lock_system()
    assert not sec.is_session_active()


if __name__ == "__main__":
    test_phrase_normalization()
    test_passcode_verification()
    print("Security unit tests passed successfully!")
