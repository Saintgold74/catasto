// CatastoApp.java
import java.sql.*;
import java.util.Scanner;

public class CatastoApp {
    // Configura i parametri di connessione al database
    private static final String DB_URL = "jdbc:postgresql://localhost:5432/catasto_storico";
    private static final String USER = "postgres";
    private static final String PASS = "Markus74"; // Cambia con la tua password

    private Connection conn = null;
    private Scanner scanner = new Scanner(System.in);

    public static void main(String[] args) {
        CatastoApp app = new CatastoApp();
        app.start();
    }

    public void start() {
        try {
            // Inizializza la connessione
            Class.forName("org.postgresql.Driver");
            conn = DriverManager.getConnection(DB_URL, USER, PASS);
            
            // Imposta lo schema corretto
            Statement stmt = conn.createStatement();
            stmt.execute("SET search_path TO catasto");
            
            System.out.println("Connessione al database stabilita con successo!");
            
            // Mostra il menu principale
            boolean exit = false;
            while (!exit) {
                displayMainMenu();
                int choice = readIntChoice();
                
                switch (choice) {
                    case 0:
                        exit = true;
                        break;
                    case 1:
                        generatePropertyCertificate();
                        break;
                    case 2:
                        generateGenealogyReport();
                        break;
                    case 3:
                        generateOwnerReport();
                        break;
                    case 4:
                        verifyDatabaseIntegrity();
                        break;
                    case 5:
                        repairDatabaseProblems();
                        break;
                    case 6:
                        backupDatabase();
                        break;
                    default:
                        System.out.println("Opzione non valida. Riprova.");
                }
                
                if (!exit) {
                    System.out.println("\nPremi INVIO per continuare...");
                    scanner.nextLine();
                }
            }
            
            System.out.println("Uscita dal programma.");
            
        } catch (Exception e) {
            System.err.println("Errore: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // Chiudi la connessione
            try {
                if (conn != null) conn.close();
            } catch (SQLException e) {
                System.err.println("Errore nella chiusura della connessione: " + e.getMessage());
            }
            scanner.close();
        }
    }

    private void displayMainMenu() {
        System.out.println("\n============================================================");
        System.out.println("                 SISTEMA CATASTO STORICO                   ");
        System.out.println("============================================================");
        System.out.println("");
        System.out.println("1) Visualizzare un certificato di proprietà");
        System.out.println("2) Generare report genealogico di una proprietà");
        System.out.println("3) Generare report storico di un possessore");
        System.out.println("4) Verificare integrità del database");
        System.out.println("5) Riparare problemi del database");
        System.out.println("6) Creare backup dei dati");
        System.out.println("0) Uscire");
        System.out.println("");
        System.out.print("Inserire il numero dell'opzione desiderata: ");
    }

    private int readIntChoice() {
        try {
            int choice = Integer.parseInt(scanner.nextLine());
            return choice;
        } catch (NumberFormatException e) {
            return -1; // Valore non valido
        }
    }

    private void generatePropertyCertificate() {
        try {
            System.out.print("Inserisci l'ID della partita: ");
            int partitaId = Integer.parseInt(scanner.nextLine());
            
            // Chiama la funzione del database
            CallableStatement stmt = conn.prepareCall("{ ? = call genera_certificato_proprieta(?) }");
            stmt.registerOutParameter(1, Types.VARCHAR);
            stmt.setInt(2, partitaId);
            stmt.execute();
            
            // Ottieni il risultato
            String result = stmt.getString(1);
            System.out.println("\nCERTIFICATO DI PROPRIETÀ:");
            System.out.println(result);
            
        } catch (SQLException e) {
            System.err.println("Errore SQL: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.err.println("Inserire un numero valido per l'ID della partita.");
        }
    }

    private void generateGenealogyReport() {
        try {
            System.out.print("Inserisci l'ID della partita: ");
            int partitaId = Integer.parseInt(scanner.nextLine());
            
            // Chiama la funzione del database
            CallableStatement stmt = conn.prepareCall("{ ? = call genera_report_genealogico(?) }");
            stmt.registerOutParameter(1, Types.VARCHAR);
            stmt.setInt(2, partitaId);
            stmt.execute();
            
            // Ottieni il risultato
            String result = stmt.getString(1);
            System.out.println("\nREPORT GENEALOGICO:");
            System.out.println(result);
            
        } catch (SQLException e) {
            System.err.println("Errore SQL: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.err.println("Inserire un numero valido per l'ID della partita.");
        }
    }

    private void generateOwnerReport() {
        try {
            System.out.print("Inserisci l'ID del possessore: ");
            int possessoreId = Integer.parseInt(scanner.nextLine());
            
            // Chiama la funzione del database
            CallableStatement stmt = conn.prepareCall("{ ? = call genera_report_possessore(?) }");
            stmt.registerOutParameter(1, Types.VARCHAR);
            stmt.setInt(2, possessoreId);
            stmt.execute();
            
            // Ottieni il risultato
            String result = stmt.getString(1);
            System.out.println("\nREPORT POSSESSORE:");
            System.out.println(result);
            
        } catch (SQLException e) {
            System.err.println("Errore SQL: " + e.getMessage());
        } catch (NumberFormatException e) {
            System.err.println("Inserire un numero valido per l'ID del possessore.");
        }
    }

    private void verifyDatabaseIntegrity() {
        try {
            // Chiama la procedura del database
            CallableStatement stmt = conn.prepareCall("{ call verifica_integrita_database(?) }");
            stmt.registerOutParameter(1, Types.BOOLEAN);
            stmt.execute();
            
            boolean problemiTrovati = stmt.getBoolean(1);
            System.out.println("\nVERIFICA INTEGRITÀ DATABASE:");
            System.out.println("Problemi trovati: " + (problemiTrovati ? "Sì" : "No"));
            System.out.println("Controlla i log del database per i dettagli.");
            
        } catch (SQLException e) {
            System.err.println("Errore SQL: " + e.getMessage());
        }
    }

    private void repairDatabaseProblems() {
        try {
            System.out.print("Confermi la riparazione automatica dei problemi? (s/n): ");
            String confirm = scanner.nextLine();
            
            if (confirm.equalsIgnoreCase("s")) {
                // Chiama la procedura del database
                CallableStatement stmt = conn.prepareCall("{ call ripara_problemi_database(?) }");
                stmt.setBoolean(1, true); // Abilita la correzione automatica
                stmt.execute();
                
                System.out.println("\nRIPARAZIONE DATABASE:");
                System.out.println("Procedura di riparazione completata.");
                System.out.println("Controlla i log del database per i dettagli.");
            } else {
                System.out.println("Riparazione annullata.");
            }
            
        } catch (SQLException e) {
            System.err.println("Errore SQL: " + e.getMessage());
        }
    }

    private void backupDatabase() {
        try {
            System.out.print("Inserisci la directory di destinazione (o premi INVIO per il default): ");
            String directory = scanner.nextLine();
            
            // Usa il valore predefinito se vuoto
            if (directory.trim().isEmpty()) {
                directory = "/tmp";
            }
            
            // Chiama la procedura del database
            CallableStatement stmt = conn.prepareCall("{ call backup_logico_dati(?, ?) }");
            stmt.setString(1, directory);
            stmt.setString(2, "catasto_backup");
            stmt.execute();
            
            System.out.println("\nBACKUP DATABASE:");
            System.out.println("Procedura di backup completata.");
            System.out.println("Controlla i log del database per i dettagli.");
            
        } catch (SQLException e) {
            System.err.println("Errore SQL: " + e.getMessage());
        }
    }
}