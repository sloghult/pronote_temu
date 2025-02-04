from cryptography.fernet import Fernet
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def generate_key(password: str, salt: bytes = None) -> bytes:
    """Génère une clé de cryptage à partir d'un mot de passe."""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_password(password: str, key: bytes) -> str:
    """Crypte un mot de passe avec une clé donnée."""
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str, key: bytes) -> str:
    """Décrypte un mot de passe avec une clé donnée."""
    f = Fernet(key)
    return f.decrypt(encrypted_password.encode()).decode()
