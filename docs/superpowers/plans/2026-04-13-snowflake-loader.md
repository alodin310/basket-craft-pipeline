# Snowflake Loader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write `load_snowflake.py` — a standalone script that reads all 8 raw Basket Craft tables from AWS RDS PostgreSQL (`raw` schema) and loads them into Snowflake (`basket_craft.raw`), idempotently, with lowercase identifiers.

**Architecture:** Read each table into a pandas DataFrame via SQLAlchemy + psycopg2, force column names to lowercase, then call `write_pandas(..., overwrite=True, auto_create_table=True)` which serializes to Parquet, stages, and fires `COPY INTO` in Snowflake. All credentials come from `.env` via `python-dotenv`. Running the script twice produces identical results.

**Tech Stack:** Python 3.11, `snowflake-connector-python[pandas]`, `pandas`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `pytest`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `load_snowflake.py` | Main loader: RDS → Snowflake for all 8 tables |
| Create | `tests/test_load_snowflake.py` | Unit tests for pure functions |
| Create | `pytest.ini` | Adds project root to Python path so tests can import `load_snowflake` |
| Modify | `requirements.txt` | Add `pandas`, `sqlalchemy`, `snowflake-connector-python[pandas]`, `pytest` |
| Modify | `CLAUDE.md` | Document the new Snowflake loader pipeline hop |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the four new packages to `requirements.txt`**

Open `requirements.txt` (currently contains `pymysql==1.1.1`, `psycopg2-binary==2.9.9`, `python-dotenv==1.0.1`) and append:

```
pandas
sqlalchemy
snowflake-connector-python[pandas]
pytest
```

The full file should now read:
```
pymysql==1.1.1
psycopg2-binary==2.9.9
python-dotenv==1.0.1
pandas
sqlalchemy
snowflake-connector-python[pandas]
pytest
```

- [ ] **Step 2: Install dependencies into the virtual environment**

```bash
source .venv/bin/activate && pip install -r requirements.txt
```

Expected: pip resolves and installs all packages. This takes 60-120 seconds — `snowflake-connector-python` pulls in `pyarrow` and `cryptography`. No errors at the end.

- [ ] **Step 3: Verify the key packages are importable**

```bash
source .venv/bin/activate && python -c "import snowflake.connector; from snowflake.connector.pandas_tools import write_pandas; import pandas; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add snowflake-connector-python, pandas, sqlalchemy, pytest"
```

---

## Task 2: Test Infrastructure + `lowercase_columns`

**Files:**
- Create: `pytest.ini`
- Create: `tests/test_load_snowflake.py`
- Create: `load_snowflake.py` (skeleton with `lowercase_columns` only)

- [ ] **Step 1: Create `pytest.ini` so tests can import from the project root**

Create `pytest.ini` at the project root with this exact content:

```ini
[pytest]
pythonpath = .
```

- [ ] **Step 2: Create `tests/test_load_snowflake.py` with two failing tests**

```python
import pandas as pd
from load_snowflake import lowercase_columns


def test_lowercase_already_lower():
    df = pd.DataFrame({"name": [1], "age": [2]})
    result = lowercase_columns(df)
    assert list(result.columns) == ["name", "age"]


def test_lowercase_mixed_case():
    df = pd.DataFrame({"Name": [1], "AGE": [2], "Order_Id": [3]})
    result = lowercase_columns(df)
    assert list(result.columns) == ["name", "age", "order_id"]
```

- [ ] **Step 3: Run tests — expect ImportError (module not yet created)**

```bash
source .venv/bin/activate && pytest tests/test_load_snowflake.py -v
```

Expected: `ImportError: No module named 'load_snowflake'`

- [ ] **Step 4: Create `load_snowflake.py` skeleton with only `lowercase_columns`**

```python
import os
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

TABLES = [
    "employees",
    "order_item_refunds",
    "order_items",
    "orders",
    "products",
    "users",
    "website_pageviews",
    "website_sessions",
]


def lowercase_columns(df):
    df.columns = [c.lower() for c in df.columns]
    return df
```

- [ ] **Step 5: Run tests — expect both to pass**

```bash
source .venv/bin/activate && pytest tests/test_load_snowflake.py -v
```

Expected:
```
PASSED tests/test_load_snowflake.py::test_lowercase_already_lower
PASSED tests/test_load_snowflake.py::test_lowercase_mixed_case
2 passed
```

