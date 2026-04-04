# Basket Craft Sales Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-stage ELT pipeline that extracts three MySQL tables into a local Postgres staging schema, then aggregates them into `analytics.monthly_sales_summary` for DBeaver.

**Architecture:** `extract.py` full-reloads `orders`, `order_items`, and `products` from MySQL (`db.isba.co`) into `staging.*` in a local Postgres Docker container. `transform.py` runs a single SQL aggregation inside Postgres to produce the mart table. `pipeline.py` calls both in sequence.

**Tech Stack:** Python 3.11, pymysql 1.1.1, psycopg2-binary 2.9.9, python-dotenv 1.0.1, PostgreSQL 15 (Docker)

---

## File Map

| File | Created/Modified | Responsibility |
|---|---|---|
| `requirements.txt` | Create | Python dependencies |
| `.env.example` | Create | Credential template (committed) |
| `.env` | Create (not committed) | Actual credentials |
| `docker-compose.yml` | Create | Postgres 15 container |
| `extract.py` | Create | MySQL → staging.* (creates tables, truncates, loads) |
| `transform.py` | Create | staging.* → analytics.monthly_sales_summary |
| `pipeline.py` | Create | Orchestrator: calls extract then transform |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.env`

- [ ] **Step 1: Create requirements.txt**

```
pymysql==1.1.1
psycopg2-binary==2.9.9
python-dotenv==1.0.1
```

- [ ] **Step 2: Create .env.example**

```
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_DB=basket_craft
MYSQL_USER=student
MYSQL_PASSWORD=your_password_here

PG_HOST=localhost
PG_PORT=5432
PG_DB=basket_craft
PG_USER=postgres
PG_PASSWORD=postgres
```

- [ ] **Step 3: Create .env with real credentials**

Copy `.env.example` to `.env` and fill in `MYSQL_PASSWORD`.

> **Note:** The MySQL password stored in DBeaver can be retrieved from macOS Keychain:
> open **Keychain Access** → search for `db.isba.co` → double-click the entry → check "Show password".

```
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_DB=basket_craft
MYSQL_USER=student
MYSQL_PASSWORD=<value from DBeaver/Keychain>

PG_HOST=localhost
PG_PORT=5432
PG_DB=basket_craft
PG_USER=postgres
PG_PASSWORD=postgres
```

- [ ] **Step 4: Verify .env is gitignored**

Run:
```bash
git check-ignore -v .env
```
Expected output: `.gitignore:139:.env	.env`

- [ ] **Step 5: Create virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: packages install without errors.

- [ ] **Step 6: Commit scaffolding**

```bash
git add requirements.txt .env.example
git commit -m "feat: add project scaffolding and dependencies"
```

---

## Task 2: Docker Compose — Postgres Container

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgres:15
    container_name: basket-craft-db
    environment:
      POSTGRES_DB: basket_craft
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - basket_craft_data:/var/lib/postgresql/data

volumes:
  basket_craft_data:
```

- [ ] **Step 2: Start the container**

```bash
docker compose up -d
```

Expected output:
```
✔ Container basket-craft-db  Started
```

- [ ] **Step 3: Verify Postgres is reachable**

```bash
docker exec basket-craft-db psql -U postgres -d basket_craft -c "SELECT version();"
```

Expected output includes: `PostgreSQL 15`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add Postgres 15 Docker container"
```

---

## Task 3: Write extract.py

**Files:**
- Create: `extract.py`

- [ ] **Step 1: Create extract.py**

```python
import os
import pymysql
import psycopg2
from dotenv import load_dotenv

load_dotenv()

MYSQL = dict(
    host=os.environ["MYSQL_HOST"],
    port=int(os.environ["MYSQL_PORT"]),
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DB"],
    cursorclass=pymysql.cursors.Cursor,
)

