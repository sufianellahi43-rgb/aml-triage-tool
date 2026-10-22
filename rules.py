import sqlite3
import os
from typing import Literal
from dotenv import load_dotenv
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

db_path = os.path.join(os.path.dirname(__file__), "triage.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


class FlagNarrative(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    narrative: str


cursor.execute("""
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    customer_id TEXT,
    flag_type TEXT,
    details TEXT,
    narrative TEXT,
    risk_level TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

def check_high_value():
    cursor.execute("""
    SELECT customer_id, amount_gbp, date, currency
    FROM transactions
    WHERE amount_gbp > 7000
    """)
    return cursor.fetchall()

def check_velocity():
    cursor.execute("""
    SELECT customer_id, COUNT(*) AS transaction_count
    FROM transactions
    WHERE date >= date('now', '-7 days')
    GROUP BY customer_id
    HAVING transaction_count > 3
    """)
    return cursor.fetchall()

def check_structuring():
    cursor.execute("""
    SELECT customer_id, COUNT(*) AS transaction_count
    FROM transactions
    WHERE amount_gbp BETWEEN 2000 AND 3000
      AND date >= date('now', '-7 days')
    GROUP BY customer_id
    HAVING transaction_count >= 2
    """)
    return cursor.fetchall()

def check_unusual():
    cursor.execute("""
    SELECT customer_id, amount_gbp, date
    FROM transactions
    ORDER BY customer_id, date
    """)
    rows = cursor.fetchall()

    by_customer = {}
    for customer, amount, date in rows:
        by_customer.setdefault(customer, []).append((amount, date))

    flags = []
    for customer, txs in by_customer.items():
        if len(txs) < 4:
            continue

        latest_amount, latest_date = txs[-1]
        previous_three = txs[-4:-1]
        average = sum(a for a, d in previous_three) / len(previous_three)

        if latest_amount > average * 1.5:
            flags.append((customer, latest_amount, latest_date, round(average, 2)))

    return flags

def write_narrative(prompt):
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=400,
        system="You are a compliance analyst at a UK foreign exchange retailer. Write in a neutral, factual tone. A flag means a transaction pattern matched a monitoring rule; it is not an accusation. Only use the details provided. Do not describe any actions, outcomes or customer motives that are not in the data. Reply ONLY with JSON, no other text, in this format: {\"risk_level\": \"...\", \"narrative\": \"...\"}. risk_level must be exactly \"low\", \"medium\" or \"high\".",
        messages=[{"role": "user", "content": prompt}]
    )
    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text
    try:
        return FlagNarrative.model_validate_json(text)
    except ValidationError:
        print("Reply failed validation:", text)
        return None

def log_flag(customer, flag_type, details, narrative, risk_level):
    cursor.execute("""
    INSERT INTO audit_log (customer_id, flag_type, details, narrative, risk_level)
    VALUES (?, ?, ?, ?, ?)
    """, (customer, flag_type, details, narrative, risk_level))
    conn.commit()

def process_flag(customer, flag_type, details, prompt):
    result = write_narrative(prompt)
    if result is None:
        log_flag(customer, flag_type, details, "LLM reply failed validation", "unknown")
        return
    print(customer, "|", flag_type, "|", result.risk_level, "|", result.narrative, "\n")
    log_flag(customer, flag_type, details, result.narrative, result.risk_level)

for customer, amount, date, currency in check_high_value():
    prompt = f"""Customer {customer} spent £{amount} buying {currency} on {date}.
This matched the high-value rule, which flags any transaction over £7,000.
Write a short narrative (2-3 sentences) explaining why it was flagged, using only these details."""
    process_flag(customer, "High value", f"£{amount} buying {currency} on {date}", prompt)

for customer, count in check_velocity():
    prompt = f"""Customer {customer} made {count} transactions in the last 7 days.
This matched the velocity rule, which flags more than 3 transactions by the same customer within 7 days.
Write a short narrative (2-3 sentences) explaining why it was flagged, using only these details."""
    process_flag(customer, "Velocity", f"{count} transactions in the last 7 days", prompt)

for customer, count in check_structuring():
    prompt = f"""Customer {customer} made {count} transactions of between £2,000 and £3,000 in the last 7 days.
This matched the structuring rule, which flags 2 or more transactions in that range by the same customer within 7 days.
Write a short narrative (2-3 sentences) explaining why it was flagged, using only these details."""
    process_flag(customer, "Structuring", f"{count} transactions of £2,000-£3,000 in the last 7 days", prompt)

for customer, amount, date, average in check_unusual():
    prompt = f"""Customer {customer} made a transaction of £{amount} on {date}.
The average of their previous three transactions was £{average}.
This matched the unusual transaction rule, which flags a transaction more than 50% above the customer's average of their previous three.
Write a short narrative (2-3 sentences) explaining why it was flagged, using only these details."""
    process_flag(customer, "Unusual", f"£{amount} on {date}, previous three average £{average}", prompt)

cursor.execute("SELECT COUNT(*) FROM audit_log")
print("Rows in audit log:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM audit_log WHERE risk_level = 'unknown'")
print("Replies that failed validation:", cursor.fetchone()[0])

conn.close()