- [ ] **Step 6: Commit**

```bash
git add pytest.ini tests/test_load_snowflake.py load_snowflake.py
git commit -m "feat: add lowercase_columns with passing tests"
```

---

## Task 3: Add Connection Helpers + Env Var Test

**Files:**
- Modify: `load_snowflake.py` — add `make_rds_engine()` and `make_sf_conn()`
- Modify: `tests/test_load_snowflake.py` — add env var test

- [ ] **Step 1: Write a failing test for missing env var fast-fail**

Add this test to `tests/test_load_snowflake.py` (append after the existing tests):

```python
from load_snowflake import make_sf_conn
import pytest


def test_make_sf_conn_raises_on_missing_account(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    with pytest.raises(KeyError):
        make_sf_conn()
```

- [ ] **Step 2: Run tests — expect the new test to fail**

```bash
source .venv/bin/activate && pytest tests/test_load_snowflake.py::test_make_sf_conn_raises_on_missing_account -v
```

Expected: `FAILED` — `ImportError` or `AttributeError` because `make_sf_conn` does not exist yet.

- [ ] **Step 3: Add `make_rds_engine` and `make_sf_conn` to `load_snowflake.py`**

Append these two functions after `lowercase_columns` in `load_snowflake.py`:

```python
def make_rds_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['RDS_USER']}:{os.environ['RDS_PASSWORD']}"
        f"@{os.environ['RDS_HOST']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DATABASE']}"
    )
    return create_engine(url)


def make_sf_conn():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )
```

- [ ] **Step 4: Run all tests — expect all three to pass**

```bash
source .venv/bin/activate && pytest tests/test_load_snowflake.py -v
```

Expected:
```
PASSED tests/test_load_snowflake.py::test_lowercase_already_lower
PASSED tests/test_load_snowflake.py::test_lowercase_mixed_case
PASSED tests/test_load_snowflake.py::test_make_sf_conn_raises_on_missing_account
3 passed
```

- [ ] **Step 5: Commit**

```bash
git add load_snowflake.py tests/test_load_snowflake.py
git commit -m "feat: add make_rds_engine and make_sf_conn with env var test"
```

---

## Task 4: Implement `load_tables` and Run End-to-End

**Files:**
- Modify: `load_snowflake.py` — add `load_tables()` and `__main__` block

- [ ] **Step 1: Append `load_tables()` and the `__main__` block to `load_snowflake.py`**

The complete final `load_snowflake.py` should look like this (replace the file entirely to ensure no drift from earlier skeleton steps):

```python
import os
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

TABLES = [
    "employees",
    "order_item_refunds",
    "order_items",
    "orders",
    "products",
    "users",
    "website_pageviews",
    "website_sessions",
]


def lowercase_columns(df):
    df.columns = [c.lower() for c in df.columns]
    return df


def make_rds_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['RDS_USER']}:{os.environ['RDS_PASSWORD']}"
        f"@{os.environ['RDS_HOST']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DATABASE']}"
    )
    return create_engine(url)


def make_sf_conn():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def load_tables():
    engine = make_rds_engine()
    sf = make_sf_conn()

    with engine.connect() as conn:
        for table in TABLES:
            df = pd.read_sql(f"SELECT * FROM raw.{table}", conn)
            df = lowercase_columns(df)
            success, nchunks, nrows, _ = write_pandas(
                sf,
                df,
                table_name=table,
                database=os.environ["SNOWFLAKE_DATABASE"],
                schema=os.environ["SNOWFLAKE_SCHEMA"],
                overwrite=True,
                auto_create_table=True,
            )
            print(f"  {table}: {nrows:,} rows loaded")

    sf.close()
    print("Load to Snowflake complete.")


if __name__ == "__main__":
    load_tables()
```

- [ ] **Step 2: Run the unit test suite to confirm nothing regressed**

```bash
source .venv/bin/activate && pytest tests/test_load_snowflake.py -v
```

Expected: `3 passed`

- [ ] **Step 3: Run the loader end-to-end**

```bash
source .venv/bin/activate && python load_snowflake.py
```

