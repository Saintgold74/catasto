# utils/logger_setup.py
import logging
import sys
import os

def setup_logging(log_directory="logs", log_file_name="app_catasto.log", app_logger_name="CatastoAppLogger", db_logger_name="CatastoDBLogger", level=logging.INFO):
    """
    Configura i logger per l'applicazione e per il gestore del database.
    Crea una directory 'logs' se non esiste.
    """
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    full_log_path = os.path.join(log_directory, log_file_name)

    # Formatter standard
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Logger principale dell'applicazione
    app_logger = logging.getLogger(app_logger_name)
    if not app_logger.hasHandlers(): # Evita di aggiungere handler multipli se chiamato più volte
        app_logger.setLevel(level)
        # Handler per file per app_logger
        app_fh = logging.FileHandler(full_log_path)
        app_fh.setFormatter(formatter)
        app_logger.addHandler(app_fh)
        # Handler per console per app_logger
        app_sh = logging.StreamHandler(sys.stdout)
        app_sh.setFormatter(formatter)
        app_logger.addHandler(app_sh)

    # Logger specifico per il Database Manager
    db_logger = logging.getLogger(db_logger_name)
    if not db_logger.hasHandlers():
        db_logger.setLevel(level) # O un livello diverso se necessario, es. logging.DEBUG per query
        # Handler per file per db_logger (può loggare nello stesso file o in uno separato)
        db_fh = logging.FileHandler(full_log_path) # Stesso file per semplicità
        db_fh.setFormatter(formatter)
        db_logger.addHandler(db_fh)
        # Handler per console per db_logger
        db_sh = logging.StreamHandler(sys.stdout)
        db_sh.setFormatter(formatter)
        db_logger.addHandler(db_sh)
        # Impedisci la propagazione al root logger se vuoi un controllo più fine
        # app_logger.propagate = False
        # db_logger.propagate = False

    # Puoi restituire il logger principale dell'app se necessario altrove
    return app_logger