# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment (required before running anything)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# --- Local pipeline (MySQL → Docker Postgres) ---
python pipeline.py        # full pipeline (extract + transform)
python extract.py         # extract only (3 tables → staging schema)
python transform.py       # transform only (staging → analytics mart)

docker compose up -d      # start local Postgres container
docker compose down       # stop it

# --- RDS pipeline (MySQL → AWS RDS PostgreSQL) ---
python extract_rds.py     # extract all 8 tables → raw schema on RDS

# --- Snowflake pipeline (RDS PostgreSQL → Snowflake) ---
python load_snowflake.py  # load all 8 raw tables from RDS into Snowflake basket_craft.raw

# --- Tests ---
pytest                    # run unit tests (3 tests, no live connections needed)
```

## Architecture

This repo contains two independent ELT pipelines sharing the same MySQL source.

### Pipeline 1 — Local (Docker Postgres)

`extract.py` → `transform.py`, orchestrated by `pipeline.py`.

- **Extract:** Full-reloads 3 tables (`orders`, `order_items`, `products`) from MySQL into a `staging` schema on the local Postgres container. Truncates before each load (idempotent).
- **Transform:** Single SQL aggregation — joins `staging.order_items` to `staging.products`, groups by month (`DATE_TRUNC`) and `product_name`, writes to `analytics.monthly_sales_summary`.
- **DBeaver connection:** `localhost:5432 / basket_craft / postgres / postgres`

`analytics.monthly_sales_summary` schema:

| Column | Type |
|---|---|
| `year_month` | `DATE` (first of month) |
| `product_name` | `TEXT` |
| `total_revenue` | `NUMERIC(12,2)` |
| `order_count` | `INTEGER` |
| `avg_order_value` | `NUMERIC(10,2)` |

### Pipeline 2 — RDS (AWS PostgreSQL)

`extract_rds.py` — standalone script, no transform stage yet.

- Full-reloads all 8 MySQL tables into the `raw` schema on AWS RDS. Drops and recreates each table on every run (idempotent).
- Introspects MySQL column types via `DESCRIBE` and maps them to Postgres types using `map_type()`. Falls back to `TEXT` for unmapped types.
- Streams rows in chunks of 5000 (`fetchmany`) to avoid loading large tables (e.g., `website_pageviews`: 1.1M rows) into memory. Inserts via `execute_values` with `page_size=5000`.
- Reconnects to MySQL per table to avoid connection timeouts on large loads.

### Pipeline 3 — Snowflake (RDS PostgreSQL → Snowflake)

`load_snowflake.py` — standalone script, no transform stage.

- Reads all 8 tables from the `raw` schema on AWS RDS into pandas DataFrames (in-memory, no chunking needed).
- Forces all column names to lowercase for Snowflake identifier safety (critical for dbt compatibility).
- Writes to `basket_craft.raw` on Snowflake using `write_pandas(..., overwrite=True, auto_create_table=True)`. Fully idempotent — drop+recreate on every run.
- Uses `SNOWFLAKE_*` env vars from `.env`.
- **Snowsight:** Log in at app.snowflake.com → Data → Databases → BASKET_CRAFT → RAW

## Environment

Credentials live in `.env` (gitignored). Copy `.env.example` to `.env` and fill in values.

Two credential groups in `.env`:

- **MySQL** — `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` (note: `MYSQL_DB` not `MYSQL_DATABASE`)
- **Local Postgres** — `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD` (hardcoded `postgres/postgres` in `docker-compose.yml`)
- **RDS** — `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, `RDS_DATABASE`
- **Snowflake** — `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`

The RDS instance's security group must have an inbound rule allowing TCP port 5432 from your current IP.
