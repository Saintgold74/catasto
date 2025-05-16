# File: genera_hash.py
import bcrypt
import getpass

# Chiedi la password in modo sicuro (non verrà mostrata a schermo)
password_in_chiaro = getpass.getpass("Inserisci la password per l'utente admin di default: ")

# Codifica la password in bytes (bcrypt lavora con bytes)
password_bytes = password_in_chiaro.encode('utf-8')

# Genera il salt
salt = bcrypt.gensalt()

# Crea l'hash
hashed_password = bcrypt.hashpw(password_bytes, salt)

# Stampa l'hash decodificato in formato stringa (da copiare nello script SQL)
print("\n=====================================================================")
print("Hash Bcrypt generato (da copiare nello script SQL):")
print(hashed_password.decode('utf-8'))
print("=====================================================================\n")