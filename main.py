from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import get_connection
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float


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


@app.post("/transfer")
def transfer_money(data: TransferRequest):
    conn = get_connection()
    cur = conn.cursor()

    try:
        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        cur.execute("SELECT balance FROM accounts WHERE id = %s;", (data.from_account_id,))
        from_result = cur.fetchone()

        cur.execute("SELECT balance FROM accounts WHERE id = %s;", (data.to_account_id,))
        to_result = cur.fetchone()

        if not from_result:
            raise HTTPException(status_code=404, detail="From account not found")
        if not to_result:
            raise HTTPException(status_code=404, detail="To account not found")

        from_balance = from_result[0]

        if from_balance < data.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        cur.execute("""
            UPDATE accounts
            SET balance = balance - %s
            WHERE id = %s;
        """, (data.amount, data.from_account_id))

        cur.execute("""
            UPDATE accounts
            SET balance = balance + %s
            WHERE id = %s;
        """, (data.amount, data.to_account_id))

        cur.execute("""
            INSERT INTO transactions (from_account_id, to_account_id, amount, transaction_type, created_at)
            VALUES (%s, %s, %s, 'transfer', CURRENT_TIMESTAMP);
        """, (data.from_account_id, data.to_account_id, data.amount))

        conn.commit()

        return {"message": "Transfer successful"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()