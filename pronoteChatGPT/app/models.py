from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from app import db  # ✅ Import `db` sans recréer une instance SQLAlchemy

class User(UserMixin, db.Model):  # ✅ Ajouter `UserMixin`
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class Classe(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)
    niveau = db.Column(db.String(20), nullable=False)
    
    def __repr__(self):
        return f"<Classe {self.nom}>"
