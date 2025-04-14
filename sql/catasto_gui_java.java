import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.sql.*;
import java.time.LocalDate;
import java.util.*;
import java.util.List;

public class CatastoGUI extends JFrame {
    private Connection conn;
    private boolean connected;
    
    // Componenti GUI principali
    private JPanel mainPanel;
    private JPanel menuPanel;
    private CardLayout cardLayout;
    private JPanel contentPanel;
    
    // Componenti di connessione
    private JTextField userField;
    private JPasswordField passwordField;
    private JTextField hostField;
    private JTextField portField;
    private JButton connectButton;
    
    // Menu buttons
    private List<JButton> menuButtons;
    
    public CatastoGUI() {
        super("Catasto Storico - Applicazione");
        connected = false;
        initializeGUI();
    }
    
    private void initializeGUI() {
        // Imposta il frame principale
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(900, 600);
        setLocationRelativeTo(null); // Centra la finestra
        
        // Crea i pannelli principali
        mainPanel = new JPanel(new BorderLayout());
        
        // Menu laterale
        menuPanel = new JPanel();
        menuPanel.setLayout(new BoxLayout(menuPanel, BoxLayout.Y_AXIS));
        menuPanel.setPreferredSize(new Dimension(200, getHeight()));
        menuPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        menuPanel.setBackground(new Color(240, 240, 240));
        
        // Pannello contenuto con CardLayout
        cardLayout = new CardLayout();
        contentPanel = new JPanel(cardLayout);
        
        // Aggiungi i pannelli al mainPanel
        mainPanel.add(menuPanel, BorderLayout.WEST);
        mainPanel.add(contentPanel, BorderLayout.CENTER);
        
        // Crea i pannelli per ogni schermata
        createLoginPanel();
        createMenuButtons();
        createTablePanels();
        createFormPanels();
        
        // Mostra solo il pannello di login inizialmente
        showLoginPanel();
        
        // Aggiungi il pannello principale al frame
        setContentPane(mainPanel);
    }
    
    private void createLoginPanel() {
        JPanel loginPanel = new JPanel();
        loginPanel.setLayout(new BoxLayout(loginPanel, BoxLayout.Y_AXIS));
        loginPanel.setBorder(BorderFactory.createEmptyBorder(30, 30, 30, 30));
        
        JLabel titleLabel = new JLabel("Connessione al database catasto_storico");
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        titleLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        
        JPanel formPanel = new JPanel(new GridLayout(4, 2, 5, 10));
        
        JLabel userLabel = new JLabel("Utente PostgreSQL:");
        userField = new JTextField("postgres", 20);
        
        JLabel passwordLabel = new JLabel("Password:");
        passwordField = new JPasswordField(20);
        
        JLabel hostLabel = new JLabel("Host:");
        hostField = new JTextField("localhost", 20);
        
        JLabel portLabel = new JLabel("Porta:");
        portField = new JTextField("5432", 20);
        
        formPanel.add(userLabel);
        formPanel.add(userField);
        formPanel.add(passwordLabel);
        formPanel.add(passwordField);
        formPanel.add(hostLabel);
        formPanel.add(hostField);
        formPanel.add(portLabel);
        formPanel.add(portField);
        
        connectButton = new JButton("Connetti");
        connectButton.setAlignmentX(Component.CENTER_ALIGNMENT);
        connectButton.addActionListener(e -> connectToDatabase());
        
        loginPanel.add(Box.createVerticalGlue());
        loginPanel.add(titleLabel);
        loginPanel.add(Box.createVerticalStrut(20));
        loginPanel.add(formPanel);
        loginPanel.add(Box.createVerticalStrut(20));
        loginPanel.add(connectButton);
        loginPanel.add(Box.createVerticalGlue());
        
        contentPanel.add(loginPanel, "login");
    }
    
