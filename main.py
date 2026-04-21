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


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str

class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/")
def root():
    return {"message": "Banking API is running"}


@app.get("/users")
def get_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, full_name, is_admin FROM users;")
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

@app.get("/admin/users-accounts")
def get_all_users_accounts():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            u.id AS user_id,
            u.username,
            u.full_name,
            u.is_admin,
            a.id AS account_id,
            a.account_type,
            a.balance,
            a.account_number
        FROM users u
        LEFT JOIN accounts a ON u.id = a.user_id
        ORDER BY u.id, a.id;
    """)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


@app.post("/register")
def register_user(data: RegisterRequest):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT id FROM users WHERE username = %s;",
            (data.username,)
        )
        existing_user = cur.fetchone()

        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        cur.execute("""
            INSERT INTO users (username, password, full_name)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (data.username, data.password, data.full_name))

        new_user_id = cur.fetchone()[0]

        checking_account_number = f"CHK{10000 + new_user_id}"
        savings_account_number = f"SAV{10000 + new_user_id}"

        cur.execute("""
            INSERT INTO accounts (user_id, account_type, balance, account_number)
            VALUES (%s, %s, %s, %s);
        """, (new_user_id, "checking", 0.00, checking_account_number))

        cur.execute("""
            INSERT INTO accounts (user_id, account_type, balance, account_number)
            VALUES (%s, %s, %s, %s);
        """, (new_user_id, "savings", 0.00, savings_account_number))

        conn.commit()

        return {
            "message": "User created successfully",
            "user_id": new_user_id
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


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


@app.post("/login")
def login_user(data: LoginRequest):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, username, full_name, is_admin
            FROM users
            WHERE username = %s AND password = %s;
        """, (data.username, data.password))

        user = cur.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        return {
            "id": user[0],
            "username": user[1],
            "full_name": user[2],
            "is_admin": user[3]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()