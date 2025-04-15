            try {
                int id = Integer.parseInt(idText);
                loadPartiteDelPossessore(model, id);
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "L'ID deve essere un numero intero.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        partitePanel.add(scrollPane, BorderLayout.CENTER);
        partitePanel.add(loadPartiteButton, BorderLayout.SOUTH);
        
        updatePossessorePanel.add(partitePanel, BorderLayout.CENTER);
    }
    
    /**
     * Connette al database PostgreSQL
     */
    public boolean connect(String user, String password, String host, String port) {
        try {
            System.out.println("Connessione al database catasto_storico...");
            
            String url = "jdbc:postgresql://" + host + ":" + port + "/catasto_storico";
            conn = DriverManager.getConnection(url, user, password);
            
            // Imposta lo schema catasto
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("SET search_path TO catasto;");
            }
            
            connected = true;
            System.out.println("Connessione stabilita con successo!");
            return true;
        } catch (SQLException e) {
            System.out.println("Errore di connessione: " + e.getMessage());
            JOptionPane.showMessageDialog(this, 
                    "Errore di connessione: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            return false;
        }
    }
    
    /**
     * Disconnette dal database
     */
    public void disconnect() {
        if (conn != null) {
            try {
                conn.close();
                System.out.println("Disconnesso dal database.");
            } catch (SQLException e) {
                System.out.println("Errore durante la disconnessione: " + e.getMessage());
            }
        }
        connected = false;
    }
    
    /**
     * Mostra il pannello dei comuni e carica i dati
     */
    private void showComuni() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "comuni");
        JTable table = (JTable) ((JScrollPane) comuniPanel.getComponent(1)).getViewport().getView();
        loadComuniData((DefaultTableModel) table.getModel());
    }
    
    /**
     * Mostra il pannello delle partite e carica i dati
     */
    private void showPartite() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "partite");
        JTable table = (JTable) ((JScrollPane) partitePanel.getComponent(1)).getViewport().getView();
        loadPartiteData((DefaultTableModel) table.getModel());
    }
    
    /**
     * Mostra il pannello dei possessori e carica i dati
     */
    private void showPossessori() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "possessori");
        JTable table = (JTable) ((JScrollPane) possessoriPanel.getComponent(1)).getViewport().getView();
        loadPossessoriData((DefaultTableModel) table.getModel());
    }
    
    /**
     * Mostra il pannello degli immobili e carica i dati
     */
    private void showImmobili() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "immobili");
        JTable table = (JTable) ((JScrollPane) immobiliPanel.getComponent(1)).getViewport().getView();
        loadImmobiliData((DefaultTableModel) table.getModel());
    }
    
    /**
     * Mostra il pannello di inserimento possessore
     */
    private void showInsertPossessore() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "insertPossessore");
        // Trova il componente JComboBox dentro il GridBagLayout
        JPanel formPanel = (JPanel) insertPossessorePanel.getComponent(0);
        Component[] components = formPanel.getComponents();
        for (Component c : components) {
            if (c instanceof JComboBox) {
                @SuppressWarnings("unchecked")
                JComboBox<String> comuneCombo = (JComboBox<String>) c;
                loadComuniCombo(comuneCombo);
                break;
            }
        }
    }
    
    /**
     * Mostra il pannello di inserimento partita
     */
    private void showInsertPartita() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "insertPartita");
        // Trova il componente JComboBox dentro il GridBagLayout
        JPanel formPanel = (JPanel) insertPartitaPanel.getComponent(0);
        Component[] components = formPanel.getComponents();
        JComboBox<String> comuneCombo = null;
        JComboBox<ComboItem> possessoreCombo = null;
        
        for (Component c : components) {
            if (c instanceof JComboBox) {
                @SuppressWarnings("unchecked")
                JComboBox<?> combo = (JComboBox<?>) c;
                if (combo.getItemAt(0) instanceof String) {
                    @SuppressWarnings("unchecked")
                    JComboBox<String> cc = (JComboBox<String>) combo;
                    comuneCombo = cc;
                } else if (combo.getItemCount() == 0 || combo.getItemAt(0) instanceof ComboItem) {
                    @SuppressWarnings("unchecked")
                    JComboBox<ComboItem> pc = (JComboBox<ComboItem>) combo;
                    possessoreCombo = pc;
                }
            }
        }
        
        if (comuneCombo != null) {
            loadComuniCombo(comuneCombo);
            if (possessoreCombo != null && comuneCombo.getItemCount() > 0) {
                String selectedComune = (String) comuneCombo.getSelectedItem();
                if (selectedComune != null) {
                    loadPossessoriCombo(possessoreCombo, selectedComune);
                }
            }
        }
    }
    
    /**
     * Mostra il pannello del certificato
     */
    private void showCertificatoPanel() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "certificato");
    }
    
    /**
     * Mostra il pannello di ricerca possessori
     */
    private void showRicercaPossessori() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "ricercaPossessori");
    }
    
    /**
     * Mostra il pannello di ricerca immobili
     */
    private void showRicercaImmobili() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "ricercaImmobili");
        // Trova il componente JComboBox dentro il GridBagLayout
        JPanel searchPanel = (JPanel) ricercaImmobiliPanel.getComponent(0);
        Component[] components = searchPanel.getComponents();
        for (Component c : components) {
            if (c instanceof JComboBox) {
                @SuppressWarnings("unchecked")
                JComboBox<String> comuneCombo = (JComboBox<String>) c;
                loadComuniCombo(comuneCombo);
                break;
            }
        }
    }
    
    /**
     * Mostra il pannello di aggiornamento possessore
     */
    private void showUpdatePossessore() {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "updatePossessore");
    }
    
    /**
     * Mostra pannello aggiornamento con possessore preselezionato
     */
    private void showUpdatePossessore(int possessoreId) {
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "updatePossessore");
        
        // Trova il campo ID e il pulsante di ricerca
        JPanel formPanel = (JPanel) updatePossessorePanel.getComponent(0);
        Component[] components = formPanel.getComponents();
        JTextField idField = null;
        JButton searchButton = null;
        
        for (Component c : components) {
            if (c instanceof JTextField) {
                JTextField tf = (JTextField) c;
                if (tf.getColumns() == 10) { // Il campo ID ha 10 colonne
                    idField = tf;
                }
            } else if (c instanceof JButton) {
                JButton btn = (JButton) c;
                if (btn.getText().equals("Cerca")) {
                    searchButton = btn;
                }
            }
        }
        
        if (idField != null && searchButton != null) {
            idField.setText(String.valueOf(possessoreId));
            searchButton.doClick(); // Simula il click sul pulsante di ricerca
            
            // Cerca anche il pulsante "Carica Partite" e simulane il click
            JPanel partitePanel = (JPanel) updatePossessorePanel.getComponent(1);
            Component[] partiteComponents = partitePanel.getComponents();
            for (Component c : partiteComponents) {
                if (c instanceof JButton && ((JButton) c).getText().equals("Carica Partite")) {
                    ((JButton) c).doClick();
                    break;
                }
            }
        }
    }
    
    /**
     * Mostra i dettagli di una partita
     */
    private void showPartitaDetails(int partitaId) {
        try {
            PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT p.*, string_agg(pos.nome_completo, ', ') as possessori " +
                    "FROM partita p " +
                    "LEFT JOIN partita_possessore pp ON p.id = pp.partita_id " +
                    "LEFT JOIN possessore pos ON pp.possessore_id = pos.id " +
                    "WHERE p.id = ? " +
                    "GROUP BY p.id;");
            pstmt.setInt(1, partitaId);
            ResultSet rs = pstmt.executeQuery();
            
            if (rs.next()) {
                StringBuilder details = new StringBuilder();
                details.append("DETTAGLI PARTITA\n\n");
                details.append("ID: ").append(rs.getInt("id")).append("\n");
                details.append("Comune: ").append(rs.getString("comune_nome")).append("\n");
                details.append("Numero: ").append(rs.getInt("numero_partita")).append("\n");
                details.append("Tipo: ").append(rs.getString("tipo")).append("\n");
                details.append("Stato: ").append(rs.getString("stato")).append("\n");
                details.append("Data impianto: ").append(rs.getDate("data_impianto")).append("\n");
                if (rs.getDate("data_chiusura") != null) {
                    details.append("Data chiusura: ").append(rs.getDate("data_chiusura")).append("\n");
                }
                details.append("Possessori: ").append(rs.getString("possessori")).append("\n\n");
                
                // Aggiungi gli immobili della partita
                details.append("IMMOBILI:\n");
                PreparedStatement immobiliStmt = conn.prepareStatement(
                        "SELECT i.id, i.natura, l.nome as localita, i.classificazione " +
                        "FROM immobile i " +
                        "JOIN localita l ON i.localita_id = l.id " +
                        "WHERE i.partita_id = ?;");
                immobiliStmt.setInt(1, partitaId);
                ResultSet immobiliRs = immobiliStmt.executeQuery();
                
                int immobileCount = 0;
                while (immobiliRs.next()) {
                    immobileCount++;
                    details.append(immobileCount).append(". ");
                    details.append(immobiliRs.getString("natura")).append(" in ");
                    details.append(immobiliRs.getString("localita")).append(" (");
                    details.append(immobiliRs.getString("classificazione")).append(")\n");
                }
                
                if (immobileCount == 0) {
                    details.append("Nessun immobile associato.\n");
                }
                
                // Mostra i dettagli in una finestra di dialogo
                JTextArea textArea = new JTextArea(details.toString());
                textArea.setEditable(false);
                textArea.setWrapStyleWord(true);
                textArea.setLineWrap(true);
                JScrollPane scrollPane = new JScrollPane(textArea);
                scrollPane.setPreferredSize(new Dimension(500, 400));
                
                JOptionPane.showMessageDialog(this, scrollPane, 
                        "Dettagli Partita #" + partitaId, JOptionPane.INFORMATION_MESSAGE);
            } else {
                JOptionPane.showMessageDialog(this, 
                        "Nessuna partita trovata con ID " + partitaId, 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        } catch (SQLException ex) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel recupero dei dettagli della partita: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Mostra i dettagli di un possessore
     */
    private void showPossessoreDetails(int possessoreId) {
        try {
            PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT * FROM possessore WHERE id = ?;");
            pstmt.setInt(1, possessoreId);
            ResultSet rs = pstmt.executeQuery();
            
            if (rs.next()) {
                StringBuilder details = new StringBuilder();
                details.append("DETTAGLI POSSESSORE\n\n");
                details.append("ID: ").append(rs.getInt("id")).append("\n");
                details.append("Nome Completo: ").append(rs.getString("nome_completo")).append("\n");
                details.append("Cognome e Nome: ").append(rs.getString("cognome_nome")).append("\n");
                details.append("Paternità: ").append(rs.getString("paternita")).append("\n");
                details.append("Comune: ").append(rs.getString("comune_nome")).append("\n");
                details.append("Stato: ").append(rs.getBoolean("attivo") ? "Attivo" : "Non attivo").append("\n\n");
                
                // Aggiungi le partite del possessore
                details.append("PARTITE:\n");
                PreparedStatement partiteStmt = conn.prepareStatement(
                        "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato, pp.titolo, pp.quota " +
                        "FROM partita p " +
                        "JOIN partita_possessore pp ON p.id = pp.partita_id " +
                        "WHERE pp.possessore_id = ? " +
                        "ORDER BY p.comune_nome, p.numero_partita;");
                partiteStmt.setInt(1, possessoreId);
                ResultSet partiteRs = partiteStmt.executeQuery();
                
                int partitaCount = 0;
                while (partiteRs.next()) {
                    partitaCount++;
                    details.append(partitaCount).append(". ");
                    details.append("Partita ").append(partiteRs.getInt("numero_partita"));
                    details.append(" in ").append(partiteRs.getString("comune_nome"));
                    details.append(" (").append(partiteRs.getString("tipo")).append(", ");
                    details.append(partiteRs.getString("stato")).append(")");
                    
                    String titolo = partiteRs.getString("titolo");
                    String quota = partiteRs.getString("quota");
                    if (titolo != null) {
                        details.append(" - ").append(titolo);
                        if (quota != null) {
                            details.append(" (quota ").append(quota).append(")");
                        }
                    }
                    details.append("\n");
                }
                
                if (partitaCount == 0) {
                    details.append("Nessuna partita associata.\n");
                }
                
                // Mostra i dettagli in una finestra di dialogo
                JTextArea textArea = new JTextArea(details.toString());
                textArea.setEditable(false);
                textArea.setWrapStyleWord(true);
                textArea.setLineWrap(true);
                JScrollPane scrollPane = new JScrollPane(textArea);
                scrollPane.setPreferredSize(new Dimension(500, 400));
                
                JOptionPane.showMessageDialog(this, scrollPane, 
                        "Dettagli Possessore #" + possessoreId, JOptionPane.INFORMATION_MESSAGE);
            } else {
                JOptionPane.showMessageDialog(this, 
                        "Nessun possessore trovato con ID " + possessoreId, 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        } catch (SQLException ex) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel recupero dei dettagli del possessore: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Mostra i dettagli di un immobile
     */
    private void showImmobileDetails(int immobileId) {
        try {
            PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT i.*, l.nome as localita_nome, l.tipo as localita_tipo, " +
                    "p.numero_partita, p.comune_nome, p.tipo as partita_tipo " +
                    "FROM immobile i " +
                    "JOIN localita l ON i.localita_id = l.id " +
                    "JOIN partita p ON i.partita_id = p.id " +
                    "WHERE i.id = ?;");
            pstmt.setInt(1, immobileId);
            ResultSet rs = pstmt.executeQuery();
            
            if (rs.next()) {
                StringBuilder details = new StringBuilder();
                details.append("DETTAGLI IMMOBILE\n\n");
                details.append("ID: ").append(rs.getInt("id")).append("\n");
                details.append("Natura: ").append(rs.getString("natura")).append("\n");
                details.append("Località: ").append(rs.getString("localita_nome"));
                details.append(" (").append(rs.getString("localita_tipo")).append(")\n");
                details.append("Classificazione: ").append(rs.getString("classificazione")).append("\n");
                
                if (rs.getInt("numero_piani") > 0) {
                    details.append("Numero Piani: ").append(rs.getInt("numero_piani")).append("\n");
                }
                
                if (rs.getInt("numero_vani") > 0) {
                    details.append("Numero Vani: ").append(rs.getInt("numero_vani")).append("\n");
                }
                
                if (rs.getString("consistenza") != null) {
                    details.append("Consistenza: ").append(rs.getString("consistenza")).append("\n");
                }
                
                details.append("\nPARTITA:\n");
                details.append("Numero: ").append(rs.getInt("numero_partita")).append("\n");
                details.append("Comune: ").append(rs.getString("comune_nome")).append("\n");
                details.append("Tipo: ").append(rs.getString("partita_tipo")).append("\n\n");
                
                // Aggiungi i possessori della partita
                PreparedStatement possessoriStmt = conn.prepareStatement(
                        "SELECT pos.nome_completo, pp.titolo, pp.quota " +
                        "FROM possessore pos " +
                        "JOIN partita_possessore pp ON pos.id = pp.possessore_id " +
                        "WHERE pp.partita_id = ? " +
                        "ORDER BY pos.nome_completo;");
                possessoriStmt.setInt(1, rs.getInt("partita_id"));
                ResultSet possessoriRs = possessoriStmt.executeQuery();
                
                details.append("POSSESSORI:\n");
                int possessoreCount = 0;
                while (possessoriRs.next()) {
                    possessoreCount++;
                    details.append(possessoreCount).append(". ");
                    details.append(possessoriRs.getString("nome_completo"));
                    
                    String titolo = possessoriRs.getString("titolo");
                    String quota = possessoriRs.getString("quota");
                    if (titolo != null) {
                        details.append(" - ").append(titolo);
                        if (quota != null) {
                            details.append(" (quota ").append(quota).append(")");
                        }
                    }
                    details.append("\n");
                }
                
                if (possessoreCount == 0) {
                    details.append("Nessun possessore associato.\n");
                }
                
                // Mostra i dettagli in una finestra di dialogo
                JTextArea textArea = new JTextArea(details.toString());
                textArea.setEditable(false);
                textArea.setWrapStyleWord(true);
                textArea.setLineWrap(true);
                JScrollPane scrollPane = new JScrollPane(textArea);
                scrollPane.setPreferredSize(new Dimension(500, 400));
                
                JOptionPane.showMessageDialog(this, scrollPane, 
                        "Dettagli Immobile #" + immobileId, JOptionPane.INFORMATION_MESSAGE);
            } else {
                JOptionPane.showMessageDialog(this, 
                        "Nessun immobile trovato con ID " + immobileId, 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        } catch (SQLException ex) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel recupero dei dettagli dell'immobile: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i dati dei comuni nella tabella
     */
    private void loadComuniData(DefaultTableModel model) {
        model.setRowCount(0);
        
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT nome, provincia, regione FROM comune ORDER BY nome;")) {
            
            while (rs.next()) {
                String nome = rs.getString("nome");
                String provincia = rs.getString("provincia");
                String regione = rs.getString("regione");
                model.addRow(new Object[]{nome, provincia, regione});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento dei comuni: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i dati delle partite nella tabella
     */
    private void loadPartiteData(DefaultTableModel model) {
        model.setRowCount(0);
        
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato, " +
                             "string_agg(pos.nome_completo, ', ') as possessori " +
                             "FROM partita p " +
                             "LEFT JOIN partita_possessore pp ON p.id = pp.partita_id " +
                             "LEFT JOIN possessore pos ON pp.possessore_id = pos.id " +
                             "GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato " +
                             "ORDER BY p.comune_nome, p.numero_partita " +
                             "LIMIT 50;")) {
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String comune = rs.getString("comune_nome");
                int numero = rs.getInt("numero_partita");
                String tipo = rs.getString("tipo");
                String stato = rs.getString("stato");
                String possessori = rs.getString("possessori");
                if (possessori == null) possessori = "";
                if (possessori.length() > 30) possessori = possessori.substring(0, 27) + "...";
                
                model.addRow(new Object[]{id, comune, numero, tipo, stato, possessori});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento delle partite: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica le partite per la selezione
     */
    private void loadPartiteForSelection(DefaultTableModel model, String comune) {
        model.setRowCount(0);
        
        try {
            String sql = "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo " +
                      "FROM partita p " +
                      "WHERE 1=1 ";
            
            if (comune != null && !comune.isEmpty()) {
                sql += "AND p.comune_nome ILIKE ? ";
            }
            
            sql += "ORDER BY p.comune_nome, p.numero_partita LIMIT 50;";
            
            PreparedStatement pstmt = conn.prepareStatement(sql);
            
            if (comune != null && !comune.isEmpty()) {
                pstmt.setString(1, "%" + comune + "%");
            }
            
            ResultSet rs = pstmt.executeQuery();
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String comuneNome = rs.getString("comune_nome");
                int numero = rs.getInt("numero_partita");
                String tipo = rs.getString("tipo");
                
                model.addRow(new Object[]{id, comuneNome, numero, tipo});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento delle partite: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i dati dei possessori nella tabella
     */
    private void loadPossessoriData(DefaultTableModel model) {
        model.setRowCount(0);
        
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT id, nome_completo, comune_nome, attivo " +
                             "FROM possessore " +
                             "ORDER BY comune_nome, nome_completo " +
                             "LIMIT 50;")) {
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String nome = rs.getString("nome_completo");
                String comune = rs.getString("comune_nome");
                boolean attivo = rs.getBoolean("attivo");
                String stato = attivo ? "Attivo" : "Non attivo";
                
                model.addRow(new Object[]{id, nome, comune, stato});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento dei possessori: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i possessori per la selezione
     */
    private void loadPossessoriForSelection(DefaultTableModel model, String nome) {
        model.setRowCount(0);
        
        try {
            String sql = "SELECT id, nome_completo, comune_nome, attivo " +
                      "FROM possessore " +
                      "WHERE 1=1 ";
            
            if (nome != null && !nome.isEmpty()) {
                sql += "AND nome_completo ILIKE ? ";
            }
            
            sql += "ORDER BY comune_nome, nome_completo LIMIT 50;";
            
            PreparedStatement pstmt = conn.prepareStatement(sql);
            
            if (nome != null && !nome.isEmpty()) {
                pstmt.setString(1, "%" + nome + "%");
            }
            
            ResultSet rs = pstmt.executeQuery();
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String nomeCompleto = rs.getString("nome_completo");
                String comune = rs.getString("comune_nome");
                boolean attivo = rs.getBoolean("attivo");
                String stato = attivo ? "Attivo" : "Non attivo";
                
                model.addRow(new Object[]{id, nomeCompleto, comune, stato});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento dei possessori: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica le partite di un possessore nella tabella
     */
    private void loadPartiteDelPossessore(DefaultTableModel model, int possessoreId) {
        model.setRowCount(0);
        
        try {
            PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato " +
                    "FROM partita p " +
                    "JOIN partita_possessore pp ON p.id = pp.partita_id " +
                    "WHERE pp.possessore_id = ? " +
                    "ORDER BY p.comune_nome, p.numero_partita;");
            
            pstmt.setInt(1, possessoreId);
            ResultSet rs = pstmt.executeQuery();
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String comune = rs.getString("comune_nome");
                int numero = rs.getInt("numero_partita");
                String tipo = rs.getString("tipo");
                String stato = rs.getString("stato");
                
                model.addRow(new Object[]{id, comune, numero, tipo, stato});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento delle partite del possessore: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i dati degli immobili nella tabella
     */
    private void loadImmobiliData(DefaultTableModel model) {
        model.setRowCount(0);
        
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT i.id, i.natura, l.nome as localita, p.numero_partita, p.comune_nome " +
                             "FROM immobile i " +
                             "JOIN localita l ON i.localita_id = l.id " +
                             "JOIN partita p ON i.partita_id = p.id " +
                             "ORDER BY p.comune_nome, p.numero_partita " +
                             "LIMIT 50;")) {
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String natura = rs.getString("natura");
                String localita = rs.getString("localita");
                int partita = rs.getInt("numero_partita");
                String comune = rs.getString("comune_nome");
                
                model.addRow(new Object[]{id, natura, localita, partita, comune});
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento degli immobili: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i comuni nella ComboBox
     */
    private void loadComuniCombo(JComboBox<String> comboBox) {
        comboBox.removeAllItems();
        
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT nome FROM comune ORDER BY nome;")) {
            
            while (rs.next()) {
                comboBox.addItem(rs.getString("nome"));
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento dei comuni: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Carica i possessori nella ComboBox in base al comune selezionato
     */
    private void loadPossessoriCombo(JComboBox<ComboItem> comboBox, String comune) {
        comboBox.removeAllItems();
        
        try (PreparedStatement pstmt = conn.prepareStatement(
                "SELECT id, nome_completo FROM possessore " +
                        "WHERE comune_nome = ? AND attivo = TRUE " +
                        "ORDER BY nome_completo;")) {
            
            pstmt.setString(1, comune);
            ResultSet rs = pstmt.executeQuery();
            
            while (rs.next()) {
                int id = rs.getInt("id");
                String nome = rs.getString("nome_completo");
                comboBox.addItem(new ComboItem(id, nome));
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                    "Errore nel caricamento dei possessori: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    /**
     * Classe di utilità per le ComboBox con ID
     */
    private static class ComboItem {
        private int id;
        private String text;
        
        public ComboItem(int id, String text) {
            this.id = id;
            this.text = text;
        }
        
        public int getId() {
            return id;
        }
        
        @Override
        public String toString() {
            return text;
        }
    }
    
    /**
     * Metodo principale
     */
    public static void main(String[] args) {
        try {
            // Imposta il look and feel del sistema
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            
            // Carica il driver JDBC di PostgreSQL
            Class.forName("org.postgresql.Driver");
        } catch (ClassNotFoundException e) {
            JOptionPane.showMessageDialog(null, 
                    "Driver PostgreSQL JDBC non trovato. Assicurati di avere il JAR nel classpath.", 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        EventQueue.invokeLater(() -> {
            CatastoApp app = new CatastoApp();
            app.setVisible(true);
        });
    }
}import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.*;
import java.sql.*;
import java.time.LocalDate;

/**
 * Applicazione Swing per la gestione del database Catasto Storico
 */
public class CatastoApp extends JFrame {
    private Connection conn;
    private boolean connected;
    
    // Componenti UI principali
    private JPanel mainPanel;
    private JPanel loginPanel;
    private JPanel menuPanel;
    private JPanel contentPanel;
    private CardLayout cardLayout;
    private JLabel statusLabel;
    
    // Pannelli per diverse funzionalità
    private JPanel comuniPanel;
    private JPanel partitePanel;
    private JPanel possessoriPanel;
    private JPanel immobiliPanel;
    private JPanel insertPossessorePanel;
    private JPanel insertPartitaPanel;
    private JPanel certificatoPanel;
    private JPanel ricercaPossessoriPanel;
    private JPanel ricercaImmobiliPanel;
    private JPanel updatePossessorePanel;
    
    /**
     * Costruttore che inizializza l'interfaccia grafica
     */
    public CatastoApp() {
        // Configurazione del frame principale
        setTitle("Catasto Storico");
        setSize(900, 650);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);
        
        // Configurazione del layout principale
        cardLayout = new CardLayout();
        mainPanel = new JPanel(cardLayout);
        
        // Creazione dei pannelli
        createLoginPanel();
        createMenuPanel();
        createContentPanel();
        createStatusBar();
        
        // Aggiunta dei pannelli al pannello principale
        mainPanel.add(loginPanel, "login");
        mainPanel.add(menuPanel, "menu");
        
        // Impostazione del pannello di login come pannello iniziale
        cardLayout.show(mainPanel, "login");
        
        // Aggiunta del pannello principale al frame
        add(mainPanel, BorderLayout.CENTER);
        
        // Gestione della chiusura per disconnettersi dal DB
        addWindowListener(new WindowAdapter() {
            @Override
            public void windowClosing(WindowEvent e) {
                disconnect();
            }
        });
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 2;
        formPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        formPanel.add(comuneLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(comuneCombo, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        formPanel.add(numeroLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(numeroField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 3;
        formPanel.add(tipoLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(tipoCombo, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 4;
        formPanel.add(possessoreLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(possessoreCombo, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 5;
        gbc.gridwidth = 2;
        gbc.anchor = GridBagConstraints.CENTER;
        formPanel.add(insertButton, gbc);
        
        // Aggiunta del pulsante di suggerimento numero partita
        JButton suggestButton = new JButton("Suggerisci Numero");
        suggestButton.addActionListener(e -> {
            String comune = (String) comuneCombo.getSelectedItem();
            if (comune != null) {
                try {
                    PreparedStatement pstmt = conn.prepareStatement(
                            "SELECT COALESCE(MAX(numero_partita), 0) + 1 FROM partita WHERE comune_nome = ?;");
                    pstmt.setString(1, comune);
                    ResultSet rs = pstmt.executeQuery();
                    if (rs.next()) {
                        numeroField.setText(String.valueOf(rs.getInt(1)));
                    }
                } catch (SQLException ex) {
                    JOptionPane.showMessageDialog(insertPartitaPanel, 
                            "Errore nel suggerimento: " + ex.getMessage(), 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                }
            }
        });
        
        gbc.gridy = 6;
        formPanel.add(suggestButton, gbc);
        
        // Aggiornamento delle combo
        JButton refreshButton = new JButton("Aggiorna Dati");
        refreshButton.addActionListener(e -> {
            loadComuniCombo(comuneCombo);
            String selectedComune = (String) comuneCombo.getSelectedItem();
            if (selectedComune != null) {
                loadPossessoriCombo(possessoreCombo, selectedComune);
            }
        });
        
        gbc.gridy = 7;
        formPanel.add(refreshButton, gbc);
        
        // Listener per aggiornare i possessori quando cambia il comune
        comuneCombo.addActionListener(e -> {
            String selectedComune = (String) comuneCombo.getSelectedItem();
            if (selectedComune != null) {
                loadPossessoriCombo(possessoreCombo, selectedComune);
            }
        });
        
        insertPartitaPanel.add(formPanel, BorderLayout.CENTER);
    }
    
    /**
     * Crea il pannello per la generazione di certificati di proprietà
     */
    private void createCertificatoPanel() {
        certificatoPanel = new JPanel(new BorderLayout());
        certificatoPanel.setBorder(new EmptyBorder(20, 20, 20, 20));
        
        JLabel titleLabel = new JLabel("Generazione Certificato di Proprietà", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        
        JLabel partitaLabel = new JLabel("ID Partita:");
        JTextField partitaField = new JTextField(10);
        
        JButton generateButton = new JButton("Genera Certificato");
        
        JTextArea certificatoArea = new JTextArea(20, 50);
        certificatoArea.setEditable(false);
        certificatoArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane scrollPane = new JScrollPane(certificatoArea);
        
        generateButton.addActionListener(e -> {
            String partitaId = partitaField.getText();
            if (partitaId.isEmpty()) {
                JOptionPane.showMessageDialog(certificatoPanel, 
                        "Inserire l'ID della partita.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                return;
            }
            
            try {
                CallableStatement cstmt = conn.prepareCall("SELECT genera_certificato_proprieta(?);");
                cstmt.setInt(1, Integer.parseInt(partitaId));
                ResultSet rs = cstmt.executeQuery();
                
                if (rs.next()) {
                    String certificato = rs.getString(1);
                    certificatoArea.setText(certificato);
                }
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(certificatoPanel, 
                        "L'ID deve essere un numero intero.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(certificatoPanel, 
                        "Errore nella generazione: " + ex.getMessage(), 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        // Aggiunta pulsante di stampa
        JButton printButton = new JButton("Stampa");
        printButton.addActionListener(e -> {
            try {
                certificatoArea.print();
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(certificatoPanel, 
                        "Errore nella stampa: " + ex.getMessage(), 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        // Pulsante di ricerca partita
        JButton searchPartitaButton = new JButton("Cerca");
        searchPartitaButton.addActionListener(e -> {
            // Mostra dialog per selezionare una partita
            JDialog dialog = new JDialog(this, "Seleziona Partita", true);
            dialog.setLayout(new BorderLayout());
            dialog.setSize(500, 400);
            dialog.setLocationRelativeTo(this);
            
            String[] columnNames = {"ID", "Comune", "Numero", "Tipo"};
            DefaultTableModel model = new DefaultTableModel(columnNames, 0);
            JTable table = new JTable(model);
            JScrollPane scrollPane2 = new JScrollPane(table);
            
            JPanel searchPanel = new JPanel();
            JTextField searchField = new JTextField(15);
            JButton searchBtn = new JButton("Cerca");
            searchPanel.add(new JLabel("Comune:"));
            searchPanel.add(searchField);
            searchPanel.add(searchBtn);
            
            JPanel buttonPanel = new JPanel();
            JButton selectBtn = new JButton("Seleziona");
            JButton cancelBtn = new JButton("Annulla");
            buttonPanel.add(selectBtn);
            buttonPanel.add(cancelBtn);
            
            searchBtn.addActionListener(e1 -> {
                String searchTerm = searchField.getText();
                loadPartiteForSelection(model, searchTerm);
            });
            
            selectBtn.addActionListener(e1 -> {
                int selectedRow = table.getSelectedRow();
                if (selectedRow >= 0) {
                    partitaField.setText(model.getValueAt(selectedRow, 0).toString());
                    dialog.dispose();
                } else {
                    JOptionPane.showMessageDialog(dialog, 
                            "Seleziona una partita dalla tabella.", 
                            "Avviso", JOptionPane.WARNING_MESSAGE);
                }
            });
            
            cancelBtn.addActionListener(e1 -> dialog.dispose());
            
            dialog.add(searchPanel, BorderLayout.NORTH);
            dialog.add(scrollPane2, BorderLayout.CENTER);
            dialog.add(buttonPanel, BorderLayout.SOUTH);
            
            // Carica alcune partite iniziali
            loadPartiteForSelection(model, "");
            
            dialog.setVisible(true);
        });
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 3;
        formPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        formPanel.add(partitaLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(partitaField, gbc);
        gbc.gridx = 2;
        formPanel.add(searchPartitaButton, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        gbc.gridwidth = 2;
        formPanel.add(generateButton, gbc);
        gbc.gridx = 2;
        gbc.gridwidth = 1;
        formPanel.add(printButton, gbc);
        
        certificatoPanel.add(formPanel, BorderLayout.NORTH);
        certificatoPanel.add(scrollPane, BorderLayout.CENTER);
    }
    
    /**
     * Crea il pannello per la ricerca di possessori
     */
    private void createRicercaPossessoriPanel() {
        ricercaPossessoriPanel = new JPanel(new BorderLayout());
        ricercaPossessoriPanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JLabel titleLabel = new JLabel("Ricerca Possessori", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JPanel searchPanel = new JPanel(new FlowLayout(FlowLayout.CENTER));
        JLabel searchLabel = new JLabel("Nome da cercare:");
        JTextField searchField = new JTextField(20);
        JButton searchButton = new JButton("Cerca");
        
        searchPanel.add(searchLabel);
        searchPanel.add(searchField);
        searchPanel.add(searchButton);
        
        // Tabella per i risultati
        String[] columnNames = {"ID", "Nome Completo", "Comune", "Num Partite"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        searchButton.addActionListener(e -> {
            String searchTerm = searchField.getText();
            if (searchTerm.isEmpty()) {
                JOptionPane.showMessageDialog(ricercaPossessoriPanel, 
                        "Inserire un termine di ricerca.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                return;
            }
            
            try {
                // Pulisci la tabella
                model.setRowCount(0);
                
                PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM cerca_possessori(?);");
                pstmt.setString(1, searchTerm);
                ResultSet rs = pstmt.executeQuery();
                
                while (rs.next()) {
                    int id = rs.getInt("id");
                    String nome = rs.getString("nome_completo");
                    String comune = rs.getString("comune_nome");
                    int numPartite = rs.getInt("num_partite");
                    
                    model.addRow(new Object[]{id, nome, comune, numPartite});
                }
                
                if (model.getRowCount() == 0) {
                    JOptionPane.showMessageDialog(ricercaPossessoriPanel, 
                            "Nessun possessore trovato.", 
                            "Informazione", JOptionPane.INFORMATION_MESSAGE);
                }
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(ricercaPossessoriPanel, 
                        "Errore nella ricerca: " + ex.getMessage(), 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        // Aggiunti pulsanti per azioni sui risultati
        JPanel buttonPanel = new JPanel();
        JButton viewDetailsButton = new JButton("Visualizza Dettagli");
        JButton updateButton = new JButton("Aggiorna Possessore");
        
        viewDetailsButton.addActionListener(e -> {
            int selectedRow = table.getSelectedRow();
            if (selectedRow >= 0) {
                int possessoreId = (int) model.getValueAt(selectedRow, 0);
                showPossessoreDetails(possessoreId);
            } else {
                JOptionPane.showMessageDialog(ricercaPossessoriPanel, 
                        "Seleziona un possessore.", 
                        "Avviso", JOptionPane.WARNING_MESSAGE);
            }
        });
        
        updateButton.addActionListener(e -> {
            int selectedRow = table.getSelectedRow();
            if (selectedRow >= 0) {
                int possessoreId = (int) model.getValueAt(selectedRow, 0);
                showUpdatePossessore(possessoreId);
            } else {
                JOptionPane.showMessageDialog(ricercaPossessoriPanel, 
                        "Seleziona un possessore.", 
                        "Avviso", JOptionPane.WARNING_MESSAGE);
            }
        });
        
        buttonPanel.add(viewDetailsButton);
        buttonPanel.add(updateButton);
        
        JPanel southPanel = new JPanel(new BorderLayout());
        southPanel.add(buttonPanel, BorderLayout.NORTH);
        
        ricercaPossessoriPanel.add(titleLabel, BorderLayout.NORTH);
        ricercaPossessoriPanel.add(searchPanel, BorderLayout.CENTER);
        ricercaPossessoriPanel.add(scrollPane, BorderLayout.SOUTH);
        ricercaPossessoriPanel.add(southPanel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per la ricerca di immobili
     */
    private void createRicercaImmobiliPanel() {
        ricercaImmobiliPanel = new JPanel(new BorderLayout());
        ricercaImmobiliPanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JLabel titleLabel = new JLabel("Ricerca Immobili", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JPanel searchPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        
        JLabel comuneLabel = new JLabel("Comune:");
        JComboBox<String> comuneCombo = new JComboBox<>();
        comuneCombo.addItem(""); // Opzione vuota
        
        JLabel naturaLabel = new JLabel("Natura:");
        JTextField naturaField = new JTextField(20);
        
        JButton searchButton = new JButton("Cerca");
        
        // Tabella per i risultati
        String[] columnNames = {"ID", "Natura", "Località", "Comune", "Partita"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        searchButton.addActionListener(e -> {
            String comune = (String) comuneCombo.getSelectedItem();
            String natura = naturaField.getText();
            
            if (comune != null && comune.isEmpty()) comune = null;
            if (natura.isEmpty()) natura = null;
            
            if (comune == null && natura == null) {
                JOptionPane.showMessageDialog(ricercaImmobiliPanel, 
                        "Inserire almeno un criterio di ricerca.", 
                        "Avviso", JOptionPane.WARNING_MESSAGE);
            }
            
            try {
                // Pulisci la tabella
                model.setRowCount(0);
                
                PreparedStatement pstmt = conn.prepareStatement(
                        "SELECT * FROM cerca_immobili(NULL, ?, NULL, ?, NULL);");
                pstmt.setString(1, comune);
                pstmt.setString(2, natura);
                ResultSet rs = pstmt.executeQuery();
                
                while (rs.next()) {
                    int id = rs.getInt("id");
                    String immobileNatura = rs.getString("natura");
                    String localita = rs.getString("localita_nome");
                    String immobileComune = rs.getString("comune");
                    int partita = rs.getInt("numero_partita");
                    
                    model.addRow(new Object[]{id, immobileNatura, localita, immobileComune, partita});
                }
                
                if (model.getRowCount() == 0) {
                    JOptionPane.showMessageDialog(ricercaImmobiliPanel, 
                            "Nessun immobile trovato.", 
                            "Informazione", JOptionPane.INFORMATION_MESSAGE);
                }
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(ricercaImmobiliPanel, 
                        "Errore nella ricerca: " + ex.getMessage(), 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        // Aggiornamento della combo dei comuni
        JButton refreshButton = new JButton("Aggiorna Comuni");
        refreshButton.addActionListener(e -> loadComuniCombo(comuneCombo));
        
        // Pulsante per visualizzare dettagli
        JButton viewDetailsButton = new JButton("Visualizza Dettagli");
        viewDetailsButton.addActionListener(e -> {
            int selectedRow = table.getSelectedRow();
            if (selectedRow >= 0) {
                int immobileId = (int) model.getValueAt(selectedRow, 0);
                showImmobileDetails(immobileId);
            } else {
                JOptionPane.showMessageDialog(ricercaImmobiliPanel, 
                        "Seleziona un immobile.", 
                        "Avviso", JOptionPane.WARNING_MESSAGE);
            }
        });
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 2;
        searchPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        searchPanel.add(comuneLabel, gbc);
        gbc.gridx = 1;
        searchPanel.add(comuneCombo, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        searchPanel.add(naturaLabel, gbc);
        gbc.gridx = 1;
        searchPanel.add(naturaField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 3;
        searchPanel.add(searchButton, gbc);
        gbc.gridx = 1;
        searchPanel.add(refreshButton, gbc);
        
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(viewDetailsButton);
        
        ricercaImmobiliPanel.add(searchPanel, BorderLayout.NORTH);
        ricercaImmobiliPanel.add(scrollPane, BorderLayout.CENTER);
        ricercaImmobiliPanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per l'aggiornamento di un possessore
     */
    private void createUpdatePossessorePanel() {
        updatePossessorePanel = new JPanel(new BorderLayout());
        updatePossessorePanel.setBorder(new EmptyBorder(20, 20, 20, 20));
        
        JLabel titleLabel = new JLabel("Aggiornamento Possessore", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        
        JLabel idLabel = new JLabel("ID Possessore:");
        JTextField idField = new JTextField(10);
        
        JButton searchButton = new JButton("Cerca");
        
        JLabel nomeLabel = new JLabel("Nome Completo:");
        JTextField nomeField = new JTextField(20);
        nomeField.setEditable(false);
        
        JLabel comuneLabel = new JLabel("Comune:");
        JTextField comuneField = new JTextField(20);
        comuneField.setEditable(false);
        
        JLabel statoLabel = new JLabel("Stato:");
        String[] stati = {"attivo", "non attivo"};
        JComboBox<String> statoCombo = new JComboBox<>(stati);
        
        JButton updateButton = new JButton("Aggiorna");
        
        searchButton.addActionListener(e -> {
            String idText = idField.getText();
            if (idText.isEmpty()) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "Inserire l'ID del possessore.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                return;
            }
            
            try {
                int id = Integer.parseInt(idText);
                
                PreparedStatement pstmt = conn.prepareStatement(
                        "SELECT id, nome_completo, comune_nome, attivo FROM possessore WHERE id = ?;");
                pstmt.setInt(1, id);
                ResultSet rs = pstmt.executeQuery();
                
                if (rs.next()) {
                    nomeField.setText(rs.getString("nome_completo"));
                    comuneField.setText(rs.getString("comune_nome"));
                    boolean attivo = rs.getBoolean("attivo");
                    statoCombo.setSelectedItem(attivo ? "attivo" : "non attivo");
                } else {
                    JOptionPane.showMessageDialog(updatePossessorePanel, 
                            "Nessun possessore trovato con ID " + id, 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                    nomeField.setText("");
                    comuneField.setText("");
                }
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "L'ID deve essere un numero intero.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "Errore nella ricerca: " + ex.getMessage(), 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        updateButton.addActionListener(e -> {
            String idText = idField.getText();
            if (idText.isEmpty() || nomeField.getText().isEmpty()) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "Cercare prima un possessore valido.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                return;
            }
            
            try {
                int id = Integer.parseInt(idText);
                boolean attivo = statoCombo.getSelectedItem().equals("attivo");
                
                PreparedStatement pstmt = conn.prepareStatement(
                        "UPDATE possessore SET attivo = ? WHERE id = ?;");
                pstmt.setBoolean(1, attivo);
                pstmt.setInt(2, id);
                int rows = pstmt.executeUpdate();
                
                if (rows > 0) {
                    JOptionPane.showMessageDialog(updatePossessorePanel, 
                            "Possessore aggiornato con successo!", 
                            "Successo", JOptionPane.INFORMATION_MESSAGE);
                } else {
                    JOptionPane.showMessageDialog(updatePossessorePanel, 
                            "Nessun possessore aggiornato.", 
                            "Avviso", JOptionPane.WARNING_MESSAGE);
                }
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "L'ID deve essere un numero intero.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "Errore nell'aggiornamento: " + ex.getMessage(), 
                        "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        // Pulsante per cercare possessori
        JButton findButton = new JButton("Trova");
        findButton.addActionListener(e -> {
            // Mostra dialog per selezionare un possessore
            JDialog dialog = new JDialog(this, "Seleziona Possessore", true);
            dialog.setLayout(new BorderLayout());
            dialog.setSize(500, 400);
            dialog.setLocationRelativeTo(this);
            
            String[] columnNames = {"ID", "Nome Completo", "Comune", "Stato"};
            DefaultTableModel model = new DefaultTableModel(columnNames, 0);
            JTable table = new JTable(model);
            JScrollPane scrollPane = new JScrollPane(table);
            
            JPanel searchPanel = new JPanel();
            JTextField searchField = new JTextField(15);
            JButton searchBtn = new JButton("Cerca");
            searchPanel.add(new JLabel("Nome:"));
            searchPanel.add(searchField);
            searchPanel.add(searchBtn);
            
            JPanel buttonPanel = new JPanel();
            JButton selectBtn = new JButton("Seleziona");
            JButton cancelBtn = new JButton("Annulla");
            buttonPanel.add(selectBtn);
            buttonPanel.add(cancelBtn);
            
            searchBtn.addActionListener(e1 -> {
                String searchTerm = searchField.getText();
                loadPossessoriForSelection(model, searchTerm);
            });
            
            selectBtn.addActionListener(e1 -> {
                int selectedRow = table.getSelectedRow();
                if (selectedRow >= 0) {
                    idField.setText(model.getValueAt(selectedRow, 0).toString());
                    
                    // Trigger la ricerca
                    searchButton.doClick();
                    
                    dialog.dispose();
                } else {
                    JOptionPane.showMessageDialog(dialog, 
                            "Seleziona un possessore dalla tabella.", 
                            "Avviso", JOptionPane.WARNING_MESSAGE);
                }
            });
            
            cancelBtn.addActionListener(e1 -> dialog.dispose());
            
            dialog.add(searchPanel, BorderLayout.NORTH);
            dialog.add(scrollPane, BorderLayout.CENTER);
            dialog.add(buttonPanel, BorderLayout.SOUTH);
            
            // Carica alcuni possessori iniziali
            loadPossessoriForSelection(model, "");
            
            dialog.setVisible(true);
        });
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 3;
        formPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        formPanel.add(idLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(idField, gbc);
        
        gbc.gridx = 2;
        formPanel.add(searchButton, gbc);
        
        gbc.gridx = 3;
        formPanel.add(findButton, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        formPanel.add(nomeLabel, gbc);
        gbc.gridx = 1;
        gbc.gridwidth = 3;
        formPanel.add(nomeField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 3;
        gbc.gridwidth = 1;
        formPanel.add(comuneLabel, gbc);
        gbc.gridx = 1;
        gbc.gridwidth = 3;
        formPanel.add(comuneField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 4;
        gbc.gridwidth = 1;
        formPanel.add(statoLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(statoCombo, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 5;
        gbc.gridwidth = 4;
        gbc.anchor = GridBagConstraints.CENTER;
        formPanel.add(updateButton, gbc);
        
        updatePossessorePanel.add(formPanel, BorderLayout.NORTH);
        
        // Aggiunto pannello per visualizzare partite del possessore
        JPanel partitePanel = new JPanel(new BorderLayout());
        partitePanel.setBorder(BorderFactory.createTitledBorder("Partite del Possessore"));
        
        String[] columnNames = {"ID", "Comune", "Numero", "Tipo", "Stato"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        JButton loadPartiteButton = new JButton("Carica Partite");
        loadPartiteButton.addActionListener(e -> {
            String idText = idField.getText();
            if (idText.isEmpty() || nomeField.getText().isEmpty()) {
                JOptionPane.showMessageDialog(updatePossessorePanel, 
                        "Cercare prima un possessore valido.", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                return;
            }
            
            try {
                int id = Integer.parseInt(idText);
                loadPart
        });
    }
    
    /**
     * Crea il pannello di login
     */
    private void createLoginPanel() {
        loginPanel = new JPanel(new BorderLayout());
        loginPanel.setBorder(new EmptyBorder(20, 20, 20, 20));
        
        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        
        JLabel titleLabel = new JLabel("Connessione al database catasto_storico", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JLabel userLabel = new JLabel("Utente:");
        JTextField userField = new JTextField("postgres", 20);
        
        JLabel passwordLabel = new JLabel("Password:");
        JPasswordField passwordField = new JPasswordField(20);
        
        JLabel hostLabel = new JLabel("Host:");
        JTextField hostField = new JTextField("localhost", 20);
        
        JLabel portLabel = new JLabel("Porta:");
        JTextField portField = new JTextField("5432", 20);
        
        JButton connectButton = new JButton("Connetti");
        connectButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String user = userField.getText();
                String password = new String(passwordField.getPassword());
                String host = hostField.getText();
                String port = portField.getText();
                
                if (connect(user, password, host, port)) {
                    cardLayout.show(mainPanel, "menu");
                    setTitle("Catasto Storico - Connesso");
                    statusLabel.setText("Connesso a: catasto_storico@" + host + ":" + port);
                }
            }
        });
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 2;
        formPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        formPanel.add(userLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(userField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        formPanel.add(passwordLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(passwordField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 3;
        formPanel.add(hostLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(hostField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 4;
        formPanel.add(portLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(portField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 5;
        gbc.gridwidth = 2;
        gbc.anchor = GridBagConstraints.CENTER;
        formPanel.add(connectButton, gbc);
        
        // Aggiunto logo o immagine al pannello di login
        JLabel logoLabel = new JLabel(new ImageIcon("catasto_logo.png"));
        logoLabel.setHorizontalAlignment(JLabel.CENTER);
        loginPanel.add(logoLabel, BorderLayout.NORTH);
        
        loginPanel.add(formPanel, BorderLayout.CENTER);
    }
    
    /**
     * Crea il pannello del menu principale
     */
    private void createMenuPanel() {
        menuPanel = new JPanel(new BorderLayout());
        
        // Creazione della barra dei menu
        JMenuBar menuBar = new JMenuBar();
        
        // Menu File
        JMenu fileMenu = new JMenu("File");
        JMenuItem disconnectItem = new JMenuItem("Disconnetti");
        JMenuItem exitItem = new JMenuItem("Esci");
        
        disconnectItem.addActionListener(e -> {
            disconnect();
            cardLayout.show(mainPanel, "login");
            setTitle("Catasto Storico");
            statusLabel.setText("Non connesso");
        });
        
        exitItem.addActionListener(e -> {
            disconnect();
            System.exit(0);
        });
        
        fileMenu.add(disconnectItem);
        fileMenu.addSeparator();
        fileMenu.add(exitItem);
        
        // Menu Visualizza
        JMenu viewMenu = new JMenu("Visualizza");
        JMenuItem comuniItem = new JMenuItem("Comuni");
        JMenuItem partiteItem = new JMenuItem("Partite");
        JMenuItem possessoriItem = new JMenuItem("Possessori");
        JMenuItem immobiliItem = new JMenuItem("Immobili");
        
        comuniItem.addActionListener(e -> showComuni());
        partiteItem.addActionListener(e -> showPartite());
        possessoriItem.addActionListener(e -> showPossessori());
        immobiliItem.addActionListener(e -> showImmobili());
        
        viewMenu.add(comuniItem);
        viewMenu.add(partiteItem);
        viewMenu.add(possessoriItem);
        viewMenu.add(immobiliItem);
        
        // Menu Inserisci
        JMenu insertMenu = new JMenu("Inserisci");
        JMenuItem insertPossessoreItem = new JMenuItem("Nuovo Possessore");
        JMenuItem insertPartitaItem = new JMenuItem("Nuova Partita");
        
        insertPossessoreItem.addActionListener(e -> showInsertPossessore());
        insertPartitaItem.addActionListener(e -> showInsertPartita());
        
        insertMenu.add(insertPossessoreItem);
        insertMenu.add(insertPartitaItem);
        
        // Menu Ricerca
        JMenu searchMenu = new JMenu("Ricerca");
        JMenuItem searchPossessoriItem = new JMenuItem("Cerca Possessori");
        JMenuItem searchImmobiliItem = new JMenuItem("Cerca Immobili");
        
        searchPossessoriItem.addActionListener(e -> showRicercaPossessori());
        searchImmobiliItem.addActionListener(e -> showRicercaImmobili());
        
        searchMenu.add(searchPossessoriItem);
        searchMenu.add(searchImmobiliItem);
        
        // Menu Strumenti
        JMenu toolsMenu = new JMenu("Strumenti");
        JMenuItem certificatoItem = new JMenuItem("Genera Certificato");
        JMenuItem updatePossessoreItem = new JMenuItem("Aggiorna Possessore");
        
        certificatoItem.addActionListener(e -> showCertificatoPanel());
        updatePossessoreItem.addActionListener(e -> showUpdatePossessore());
        
        toolsMenu.add(certificatoItem);
        toolsMenu.add(updatePossessoreItem);
        
        // Menu Aiuto
        JMenu helpMenu = new JMenu("Aiuto");
        JMenuItem aboutItem = new JMenuItem("Informazioni");
        
        aboutItem.addActionListener(e -> {
            JOptionPane.showMessageDialog(this,
                    "Applicazione Catasto Storico\nVersione 1.0\n\nSviluppata per la gestione del database catasto_storico",
                    "Informazioni",
                    JOptionPane.INFORMATION_MESSAGE);
        });
        
        helpMenu.add(aboutItem);
        
        // Aggiunta dei menu alla barra dei menu
        menuBar.add(fileMenu);
        menuBar.add(viewMenu);
        menuBar.add(insertMenu);
        menuBar.add(searchMenu);
        menuBar.add(toolsMenu);
        menuBar.add(helpMenu);
        
        // Aggiunta della barra dei menu e del pannello di contenuto
        menuPanel.add(menuBar, BorderLayout.NORTH);
        
        // Creazione del pannello di contenuto
        contentPanel = new JPanel(new CardLayout());
        createContentPanels();
        menuPanel.add(contentPanel, BorderLayout.CENTER);
    }
    
    /**
     * Crea il pannello principale di contenuto
     */
    private void createContentPanel() {
        contentPanel = new JPanel(new CardLayout());
        JPanel welcomePanel = new JPanel(new BorderLayout());
        
        JLabel welcomeLabel = new JLabel("Benvenuto nel Sistema Catasto Storico", JLabel.CENTER);
        welcomeLabel.setFont(new Font("Arial", Font.BOLD, 24));
        welcomePanel.add(welcomeLabel, BorderLayout.CENTER);
        
        contentPanel.add(welcomePanel, "welcome");
    }
    
    /**
     * Crea tutti i pannelli di contenuto per le diverse funzionalità
     */
    private void createContentPanels() {
        // Creazione dei pannelli per le diverse funzionalità
        createComuniPanel();
        createPartitePanel();
        createPossessoriPanel();
        createImmobiliPanel();
        createInsertPossessorePanel();
        createInsertPartitaPanel();
        createCertificatoPanel();
        createRicercaPossessoriPanel();
        createRicercaImmobiliPanel();
        createUpdatePossessorePanel();
        
        // Aggiunta dei pannelli al contenitore
        JPanel welcomePanel = new JPanel(new BorderLayout());
        JLabel welcomeLabel = new JLabel("Benvenuto nel Sistema Catasto Storico", JLabel.CENTER);
        welcomeLabel.setFont(new Font("Arial", Font.BOLD, 24));
        
        // Aggiunta di un'immagine o descrizione nella pagina di benvenuto
        JTextArea welcomeText = new JTextArea(
                "Questo sistema permette di gestire i dati del catasto storico degli anni '50.\n\n" +
                "Utilizza il menu in alto per navigare tra le diverse funzionalità:\n" +
                "- Visualizza i dati di comuni, partite, possessori e immobili\n" +
                "- Inserisci nuovi possessori e partite\n" +
                "- Ricerca possessori e immobili\n" +
                "- Genera certificati di proprietà e aggiorna dati\n\n" +
                "Per iniziare, seleziona una delle opzioni dal menu."
        );
        welcomeText.setEditable(false);
        welcomeText.setLineWrap(true);
        welcomeText.setWrapStyleWord(true);
        welcomeText.setBackground(welcomePanel.getBackground());
        welcomeText.setFont(new Font("Arial", Font.PLAIN, 14));
        welcomeText.setBorder(new EmptyBorder(20, 40, 20, 40));
        
        welcomePanel.add(welcomeLabel, BorderLayout.NORTH);
        welcomePanel.add(welcomeText, BorderLayout.CENTER);
        
        contentPanel.add(welcomePanel, "welcome");
        contentPanel.add(comuniPanel, "comuni");
        contentPanel.add(partitePanel, "partite");
        contentPanel.add(possessoriPanel, "possessori");
        contentPanel.add(immobiliPanel, "immobili");
        contentPanel.add(insertPossessorePanel, "insertPossessore");
        contentPanel.add(insertPartitaPanel, "insertPartita");
        contentPanel.add(certificatoPanel, "certificato");
        contentPanel.add(ricercaPossessoriPanel, "ricercaPossessori");
        contentPanel.add(ricercaImmobiliPanel, "ricercaImmobili");
        contentPanel.add(updatePossessorePanel, "updatePossessore");
        
        ((CardLayout) contentPanel.getLayout()).show(contentPanel, "welcome");
    }
    
    /**
     * Crea la barra di stato
     */
    private void createStatusBar() {
        statusLabel = new JLabel("Non connesso");
        statusLabel.setBorder(BorderFactory.createLoweredBevelBorder());
        add(statusLabel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per la visualizzazione dei comuni
     */
    private void createComuniPanel() {
        comuniPanel = new JPanel(new BorderLayout());
        comuniPanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JLabel titleLabel = new JLabel("Elenco Comuni", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        // Tabella per i dati
        String[] columnNames = {"Nome", "Provincia", "Regione"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        // Pulsante di aggiornamento
        JButton refreshButton = new JButton("Aggiorna");
        refreshButton.addActionListener(e -> loadComuniData(model));
        
        // Pannello dei pulsanti
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(refreshButton);
        
        // Aggiunta dei componenti al pannello
        comuniPanel.add(titleLabel, BorderLayout.NORTH);
        comuniPanel.add(scrollPane, BorderLayout.CENTER);
        comuniPanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per la visualizzazione delle partite
     */
    private void createPartitePanel() {
        partitePanel = new JPanel(new BorderLayout());
        partitePanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JLabel titleLabel = new JLabel("Elenco Partite", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        // Tabella per i dati
        String[] columnNames = {"ID", "Comune", "Numero", "Tipo", "Stato", "Possessori"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        // Pulsanti
        JButton refreshButton = new JButton("Aggiorna");
        refreshButton.addActionListener(e -> loadPartiteData(model));
        
        JButton viewDetailsButton = new JButton("Visualizza Dettagli");
        viewDetailsButton.addActionListener(e -> {
            int selectedRow = table.getSelectedRow();
            if (selectedRow >= 0) {
                int partitaId = (int) model.getValueAt(selectedRow, 0);
                showPartitaDetails(partitaId);
            } else {
                JOptionPane.showMessageDialog(partitePanel, 
                        "Seleziona una partita.", 
                        "Avviso", JOptionPane.WARNING_MESSAGE);
            }
        });
        
        // Pannello dei pulsanti
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(refreshButton);
        buttonPanel.add(viewDetailsButton);
        
        // Aggiunta dei componenti al pannello
        partitePanel.add(titleLabel, BorderLayout.NORTH);
        partitePanel.add(scrollPane, BorderLayout.CENTER);
        partitePanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per la visualizzazione dei possessori
     */
    private void createPossessoriPanel() {
        possessoriPanel = new JPanel(new BorderLayout());
        possessoriPanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JLabel titleLabel = new JLabel("Elenco Possessori", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        // Tabella per i dati
        String[] columnNames = {"ID", "Nome Completo", "Comune", "Stato"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        // Pulsanti
        JButton refreshButton = new JButton("Aggiorna");
        refreshButton.addActionListener(e -> loadPossessoriData(model));
        
        JButton updateButton = new JButton("Aggiorna Possessore");
        updateButton.addActionListener(e -> {
            int selectedRow = table.getSelectedRow();
            if (selectedRow >= 0) {
                int possessoreId = (int) model.getValueAt(selectedRow, 0);
                showUpdatePossessore(possessoreId);
            } else {
                JOptionPane.showMessageDialog(possessoriPanel, 
                        "Seleziona un possessore.", 
                        "Avviso", JOptionPane.WARNING_MESSAGE);
            }
        });
        
        // Pannello dei pulsanti
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(refreshButton);
        buttonPanel.add(updateButton);
        
        // Aggiunta dei componenti al pannello
        possessoriPanel.add(titleLabel, BorderLayout.NORTH);
        possessoriPanel.add(scrollPane, BorderLayout.CENTER);
        possessoriPanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per la visualizzazione degli immobili
     */
    private void createImmobiliPanel() {
        immobiliPanel = new JPanel(new BorderLayout());
        immobiliPanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JLabel titleLabel = new JLabel("Elenco Immobili", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        // Tabella per i dati
        String[] columnNames = {"ID", "Natura", "Località", "Partita", "Comune"};
        DefaultTableModel model = new DefaultTableModel(columnNames, 0);
        JTable table = new JTable(model);
        JScrollPane scrollPane = new JScrollPane(table);
        
        // Pulsante di aggiornamento
        JButton refreshButton = new JButton("Aggiorna");
        refreshButton.addActionListener(e -> loadImmobiliData(model));
        
        // Pannello dei pulsanti
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(refreshButton);
        
        // Aggiunta dei componenti al pannello
        immobiliPanel.add(titleLabel, BorderLayout.NORTH);
        immobiliPanel.add(scrollPane, BorderLayout.CENTER);
        immobiliPanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
    /**
     * Crea il pannello per l'inserimento di un nuovo possessore
     */
    private void createInsertPossessorePanel() {
        insertPossessorePanel = new JPanel(new BorderLayout());
        insertPossessorePanel.setBorder(new EmptyBorder(20, 20, 20, 20));
        
        JLabel titleLabel = new JLabel("Inserimento Nuovo Possessore", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        
        JLabel comuneLabel = new JLabel("Comune:");
        JComboBox<String> comuneCombo = new JComboBox<>();
        
        JLabel cognomeNomeLabel = new JLabel("Cognome e Nome:");
        JTextField cognomeNomeField = new JTextField(20);
        
        JLabel paternitaLabel = new JLabel("Paternità:");
        JTextField paternitaField = new JTextField(20);
        
        JButton insertButton = new JButton("Inserisci");
        insertButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String comune = (String) comuneCombo.getSelectedItem();
                String cognomeNome = cognomeNomeField.getText();
                String paternita = paternitaField.getText();
                String nomeCompleto = cognomeNome + " " + paternita;
                
                if (comune == null || cognomeNome.isEmpty()) {
                    JOptionPane.showMessageDialog(insertPossessorePanel, 
                            "Comune e Cognome/Nome sono campi obbligatori.", 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                try {
                    CallableStatement cstmt = conn.prepareCall("CALL inserisci_possessore(?, ?, ?, ?, ?);");
                    cstmt.setString(1, comune);
                    cstmt.setString(2, cognomeNome);
                    cstmt.setString(3, paternita);
                    cstmt.setString(4, nomeCompleto);
                    cstmt.setBoolean(5, true);
                    cstmt.execute();
                    
                    JOptionPane.showMessageDialog(insertPossessorePanel, 
                            "Possessore inserito con successo!", 
                            "Successo", JOptionPane.INFORMATION_MESSAGE);
                    
                    // Reset dei campi
                    cognomeNomeField.setText("");
                    paternitaField.setText("");
                } catch (SQLException ex) {
                    JOptionPane.showMessageDialog(insertPossessorePanel, 
                            "Errore nell'inserimento: " + ex.getMessage(), 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                }
            }
        });
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 2;
        formPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        formPanel.add(comuneLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(comuneCombo, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        formPanel.add(cognomeNomeLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(cognomeNomeField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 3;
        formPanel.add(paternitaLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(paternitaField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 4;
        gbc.gridwidth = 2;
        gbc.anchor = GridBagConstraints.CENTER;
        formPanel.add(insertButton, gbc);
        
        // Aggiornamento della combo dei comuni
        JButton refreshButton = new JButton("Aggiorna Comuni");
        refreshButton.addActionListener(e -> loadComuniCombo(comuneCombo));
        
        gbc.gridy = 5;
        formPanel.add(refreshButton, gbc);
        
        insertPossessorePanel.add(formPanel, BorderLayout.CENTER);
    }
    
    /**
     * Crea il pannello per l'inserimento di una nuova partita
     */
    private void createInsertPartitaPanel() {
        insertPartitaPanel = new JPanel(new BorderLayout());
        insertPartitaPanel.setBorder(new EmptyBorder(20, 20, 20, 20));
        
        JLabel titleLabel = new JLabel("Inserimento Nuova Partita", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        
        JPanel formPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        
        JLabel comuneLabel = new JLabel("Comune:");
        JComboBox<String> comuneCombo = new JComboBox<>();
        
        JLabel numeroLabel = new JLabel("Numero Partita:");
        JTextField numeroField = new JTextField(10);
        
        JLabel tipoLabel = new JLabel("Tipo:");
        String[] tipi = {"principale", "secondaria"};
        JComboBox<String> tipoCombo = new JComboBox<>(tipi);
        
        JLabel possessoreLabel = new JLabel("Possessore:");
        JComboBox<ComboItem> possessoreCombo = new JComboBox<>();
        
        JButton insertButton = new JButton("Inserisci");
        insertButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String comune = (String) comuneCombo.getSelectedItem();
                String numeroText = numeroField.getText();
                String tipo = (String) tipoCombo.getSelectedItem();
                ComboItem possessore = (ComboItem) possessoreCombo.getSelectedItem();
                
                if (comune == null || numeroText.isEmpty() || possessore == null) {
                    JOptionPane.showMessageDialog(insertPartitaPanel, 
                            "Tutti i campi sono obbligatori.", 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                try {
                    int numero = Integer.parseInt(numeroText);
                    int possessoreId = possessore.getId();
                    Integer[] possessoreIds = new Integer[]{possessoreId};
                    
                    // Verifica che il numero partita non esista già
                    PreparedStatement checkStmt = conn.prepareStatement(
                            "SELECT 1 FROM partita WHERE comune_nome = ? AND numero_partita = ?;");
                    checkStmt.setString(1, comune);
                    checkStmt.setInt(2, numero);
                    ResultSet rs = checkStmt.executeQuery();
                    
                    if (rs.next()) {
                        JOptionPane.showMessageDialog(insertPartitaPanel, 
                                "La partita " + numero + " esiste già nel comune " + comune, 
                                "Errore", JOptionPane.ERROR_MESSAGE);
                        return;
                    }
                    
                    // Inserisci la partita
                    CallableStatement cstmt = conn.prepareCall(
                            "CALL inserisci_partita_con_possessori(?, ?, ?, ?, ?);");
                    cstmt.setString(1, comune);
                    cstmt.setInt(2, numero);
                    cstmt.setString(3, tipo);
                    cstmt.setDate(4, java.sql.Date.valueOf(LocalDate.now()));
                    
                    // Crea un array SQL dall'array Java
                    Array possessoreIdsArray = conn.createArrayOf("integer", possessoreIds);
                    cstmt.setArray(5, possessoreIdsArray);
                    
                    cstmt.execute();
                    
                    JOptionPane.showMessageDialog(insertPartitaPanel, 
                            "Partita inserita con successo!", 
                            "Successo", JOptionPane.INFORMATION_MESSAGE);
                    
                    // Reset dei campi
                    numeroField.setText("");
                    tipoCombo.setSelectedIndex(0);
                } catch (NumberFormatException ex) {
                    JOptionPane.showMessageDialog(insertPartitaPanel, 
                            "Il numero partita deve essere un numero intero.", 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                } catch (SQLException ex) {
                    JOptionPane.showMessageDialog(insertPartitaPanel, 
                            "Errore nell'inserimento: " + ex.getMessage(), 
                            "Errore", JOptionPane.ERROR_MESSAGE);
                }
            }