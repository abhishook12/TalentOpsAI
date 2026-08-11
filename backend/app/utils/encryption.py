import os
from cryptography.fernet import Fernet

# For MVP, we derive a key from a fixed secret or generate one.
# In production, this should come from an environment variable ENCRYPTION_KEY.
# We'll use a fixed key here to avoid breaking on restart if env var is missing.
_env_key = os.getenv("ENCRYPTION_KEY", "uO_kM1o3lqWbzB5bHq2w8VnUu2T9s-A7aV9R7w9g0_c=")
_fernet = Fernet(_env_key.encode('utf-8'))

def encrypt_token(plain_text: str) -> str:
    if not plain_text:
        return plain_text
    return _fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_token(cipher_text: str) -> str:
    if not cipher_text:
        return cipher_text
    try:
        return _fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception:
        # If decryption fails (e.g. key change or old plain text), return as-is
        # This allows graceful transition from plain text to encrypted.
        return cipher_text
