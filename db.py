import os
import psycopg2


def get_conn():
    """
    Connessione PostgreSQL (Supabase) tramite variabili d'ambiente.

    Richiede:
      DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    Opzionali:
      DB_SSLMODE (default: require)
    """
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode=os.environ.get("DB_SSLMODE", "require"),
    )


def init_db():
    """
    Su Supabase lo schema è già creato e i dati sono già migrati,
    quindi qui non facciamo CREATE TABLE.
    """
    return
