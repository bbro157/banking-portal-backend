CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    account_type VARCHAR(20),
    balance NUMERIC(12,2),
    account_number VARCHAR(20)
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    from_account_id INT,
    to_account_id INT,
    amount NUMERIC(12,2),
    transaction_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);