Expected output (row counts will match RDS):
```
  employees: 18 rows loaded
  order_item_refunds: X rows loaded
  order_items: X rows loaded
  orders: X rows loaded
  products: X rows loaded
  users: X rows loaded
  website_pageviews: 1,188,124 rows loaded
  website_sessions: X rows loaded
Load to Snowflake complete.
```

If a connection error appears, check:
- RDS: security group inbound rule allows your current IP on port 5432
- Snowflake: `SNOWFLAKE_ACCOUNT` value in `.env` matches the identifier shown in Snowsight under **Admin > Accounts**

- [ ] **Step 4: Verify row counts in Snowsight**

Open a Snowsight worksheet and run:

```sql
USE DATABASE basket_craft;
USE SCHEMA raw;

SELECT 'employees'         AS tbl, COUNT(*) AS n FROM employees         UNION ALL
SELECT 'order_item_refunds',        COUNT(*)     FROM order_item_refunds UNION ALL
SELECT 'order_items',               COUNT(*)     FROM order_items        UNION ALL
SELECT 'orders',                    COUNT(*)     FROM orders             UNION ALL
SELECT 'products',                  COUNT(*)     FROM products           UNION ALL
SELECT 'users',                     COUNT(*)     FROM users              UNION ALL
SELECT 'website_pageviews',         COUNT(*)     FROM website_pageviews  UNION ALL
SELECT 'website_sessions',          COUNT(*)     FROM website_sessions
ORDER BY tbl;
```

Confirm all 8 rows are present and each count matches the RDS row count from Session 02.

- [ ] **Step 5: Confirm idempotency — run the script a second time**

```bash
source .venv/bin/activate && python load_snowflake.py
```

Expected: same row counts as Step 3. No duplicates, no errors.

- [ ] **Step 6: Commit**

```bash
git add load_snowflake.py
git commit -m "feat: implement load_tables — RDS to Snowflake raw"
```

---

## Task 5: Update CLAUDE.md and Push

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add a Snowflake loader section to `CLAUDE.md`**

Open `CLAUDE.md` and add the following under the `## Commands` section (after the existing RDS pipeline entry):

```markdown
# --- Snowflake pipeline (RDS PostgreSQL → Snowflake) ---
python load_snowflake.py   # load all 8 raw tables from RDS into Snowflake basket_craft.raw
```

And add a new subsection under `## Architecture`:

```markdown
### Pipeline 3 — Snowflake (RDS PostgreSQL → Snowflake)

`load_snowflake.py` — standalone script, no transform stage.

- Reads all 8 tables from the `raw` schema on AWS RDS into pandas DataFrames.
- Forces all column names to lowercase (Snowflake identifier safety for dbt Session 04).
- Writes to `basket_craft.raw` on Snowflake using `write_pandas(..., overwrite=True, auto_create_table=True)`. Fully idempotent — drop+recreate on every run.
- Uses `SNOWFLAKE_*` env vars from `.env`.

**Snowsight connection:** Log in at app.snowflake.com → Data → Databases → BASKET_CRAFT → RAW
```

Also add to the `## Environment` section:

```markdown
- **Snowflake** — `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`
```

- [ ] **Step 2: Commit and push everything**

```bash
git add CLAUDE.md pytest.ini tests/ load_snowflake.py requirements.txt
git commit -m "feat: add Snowflake loader (RDS → Snowflake raw)"
git push
```

- [ ] **Step 3: Confirm on GitHub**

Open the repo on GitHub and verify these files are present in the latest commit:
- `load_snowflake.py`
- `requirements.txt` (with snowflake deps)
- `CLAUDE.md` (updated with Snowflake section)
- `tests/test_load_snowflake.py`
- `pytest.ini`

---

## Self-Review Checklist

- [x] **Spec coverage:** All 8 tables ✓ | in-memory load ✓ | `overwrite=True` idempotency ✓ | lowercase columns ✓ | credentials from `.env` ✓ | `write_pandas` ✓
- [x] **No placeholders:** All steps contain exact code, exact commands, exact expected output
- [x] **Type consistency:** `lowercase_columns` defined in Task 2 Step 4, imported in tests Task 2 Step 2, called in `load_tables` Task 4 Step 1 — name consistent throughout
- [x] **`make_sf_conn`** defined in Task 3 Step 3, imported in test Task 3 Step 1 — consistent
- [x] **`write_pandas` return tuple** — `(success, nchunks, nrows, _)` used consistently in Task 4 Step 1
