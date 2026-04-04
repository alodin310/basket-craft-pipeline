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
