CREATE UNIQUE INDEX users_email ON users (email);
INSERT INTO users (email, created_at) VALUES ('system@example.com', '2026-01-01T00:00:00Z');
