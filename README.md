# AML Transaction-Monitoring Triage Tool

A small Python tool that checks transactions against four anti-money-laundering (AML) monitoring rules. It uses the Anthropic API to write a short, plain-English narrative for each flag and saves every result to an audit log.

> **This project uses synthetic (made-up) data only.** No real customers or transactions are involved.

## What it does

- **`generate_data.py`** creates about 200 random transactions for made-up customers (C001–C020). It also adds a few hand-made cases so each rule has something to catch. They are saved in a SQLite database (`triage.db`), in a `transactions` table.
- **`rules.py`** runs four SQL-based rules:
  1. **High value**: a transaction over £7,000.
  2. **Velocity**: more than 3 transactions by one customer in the last 7 days.
  3. **Structuring**: 2 or more transactions between £2,000 and £3,000 by one customer in the last 7 days.
  4. **Unusual**: a customer's latest transaction is more than 50% above the average of their previous three.

  For each flag, it asks Claude (model `claude-haiku-5-5`) for a 2–3 sentence neutral narrative. The prompt tells it to use only the facts provided. Each flag and its narrative is saved to an `audit_log` table.

## How to run it

1. Install Python 3, then install the libraries:
   ```
   pip install -r requirements.txt
   ```
2. Set your Anthropic API key. Create a file called `.env` in this folder containing:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```
   The `.env` file is listed in `.gitignore`, so it is never uploaded to GitHub.
3. Create the synthetic data:
   ```
   python generate_data.py
   ```
4. Run the rules and write the narratives:
   ```
   python rules.py
   ```
   Each flag is printed with its narrative, followed by the total number of rows in the audit log.

## Tech used

- Python
- SQLite (`sqlite3`) and SQL queries
- Anthropic API (`anthropic` Python library)
- `python-dotenv` for loading the API key from `.env`

## What I learned

