from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db
from app.auth.routes import login_required
from functools import wraps

parent_bp = Blueprint('parent', __name__)

def parent_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_parent'):
            flash("Accès refusé. Vous devez être un parent.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@parent_bp.route("/")
@login_required
@parent_required
def parent_home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Récupérer les informations du parent
    cursor.execute("""
        SELECT p.* FROM parents p
        WHERE p.user_id = %s
    """, (session['user_id'],))
    parent = cursor.fetchone()
    
    # Récupérer la liste des enfants
    cursor.execute("""
        SELECT e.*, pe.relation, c.classe as classe_nom
        FROM eleves e
        JOIN parent_eleve pe ON e.id = pe.eleve_id
        LEFT JOIN classes c ON e.classe_id = c.id
        WHERE pe.parent_id = %s
    """, (parent['parent_id'],))
    enfants = cursor.fetchall()
    
    cursor.close()
    return render_template('parent/home.html', parent=parent, enfants=enfants)

@parent_bp.route("/enfant/<int:eleve_id>/notes")
@login_required
@parent_required
def voir_notes(eleve_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Vérifier que le parent a accès à cet élève
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM parent_eleve
        WHERE parent_id = (SELECT parent_id FROM parents WHERE user_id = %s)
        AND eleve_id = %s
    """, (session['user_id'], eleve_id))
    
    if cursor.fetchone()['count'] == 0:
        flash("Vous n'avez pas accès aux notes de cet élève.", "danger")
        return redirect(url_for('parent.parent_home'))
    
    # Récupérer les notes de l'élève
    cursor.execute("""
        SELECT n.*, m.nom_matiere as matiere_nom, 
               COALESCE(d.titre, 'Note sans devoir') as devoir_titre,
               COALESCE(d.date, CURRENT_DATE) as devoir_date, 
               ROUND(AVG(n2.note), 2) as moyenne_classe
        FROM notes n
        JOIN matieres m ON n.matiere_id = m.id
        LEFT JOIN devoirs d ON n.devoir_id = d.id
        LEFT JOIN notes n2 ON n2.devoir_id = d.id
        WHERE n.eleve_id = %s
        GROUP BY n.id
        ORDER BY COALESCE(d.date, CURRENT_DATE) DESC, m.nom_matiere
    """, (eleve_id,))
    notes = cursor.fetchall()
    
    cursor.close()
    return render_template('parent/notes.html', notes=notes, eleve_id=eleve_id)

@parent_bp.route("/enfant/<int:eleve_id>/absences")
@login_required
@parent_required
def voir_absences(eleve_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Vérifier que le parent a accès à cet élève
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM parent_eleve
        WHERE parent_id = (SELECT parent_id FROM parents WHERE user_id = %s)
        AND eleve_id = %s
    """, (session['user_id'], eleve_id))
    
    if cursor.fetchone()['count'] == 0:
        flash("Vous n'avez pas accès aux absences de cet élève.", "danger")
        return redirect(url_for('parent.parent_home'))
    
    # Récupérer les absences de l'élève
    cursor.execute("""
        SELECT a.*, 
               CASE 
                   WHEN a.justification IS NULL AND a.justifie = 0 THEN 'À justifier'
                   WHEN a.justification_status = 'en_attente' THEN 'En attente'
                   WHEN a.justification_status = 'acceptee' THEN 'Acceptée'
                   WHEN a.justification_status = 'refusee' THEN 'Refusée'
                   ELSE 'Inconnue'
               END as status_text
        FROM absences a
        WHERE a.eleve_id = %s
        ORDER BY a.date DESC
    """, (eleve_id,))
    absences = cursor.fetchall()
    
    cursor.close()
    return render_template('parent/absences.html', absences=absences, eleve_id=eleve_id)
