import sqlite3

conn = sqlite3.connect("finance.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    date TEXT,
    type TEXT,   -- income / expense
    category TEXT,
    amount REAL
)
""")

data = [
    ("2024-01-01", "expense", "food", 20),
    ("2024-01-02", "expense", "transport", 10),
    ("2024-01-03", "income", "salary", 1000),
    ("2024-01-04", "expense", "entertainment", 50),
    ("2024-01-05", "expense", "food", 30),
]

cursor.executemany(
    "INSERT INTO transactions(date, type, category, amount) VALUES (?, ?, ?, ?)",
    data
)

conn.commit()
conn.close()
