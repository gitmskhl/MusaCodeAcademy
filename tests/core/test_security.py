import secrets
from app.core.security import hash_password, verify_password

def test_hash_password():
    password = secrets.token_hex(10)
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password(password + "1", hashed)
