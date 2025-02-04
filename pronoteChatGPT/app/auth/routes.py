from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from app.db import get_db
from app.utils.password import verify_password
import logging

auth_bp = Blueprint("auth", __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter pour accéder à cette page", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    return session.get("is_admin", False)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        logger.info("Tentative de connexion")
        
        if not username or not password:
            flash("Veuillez remplir tous les champs", "danger")
            return render_template("login.html")
        
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            
            # Vérifier si c'est un admin
            cursor.execute("""
                SELECT id, username, password, role 
                FROM users 
                WHERE username = %s AND role = 'admin'
            """, (username,))
            user = cursor.fetchone()
            
            if user:
                logger.info("Vérification des identifiants admin")
                stored_password = user.get('password', '')
                logger.info(f"Format du mot de passe stocké: {stored_password}")
                
                if verify_password(password, stored_password):
                    logger.info("Connexion réussie avec PBKDF2")
                    session.clear()
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    session["role"] = user["role"]
                    session["is_admin"] = True
                    flash(f"Bienvenue {user['username']}", "success")
                    return redirect(url_for("admin.admin_home"))
                else:
                    logger.error("Échec de la vérification du mot de passe")
            
            # Si ce n'est pas un admin, vérifier si c'est un professeur
            cursor.execute("""
                SELECT u.id as user_id, u.username, u.password, p.id as prof_id
                FROM users u
                JOIN prof p ON u.id = p.user_id
                WHERE u.username = %s AND u.role = 'prof'
            """, (username,))
            prof = cursor.fetchone()
            
            if prof:
                logger.info("Vérification des identifiants prof")
                stored_password = prof.get('password', '')
                
                if verify_password(password, stored_password):
                    logger.info("Connexion prof réussie")
                    session.clear()
                    session["user_id"] = prof["user_id"]
                    session["username"] = prof["username"]
                    session["role"] = prof["role"]
                    session["is_admin"] = False
                    session["is_prof"] = True
                    session["prof_id"] = prof["prof_id"]
                    logger.info("Session après connexion prof")
                    cursor.close()
                    return redirect(url_for("prof.home_page_prof"))
            
            # Si ce n'est pas un prof, vérifier si c'est un parent
            cursor.execute("""
                SELECT u.id as user_id, u.username, u.password, p.parent_id
                FROM users u
                JOIN parents p ON u.id = p.user_id
                WHERE u.username = %s AND u.role = 'parent'
            """, (username,))
            parent = cursor.fetchone()
            
            if parent:
                logger.info("Vérification des identifiants parent")
                stored_password = parent.get('password', '')
                
                if verify_password(password, stored_password):
                    logger.info("Connexion parent réussie")
                    session.clear()
                    session["user_id"] = parent["user_id"]
                    session["username"] = parent["username"]
                    session["role"] = parent["role"]
                    session["is_admin"] = False
                    session["is_parent"] = True
                    session["parent_id"] = parent["parent_id"]
                    logger.info("Session après connexion parent")
                    cursor.close()
                    return redirect(url_for("parent.parent_home"))

            # Si ce n'est pas un parent, vérifier si c'est un élève
            cursor.execute("""
                SELECT u.id as user_id, u.username, u.password, e.id as eleve_id
                FROM users u
                JOIN eleves e ON u.id = e.user_id
                WHERE u.username = %s AND u.role = 'eleve'
            """, (username,))
            eleve = cursor.fetchone()
            
            if eleve:
                logger.info("Vérification des identifiants élève")
                stored_password = eleve.get('password', '')
                
                if verify_password(password, stored_password):
                    logger.info("Connexion élève réussie")
                    session.clear()
                    session["user_id"] = eleve["user_id"]
                    session["username"] = eleve["username"]
                    session["role"] = eleve["role"]
                    session["is_admin"] = False
                    session["eleve_id"] = eleve["eleve_id"]
                    logger.info("Session après connexion élève")
                    cursor.close()
                    return redirect(url_for("eleve.eleve_home"))
            
            flash("Nom d'utilisateur ou mot de passe incorrect", "danger")
            cursor.close()
            logger.warning("Échec de la connexion")
            
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {str(e)}")
            flash("Une erreur est survenue lors de la connexion", "danger")
            return render_template("login.html")
    
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Vous avez été déconnecté", "success")
    return redirect(url_for("auth.login"))

@auth_bp.route("/hash_password/<password>")
def hash_password(password):
    hashed = generate_password_hash(password)
    return {"hash": hashed}
