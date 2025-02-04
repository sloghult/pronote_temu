from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import session, redirect, url_for
import mysql.connector
from ..db import get_db  # Importer la fonction get_db
from ..auth.routes import login_required  # Corriger l'importation du décorateur login_required
from .forms import JustificationForm

eleve_bp = Blueprint('eleve', __name__)

@eleve_bp.route('/')
def eleve_home():
    return render_template("eleve/home.html")

# Route pour afficher l'emploi du temps élève
@eleve_bp.route("/edt")
@login_required
def emploi_du_temps_page_eleve():
    # Données factices pour l'emploi du temps
    emploi_du_temps_eleve = [
        {"jour": "Lundi", "horaire": "8h-10h", "matiere": "Mathématiques", "professeur": "M. Martin", "salle": "Salle 101"},
        {"jour": "Lundi", "horaire": "10h-12h", "matiere": "Français", "professeur": "Mme Dubois", "salle": "Salle 102"},
        {"jour": "Mardi", "horaire": "8h-10h", "matiere": "Histoire-Géo", "professeur": "M. Bernard", "salle": "Salle 103"},
        {"jour": "Mardi", "horaire": "14h-16h", "matiere": "Anglais", "professeur": "Mme Smith", "salle": "Salle 104"},
        {"jour": "Mercredi", "horaire": "8h-10h", "matiere": "SVT", "professeur": "M. Petit", "salle": "Salle 105"},
        {"jour": "Jeudi", "horaire": "10h-12h", "matiere": "Physique-Chimie", "professeur": "Mme Robert", "salle": "Salle 106"},
        {"jour": "Jeudi", "horaire": "14h-16h", "matiere": "Technologie", "professeur": "M. Durand", "salle": "Salle 107"},
        {"jour": "Vendredi", "horaire": "16h-18h", "matiere": "Sport", "professeur": "M. Richard", "salle": "Gymnase"}
    ]
    
    return render_template("eleve/edt.html", emploi=emploi_du_temps_eleve)

@eleve_bp.route("/notes")
def notes_eleve():
    if "user_id" not in session:  # Vérifie si l'utilisateur est connecté
        return "Accès interdit", 403

    user_id = session["user_id"]  # Récupération de l'ID utilisateur depuis la session

    # Utiliser get_db() pour avoir une connexion fraîche
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Récupération de l'ID de l'élève
    query_id_eleve = "SELECT e.id as eleve_id FROM users u JOIN eleves e ON u.eleve_id = e.id WHERE u.id = %s"
    cursor.execute(query_id_eleve, (session['user_id'],))
    result = cursor.fetchone()

    if not result:
        flash("Erreur : Impossible de trouver l'élève associé à cet utilisateur.", "danger")
        return redirect(url_for('auth.login'))

    id_eleve = result["eleve_id"]  # Extraction de l'ID de l'élève

    try:
        # Récupérer les notes avec coefficients et commentaires
        query_notes = """
        SELECT m.nom_matiere, n.note, n.coef, n.commentaire,
               CASE 
                   WHEN n.commentaire IS NOT NULL AND n.commentaire != '' 
                   THEN n.commentaire 
                   ELSE 'Devoir'
               END as nom_devoir
        FROM notes n
        JOIN matieres m ON n.matiere_id = m.id
        WHERE n.eleve_id = %s
        ORDER BY m.nom_matiere;
        """
        cursor.execute(query_notes, (id_eleve,))
        all_notes = cursor.fetchall()

        # Organiser les notes par matière
        notes_by_matiere = {}
        for note in all_notes:
            matiere = note['nom_matiere']
            if matiere not in notes_by_matiere:
                notes_by_matiere[matiere] = []
            notes_by_matiere[matiere].append(note)

        # Calculer la moyenne par matière (déjà correct)
        query_moyennes = """
        SELECT m.nom_matiere, 
        SUM(n.note * n.coef) / SUM(n.coef) AS moyenne
        FROM notes n
        JOIN matieres m ON n.matiere_id = m.id
        WHERE n.eleve_id = %s
        GROUP BY m.nom_matiere;
        """
        cursor.execute(query_moyennes, (id_eleve,))
        moyennes = cursor.fetchall()

        # Calculer la moyenne globale sans coefficient (nouvelle requête)
        query_moyenne_globale = """
        SELECT AVG(moyenne) AS moyenne_globale
        FROM (
        SELECT SUM(n.note * n.coef) / SUM(n.coef) AS moyenne
        FROM notes n
        JOIN matieres m ON n.matiere_id = m.id
        WHERE n.eleve_id = %s
        GROUP BY m.nom_matiere
        ) AS sous_requete;
        """
        cursor.execute(query_moyenne_globale, (id_eleve,))
        moyenne_globale_result = cursor.fetchone()

        #   Vérifier si la moyenne globale est None (si l'élève n'a pas de notes)
        moyenne_globale = moyenne_globale_result["moyenne_globale"] if moyenne_globale_result and moyenne_globale_result["moyenne_globale"] is not None else 0

        return render_template("eleve/notes.html", notes=notes_by_matiere, moyennes=moyennes, moyenne_globale=moyenne_globale)

    except mysql.connector.Error as err:
        print(f"Erreur MySQL: {err}")
        return "Erreur lors de la récupération des notes", 500

    finally:
        cursor.close()

