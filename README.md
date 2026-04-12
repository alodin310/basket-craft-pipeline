# Basket Craft Sales Pipeline

An ELT pipeline that extracts sales data from the Basket Craft MySQL database and loads it into two destinations:

- **AWS RDS PostgreSQL** — all 8 raw tables (1.7M rows) in a `raw` schema, loaded by `extract_rds.py`
- **Local PostgreSQL (Docker)** — 3 tables transformed into a monthly sales summary, loaded and aggregated by `pipeline.py`

**Local output:** `analytics.monthly_sales_summary` — revenue, order count, and average order value by product and month, queryable in DBeaver.

---

## Prerequisites

- Python 3.11+
- Docker Desktop (local pipeline only)

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

Open `.env` and fill in `MYSQL_PASSWORD`. For the RDS pipeline, also add `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, and `RDS_DATABASE`.

**3. Start the Postgres container**

```bash
docker compose up -d
```

---

## Running the Pipelines

### RDS Pipeline (MySQL → AWS RDS)

```bash
source .venv/bin/activate
python extract_rds.py
```

Loads all 8 raw tables into the `raw` schema on AWS RDS. Re-runnable — drops and recreates each table on every run.

Expected output:
```
  raw.employees: 20 rows loaded
  raw.order_item_refunds: 1,731 rows loaded
  raw.order_items: 40,025 rows loaded
  raw.orders: 32,313 rows loaded
  raw.products: 4 rows loaded
  raw.users: 31,696 rows loaded
  raw.website_pageviews: 1,188,124 rows loaded
  raw.website_sessions: 472,871 rows loaded
Extract to RDS complete.
```

### Local Pipeline (MySQL → Docker Postgres)

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
├── extract_rds.py      # RDS pipeline: MySQL → AWS RDS (all 8 tables)
├── extract.py          # Local pipeline stage 1: MySQL → staging schema
├── transform.py        # Local pipeline stage 2: staging → analytics mart
├── pipeline.py         # Local pipeline orchestrator
├── docker-compose.yml  # Postgres 15 container (local pipeline)
├── requirements.txt
└── .env.example        # Credential template
```
