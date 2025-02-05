from flask import Blueprint

# 📌 Définir le Blueprint AVANT d'importer les routes
auth_bp = Blueprint('auth', __name__)

# 📌 Importer les routes APRÈS avoir défini `auth_bp`
from app.auth import routes
