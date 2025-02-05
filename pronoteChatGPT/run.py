from app import create_app
from flask import url_for

# Créer l'application Flask
app = create_app()

# 📌 Afficher toutes les routes disponibles
with app.app_context():
    print("🚀 Routes disponibles :")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: http://127.0.0.1:5000{rule}")

# 📌 Lancer l'application Flask
if __name__ == '__main__':
    app.run(debug=True)
