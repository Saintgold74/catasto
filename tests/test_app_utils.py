# tests/test_app_utils.py

import pytest # Importiamo pytest per usare le sue funzionalità avanzate

# Importa le funzioni che vuoi testare dal tuo modulo di utility
# Per questo esempio, modifichiamo leggermente la funzione per essere più robusta
# e gestire anche i tipi di dati non corretti.
#
# # in app_utils.py (versione migliorata):
# def format_full_name(first_name, last_name):
#     """Formatta nome e cognome in 'Cognome Nome', gestendo input non validi."""
#     if not isinstance(first_name, str) or not isinstance(last_name, str):
#         raise TypeError("First name and last name must be strings.")
#     
#     if not first_name and not last_name:
#         return ""
#     return f"{last_name.strip().title()} {first_name.strip().title()}".strip()

from app_utils import format_full_name

# --- Test Parametrizzato per i casi validi ---
# Usiamo @pytest.mark.parametrize per eseguire lo stesso test con tanti dati diversi.
# 'test_input' e 'expected_output' sono i nomi delle variabili che useremo nel test.
@pytest.mark.parametrize("first_name, last_name, expected_output", [
    # Caso standard
    ("Mario", "Rossi", "Rossi Mario"),
    # Caso con spazi extra
    ("  Luigi  ", "  Verdi ", "Verdi Luigi"),
    # Caso con maiuscole/minuscole miste
    ("giuseppe", "BIANCHI", "Bianchi Giuseppe"),
    # Caso con solo cognome
    ("", "Neri", "Neri"),
    # Caso con solo nome
    ("Paolo", "", "Paolo"),
    # Caso con input vuoti
    ("", "", ""),
    # --- Nuovi test "più difficili" (casi limite) ---
    # Nomi con apostrofo
    ("Giovanni", "D'Amico", "D'Amico Giovanni"),
    # Nomi composti (il title() di Python potrebbe non essere perfetto qui, ma testiamo il comportamento)
    ("Anna Maria", "De Luca", "De Luca Anna Maria"),
    # Nomi con trattino
    ("Jean-Luc", "Picard", "Picard Jean-Luc"),
])
def test_format_full_name_valid_cases(first_name, last_name, expected_output):
    """
    Testa una vasta gamma di casi di input validi usando la parametrizzazione.
    """
    assert format_full_name(first_name, last_name) == expected_output


# --- Test per la gestione degli errori (input non validi) ---
@pytest.mark.parametrize("first_name, last_name", [
    (123, "Rossi"),          # Nome non è una stringa
    ("Mario", 456),          # Cognome non è una stringa
    (None, "Verdi"),         # Nome è None
    ("Bianchi", None),       # Cognome è None
    (["Mario"], "Rossi"),    # Nome è una lista
])
def test_format_full_name_invalid_types(first_name, last_name):
    """
    Verifica che la funzione sollevi un'eccezione TypeError quando riceve
    tipi di dati non corretti. 'pytest.raises' è il modo corretto per testare le eccezioni.
    """
    with pytest.raises(TypeError):
        format_full_name(first_name, last_name)