    private void createMenuButtons() {
        menuButtons = new ArrayList<>();
        
        // Crea i pulsanti del menu
        String[] menuItems = {
            "Home", "Comuni", "Partite", "Possessori", "Immobili",
            "Nuovo Possessore", "Nuova Partita", "Certificato", "Ricerca"
        };
        
        for (String item : menuItems) {
            JButton button = new JButton(item);
            button.setMaximumSize(new Dimension(180, 40));
            button.setAlignmentX(Component.CENTER_ALIGNMENT);
            button.setFocusPainted(false);
            
            // Imposta l'azione per ogni pulsante
            button.addActionListener(e -> {
                String cmd = e.getActionCommand();
                switch (cmd) {
                    case "Home":
                        cardLayout.show(contentPanel, "home");
                        break;
                    case "Comuni":
                        mostraComuni();
                        cardLayout.show(contentPanel, "comuni");
                        break;
                    case "Partite":
                        mostraPartite();
                        cardLayout.show(contentPanel, "partite");
                        break;
                    case "Possessori":
                        mostraPossessori();
                        cardLayout.show(contentPanel, "possessori");
                        break;
                    case "Immobili":
                        mostraImmobili();
                        cardLayout.show(contentPanel, "immobili");
                        break;
                    case "Nuovo Possessore":
                        aggiornaComboBoxComuni();
                        cardLayout.show(contentPanel, "nuovoPossessore");
                        break;
                    case "Nuova Partita":
                        preparaFormPartita();
                        cardLayout.show(contentPanel, "nuovaPartita");
                        break;
                    case "Certificato":
                        cardLayout.show(contentPanel, "certificato");
                        break;
                    case "Ricerca":
                        cardLayout.show(contentPanel, "ricerca");
                        break;
                }
            });
            
            menuButtons.add(button);
        }
        
        // Aggiungi il pulsante di disconnessione
        JButton logoutButton = new JButton("Disconnetti");
        logoutButton.setMaximumSize(new Dimension(180, 40));
        logoutButton.setAlignmentX(Component.CENTER_ALIGNMENT);
        logoutButton.setFocusPainted(false);
        logoutButton.addActionListener(e -> {
            disconnect();
            showLoginPanel();
        });
        
        menuButtons.add(logoutButton);
    }
    
    private void createTablePanels() {
        // Pannello Home
        JPanel homePanel = new JPanel();
        homePanel.setLayout(new BorderLayout());
        
        JLabel welcomeLabel = new JLabel("<html><h1>Benvenuto nel Sistema Catasto Storico</h1>" +
                "<p>Seleziona un'opzione dal menu a sinistra per iniziare.</p></html>");
        welcomeLabel.setHorizontalAlignment(JLabel.CENTER);
        welcomeLabel.setBorder(BorderFactory.createEmptyBorder(30, 30, 30, 30));
        
        homePanel.add(welcomeLabel, BorderLayout.CENTER);
        contentPanel.add(homePanel, "home");
        
        // Pannelli per le tabelle
        String[] panelNames = {"comuni", "partite", "possessori", "immobili"};
        for (String name : panelNames) {
            JPanel panel = new JPanel(new BorderLayout());
            panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
            
            JLabel titleLabel = new JLabel("Elenco " + name.substring(0, 1).toUpperCase() + name.substring(1));
            titleLabel.setFont(new Font("Arial", Font.BOLD, 16));
            titleLabel.setBorder(BorderFactory.createEmptyBorder(0, 0, 10, 0));
            
            JTable table = new JTable();
            JScrollPane scrollPane = new JScrollPane(table);
            
            JButton refreshButton = new JButton("Aggiorna");
            refreshButton.addActionListener(e -> {
                switch (name) {
                    case "comuni":
                        mostraComuni();
                        break;
                    case "partite":
                        mostraPartite();
                        break;
                    case "possessori":
                        mostraPossessori();
                        break;
                    case "immobili":
                        mostraImmobili();
                        break;
                }
            });
            
            JPanel topPanel = new JPanel(new BorderLayout());
            topPanel.add(titleLabel, BorderLayout.WEST);
            topPanel.add(refreshButton, BorderLayout.EAST);
            
            panel.add(topPanel, BorderLayout.NORTH);
            panel.add(scrollPane, BorderLayout.CENTER);
            
            contentPanel.add(panel, name);
        }
    }
    
