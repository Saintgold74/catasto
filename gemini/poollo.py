import psycopg2
print(hasattr(psycopg2, 'pool'))
# Se hasattr restituisce True, prova:
from psycopg2 import pool
print(pool)