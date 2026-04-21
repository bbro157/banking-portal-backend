INSERT INTO users (username, password, full_name, is_admin)
VALUES
('dev', 'dev123', 'Developer Admin', TRUE),
('alice', 'password123', 'Alice Johnson', FALSE),
('bob', 'password123', 'Bob Smith', FALSE);

INSERT INTO accounts (user_id, account_type, balance, account_number)
VALUES
(2, 'checking', 1500.00, 'CHK10001'),
(2, 'savings', 3000.00, 'SAV10001'),
(3, 'checking', 800.00, 'CHK10002');
(3, 'savings', 1200.00, 'SAV10002');

INSERT INTO transactions (from_account_id, to_account_id, amount, transaction_type, created_at)
VALUES
(NULL, 1, 1500.00, 'deposit', CURRENT_TIMESTAMP),
(NULL, 2, 3000.00, 'deposit', CURRENT_TIMESTAMP),
(NULL, 3, 800.00, 'deposit', CURRENT_TIMESTAMP),
(1, 3, 200.00, 'transfer', CURRENT_TIMESTAMP);