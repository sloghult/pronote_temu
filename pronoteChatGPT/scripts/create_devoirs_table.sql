-- Table pour les devoirs
CREATE TABLE IF NOT EXISTS devoirs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    titre VARCHAR(200) NOT NULL,
    description TEXT,
    date DATE NOT NULL,
    matiere_id INT NOT NULL,
    FOREIGN KEY (matiere_id) REFERENCES matieres(id)
);

-- Vérifier si la colonne devoir_id existe déjà
SET @dbname = 'pronote1';
SET @tablename = 'notes';
SET @columnname = 'devoir_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      TABLE_SCHEMA = @dbname
      AND TABLE_NAME = @tablename
      AND COLUMN_NAME = @columnname
  ) > 0,
  'SELECT 1',
  'ALTER TABLE notes ADD COLUMN devoir_id INT, ADD FOREIGN KEY (devoir_id) REFERENCES devoirs(id)'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
