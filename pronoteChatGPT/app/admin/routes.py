from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.db import get_db
from functools import wraps
from app.auth.routes import login_required
from app.utils.password import hash_password

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Accès refusé. Vous devez être administrateur.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/")
@login_required
@admin_required
def admin_home():
    return render_template('admin/admin_home.html')

@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    cursor = get_db().cursor(dictionary=True)
    
    # Récupérer les classes et matières pour les formulaires
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()
    cursor.execute("SELECT * FROM matieres")
    matieres = cursor.fetchall()

    # Récupérer les paramètres de filtrage
    filter_type = request.args.get('filter_type', 'all')  # all, prof, class
    class_id = request.args.get('class_id')

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")

        if not all([username, email, password, confirm_password, role]):
            flash("Tous les champs sont requis", "danger")
            return redirect(url_for("admin.users"))

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas", "danger")
            return redirect(url_for("admin.users"))

        # Vérifier si le nom d'utilisateur existe déjà
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            flash("Ce nom d'utilisateur existe déjà", "danger")
            return redirect(url_for("admin.users"))

        # Vérifier si l'email existe déjà
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Cet email est déjà utilisé", "danger")
            return redirect(url_for("admin.users"))

        try:
            # Créer l'utilisateur avec PBKDF2
            hashed_password, salt_b64 = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password, salt, role) VALUES (%s, %s, %s, %s, %s)",
                (username, email, hashed_password, salt_b64, role),
            )
            user_id = cursor.lastrowid

            if role == "prof":
                nom_prof = request.form.get("nom_prof")
                prenom_prof = request.form.get("prenom_prof")
                matiere = request.form.get("matiere")
                matiere2 = request.form.get("matiere2")
                matiere3 = request.form.get("matiere3")
                classe1 = request.form.get("classe1")
                classe2 = request.form.get("classe2")
                classe3 = request.form.get("classe3")

                if not all([nom_prof, prenom_prof, matiere]):
                    get_db().rollback()
                    flash("Le nom, prénom et la matière principale du professeur sont requis", "danger")
                    return redirect(url_for("admin.users"))

                try:
                    cursor.execute(
                        "INSERT INTO prof (user_id, nom, prenom, matiere1, matiere2, matiere3, classe1, classe2, classe3) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_id, nom_prof, prenom_prof, matiere, matiere2, matiere3, classe1, classe2, classe3)
                    )
                except Exception as e:
                    get_db().rollback()
                    if "foreign key constraint" in str(e).lower():
                        flash("Erreur : Une ou plusieurs matières ou classes sélectionnées n'existent pas", "danger")
                    else:
                        flash(f"Erreur lors de l'ajout des informations du professeur : {str(e)}", "danger")
                    return redirect(url_for("admin.users"))

            elif role == "eleve":
                nom_eleve = request.form.get("nom_eleve")
                prenom_eleve = request.form.get("prenom_eleve")
                classe_eleve = request.form.get("classe_eleve")

                if not all([nom_eleve, prenom_eleve, classe_eleve]):
                    get_db().rollback()
                    flash("Le nom, prénom et la classe de l'élève sont requis", "danger")
                    return redirect(url_for("admin.users"))

                try:
                    cursor.execute(
                        "INSERT INTO eleves (nom, prenom, classe_id) VALUES (%s, %s, %s)",
                        (nom_eleve, prenom_eleve, classe_eleve)
                    )
                    eleve_id = cursor.lastrowid
                    cursor.execute(
                        "UPDATE users SET eleve_id = %s WHERE id = %s",
                        (eleve_id, user_id)
                    )
                except Exception as e:
                    get_db().rollback()
                    if "foreign key constraint" in str(e).lower():
                        flash("Erreur : La classe sélectionnée n'existe pas", "danger")
                    else:
                        flash(f"Erreur lors de l'ajout des informations de l'élève : {str(e)}", "danger")
                    return redirect(url_for("admin.users"))

            elif role == "parent":
                nom_parent = request.form.get("nom_parent")
                prenom_parent = request.form.get("prenom_parent")
                telephone = request.form.get("telephone")
                eleve_ids = request.form.getlist("eleve_ids")
                relation = request.form.get("relation")

                if not all([nom_parent, prenom_parent, eleve_ids, relation]):
                    get_db().rollback()
                    flash("Le nom, prénom, les élèves et la relation sont requis", "danger")
                    return redirect(url_for("admin.users"))

                try:
                    cursor.execute(
                        "INSERT INTO parents (user_id, nom, prenom, telephone) VALUES (%s, %s, %s, %s)",
                        (user_id, nom_parent, prenom_parent, telephone)
                    )
                    parent_id = cursor.lastrowid
                    for eleve_id in eleve_ids:
                        cursor.execute(
                            "INSERT INTO parent_eleve (parent_id, eleve_id, relation) VALUES (%s, %s, %s)",
                            (parent_id, eleve_id, relation)
                        )
                except Exception as e:
                    get_db().rollback()
                    flash(f"Erreur lors de l'ajout des informations du parent : {str(e)}", "danger")
                    return redirect(url_for("admin.users"))

            get_db().commit()
            if role == "prof":
                flash(f"Le professeur {nom_prof} {prenom_prof} a été ajouté avec succès", "success")
            elif role == "eleve":
                flash(f"L'élève {nom_eleve} {prenom_eleve} a été ajouté avec succès", "success")
            elif role == "parent":
                flash(f"Le parent {nom_parent} {prenom_parent} a été ajouté avec succès", "success")
            else:
                flash("L'administrateur a été ajouté avec succès", "success")

        except Exception as e:
            get_db().rollback()
            if "Duplicate entry" in str(e):
                if "username" in str(e):
                    flash("Ce nom d'utilisateur est déjà utilisé", "danger")
                elif "email" in str(e):
                    flash("Cet email est déjà utilisé", "danger")
                else:
                    flash("Une erreur est survenue lors de la création de l'utilisateur", "danger")
            else:
                flash(f"Erreur lors de la création de l'utilisateur : {str(e)}", "danger")
        finally:
            cursor.close()
        return redirect(url_for("admin.users"))

    # Base de la requête SQL
    query = """
    SELECT 
        users.id,
        users.username,
        users.email,
        users.role,
        COALESCE(
            MAX(eleves.nom),
            MAX(prof.nom),
            MAX(parents.nom)
        ) AS nom,
        COALESCE(
            MAX(eleves.prenom),
            MAX(prof.prenom),
            MAX(parents.prenom)
        ) AS prenom,
        CASE 
            WHEN users.role = 'eleve' THEN MAX(classes.classe)
            WHEN users.role = 'prof' THEN GROUP_CONCAT(DISTINCT
                NULLIF(CONCAT_WS(', ',
                    NULLIF(c1.classe, ''),
                    NULLIF(c2.classe, ''),
                    NULLIF(c3.classe, '')
                ), '')
            )
            WHEN users.role = 'parent' THEN GROUP_CONCAT(DISTINCT e2.nom SEPARATOR ', ')
            ELSE ''
        END AS classe
    FROM users
    LEFT JOIN eleves ON users.eleve_id = eleves.id
    LEFT JOIN prof ON users.id = prof.user_id
    LEFT JOIN parents ON users.id = parents.user_id
    LEFT JOIN parent_eleve ON parents.parent_id = parent_eleve.parent_id
    LEFT JOIN eleves e2 ON parent_eleve.eleve_id = e2.id
    LEFT JOIN classes ON eleves.classe_id = classes.id
    LEFT JOIN classes c1 ON prof.classe1 = c1.id
    LEFT JOIN classes c2 ON prof.classe2 = c2.id
    LEFT JOIN classes c3 ON prof.classe3 = c3.id
    """

    # Ajouter les conditions de filtrage
    if filter_type == 'prof':
        query += " WHERE users.role = 'prof'"
    elif filter_type == 'parent':
        query += " WHERE users.role = 'parent'"
    elif filter_type == 'class' and class_id:
        query += f" WHERE users.role = 'eleve' AND eleves.classe_id = {class_id}"

    query += " GROUP BY users.id, users.username, users.email, users.role ORDER BY users.id"
    
    cursor.execute(query)
    users = cursor.fetchall()
    cursor.close()

    return render_template("admin/users.html", 
                         users=users, 
                         classes=classes, 
                         matieres=matieres,
                         filter_type=filter_type,
                         class_id=class_id)

