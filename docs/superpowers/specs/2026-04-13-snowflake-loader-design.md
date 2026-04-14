# Design Spec: RDS → Snowflake Loader

**Date:** 2026-04-13  
**Author:** Anders  
**Status:** Approved

---

## Overview

Write a Python script (`load_snowflake.py`) that reads all 8 raw Basket Craft tables from the `raw` schema on AWS RDS PostgreSQL and loads them into the `basket_craft.raw` schema on Snowflake. This is the "L" in ELT — no transformations, raw data only.

---

## Architecture

```
AWS RDS PostgreSQL          Python Script             Snowflake
(basket_craft / raw)    (load_snowflake.py)      (basket_craft.raw)
  ┌─────────────┐         ┌──────────────┐         ┌─────────────┐
  │ raw.orders  │──read──▶│ pandas read  │──write──▶│ raw.orders  │
  │ raw.products│         │ DataFrame    │  pandas  │ raw.products│
  │ raw.users   │         │ lowercase    │ overwrite│ raw.users   │
  │ ... (8 tbl) │         │ columns      │          │ ... (8 tbl) │
  └─────────────┘         └──────────────┘         └─────────────┘
         ↑                       ↑
     .env (RDS_*)           .env (SNOWFLAKE_*)
```

---

## Tables

All 8 raw tables from `raw` schema on RDS, loaded as-is into `basket_craft.raw` on Snowflake:

- `employees`
- `order_item_refunds`
- `order_items`
- `orders`
- `products`
- `users`
- `website_pageviews`
- `website_sessions`

---

## Key Design Decisions

### Chunking strategy
Load each table fully into memory as a pandas DataFrame. The largest table (`website_pageviews`, ~1.1M rows) fits comfortably in memory. No chunking required.

### Idempotency
Use `write_pandas(..., overwrite=True, auto_create_table=True)`. This drops and recreates the Snowflake target table on every run. Running the script twice produces identical results. No manual `TRUNCATE` needed.

### Identifier casing
All table names and column names are **lowercase, unquoted** everywhere in the code. Snowflake folds unquoted identifiers to uppercase internally, but the connector handles this transparently when casing is consistent across the entire pipeline. Using lowercase now prevents the #1 dbt failure in Session 04, where dbt also uses lowercase unquoted identifiers.

---

## Approach

Use `snowflake.connector.pandas_tools.write_pandas()`. Under the hood, this serializes the DataFrame to Parquet, uploads it to a Snowflake-managed internal stage, and fires `COPY INTO`. It is fast, parallelizes reads, and is the canonical Snowflake ingestion method from Python.

Alternatives considered:
- Manual `CREATE TABLE` + `executemany`: more code, slower, no parallelism.
- `sqlalchemy-snowflake` + `df.to_sql()`: extra dependency, less control.

---

## Data Flow (per table)

1. `pd.read_sql(f"SELECT * FROM raw.{table}", rds_conn)` — read full table into DataFrame
2. `df.columns = [c.lower() for c in df.columns]` — force lowercase column names
3. `write_pandas(sf_conn, df, table_name=table, database="basket_craft", schema="raw", overwrite=True, auto_create_table=True)` — write to Snowflake
4. Print row count confirmation

---

## Credentials

Read from `.env` via `python-dotenv`. Never hardcoded.

**RDS (existing):**
- `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, `RDS_DATABASE`

**Snowflake (new in Session 03):**
- `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE` (`basket_craft`), `SNOWFLAKE_SCHEMA` (`raw`)

---

## New File

| File | Purpose |
|------|---------|
| `load_snowflake.py` | Standalone script: RDS raw → Snowflake raw |

---

## Dependencies to Add to `requirements.txt`

- `snowflake-connector-python` — Snowflake Python connector (includes `write_pandas`)
- `pandas` — DataFrame for in-memory reads and writes
- `sqlalchemy` — required by `pandas.read_sql` for database URIs

---

## Error Handling

- Missing env vars → `KeyError` at startup (fast-fail before any connection is made)
- Connection failures → connector raises natively, no silent swallowing
- No retry logic — script is idempotent, re-run is safe

---

## Success Criteria

- All 8 tables present in Snowflake `basket_craft.raw`
- Row counts in Snowflake match row counts in RDS exactly
- Script can be run twice with identical results (idempotent)
- No credentials in any `.py` file
- All identifiers lowercase and unquoted
