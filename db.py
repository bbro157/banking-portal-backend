import psycopg

def get_connection():
    return psycopg.connect(
        host="localhost",
        dbname="banking_portal",
        user="taylormanuel",
        port=5432
    )
