# Basket Craft Sales Pipeline — Design Spec

**Date:** 2026-04-03
**Project:** basket-craft-pipeline
**Goal:** Monthly sales dashboard with revenue, order count, and average order value (AOV) by product category and month.

---

## Overview

A two-stage ELT pipeline that extracts raw tables from the Basket Craft MySQL database, loads them into a local PostgreSQL instance (Docker), and transforms them into a single analytics mart table consumed by DBeaver.

Execution is manual — run `pipeline.py` when a data refresh is needed.

---

## Architecture

```
SOURCE
  MySQL  db.isba.co:3306/basket_craft
  tables: orders, order_items, products, categories

        │
        │  extract.py  (full reload via pymysql → psycopg2)
        ▼

DESTINATION  PostgreSQL in Docker (localhost:5432/basket_craft)

  schema: staging
  ├── orders
  ├── order_items
  └── products

        │
        │  transform.py  (SQL aggregation inside Postgres)
        ▼

  schema: analytics
  └── monthly_sales_summary
      columns: year_month, category_name, total_revenue,
               order_count, avg_order_value

        │
        ▼
  DBeaver  →  queries analytics.monthly_sales_summary
```

---

## File Layout

```
basket-craft-pipeline/
├── docker-compose.yml     # PostgreSQL container definition
├── .env                   # credentials — gitignored
├── requirements.txt       # pymysql, psycopg2-binary
├── extract.py             # Stage 1: MySQL → staging.*
├── transform.py           # Stage 2: staging.* → analytics.monthly_sales_summary
└── pipeline.py            # Orchestrator: runs extract then transform
```

---

## Source Schema (MySQL: basket_craft)

| Table | Key Columns |
|---|---|
| `orders` | `order_id`, `created_at`, `website_session_id`, `user_id`, `primary_product_id`, `items_purchased`, `price_usd`, `cogs_usd` |
| `order_items` | `order_item_id`, `created_at`, `order_id`, `product_id`, `is_primary_item`, `price_usd`, `cogs_usd` |
| `products` | `product_id`, `created_at`, `product_name`, `description` |

> No `categories` table exists. The dashboard groups by `product_name` instead of category.

---

## Stage 1 — Extract (`extract.py`)

- Connects to MySQL using `pymysql`
- Connects to Postgres using `psycopg2`
- For each source table: `TRUNCATE` the staging table, then bulk-insert all rows
- Prints row count after each table load
- Runs inside a transaction — rolls back on failure, no partial writes

Tables loaded: `orders`, `order_items`, `products`

---

## Stage 2 — Transform (`transform.py`)

Truncates `analytics.monthly_sales_summary`, then runs:

```sql
INSERT INTO analytics.monthly_sales_summary
SELECT
    DATE_TRUNC('month', oi.created_at)      AS year_month,
    p.product_name,
    SUM(oi.price_usd)                       AS total_revenue,
    COUNT(DISTINCT oi.order_id)             AS order_count,
    SUM(oi.price_usd)
      / NULLIF(COUNT(DISTINCT oi.order_id), 0) AS avg_order_value
FROM staging.order_items oi
JOIN staging.products p ON p.product_id = oi.product_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Output Table: `analytics.monthly_sales_summary`

| Column | Type | Description |
|---|---|---|
| `year_month` | `DATE` | First day of the month (e.g. 2024-01-01) |
| `product_name` | `TEXT` | Product name (no category column exists in source) |
| `total_revenue` | `NUMERIC(12,2)` | Sum of quantity × unit_price |
| `order_count` | `INTEGER` | Distinct orders in that month/category |
| `avg_order_value` | `NUMERIC(10,2)` | total_revenue / order_count |

---

## Docker Setup

`docker-compose.yml` defines a single Postgres 15 service:
- Container name: `basket-craft-db`
- Port: `5432`
- Database: `basket_craft`
- Credentials stored in `.env`

---

## Credentials & Environment

All secrets live in `.env` (gitignored):

```
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_DB=basket_craft
MYSQL_USER=student
MYSQL_PASSWORD=<password>

PG_HOST=localhost
PG_PORT=5432
PG_DB=basket_craft
PG_USER=postgres
PG_PASSWORD=postgres
```

---

## Error Handling

- Connection failures raise immediately with a clear message — no silent failures
- Each stage runs in a single transaction; failure rolls back the entire stage
- Truncate-before-load makes every run idempotent (safe to re-run)
- No retry logic or alerting — this is a manual, local pipeline

---

## Testing

Manual smoke testing via DBeaver:

1. After `extract.py`: verify row counts in `staging.*` match MySQL source tables
2. After `transform.py`: spot-check `analytics.monthly_sales_summary` — pick one month and category, manually verify totals
3. `pipeline.py` prints row counts at each stage for quick sanity checking

---

## Out of Scope

- Incremental/delta loads
- Scheduling / cron
- Data quality checks
- BI tool integration beyond DBeaver
