# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment (required before running anything)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (extract + transform)
python pipeline.py

# Run stages individually
python extract.py
python transform.py

# Start the Postgres container
docker compose up -d

# Stop the Postgres container
docker compose down
```

## Architecture

Two-stage ELT pipeline: MySQL source → local Postgres (Docker).

**Stage 1 — `extract.py`:** Connects to MySQL at `db.isba.co` and full-reloads three tables (`orders`, `order_items`, `products`) into a `staging` schema in the local Postgres container. Creates the schema and tables on first run. Truncates before each load so re-runs are idempotent.

**Stage 2 — `transform.py`:** Runs a single SQL aggregation inside Postgres: joins `staging.order_items` to `staging.products`, groups by month (`DATE_TRUNC`) and `product_name`, and writes the result to `analytics.monthly_sales_summary`. Also self-bootstrapping via `CREATE SCHEMA/TABLE IF NOT EXISTS`.

**`pipeline.py`:** Calls `extract()` then `transform()` in sequence. No orchestration framework — just two imports.

## Environment

Credentials live in `.env` (gitignored). Copy `.env.example` to `.env` and fill in `MYSQL_PASSWORD`. The Postgres credentials (`postgres/postgres`) are hardcoded in `docker-compose.yml` and `.env.example`.

MySQL connection key in `.env` is `MYSQL_DB` (not `MYSQL_DATABASE`).

## Destination Schema

`analytics.monthly_sales_summary` — the dashboard table consumed by DBeaver:

| Column | Type |
|---|---|
| `year_month` | `DATE` (first of month) |
| `product_name` | `TEXT` |
| `total_revenue` | `NUMERIC(12,2)` |
| `order_count` | `INTEGER` |
| `avg_order_value` | `NUMERIC(10,2)` |

Connect DBeaver to `localhost:5432 / basket_craft / postgres / postgres` to query it.