    private void createFormPanels() {
        // Pannello Nuovo Possessore
        JPanel nuovoPossessorePanel = new JPanel();
        nuovoPossessorePanel.setLayout(new BorderLayout());
        nuovoPossessorePanel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        
        JLabel titleLabel = new JLabel("Inserimento Nuovo Possessore");
        titleLabel.setFont(new Font("Arial", Font.BOLD, 16));
        
        JPanel formPanel = new JPanel(new GridLayout(4, 2, 10, 10));
        
        JLabel comuneLabel = new JLabel("Comune:");
        JComboBox<String> comuneCombo = new JComboBox<>();
        
        JLabel cognomeNomeLabel = new JLabel("Cognome e Nome:");
        JTextField cognomeNomeField = new JTextField(20);
        
        JLabel paternitaLabel = new JLabel("Paternità:");
        JTextField paternitaField = new JTextField(20);
        
        JLabel attivoLabel = new JLabel("Attivo:");
        JCheckBox attivoCheck = new JCheckBox();
        attivoCheck.setSelected(true);
        
        formPanel.add(comuneLabel);
        formPanel.add(comuneCombo);
        formPanel.add(cognomeNomeLabel);
        formPanel.add(cognomeNomeField);
        formPanel.add(paternitaLabel);
        formPanel.add(paternitaField);
        formPanel.add(attivoLabel);
        formPanel.add(attivoCheck);
        
        JButton salvaButton = new JButton("Salva Possessore");
        salvaButton.addActionListener(e -> {
            try {
                String comune = (String) comuneCombo.getSelectedItem();
                String cognomeNome = cognomeNomeField.getText();
                String paternita = paternitaField.getText();
                String nomeCompleto = cognomeNome + " " + paternita;
                boolean attivo = attivoCheck.isSelected();
                
                if (comune == null || cognomeNome.isEmpty()) {
                    JOptionPane.showMessageDialog(this, 
                        "Inserire comune e cognome nome!", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                try (CallableStatement cstmt = conn.prepareCall("CALL inserisci_possessore(?, ?, ?, ?, ?);")) {
                    cstmt.setString(1, comune);
                    cstmt.setString(2, cognomeNome);
                    cstmt.setString(3, paternita);
                    cstmt.setString(4, nomeCompleto);
                    cstmt.setBoolean(5, attivo);
                    cstmt.execute();
                }
                
                JOptionPane.showMessageDialog(this, 
                    "Possessore inserito con successo!", 
                    "Successo", JOptionPane.INFORMATION_MESSAGE);
                
                // Reset form
                cognomeNomeField.setText("");
                paternitaField.setText("");
                attivoCheck.setSelected(true);
                
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(this, 
                    "Errore: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(salvaButton);
        
        nuovoPossessorePanel.add(titleLabel, BorderLayout.NORTH);
        nuovoPossessorePanel.add(formPanel, BorderLayout.CENTER);
        nuovoPossessorePanel.add(buttonPanel, BorderLayout.SOUTH);
        
        contentPanel.add(nuovoPossessorePanel, "nuovoPossessore");
        
        // Pannello Nuova Partita
        JPanel nuovaPartitaPanel = new JPanel();
        nuovaPartitaPanel.setLayout(new BorderLayout());
        nuovaPartitaPanel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        
        JLabel partitaTitle = new JLabel("Inserimento Nuova Partita");
        partitaTitle.setFont(new Font("Arial", Font.BOLD, 16));
        
        JPanel partitaForm = new JPanel(new GridLayout(4, 2, 10, 10));
        
        JLabel partitaComuneLabel = new JLabel("Comune:");
        JComboBox<String> partitaComuneCombo = new JComboBox<>();
        
        JLabel numeroPartitaLabel = new JLabel("Numero Partita:");
        JTextField numeroPartitaField = new JTextField(10);
        
        JLabel tipoPartitaLabel = new JLabel("Tipo:");
        JComboBox<String> tipoPartitaCombo = new JComboBox<>(new String[]{"principale", "secondaria"});
        
        JLabel possessoreLabel = new JLabel("Possessore:");
        JComboBox<String> possessoreCombo = new JComboBox<>();
        
        partitaForm.add(partitaComuneLabel);
        partitaForm.add(partitaComuneCombo);
        partitaForm.add(numeroPartitaLabel);
        partitaForm.add(numeroPartitaField);
        partitaForm.add(tipoPartitaLabel);
        partitaForm.add(tipoPartitaCombo);
        partitaForm.add(possessoreLabel);
        partitaForm.add(possessoreCombo);
        
        // Aggiorna GUI
        menuPanel.revalidate();
        menuPanel.repaint();
    }
    
    private void connectToDatabase() {
        try {
            String user = userField.getText();
            String password = new String(passwordField.getPassword());
            String host = hostField.getText();
            String port = portField.getText();
            
            String url = "jdbc:postgresql://" + host + ":" + port + "/catasto_storico";
            conn = DriverManager.getConnection(url, user, password);
            
            // Imposta lo schema catasto
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("SET search_path TO catasto;");
            }
            
            connected = true;
            
            // Aggiorna liste comuni e possessori nei vari combo box
            aggiornaComboBoxComuni();
            
            // Mostra il menu principale
            showMainMenu();
            
            JOptionPane.showMessageDialog(this, 
                "Connessione al database effettuata con successo!", 
                "Connessione", JOptionPane.INFORMATION_MESSAGE);
            
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore di connessione: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private void disconnect() {
        if (conn != null) {
            try {
                conn.close();
                connected = false;
                JOptionPane.showMessageDialog(this, 
                    "Disconnessione effettuata con successo!", 
                    "Disconnessione", JOptionPane.INFORMATION_MESSAGE);
            } catch (SQLException e) {
                JOptionPane.showMessageDialog(this, 
                    "Errore durante la disconnessione: " + e.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            }
        }
    }
    
    private void aggiornaComboBoxComuni() {
        try {
            // Trova tutti i componenti JComboBox del tipo comune e li aggiorna
            for (Component component : contentPanel.getComponents()) {
                if (component instanceof JPanel) {
                    updateComuniComboInPanel((JPanel) component);
                }
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore nell'aggiornamento dei comuni: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private void updateComuniComboInPanel(JPanel panel) throws SQLException {
        for (Component component : panel.getComponents()) {
            if (component instanceof JComboBox) {
                JComboBox<?> comboBox = (JComboBox<?>) component;
                if (comboBox.getName() != null && comboBox.getName().contains("comune")) {
                    updateComuniCombo((JComboBox<String>) comboBox);
                }
            } else if (component instanceof JPanel) {
                updateComuniComboInPanel((JPanel) component);
            } else if (component instanceof JScrollPane) {
                JScrollPane scrollPane = (JScrollPane) component;
                Component view = scrollPane.getViewport().getView();
                if (view instanceof JPanel) {
                    updateComuniComboInPanel((JPanel) view);
                }
            } else if (component instanceof JTabbedPane) {
                JTabbedPane tabbedPane = (JTabbedPane) component;
                for (int i = 0; i < tabbedPane.getTabCount(); i++) {
                    Component tabComponent = tabbedPane.getComponentAt(i);
                    if (tabComponent instanceof JPanel) {
                        updateComuniComboInPanel((JPanel) tabComponent);
                    }
                }
            }
        }
    }
    
    private void updateComuniCombo(JComboBox<String> comboBox) throws SQLException {
        comboBox.removeAllItems();
        
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT nome FROM comune ORDER BY nome;")) {
            while (rs.next()) {
                comboBox.addItem(rs.getString("nome"));
            }
        }
    }
    
    private void aggiornaPossessoriCombo(JComboBox<String> comboBox, String comune) {
        try {
            comboBox.removeAllItems();
            
            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT id, nome_completo FROM possessore " +
                    "WHERE comune_nome = ? AND attivo = TRUE " +
                    "ORDER BY nome_completo;")) {
                pstmt.setString(1, comune);
                try (ResultSet rs = pstmt.executeQuery()) {
                    while (rs.next()) {
                        int id = rs.getInt("id");
                        String nome = rs.getString("nome_completo");
                        comboBox.addItem(nome + " (ID: " + id + ")");
                    }
                }
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore nell'aggiornamento dei possessori: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private void preparaFormPartita() {
        try {
            // Prima aggiorna i comuni
            aggiornaComboBoxComuni();
            
            // Trova il combo box del comune sulla form partita
            for (Component component : contentPanel.getComponents()) {
                if (component instanceof JPanel && component.getName() != null && 
                    component.getName().equals("nuovaPartita")) {
                    
                    JPanel partitaPanel = (JPanel) component;
                    for (Component c : partitaPanel.getComponents()) {
                        if (c instanceof JPanel) {
                            JPanel formPanel = (JPanel) c;
                            for (Component formComp : formPanel.getComponents()) {
                                if (formComp instanceof JComboBox) {
                                    JComboBox<?> comboBox = (JComboBox<?>) formComp;
                                    if (comboBox.getName() != null && comboBox.getName().contains("comune")) {
                                        // Se c'è un elemento selezionato, aggiorna i possessori
                                        if (comboBox.getSelectedItem() != null) {
                                            String comune = (String) comboBox.getSelectedItem();
                                            // Cerca il combo box dei possessori
                                            for (Component possComp : formPanel.getComponents()) {
                                                if (possComp instanceof JComboBox && 
                                                    possComp.getName() != null && 
                                                    possComp.getName().contains("possessore")) {
                                                    
                                                    JComboBox<String> possessoreCombo = (JComboBox<String>) possComp;
                                                    aggiornaPossessoriCombo(possessoreCombo, comune);
                                                    break;
                                                }
                                            }
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    private void mostraComuni() {
        try {
            // Trova il JTable nel pannello dei comuni
            JTable table = null;
            for (Component component : contentPanel.getComponents()) {
                if (component instanceof JPanel && 
                    component.getName() != null && 
                    component.getName().equals("comuni")) {
                    
                    JPanel panel = (JPanel) component;
                    for (Component comp : panel.getComponents()) {
                        if (comp instanceof JScrollPane) {
                            JScrollPane scrollPane = (JScrollPane) comp;
                            Component view = scrollPane.getViewport().getView();
                            if (view instanceof JTable) {
                                table = (JTable) view;
                                break;
                            }
                        }
                    }
                }
            }
            
            if (table == null) {
                // Se non troviamo la tabella, cerchiamola direttamente
                for (Component component : contentPanel.getComponents()) {
                    if (component instanceof JPanel) {
                        JPanel panel = (JPanel) component;
                        for (Component comp : panel.getComponents()) {
                            if (comp instanceof JScrollPane) {
                                JScrollPane scrollPane = (JScrollPane) comp;
                                Component view = scrollPane.getViewport().getView();
                                if (view instanceof JTable) {
                                    // Verifica se siamo nel pannello giusto
                                    String panelName = component.getName();
                                    if (panelName != null && panelName.equals("comuni")) {
                                        table = (JTable) view;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            if (table != null) {
                // Esegui la query
                try (Statement stmt = conn.createStatement();
                     ResultSet rs = stmt.executeQuery(
                             "SELECT nome, provincia, regione FROM comune ORDER BY nome;")) {
                    
                    // Crea il modello della tabella
                    DefaultTableModel model = new DefaultTableModel();
                    model.addColumn("Nome");
                    model.addColumn("Provincia");
                    model.addColumn("Regione");
                    
                    while (rs.next()) {
                        model.addRow(new Object[]{
                            rs.getString("nome"),
                            rs.getString("provincia"),
                            rs.getString("regione")
                        });
                    }
                    
                    table.setModel(model);
                }
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore nella visualizzazione dei comuni: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private void mostraPartite() {
        try {
            // Trova la tabella nel pannello delle partite
            JTable table = findTableInPanel("partite");
            
            if (table != null) {
                // Esegui la query
                try (Statement stmt = conn.createStatement();
                     ResultSet rs = stmt.executeQuery(
                             "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato, " +
                             "string_agg(pos.nome_completo, ', ') as possessori " +
                             "FROM partita p " +
                             "LEFT JOIN partita_possessore pp ON p.id = pp.partita_id " +
                             "LEFT JOIN possessore pos ON pp.possessore_id = pos.id " +
                             "GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato " +
                             "ORDER BY p.comune_nome, p.numero_partita " +
                             "LIMIT 100;")) {
                    
                    // Crea il modello della tabella
                    DefaultTableModel model = new DefaultTableModel();
                    model.addColumn("ID");
                    model.addColumn("Comune");
                    model.addColumn("Numero");
                    model.addColumn("Tipo");
                    model.addColumn("Stato");
                    model.addColumn("Possessori");
                    
                    while (rs.next()) {
                        String possessori = rs.getString("possessori");
                        if (possessori != null && possessori.length() > 30) {
                            possessori = possessori.substring(0, 27) + "...";
                        }
                        
                        model.addRow(new Object[]{
                            rs.getInt("id"),
                            rs.getString("comune_nome"),
                            rs.getInt("numero_partita"),
                            rs.getString("tipo"),
                            rs.getString("stato"),
                            possessori
                        });
                    }
                    
                    table.setModel(model);
                }
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore nella visualizzazione delle partite: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private void mostraPossessori() {
        try {
            // Trova la tabella nel pannello dei possessori
            JTable table = findTableInPanel("possessori");
            
            if (table != null) {
                // Esegui la query
                try (Statement stmt = conn.createStatement();
                     ResultSet rs = stmt.executeQuery(
                             "SELECT id, nome_completo, comune_nome, cognome_nome, paternita, attivo " +
                             "FROM possessore " +
                             "ORDER BY comune_nome, nome_completo " +
                             "LIMIT 100;")) {
                    
                    // Crea il modello della tabella
                    DefaultTableModel model = new DefaultTableModel();
                    model.addColumn("ID");
                    model.addColumn("Nome Completo");
                    model.addColumn("Comune");
                    model.addColumn("Paternità");
                    model.addColumn("Stato");
                    
                    while (rs.next()) {
                        model.addRow(new Object[]{
                            rs.getInt("id"),
                            rs.getString("nome_completo"),
                            rs.getString("comune_nome"),
                            rs.getString("paternita"),
                            rs.getBoolean("attivo") ? "Attivo" : "Non attivo"
                        });
                    }
                    
                    table.setModel(model);
                }
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore nella visualizzazione dei possessori: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private void mostraImmobili() {
        try {
            // Trova la tabella nel pannello degli immobili
            JTable table = findTableInPanel("immobili");
            
            if (table != null) {
                // Esegui la query
                try (Statement stmt = conn.createStatement();
                     ResultSet rs = stmt.executeQuery(
                             "SELECT i.id, i.natura, l.nome as localita, p.numero_partita, p.comune_nome " +
                             "FROM immobile i " +
                             "JOIN localita l ON i.localita_id = l.id " +
                             "JOIN partita p ON i.partita_id = p.id " +
                             "ORDER BY p.comune_nome, p.numero_partita " +
                             "LIMIT 100;")) {
                    
                    // Crea il modello della tabella
                    DefaultTableModel model = new DefaultTableModel();
                    model.addColumn("ID");
                    model.addColumn("Natura");
                    model.addColumn("Località");
                    model.addColumn("Partita");
                    model.addColumn("Comune");
                    
                    while (rs.next()) {
                        model.addRow(new Object[]{
                            rs.getInt("id"),
                            rs.getString("natura"),
                            rs.getString("localita"),
                            rs.getInt("numero_partita"),
                            rs.getString("comune_nome")
                        });
                    }
                    
                    table.setModel(model);
                }
            }
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(this, 
                "Errore nella visualizzazione degli immobili: " + e.getMessage(), 
                "Errore", JOptionPane.ERROR_MESSAGE);
        }
    }
    
    private JTable findTableInPanel(String panelName) {
        for (Component component : contentPanel.getComponents()) {
            if (component instanceof JPanel && 
                component.getName() != null && 
                component.getName().equals(panelName)) {
                
                JPanel panel = (JPanel) component;
                for (Component comp : panel.getComponents()) {
                    if (comp instanceof JScrollPane) {
                        JScrollPane scrollPane = (JScrollPane) comp;
                        Component view = scrollPane.getViewport().getView();
                        if (view instanceof JTable) {
                            return (JTable) view;
                        }
                    }
                }
            }
        }
        
        // Fallback: cerca in tutti i pannelli
        for (Component component : contentPanel.getComponents()) {
            if (component instanceof JPanel) {
                JPanel panel = (JPanel) component;
                for (Component comp : panel.getComponents()) {
                    if (comp instanceof JScrollPane) {
                        JScrollPane scrollPane = (JScrollPane) comp;
                        Component view = scrollPane.getViewport().getView();
                        if (view instanceof JTable) {
                            return (JTable) view;
                        }
                    }
                }
            }
        }
        
        return null;
    }
    
    public static void main(String[] args) {
        try {
            // Carica il driver JDBC di PostgreSQL
            Class.forName("org.postgresql.Driver");
            
            // Imposta il look and feel del sistema
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (ClassNotFoundException e) {
            JOptionPane.showMessageDialog(null, 
                "Driver PostgreSQL JDBC non trovato. Assicurati di avere il JAR nel classpath.",
                "Errore", JOptionPane.ERROR_MESSAGE);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        // Esegui l'applicazione nell'Event Dispatch Thread
        SwingUtilities.invokeLater(() -> {
            CatastoGUI app = new CatastoGUI();
            app.setVisible(true);
        });
    } i possessori quando si seleziona un comune
        partitaComuneCombo.addActionListener(e -> {
            String selectedComune = (String) partitaComuneCombo.getSelectedItem();
            if (selectedComune != null) {
                // Aggiorna i possessori disponibili per questo comune
                aggiornaPossessoriCombo(possessoreCombo, selectedComune);
                
                // Suggerisci un numero di partita
                try {
                    try (PreparedStatement pstmt = conn.prepareStatement(
                            "SELECT COALESCE(MAX(numero_partita), 0) + 1 FROM partita WHERE comune_nome = ?;")) {
                        pstmt.setString(1, selectedComune);
                        try (ResultSet rs = pstmt.executeQuery()) {
                            if (rs.next()) {
                                numeroPartitaField.setText(String.valueOf(rs.getInt(1)));
                            }
                        }
                    }
                } catch (SQLException ex) {
                    ex.printStackTrace();
                }
            }
        });
        
        JButton salvaPartitaButton = new JButton("Salva Partita");
        salvaPartitaButton.addActionListener(e -> {
            try {
                String comune = (String) partitaComuneCombo.getSelectedItem();
                String numeroStr = numeroPartitaField.getText();
                String tipo = (String) tipoPartitaCombo.getSelectedItem();
                String possessoreText = (String) possessoreCombo.getSelectedItem();
                
                if (comune == null || numeroStr.isEmpty() || possessoreText == null) {
                    JOptionPane.showMessageDialog(this, 
                        "Tutti i campi sono obbligatori!", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                int numero = Integer.parseInt(numeroStr);
                
                // Estrai l'ID del possessore dalla stringa (ID: XX)
                int possessoreId = Integer.parseInt(possessoreText.substring(
                    possessoreText.lastIndexOf("(ID: ") + 5, 
                    possessoreText.lastIndexOf(")")));
                
                // Crea array con l'ID del possessore
                Integer[] possessoreIds = new Integer[]{possessoreId};
                
                // Inserisci la partita
                try (CallableStatement cstmt = conn.prepareCall(
                        "CALL inserisci_partita_con_possessori(?, ?, ?, ?, ?);")) {
                    cstmt.setString(1, comune);
                    cstmt.setInt(2, numero);
                    cstmt.setString(3, tipo);
                    cstmt.setDate(4, java.sql.Date.valueOf(LocalDate.now()));
                    
                    // Crea un array SQL dall'array Java
                    Array possessoreIdsArray = conn.createArrayOf("integer", possessoreIds);
                    cstmt.setArray(5, possessoreIdsArray);
                    
                    cstmt.execute();
                }
                
                JOptionPane.showMessageDialog(this, 
                    "Partita inserita con successo!", 
                    "Successo", JOptionPane.INFORMATION_MESSAGE);
                
                // Reset form
                numeroPartitaField.setText("");
                tipoPartitaCombo.setSelectedIndex(0);
                
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(this, 
                    "Errore: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(this, 
                    "Numero partita non valido!", 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        JPanel partitaButtonPanel = new JPanel();
        partitaButtonPanel.add(salvaPartitaButton);
        
        nuovaPartitaPanel.add(partitaTitle, BorderLayout.NORTH);
        nuovaPartitaPanel.add(partitaForm, BorderLayout.CENTER);
        nuovaPartitaPanel.add(partitaButtonPanel, BorderLayout.SOUTH);
        
        contentPanel.add(nuovaPartitaPanel, "nuovaPartita");
        
        // Pannello Certificato
        JPanel certificatoPanel = new JPanel(new BorderLayout());
        certificatoPanel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        
        JLabel certificatoTitle = new JLabel("Genera Certificato di Proprietà");
        certificatoTitle.setFont(new Font("Arial", Font.BOLD, 16));
        
        JPanel certificatoForm = new JPanel(new FlowLayout(FlowLayout.LEFT));
        
        JLabel partitaIdLabel = new JLabel("ID Partita:");
        JTextField partitaIdField = new JTextField(10);
        JButton generaButton = new JButton("Genera Certificato");
        
        certificatoForm.add(partitaIdLabel);
        certificatoForm.add(partitaIdField);
        certificatoForm.add(generaButton);
        
        JTextArea certificatoText = new JTextArea();
        certificatoText.setEditable(false);
        certificatoText.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane certificatoScroll = new JScrollPane(certificatoText);
        
        generaButton.addActionListener(e -> {
            try {
                String idStr = partitaIdField.getText().trim();
                if (idStr.isEmpty()) {
                    JOptionPane.showMessageDialog(this, 
                        "Inserire l'ID della partita!", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                int id = Integer.parseInt(idStr);
                
                try (CallableStatement cstmt = conn.prepareCall(
                        "SELECT genera_certificato_proprieta(?);")) {
                    cstmt.setInt(1, id);
                    try (ResultSet rs = cstmt.executeQuery()) {
                        if (rs.next()) {
                            certificatoText.setText(rs.getString(1));
                            certificatoText.setCaretPosition(0);
                        }
                    }
                }
                
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(this, 
                    "Errore: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(this, 
                    "ID partita non valido!", 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        certificatoPanel.add(certificatoTitle, BorderLayout.NORTH);
        certificatoPanel.add(certificatoForm, BorderLayout.NORTH);
        certificatoPanel.add(certificatoScroll, BorderLayout.CENTER);
        
        contentPanel.add(certificatoPanel, "certificato");
        
        // Pannello Ricerca
        JPanel ricercaPanel = new JPanel(new BorderLayout());
        ricercaPanel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        
        JTabbedPane tabbedPane = new JTabbedPane();
        
        // Tab ricerca possessori
        JPanel ricercaPossessoriPanel = new JPanel(new BorderLayout());
        
        JPanel ricercaPossessoriForm = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JLabel nomeRicercaLabel = new JLabel("Nome da cercare:");
        JTextField nomeRicercaField = new JTextField(20);
        JButton cercaPossessoriButton = new JButton("Cerca");
        
        ricercaPossessoriForm.add(nomeRicercaLabel);
        ricercaPossessoriForm.add(nomeRicercaField);
        ricercaPossessoriForm.add(cercaPossessoriButton);
        
        JTable possessoriTable = new JTable();
        JScrollPane possessoriScroll = new JScrollPane(possessoriTable);
        
        cercaPossessoriButton.addActionListener(e -> {
            try {
                String nome = nomeRicercaField.getText().trim();
                if (nome.isEmpty()) {
                    JOptionPane.showMessageDialog(this, 
                        "Inserire un nome da cercare!", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                try (PreparedStatement pstmt = conn.prepareStatement(
                        "SELECT * FROM cerca_possessori(?);")) {
                    pstmt.setString(1, nome);
                    try (ResultSet rs = pstmt.executeQuery()) {
                        DefaultTableModel model = new DefaultTableModel();
                        model.addColumn("ID");
                        model.addColumn("Nome Completo");
                        model.addColumn("Comune");
                        model.addColumn("Num. Partite");
                        
                        while (rs.next()) {
                            model.addRow(new Object[]{
                                rs.getInt("id"),
                                rs.getString("nome_completo"),
                                rs.getString("comune_nome"),
                                rs.getInt("num_partite")
                            });
                        }
                        
                        possessoriTable.setModel(model);
                    }
                }
                
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(this, 
                    "Errore: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        ricercaPossessoriPanel.add(ricercaPossessoriForm, BorderLayout.NORTH);
        ricercaPossessoriPanel.add(possessoriScroll, BorderLayout.CENTER);
        
        // Tab ricerca immobili
        JPanel ricercaImmobiliPanel = new JPanel(new BorderLayout());
        
        JPanel ricercaImmobiliForm = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JLabel comuneRicercaLabel = new JLabel("Comune:");
        JTextField comuneRicercaField = new JTextField(15);
        JLabel naturaRicercaLabel = new JLabel("Natura:");
        JTextField naturaRicercaField = new JTextField(15);
        JButton cercaImmobiliButton = new JButton("Cerca");
        
        ricercaImmobiliForm.add(comuneRicercaLabel);
        ricercaImmobiliForm.add(comuneRicercaField);
        ricercaImmobiliForm.add(naturaRicercaLabel);
        ricercaImmobiliForm.add(naturaRicercaField);
        ricercaImmobiliForm.add(cercaImmobiliButton);
        
        JTable immobiliTable = new JTable();
        JScrollPane immobiliScroll = new JScrollPane(immobiliTable);
        
        cercaImmobiliButton.addActionListener(e -> {
            try {
                String comune = comuneRicercaField.getText().trim();
                String natura = naturaRicercaField.getText().trim();
                
                if (comune.isEmpty() && natura.isEmpty()) {
                    JOptionPane.showMessageDialog(this, 
                        "Inserire almeno un criterio di ricerca!", 
                        "Errore", JOptionPane.ERROR_MESSAGE);
                    return;
                }
                
                try (PreparedStatement pstmt = conn.prepareStatement(
                        "SELECT * FROM cerca_immobili(NULL, ?, NULL, ?, NULL);")) {
                    pstmt.setString(1, comune.isEmpty() ? null : comune);
                    pstmt.setString(2, natura.isEmpty() ? null : natura);
                    
                    try (ResultSet rs = pstmt.executeQuery()) {
                        DefaultTableModel model = new DefaultTableModel();
                        model.addColumn("ID");
                        model.addColumn("Natura");
                        model.addColumn("Località");
                        model.addColumn("Comune");
                        model.addColumn("Partita");
                        
                        while (rs.next()) {
                            model.addRow(new Object[]{
                                rs.getInt("id"),
                                rs.getString("natura"),
                                rs.getString("localita_nome"),
                                rs.getString("comune"),
                                rs.getInt("numero_partita")
                            });
                        }
                        
                        immobiliTable.setModel(model);
                    }
                }
                
            } catch (SQLException ex) {
                JOptionPane.showMessageDialog(this, 
                    "Errore: " + ex.getMessage(), 
                    "Errore", JOptionPane.ERROR_MESSAGE);
            }
        });
        
        ricercaImmobiliPanel.add(ricercaImmobiliForm, BorderLayout.NORTH);
        ricercaImmobiliPanel.add(immobiliScroll, BorderLayout.CENTER);
        
        // Aggiungi i tab
        tabbedPane.addTab("Ricerca Possessori", ricercaPossessoriPanel);
        tabbedPane.addTab("Ricerca Immobili", ricercaImmobiliPanel);
        
        ricercaPanel.add(tabbedPane);
        
        contentPanel.add(ricercaPanel, "ricerca");
    }
    
    private void showLoginPanel() {
        // Rimuovi tutti i pulsanti dal menu
        menuPanel.removeAll();
        
        // Aggiungi titolo
        JLabel titleLabel = new JLabel("Catasto Storico");
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        titleLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        
        JLabel subtitleLabel = new JLabel("Gestione Catasto");
        subtitleLabel.setFont(new Font("Arial", Font.ITALIC, 12));
        subtitleLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        
        menuPanel.add(titleLabel);
        menuPanel.add(Box.createVerticalStrut(5));
        menuPanel.add(subtitleLabel);
        menuPanel.add(Box.createVerticalStrut(30));
        
        // Mostra pannello login
        cardLayout.show(contentPanel, "login");
        
        // Aggiorna GUI
        menuPanel.revalidate();
        menuPanel.repaint();
    }
    
    private void showMainMenu() {
        // Rimuovi tutti i pulsanti dal menu
        menuPanel.removeAll();
        
        // Aggiungi titolo
        JLabel titleLabel = new JLabel("Catasto Storico");
        titleLabel.setFont(new Font("Arial", Font.BOLD, 18));
        titleLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        
        JLabel subtitleLabel = new JLabel("Gestione Catasto");
        subtitleLabel.setFont(new Font("Arial", Font.ITALIC, 12));
        subtitleLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        
        menuPanel.add(titleLabel);
        menuPanel.add(Box.createVerticalStrut(5));
        menuPanel.add(subtitleLabel);
        menuPanel.add(Box.createVerticalStrut(30));
        
        // Aggiungi i pulsanti di menu
        for (JButton button : menuButtons) {
            menuPanel.add(button);
            menuPanel.add(Box.createVerticalStrut(10));
        }
        
        // Mostra pannello home
        cardLayout.show(contentPanel, "home");
        
        // Aggiorna