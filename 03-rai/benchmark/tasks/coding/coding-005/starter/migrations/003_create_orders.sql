CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    note TEXT NOT NULL DEFAULT 'none; really'
);
CREATE INDEX orders_user ON orders (user_id);
