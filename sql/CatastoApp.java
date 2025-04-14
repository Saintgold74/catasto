import java.sql.*;
import java.time.LocalDate;
import java.util.*;
import java.util.Date;

public class CatastoApp {
    private Connection conn;
    private boolean connected;
    private Scanner scanner;

    public CatastoApp() {
        scanner = new Scanner(System.in);
        connected = false;
    }

    public void connect() {
        try {
            System.out.println("Connessione al database catasto_storico...");
            System.out.print("Utente PostgreSQL [postgres]: ");
            String user = scanner.nextLine().trim();
            if (user.isEmpty()) {
                user = "postgres";
            }

            System.out.print("Password per " + user + ": ");
            String password = scanner.nextLine();

            System.out.print("Host [localhost]: ");
            String host = scanner.nextLine().trim();
            if (host.isEmpty()) {
                host = "localhost";
            }

            System.out.print("Porta [5432]: ");
            String port = scanner.nextLine().trim();
            if (port.isEmpty()) {
                port = "5432";
            }

            String url = "jdbc:postgresql://" + host + ":" + port + "/catasto_storico";
            conn = DriverManager.getConnection(url, user, password);

            // Imposta lo schema catasto
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("SET search_path TO catasto;");
            }

            connected = true;
            System.out.println("Connessione stabilita con successo!");
        } catch (SQLException e) {
            System.out.println("Errore di connessione: " + e.getMessage());
        }
    }

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

    public void clearScreen() {
        try {
            if (System.getProperty("os.name").contains("Windows")) {
                new ProcessBuilder("cmd", "/c", "cls").inheritIO().start().waitFor();
            } else {
                System.out.print("\033[H\033[2J");
                System.out.flush();
            }
        } catch (Exception e) {
            // Fallback se non è possibile pulire la console
            for (int i = 0; i < 50; i++) {
                System.out.println();
            }
        }
    }

    public void printHeader(String title) {
        clearScreen();
        System.out.println("=".repeat(50));
        System.out.println(title.toUpperCase());
        System.out.println("=".repeat(50));
        System.out.println();
    }

    public void waitForKey() {
        System.out.println("\nPremi INVIO per continuare...");
        scanner.nextLine();
    }

    public void mostraComuni() {
        printHeader("ELENCO COMUNI");

        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT nome, provincia, regione FROM comune ORDER BY nome;")) {

            if (!rs.isBeforeFirst()) {
                System.out.println("Nessun comune trovato.");
                return;
            }

            System.out.printf("%-20s %-15s %-15s\n", "NOME", "PROVINCIA", "REGIONE");
            System.out.println("-".repeat(50));

            while (rs.next()) {
                String nome = rs.getString("nome");
                String provincia = rs.getString("provincia");
                String regione = rs.getString("regione");
                System.out.printf("%-20s %-15s %-15s\n", nome, provincia, regione);
            }

        } catch (SQLException e) {
            System.out.println("Errore nella visualizzazione dei comuni: " + e.getMessage());
        }

        waitForKey();
    }

    public void mostraPartite() {
        printHeader("ELENCO PARTITE");

        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato, " +
                             "string_agg(pos.nome_completo, ', ') as possessori " +
                             "FROM partita p " +
                             "LEFT JOIN partita_possessore pp ON p.id = pp.partita_id " +
                             "LEFT JOIN possessore pos ON pp.possessore_id = pos.id " +
                             "GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato " +
                             "ORDER BY p.comune_nome, p.numero_partita " +
                             "LIMIT 20;")) {

            if (!rs.isBeforeFirst()) {
                System.out.println("Nessuna partita trovata.");
                return;
            }

            System.out.printf("%-5s %-15s %-8s %-12s %-10s %-30s\n", "ID", "COMUNE", "NUMERO", "TIPO", "STATO", "POSSESSORI");
            System.out.println("-".repeat(80));

            while (rs.next()) {
                int id = rs.getInt("id");
                String comune = rs.getString("comune_nome");
                int numero = rs.getInt("numero_partita");
                String tipo = rs.getString("tipo");
                String stato = rs.getString("stato");
                String possessori = rs.getString("possessori");
                if (possessori == null) possessori = "";
                if (possessori.length() > 30) possessori = possessori.substring(0, 27) + "...";

                System.out.printf("%-5d %-15s %-8d %-12s %-10s %-30s\n", id, comune, numero, tipo, stato, possessori);
            }

        } catch (SQLException e) {
            System.out.println("Errore nella visualizzazione delle partite: " + e.getMessage());
        }

        waitForKey();
    }

    public void mostraPossessori() {
        printHeader("ELENCO POSSESSORI");

        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT id, nome_completo, comune_nome, cognome_nome, paternita, attivo " +
                             "FROM possessore " +
                             "ORDER BY comune_nome, nome_completo " +
                             "LIMIT 20;")) {

            if (!rs.isBeforeFirst()) {
                System.out.println("Nessun possessore trovato.");
                return;
            }

            System.out.printf("%-5s %-30s %-15s %-10s\n", "ID", "NOME COMPLETO", "COMUNE", "STATO");
            System.out.println("-".repeat(60));

            while (rs.next()) {
                int id = rs.getInt("id");
                String nome = rs.getString("nome_completo");
                String comune = rs.getString("comune_nome");
                boolean attivo = rs.getBoolean("attivo");
                String stato = attivo ? "Attivo" : "Non attivo";

                System.out.printf("%-5d %-30s %-15s %-10s\n", id, nome, comune, stato);
            }

        } catch (SQLException e) {
            System.out.println("Errore nella visualizzazione dei possessori: " + e.getMessage());
        }

        waitForKey();
    }

    public void mostraImmobili() {
        printHeader("ELENCO IMMOBILI");

        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                     "SELECT i.id, i.natura, l.nome as localita, p.numero_partita, p.comune_nome " +
                             "FROM immobile i " +
                             "JOIN localita l ON i.localita_id = l.id " +
                             "JOIN partita p ON i.partita_id = p.id " +
                             "ORDER BY p.comune_nome, p.numero_partita " +
                             "LIMIT 20;")) {

            if (!rs.isBeforeFirst()) {
                System.out.println("Nessun immobile trovato.");
                return;
            }

            System.out.printf("%-5s %-25s %-20s %-8s %-15s\n", "ID", "NATURA", "LOCALITA", "PARTITA", "COMUNE");
            System.out.println("-".repeat(75));

            while (rs.next()) {
                int id = rs.getInt("id");
                String natura = rs.getString("natura");
                String localita = rs.getString("localita");
                int partita = rs.getInt("numero_partita");
                String comune = rs.getString("comune_nome");

                System.out.printf("%-5d %-25s %-20s %-8d %-15s\n", id, natura, localita, partita, comune);
            }

        } catch (SQLException e) {
            System.out.println("Errore nella visualizzazione degli immobili: " + e.getMessage());
        }

        waitForKey();
    }

    public void inserisciPossessore() {
        printHeader("INSERIMENTO NUOVO POSSESSORE");

        try {
            // Ottieni la lista dei comuni disponibili
            List<String> comuni = new ArrayList<>();
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT nome FROM comune ORDER BY nome;")) {
                while (rs.next()) {
                    comuni.add(rs.getString("nome"));
                }
            }

            if (comuni.isEmpty()) {
                System.out.println("Nessun comune disponibile. Impossibile inserire un possessore.");
                waitForKey();
                return;
            }

            System.out.println("Comuni disponibili:");
            for (int i = 0; i < comuni.size(); i++) {
                System.out.println((i + 1) + ". " + comuni.get(i));
            }

            System.out.print("\nSeleziona il numero del comune: ");
            int idx = Integer.parseInt(scanner.nextLine()) - 1;
            if (idx < 0 || idx >= comuni.size()) {
                System.out.println("Selezione non valida.");
                waitForKey();
                return;
            }

            String comuneNome = comuni.get(idx);
            System.out.print("Cognome e nome (es. Rossi Mario): ");
            String cognomeNome = scanner.nextLine();
            System.out.print("Paternità (es. fu Giuseppe): ");
            String paternita = scanner.nextLine();
            String nomeCompleto = cognomeNome + " " + paternita;

            String sql = "CALL inserisci_possessore(?, ?, ?, ?, ?);";
            try (CallableStatement cstmt = conn.prepareCall(sql)) {
                cstmt.setString(1, comuneNome);
                cstmt.setString(2, cognomeNome);
                cstmt.setString(3, paternita);
                cstmt.setString(4, nomeCompleto);
                cstmt.setBoolean(5, true);
                cstmt.execute();
            }

            System.out.println("\nPossessore " + nomeCompleto + " inserito con successo nel comune di " + comuneNome + "!");

        } catch (SQLException e) {
            System.out.println("Errore nell'inserimento del possessore: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.out.println("Errore: inserire un numero valido.");
        }

        waitForKey();
    }

    public void inserisciPartita() {
        printHeader("INSERIMENTO NUOVA PARTITA");

        try {
            // Ottieni la lista dei comuni disponibili
            List<String> comuni = new ArrayList<>();
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT nome FROM comune ORDER BY nome;")) {
                while (rs.next()) {
                    comuni.add(rs.getString("nome"));
                }
            }

            if (comuni.isEmpty()) {
                System.out.println("Nessun comune disponibile. Impossibile inserire una partita.");
                waitForKey();
                return;
            }

            System.out.println("Comuni disponibili:");
            for (int i = 0; i < comuni.size(); i++) {
                System.out.println((i + 1) + ". " + comuni.get(i));
            }

            System.out.print("\nSeleziona il numero del comune: ");
            int idx = Integer.parseInt(scanner.nextLine()) - 1;
            if (idx < 0 || idx >= comuni.size()) {
                System.out.println("Selezione non valida.");
                waitForKey();
                return;
            }

            String comuneNome = comuni.get(idx);

            // Trova un numero di partita disponibile
            int numeroPartita;
            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT COALESCE(MAX(numero_partita), 0) + 1 FROM partita WHERE comune_nome = ?;")) {
                pstmt.setString(1, comuneNome);
                try (ResultSet rs = pstmt.executeQuery()) {
                    rs.next();
                    numeroPartita = rs.getInt(1);
                }
            }

            System.out.print("Numero partita [suggerito: " + numeroPartita + "]: ");
            String input = scanner.nextLine();
            if (!input.isEmpty()) {
                numeroPartita = Integer.parseInt(input);
            }

            // Verifica che il numero partita non esista già
            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT 1 FROM partita WHERE comune_nome = ? AND numero_partita = ?;")) {
                pstmt.setString(1, comuneNome);
                pstmt.setInt(2, numeroPartita);
                try (ResultSet rs = pstmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("Errore: La partita " + numeroPartita + " esiste già nel comune " + comuneNome + ".");
                        waitForKey();
                        return;
                    }
                }
            }

            System.out.print("Tipo (principale/secondaria) [principale]: ");
            String tipo = scanner.nextLine();
            if (tipo.isEmpty()) {
                tipo = "principale";
            }

            // Ottieni la lista dei possessori disponibili per il comune
            List<Map<String, Object>> possessori = new ArrayList<>();
            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT id, nome_completo FROM possessore " +
                            "WHERE comune_nome = ? AND attivo = TRUE " +
                            "ORDER BY nome_completo;")) {
                pstmt.setString(1, comuneNome);
                try (ResultSet rs = pstmt.executeQuery()) {
                    while (rs.next()) {
                        Map<String, Object> possessore = new HashMap<>();
                        possessore.put("id", rs.getInt("id"));
                        possessore.put("nome", rs.getString("nome_completo"));
                        possessori.add(possessore);
                    }
                }
            }

            if (possessori.isEmpty()) {
                System.out.println("Nessun possessore disponibile nel comune " + comuneNome + ". Impossibile inserire una partita.");
                waitForKey();
                return;
            }

            System.out.println("\nPossessori disponibili:");
            for (int i = 0; i < possessori.size(); i++) {
                Map<String, Object> possessore = possessori.get(i);
                System.out.println((i + 1) + ". " + possessore.get("nome") + " (ID: " + possessore.get("id") + ")");
            }

            System.out.print("\nSeleziona il numero del possessore: ");
            idx = Integer.parseInt(scanner.nextLine()) - 1;
            if (idx < 0 || idx >= possessori.size()) {
                System.out.println("Selezione non valida.");
                waitForKey();
                return;
            }

            int possessoreId = (int) possessori.get(idx).get("id");
            Integer[] possessoreIds = new Integer[]{possessoreId};

            // Inserisci la partita
            try (CallableStatement cstmt = conn.prepareCall(
                    "CALL inserisci_partita_con_possessori(?, ?, ?, ?, ?);")) {
                cstmt.setString(1, comuneNome);
                cstmt.setInt(2, numeroPartita);
                cstmt.setString(3, tipo);
                cstmt.setDate(4, java.sql.Date.valueOf(LocalDate.now()));
                
                // Crea un array SQL dall'array Java
                Array possessoreIdsArray = conn.createArrayOf("integer", possessoreIds);
                cstmt.setArray(5, possessoreIdsArray);
                
                cstmt.execute();
            }

            System.out.println("\nPartita " + numeroPartita + " inserita con successo nel comune di " + comuneNome + "!");

        } catch (SQLException e) {
            System.out.println("Errore nell'inserimento della partita: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.out.println("Errore: inserire un numero valido.");
        }

        waitForKey();
    }

    public void generaCertificato() {
        printHeader("GENERAZIONE CERTIFICATO DI PROPRIETÀ");

        try {
            System.out.print("Inserisci l'ID della partita: ");
            int partitaId = Integer.parseInt(scanner.nextLine());

            try (CallableStatement cstmt = conn.prepareCall(
                    "SELECT genera_certificato_proprieta(?);")) {
                cstmt.setInt(1, partitaId);
                try (ResultSet rs = cstmt.executeQuery()) {
                    if (rs.next()) {
                        String certificato = rs.getString(1);
                        System.out.println("\n" + certificato);
                    }
                }
            }

        } catch (SQLException e) {
            System.out.println("Errore nella generazione del certificato: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.out.println("Errore: inserire un numero valido.");
        }

        waitForKey();
    }

    public void ricercaPossessori() {
        printHeader("RICERCA POSSESSORI");

        try {
            System.out.print("Inserisci il nome da cercare: ");
            String nome = scanner.nextLine();

            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT * FROM cerca_possessori(?);")) {
                pstmt.setString(1, nome);
                try (ResultSet rs = pstmt.executeQuery()) {
                    if (!rs.isBeforeFirst()) {
                        System.out.println("Nessun possessore trovato con questo nome.");
                        waitForKey();
                        return;
                    }

                    System.out.printf("%-5s %-30s %-15s %-10s\n", "ID", "NOME COMPLETO", "COMUNE", "NUM PARTITE");
                    System.out.println("-".repeat(60));

                    while (rs.next()) {
                        int id = rs.getInt("id");
                        String nomeCompleto = rs.getString("nome_completo");
                        String comune = rs.getString("comune_nome");
                        int numPartite = rs.getInt("num_partite");
                        System.out.printf("%-5d %-30s %-15s %-10d\n", id, nomeCompleto, comune, numPartite);
                    }
                }
            }

        } catch (SQLException e) {
            System.out.println("Errore nella ricerca dei possessori: " + e.getMessage());
        }

        waitForKey();
    }

    public void ricercaImmobili() {
        printHeader("RICERCA IMMOBILI");

        try {
            System.out.print("Comune [lascia vuoto per tutti]: ");
            String comune = scanner.nextLine();
            System.out.print("Natura immobile [lascia vuoto per tutti]: ");
            String natura = scanner.nextLine();

            if (comune.isEmpty()) comune = null;
            if (natura.isEmpty()) natura = null;

            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT * FROM cerca_immobili(NULL, ?, NULL, ?, NULL);")) {
                pstmt.setString(1, comune);
                pstmt.setString(2, natura);
                try (ResultSet rs = pstmt.executeQuery()) {
                    if (!rs.isBeforeFirst()) {
                        System.out.println("Nessun immobile trovato con questi criteri.");
                        waitForKey();
                        return;
                    }

                    System.out.printf("%-5s %-25s %-20s %-15s %-8s\n", "ID", "NATURA", "LOCALITA", "COMUNE", "PARTITA");
                    System.out.println("-".repeat(75));

                    while (rs.next()) {
                        int id = rs.getInt("id");
                        String immobileNatura = rs.getString("natura");
                        String localita = rs.getString("localita_nome");
                        String immobileComune = rs.getString("comune");
                        int numeroPartita = rs.getInt("numero_partita");
                        System.out.printf("%-5d %-25s %-20s %-15s %-8d\n", id, immobileNatura, localita, immobileComune, numeroPartita);
                    }
                }
            }

        } catch (SQLException e) {
            System.out.println("Errore nella ricerca degli immobili: " + e.getMessage());
        }

        waitForKey();
    }

    public void aggiornaPossessore() {
        printHeader("AGGIORNAMENTO POSSESSORE");

        try {
            System.out.print("Inserisci l'ID del possessore da aggiornare: ");
            int id = Integer.parseInt(scanner.nextLine());

            // Verifica che il possessore esista
            try (PreparedStatement pstmt = conn.prepareStatement(
                    "SELECT id, nome_completo, comune_nome, cognome_nome, paternita, attivo " +
                            "FROM possessore " +
                            "WHERE id = ?;")) {
                pstmt.setInt(1, id);
                try (ResultSet rs = pstmt.executeQuery()) {
                    if (!rs.next()) {
                        System.out.println("Nessun possessore trovato con ID " + id + ".");
                        waitForKey();
                        return;
                    }

                    String nome = rs.getString("nome_completo");
                    String comune = rs.getString("comune_nome");
                    boolean attivo = rs.getBoolean("attivo");

                    System.out.println("Possessore: " + nome + " (" + comune + ")");
                    System.out.println("Attualmente " + (attivo ? "attivo" : "non attivo"));

                    System.out.print("Nuovo stato (attivo/non attivo) [lascia vuoto per mantenere]: ");
                    String nuovoStato = scanner.nextLine();

                    if (!nuovoStato.isEmpty()) {
                        boolean nuovoAttivo = nuovoStato.toLowerCase().equals("attivo");

                        try (PreparedStatement updateStmt = conn.prepareStatement(
                                "UPDATE possessore SET attivo = ? WHERE id = ?;")) {
                            updateStmt.setBoolean(1, nuovoAttivo);
                            updateStmt.setInt(2, id);
                            updateStmt.executeUpdate();
                        }

                        System.out.println("\nPossessore aggiornato con successo! Nuovo stato: " +
                                (nuovoAttivo ? "attivo" : "non attivo"));
                    } else {
                        System.out.println("Nessuna modifica effettuata.");
                    }
                }
            }

        } catch (SQLException e) {
            System.out.println("Errore nell'aggiornamento del possessore: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.out.println("Errore: inserire un numero valido.");
        }

        waitForKey();
    }

    public void mainMenu() {
        while (true) {
            printHeader("CATASTO STORICO - MENU PRINCIPALE");

            if (!connected) {
                System.out.println("Non sei connesso al database.");
                System.out.println("1. Connetti al database");
                System.out.println("0. Esci");

                System.out.print("\nScelta: ");
                String choice = scanner.nextLine();

                if (choice.equals("1")) {
                    connect();
                } else if (choice.equals("0")) {
                    break;
                } else {
                    System.out.println("Scelta non valida!");
                    waitForKey();
                }
            } else {
                System.out.println("1. Visualizza comuni");
                System.out.println("2. Visualizza partite");
                System.out.println("3. Visualizza possessori");
                System.out.println("4. Visualizza immobili");
                System.out.println("5. Inserisci nuovo possessore");
                System.out.println("6. Inserisci nuova partita");
                System.out.println("7. Genera certificato di proprietà");
                System.out.println("8. Ricerca possessori");
                System.out.println("9. Ricerca immobili");
                System.out.println("10. Aggiorna possessore");
                System.out.println("0. Disconnetti ed esci");

                System.out.print("\nScelta: ");
                String choice = scanner.nextLine();

                switch (choice) {
                    case "1":
                        mostraComuni();
                        break;
                    case "2":
                        mostraPartite();
                        break;
                    case "3":
                        mostraPossessori();
                        break;
                    case "4":
                        mostraImmobili();
                        break;
                    case "5":
                        inserisciPossessore();
                        break;
                    case "6":
                        inserisciPartita();
                        break;
                    case "7":
                        generaCertificato();
                        break;
                    case "8":
                        ricercaPossessori();
                        break;
                    case "9":
                        ricercaImmobili();
                        break;
                    case "10":
                        aggiornaPossessore();
                        break;
                    case "0":
                        disconnect();
                        return;
                    default:
                        System.out.println("Scelta non valida!");
                        waitForKey();
                        break;
                }
            }
        }
    }

    public static void main(String[] args) {
        try {
            // Carica il driver JDBC di PostgreSQL
            Class.forName("org.postgresql.Driver");
        } catch (ClassNotFoundException e) {
            System.out.println("Driver PostgreSQL JDBC non trovato. Assicurati di avere il JAR nel classpath.");
            System.exit(1);
        }

        CatastoApp app = new CatastoApp();
        app.mainMenu();
    }
}