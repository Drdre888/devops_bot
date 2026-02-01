CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phone_numbers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO emails (email) VALUES 
    ('test@example.com'),
    ('admin@company.org')
ON CONFLICT (email) DO NOTHING;

INSERT INTO phone_numbers (phone_number) VALUES 
    ('89161234567'),
    ('+79267654321')
ON CONFLICT (phone_number) DO NOTHING;

CREATE USER repl_user WITH REPLICATION ENCRYPTED PASSWORD '123';
