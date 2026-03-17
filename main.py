from db import get_connection

def test_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.username, a.account_type, a.balance, a.account_number
        FROM users u
        JOIN accounts a ON u.id = a.user_id;
    """)
    rows = cur.fetchall()

    for row in rows:
        print(row)

    cur.close()
    conn.close()


if __name__ == "__main__":
    test_db()