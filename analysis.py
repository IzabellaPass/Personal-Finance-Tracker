import sqlite3

conn = sqlite3.connect("finance.db")
cursor = conn.cursor()

# 💰 TOTAL INCOME
cursor.execute("""
SELECT SUM(amount) FROM transactions WHERE type='income'
""")
income = cursor.fetchone()[0]

# 💸 TOTAL EXPENSES
cursor.execute("""
SELECT SUM(amount) FROM transactions WHERE type='expense'
""")
expense = cursor.fetchone()[0]

print("Total Income:", income)
print("Total Expenses:", expense)
print("Balance:", income - expense)

# 📊 SPENDING BY CATEGORY
cursor.execute("""
SELECT category, SUM(amount)
FROM transactions
WHERE type='expense'
GROUP BY category
ORDER BY SUM(amount) DESC
""")

print("\nExpenses by Category:")
for row in cursor.fetchall():
    print(row)

conn.close()
