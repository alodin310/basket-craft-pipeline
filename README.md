# Basket Craft Sales Pipeline

A two-stage ELT pipeline that extracts sales data from the Basket Craft MySQL database, loads it into a local PostgreSQL instance, and transforms it into a monthly sales summary for dashboard analysis.

**Output:** `analytics.monthly_sales_summary` — revenue, order count, and average order value by product and month, queryable in DBeaver.

---

## Prerequisites

- Python 3.11+
- Docker Desktop

---

## Setup

**1. Clone and create a virtual environment**

```bash
git clone https://github.com/alodin310/basket-craft-pipeline.git
cd basket-craft-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure credentials**

```bash
cp .env.example .env
```

Open `.env` and set `MYSQL_PASSWORD` to the course database password.

**3. Start the Postgres container**

```bash
docker compose up -d
```

---

## Running the Pipeline

```bash
source .venv/bin/activate
python pipeline.py
```

Expected output:
```
=== Basket Craft Pipeline ===

[1/2] Extract: MySQL → staging
  staging.orders: 32313 rows loaded
  staging.order_items: 40025 rows loaded
  staging.products: 4 rows loaded
Extract complete.

[2/2] Transform: staging → analytics
  analytics.monthly_sales_summary: 94 rows written
Transform complete.

Pipeline complete.
```

The pipeline is idempotent — safe to re-run at any time.

---

## Querying Results in DBeaver

Add a new PostgreSQL connection in DBeaver:

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `basket_craft` |
| Username | `postgres` |
| Password | `postgres` |

Then query the dashboard table:

```sql
SELECT * FROM analytics.monthly_sales_summary
ORDER BY year_month, product_name;
```

---

## Project Structure

```
├── extract.py          # Stage 1: MySQL → staging schema
├── transform.py        # Stage 2: staging → analytics mart
├── pipeline.py         # Orchestrator
├── docker-compose.yml  # Postgres 15 container
├── requirements.txt
├── .env.example        # Credential template
└── docs/
    └── superpowers/
        ├── specs/      # Design document
        └── plans/      # Implementation plan
```
