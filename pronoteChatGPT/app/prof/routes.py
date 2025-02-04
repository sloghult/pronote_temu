from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.db import get_db
from app.auth.routes import login_required
from app.prof.forms import NoteForm, AppelForm  # Import du formulaire
from functools import wraps
import json

prof_bp = Blueprint('prof', __name__)

def prof_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not session.get('is_prof'):
            flash("Accès réservé aux professeurs", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@prof_bp.route("/")
@login_required
def home_page_prof():
    return render_template("prof/home.html")

@prof_bp.route("/notes", methods=["GET", "POST"])
@login_required
def notes_prof():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Récupérer les informations du professeur
    cursor.execute("""
        SELECT p.*,
               m1.nom_matiere as matiere1_nom,
               m2.nom_matiere as matiere2_nom,
               m3.nom_matiere as matiere3_nom,
               c1.classe as classe1_nom,
               c2.classe as classe2_nom,
               c3.classe as classe3_nom
        FROM prof p
        LEFT JOIN matieres m1 ON p.matiere1 = m1.id
        LEFT JOIN matieres m2 ON p.matiere2 = m2.id
        LEFT JOIN matieres m3 ON p.matiere3 = m3.id
        LEFT JOIN classes c1 ON p.classe1 = c1.id
        LEFT JOIN classes c2 ON p.classe2 = c2.id
        LEFT JOIN classes c3 ON p.classe3 = c3.id
        WHERE p.user_id = %s
    """, (session["user_id"],))
    prof_data = cursor.fetchone()
    
    if not prof_data:
        flash("Accès refusé", "danger")
        return redirect(url_for("auth.login"))

    # Récupérer les matières du professeur
    matieres = []
    for i in range(1, 4):
        matiere_id = prof_data[f"matiere{i}"]
        matiere_nom = prof_data[f"matiere{i}_nom"]
        if matiere_id:
            matieres.append({"id": matiere_id, "nom_matiere": matiere_nom})

    # Récupérer les classes du professeur
    classes = []
    for i in range(1, 4):
        classe_id = prof_data[f"classe{i}"]
        classe_nom = prof_data[f"classe{i}_nom"]
        if classe_id:
            classes.append({"id": classe_id, "classe": classe_nom})

    # Récupérer les élèves des classes du professeur
    eleves = []
    if classes:
        classes_ids = [classe["id"] for classe in classes]
        classes_placeholders = ", ".join(["%s"] * len(classes_ids))
        cursor.execute(f"""
            SELECT e.id, e.nom, e.prenom, c.classe
            FROM eleves e
            JOIN classes c ON e.classe_id = c.id
            WHERE e.classe_id IN ({classes_placeholders})
            ORDER BY c.classe, e.nom, e.prenom
        """, classes_ids)
        eleves = cursor.fetchall()
    
    if request.method == "POST":
        eleve_id = request.form.get("eleve")
        matiere_id = request.form.get("matiere")
        note = request.form.get("note")
        coef = request.form.get("coef")
        commentaire = request.form.get("commentaire")
        
        if not all([eleve_id, matiere_id, note, coef]):
            flash("Tous les champs obligatoires doivent être remplis", "danger")
            return redirect(url_for("prof.notes_prof"))
        
        try:
            # Vérifier que l'élève est dans une des classes du professeur
            cursor.execute("""
                SELECT e.id 
                FROM eleves e
                WHERE e.id = %s AND e.classe_id IN (%s, %s, %s)
            """, (eleve_id, prof_data["classe1"], prof_data["classe2"], prof_data["classe3"]))
            
            if not cursor.fetchone():
                flash("L'élève sélectionné n'est pas dans une de vos classes", "danger")
                return redirect(url_for("prof.notes_prof"))

            # Ajouter la note
            cursor.execute(
                "INSERT INTO notes (eleve_id, matiere_id, note, coef, commentaire) VALUES (%s, %s, %s, %s, %s)",
                (eleve_id, matiere_id, note, coef, commentaire)
            )
            db.commit()
            flash("Note ajoutée avec succès", "success")
        except Exception as e:
            db.rollback()
            flash(f"Erreur lors de l'ajout de la note : {str(e)}", "danger")
        return redirect(url_for("prof.notes_prof"))
    
    # Récupérer les notes des élèves du professeur
    notes = []
    if classes and matieres:
        classes_ids = [classe["id"] for classe in classes]
        matieres_ids = [matiere["id"] for matiere in matieres]
        classes_placeholders = ", ".join(["%s"] * len(classes_ids))
        matieres_placeholders = ", ".join(["%s"] * len(matieres_ids))
        
        cursor.execute(f"""
            SELECT n.id as note_id, n.note, n.coef, n.commentaire,
                   e.nom, e.prenom, c.classe,
                   m.nom_matiere
            FROM notes n
            JOIN eleves e ON n.eleve_id = e.id
            JOIN classes c ON e.classe_id = c.id
            JOIN matieres m ON n.matiere_id = m.id
            WHERE e.classe_id IN ({classes_placeholders})
            AND n.matiere_id IN ({matieres_placeholders})
            ORDER BY c.classe, e.nom, e.prenom, m.nom_matiere
        """, classes_ids + matieres_ids)
        notes = cursor.fetchall()
    
    return render_template("prof/notes.html", 
                         notes=notes, 
                         classes=classes,
                         matieres=matieres, 
                         eleves=eleves,
                         prof_data=prof_data,
                         is_admin=False)

@prof_bp.route("/get_eleves")
@login_required
def get_eleves():
    try:
        classe_id = request.args.get('classe_id')
        if not classe_id:
            return jsonify([])
            
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Vérifier que le professeur a accès à cette classe
        cursor.execute("""
            SELECT classe1, classe2, classe3
            FROM prof
            WHERE user_id = %s
        """, (session['user_id'],))
        prof_classes = cursor.fetchone()
        
        if not prof_classes or int(classe_id) not in [
            prof_classes['classe1'],
            prof_classes['classe2'],
            prof_classes['classe3']
        ]:
            return jsonify({"error": "Accès non autorisé à cette classe"}), 403
            
        cursor.execute("""
            SELECT id, nom, prenom
            FROM eleves
            WHERE classe_id = %s
            ORDER BY nom, prenom
        """, (classe_id,))
        
        eleves = cursor.fetchall()
        return jsonify(eleves)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@prof_bp.route("/get_eleves_by_classe/<string:classe>")
@login_required
def get_eleves_by_classe(classe):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Récupérer l'ID de la classe
        cursor.execute("SELECT id FROM classes WHERE classe = %s", (classe,))
        classe_data = cursor.fetchone()
        
        if not classe_data:
            return jsonify({"error": "Classe non trouvée"}), 404
            
        # Récupérer les élèves de la classe
        cursor.execute("""
            SELECT e.id, e.nom, e.prenom
            FROM eleves e
            WHERE e.classe_id = %s
            ORDER BY e.nom, e.prenom
        """, (classe_data['id'],))
        
        eleves = cursor.fetchall()
        return jsonify(eleves)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@prof_bp.route("/notes/delete/<int:note_id>", methods=["POST"])
@login_required
def delete_note(note_id):
    if not session.get('user_id'):
        flash("Veuillez vous connecter", "danger")
        return redirect(url_for("auth.login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Vérifier que la note appartient à une classe et une matière du professeur
        cursor.execute("""
            SELECT p.classe1, p.classe2, p.classe3,
                   p.matiere1, p.matiere2, p.matiere3
            FROM prof p
            WHERE p.user_id = %s
        """, (session['user_id'],))
        prof_data = cursor.fetchone()

        if not prof_data:
            flash("Professeur non trouvé", "danger")
            return redirect(url_for("prof.notes_prof"))

        # Construire la liste des classes et matières autorisées
        classes_autorisees = [c for c in [prof_data['classe1'], prof_data['classe2'], prof_data['classe3']] if c]
        matieres_autorisees = [m for m in [prof_data['matiere1'], prof_data['matiere2'], prof_data['matiere3']] if m]

        # Vérifier que la note appartient à une classe et une matière autorisée
        cursor.execute("""
            SELECT 1
            FROM notes n
            JOIN eleves e ON n.eleve_id = e.id
            WHERE n.id = %s
            AND e.classe_id IN (%s)
            AND n.matiere_id IN (%s)
        """, (
            note_id,
            ','.join(str(c) for c in classes_autorisees),
            ','.join(str(m) for m in matieres_autorisees)
        ))

        if not cursor.fetchone():
            flash("Vous n'êtes pas autorisé à supprimer cette note", "danger")
            return redirect(url_for("prof.notes_prof"))

        cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        db.commit()
        flash("Note supprimée avec succès", "success")
    except Exception as e:
        db.rollback()
        flash(f"Erreur lors de la suppression de la note : {str(e)}", "danger")
    finally:
        cursor.close()
    return redirect(url_for("prof.notes_prof"))

@prof_bp.route("/delete_all_notes", methods=["POST"])
@login_required
@prof_required
def delete_all_notes():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Supprimer toutes les notes
        cursor.execute("DELETE FROM notes")
        db.commit()
        
        flash("Toutes les notes ont été supprimées avec succès.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Une erreur est survenue lors de la suppression des notes : {str(e)}", "danger")
    
    return redirect(url_for('prof.notes_prof'))

@prof_bp.route("/appel", methods=['GET', 'POST'])
@login_required
def appel():
    form = AppelForm()
    
    # Récupérer les classes du professeur connecté
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT c.id, c.classe 
        FROM classes c 
        JOIN prof p ON (c.id = p.classe1 OR c.id = p.classe2 OR c.id = p.classe3)
        WHERE p.user_id = %s
    """, (session["user_id"],))
    classes = cursor.fetchall()
    cursor.close()
    
    form.classe_id.choices = [(c['id'], c['classe']) for c in classes]
    
    if form.validate_on_submit():
        return redirect(url_for('prof.faire_appel', 
                              classe_id=form.classe_id.data,
                              date=form.date.data.strftime('%Y-%m-%d'),
                              creneau=form.creneau.data))
    
    return render_template('prof/appel.html', form=form)

@prof_bp.route("/faire_appel", methods=['GET', 'POST'])
@prof_required
def faire_appel():
    cursor = get_db().cursor(dictionary=True)
    
    # Récupérer l'ID du professeur
    prof_id = session.get('user_id')
    
    if request.method == 'POST':
        classe_id = request.form.get('classe_id')
        date = request.form.get('date')
        creneau = request.form.get('creneau')
        eleves_absents = request.form.getlist('absent[]')
        
        # Vérifier que le prof a accès à cette classe
        cursor.execute("""
            SELECT 1 
            FROM prof 
            WHERE id = %s 
            AND (classe1 = %s OR classe2 = %s OR classe3 = %s)
        """, (prof_id, classe_id, classe_id, classe_id))
        
        if cursor.fetchone():
            # Enregistrer les absences
            for eleve_id in eleves_absents:
                cursor.execute("""
                    INSERT INTO absences (eleve_id, date, creneau)
                    VALUES (%s, %s, %s)
                """, (eleve_id, date, creneau))
            
            get_db().commit()
            flash(f"L'appel a été enregistré pour le {date}, {creneau}", "success")
        else:
            flash("Vous n'avez pas accès à cette classe", "danger")
        
        return redirect(url_for('prof.faire_appel'))
    
    # Récupérer les classes du professeur
    cursor.execute("""
        SELECT DISTINCT c.id, c.classe
        FROM classes c
        JOIN prof p ON c.id IN (p.classe1, p.classe2, p.classe3)
        WHERE p.id = %s
        ORDER BY c.classe
    """, (prof_id,))
    
    classes = cursor.fetchall()

    # Si on a les paramètres classe_id, date et creneau, on affiche la liste des élèves
    classe_id = request.args.get('classe_id')
    date = request.args.get('date')
    creneau = request.args.get('creneau')

    eleves = None
    if classe_id and date and creneau:
        # Vérifier que le prof a accès à cette classe
        cursor.execute("""
            SELECT 1 
            FROM prof 
            WHERE id = %s 
            AND (classe1 = %s OR classe2 = %s OR classe3 = %s)
        """, (prof_id, classe_id, classe_id, classe_id))
        
        if cursor.fetchone():
            # Récupérer la liste des élèves
            cursor.execute("""
                SELECT e.id, e.nom, e.prenom
                FROM eleves e
                WHERE e.classe_id = %s
                ORDER BY e.nom, e.prenom
            """, (classe_id,))
            
            eleves = cursor.fetchall()
        else:
            flash("Vous n'avez pas accès à cette classe", "danger")

    cursor.close()
    
    return render_template('prof/faire_appel.html', 
                         classes=classes,
                         eleves=eleves,
                         selected_classe_id=int(classe_id) if classe_id else None,
                         date=date,
                         creneau=creneau)

@prof_bp.route("/faire_appel/<int:classe_id>/<date>/<creneau>", methods=['GET', 'POST'])
@prof_required
def faire_appel_detail(classe_id, date, creneau):
    cursor = get_db().cursor(dictionary=True)
    
    # Vérifier que le prof a accès à cette classe
    prof_id = session.get('user_id')
    cursor.execute("""
        SELECT 1 
        FROM prof 
        WHERE id = %s 
        AND (classe1 = %s OR classe2 = %s OR classe3 = %s)
    """, (prof_id, classe_id, classe_id, classe_id))
    
    if not cursor.fetchone():
        flash("Vous n'avez pas accès à cette classe", "danger")
        return redirect(url_for('prof.faire_appel'))
    
    # Récupérer la liste des élèves
    cursor.execute("""
        SELECT e.id, e.nom, e.prenom
        FROM eleves e
        WHERE e.classe_id = %s
        ORDER BY e.nom, e.prenom
    """, (classe_id,))
    
    eleves = cursor.fetchall()
    cursor.close()
    
    return render_template('prof/faire_appel_detail.html', 
                         eleves=eleves, 
                         date=date, 
                         creneau=creneau)

@prof_bp.route("/edt")
@login_required
def emploi_du_temps_page_prof():
    # Données factices pour l'emploi du temps
    emploi_du_temps_prof = [
        {"jour": "Lundi", "horaire": "8h-10h", "matiere": "Mathématiques", "classe": "6ème A", "salle": "Salle 101"},
        {"jour": "Lundi", "horaire": "10h-12h", "matiere": "Mathématiques", "classe": "5ème B", "salle": "Salle 102"},
        {"jour": "Mardi", "horaire": "14h-16h", "matiere": "Mathématiques", "classe": "4ème A", "salle": "Salle 103"},
        {"jour": "Mardi", "horaire": "16h-18h", "matiere": "Mathématiques", "classe": "3ème B", "salle": "Salle 104"},
        {"jour": "Mercredi", "horaire": "8h-10h", "matiere": "Mathématiques", "classe": "6ème B", "salle": "Salle 101"},
        {"jour": "Jeudi", "horaire": "10h-12h", "matiere": "Mathématiques", "classe": "5ème A", "salle": "Salle 102"},
        {"jour": "Jeudi", "horaire": "14h-16h", "matiere": "Mathématiques", "classe": "4ème B", "salle": "Salle 103"},
        {"jour": "Vendredi", "horaire": "16h-18h", "matiere": "Mathématiques", "classe": "3ème A", "salle": "Salle 104"}
    ]
    
    return render_template("prof/edt.html", emploi=emploi_du_temps_prof)

@prof_bp.route("/saisir_notes_devoir", methods=["GET"])
@login_required
def saisir_notes_devoir():
    classe_id = request.args.get('classe_id')
    matiere_id = request.args.get('matiere_id')
    nom_devoir = request.args.get('nom_devoir')
    coefficient = request.args.get('coefficient')
    
    if not all([classe_id, matiere_id, nom_devoir, coefficient]):
        flash("Tous les champs sont requis", "danger")
        return redirect(url_for('prof.notes_prof'))
        
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Récupérer les élèves de la classe
    cursor.execute("""
        SELECT e.id, e.nom, e.prenom
        FROM eleves e
        WHERE e.classe_id = %s
        ORDER BY e.nom, e.prenom
    """, (classe_id,))
    eleves = cursor.fetchall()
    
    # Récupérer les infos de la classe et de la matière
    cursor.execute("SELECT classe FROM classes WHERE id = %s", (classe_id,))
    classe = cursor.fetchone()
    
    cursor.execute("SELECT nom_matiere FROM matieres WHERE id = %s", (matiere_id,))
    matiere = cursor.fetchone()
    
    return render_template('prof/saisie_notes.html',
                         eleves=eleves,
                         classe=classe,
                         matiere=matiere,
                         classe_id=classe_id,
                         matiere_id=matiere_id,
                         nom_devoir=nom_devoir,
                         coefficient=coefficient)

@prof_bp.route("/ajouter_devoir", methods=["POST"])
@login_required
def ajouter_devoir():
    classe_id = request.form.get('classe_id')
    matiere_id = request.form.get('matiere_id')
    nom_devoir = request.form.get('nom_devoir')
    coefficient = request.form.get('coefficient')
    notes = request.form.getlist('notes[]')
    eleve_ids = request.form.getlist('eleve_ids[]')
    
    if not all([classe_id, matiere_id, nom_devoir, coefficient, notes, eleve_ids]):
        flash("Tous les champs sont requis", "danger")
        return redirect(url_for('prof.notes_prof'))
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Ajouter les notes pour chaque élève
        for eleve_id, note in zip(eleve_ids, notes):
            if note.strip():  # Ne pas ajouter si la note est vide
                cursor.execute(
                    "INSERT INTO notes (eleve_id, matiere_id, note, coef, commentaire) VALUES (%s, %s, %s, %s, %s)",
                    (eleve_id, matiere_id, float(note), coefficient, nom_devoir)
                )
        
        db.commit()
        flash("Notes ajoutées avec succès", "success")
    except Exception as e:
        db.rollback()
        flash(f"Erreur lors de l'ajout des notes : {str(e)}", "danger")
    
    return redirect(url_for('prof.notes_prof'))
