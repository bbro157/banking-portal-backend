from fastapi import FastAPI
from db import get_connection

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Banking API is running"}

@app.get("/users")
def get_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, full_name FROM users;")
    users = cur.fetchall()

    cur.close()
    conn.close()

    return users

@app.get("/accounts/{user_id}")
def get_accounts(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, account_type, balance, account_number
        FROM accounts
        WHERE user_id = %s;
    """, (user_id,))
    accounts = cur.fetchall()

    cur.close()
    conn.close()

    return accounts

@app.get("/transactions/{account_id}")
def get_transactions(account_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, from_account_id, to_account_id, amount, transaction_type, created_at
        FROM transactions
        WHERE from_account_id = %s OR to_account_id = %s
        ORDER BY created_at DESC;
    """, (account_id, account_id))
    transactions = cur.fetchall()

    cur.close()
    conn.close()

    return transactions