@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    cursor = get_db().cursor(dictionary=True)
    try:
        # Récupérer les informations de l'utilisateur
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("admin.users"))

        # Supprimer les données associées selon le rôle
        if user['role'] == 'prof':
            cursor.execute("DELETE FROM prof WHERE user_id = %s", (user_id,))
        elif user['role'] == 'eleve':
            # Supprimer d'abord les absences
            cursor.execute("DELETE FROM absences WHERE eleve_id = %s", (user['eleve_id'],))
            # Puis les notes
            cursor.execute("DELETE FROM notes WHERE eleve_id = %s", (user['eleve_id'],))
            # Enfin l'élève lui-même
            cursor.execute("DELETE FROM eleves WHERE id = %s", (user['eleve_id'],))
        elif user['role'] == 'parent':
            cursor.execute("DELETE FROM parent_eleve WHERE parent_id = (SELECT parent_id FROM parents WHERE user_id = %s)", (user_id,))
            cursor.execute("DELETE FROM parents WHERE user_id = %s", (user_id,))

        # Supprimer l'utilisateur
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        get_db().commit()
        flash("Utilisateur supprimé avec succès", "success")
    except Exception as e:
        get_db().rollback()
        flash(f"Erreur lors de la suppression de l'utilisateur: {str(e)}", "danger")
    finally:
        cursor.close()
    return redirect(url_for("admin.users"))

