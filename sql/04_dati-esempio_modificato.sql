-- Imposta lo schema
SET search_path TO catasto;

-- Inserimento Comuni (con ON CONFLICT per evitare duplicati)
INSERT INTO comune (nome, provincia, regione) VALUES 
('Carcare', 'Savona', 'Liguria'),
('Cairo Montenotte', 'Savona', 'Liguria'),
('Altare', 'Savona', 'Liguria')
ON CONFLICT (nome) DO NOTHING;

-- Inserimento Registri Partite
INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) VALUES
('Carcare', 1950, 3, 'Buono'),
('Cairo Montenotte', 1948, 5, 'Discreto'),
('Altare', 1952, 2, 'Ottimo')
ON CONFLICT DO NOTHING;

-- Inserimento Registri Matricole
INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) VALUES
('Carcare', 1950, 2, 'Buono'),
('Cairo Montenotte', 1948, 4, 'Discreto'),
('Altare', 1952, 1, 'Ottimo')
ON CONFLICT DO NOTHING;

-- Inserimento Possessori
INSERT INTO possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo) VALUES
('Carcare', 'Fossati Angelo', 'fu Roberto', 'Fossati Angelo fu Roberto', true),
('Carcare', 'Caviglia Maria', 'fu Giuseppe', 'Caviglia Maria fu Giuseppe', true),
('Carcare', 'Barberis Giovanni', 'fu Paolo', 'Barberis Giovanni fu Paolo', true),
('Cairo Montenotte', 'Berruti Antonio', 'fu Luigi', 'Berruti Antonio fu Luigi', true),
('Cairo Montenotte', 'Ferraro Caterina', 'fu Marco', 'Ferraro Caterina fu Marco', true),
('Altare', 'Bormioli Pietro', 'fu Carlo', 'Bormioli Pietro fu Carlo', true)
ON CONFLICT DO NOTHING;

-- Inserimento Località
INSERT INTO localita (comune_nome, nome, tipo, civico) VALUES
('Carcare', 'Regione Vista', 'regione', NULL),
('Carcare', 'Via Giuseppe Verdi', 'via', 12),
('Carcare', 'Via Roma', 'via', 5),
('Cairo Montenotte', 'Borgata Ferrere', 'borgata', NULL),
('Cairo Montenotte', 'Strada Provinciale', 'via', 76),
('Altare', 'Via Palermo', 'via', 22)
ON CONFLICT DO NOTHING;

-- Inserimento Partite
INSERT INTO partita (comune_nome, numero_partita, tipo, data_impianto, stato) VALUES
('Carcare', 221, 'principale', '1950-05-10', 'attiva'),
('Carcare', 219, 'principale', '1950-05-10', 'attiva'),
('Carcare', 245, 'secondaria', '1951-03-22', 'attiva'),
('Cairo Montenotte', 112, 'principale', '1948-11-05', 'attiva'),
('Cairo Montenotte', 118, 'principale', '1949-01-15', 'inattiva'),
('Altare', 87, 'principale', '1952-07-03', 'attiva')
ON CONFLICT DO NOTHING;

-- Associazione Partite-Possessori
INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES
(1, 1, 'principale', 'proprietà esclusiva', NULL),
(2, 2, 'principale', 'proprietà esclusiva', NULL),
(3, 3, 'secondaria', 'comproprietà', '1/2'),
(3, 2, 'secondaria', 'comproprietà', '1/2'),
(4, 4, 'principale', 'proprietà esclusiva', NULL),
(5, 5, 'principale', 'proprietà esclusiva', NULL),
(6, 6, 'principale', 'proprietà esclusiva', NULL)
ON CONFLICT DO NOTHING;

-- Relazioni tra partite (principale-secondaria)
INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) VALUES
(2, 3)
ON CONFLICT DO NOTHING;

-- Inserimento Immobili
INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES
(1, 1, 'Molino da cereali', 2, NULL, '150 mq', 'Artigianale'),
(2, 2, 'Casa', 3, 8, '210 mq', 'Abitazione civile'),
(3, 3, 'Magazzino', 1, NULL, '80 mq', 'Deposito'),
(4, 4, 'Fabbricato rurale', 2, 5, '180 mq', 'Abitazione rurale'),
(5, 5, 'Casa', 2, 6, '160 mq', 'Abitazione civile'),
(6, 6, 'Laboratorio', 1, NULL, '120 mq', 'Artigianale')
ON CONFLICT DO NOTHING;

-- Inserimento Variazioni
INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) VALUES
(5, NULL, 'Successione', '1952-08-15', '22/52', 'Ferraro Caterina')
ON CONFLICT DO NOTHING;

-- Inserimento Contratti
INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES
(1, 'Successione', '1952-08-10', 'Notaio Rossi', '1234/52', 'Successione per morte del proprietario Luigi Ferraro')
ON CONFLICT DO NOTHING;

-- Inserimento Consultazioni
INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) VALUES
('2025-04-01', 'Mario Bianchi', 'CI AB1234567', 'Ricerca storica', 'Registro partite Carcare 1950', 'Dott. Verdi'),
('2025-04-05', 'Studio Legale Rossi', 'Tessera Ordine 55213', 'Verifica proprietà', 'Partite 221 e 219 Carcare', 'Dott. Verdi')
ON CONFLICT DO NOTHING;