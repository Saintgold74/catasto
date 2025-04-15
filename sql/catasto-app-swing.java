import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.sql.*;
import java.time.LocalDate;
import java.util.*;
import java.util.List;

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
    
    public CatastoApp() {
        // Configurazione del frame principale
        setTitle("Catasto Storico");
        setSize(800, 600);
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
    }
    
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
        
        loginPanel.add(formPanel, BorderLayout.CENTER);
    }
    
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
        
        // Aggiunta dei menu alla barra dei menu
        menuBar.add(fileMenu);
        menuBar.add(viewMenu);
        menuBar.add(insertMenu);
        menuBar.add(searchMenu);
        menuBar.add(toolsMenu);
        
        // Aggiunta della barra dei menu e del pannello di contenuto
        menuPanel.add(menuBar, BorderLayout.NORTH);
        
        // Creazione del pannello di contenuto
        contentPanel = new JPanel(new CardLayout());
        createContentPanels();
        menuPanel.add(contentPanel, BorderLayout.CENTER);
    }
    
    private void createContentPanel() {
        contentPanel = new JPanel(new CardLayout());
        JPanel welcomePanel = new JPanel(new BorderLayout());
        
        JLabel welcomeLabel = new JLabel("Benvenuto nel Sistema Catasto Storico", JLabel.CENTER);
        welcomeLabel.setFont(new Font("Arial", Font.BOLD, 24));
        welcomePanel.add(welcomeLabel, BorderLayout.CENTER);
        
        contentPanel.add(welcomePanel, "welcome");
    }
    
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
        welcomePanel.add(welcomeLabel, BorderLayout.CENTER);
        
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
    
    private void createStatusBar() {
        statusLabel = new JLabel("Non connesso");
        statusLabel.setBorder(BorderFactory.createLoweredBevelBorder());
        add(statusLabel, BorderLayout.SOUTH);
    }
    
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
        
        // Pulsante di aggiornamento
        JButton refreshButton = new JButton("Aggiorna");
        refreshButton.addActionListener(e -> loadPartiteData(model));
        
        // Pannello dei pulsanti
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(refreshButton);
        
        // Aggiunta dei componenti al pannello
        partitePanel.add(titleLabel, BorderLayout.NORTH);
        partitePanel.add(scrollPane, BorderLayout.CENTER);
        partitePanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
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
        
        // Pulsante di aggiornamento
        JButton refreshButton = new JButton("Aggiorna");
        refreshButton.addActionListener(e -> loadPossessoriData(model));
        
        // Pannello dei pulsanti
        JPanel buttonPanel = new JPanel();
        buttonPanel.add(refreshButton);
        
        // Aggiunta dei componenti al pannello
        possessoriPanel.add(titleLabel, BorderLayout.NORTH);
        possessoriPanel.add(scrollPane, BorderLayout.CENTER);
        possessoriPanel.add(buttonPanel, BorderLayout.SOUTH);
    }
    
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
        
        // Aggiunta dei componenti al pannello
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.gridwidth = 2;
        formPanel.add(titleLabel, gbc);
        
        gbc.gridwidth = 1;
        gbc.gridy = 1;
        formPanel.add(partitaLabel, gbc);
        gbc.gridx = 1;
        formPanel.add(partitaField, gbc);
        
        gbc.gridx = 0;
        gbc.gridy = 2;
        gbc.gridwidth = 2;
        gbc.anchor = GridBagConstraints.CENTER;
        formPanel.add(generateButton, gbc);
        
        certificatoPanel.add(formPanel, BorderLayout.NORTH);
        certificatoPanel.add(scrollPane, BorderLayout.CENTER);
