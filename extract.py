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
