from fastapi import FastAPI, HTTPException, Depends
from db import get_connection
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

app = FastAPI()

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_token(username: str):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_admin(current_user: str = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT is_admin
            FROM users
            WHERE username = %s;
        """, (current_user,))
        result = cur.fetchone()

        if not result or not result[0]:
            raise HTTPException(status_code=403, detail="Admin access required")

        return current_user
    finally:
        cur.close()
        conn.close()


class SignupRequest(BaseModel):
    username: str
    password: str
    full_name: str
    is_admin: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float


@app.get("/")
def root():
    return {"message": "Banking API is running"}


@app.post("/signup")
def signup(data: SignupRequest):
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        hashed_pw = hash_password(data.password)

        cur.execute("""
            INSERT INTO users (username, password, full_name, is_admin)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, full_name, is_admin;
        """, (data.username, hashed_pw, data.full_name, data.is_admin))

        user = cur.fetchone()
        conn.commit()

        return {
            "message": "User created successfully",
            "user": user
        }

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/login")
def login(data: LoginRequest):
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, password
            FROM users
            WHERE username = %s;
        """, (data.username,))
        user = cur.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id, username, hashed_password = user

        if not verify_password(data.password, hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token(username)

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.get("/users")
def get_users(current_user: str = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, full_name, is_admin FROM users;")
    users = cur.fetchall()

    cur.close()
    conn.close()

    return users


@app.get("/admin/users")
def admin_get_users(admin: str = Depends(get_current_admin)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, full_name, is_admin FROM users;")
    users = cur.fetchall()

    cur.close()
    conn.close()

    return users


@app.get("/accounts/{user_id}")
def get_accounts(user_id: int, current_user: str = Depends(get_current_user)):
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
def get_transactions(account_id: int, current_user: str = Depends(get_current_user)):
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
def transfer_money(data: TransferRequest, current_user: str = Depends(get_current_user)):
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")

        cur.execute("SELECT balance FROM accounts WHERE id = %s;", (data.from_account_id,))
        from_account = cur.fetchone()

        cur.execute("SELECT balance FROM accounts WHERE id = %s;", (data.to_account_id,))
        to_account = cur.fetchone()

        if not from_account or not to_account:
            raise HTTPException(status_code=404, detail="Account not found")

        from_balance = from_account[0]

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
            INSERT INTO transactions (from_account_id, to_account_id, amount, transaction_type)
            VALUES (%s, %s, %s, %s);
        """, (data.from_account_id, data.to_account_id, data.amount, "transfer"))

        conn.commit()

        return {"message": "Transfer completed successfully"}

    except HTTPException:
        if conn:
            conn.rollback()
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.get("/search")
def search_users(query: str, current_user: str = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, full_name, is_admin
        FROM users
        WHERE username ILIKE %s
        OR full_name ILIKE %s;
    """, (f"%{query}%", f"%{query}%"))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return results
