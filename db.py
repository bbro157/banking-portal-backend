import psycopg

def get_connection():
    return psycopg.connect(
        host="localhost",
        dbname="banking_portal",
        user="postgres",
        password="password",
        port=5432
    )