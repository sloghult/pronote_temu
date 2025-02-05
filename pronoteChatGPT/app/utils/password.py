from hashlib import pbkdf2_hmac
import os
import base64
import logging

logger = logging.getLogger(__name__)

def hash_password(password: str) -> tuple[str, str]:
    """Hash a password using PBKDF2-SHA256.
    
    Returns:
        tuple: (hashed_password, salt_b64)
    """
    salt = os.urandom(16)  # Generate a random 16-byte salt
    # Use PBKDF2-SHA256 with 100,000 iterations
    hash_bytes = pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    # Encode both the hash and salt in base64 for storage
    hash_b64 = base64.b64encode(hash_bytes).decode('utf-8')
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    # Format: iterations$salt$hash
    hashed = f"100000${salt_b64}${hash_b64}"
    logger.info(f"Generated hash: {hashed}")
    return hashed, salt_b64

def verify_password(password: str, hash_str: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        password: The password to verify
        hash_str: The stored hash string in format "iterations$salt$hash"
    
    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        logger.info(f"Verifying password against hash: {hash_str}")
        
        # Vérifier que le hash a le bon format
        if not hash_str or hash_str.count('$') != 2:
            logger.error(f"Invalid hash format (wrong number of $ separators): {hash_str}")
            return False
            
        try:
            iterations_str, salt_b64, hash_b64 = hash_str.split('$')
            iterations = int(iterations_str)
            
            # Vérifier que les paramètres sont valides
            if iterations != 100000:
                logger.error(f"Invalid iterations count: {iterations}")
                return False
                
            # Vérifier que le sel et le hash sont en base64 valide
            if not (salt_b64 and hash_b64):
                logger.error("Empty salt or hash")
                return False
                
            # Vérifier que le sel a la bonne taille une fois décodé (16 bytes)
            salt = base64.b64decode(salt_b64)
            if len(salt) != 16:
                logger.error(f"Invalid salt length: {len(salt)}")
                return False
                
            stored_hash = base64.b64decode(hash_b64)
            # Le hash SHA256 fait toujours 32 bytes
            if len(stored_hash) != 32:
                logger.error(f"Invalid hash length: {len(stored_hash)}")
                return False
                
        except ValueError as e:
            logger.error(f"Error parsing hash format: {e}")
            return False
        except Exception as e:
            logger.error(f"Error decoding base64: {e}")
            return False
            
        # Calculate hash of the provided password
        hash_bytes = pbkdf2_hmac('sha256', password.encode(), salt, iterations)
        result = hash_bytes == stored_hash
        logger.info(f"Password verification result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error during password verification: {e}")
        return False