PG = dict(
    host=os.environ["PG_HOST"],
    port=int(os.environ["PG_PORT"]),
    dbname=os.environ["PG_DB"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
)

SETUP_SQL = [
    "CREATE SCHEMA IF NOT EXISTS staging",
    """
    CREATE TABLE IF NOT EXISTS staging.orders (
        order_id           INTEGER PRIMARY KEY,
        created_at         TIMESTAMP,
        website_session_id INTEGER,
        user_id            INTEGER,
        primary_product_id INTEGER,
        items_purchased    SMALLINT,
        price_usd          NUMERIC(6,2),
        cogs_usd           NUMERIC(6,2)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS staging.order_items (
        order_item_id   INTEGER PRIMARY KEY,
        created_at      TIMESTAMP,
        order_id        INTEGER,
        product_id      INTEGER,
        is_primary_item SMALLINT,
        price_usd       NUMERIC(6,2),
        cogs_usd        NUMERIC(6,2)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS staging.products (
        product_id   INTEGER PRIMARY KEY,
        created_at   TIMESTAMP,
        product_name VARCHAR(50),
        description  TEXT
    )
    """,
]

TABLES = ["orders", "order_items", "products"]


def extract():
    mysql = pymysql.connect(**MYSQL)
    pg = psycopg2.connect(**PG)

    with pg, pg.cursor() as pg_cur:
        for stmt in SETUP_SQL:
            pg_cur.execute(stmt)

        with mysql.cursor() as my_cur:
            for table in TABLES:
                my_cur.execute(f"SELECT * FROM {table}")
                rows = my_cur.fetchall()
                pg_cur.execute(f"TRUNCATE TABLE staging.{table} CASCADE")
                if rows:
                    placeholders = ",".join(["%s"] * len(rows[0]))
                    pg_cur.executemany(
                        f"INSERT INTO staging.{table} VALUES ({placeholders})",
                        rows,
                    )
                print(f"  staging.{table}: {len(rows)} rows loaded")

    mysql.close()
    print("Extract complete.")


if __name__ == "__main__":
    extract()
```

- [ ] **Step 2: Run extract**

```bash
python extract.py
```

Expected output (row counts will vary):
```
  staging.orders: 32313 rows loaded
  staging.order_items: 54721 rows loaded
  staging.products: 4 rows loaded
Extract complete.
```

- [ ] **Step 3: Verify staging tables in DBeaver**

In DBeaver, connect to the local Postgres (`localhost:5432 / basket_craft / postgres / postgres`) and run:

```sql
SELECT 'orders'      AS tbl, COUNT(*) FROM staging.orders
UNION ALL
SELECT 'order_items' AS tbl, COUNT(*) FROM staging.order_items
UNION ALL
SELECT 'products'    AS tbl, COUNT(*) FROM staging.products;
```

Expected: row counts match what `extract.py` printed.

- [ ] **Step 4: Commit**

```bash
git add extract.py
git commit -m "feat: add extract stage (MySQL → staging)"
```

---

## Task 4: Write transform.py

**Files:**
- Create: `transform.py`

- [ ] **Step 1: Create transform.py**

```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PG = dict(
    host=os.environ["PG_HOST"],
    port=int(os.environ["PG_PORT"]),
    dbname=os.environ["PG_DB"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
)

SETUP_SQL = [
    "CREATE SCHEMA IF NOT EXISTS analytics",
    """
    CREATE TABLE IF NOT EXISTS analytics.monthly_sales_summary (
        year_month      DATE,
        product_name    TEXT,
        total_revenue   NUMERIC(12,2),
        order_count     INTEGER,
        avg_order_value NUMERIC(10,2),
        PRIMARY KEY (year_month, product_name)
    )
    """,
]

TRANSFORM_SQL = """
INSERT INTO analytics.monthly_sales_summary
SELECT
    DATE_TRUNC('month', oi.created_at)::DATE           AS year_month,
    p.product_name,
    SUM(oi.price_usd)                                  AS total_revenue,
    COUNT(DISTINCT oi.order_id)                        AS order_count,
    SUM(oi.price_usd)
        / NULLIF(COUNT(DISTINCT oi.order_id), 0)       AS avg_order_value
FROM staging.order_items oi
JOIN staging.products p ON p.product_id = oi.product_id
GROUP BY 1, 2
ORDER BY 1, 2
"""


def transform():
    pg = psycopg2.connect(**PG)

    with pg, pg.cursor() as cur:
        for stmt in SETUP_SQL:
            cur.execute(stmt)

        cur.execute("TRUNCATE TABLE analytics.monthly_sales_summary")
        cur.execute(TRANSFORM_SQL)
        cur.execute("SELECT COUNT(*) FROM analytics.monthly_sales_summary")
        count = cur.fetchone()[0]
        print(f"  analytics.monthly_sales_summary: {count} rows written")

    print("Transform complete.")


if __name__ == "__main__":
    transform()
```

- [ ] **Step 2: Run transform**

```bash
python transform.py
```

Expected output:
```
  analytics.monthly_sales_summary: <N> rows written
Transform complete.
```

- [ ] **Step 3: Spot-check results in DBeaver**

Run in DBeaver:

```sql
-- Preview the mart table
SELECT *
FROM analytics.monthly_sales_summary
ORDER BY year_month, product_name
LIMIT 20;
```

Then manually verify one row: pick a product and month, go back to `staging.order_items` and compute the total by hand:

```sql
-- Manual check: replace the values with one row from your results
SELECT
    COUNT(DISTINCT oi.order_id)  AS order_count,
    SUM(oi.price_usd)            AS total_revenue
FROM staging.order_items oi
JOIN staging.products p ON p.product_id = oi.product_id
WHERE DATE_TRUNC('month', oi.created_at) = '2013-03-01'
  AND p.product_name = 'The Original Mr. Fuzzy Bear';
```

Numbers should match the corresponding row in `monthly_sales_summary`.

- [ ] **Step 4: Commit**

```bash
git add transform.py
git commit -m "feat: add transform stage (staging → analytics mart)"
```

---

## Task 5: Write pipeline.py and Final Smoke Test

**Files:**
- Create: `pipeline.py`

- [ ] **Step 1: Create pipeline.py**

```python
from extract import extract
from transform import transform

print("=== Basket Craft Pipeline ===")
print("\n[1/2] Extract: MySQL → staging")
extract()
print("\n[2/2] Transform: staging → analytics")
transform()
print("\nPipeline complete.")
```

- [ ] **Step 2: Run the full pipeline end-to-end**

```bash
python pipeline.py
```

Expected output:
```
=== Basket Craft Pipeline ===

[1/2] Extract: MySQL → staging
  staging.orders: 32313 rows loaded
  staging.order_items: 54721 rows loaded
  staging.products: 4 rows loaded
Extract complete.

[2/2] Transform: staging → analytics
  analytics.monthly_sales_summary: <N> rows written
Transform complete.

Pipeline complete.
```

- [ ] **Step 3: Final DBeaver smoke test**

Run each of these queries in DBeaver and confirm they return reasonable results:

```sql
-- 1. Monthly revenue by product (the dashboard view)
SELECT
    year_month,
    product_name,
    total_revenue,
    order_count,
    avg_order_value
FROM analytics.monthly_sales_summary
ORDER BY year_month, product_name;

-- 2. Total revenue per product (all time)
SELECT
    product_name,
    SUM(total_revenue)  AS all_time_revenue,
    SUM(order_count)    AS all_time_orders
FROM analytics.monthly_sales_summary
GROUP BY product_name
ORDER BY all_time_revenue DESC;

-- 3. Monthly revenue trend (all products combined)
SELECT
    year_month,
    SUM(total_revenue)  AS monthly_revenue,
    SUM(order_count)    AS monthly_orders
FROM analytics.monthly_sales_summary
GROUP BY year_month
ORDER BY year_month;
```

- [ ] **Step 4: Commit and push**

```bash
git add pipeline.py
git commit -m "feat: add pipeline orchestrator and complete implementation"
git push origin main
```
