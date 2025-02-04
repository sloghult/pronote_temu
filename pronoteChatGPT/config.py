import os
from dotenv import load_dotenv
from app.utils.crypto import decrypt_password, generate_key
import base64

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    
    # Récupérer les informations de connexion à la base de données
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'pronote1')
    
    # Décrypter le mot de passe de la base de données
    try:
        CRYPTO_KEY = base64.urlsafe_b64decode(os.environ.get('CRYPTO_KEY', '').encode())
        ENCRYPTED_DB_PASS = os.environ.get('ENCRYPTED_DB_PASS')
        if CRYPTO_KEY and ENCRYPTED_DB_PASS:
            DB_PASS = decrypt_password(ENCRYPTED_DB_PASS, CRYPTO_KEY)
        else:
            DB_PASS = os.environ.get('DB_PASS', '')
    except Exception as e:
        print(f"Erreur lors du décryptage du mot de passe: {e}")
        DB_PASS = os.environ.get('DB_PASS', '')

    # Construire l'URL de connexion
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE = 280
    SQLALCHEMY_POOL_SIZE = 10
