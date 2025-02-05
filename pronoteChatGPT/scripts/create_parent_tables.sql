-- Table pour les parents
CREATE TABLE IF NOT EXISTS parents (
    parent_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    telephone VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table de liaison entre parents et élèves
CREATE TABLE IF NOT EXISTS parent_eleve (
    parent_id INT,
    eleve_id INT,
    relation VARCHAR(50) NOT NULL, -- 'père', 'mère', 'tuteur'
    PRIMARY KEY (parent_id, eleve_id),
    FOREIGN KEY (parent_id) REFERENCES parents(parent_id),
    FOREIGN KEY (eleve_id) REFERENCES eleves(id)
);
