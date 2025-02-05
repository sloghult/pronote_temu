-- Ajouter la colonne salt à la table users
ALTER TABLE users ADD COLUMN salt BLOB;

-- Mettre à jour les mots de passe existants
-- Note: Les anciens mots de passe devront être réinitialisés car nous ne pouvons pas les décrypter
