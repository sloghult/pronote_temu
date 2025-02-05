import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.crypto import generate_key, encrypt_password
import base64

def main():
    # Demander le mot de passe de la base de données
    db_password = input("Entrez le mot de passe de la base de données: ")
    
    # Générer une clé de cryptage
    key, salt = generate_key(os.urandom(32).hex())
    
    # Crypter le mot de passe
    encrypted_password = encrypt_password(db_password, key)
    
    print("\nAjoutez ces lignes à votre fichier .env :")
    print("----------------------------------------")
    print(f"CRYPTO_KEY={key.decode()}")
    print(f"ENCRYPTED_DB_PASS={encrypted_password}")
    print("DB_USER=root")  # ou votre utilisateur MySQL
    print("DB_HOST=localhost")  # ou votre hôte MySQL
    print("DB_NAME=pronote1")  # ou votre nom de base de données
    print("----------------------------------------")
    
    # Sauvegarder dans un fichier temporaire
    with open("db_credentials.tmp", "w") as f:
        f.write(f"CRYPTO_KEY={key.decode()}\n")
        f.write(f"ENCRYPTED_DB_PASS={encrypted_password}\n")
        f.write("DB_USER=root\n")
        f.write("DB_HOST=localhost\n")
        f.write("DB_NAME=pronote1\n")
    
    print("\nLes informations ont aussi été sauvegardées dans 'db_credentials.tmp'")
    print("ATTENTION: Supprimez ce fichier une fois que vous avez mis à jour votre .env")

if __name__ == "__main__":
    main()