@eleve_bp.route("/absences")
@login_required
def absences():
    cursor = get_db().cursor(dictionary=True)
    
    # Récupérer l'ID de l'élève à partir de l'utilisateur connecté
    cursor.execute("SELECT e.id as eleve_id FROM users u JOIN eleves e ON u.eleve_id = e.id WHERE u.id = %s", (session['user_id'],))
    user = cursor.fetchone()

    if not user or not user['eleve_id']:
        flash("Erreur : Impossible de trouver l'élève associé à cet utilisateur.", "danger")
        return redirect(url_for('auth.login'))

    # Récupérer les absences de l'élève
    cursor.execute("""
        SELECT n.*, m.nom as matiere_nom, d.titre as devoir_titre,
               d.date as devoir_date, ROUND(AVG(n2.note), 2) as moyenne_classe
        FROM notes n
        JOIN devoirs d ON n.devoir_id = d.id
        JOIN matieres m ON d.matiere_id = m.id
        LEFT JOIN notes n2 ON n2.devoir_id = d.id
        WHERE n.eleve_id = %s
        GROUP BY n.id
        ORDER BY d.date DESC, m.nom
    """, (user['eleve_id'],))
    
    absences = cursor.fetchall()
    cursor.close()
    
    # Calculer les statistiques
    total_absences = len(absences)
    absences_justifiees = sum(1 for a in absences if a['justifie'])
    absences_non_justifiees = total_absences - absences_justifiees
    
    # Créer le formulaire de justification
    form = JustificationForm()
    
    # Ajouter temporairement le champ manquant
    for absence in absences:
        absence['statut_autorisation'] = 'non_autorisee'
    
    return render_template('eleve/absences.html', 
                         absences=absences,
                         total_absences=total_absences,
                         absences_justifiees=absences_justifiees,
                         absences_non_justifiees=absences_non_justifiees,
                         form=form)

@eleve_bp.route("/soumettre_justification/<int:absence_id>", methods=['POST'])
@login_required
def soumettre_justification(absence_id):
    cursor = get_db().cursor(dictionary=True)
    
    # Vérifier que l'absence appartient bien à l'élève connecté
    cursor.execute("""
        SELECT a.id, a.eleve_id 
        FROM absences a 
        JOIN users u ON u.eleve_id = a.eleve_id 
        WHERE a.id = %s AND u.id = %s
    """, (absence_id, session['user_id']))
    
    absence = cursor.fetchone()
    if not absence:
        cursor.close()
        flash("Cette absence n'existe pas ou ne vous appartient pas.", "danger")
        return redirect(url_for('eleve.absences'))
    
    form = JustificationForm()
    if form.validate_on_submit():
        # Mettre à jour l'absence avec la justification
        cursor.execute("""
            UPDATE absences 
            SET justification = %s, 
                justification_status = 'en_attente'
            WHERE id = %s
        """, (form.justification.data, absence_id))
        
        get_db().commit()
        cursor.close()
        
        flash("Votre justification a été soumise et est en attente de validation.", "success")
    else:
        cursor.close()
        flash("Erreur dans le formulaire. Veuillez réessayer.", "danger")
    
    return redirect(url_for('eleve.absences'))