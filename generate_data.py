import sqlite3
import random
import datetime
import os

db_path = os.path.join(os.path.dirname(__file__), "triage.db")

customers = [f"C{i:03d}" for i in range(1, 21)]
currencies = ["EUR", "USD", "TRY", "AED", "JPY"]
transactions = []

today = datetime.date.today()

def days_ago(n):
    return str(today - datetime.timedelta(days=n))

for i in range(200):
    cust = random.choice(customers)
    amt = round(random.uniform(50, 2000), 2)
    tx_date = days_ago(random.randint(0, 60))
    cur = random.choice(currencies)
    transactions.append((cust, amt, tx_date, cur))

transactions.append(("C001", 8500.00, days_ago(5), "USD"))
transactions.append(("C010", 12000.00, days_ago(12), "AED"))

transactions.append(("C021", 2400.00, days_ago(6), "EUR"))
transactions.append(("C021", 2850.00, days_ago(3), "EUR"))

transactions.append(("C022", 150.00, days_ago(6), "TRY"))
transactions.append(("C022", 220.00, days_ago(5), "TRY"))
transactions.append(("C022", 90.00, days_ago(3), "EUR"))
transactions.append(("C022", 300.00, days_ago(2), "TRY"))
transactions.append(("C022", 180.00, days_ago(1), "USD"))

transactions.append(("C023", 300.00, days_ago(30), "EUR"))
transactions.append(("C023", 250.00, days_ago(20), "EUR"))
transactions.append(("C023", 350.00, days_ago(10), "EUR"))
transactions.append(("C023", 1500.00, days_ago(1), "JPY"))

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    customer_id TEXT,
    amount_gbp REAL,
    date TEXT,
    currency TEXT
)
""")

cursor.execute("DELETE FROM transactions")

cursor.executemany("""
INSERT INTO transactions (customer_id, amount_gbp, date, currency)
VALUES (?, ?, ?, ?)
""", transactions)

conn.commit()

cursor.execute("SELECT COUNT(*) FROM transactions")
print(cursor.fetchone())

conn.close()