# Route pour afficher la page HTML des étudiants
@admin_bp.route('/students')
@login_required
@admin_required
def students_page():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM eleves")  
    eleves = cursor.fetchall()
    cursor.close()
    return render_template("admin/students.html", eleves=eleves)

@admin_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    cursor = get_db().cursor(dictionary=True)

    cursor.execute("SELECT id, classe FROM classes")
    classes = [(classe["id"], classe["classe"]) for classe in cursor.fetchall()]
    cursor.execute("SELECT id, nom_matiere FROM matieres")
    matieres = [(matiere["id"], matiere["nom_matiere"]) for matiere in cursor.fetchall()]
    cursor.close()

    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cursor = get_db().cursor()
        hashed_password, salt_b64 = hash_password(password)
        cursor.execute("INSERT INTO users (username, email, password, salt, role) VALUES (%s, %s, %s, %s, %s)",
                       (username, email, hashed_password, salt_b64, role))
        user_id = cursor.lastrowid

        if role == 'eleve':
            nom = request.form['nom']
            prenom = request.form['prenom']
            classe_id = request.form['classe_id']
            cursor.execute("INSERT INTO eleves (nom, prenom, classe_id) VALUES (%s, %s, %s)",
                           (nom, prenom, classe_id))
            eleve_id = cursor.lastrowid
            cursor.execute("UPDATE users SET eleve_id = %s WHERE id = %s", (eleve_id, user_id))
        elif role == 'prof':
            nomp = request.form['nomp']
            matiere1 = request.form['matiere1']
            matiere2 = request.form['matiere2']
            matiere3 = request.form['matiere3']
            classe1 = request.form['classe1']
            classe2 = request.form['classe2']
            classe3 = request.form['classe3']
            cursor.execute("INSERT INTO prof (user_id, nom, matiere1, matiere2, matiere3, classe1, classe2, classe3) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (user_id, nomp, matiere1, matiere2, matiere3, classe1, classe2, classe3))
        get_db().commit()
        cursor.close()
        return redirect(url_for('admin.add_user'))
    return render_template('admin/add_user.html', classes=classes, matieres=matieres)

@admin_bp.route('/delete_matiere/<int:matiere_id>', methods=['POST'])
@login_required
@admin_required
def delete_matiere(matiere_id):
    cursor = get_db().cursor()
    cursor.execute("DELETE FROM notes WHERE matiere_id = %s", (matiere_id,))
    cursor.execute("DELETE FROM matieres WHERE id = %s", (matiere_id,))
    get_db().commit()
    cursor.close()
    flash("Matière et notes associées supprimées avec succès.", "success")
    return redirect(url_for("admin.gestion_matieres"))

@admin_bp.route('/classes', methods=['GET', 'POST'])
@login_required
@admin_required
def classes():
    if request.method == 'POST':
        nom = request.form.get('nom')
        if not nom:
            flash('Le nom de la classe est requis', 'danger')
            return redirect(url_for('admin.classes'))
        
        cursor = get_db().cursor()
        try:
            cursor.execute("INSERT INTO classes (classe) VALUES (%s)", (nom,))
            get_db().commit()
            flash('Classe ajoutée avec succès', 'success')
        except:
            get_db().rollback()
            flash('Erreur lors de l\'ajout de la classe', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('admin.classes'))

    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT classe as nom FROM classes")
    classes = cursor.fetchall()
    cursor.close()
    return render_template('admin/classes.html', classes=classes)

@admin_bp.route('/classes/supprimer/<string:nom>', methods=['POST'])
@login_required
@admin_required
def supprimer_classe(nom):
    cursor = get_db().cursor()
    try:
        cursor.execute("DELETE FROM classes WHERE classe = %s", (nom,))
        get_db().commit()
        flash('Classe supprimée avec succès', 'success')
    except:
        get_db().rollback()
        flash('Erreur lors de la suppression de la classe', 'danger')
    finally:
        cursor.close()
    return redirect(url_for('admin.classes'))

@admin_bp.route("/gestion_matieres", methods=["GET", "POST"])
@login_required
@admin_required
def gestion_matieres():
    if request.method == "POST":
        nom_matiere = request.form.get("nom_matiere")
        if not nom_matiere:
            flash("Le nom de la matière est requis", "danger")
            return redirect(url_for("admin.gestion_matieres"))

        cursor = get_db().cursor()
        try:
            cursor.execute("INSERT INTO matieres (nom_matiere) VALUES (%s)", (nom_matiere,))
            get_db().commit()
            flash("Matière ajoutée avec succès", "success")
        except:
            get_db().rollback()
            flash("Erreur lors de l'ajout de la matière", "danger")
        finally:
            cursor.close()
        return redirect(url_for("admin.gestion_matieres"))

    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM matieres")
    matieres = cursor.fetchall()
    cursor.close()
    return render_template("admin/matieres.html", matieres=matieres)

@admin_bp.route("/notes", methods=["GET", "POST"])
@login_required
@admin_required
def notes():
    cursor = get_db().cursor(dictionary=True)
    
    # Récupérer les classes et matières pour les formulaires
    cursor.execute("SELECT * FROM classes ORDER BY classe")
    classes = cursor.fetchall()
    cursor.execute("SELECT * FROM matieres ORDER BY nom_matiere")
    matieres = cursor.fetchall()
    
    # Récupérer les élèves pour le formulaire d'ajout
    cursor.execute("""
        SELECT e.id, e.nom, e.prenom, c.classe, c.id as classe_id
        FROM eleves e
        JOIN classes c ON e.classe_id = c.id
        ORDER BY c.classe, e.nom, e.prenom
    """)
    eleves = cursor.fetchall()
    
    if request.method == "POST":
        eleve_id = request.form.get("eleve")
        matiere_id = request.form.get("matiere")
        note = request.form.get("note")
        coef = request.form.get("coef")
        commentaire = request.form.get("commentaire")
        
        if not all([eleve_id, matiere_id, note, coef]):
            flash("Tous les champs obligatoires doivent être remplis", "danger")
            return redirect(url_for("admin.notes"))
            
        try:
            cursor.execute(
                "INSERT INTO notes (eleve_id, matiere_id, note, coef, commentaire) VALUES (%s, %s, %s, %s, %s)",
                (eleve_id, matiere_id, note, coef, commentaire)
            )
            get_db().commit()
            flash("Note ajoutée avec succès", "success")
        except Exception as e:
            get_db().rollback()
            flash(f"Erreur lors de l'ajout de la note : {str(e)}", "danger")
        
        return redirect(url_for("admin.notes"))
    
    # Récupérer toutes les notes avec les informations associées
    cursor.execute("""
        SELECT n.id as note_id, n.note, n.coef, n.commentaire,
               e.nom, e.prenom, c.classe,
               m.nom_matiere
        FROM notes n
        JOIN eleves e ON n.eleve_id = e.id
        JOIN classes c ON e.classe_id = c.id
        JOIN matieres m ON n.matiere_id = m.id
        ORDER BY c.classe, e.nom, e.prenom, m.nom_matiere
    """)
    notes = cursor.fetchall()
    
    return render_template("admin/notes.html", notes=notes, classes=classes, matieres=matieres, eleves=eleves)

@admin_bp.route("/get_eleves")
@login_required
@admin_required
def get_eleves():
    classe_id = request.args.get('classe_id')
    if not classe_id:
        return {"eleves": []}

    cursor = get_db().cursor(dictionary=True)
    
    try:
        # Récupérer les élèves de la classe
        cursor.execute("""
            SELECT e.id, e.nom, e.prenom, c.classe, c.id as classe_id
            FROM eleves e
            JOIN classes c ON e.classe_id = c.id
            WHERE c.id = %s
            ORDER BY e.nom, e.prenom
        """, (classe_id,))
        
        eleves = cursor.fetchall()
        return {"eleves": eleves}
    
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        cursor.close()

@admin_bp.route("/get_eleves_by_classe/<int:classe_id>")
@login_required
@admin_required
def get_eleves_by_classe(classe_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Récupérer les élèves de la classe
        cursor.execute("""
            SELECT e.id, e.nom, e.prenom, c.classe, c.id as classe_id
            FROM eleves e
            JOIN classes c ON e.classe_id = c.id
            WHERE c.id = %s
            ORDER BY e.nom, e.prenom
        """, (classe_id,))
        
        eleves = cursor.fetchall()
        return jsonify(eleves)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/saisir_notes_devoir")
@login_required
@admin_required
def saisir_notes_devoir():
    # Récupérer les paramètres
    classe_id = request.args.get('classe_id')
    matiere_id = request.args.get('matiere_id')
    nom_devoir = request.args.get('nom_devoir')
    coefficient = request.args.get('coefficient')

    if not all([classe_id, matiere_id, nom_devoir, coefficient]):
        flash("Tous les champs sont requis", "danger")
        return redirect(url_for('admin.notes'))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Récupérer les informations de la classe et de la matière
        cursor.execute("""
            SELECT c.classe, m.nom_matiere
            FROM classes c, matieres m
            WHERE c.id = %s AND m.id = %s
        """, (classe_id, matiere_id))
        info = cursor.fetchone()

        # Récupérer la liste des élèves de la classe
        cursor.execute("""
            SELECT id, nom, prenom
            FROM eleves
            WHERE classe_id = %s
            ORDER BY nom, prenom
        """, (classe_id,))
        eleves = cursor.fetchall()

        return render_template('admin/saisie_notes.html',
                             classe_id=classe_id,
                             matiere_id=matiere_id,
                             nom_devoir=nom_devoir,
                             coefficient=coefficient,
                             classe=info['classe'],
                             matiere=info['nom_matiere'],
                             eleves=eleves,
                             is_admin=True)

    except Exception as e:
        print(f"Erreur complète : {str(e)}")
        flash(f"Erreur : {str(e)}", "danger")
        return redirect(url_for('admin.notes'))

@admin_bp.route("/ajouter_devoir", methods=["POST"])
@login_required
@admin_required
def ajouter_devoir():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Récupérer les informations du devoir
        classe_id = request.form.get('classe_id')
        matiere_id = request.form.get('matiere_id')
        nom_devoir = request.form.get('nom_devoir')
        coefficient = request.form.get('coefficient')
        eleve_ids = request.form.getlist('eleve_ids[]')
        notes = request.form.getlist('notes[]')

        # Vérifier que nous avons toutes les informations nécessaires
        if not all([classe_id, matiere_id, nom_devoir, coefficient]):
            flash("Toutes les informations du devoir sont requises", "danger")
            return redirect(url_for('admin.notes'))

        # Insérer les notes pour chaque élève
        for eleve_id, note in zip(eleve_ids, notes):
            if note.strip():  # Vérifier que la note n'est pas vide
                try:
                    cursor.execute("""
                        INSERT INTO notes (eleve_id, matiere_id, note, coef, commentaire)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        eleve_id,
                        matiere_id,
                        float(note),
                        int(coefficient),
                        nom_devoir
                    ))
                except ValueError:
                    flash(f"La note '{note}' n'est pas valide", "danger")
                    return redirect(url_for('admin.notes'))

        db.commit()
        flash("Les notes ont été ajoutées avec succès", "success")
        
    except Exception as e:
        db.rollback()
        flash(f"Erreur lors de l'ajout des notes : {str(e)}", "danger")
        
    return redirect(url_for('admin.notes'))

@admin_bp.route("/notes/delete/<int:note_id>", methods=["POST"])
@login_required
@admin_required
def delete_note(note_id):
    try:
        cursor = get_db().cursor()
        # Utiliser le nom de colonne correct pour l'ID
        cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        get_db().commit()
        flash("Note supprimée avec succès", "success")
    except Exception as e:
        flash(f"Erreur lors de la suppression de la note : {str(e)}", "danger")
        get_db().rollback()
    finally:
        cursor.close()
    
    return redirect(url_for("admin.notes"))

@admin_bp.route("/justifications")
@login_required
@admin_required
def justifications():
    cursor = get_db().cursor(dictionary=True)
    
    # Récupérer uniquement les absences avec justification en attente
    cursor.execute("""
        SELECT a.id, a.date, a.creneau, a.justification, a.justification_status,
               CONCAT(e.nom, ' ', e.prenom) as eleve_nom,
               c.classe as classe_nom
        FROM absences a
        JOIN eleves e ON a.eleve_id = e.id
        JOIN classes c ON e.classe_id = c.id
        WHERE a.justification_status = 'en_attente'
        ORDER BY a.date DESC, a.creneau
    """)
    
    justifications = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/justifications.html', justifications=justifications)

@admin_bp.route("/justifications_traitees")
@login_required
@admin_required
def justifications_traitees():
    cursor = get_db().cursor(dictionary=True)
    
    # Récupérer toutes les classes
    cursor.execute("SELECT id, classe FROM classes ORDER BY classe")
    classes = cursor.fetchall()
    
    # Récupérer les paramètres de filtrage
    classe_id = request.args.get('classe_id', type=int)
    eleve_id = request.args.get('eleve_id', type=int)
    status = request.args.get('status')
    
    # Récupérer les élèves de la classe sélectionnée
    if classe_id:
        cursor.execute("""
            SELECT e.id, e.nom, e.prenom, c.classe, c.id as classe_id
            FROM eleves e
            JOIN classes c ON e.classe_id = c.id
            WHERE c.id = %s
            ORDER BY e.nom, e.prenom
        """, (classe_id,))
        eleves = cursor.fetchall()
    else:
        eleves = []
        # Si un élève était sélectionné mais qu'on a désélectionné la classe, on retire aussi l'élève
        eleve_id = None
    
    # Construire la requête de base
    query = """
        SELECT a.id, a.date, a.creneau, a.justification, a.justification_status,
               CONCAT(e.nom, ' ', e.prenom) as eleve_nom,
               c.classe as classe_nom,
               e.id as eleve_id,
               c.id as classe_id
        FROM absences a
        JOIN eleves e ON a.eleve_id = e.id
        JOIN classes c ON e.classe_id = c.id
        WHERE 1=1
    """
    params = []
    
    # Ajouter les conditions de filtrage
    if classe_id:
        query += " AND c.id = %s"
        params.append(classe_id)
        
    if eleve_id:
        query += " AND e.id = %s"
        params.append(eleve_id)

    if status:
        if status == 'non_justifiee':
            query += " AND (a.justification_status IS NULL OR a.justification_status = '')"
        else:
            query += " AND a.justification_status = %s"
            params.append(status)
    
    # Ajouter l'ordre
    query += """ ORDER BY 
        CASE 
            WHEN a.justification_status IS NULL THEN 1
            WHEN a.justification_status = 'en_attente' THEN 2
            WHEN a.justification_status = 'acceptee' THEN 3
            WHEN a.justification_status = 'refusee' THEN 4
        END,
        a.date DESC, a.creneau
    """
    
    # Exécuter la requête finale
    cursor.execute(query, params)
    justifications = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/justifications_traitees.html',
                         justifications=justifications,
                         classes=classes,
                         eleves=eleves,
                         selected_classe_id=classe_id,
                         selected_eleve_id=eleve_id,
                         selected_status=status)

@admin_bp.route("/valider_justification/<int:absence_id>/<string:action>")
@login_required
@admin_required
def valider_justification(absence_id, action):
    cursor = get_db().cursor(dictionary=True)
    
    if action == 'accepter':
        cursor.execute("""
            UPDATE absences 
            SET justification_status = 'acceptee', justifie = 1
            WHERE id = %s
        """, (absence_id,))
    elif action == 'refuser':
        cursor.execute("""
            UPDATE absences 
            SET justification_status = 'refusee', justifie = 0
            WHERE id = %s
        """, (absence_id,))
    
    get_db().commit()
    cursor.close()
    
    flash("Justification traitée avec succès", "success")
    return redirect(url_for('admin.justifications'))

@admin_bp.route('/eleves')
@login_required
@admin_required
def eleves():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM eleves")  
    eleves = cursor.fetchall()
    cursor.close()
    return render_template("admin/eleves.html", eleves=eleves)

@admin_bp.route("/parents", methods=["GET", "POST"])
@login_required
@admin_required
def parents():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    if request.method == "POST":
        # Récupérer et valider les données du formulaire
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        telephone = request.form.get("telephone", "").strip()
        eleve_ids = request.form.getlist("eleve_ids")
        relation = request.form.get("relation", "").strip()
        
        print(f"Données reçues du formulaire:")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Nom: {nom}")
        print(f"Prénom: {prenom}")
        print(f"Relation: {relation}")
        print(f"IDs des élèves: {eleve_ids}")
        
        # Vérifier que les champs requis sont remplis
        if not all([username, email, password, nom, prenom, relation, eleve_ids]):
            flash("Tous les champs requis doivent être remplis", "danger")
            return redirect(url_for('admin.parents'))
        
        try:
            # Créer l'utilisateur avec le rôle 'parent'
            hashed_password, salt_b64 = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password, salt, role) VALUES (%s, %s, %s, %s, %s)",
                (username, email, hashed_password, salt_b64, 'parent')
            )
            user_id = cursor.lastrowid
            print(f"Utilisateur créé avec ID: {user_id}")
            
            # Créer le parent
            cursor.execute(
                "INSERT INTO parents (user_id, nom, prenom, telephone) VALUES (%s, %s, %s, %s)",
                (user_id, nom, prenom, telephone or None)
            )
            parent_id = cursor.lastrowid
            print(f"Parent créé avec ID: {parent_id}")
            
            # Lier le parent aux élèves sélectionnés
            for eleve_id in eleve_ids:
                if eleve_id.strip():  # Vérifier que l'ID n'est pas vide
                    print(f"Tentative de liaison avec l'élève ID: {eleve_id}")
                    cursor.execute(
                        "INSERT INTO parent_eleve (parent_id, eleve_id, relation) VALUES (%s, %s, %s)",
                        (parent_id, int(eleve_id), relation)
                    )
                    print(f"Liaison créée avec l'élève ID: {eleve_id}")
            
            db.commit()
            flash("Parent ajouté avec succès", "success")
            
        except Exception as e:
            db.rollback()
            print(f"Erreur détaillée: {str(e)}")
            flash(f"Erreur lors de l'ajout du parent: {str(e)}", "danger")
    
    # Récupérer la liste des parents
    cursor.execute("""
        SELECT p.*, u.username, u.email,
               GROUP_CONCAT(CONCAT(e.prenom, ' ', e.nom) SEPARATOR ', ') as enfants
        FROM parents p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN parent_eleve pe ON p.parent_id = pe.parent_id
        LEFT JOIN eleves e ON pe.eleve_id = e.id
        GROUP BY p.parent_id
    """)
    parents = cursor.fetchall()
    
    # Récupérer la liste des élèves pour le formulaire
    cursor.execute("SELECT id, prenom, nom FROM eleves ORDER BY nom, prenom")
    eleves = cursor.fetchall()
    
    cursor.close()
    return render_template('admin/parents.html', parents=parents, eleves=eleves)

@admin_bp.route("/parents/delete/<int:parent_id>", methods=["POST"])
@login_required
@admin_required
def delete_parent(parent_id):
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Récupérer l'ID utilisateur
        cursor.execute("SELECT user_id FROM parents WHERE parent_id = %s", (parent_id,))
        user_id = cursor.fetchone()[0]
        
        # Supprimer les liens parent-élève
        cursor.execute("DELETE FROM parent_eleve WHERE parent_id = %s", (parent_id,))
        
        # Supprimer le parent
        cursor.execute("DELETE FROM parents WHERE parent_id = %s", (parent_id,))
        
        # Supprimer l'utilisateur
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        db.commit()
        flash("Parent supprimé avec succès", "success")
        
    except Exception as e:
        db.rollback()
        flash(f"Erreur lors de la suppression du parent: {str(e)}", "danger")
    
    cursor.close()
    return redirect(url_for('admin.parents'))
