# --- Nomi per le chiavi di QSettings (definisci globalmente o prima di run_gui_app) ---
SETTINGS_DB_TYPE = "Database/Type"
SETTINGS_DB_HOST = "Database/Host"
SETTINGS_DB_PORT = "Database/Port"
SETTINGS_DB_NAME = "Database/DBName"
SETTINGS_DB_USER = "Database/User"
SETTINGS_DB_SCHEMA = "Database/Schema"
# Non salviamo la password in QSettings
# Non usato, ma definito per completezza
SETTINGS_DB_PASSWORD = "Database/Password"

COLONNE_POSSESSORI_DETTAGLI_NUM = 6
COLONNE_POSSESSORI_DETTAGLI_LABELS = [
    "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]
# Costanti per la configurazione delle tabelle dei possessori, se usate in più punti
# Scegli nomi specifici se diverse tabelle hanno diverse configurazioni
# Esempio: ID, Nome Compl, Paternità, Comune, Num. Partite
COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = [
    "ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]

# Per InserimentoPossessoreWidget, se la sua tabella è diversa:
# Esempio: ID, Nome Completo, Paternità, Comune
COLONNE_INSERIMENTO_POSSESSORI_NUM = 4
COLONNE_INSERIMENTO_POSSESSORI_LABELS = [
    "ID", "Nome Completo", "Paternità", "Comune Riferimento"]

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome",
                              "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]
# Nomi per le chiavi di QSettings (globali o definite prima di run_gui_app)
